from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.core.enums import PlanStatus, BillingCycle


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    billing_cycle: BillingCycle = Field(..., description="Billing frequency: monthly, quarterly, yearly, custom")
    price: Decimal = Field(..., description="Price must be strictly greater than 0")
    currency: str = Field(default="USD", min_length=3, max_length=10)
    status: PlanStatus = Field(default=PlanStatus.ACTIVE)

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Plan price must be greater than 0")
        return v


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    billing_cycle: Optional[BillingCycle] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[PlanStatus] = None

    @field_validator("price")
    @classmethod
    def validate_price_if_present(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Plan price must be greater than 0")
        return v


class PlanResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    billing_cycle: BillingCycle
    price: Decimal
    currency: str
    status: PlanStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
