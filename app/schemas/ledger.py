from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.core.enums import LedgerEntryType


class LedgerEntryResponse(BaseModel):
    id: int
    customer_id: int
    invoice_id: Optional[int] = None
    entry_type: LedgerEntryType
    amount: Decimal
    currency: str
    reference_id: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
