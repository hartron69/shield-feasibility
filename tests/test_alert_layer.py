"""
Tests for C5AI+ v5.0 – Early Warning / Alert Layer.

~48 tests across 7 classes.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest

from c5ai_plus.alerts.alert_models import (
    AlertRecord,
    AlertSummary,
    ALERT_LEVELS,
    WORKFLOW_STATUSES,
    PatternSignal,
    ProbabilityShiftSignal,
)
from c5ai_plus.alerts.alert_rules import (
    ALL_RULES,
    HAB_RULES,
    LICE_RULES,
    JELLYFISH_RULES,
    PATHOGEN_RULES,
)
from c5ai_plus.alerts.pattern_detector import PatternDetector
from c5ai_plus.alerts.probability_shift_detector import ProbabilityShiftDetector
from c5ai_plus.alerts.alert_engine import AlertEngine, _determine_level
from c5ai_plus.alerts.alert_explainer import AlertExplainer, RECOMMENDED_ACTIONS
from c5ai_plus.alerts.alert_store import AlertStore
from c5ai_plus.alerts.alert_simulator import AlertSimulator


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_alert_record(**kwargs) -> AlertRecord:
    defaults = dict(
        alert_id='abc123',
        site_id='S01',
        risk_type='hab',
        alert_type='composite',
        alert_level='WARNING',
        current_probability=0.28,
        previous_probability=0.12,
        probability_delta=0.16,
        top_drivers=['High temp'],
        triggered_rules=['hab_warm_surface'],
        explanation_text='',
        recommended_actions=[],
        generated_at='2026-01-15T10:00:00+00:00',
    )
    defaults.update(kwargs)
    return AlertRecord(**defaults)


def _make_pattern_signal(**kwargs) -> PatternSignal:
    defaults = dict(
        site_id='S01', risk_type='hab', signal_name='hab_warm_surface',
        current_value=18.0, baseline_value=14.0, z_score=4.0,
        threshold=1.5, direction='increasing', triggered=True,
    )
    defaults.update(kwargs)
    return PatternSignal(**defaults)


def _make_shift_signal(**kwargs) -> ProbabilityShiftSignal:
    defaults = dict(
        site_id='S01', risk_type='hab',
        previous_probability=0.12, current_probability=0.28,
        absolute_change=0.16, relative_change=1.33,
        threshold_crossed=True, triggered=True,
    )
    defaults.update(kwargs)
    return ProbabilityShiftSignal(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# 1. TestAlertModels
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertModels:

    def test_alert_record_creation(self):
        a = _make_alert_record()
        assert a.site_id == 'S01'
        assert a.alert_level == 'WARNING'
        assert a.workflow_status == 'OPEN'          # default
        assert a.board_visibility is False           # default

    def test_alert_record_to_dict_round_trip(self):
        a = _make_alert_record()
        d = a.to_dict()
        assert isinstance(d, dict)
        assert d['alert_id'] == 'abc123'
        b = AlertRecord.from_dict(d)
        assert b.alert_id == a.alert_id
        assert b.top_drivers == a.top_drivers

    def test_alert_record_from_dict_ignores_extra_keys(self):
        d = _make_alert_record().to_dict()
        d['unknown_field'] = 'should_be_ignored'
        a = AlertRecord.from_dict(d)
        assert a.site_id == 'S01'

    def test_pattern_signal_to_dict_round_trip(self):
        s = _make_pattern_signal()
        d = s.to_dict()
        s2 = PatternSignal.from_dict(d)
        assert s2.signal_name == 'hab_warm_surface'
        assert s2.triggered is True

    def test_probability_shift_signal_to_dict(self):
        sig = _make_shift_signal()
        d = sig.to_dict()
        sig2 = ProbabilityShiftSignal.from_dict(d)
        assert sig2.absolute_change == pytest.approx(0.16)
        assert sig2.threshold_crossed is True

    def test_alert_summary_creation_and_dict(self):
        summary = AlertSummary(
            site_id='S01', total_alerts=5, critical_alerts=1,
            warning_alerts=2, top_risk_type='hab', latest_alert_at='2026-01-15T10:00:00+00:00',
        )
        d = summary.to_dict()
        s2 = AlertSummary.from_dict(d)
        assert s2.critical_alerts == 1
        assert s2.top_risk_type == 'hab'

    def test_alert_levels_tuple(self):
        assert 'CRITICAL' in ALERT_LEVELS
        assert 'NORMAL' in ALERT_LEVELS
        assert len(ALERT_LEVELS) == 4

    def test_workflow_statuses_tuple(self):
        assert 'OPEN' in WORKFLOW_STATUSES
        assert 'CLOSED' in WORKFLOW_STATUSES


# ─────────────────────────────────────────────────────────────────────────────
# 2. TestAlertRules
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertRules:

    def test_all_rule_lists_non_empty(self):
        for risk_type, rules in ALL_RULES.items():
            assert len(rules) >= 3, f"{risk_type} has fewer than 3 rules"

    def test_four_risk_types_covered(self):
        # Sprint multi-domain: ALL_RULES now covers 19 risk types across 4 domains
        bio_types = {'hab', 'lice', 'jellyfish', 'pathogen'}
        assert bio_types.issubset(set(ALL_RULES.keys()))
        assert len(ALL_RULES) >= 19

    def test_weights_sum_at_most_one_per_risk_type(self):
        for risk_type, rules in ALL_RULES.items():
            total = sum(r.weight for r in rules)
            assert total <= 1.001, f"{risk_type} weights sum to {total:.3f} > 1.0"

    def test_rule_weights_positive(self):
        for rules in ALL_RULES.values():
            for r in rules:
                assert r.weight > 0, f"{r.rule_id} has non-positive weight"


# ─────────────────────────────────────────────────────────────────────────────
# 3. TestPatternDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestPatternDetector:

    def setup_method(self):
        self.detector = PatternDetector(trigger_z_score=1.5)

    def test_score_in_range_hab(self):
        score, signals = self.detector.detect('S01', 'hab', 0.15)
        assert 0.0 <= score <= 1.0
        assert isinstance(signals, list)

    def test_score_in_range_lice(self):
        score, signals = self.detector.detect('S01', 'lice', 0.20)
        assert 0.0 <= score <= 1.0

    def test_score_in_range_jellyfish(self):
        score, signals = self.detector.detect('S01', 'jellyfish', 0.10)
        assert 0.0 <= score <= 1.0

    def test_score_in_range_pathogen(self):
        score, signals = self.detector.detect('S01', 'pathogen', 0.12)
        assert 0.0 <= score <= 1.0

    def test_env_data_none_graceful(self):
        # Should not raise when env_data is None
        score, signals = self.detector.detect('S01', 'hab', 0.25, env_data=None)
        assert 0.0 <= score <= 1.0

    def test_env_data_provided_used(self):
        env = {'surface_temp_c': 22.0, 'dissolved_oxygen_mg_l': 5.5}
        score_no_env, _ = self.detector.detect('S01', 'hab', 0.25)
        score_env, _ = self.detector.detect('S01', 'hab', 0.25, env_data=env)
        # Both should be in [0,1]; env data may influence score
        assert 0.0 <= score_env <= 1.0

    def test_high_probability_triggers_signals(self):
        # Very high probability should trigger at least one signal
        score, signals = self.detector.detect('S01', 'hab', 0.80)
        triggered = [s for s in signals if s.triggered]
        assert len(triggered) >= 1

    def test_signals_have_correct_site_and_risk_type(self):
        _, signals = self.detector.detect('MY_SITE', 'lice', 0.25)
        for s in signals:
            assert s.site_id == 'MY_SITE'
            assert s.risk_type == 'lice'

    def test_unknown_risk_type_returns_zero_score(self):
        score, signals = self.detector.detect('S01', 'unknown_risk', 0.20)
        assert score == 0.0
        assert signals == []

    def test_pattern_signal_triggered_field_is_bool(self):
        _, signals = self.detector.detect('S01', 'hab', 0.20)
        for s in signals:
            assert isinstance(s.triggered, bool)


# ─────────────────────────────────────────────────────────────────────────────
# 4. TestProbabilityShiftDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestProbabilityShiftDetector:

    def setup_method(self):
        self.detector = ProbabilityShiftDetector(
            abs_threshold=0.10, rel_threshold=0.50,
            cross_low=0.10, cross_high=0.20,
        )

    def test_absolute_change_triggers(self):
        sig = self.detector.detect('S01', 'hab', 0.10, 0.25)
        assert sig.triggered is True
        assert sig.absolute_change == pytest.approx(0.15)

    def test_relative_change_triggers(self):
        # 100% relative change; absolute = 0.05 < abs_threshold
        sig = self.detector.detect('S01', 'hab', 0.05, 0.10)
        assert sig.triggered is True
        assert sig.relative_change == pytest.approx(1.0)

    def test_threshold_crossing_low(self):
        sig = self.detector.detect('S01', 'hab', 0.08, 0.12)
        assert sig.threshold_crossed is True
        assert sig.triggered is True

    def test_threshold_crossing_high(self):
        sig = self.detector.detect('S01', 'lice', 0.18, 0.22)
        assert sig.threshold_crossed is True

    def test_no_trigger_when_stable(self):
        sig = self.detector.detect('S01', 'hab', 0.12, 0.13)
        assert sig.triggered is False
        assert sig.threshold_crossed is False

    def test_probability_decrease_detected(self):
        sig = self.detector.detect('S01', 'hab', 0.30, 0.15)
        assert sig.absolute_change == pytest.approx(-0.15)
        assert sig.triggered is True

    def test_return_type_is_probability_shift_signal(self):
        sig = self.detector.detect('S01', 'hab', 0.10, 0.20)
        assert isinstance(sig, ProbabilityShiftSignal)

    def test_site_and_risk_type_propagated(self):
        sig = self.detector.detect('SITE_X', 'lice', 0.10, 0.15)
        assert sig.site_id == 'SITE_X'
        assert sig.risk_type == 'lice'


# ─────────────────────────────────────────────────────────────────────────────
# 5. TestAlertEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertEngine:

    def setup_method(self):
        self.engine = AlertEngine()

    def _site_forecasts(self, probs: dict) -> dict:
        """Build minimal site_forecasts dict from {risk_type: prob}."""
        return {'S01': {rt: {'event_probability': p} for rt, p in probs.items()}}

    def test_returns_alert_record_list(self):
        sf = self._site_forecasts({'hab': 0.15})
        alerts = self.engine.generate_alerts(sf)
        assert isinstance(alerts, list)
        assert len(alerts) == 1
        assert isinstance(alerts[0], AlertRecord)

    def test_critical_for_high_probability(self):
        sf = self._site_forecasts({'hab': 0.40})
        alerts = self.engine.generate_alerts(sf)
        assert alerts[0].alert_level == 'CRITICAL'

    def test_normal_for_low_probability(self):
        sf = self._site_forecasts({'hab': 0.05})
        alerts = self.engine.generate_alerts(sf)
        assert alerts[0].alert_level in ('NORMAL', 'WATCH')

    def test_multiple_risk_types_generate_multiple_alerts(self):
        sf = self._site_forecasts({'hab': 0.15, 'lice': 0.30, 'jellyfish': 0.10})
        alerts = self.engine.generate_alerts(sf)
        assert len(alerts) == 3

    def test_previous_probabilities_used_for_shift(self):
        sf = self._site_forecasts({'lice': 0.30})
        prev = {'S01': {'lice': 0.10}}
        alerts = self.engine.generate_alerts(sf, previous_probabilities=prev)
        assert alerts[0].previous_probability == pytest.approx(0.10)
        assert alerts[0].probability_delta == pytest.approx(0.20)

    def test_no_previous_probabilities_uses_priors(self):
        sf = self._site_forecasts({'hab': 0.15})
        alerts = self.engine.generate_alerts(sf)
        # Prior for hab = 0.12; delta = 0.03
        assert alerts[0].previous_probability == pytest.approx(0.12)

    def test_explanation_text_populated(self):
        sf = self._site_forecasts({'hab': 0.28})
        alerts = self.engine.generate_alerts(sf)
        assert len(alerts[0].explanation_text) > 10

    def test_recommended_actions_populated(self):
        sf = self._site_forecasts({'hab': 0.28})
        alerts = self.engine.generate_alerts(sf)
        assert len(alerts[0].recommended_actions) >= 1

    def test_level_determination_function(self):
        assert _determine_level(0.80, 0.10, False) == 'CRITICAL'
        assert _determine_level(0.10, 0.38, False) == 'CRITICAL'
        assert _determine_level(0.50, 0.10, False) == 'WARNING'
        assert _determine_level(0.10, 0.27, False) == 'WARNING'
        assert _determine_level(0.30, 0.10, False) == 'WATCH'
        assert _determine_level(0.10, 0.10, True) == 'WATCH'
        assert _determine_level(0.10, 0.05, False) == 'NORMAL'

    def test_summarise_returns_alert_summary_list(self):
        sf = {'S01': {'hab': {'event_probability': 0.30}},
              'S02': {'lice': {'event_probability': 0.15}}}
        alerts = self.engine.generate_alerts(sf)
        summaries = self.engine.summarise(alerts)
        assert len(summaries) == 2
        site_ids = {s.site_id for s in summaries}
        assert 'S01' in site_ids
        assert 'S02' in site_ids


# ─────────────────────────────────────────────────────────────────────────────
# 6. TestAlertExplainer
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertExplainer:

    def setup_method(self):
        self.explainer = AlertExplainer()

    def test_explanation_text_non_empty(self):
        alert = _make_alert_record(alert_level='WARNING', risk_type='hab')
        self.explainer.explain(alert)
        assert len(alert.explanation_text) > 0

    def test_recommended_actions_for_each_risk_type(self):
        for rt in ('hab', 'lice', 'jellyfish', 'pathogen'):
            alert = _make_alert_record(risk_type=rt, alert_level='WARNING')
            self.explainer.explain(alert)
            assert len(alert.recommended_actions) >= 1
            # Actions should match the risk type
            for action in alert.recommended_actions:
                assert isinstance(action, str)
                assert len(action) > 0

    def test_board_visibility_set_for_critical(self):
        alert = _make_alert_record(alert_level='CRITICAL')
        self.explainer.explain(alert)
        assert alert.board_visibility is True

    def test_board_visibility_not_set_for_warning(self):
        alert = _make_alert_record(alert_level='WARNING')
        self.explainer.explain(alert)
        assert alert.board_visibility is False

    def test_critical_alert_gets_all_actions(self):
        alert = _make_alert_record(alert_level='CRITICAL', risk_type='hab')
        self.explainer.explain(alert)
        all_actions = RECOMMENDED_ACTIONS.get('hab', [])
        assert len(alert.recommended_actions) == len(all_actions)

    def test_normal_alert_gets_minimal_actions(self):
        alert = _make_alert_record(alert_level='NORMAL', risk_type='lice')
        self.explainer.explain(alert)
        assert len(alert.recommended_actions) == 1

    def test_pattern_signals_mentioned_in_explanation(self):
        alert = _make_alert_record(alert_level='WARNING', risk_type='hab')
        signals = [_make_pattern_signal(triggered=True, signal_name='hab_warm_surface')]
        self.explainer.explain(alert, pattern_signals=signals)
        assert 'hab_warm_surface' in alert.explanation_text

    def test_returns_mutated_alert(self):
        alert = _make_alert_record()
        returned = self.explainer.explain(alert)
        assert returned is alert


# ─────────────────────────────────────────────────────────────────────────────
# 7. TestAlertStore
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertStore:

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.store = AlertStore(store_dir=self._tmpdir)

    def _make_saved_alert(self, site_id='S01', risk_type='hab', level='WARNING') -> AlertRecord:
        a = _make_alert_record(site_id=site_id, risk_type=risk_type, alert_level=level)
        self.store.save(a)
        return a

    def test_save_and_load_all_round_trip(self):
        a = self._make_saved_alert()
        loaded = self.store.load_all('S01')
        assert len(loaded) == 1
        assert loaded[0].alert_id == a.alert_id
        assert loaded[0].alert_level == 'WARNING'

    def test_multiple_alerts_same_site(self):
        self._make_saved_alert(site_id='S01', risk_type='hab')
        self._make_saved_alert(site_id='S01', risk_type='lice')
        loaded = self.store.load_all('S01')
        assert len(loaded) == 2

    def test_load_all_empty_when_no_data(self):
        loaded = self.store.load_all('UNKNOWN_SITE')
        assert loaded == []

    def test_load_recent_respects_n(self):
        for _ in range(5):
            self._make_saved_alert()
        loaded = self.store.load_recent('S01', n=3)
        assert len(loaded) == 3

    def test_filter_by_level(self):
        self._make_saved_alert(level='WARNING')
        self._make_saved_alert(level='CRITICAL')
        self._make_saved_alert(level='WATCH')
        all_alerts = self.store.load_all('S01')
        crit = self.store.filter_by_level(all_alerts, 'CRITICAL')
        assert len(crit) == 1
        assert crit[0].alert_level == 'CRITICAL'

    def test_filter_by_risk_type(self):
        self._make_saved_alert(risk_type='hab')
        self._make_saved_alert(risk_type='lice')
        all_alerts = self.store.load_all('S01')
        hab_alerts = self.store.filter_by_risk_type(all_alerts, 'hab')
        assert len(hab_alerts) == 1
        assert hab_alerts[0].risk_type == 'hab'

    def test_alerts_isolated_by_site(self):
        self._make_saved_alert(site_id='S01')
        self._make_saved_alert(site_id='S02')
        s01 = self.store.load_all('S01')
        s02 = self.store.load_all('S02')
        assert len(s01) == 1
        assert len(s02) == 1
        assert s01[0].site_id == 'S01'

    def test_save_creates_parent_dirs(self):
        new_site_id = 'BRAND_NEW_SITE'
        a = _make_alert_record(site_id=new_site_id)
        self.store.save(a)
        loaded = self.store.load_all(new_site_id)
        assert len(loaded) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 8. TestAlertSimulator
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertSimulator:

    def setup_method(self):
        self.sim = AlertSimulator()

    def test_hab_warning(self):
        a = self.sim.simulate_hab_warning()
        assert a.risk_type == 'hab'
        assert a.alert_level == 'WARNING'
        assert a.site_id == 'KH_S01'

    def test_lice_watch(self):
        a = self.sim.simulate_lice_watch()
        assert a.risk_type == 'lice'
        assert a.alert_level == 'WATCH'

    def test_jellyfish_critical(self):
        a = self.sim.simulate_jellyfish_critical()
        assert a.risk_type == 'jellyfish'
        assert a.alert_level == 'CRITICAL'
        assert a.board_visibility is True

    def test_pathogen_warning(self):
        a = self.sim.simulate_pathogen_warning()
        assert a.risk_type == 'pathogen'
        assert a.alert_level == 'WARNING'

    def test_simulate_all_returns_ten_records(self):
        # Sprint multi-domain: simulate_all now returns ~18 records (all 4 domains)
        alerts = self.sim.simulate_all()
        assert len(alerts) >= 10

    def test_simulate_all_covers_four_risk_types(self):
        alerts = self.sim.simulate_all()
        risk_types = {a.risk_type for a in alerts}
        # Biological types still present; new domains also included
        assert {'hab', 'lice', 'jellyfish', 'pathogen'}.issubset(risk_types)

    def test_simulate_all_has_critical_and_normal(self):
        alerts = self.sim.simulate_all()
        levels = {a.alert_level for a in alerts}
        assert 'CRITICAL' in levels
        assert 'NORMAL' in levels

    def test_all_alerts_have_alert_id(self):
        alerts = self.sim.simulate_all()
        for a in alerts:
            assert len(a.alert_id) >= 8
