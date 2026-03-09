"""
C5AI+ v5.0 – Learning Loop Data Models.

JSON-serialisable dataclasses for the predict→observe→evaluate→retrain loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PredictionRecord:
    """A stored prediction made by C5AI+ for one site/risk_type/year."""
    operator_id: str
    site_id: str
    risk_type: str
    forecast_year: int
    predicted_at: str           # ISO-8601 UTC
    event_probability: float
    expected_loss_mean: float
    model_version: str
    model_used: str
    data_quality_flag: str
    cycle_id: int = 0

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "PredictionRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ObservedEvent:
    """An observed outcome for one site/risk_type/year."""
    operator_id: str
    site_id: str
    risk_type: str
    event_year: int
    observed_at: str            # ISO-8601 UTC
    event_occurred: bool
    actual_loss_nok: float
    source: str = "simulated"   # "simulated" | "operator_reported"

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "ObservedEvent":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EvaluationMetrics:
    """Evaluation of prediction quality for one risk_type over a sample of pairs."""
    risk_type: str
    n_samples: int
    brier_score: float          # E[(p_pred - y)^2]; 0=perfect, 0.25=uninformative
    log_loss: float             # cross-entropy
    mean_probability_error: float  # bias check (mean pred_prob - mean observed)
    severity_mae_nok: float        # events-only MAE (0 when no events observed)
    severity_rmse_nok: float
    calibration_slope: float    # logistic slope; 1.0=perfect
    computed_at: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "EvaluationMetrics":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class LearningCycleResult:
    """Summary returned by LearningLoop.run_cycle()."""
    cycle_id: int
    operator_id: str
    forecast_year: int
    metrics_by_risk_type: Dict[str, EvaluationMetrics]
    retrain_triggered: bool
    models_promoted: List[str]
    overall_brier_improvement: float   # vs previous cycle; positive=better
    learning_status: str               # "cold" | "warming" | "active"

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["metrics_by_risk_type"] = {
            k: v.to_dict() for k, v in self.metrics_by_risk_type.items()
        }
        return d
