"""
C5AI+ v5.0 – Probability Models for the Learning Loop.

Two implementations share a common interface:
  - BetaBinomialModel  : Bayesian conjugate, works from sample 1
  - SklearnProbabilityModel : RandomForest, requires >= 20 observations

Both are safe to use without sklearn installed (SklearnProbabilityModel will
raise ImportError gracefully at construction time).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseProbabilityModel(ABC):
    """Shared interface for all probability models."""

    @abstractmethod
    def predict(self, features: Optional[Dict[str, Any]] = None) -> float:
        """Return the current probability estimate in [0, 1]."""

    @abstractmethod
    def update(self, event_occurred: bool) -> None:
        """Incorporate one new observation."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Monotonically increasing version string e.g. 'v1.3'."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialise to JSON-compatible dict."""

    @classmethod
    @abstractmethod
    def from_dict(cls, d: dict) -> "BaseProbabilityModel":
        """Reconstruct from serialised dict."""

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _next_version(current: str) -> str:
        """Increment minor version: 'v1.3' → 'v1.4'."""
        try:
            major, minor = current.lstrip("v").split(".")
            return f"v{major}.{int(minor) + 1}"
        except Exception:
            return "v1.0"


# ── Beta-Binomial conjugate ──────────────────────────────────────────────────

class BetaBinomialModel(BaseProbabilityModel):
    """
    Beta-Binomial conjugate model.

    Prior: Beta(alpha_0, beta_0) where
        alpha_0 = prior_prob * concentration
        beta_0  = (1 - prior_prob) * concentration

    Each observation updates:
        alpha += event_occurred
        beta  += 1 - event_occurred

    Posterior mean = alpha / (alpha + beta).
    """

    MODEL_TYPE = "beta_binomial"

    def __init__(
        self,
        prior_prob: float = 0.12,
        concentration: float = 5.0,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        n_updates: int = 0,
        _version: str = "v1.0",
    ):
        if alpha is None:
            alpha = prior_prob * concentration
        if beta is None:
            beta = (1.0 - prior_prob) * concentration
        self._alpha = float(alpha)
        self._beta = float(beta)
        self._n_updates = n_updates
        self._version = _version

    # ── Interface ─────────────────────────────────────────────────────────

    def predict(self, features: Optional[Dict[str, Any]] = None) -> float:
        return self._alpha / (self._alpha + self._beta)

    def update(self, event_occurred: bool) -> None:
        self._alpha += float(event_occurred)
        self._beta += float(not event_occurred)
        self._n_updates += 1
        self._version = self._next_version(self._version)

    @property
    def version(self) -> str:
        return self._version

    @property
    def n_updates(self) -> int:
        return self._n_updates

    def to_dict(self) -> dict:
        return {
            "model_type": self.MODEL_TYPE,
            "alpha": self._alpha,
            "beta": self._beta,
            "n_updates": self._n_updates,
            "version": self._version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BetaBinomialModel":
        return cls(
            alpha=d["alpha"],
            beta=d["beta"],
            n_updates=d.get("n_updates", 0),
            _version=d.get("version", "v1.0"),
        )


# ── RandomForest wrapper ─────────────────────────────────────────────────────

class SklearnProbabilityModel(BaseProbabilityModel):
    """
    RandomForestClassifier retrained from scratch on accumulated events.

    Only usable when sklearn is installed and n_observations >= 20.
    Raises ImportError at construction time if sklearn is absent.

    Features used for prediction are the observation index (default)
    or any dict passed to predict().
    """

    MODEL_TYPE = "sklearn_rf"

    def __init__(
        self,
        observations: Optional[List[bool]] = None,
        n_estimators: int = 50,
        random_state: int = 42,
        _version: str = "v1.0",
    ):
        try:
            from sklearn.ensemble import RandomForestClassifier  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "sklearn is required for SklearnProbabilityModel. "
                "Install with: pip install scikit-learn"
            ) from exc

        self._observations: List[bool] = list(observations or [])
        self._n_estimators = n_estimators
        self._random_state = random_state
        self._version = _version
        self._model = None
        if len(self._observations) >= 20:
            self._fit()

    # ── Interface ─────────────────────────────────────────────────────────

    def predict(self, features: Optional[Dict[str, Any]] = None) -> float:
        if self._model is None:
            # Not enough data to train — return base rate
            if not self._observations:
                return 0.12
            return sum(self._observations) / len(self._observations)
        # Feature: index (time-based)
        idx = len(self._observations)
        X = [[idx]]
        prob = self._model.predict_proba(X)[0]
        # class order: [False, True] → index 1 is P(event)
        classes = list(self._model.classes_)
        if True in classes:
            return float(prob[classes.index(True)])
        return float(prob[-1])

    def update(self, event_occurred: bool) -> None:
        self._observations.append(event_occurred)
        if len(self._observations) >= 20:
            self._fit()
        self._version = self._next_version(self._version)

    @property
    def version(self) -> str:
        return self._version

    @property
    def n_observations(self) -> int:
        return len(self._observations)

    def _fit(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        X = [[i] for i in range(len(self._observations))]
        y = [int(v) for v in self._observations]
        # Guard: need at least 2 classes
        if len(set(y)) < 2:
            self._model = None
            return
        clf = RandomForestClassifier(
            n_estimators=self._n_estimators,
            random_state=self._random_state,
            class_weight="balanced",
        )
        clf.fit(X, y)
        self._model = clf

    def to_dict(self) -> dict:
        return {
            "model_type": self.MODEL_TYPE,
            "observations": [bool(o) for o in self._observations],
            "n_estimators": self._n_estimators,
            "random_state": self._random_state,
            "version": self._version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SklearnProbabilityModel":
        return cls(
            observations=[bool(o) for o in d.get("observations", [])],
            n_estimators=d.get("n_estimators", 50),
            random_state=d.get("random_state", 42),
            _version=d.get("version", "v1.0"),
        )


# ── Factory ──────────────────────────────────────────────────────────────────

def probability_model_from_dict(d: dict) -> BaseProbabilityModel:
    """Reconstruct the right model class from a serialised dict."""
    model_type = d.get("model_type", BetaBinomialModel.MODEL_TYPE)
    if model_type == SklearnProbabilityModel.MODEL_TYPE:
        try:
            return SklearnProbabilityModel.from_dict(d)
        except ImportError:
            # Fall back to BetaBinomial derived from observation history
            obs = d.get("observations", [])
            alpha = sum(bool(o) for o in obs) + 0.6
            beta = sum(not bool(o) for o in obs) + 4.4
            return BetaBinomialModel(alpha=alpha, beta=beta,
                                     n_updates=len(obs),
                                     _version=d.get("version", "v1.0"))
    return BetaBinomialModel.from_dict(d)
