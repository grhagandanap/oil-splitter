"""Pydantic schemas for SplitRun creation and retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict  # pyright: ignore[reportMissingImports]


class SplitRunRead(BaseModel):
    """Lightweight summary used in list views and create-response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str
    error: str | None
    dataset_ids: dict[str, Any] | None
    warnings: list[str] | None
    created_at: datetime
    completed_at: datetime | None


class SplitRunDetail(SplitRunRead):
    """Full payload including the detail/summary tables."""

    detail: list[dict[str, Any]] | None
    summary: list[dict[str, Any]] | None
