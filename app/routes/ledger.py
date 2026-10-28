from typing import List, Optional
from fastapi import APIRouter, Depends
from app.core.enums import LedgerEntryType
from app.schemas.ledger import LedgerEntryResponse
from app.services.ledger_service import LedgerService
from app.routes.deps import get_ledger_service

router = APIRouter(tags=["Ledger"])


@router.get("/customers/{customer_id}/ledger", response_model=List[LedgerEntryResponse])
def get_customer_ledger(
    customer_id: int,
    entry_type: Optional[LedgerEntryType] = None,
    skip: int = 0,
    limit: int = 100,
    service: LedgerService = Depends(get_ledger_service)
):
    """Fetch immutable append-only ledger history for a customer with optional entry_type filtering and pagination."""
    return service.get_customer_ledger(customer_id, entry_type=entry_type, skip=skip, limit=limit)


@router.get("/invoices/{invoice_id}/ledger", response_model=List[LedgerEntryResponse])
def get_invoice_ledger(
    invoice_id: int,
    service: LedgerService = Depends(get_ledger_service)
):
    """Fetch immutable append-only ledger history for an invoice."""
    return service.get_invoice_ledger(invoice_id)
