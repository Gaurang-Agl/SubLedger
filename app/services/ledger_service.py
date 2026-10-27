from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.ledger_entry import LedgerEntry
from app.repositories.ledger_repo import LedgerRepository
from app.core.enums import LedgerEntryType


class LedgerService:
    def __init__(self, db: Session, ledger_repo: Optional[LedgerRepository] = None):
        self.db = db
        self.ledger_repo = ledger_repo or LedgerRepository(db)

    def record_entry(
        self,
        customer_id: int,
        invoice_id: Optional[int],
        entry_type: LedgerEntryType,
        amount: Decimal,
        currency: str,
        reference_id: str,
        description: Optional[str] = None
    ) -> LedgerEntry:
        entry = LedgerEntry(
            customer_id=customer_id,
            invoice_id=invoice_id,
            entry_type=entry_type,
            amount=amount,
            currency=currency.upper(),
            reference_id=reference_id,
            description=description
        )
        return self.ledger_repo.create(entry)

    def get_customer_ledger(
        self,
        customer_id: int,
        entry_type: Optional[LedgerEntryType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[LedgerEntry]:
        return self.ledger_repo.list_by_customer(customer_id, entry_type=entry_type, skip=skip, limit=limit)

    def get_invoice_ledger(self, invoice_id: int) -> List[LedgerEntry]:
        return self.ledger_repo.list_by_invoice(invoice_id)
