from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import User
from src.infrastructure.security.jwt import create_access_token
from src.infrastructure.security.password import get_password_hash, verify_password
from src.modules.authentication.schemas import LoginRequest, TokenResponse, UserCreate, UserRead
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


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("administrator")),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("administrator")),
) -> User:
    existing_user = db.scalar(select(User).where(User.username == payload.username))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
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
