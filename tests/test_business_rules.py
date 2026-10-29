import pytest
from decimal import Decimal
from app.repositories.ledger_repo import LedgerRepository


# Rule 1: Plan price must be greater than 0
def test_plan_price_must_be_greater_than_zero(client):
    # Attempt with 0 price
    res_zero = client.post("/plans", json={
        "name": "Free Tier Plan",
        "billing_cycle": "monthly",
        "price": "0.00",
        "currency": "USD",
        "status": "active"
    })
    assert res_zero.status_code in (400, 422)

    # Attempt with negative price
    res_neg = client.post("/plans", json={
        "name": "Negative Price Plan",
        "billing_cycle": "monthly",
        "price": "-29.99",
        "currency": "USD",
        "status": "active"
    })
    assert res_neg.status_code in (400, 422)

    # Valid positive price succeeds
    res_ok = client.post("/plans", json={
        "name": "Standard Plan",
        "billing_cycle": "monthly",
        "price": "49.99",
        "currency": "USD",
        "status": "active"
    })
    assert res_ok.status_code == 201
    assert Decimal(str(res_ok.json()["price"])) == Decimal("49.99")


# Rule 2: Customer email must be unique
def test_customer_email_must_be_unique(client):
    email = "ceo@startup.io"
    # First customer creation succeeds
    res1 = client.post("/customers", json={
        "name": "Jane Doe",
        "email": email,
        "company_name": "Startup Inc."
    })
    assert res1.status_code == 201

    # Second customer with identical email is rejected with 409 Conflict
    res2 = client.post("/customers", json={
        "name": "Another User",
        "email": email,
        "company_name": "Different Corp"
    })
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


# Rule 3: A subscription cannot be created for an inactive plan
def test_cannot_subscribe_to_inactive_plan(client):
    # Create customer
    c_res = client.post("/customers", json={"name": "Alice", "email": "alice@test.com"})
    customer_id = c_res.json()["id"]

    # Create inactive plan
    p_res = client.post("/plans", json={
        "name": "Legacy Plan",
        "billing_cycle": "monthly",
        "price": "19.99",
        "status": "inactive"
    })
    plan_id = p_res.json()["id"]

    # Subscribe to inactive plan should fail with 400 Bad Request
    sub_res = client.post("/subscriptions", json={
        "customer_id": customer_id,
        "plan_id": plan_id
    })
    assert sub_res.status_code == 400
    assert "inactive plan" in sub_res.json()["detail"].lower()


# Rule 4: A customer cannot have two active subscriptions to the same plan
def test_cannot_have_duplicate_active_subscription_to_same_plan(client):
    c_res = client.post("/customers", json={"name": "Bob", "email": "bob@test.com"})
    customer_id = c_res.json()["id"]

    p_res = client.post("/plans", json={
        "name": "Pro Tier",
        "billing_cycle": "monthly",
        "price": "99.00",
        "status": "active"
    })
    plan_id = p_res.json()["id"]

    # First subscription succeeds
    sub1 = client.post("/subscriptions", json={"customer_id": customer_id, "plan_id": plan_id})
    assert sub1.status_code == 201
    assert sub1.json()["status"] == "active"

    # Second active subscription to the same plan is rejected with 409 Conflict
    sub2 = client.post("/subscriptions", json={"customer_id": customer_id, "plan_id": plan_id})
    assert sub2.status_code == 409
    assert "already has an active subscription" in sub2.json()["detail"]

    # If first is cancelled, customer CAN subscribe again
    client.patch(f"/subscriptions/{sub1.json()['id']}/cancel")
    sub3 = client.post("/subscriptions", json={"customer_id": customer_id, "plan_id": plan_id})
    assert sub3.status_code == 201


# Rule 5: Invoice amount_due comes from plan price at generation time (snapshot)
def test_invoice_amount_due_snapshots_plan_price(client):
    c_res = client.post("/customers", json={"name": "Charlie", "email": "charlie@test.com"})
    customer_id = c_res.json()["id"]

    p_res = client.post("/plans", json={
        "name": "Growth Tier",
        "billing_cycle": "monthly",
        "price": "100.00",
        "status": "active"
    })
    plan_id = p_res.json()["id"]

    sub_res = client.post("/subscriptions", json={"customer_id": customer_id, "plan_id": plan_id})
    sub_id = sub_res.json()["id"]

    # Generate invoice when plan price is 100.00
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_id})
    assert inv_res.status_code == 201
    invoice_id = inv_res.json()["id"]
    assert Decimal(str(inv_res.json()["amount_due"])) == Decimal("100.00")

    # Update plan price to 200.00
    client.patch(f"/plans/{plan_id}", json={"price": "200.00"})

    # Check that already generated invoice amount_due is STILL 100.00 (snapshot preserved)
    fetch_inv = client.get(f"/invoices/{invoice_id}")
    assert fetch_inv.status_code == 200
    assert Decimal(str(fetch_inv.json()["amount_due"])) == Decimal("100.00")


