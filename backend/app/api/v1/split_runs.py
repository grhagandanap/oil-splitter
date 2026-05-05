"""Split-run endpoints — execute the splitter pipeline and fetch results."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.db.models.dataset import Dataset
from app.db.models.project import Project
from app.db.models.split_run import SplitRun, SplitRunStatus
from app.schemas.split_run import SplitRunDetail, SplitRunRead
from app.services.run_executor import REQUIRED_KINDS, RunInputError, execute_run

router = APIRouter(prefix="/projects/{project_id}/split", tags=["split"])


_DETAIL_ROW_LIMIT = 500


async def _get_owned_project(db, project_id: int, owner_id: int) -> Project:
    project = await db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return project


async def _latest_valid_datasets(
    db, project_id: int
) -> tuple[dict[str, list[dict]], dict[str, int]]:
    """Pick the most recent valid dataset for each required kind.

    Returns ``(datasets_by_kind_raw_data, dataset_id_by_kind)``.
    """
    by_kind: dict[str, list[dict]] = {}
    ids: dict[str, int] = {}

    for kind in REQUIRED_KINDS:
        ds = await db.scalar(
            select(Dataset)
            .where(
                Dataset.project_id == project_id,
                Dataset.kind == kind,
                Dataset.is_valid.is_(True),
            )
            .order_by(Dataset.id.desc())
            .limit(1)
        )
        if ds is None:
            continue
        by_kind[kind] = list(ds.raw_data or [])
        ids[kind] = ds.id

    return by_kind, ids


@router.post("/run", response_model=SplitRunDetail, status_code=status.HTTP_201_CREATED)
async def run_split(project_id: int, db: DbSession, user: CurrentUser):
    """Execute the splitter pipeline against the project's latest valid datasets."""
    await _get_owned_project(db, project_id, user.id)

    datasets_by_kind, dataset_ids = await _latest_valid_datasets(db, project_id)

    missing = [k for k in REQUIRED_KINDS if k not in dataset_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cannot run splitter — missing valid datasets: "
                + ", ".join(missing)
                + ". Upload and validate one of each kind before running."
            ),
        )

    run = SplitRun(
        project_id=project_id,
        status=SplitRunStatus.running,
        dataset_ids=dataset_ids,
    )
    db.add(run)
    await db.flush()

    try:
        artifacts = execute_run(datasets_by_kind)
    except RunInputError as exc:
        run.status = SplitRunStatus.failed
        run.error = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001 — engine errors surface verbatim
        run.status = SplitRunStatus.failed
        run.error = f"{type(exc).__name__}: {exc}"
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Run failed: {exc}",
        ) from exc

    run.marker_preview = artifacts.marker_preview
    run.detail = artifacts.detail
    run.summary = artifacts.summary
    run.warnings = artifacts.warnings
    run.status = SplitRunStatus.succeeded
    run.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run)

    return _build_detail_response(run)


@router.get("/runs", response_model=list[SplitRunRead])
async def list_runs(project_id: int, db: DbSession, user: CurrentUser):
    """List runs for a project (newest first), without the heavy detail/summary blobs."""
    await _get_owned_project(db, project_id, user.id)
    result = await db.scalars(
        select(SplitRun)
        .where(SplitRun.project_id == project_id)
        .order_by(SplitRun.id.desc())
    )
    return result.all()


@router.get("/runs/{run_id}", response_model=SplitRunDetail)
async def get_run(project_id: int, run_id: int, db: DbSession, user: CurrentUser):
    await _get_owned_project(db, project_id, user.id)

    run = await db.scalar(
        select(SplitRun).where(
            SplitRun.id == run_id, SplitRun.project_id == project_id
        )
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    return _build_detail_response(run)


@router.get("/runs/{run_id}/export")
async def export_run(
    project_id: int,
    run_id: int,
    db: DbSession,
    user: CurrentUser,
    table: str = Query("detail", pattern="^(detail|summary|marker)$"),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
):
    """Stream the full ``detail`` or ``summary`` table as CSV / XLSX.

    Bypasses the UI truncation so users can pull complete results for
    downstream analysis.
    """
    await _get_owned_project(db, project_id, user.id)

    run = await db.scalar(
        select(SplitRun).where(
            SplitRun.id == run_id, SplitRun.project_id == project_id
        )
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    if run.status != SplitRunStatus.succeeded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run is not in a succeeded state.",
        )

    rows: list[dict] = list(
        (
            run.marker_preview
            if table == "marker"
            else run.detail
            if table == "detail"
            else run.summary
        )
        or []
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run has no {table} rows.",
        )

    headers_order = list(rows[0].keys())
    filename_base = f"split_run_{run_id}_{table}"

    if format == "csv":
        return _stream_csv(rows, headers_order, filename_base)
    return _stream_xlsx(rows, headers_order, filename_base)


def _stream_csv(
    rows: list[dict], headers: list[str], filename_base: str
) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _csv_cell(row.get(k)) for k in headers})
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename_base}.csv"'
        },
    )


def _stream_xlsx(
    rows: list[dict], headers: list[str], filename_base: str
) -> StreamingResponse:
    # Imported lazily so unrelated requests don't pay the openpyxl cost.
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(headers)
    for row in rows:
        ws.append([_xlsx_cell(row.get(k)) for k in headers])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename_base}.xlsx"'
        },
    )


def _csv_cell(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        # Lists (e.g. MARKER column) get joined for readable CSV output.
        if isinstance(value, list):
            return "|".join(str(v) for v in value)
        return str(value)
    return value


def _xlsx_cell(value):
    if value is None:
        return None
    if isinstance(value, list):
        return "|".join(str(v) for v in value)
    if isinstance(value, dict):
        return str(value)
    return value


def _build_detail_response(run: SplitRun) -> SplitRunDetail:
    """Truncate the detail payload before returning to the client.

    The full payload stays in the DB; the API only ships the head so very
    large datasets don't freeze the browser. ``summary`` is small (one row
    per sand) so we always return it in full. Use the ``/export`` endpoint
    above to download the complete table.
    """
    detail = list(run.detail or [])
    marker_preview = list(run.marker_preview or [])
    return SplitRunDetail(
        id=run.id,
        project_id=run.project_id,
        status=run.status,
        error=run.error,
        dataset_ids=run.dataset_ids,
        warnings=run.warnings,
        created_at=run.created_at,
        completed_at=run.completed_at,
        marker_preview=marker_preview[:_DETAIL_ROW_LIMIT],
        detail=detail[:_DETAIL_ROW_LIMIT],
        summary=list(run.summary or []),
    )
