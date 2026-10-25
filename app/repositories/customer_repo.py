from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def get_by_email(self, email: str) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.email == email.strip().lower()).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        return self.db.query(Customer).offset(skip).limit(limit).all()

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        self.db.refresh(customer)
        return customer
