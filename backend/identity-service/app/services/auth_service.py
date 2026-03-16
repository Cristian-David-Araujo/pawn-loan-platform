from typing import Optional
from uuid import UUID

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenData


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def authenticate(self, username: str, password: str) -> Optional[TokenData]:
        user = self.repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        access_token = create_access_token({"sub": str(user.id), "username": user.username})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return TokenData(access_token=access_token, refresh_token=refresh_token)

    def refresh(self, refresh_token: str) -> Optional[TokenData]:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                return None
            user_id = UUID(payload["sub"])
            user = self.repo.get_by_id(user_id)
            if not user or not user.is_active:
                return None
            access_token = create_access_token({"sub": str(user.id), "username": user.username})
            new_refresh = create_refresh_token({"sub": str(user.id)})
            return TokenData(access_token=access_token, refresh_token=new_refresh)
        except (JWTError, ValueError, KeyError):
            return None

    def get_current_user(self, token: str) -> Optional[User]:
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                return None
            user_id = UUID(payload["sub"])
            return self.repo.get_by_id(user_id)
        except (JWTError, ValueError, KeyError):
            return None
