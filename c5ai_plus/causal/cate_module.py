"""
C5AI+ v5.0 – Causal Treatment Effect Module (Optional).

Provides Conditional Average Treatment Effect (CATE) estimation using
the T-Learner meta-learner from the econml library.

Use case: Estimate the causal effect of specific interventions
(e.g. early harvest, lice treatment, HAB evacuation) on economic loss,
holding confounders constant.

Availability
------------
This module is OPTIONAL. It requires econml (and its dependencies) to be
installed. The rest of C5AI+ operates without it.

To install: pip install "shield-feasibility[ml-advanced]"

Phase note
----------
This is a Phase 3 capability. In Phase 1 and 2, this module is imported
only if explicitly requested, and its absence has no effect on forecasting.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Optional import guard ──────────────────────────────────────────────────────
try:
    from econml.metalearners import TLearner
    from sklearn.ensemble import RandomForestRegressor
    _ECONML_AVAILABLE = True
except ImportError:
    _ECONML_AVAILABLE = False


class CATEModule:
    """
    Conditional Average Treatment Effect estimator for aquaculture interventions.

    Wraps econml's TLearner with a RandomForest base learner.

    Parameters
    ----------
    intervention_col : str
        Name of the treatment column (1 = treated, 0 = control).

    Raises
    ------
    ImportError
        If econml is not installed.
    """

    def __init__(self, intervention_col: str = "treatment_applied"):
        if not _ECONML_AVAILABLE:
            raise ImportError(
                "econml is required for CATE estimation. "
                "Install it with: pip install 'shield-feasibility[ml-advanced]'"
            )
        self.intervention_col = intervention_col
        self._estimator = TLearner(
            models=RandomForestRegressor(n_estimators=200, random_state=42)
        )
        self._fitted = False

    def fit(
        self,
        X: np.ndarray,
        treatment: np.ndarray,
        outcome: np.ndarray,
    ) -> "CATEModule":
        """
        Fit the T-Learner on observed data.

        Parameters
        ----------
        X : np.ndarray, shape (n_samples, n_features)
            Confounding covariates (temperature, season, prior lice count, etc.)
        treatment : np.ndarray, shape (n_samples,), binary
            Treatment indicator (1 = intervention applied, 0 = control).
        outcome : np.ndarray, shape (n_samples,)
            Observed economic outcome (loss in NOK, or lice burden proxy).
        """
        self._estimator.fit(Y=outcome, T=treatment, X=X)
        self._fitted = True
        return self

    def effect(self, X: np.ndarray) -> np.ndarray:
        """
        Estimate CATE: E[Y(1) - Y(0) | X].

        Returns
        -------
        np.ndarray, shape (n_samples,)
            Estimated treatment effect per observation. Negative values
            indicate the treatment reduces the outcome (loss).
        """
        if not self._fitted:
            raise RuntimeError("Model must be fitted before calling effect().")
        return self._estimator.effect(X)

    def ate(self, X: np.ndarray) -> float:
        """Average Treatment Effect across the sample."""
        return float(self.effect(X).mean())

    @staticmethod
    def is_available() -> bool:
        """Return True if econml is installed and CATE estimation is possible."""
        return _ECONML_AVAILABLE

    @staticmethod
    def availability_note() -> str:
        if _ECONML_AVAILABLE:
            return "econml available – CATE estimation enabled."
        return (
            "econml not installed – CATE estimation unavailable. "
            "Install with: pip install 'shield-feasibility[ml-advanced]'"
        )
