from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.plan_service import PlanService
from app.services.customer_service import CustomerService
from app.services.subscription_service import SubscriptionService
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService
from app.services.ledger_service import LedgerService


def get_plan_service(db: Session = Depends(get_db)) -> PlanService:
    return PlanService(db)


def get_customer_service(db: Session = Depends(get_db)) -> CustomerService:
    return CustomerService(db)


def get_subscription_service(db: Session = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(db)


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(db)


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    return PaymentService(db)


def get_ledger_service(db: Session = Depends(get_db)) -> LedgerService:
    return LedgerService(db)
