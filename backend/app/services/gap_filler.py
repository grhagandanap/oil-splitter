"""Gap filler — detects and fills missing "p" patterns in markered production.

Three gap categories:

1. **Leading gaps** (blank at the *start* of a well's time series before the
   first ``"p"``): auto-filled with ``bfill`` (copy from the first non-blank
   period forward).
2. **Trailing gaps** (blank at the *end* after the last ``"p"``): auto-filled
   with ``ffill`` (carry the last non-blank period forward).
3. **Middle gaps** (blanks sandwiched between two periods that have ``"p"``):
   returned to the caller for interactive user resolution (``bfill``,
   ``ffill``, or manual value).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class FillStrategy(str, Enum):
    BFILL = "bfill"
    FFILL = "ffill"
    MANUAL = "manual"


@dataclass
class GapSpan:
    """Describes a contiguous run of blank rows for one sand column in one well."""

    well: str
    sand: str
    start_row: int
    end_row: int
    position: str  # "leading", "trailing", or "middle"


@dataclass
class GapReport:
    """Returned by ``detect_gaps`` so the caller knows what remains unresolved."""

    auto_filled: list[GapSpan] = field(default_factory=list)
    middle_gaps: list[GapSpan] = field(default_factory=list)


@dataclass
class GapResolution:
    """User's chosen strategy for a single middle gap."""

    well: str
    sand: str
    start_row: int
    end_row: int
    strategy: FillStrategy
    manual_value: str | None = None  # only used when strategy == MANUAL


# ── Core detection ───────────────────────────────────────────────────────────

def _find_gaps(series: pd.Series) -> list[tuple[int, int, str]]:
    """Return ``(start_idx, end_idx, position)`` tuples for blank runs.

    ``series`` uses the DataFrame's positional index (0-based within the
    well's slice).
    """
    n = len(series)
    if n == 0:
        return []

    is_p = series.apply(lambda v: v == "p" if pd.notna(v) else False).tolist()

    first_p = None
    last_p = None
    for i, val in enumerate(is_p):
        if val:
            if first_p is None:
                first_p = i
            last_p = i

    if first_p is None:
        return []

    gaps: list[tuple[int, int, str]] = []

    # leading gap
    if first_p > 0:
        gaps.append((0, first_p - 1, "leading"))

    # trailing gap
    if last_p is not None and last_p < n - 1:
        gaps.append((last_p + 1, n - 1, "trailing"))

    # middle gaps
    in_gap = False
    gap_start = 0
    for i in range(first_p, (last_p or 0) + 1):
        if not is_p[i]:
            if not in_gap:
                in_gap = True
                gap_start = i
        else:
            if in_gap:
                gaps.append((gap_start, i - 1, "middle"))
                in_gap = False

    return gaps


# ── Public API ───────────────────────────────────────────────────────────────

def detect_gaps(
    df: pd.DataFrame,
    sands: list[str],
) -> tuple[pd.DataFrame, GapReport]:
    """Scan the markered production DataFrame for blank "p" gaps.

    Leading and trailing gaps are auto-filled *in-place* on the returned
    DataFrame copy.  Middle gaps are reported but **not** filled — the caller
    must collect user input via ``apply_resolutions``.

    Returns ``(filled_df, report)``.
    """
    result = df.copy()
    report = GapReport()

    for well in result["WELL"].unique():
        mask = result["WELL"] == well
        idxs = result.index[mask].tolist()
        if not idxs:
            continue

        for sand in sands:
            if sand not in result.columns:
                continue

            well_series = result.loc[idxs, sand].reset_index(drop=True)
            gaps = _find_gaps(well_series)

            for start_pos, end_pos, position in gaps:
                abs_start = idxs[start_pos]
                abs_end = idxs[end_pos]
                span = GapSpan(
                    well=str(well),
                    sand=sand,
                    start_row=abs_start,
                    end_row=abs_end,
                    position=position,
                )

                if position == "leading":
                    # bfill: copy from the row just after the gap
                    after = idxs[end_pos + 1] if end_pos + 1 < len(idxs) else None
                    if after is not None:
                        fill_val = result.at[after, sand]
                        for r in idxs[start_pos : end_pos + 1]:
                            result.at[r, sand] = fill_val
                    report.auto_filled.append(span)

                elif position == "trailing":
                    # ffill: copy from the row just before the gap
                    before = idxs[start_pos - 1] if start_pos > 0 else None
                    if before is not None:
                        fill_val = result.at[before, sand]
                        for r in idxs[start_pos : end_pos + 1]:
                            result.at[r, sand] = fill_val
                    report.auto_filled.append(span)

                else:
                    report.middle_gaps.append(span)

    return result, report


def apply_resolutions(
    df: pd.DataFrame,
    resolutions: list[GapResolution],
) -> pd.DataFrame:
    """Apply user-chosen strategies for middle gaps.

    Parameters
    ----------
    df : DataFrame
        The DataFrame previously returned by ``detect_gaps`` (with leading
        and trailing gaps already filled).
    resolutions : list[GapResolution]
        One entry per middle gap returned in the ``GapReport``.

    Returns
    -------
    DataFrame with all middle gaps resolved.
    """
    result = df.copy()

    for res in resolutions:
        well_mask = result["WELL"] == res.well
        idxs = result.index[well_mask].tolist()
        gap_idxs = [i for i in idxs if res.start_row <= i <= res.end_row]

        if not gap_idxs:
            continue

        if res.strategy == FillStrategy.BFILL:
            after_idx = res.end_row + 1
            fill_val = result.at[after_idx, res.sand] if after_idx in result.index else None
            if fill_val is not None:
                for r in gap_idxs:
                    result.at[r, res.sand] = fill_val

        elif res.strategy == FillStrategy.FFILL:
            before_idx = res.start_row - 1
            fill_val = result.at[before_idx, res.sand] if before_idx in result.index else None
            if fill_val is not None:
                for r in gap_idxs:
                    result.at[r, res.sand] = fill_val

        elif res.strategy == FillStrategy.MANUAL:
            for r in gap_idxs:
                result.at[r, res.sand] = res.manual_value

    return result
