"""Data ingestion service — parse, validate, and normalise uploaded datasets.

Supports three input vectors:
* **paste** — caller provides ``list[dict]`` already (from pasted TSV/CSV
  parsed on the frontend).
* **csv** / **tsv** — raw bytes from an uploaded file.
* **xlsx** — raw bytes from an uploaded Excel file (uses openpyxl via pandas).

Row-level validation is applied per dataset *kind*. Each kind specifies a set
of required columns and per-column type expectations.

Cross-column rules (e.g. ``Perf Base > Perf Top``) are layered on top of the
basic per-cell coercion checks.
"""

from __future__ import annotations

import io
import math
import re
from datetime import date, datetime, time
from typing import Any

import numpy as np
import pandas as pd


# ── Column schemas per dataset kind ──────────────────────────────────────────

_MARKER_REQUIRED = {"Well": str, "Marker": str, "Depth": float}
_SAND_REQUIRED = {"Marker": str}
_COMPLETION_REQUIRED = {
    "Well": str,
    "Date": str,
    "Perf Status": str,
    "Perf Top": float,
    "Perf Bottom": float,
}
_PRODUCTION_REQUIRED = {
    "Well": str,
    "Date": str,
}
_LUMPING_REQUIRED = {"Zone": str, "Well": str, "Lumping": float}
_WELL_REQUIRED = {"Well": str}

KIND_SCHEMAS: dict[str, dict[str, type]] = {
    "marker": _MARKER_REQUIRED,
    "sand": _SAND_REQUIRED,
    "completion": _COMPLETION_REQUIRED,
    "production": _PRODUCTION_REQUIRED,
    "lumping": _LUMPING_REQUIRED,
    "well": _WELL_REQUIRED,
}

_PRODUCTION_FLUID_COLUMNS = ("Oil", "Water", "Gas", "Water Injection")
_VALID_PERF_STATUSES = frozenset({"perforation", "squeeze"})
_NON_NEGATIVE_NUMERIC = {
    "marker": ("Depth",),
    "completion": ("Perf Top", "Perf Bottom"),
    "production": _PRODUCTION_FLUID_COLUMNS,
    "lumping": ("Lumping",),
}

# Columns that should be normalised to a canonical DD/MM/YYYY string before
# validation. Keeps storage/display consistent regardless of whether the
# source was a paste of "13/1/2007" strings or an Excel datetime cell.
_DATE_COLUMNS_BY_KIND: dict[str, tuple[str, ...]] = {
    "completion": ("Date",),
    "production": ("Date",),
}
_DATE_DISPLAY_FORMAT = "%d/%m/%Y"

_COLUMN_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "marker": {
        "Well": ("Well", "WELL", "well"),
        "Marker": ("Marker", "Sand", "ZONE"),
        "Depth": ("Depth", "MD", "Marker Depth"),
    },
    "sand": {
        "Marker": ("Marker", "Sand", "Zone"),
    },
    "completion": {
        "Well": ("Well", "WELL"),
        "Date": ("Date", "DATE"),
        "Perf Status": ("Perf Status", "Status", "PerfStatus"),
        "Perf Top": ("Perf Top", "Perf Top (ftMD)", "PerfTop", "Top", "Perf From"),
        "Perf Bottom": (
            "Perf Bottom",
            "Perf Base",
            "Perf Base (ftMD)",
            "Perf Bottom (ftMD)",
            "PerfBottom",
            "Bottom",
            "Perf To",
        ),
    },
    "production": {
        "Well": ("Well", "WELL"),
        "Date": ("Date", "DATE"),
        "Oil": ("Oil", "OIL"),
        "Water": ("Water", "WATER"),
        "Gas": ("Gas", "GAS"),
        "Water Injection": ("Water Injection", "WINJ", "WaterInjection", "W Inj"),
    },
    "lumping": {
        "Zone": ("Zone", "Sand", "Marker"),
        "Well": ("Well", "WELL"),
        "Lumping": ("Lumping", "KH"),
    },
    "well": {
        "Well": ("Well", "WELL"),
    },
}

