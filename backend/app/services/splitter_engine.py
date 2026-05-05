"""KH-weighted splitting engine.

Takes the markered production DataFrame (where sand columns contain ``"p"``
for open sands), lumping KH data, and a well list to produce per-sand
allocated volumes for OIL, GAS, WATER, and WINJ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SplitResult:
    """Output of the splitting engine."""

    detail: pd.DataFrame
    summary: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


# ── Fluids we allocate ───────────────────────────────────────────────────────
# Ingestion and :func:`marker_engine` use this physical order, but
# *only* the fluid columns that exist on the production frame are
# allocated, so a user with only *Oil* and *Water* in Production never
# sees *GAS_* / *WINJ_* in the result.

FLUID_COLUMNS = ("OIL", "GAS", "WATER", "WINJ")


def _active_fluids(markered_df: pd.DataFrame) -> tuple[str, ...]:
    """Fluids present on ``markered_df`` (subset of ``FLUID_COLUMNS`` order)."""
    return tuple(f for f in FLUID_COLUMNS if f in markered_df.columns)


def _safe_float(v: Any) -> float:
    """Convert to float, treating NaN / None as 0."""
    try:
        f = float(v)
        return f if not np.isnan(f) else 0.0
    except (TypeError, ValueError):
        return 0.0


# ── Public API ───────────────────────────────────────────────────────────────

def split(
    markered_df: pd.DataFrame,
    lumping_df: pd.DataFrame,
    well_list: list[str],
    sands: list[str],
) -> SplitResult:
    """Run KH-weighted production splitting.

    Parameters
    ----------
    markered_df : DataFrame
        Production data with one column per sand.  Values of ``"p"`` (or
        ``"P"``) mark an open sand for that timestep.  Must contain ``WELL``,
        ``DATE``, and at least one of ``OIL``, ``GAS``, ``WATER``, ``WINJ``.
    lumping_df : DataFrame
        Indexed by zone / sand name, with one column per well holding the KH
        value.  Example::

            Zone log  | W-01 | W-02
            ----------+------+-----
            T_TE600   |  50  |  60
            T_TE1000  | 120  |  90
    well_list : list[str]
        Ordered well names (controls iteration order).
    sands : list[str]
        Master ordered sand list.

    Returns
    -------
    SplitResult
        ``.detail`` — row-level allocated volumes per sand.
        ``.summary`` — sand-level totals.
    """
    warnings: list[str] = []

    active_fluids = _active_fluids(markered_df)
    if not active_fluids:
        raise ValueError(
            "markered_df must have at least one of "
            + ", ".join(FLUID_COLUMNS)
            + " (production fluids)."
        )

    meta_cols = [c for c in markered_df.columns if c not in sands]
    detail = markered_df[meta_cols].copy()

    for s in sands:
        for fluid in active_fluids:
            detail[f"{fluid}_{s}"] = 0.0

    for well in well_list:
        well_str = str(well)
        well_mask = markered_df["WELL"].astype(str) == well_str
        if not well_mask.any():
            continue

        if well_str not in lumping_df.columns:
            warnings.append(f"Well {well_str}: not found in lumping data, skipped.")
            continue

        for idx in markered_df.index[well_mask]:
            total_kh = 0.0
            open_sands: list[str] = []

            for s in sands:
                if s not in markered_df.columns:
                    continue
                val = markered_df.at[idx, s]
                if pd.notna(val) and str(val).upper() == "P":
                    kh = _safe_float(lumping_df.at[s, well_str]) if s in lumping_df.index else 0.0
                    total_kh += kh
                    open_sands.append(s)

            for s in sands:
                if s not in markered_df.columns:
                    continue
                if total_kh > 0 and s in open_sands:
                    kh = _safe_float(lumping_df.at[s, well_str]) if s in lumping_df.index else 0.0
                    fraction = kh / total_kh
                    for fluid in active_fluids:
                        vol = _safe_float(markered_df.at[idx, fluid])
                        detail.at[idx, f"{fluid}_{s}"] = vol * fraction

    summary_rows: list[dict[str, Any]] = []
    for s in sands:
        row: dict[str, Any] = {"Sand": s}
        for fluid in active_fluids:
            col = f"{fluid}_{s}"
            row[f"Total_{fluid}"] = float(detail[col].sum()) if col in detail.columns else 0.0
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)

    return SplitResult(detail=detail, summary=summary, warnings=warnings)
