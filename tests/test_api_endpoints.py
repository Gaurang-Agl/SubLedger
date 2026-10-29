def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "service": "SubLedger", "database": "connected"}


def test_plan_crud_endpoints(client):
    # Create plan
    res = client.post("/plans", json={
        "name": "Standard Monthly",
        "description": "Standard features",
        "billing_cycle": "monthly",
        "price": "29.00"
    })
    assert res.status_code == 201
    plan_id = res.json()["id"]

    # List plans
    list_res = client.get("/plans")
    assert list_res.status_code == 200
    assert any(p["id"] == plan_id for p in list_res.json())

    # Get single plan
    get_res = client.get(f"/plans/{plan_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Standard Monthly"

    # Update plan
    patch_res = client.patch(f"/plans/{plan_id}", json={
        "description": "Updated standard features",
        "status": "inactive"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["description"] == "Updated standard features"
    assert patch_res.json()["status"] == "inactive"


def test_customer_crud_endpoints(client):
    # Create customer
    res = client.post("/customers", json={
        "name": "Acme Corp Admin",
        "email": "admin@acme.com",
        "company_name": "Acme Corp"
    })
    assert res.status_code == 201
    cust_id = res.json()["id"]

    # List customers
    list_res = client.get("/customers")
    assert list_res.status_code == 200
    assert any(c["id"] == cust_id for c in list_res.json())

    # Get customer
    get_res = client.get(f"/customers/{cust_id}")
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "admin@acme.com"

    # Get non-existent customer
    nf_res = client.get("/customers/99999")
    assert nf_res.status_code == 404


def test_subscription_lifecycle(client):
    c_res = client.post("/customers", json={"name": "Hannah", "email": "hannah@test.com"})
    cust_id = c_res.json()["id"]
    p_res = client.post("/plans", json={"name": "Annual Pro", "billing_cycle": "yearly", "price": "999.00"})
    plan_id = p_res.json()["id"]

    # Create subscription
    sub_res = client.post("/subscriptions", json={"customer_id": cust_id, "plan_id": plan_id})
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["id"]

    # Get subscription
    get_res = client.get(f"/subscriptions/{sub_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "active"

    # List subscriptions
    list_res = client.get(f"/subscriptions?customer_id={cust_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Cancel subscription
    cancel_res = client.patch(f"/subscriptions/{sub_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"
    assert cancel_res.json()["cancelled_at"] is not None


def test_invoice_and_ledger_queries(client):
    c_res = client.post("/customers", json={"name": "Ian", "email": "ian@test.com"})
    cust_id = c_res.json()["id"]
    p_res = client.post("/plans", json={"name": "Quarterly Plus", "billing_cycle": "quarterly", "price": "150.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": cust_id, "plan_id": p_res.json()["id"]})
    sub_id = sub_res.json()["id"]

    # Generate invoice
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_id})
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # Get invoice
    get_inv = client.get(f"/invoices/{inv_id}")
    assert get_inv.status_code == 200
    assert get_inv.json()["status"] == "issued"

    # List invoices
    list_inv = client.get(f"/invoices?subscription_id={sub_id}")
    assert list_inv.status_code == 200
    assert len(list_inv.json()) == 1

    # Get invoice ledger
    inv_ledger = client.get(f"/invoices/{inv_id}/ledger")
    assert inv_ledger.status_code == 200
    assert len(inv_ledger.json()) == 1
    assert inv_ledger.json()[0]["entry_type"] == "invoice_created"


def test_ledger_filtering_by_entry_type(client):
    c_res = client.post("/customers", json={"name": "Jack", "email": "jack@test.com"})
    cust_id = c_res.json()["id"]
    p_res = client.post("/plans", json={"name": "Basic", "billing_cycle": "monthly", "price": "50.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": cust_id, "plan_id": p_res.json()["id"]})

    # Generate invoice -> invoice_created
    inv_res = client.post("/invoices/generate", json={"subscription_id": sub_res.json()["id"]})
    inv_id = inv_res.json()["id"]

    # Failed payment -> payment_failure
    client.post("/payments/record", json={
        "invoice_id": inv_id,
        "amount": "50.00",
        "currency": "USD",
        "status": "failed",
        "provider_reference": "ref_fail_x1"
    })

    # Successful payment -> payment_success
    client.post("/payments/record", json={
        "invoice_id": inv_id,
        "amount": "50.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "ref_succ_x2"
    })

    # Filter only payment_success
    res_succ = client.get(f"/customers/{cust_id}/ledger?entry_type=payment_success")
    assert res_succ.status_code == 200
    assert len(res_succ.json()) == 1
    assert res_succ.json()[0]["entry_type"] == "payment_success"

    # Filter only payment_failure
    res_fail = client.get(f"/customers/{cust_id}/ledger?entry_type=payment_failure")
    assert res_fail.status_code == 200
    assert len(res_fail.json()) == 1
    assert res_fail.json()[0]["entry_type"] == "payment_failure"


def test_mark_overdue_endpoint(client):
    from datetime import datetime, timezone, timedelta
    c_res = client.post("/customers", json={"name": "Overdue Customer", "email": "overdue@test.com"})
    p_res = client.post("/plans", json={"name": "Overdue Plan", "billing_cycle": "monthly", "price": "10.00"})
    sub_res = client.post("/subscriptions", json={"customer_id": c_res.json()["id"], "plan_id": p_res.json()["id"]})
    
    past_due = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    client.post("/invoices/generate", json={
        "subscription_id": sub_res.json()["id"],
        "due_date": past_due
    })

    res = client.post("/invoices/mark-overdue")
    assert res.status_code == 200
    assert res.json()["marked_overdue_count"] >= 1
