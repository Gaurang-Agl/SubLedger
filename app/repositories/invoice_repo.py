from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.invoice import Invoice


class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, invoice_id: int, for_update: bool = False) -> Optional[Invoice]:
        query = self.db.query(Invoice).filter(Invoice.id == invoice_id)
        if for_update:
            query = query.with_for_update()
        return query.first()

    def list(self, subscription_id: Optional[int] = None, customer_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Invoice]:
        query = self.db.query(Invoice)
        if subscription_id:
            query = query.filter(Invoice.subscription_id == subscription_id)
        if customer_id:
            query = query.filter(Invoice.customer_id == customer_id)
        return query.offset(skip).limit(limit).all()

    def create(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        self.db.flush()
        self.db.refresh(invoice)
        return invoice

    def update(self, invoice: Invoice) -> Invoice:
        self.db.flush()
        self.db.refresh(invoice)
        return invoice
