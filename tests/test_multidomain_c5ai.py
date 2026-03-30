"""
Tests for the Multi-Domain C5AI+ Extension.

Covers structural, environmental, operational inputs/simulators/forecasters,
multi-domain alert rules, and the alert engine domain field.
Target: 56 new tests.
"""

import pytest

# ── Structural ─────────────────────────────────────────────────────────────────

from c5ai_plus.structural.inputs import StructuralSiteInput
from c5ai_plus.structural.simulator import MockStructuralSimulator
from c5ai_plus.structural.forecaster import StructuralForecaster
from c5ai_plus.structural.rules import STRUCTURAL_RULES


class TestStructuralInputs:
    def test_dataclass_creation(self):
        inp = StructuralSiteInput(
            site_id='S1',
            net_age_years=2.0,
            net_strength_residual_pct=85.0,
            mooring_inspection_score=0.8,
            deformation_load_index=0.3,
            anchor_line_condition=0.9,
            last_inspection_days_ago=60,
        )
        assert inp.site_id == 'S1'
        assert inp.net_age_years == 2.0

    def test_to_dict_round_trip(self):
        inp = StructuralSiteInput('S1', 2.0, 85.0, 0.8, 0.3, 0.9, 60)
        d = inp.to_dict()
        inp2 = StructuralSiteInput.from_dict(d)
        assert inp2.site_id == inp.site_id
        assert inp2.net_strength_residual_pct == inp.net_strength_residual_pct

    def test_simulator_known_site(self):
        sim = MockStructuralSimulator()
        inp = sim.simulate('KH_S01')
        assert isinstance(inp, StructuralSiteInput)
        assert inp.site_id == 'KH_S01'

    def test_simulator_all_sites(self):
        sim = MockStructuralSimulator()
        all_sites = sim.simulate_all()
        assert len(all_sites) == 3
        assert 'KH_S01' in all_sites

    def test_simulator_unknown_site_raises(self):
        with pytest.raises(ValueError):
            MockStructuralSimulator().simulate('UNKNOWN')

    def test_simulator_field_ranges(self):
        sim = MockStructuralSimulator()
        for site_id, inp in sim.simulate_all().items():
            assert 0.0 <= inp.mooring_inspection_score <= 1.0
            assert 0.0 <= inp.deformation_load_index <= 1.0
            assert 0.0 <= inp.anchor_line_condition <= 1.0
            assert 0.0 <= inp.net_strength_residual_pct <= 100.0
            assert inp.last_inspection_days_ago >= 0


# ── Environmental ──────────────────────────────────────────────────────────────

from c5ai_plus.environmental.inputs import EnvironmentalSiteInput
from c5ai_plus.environmental.simulator import MockEnvironmentalSimulator
from c5ai_plus.environmental.forecaster import EnvironmentalForecaster
from c5ai_plus.environmental.rules import ENVIRONMENTAL_RULES


class TestEnvironmentalInputs:
    def test_dataclass_creation(self):
        inp = EnvironmentalSiteInput(
            site_id='S2',
            dissolved_oxygen_mg_l=8.5,
            oxygen_saturation_pct=95.0,
            surface_temp_c=12.0,
            current_speed_ms=0.4,
            significant_wave_height_m=1.2,
            ice_risk_score=0.02,
            site_exposure_class='semi',
        )
        assert inp.site_id == 'S2'
        assert inp.dissolved_oxygen_mg_l == 8.5

    def test_to_dict_round_trip(self):
        inp = EnvironmentalSiteInput('S2', 8.5, 95.0, 12.0, 0.4, 1.2, 0.02, 'semi')
        d = inp.to_dict()
        inp2 = EnvironmentalSiteInput.from_dict(d)
        assert inp2.site_exposure_class == 'semi'

    def test_simulator_known_site(self):
        sim = MockEnvironmentalSimulator()
        inp = sim.simulate('KH_S02')
        assert isinstance(inp, EnvironmentalSiteInput)
        assert inp.site_id == 'KH_S02'

    def test_simulator_all_sites(self):
        all_sites = MockEnvironmentalSimulator().simulate_all()
        assert len(all_sites) == 3

    def test_simulator_unknown_site_raises(self):
        with pytest.raises(ValueError):
            MockEnvironmentalSimulator().simulate('NOPE')

    def test_simulator_field_ranges(self):
        for sid, inp in MockEnvironmentalSimulator().simulate_all().items():
            assert 0.0 <= inp.ice_risk_score <= 1.0
            assert inp.dissolved_oxygen_mg_l > 0
            assert inp.current_speed_ms >= 0
            assert inp.significant_wave_height_m >= 0


