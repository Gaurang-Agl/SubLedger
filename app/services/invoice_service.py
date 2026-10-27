from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.repositories.plan_repo import PlanRepository
from app.services.ledger_service import LedgerService
from app.schemas.invoice import InvoiceGenerateRequest
from app.core.enums import InvoiceStatus, SubscriptionStatus, LedgerEntryType
from app.core.exceptions import NotFoundException, BusinessRuleException


class InvoiceService:
    def __init__(
        self,
        db: Session,
        subscription_repo: Optional[SubscriptionRepository] = None,
        plan_repo: Optional[PlanRepository] = None,
        invoice_repo: Optional[InvoiceRepository] = None,
        ledger_service: Optional[LedgerService] = None
    ):
        self.db = db
        self.subscription_repo = subscription_repo or SubscriptionRepository(db)
        self.plan_repo = plan_repo or PlanRepository(db)
        self.invoice_repo = invoice_repo or InvoiceRepository(db)
        self.ledger_service = ledger_service or LedgerService(db)

    def generate_invoice(self, data: InvoiceGenerateRequest) -> Invoice:
        # 1. Fetch subscription
        sub = self.subscription_repo.get_by_id(data.subscription_id)
        if not sub:
            raise NotFoundException(f"Subscription with id {data.subscription_id} not found")

        # 2. Verify subscription is active
        if sub.status != SubscriptionStatus.ACTIVE:
            raise BusinessRuleException("Cannot generate invoice for a non-active subscription")

        # 3. Snapshot plan price at generation time
        plan = self.plan_repo.get_by_id(sub.plan_id)
        if not plan:
            raise NotFoundException(f"Plan with id {sub.plan_id} not found")

        amount_due = plan.price
        period_start = data.period_start or sub.current_period_start
        period_end = data.period_end or sub.current_period_end
        due_date = data.due_date or (period_start + timedelta(days=14))

        # 4. Create Invoice with issued status
        invoice = Invoice(
            subscription_id=sub.id,
            customer_id=sub.customer_id,
            amount_due=amount_due,
            amount_paid=Decimal("0.00"),
            currency=plan.currency,
            status=InvoiceStatus.ISSUED,
            period_start=period_start,
            period_end=period_end,
            due_date=due_date
        )
        created_invoice = self.invoice_repo.create(invoice)

        # 5. Record immutable invoice_created ledger entry
        self.ledger_service.record_entry(
            customer_id=sub.customer_id,
            invoice_id=created_invoice.id,
            entry_type=LedgerEntryType.INVOICE_CREATED,
            amount=amount_due,
            currency=plan.currency,
            reference_id=str(created_invoice.id),
            description=f"Invoice #{created_invoice.id} created for subscription #{sub.id}"
        )

        # 6. Commit transaction atomically
        self.db.commit()
        self.db.refresh(created_invoice)
        return created_invoice

    def apply_payment(self, invoice: Invoice, amount: Decimal) -> Invoice:
        """
        Updates invoice amount_paid and calculates the new status (partially_paid vs paid).
        Owned by InvoiceService per the Service Responsibility matrix.
        """
        new_paid = invoice.amount_paid + amount
        invoice.amount_paid = new_paid

        if new_paid >= invoice.amount_due:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        return self.invoice_repo.update(invoice)

    def check_and_update_overdue(self, invoice: Invoice) -> Invoice:
        """Transitions unpaid invoice to OVERDUE if due_date has elapsed."""
        now = datetime.now(timezone.utc)
        due_date = invoice.due_date
        if due_date and due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)
        if due_date and due_date < now and invoice.status in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID):
            invoice.status = InvoiceStatus.OVERDUE
            self.invoice_repo.update(invoice)
            self.db.commit()
        return invoice

    def get_invoice(self, invoice_id: int) -> Invoice:
        inv = self.invoice_repo.get_by_id(invoice_id)
        if not inv:
            raise NotFoundException(f"Invoice with id {invoice_id} not found")
        return self.check_and_update_overdue(inv)

    def mark_overdue_invoices(self) -> int:
        """Finds all issued or partially paid invoices past due_date and transitions them to OVERDUE."""
        now = datetime.now(timezone.utc)
        invoices = self.db.query(Invoice).filter(
            Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]),
            Invoice.due_date < now
        ).all()
        count = 0
        for inv in invoices:
            inv.status = InvoiceStatus.OVERDUE
            self.invoice_repo.update(inv)
            count += 1
        if count > 0:
            self.db.commit()
        return count

    def list_invoices(
        self,
        subscription_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        return self.invoice_repo.list(
            subscription_id=subscription_id,
            customer_id=customer_id,
            skip=skip,
            limit=limit
        )
