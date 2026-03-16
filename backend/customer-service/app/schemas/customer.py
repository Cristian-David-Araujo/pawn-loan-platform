from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.customer import CustomerStatus, DocumentType


class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    document_type: DocumentType
    document_number: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[CustomerStatus] = None


class CustomerRead(CustomerBase):
    id: UUID
    status: CustomerStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    items: list[CustomerRead]
    total: int
    skip: int
    limit: int
