"""Tests for marker_engine.py — TOP_WAY / BOTTOM_WAY assignment,
first-marker tolerance, marker resolution, squeeze machine, and the
full auto_marker pipeline.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from app.services.marker_engine import (
    MarkerResult,
    _assign_way,
    assign_markers,
    assign_ways,
    auto_marker,
    resolve_marker,
    squeeze_machine,
)


SANDS = ["T_TE600", "T_TE1000", "T_BT1100", "T_PM2300"]


# ── _assign_way ──────────────────────────────────────────────────────────────

class TestAssignWay:
    """Unit tests for the low-level _assign_way helper."""

    def _depths(self) -> dict[str, float]:
        return {"T_TE600": 1000, "T_TE1000": 1400, "T_BT1100": 1800}

    def test_depth_between_markers(self):
        result = _assign_way(1200, self._depths(), ["T_TE600", "T_TE1000", "T_BT1100"], SANDS, 10)
        assert result == "T_TE600"

    def test_depth_at_marker(self):
        result = _assign_way(1400, self._depths(), ["T_TE600", "T_TE1000", "T_BT1100"], SANDS, 10)
        assert result == "T_TE1000"

    def test_depth_below_last(self):
        result = _assign_way(2000, self._depths(), ["T_TE600", "T_TE1000", "T_BT1100"], SANDS, 10)
        assert result == "T_BT1100"

    def test_depth_above_first_within_tolerance(self):
        """Perf top is 5ft shallower than T_TE600 (marker MD=1000).
        With tolerance=10, it should snap to T_TE600."""
        result = _assign_way(995, self._depths(), ["T_TE600", "T_TE1000", "T_BT1100"], SANDS, 10)
        assert result == "T_TE600"

    def test_depth_above_first_exceeds_tolerance(self):
        """Perf top is 50ft above T_TE600 → should fall to the sand *before*
        T_TE600 in the global list. But T_TE600 is already at index 0, so we
        still get T_TE600 (no negative index)."""
        result = _assign_way(950, self._depths(), ["T_TE600", "T_TE1000", "T_BT1100"], SANDS, 10)
        # T_TE600 is the first sand globally, so index-1 would be negative → stays at T_TE600.
        # If there was a sand before T_TE600, it would return that instead.
        assert result == "T_TE600"  # it's the global first so no prior exists

    def test_depth_above_first_with_prior_global(self):
        """If the well only has T_TE1000 and T_BT1100, and perf is above
        T_TE1000 beyond tolerance, it should return T_TE600 (the prior global sand)."""
        depths = {"T_TE1000": 1400, "T_BT1100": 1800}
        result = _assign_way(1350, depths, ["T_TE1000", "T_BT1100"], SANDS, 10)
        assert result == "T_TE600"

    def test_single_sand(self):
        result = _assign_way(1100, {"T_TE1000": 1400}, ["T_TE1000"], SANDS, 10)
        # 1100 < 1400 and diff = 300 > tolerance → fall back to T_TE600
        assert result == "T_TE600"

    def test_single_sand_at_marker(self):
        result = _assign_way(1400, {"T_TE1000": 1400}, ["T_TE1000"], SANDS, 10)
        assert result == "T_TE1000"

    def test_user_scenario_perf_98_to_109_resolves_to_first_marker(self):
        """User scenario: markers A=100, B=110, C=150 with perf 98-109.

        - Top=98 is 2 ft above A (within tolerance) → snaps to A.
        - Base=109 is 1 ft above B → falls back to the previous zone (A).
        - Resolved MARKER list must therefore be just ["A"].
        """
        sands_global = ["A", "B", "C"]
        depths = {"A": 100.0, "B": 110.0, "C": 150.0}

        top = _assign_way(98, depths, sands_global, sands_global, tolerance_ft=10)
        base = _assign_way(109, depths, sands_global, sands_global, tolerance_ft=10)
        assert top == "A"
        assert base == "A"
        assert resolve_marker(top, base, sands_global, sands_global) == ["A"]

    def test_user_scenario_outside_tolerance_falls_through(self):
        """If top is 20 ft above the first marker (tolerance=10), it must NOT
        snap. Falls through to the global zone before A — none here, so stays
        at A as a no-op fallback (no negative index)."""
        sands_global = ["A", "B", "C"]
        depths = {"A": 100.0, "B": 110.0, "C": 150.0}
        top = _assign_way(80, depths, sands_global, sands_global, tolerance_ft=10)
        assert top == "A"  # A is global[0], so prior is unavailable

    def test_perf_spans_multiple_zones(self):
        """Perf 105 → 145 should cover zones A and B (105 in A, 145 in B)."""
        sands_global = ["A", "B", "C"]
        depths = {"A": 100.0, "B": 110.0, "C": 150.0}
        top = _assign_way(105, depths, sands_global, sands_global, tolerance_ft=10)
        base = _assign_way(145, depths, sands_global, sands_global, tolerance_ft=10)
        assert top == "A"
        assert base == "B"
        assert resolve_marker(top, base, sands_global, sands_global) == ["A", "B"]


# ── assign_ways (full DataFrame) ────────────────────────────────────────────

class TestAssignWays:

    def _make_comp(self) -> pd.DataFrame:
        return pd.DataFrame({
            "WELL": ["W-01", "W-01"],
            "DATE": [datetime(2025, 1, 1), datetime(2025, 3, 1)],
            "Perf Status": ["perforation", "perforation"],
            "Perf Top (ftMD)": [995, 1600],
            "Perf Base (ftMD)": [1500, 1900],
            "T_TE600": [1000, 1000],
            "T_TE1000": [1400, 1400],
            "T_BT1100": [1800, 1800],
        })

    def test_assigns_top_and_bottom(self):
        comp = self._make_comp()
        result = assign_ways(comp, SANDS, tolerance_ft=10)
        assert "TOP_WAY" in result.columns
        assert "BOTTOM_WAY" in result.columns
        # Row 0: top=995, within 5ft tolerance of T_TE600 (1000)
        assert result.at[0, "TOP_WAY"] == "T_TE600"
        assert result.at[0, "BOTTOM_WAY"] == "T_TE1000"


# ── resolve_marker ───────────────────────────────────────────────────────────

class TestResolveMarker:

    def test_same_way(self):
        result = resolve_marker("T_TE600", "T_TE600", ["T_TE600", "T_TE1000"], SANDS)
        assert result == ["T_TE600"]

    def test_range_across_sands(self):
        result = resolve_marker("T_TE600", "T_BT1100", ["T_TE600", "T_TE1000", "T_BT1100"], SANDS)
        assert result == ["T_TE600", "T_TE1000", "T_BT1100"]

    def test_fallback_to_global(self):
        result = resolve_marker("T_TE600", "T_BT1100", ["T_TE1000"], SANDS)
        assert result == ["T_TE600", "T_TE1000", "T_BT1100"]


# ── squeeze_machine ─────────────────────────────────────────────────────────

class TestSqueezeMachine:

    def test_full_squeeze_removes_perforation(self):
        tp = [1000.0]
        bp = [1500.0]
        pf = [["T_TE600", "T_TE1000"]]
        pd_dates = [datetime(2025, 1, 1)]
        ts = [1000.0]
        bs = [1500.0]
        sf = [["T_TE600", "T_TE1000"]]
        sd_dates = [datetime(2025, 3, 1)]
        marker_row = {"T_TE600": 1000, "T_TE1000": 1400}

        squeeze_machine(tp, bp, pf, pd_dates, ts, bs, sf, sd_dates, marker_row)
        assert len(pf) == 0
        assert len(tp) == 0

    def test_partial_squeeze_from_top(self):
        tp = [1000.0]
        bp = [1800.0]
        pf = [["T_TE600", "T_TE1000", "T_BT1100"]]
        pd_dates = [datetime(2025, 1, 1)]
        ts = [1000.0]
        bs = [1400.0]
        sf = [["T_TE600"]]
        sd_dates = [datetime(2025, 3, 1)]
        marker_row = {"T_TE600": 1000, "T_TE1000": 1400, "T_BT1100": 1800}

        squeeze_machine(tp, bp, pf, pd_dates, ts, bs, sf, sd_dates, marker_row)
        assert tp[0] == 1400.0  # top moved down
        assert "T_TE600" not in pf[0]

    def test_partial_squeeze_from_bottom(self):
        tp = [1000.0]
        bp = [1800.0]
        pf = [["T_TE600", "T_TE1000", "T_BT1100"]]
        pd_dates = [datetime(2025, 1, 1)]
        ts = [1400.0]
        bs = [1800.0]
        sf = [["T_BT1100"]]
        sd_dates = [datetime(2025, 3, 1)]
        marker_row = {"T_TE600": 1000, "T_TE1000": 1400, "T_BT1100": 1800}

        squeeze_machine(tp, bp, pf, pd_dates, ts, bs, sf, sd_dates, marker_row)
        assert bp[0] == 1400.0  # bottom moved up
        assert "T_BT1100" not in pf[0]


# ── auto_marker (integration) ───────────────────────────────────────────────

class TestAutoMarker:

    def _make_data(self):
        completion = pd.DataFrame({
            "WELL": ["W-01", "W-01"],
            "DATE": [datetime(2025, 1, 1), datetime(2025, 6, 1)],
            "Perf Status": ["perforation", "squeeze"],
            "Perf Top (ftMD)": [998, 998],
            "Perf Base (ftMD)": [1500, 1200],
            "T_TE600": [1000, 1000],
            "T_TE1000": [1400, 1400],
        })
        production = pd.DataFrame({
            "WELL": ["W-01", "W-01", "W-01"],
            "DATE": [datetime(2025, 2, 1), datetime(2025, 4, 1), datetime(2025, 8, 1)],
            "OIL": [100, 200, 150],
            "WATER": [50, 60, 40],
        })
        return completion, production

    def test_basic_auto_marker(self):
        comp, prod = self._make_data()
        sands = ["T_TE600", "T_TE1000"]
        result = auto_marker(prod, comp, sands, tolerance_ft=10)

        assert isinstance(result, MarkerResult)
        df = result.markered_production

        # Before squeeze (Feb, Apr): both T_TE600 and T_TE1000 should be "p"
        assert df.at[0, "T_TE600"] == "p"
        assert df.at[0, "T_TE1000"] == "p"
        assert df.at[1, "T_TE600"] == "p"
        assert df.at[1, "T_TE1000"] == "p"

        # After squeeze (Aug): squeeze at top removed T_TE600, only T_TE1000 open
        assert df.at[2, "T_TE1000"] == "p"

    def test_tolerance_snaps_to_first_marker(self):
        """Perf top = 998 with T_TE600 at 1000 → within 2ft tolerance."""
        comp, prod = self._make_data()
        sands = ["T_TE600", "T_TE1000"]
        result = auto_marker(prod, comp, sands, tolerance_ft=10)
        df = result.markered_production
        assert df.at[0, "T_TE600"] == "p"

    def test_missing_well_gives_warning(self):
        comp, prod = self._make_data()
        prod_extra = pd.concat([
            prod,
            pd.DataFrame({
                "WELL": ["W-99"],
                "DATE": [datetime(2025, 1, 1)],
                "OIL": [10],
                "WATER": [5],
            }),
        ], ignore_index=True)
        result = auto_marker(prod_extra, comp, ["T_TE600", "T_TE1000"], tolerance_ft=10)
        assert any("W-99" in w for w in result.warnings)
