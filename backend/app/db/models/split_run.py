"""SplitRun SQLAlchemy model.

Stores the inputs (dataset snapshot) and outputs (detail / summary frames,
warnings) of a single splitter execution for a project.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class SplitRunStatus:
    """Allowed values for ``SplitRun.status``."""

    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


from app.db.base import Base


class SplitRun(Base):
    __tablename__ = "split_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # Snapshot of which dataset rows fed this run (id per kind).
    dataset_ids: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Markered production after gap-fill: ``WELL``, ``DATE``, fluids, sand
    # columns with ``"p"`` — shown as the “Perforation marker” tab in the UI.
    marker_preview: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    # Per-row allocated volumes for each fluid × sand combination.
    detail: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    # Sand-level totals.
    summary: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
