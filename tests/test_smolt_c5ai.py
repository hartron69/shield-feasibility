"""
Sprint S3 – Smolt C5AI+ forecasters and alert rules.

Covers:
  - RASMonitoringData / SmoltC5AIInput (data models)
  - RASWaterQualityForecaster
  - BiofilterForecaster
  - SmoltHealthForecaster
  - PowerSupplyForecaster
  - SmoltAlertRule / smolt_alert_rules (15 rules)
  - evaluate_smolt_rules integration

28+ tests in 7 groups.
"""

from __future__ import annotations

import pytest

from c5ai_plus.data_models.smolt_biological_input import RASMonitoringData, SmoltC5AIInput
from c5ai_plus.data_models.forecast_schema import RiskTypeForecast
from c5ai_plus.forecasting.ras_water_quality_forecaster import RASWaterQualityForecaster
from c5ai_plus.forecasting.biofilter_forecaster import BiofilterForecaster
from c5ai_plus.forecasting.smolt_health_forecaster import SmoltHealthForecaster
from c5ai_plus.forecasting.power_supply_forecaster import PowerSupplyForecaster
from c5ai_plus.alerts.smolt_alert_rules import (
    SmoltAlertRule,
    ALL_SMOLT_RULES,
    ALL_SMOLT_RULES_FLAT,
    RAS_WATER_QUALITY_RULES,
    BIOFILTER_RULES,
    SMOLT_HEALTH_RULES,
    POWER_SUPPLY_RULES,
    evaluate_smolt_rules,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _minimal_site(**kwargs) -> RASMonitoringData:
    """Return a RASMonitoringData with all optional fields None unless overridden."""
    defaults = dict(
        site_id        = "TEST_S01",
        site_name      = "Test Facility",
        timestamp_iso  = "2026-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return RASMonitoringData(**defaults)


def _healthy_site() -> RASMonitoringData:
    """All readings well within safe limits."""
    return _minimal_site(
        dissolved_oxygen_mg_l          = 9.0,
        water_temp_c                   = 14.0,
        nitrate_umol_l                 = 5.0,
        nitrite_mg_l                   = 0.02,
        ammonia_mg_l                   = 0.1,
        days_since_last_filter_maintenance = 30,
        biofilter_efficiency_pct       = 95.0,
        backup_power_hours             = 8.0,
        grid_reliability_score         = 0.97,
        last_power_test_days           = 10,
        cataract_prevalence_pct        = 1.0,
        agd_score_mean                 = 0.5,
        mortality_rate_7d_pct          = 0.1,
        co2_ppm                        = 8.0,
        stocking_density_kg_m3         = 50.0,
        biomass_kg                     = 200_000.0,
    )


# ════════════════════════════════════════════════════════════════════════════
# Group 1 — Data models
# ════════════════════════════════════════════════════════════════════════════

class TestRASMonitoringData:
    def test_minimal_construction(self):
        site = _minimal_site()
        assert site.site_id == "TEST_S01"
        assert site.dissolved_oxygen_mg_l is None

    def test_as_dict_contains_site_id(self):
        site = _minimal_site()
        d = site.as_dict()
        assert "site_id" in d
        assert d["site_id"] == "TEST_S01"

    def test_as_dict_all_optional_none(self):
        site = _minimal_site()
        d = site.as_dict()
        assert d["dissolved_oxygen_mg_l"] is None
        assert d["biomass_kg"] is None

    def test_smolt_c5ai_input_empty_sites(self):
        inp = SmoltC5AIInput(operator_id="OP01", operator_name="Test AS")
        assert inp.sites == []
        assert inp.forecast_years == 5

    def test_smolt_c5ai_input_with_sites(self):
        s = _minimal_site()
        inp = SmoltC5AIInput(operator_id="OP01", operator_name="Test AS", sites=[s])
        assert len(inp.sites) == 1


# ════════════════════════════════════════════════════════════════════════════
# Group 2 — RASWaterQualityForecaster
# ════════════════════════════════════════════════════════════════════════════

class TestRASWaterQualityForecaster:
    def setup_method(self):
        self.f = RASWaterQualityForecaster()

    def test_no_data_returns_base_prior(self):
        site = _minimal_site()
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability == pytest.approx(0.10)
        assert results[0].data_quality_flag == "PRIOR_ONLY"

    def test_no_data_confidence_low(self):
        site = _minimal_site()
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].confidence_score == pytest.approx(0.20)

    def test_o2_critical_raises_probability(self):
        site = _minimal_site(dissolved_oxygen_mg_l=5.0)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.40

    def test_o2_warning_raises_probability_moderately(self):
        site = _minimal_site(dissolved_oxygen_mg_l=7.0)
        results = self.f.forecast(site, forecast_years=1)
        prob = results[0].event_probability
        assert 0.20 < prob <= 0.40

    def test_temp_high_adds_risk(self):
        site = _minimal_site(water_temp_c=20.0)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.10

    def test_five_year_forecast_length(self):
        site = _minimal_site()
        results = self.f.forecast(site, forecast_years=5)
        assert len(results) == 5

    def test_forecast_returns_risk_type_forecast(self):
        site = _minimal_site()
        results = self.f.forecast(site, forecast_years=1)
        assert isinstance(results[0], RiskTypeForecast)
        assert results[0].risk_type == "ras_water_quality"

    def test_healthy_site_low_probability(self):
        results = self.f.forecast(_healthy_site(), forecast_years=1)
        assert results[0].event_probability < 0.15

    def test_probability_capped_at_one(self):
        site = _minimal_site(
            dissolved_oxygen_mg_l=4.0,
            water_temp_c=22.0,
            nitrate_umol_l=20.0,
        )
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability <= 1.0


# ════════════════════════════════════════════════════════════════════════════
# Group 3 — BiofilterForecaster
# ════════════════════════════════════════════════════════════════════════════

class TestBiofilterForecaster:
    def setup_method(self):
        self.f = BiofilterForecaster()

    def test_no_data_returns_base_prior(self):
        site = _minimal_site()
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability == pytest.approx(0.12)
        assert results[0].data_quality_flag == "PRIOR_ONLY"

    def test_nitrite_elevated_raises_risk(self):
        site = _minimal_site(nitrite_mg_l=0.5)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.30

    def test_maintenance_overdue_raises_risk(self):
        site = _minimal_site(days_since_last_filter_maintenance=120)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.30

    def test_efficiency_low_raises_risk(self):
        site = _minimal_site(biofilter_efficiency_pct=60.0)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.25

    def test_risk_type_is_biofilter(self):
        results = self.f.forecast(_minimal_site(), forecast_years=1)
        assert results[0].risk_type == "biofilter"

    def test_probability_capped_at_one(self):
        site = _minimal_site(
            nitrite_mg_l=2.0,
            ammonia_mg_l=5.0,
            days_since_last_filter_maintenance=200,
            biofilter_efficiency_pct=40.0,
            nitrate_umol_l=30.0,
        )
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability <= 1.0


# ════════════════════════════════════════════════════════════════════════════
# Group 4 — SmoltHealthForecaster
# ════════════════════════════════════════════════════════════════════════════

class TestSmoltHealthForecaster:
    def setup_method(self):
        self.f = SmoltHealthForecaster()

    def test_no_data_returns_base_prior(self):
        site = _minimal_site()
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability == pytest.approx(0.08)
        assert results[0].data_quality_flag == "PRIOR_ONLY"

    def test_mortality_elevated_is_dominant(self):
        site = _minimal_site(mortality_rate_7d_pct=1.5)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.35

    def test_cataract_high_raises_risk(self):
        site = _minimal_site(cataract_prevalence_pct=10.0)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.25

    def test_agd_elevated_raises_risk(self):
        site = _minimal_site(agd_score_mean=2.5)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.20

    def test_co2_high_adds_risk(self):
        site = _minimal_site(co2_ppm=20.0)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.10

    def test_risk_type_is_smolt_health(self):
        results = self.f.forecast(_minimal_site(), forecast_years=1)
        assert results[0].risk_type == "smolt_health"

    def test_probability_capped_at_one(self):
        site = _minimal_site(
            cataract_prevalence_pct=30.0,
            agd_score_mean=4.0,
            mortality_rate_7d_pct=5.0,
            co2_ppm=40.0,
            stocking_density_kg_m3=120.0,
        )
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability <= 1.0


# ════════════════════════════════════════════════════════════════════════════
# Group 5 — PowerSupplyForecaster
# ════════════════════════════════════════════════════════════════════════════

class TestPowerSupplyForecaster:
    def setup_method(self):
        self.f = PowerSupplyForecaster()

    def test_no_data_returns_base_prior(self):
        site = _minimal_site()
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability == pytest.approx(0.05)
        assert results[0].data_quality_flag == "PRIOR_ONLY"

    def test_inadequate_backup_is_critical(self):
        site = _minimal_site(backup_power_hours=1.0)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.30

    def test_unreliable_grid_raises_risk(self):
        site = _minimal_site(grid_reliability_score=0.60)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.20

    def test_test_overdue_raises_risk(self):
        site = _minimal_site(last_power_test_days=60)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability > 0.15

    def test_risk_type_is_power_supply(self):
        results = self.f.forecast(_minimal_site(), forecast_years=1)
        assert results[0].risk_type == "power_supply"

    def test_two_signals_sufficient_flag(self):
        site = _minimal_site(backup_power_hours=2.0, grid_reliability_score=0.70)
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].data_quality_flag == "SUFFICIENT"

    def test_probability_capped_at_one(self):
        site = _minimal_site(
            backup_power_hours=0.5,
            grid_reliability_score=0.40,
            last_power_test_days=365,
        )
        results = self.f.forecast(site, forecast_years=1)
        assert results[0].event_probability <= 1.0