# ── Parsing helpers ──────────────────────────────────────────────────────────


def parse_csv_bytes(raw: bytes) -> pd.DataFrame:
    """Auto-detect delimiter (comma or tab) and return a DataFrame."""
    text = raw.decode("utf-8-sig", errors="replace")
    sep = "\t" if "\t" in text.split("\n", 1)[0] else ","
    return pd.read_csv(io.StringIO(text), sep=sep)


def parse_xlsx_bytes(raw: bytes, sheet_name: str | None = None) -> pd.DataFrame:
    return pd.read_excel(
        io.BytesIO(raw),
        sheet_name=sheet_name or 0,
        engine="openpyxl",
    )


def list_xlsx_sheets(raw: bytes) -> list[str]:
    """Return workbook sheet names without loading every sheet into memory."""
    with pd.ExcelFile(io.BytesIO(raw), engine="openpyxl") as excel:
        return list(excel.sheet_names)


def records_to_df(data: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(data)


def _normalize_header(value: str) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _canonicalize_columns(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Rename known header variants to canonical names for *kind*.

    This allows users to keep arbitrary column order and common header
    variants (case, spacing, legacy names like "Perf Base (ftMD)", etc.).
    """
    aliases = _COLUMN_ALIASES.get(kind, {})
    if not aliases:
        return df

    normalized_to_canonical: dict[str, str] = {}
    for canonical, variants in aliases.items():
        for variant in variants:
            normalized_to_canonical[_normalize_header(variant)] = canonical

    rename_map: dict[str, str] = {}
    used_targets: set[str] = set()
    for column in df.columns:
        canonical = normalized_to_canonical.get(_normalize_header(str(column)))
        if canonical is None:
            continue
        # Keep the first matching source for a canonical target.
        if canonical in used_targets:
            continue
        rename_map[column] = canonical
        used_targets.add(canonical)

    return df.rename(columns=rename_map)


# ── Validation ───────────────────────────────────────────────────────────────


def _coerce(value: Any, expected: type) -> tuple[Any, str | None]:
    """Try to coerce *value* into *expected* type; return (coerced, error).

    Empty strings are treated as missing values (a common artefact of Excel
    cells and CSV pastes).

    Kept as a single-cell helper for tests / small-scale callers; the bulk
    column-level validation in :func:`validate_rows` is vectorised below.
    """
    if pd.isna(value):
        return None, "value is missing"
    if isinstance(value, str) and value.strip() == "":
        return None, "value is missing"
    try:
        if expected is float:
            return float(value), None
        if expected is str:
            return str(value), None
        return expected(value), None
    except (TypeError, ValueError):
        return value, f"expected {expected.__name__}, got {type(value).__name__}"


def _missing_mask(series: pd.Series) -> np.ndarray:
    """Return a boolean array marking NaN/None and whitespace-only string cells.

    Operates on the whole column at once instead of cell-by-cell, which is
    O(N) but with one Python pass per column rather than per cell.
    """
    arr = series.to_numpy()
    isna = pd.isna(arr)
    is_blank_str = np.fromiter(
        (isinstance(v, str) and v.strip() == "" for v in arr),
        dtype=bool,
        count=len(arr),
    )
    return isna | is_blank_str


def _validate_column(series: pd.Series, expected_type: type, col: str) -> list[dict[str, Any]]:
    """Vectorised per-column validation. Returns a list of error dicts.

    Iterates only over invalid positions so clean datasets are O(1) in the
    error-construction step regardless of length.
    """
    errors: list[dict[str, Any]] = []
    missing = _missing_mask(series)
    arr = series.to_numpy()

    for pos in np.flatnonzero(missing):
        errors.append(
            {"row": int(pos) + 1, "column": col, "message": "value is missing"}
        )

    if expected_type is float:
        coerced = pd.to_numeric(series, errors="coerce").to_numpy()
        # NaN in coerced + non-missing in original ⇒ uncoercible value.
        bad_type = np.isnan(coerced) & ~missing
        for pos in np.flatnonzero(bad_type):
            val = arr[pos]
            errors.append(
                {
                    "row": int(pos) + 1,
                    "column": col,
                    "message": f"expected float, got {type(val).__name__}",
                }
            )

    # ``str`` columns: anything not caught by the missing mask coerces via
    # ``str()`` without error, so no extra type check needed.
    return errors


def _normalize_date_value(value: Any) -> Any:
    """Normalise a single Date cell to a ``DD/MM/YYYY`` string.

    Accepts pandas ``Timestamp`` / ``datetime`` / ``date`` (from Excel) and
    string forms like ``"13/1/2007"``, ``"2025-01-15"``,
    ``"2025-01-15T00:00:00"``. Day-first parsing is used for ambiguous
    numeric strings to match the requested ``DD/MM/YYYY`` output. Empty,
    missing, or unparseable values pass through unchanged so per-cell
    validation can flag them downstream.
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            return None
        return ts.strftime(_DATE_DISPLAY_FORMAT)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # Prefer ISO parsing for unambiguous YYYY-MM-DD strings; otherwise
        # fall back to day-first to honour formats like "13/1/2007".
        is_iso = bool(re.match(r"^\d{4}-\d{2}-\d{2}", text))
        try:
            ts = pd.to_datetime(text, dayfirst=not is_iso, errors="raise")
        except (ValueError, TypeError):
            return value
        if pd.isna(ts):
            return None
        return ts.strftime(_DATE_DISPLAY_FORMAT)
    return value


def _normalize_date_columns(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Normalise known Date columns in *df* to ``DD/MM/YYYY`` strings."""
    columns = _DATE_COLUMNS_BY_KIND.get(kind, ())
    if not columns:
        return df
    for col in columns:
        if col in df.columns:
            df[col] = df[col].map(_normalize_date_value)
    return df


def _to_float(value: Any) -> float | None:
    """Best-effort float conversion; returns ``None`` on failure or NaN."""
    if pd.isna(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:  # NaN check without importing math
        return None
    return result


def validate_rows(
    df: pd.DataFrame,
    kind: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate *df* against the schema for *kind*.

    Returns
    -------
    (clean_rows, errors)
        ``clean_rows`` is a list of dicts (JSON-serialisable) suitable for
        storing in ``Dataset.raw_data``.
        ``errors`` is a list of ``{"row": int, "column": str, "message": str}``.
    """
    df = _canonicalize_columns(df, kind)
    df = _normalize_date_columns(df, kind)
    schema = KIND_SCHEMAS.get(kind)
    if schema is None:
        raise ValueError(f"Unknown dataset kind: {kind}")

    # Reset to a positional 0..N-1 index so error rows are predictable
    # regardless of the index attached by the caller (Excel / CSV reads can
    # carry over arbitrary indexes).
    df = df.reset_index(drop=True)

    errors: list[dict[str, Any]] = []

    missing_cols = set(schema.keys()) - set(df.columns)
    if missing_cols:
        errors.append(
            {
                "row": 0,
                "column": ", ".join(sorted(missing_cols)),
                "message": f"Missing required column(s): {', '.join(sorted(missing_cols))}",
            }
        )
        clean = df.head(0).to_dict(orient="records")
        return clean, errors

    if len(df) == 0:
        errors.append({"row": 0, "column": "*", "message": "Dataset is empty."})
        return [], errors

    for col, expected_type in schema.items():
        errors.extend(_validate_column(df[col], expected_type, col))

    if kind == "production":
        present_fluid_cols = [col for col in _PRODUCTION_FLUID_COLUMNS if col in df.columns]
        if not present_fluid_cols:
            errors.append(
                {
                    "row": 0,
                    "column": ", ".join(_PRODUCTION_FLUID_COLUMNS),
                    "message": (
                        "Production must include at least one fluid column: "
                        "Oil, Water, Gas, or Water Injection."
                    ),
                }
            )

        for col in present_fluid_cols:
            errors.extend(_validate_column(df[col], float, col))

    for col in _NON_NEGATIVE_NUMERIC.get(kind, ()):
        if col not in df.columns:
            continue
        coerced = pd.to_numeric(df[col], errors="coerce").to_numpy()
        # ``coerced < 0`` propagates NaN as False, so missing/uncoercible
        # cells (already flagged above) are skipped here.
        bad_negative = (coerced < 0) & ~np.isnan(coerced)
        for pos in np.flatnonzero(bad_negative):
            errors.append(
                {
                    "row": int(pos) + 1,
                    "column": col,
                    "message": f"must be ≥ 0, got {coerced[pos]}",
                }
            )

    if kind == "completion":
        status_series = df["Perf Status"]
        status_arr = status_series.to_numpy()
        status_lower = (
            status_series.astype(object)
            .map(lambda v: str(v).strip().lower() if isinstance(v, str) else v)
        )
        invalid_status = (
            status_series.notna().to_numpy()
            & ~status_lower.isin(_VALID_PERF_STATUSES).to_numpy()
        )
        for pos in np.flatnonzero(invalid_status):
            errors.append(
                {
                    "row": int(pos) + 1,
                    "column": "Perf Status",
                    "message": (
                        f"must be 'perforation' or 'squeeze', got '{status_arr[pos]}'"
                    ),
                }
            )

        top = pd.to_numeric(df["Perf Top"], errors="coerce").to_numpy()
        base = pd.to_numeric(df["Perf Bottom"], errors="coerce").to_numpy()
        valid_pair = ~np.isnan(top) & ~np.isnan(base)
        bad_depth = valid_pair & (base <= top)
        for pos in np.flatnonzero(bad_depth):
            errors.append(
                {
                    "row": int(pos) + 1,
                    "column": "Perf Bottom",
                    "message": (
                        f"Perf Bottom ({base[pos]}) must be deeper than "
                        f"Perf Top ({top[pos]})."
                    ),
                }
            )

    clean = _pivot_lumping(df) if kind == "lumping" and not errors else _df_to_json_safe(df)
    return clean, errors


def _pivot_lumping(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert long-format lumping input to a zone × well matrix.

    Input rows:
        Zone | Well | Lumping

    Stored preview/output:
        Zone | W-01 | W-02 | ...
    """
    pivot = (
        df.assign(Lumping=df["Lumping"].map(float))
        .pivot_table(
            index="Zone",
            columns="Well",
            values="Lumping",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )
    pivot.columns = [str(col) for col in pivot.columns]
    return _df_to_json_safe(pivot)


def _to_json_value(value: Any) -> Any:
    """Coerce a single cell value into a JSON-serializable form.

    Excel uploads return ``pandas.Timestamp`` / ``datetime`` for date cells
    and ``numpy.*`` scalars for numerics — neither is JSON-safe out of the
    box. We render dates as ISO strings and unwrap numpy scalars to native
    Python.
    """
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
    return value


def _df_to_json_safe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to list-of-dicts of JSON-safe primitives.

    Replaces NaN / NaT with ``None`` and serializes datetimes as ISO strings
    so the result can be written into a JSONB column without errors.
    """
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    safe: list[dict[str, Any]] = []
    for row in records:
        safe.append({k: _to_json_value(v) for k, v in row.items()})
    return safe


# ── Convenience façade ───────────────────────────────────────────────────────


def ingest(
    kind: str,
    *,
    raw_bytes: bytes | None = None,
    filename: str | None = None,
    sheet_name: str | None = None,
    pasted_rows: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], bool]:
    """Parse + validate in one step.

    Returns ``(source, clean_rows, errors, is_valid)``.
    """
    if pasted_rows is not None:
        df = records_to_df(pasted_rows)
        source = "paste"
    elif raw_bytes is not None and filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("xlsx", "xls"):
            df = parse_xlsx_bytes(raw_bytes, sheet_name)
            source = "xlsx"
        else:
            df = parse_csv_bytes(raw_bytes)
            source = "csv"
    else:
        raise ValueError("Provide either pasted_rows or (raw_bytes + filename).")

    clean, errors = validate_rows(df, kind)
    return source, clean, errors, len(errors) == 0
