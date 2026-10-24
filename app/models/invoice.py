from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.db import Base
from app.core.enums import InvoiceStatus


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    amount_due = Column(Numeric(10, 2), nullable=False)
    amount_paid = Column(Numeric(10, 2), default=0.00, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    status = Column(Enum(InvoiceStatus, native_enum=False), default=InvoiceStatus.ISSUED, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subscription = relationship("Subscription", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    payment_attempts = relationship("PaymentAttempt", back_populates="invoice", cascade="all, delete-orphan")
    ledger_entries = relationship("LedgerEntry", back_populates="invoice")
