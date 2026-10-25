from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.payment_attempt import PaymentAttempt


class PaymentAttemptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, payment_id: int) -> Optional[PaymentAttempt]:
        return self.db.query(PaymentAttempt).filter(PaymentAttempt.id == payment_id).first()

    def get_by_provider_reference(self, provider_reference: str) -> Optional[PaymentAttempt]:
        return self.db.query(PaymentAttempt).filter(PaymentAttempt.provider_reference == provider_reference).first()

    def list_by_invoice(self, invoice_id: int) -> List[PaymentAttempt]:
        return self.db.query(PaymentAttempt).filter(PaymentAttempt.invoice_id == invoice_id).all()

    def create(self, payment_attempt: PaymentAttempt) -> PaymentAttempt:
        self.db.add(payment_attempt)
        self.db.flush()
        self.db.refresh(payment_attempt)
        return payment_attempt
