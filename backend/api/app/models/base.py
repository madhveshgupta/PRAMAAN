"""Shared column types and mixins.

Two conventions worth knowing before you read any model:

* **Money is BIGINT paise, never float** (invariant #7). ``Money`` is that type.
* **Coordinates are normalised 0-1** against page width/height (invariant #8).
  ``BBox`` is a 4-element ``[x0, y0, x1, y1]`` array, top-left origin.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import ARRAY, BigInteger, DateTime, Enum, Float, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

Money = BigInteger        # paise
# Always timezone-aware. A naive timestamp column compared against Postgres now()
# silently misbehaves across timezones — it made the stale-lock reclaim never fire.
TZDateTime = DateTime(timezone=True)
BBox = ARRAY(Float, dimensions=1)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def fk_uuid(target: str, nullable: bool = False, index: bool = True):
    from sqlalchemy import ForeignKey
    return mapped_column(PGUUID(as_uuid=True), ForeignKey(target, ondelete="CASCADE"),
                         nullable=nullable, index=index)


def pg_enum(*values: str, name: str) -> Enum:
    """Native Postgres enum. Chosen over a free-text column deliberately: it lets the
    database itself refuse an invalid value. `finding_status` in particular has no
    'fail' member, so invariant #4 is enforced by the schema, not by application code."""
    return Enum(*values, name=name, native_enum=True, validate_strings=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