# ── Operational ────────────────────────────────────────────────────────────────

from c5ai_plus.operational.inputs import OperationalSiteInput
from c5ai_plus.operational.simulator import MockOperationalSimulator
from c5ai_plus.operational.forecaster import OperationalForecaster
from c5ai_plus.operational.rules import OPERATIONAL_RULES


class TestOperationalInputs:
    def test_dataclass_creation(self):
        inp = OperationalSiteInput(
            site_id='S3',
            staffing_score=0.85,
            training_compliance_pct=90.0,
            incident_rate_12m=0.3,
            maintenance_backlog_score=0.15,
            critical_ops_frequency_per_month=3.0,
            equipment_readiness_score=0.88,
        )
        assert inp.staffing_score == 0.85

    def test_to_dict_round_trip(self):
        inp = OperationalSiteInput('S3', 0.85, 90.0, 0.3, 0.15, 3.0, 0.88)
        inp2 = OperationalSiteInput.from_dict(inp.to_dict())
        assert inp2.training_compliance_pct == 90.0

    def test_simulator_known_site(self):
        sim = MockOperationalSimulator()
        inp = sim.simulate('KH_S03')
        assert isinstance(inp, OperationalSiteInput)
        assert inp.site_id == 'KH_S03'

    def test_simulator_all_sites(self):
        assert len(MockOperationalSimulator().simulate_all()) == 3

    def test_simulator_unknown_site_raises(self):
        with pytest.raises(ValueError):
            MockOperationalSimulator().simulate('UNKNOWN')

    def test_simulator_field_ranges(self):
        for sid, inp in MockOperationalSimulator().simulate_all().items():
            assert 0.0 <= inp.staffing_score <= 1.0
            assert 0.0 <= inp.equipment_readiness_score <= 1.0
            assert 0.0 <= inp.training_compliance_pct <= 100.0
            assert inp.incident_rate_12m >= 0


# ── Structural Forecaster ──────────────────────────────────────────────────────

_HIGH_RISK_STRUCTURAL = StructuralSiteInput(
    site_id='TEST',
    net_age_years=5.0,
    net_strength_residual_pct=55.0,
    mooring_inspection_score=0.40,
    deformation_load_index=0.75,
    anchor_line_condition=0.35,
    last_inspection_days_ago=250,
)
_LOW_RISK_STRUCTURAL = StructuralSiteInput(
    site_id='TEST',
    net_age_years=0.5,
    net_strength_residual_pct=98.0,
    mooring_inspection_score=0.95,
    deformation_load_index=0.10,
    anchor_line_condition=0.95,
    last_inspection_days_ago=30,
)
_META = {'biomass_value_nok': 100_000_000}


