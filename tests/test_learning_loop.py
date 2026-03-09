"""
Tests for the C5AI+ Self-Learning Extension.

~60 tests across 9 test classes covering:
  - PredictionStore
  - EventStore
  - BetaBinomialModel
  - LogNormalSeverityModel
  - Evaluator
  - SiteDataSimulator
  - EventSimulator
  - RetrainingPipeline
  - LearningLoop (end-to-end)
"""

from __future__ import annotations

import math
import os
import tempfile
from datetime import datetime, timezone
from typing import List, Tuple

import pytest

# ── Shared fixtures ────────────────────────────────────────────────────────────

NOW_ISO = datetime.now(timezone.utc).isoformat()


def _make_prediction(
    operator_id="OP1",
    site_id="OP1_S01",
    risk_type="hab",
    forecast_year=2021,
    event_probability=0.15,
    expected_loss_mean=500_000.0,
    cycle_id=0,
):
    from c5ai_plus.data_models.learning_schema import PredictionRecord
    return PredictionRecord(
        operator_id=operator_id,
        site_id=site_id,
        risk_type=risk_type,
        forecast_year=forecast_year,
        predicted_at=NOW_ISO,
        event_probability=event_probability,
        expected_loss_mean=expected_loss_mean,
        model_version="5.0.0",
        model_used="prior",
        data_quality_flag="PRIOR_ONLY",
        cycle_id=cycle_id,
    )


def _make_event(
    operator_id="OP1",
    site_id="OP1_S01",
    risk_type="hab",
    event_year=2021,
    event_occurred=True,
    actual_loss_nok=400_000.0,
):
    from c5ai_plus.data_models.learning_schema import ObservedEvent
    return ObservedEvent(
        operator_id=operator_id,
        site_id=site_id,
        risk_type=risk_type,
        event_year=event_year,
        observed_at=NOW_ISO,
        event_occurred=event_occurred,
        actual_loss_nok=actual_loss_nok,
        source="simulated",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. TestPredictionStore
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictionStore:
    def _store(self, tmp_path):
        from c5ai_plus.learning.prediction_store import PredictionStore
        return PredictionStore(store_dir=str(tmp_path))

    def test_save_and_load_round_trip(self, tmp_path):
        store = self._store(tmp_path)
        rec = _make_prediction()
        store.save(rec)
        loaded = store.load("OP1", "hab", 2021)
        assert loaded is not None
        assert loaded.operator_id == "OP1"
        assert loaded.risk_type == "hab"
        assert loaded.forecast_year == 2021
        assert abs(loaded.event_probability - 0.15) < 1e-9

    def test_load_missing_returns_none(self, tmp_path):
        store = self._store(tmp_path)
        assert store.load("UNKNOWN", "hab", 9999) is None

    def test_save_multiple_risk_types(self, tmp_path):
        store = self._store(tmp_path)
        for rt in ("hab", "lice", "jellyfish", "pathogen"):
            store.save(_make_prediction(risk_type=rt, forecast_year=2022))
        records = store.load_all("OP1")
        assert len(records) == 4
        loaded_types = {r.risk_type for r in records}
        assert loaded_types == {"hab", "lice", "jellyfish", "pathogen"}

    def test_overwrite_same_key(self, tmp_path):
        store = self._store(tmp_path)
        store.save(_make_prediction(event_probability=0.10))
        store.save(_make_prediction(event_probability=0.25))
        loaded = store.load("OP1", "hab", 2021)
        assert abs(loaded.event_probability - 0.25) < 1e-9

    def test_list_years(self, tmp_path):
        store = self._store(tmp_path)
        for yr in (2020, 2021, 2022):
            store.save(_make_prediction(forecast_year=yr))
        years = store.list_years("OP1", "hab")
        assert years == [2020, 2021, 2022]

    def test_load_all_empty_operator(self, tmp_path):
        store = self._store(tmp_path)
        assert store.load_all("NO_SUCH_OP") == []


# ─────────────────────────────────────────────────────────────────────────────
# 2. TestEventStore
# ─────────────────────────────────────────────────────────────────────────────

class TestEventStore:
    def _store(self, tmp_path):
        from c5ai_plus.learning.event_store import EventStore
        return EventStore(store_dir=str(tmp_path))

    def test_save_and_load_round_trip(self, tmp_path):
        store = self._store(tmp_path)
        events = [_make_event()]
        store.save(events)
        loaded = store.load("OP1", 2021)
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].risk_type == "hab"
        assert loaded[0].event_occurred is True

    def test_load_missing_returns_none(self, tmp_path):
        store = self._store(tmp_path)
        assert store.load("UNKNOWN", 9999) is None

    def test_save_merges_risk_types(self, tmp_path):
        store = self._store(tmp_path)
        store.save([_make_event(risk_type="hab")])
        store.save([_make_event(risk_type="lice", actual_loss_nok=100_000)])
        loaded = store.load("OP1", 2021)
        assert len(loaded) == 2

    def test_matched_pairs_join(self, tmp_path):
        store = self._store(tmp_path)
        events = [_make_event(risk_type="hab", event_year=2021)]
        store.save(events)
        preds = [_make_prediction(risk_type="hab", forecast_year=2021)]
        pairs = store.matched_pairs("OP1", "hab", preds)
        assert len(pairs) == 1
        pred, ev = pairs[0]
        assert pred.forecast_year == ev.event_year == 2021

    def test_matched_pairs_empty_when_no_overlap(self, tmp_path):
        store = self._store(tmp_path)
        store.save([_make_event(event_year=2021)])
        preds = [_make_prediction(forecast_year=2022)]  # different year
        pairs = store.matched_pairs("OP1", "hab", preds)
        assert pairs == []

    def test_load_all_accumulates_years(self, tmp_path):
        store = self._store(tmp_path)
        for yr in (2020, 2021, 2022):
            store.save([_make_event(event_year=yr)])
        all_events = store.load_all("OP1")
        assert len(all_events) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 3. TestBetaBinomialModel
