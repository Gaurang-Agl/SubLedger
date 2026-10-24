from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.core.enums import InvoiceStatus


class InvoiceGenerateRequest(BaseModel):
    subscription_id: int = Field(..., gt=0)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    due_date: Optional[datetime] = None


class InvoiceResponse(BaseModel):
    id: int
    subscription_id: int
    customer_id: int
    amount_due: Decimal
    amount_paid: Decimal
    currency: str
    status: InvoiceStatus
    period_start: datetime
    period_end: datetime
    due_date: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
