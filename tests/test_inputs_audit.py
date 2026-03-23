"""
tests/test_inputs_audit.py — GET /api/inputs/audit endpoint tests.

Tests:
  TestInputsAuditEndpoint    (5) — HTTP response shape
  TestInputsAuditContent     (8) — data correctness
  TestInputsAuditC5AIState   (4) — live C5AI+ state reflected in report

Total: 17 tests
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _reset_c5ai_state():
    import backend.services.c5ai_state as _st
    with _st._lock:
        _st._c5ai_run_id = None
        _st._c5ai_last_run_at = None
        _st._inputs_last_updated_at = None
        _st._extra_run_meta = {}


# ─────────────────────────────────────────────────────────────────────────────
# TestInputsAuditEndpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestInputsAuditEndpoint:
    def setup_method(self):
        _reset_c5ai_state()

    def test_returns_200(self):
        r = client.get("/api/inputs/audit")
        assert r.status_code == 200

    def test_returns_json(self):
        r = client.get("/api/inputs/audit")
        data = r.json()
        assert isinstance(data, dict)

    def test_report_type_field(self):
        r = client.get("/api/inputs/audit")
        assert r.json()["report_type"] == "input_data_audit"

    def test_generated_at_present(self):
        from datetime import datetime
        r = client.get("/api/inputs/audit")
        ts = r.json()["generated_at"]
        assert ts is not None
        datetime.fromisoformat(ts)  # parseable ISO string

    def test_operator_field_present(self):
        r = client.get("/api/inputs/audit")
        assert "operator" in r.json()
        assert isinstance(r.json()["operator"], str)


# ─────────────────────────────────────────────────────────────────────────────
# TestInputsAuditContent
# ─────────────────────────────────────────────────────────────────────────────

class TestInputsAuditContent:
    def setup_method(self):
        _reset_c5ai_state()

    def _report(self):
        return client.get("/api/inputs/audit").json()

    def test_three_sites(self):
        report = self._report()
        assert len(report["sites"]) == 3

    def test_site_ids_are_correct(self):
        report = self._report()
        ids = {s["site_id"] for s in report["sites"]}
        assert ids == {"DEMO_OP_S01", "DEMO_OP_S02", "DEMO_OP_S03"}

    def test_each_site_has_risk_types(self):
        report = self._report()
        for site in report["sites"]:
            assert len(site["risk_types"]) > 0

    def test_four_domain_coverage_entries(self):
        report = self._report()
        domains = set(report["domain_coverage"].keys())
        assert domains == {"biological", "structural", "environmental", "operational"}

    def test_non_bio_domains_are_estimated(self):
        """structural, environmental, operational must always be 'estimated'."""
        report = self._report()
        for domain in ["structural", "environmental", "operational"]:
            assert report["domain_coverage"][domain]["source"] == "estimated"

    def test_summary_totals_are_consistent(self):
        report = self._report()
        s = report["summary"]
        assert s["total_sites"] == len(report["sites"])
        assert s["sufficient_count"] + s["limited_count"] + s["poor_count"] == s["total_risk_types_assessed"]

    def test_portfolio_completeness_in_range(self):
        report = self._report()
        pc = report["summary"]["portfolio_completeness"]
        assert 0.0 <= pc <= 1.0

    def test_model_limitations_non_empty(self):
        report = self._report()
        lims = report["model_limitations"]
        assert isinstance(lims, list)
        assert len(lims) >= 3


# ─────────────────────────────────────────────────────────────────────────────
# TestInputsAuditC5AIState
# ─────────────────────────────────────────────────────────────────────────────

class TestInputsAuditC5AIState:
    def setup_method(self):
        _reset_c5ai_state()

    def test_freshness_missing_initially(self):
        report = client.get("/api/inputs/audit").json()
        assert report["c5ai_status"]["freshness"] == "missing"

    def test_freshness_fresh_after_c5ai_run(self):
        client.post("/api/c5ai/run")
        report = client.get("/api/inputs/audit").json()
        assert report["c5ai_status"]["freshness"] == "fresh"

    def test_pipeline_ran_false_initially(self):
        report = client.get("/api/inputs/audit").json()
        assert report["c5ai_status"]["pipeline_ran"] is False

    def test_biological_domain_c5ai_when_fresh(self):
        """When C5AI+ is fresh, biological domain source should be 'c5ai_plus'."""
        client.post("/api/c5ai/run")
        report = client.get("/api/inputs/audit").json()
        assert report["domain_coverage"]["biological"]["source"] == "c5ai_plus"

    def test_biological_domain_estimated_when_missing(self):
        """When C5AI+ has never run, biological domain source falls back to 'estimated'."""
        report = client.get("/api/inputs/audit").json()
        assert report["domain_coverage"]["biological"]["source"] == "estimated"
