from pydantic import BaseModel, ConfigDict, Field
from src.domain.enums.user import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    # Same floor as a password reset: it made no sense to enforce eight characters when a
    # user replaces their own password and accept a single one when an admin sets it.
    password: str = Field(..., min_length=8)
    full_name: str | None = ""
    email: str | None = ""
    phone: str | None = ""
    document_number: str | None = ""
    address: str | None = ""
    role: UserRole = UserRole.loan_officer


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str
    phone: str
    document_number: str
    address: str
    role: UserRole
    is_active: bool

class UserUpdate(BaseModel):
    username: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    document_number: str | None = None
    address: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class ForgotPasswordRequest(BaseModel):
    username_or_email: str = Field(..., min_length=1)


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class ResetPasswordResponse(BaseModel):
    message: str