class TestStructuralForecaster:
    def test_returns_five_subtypes(self):
        forecasts = StructuralForecaster().forecast(_HIGH_RISK_STRUCTURAL, _META)
        risk_types = {f['risk_type'] for f in forecasts}
        assert risk_types == {'mooring_failure', 'net_integrity', 'cage_structural', 'deformation', 'anchor_deterioration'}

    def test_probabilities_in_range(self):
        for f in StructuralForecaster().forecast(_HIGH_RISK_STRUCTURAL, _META):
            assert 0.0 <= f['event_probability'] <= 1.0

    def test_losses_positive(self):
        for f in StructuralForecaster().forecast(_HIGH_RISK_STRUCTURAL, _META):
            assert f['expected_loss_mean'] > 0
            assert f['expected_loss_p50'] > 0
            assert f['expected_loss_p90'] >= f['expected_loss_p50']

    def test_drivers_non_empty_for_high_risk(self):
        for f in StructuralForecaster().forecast(_HIGH_RISK_STRUCTURAL, _META):
            assert len(f['drivers']) >= 1

    def test_high_risk_higher_probability(self):
        high = {f['risk_type']: f['event_probability'] for f in StructuralForecaster().forecast(_HIGH_RISK_STRUCTURAL, _META)}
        low = {f['risk_type']: f['event_probability'] for f in StructuralForecaster().forecast(_LOW_RISK_STRUCTURAL, _META)}
        assert high['mooring_failure'] > low['mooring_failure']
        assert high['net_integrity'] > low['net_integrity']

    def test_confidence_score_range(self):
        for f in StructuralForecaster().forecast(_HIGH_RISK_STRUCTURAL, _META):
            assert 0.0 <= f['confidence_score'] <= 1.0

    def test_model_used_field(self):
        for f in StructuralForecaster().forecast(_HIGH_RISK_STRUCTURAL, _META):
            assert f['model_used'] == 'score_structural'

    def test_demo_site_simulation(self):
        sim = MockStructuralSimulator()
        forecaster = StructuralForecaster()
        inp = sim.simulate('KH_S01')
        forecasts = forecaster.forecast(inp, _META)
        assert len(forecasts) == 5


# ── Environmental Forecaster ───────────────────────────────────────────────────

_HIGH_RISK_ENV = EnvironmentalSiteInput(
    site_id='TEST',
    dissolved_oxygen_mg_l=5.5,
    oxygen_saturation_pct=65.0,
    surface_temp_c=18.5,
    current_speed_ms=0.90,
    significant_wave_height_m=3.2,
    ice_risk_score=0.60,
    site_exposure_class='open',
)
_LOW_RISK_ENV = EnvironmentalSiteInput(
    site_id='TEST',
    dissolved_oxygen_mg_l=9.8,
    oxygen_saturation_pct=102.0,
    surface_temp_c=11.0,
    current_speed_ms=0.20,
    significant_wave_height_m=0.5,
    ice_risk_score=0.01,
    site_exposure_class='sheltered',
)


class TestEnvironmentalForecaster:
    def test_returns_five_subtypes(self):
        forecasts = EnvironmentalForecaster().forecast(_HIGH_RISK_ENV, _META)
        risk_types = {f['risk_type'] for f in forecasts}
        assert risk_types == {'oxygen_stress', 'temperature_extreme', 'current_storm', 'ice', 'exposure_anomaly'}

    def test_probabilities_in_range(self):
        for f in EnvironmentalForecaster().forecast(_HIGH_RISK_ENV, _META):
            assert 0.0 <= f['event_probability'] <= 1.0

    def test_losses_positive(self):
        for f in EnvironmentalForecaster().forecast(_HIGH_RISK_ENV, _META):
            assert f['expected_loss_mean'] > 0
            assert f['expected_loss_p90'] >= f['expected_loss_p50']

    def test_drivers_non_empty_for_high_risk(self):
        for f in EnvironmentalForecaster().forecast(_HIGH_RISK_ENV, _META):
            assert len(f['drivers']) >= 1

    def test_high_risk_higher_probability(self):
        high = {f['risk_type']: f['event_probability'] for f in EnvironmentalForecaster().forecast(_HIGH_RISK_ENV, _META)}
        low = {f['risk_type']: f['event_probability'] for f in EnvironmentalForecaster().forecast(_LOW_RISK_ENV, _META)}
        assert high['oxygen_stress'] > low['oxygen_stress']
        assert high['current_storm'] > low['current_storm']

    def test_confidence_score_range(self):
        for f in EnvironmentalForecaster().forecast(_HIGH_RISK_ENV, _META):
            assert 0.0 <= f['confidence_score'] <= 1.0

    def test_model_used_field(self):
        for f in EnvironmentalForecaster().forecast(_HIGH_RISK_ENV, _META):
            assert f['model_used'] == 'score_environmental'

    def test_demo_site_simulation(self):
        sim = MockEnvironmentalSimulator()
        forecaster = EnvironmentalForecaster()
        for sid in ['KH_S01', 'KH_S02', 'KH_S03']:
            inp = sim.simulate(sid)
            forecasts = forecaster.forecast(inp, _META)
            assert len(forecasts) == 5


