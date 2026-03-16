from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.collateral import CollateralItem, CollateralStatus


class CollateralRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, item_id: UUID) -> Optional[CollateralItem]:
        return self.db.query(CollateralItem).filter(CollateralItem.id == item_id).first()

    def get_by_loan_id(self, loan_id: UUID) -> List[CollateralItem]:
        return self.db.query(CollateralItem).filter(CollateralItem.loan_id == loan_id).all()

    def get_all(self, skip: int = 0, limit: int = 100, status: Optional[CollateralStatus] = None) -> Tuple[List[CollateralItem], int]:
        query = self.db.query(CollateralItem)
        if status:
            query = query.filter(CollateralItem.status == status)
        total = query.count()
        items = query.order_by(CollateralItem.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, **kwargs) -> CollateralItem:
        item = CollateralItem(**kwargs)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, item: CollateralItem, **kwargs) -> CollateralItem:
        for key, value in kwargs.items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def release(self, item: CollateralItem, released_by: Optional[UUID] = None) -> CollateralItem:
        return self.update(
            item,
            status=CollateralStatus.RELEASED,
            release_date=datetime.now(timezone.utc),
            released_by=released_by,
        )

    def liquidate(self, item: CollateralItem, sale_amount=None, notes: Optional[str] = None) -> CollateralItem:
        return self.update(
            item,
            status=CollateralStatus.SOLD if sale_amount else CollateralStatus.UNDER_LIQUIDATION,
            sale_amount=sale_amount,
            liquidation_notes=notes,
        )
