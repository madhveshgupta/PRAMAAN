from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db import get_db
from api.app.models import User
from api.app.models.base import utcnow
from api.app.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from api.app.security import (current_user, decode_token, make_access_token,
                              make_refresh_token, verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])


def _pair(user: User) -> TokenPair:
    return TokenPair(access_token=make_access_token(user),
                     refresh_token=make_refresh_token(user),
                     role=user.role, can_sanction=user.can_sanction,
                     full_name=user.full_name)


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    # Same message either way — don't reveal which addresses exist.
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user.last_login_at = utcnow()
    db.commit()
    return _pair(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    import uuid
    claims = decode_token(body.refresh_token)
    if claims.get("typ") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not a refresh token")
    user = db.get(User, uuid.UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return _pair(user)


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"id": str(user.id), "email": user.email, "full_name": user.full_name,
            "role": user.role, "can_sanction": user.can_sanction,
            "organisation_id": str(user.organisation_id) if user.organisation_id else None}