# ── Operational Forecaster ─────────────────────────────────────────────────────

_HIGH_RISK_OPS = OperationalSiteInput(
    site_id='TEST',
    staffing_score=0.40,
    training_compliance_pct=60.0,
    incident_rate_12m=2.5,
    maintenance_backlog_score=0.70,
    critical_ops_frequency_per_month=8.0,
    equipment_readiness_score=0.45,
)
_LOW_RISK_OPS = OperationalSiteInput(
    site_id='TEST',
    staffing_score=0.95,
    training_compliance_pct=98.0,
    incident_rate_12m=0.1,
    maintenance_backlog_score=0.05,
    critical_ops_frequency_per_month=1.5,
    equipment_readiness_score=0.96,
)


class TestOperationalForecaster:
    def test_returns_five_subtypes(self):
        forecasts = OperationalForecaster().forecast(_HIGH_RISK_OPS, _META)
        risk_types = {f['risk_type'] for f in forecasts}
        assert risk_types == {'human_error', 'procedure_failure', 'equipment_failure', 'incident', 'maintenance_backlog'}

    def test_probabilities_in_range(self):
        for f in OperationalForecaster().forecast(_HIGH_RISK_OPS, _META):
            assert 0.0 <= f['event_probability'] <= 1.0

    def test_losses_positive(self):
        for f in OperationalForecaster().forecast(_HIGH_RISK_OPS, _META):
            assert f['expected_loss_mean'] > 0
            assert f['expected_loss_p90'] >= f['expected_loss_p50']

    def test_drivers_non_empty_for_high_risk(self):
        for f in OperationalForecaster().forecast(_HIGH_RISK_OPS, _META):
            assert len(f['drivers']) >= 1

    def test_high_risk_higher_probability(self):
        high = {f['risk_type']: f['event_probability'] for f in OperationalForecaster().forecast(_HIGH_RISK_OPS, _META)}
        low = {f['risk_type']: f['event_probability'] for f in OperationalForecaster().forecast(_LOW_RISK_OPS, _META)}
        assert high['human_error'] > low['human_error']
        assert high['maintenance_backlog'] > low['maintenance_backlog']

    def test_confidence_score_range(self):
        for f in OperationalForecaster().forecast(_HIGH_RISK_OPS, _META):
            assert 0.0 <= f['confidence_score'] <= 1.0

    def test_model_used_field(self):
        for f in OperationalForecaster().forecast(_HIGH_RISK_OPS, _META):
            assert f['model_used'] == 'score_operational'

    def test_demo_site_simulation(self):
        sim = MockOperationalSimulator()
        for sid in ['KH_S01', 'KH_S02', 'KH_S03']:
            inp = sim.simulate(sid)
            forecasts = OperationalForecaster().forecast(inp, _META)
            assert len(forecasts) == 5


# ── Multi-Domain Alert Rules ───────────────────────────────────────────────────

from c5ai_plus.alerts.alert_rules import (
    ALL_RULES, STRUCTURAL_RULES, ENVIRONMENTAL_RULES, OPERATIONAL_RULES,
    HAB_RULES, LICE_RULES,
)
from c5ai_plus.alerts.alert_models import RISK_TYPE_DOMAIN


