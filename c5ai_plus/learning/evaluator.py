"""
C5AI+ v5.0 – Prediction Evaluator.

Computes EvaluationMetrics from matched (prediction, observation) pairs.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from c5ai_plus.data_models.learning_schema import (
    EvaluationMetrics,
    ObservedEvent,
    PredictionRecord,
)
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS

_EPSILON = 1e-15


class Evaluator:
    """Stateless evaluator: computes metrics from paired predictions and observations."""

    def evaluate(
        self,
        pairs: List[Tuple[PredictionRecord, ObservedEvent]],
        risk_type: str,
    ) -> EvaluationMetrics:
        """
        Compute EvaluationMetrics for a collection of matched pairs.

        Parameters
        ----------
        pairs : list of (PredictionRecord, ObservedEvent)
        risk_type : str

        Returns
        -------
        EvaluationMetrics
        """
        n = len(pairs)
        if n == 0:
            return self._zero_metrics(risk_type)

        probs = [float(p.event_probability) for p, _ in pairs]
        actuals = [float(e.event_occurred) for _, e in pairs]
        losses_pred = [float(p.expected_loss_mean) for p, _ in pairs]
        losses_act = [float(e.actual_loss_nok) for _, e in pairs]

        # Brier score: E[(p - y)^2]
        brier = sum((p - y) ** 2 for p, y in zip(probs, actuals)) / n

        # Log loss
        ll = -sum(
            y * math.log(max(p, _EPSILON)) + (1 - y) * math.log(max(1 - p, _EPSILON))
            for p, y in zip(probs, actuals)
        ) / n

        # Mean probability error (bias)
        mean_prob_err = (sum(probs) / n) - (sum(actuals) / n)

        # Severity metrics – events only
        event_pairs = [
            (lp, la) for (_, e), lp, la in zip(pairs, losses_pred, losses_act)
            if e.event_occurred and la > 0
        ]
        if event_pairs:
            n_ev = len(event_pairs)
            mae = sum(abs(lp - la) for lp, la in event_pairs) / n_ev
            rmse = math.sqrt(sum((lp - la) ** 2 for lp, la in event_pairs) / n_ev)
        else:
            mae = 0.0
            rmse = 0.0

        # Calibration slope (simple linear regression p_pred ~ y)
        cal_slope = self._calibration_slope(probs, actuals)

        return EvaluationMetrics(
            risk_type=risk_type,
            n_samples=n,
            brier_score=round(brier, 6),
            log_loss=round(ll, 6),
            mean_probability_error=round(mean_prob_err, 6),
            severity_mae_nok=round(mae, 2),
            severity_rmse_nok=round(rmse, 2),
            calibration_slope=round(cal_slope, 6),
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    def should_retrain(
        self,
        metrics: EvaluationMetrics,
        min_samples: Optional[int] = None,
    ) -> bool:
        """
        Return True when metrics indicate retraining is warranted.

        Triggers when:
          - n_samples >= min_samples (enough data)
          - Brier score > 0.10 (non-trivial error)
        """
        threshold = min_samples or C5AI_SETTINGS.learning_retrain_trigger_samples
        if metrics.n_samples < threshold:
            return False
        return metrics.brier_score > 0.10

    def is_shadow_better(
        self,
        current: EvaluationMetrics,
        shadow: EvaluationMetrics,
        min_improvement: Optional[float] = None,
    ) -> bool:
        """
        Return True if the shadow model is materially better than the current.

        "Better" = shadow Brier score is at least min_improvement lower than current.
        Also requires shadow.n_samples >= min_shadow_samples.
        """
        threshold = min_improvement or C5AI_SETTINGS.learning_shadow_min_improvement
        min_samples = C5AI_SETTINGS.learning_shadow_min_samples
        if shadow.n_samples < min_samples:
            return False
        improvement = current.brier_score - shadow.brier_score
        return improvement >= threshold

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _calibration_slope(probs: List[float], actuals: List[float]) -> float:
        """
        Compute slope of linear regression actuals ~ probs.

        Returns 1.0 when perfectly calibrated, <1 when over-confident.
        Returns 1.0 when all probs are identical (undefined slope).
        """
        n = len(probs)
        if n < 2:
            return 1.0
        mean_p = sum(probs) / n
        mean_y = sum(actuals) / n
        cov = sum((p - mean_p) * (y - mean_y) for p, y in zip(probs, actuals))
        var = sum((p - mean_p) ** 2 for p in probs)
        if abs(var) < 1e-12:
            return 1.0
        return cov / var

    @staticmethod
    def _zero_metrics(risk_type: str) -> EvaluationMetrics:
        return EvaluationMetrics(
            risk_type=risk_type,
            n_samples=0,
            brier_score=0.25,   # uninformative default
            log_loss=math.log(2),
            mean_probability_error=0.0,
            severity_mae_nok=0.0,
            severity_rmse_nok=0.0,
            calibration_slope=1.0,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
