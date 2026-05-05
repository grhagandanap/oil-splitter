"""Tests for ``app.services.run_executor`` — end-to-end orchestration."""

from __future__ import annotations

import json

import pytest

from app.services.run_executor import (
    REQUIRED_KINDS,
    RunInputError,
    execute_run,
)


# ── Synthetic project fixture ────────────────────────────────────────────────


def _project_datasets() -> dict[str, list[dict]]:
    """Minimal but realistic dataset bundle for one well, two markers."""
    return {
        "sand": [{"Marker": "S1"}, {"Marker": "S2"}, {"Marker": "S3"}],
        "well": [{"Well": "W-01"}],
        "marker": [
            {"Well": "W-01", "Marker": "S1", "Depth": 1000.0},
            {"Well": "W-01", "Marker": "S2", "Depth": 1100.0},
            {"Well": "W-01", "Marker": "S3", "Depth": 1200.0},
        ],
        "completion": [
            {
                "Well": "W-01",
                "Date": "01/01/2025",
                "Perf Status": "perforation",
                "Perf Top": 1000.0,
                "Perf Bottom": 1150.0,
            }
        ],
        "production": [
            {
                "Well": "W-01",
                "Date": "01/02/2025",
                "Oil": 300.0,
                "Water": 150.0,
                "Gas": 60.0,
                "Water Injection": 0.0,
            }
        ],
        # Lumping is stored pivoted by ingestion: Zone column + one column per well.
        "lumping": [
            {"Zone": "S1", "W-01": 50.0},
            {"Zone": "S2", "W-01": 100.0},
            {"Zone": "S3", "W-01": 50.0},
        ],
    }


# ── Required-input validation ────────────────────────────────────────────────


class TestInputValidation:
    @pytest.mark.parametrize("kind", REQUIRED_KINDS)
    def test_missing_kind_raises(self, kind):
        ds = _project_datasets()
        del ds[kind]
        with pytest.raises(RunInputError, match=kind):
            execute_run(ds)

    def test_empty_kind_raises(self):
        ds = _project_datasets()
        ds["production"] = []
        with pytest.raises(RunInputError, match="production"):
            execute_run(ds)


# ── Happy path ───────────────────────────────────────────────────────────────


class TestHappyPath:
    def test_returns_jsonable_detail_and_summary(self):
        artifacts = execute_run(_project_datasets())

        # JSON round-trip — guards against datetime / numpy leakage.
        json.dumps(artifacts.marker_preview)
        json.dumps(artifacts.detail)
        json.dumps(artifacts.summary)

        assert len(artifacts.detail) == 1
        assert len(artifacts.summary) == 3
        assert {row["Sand"] for row in artifacts.summary} == {"S1", "S2", "S3"}

    def test_summary_totals_balance_to_input_volumes(self):
        """KH-weighted split must conserve total fluid volumes per timestep."""
        artifacts = execute_run(_project_datasets())

        for fluid_in, fluid_total_key in [
            ("Total_OIL", 300.0),
            ("Total_WATER", 150.0),
            ("Total_GAS", 60.0),
        ]:
            total_allocated = sum(
                row.get(fluid_in, 0.0) or 0.0 for row in artifacts.summary
            )
            assert total_allocated == pytest.approx(fluid_total_key, abs=1e-6)

    def test_well_missing_from_lumping_emitted_as_warning(self):
        """If a well is in the well list / production but absent from lumping,
        the splitter records a warning instead of failing."""
        ds = _project_datasets()
        ds["well"].append({"Well": "W-99"})
        ds["production"].append(
            {
                "Well": "W-99",
                "Date": "01/02/2025",
                "Oil": 10.0,
                "Water": 5.0,
                "Gas": 2.0,
                "Water Injection": 0.0,
            }
        )
        # Add minimal completion + markers for the new well so auto_marker
        # doesn't bail before splitter sees it.
        ds["marker"].extend(
            [
                {"Well": "W-99", "Marker": "S1", "Depth": 1000.0},
                {"Well": "W-99", "Marker": "S2", "Depth": 1100.0},
                {"Well": "W-99", "Marker": "S3", "Depth": 1200.0},
            ]
        )
        ds["completion"].append(
            {
                "Well": "W-99",
                "Date": "01/01/2025",
                "Perf Status": "perforation",
                "Perf Top": 1000.0,
                "Perf Bottom": 1150.0,
            }
        )

        artifacts = execute_run(ds)
        assert any("W-99" in w and "lumping" in w for w in artifacts.warnings)

    def test_marker_preview_shows_p_in_sand_columns(self):
        artifacts = execute_run(_project_datasets())
        assert len(artifacts.marker_preview) >= 1
        found_p = any(
            str(row.get(sand, "") or "").strip().upper() == "P"
            for row in artifacts.marker_preview
            for sand in ("S1", "S2", "S3")
        )
        assert found_p, "expected at least one open sand cell with marker 'p'"

    def test_oil_water_only_production_omits_gas_and_winj_split_columns(self):
        ds = _project_datasets()
        ds["production"] = [
            {k: v for k, v in row.items() if k not in ("Gas", "Water Injection")}
            for row in ds["production"]
        ]
        artifacts = execute_run(ds)
        for row in artifacts.detail:
            for key in row:
                assert not key.startswith("GAS_")
                assert not key.startswith("WINJ_")
        for srow in artifacts.summary:
            assert "Total_GAS" not in srow
            assert "Total_WINJ" not in srow
