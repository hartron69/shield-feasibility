"""
tests/test_bw_adapter.py — BarentsWatch → C5AI+ adapter unit tests.

Tests:
  TestBWConfig              (3) — config constants and directory
  TestBWAdapterNoData       (4) — behaviour when no BW files exist
  TestBWAdapterWithCSV      (6) — lice CSV parsing → LiceObservation + EnvironmentalObservation
  TestBWAdapterWithSykdom   (5) — sykdom JSON parsing → PathogenObservation
  TestBWAdapterFull         (4) — full bw_data_to_operator_input()
  TestBWAPIEndpoints        (5) — /api/c5ai/prefetch and /api/c5ai/bw/data-status

Total: 27 tests
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from c5ai_plus.Barentswatch.bw_to_c5ai_adapter import (
    _load_lice_csv,
    _load_sykdom_json,
    _week_to_month,
    bw_data_available,
    bw_data_to_operator_input,
    bw_quality_summary,
)
from c5ai_plus.Barentswatch.bw_config import BW_DATA_DIR, OPERATOR_LOCALITIES

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_LICE_ROWS = [
    {"year": "2025", "week": "1",  "avgAdultFemaleLice": "0.20", "avgMobileLice": "0.10",
     "seaTemperature": "7.5", "hasTreatment": "False", "aboveThreshold": "False"},
    {"year": "2025", "week": "5",  "avgAdultFemaleLice": "0.55", "avgMobileLice": "0.25",
     "seaTemperature": "7.8", "hasTreatment": "True",  "aboveThreshold": "True"},
    {"year": "2025", "week": "10", "avgAdultFemaleLice": "0.30", "avgMobileLice": "0.15",
     "seaTemperature": "8.2", "hasTreatment": "False", "aboveThreshold": "False"},
    {"year": "2025", "week": "20", "avgAdultFemaleLice": "nan",  "avgMobileLice": "",
     "seaTemperature": "10.1", "hasTreatment": "False", "aboveThreshold": "False"},
]

SAMPLE_SYKDOM = {
    "alle_tilfeller": [
        {
            "name": "ILA",
            "status": "CLOSED",
            "suspicionDate": "2023-03-15",
            "diagnosisDate": "2023-04-01",
        },
        {
            "name": "PD",
            "status": "CLOSED",
            "suspicionDate": "2024-06-01",
            "diagnosisDate": None,
        },
    ],
    "aktive": [],
    "historiske_ant": 2,
    "patogen_prior": 0.16,
    "risiko_flagg": "HISTORISK",
}


def _write_lice_csv(path: Path, rows=None) -> None:
    rows = rows or SAMPLE_LICE_ROWS
    fields = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _write_sykdom_json(path: Path, data=None) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data or SAMPLE_SYKDOM, f, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# TestBWConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestBWConfig:
    def test_bw_data_dir_is_path(self):
        assert isinstance(BW_DATA_DIR, Path)

    def test_operator_localities_non_empty(self):
        assert len(OPERATOR_LOCALITIES) > 0
        assert "localities" in OPERATOR_LOCALITIES[0]

    def test_each_locality_has_required_fields(self):
        for op in OPERATOR_LOCALITIES:
            for loc in op["localities"]:
                for key in ("localityNo", "site_id", "site_name", "lat", "lon"):
                    assert key in loc, f"Missing key '{key}' in locality {loc}"


# ─────────────────────────────────────────────────────────────────────────────
# TestBWAdapterNoData
# ─────────────────────────────────────────────────────────────────────────────

class TestBWAdapterNoData:
    def test_bw_data_available_false_for_empty_dir(self, tmp_path):
        assert bw_data_available(data_dir=tmp_path) is False

    def test_load_lice_csv_missing_returns_empty(self, tmp_path):
        lice, env = _load_lice_csv(tmp_path / "nonexistent.csv", "S01")
        assert lice == []
        assert env == []

    def test_load_sykdom_missing_returns_empty(self, tmp_path):
        obs = _load_sykdom_json(tmp_path / "nonexistent.json", "S01")
        assert obs == []

    def test_bw_data_to_operator_input_empty_dir_has_sites(self, tmp_path):
        op = bw_data_to_operator_input(data_dir=tmp_path)
        # Sites are built from config even without data files
        assert len(op.sites) > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestBWAdapterWithCSV
# ─────────────────────────────────────────────────────────────────────────────

class TestBWAdapterWithCSV:
    def test_lice_obs_count_matches_rows(self, tmp_path):
        _write_lice_csv(tmp_path / "luse.csv")
        lice, _ = _load_lice_csv(tmp_path / "luse.csv", "S01")
        assert len(lice) == len(SAMPLE_LICE_ROWS)

    def test_lice_obs_site_id(self, tmp_path):
        _write_lice_csv(tmp_path / "luse.csv")
        lice, _ = _load_lice_csv(tmp_path / "luse.csv", "MYSITE")
        assert all(o.site_id == "MYSITE" for o in lice)

    def test_lice_obs_nan_becomes_zero(self, tmp_path):
        _write_lice_csv(tmp_path / "luse.csv")
        lice, _ = _load_lice_csv(tmp_path / "luse.csv", "S01")
        nan_rows = [o for o in lice if o.week == 20]
        assert nan_rows[0].avg_lice_per_fish == 0.0

    def test_treatment_flag_parsed(self, tmp_path):
        _write_lice_csv(tmp_path / "luse.csv")
        lice, _ = _load_lice_csv(tmp_path / "luse.csv", "S01")
        treated = [o for o in lice if o.treatment_applied]
        assert len(treated) == 1

    def test_env_obs_aggregated_to_monthly(self, tmp_path):
        _write_lice_csv(tmp_path / "luse.csv")
        _, env = _load_lice_csv(tmp_path / "luse.csv", "S01")
        # All env obs should have valid months
        assert all(1 <= o.month <= 12 for o in env)

    def test_env_temp_is_float(self, tmp_path):
        _write_lice_csv(tmp_path / "luse.csv")
        _, env = _load_lice_csv(tmp_path / "luse.csv", "S01")
        assert all(isinstance(o.sea_temp_celsius, float) for o in env)


# ─────────────────────────────────────────────────────────────────────────────
# TestBWAdapterWithSykdom
# ─────────────────────────────────────────────────────────────────────────────

class TestBWAdapterWithSykdom:
    def test_pathogen_count_matches_tilfeller(self, tmp_path):
        _write_sykdom_json(tmp_path / "sykdom.json")
        obs = _load_sykdom_json(tmp_path / "sykdom.json", "S01")
        assert len(obs) == len(SAMPLE_SYKDOM["alle_tilfeller"])

    def test_confirmed_when_diagnosis_date_present(self, tmp_path):
        _write_sykdom_json(tmp_path / "sykdom.json")
        obs = _load_sykdom_json(tmp_path / "sykdom.json", "S01")
        ila = next(o for o in obs if o.pathogen_type == "ILA")
        assert ila.confirmed is True

    def test_unconfirmed_when_no_diagnosis_date(self, tmp_path):
        _write_sykdom_json(tmp_path / "sykdom.json")
        obs = _load_sykdom_json(tmp_path / "sykdom.json", "S01")
        pd_obs = next(o for o in obs if o.pathogen_type == "PD")
        assert pd_obs.confirmed is False

    def test_year_extracted_from_date(self, tmp_path):
        _write_sykdom_json(tmp_path / "sykdom.json")
        obs = _load_sykdom_json(tmp_path / "sykdom.json", "S01")
        ila = next(o for o in obs if o.pathogen_type == "ILA")
        assert ila.year == 2023

    def test_week_in_valid_range(self, tmp_path):
        _write_sykdom_json(tmp_path / "sykdom.json")
        obs = _load_sykdom_json(tmp_path / "sykdom.json", "S01")
        assert all(1 <= o.week <= 53 for o in obs)


# ─────────────────────────────────────────────────────────────────────────────
# TestBWAdapterFull
# ─────────────────────────────────────────────────────────────────────────────

class TestBWAdapterFull:
    def _setup_data_dir(self, tmp_path) -> Path:
        op_cfg = OPERATOR_LOCALITIES[0]
        for loc in op_cfg["localities"]:
            no = loc["localityNo"]
            _write_lice_csv(tmp_path / f"luse_historikk_{no}.csv")
            _write_sykdom_json(tmp_path / f"sykdom_historikk_{no}.json")
        return tmp_path

    def test_bw_data_available_true_with_files(self, tmp_path):
        d = self._setup_data_dir(tmp_path)
        assert bw_data_available(data_dir=d) is True

    def test_operator_input_has_correct_site_count(self, tmp_path):
        d = self._setup_data_dir(tmp_path)
        op = bw_data_to_operator_input(data_dir=d)
        assert len(op.sites) == len(OPERATOR_LOCALITIES[0]["localities"])

    def test_operator_input_has_lice_observations(self, tmp_path):
        d = self._setup_data_dir(tmp_path)
        op = bw_data_to_operator_input(data_dir=d)
        assert len(op.lice_observations) > 0

    def test_operator_input_has_pathogen_observations(self, tmp_path):
        d = self._setup_data_dir(tmp_path)
        op = bw_data_to_operator_input(data_dir=d)
        assert len(op.pathogen_observations) > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestBWAPIEndpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestBWAPIEndpoints:
    def test_bw_data_status_returns_200(self):
        r = client.get("/api/c5ai/bw/data-status")
        assert r.status_code == 200

    def test_bw_data_status_has_available_field(self):
        r = client.get("/api/c5ai/bw/data-status")
        assert "available" in r.json()

    def test_prefetch_without_secret_returns_error(self):
        # Ensure no secret is set
        import os
        original = os.environ.pop("BW_CLIENT_SECRET", None)
        try:
            r = client.post("/api/c5ai/prefetch")
            assert r.status_code == 200
            assert r.json()["status"] == "error"
        finally:
            if original is not None:
                os.environ["BW_CLIENT_SECRET"] = original

    def test_prefetch_status_endpoint_returns_200(self):
        r = client.get("/api/c5ai/prefetch/status")
        assert r.status_code == 200

    def test_prefetch_status_has_running_field(self):
        r = client.get("/api/c5ai/prefetch/status")
        assert "running" in r.json()
