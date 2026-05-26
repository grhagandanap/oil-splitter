import os
import shutil
from pathlib import Path
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import SessionLocal, get_db
from app.dependencies import get_current_user
from app.models import FileType, ProjectStatus

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
    sheet_name: Optional[str] = Query(None),
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
        existing.sheet_name = sheet_name
        db.commit()
        db.refresh(existing)
        return existing

    data_file = models.DataFile(
        project_id=project_id,
        file_type=file_type,
        original_filename=file.filename,
        sheet_name=sheet_name,
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


# ── Execute ────────────────────────────────────────────────────────────────────

def _run_engine_background(
    exec_id: UUID,
    project_id: UUID,
    file_map: dict,
    sheet_map: dict,
    output_path: str,
) -> None:
    from app.services.engine import run_engine

    db = SessionLocal()
    logs: list[str] = []

    try:
        run_engine(
            marker_path=file_map[FileType.marker],
            completion_path=file_map[FileType.completion],
            sand_path=file_map[FileType.well],
            production_path=file_map[FileType.production],
            lumping_path=file_map[FileType.lumping],
            marker_sheet=sheet_map.get(FileType.marker),
            completion_sheet=sheet_map.get(FileType.completion),
            sand_sheet=sheet_map.get(FileType.well),
            production_sheet=sheet_map.get(FileType.production),
            lumping_sheet=sheet_map.get(FileType.lumping),
            output_path=output_path,
            log_fn=lambda msg: logs.append(msg),
        )
        execution = db.query(models.ExecutionHistory).filter_by(id=exec_id).first()
        if execution:
            execution.status = ProjectStatus.completed
            execution.result_file_url = output_path
            execution.logs = "\n".join(logs)
        project = db.query(models.Project).filter_by(id=project_id).first()
        if project:
            project.status = ProjectStatus.completed
        db.commit()
    except Exception as exc:
        execution = db.query(models.ExecutionHistory).filter_by(id=exec_id).first()
        if execution:
            execution.status = ProjectStatus.failed
            execution.logs = f"ERROR: {exc}\n" + "\n".join(logs)
        project = db.query(models.Project).filter_by(id=project_id).first()
        if project:
            project.status = ProjectStatus.failed
        db.commit()
    finally:
        db.close()


@router.post(
    "/{project_id}/execute",
    response_model=schemas.ExecutionHistoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def execute_project(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user, db)

    files = (
        db.query(models.DataFile)
        .filter(models.DataFile.project_id == project_id)
        .all()
    )
    file_map = {f.file_type: f.storage_path for f in files}
    sheet_map = {f.file_type: f.sheet_name for f in files if f.sheet_name}
    required = {FileType.marker, FileType.well, FileType.production, FileType.completion, FileType.lumping}
    missing = required - set(file_map.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing files: {', '.join(sorted(m.value for m in missing))}",
        )

    output_path = str(UPLOAD_DIR / str(project_id) / "result.xlsx")

    execution = models.ExecutionHistory(
        project_id=project_id,
        status=ProjectStatus.processing,
    )
    db.add(execution)
    project.status = ProjectStatus.processing
    db.commit()
    db.refresh(execution)

    background_tasks.add_task(
        _run_engine_background,
        exec_id=execution.id,
        project_id=project_id,
        file_map=file_map,
        sheet_map=sheet_map,
        output_path=output_path,
    )
    return execution


@router.get("/{project_id}/history/{execution_id}/download")
def download_result(
    project_id: UUID,
    execution_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user, db)
    execution = (
        db.query(models.ExecutionHistory)
        .filter_by(id=execution_id, project_id=project_id)
        .first()
    )
    if not execution or not execution.result_file_url:
        raise HTTPException(404, "Result not available yet")
    path = Path(execution.result_file_url)
    if not path.exists():
        raise HTTPException(404, "Result file not found on disk")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"result_{execution_id}.xlsx",
    )