# Rule 6: Successful payment cannot exceed remaining unpaid amount on invoice
def test_payment_cannot_exceed_remaining_unpaid_amount(client):
    c_res = client.post("/customers", json={"name": "Diana", "email": "diana@test.com"})
    customer_id = c_res.json()["id"]

    p_res = client.post("/plans", json={
        "name": "Starter",
        "billing_cycle": "monthly",
        "price": "50.00",
        "status": "active"
    })
    plan_id = p_res.json()["id"]

    sub_res = client.post("/subscriptions", json={"customer_id": customer_id, "plan_id": plan_id})
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_res.json()["id"]})
    invoice_id = inv_res.json()["id"]

    # Attempting to pay 60.00 on a 50.00 invoice must be rejected
    pay_res = client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "60.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "pay_over_123"
    })
    assert pay_res.status_code == 400
    assert "exceeds remaining unpaid" in pay_res.json()["detail"]


# Rule 7: Fully paid invoice moves to paid status; partial payment moves to partially_paid status
def test_payment_partial_and_full_status_transitions(client):
    c_res = client.post("/customers", json={"name": "Evan", "email": "evan@test.com"})
    p_res = client.post("/plans", json={"name": "Team", "billing_cycle": "monthly", "price": "100.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": c_res.json()["id"], "plan_id": p_res.json()["id"]})
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_res.json()["id"]})
    invoice_id = inv_res.json()["id"]

    # Partial payment of 40.00
    pay1 = client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "40.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "tx_part_1"
    })
    assert pay1.status_code == 201
    assert pay1.json()["invoice"]["status"] == "partially_paid"
    assert Decimal(str(pay1.json()["invoice"]["amount_paid"])) == Decimal("40.00")

    # Remaining payment of 60.00
    pay2 = client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "60.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "tx_full_2"
    })
    assert pay2.status_code == 201
    assert pay2.json()["invoice"]["status"] == "paid"
    assert Decimal(str(pay2.json()["invoice"]["amount_paid"])) == Decimal("100.00")


# Rule 8: Failed payment does not increase amount_paid
def test_failed_payment_does_not_increase_amount_paid(client):
    c_res = client.post("/customers", json={"name": "Fiona", "email": "fiona@test.com"})
    p_res = client.post("/plans", json={"name": "Basic", "billing_cycle": "monthly", "price": "75.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": c_res.json()["id"], "plan_id": p_res.json()["id"]})
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_res.json()["id"]})
    invoice_id = inv_res.json()["id"]

    # Record failed payment
    fail_res = client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "75.00",
        "currency": "USD",
        "status": "failed",
        "provider_reference": "tx_fail_999",
        "failure_reason": "Card expired"
    })
    assert fail_res.status_code == 201
    assert fail_res.json()["payment_attempt"]["status"] == "failed"
    assert fail_res.json()["payment_attempt"]["failure_reason"] == "Card expired"
    assert Decimal(str(fail_res.json()["invoice"]["amount_paid"])) == Decimal("0.00")
    assert fail_res.json()["invoice"]["status"] == "issued"


# Rule 9: Ledger entries are append-only and traceable through reference_id
def test_ledger_entries_are_append_only_and_traceable(client, db_session):
    c_res = client.post("/customers", json={"name": "George", "email": "george@test.com"})
    customer_id = c_res.json()["id"]
    p_res = client.post("/plans", json={"name": "Premium", "billing_cycle": "monthly", "price": "120.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": customer_id, "plan_id": p_res.json()["id"]})

    # 1. Generate invoice -> triggers invoice_created ledger entry
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_res.json()["id"]})
    invoice_id = inv_res.json()["id"]

    # 2. Failed payment -> triggers payment_failure ledger entry
    client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "120.00",
        "currency": "USD",
        "status": "failed",
        "provider_reference": "ref_fail_001",
        "failure_reason": "Insufficient funds"
    })

    # 3. Successful payment -> triggers payment_success ledger entry
    client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "120.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "ref_succ_002"
    })

    # Fetch customer ledger history
    ledger_res = client.get(f"/customers/{customer_id}/ledger")
    assert ledger_res.status_code == 200
    entries = ledger_res.json()
    assert len(entries) == 3

    types = [e["entry_type"] for e in entries]
    assert types == ["invoice_created", "payment_failure", "payment_success"]

    # Verify reference_id traceability
    assert entries[0]["reference_id"] == str(invoice_id)
    assert entries[1]["reference_id"] == "ref_fail_001"
    assert entries[2]["reference_id"] == "ref_succ_002"

    # Enforce structural immutability in LedgerRepository
    ledger_repo = LedgerRepository(db_session)
    with pytest.raises(NotImplementedError):
        ledger_repo.update()
    with pytest.raises(NotImplementedError):
        ledger_repo.delete()


