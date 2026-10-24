from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from app.core.enums import CustomerStatus


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(..., max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    status: CustomerStatus = Field(default=CustomerStatus.ACTIVE)


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    company_name: Optional[str] = None
    status: CustomerStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
