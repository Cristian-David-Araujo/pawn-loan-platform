import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.models import User
from src.infrastructure.security.jwt import create_access_token
from src.infrastructure.security.password import get_password_hash, verify_password
from src.modules.authentication.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import get_current_user, require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(tags=["authentication"])


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(user.username)
    return TokenResponse(access_token=token)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(current_user: User = Depends(get_current_user)) -> TokenResponse:
    token = create_access_token(current_user.username)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    settings = get_settings()
    identifier = payload.username_or_email.strip()
    user = db.scalar(
        select(User).where(
            (User.username == identifier) | (User.email == identifier)
        )
    )

    token: str | None = None
    if user is not None and user.is_active:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.commit()

        write_audit(
            db,
            action="forgot_password",
            entity_type="User",
            entity_id=str(user.id),
            user=user,
            new_data="password_reset_requested=true",
        )

    # Anti-user enumeration guarantee: identical response message regardless of user existence.
    # In production, never leak the token in API responses.
    expose_token = token if settings.app_env != "production" else None
    return ForgotPasswordResponse(
        message="Si la cuenta existe y está activa, recibirás instrucciones para restablecer tu contraseña.",
        reset_token=expose_token,
    )


@router.post("/auth/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> ResetPasswordResponse:
    user = db.scalar(select(User).where(User.reset_token == payload.token))
    now = datetime.now(timezone.utc)

    if user is None or user.reset_token_expires_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de restablecimiento inválido o expirado")

    expires_at = user.reset_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de restablecimiento inválido o expirado")

    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    write_audit(
        db,
        action="reset_password",
        entity_type="User",
        entity_id=str(user.id),
        user=user,
        new_data="password_reset_completed=true",
    )

    return ResetPasswordResponse(message="Contraseña actualizada exitosamente")


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator)),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> User:
    existing_user = db.scalar(select(User).where(User.username == payload.username))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name or "",
        email=payload.email or "",
        phone=payload.phone or "",
        document_number=payload.document_number or "",
        address=payload.address or "",
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit(
        db,
        action="create_user",
        entity_type="User",
        entity_id=str(user.id),
        user=current_user,
        new_data=f"username={user.username},role={user.role}",
    )

    return user


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> User:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.username is not None:
        # Check uniqueness if username changed
        if payload.username != user.username:
            existing = db.scalar(select(User).where(User.username == payload.username))
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
        user.username = payload.username

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.document_number is not None:
        user.document_number = payload.document_number
    if payload.address is not None:
        user.address = payload.address

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        # Prevent deactivating oneself
        if user.id == current_user.id and payload.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
        user.is_active = payload.is_active
    if payload.password is not None and payload.password.strip():
        user.hashed_password = get_password_hash(payload.password)

    db.commit()
    db.refresh(user)

    write_audit(
        db,
        action="update_user",
        entity_type="User",
        entity_id=str(user.id),
        user=current_user,
        new_data=f"role={user.role},active={user.is_active},password_changed={bool(payload.password)}",
    )

    return user
