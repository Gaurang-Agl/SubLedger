from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.repositories.subscription_repo import SubscriptionRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.plan_repo import PlanRepository
from app.schemas.subscription import SubscriptionCreate
from app.core.enums import SubscriptionStatus, PlanStatus, BillingCycle
from app.core.exceptions import NotFoundException, BusinessRuleException, ConflictException


class SubscriptionService:
    def __init__(
        self,
        db: Session,
        subscription_repo: Optional[SubscriptionRepository] = None,
        customer_repo: Optional[CustomerRepository] = None,
        plan_repo: Optional[PlanRepository] = None
    ):
        self.db = db
        self.subscription_repo = subscription_repo or SubscriptionRepository(db)
        self.customer_repo = customer_repo or CustomerRepository(db)
        self.plan_repo = plan_repo or PlanRepository(db)

    def create_subscription(self, data: SubscriptionCreate) -> Subscription:
        customer = self.customer_repo.get_by_id(data.customer_id)
        if not customer:
            raise NotFoundException(f"Customer with id {data.customer_id} not found")

        plan = self.plan_repo.get_by_id(data.plan_id)
        if not plan:
            raise NotFoundException(f"Plan with id {data.plan_id} not found")

        # Business Rule: A subscription cannot be created for an inactive plan
        if plan.status != PlanStatus.ACTIVE:
            raise BusinessRuleException("A subscription cannot be created for an inactive plan")

        # Business Rule: A customer cannot have two active subscriptions to the same plan
        existing_active = self.subscription_repo.get_active_by_customer_and_plan(data.customer_id, data.plan_id)
        if existing_active:
            raise ConflictException(f"Customer {data.customer_id} already has an active subscription to plan {data.plan_id}")

        start_time = data.start_date or datetime.now(timezone.utc)
        
        # Calculate period end based on billing cycle
        if plan.billing_cycle == BillingCycle.MONTHLY:
            end_time = start_time + timedelta(days=30)
        elif plan.billing_cycle == BillingCycle.QUARTERLY:
            end_time = start_time + timedelta(days=90)
        elif plan.billing_cycle == BillingCycle.YEARLY:
            end_time = start_time + timedelta(days=365)
        else:
            # Custom cycle defaults to 30 days unless specified
            end_time = start_time + timedelta(days=30)

        subscription = Subscription(
            customer_id=data.customer_id,
            plan_id=data.plan_id,
            status=SubscriptionStatus.ACTIVE,
            start_date=start_time,
            current_period_start=start_time,
            current_period_end=end_time
        )
        try:
            created = self.subscription_repo.create(subscription)
            self.db.commit()
            return created
        except IntegrityError:
            self.db.rollback()
            raise ConflictException(f"Customer {data.customer_id} already has an active subscription to plan {data.plan_id}")

    def get_subscription(self, subscription_id: int) -> Subscription:
        sub = self.subscription_repo.get_by_id(subscription_id)
        if not sub:
            raise NotFoundException(f"Subscription with id {subscription_id} not found")
        return sub

    def list_subscriptions(self, customer_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Subscription]:
        return self.subscription_repo.list(customer_id=customer_id, skip=skip, limit=limit)

    def cancel_subscription(self, subscription_id: int) -> Subscription:
        sub = self.get_subscription(subscription_id)
        if sub.status == SubscriptionStatus.CANCELLED:
            return sub  # idempotent

        sub.status = SubscriptionStatus.CANCELLED
        sub.cancelled_at = datetime.now(timezone.utc)
        updated = self.subscription_repo.update(sub)
        self.db.commit()
        return updated
