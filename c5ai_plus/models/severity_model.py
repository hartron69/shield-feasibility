"""
C5AI+ v5.0 – Severity (Loss) Models for the Learning Loop.

LogNormalSeverityModel: online MLE via Welford's algorithm.
Falls back to config prior when fewer than 3 observed losses are available.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple


class LogNormalSeverityModel:
    """
    Online LogNormal MLE for observed loss amounts.

    Uses Welford's algorithm to maintain running log-space mean and variance
    without storing all historical observations.

    Parameters
    ----------
    prior_mean_nok : float
        Prior expected loss when no data is available.
    prior_cv : float
        Prior coefficient of variation (σ / μ in linear space).
    """

    MODEL_TYPE = "lognormal_severity"

    def __init__(
        self,
        prior_mean_nok: float = 1_000_000.0,
        prior_cv: float = 0.60,
        n_obs: int = 0,
        log_mean: Optional[float] = None,
        log_m2: float = 0.0,   # running sum of squared deviations in log-space
        _version: str = "v1.0",
    ):
        self._prior_mean_nok = float(prior_mean_nok)
        self._prior_cv = float(prior_cv)
        self._n_obs = n_obs
        self._log_mean = log_mean   # running mean of log(loss)
        self._log_m2 = float(log_m2)
        self._version = _version

    # ── Public API ────────────────────────────────────────────────────────────

    def predict(
        self,
        biomass_value_nok: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """
        Return (mean, p50, p90) in NOK.

        When data is insufficient (< 3 obs), uses the prior anchored to
        biomass_value_nok if provided.
        """
        if self._n_obs < 3 or self._log_mean is None:
            return self._prior_prediction(biomass_value_nok)
        mu, sigma = self._log_params()
        mean_nok = math.exp(mu + 0.5 * sigma ** 2)
        p50_nok = math.exp(mu)
        p90_nok = math.exp(mu + 1.2816 * sigma)
        return mean_nok, p50_nok, p90_nok

    def update(self, observed_loss_nok: float) -> None:
        """
        Incorporate one new loss observation (must be > 0).

        Silently ignores non-positive values.
        """
        if observed_loss_nok <= 0:
            return
        log_x = math.log(observed_loss_nok)
        self._n_obs += 1
        if self._log_mean is None:
            self._log_mean = log_x
            self._log_m2 = 0.0
        else:
            delta = log_x - self._log_mean
            self._log_mean += delta / self._n_obs
            delta2 = log_x - self._log_mean
            self._log_m2 += delta * delta2
        self._version = self._next_version(self._version)

    @property
    def n_obs(self) -> int:
        return self._n_obs

    @property
    def version(self) -> str:
        return self._version

    # ── Internals ─────────────────────────────────────────────────────────────

    def _log_params(self) -> Tuple[float, float]:
        """Return (mu, sigma) of the fitted log-normal."""
        mu = self._log_mean if self._log_mean is not None else 0.0
        if self._n_obs >= 2:
            var = self._log_m2 / (self._n_obs - 1)
            sigma = math.sqrt(max(var, 1e-8))
        else:
            sigma = math.sqrt(math.log(1 + self._prior_cv ** 2))
        return mu, sigma

    def _prior_prediction(
        self,
        biomass_value_nok: Optional[float],
    ) -> Tuple[float, float, float]:
        base = biomass_value_nok if biomass_value_nok else self._prior_mean_nok
        mean_nok = base * 0.10   # 10% of biomass as default prior loss
        cv = self._prior_cv
        sigma = math.sqrt(math.log(1 + cv ** 2))
        mu = math.log(mean_nok) - 0.5 * sigma ** 2
        p50_nok = math.exp(mu)
        p90_nok = math.exp(mu + 1.2816 * sigma)
        return mean_nok, p50_nok, p90_nok

    @staticmethod
    def _next_version(current: str) -> str:
        try:
            major, minor = current.lstrip("v").split(".")
            return f"v{major}.{int(minor) + 1}"
        except Exception:
            return "v1.0"

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "model_type": self.MODEL_TYPE,
            "prior_mean_nok": self._prior_mean_nok,
            "prior_cv": self._prior_cv,
            "n_obs": self._n_obs,
            "log_mean": self._log_mean,
            "log_m2": self._log_m2,
            "version": self._version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LogNormalSeverityModel":
        return cls(
            prior_mean_nok=d.get("prior_mean_nok", 1_000_000.0),
            prior_cv=d.get("prior_cv", 0.60),
            n_obs=d.get("n_obs", 0),
            log_mean=d.get("log_mean"),
            log_m2=d.get("log_m2", 0.0),
            _version=d.get("version", "v1.0"),
        )
