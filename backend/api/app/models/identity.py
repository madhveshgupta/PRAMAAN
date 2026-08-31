"""Users and organisations.

Two roles only: applicant and ministry. Appraisal and sanction are two distinct acts
recorded as two distinct audit events, but both are open to any ministry account — there
is no per-user sanction flag. See docs/04_USER_ROLES_AND_JOURNEYS.md.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db import Base
from api.app.models.base import TZDateTime, TimestampMixin, pg_enum, uuid_pk

USER_ROLE = pg_enum("applicant", "ministry", name="user_role")
ORG_TYPE = pg_enum("ministry", "state_dept", "implementing_agency", "consultant",
                   name="org_type")


class Organisation(Base, TimestampMixin):
    __tablename__ = "organisations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(ORG_TYPE, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organisations.id"), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100))


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(USER_ROLE, nullable=False)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organisations.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class Sector(Base, TimestampMixin):
    __tablename__ = "sectors"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    hml_category: Mapped[str | None] = mapped_column(String(120))
