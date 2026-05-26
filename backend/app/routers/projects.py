import os
import shutil
from pathlib import Path
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.models import FileType

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(
    project_id: UUID, user: models.User, db: Session
) -> models.Project:
    project = (
        db.query(models.Project)
        .filter(models.Project.id == project_id, models.Project.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── Projects CRUD ──────────────────────────────────────────────────────────────

@router.post("/", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = models.Project(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/", response_model=List[schemas.ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Project)
        .filter(models.Project.user_id == current_user.id)
        .order_by(models.Project.created_at.desc())
        .all()
    )


@router.get("/{project_id}", response_model=schemas.ProjectWithFiles)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_project_or_404(project_id, current_user, db)


@router.patch("/{project_id}", response_model=schemas.ProjectResponse)
def update_project(
    project_id: UUID,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user, db)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user, db)
    project_dir = UPLOAD_DIR / str(project_id)
    if project_dir.exists():
        shutil.rmtree(project_dir)
    db.delete(project)
    db.commit()


# ── File Uploads ───────────────────────────────────────────────────────────────

@router.post("/{project_id}/files/{file_type}", response_model=schemas.DataFileResponse)
async def upload_file(
    project_id: UUID,
    file_type: FileType,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user, db)

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    project_dir = UPLOAD_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    dest = project_dir / f"{file_type.value}{suffix}"

    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    existing = (
        db.query(models.DataFile)
        .filter(
            models.DataFile.project_id == project_id,
            models.DataFile.file_type == file_type,
        )
        .first()
    )
    if existing:
        existing.storage_path = str(dest)
        existing.original_filename = file.filename
        db.commit()
        db.refresh(existing)
        return existing

    data_file = models.DataFile(
        project_id=project_id,
        file_type=file_type,
        original_filename=file.filename,
        storage_path=str(dest),
    )
    db.add(data_file)
    db.commit()
    db.refresh(data_file)
    return data_file


@router.get("/{project_id}/files", response_model=List[schemas.DataFileResponse])
def list_files(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user, db)
    return (
        db.query(models.DataFile)
        .filter(models.DataFile.project_id == project_id)
        .all()
    )


# ── Execution History ──────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/history", response_model=List[schemas.ExecutionHistoryResponse]
)
def get_history(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user, db)
    return (
        db.query(models.ExecutionHistory)
        .filter(models.ExecutionHistory.project_id == project_id)
        .order_by(models.ExecutionHistory.executed_at.desc())
        .all()
    )
