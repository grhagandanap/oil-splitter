"""Tests for ``app.services.ingestion`` — parsing and per-kind validation."""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.ingestion import (
    KIND_SCHEMAS,
    ingest,
    list_xlsx_sheets,
    parse_csv_bytes,
    validate_rows,
)


# ── Schema sanity ────────────────────────────────────────────────────────────


class TestSchemaSurface:
    def test_all_dataset_kinds_have_schemas(self):
        assert set(KIND_SCHEMAS.keys()) == {
            "marker",
            "sand",
            "completion",
            "production",
            "lumping",
            "well",
        }

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown dataset kind"):
            validate_rows(pd.DataFrame({"Well": ["W-1"]}), "wellbore")


# ── Marker ───────────────────────────────────────────────────────────────────


class TestMarkerValidation:
    def test_valid_marker(self):
        df = pd.DataFrame(
            {
                "Well": ["W-01", "W-01"],
                "Marker": ["A", "B"],
                "Depth": [100.0, 110.0],
            }
        )
        clean, errors = validate_rows(df, "marker")
        assert errors == []
        assert len(clean) == 2

    def test_missing_required_column(self):
        df = pd.DataFrame({"Well": ["W-01"], "Marker": ["A"]})
        _, errors = validate_rows(df, "marker")
        assert any("Missing required column" in e["message"] for e in errors)

    def test_negative_depth_flagged(self):
        df = pd.DataFrame({"Well": ["W-01"], "Marker": ["A"], "Depth": [-5.0]})
        _, errors = validate_rows(df, "marker")
        assert any(e["column"] == "Depth" and "≥ 0" in e["message"] for e in errors)

    def test_missing_value(self):
        df = pd.DataFrame(
            {"Well": ["W-01"], "Marker": [None], "Depth": [100.0]}
        )
        _, errors = validate_rows(df, "marker")
        assert any(
            e["row"] == 1 and e["column"] == "Marker" and "missing" in e["message"]
            for e in errors
        )

    def test_blank_string_treated_as_missing(self):
        df = pd.DataFrame({"Well": ["W-01"], "Marker": ["   "], "Depth": [100.0]})
        _, errors = validate_rows(df, "marker")
        assert any(
            e["row"] == 1 and e["column"] == "Marker" and "missing" in e["message"]
            for e in errors
        )


class TestSandValidation:
    def test_marker_list_uses_marker_column(self):
        clean, errors = validate_rows(pd.DataFrame({"Marker": ["A", "B"]}), "sand")
        assert errors == []
        assert clean == [{"Marker": "A"}, {"Marker": "B"}]


# ── Completion (the most rules) ──────────────────────────────────────────────


def _completion_row(
    *,
    well: str = "W-01",
    date: str = "2025-01-01",
    status: str = "perforation",
    top: float = 1000.0,
    base: float = 1100.0,
) -> dict:
    return {
        "Well": well,
        "Date": date,
        "Perf Status": status,
        "Perf Top": top,
        "Perf Bottom": base,
    }


class TestCompletionValidation:
    def test_valid_row(self):
        df = pd.DataFrame([_completion_row()])
        clean, errors = validate_rows(df, "completion")
        assert errors == []
        assert len(clean) == 1

    def test_invalid_status(self):
        df = pd.DataFrame([_completion_row(status="abandoned")])
        _, errors = validate_rows(df, "completion")
        assert any(e["column"] == "Perf Status" for e in errors)

    def test_status_case_insensitive(self):
        df = pd.DataFrame([_completion_row(status="Perforation")])
        _, errors = validate_rows(df, "completion")
        assert all(e["column"] != "Perf Status" for e in errors)

    def test_squeeze_status_accepted(self):
        df = pd.DataFrame([_completion_row(status="squeeze")])
        _, errors = validate_rows(df, "completion")
        assert errors == []

    def test_perf_base_must_be_deeper_than_top(self):
        """Top=1500 with Base=1200 is invalid (base must be deeper)."""
        df = pd.DataFrame([_completion_row(top=1500, base=1200)])
        _, errors = validate_rows(df, "completion")
        assert any(
            e["column"] == "Perf Bottom" and "deeper than Perf Top" in e["message"]
            for e in errors
        )

    def test_perf_base_equal_to_top_is_invalid(self):
        df = pd.DataFrame([_completion_row(top=1000, base=1000)])
        _, errors = validate_rows(df, "completion")
        assert any("deeper than Perf Top" in e["message"] for e in errors)

    def test_negative_perf_top_flagged(self):
        df = pd.DataFrame([_completion_row(top=-50, base=100)])
        _, errors = validate_rows(df, "completion")
        assert any(e["column"] == "Perf Top" for e in errors)

    def test_missing_well_flagged(self):
        df = pd.DataFrame([_completion_row(well=None)])
        _, errors = validate_rows(df, "completion")
        assert any(e["column"] == "Well" for e in errors)

    def test_non_numeric_perf_top(self):
        rows = [_completion_row()]
        rows[0]["Perf Top"] = "deep"
        df = pd.DataFrame(rows)
        _, errors = validate_rows(df, "completion")
        assert any(
            e["column"] == "Perf Top" and "expected float" in e["message"]
            for e in errors
        )


# ── Production ──────────────────────────────────────────────────────────────


