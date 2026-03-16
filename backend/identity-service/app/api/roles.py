from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import RoleCreate, RoleRead

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("", response_model=List[RoleRead])
def list_roles(db: Session = Depends(get_db), _=Depends(get_current_user)):
    repo = UserRepository(db)
    return repo.get_all_roles()


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    repo = UserRepository(db)
    existing = repo.get_role_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")
    return repo.create_role(name=payload.name, description=payload.description)
