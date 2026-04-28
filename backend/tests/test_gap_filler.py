"""Tests for gap_filler.py — leading / trailing auto-fill and middle gap
detection + interactive resolution.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.gap_filler import (
    FillStrategy,
    GapResolution,
    apply_resolutions,
    detect_gaps,
)


SANDS = ["S1", "S2", "S3"]


def _make_df() -> pd.DataFrame:
    """Build a simple markered production DataFrame with known gap patterns.

    Rows 0-7 for well W-01, sand S1:
      - rows 0-1: blank (leading gap)
      - rows 2-3: "p"
      - row  4:   blank (middle gap)
      - rows 5-6: "p"
      - row  7:   blank (trailing gap)
    """
    return pd.DataFrame({
        "WELL": ["W-01"] * 8,
        "DATE": pd.date_range("2025-01-01", periods=8, freq="MS"),
        "OIL": [100] * 8,
        "S1": [pd.NA, pd.NA, "p", "p", pd.NA, "p", "p", pd.NA],
        "S2": ["p"] * 8,  # no gaps
        "S3": [pd.NA] * 8,  # entirely blank → no gap (no "p" at all)
    })


class TestDetectGaps:

    def test_auto_fills_leading_and_trailing(self):
        df = _make_df()
        filled, report = detect_gaps(df, SANDS)

        # Leading gap rows 0-1 should be bfilled with "p" (from row 2)
        assert filled.at[0, "S1"] == "p"
        assert filled.at[1, "S1"] == "p"

        # Trailing gap row 7 should be ffilled with "p" (from row 6)
        assert filled.at[7, "S1"] == "p"

        # Middle gap row 4 should remain blank (not auto-filled)
        assert pd.isna(filled.at[4, "S1"])

    def test_reports_correct_gap_counts(self):
        df = _make_df()
        _, report = detect_gaps(df, SANDS)

        assert len(report.auto_filled) == 2  # 1 leading + 1 trailing
        assert len(report.middle_gaps) == 1

        middle = report.middle_gaps[0]
        assert middle.well == "W-01"
        assert middle.sand == "S1"
        assert middle.start_row == 4
        assert middle.end_row == 4

    def test_no_gaps_when_all_p(self):
        df = _make_df()
        _, report = detect_gaps(df, ["S2"])
        assert len(report.auto_filled) == 0
        assert len(report.middle_gaps) == 0

    def test_no_gaps_when_entirely_blank(self):
        df = _make_df()
        _, report = detect_gaps(df, ["S3"])
        assert len(report.auto_filled) == 0
        assert len(report.middle_gaps) == 0


class TestApplyResolutions:

    def test_bfill_middle_gap(self):
        df = _make_df()
        filled, report = detect_gaps(df, SANDS)

        resolutions = [
            GapResolution(
                well="W-01", sand="S1",
                start_row=4, end_row=4,
                strategy=FillStrategy.BFILL,
            ),
        ]
        result = apply_resolutions(filled, resolutions)
        assert result.at[4, "S1"] == "p"

    def test_ffill_middle_gap(self):
        df = _make_df()
        filled, report = detect_gaps(df, SANDS)

        resolutions = [
            GapResolution(
                well="W-01", sand="S1",
                start_row=4, end_row=4,
                strategy=FillStrategy.FFILL,
            ),
        ]
        result = apply_resolutions(filled, resolutions)
        assert result.at[4, "S1"] == "p"

    def test_manual_fill_middle_gap(self):
        df = _make_df()
        filled, report = detect_gaps(df, SANDS)

        resolutions = [
            GapResolution(
                well="W-01", sand="S1",
                start_row=4, end_row=4,
                strategy=FillStrategy.MANUAL,
                manual_value="custom_val",
            ),
        ]
        result = apply_resolutions(filled, resolutions)
        assert result.at[4, "S1"] == "custom_val"

    def test_multi_row_middle_gap(self):
        """Create a wider middle gap spanning rows 4-5."""
        df = pd.DataFrame({
            "WELL": ["W-01"] * 9,
            "DATE": pd.date_range("2025-01-01", periods=9, freq="MS"),
            "OIL": [100] * 9,
            "S1": ["p", "p", "p", pd.NA, pd.NA, pd.NA, "p", "p", "p"],
        })
        filled, report = detect_gaps(df, ["S1"])
        assert len(report.middle_gaps) == 1
        mg = report.middle_gaps[0]
        assert mg.start_row == 3
        assert mg.end_row == 5

        resolutions = [
            GapResolution(
                well="W-01", sand="S1",
                start_row=3, end_row=5,
                strategy=FillStrategy.FFILL,
            ),
        ]
        result = apply_resolutions(filled, resolutions)
        for r in [3, 4, 5]:
            assert result.at[r, "S1"] == "p"
