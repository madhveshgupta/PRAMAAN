"""Password hashing, JWTs, and the role dependencies.

Note what ``RequireRole`` does and does not do. It rejects the *request*. Hiding a control
in the UI is presentation; this is access control. Both exist, and only this one counts.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.app.config import get_settings
from api.app.db import get_db
from api.app.models import Dpr, User

Role = Literal["applicant", "ministry"]
_bearer = HTTPBearer(auto_error=False)


def scope_dprs(q, user: User):
    """Row scoping for DPR queries, applied in SQL rather than in the UI.

    Two rules, and both are access control rather than presentation:
      * an applicant sees only their own organisation's reports;
      * a self-check never leaves the organisation that submitted it. The applicant UI
        calls it a "private pre-submission check - not seen by the ministry" in as many
        words, so the promise is kept here, where calling the API directly cannot get
        around it. It used to be enforced only in the portfolio ranking, which meant the
        report list, its assessment, its risk score and its audit trail were all readable
        by any ministry account.
    """
    if user.role == "applicant":
        return q.where(Dpr.organisation_id == user.organisation_id)
    return q.where(~Dpr.is_self_check)


def visible_dpr_or_404(db: Session, dpr_id: uuid.UUID, user: User) -> Dpr:
    """Row-level twin of ``scope_dprs``, for the routes that address one DPR by id.

    404 rather than 403 throughout: confirming that a hidden report exists is itself the
    leak, so an invisible DPR is indistinguishable from one that was never submitted.
    """
    dpr = db.get(Dpr, dpr_id)
    if dpr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "DPR not found")
    if user.role == "applicant":
        if dpr.organisation_id != user.organisation_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "DPR not found")
    elif dpr.is_self_check:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "DPR not found")
    return dpr


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def _token(sub: str, role: str, kind: str, delta: timedelta) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "role": role, "typ": kind, "iat": now, "exp": now + delta}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_alg)


def make_access_token(user: User) -> str:
    s = get_settings()
    return _token(str(user.id), user.role, "access",
                  timedelta(minutes=s.access_token_minutes))


def make_refresh_token(user: User) -> str:
    s = get_settings()
    return _token(str(user.id), user.role, "refresh",
                  timedelta(days=s.refresh_token_days))


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_alg])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                 db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    claims = decode_token(creds.credentials)
    if claims.get("typ") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not an access token")
    user = db.get(User, uuid.UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


class RequireRole:
    """Dependency: allow only the listed roles.

    Row-level scoping is separate and lives in the query layer — an applicant's
    ``GET /dprs`` is filtered by organisation_id in SQL, not by omitting rows in the UI.
    """

    def __init__(self, *roles: Role) -> None:
        self.roles = set(roles)

    def __call__(self, user: User = Depends(current_user)) -> User:
        if user.role not in self.roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Requires role: {', '.join(sorted(self.roles))}")
        return user