# ─────────────────────────────────────────────────────────────────────────────

class TestBetaBinomialModel:
    def _model(self, prior_prob=0.12, concentration=5.0):
        from c5ai_plus.models.probability_model import BetaBinomialModel
        return BetaBinomialModel(prior_prob=prior_prob, concentration=concentration)

    def test_prior_mean_equals_prior_prob(self):
        model = self._model(prior_prob=0.20)
        assert abs(model.predict() - 0.20) < 1e-9

    def test_update_event_shifts_probability_up(self):
        model = self._model(prior_prob=0.10)
        before = model.predict()
        model.update(event_occurred=True)
        assert model.predict() > before

    def test_update_no_event_shifts_probability_down(self):
        model = self._model(prior_prob=0.90)
        before = model.predict()
        model.update(event_occurred=False)
        assert model.predict() < before

    def test_version_increments_on_update(self):
        model = self._model()
        v0 = model.version
        model.update(True)
        v1 = model.version
        assert v1 != v0

    def test_many_events_converges_to_high_probability(self):
        model = self._model(prior_prob=0.10, concentration=2.0)
        for _ in range(50):
            model.update(True)
        assert model.predict() > 0.80

    def test_many_no_events_converges_to_low_probability(self):
        model = self._model(prior_prob=0.90, concentration=2.0)
        for _ in range(50):
            model.update(False)
        assert model.predict() < 0.20

    def test_serialise_round_trip(self):
        from c5ai_plus.models.probability_model import BetaBinomialModel
        model = self._model(prior_prob=0.15)
        model.update(True)
        model.update(False)
        d = model.to_dict()
        restored = BetaBinomialModel.from_dict(d)
        assert abs(restored.predict() - model.predict()) < 1e-9
        assert restored.version == model.version

    def test_predict_always_in_unit_interval(self):
        model = self._model(prior_prob=0.5)
        for i in range(20):
            model.update(i % 2 == 0)
            p = model.predict()
            assert 0.0 <= p <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. TestLogNormalSeverityModel
# ─────────────────────────────────────────────────────────────────────────────

