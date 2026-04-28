"""Aggregated v1 API router."""

from fastapi import APIRouter

from app.api.v1 import auth, datasets, projects, split_runs

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(datasets.router)
api_router.include_router(split_runs.router)
