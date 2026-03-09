"""
Regime-switching model for annual risk multipliers.

In each simulation-year, a discrete regime is sampled from a probability
distribution over named risk states. The regime determines a multiplier
applied to the Poisson event-frequency parameter (lambda), so that some
simulation-years are drawn from a "high-risk" or "catastrophic" environment.

Simplifying assumptions
-----------------------
* Each (simulation, year) cell draws its regime independently. All sites
  within a portfolio experience the same regime in a given year — correct
  for systemic, correlated perils such as disease outbreaks or storm seasons.
* Probabilities must sum to 1.0 ± 1e-4 (numerical tolerance for float
  arithmetic when loading from config dicts).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskRegime:
    """
    A single named risk regime.

    Attributes
    ----------
    name : str
        Unique identifier for the regime (e.g. "normal_year").
    probability : float
        Prior probability of this regime occurring in any given year.
        All regimes in a RegimeModel must sum to 1.0.
    risk_multiplier : float
        Scalar applied to the Poisson lambda when this regime is active.
        Values > 1 increase expected event frequency; < 1 suppresses it.
    description : str
        Human-readable explanation for reports and logs.
    """

    name: str
    probability: float
    risk_multiplier: float
    description: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Predefined regime set
# ─────────────────────────────────────────────────────────────────────────────

PREDEFINED_REGIMES: Dict[str, RiskRegime] = {
    "normal_year": RiskRegime(
        name="normal_year",
        probability=0.75,
        risk_multiplier=1.0,
        description="Typical year with baseline event frequency",
    ),
    "high_bio_risk_year": RiskRegime(
        name="high_bio_risk_year",
        probability=0.20,
        risk_multiplier=1.8,
        description=(
            "Elevated biological risk: algal blooms, lice pressure, "
            "disease outbreak conditions"
        ),
    ),
    "catastrophic_year": RiskRegime(
        name="catastrophic_year",
        probability=0.05,
        risk_multiplier=3.5,
        description="Catastrophic year: multiple concurrent perils, systemic event",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Regime model
# ─────────────────────────────────────────────────────────────────────────────

class RegimeModel:
    """
    Discrete-state regime model for annual Poisson frequency scaling.

    Parameters
    ----------
    regimes : Dict[str, RiskRegime], optional
        Named regimes. Defaults to PREDEFINED_REGIMES (3 regimes totalling
        probability 1.0).

    Usage
    -----
    Pass an instance to MonteCarloEngine(regime_model=...).  The engine calls
    sample_regimes() to obtain per-cell multipliers applied to lambda before
    drawing Poisson event counts.
    """

    def __init__(self, regimes: Optional[Dict[str, RiskRegime]] = None) -> None:
        self.regimes: Dict[str, RiskRegime] = (
            regimes if regimes is not None else PREDEFINED_REGIMES.copy()
        )
        self._validate()
        # Pre-compute arrays in stable dict-insertion order for reproducibility
        self._names = list(self.regimes.keys())
        self._probs = np.array(
            [self.regimes[n].probability for n in self._names], dtype=float
        )
        self._multipliers = np.array(
            [self.regimes[n].risk_multiplier for n in self._names], dtype=float
        )

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self) -> None:
        if not self.regimes:
            raise ValueError("RegimeModel requires at least one regime")
        for name, regime in self.regimes.items():
            if regime.probability < 0:
                raise ValueError(
                    f"Regime '{name}' has negative probability {regime.probability}"
                )
            if regime.risk_multiplier < 0:
                raise ValueError(
                    f"Regime '{name}' has negative risk_multiplier "
                    f"{regime.risk_multiplier}"
                )
        total_prob = sum(r.probability for r in self.regimes.values())
        if abs(total_prob - 1.0) > 1e-4:
            raise ValueError(
                f"Regime probabilities must sum to 1.0, got {total_prob:.6f}"
            )

    # ── Sampling ──────────────────────────────────────────────────────────────

    def sample_regimes(
        self, N: int, T: int, rng: np.random.Generator
    ) -> np.ndarray:
        """
        Sample regime risk multipliers for N simulations × T years.

        Parameters
        ----------
        N : int
            Number of Monte Carlo simulations.
        T : int
            Projection years.
        rng : np.random.Generator
            Shared RNG (passed from MonteCarloEngine).

        Returns
        -------
        np.ndarray
            Shape (N, T), dtype float.  Each element is the risk_multiplier
            of the drawn regime.
        """
        indices = rng.choice(len(self._names), size=(N, T), p=self._probs)
        return self._multipliers[indices]  # (N, T)

    def sample_regime_names(
        self, N: int, T: int, rng: np.random.Generator
    ) -> np.ndarray:
        """
        Sample regime names for N simulations × T years.

        Returns
        -------
        np.ndarray
            Shape (N, T), dtype object (str).
        """
        names_arr = np.array(self._names, dtype=object)
        indices = rng.choice(len(self._names), size=(N, T), p=self._probs)
        return names_arr[indices]  # (N, T)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, d: Dict) -> "RegimeModel":
        """
        Construct a RegimeModel from a plain dict.

        Expected format::

            {
                "normal":   {"probability": 0.8, "risk_multiplier": 1.0},
                "bad_year": {"probability": 0.2, "risk_multiplier": 2.5,
                             "description": "Elevated risk year"},
            }

        Parameters
        ----------
        d : dict
            Keys are regime names; values are dicts with "probability" and
            "risk_multiplier" (required) and "description" (optional).

        Returns
        -------
        RegimeModel
        """
        regimes: Dict[str, RiskRegime] = {}
        for name, spec in d.items():
            regimes[name] = RiskRegime(
                name=name,
                probability=spec["probability"],
                risk_multiplier=spec["risk_multiplier"],
                description=spec.get("description", ""),
            )
        return cls(regimes=regimes)
