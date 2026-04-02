"""
backend/services/locality_mc_runner.py

Runs MonteCarloEngine for a single locality using LocalityRiskProfile as input.
Returns a LocalityMCResult with EAL, SCR, and domain breakdown.

Architecture
------------
  LocalityRiskProfile (Sprint 1)
      → build_locality_mc_inputs()        (models/locality_mc_inputs.py)
      → OperatorInput
      → MonteCarloEngine (existing, unchanged)
          + DomainCorrelationMatrix.expert_default()
          + cage_multipliers   (from profile.domain_multipliers)
          + non_bio_domain_fracs (from profile.domain_weights)
      → SimulationResults
      → LocalityMCResult
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from models.domain_correlation import DomainCorrelationMatrix
from models.locality_mc_inputs import LocalityMonteCarloInput, build_locality_mc_inputs
from models.locality_risk_profile import DOMAINS, LocalityRiskProfile
from models.monte_carlo import MonteCarloEngine
from backend.services.locality_risk_builder import build_locality_risk_profile


# ── Default simulation parameters ──────────────────────────────────────────────

_DEFAULT_N_SIMS: int = 5_000    # per-locality: fast enough for API, stable enough for SCR
_DEFAULT_SEED:   int = 42


# ── Result model ────────────────────────────────────────────────────────────────

@dataclass
class LocalityMCResult:
    """
    Structured output of a single-locality Monte Carlo simulation.

    All monetary values in NOK.
    """

    locality_id:   str
    locality_name: str

    # ── Core risk metrics ───────────────────────────────────────────────────────
    eal_nok:      float    # E[Annual Loss] = mean_annual_loss
    scr_nok:      float    # VaR(99.5%)  — Solvency Capital Requirement anchor
    var_99_nok:   float    # VaR(99%)
    var_95_nok:   float    # VaR(95%)
    std_nok:      float    # standard deviation of annual loss
    tvar_95_nok:  float    # Tail VaR (expected shortfall above 95th pctl)

    # ── Frequency ───────────────────────────────────────────────────────────────
    mean_event_count: float

    # ── Domain decomposition ────────────────────────────────────────────────────
    domain_eal_nok:   Dict[str, float]   # {bio: NOK, struct: NOK, env: NOK, ops: NOK}
    domain_fractions: Dict[str, float]   # {bio: 0.45, …}  — sum=1

    # ── Input transparency ──────────────────────────────────────────────────────
    effective_expected_events:   float
    effective_mean_severity_nok: float
    frequency_multiplier:        float
    severity_multiplier:         float
    base_expected_events:        float
    base_mean_severity_nok:      float
    total_risk_score:            float

    # ── Provenance ──────────────────────────────────────────────────────────────
    n_simulations: int
    domain_correlation_applied: bool
    source: str = "locality_mc"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "locality_id":   self.locality_id,
            "locality_name": self.locality_name,
            "eal_nok":       self.eal_nok,
            "scr_nok":       self.scr_nok,
            "var_99_nok":    self.var_99_nok,
            "var_95_nok":    self.var_95_nok,
            "std_nok":       self.std_nok,
            "tvar_95_nok":   self.tvar_95_nok,
            "mean_event_count": self.mean_event_count,
            "domain_eal_nok":   self.domain_eal_nok,
            "domain_fractions": self.domain_fractions,
            "effective_expected_events":   self.effective_expected_events,
            "effective_mean_severity_nok": self.effective_mean_severity_nok,
            "frequency_multiplier":        self.frequency_multiplier,
            "severity_multiplier":         self.severity_multiplier,
            "base_expected_events":        self.base_expected_events,
            "base_mean_severity_nok":      self.base_mean_severity_nok,
            "total_risk_score":            self.total_risk_score,
            "n_simulations":               self.n_simulations,
            "domain_correlation_applied":  self.domain_correlation_applied,
            "source":                      self.source,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LocalityMCResult":
        return cls(
            locality_id=d["locality_id"],
            locality_name=d["locality_name"],
            eal_nok=float(d["eal_nok"]),
            scr_nok=float(d["scr_nok"]),
            var_99_nok=float(d["var_99_nok"]),
            var_95_nok=float(d["var_95_nok"]),
            std_nok=float(d["std_nok"]),
            tvar_95_nok=float(d["tvar_95_nok"]),
            mean_event_count=float(d["mean_event_count"]),
            domain_eal_nok=dict(d["domain_eal_nok"]),
            domain_fractions=dict(d["domain_fractions"]),
            effective_expected_events=float(d["effective_expected_events"]),
            effective_mean_severity_nok=float(d["effective_mean_severity_nok"]),
            frequency_multiplier=float(d["frequency_multiplier"]),
            severity_multiplier=float(d["severity_multiplier"]),
            base_expected_events=float(d["base_expected_events"]),
            base_mean_severity_nok=float(d["base_mean_severity_nok"]),
            total_risk_score=float(d["total_risk_score"]),
            n_simulations=int(d["n_simulations"]),
            domain_correlation_applied=bool(d["domain_correlation_applied"]),
            source=d.get("source", "locality_mc"),
        )


# ── Runner ──────────────────────────────────────────────────────────────────────

def run_locality_mc(
    locality_id: str,
    cages: Optional[List] = None,
    n_simulations: int = _DEFAULT_N_SIMS,
    seed: int = _DEFAULT_SEED,
) -> LocalityMCResult:
    """
    Run a single-locality Monte Carlo simulation.

    Parameters
    ----------
    locality_id : str
    cages : list[CagePenConfig] | None
        Optional cage portfolio — enables advanced domain weighting.
    n_simulations : int
        Number of Monte Carlo trials (default 5000).
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    LocalityMCResult
    """
    profile  = build_locality_risk_profile(locality_id, cages=cages)
    mc_input = build_locality_mc_inputs(profile)

    domain_corr = DomainCorrelationMatrix.expert_default()

    sim = MonteCarloEngine(
        operator=mc_input.operator_input,
        n_simulations=n_simulations,
        seed=seed,
        domain_correlation=domain_corr,
        cage_multipliers=mc_input.cage_multipliers,
        non_bio_domain_fracs=mc_input.non_bio_domain_fracs,
    ).run()

    domain_eal, domain_fracs = _extract_domain_breakdown(sim, profile)

    return LocalityMCResult(
        locality_id=locality_id,
        locality_name=profile.locality_name,
        eal_nok=round(sim.mean_annual_loss),
        scr_nok=round(sim.var_995),
        var_99_nok=round(sim.var_99),
        var_95_nok=round(sim.var_95),
        std_nok=round(sim.std_annual_loss),
        tvar_95_nok=round(sim.tvar_95),
        mean_event_count=round(sim.mean_event_count, 3),
        domain_eal_nok={d: round(v) for d, v in domain_eal.items()},
        domain_fractions={d: round(v, 4) for d, v in domain_fracs.items()},
        effective_expected_events=round(mc_input.effective_expected_events, 4),
        effective_mean_severity_nok=round(mc_input.effective_mean_severity_nok),
        frequency_multiplier=round(mc_input.frequency_multiplier, 4),
        severity_multiplier=round(mc_input.severity_multiplier, 4),
        base_expected_events=round(mc_input.base_expected_events, 4),
        base_mean_severity_nok=round(mc_input.base_mean_severity_nok),
        total_risk_score=profile.total_risk_score,
        n_simulations=n_simulations,
        domain_correlation_applied=sim.domain_loss_breakdown is not None,
    )


def run_locality_mc_batch(
    locality_ids: List[str],
    n_simulations: int = _DEFAULT_N_SIMS,
    seed: int = _DEFAULT_SEED,
) -> List[Dict[str, Any]]:
    """
    Run per-locality MC for each ID. Unknown IDs produce error entries.

    Each locality uses `seed + index` for independence between localities
    while remaining reproducible.
    """
    from backend.services.live_risk_mock import get_all_locality_ids
    known = set(get_all_locality_ids())

    results = []
    for i, lid in enumerate(locality_ids):
        if lid not in known:
            results.append({"locality_id": lid, "error": f"Locality '{lid}' not found"})
            continue
        result = run_locality_mc(lid, n_simulations=n_simulations, seed=seed + i)
        results.append(result.to_dict())
    return results


# ── Private helpers ─────────────────────────────────────────────────────────────

def _extract_domain_breakdown(sim, profile: LocalityRiskProfile):
    """
    Extract per-domain EAL and fractions from SimulationResults.

    Falls back to profile.domain_weights if domain_loss_breakdown is absent.
    """
    domain_eal: Dict[str, float] = {}
    domain_fracs: Dict[str, float] = {}

    if sim.domain_loss_breakdown is not None:
        dt = sim.domain_loss_breakdown.domain_totals()
        for d in DOMAINS:
            arr = dt.get(d)
            domain_eal[d] = float(np.mean(arr)) if arr is not None else 0.0
        total = sum(domain_eal.values()) or float(sim.mean_annual_loss) or 1.0
        for d in DOMAINS:
            domain_fracs[d] = domain_eal[d] / total
    else:
        # Fallback: allocate EAL proportionally to domain_weights
        dw = profile.domain_weights.to_dict()
        for d in DOMAINS:
            domain_eal[d]  = sim.mean_annual_loss * dw[d]
            domain_fracs[d] = dw[d]

    return domain_eal, domain_fracs
