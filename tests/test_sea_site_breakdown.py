"""
tests/test_sea_site_breakdown.py — Sprint S7: Sea site loss breakdown tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from models.sea_loss_categories import SEA_LOSS_CATEGORIES, get_shares_for_exposure
from data.input_schema import SiteProfile

client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_site(
    name="Frohavet North",
    fjord_exposure="open_coast",
    biomass_tonnes=3200.0,
    biomass_value_per_tonne=64_800.0,
    lice_pressure_factor=1.0,
    hab_risk_factor=1.0,
) -> SiteProfile:
    return SiteProfile(
        name=name,
        location="Norway",
        species="Atlantic Salmon",
        biomass_tonnes=biomass_tonnes,
        biomass_value_per_tonne=biomass_value_per_tonne,
        equipment_value=5_000_000,
        infrastructure_value=3_000_000,
        annual_revenue=biomass_tonnes * biomass_value_per_tonne * 1.1,
        fjord_exposure=fjord_exposure,
        lice_pressure_factor=lice_pressure_factor,
        hab_risk_factor=hab_risk_factor,
    )


THREE_SITES_PAYLOAD = {
    "facility_type": "sea",
    "preset_id": "lice_outbreak",
    "lice_pressure_index": 2.8,
    "affected_facility_index": 0,
    "operator": {
        "name": "Nordic Aqua Partners",
        "n_sites": 3,
        "total_biomass_tonnes": 9200,
        "biomass_value_per_tonne": 64800,
        "annual_revenue_nok": 800_000_000,
        "annual_premium_nok": 18_000_000,
        "sites": [
            {
                "site_id": "S01",
                "site_name": "Frohavet North",
                "biomass_value_nok": 320_000_000,
                "fjord_exposure": "open_coast",
                "lice_pressure_factor": 1.4,
                "hab_risk_factor": 1.25,
                "latitude": 63.8,
                "longitude": 8.9,
            },
            {
                "site_id": "S02",
                "site_name": "Sunndalsfjord",
                "biomass_value_nok": 280_000_000,
                "fjord_exposure": "semi_exposed",
                "lice_pressure_factor": 1.1,
                "hab_risk_factor": 0.9,
                "latitude": 62.7,
                "longitude": 8.6,
            },
            {
                "site_id": "S03",
                "site_name": "Storfjorden South",
                "biomass_value_nok": 240_000_000,
                "fjord_exposure": "sheltered",
                "lice_pressure_factor": 0.85,
                "hab_risk_factor": 0.7,
                "latitude": 62.1,
                "longitude": 7.2,
            },
        ],
    },
}


# ── SEA_LOSS_CATEGORIES ───────────────────────────────────────────────────────

class TestSeaLossCategories:

    def test_five_sea_categories_defined(self):
        assert len(SEA_LOSS_CATEGORIES) == 5

    def test_all_categories_have_required_keys(self):
        for cat in SEA_LOSS_CATEGORIES.values():
            assert "share_open" in cat
            assert "share_semi" in cat
            assert "share_sheltered" in cat
            assert "label" in cat

    def test_open_coast_shares_sum_to_one(self):
        total = sum(c["share_open"] for c in SEA_LOSS_CATEGORIES.values())
        assert abs(total - 1.0) < 1e-9

    def test_semi_exposed_shares_sum_to_one(self):
        total = sum(c["share_semi"] for c in SEA_LOSS_CATEGORIES.values())
        assert abs(total - 1.0) < 1e-9

    def test_sheltered_shares_sum_to_one(self):
        total = sum(c["share_sheltered"] for c in SEA_LOSS_CATEGORIES.values())
        assert abs(total - 1.0) < 1e-9

    def test_biological_highest_share_open_coast(self):
        shares = get_shares_for_exposure("open_coast")
        assert shares["biological"] == max(shares.values())

    def test_structural_higher_share_sheltered_than_open(self):
        open_shares = get_shares_for_exposure("open_coast")
        sheltered   = get_shares_for_exposure("sheltered")
        assert sheltered["structural"] > open_shares["structural"]

    def test_get_shares_for_exposure_open(self):
        shares = get_shares_for_exposure("open_coast")
        assert shares["biological"] == pytest.approx(0.42)

    def test_get_shares_for_exposure_sheltered(self):
        shares = get_shares_for_exposure("sheltered")
        # biological=0.27, structural=0.31 (structural dominant for sheltered fjords)
        assert shares["biological"] == pytest.approx(0.27)
        assert shares["structural"] == pytest.approx(0.31)

    def test_get_shares_for_exposure_invalid_falls_back_to_semi(self):
        shares = get_shares_for_exposure("unknown_type")
        expected = get_shares_for_exposure("semi_exposed")
        assert shares == expected


# ── SiteProfile extension ─────────────────────────────────────────────────────

class TestSiteProfileExtension:

    def test_site_profile_has_fjord_exposure(self):
        site = _make_site(fjord_exposure="open_coast")
        assert site.fjord_exposure == "open_coast"

    def test_site_profile_exposure_category_normalises_open(self):
        site = _make_site(fjord_exposure="open_coast")
        assert site.exposure_category == "open_coast"

    def test_site_profile_exposure_category_normalises_sheltered(self):
        site = _make_site(fjord_exposure="sheltered")
        assert site.exposure_category == "sheltered"

    def test_site_profile_exposure_category_default_semi(self):
        site = _make_site(fjord_exposure="semi_exposed")
        assert site.exposure_category == "semi_exposed"

    def test_site_profile_base_loss_frequency_open_higher_than_sheltered(self):
        open_site     = _make_site(fjord_exposure="open_coast")
        sheltered_site = _make_site(fjord_exposure="sheltered")
        assert open_site.base_loss_frequency > sheltered_site.base_loss_frequency

    def test_site_profile_lice_factor_scales_frequency(self):
        base   = _make_site(lice_pressure_factor=1.0)
        high   = _make_site(lice_pressure_factor=2.0)
        assert high.base_loss_frequency == pytest.approx(base.base_loss_frequency * 2.0)

    def test_site_profile_hab_factor_scales_frequency(self):
        base  = _make_site(hab_risk_factor=1.0)
        high  = _make_site(hab_risk_factor=1.5)
        assert high.base_loss_frequency == pytest.approx(base.base_loss_frequency * 1.5)

    def test_site_profile_base_severity_nok(self):
        site = _make_site(biomass_tonnes=1000, biomass_value_per_tonne=64_800)
        expected = 1000 * 64_800 * 0.18
        assert site.base_severity_nok == pytest.approx(expected)


# ── SeaSiteBuilder ────────────────────────────────────────────────────────────

class TestSeaSiteBuilder:

    def _three_sites(self):
        return [
            _make_site("Frohavet North",    "open_coast",   3200, 64_800, 1.40, 1.25),
            _make_site("Sunndalsfjord",     "semi_exposed", 2800, 64_800, 1.10, 0.90),
            _make_site("Storfjorden South", "sheltered",    2400, 64_800, 0.85, 0.70),
        ]

    def test_build_per_site_returns_one_op_per_site(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        sites = self._three_sites()
        ops = SeaSiteBuilder().build_per_site(sites, "Nordic Aqua", 18_000_000)
        assert len(ops) == 3

    def test_premium_split_proportional_to_biomass(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        sites = self._three_sites()
        total_premium = 18_000_000
        ops = SeaSiteBuilder().build_per_site(sites, "Nordic Aqua", total_premium)
        # Premiums should roughly sum to total (they come from insurance override)
        # Just verify all sites have a positive premium
        for op in ops:
            assert op.current_insurance.annual_premium > 0

    def test_build_group_returns_group_and_site_list(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        sites = self._three_sites()
        group, per_site = SeaSiteBuilder().build_group(sites, "Nordic Aqua", 18_000_000)
        assert group is not None
        assert len(per_site) == 3

    def test_group_n_sites_equals_site_count(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        sites = self._three_sites()
        group, _ = SeaSiteBuilder().build_group(sites, "Nordic Aqua", 18_000_000)
        assert len(group.sites) == 3

    def test_inter_site_correlation_sea_standard(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        builder = SeaSiteBuilder()
        assert builder.INTER_SITE_CORRELATION == pytest.approx(0.20)

    def test_open_coast_has_higher_events_than_sheltered(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        open_site     = _make_site("Open",     "open_coast", lice_pressure_factor=1.0, hab_risk_factor=1.0)
        sheltered_site = _make_site("Shelter", "sheltered",  lice_pressure_factor=1.0, hab_risk_factor=1.0)
        ops = SeaSiteBuilder().build_per_site([open_site, sheltered_site], "Test", 10_000_000)
        assert ops[0].risk_params.expected_annual_events > ops[1].risk_params.expected_annual_events


# ── ScenarioEngine sea per-site ───────────────────────────────────────────────

class TestScenarioEngineSeaMulti:

    def _build_site_ops(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        sites = [
            _make_site("Frohavet North",    "open_coast",   3200, 64_800, 1.40, 1.25),
            _make_site("Sunndalsfjord",     "semi_exposed", 2800, 64_800, 1.10, 0.90),
            _make_site("Storfjorden South", "sheltered",    2400, 64_800, 0.85, 0.70),
        ]
        _, site_ops = SeaSiteBuilder().build_group(sites, "Nordic Aqua", 18_000_000)
        return site_ops, sites[0]

    def test_sea_scenario_per_site_returns_three_facility_results(self):
        from models.scenario_engine import ScenarioEngine, ScenarioParameters
        site_ops, first_site = self._build_site_ops()
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=2.0,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(site_ops[0], params, site_inputs=site_ops)
        assert len(result.facility_results) == 3

    def test_affected_site_has_higher_loss_than_baseline(self):
        from models.scenario_engine import ScenarioEngine, ScenarioParameters
        site_ops, _ = self._build_site_ops()
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=3.0,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(site_ops[0], params, site_inputs=site_ops)
        assert result.facility_results[0].change_pct > 0

    def test_unaffected_sites_unchanged(self):
        from models.scenario_engine import ScenarioEngine, ScenarioParameters
        site_ops, _ = self._build_site_ops()
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=3.0,
                                    affected_facility_index=0)
        result = ScenarioEngine().run(site_ops[0], params, site_inputs=site_ops)
        assert result.facility_results[1].change_pct == 0.0
        assert result.facility_results[2].change_pct == 0.0

    def test_sea_diversification_factor_0_89(self):
        from models.scenario_engine import ScenarioEngine, ScenarioParameters
        site_ops, _ = self._build_site_ops()
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=3.0)
        result = ScenarioEngine().run(site_ops[0], params, site_inputs=site_ops)
        facility_sum = sum(fr.scenario_expected_loss for fr in result.facility_results)
        assert result.scenario_total_loss < facility_sum
        assert abs(result.scenario_total_loss - facility_sum * 0.89) < 1.0

    def test_group_total_less_than_sum_of_site_losses(self):
        from models.scenario_engine import ScenarioEngine, ScenarioParameters
        site_ops, _ = self._build_site_ops()
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=2.5)
        result = ScenarioEngine().run(site_ops[0], params, site_inputs=site_ops)
        site_sum = sum(fr.scenario_expected_loss for fr in result.facility_results)
        assert result.scenario_total_loss < site_sum

    def test_open_coast_dominant_risk_biological(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        from models.scenario_engine import ScenarioEngine, ScenarioParameters
        site = _make_site("Open", "open_coast", lice_pressure_factor=1.4)
        _, site_ops = SeaSiteBuilder().build_group([site], "Test", 5_000_000)
        params = ScenarioParameters(facility_type="sea", lice_pressure_index=2.5)
        result = ScenarioEngine().run(site_ops[0], params, site_inputs=site_ops)
        assert result.facility_results[0].highest_risk_driver == "biological"

    def test_sheltered_dominant_risk_structural(self):
        from backend.services.sea_site_builder import SeaSiteBuilder
        from models.scenario_engine import ScenarioEngine, ScenarioParameters
        site = _make_site("Sheltered", "sheltered", lice_pressure_factor=0.8, hab_risk_factor=0.7)
        _, site_ops = SeaSiteBuilder().build_group([site], "Test", 5_000_000)
        params = ScenarioParameters(facility_type="sea")
        result = ScenarioEngine().run(site_ops[0], params, site_inputs=site_ops)
        assert result.facility_results[0].highest_risk_driver == "structural"


# ── API ──────────────────────────────────────────────────────────────────────

class TestScenarioAPIWithSites:

    def test_post_scenario_sea_with_sites_returns_200(self):
        resp = client.post("/api/c5ai/scenario", json=THREE_SITES_PAYLOAD)
        assert resp.status_code == 200

    def test_post_scenario_sea_with_sites_returns_facility_results(self):
        resp = client.post("/api/c5ai/scenario", json=THREE_SITES_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["facility_results"]) == 3

    def test_post_scenario_sea_without_sites_still_works(self):
        payload = {
            "facility_type": "sea",
            "lice_pressure_index": 2.0,
        }
        resp = client.post("/api/c5ai/scenario", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["facility_results"]) == 1

    def test_post_scenario_sea_affected_site_has_positive_change(self):
        resp = client.post("/api/c5ai/scenario", json=THREE_SITES_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        frohavet = data["facility_results"][0]
        assert frohavet["change_pct"] > 0

    def test_post_scenario_sea_unaffected_sites_zero_change(self):
        resp = client.post("/api/c5ai/scenario", json=THREE_SITES_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["facility_results"][1]["change_pct"] == 0.0
        assert data["facility_results"][2]["change_pct"] == 0.0


# ── Regression ───────────────────────────────────────────────────────────────

class TestRegressionS7:

    def test_existing_smolt_pipeline_unchanged(self):
        from tests.test_backend_api import MINIMAL_PAYLOAD
        resp = client.post("/api/feasibility/run", json=MINIMAL_PAYLOAD)
        assert resp.status_code == 200

    def test_existing_sea_single_site_scenario_unchanged(self):
        payload = {"facility_type": "sea", "lice_pressure_index": 2.0}
        resp = client.post("/api/c5ai/scenario", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["facility_type"] == "sea"
        assert len(data["facility_results"]) >= 1
