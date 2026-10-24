from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.db import Base
from app.core.enums import PaymentStatus


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    status = Column(Enum(PaymentStatus, native_enum=False), nullable=False)
    provider_reference = Column(String(255), nullable=False, index=True)
    failure_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    invoice = relationship("Invoice", back_populates="payment_attempts")