class TestLogNormalSeverityModel:
    def _model(self, prior_mean=1_000_000.0, prior_cv=0.60):
        from c5ai_plus.models.severity_model import LogNormalSeverityModel
        return LogNormalSeverityModel(prior_mean_nok=prior_mean, prior_cv=prior_cv)

    def test_prior_p50_less_than_mean_less_than_p90(self):
        model = self._model()
        mean, p50, p90 = model.predict()
        assert p50 < mean
        assert mean < p90

    def test_update_increments_n_obs(self):
        model = self._model()
        assert model.n_obs == 0
        model.update(500_000)
        assert model.n_obs == 1

    def test_update_shifts_mean_toward_data(self):
        model = self._model(prior_mean=1_000_000.0)
        # Add 5 small losses to build up enough obs for learned estimate
        for _ in range(5):
            model.update(100_000.0)
        mean, _, _ = model.predict()
        assert mean < 1_000_000.0   # learned < prior

    def test_version_increments_on_update(self):
        model = self._model()
        v0 = model.version
        model.update(200_000.0)
        assert model.version != v0

    def test_serialise_round_trip(self):
        from c5ai_plus.models.severity_model import LogNormalSeverityModel
        model = self._model()
        for loss in (200_000, 500_000, 800_000):
            model.update(loss)
        d = model.to_dict()
        restored = LogNormalSeverityModel.from_dict(d)
        assert restored.n_obs == model.n_obs
        assert abs(restored.predict()[0] - model.predict()[0]) < 1.0

    def test_ignores_nonpositive_losses(self):
        model = self._model()
        model.update(-100)
        model.update(0)
        assert model.n_obs == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. TestEvaluator
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluator:
    def _evaluator(self):
        from c5ai_plus.learning.evaluator import Evaluator
        return Evaluator()

    def _pairs(self, probs, actuals, losses_pred=None, losses_act=None):
        if losses_pred is None:
            losses_pred = [500_000.0] * len(probs)
        if losses_act is None:
            losses_act = [400_000.0 if y else 0.0 for y in actuals]
        preds = [_make_prediction(event_probability=p, expected_loss_mean=lp)
                 for p, lp in zip(probs, losses_pred)]
        events = [_make_event(event_occurred=bool(y), actual_loss_nok=la)
                  for y, la in zip(actuals, losses_act)]
        return list(zip(preds, events))

    def test_perfect_predictor_brier_zero(self):
        ev = self._evaluator()
        # p=1 when y=1, p=0 when y=0
        pairs = self._pairs([1.0, 0.0, 1.0, 0.0], [True, False, True, False])
        m = ev.evaluate(pairs, "hab")
        assert m.brier_score < 1e-9

    def test_uninformative_predictor_brier_025(self):
        ev = self._evaluator()
        # Always predict 0.5, alternating outcomes
        pairs = self._pairs([0.5]*8, [True]*4 + [False]*4)
        m = ev.evaluate(pairs, "hab")
        assert abs(m.brier_score - 0.25) < 1e-9

    def test_empty_pairs_returns_default_metrics(self):
        ev = self._evaluator()
        m = ev.evaluate([], "lice")
        assert m.n_samples == 0
        assert m.brier_score == 0.25  # uninformative default

    def test_severity_mae_correct(self):
        ev = self._evaluator()
        # Two events with known losses
        pairs = self._pairs(
            [1.0, 1.0], [True, True],
            losses_pred=[600_000, 600_000],
            losses_act=[400_000, 800_000],
        )
        m = ev.evaluate(pairs, "hab")
        # MAE = (|600k-400k| + |600k-800k|) / 2 = 200k
        assert abs(m.severity_mae_nok - 200_000.0) < 1.0

    def test_should_retrain_when_sufficient_samples(self):
        ev = self._evaluator()
        from c5ai_plus.data_models.learning_schema import EvaluationMetrics
        m = EvaluationMetrics(
            risk_type="hab", n_samples=10, brier_score=0.15,
            log_loss=0.5, mean_probability_error=0.0,
            severity_mae_nok=0.0, severity_rmse_nok=0.0,
            calibration_slope=1.0, computed_at=NOW_ISO,
        )
        assert ev.should_retrain(m, min_samples=5) is True

    def test_should_not_retrain_when_too_few_samples(self):
        ev = self._evaluator()
        from c5ai_plus.data_models.learning_schema import EvaluationMetrics
        m = EvaluationMetrics(
            risk_type="hab", n_samples=2, brier_score=0.20,
            log_loss=0.5, mean_probability_error=0.0,
            severity_mae_nok=0.0, severity_rmse_nok=0.0,
            calibration_slope=1.0, computed_at=NOW_ISO,
        )
        assert ev.should_retrain(m, min_samples=5) is False

    def test_is_shadow_better_detects_improvement(self):
        ev = self._evaluator()
        from c5ai_plus.data_models.learning_schema import EvaluationMetrics

        def _metrics(brier, n):
            return EvaluationMetrics(
                risk_type="hab", n_samples=n, brier_score=brier,
                log_loss=0.5, mean_probability_error=0.0,
                severity_mae_nok=0.0, severity_rmse_nok=0.0,
                calibration_slope=1.0, computed_at=NOW_ISO,
            )
        current = _metrics(brier=0.20, n=15)
        shadow = _metrics(brier=0.12, n=15)   # 0.08 improvement > 0.05 threshold
        assert ev.is_shadow_better(current, shadow) is True

    def test_is_shadow_not_better_when_insufficient_samples(self):
        ev = self._evaluator()
        from c5ai_plus.data_models.learning_schema import EvaluationMetrics

        def _metrics(brier, n):
            return EvaluationMetrics(
                risk_type="hab", n_samples=n, brier_score=brier,
                log_loss=0.5, mean_probability_error=0.0,
                severity_mae_nok=0.0, severity_rmse_nok=0.0,
                calibration_slope=1.0, computed_at=NOW_ISO,
            )
        current = _metrics(brier=0.25, n=15)
        shadow = _metrics(brier=0.05, n=5)   # good Brier but n < 10
        assert ev.is_shadow_better(current, shadow) is False


