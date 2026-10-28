from typing import List
from fastapi import APIRouter, Depends, status
from app.schemas.customer import CustomerCreate, CustomerResponse
from app.services.customer_service import CustomerService
from app.routes.deps import get_customer_service

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    service: CustomerService = Depends(get_customer_service)
):
    """Create a customer with unique email."""
    return service.create_customer(data)


@router.get("", response_model=List[CustomerResponse])
def list_customers(
    skip: int = 0,
    limit: int = 100,
    service: CustomerService = Depends(get_customer_service)
):
    """List customers."""
    return service.list_customers(skip=skip, limit=limit)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service)
):
    """Fetch customer details by ID."""
    return service.get_customer(customer_id)
