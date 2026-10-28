from fastapi import APIRouter
from app.routes.plans import router as plans_router
from app.routes.customers import router as customers_router
from app.routes.subscriptions import router as subscriptions_router
from app.routes.invoices import router as invoices_router
from app.routes.payments import router as payments_router
from app.routes.ledger import router as ledger_router

api_router = APIRouter()

api_router.include_router(plans_router)
api_router.include_router(customers_router)
api_router.include_router(subscriptions_router)
api_router.include_router(invoices_router)
api_router.include_router(payments_router)
api_router.include_router(ledger_router)

__all__ = ["api_router"]
