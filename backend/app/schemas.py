from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.models import ProjectStatus, FileType

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


# --- Project ---

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    status: ProjectStatus
    created_at: datetime

    class Config:
        from_attributes = True


# --- DataFile ---

class DataFileResponse(BaseModel):
    id: UUID
    project_id: UUID
    file_type: FileType
    original_filename: str
    storage_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ProjectWithFiles(ProjectResponse):
    files: List[DataFileResponse] = []


# --- ExecutionHistory ---

class ExecutionHistoryResponse(BaseModel):
    id: UUID
    project_id: UUID
    result_file_url: Optional[str]
    logs: Optional[str]
    executed_at: datetime

    class Config:
        from_attributes = True
