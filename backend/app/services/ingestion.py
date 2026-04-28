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
from typing import Any

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


# ── Validation ───────────────────────────────────────────────────────────────


def _coerce(value: Any, expected: type) -> tuple[Any, str | None]:
    """Try to coerce *value* into *expected* type; return (coerced, error).

    Empty strings are treated as missing values (a common artefact of Excel
    cells and CSV pastes).
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
    schema = KIND_SCHEMAS.get(kind)
    if schema is None:
        raise ValueError(f"Unknown dataset kind: {kind}")

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

    for row_idx in range(len(df)):
        for col, expected_type in schema.items():
            val = df.iloc[row_idx][col]
            _, err = _coerce(val, expected_type)
            if err:
                errors.append({"row": row_idx + 1, "column": col, "message": err})

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
            if col in df.columns:
                for row_idx in range(len(df)):
                    val = df.iloc[row_idx][col]
                    _, err = _coerce(val, float)
                    if err:
                        errors.append(
                            {"row": row_idx + 1, "column": col, "message": err}
                        )

    for col in _NON_NEGATIVE_NUMERIC.get(kind, ()):
        if col not in df.columns:
            continue
        for row_idx in range(len(df)):
            val = _to_float(df.iloc[row_idx][col])
            if val is not None and val < 0:
                errors.append(
                    {
                        "row": row_idx + 1,
                        "column": col,
                        "message": f"must be ≥ 0, got {val}",
                    }
                )

    if kind == "completion":
        for row_idx in range(len(df)):
            status_raw = df.iloc[row_idx].get("Perf Status")
            if pd.notna(status_raw) and str(status_raw).strip().lower() not in _VALID_PERF_STATUSES:
                errors.append(
                    {
                        "row": row_idx + 1,
                        "column": "Perf Status",
                        "message": (
                            f"must be 'perforation' or 'squeeze', got '{status_raw}'"
                        ),
                    }
                )

            top = _to_float(df.iloc[row_idx].get("Perf Top"))
            base = _to_float(df.iloc[row_idx].get("Perf Bottom"))
            if top is not None and base is not None and base <= top:
                errors.append(
                    {
                        "row": row_idx + 1,
                        "column": "Perf Bottom",
                        "message": (
                            f"Perf Bottom ({base}) must be deeper than Perf Top ({top})."
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


def _df_to_json_safe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to list-of-dicts, replacing NaN/NaT with None."""
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    safe: list[dict[str, Any]] = []
    for row in records:
        safe.append(
            {k: (None if isinstance(v, float) and pd.isna(v) else v)
             for k, v in row.items()}
        )
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
