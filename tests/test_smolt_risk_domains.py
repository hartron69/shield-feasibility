"""
Test suite for Sprint S2: RAS risk domains and Monte Carlo calibration.
32 tests covering RASRiskDomain, SmoltMCCalibrator, scenario presets,
and integration with MonteCarloEngine.
"""

from __future__ import annotations

import pytest

from risk_domains.ras_systems import RAS_PERILS, RASPerilProfile, RASRiskDomain
from models.smolt_calibration import SmoltMCCalibrator, SmoltMCParameters
from config.smolt_scenarios import SMOLT_SCENARIO_PRESETS, SmoltScenarioPreset
from data.input_schema import (
    BuildingComponent,
    FacilityType,
    SmoltFacilityTIV,
    SmoltOperatorInput,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _agaqua_smolt_input() -> SmoltOperatorInput:
    villa = SmoltFacilityTIV(
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
    )
    olden = SmoltFacilityTIV(
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
    )
    setran = SmoltFacilityTIV(
        facility_name="Setran Settefisk AS",
        facility_type=FacilityType.SMOLT_FLOW,
        building_components=[
            BuildingComponent("Hall A",         280, 27000),
            BuildingComponent("Vannbehandling", 170, 27000),
            BuildingComponent("Hall B",         715, 27000),
            BuildingComponent("Hall C",         979, 27000),
        ],
        site_clearance_nok            = 15_000_000,
        machinery_nok                 = 45_000_000,
        avg_biomass_insured_value_nok = 13_287_917,
        bi_sum_insured_nok            = 85_100_000,
    )
    return SmoltOperatorInput(
        operator_name        = "Agaqua AS",
        facilities           = [villa, olden, setran],
        annual_revenue_nok   = 232_248_232,
        ebitda_nok           = 70_116_262,
        equity_nok           = 39_978_809,
        operating_cf_nok     = 46_510_739,
        liquidity_nok        = 55_454_950,
        claims_history_years = 10,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Group 1: RASRiskDomain
# ─────────────────────────────────────────────────────────────────────────────

class TestRASRiskDomain:
    def test_aggregate_frequency_sum_of_all_perils(self):
        """Undiscounted aggregate frequency = sum of individual base frequencies."""
        ras = RASRiskDomain(property_tiv_nok=500_000_000, claims_free_years=0)
        expected_raw = sum(p.annual_frequency_base for p in RAS_PERILS.values())
        assert ras.aggregate_frequency == pytest.approx(expected_raw, rel=1e-6)

    def test_history_discount_10_years_reduces_frequency(self):
        ras_clean  = RASRiskDomain(500_000_000, claims_free_years=10)
        ras_no_hist = RASRiskDomain(500_000_000, claims_free_years=0)
        assert ras_clean.aggregate_frequency < ras_no_hist.aggregate_frequency

    def test_history_discount_values(self):
        assert RASRiskDomain._history_discount(0)  == 1.00
        assert RASRiskDomain._history_discount(3)  == 0.85
        assert RASRiskDomain._history_discount(7)  == 0.72
        assert RASRiskDomain._history_discount(10) == 0.65

    def test_expected_annual_loss_positive_for_nonzero_tiv(self):
        ras = RASRiskDomain(300_000_000)
        assert ras.expected_annual_loss_nok > 0

    def test_expected_annual_loss_zero_for_zero_tiv(self):
        ras = RASRiskDomain(0.0)
        assert ras.expected_annual_loss_nok == 0.0

    def test_catastrophe_scenario_returns_dict_with_required_keys(self):
        ras = RASRiskDomain(500_000_000)
        cat = ras.catastrophe_scenario()
        assert "combined_probability" in cat
        assert "severity_pct_of_property" in cat
        assert "estimated_loss_nok" in cat

    def test_catastrophe_estimated_loss_positive(self):
        ras = RASRiskDomain(500_000_000)
        assert ras.catastrophe_scenario()["estimated_loss_nok"] > 0

    def test_zero_claims_free_years_no_discount(self):
        ras = RASRiskDomain(100_000_000, claims_free_years=0)
        assert ras.discount == 1.00

    def test_inter_facility_correlation_is_low(self):
        """All perils must have inter_facility_correlation < 0.10."""
        for key, peril in RAS_PERILS.items():
            assert peril.inter_facility_correlation < 0.10, (
                f"{key} inter_facility_correlation = {peril.inter_facility_correlation}"
            )

    def test_six_perils_defined(self):
        assert len(RAS_PERILS) == 6

    def test_all_perils_have_bi_trigger_field(self):
        for peril in RAS_PERILS.values():
            assert isinstance(peril.bi_trigger, bool)


# ─────────────────────────────────────────────────────────────────────────────
# Group 2: SmoltMCCalibrator
# ─────────────────────────────────────────────────────────────────────────────

class TestSmoltMCCalibrator:
    def setup_method(self):
        self.calibrator = SmoltMCCalibrator()
        self.agaqua     = _agaqua_smolt_input()

    def test_calibrate_returns_smolt_mc_parameters(self):
        params = self.calibrator.calibrate(self.agaqua)
        assert isinstance(params, SmoltMCParameters)

    def test_calibrated_frequency_lower_for_claims_free_operator(self):
        clean = self.agaqua
        dirty = SmoltOperatorInput(
            operator_name="DirtyOp",
            facilities=clean.facilities,
            claims_history_years=0,
        )
        p_clean = self.calibrator.calibrate(clean)
        p_dirty = self.calibrator.calibrate(dirty)
        assert p_clean.expected_annual_events < p_dirty.expected_annual_events

    def test_calibrated_frequency_agaqua_within_range(self):
        """0.30 < expected_annual_events < 1.50 for Agaqua (10 years claims-free)."""
        params = self.calibrator.calibrate(self.agaqua)
        assert 0.30 < params.expected_annual_events < 1.50

    def test_calibrated_severity_positive(self):
        params = self.calibrator.calibrate(self.agaqua)
        assert params.mean_loss_severity_nok > 0

    def test_bi_heavy_portfolio_increases_cv(self):
        """Agaqua (BI-share ≈ 36%): cv_loss_severity > 0.79."""
        params = self.calibrator.calibrate(self.agaqua)
        assert params.cv_loss_severity > 0.79

    def test_inter_site_corr_decreases_with_more_facilities(self):
        single = SmoltOperatorInput(
            operator_name="One",
            facilities=self.agaqua.facilities[:1],
        )
        triple = self.agaqua
        p1 = self.calibrator.calibrate(single)
        p3 = self.calibrator.calibrate(triple)
        assert p1.inter_site_correlation > p3.inter_site_correlation

    def test_dominant_peril_is_ras_peril(self):
        params = self.calibrator.calibrate(self.agaqua)
        assert params.dominant_peril in RAS_PERILS

    def test_dominant_peril_is_oxygen_collapse(self):
        """oxygen_collapse has highest expected loss contribution (freq × severity)."""
        params = self.calibrator.calibrate(self.agaqua)
        assert params.dominant_peril == "oxygen_collapse"

    def test_history_discount_applied_is_065_for_agaqua(self):
        params = self.calibrator.calibrate(self.agaqua)
        assert params.history_discount_applied == pytest.approx(0.65)

    def test_catastrophe_params_are_fixed(self):
        params = self.calibrator.calibrate(self.agaqua)
        assert params.catastrophe_probability == pytest.approx(0.03)
        assert params.catastrophe_multiplier  == pytest.approx(4.5)


# ─────────────────────────────────────────────────────────────────────────────
# Group 3: Scenario presets
# ─────────────────────────────────────────────────────────────────────────────

class TestSmoltScenarioPresets:
    def test_four_smolt_presets_defined(self):
        assert len(SMOLT_SCENARIO_PRESETS) == 4

    def test_all_presets_have_unique_ids(self):
        ids = [p.id for p in SMOLT_SCENARIO_PRESETS]
        assert len(ids) == len(set(ids))

    def test_ras_collapse_has_highest_loss_multiplier_among_likely_scenarios(self):
        """Among presets with frequency_multiplier == 1.0, ras_total_collapse is highest."""
        likely = [
            p for p in SMOLT_SCENARIO_PRESETS
            if p.parameter_overrides.get("frequency_multiplier", 1.0) == 1.0
        ]
        collapse = next(p for p in likely if p.id == "ras_total_collapse")
        max_mult = max(p.parameter_overrides["loss_multiplier"] for p in likely)
        assert collapse.parameter_overrides["loss_multiplier"] == max_mult

    def test_water_contamination_has_lowest_frequency_multiplier(self):
        wc = next(p for p in SMOLT_SCENARIO_PRESETS if p.id == "water_contamination")
        min_freq = min(
            p.parameter_overrides.get("frequency_multiplier", 1.0)
            for p in SMOLT_SCENARIO_PRESETS
        )
        assert wc.parameter_overrides["frequency_multiplier"] == min_freq

    def test_all_presets_trigger_bi(self):
        for preset in SMOLT_SCENARIO_PRESETS:
            assert preset.parameter_overrides.get("bi_trigger") is True, (
                f"Preset '{preset.id}' does not have bi_trigger=True"
            )

    def test_all_presets_are_frozen(self):
        """SmoltScenarioPreset is frozen; overrides must not be mutated."""
        preset = SMOLT_SCENARIO_PRESETS[0]
        with pytest.raises((AttributeError, TypeError)):
            preset.id = "hacked"  # type: ignore[misc]

    def test_preset_ids_match_expected(self):
        ids = {p.id for p in SMOLT_SCENARIO_PRESETS}
        assert ids == {
            "ras_total_collapse",
            "oxygen_crisis",
            "water_contamination",
            "extended_power_outage",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Group 4: Integration — SmoltMCCalibrator → MonteCarloEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestSmoltMCIntegration:
    def test_calibrated_parameters_accepted_by_mc_engine(self):
        """MC engine runs without exception using smolt-calibrated OperatorInput."""
        from backend.services.smolt_operator_builder import SmoltOperatorBuilder
        from models.monte_carlo import MonteCarloEngine

        agaqua = _agaqua_smolt_input()
        op_input, _ = SmoltOperatorBuilder().build(agaqua)

        engine = MonteCarloEngine(op_input, n_simulations=200)
        sim = engine.run()
        assert sim is not None

    def test_mc_output_has_positive_var_99_5(self):
        from backend.services.smolt_operator_builder import SmoltOperatorBuilder
        from models.monte_carlo import MonteCarloEngine

        agaqua = _agaqua_smolt_input()
        op_input, _ = SmoltOperatorBuilder().build(agaqua)
        sim = MonteCarloEngine(op_input, n_simulations=500).run()
        assert sim.var_995 > 0

    def test_agaqua_var_99_5_below_bi_sum(self):
        """VaR 99.5% must be below total BI exposure (NOK 430.3M)."""
        from backend.services.smolt_operator_builder import SmoltOperatorBuilder
        from models.monte_carlo import MonteCarloEngine

        agaqua = _agaqua_smolt_input()
        op_input, _ = SmoltOperatorBuilder().build(agaqua)
        sim = MonteCarloEngine(op_input, n_simulations=1000).run()
        assert sim.var_995 < 430_300_000

    def test_sea_domain_files_unaffected(self):
        """Existing sea-based risk domain files must still import cleanly."""
        from risk_domains.biological import BiologicalRiskDomain
        from risk_domains.structural import StructuralRiskDomain
        from risk_domains.environmental import EnvironmentalRiskDomain
        from risk_domains.operational import OperationalRiskDomain
        assert BiologicalRiskDomain is not None
        assert StructuralRiskDomain is not None
        assert EnvironmentalRiskDomain is not None
        assert OperationalRiskDomain is not None