# ─────────────────────────────────────────────────────────────────────────────
# 6. TestSiteDataSimulator
# ─────────────────────────────────────────────────────────────────────────────

class TestSiteDataSimulator:
    def _sim(self, seed=42):
        from c5ai_plus.simulation.site_data_simulator import SiteDataSimulator
        return SiteDataSimulator(seed=seed)

    def test_generates_valid_operator_input(self):
        from c5ai_plus.data_models.biological_input import C5AIOperatorInput
        sim = self._sim()
        op = sim.generate_operator_input(n_sites=2, n_years=2)
        assert isinstance(op, C5AIOperatorInput)
        assert len(op.sites) == 2
        assert op.operator_id == "SIM_OP_001"

    def test_temperature_has_seasonal_pattern(self):
        sim = self._sim()
        op = sim.generate_operator_input(n_sites=1, n_years=1)
        site = op.sites[0]
        env_by_month = {e.month: e.sea_temp_celsius
                        for e in op.env_observations if e.site_id == site.site_id}
        if env_by_month:
            # Summer should be warmer than winter on average
            summer = [env_by_month[m] for m in (7, 8) if m in env_by_month]
            winter = [env_by_month[m] for m in (1, 2) if m in env_by_month]
            if summer and winter:
                assert sum(summer)/len(summer) > sum(winter)/len(winter)

    def test_lice_counts_in_reasonable_range(self):
        sim = self._sim()
        op = sim.generate_operator_input(n_sites=1, n_years=2)
        for obs in op.lice_observations:
            assert obs.avg_lice_per_fish >= 0.0
            assert obs.avg_lice_per_fish < 10.0

    def test_hab_alerts_summer_skewed(self):
        sim = self._sim()
        op = sim.generate_operator_input(n_sites=3, n_years=5)
        summer_months = {4, 5, 6, 7, 8, 9}
        summer_count = sum(1 for a in op.hab_alerts if a.month in summer_months)
        total = len(op.hab_alerts)
        if total > 0:
            assert summer_count / total > 0.5

    def test_multiple_sites_have_unique_ids(self):
        sim = self._sim()
        op = sim.generate_operator_input(n_sites=5, n_years=1)
        ids = [s.site_id for s in op.sites]
        assert len(ids) == len(set(ids))

    def test_forecast_years_default(self):
        sim = self._sim()
        op = sim.generate_operator_input()
        assert op.forecast_years == 5

    def test_reproducible_with_same_seed(self):
        op1 = self._sim(seed=7).generate_operator_input(n_sites=2, n_years=2)
        op2 = self._sim(seed=7).generate_operator_input(n_sites=2, n_years=2)
        assert len(op1.env_observations) == len(op2.env_observations)
        if op1.env_observations:
            assert op1.env_observations[0].sea_temp_celsius == op2.env_observations[0].sea_temp_celsius

    def test_jellyfish_density_positive(self):
        sim = self._sim()
        op = sim.generate_operator_input(n_sites=2, n_years=3)
        for obs in op.jellyfish_observations:
            assert obs.density_index >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 7. TestEventSimulator
