"""Marker engine — assigns TOP_WAY / BOTTOM_WAY to each completion event,
resolves the final MARKER list per row, and processes squeeze events.

Key improvements over the Jupyter Notebook version:

*  **First-marker tolerance** — when Perf Top is shallower than the
   shallowest marker by ≤ ``tolerance_ft`` (default 10 ft) we snap to that
   first marker instead of falling through to a hard-coded zone name.
*  **No hard-coded zone names** — the ``T_PM2300`` / ``T_TE600`` special case
   is replaced by the generic tolerance rule above.
*  **Pure-function API** — every function takes DataFrames / lists in and
   returns results; nothing mutates global state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


# ── Public data structures ──────────────────────────────────────────────────

@dataclass
class MarkerResult:
    """Result of the full markering + auto-marker pipeline for one project."""

    markered_production: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


# ── Step 1: assign TOP_WAY / BOTTOM_WAY ─────────────────────────────────────

def _assign_way(
    perf_depth: float,
    marker_depths: dict[str, float],
    sand_list: list[str],
    global_sands: list[str],
    tolerance_ft: float,
) -> str:
    """Determine which marker zone a perforation depth falls into.

    Parameters
    ----------
    perf_depth : float
        Perf Top or Perf Base measured depth.
    marker_depths : dict[str, float]
        ``{sand_name: MD}`` for the sands that have valid marker data in this
        well (subset of *global_sands*).
    sand_list : list[str]
        Ordered sand names present in this well (same order as *global_sands*).
    global_sands : list[str]
        Master ordered sand list from the "Sand" sheet.
    tolerance_ft : float
        If perf_depth is shallower than the first marker by at most this
        value, snap to that first marker.
    """
    if not sand_list:
        return ""

    if len(sand_list) == 1:
        s = sand_list[0]
        if perf_depth >= marker_depths[s]:
            return s
        # tolerance: perf is above the only marker
        if marker_depths[s] - perf_depth <= tolerance_ft:
            return s
        idx = global_sands.index(s) - 1
        return global_sands[idx] if idx >= 0 else s

    for k, s in enumerate(sand_list):
        if k == 0:
            if perf_depth < marker_depths[s]:
                diff = marker_depths[s] - perf_depth
                if diff <= tolerance_ft:
                    return s
                idx = global_sands.index(s) - 1
                return global_sands[idx] if idx >= 0 else s

        elif k == len(sand_list) - 1:
            if perf_depth >= marker_depths[s]:
                return s
            return sand_list[k - 1]

        else:
            if perf_depth < marker_depths[s]:
                return sand_list[k - 1]

    return sand_list[-1]


def assign_ways(
    completion_df: pd.DataFrame,
    global_sands: list[str],
    tolerance_ft: float = 10.0,
) -> pd.DataFrame:
    """Add ``TOP_WAY`` and ``BOTTOM_WAY`` columns to a completion DataFrame.

    Parameters
    ----------
    completion_df : DataFrame
        Must contain columns ``WELL``, ``DATE``, ``Perf Status``,
        ``Perf Top (ftMD)``, ``Perf Base (ftMD)``, and one column per sand
        whose value is the marker MD for that well (NaN when absent).
    global_sands : list[str]
        Master ordered sand list.
    tolerance_ft : float
        First-marker tolerance in feet.
    """
    result = completion_df.copy()
    result["TOP_WAY"] = ""
    result["BOTTOM_WAY"] = ""

    for well in result["WELL"].unique():
        mask = result["WELL"] == well
        temp = result.loc[mask]

        available_sands = [
            s for s in global_sands
            if s in temp.columns and temp[s].notna().all()
        ]
        if not available_sands:
            continue

        for idx in temp.index:
            marker_depths = {s: temp.at[idx, s] for s in available_sands}

            result.at[idx, "TOP_WAY"] = _assign_way(
                temp.at[idx, "Perf Top (ftMD)"],
                marker_depths,
                available_sands,
                global_sands,
                tolerance_ft,
            )
            result.at[idx, "BOTTOM_WAY"] = _assign_way(
                temp.at[idx, "Perf Base (ftMD)"],
                marker_depths,
                available_sands,
                global_sands,
                tolerance_ft,
            )

    return result


# ── Step 2: resolve final MARKER list ────────────────────────────────────────

def resolve_marker(
    top_way: str,
    bottom_way: str,
    well_sands: list[str],
    global_sands: list[str],
) -> list[str]:
    """Return the list of sand zones perforated between *top_way* and
    *bottom_way* (inclusive).

    Falls back to ``global_sands`` for range slicing when one or both ways are
    outside the well's local sand list.
    """
    if not top_way or not bottom_way:
        return []

    both_in_well = top_way in well_sands and bottom_way in well_sands

    if both_in_well:
        i = well_sands.index(top_way)
        j = well_sands.index(bottom_way)
        return well_sands[i : j + 1]

    if top_way in global_sands and bottom_way in global_sands:
        i = global_sands.index(top_way)
        j = global_sands.index(bottom_way)
        return global_sands[i : j + 1]

    return []


def assign_markers(
    df: pd.DataFrame,
    global_sands: list[str],
) -> pd.DataFrame:
    """Populate a ``MARKER`` column (list of perforated sands) on *df*.

    Requires ``TOP_WAY``, ``BOTTOM_WAY`` columns (output of ``assign_ways``).
    """
    result = df.copy()
    result["MARKER"] = None

    for well in result["WELL"].unique():
        mask = result["WELL"] == well
        temp = result.loc[mask]

        well_sands = [
            s for s in global_sands
            if s in temp.columns and temp[s].notna().all()
        ]

        for idx in temp.index:
            tw = result.at[idx, "TOP_WAY"]
            bw = result.at[idx, "BOTTOM_WAY"]
            result.at[idx, "MARKER"] = resolve_marker(tw, bw, well_sands, global_sands)

    return result


# ── Step 3: squeeze machine ──────────────────────────────────────────────────

def squeeze_machine(
    tp: list[float],
    bp: list[float],
    pf: list[list[str]],
    pd_dates: list[Any],
    ts: list[float],
    bs: list[float],
    sf: list[list[str]],
    sd_dates: list[Any],
    marker_row: dict[str, float],
) -> tuple[list[float], list[float], list[list[str]]]:
    """Process squeeze events against perforation events for a single
    production timestep.

    Modifies and returns *(tp, bp, pf)* in-place.
    """
    a = 0
    while a < len(sd_dates):
        b = 0
        while b < len(pd_dates):
            if sd_dates[a] >= pd_dates[b]:
                # partial squeeze from top
                if ts[a] == tp[b] and bs[a] < bp[b]:
                    tp[b] = bs[a]
                    if len(pf[b]) == len(sf[a]):
                        pf[b] = [pf[b][-1]]
                    elif len(pf[b]) > len(sf[a]):
                        boundary_sand = pf[b][len(sf[a])]
                        if boundary_sand in marker_row and tp[b] < marker_row[boundary_sand]:
                            pf[b] = [pf[b][len(sf[a]) - 1]] + [
                                x for x in pf[b] if x not in sf[a]
                            ]
                        else:
                            pf[b] = [x for x in pf[b] if x not in sf[a]]

                # partial squeeze from bottom
                elif ts[a] > tp[b] and bs[a] == bp[b]:
                    bp[b] = ts[a]
                    if len(pf[b]) == len(sf[a]):
                        pf[b] = [pf[b][0]]
                    elif len(pf[b]) > len(sf[a]):
                        boundary_sand = pf[b][len(sf[a])]
                        if boundary_sand in marker_row and bp[b] > marker_row[boundary_sand]:
                            pf[b] = [pf[b][len(sf[a])]] + [
                                x for x in pf[b] if x not in sf[a]
                            ]
                        else:
                            pf[b] = [x for x in pf[b] if x not in sf[a]]

            # full squeeze removes the entire perforation event
            if (
                b < len(pd_dates)
                and ts[a] <= tp[b]
                and bs[a] >= bp[b]
                and sd_dates[a] >= pd_dates[b]
            ):
                del pf[b], tp[b], bp[b], pd_dates[b]
            else:
                b += 1

        a += 1

    return tp, bp, pf


# ── Step 4: auto-marker (write "p" on production) ───────────────────────────

def _date_lte(prod_date: datetime, marker_date: datetime) -> bool:
    """Return True when *prod_date* is on or after the year-month of
    *marker_date* (day is ignored, matching notebook behaviour)."""
    if prod_date.year > marker_date.year:
        return True
    if prod_date.year == marker_date.year and prod_date.month >= marker_date.month:
        return True
    return False


def auto_marker(
    production_df: pd.DataFrame,
    completion_df: pd.DataFrame,
    global_sands: list[str],
    tolerance_ft: float = 10.0,
) -> MarkerResult:
    """Run the full auto-marker pipeline.

    1. ``assign_ways`` + ``assign_markers`` on *completion_df*.
    2. For each well × timestep in *production_df*, collect relevant
       perforation / squeeze events, apply ``squeeze_machine``, then write
       ``"p"`` in the sand columns that are open.

    Parameters
    ----------
    production_df : DataFrame
        Must contain ``WELL``, ``DATE``, ``OIL``, ``WATER`` (and optionally
        ``GAS``, ``WINJ``).
    completion_df : DataFrame
        Raw completion data merged with marker depths (see ``assign_ways``).
    global_sands : list[str]
        Master ordered sand list.
    tolerance_ft : float
        First-marker tolerance in feet (default 10).

    Returns
    -------
    MarkerResult
        ``.markered_production`` has original production columns plus one
        column per sand filled with ``"p"`` or ``NaN``.
    """
    warnings: list[str] = []

    comp = assign_ways(completion_df, global_sands, tolerance_ft)
    comp = assign_markers(comp, global_sands)

    prod = production_df.copy()
    for s in global_sands:
        prod[s] = pd.array([pd.NA] * len(prod), dtype="object")

    for uwi in prod["WELL"].unique():
        if uwi not in comp["WELL"].values:
            warnings.append(f"Well {uwi}: not found in completion data, skipped.")
            continue

        well_comp = comp[comp["WELL"] == uwi].reset_index(drop=True)
        if well_comp["MARKER"].isna().all():
            warnings.append(f"Well {uwi}: no valid markers, skipped.")
            continue

        well_sands = [
            s for s in global_sands
            if s in well_comp.columns and well_comp[s].notna().all()
        ]
        marker_row: dict[str, float] = {}
        if well_sands:
            marker_row = {s: float(well_comp.at[0, s]) for s in well_sands}

        well_prod_mask = prod["WELL"] == uwi
        well_prod_idx = prod.index[well_prod_mask].tolist()

        for prod_idx in well_prod_idx:
            prod_date = prod.at[prod_idx, "DATE"]

            PF: list[list[str]] = []
            SF: list[list[str]] = []
            TP: list[float] = []
            BP: list[float] = []
            TS: list[float] = []
            BS: list[float] = []
            PD: list[Any] = []
            SD: list[Any] = []

            for ci in range(len(well_comp)):
                if not _date_lte(prod_date, well_comp.at[ci, "DATE"]):
                    break

                status = well_comp.at[ci, "Perf Status"]
                marker_val = well_comp.at[ci, "MARKER"]
                if not isinstance(marker_val, list) or len(marker_val) == 0:
                    continue

                if status == "perforation":
                    PF.append(marker_val)
                    TP.append(float(well_comp.at[ci, "Perf Top (ftMD)"]))
                    BP.append(float(well_comp.at[ci, "Perf Base (ftMD)"]))
                    PD.append(well_comp.at[ci, "DATE"])
                elif status == "squeeze":
                    SF.append(marker_val)
                    TS.append(float(well_comp.at[ci, "Perf Top (ftMD)"]))
                    BS.append(float(well_comp.at[ci, "Perf Base (ftMD)"]))
                    SD.append(well_comp.at[ci, "DATE"])

            if SF:
                squeeze_machine(TP, BP, PF, PD, TS, BS, SF, SD, marker_row)

            open_sands: dict[str, int] = {}
            for s in global_sands:
                count = sum(1 for perf_sands in PF if s in perf_sands)
                open_sands[s] = count

            for s, cnt in open_sands.items():
                if cnt > 0:
                    prod.at[prod_idx, s] = "p"

    return MarkerResult(markered_production=prod, warnings=warnings)