class TestProductionValidation:
    def test_valid_with_all_fluids(self):
        df = pd.DataFrame(
            [
                {
                    "WELL": "W-01",
                    "DATE": "2025-01-01",
                    "OIL": 100.0,
                    "GAS": 50.0,
                    "WATER": 25.0,
                    "WINJ": 0.0,
                }
            ]
        )
        _, errors = validate_rows(
            df.rename(
                columns={
                    "WELL": "Well",
                    "DATE": "Date",
                    "OIL": "Oil",
                    "GAS": "Gas",
                    "WATER": "Water",
                    "WINJ": "Water Injection",
                }
            ),
            "production",
        )
        assert errors == []

    def test_optional_fluid_invalid(self):
        df = pd.DataFrame(
            [
                {
                    "Well": "W-01",
                    "Date": "2025-01-01",
                    "Oil": 100.0,
                    "Gas": "bad",
                }
            ]
        )
        _, errors = validate_rows(df, "production")
        assert any(e["column"] == "Gas" for e in errors)

    def test_included_fluid_blank_is_invalid(self):
        df = pd.DataFrame(
            [
                {
                    "Well": "W-01",
                    "Date": "2025-01-01",
                    "Oil": 100.0,
                    "Gas": None,
                }
            ]
        )
        _, errors = validate_rows(df, "production")
        assert any(e["column"] == "Gas" and "missing" in e["message"] for e in errors)

    def test_negative_oil_flagged(self):
        df = pd.DataFrame([{"Well": "W-01", "Date": "2025-01-01", "Oil": -10.0}])
        _, errors = validate_rows(df, "production")
        assert any(e["column"] == "Oil" and "≥ 0" in e["message"] for e in errors)

    def test_at_least_one_fluid_column_required(self):
        df = pd.DataFrame([{"Well": "W-01", "Date": "2025-01-01"}])
        _, errors = validate_rows(df, "production")
        assert any("at least one fluid column" in e["message"] for e in errors)


class TestLumpingValidation:
    def test_valid_lumping_pivots_zone_index_and_well_columns(self):
        df = pd.DataFrame(
            [
                {"Zone": "A", "Well": "W-01", "Lumping": 10},
                {"Zone": "A", "Well": "W-02", "Lumping": 20},
                {"Zone": "B", "Well": "W-01", "Lumping": 30},
            ]
        )
        clean, errors = validate_rows(df, "lumping")
        assert errors == []
        assert clean == [
            {"Zone": "A", "W-01": 10.0, "W-02": 20.0},
            {"Zone": "B", "W-01": 30.0, "W-02": 0.0},
        ]

    def test_lumping_requires_long_format(self):
        df = pd.DataFrame({"Zone": ["A"], "W-01": [10]})
        _, errors = validate_rows(df, "lumping")
        assert any("Missing required column" in e["message"] for e in errors)


class TestWellValidation:
    def test_valid_well_list(self):
        clean, errors = validate_rows(pd.DataFrame({"Well": ["W-01"]}), "well")
        assert errors == []
        assert clean == [{"Well": "W-01"}]


# ── Empty input ─────────────────────────────────────────────────────────────


class TestEmptyDataset:
    def test_empty_dataset_flagged(self):
        df = pd.DataFrame(columns=["Zone", "Well", "Lumping"])
        _, errors = validate_rows(df, "lumping")
        assert any(e["message"] == "Dataset is empty." for e in errors)


# ── Parsing ────────────────────────────────────────────────────────────────


class TestParsing:
    def test_csv_autodetect_comma(self):
        raw = b"Well,Marker,Depth\nW-01,A,100\nW-01,B,200\n"
        df = parse_csv_bytes(raw)
        assert list(df.columns) == ["Well", "Marker", "Depth"]
        assert len(df) == 2

    def test_csv_autodetect_tab(self):
        raw = b"Well\tMarker\tDepth\nW-01\tA\t100\nW-01\tB\t200\n"
        df = parse_csv_bytes(raw)
        assert list(df.columns) == ["Well", "Marker", "Depth"]
        assert len(df) == 2

    def test_list_xlsx_sheets(self):
        from io import BytesIO

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"Well": ["W-01"]}).to_excel(
                writer, sheet_name="Wells", index=False
            )
            pd.DataFrame({"Marker": ["A"]}).to_excel(
                writer, sheet_name="Markers", index=False
            )

        assert list_xlsx_sheets(buffer.getvalue()) == ["Wells", "Markers"]


# ── Façade ─────────────────────────────────────────────────────────────────


class TestIngestFacade:
    def test_paste_rows(self):
        rows = [
            {
                "WELL": "W-01",
                "Marker": "A",
                "Depth": 100.0,
            }
        ]
        rows[0]["Well"] = rows[0].pop("WELL")
        source, clean, errors, ok = ingest(kind="marker", pasted_rows=rows)
        assert source == "paste"
        assert ok is True
        assert errors == []
        assert clean == rows

    def test_csv_bytes(self):
        raw = b"Zone,Well,Lumping\nA,W-01,50\nB,W-01,30\n"
        source, clean, errors, ok = ingest(
            kind="lumping", raw_bytes=raw, filename="kh.csv"
        )
        assert source == "csv"
        assert ok is True
        assert clean == [{"Zone": "A", "W-01": 50.0}, {"Zone": "B", "W-01": 30.0}]

    def test_paste_with_invalid_completion(self):
        rows = [
            {
                "Well": "W-01",
                "Date": "2025-01-01",
                "Perf Status": "perforation",
                "Perf Top": 1500,
                "Perf Bottom": 1200,
            }
        ]
        source, _, errors, ok = ingest(kind="completion", pasted_rows=rows)
        assert source == "paste"
        assert ok is False
        assert any("deeper than Perf Top" in e["message"] for e in errors)

    def test_requires_one_input_vector(self):
        with pytest.raises(ValueError, match="Provide either"):
            ingest(kind="marker")
