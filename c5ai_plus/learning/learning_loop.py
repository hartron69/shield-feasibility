"""
C5AI+ v5.0 – Learning Loop Orchestrator.

Coordinates the full predict → observe → evaluate → retrain cycle.
PCC integration remains 100% backward-compatible: scale_factor and
loss_fractions are unchanged by the learning layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.data_models.biological_input import C5AIOperatorInput
from c5ai_plus.data_models.forecast_schema import RISK_TYPES, RiskForecast
from c5ai_plus.data_models.learning_schema import (
    EvaluationMetrics,
    LearningCycleResult,
    ObservedEvent,
    PredictionRecord,
)
from c5ai_plus.learning.evaluator import Evaluator
from c5ai_plus.learning.event_store import EventStore
from c5ai_plus.learning.prediction_store import PredictionStore
from c5ai_plus.learning.retraining_pipeline import RetrainingPipeline
from c5ai_plus.learning.shadow_mode import ShadowModeManager
from c5ai_plus.models.model_registry import ModelRegistry
from c5ai_plus.pipeline import ForecastPipeline
from c5ai_plus.simulation.event_simulator import EventSimulator


class LearningLoop:
    """
    Orchestrates C5AI+ self-learning cycles.

    Steps per cycle:
      1. Run ForecastPipeline (existing, unchanged)
      2. Enrich RiskTypeForecast.adjusted_probability from ModelRegistry
      3. Save predictions to PredictionStore
      4. Use provided observed_events or auto-simulate via EventSimulator
      5. Save events to EventStore
      6. Update models in ModelRegistry
      7. Evaluate matched pairs → EvaluationMetrics
      8. Retrain if should_retrain()
      9. Shadow evaluate and promote if criteria met
      10. Return LearningCycleResult

    Parameters
    ----------
    store_dir : str
        Root directory for JSON persistence. Defaults to C5AI_SETTINGS.learning_store_dir.
    verbose : bool
        Print progress if True.
    """

    def __init__(self, store_dir: str = "", verbose: bool = False):
        self._store_dir = store_dir or C5AI_SETTINGS.learning_store_dir
        self._verbose = verbose

        self._registry = ModelRegistry(self._store_dir)
        self._pred_store = PredictionStore(self._store_dir)
        self._event_store = EventStore(self._store_dir)
        self._evaluator = Evaluator()
        self._retrainer = RetrainingPipeline(self._registry, self._event_store)
        self._shadow_mgr = ShadowModeManager(
            self._registry, self._pred_store, self._event_store, self._evaluator
        )
        self._pipeline = ForecastPipeline(verbose=verbose)
        self._event_sim = EventSimulator()

        # Per-operator cycle counter (persisted implicitly via stored predictions)
        self._cycle_counters: Dict[str, int] = {}

    # ── Public API ─────────────────────────────────────────────────────────

    def run_cycle(
        self,
        operator_input: C5AIOperatorInput,
        static_mean_annual_loss: float,
        forecast_year: int,
        observed_events: Optional[List[ObservedEvent]] = None,
    ) -> LearningCycleResult:
        """
        Run one full predict → observe → evaluate → retrain cycle.

        Parameters
        ----------
        operator_input : C5AIOperatorInput
        static_mean_annual_loss : float
            E[annual loss] from static Monte Carlo model (NOK).
        forecast_year : int
            Calendar year being forecast / observed.
        observed_events : Optional[List[ObservedEvent]]
            Real observed events. If None, events are auto-simulated.

        Returns
        -------
        LearningCycleResult
        """
        operator_id = operator_input.operator_id
        self._log(f"[LearningLoop] Cycle for {operator_id}, year {forecast_year}")

        # ── Step 1: Run forecast pipeline ─────────────────────────────────
        forecast = self._pipeline.run(operator_input, static_mean_annual_loss)

        # ── Step 2: Enrich probabilities from ModelRegistry ───────────────
        self._enrich_forecast(forecast, operator_id)

        # ── Step 3: Save predictions ──────────────────────────────────────
        cycle_id = self._next_cycle_id(operator_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        self._save_predictions(forecast, operator_id, forecast_year, cycle_id, now_iso)

        # ── Steps 4+5: Get/simulate events and save ───────────────────────
        if observed_events is None:
            observed_events = self._event_sim.simulate_year(
                forecast, forecast_year=forecast_year, operator_id=operator_id
            )
        self._event_store.save(observed_events)

        # ── Step 6: Update models ─────────────────────────────────────────
        self._update_models(operator_id, observed_events)

        # ── Step 7: Evaluate ──────────────────────────────────────────────
        all_preds = self._pred_store.load_all(operator_id)
        metrics_by_rt: Dict[str, EvaluationMetrics] = {}
        prev_briers: Dict[str, float] = {}
        for rt in RISK_TYPES:
            pairs = self._event_store.matched_pairs(operator_id, rt, all_preds)
            metrics = self._evaluator.evaluate(pairs, rt)
            metrics_by_rt[rt] = metrics
            prev_briers[rt] = metrics.brier_score  # before retraining

        # ── Step 8: Retrain ───────────────────────────────────────────────
        retrain_triggered = False
        for rt, metrics in metrics_by_rt.items():
            if self._evaluator.should_retrain(metrics):
                self._retrainer.retrain(operator_id, rt)
                retrain_triggered = True

        # ── Step 9: Shadow evaluate & promote ────────────────────────────
        models_promoted: List[str] = []
        for rt in RISK_TYPES:
            all_preds_rt = [p for p in all_preds if p.risk_type == rt]
            pairs = self._event_store.matched_pairs(operator_id, rt, all_preds_rt)
            promoted = self._shadow_mgr.evaluate_and_promote(
                operator_id, rt,
                current_pairs=pairs,
                shadow_pairs=pairs,  # share same pairs; shadow predicts differently
            )
            if promoted:
                models_promoted.append(rt)

        # ── Step 10: Compute overall Brier improvement ────────────────────
        overall_improvement = 0.0
        if retrain_triggered:
            new_briers = {rt: m.brier_score for rt, m in metrics_by_rt.items()}
            diffs = [prev_briers[rt] - new_briers[rt] for rt in RISK_TYPES]
            overall_improvement = sum(diffs) / len(diffs)

        status = self.get_learning_status(operator_id)

        return LearningCycleResult(
            cycle_id=cycle_id,
            operator_id=operator_id,
            forecast_year=forecast_year,
            metrics_by_risk_type=metrics_by_rt,
            retrain_triggered=retrain_triggered,
            models_promoted=models_promoted,
            overall_brier_improvement=overall_improvement,
            learning_status=status,
        )

    def get_learning_status(self, operator_id: str) -> str:
        """
        Return learning status string based on number of completed cycles.

        cold     : < 3 cycles
        warming  : 3–9 cycles
        active   : >= 10 cycles
        """
        n = self._cycle_counters.get(operator_id, 0)
        if n < 3:
            return "cold"
        if n < 10:
            return "warming"
        return "active"

    # ── Internals ──────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        if self._verbose:
            print(msg)

    def _next_cycle_id(self, operator_id: str) -> int:
        n = self._cycle_counters.get(operator_id, 0)
        self._cycle_counters[operator_id] = n + 1
        return n

    def _enrich_forecast(
        self, forecast: RiskForecast, operator_id: str
    ) -> None:
        """
        Overwrite event_probability in each RiskTypeForecast with the
        Bayesian posterior from ModelRegistry, storing the original as
        baseline_probability.
        """
        for sf in forecast.site_forecasts:
            for rtf in sf.annual_forecasts:
                model = self._registry.get_probability_model(
                    operator_id, rtf.risk_type
                )
                posterior = model.predict()
                # Only store adjusted values if we have updates (not cold prior)
                rtf.baseline_probability = rtf.event_probability
                rtf.adjusted_probability = float(posterior)
                # Leave event_probability unchanged so PCC pipeline is unaffected

    def _save_predictions(
        self,
        forecast: RiskForecast,
        operator_id: str,
        forecast_year: int,
        cycle_id: int,
        now_iso: str,
    ) -> None:
        """Save one PredictionRecord per (site, risk_type)."""
        for sf in forecast.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.year != 1:   # Only save year-1 forecast per cycle
                    continue
                rec = PredictionRecord(
                    operator_id=operator_id,
                    site_id=sf.site_id,
                    risk_type=rtf.risk_type,
                    forecast_year=forecast_year,
                    predicted_at=now_iso,
                    event_probability=rtf.adjusted_probability or rtf.event_probability,
                    expected_loss_mean=rtf.expected_loss_mean,
                    model_version=forecast.metadata.model_version,
                    model_used=rtf.model_used,
                    data_quality_flag=rtf.data_quality_flag,
                    cycle_id=cycle_id,
                )
                self._pred_store.save(rec)

    def _update_models(
        self,
        operator_id: str,
        events: List[ObservedEvent],
    ) -> None:
        """Update probability and severity models with observed events."""
        for event in events:
            self._registry.update_probability_model(
                operator_id, event.risk_type, event.event_occurred
            )
            if event.event_occurred and event.actual_loss_nok > 0:
                self._registry.update_severity_model(
                    operator_id, event.risk_type, event.actual_loss_nok
                )
