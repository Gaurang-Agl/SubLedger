# SubLedger — SaaS Subscription & Billing System

A production-ready, concurrency-safe SaaS subscription, billing, and ledger backend designed with Low-Level Design (LLD) principles, strict 5-layer separation, and **100% automated test coverage**.

---

## 📖 What is SubLedger?

In real-world SaaS applications, billing is high-stakes. Financial bugs cause customer mistrust, audit fines, or direct revenue loss. SubLedger acts as the internal **financial system of record**, solving four critical billing challenges:
1. **Price Creep**: If a subscription plan price is updated next month, previously generated unpaid invoices must not retroactively jump in price. SubLedger snapshots plan prices into invoices at creation time.
2. **Double-Spend & Overpayment**: Prevents payments that exceed the unpaid invoice balance, even when two concurrent payment requests arrive simultaneously, using database row-level locking (`SELECT ... FOR UPDATE`).
3. **Ghost Subscriptions**: Prevents duplicate active subscriptions to the same plan via database-level partial unique indexes.
4. **Audit Immutability**: All financial events (invoices, successes, failures) are logged to an append-only, tamper-proof ledger with zero edit/delete access.

---

## 🏛️ The 5-Layer Clean Architecture

SubLedger enforces strict layer boundaries ensuring business rules remain completely decoupled from web frameworks and database engines:

```text
  [ Client / Browser / Postman / Swagger UI ]
                      │
                      ▼
            [ 1. Routes Layer ]             app/routes/
      Thin HTTP controllers; validate input schemas,
      delegate to services, return HTTP status codes.
                      │
                      ▼
            [ 2. Service Layer ]            app/services/
      THE BUSINESS BRAIN: Orchestrates business rules,
      calculates billing periods, transitions statuses,
      and raises pure Python domain exceptions.
                      │
                      ▼
          [ 3. Repository Layer ]           app/repositories/
      DATA ACCESS: Encapsulates pure SQLAlchemy database
      queries. Contains ZERO business rules.
                      │
                      ▼
        [ 4. Models & Database Layer ]      app/models/ & app/db/
      SQLAlchemy ORM tables, relationships, foreign keys,
      and connection session management.
                      ▲
                      │
             [ 5. Schemas Layer ]           app/schemas/
      Pydantic v2 DTOs: strict Decimal monetary validation,
      serialization, and request/response formatting.
```

---

