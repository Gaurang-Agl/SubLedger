from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse
from app.services.subscription_service import SubscriptionService
from app.routes.deps import get_subscription_service

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    data: SubscriptionCreate,
    service: SubscriptionService = Depends(get_subscription_service)
):
    """Create and activate a customer subscription."""
    return service.create_subscription(data)


@router.get("", response_model=List[SubscriptionResponse])
def list_subscriptions(
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    skip: int = 0,
    limit: int = 100,
    service: SubscriptionService = Depends(get_subscription_service)
):
    """List subscriptions, optionally filtered by customer."""
    return service.list_subscriptions(customer_id=customer_id, skip=skip, limit=limit)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    service: SubscriptionService = Depends(get_subscription_service)
):
    """Fetch subscription details by ID."""
    return service.get_subscription(subscription_id)


@router.patch("/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    subscription_id: int,
    service: SubscriptionService = Depends(get_subscription_service)
):
    """Cancel an active subscription."""
    return service.cancel_subscription(subscription_id)
