from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.ledger_entry import LedgerEntry
from app.core.enums import LedgerEntryType


class LedgerRepository:
    """
    Append-only repository for immutable financial audit events.
    To strictly enforce the append-only invariant, no update or delete operations are provided.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, entry_id: int) -> Optional[LedgerEntry]:
        return self.db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()

    def list_by_customer(
        self,
        customer_id: int,
        entry_type: Optional[LedgerEntryType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[LedgerEntry]:
        query = self.db.query(LedgerEntry).filter(LedgerEntry.customer_id == customer_id)
        if entry_type:
            query = query.filter(LedgerEntry.entry_type == entry_type)
        return query.order_by(LedgerEntry.created_at.asc()).offset(skip).limit(limit).all()

    def list_by_invoice(self, invoice_id: int) -> List[LedgerEntry]:
        return self.db.query(LedgerEntry).filter(
            LedgerEntry.invoice_id == invoice_id
        ).order_by(LedgerEntry.created_at.asc()).all()

    def create(self, entry: LedgerEntry) -> LedgerEntry:
        self.db.add(entry)
        self.db.flush()
        self.db.refresh(entry)
        return entry

    def update(self, *args, **kwargs):
        raise NotImplementedError("Ledger entries are strictly append-only and cannot be updated.")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Ledger entries are strictly append-only and cannot be deleted.")
