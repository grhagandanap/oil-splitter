"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI  # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware  # pyright: ignore[reportMissingImports]

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

if settings.BACKEND_CORS_ORIGINS or settings.BACKEND_CORS_ORIGIN_REGEX:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_origin_regex=settings.BACKEND_CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "Oil Splitting API is running"}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
