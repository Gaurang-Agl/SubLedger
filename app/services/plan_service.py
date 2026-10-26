from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.plan import Plan
from app.repositories.plan_repo import PlanRepository
from app.schemas.plan import PlanCreate, PlanUpdate
from app.core.enums import PlanStatus
from app.core.exceptions import NotFoundException, BusinessRuleException


class PlanService:
    def __init__(self, db: Session, plan_repo: Optional[PlanRepository] = None):
        self.db = db
        self.plan_repo = plan_repo or PlanRepository(db)

    def create_plan(self, data: PlanCreate) -> Plan:
        if data.price <= Decimal("0"):
            raise BusinessRuleException("Plan price must be greater than 0")
        
        plan = Plan(
            name=data.name,
            description=data.description,
            billing_cycle=data.billing_cycle,
            price=data.price,
            currency=data.currency.upper(),
            status=data.status
        )
        created = self.plan_repo.create(plan)
        self.db.commit()
        return created

    def get_plan(self, plan_id: int) -> Plan:
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise NotFoundException(f"Plan with id {plan_id} not found")
        return plan

    def list_plans(self, skip: int = 0, limit: int = 100) -> List[Plan]:
        return self.plan_repo.list(skip=skip, limit=limit)

    def update_plan(self, plan_id: int, data: PlanUpdate) -> Plan:
        plan = self.get_plan(plan_id)

        if data.price is not None:
            if data.price <= Decimal("0"):
                raise BusinessRuleException("Plan price must be greater than 0")
            plan.price = data.price

        if data.name is not None:
            plan.name = data.name
        if data.description is not None:
            plan.description = data.description
        if data.billing_cycle is not None:
            plan.billing_cycle = data.billing_cycle
        if data.currency is not None:
            plan.currency = data.currency.upper()
        if data.status is not None:
            plan.status = data.status

        updated = self.plan_repo.update(plan)
        self.db.commit()
        return updated