class TestMultiDomainAlertRules:
    def test_structural_rules_non_empty(self):
        assert len(STRUCTURAL_RULES) >= 5

    def test_environmental_rules_non_empty(self):
        assert len(ENVIRONMENTAL_RULES) >= 5

    def test_operational_rules_non_empty(self):
        assert len(OPERATIONAL_RULES) >= 5

    def test_structural_weights_le_1(self):
        for rule in STRUCTURAL_RULES:
            assert 0.0 < rule.weight <= 1.0

    def test_environmental_weights_le_1(self):
        for rule in ENVIRONMENTAL_RULES:
            assert 0.0 < rule.weight <= 1.0

    def test_all_rules_contains_new_risk_types(self):
        new_types = [
            'mooring_failure', 'net_integrity', 'cage_structural',
            'oxygen_stress', 'temperature_extreme', 'current_storm',
            'human_error', 'procedure_failure', 'equipment_failure',
        ]
        for rt in new_types:
            assert rt in ALL_RULES, f'Missing {rt} in ALL_RULES'

    def test_risk_type_domain_covers_all_19(self):
        assert len(RISK_TYPE_DOMAIN) == 19

    def test_biological_types_mapped_correctly(self):
        for rt in ('hab', 'lice', 'jellyfish', 'pathogen'):
            assert RISK_TYPE_DOMAIN[rt] == 'biological'

    def test_structural_types_mapped_correctly(self):
        for rt in ('mooring_failure', 'net_integrity', 'cage_structural'):
            assert RISK_TYPE_DOMAIN[rt] == 'structural'

    def test_original_rules_unchanged(self):
        assert len(HAB_RULES) == 4
        assert len(LICE_RULES) == 4


# ── Multi-Domain Alert Engine ──────────────────────────────────────────────────

from c5ai_plus.alerts.alert_engine import AlertEngine
from c5ai_plus.alerts.alert_simulator import AlertSimulator


class TestMultiDomainAlertEngine:
    def test_generate_structural_alert(self):
        engine = AlertEngine()
        forecasts = {
            'SITE_A': {'mooring_failure': {'event_probability': 0.40}}
        }
        alerts = engine.generate_alerts(forecasts)
        assert len(alerts) == 1
        assert alerts[0].risk_type == 'mooring_failure'

    def test_domain_field_populated_structural(self):
        engine = AlertEngine()
        forecasts = {'S1': {'mooring_failure': {'event_probability': 0.30}}}
        alert = engine.generate_alerts(forecasts)[0]
        assert alert.domain == 'structural'

    def test_domain_field_populated_environmental(self):
        engine = AlertEngine()
        forecasts = {'S1': {'oxygen_stress': {'event_probability': 0.25}}}
        alert = engine.generate_alerts(forecasts)[0]
        assert alert.domain == 'environmental'

    def test_domain_field_populated_operational(self):
        engine = AlertEngine()
        forecasts = {'S1': {'human_error': {'event_probability': 0.20}}}
        alert = engine.generate_alerts(forecasts)[0]
        assert alert.domain == 'operational'

    def test_domain_field_populated_biological(self):
        engine = AlertEngine()
        forecasts = {'S1': {'hab': {'event_probability': 0.20}}}
        alert = engine.generate_alerts(forecasts)[0]
        assert alert.domain == 'biological'

    def test_simulator_all_returns_18_records(self):
        sim = AlertSimulator()
        alerts = sim.simulate_all()
        assert len(alerts) == 18

    def test_simulator_new_structural_scenarios(self):
        sim = AlertSimulator()
        a1 = sim.simulate_mooring_warning()
        a2 = sim.simulate_net_critical()
        assert a1.risk_type == 'mooring_failure'
        assert a2.risk_type == 'net_integrity'
        assert a2.alert_level == 'CRITICAL'

    def test_simulator_new_operational_scenarios(self):
        sim = AlertSimulator()
        a1 = sim.simulate_staffing_warning()
        a2 = sim.simulate_equipment_watch()
        a3 = sim.simulate_maintenance_warning()
        assert a1.domain == 'operational'
        assert a2.domain == 'operational'
        assert a3.domain == 'operational'

    def test_high_probability_structural_is_critical(self):
        engine = AlertEngine()
        forecasts = {'S1': {'anchor_deterioration': {'event_probability': 0.40}}}
        alert = engine.generate_alerts(forecasts)[0]
        assert alert.alert_level == 'CRITICAL'

    def test_recommended_actions_populated_for_new_types(self):
        sim = AlertSimulator()
        alert = sim.simulate_mooring_warning()
        assert len(alert.recommended_actions) >= 1

    def test_recommended_actions_structural_critical(self):
        sim = AlertSimulator()
        alert = sim.simulate_net_critical()
        assert len(alert.recommended_actions) >= 3   # CRITICAL = all actions
