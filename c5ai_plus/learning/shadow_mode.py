"""
C5AI+ v5.0 – Shadow Mode Manager.

Runs shadow predictions alongside production models and evaluates whether
the shadow should be promoted to production.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from c5ai_plus.data_models.learning_schema import (
    EvaluationMetrics,
    ObservedEvent,
    PredictionRecord,
)
from c5ai_plus.learning.evaluator import Evaluator
from c5ai_plus.learning.event_store import EventStore
from c5ai_plus.learning.prediction_store import PredictionStore
from c5ai_plus.models.model_registry import ModelRegistry
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS


class ShadowModeManager:
    """
    Manages parallel shadow predictions and promotion decisions.

    Parameters
    ----------
    model_registry : ModelRegistry
    prediction_store : PredictionStore
    event_store : EventStore
    evaluator : Evaluator
    """

    def __init__(
        self,
        model_registry: ModelRegistry,
        prediction_store: PredictionStore,
        event_store: EventStore,
        evaluator: Optional[Evaluator] = None,
    ):
        self._registry = model_registry
        self._pred_store = prediction_store
        self._event_store = event_store
        self._evaluator = evaluator or Evaluator()

    def run_shadow_prediction(
        self,
        operator_id: str,
        risk_type: str,
    ) -> Optional[float]:
        """
        Return the shadow model's probability estimate, or None if no shadow.
        """
        shadow = self._registry.get_shadow_model(operator_id, risk_type)
        if shadow is None:
            return None
        return shadow.predict()

    def evaluate_and_promote(
        self,
        operator_id: str,
        risk_type: str,
        current_pairs: List[Tuple[PredictionRecord, ObservedEvent]],
        shadow_pairs: List[Tuple[PredictionRecord, ObservedEvent]],
        min_shadow_samples: Optional[int] = None,
    ) -> bool:
        """
        Evaluate current vs. shadow metrics and promote if shadow is better.

        Parameters
        ----------
        current_pairs : matched pairs for current production model
        shadow_pairs  : matched pairs for shadow model predictions
        min_shadow_samples : minimum shadow observations required

        Returns
        -------
        True if shadow was promoted; False otherwise.
        """
        min_samples = min_shadow_samples or C5AI_SETTINGS.learning_shadow_min_samples
        if len(shadow_pairs) < min_samples:
            return False

        current_metrics = self._evaluator.evaluate(current_pairs, risk_type)
        shadow_metrics = self._evaluator.evaluate(shadow_pairs, risk_type)

        if self._evaluator.is_shadow_better(current_metrics, shadow_metrics):
            promoted = self._registry.promote_shadow(operator_id, risk_type)
            return promoted
        return False