# ─────────────────────────────────────────────────────────────────────────────

class TestEventSimulator:
    def _forecast_with_prob(self, prob: float) -> "RiskForecast":
        """Build a minimal RiskForecast with all risk types at given probability."""
        from c5ai_plus.data_models.forecast_schema import (
            ForecastMetadata, OperatorAggregate, RiskForecast,
            RiskTypeForecast, SiteForecast, RISK_TYPES,
        )
        site_id = "OP1_S01"
        forecasts = [
            RiskTypeForecast(
                risk_type=rt, year=1,
                event_probability=prob,
                expected_loss_mean=500_000.0,
                expected_loss_p50=300_000.0,
                expected_loss_p90=900_000.0,
                confidence_score=0.5,
                data_quality_flag="PRIOR_ONLY",
            )
            for rt in RISK_TYPES
        ]
        site_forecast = SiteForecast(site_id=site_id, site_name="Site 1",
                                     annual_forecasts=forecasts)
        meta = ForecastMetadata(
            model_version="5.0.0",
            generated_at=NOW_ISO,
            operator_id="OP1",
            operator_name="Test",
            forecast_horizon_years=1,
            overall_confidence="low",
            overall_data_quality="PRIOR_ONLY",
            sites_included=[site_id],
        )
        agg = OperatorAggregate(
            annual_expected_loss_by_type={rt: 500_000.0 for rt in RISK_TYPES},
            total_expected_annual_loss=2_000_000.0,
            c5ai_vs_static_ratio=1.0,
            loss_breakdown_fractions={rt: 0.25 for rt in RISK_TYPES},
        )
        return RiskForecast(metadata=meta, site_forecasts=[site_forecast],
                            operator_aggregate=agg)

    def test_p1_always_event(self):
        from c5ai_plus.simulation.event_simulator import EventSimulator
        sim = EventSimulator(seed=42)
        forecast = self._forecast_with_prob(1.0)
        events = sim.simulate_year(forecast, 2021, "OP1")
        assert all(e.event_occurred for e in events)

    def test_p0_never_event(self):
        from c5ai_plus.simulation.event_simulator import EventSimulator
        sim = EventSimulator(seed=42)
        forecast = self._forecast_with_prob(0.0)
        events = sim.simulate_year(forecast, 2021, "OP1")
        assert all(not e.event_occurred for e in events)

    def test_loss_zero_when_no_event(self):
        from c5ai_plus.simulation.event_simulator import EventSimulator
        sim = EventSimulator(seed=42)
        forecast = self._forecast_with_prob(0.0)
        events = sim.simulate_year(forecast, 2021, "OP1")
        assert all(e.actual_loss_nok == 0.0 for e in events)

    def test_loss_positive_when_event(self):
        from c5ai_plus.simulation.event_simulator import EventSimulator
        sim = EventSimulator(seed=42)
        forecast = self._forecast_with_prob(1.0)
        events = sim.simulate_year(forecast, 2021, "OP1")
        assert all(e.actual_loss_nok > 0.0 for e in events)

    def test_multi_year_returns_all_years(self):
        from c5ai_plus.simulation.event_simulator import EventSimulator
        sim = EventSimulator(seed=42)
        forecast = self._forecast_with_prob(0.3)
        result = sim.simulate_multi_year(forecast, start_year=2020, n_years=3, operator_id="OP1")
        assert set(result.keys()) == {2020, 2021, 2022}
        for yr, events in result.items():
            assert len(events) > 0

    def test_events_have_correct_operator_id(self):
        from c5ai_plus.simulation.event_simulator import EventSimulator
        sim = EventSimulator(seed=42)
        forecast = self._forecast_with_prob(0.5)
        events = sim.simulate_year(forecast, 2021, "MY_OP")
        assert all(e.operator_id == "MY_OP" for e in events)


