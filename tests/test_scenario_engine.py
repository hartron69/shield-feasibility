"""
tests/test_scenario_engine.py — Sprint S6: Scenario Engine tests.

Tests cover:
- ScenarioEngine sea scenarios (8 tests)
- ScenarioEngine smolt scenarios (10 tests)
- API endpoint (5 tests)
- Regression guards (2 tests)
Total: 25 unit/integration tests + 5 API = 30 tests
"""

from __future__ import annotations

import pytest
from copy import deepcopy
from unittest.mock import MagicMock

import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from models.scenario_engine import ScenarioEngine, ScenarioParameters, ScenarioResult, _pct_change
from models.smolt_loss_categories import SMOLT_LOSS_CATEGORIES

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_op_input(name: str = "Test AS", events: float = 0.5, severity: float = 20_000_000):
    """Build a minimal OperatorInput using the sample template via build_operator_input."""
    from backend.schemas import OperatorProfileInput
    from backend.services.operator_builder import build_operator_input
    profile = OperatorProfileInput(
        name=name,
        n_sites=2,
        total_biomass_tonnes=5000,
        biomass_value_per_tonne=64_800,
        annual_revenue_nok=400_000_000,
        annual_premium_nok=10_000_000,
    )
    op, _ = build_operator_input(profile)
    # Override risk params for deterministic test control
    op.risk_params.expected_annual_events = events
    op.risk_params.mean_loss_severity = severity
    return op


def _make_smolt_facility_input(name: str = "Anlegg A", events: float = 0.08, severity: float = 5_000_000):
    """Single-facility OperatorInput with smolt risk profile."""
    op = _make_op_input(name, events, severity)
    op.facility_type = "smolt"
    return op


AGAQUA_SMOLT_PAYLOAD = {
    "facility_type": "smolt",
    "preset_id": "ras_collapse",
    "ras_failure_multiplier": 4.2,
    "affected_facility_index": 0,
    "smolt_operator": {
        "operator_name": "Agaqua AS",
        "org_number": "930529591",
        "facilities": [
            {
                "facility_name": "Villa Smolt AS",
                "facility_type": "smolt_ras",
                "building_components": [
                    {"name": "Hall", "area_sqm": 1370, "value_per_sqm_nok": 27000}
                ],
                "site_clearance_nok": 20_000_000,
                "machinery_nok": 200_000_000,
                "avg_biomass_insured_value_nok": 39_680_409,
                "bi_sum_insured_nok": 243_200_000,
                "bi_indemnity_months": 24,
            },
            {
                "facility_name": "Olden Oppdrettsanlegg AS",
                "facility_type": "smolt_flow",
                "building_components": [
                    {"name": "Hall", "area_sqm": 2204, "value_per_sqm_nok": 27000}
                ],
                "site_clearance_nok": 20_000_000,
                "machinery_nok": 120_000_000,
                "avg_biomass_insured_value_nok": 18_260_208,
                "bi_sum_insured_nok": 102_000_000,
                "bi_indemnity_months": 24,
            },
            {
                "facility_name": "Setran Settefisk AS",
                "facility_type": "smolt_flow",
                "building_components": [
                    {"name": "Hall A", "area_sqm": 280, "value_per_sqm_nok": 27000}
                ],
                "site_clearance_nok": 15_000_000,
                "machinery_nok": 45_000_000,
                "avg_biomass_insured_value_nok": 13_287_917,
                "bi_sum_insured_nok": 85_100_000,
                "bi_indemnity_months": 24,
            },
        ],
        "annual_revenue_nok": 232_248_232,
        "claims_history_years": 10,
        "total_claims_paid_nok": 0.0,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# ScenarioEngine — sea scenarios
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioEngineSea:

    def test_sea_scenario_returns_scenario_result(self):
        op = _make_op_input()
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=2.0)
        result = ScenarioEngine().run(op, params)
        assert isinstance(result, ScenarioResult)

    def test_lice_outbreak_increases_loss(self):
        op = _make_op_input()
        baseline_params = ScenarioParameters(facility_type="sea")
        high_lice_params = ScenarioParameters(facility_type="sea", lice_pressure_index=3.0)
        engine = ScenarioEngine()
        baseline = engine.run(op, baseline_params)
        high_lice = engine.run(op, high_lice_params)
        assert high_lice.scenario_total_loss > baseline.scenario_total_loss

    def test_severe_storm_increases_structural_loss(self):
        op = _make_op_input()
        params = ScenarioParameters(facility_type="sea", exposure_factor=1.8)
        result = ScenarioEngine().run(op, params)
        assert result.total_change_pct > 0

    def test_optimal_conditions_reduces_loss(self):
        op = _make_op_input()
        high_params = ScenarioParameters(facility_type="sea", lice_pressure_index=3.0, exposure_factor=1.5)
        low_params  = ScenarioParameters(facility_type="sea", lice_pressure_index=0.8, exposure_factor=0.8,
                                          operational_factor=0.8)
        engine = ScenarioEngine()
        high = engine.run(op, high_params)
        low  = engine.run(op, low_params)
        assert low.scenario_total_loss < high.scenario_total_loss

    def test_warm_summer_increases_biological_loss(self):
        op = _make_op_input()
        params = ScenarioParameters(facility_type="sea", dissolved_oxygen_mg_l=6.0)
        baseline = ScenarioParameters(facility_type="sea", dissolved_oxygen_mg_l=9.0)
        engine = ScenarioEngine()
        warm  = engine.run(op, params)
        cool  = engine.run(op, baseline)
        assert warm.scenario_total_loss >= cool.scenario_total_loss

    def test_sea_baseline_equals_no_change_scenario(self):
        """All-None params should return approximately the same loss as running the baseline MC."""
        op = _make_op_input()
        params = ScenarioParameters(facility_type="sea")
        result = ScenarioEngine().run(op, params)
        # Change should be ~0% (both baseline and scenario use same params)
        assert abs(result.total_change_pct) < 5.0

    def test_sea_scenario_narrative_contains_change_pct(self):
        op = _make_op_input()
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=2.5)
        result = ScenarioEngine().run(op, params)
        assert "%" in result.narrative

    def test_sea_dominant_driver_lice_when_lice_high(self):
        op = _make_op_input()
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=3.5)
        result = ScenarioEngine().run(op, params)
        assert result.highest_risk_driver == "biological"

    def test_sea_result_has_one_facility_result(self):
        op = _make_op_input()
        params = ScenarioParameters(facility_type="sea")
        result = ScenarioEngine().run(op, params)
        assert len(result.facility_results) == 1


