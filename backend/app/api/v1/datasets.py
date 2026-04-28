"""Dataset ingestion router — paste, upload, list, get, delete."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.db.models.dataset import Dataset
from app.db.models.project import Project
from app.schemas.dataset import (
    DatasetDetail,
    DatasetKind,
    DatasetPasteRequest,
    DatasetRead,
    WorkbookSheetsRead,
)
from app.services.ingestion import ingest, list_xlsx_sheets

router = APIRouter(prefix="/projects/{project_id}/datasets", tags=["datasets"])


async def _get_owned_project(db, project_id: int, owner_id: int) -> Project:
    project = await db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/paste", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def paste_dataset(
    project_id: int,
    body: DatasetPasteRequest,
    db: DbSession,
    user: CurrentUser,
):
    await _get_owned_project(db, project_id, user.id)

    source, clean, errors, is_valid = ingest(
        kind=body.kind.value,
        pasted_rows=body.data,
    )

    ds = Dataset(
        project_id=project_id,
        kind=body.kind.value,
        source=source,
        filename=None,
        row_count=len(clean),
        raw_data=clean,
        validation_errors=errors,
        is_valid=is_valid,
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return ds


@router.post("/upload", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    project_id: int,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    kind: DatasetKind = Form(...),
    sheet_name: Optional[str] = Form(None),
):
    await _get_owned_project(db, project_id, user.id)

    raw_bytes = await file.read()
    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        source, clean, errors, is_valid = ingest(
            kind=kind.value,
            raw_bytes=raw_bytes,
            filename=file.filename or "unknown.csv",
            sheet_name=sheet_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse file: {exc}",
        ) from exc

    ds = Dataset(
        project_id=project_id,
        kind=kind.value,
        source=source,
        filename=file.filename,
        row_count=len(clean),
        raw_data=clean,
        validation_errors=errors,
        is_valid=is_valid,
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return ds


@router.post("/workbook-sheets", response_model=WorkbookSheetsRead)
async def workbook_sheets(
    project_id: int,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
):
    await _get_owned_project(db, project_id, user.id)

    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"xlsx", "xls"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sheet selection is only available for Excel files.",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        return WorkbookSheetsRead(sheets=list_xlsx_sheets(raw_bytes))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to inspect workbook sheets: {exc}",
        ) from exc


@router.get("", response_model=list[DatasetRead])
async def list_datasets(
    project_id: int,
    db: DbSession,
    user: CurrentUser,
    kind: Optional[DatasetKind] = None,
):
    await _get_owned_project(db, project_id, user.id)

    stmt = select(Dataset).where(Dataset.project_id == project_id)
    if kind is not None:
        stmt = stmt.where(Dataset.kind == kind.value)
    stmt = stmt.order_by(Dataset.id.desc())

    result = await db.scalars(stmt)
    return result.all()


@router.get("/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(
    project_id: int,
    dataset_id: int,
    db: DbSession,
    user: CurrentUser,
):
    await _get_owned_project(db, project_id, user.id)

    ds = await db.scalar(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.project_id == project_id,
        )
    )
    if ds is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return ds


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    project_id: int,
    dataset_id: int,
    db: DbSession,
    user: CurrentUser,
):
    await _get_owned_project(db, project_id, user.id)

    ds = await db.scalar(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.project_id == project_id,
        )
    )
    if ds is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    await db.delete(ds)
    await db.commit()
