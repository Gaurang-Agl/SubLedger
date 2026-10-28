from typing import List
from fastapi import APIRouter, Depends, status
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse
from app.services.plan_service import PlanService
from app.routes.deps import get_plan_service

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    data: PlanCreate,
    service: PlanService = Depends(get_plan_service)
):
    """Create a new subscription plan."""
    return service.create_plan(data)


@router.get("", response_model=List[PlanResponse])
def list_plans(
    skip: int = 0,
    limit: int = 100,
    service: PlanService = Depends(get_plan_service)
):
    """List subscription plans."""
    return service.list_plans(skip=skip, limit=limit)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    service: PlanService = Depends(get_plan_service)
):
    """Fetch plan details by ID."""
    return service.get_plan(plan_id)


@router.patch("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: int,
    data: PlanUpdate,
    service: PlanService = Depends(get_plan_service)
):
    """Update or deactivate a subscription plan."""
    return service.update_plan(plan_id, data)
