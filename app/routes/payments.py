from fastapi import APIRouter, Depends, status
from app.schemas.payment import PaymentRecordRequest, PaymentRecordResponse, PaymentAttemptResponse
from app.schemas.invoice import InvoiceResponse
from app.services.payment_service import PaymentService
from app.routes.deps import get_payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/record", response_model=PaymentRecordResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    data: PaymentRecordRequest,
    service: PaymentService = Depends(get_payment_service)
):
    """
    Record a payment attempt.
    Successful payments update invoice status and paid amount, and generate a payment_success ledger entry.
    Failed payments do not update paid amount, and generate a payment_failure ledger entry.
    """
    attempt, invoice = service.record_payment(data)
    return PaymentRecordResponse(
        payment_attempt=PaymentAttemptResponse.model_validate(attempt),
        invoice=InvoiceResponse.model_validate(invoice)
    )