## 📚 Documentation Index
- **[`README.md`](file:///d:/Projects/SubLedger%20-%20SaaS%20Subscription%20&%20Billing%20System/README.md)**: Setup guide, API catalog, workflow cURL examples, and architectural invariants.
- **[`DESIGN.md`](file:///d:/Projects/SubLedger%20-%20SaaS%20Subscription%20&%20Billing%20System/DESIGN.md)**: Low-Level Design (LLD), Mermaid Entity Relationship Diagram (ERD), Service Responsibility Matrix, Repository Matrix, Business Rule Ownership Table, and Sequence Flows.

---

## 1. Getting Started

### Option A: Local Setup (Windows PowerShell / Linux / macOS)

1. **Clone & enter repository directory**:
   ```powershell
   cd "d:\Projects\SubLedger - SaaS Subscription & Billing System"
   ```

2. **Create & activate a virtual environment**:
   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   The application defaults to SQLite (`sqlite:///./subledger.db`) for immediate out-of-the-box local operation. To configure PostgreSQL or other settings:
   ```powershell
   cp .env.example .env
   ```

5. **Start the API Server**:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```
   - **Interactive API Docs (Swagger UI)**: `http://localhost:8000/docs`
   - **Alternative ReDoc**: `http://localhost:8000/redoc`
   - **Health Check**: `http://localhost:8000/health`

---

### Option B: Docker Compose Setup

Run the multi-container stack (FastAPI backend + PostgreSQL 15):
```bash
docker-compose up --build
```
The application will automatically wait for PostgreSQL health checks to pass before starting the backend service.

---

## 2. Running Automated Tests

SubLedger includes 28 comprehensive tests verifying all domain business rules, concurrency race condition guards, payment idempotency, and CRUD API endpoints with **100% code coverage (864/864 statements)** using an in-memory SQLite fixture:

```powershell
python -m pytest -v --cov=app --cov-report=term-missing
```

---

## 3. Required API Reference (14 Endpoints + Health)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Deep health check (service + database connectivity probe) |
| `POST` | `/plans` | Create a subscription plan |
| `GET` | `/plans` | List subscription plans |
| `GET` | `/plans/{plan_id}` | Fetch plan details |
| `PATCH` | `/plans/{plan_id}` | Update or deactivate a plan |
| `POST` | `/customers` | Create a customer |
| `GET` | `/customers` | List customers |
| `GET` | `/customers/{customer_id}` | Fetch customer profile |
| `POST` | `/subscriptions` | Create and activate a subscription (concurrency-safe) |
| `GET` | `/subscriptions` | List subscriptions (optional `?customer_id=`) |
| `PATCH` | `/subscriptions/{subscription_id}/cancel` | Cancel an active subscription |
| `POST` | `/invoices/generate` | Generate invoice for active subscription |
| `GET` | `/invoices/{invoice_id}` | Fetch invoice details (checks & updates overdue) |
| `POST` | `/invoices/mark-overdue` | Batch job transitioning past-due unpaid invoices to overdue |
| `POST` | `/payments/record` | Record payment attempt (row-locked & idempotent) |
| `GET` | `/customers/{customer_id}/ledger` | Fetch customer ledger history (supports `?entry_type=`) |

---

## 4. Example Workflows & cURL Commands

### 1. Create a Plan
```bash
curl -X POST "http://localhost:8000/plans" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Developer Pro",
    "description": "Full API access and analytics",
    "billing_cycle": "monthly",
    "price": "49.99",
    "currency": "USD"
  }'
```

### 2. Create a Customer
```bash
curl -X POST "http://localhost:8000/customers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "email": "jane@example.com",
    "company_name": "Acme Labs"
  }'
```

### 3. Subscribe Customer to Plan
```bash
curl -X POST "http://localhost:8000/subscriptions" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "plan_id": 1
  }'
```

### 4. Generate Invoice
```bash
curl -X POST "http://localhost:8000/invoices/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_id": 1
  }'
```

### 5. Record a Payment Attempt
```bash
curl -X POST "http://localhost:8000/payments/record" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": 1,
    "amount": "49.99",
    "currency": "USD",
    "status": "success",
    "provider_reference": "ch_stripe_sample_98765"
  }'
```

### 6. View Customer Ledger Audit Trail
```bash
curl -X GET "http://localhost:8000/customers/1/ledger"
```

---

## 5. Architectural Invariants & Business Rules

1. **Price Integrity**: All monetary values use `Numeric(10, 2)` in database tables and `Decimal` in Pydantic schemas to prevent floating-point rounding errors.
2. **Append-Only Ledger**: The `LedgerRepository` intentionally omits `update()` and `delete()` methods. Calling them raises `NotImplementedError`, ensuring ledger entries remain strictly immutable.
3. **Price Snapshotting**: Invoices capture the plan price at the moment of invoice generation. If an administrator later updates the plan price, previously generated invoices remain unchanged.
4. **Service Responsibility Split**: `PaymentService` records payment attempts and triggers `InvoiceService.apply_payment()` to adjust balances and transition statuses (`partially_paid` vs `paid`).
5. **Decoupled Domain Exceptions**: The service layer raises pure domain exceptions (`NotFoundException`, `BusinessRuleException`, `ConflictException`), which are mapped into HTTP status codes (`404`, `400`, `409`) via FastAPI exception handlers.
6. **Concurrency Protection**: Invoices are fetched with `with_for_update()` row-level locking during payment processing to serialize concurrent payments and prevent race condition double-payments.
7. **Database-Level Partial Unique Index**: Subscriptions enforce a partial unique index (`uq_active_customer_plan`) on `(customer_id, plan_id)` where `status IN ('ACTIVE', 'active')`, completely eliminating duplicate active subscriptions even under heavy concurrent load.
8. **Payment Idempotency**: Replay of duplicate successful `provider_reference` transactions is rejected with `409 Conflict`.
9. **Currency Integrity**: Payments must match the currency of the invoice being paid; mismatched currencies are rejected with `400 Bad Request`.
10. **Lifecycle Transitions**: Invoices past `due_date` automatically transition to `overdue` upon fetch or via the `POST /invoices/mark-overdue` batch worker endpoint.

---

## 6. Assumptions & Limitations

- **"Custom" Billing Cycle**: Plans configured with `billing_cycle: "custom"` default to a 30-day duration unless explicit `period_start` and `period_end` dates are provided when calling `/invoices/generate`.
- **Payment Gateway Webhooks**: Real payment gateway integrations (Stripe/Razorpay SDKs) are out of scope. Payment attempts are recorded via the `/payments/record` API.
- **Provider Reference Idempotency**: `provider_reference` uniquely identifies external gateway transactions and is protected against replay attacks.
- **Out of Scope**: Complex proration, tiered taxation engines, and multi-tenant RBAC are excluded per the project specification.
