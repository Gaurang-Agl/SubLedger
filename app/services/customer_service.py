from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.repositories.customer_repo import CustomerRepository
from app.schemas.customer import CustomerCreate
from app.core.exceptions import NotFoundException, ConflictException


class CustomerService:
    def __init__(self, db: Session, customer_repo: Optional[CustomerRepository] = None):
        self.db = db
        self.customer_repo = customer_repo or CustomerRepository(db)

    def create_customer(self, data: CustomerCreate) -> Customer:
        normalized_email = data.email.strip().lower()
        existing = self.customer_repo.get_by_email(normalized_email)
        if existing:
            raise ConflictException(f"Customer with email '{normalized_email}' already exists")

        customer = Customer(
            name=data.name.strip(),
            email=normalized_email,
            company_name=data.company_name.strip() if data.company_name else None,
            status=data.status
        )
        created = self.customer_repo.create(customer)
        self.db.commit()
        return created

    def get_customer(self, customer_id: int) -> Customer:
        customer = self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException(f"Customer with id {customer_id} not found")
        return customer

    def list_customers(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        return self.customer_repo.list(skip=skip, limit=limit)
