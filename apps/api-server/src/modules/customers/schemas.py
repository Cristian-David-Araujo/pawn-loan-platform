from datetime import datetime

from src.domain.enums.collateral import CustomerStatus
from pydantic import BaseModel, ConfigDict
from src.modules.authentication.schemas import UserSummary


class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    document_type: str
    document_number: str
    phone: str = ""
    email: str = ""
    address: str = ""
    city: str = ""
    status: CustomerStatus = CustomerStatus.active


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    status: CustomerStatus | None = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    created_by: UserSummary | None = None