# ════════════════════════════════════════════════════════════════════════════
# Group 6 — Smolt alert rules (15 rules)
# ════════════════════════════════════════════════════════════════════════════

class TestSmoltAlertRules:
    def test_15_smolt_alert_rules_defined(self):
        assert len(ALL_SMOLT_RULES_FLAT) == 15

    def test_all_rules_are_smolt_alert_rule_instances(self):
        for rule in ALL_SMOLT_RULES_FLAT:
            assert isinstance(rule, SmoltAlertRule)

    def test_rule_ids_are_unique(self):
        ids = [r.rule_id for r in ALL_SMOLT_RULES_FLAT]
        assert len(ids) == len(set(ids))

    def test_four_risk_categories(self):
        assert set(ALL_SMOLT_RULES.keys()) == {
            "ras_water_quality", "biofilter", "smolt_health", "power_supply"
        }

    def test_water_quality_has_4_rules(self):
        assert len(RAS_WATER_QUALITY_RULES) == 4

    def test_biofilter_has_4_rules(self):
        assert len(BIOFILTER_RULES) == 4

    def test_smolt_health_has_4_rules(self):
        assert len(SMOLT_HEALTH_RULES) == 4

    def test_power_supply_has_3_rules(self):
        assert len(POWER_SUPPLY_RULES) == 3

    def test_weights_per_risk_type_sum_leq_one(self):
        for risk_type, rules in ALL_SMOLT_RULES.items():
            total = sum(r.weight for r in rules)
            assert total <= 1.0 + 1e-9, (
                f"Weights for {risk_type} sum to {total:.3f} > 1.0"
            )

    def test_o2_critical_triggers_below_6(self):
        site = _minimal_site(dissolved_oxygen_mg_l=5.5)
        rule = next(r for r in RAS_WATER_QUALITY_RULES if r.rule_id == "ras_o2_critical")
        assert rule.triggered_when(site) is True

    def test_o2_critical_does_not_trigger_above_6(self):
        site = _minimal_site(dissolved_oxygen_mg_l=6.5)
        rule = next(r for r in RAS_WATER_QUALITY_RULES if r.rule_id == "ras_o2_critical")
        assert rule.triggered_when(site) is False

    def test_o2_warning_triggers_between_6_and_7_5(self):
        site = _minimal_site(dissolved_oxygen_mg_l=7.0)
        rule = next(r for r in RAS_WATER_QUALITY_RULES if r.rule_id == "ras_o2_warning")
        assert rule.triggered_when(site) is True

    def test_o2_warning_does_not_trigger_above_7_5(self):
        site = _minimal_site(dissolved_oxygen_mg_l=8.0)
        rule = next(r for r in RAS_WATER_QUALITY_RULES if r.rule_id == "ras_o2_warning")
        assert rule.triggered_when(site) is False

    def test_maintenance_overdue_triggers_above_90_days(self):
        site = _minimal_site(days_since_last_filter_maintenance=100)
        rule = next(r for r in BIOFILTER_RULES if r.rule_id == "biofilter_maintenance_overdue")
        assert rule.triggered_when(site) is True

    def test_maintenance_ok_does_not_trigger(self):
        site = _minimal_site(days_since_last_filter_maintenance=45)
        rule = next(r for r in BIOFILTER_RULES if r.rule_id == "biofilter_maintenance_overdue")
        assert rule.triggered_when(site) is False

    def test_missing_field_never_triggers(self):
        """None sensor value must never cause a false positive."""
        site = _minimal_site()  # all fields None
        for rule in ALL_SMOLT_RULES_FLAT:
            assert rule.triggered_when(site) is False, (
                f"Rule {rule.rule_id} fired on all-None site"
            )

    def test_power_backup_inadequate_triggers_below_4h(self):
        site = _minimal_site(backup_power_hours=2.0)
        rule = next(r for r in POWER_SUPPLY_RULES if r.rule_id == "power_backup_inadequate")
        assert rule.triggered_when(site) is True

    def test_power_backup_ok_does_not_trigger(self):
        site = _minimal_site(backup_power_hours=6.0)
        rule = next(r for r in POWER_SUPPLY_RULES if r.rule_id == "power_backup_inadequate")
        assert rule.triggered_when(site) is False


