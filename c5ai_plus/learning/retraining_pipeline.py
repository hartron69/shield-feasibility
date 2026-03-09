"""
C5AI+ v5.0 – Retraining Pipeline.

Loads historical ObservedEvents and retrains probability models:
  - n >= 20 → SklearnProbabilityModel
  - else    → BetaBinomialModel (Bayesian conjugate)

Registers the result as a shadow model in ModelRegistry (does NOT promote).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from c5ai_plus.data_models.forecast_schema import RISK_TYPES
from c5ai_plus.data_models.learning_schema import ObservedEvent
from c5ai_plus.learning.event_store import EventStore
from c5ai_plus.models.model_registry import ModelRegistry
from c5ai_plus.models.probability_model import (
    BaseProbabilityModel,
    BetaBinomialModel,
)
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS

_SKLEARN_THRESHOLD = 20


class RetrainingPipeline:
    """
    Retrain probability models from accumulated ObservedEvents.

    Parameters
    ----------
    model_registry : ModelRegistry
    event_store : EventStore
    """

    def __init__(self, model_registry: ModelRegistry, event_store: EventStore):
        self._registry = model_registry
        self._event_store = event_store

    def retrain(
        self, operator_id: str, risk_type: str
    ) -> Optional[BaseProbabilityModel]:
        """
        Retrain a probability model for one (operator, risk_type).

        1. Load all ObservedEvents for operator/risk_type
        2. n >= 20 → SklearnProbabilityModel; else → BetaBinomialModel
        3. Register as shadow in ModelRegistry

        Returns the new candidate model, or None if no events found.
        """
        all_events = self._event_store.load_all(operator_id)
        relevant = [e for e in all_events if e.risk_type == risk_type]
        if not relevant:
            return None

        candidate = self._build_model(relevant)
        self._registry.register_shadow(operator_id, risk_type, candidate)
        return candidate

    def retrain_all(self, operator_id: str) -> Dict[str, bool]:
        """
        Retrain models for all 4 standard risk types.

        Returns
        -------
        Dict[risk_type → True if retrained, False if no data]
        """
        results: Dict[str, bool] = {}
        for risk_type in RISK_TYPES:
            model = self.retrain(operator_id, risk_type)
            results[risk_type] = model is not None
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_model(
        self, events: List[ObservedEvent]
    ) -> BaseProbabilityModel:
        """Choose BetaBinomial or Sklearn based on sample count."""
        n = len(events)
        if n >= _SKLEARN_THRESHOLD:
            try:
                from c5ai_plus.models.probability_model import SklearnProbabilityModel
                model = SklearnProbabilityModel(
                    observations=[e.event_occurred for e in events]
                )
                return model
            except ImportError:
                pass  # Fall through to BetaBinomial

        # BetaBinomial: accumulate all events from scratch
        n_events = sum(1 for e in events if e.event_occurred)
        concentration = C5AI_SETTINGS.learning_bayesian_concentration
        # Derive a reasonable prior from risk_type
        risk_type = events[0].risk_type if events else "hab"
        from c5ai_plus.models.model_registry import _PRIOR_PROBS
        prior_prob = _PRIOR_PROBS.get(risk_type, 0.12)
        alpha_0 = prior_prob * concentration
        beta_0 = (1.0 - prior_prob) * concentration
        model = BetaBinomialModel(
            alpha=alpha_0 + n_events,
            beta=beta_0 + (n - n_events),
            n_updates=n,
            _version=f"v1.{n}",
        )
        return model
