"""Tests for splitter_engine.py — KH-weighted allocation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.splitter_engine import FLUID_COLUMNS, SplitResult, split


SANDS = ["S1", "S2", "S3"]


def _lumping() -> pd.DataFrame:
    """KH table: well W-01 has S1=50, S2=100, S3=50.  Total KH = 200."""
    return pd.DataFrame(
        {"W-01": [50.0, 100.0, 50.0]},
        index=["S1", "S2", "S3"],
    )


def _production() -> pd.DataFrame:
    """Two timesteps for W-01.
    Row 0: S1 and S2 open → total KH = 150 (50+100).
    Row 1: only S2 open  → total KH = 100.
    """
    return pd.DataFrame({
        "WELL": ["W-01", "W-01"],
        "DATE": pd.to_datetime(["2025-01-01", "2025-02-01"]),
        "OIL": [300.0, 200.0],
        "GAS": [60.0, 40.0],
        "WATER": [150.0, 100.0],
        "WINJ": [0.0, 0.0],
        "S1": ["p", pd.NA],
        "S2": ["p", "p"],
        "S3": [pd.NA, pd.NA],
    })


class TestSplit:

    def test_basic_allocation(self):
        result = split(_production(), _lumping(), ["W-01"], SANDS)
        assert isinstance(result, SplitResult)
        df = result.detail

        # Row 0: OIL=300, KH_S1=50, KH_S2=100, total=150
        assert df.at[0, "OIL_S1"] == pytest.approx(300 * 50 / 150)
        assert df.at[0, "OIL_S2"] == pytest.approx(300 * 100 / 150)
        assert df.at[0, "OIL_S3"] == pytest.approx(0.0)

        # Row 1: OIL=200, only S2 open, KH=100 → fraction = 1.0
        assert df.at[1, "OIL_S2"] == pytest.approx(200.0)
        assert df.at[1, "OIL_S1"] == pytest.approx(0.0)

    def test_gas_water_winj_allocated(self):
        result = split(_production(), _lumping(), ["W-01"], SANDS)
        df = result.detail

        # Row 0: GAS=60 allocated same as OIL fractions
        assert df.at[0, "GAS_S1"] == pytest.approx(60 * 50 / 150)
        assert df.at[0, "GAS_S2"] == pytest.approx(60 * 100 / 150)

        assert df.at[0, "WATER_S1"] == pytest.approx(150 * 50 / 150)
        assert df.at[0, "WATER_S2"] == pytest.approx(150 * 100 / 150)

    def test_summary_totals(self):
        result = split(_production(), _lumping(), ["W-01"], SANDS)
        sm = result.summary

        total_oil = sm["Total_OIL"].sum()
        assert total_oil == pytest.approx(300.0 + 200.0)

    def test_missing_well_in_lumping_warns(self):
        prod = pd.DataFrame({
            "WELL": ["W-99"],
            "DATE": pd.to_datetime(["2025-01-01"]),
            "OIL": [100.0],
            "WATER": [50.0],
            "S1": ["p"],
        })
        result = split(prod, _lumping(), ["W-99"], SANDS)
        assert any("W-99" in w for w in result.warnings)
        assert result.detail.at[0, "OIL_S1"] == pytest.approx(0.0)

    def test_zero_kh_row(self):
        """When no sands are open (no "p"), nothing is allocated."""
        prod = pd.DataFrame({
            "WELL": ["W-01"],
            "DATE": pd.to_datetime(["2025-01-01"]),
            "OIL": [100.0],
            "WATER": [50.0],
            "WINJ": [0.0],
            "GAS": [10.0],
            "S1": [pd.NA],
            "S2": [pd.NA],
            "S3": [pd.NA],
        })
        result = split(prod, _lumping(), ["W-01"], SANDS)
        for s in SANDS:
            assert result.detail.at[0, f"OIL_{s}"] == pytest.approx(0.0)

    def test_case_insensitive_p(self):
        """Both 'p' and 'P' should be treated as open."""
        prod = pd.DataFrame({
            "WELL": ["W-01"],
            "DATE": pd.to_datetime(["2025-01-01"]),
            "OIL": [100.0],
            "WATER": [50.0],
            "WINJ": [0.0],
            "GAS": [10.0],
            "S1": ["P"],
            "S2": ["p"],
            "S3": [pd.NA],
        })
        result = split(prod, _lumping(), ["W-01"], SANDS)
        assert result.detail.at[0, "OIL_S1"] == pytest.approx(100 * 50 / 150)
        assert result.detail.at[0, "OIL_S2"] == pytest.approx(100 * 100 / 150)

    def test_only_fluids_present_in_production_get_allocated_columns(self):
        """If *GAS* and *WINJ* are absent from production, no GAS_* / WINJ_* split."""
        prod = pd.DataFrame({
            "WELL": ["W-01", "W-01"],
            "DATE": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "OIL": [300.0, 200.0],
            "WATER": [150.0, 100.0],
            "S1": ["p", pd.NA],
            "S2": ["p", "p"],
            "S3": [pd.NA, pd.NA],
        })
        result = split(prod, _lumping(), ["W-01"], SANDS)
        alloc_cols = [c for c in result.detail.columns if "_" in c and c.split("_", 1)[0] in {"OIL", "GAS", "WATER", "WINJ"}]
        assert not any(c.startswith("GAS_") for c in alloc_cols)
        assert not any(c.startswith("WINJ_") for c in alloc_cols)
        assert "Total_GAS" not in result.summary.columns
        assert "Total_WINJ" not in result.summary.columns
        assert "Total_OIL" in result.summary.columns
        assert "Total_WATER" in result.summary.columns
