from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.plan import Plan


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, plan_id: int) -> Optional[Plan]:
        return self.db.query(Plan).filter(Plan.id == plan_id).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[Plan]:
        return self.db.query(Plan).offset(skip).limit(limit).all()

    def create(self, plan: Plan) -> Plan:
        self.db.add(plan)
        self.db.flush()
        self.db.refresh(plan)
        return plan

    def update(self, plan: Plan) -> Plan:
        self.db.flush()
        self.db.refresh(plan)
        return plan