# ════════════════════════════════════════════════════════════════════════════
# Group 7 — evaluate_smolt_rules integration
# ════════════════════════════════════════════════════════════════════════════

class TestEvaluateSmoltRules:
    def test_adequate_conditions_trigger_no_rules(self):
        result = evaluate_smolt_rules(_healthy_site())
        total_triggered = sum(len(v) for v in result.values())
        assert total_triggered == 0

    def test_critical_o2_triggers_ras_water_quality(self):
        site = _minimal_site(dissolved_oxygen_mg_l=5.0)
        result = evaluate_smolt_rules(site)
        ids = [r.rule_id for r in result["ras_water_quality"]]
        assert "ras_o2_critical" in ids

    def test_multiple_biofilter_signals_all_trigger(self):
        site = _minimal_site(
            nitrite_mg_l=0.5,
            ammonia_mg_l=1.0,
            days_since_last_filter_maintenance=150,
            biofilter_efficiency_pct=60.0,
        )
        result = evaluate_smolt_rules(site)
        assert len(result["biofilter"]) == 4

    def test_result_keys_match_all_smolt_rules(self):
        result = evaluate_smolt_rules(_minimal_site())
        assert set(result.keys()) == set(ALL_SMOLT_RULES.keys())

    def test_no_cross_contamination_between_categories(self):
        """A biofilter signal must not appear in ras_water_quality results."""
        site = _minimal_site(nitrite_mg_l=0.5)
        result = evaluate_smolt_rules(site)
        wq_ids = [r.rule_id for r in result["ras_water_quality"]]
        assert "biofilter_nitrite_elevated" not in wq_ids
