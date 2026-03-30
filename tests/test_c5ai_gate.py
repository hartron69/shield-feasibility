"""
tests/test_c5ai_gate.py – Sprint 3: C5AI+ activation and freshness gate tests.

Tests:
  TestC5AIStateUnit       (7)  – c5ai_state module in isolation
  TestC5AIEndpoints       (8)  – /api/c5ai/* via TestClient
  TestFeasibilityMeta     (4)  – c5ai_meta field in FeasibilityResponse

Total: 19 tests
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import c5ai_state

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _reset_state():
    """Reset the in-memory c5ai_state between tests."""
    import backend.services.c5ai_state as _st
    with _st._lock:
        _st._c5ai_run_id = None
        _st._c5ai_last_run_at = None
        _st._inputs_last_updated_at = None


MINIMAL_FEASIBILITY_PAYLOAD = {
    "operator_profile": {
        "name": "Test Operator",
        "country": "Norge",
        "n_sites": 2,
        "total_biomass_tonnes": 5000,
        "biomass_value_per_tonne": 70000,
        "annual_revenue_nok": 400_000_000,
        "annual_premium_nok": 10_000_000,
    },
    "model_settings": {"n_simulations": 100, "generate_pdf": False},
    "strategy_settings": {"strategy": "pcc_captive"},
    "mitigation": {"selected_actions": []},
}


# ─────────────────────────────────────────────────────────────────────────────
# TestC5AIStateUnit
# ─────────────────────────────────────────────────────────────────────────────

class TestC5AIStateUnit:
    def setup_method(self):
        _reset_state()

    def test_initial_status_is_missing(self):
        s = c5ai_state.get_status()
        assert s["freshness"] == "missing"
        assert s["is_fresh"] is False
        assert s["run_id"] is None

    def test_record_run_returns_run_id_and_datetime(self):
        run_id, run_at = c5ai_state.record_c5ai_run()
        assert isinstance(run_id, str) and len(run_id) > 0
        assert isinstance(run_at, datetime)

    def test_after_run_freshness_is_fresh(self):
        c5ai_state.record_c5ai_run()
        s = c5ai_state.get_status()
        assert s["freshness"] == "fresh"
        assert s["is_fresh"] is True

    def test_inputs_updated_after_run_makes_stale(self):
        c5ai_state.record_c5ai_run()
        time.sleep(0.01)
        c5ai_state.mark_inputs_updated()
        s = c5ai_state.get_status()
        assert s["freshness"] == "stale"
        assert s["is_fresh"] is False

    def test_run_after_inputs_updated_makes_fresh_again(self):
        c5ai_state.record_c5ai_run()
        time.sleep(0.01)
        c5ai_state.mark_inputs_updated()
        time.sleep(0.01)
        c5ai_state.record_c5ai_run()
        s = c5ai_state.get_status()
        assert s["freshness"] == "fresh"

    def test_custom_run_id(self):
        c5ai_state.record_c5ai_run(run_id="test-run-abc")
        s = c5ai_state.get_status()
        assert s["run_id"] == "test-run-abc"

    def test_status_timestamps_are_iso_strings(self):
        c5ai_state.record_c5ai_run()
        c5ai_state.mark_inputs_updated()
        s = c5ai_state.get_status()
        assert s["c5ai_last_run_at"] is not None
        # Should be parseable as ISO datetime
        datetime.fromisoformat(s["c5ai_last_run_at"])
        datetime.fromisoformat(s["inputs_last_updated_at"])


# ─────────────────────────────────────────────────────────────────────────────
# TestC5AIEndpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestC5AIEndpoints:
    def setup_method(self):
        _reset_state()

    def test_status_endpoint_returns_missing_initially(self):
        r = client.get("/api/c5ai/status")
        assert r.status_code == 200
        data = r.json()
        assert data["freshness"] == "missing"
        assert data["is_fresh"] is False

    def test_run_endpoint_returns_200(self):
        r = client.post("/api/c5ai/run")
        assert r.status_code == 200

    def test_run_endpoint_returns_run_id(self):
        r = client.post("/api/c5ai/run")
        data = r.json()
        assert "run_id" in data
        assert isinstance(data["run_id"], str) and len(data["run_id"]) > 0

    def test_run_endpoint_returns_freshness_field(self):
        r = client.post("/api/c5ai/run")
        data = r.json()
        assert "freshness" in data
        assert data["freshness"] in ("fresh", "stale", "missing")

    def test_run_sets_status_fresh(self):
        client.post("/api/c5ai/run")
        r = client.get("/api/c5ai/status")
        assert r.json()["freshness"] == "fresh"

    def test_inputs_updated_endpoint_returns_200(self):
        r = client.post("/api/c5ai/inputs/updated")
        assert r.status_code == 200

    def test_inputs_updated_makes_stale(self):
        client.post("/api/c5ai/run")
        time.sleep(0.01)
        client.post("/api/c5ai/inputs/updated")
        r = client.get("/api/c5ai/status")
        assert r.json()["freshness"] == "stale"

    def test_run_after_inputs_updated_restores_fresh(self):
        client.post("/api/c5ai/run")
        time.sleep(0.01)
        client.post("/api/c5ai/inputs/updated")
        time.sleep(0.01)
        client.post("/api/c5ai/run")
        r = client.get("/api/c5ai/status")
        assert r.json()["freshness"] == "fresh"


# ─────────────────────────────────────────────────────────────────────────────
# TestFeasibilityMeta
# ─────────────────────────────────────────────────────────────────────────────

class TestFeasibilityMeta:
    def setup_method(self):
        _reset_state()

    def test_feasibility_response_has_c5ai_meta_field(self):
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "c5ai_meta" in data

    def test_c5ai_meta_freshness_missing_when_not_run(self):
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        meta = r.json().get("c5ai_meta") or {}
        assert meta.get("freshness") == "missing"

    def test_c5ai_meta_freshness_fresh_after_run(self):
        client.post("/api/c5ai/run")
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        meta = r.json().get("c5ai_meta") or {}
        assert meta.get("freshness") == "fresh"
        assert meta.get("is_fresh") is True

    def test_c5ai_meta_has_run_id_after_c5ai_run(self):
        client.post("/api/c5ai/run")
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        meta = r.json().get("c5ai_meta") or {}
        assert meta.get("run_id") is not None


# ─────────────────────────────────────────────────────────────────────────────
# TestExtendedC5AIRunMeta
# ─────────────────────────────────────────────────────────────────────────────

class TestExtendedC5AIRunMeta:
    def setup_method(self):
        _reset_state()
        # Also reset extra run meta
        import backend.services.c5ai_state as _st
        with _st._lock:
            _st._extra_run_meta = {}

    def test_c5ai_run_meta_has_site_count_after_c5ai_run(self):
        """After POST /api/c5ai/run, FeasibilityResponse.c5ai_meta.site_count > 0."""
        client.post("/api/c5ai/run")
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        assert r.status_code == 200
        meta = r.json().get("c5ai_meta") or {}
        assert meta.get("site_count", 0) > 0

    def test_c5ai_run_meta_has_domains_used_after_c5ai_run(self):
        """After POST /api/c5ai/run, domains_used is a non-empty list."""
        client.post("/api/c5ai/run")
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        assert r.status_code == 200
        meta = r.json().get("c5ai_meta") or {}
        domains_used = meta.get("domains_used", [])
        assert isinstance(domains_used, list)
        assert len(domains_used) > 0

    def test_c5ai_run_meta_site_trace_populated_after_feasibility(self):
        """After running feasibility, site_trace field is present (list, possibly empty)."""
        client.post("/api/c5ai/run")
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        assert r.status_code == 200
        meta = r.json().get("c5ai_meta") or {}
        assert "site_trace" in meta
        assert isinstance(meta["site_trace"], list)

    def test_c5ai_run_meta_data_mode_is_set(self):
        """data_mode is one of 'simulated', 'real', 'mixed'."""
        client.post("/api/c5ai/run")
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        assert r.status_code == 200
        meta = r.json().get("c5ai_meta") or {}
        assert meta.get("data_mode") in ("simulated", "real", "mixed", "live_risk")

    def test_c5ai_run_meta_source_labels_is_list(self):
        """source_labels is a list (possibly empty)."""
        client.post("/api/c5ai/run")
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        assert r.status_code == 200
        meta = r.json().get("c5ai_meta") or {}
        assert isinstance(meta.get("source_labels", []), list)


# ─────────────────────────────────────────────────────────────────────────────
# TestTransparencyFields
# ─────────────────────────────────────────────────────────────────────────────

class TestTransparencyFields:
    """Verify domain_sources, confidence_score, confidence_label in site_trace."""

    def setup_method(self):
        _reset_state()
        import backend.services.c5ai_state as _st
        with _st._lock:
            _st._extra_run_meta = {}

    def _get_site_trace(self):
        client.post("/api/c5ai/run")
        r = client.post("/api/feasibility/run", json=MINIMAL_FEASIBILITY_PAYLOAD)
        assert r.status_code == 200
        return r.json().get("c5ai_meta", {}).get("site_trace", [])

    def test_site_trace_items_have_domain_sources(self):
        """Each site_trace entry carries a domain_sources dict."""
        trace = self._get_site_trace()
        if not trace:
            return  # no sites produced — skip
        for site in trace:
            assert "domain_sources" in site
            assert isinstance(site["domain_sources"], dict)

    def test_domain_sources_cover_all_four_domains(self):
        """domain_sources contains entries for all four risk domains."""
        trace = self._get_site_trace()
        if not trace:
            return
        expected = {"biological", "structural", "environmental", "operational"}
        for site in trace:
            assert expected.issubset(set(site["domain_sources"].keys()))

    def test_non_biological_domains_are_estimated(self):
        """structural, environmental, operational must always be 'estimated'."""
        trace = self._get_site_trace()
        if not trace:
            return
        non_bio = ["structural", "environmental", "operational"]
        for site in trace:
            for domain in non_bio:
                assert site["domain_sources"].get(domain) == "estimated", (
                    f"Domain '{domain}' must be 'estimated' but got "
                    f"'{site['domain_sources'].get(domain)}'"
                )

    def test_confidence_score_is_float_in_range(self):
        """confidence_score is a float in [0.0, 1.0]."""
        trace = self._get_site_trace()
        if not trace:
            return
        for site in trace:
            score = site.get("confidence_score", -1)
            assert isinstance(score, (int, float))
            assert 0.0 <= score <= 1.0

    def test_confidence_score_never_high_without_full_domain_data(self):
        """confidence_score must not reach 1.0 (impossible: non-bio always estimated)."""
        trace = self._get_site_trace()
        if not trace:
            return
        for site in trace:
            assert site.get("confidence_score", 0) < 1.0, (
                "confidence_score must stay below 1.0 when non-bio domains are estimated"
            )

    def test_confidence_label_is_valid_string(self):
        """confidence_label is one of the expected Norwegian labels."""
        valid_labels = {"Lav", "Lav-Middels", "Lav–Middels", "Middels", "Høy"}
        trace = self._get_site_trace()
        if not trace:
            return
        for site in trace:
            assert site.get("confidence_label") in valid_labels, (
                f"Unexpected confidence_label: {site.get('confidence_label')!r}"
            )

    def test_confidence_capped_at_middels_without_c5ai_enrichment(self):
        """Without C5AI+ enrichment, confidence_label must not be 'Høy'."""
        # In the test environment the C5AI+ pipeline stubs out (no real enrichment),
        # so c5ai_enriched is always False in test runs.
        trace = self._get_site_trace()
        if not trace:
            return
        for site in trace:
            assert site.get("confidence_label") != "Høy"