# ─────────────────────────────────────────────────────────────────────────────
# ScenarioEngine — smolt scenarios
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioEngineSmolt:

    def _make_three_facilities(self):
        return [
            _make_smolt_facility_input("Villa Smolt AS",   events=0.08, severity=5_000_000),
            _make_smolt_facility_input("Olden Oppdrett",   events=0.07, severity=4_500_000),
            _make_smolt_facility_input("Setran Settefisk", events=0.06, severity=3_500_000),
        ]

    def test_smolt_scenario_returns_facility_results(self):
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=2.0,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        assert isinstance(result, ScenarioResult)
        assert len(result.facility_results) == 3

    def test_ras_collapse_affects_only_targeted_facility(self):
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=5.0,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        # Affected facility (index 0) should have large increase
        assert result.facility_results[0].change_pct > 50
        # Unaffected facilities should be unchanged
        assert result.facility_results[1].change_pct == 0.0
        assert result.facility_results[2].change_pct == 0.0

    def test_unaffected_facilities_unchanged_in_smolt_scenario(self):
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=10.0,
                                    affected_facility_index=1)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        # Index 0 and 2 should be unchanged
        assert result.facility_results[0].change_pct == 0.0
        assert result.facility_results[2].change_pct == 0.0

    def test_smolt_group_total_includes_diversification(self):
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=3.0)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        # Group total < sum of individual facility scenario losses (diversification applied)
        facility_sum = sum(fr.scenario_expected_loss for fr in result.facility_results)
        assert result.scenario_total_loss < facility_sum

    def test_diversification_factor_reduces_group_total(self):
        """Group total = sum of per-facility scenario * DIVERSIFICATION_FACTOR."""
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=2.0)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        expected_div = sum(fr.scenario_expected_loss for fr in result.facility_results) * ScenarioEngine.DIVERSIFICATION_FACTOR
        assert abs(result.scenario_total_loss - expected_div) < 1.0

    def test_oxygen_crisis_increases_villa_smolt_loss(self):
        facilities = self._make_three_facilities()
        # Critical O2 on facility 0
        params = ScenarioParameters(facility_type="smolt", oxygen_level_mg_l=4.5,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        assert result.facility_results[0].change_pct > 100  # 3.5× severity + 2× frequency

    def test_water_contamination_high_multiplier(self):
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=8.0,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        assert result.total_change_pct > 0

    def test_power_outage_48h_moderate_increase(self):
        """48h backup → no penalty (≥4h); 3h backup → penalty."""
        facilities = self._make_three_facilities()
        no_penalty = ScenarioParameters(facility_type="smolt", power_backup_hours=48.0)
        with_penalty = ScenarioParameters(facility_type="smolt", power_backup_hours=3.0)
        engine = ScenarioEngine()
        res_no   = engine.run(facilities[0], no_penalty,   facility_inputs=facilities)
        res_with = engine.run(facilities[0], with_penalty, facility_inputs=facilities)
        assert res_with.scenario_total_loss > res_no.scenario_total_loss

    def test_smolt_narrative_mentions_affected_facility(self):
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=5.0,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        assert "Villa Smolt AS" in result.narrative

    def test_smolt_category_breakdown_sums_to_facility_loss(self):
        """loss_by_category values should sum to exactly facility scenario loss."""
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=2.0,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        fr = result.facility_results[0]
        cat_sum = sum(fr.loss_by_category.values())
        assert abs(cat_sum - fr.scenario_expected_loss) < 1.0

    def test_affected_none_means_all_facilities_impacted(self):
        facilities = self._make_three_facilities()
        params = ScenarioParameters(facility_type="smolt", ras_failure_multiplier=3.0,
                                    affected_facility_index=None)
        result = ScenarioEngine().run(facilities[0], params, facility_inputs=facilities)
        # All facilities should show positive change
        for fr in result.facility_results:
            assert fr.change_pct > 0


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioAPI:

    def test_post_scenario_sea_returns_200(self):
        payload = {
            "facility_type": "sea",
            "preset_id": "lice_outbreak",
            "lice_pressure_index": 2.5,
            "exposure_factor": 1.3,
        }
        resp = client.post("/api/c5ai/scenario", json=payload)
        assert resp.status_code == 200

    def test_post_scenario_smolt_returns_200(self):
        resp = client.post("/api/c5ai/scenario", json=AGAQUA_SMOLT_PAYLOAD)
        assert resp.status_code == 200

    def test_post_scenario_smolt_returns_three_facility_results(self):
        resp = client.post("/api/c5ai/scenario", json=AGAQUA_SMOLT_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["facility_results"]) == 3

    def test_post_scenario_sea_response_has_required_fields(self):
        payload = {"facility_type": "sea", "lice_pressure_index": 2.0}
        resp = client.post("/api/c5ai/scenario", json=payload)
        data = resp.json()
        assert all(k in data for k in [
            "preset_id", "facility_type", "baseline_total_loss",
            "scenario_total_loss", "total_change_pct",
            "facility_results", "highest_risk_driver", "narrative",
        ])

    def test_post_scenario_agaqua_ras_collapse_change_positive(self):
        """RAS collapse × 4.2 on Villa Smolt should drive a positive group change.
        The simplified payload (1 building component) gives ~21%.
        The full Agaqua example with 5 building components gives ~97%.
        """
        resp = client.post("/api/c5ai/scenario", json=AGAQUA_SMOLT_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        # Group change must be positive and the affected facility change must be large
        assert data["total_change_pct"] > 0
        villa = next(fr for fr in data["facility_results"] if "Villa" in fr["facility_name"])
        assert villa["change_pct"] > 50


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

class TestPctChange:

    def test_positive_change(self):
        assert _pct_change(100, 150) == pytest.approx(50.0)

    def test_negative_change(self):
        assert _pct_change(100, 80) == pytest.approx(-20.0)

    def test_zero_baseline(self):
        assert _pct_change(0, 100) == 0.0

    def test_no_change(self):
        assert _pct_change(100, 100) == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Smolt loss categories
# ─────────────────────────────────────────────────────────────────────────────

class TestSmoltLossCategories:

    def test_all_six_categories_present(self):
        assert len(SMOLT_LOSS_CATEGORIES) == 6

    def test_ras_shares_sum_to_one(self):
        total = sum(c["share_ras"] for c in SMOLT_LOSS_CATEGORIES.values())
        assert abs(total - 1.0) < 1e-9

    def test_flow_shares_sum_to_one(self):
        total = sum(c["share_flow"] for c in SMOLT_LOSS_CATEGORIES.values())
        assert abs(total - 1.0) < 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# Regression guards
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionGuards:

    def test_existing_feasibility_pipeline_unchanged(self):
        """POST /api/feasibility/run still returns 200 with standard payload."""
        from tests.test_backend_api import MINIMAL_PAYLOAD
        resp = client.post("/api/feasibility/run", json=MINIMAL_PAYLOAD)
        assert resp.status_code == 200

    def test_existing_sea_mitigation_library_unchanged(self):
        """GET /api/mitigation/library?facility_type=sea still returns 12 actions."""
        resp = client.get("/api/mitigation/library?facility_type=sea")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12
