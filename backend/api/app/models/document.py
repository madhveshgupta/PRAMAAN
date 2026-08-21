"""DPRs, documents, and the parsed substrate.

``text_spans`` is the busiest table in the system — a 400-page DPR produces roughly
80k-150k rows. Everything downstream (extraction, scoring, highlighting) resolves through
it, so two invariants live here:

* ``full_text[char_start:char_end] == text`` must hold for every span. If offsets drift,
  every highlight in the document is silently wrong and it survives casual inspection.
* ``bbox`` is normalised 0-1, top-left origin, already de-rotated at parse time.
"""
import uuid

from sqlalchemy import Boolean, Float, Index, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db import Base
from api.app.models.base import BBox, TimestampMixin, fk_uuid, pg_enum, uuid_pk

DPR_STATUS = pg_enum("draft", "processing", "assessed", "under_review",
                     "approved", "returned", "rejected", name="dpr_status")
DOC_STATUS = pg_enum("queued", "parsing", "ocr", "indexing", "ready", "failed",
                     name="document_status")


class Dpr(Base, TimestampMixin):
    __tablename__ = "dprs"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    project_name: Mapped[str | None] = mapped_column(String(500))
    submitted_by = fk_uuid("users.id", nullable=True)
    organisation_id = fk_uuid("organisations.id", nullable=True)
    sector_id = fk_uuid("sectors.id", nullable=True)
    state: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(DPR_STATUS, default="draft", nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    # Private pre-submission self-check: scored, but not in anyone's queue.
    is_self_check: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    dpr_id = fk_uuid("dprs.id")
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(DOC_STATUS, default="queued", nullable=False)
    stage: Mapped[str | None] = mapped_column(String(60))
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    pages_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_no", name="uq_doc_page"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id = fk_uuid("documents.id")
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)   # 1-indexed
    width_pt: Mapped[float] = mapped_column(Float, nullable=False)
    height_pt: Mapped[float] = mapped_column(Float, nullable=False)
    rotation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    full_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    raster_key: Mapped[str | None] = mapped_column(String(500))


class TextSpan(Base):
    __tablename__ = "text_spans"
    __table_args__ = (Index("ix_spans_doc_page", "document_id", "page_no"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id = fk_uuid("documents.id")
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[list[float]] = mapped_column(BBox, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    font_size: Mapped[float | None] = mapped_column(Float)
    is_bold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id = fk_uuid("documents.id")
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[list[float]] = mapped_column(BBox, nullable=False)
    n_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_cols: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extractor: Mapped[str] = mapped_column(String(40), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)


class TableCell(Base):
    __tablename__ = "table_cells"
    __table_args__ = (Index("ix_cells_table", "table_id", "row_idx", "col_idx"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    table_id = fk_uuid("tables.id")
    document_id = fk_uuid("documents.id")
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    row_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    col_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    bbox: Mapped[list[float]] = mapped_column(BBox, nullable=False)
