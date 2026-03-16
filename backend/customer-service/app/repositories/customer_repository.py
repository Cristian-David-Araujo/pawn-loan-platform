from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.customer import Customer, CustomerStatus


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def get_by_document(self, document_number: str) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.document_number == document_number).first()

    def get_all(self, skip: int = 0, limit: int = 100, status: Optional[CustomerStatus] = None, search: Optional[str] = None) -> Tuple[List[Customer], int]:
        query = self.db.query(Customer)
        if status:
            query = query.filter(Customer.status == status)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                Customer.first_name.ilike(search_term)
                | Customer.last_name.ilike(search_term)
                | Customer.document_number.ilike(search_term)
                | Customer.email.ilike(search_term)
            )
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def create(self, **kwargs) -> Customer:
        customer = Customer(**kwargs)
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def update(self, customer: Customer, **kwargs) -> Customer:
        for key, value in kwargs.items():
            setattr(customer, key, value)
        self.db.commit()
        self.db.refresh(customer)
        return customer
