"""
tests/test_backend_api.py – Sprint 8 backend API tests.

Uses FastAPI TestClient (no real HTTP server needed).
16 tests total.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

MINIMAL_PAYLOAD = {
    "operator_profile": {
        "name": "Test Operator",
        "country": "Norge",
        "n_sites": 2,
        "total_biomass_tonnes": 5000,
        "biomass_value_per_tonne": 70000,
        "annual_revenue_nok": 400_000_000,
        "annual_premium_nok": 10_000_000,
    },
    "model_settings": {
        "n_simulations": 200,        # small for fast tests
        "domain_correlation": "expert_default",
        "generate_pdf": False,       # skip PDF in tests
    },
    "strategy_settings": {"strategy": "pcc_captive", "retention_nok": None},
    "mitigation": {"selected_actions": []},
}

MITIGATED_PAYLOAD = {
    **MINIMAL_PAYLOAD,
    "mitigation": {"selected_actions": ["stronger_nets", "environmental_sensors"]},
}


# ─────────────────────────────────────────────────────────────────────────────
# TestMitigationLibrary (4 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestMitigationLibrary:
    def test_get_library_200(self):
        res = client.get("/api/mitigation/library")
        assert res.status_code == 200

    def test_library_returns_12_items(self):
        res = client.get("/api/mitigation/library")
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 12

    def test_each_item_has_required_fields(self):
        res = client.get("/api/mitigation/library")
        for item in res.json():
            assert "id" in item
            assert "name" in item
            assert "description" in item
            assert "affected_domains" in item

    def test_new_actions_present(self):
        res = client.get("/api/mitigation/library")
        ids = {item["id"] for item in res.json()}
        assert "deformation_monitoring" in ids
        assert "ai_early_warning" in ids


# ─────────────────────────────────────────────────────────────────────────────
# TestFeasibilityExample (2 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestFeasibilityExample:
    def test_example_returns_200(self):
        res = client.post("/api/feasibility/example")
        assert res.status_code == 200

    def test_example_has_selected_actions(self):
        res = client.post("/api/feasibility/example")
        data = res.json()
        actions = data.get("mitigation", {}).get("selected_actions", [])
        assert len(actions) > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestFeasibilityBaseline (4 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestFeasibilityBaseline:
    @pytest.fixture(scope="class")
    def baseline_response(self):
        res = client.post("/api/feasibility/run", json=MINIMAL_PAYLOAD)
        assert res.status_code == 200
        return res.json()

    def test_run_returns_200(self, baseline_response):
        # Already asserted in fixture; just confirm the response exists
        assert baseline_response is not None

    def test_baseline_summary_keys_present(self, baseline_response):
        summary = baseline_response["baseline"]["summary"]
        for key in ("expected_annual_loss", "p95_loss", "p99_loss", "scr", "verdict", "composite_score", "confidence_level"):
            assert key in summary, f"Missing key: {key}"

    def test_mitigated_and_comparison_are_null_without_actions(self, baseline_response):
        assert baseline_response["mitigated"] is None
        assert baseline_response["comparison"] is None

    def test_report_available_is_bool(self, baseline_response):
        assert isinstance(baseline_response["report"]["available"], bool)


# ─────────────────────────────────────────────────────────────────────────────
# TestFeasibilityMitigated (4 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestFeasibilityMitigated:
    @pytest.fixture(scope="class")
    def mit_response(self):
        res = client.post("/api/feasibility/run", json=MITIGATED_PAYLOAD)
        assert res.status_code == 200
        return res.json()

    def test_mitigated_block_present(self, mit_response):
        assert mit_response["mitigated"] is not None

    def test_mitigated_loss_lower_than_baseline(self, mit_response):
        baseline_loss = mit_response["baseline"]["summary"]["expected_annual_loss"]
        mit_loss = mit_response["mitigated"]["summary"]["expected_annual_loss"]
        assert mit_loss < baseline_loss

    def test_comparison_delta_pct_negative(self, mit_response):
        delta_pct = mit_response["comparison"]["expected_loss_delta_pct"]
        assert delta_pct < 0

    def test_comparison_top_benefit_domains_nonempty(self, mit_response):
        domains = mit_response["comparison"]["top_benefit_domains"]
        assert isinstance(domains, list)
        assert len(domains) > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestBackwardCompat (2 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestBackwardCompat:
    def test_omitting_mitigation_field_returns_200(self):
        payload = {k: v for k, v in MINIMAL_PAYLOAD.items() if k != "mitigation"}
        res = client.post("/api/feasibility/run", json=payload)
        assert res.status_code == 200, res.text

    def test_omitting_domain_correlation_uses_default(self):
        payload = {
            **MINIMAL_PAYLOAD,
            "model_settings": {
                "n_simulations": 200,
                "generate_pdf": False,
                # domain_correlation omitted → should default to "expert_default"
            },
        }
        res = client.post("/api/feasibility/run", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["metadata"]["domain_correlation_active"] is True
