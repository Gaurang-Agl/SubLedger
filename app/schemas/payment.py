from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.core.enums import PaymentStatus
from app.schemas.invoice import InvoiceResponse


class PaymentRecordRequest(BaseModel):
    invoice_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., description="Payment amount must be greater than 0")
    currency: str = Field(default="USD", min_length=3, max_length=10)
    status: PaymentStatus = Field(..., description="Payment status: success or failed")
    provider_reference: str = Field(..., min_length=1, max_length=255)
    failure_reason: Optional[str] = Field(None, max_length=500)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Payment amount must be greater than 0")
        return v


class PaymentAttemptResponse(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider_reference: str
    failure_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentRecordResponse(BaseModel):
    payment_attempt: PaymentAttemptResponse
    invoice: InvoiceResponse
