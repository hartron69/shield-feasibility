"""
Test suite for Sprint S1: Settefisk TIV model and operator-builder.
37 tests covering data model, builder, Pydantic schema, API endpoints,
and regression guard for the sea-based pipeline.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from data.input_schema import (
    BuildingComponent,
    FacilityType,
    SmoltFacilityTIV,
    SmoltOperatorInput,
)
from backend.services.smolt_operator_builder import SmoltAllocationSummary, SmoltOperatorBuilder
from backend.schemas import (
    BuildingComponentInput,
    SmoltFacilityInput,
    SmoltOperatorRequest,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _villa_smolt() -> SmoltFacilityTIV:
    return SmoltFacilityTIV(
        facility_name="Villa Smolt AS",
        facility_type=FacilityType.SMOLT_RAS,
        building_components=[
            BuildingComponent("Hall over fish tanks", 1370, 27000),
            BuildingComponent("RAS 1-2",              530,  27000),
            BuildingComponent("RAS 3-4",              610,  27000),
            BuildingComponent("Gamledelen",           1393, 27000),
            BuildingComponent("Forlager",             275,  27000),
        ],
        site_clearance_nok            = 20_000_000,
        machinery_nok                 = 200_000_000,
        avg_biomass_insured_value_nok = 39_680_409,
        bi_sum_insured_nok            = 243_200_000,
        bi_indemnity_months           = 24,
        municipality                  = "Herøy",
    )


def _olden() -> SmoltFacilityTIV:
    return SmoltFacilityTIV(
        facility_name="Olden Oppdrettsanlegg AS",
        facility_type=FacilityType.SMOLT_FLOW,
        building_components=[
            BuildingComponent("Påvekstavdeling",        2204, 27000),
            BuildingComponent("Yngel",                  899,  27000),
            BuildingComponent("Klekkeri/startforing",   221,  27000),
            BuildingComponent("Teknisk/vannbehandling",  77,  27000),
        ],
        site_clearance_nok            = 20_000_000,
        machinery_nok                 = 120_000_000,
        avg_biomass_insured_value_nok = 18_260_208,
        bi_sum_insured_nok            = 102_000_000,
        bi_indemnity_months           = 24,
        municipality                  = "Ørland",
    )


def _setran() -> SmoltFacilityTIV:
    return SmoltFacilityTIV(
        facility_name="Setran Settefisk AS",
        facility_type=FacilityType.SMOLT_FLOW,
        building_components=[
            BuildingComponent("Hall A",          280, 27000),
            BuildingComponent("Vannbehandling",  170, 27000),
            BuildingComponent("Hall B",          715, 27000),
            BuildingComponent("Hall C",          979, 27000),
        ],
        site_clearance_nok            = 15_000_000,
        machinery_nok                 = 45_000_000,
        avg_biomass_insured_value_nok = 13_287_917,
        bi_sum_insured_nok            = 85_100_000,
        bi_indemnity_months           = 24,
        municipality                  = "Osen",
    )


def _agaqua_smolt_input() -> SmoltOperatorInput:
    return SmoltOperatorInput(
        operator_name     = "Agaqua AS",
        org_number        = "930529591",
        facilities        = [_villa_smolt(), _olden(), _setran()],
        annual_revenue_nok = 232_248_232,
        ebitda_nok        = 70_116_262,
        equity_nok        = 39_978_809,
        operating_cf_nok  = 46_510_739,
        liquidity_nok     = 55_454_950,
        claims_history_years = 10,
        total_claims_paid_nok = 0.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Group 1: SmoltFacilityTIV
# ─────────────────────────────────────────────────────────────────────────────

class TestSmoltFacilityTIV:
    def test_building_total_sums_components(self):
        f = _villa_smolt()
        expected = (1370 + 530 + 610 + 1393 + 275) * 27000 + 20_000_000
        assert abs(f.building_total_nok - expected) < 1

    def test_property_total_includes_machinery(self):
        f = _villa_smolt()
        assert f.property_total_nok == f.building_total_nok + f.machinery_nok

    def test_total_tiv_is_sum_of_all_parts(self):
        f = _villa_smolt()
        expected = f.property_total_nok + f.avg_biomass_insured_value_nok + f.bi_sum_insured_nok
        assert abs(f.total_tiv_nok - expected) < 1

    def test_tiv_breakdown_sums_to_total(self):
        f = _villa_smolt()
        assert abs(sum(f.tiv_breakdown.values()) - f.total_tiv_nok) < 1

    def test_tiv_shares_sum_to_one(self):
        f = _villa_smolt()
        total = sum(f.tiv_shares.values())
        assert abs(total - 1.0) < 1e-6

    def test_zero_tiv_shares_returns_zeros(self):
        """Empty facility must not raise ZeroDivisionError."""
        f = SmoltFacilityTIV(facility_name="Empty")
        shares = f.tiv_shares
        assert all(v == 0.0 for v in shares.values())

    def test_building_component_value(self):
        c = BuildingComponent("Test hall", area_sqm=1000, value_per_sqm_nok=27000)
        assert c.insured_value_nok == 27_000_000

    def test_site_clearance_included_in_building_total(self):
        f = SmoltFacilityTIV(
            facility_name="X",
            building_components=[BuildingComponent("A", 100, 27000)],
            site_clearance_nok=5_000_000,
        )
        assert f.building_total_nok == 100 * 27000 + 5_000_000

    def test_facility_type_enum_values(self):
        assert FacilityType.SMOLT_RAS   == "smolt_ras"
        assert FacilityType.SMOLT_FLOW  == "smolt_flow"
        assert FacilityType.SMOLT_HYBRID == "smolt_hybrid"
        assert FacilityType.SEA_BASED   == "sea_based"


# ─────────────────────────────────────────────────────────────────────────────
# Group 2: SmoltOperatorInput
# ─────────────────────────────────────────────────────────────────────────────

class TestSmoltOperatorInput:
    def test_consolidated_breakdown_keys(self):
        op = _agaqua_smolt_input()
        bd = op.consolidated_tiv_breakdown
        assert set(bd.keys()) == {"buildings", "machinery", "biomass", "bi"}

    def test_n_facilities_correct(self):
        op = _agaqua_smolt_input()
        assert op.n_facilities == 3

    def test_total_tiv_agaqua_within_tolerance(self):
        op = _agaqua_smolt_input()
        assert abs(op.total_tiv_nok - 1_184_049_534) / 1_184_049_534 < 0.01

    def test_consolidated_buildings_agaqua(self):
        op = _agaqua_smolt_input()
        bd = op.consolidated_tiv_breakdown
        # buildings = sum of building_total_nok across all facilities
        expected = sum(f.building_total_nok for f in op.facilities)
        assert abs(bd["buildings"] - expected) < 1

    def test_consolidated_bi_agaqua(self):
        op = _agaqua_smolt_input()
        assert abs(op.consolidated_tiv_breakdown["bi"] - 430_300_000) < 1

    def test_single_facility_input(self):
        op = SmoltOperatorInput(operator_name="Test", facilities=[_villa_smolt()])
        assert op.n_facilities == 1
        assert op.total_tiv_nok == _villa_smolt().total_tiv_nok


# ─────────────────────────────────────────────────────────────────────────────
# Group 3: SmoltOperatorBuilder
# ─────────────────────────────────────────────────────────────────────────────

class TestSmoltOperatorBuilder:
    def setup_method(self):
        self.builder = SmoltOperatorBuilder()
        self.agaqua  = _agaqua_smolt_input()

    def test_build_returns_operator_input_and_alloc(self):
        op, alloc = self.builder.build(self.agaqua)
        assert op is not None
        assert isinstance(alloc, SmoltAllocationSummary)

    def test_operator_input_has_facility_type_smolt(self):
        op, _ = self.builder.build(self.agaqua)
        assert op.facility_type == "smolt"

    def test_premium_uses_howden_if_provided(self):
        _, _ = self.builder.build(self.agaqua, estimated_market_premium_nok=8_000_000)
        # Verify the pipeline accepts external premium without error
        op, _ = self.builder.build(self.agaqua, estimated_market_premium_nok=8_000_000)
        assert op.current_insurance.annual_premium == pytest.approx(8_000_000)

    def test_premium_estimated_when_no_howden(self):
        op, _ = self.builder.build(self.agaqua)
        assert op.current_insurance.annual_premium > 0

    def test_estimated_premium_above_pcc_minimum(self):
        op, _ = self.builder.build(self.agaqua)
        assert op.current_insurance.annual_premium > 5_250_000

    def test_history_discount_10_years(self):
        assert SmoltOperatorBuilder._history_discount(10) == 0.65

    def test_history_discount_zero_years(self):
        assert SmoltOperatorBuilder._history_discount(0) == 1.00

    def test_history_discount_intermediate_values(self):
        assert SmoltOperatorBuilder._history_discount(2) == 0.92
        assert SmoltOperatorBuilder._history_discount(4) == 0.85
        assert SmoltOperatorBuilder._history_discount(6) == 0.78
        assert SmoltOperatorBuilder._history_discount(8) == 0.72

    def test_inter_site_correlation_is_low(self):
        op, _ = self.builder.build(self.agaqua)
        assert op.risk_params.inter_site_correlation == pytest.approx(0.10)

    def test_scr_capacity_ratio_agaqua(self):
        _, alloc = self.builder.build(self.agaqua)
        assert alloc.scr_capacity_ratio > 1.0

    def test_alloc_summary_facility_names(self):
        _, alloc = self.builder.build(self.agaqua)
        assert "Villa Smolt AS" in alloc.facility_names
        assert "Olden Oppdrettsanlegg AS" in alloc.facility_names
        assert "Setran Settefisk AS" in alloc.facility_names

    def test_alloc_bi_share_agaqua(self):
        _, alloc = self.builder.build(self.agaqua)
        assert abs(alloc.bi_share - 0.36) < 0.02

    def test_alloc_machinery_share_agaqua(self):
        _, alloc = self.builder.build(self.agaqua)
        assert abs(alloc.machinery_share - 0.31) < 0.02

    def test_total_tiv_preserved_in_alloc(self):
        _, alloc = self.builder.build(self.agaqua)
        assert abs(alloc.total_tiv_nok - 1_184_049_534) / 1_184_049_534 < 0.01

    def test_to_allocation_summary_returns_api_model(self):
        from backend.schemas import AllocationSummary
        _, smolt_alloc = self.builder.build(self.agaqua)
        api_alloc = smolt_alloc.to_allocation_summary()
        assert isinstance(api_alloc, AllocationSummary)

    def test_to_allocation_summary_user_exposure_equals_tiv(self):
        _, smolt_alloc = self.builder.build(self.agaqua)
        api_alloc = smolt_alloc.to_allocation_summary()
        assert api_alloc.user_exposure_nok == pytest.approx(smolt_alloc.total_tiv_nok)


# ─────────────────────────────────────────────────────────────────────────────
# Group 4: Pydantic schema
# ─────────────────────────────────────────────────────────────────────────────

class TestSmoltPydanticSchema:
    def test_smolt_operator_request_validates_agaqua(self):
        from backend.api.smolt_feasibility import _agaqua_example
        req = _agaqua_example()
        assert req.operator_name == "Agaqua AS"

    def test_bi_indemnity_months_range(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SmoltFacilityInput(facility_name="X", bi_indemnity_months=5)  # < 6
        with pytest.raises(ValidationError):
            SmoltFacilityInput(facility_name="X", bi_indemnity_months=37)  # > 36

    def test_facilities_min_length_one(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SmoltOperatorRequest(operator_name="X", facilities=[])

    def test_building_component_input_area_gt_zero(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BuildingComponentInput(name="X", area_sqm=0)

    def test_smolt_facility_input_defaults(self):
        f = SmoltFacilityInput(facility_name="Test")
        assert f.bi_indemnity_months == 24
        assert f.facility_type == "smolt_ras"
        assert f.machinery_nok == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Group 5: API endpoints (TestClient)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from backend.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def agaqua_payload():
    from backend.api.smolt_feasibility import _agaqua_example
    return _agaqua_example().model_dump()


class TestSmoltAPIEndpoints:
    def test_smolt_run_endpoint_returns_200(self, client, agaqua_payload):
        agaqua_payload["model"] = {"n_simulations": 500, "generate_pdf": False}
        resp = client.post("/api/feasibility/smolt/run", json=agaqua_payload)
        assert resp.status_code == 200

    def test_smolt_example_endpoint_agaqua(self, client):
        resp = client.get("/api/feasibility/smolt/example/agaqua")
        assert resp.status_code == 200
        data = resp.json()
        assert data["operator_name"] == "Agaqua AS"
        assert data["facilities"][0]["facility_name"] == "Villa Smolt AS"

    def test_smolt_run_verdict_not_not_suitable(self, client, agaqua_payload):
        agaqua_payload["model"] = {"n_simulations": 500, "generate_pdf": False}
        resp = client.post("/api/feasibility/smolt/run", json=agaqua_payload)
        assert resp.status_code == 200
        verdict = resp.json()["baseline"]["summary"]["verdict"]
        assert verdict != "NOT_SUITABLE"

    def test_smolt_run_allocation_tiv_within_tolerance(self, client, agaqua_payload):
        agaqua_payload["model"] = {"n_simulations": 500, "generate_pdf": False}
        resp = client.post("/api/feasibility/smolt/run", json=agaqua_payload)
        assert resp.status_code == 200
        alloc = resp.json().get("allocation")
        assert alloc is not None
        tiv = alloc["user_exposure_nok"]
        assert abs(tiv - 1_184_049_534) / 1_184_049_534 < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# Group 6: Regression — sea-based pipeline unaffected
# ─────────────────────────────────────────────────────────────────────────────

class TestSeaPipelineUnaffected:
    def test_sea_based_pipeline_unchanged_after_smolt_sprint(self, client):
        """Existing /api/feasibility/example must still return a valid response."""
        resp = client.post(
            "/api/feasibility/example",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        # The example endpoint returns the example request dict, not a response
        # Verify it has the expected operator name
        assert "operator_profile" in data or "name" in data

    def test_sea_run_endpoint_still_works(self, client):
        from backend.api.feasibility import EXAMPLE_REQUEST
        payload = EXAMPLE_REQUEST.model_dump()
        payload["model_settings"]["n_simulations"] = 500
        payload["model_settings"]["generate_pdf"]  = False
        resp = client.post("/api/feasibility/run", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "baseline" in data
        assert data["baseline"]["summary"]["verdict"] != ""

    def test_facility_type_default_is_sea_based(self):
        """OperatorInput built from template still defaults to sea_based."""
        from backend.services.operator_builder import build_operator_input
        from backend.schemas import OperatorProfileInput
        op, _ = build_operator_input(OperatorProfileInput())
        assert op.facility_type == "sea_based"


# ─────────────────────────────────────────────────────────────────────────────
# Self-handled history tests — Sprint (agaqua internal logs)
# ─────────────────────────────────────────────────────────────────────────────

class TestAgaquaSelfHandledHistory:
    """Tests for the internal self-handled loss history in data/agaqua_input.json."""

    @pytest.fixture(autouse=True)
    def load_agaqua(self):
        import json, pathlib
        path = pathlib.Path("data/agaqua_input.json")
        with open(path, encoding="utf-8") as f:
            self.raw = json.load(f)
        self.hist = self.raw.get("historical_losses", [])

    def test_agaqua_self_handled_losses_sum(self):
        """Sum of all historical_losses.total_loss_nok must equal NOK 240 300."""
        total = sum(r["total_loss_nok"] for r in self.hist)
        assert total == 240_300

    def test_agaqua_reported_losses_zero(self):
        """All historical_losses entries must have reported_to_insurer=False."""
        for r in self.hist:
            assert r.get("reported_to_insurer") is False, (
                f"Year {r['year']} has reported_to_insurer={r.get('reported_to_insurer')}"
            )

    def test_history_analytics_separates_reported_vs_self_handled(self):
        """build_smolt_self_handled_summary produces correct domain split."""
        from backend.services.history_analytics import build_smolt_self_handled_summary
        summary = build_smolt_self_handled_summary(self.hist, use_history_calibration=True)
        assert summary.reported_total_nok == pytest.approx(0.0)
        assert summary.self_handled_total_nok == pytest.approx(240_300.0)
        assert summary.calibration_mode == "domain"
        assert "ras_failure" in summary.domain_frequencies
        assert summary.domain_frequencies["ras_failure"] > 0
        assert "oxygen_event" in summary.domain_frequencies
        assert summary.domain_frequencies["oxygen_event"] > 0
        assert "biological" in summary.domain_frequencies
        assert summary.domain_frequencies["biological"] > 0

    def test_agaqua_calibration_activates_with_self_handled(self):
        """With use_history_calibration=True and 10 records, calibration_active=True."""
        from backend.services.history_analytics import build_smolt_self_handled_summary
        summary = build_smolt_self_handled_summary(self.hist, use_history_calibration=True)
        assert summary.calibration_active is True
        # calibration_mode is "domain" since >3 self-handled events with multiple domains
        assert summary.calibration_mode in ("domain", "portfolio")
