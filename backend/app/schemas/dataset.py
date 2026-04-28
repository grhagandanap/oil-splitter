"""Pydantic schemas for Dataset ingestion and listing."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class DatasetKind(str, Enum):
    marker = "marker"
    sand = "sand"
    completion = "completion"
    production = "production"
    lumping = "lumping"
    well = "well"


class DatasetPasteRequest(BaseModel):
    kind: DatasetKind
    data: list[dict[str, Any]]


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    kind: str
    source: str
    filename: str | None
    row_count: int
    is_valid: bool
    validation_errors: list[dict[str, Any]] | None
    created_at: datetime


class DatasetDetail(DatasetRead):
    raw_data: list[dict[str, Any]] | None


class WorkbookSheetsRead(BaseModel):
    sheets: list[str]
