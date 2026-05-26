"""
engine.py — Oil Splitter processing engine.

Full pipeline:
  1. Auto-marker  : classify each perforation interval into sand zone(s)
                    using depth-based lookup against the marker table.
  2. Squeeze      : walk the production timeline well-by-well, accumulating
                    open perforations and removing them as squeeze events occur.
  3. Split        : distribute well-level OIL/WATER/GAS/WINJ across sand zones
                    proportional to kh weights from the lumping table.
  4. Summary      : aggregate cumulative volumes per sand zone.

Input files (any mix of CSV / XLSX):
  - marker      : columns [Well, Surface, MD]
  - completion  : columns [WELL, DATE, Perf Status, Perf Top (ftMD), Perf Base (ftMD)]
  - sand        : column  [Marker]  — ordered list of zone names top → bottom
  - production  : columns [WELL, DATE, OIL, WATER, GAS, WINJ]
  - lumping     : index="Zone log" (sand names), columns=well names, values=kh weights
"""

import copy
import logging
import warnings
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ── helpers ────────────────────────────────────────────────────────────────────

def _read_file(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def load_inputs(
    marker_path: str,
    completion_path: str,
    sand_path: str,
    production_path: str,
    lumping_path: str,
) -> Dict[str, pd.DataFrame]:
    return {
        "marker":     _read_file(marker_path),
        "completion": _read_file(completion_path),
        "sand":       _read_file(sand_path),
        "production": _read_file(production_path),
        "lumping":    _read_file(lumping_path),
    }


# ── Phase 1: Auto-marker ───────────────────────────────────────────────────────

def _classify_perf(
    perf_depth: float, sand_list: List[str], row: pd.Series
) -> Optional[str]:
    """Return which sand zone a single depth value falls into."""
    if pd.isna(perf_depth):
        return None
    for i, sand in enumerate(sand_list):
        sand_top = row.get(sand)
        if sand_top is None or pd.isna(sand_top):
            continue
        if i + 1 < len(sand_list):
            sand_next = row.get(sand_list[i + 1])
            if sand_next is not None and not pd.isna(sand_next):
                if float(sand_top) <= float(perf_depth) < float(sand_next):
                    return sand
            else:
                if float(perf_depth) >= float(sand_top):
                    return sand
        else:
            if float(perf_depth) >= float(sand_top):
                return sand
    return None


def _get_marker(
    top_val: Optional[str], bottom_val: Optional[str], sand_list: List[str]
) -> Optional[List[str]]:
    """Return the sand_list slice between top and bottom classification."""
    if top_val is None or bottom_val is None:
        return None
    if top_val not in sand_list or bottom_val not in sand_list:
        return None
    i_top    = sand_list.index(top_val)
    i_bottom = sand_list.index(bottom_val)
    if i_top > i_bottom:
        i_top, i_bottom = i_bottom, i_top
    return sand_list[i_top: i_bottom + 1]


def run_automarker(
    marker_df: pd.DataFrame,
    completion_df: pd.DataFrame,
    sand_list: List[str],
) -> pd.DataFrame:
    """
    Merge marker depths into completion events and classify each perforation
    interval into its sand zone(s).

    Returns completion_df enriched with TOP_WAY, BOTTOM_WAY, MARKER columns.
    """
    marker_pivot = (
        pd.pivot_table(marker_df, index="Well", columns="Surface", values="MD")
        .reset_index()
        .rename_axis(None, axis=1)
    )

    perfo = completion_df.merge(
        marker_pivot, how="left", left_on="WELL", right_on="Well"
    )

    base_cols    = ["WELL", "DATE", "Perf Status", "Perf Top (ftMD)", "Perf Base (ftMD)"]
    present_sand = [s for s in sand_list if s in perfo.columns]
    perfo        = perfo[base_cols + present_sand].copy()

    top_way, bottom_way, marker_result = {}, {}, {}

    for well in perfo["WELL"].unique():
        temp = perfo[perfo["WELL"] == well].copy()
        temp = temp.dropna(axis=1, how="all")
        well_sands = [s for s in sand_list if s in temp.columns]
        if not well_sands:
            continue

        for idx, row in temp.iterrows():
            top_val    = _classify_perf(row["Perf Top (ftMD)"],  well_sands, row)
            bottom_val = _classify_perf(row["Perf Base (ftMD)"], well_sands, row)
            marker     = _get_marker(top_val, bottom_val, well_sands)

            top_way[idx]       = top_val
            bottom_way[idx]    = bottom_val
            marker_result[idx] = marker

    perfo["TOP_WAY"]    = perfo.index.map(top_way)
    perfo["BOTTOM_WAY"] = perfo.index.map(bottom_way)
    perfo["MARKER"]     = perfo.index.map(marker_result)
    return perfo


# ── Phase 2: Squeeze machine ───────────────────────────────────────────────────

def _build_marker_lookup(tempmarker: pd.DataFrame) -> Dict[str, float]:
    """Build {sand_name: top_depth} from first row, used in squeeze boundary checks."""
    skip = {
        "WELL", "Well", "DATE", "Perf Status",
        "Perf Top (ftMD)", "Perf Base (ftMD)",
        "TOP_WAY", "BOTTOM_WAY", "MARKER",
    }
    row0 = tempmarker.iloc[0]
    return {
        col: float(row0[col])
        for col in tempmarker.columns
        if col not in skip and not pd.isna(row0.get(col, np.nan))
    }


def _squeeze_machine(
    tp: list, bp: list, pf: list, pd_: list,
    ts: list, bs: list, sf: list, sd: list,
    marker_lookup: Dict[str, float],
) -> tuple:
    """
    Mutate perforation lists in-place to account for squeeze events.
    Faithful port of the notebook squeeze logic with index-safety guards.
    """
    for a in range(len(sd)):
        b = 0
        while b < len(pd_):
            if sd[a] >= pd_[b]:
                sq_inside_pf = ts[a] <= tp[b] and bs[a] >= bp[b]
                top_match    = ts[a] == tp[b]
                bottom_match = bs[a] == bp[b]

                if sq_inside_pf:
                    del pf[b], tp[b], bp[b], pd_[b]
                    continue  # b unchanged — next element shifted down

                if top_match and bs[a] < bp[b]:
                    tp[b] = bs[a]
                    n_sf, n_pf = len(sf[a]), len(pf[b])
                    if n_pf == n_sf:
                        pf[b] = [pf[b][-1]]
                    elif n_pf > n_sf:
                        pivot = pf[b][n_sf] if n_sf < len(pf[b]) else None
                        depth = marker_lookup.get(pivot) if pivot else None
                        if depth is not None and tp[b] < depth:
                            pf[b] = [pf[b][n_sf - 1]] + [x for x in pf[b] if x not in sf[a]]
                        else:
                            pf[b] = [x for x in pf[b] if x not in sf[a]]

                elif bottom_match and ts[a] > tp[b]:
                    bp[b] = ts[a]
                    n_sf, n_pf = len(sf[a]), len(pf[b])
                    if n_pf == n_sf:
                        pf[b] = [pf[b][0]]
                    elif n_pf > n_sf:
                        pivot = pf[b][n_sf] if n_sf < len(pf[b]) else None
                        depth = marker_lookup.get(pivot) if pivot else None
                        if depth is not None and bp[b] > depth:
                            pf[b] = [pf[b][n_sf]] + [x for x in pf[b] if x not in sf[a]]
                        else:
                            pf[b] = [x for x in pf[b] if x not in sf[a]]
            b += 1

    return tp, bp, pf


def _count_perforated_sands(pf: list, all_sands: List[str]) -> Dict[str, int]:
    """Count how many open perforation intervals cover each sand — O(total markers)."""
    counts = {s: 0 for s in all_sands}
    for zone_list in pf:
        if not zone_list:
            continue
        for s in zone_list:
            if s in counts:
                counts[s] += 1
    return counts


def run_squeeze(
    perfo_marked: pd.DataFrame,
    production_df: pd.DataFrame,
    sand_list: List[str],
    log_fn: Optional[Callable] = None,
) -> pd.DataFrame:
    """
    Walk the production timeline for each well, accumulating perforation events
    and applying squeeze logic. Returns production_df annotated with 'p' markers
    for each perforated sand at each time step.
    """
    def _log(msg):
        logger.debug(msg)
        if log_fn:
            log_fn(msg)

    marker = perfo_marked.copy()
    marker["DATE"] = pd.to_datetime(marker["DATE"])
    marker = marker.sort_values(["WELL", "DATE"])

    prod = production_df.copy()
    prod["DATE"] = pd.to_datetime(prod["DATE"])

    for s in sand_list:
        if s not in prod.columns:
            prod[s] = pd.array([None] * len(prod), dtype=object)
        else:
            prod[s] = prod[s].astype(object)

    result_frames: List[pd.DataFrame] = []

    for uwi in prod["WELL"].unique():
        well_mask = marker["WELL"] == uwi
        has_marker = well_mask.any() and marker.loc[well_mask, "MARKER"].notna().any()

        temp_prod = prod[prod["WELL"] == uwi].reset_index(drop=True).copy()

        if not has_marker:
            _log(f"[{uwi}] No marker data — skipping squeeze.")
            result_frames.append(temp_prod)
            continue

        tempmarker = (
            marker[well_mask]
            .dropna(axis=1, how="all")
            .reset_index(drop=True)
        )
        marker_lookup = _build_marker_lookup(tempmarker)

        perf_rows = tempmarker[tempmarker["Perf Status"] == "perforation"].reset_index(drop=True)
        sq_rows   = tempmarker[tempmarker["Perf Status"] == "squeeze"].reset_index(drop=True)

        perf_ptr = sq_ptr = 0
        PF: list = []
        TP: list = []
        BP: list = []
        PD: list = []
        SF: list = []
        TS: list = []
        BS: list = []
        SD: list = []

        for index, prod_row in temp_prod.iterrows():
            prod_date = prod_row["DATE"]
            changed   = False

            while perf_ptr < len(perf_rows):
                r      = perf_rows.iloc[perf_ptr]
                r_date = r["DATE"]
                in_window = (
                    prod_date.year > r_date.year or
                    (prod_date.year == r_date.year and prod_date.month >= r_date.month)
                )
                if in_window:
                    mval = r["MARKER"]
                    if isinstance(mval, list) and len(mval) > 0:
                        PF.append(copy.copy(mval))
                        TP.append(float(r["Perf Top (ftMD)"]))
                        BP.append(float(r["Perf Base (ftMD)"]))
                        PD.append(r_date)
                        changed = True
                    perf_ptr += 1
                else:
                    break

            while sq_ptr < len(sq_rows):
                r      = sq_rows.iloc[sq_ptr]
                r_date = r["DATE"]
                in_window = (
                    prod_date.year > r_date.year or
                    (prod_date.year == r_date.year and prod_date.month >= r_date.month)
                )
                if in_window:
                    mval = r["MARKER"]
                    if isinstance(mval, list) and len(mval) > 0:
                        SF.append(copy.copy(mval))
                        TS.append(float(r["Perf Top (ftMD)"]))
                        BS.append(float(r["Perf Base (ftMD)"]))
                        SD.append(r_date)
                        changed = True
                    sq_ptr += 1
                else:
                    break

            if changed and SF:
                _squeeze_machine(TP, BP, PF, PD, TS, BS, SF, SD, marker_lookup)

            counts = _count_perforated_sands(PF, sand_list)
            for sand, cnt in counts.items():
                if cnt > 0:
                    temp_prod.at[index, sand] = "p"

            _log(f"[{uwi}] row={index} | perf_ptr={perf_ptr} | open={len(PF)}")

        result_frames.append(temp_prod)

    return pd.concat(result_frames, ignore_index=True) if result_frames else prod


# ── Phase 3: Splitting machine ─────────────────────────────────────────────────

def run_splitting(
    marked_production: pd.DataFrame,
    lumping_df: pd.DataFrame,
    sand_list: List[str],
    fluid_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Distribute well-level fluid volumes across sand zones using kh weights.

    marked_production : output of run_squeeze() — has 'p' markers per sand column
    lumping_df        : index="Zone log" (sand names), columns=well names, values=kh
    fluid_cols        : which columns to split (default auto-detect OIL/WATER/GAS/WINJ)
    """
    if "Zone log" in lumping_df.columns:
        lumping_df = lumping_df.set_index("Zone log")

    if fluid_cols is None:
        fluid_cols = [c for c in ["OIL", "WATER", "GAS", "WINJ"] if c in marked_production.columns]

    non_sand_cols = [c for c in marked_production.columns if c not in sand_list]
    df = marked_production[non_sand_cols].copy()

    for s in sand_list:
        for fluid in fluid_cols:
            df[f"{fluid}_{s}"] = np.nan

    for row_idx, row in marked_production.iterrows():
        well = str(row.get("WELL", ""))
        if well not in lumping_df.columns:
            for s in sand_list:
                for fluid in fluid_cols:
                    df.at[row_idx, f"{fluid}_{s}"] = 0.0
            continue

        well_kh  = lumping_df[well]
        total_kh = 0.0

        for s in sand_list:
            if row.get(s) == "p":
                kh_val = well_kh.get(s, np.nan)
                if not pd.isna(kh_val):
                    total_kh += float(kh_val)

        for s in sand_list:
            kh_val = well_kh.get(s, np.nan)
            perf   = row.get(s) == "p"

            for fluid in fluid_cols:
                if total_kh > 0 and perf and not pd.isna(kh_val):
                    raw = row.get(fluid, 0)
                    val = float(raw if not pd.isna(raw) else 0) * float(kh_val) / total_kh
                else:
                    val = 0.0
                df.at[row_idx, f"{fluid}_{s}"] = val

    return df


# ── Phase 4: Summary ───────────────────────────────────────────────────────────

def run_summary(split_df: pd.DataFrame, sand_list: List[str]) -> pd.DataFrame:
    """Aggregate cumulative split volumes per sand zone."""
    rows = []
    for s in sand_list:
        row = {"Sand": s}
        for fluid in ["OIL", "WATER", "GAS", "WINJ"]:
            cols = [c for c in split_df.columns if c == f"{fluid}_{s}"]
            row[fluid] = float(split_df[cols].sum().sum()) if cols else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


# ── Main entry point ───────────────────────────────────────────────────────────

def run_engine(
    marker_path: str,
    completion_path: str,
    sand_path: str,
    production_path: str,
    lumping_path: str,
    output_path: str,
    log_fn: Optional[Callable] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Execute the full auto-marker → squeeze → split → summary pipeline.

    Writes a multi-sheet Excel file to output_path.
    Returns dict with keys: 'split', 'summary', 'marked_production'.
    """
    def _log(msg: str):
        logger.info(msg)
        if log_fn:
            log_fn(msg)

    _log("Loading input files...")
    inputs = load_inputs(
        marker_path, completion_path, sand_path, production_path, lumping_path
    )

    marker_df     = inputs["marker"]
    completion_df = inputs["completion"]
    sand_list     = inputs["sand"]["Marker"].dropna().tolist()
    production_df = inputs["production"]
    lumping_df    = inputs["lumping"]

    _log(f"  Wells in production : {production_df['WELL'].nunique()}")
    _log(f"  Sand zones          : {len(sand_list)}")
    _log(f"  Completion events   : {len(completion_df)}")

    _log("Phase 1 — Auto-marker...")
    perfo_marked = run_automarker(marker_df, completion_df, sand_list)
    _log(f"  Classified {len(perfo_marked)} completion events.")

    _log("Phase 2 — Squeeze machine...")
    marked_production = run_squeeze(perfo_marked, production_df, sand_list, log_fn=log_fn)
    _log(f"  Annotated {len(marked_production)} production rows.")

    _log("Phase 3 — Splitting machine...")
    split_df = run_splitting(marked_production, lumping_df, sand_list)
    _log(f"  Generated {len(split_df.columns)} output columns.")

    _log("Phase 4 — Summary...")
    summary_df = run_summary(split_df, sand_list)

    _log(f"Writing output → {output_path}")
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        split_df.to_excel(writer, sheet_name="Split Production", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        marked_production.to_excel(writer, sheet_name="Marked Production", index=False)

    _log("Engine complete.")
    return {
        "split":              split_df,
        "summary":            summary_df,
        "marked_production":  marked_production,
    }