# Rule 10: Payment currency must strictly match invoice currency
def test_payment_currency_must_match_invoice_currency(client):
    c_res = client.post("/customers", json={"name": "Karen", "email": "karen@test.com"})
    p_res = client.post("/plans", json={"name": "US Plan", "billing_cycle": "monthly", "price": "100.00", "currency": "USD"})
    sub_res = client.post("/subscriptions", json={"customer_id": c_res.json()["id"], "plan_id": p_res.json()["id"]})
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_res.json()["id"]})
    invoice_id = inv_res.json()["id"]

    # Attempt to pay in EUR on a USD invoice
    pay_res = client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "100.00",
        "currency": "EUR",
        "status": "success",
        "provider_reference": "ref_curr_mismatch"
    })
    assert pay_res.status_code == 400
    assert "does not match invoice currency" in pay_res.json()["detail"].lower()


# Rule 11: Idempotency - Duplicate successful provider_reference is rejected
def test_payment_idempotency_duplicate_provider_reference(client):
    c_res = client.post("/customers", json={"name": "Leo", "email": "leo@test.com"})
    p_res = client.post("/plans", json={"name": "Plus", "billing_cycle": "monthly", "price": "200.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": c_res.json()["id"], "plan_id": p_res.json()["id"]})
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_res.json()["id"]})
    invoice_id = inv_res.json()["id"]

    # First payment attempt succeeds
    pay1 = client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "100.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "stripe_ch_unique_123"
    })
    assert pay1.status_code == 201

    # Second payment attempt with same provider_reference is rejected with 409 Conflict
    pay2 = client.post("/payments/record", json={
        "invoice_id": invoice_id,
        "amount": "100.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "stripe_ch_unique_123"
    })
    assert pay2.status_code == 409
    assert "already been processed" in pay2.json()["detail"].lower()


# Rule 12: Overdue invoice progression when due_date elapses
def test_invoice_overdue_transition(client):
    from datetime import datetime, timezone, timedelta
    c_res = client.post("/customers", json={"name": "Maya", "email": "maya@test.com"})
    p_res = client.post("/plans", json={"name": "Standard", "billing_cycle": "monthly", "price": "80.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": c_res.json()["id"], "plan_id": p_res.json()["id"]})

    # Generate invoice with a past due date (1 day ago)
    past_due = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    inv_res = client.post("/invoices/generate", json={
        "subscription_id": sub_res.json()["id"],
        "due_date": past_due
    })
    invoice_id = inv_res.json()["id"]

    # Fetching the invoice checks and transitions it to 'overdue'
    get_res = client.get(f"/invoices/{invoice_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "overdue"


# Rule 13: Partial unique index blocks duplicate active subscriptions at DB level
def test_partial_unique_index_blocks_duplicate_active_subscription_at_db_level(client, db_session):
    from app.models.subscription import Subscription
    from app.core.enums import SubscriptionStatus
    from datetime import datetime, timezone, timedelta
    from sqlalchemy.exc import IntegrityError

    c_res = client.post("/customers", json={"name": "Race Tester", "email": "racetest@test.com"})
    p_res = client.post("/plans", json={"name": "Race Plan", "billing_cycle": "monthly", "price": "10.00"})
    cid, pid = c_res.json()["id"], p_res.json()["id"]

    now = datetime.now(timezone.utc)
    s1 = Subscription(
        customer_id=cid,
        plan_id=pid,
        status=SubscriptionStatus.ACTIVE,
        start_date=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=30)
    )
    db_session.add(s1)
    db_session.commit()

    # Second active subscription bypassing service layer check directly into DB
    s2 = Subscription(
        customer_id=cid,
        plan_id=pid,
        status=SubscriptionStatus.ACTIVE,
        start_date=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=30)
    )
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_subscription_service_handles_race_condition_integrity_error(client, db_session):
    from unittest.mock import MagicMock
    from app.services.subscription_service import SubscriptionService
    from app.schemas.subscription import SubscriptionCreate
    from app.core.exceptions import ConflictException

    c_res = client.post("/customers", json={"name": "Race Service Tester", "email": "racesvc@test.com"})
    p_res = client.post("/plans", json={"name": "Race Svc Plan", "billing_cycle": "monthly", "price": "15.00"})
    cid, pid = c_res.json()["id"], p_res.json()["id"]

    sub_service = SubscriptionService(db_session)
    # First subscription succeeds
    sub_service.create_subscription(SubscriptionCreate(customer_id=cid, plan_id=pid))

    # Mock the check to simulate race condition where check passes but DB partial unique index catches it
    sub_service.subscription_repo.get_active_by_customer_and_plan = MagicMock(return_value=None)
    with pytest.raises(ConflictException) as exc_info:
        sub_service.create_subscription(SubscriptionCreate(customer_id=cid, plan_id=pid))
    assert "already has an active subscription" in str(exc_info.value.message)
