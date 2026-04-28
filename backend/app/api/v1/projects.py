"""Project CRUD router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.db.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: DbSession,
    user: CurrentUser,
):
    project = Project(owner_id=user.id, **body.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: DbSession,
    user: CurrentUser,
):
    result = await db.scalars(
        select(Project).where(Project.owner_id == user.id).order_by(Project.id.desc())
    )
    return result.all()


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int,
    db: DbSession,
    user: CurrentUser,
):
    project = await _get_owned_project(db, project_id, user.id)
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: DbSession,
    user: CurrentUser,
):
    project = await _get_owned_project(db, project_id, user.id)
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: DbSession,
    user: CurrentUser,
):
    project = await _get_owned_project(db, project_id, user.id)
    await db.delete(project)
    await db.commit()


async def _get_owned_project(db, project_id: int, owner_id: int) -> Project:
    project = await db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
