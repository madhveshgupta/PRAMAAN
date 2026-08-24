"""Extracted fields and the rejection log.

``extraction_rejections`` is not an error log. It is the record proving the system refused
to store what it could not verify, and it is surfaced in Ministry settings as a reliability
feature: "the AI tried to state a figure it could not evidence, and was blocked, 47 times
this month."
"""
import uuid
from datetime import datetime

from sqlalchemy import Float, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db import Base
from api.app.models.base import TimestampMixin, fk_uuid, pg_enum, uuid_pk

# 'not_found' (the document genuinely lacks it) and 'not_extracted' (we failed to get it)
# are scored very differently by F3. Conflating them would penalise a DPR for our own
# parsing shortfall.
FIELD_STATUS = pg_enum("found", "not_found", "not_extracted", "needs_human_verification",
                       name="field_status")
EXTRACT_METHOD = pg_enum("regex", "llm_verified", "ocr_regex", "table_cell", "rule_match",
                         name="extract_method")


class DprExtraction(Base, TimestampMixin):
    __tablename__ = "dpr_extractions"

    id: Mapped[uuid.UUID] = uuid_pk()
    dpr_id = fk_uuid("dprs.id")
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(120))


class ExtractedField(Base, TimestampMixin):
    __tablename__ = "extracted_fields"
    __table_args__ = (Index("ix_fields_dpr_key", "dpr_id", "field_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    dpr_id = fk_uuid("dprs.id")
    field_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_numeric: Mapped[float | None] = mapped_column(Numeric(24, 4))
    unit: Mapped[str | None] = mapped_column(String(40))
    # Never empty for status='found'. Invariant #1.
    evidence: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    method: Mapped[str | None] = mapped_column(EXTRACT_METHOD)
    status: Mapped[str] = mapped_column(FIELD_STATUS, default="found", nullable=False)


class ExtractionRejection(Base, TimestampMixin):
    __tablename__ = "extraction_rejections"

    id: Mapped[uuid.UUID] = uuid_pk()
    dpr_id = fk_uuid("dprs.id")
    field_key: Mapped[str] = mapped_column(String(120), nullable=False)
    claimed_value: Mapped[str | None] = mapped_column(Text)
    claimed_span: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(60), nullable=False)
    best_fuzzy_score: Mapped[float | None] = mapped_column(Float)
