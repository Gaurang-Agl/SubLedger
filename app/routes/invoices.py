from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.schemas.invoice import InvoiceGenerateRequest, InvoiceResponse
from app.services.invoice_service import InvoiceService
from app.routes.deps import get_invoice_service

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("/generate", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def generate_invoice(
    data: InvoiceGenerateRequest,
    service: InvoiceService = Depends(get_invoice_service)
):
    """Generate an invoice for an active subscription."""
    return service.generate_invoice(data)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    service: InvoiceService = Depends(get_invoice_service)
):
    """Fetch invoice details by ID."""
    return service.get_invoice(invoice_id)


@router.get("", response_model=List[InvoiceResponse])
def list_invoices(
    subscription_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    service: InvoiceService = Depends(get_invoice_service)
):
    """List invoices, optionally filtered by subscription or customer."""
    return service.list_invoices(
        subscription_id=subscription_id,
        customer_id=customer_id,
        skip=skip,
        limit=limit
    )


@router.post("/mark-overdue")
def mark_overdue_invoices(
    service: InvoiceService = Depends(get_invoice_service)
):
    """Batch job endpoint to transition unpaid invoices past due_date to OVERDUE."""
    updated_count = service.mark_overdue_invoices()
    return {"status": "success", "marked_overdue_count": updated_count}
