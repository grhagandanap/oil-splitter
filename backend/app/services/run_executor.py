"""Project run orchestrator.

Wires the latest valid datasets (marker, sand, completion, production,
lumping, well) for a project into the marker / gap-filler / splitter
pipeline and returns JSON-safe artefacts ready to persist on a ``SplitRun``.

The ingestion pipeline stores datasets with canonical Title-Case column names
(``Well``, ``Date``, ``Oil`` …); the engines expect the older notebook-style
upper-case names (``WELL``, ``DATE``, ``OIL`` …) and ``Perf Top (ftMD)`` /
``Perf Base (ftMD)``. All renaming happens here so the engines stay
unchanged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

import numpy as np  # pyright: ignore[reportMissingImports]
import pandas as pd  # pyright: ignore[reportMissingImports]

from app.services.gap_filler import detect_gaps
from app.services.marker_engine import auto_marker
from app.services.splitter_engine import split

# ── Required dataset kinds ───────────────────────────────────────────────────

REQUIRED_KINDS = ("marker", "sand", "completion", "production", "lumping", "well")


# ── Public payload returned to the API layer ─────────────────────────────────


@dataclass
class RunArtifacts:
    """JSON-serialisable outputs ready to persist on a ``SplitRun``."""

    detail: list[dict[str, Any]]
    summary: list[dict[str, Any]]
    warnings: list[str]


class RunInputError(ValueError):
    """Raised when one or more required datasets are missing or invalid."""


# ── Orchestrator ─────────────────────────────────────────────────────────────


def execute_run(datasets_by_kind: dict[str, list[dict[str, Any]]]) -> RunArtifacts:
    """Run marker assignment + gap filling + splitting for a project.

    Parameters
    ----------
    datasets_by_kind : dict
        Mapping of dataset kind → ``raw_data`` list-of-dicts as produced by
        :func:`app.services.ingestion.validate_rows`.

    Raises
    ------
    RunInputError
        If a required kind is missing or empty.
    """
    _require_kinds(datasets_by_kind)

    sands = _build_sands(datasets_by_kind["sand"])
    well_list = _build_well_list(datasets_by_kind["well"])
    completion_df = _build_completion_df(
        marker_rows=datasets_by_kind["marker"],
        completion_rows=datasets_by_kind["completion"],
        global_sands=sands,
    )
    production_df = _build_production_df(datasets_by_kind["production"])
    lumping_df = _build_lumping_df(datasets_by_kind["lumping"])

    warnings: list[str] = []

    # 1. Marker pipeline.
    marker_result = auto_marker(production_df, completion_df, sands)
    warnings.extend(marker_result.warnings)
    markered = marker_result.markered_production

    # 2. Gap filling — auto-fill leading/trailing in place; report middle gaps.
    filled, report = detect_gaps(markered, sands)
    if report.middle_gaps:
        for gap in report.middle_gaps:
            warnings.append(
                f"Middle gap left unfilled — well={gap.well} sand={gap.sand} "
                f"rows={gap.start_row}..{gap.end_row}"
            )

    # 3. Splitter.
    result = split(filled, lumping_df, well_list, sands)
    warnings.extend(result.warnings)

    return RunArtifacts(
        detail=_df_to_records(result.detail),
        summary=_df_to_records(result.summary),
        warnings=warnings,
    )


# ── Validation ───────────────────────────────────────────────────────────────


def _require_kinds(datasets_by_kind: dict[str, list[dict[str, Any]]]) -> None:
    missing = [k for k in REQUIRED_KINDS if not datasets_by_kind.get(k)]
    if missing:
        raise RunInputError(
            "Missing or empty required datasets: " + ", ".join(missing)
        )


# ── Builders: ingestion JSON → engine-shaped DataFrames ──────────────────────


def _build_sands(rows: list[dict[str, Any]]) -> list[str]:
    sands: list[str] = []
    seen: set[str] = set()
    for row in rows:
        marker = row.get("Marker")
        if marker is None:
            continue
        s = str(marker).strip()
        if s and s not in seen:
            sands.append(s)
            seen.add(s)
    if not sands:
        raise RunInputError("Sand dataset has no Marker values.")
    return sands


def _build_well_list(rows: list[dict[str, Any]]) -> list[str]:
    wells: list[str] = []
    seen: set[str] = set()
    for row in rows:
        well = row.get("Well")
        if well is None:
            continue
        w = str(well).strip()
        if w and w not in seen:
            wells.append(w)
            seen.add(w)
    if not wells:
        raise RunInputError("Wells dataset has no Well values.")
    return wells


def _build_production_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        raise RunInputError("Production dataset is empty.")
    df = df.rename(
        columns={
            "Well": "WELL",
            "Date": "DATE",
            "Oil": "OIL",
            "Water": "WATER",
            "Gas": "GAS",
            "Water Injection": "WINJ",
        }
    )
    df["DATE"] = _parse_dates(df["DATE"])
    return df


def _build_completion_df(
    *,
    marker_rows: list[dict[str, Any]],
    completion_rows: list[dict[str, Any]],
    global_sands: list[str],
) -> pd.DataFrame:
    """Merge per-well marker depths into the completion frame.

    The marker engine expects each completion row to carry one column per
    *global sand*, holding the MD for that sand on that well (NaN when the
    well doesn't penetrate that sand). We pivot the marker dataset and join
    it onto the completion rows on ``Well``.
    """
    if not completion_rows:
        raise RunInputError("Completion dataset is empty.")
    if not marker_rows:
        raise RunInputError("Marker dataset is empty.")

    markers = pd.DataFrame(marker_rows)
    if not {"Well", "Marker", "Depth"}.issubset(markers.columns):
        raise RunInputError(
            "Marker dataset must have Well / Marker / Depth columns."
        )

    pivoted = (
        markers.assign(Depth=pd.to_numeric(markers["Depth"], errors="coerce"))
        .pivot_table(
            index="Well",
            columns="Marker",
            values="Depth",
            aggfunc="first",
        )
    )
    # Ensure every global sand exists as a column even if no well has that
    # marker — assign_ways / assign_markers iterate over global_sands.
    for s in global_sands:
        if s not in pivoted.columns:
            pivoted[s] = pd.NA
    pivoted = pivoted[[c for c in pivoted.columns if c in global_sands]]

    completion = pd.DataFrame(completion_rows).rename(
        columns={
            "Well": "WELL",
            "Date": "DATE",
            "Perf Top": "Perf Top (ftMD)",
            "Perf Bottom": "Perf Base (ftMD)",
        }
    )
    completion["DATE"] = _parse_dates(completion["DATE"])

    # Normalise status casing — auto_marker compares against literal
    # ``"perforation"`` / ``"squeeze"``.
    if "Perf Status" in completion.columns:
        completion["Perf Status"] = (
            completion["Perf Status"].astype(str).str.strip().str.lower()
        )

    merged = completion.merge(
        pivoted.reset_index().rename(columns={"Well": "WELL"}),
        on="WELL",
        how="left",
    )
    return merged


def _build_lumping_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Lumping is already pivoted at ingestion time (Zone × Well matrix)."""
    if not rows:
        raise RunInputError("Lumping dataset is empty.")
    df = pd.DataFrame(rows)
    if "Zone" not in df.columns:
        raise RunInputError("Lumping dataset must include a Zone column.")
    return df.set_index("Zone")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse heterogeneous date inputs (``DD/MM/YYYY`` strings, ISO,
    ``Timestamp``s) into a ``datetime64[ns]`` series."""

    def _parse_one(value: Any) -> Any:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return pd.NaT
        if isinstance(value, (pd.Timestamp, datetime, date)):
            return pd.Timestamp(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return pd.NaT
            try:
                # ``DD/MM/YYYY`` or ISO — disambiguated by string shape.
                if len(text) >= 10 and text[4:5] == "-":
                    return pd.to_datetime(text)
                return pd.to_datetime(text, dayfirst=True)
            except (ValueError, TypeError):
                return pd.NaT
        return pd.NaT

    return series.map(_parse_one)


def _to_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, list):
        return [_to_json_value(v) for v in value]
    return value


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    return [{k: _to_json_value(v) for k, v in row.items()} for row in records]