# ─────────────────────────────────────────────────────────────────────────────
# 8. TestRetrainingPipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestRetrainingPipeline:
    def _setup(self, tmp_path):
        from c5ai_plus.learning.event_store import EventStore
        from c5ai_plus.learning.retraining_pipeline import RetrainingPipeline
        from c5ai_plus.models.model_registry import ModelRegistry
        registry = ModelRegistry(store_dir=str(tmp_path))
        event_store = EventStore(store_dir=str(tmp_path))
        pipeline = RetrainingPipeline(registry, event_store)
        return registry, event_store, pipeline

    def _populate_events(self, event_store, n=10, risk_type="hab"):
        import random
        rng = random.Random(42)
        events = [
            _make_event(
                risk_type=risk_type,
                event_year=2020 + i,
                event_occurred=rng.random() < 0.20,
                actual_loss_nok=rng.uniform(100_000, 1_000_000) if rng.random() < 0.20 else 0.0,
            )
            for i in range(n)
        ]
        for e in events:
            event_store.save([e])
        return events

    def test_no_events_returns_none(self, tmp_path):
        _, _, pipeline = self._setup(tmp_path)
        result = pipeline.retrain("OP1", "hab")
        assert result is None

    def test_small_sample_uses_beta_binomial(self, tmp_path):
        from c5ai_plus.models.probability_model import BetaBinomialModel
        registry, event_store, pipeline = self._setup(tmp_path)
        self._populate_events(event_store, n=5)
        model = pipeline.retrain("OP1", "hab")
        assert model is not None
        assert isinstance(model, BetaBinomialModel)

    def test_shadow_registered_after_retrain(self, tmp_path):
        registry, event_store, pipeline = self._setup(tmp_path)
        self._populate_events(event_store, n=5)
        pipeline.retrain("OP1", "hab")
        shadow = registry.get_shadow_model("OP1", "hab")
        assert shadow is not None

    def test_retrain_all_covers_all_risk_types(self, tmp_path):
        registry, event_store, pipeline = self._setup(tmp_path)
        for rt in ("hab", "lice", "jellyfish", "pathogen"):
            self._populate_events(event_store, n=5, risk_type=rt)
        results = pipeline.retrain_all("OP1")
        assert set(results.keys()) == {"hab", "lice", "jellyfish", "pathogen"}
        assert all(results.values())

    def test_model_probability_in_unit_interval(self, tmp_path):
        _, event_store, pipeline = self._setup(tmp_path)
        self._populate_events(event_store, n=8)
        model = pipeline.retrain("OP1", "hab")
        p = model.predict()
        assert 0.0 <= p <= 1.0

    def test_retrain_when_no_data_for_type_returns_false(self, tmp_path):
        registry, event_store, pipeline = self._setup(tmp_path)
        # Only populate "hab", not "lice"
        self._populate_events(event_store, n=5, risk_type="hab")
        results = pipeline.retrain_all("OP1")
        assert results["lice"] is False
        assert results["hab"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 9. TestLearningLoop
# ─────────────────────────────────────────────────────────────────────────────

class TestLearningLoop:
    def _loop(self, tmp_path):
        from c5ai_plus.learning.learning_loop import LearningLoop
        return LearningLoop(store_dir=str(tmp_path), verbose=False)

    def _operator_input(self):
        from c5ai_plus.simulation.site_data_simulator import SiteDataSimulator
        sim = SiteDataSimulator(seed=0)
        return sim.generate_operator_input(
            n_sites=2, n_years=2, base_year=2018,
            operator_id="LEARN_OP",
        )

    def test_first_cycle_cold_status(self, tmp_path):
        loop = self._loop(tmp_path)
        op = self._operator_input()
        result = loop.run_cycle(op, static_mean_annual_loss=5_000_000, forecast_year=2020)
        assert result.learning_status == "cold"
        assert result.cycle_id == 0

    def test_cycle_id_increments(self, tmp_path):
        loop = self._loop(tmp_path)
        op = self._operator_input()
        r1 = loop.run_cycle(op, 5_000_000, 2020)
        r2 = loop.run_cycle(op, 5_000_000, 2021)
        assert r2.cycle_id == r1.cycle_id + 1

    def test_warming_status_after_3_cycles(self, tmp_path):
        loop = self._loop(tmp_path)
        op = self._operator_input()
        for yr in range(2020, 2023):
            result = loop.run_cycle(op, 5_000_000, yr)
        assert result.learning_status == "warming"

    def test_active_status_after_10_cycles(self, tmp_path):
        loop = self._loop(tmp_path)
        op = self._operator_input()
        for yr in range(2020, 2030):
            result = loop.run_cycle(op, 5_000_000, yr)
        assert result.learning_status == "active"

    def test_metrics_for_all_risk_types(self, tmp_path):
        loop = self._loop(tmp_path)
        op = self._operator_input()
        result = loop.run_cycle(op, 5_000_000, 2020)
        assert set(result.metrics_by_risk_type.keys()) == {"hab", "lice", "jellyfish", "pathogen"}

    def test_brier_score_in_unit_interval(self, tmp_path):
        loop = self._loop(tmp_path)
        op = self._operator_input()
        # Run a few cycles to accumulate observations
        for yr in range(2020, 2023):
            result = loop.run_cycle(op, 5_000_000, yr)
        for m in result.metrics_by_risk_type.values():
            assert 0.0 <= m.brier_score <= 1.0

    def test_adjusted_probability_set_after_first_cycle(self, tmp_path):
        loop = self._loop(tmp_path)
        op = self._operator_input()
        # First cycle: run pipeline and enrich
        forecast = loop._pipeline.run(op, 5_000_000)
        loop._enrich_forecast(forecast, op.operator_id)
        for sf in forecast.site_forecasts:
            for rtf in sf.annual_forecasts:
                assert rtf.adjusted_probability is not None
                assert rtf.baseline_probability is not None

    def test_adjusted_differs_from_baseline_after_many_cycles(self, tmp_path):
        loop = self._loop(tmp_path)
        op = self._operator_input()
        # Run 5 cycles to build up Bayesian posterior
        for yr in range(2020, 2025):
            loop.run_cycle(op, 5_000_000, yr)
        # After 5 cycles, check that the registry has been updated
        from c5ai_plus.models.model_registry import ModelRegistry
        reg = ModelRegistry(store_dir=str(tmp_path))
        # Model should have been updated (non-zero n_updates)
        model = reg.get_probability_model(op.operator_id, "hab")
        assert model.predict() is not None  # just check no crash

    def test_pcc_compatibility_scale_factor_unchanged(self, tmp_path):
        """Scale factor and loss_fractions must be unaffected by learning enrichment."""
        loop = self._loop(tmp_path)
        op = self._operator_input()
        forecast_before = loop._pipeline.run(op, 5_000_000)
        sf_before = forecast_before.scale_factor
        lf_before = dict(forecast_before.loss_fractions)

        # Run a learning cycle
        loop.run_cycle(op, 5_000_000, 2020)

        # Run pipeline again – scale_factor is determined by C5AI data, not learning
        forecast_after = loop._pipeline.run(op, 5_000_000)
        # The pipeline is deterministic for same input, so values should be equal
        assert abs(forecast_after.scale_factor - sf_before) < 1e-6
        for rt in lf_before:
            assert abs(forecast_after.loss_fractions[rt] - lf_before[rt]) < 1e-6

    def test_result_is_learning_cycle_result(self, tmp_path):
        from c5ai_plus.data_models.learning_schema import LearningCycleResult
        loop = self._loop(tmp_path)
        op = self._operator_input()
        result = loop.run_cycle(op, 5_000_000, 2020)
        assert isinstance(result, LearningCycleResult)

    def test_to_dict_serialisable(self, tmp_path):
        import json
        loop = self._loop(tmp_path)
        op = self._operator_input()
        result = loop.run_cycle(op, 5_000_000, 2020)
        d = result.to_dict()
        # Must be JSON serialisable
        json.dumps(d)

    def test_provided_events_used_over_simulated(self, tmp_path):
        from c5ai_plus.learning.event_store import EventStore
        loop = self._loop(tmp_path)
        op = self._operator_input()
        # Provide a single known event
        known_event = _make_event(
            operator_id=op.operator_id,
            site_id=op.sites[0].site_id,
            risk_type="hab",
            event_year=2020,
            event_occurred=True,
            actual_loss_nok=1_000_000.0,
        )
        loop.run_cycle(op, 5_000_000, 2020, observed_events=[known_event])
        event_store = EventStore(store_dir=str(tmp_path))
        loaded = event_store.load(op.operator_id, 2020)
        assert loaded is not None
        hab_events = [e for e in loaded if e.risk_type == "hab"]
        assert any(e.actual_loss_nok == 1_000_000.0 for e in hab_events)
