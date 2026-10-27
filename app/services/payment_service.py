from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.payment_attempt import PaymentAttempt
from app.models.invoice import Invoice
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.payment_repo import PaymentAttemptRepository
from app.services.invoice_service import InvoiceService
from app.services.ledger_service import LedgerService
from app.schemas.payment import PaymentRecordRequest
from app.core.enums import PaymentStatus, InvoiceStatus, LedgerEntryType
from app.core.exceptions import NotFoundException, BusinessRuleException, ConflictException


class PaymentService:
    def __init__(
        self,
        db: Session,
        invoice_repo: Optional[InvoiceRepository] = None,
        payment_attempt_repo: Optional[PaymentAttemptRepository] = None,
        ledger_service: Optional[LedgerService] = None,
        invoice_service: Optional[InvoiceService] = None
    ):
        self.db = db
        self.invoice_repo = invoice_repo or InvoiceRepository(db)
        self.payment_attempt_repo = payment_attempt_repo or PaymentAttemptRepository(db)
        self.ledger_service = ledger_service or LedgerService(db)
        self.invoice_service = invoice_service or InvoiceService(db, invoice_repo=self.invoice_repo, ledger_service=self.ledger_service)

    def record_payment(self, data: PaymentRecordRequest) -> Tuple[PaymentAttempt, Invoice]:
        # 1. Fetch invoice with row lock for concurrency protection
        invoice = self.invoice_repo.get_by_id(data.invoice_id, for_update=True)
        if not invoice:
            raise NotFoundException(f"Invoice with id {data.invoice_id} not found")

        if invoice.status == InvoiceStatus.VOID:
            raise BusinessRuleException("Cannot record payment for a voided invoice")

        # 2. Currency Validation: Prevent currency mismatch bugs
        if data.currency.upper() != invoice.currency.upper():
            raise BusinessRuleException(
                f"Payment currency '{data.currency.upper()}' does not match invoice currency '{invoice.currency.upper()}'"
            )

        # 3. Idempotency Check: Prevent duplicate payment recording via replayed provider_reference
        if data.provider_reference:
            existing_payment = self.payment_attempt_repo.get_by_provider_reference(data.provider_reference)
            if existing_payment and existing_payment.status == PaymentStatus.SUCCESS:
                raise ConflictException(
                    f"Payment attempt with provider reference '{data.provider_reference}' has already been processed successfully"
                )

        remaining = invoice.amount_due - invoice.amount_paid

        # 4. Business Rule: A successful payment cannot exceed remaining unpaid amount
        if data.status == PaymentStatus.SUCCESS:
            if remaining <= Decimal("0.00"):
                raise BusinessRuleException("Invoice is already fully paid")
            if data.amount > remaining:
                raise BusinessRuleException(
                    f"Payment amount {data.amount} exceeds remaining unpaid invoice amount of {remaining}"
                )

        # 3. Create Payment Attempt Record
        payment_attempt = PaymentAttempt(
            invoice_id=invoice.id,
            amount=data.amount,
            currency=data.currency.upper(),
            status=data.status,
            provider_reference=data.provider_reference,
            failure_reason=data.failure_reason if data.status == PaymentStatus.FAILED else None
        )
        created_attempt = self.payment_attempt_repo.create(payment_attempt)

        # 4. Handle success vs failure
        if data.status == PaymentStatus.SUCCESS:
            # Trigger invoice status update via InvoiceService (ownership separation)
            self.invoice_service.apply_payment(invoice, data.amount)

            # Record payment_success ledger entry
            self.ledger_service.record_entry(
                customer_id=invoice.customer_id,
                invoice_id=invoice.id,
                entry_type=LedgerEntryType.PAYMENT_SUCCESS,
                amount=data.amount,
                currency=data.currency.upper(),
                reference_id=data.provider_reference,
                description=f"Successful payment of {data.amount} {data.currency} for invoice #{invoice.id}"
            )
        else:
            # Failed payment: DO NOT increase amount_paid
            # Record payment_failure ledger entry
            self.ledger_service.record_entry(
                customer_id=invoice.customer_id,
                invoice_id=invoice.id,
                entry_type=LedgerEntryType.PAYMENT_FAILURE,
                amount=data.amount,
                currency=data.currency.upper(),
                reference_id=data.provider_reference,
                description=f"Failed payment attempt: {data.failure_reason or 'Payment rejected'}"
            )

        # 5. Commit transaction atomically
        self.db.commit()
        self.db.refresh(created_attempt)
        self.db.refresh(invoice)

        return created_attempt, invoice
