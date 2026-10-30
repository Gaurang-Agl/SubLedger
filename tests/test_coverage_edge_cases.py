from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from app.db.session import get_db
from app.core.exceptions import NotFoundException, BusinessRuleException
from app.core.enums import InvoiceStatus, BillingCycle
from app.services.plan_service import PlanService
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.schemas.plan import PlanCreate, PlanUpdate
from app.schemas.payment import PaymentRecordRequest
from app.repositories.payment_repo import PaymentAttemptRepository
from app.repositories.ledger_repo import LedgerRepository


def test_session_get_db_generator():
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    try:
        next(db_gen)
    except StopIteration:
        pass


def test_health_check_database_failure(client):
    from app.main import app
    from app.db.session import get_db

    def mock_db_fail():
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("DB Connection Lost")
        yield mock_session

    app.dependency_overrides[get_db] = mock_db_fail
    res = client.get("/health")
    assert res.status_code == 503
    assert res.json()["status"] == "unhealthy"
    app.dependency_overrides.clear()


def test_plan_service_and_schema_edge_cases(client, db_session):
    service = PlanService(db_session)

    # 1. Plan not found (404)
    with pytest.raises(NotFoundException):
        service.get_plan(99999)

    # 2. PlanCreate price <= 0 domain check
    with pytest.raises(BusinessRuleException):
        service.create_plan(PlanCreate.model_construct(name="Test", billing_cycle=BillingCycle.MONTHLY, price=Decimal("0.00"), currency="USD", status="active"))

    # 3. Create a valid plan
    p = service.create_plan(PlanCreate(name="Original", billing_cycle=BillingCycle.MONTHLY, price=Decimal("10.00"), currency="USD"))

    # 4. PlanUpdate price <= 0 domain check
    with pytest.raises(BusinessRuleException):
        service.update_plan(p.id, PlanUpdate.model_construct(price=Decimal("-5.00")))

    # 5. Schema validation error for negative price on PATCH
    res_neg = client.patch(f"/plans/{p.id}", json={"price": "-10.00"})
    assert res_neg.status_code in (400, 422)

    # 6. Update all fields in plan
    updated = service.update_plan(
        p.id,
        PlanUpdate(
            name="Renamed",
            description="New description",
            billing_cycle=BillingCycle.YEARLY,
            currency="EUR"
        )
    )
    assert updated.name == "Renamed"
    assert updated.currency == "EUR"


def test_subscription_service_edge_cases(client, db_session):
    service = SubscriptionService(db_session)

    p_res = client.post("/plans", json={"name": "P1", "billing_cycle": "monthly", "price": "10.00"})
    pid = p_res.json()["id"]

    from app.schemas.subscription import SubscriptionCreate
    with pytest.raises(NotFoundException) as exc:
        service.create_subscription(SubscriptionCreate(customer_id=99999, plan_id=pid))
    assert "Customer with id 99999 not found" in str(exc.value.message)

    c_res = client.post("/customers", json={"name": "C1", "email": "c1@test.com"})
    cid = c_res.json()["id"]
    with pytest.raises(NotFoundException) as exc:
        service.create_subscription(SubscriptionCreate(customer_id=cid, plan_id=99999))
    assert "Plan with id 99999 not found" in str(exc.value.message)

    p_custom = client.post("/plans", json={"name": "Custom Plan", "billing_cycle": "custom", "price": "10.00"})
    sub_custom = service.create_subscription(SubscriptionCreate(customer_id=cid, plan_id=p_custom.json()["id"]))
    assert sub_custom.status.value == "active"

    with pytest.raises(NotFoundException):
        service.get_subscription(99999)

    service.cancel_subscription(sub_custom.id)
    second_cancel = service.cancel_subscription(sub_custom.id)
    assert second_cancel.status.value == "cancelled"


def test_invoice_service_edge_cases(client, db_session):
    service = InvoiceService(db_session)
    from app.schemas.invoice import InvoiceGenerateRequest

    with pytest.raises(NotFoundException):
        service.generate_invoice(InvoiceGenerateRequest(subscription_id=99999))

    c_res = client.post("/customers", json={"name": "C2", "email": "c2@test.com"})
    p_res = client.post("/plans", json={"name": "P2", "billing_cycle": "monthly", "price": "20.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": c_res.json()["id"], "plan_id": p_res.json()["id"]})
    sub_id = sub_res.json()["id"]
    client.patch(f"/subscriptions/{sub_id}/cancel")

    with pytest.raises(BusinessRuleException) as exc:
        service.generate_invoice(InvoiceGenerateRequest(subscription_id=sub_id))
    assert "non-active subscription" in str(exc.value.message)

    active_sub = service.subscription_repo.get_by_id(sub_id)
    active_sub.status = "active"
    active_sub.plan_id = 99999
    with pytest.raises(NotFoundException):
        service.generate_invoice(InvoiceGenerateRequest(subscription_id=sub_id))

    with pytest.raises(NotFoundException):
        service.get_invoice(99999)

    invoices = service.list_invoices(customer_id=c_res.json()["id"])
    assert isinstance(invoices, list)


def test_payment_service_and_schema_edge_cases(client, db_session):
    service = PaymentService(db_session)

    with pytest.raises(NotFoundException):
        service.record_payment(PaymentRecordRequest(invoice_id=99999, amount=Decimal("10.00"), currency="USD", status="success", provider_reference="r_nf"))

    c_res = client.post("/customers", json={"name": "C3", "email": "c3@test.com"})
    p_res = client.post("/plans", json={"name": "P3", "billing_cycle": "monthly", "price": "30.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": c_res.json()["id"], "plan_id": p_res.json()["id"]})
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_res.json()["id"]})
    inv_id = inv_res.json()["id"]

    inv = service.invoice_repo.get_by_id(inv_id)
    inv.status = InvoiceStatus.VOID
    db_session.commit()

    with pytest.raises(BusinessRuleException) as exc:
        service.record_payment(PaymentRecordRequest(invoice_id=inv_id, amount=Decimal("30.00"), currency="USD", status="success", provider_reference="r_void"))
    assert "voided invoice" in str(exc.value.message)

    res_zero = client.post("/payments/record", json={"invoice_id": inv_id, "amount": "0.00", "currency": "USD", "status": "success", "provider_reference": "r_0"})
    assert res_zero.status_code in (400, 422)

    inv.status = InvoiceStatus.ISSUED
    inv.amount_paid = Decimal("30.00")
    db_session.commit()

    with pytest.raises(BusinessRuleException) as exc:
        service.record_payment(PaymentRecordRequest(invoice_id=inv_id, amount=Decimal("10.00"), currency="USD", status="success", provider_reference="r_paid"))
    assert "already fully paid" in str(exc.value.message)


def test_payment_repo_and_ledger_repo_helpers(db_session):
    pay_repo = PaymentAttemptRepository(db_session)
    assert pay_repo.get_by_id(99999) is None
    assert pay_repo.list_by_invoice(99999) == []

    led_repo = LedgerRepository(db_session)
    assert led_repo.get_by_id(99999) is None
