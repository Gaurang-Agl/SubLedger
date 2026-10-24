from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.core.enums import SubscriptionStatus
from app.schemas.plan import PlanResponse


class SubscriptionCreate(BaseModel):
    customer_id: int = Field(..., gt=0)
    plan_id: int = Field(..., gt=0)
    start_date: Optional[datetime] = None


class SubscriptionResponse(BaseModel):
    id: int
    customer_id: int
    plan_id: int
    status: SubscriptionStatus
    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    plan: Optional[PlanResponse] = None

    model_config = ConfigDict(from_attributes=True)
