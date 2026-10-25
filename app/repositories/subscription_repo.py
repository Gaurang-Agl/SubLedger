from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.core.enums import SubscriptionStatus


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, subscription_id: int) -> Optional[Subscription]:
        return self.db.query(Subscription).filter(Subscription.id == subscription_id).first()

    def get_active_by_customer_and_plan(self, customer_id: int, plan_id: int) -> Optional[Subscription]:
        return self.db.query(Subscription).filter(
            Subscription.customer_id == customer_id,
            Subscription.plan_id == plan_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()

    def list(self, customer_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Subscription]:
        query = self.db.query(Subscription)
        if customer_id:
            query = query.filter(Subscription.customer_id == customer_id)
        return query.offset(skip).limit(limit).all()

    def create(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        self.db.refresh(subscription)
        return subscription

    def update(self, subscription: Subscription) -> Subscription:
        self.db.flush()
        self.db.refresh(subscription)
        return subscription
