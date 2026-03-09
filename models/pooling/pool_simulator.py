"""
Pool simulator: generate synthetic pool members and simulate correlated losses.

v2.1 simplifications (see KNOWN_SIMPLIFICATIONS in assumptions.py):
  - Members 2..N are synthetic: risk parameters perturbed from the operator's
    values using similarity_spread (multiplicative uniform noise).
  - Correlation is injected via rank-based blending of a shared Gaussian factor.
    This gives approximate Pearson correlation ≈ rho (not exact Gaussian copula).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from data.input_schema import OperatorInput
from models.pooling.assumptions import PoolingAssumptions


@dataclass
class PoolMemberSpec:
    """Risk parameters for one pool member."""
    member_id: int
    label: str                  # "Operator (you)" or "Synthetic Member N"
    expected_events: float
    mean_severity: float
    cv_severity: float
    expected_annual_loss: float  # = expected_events × mean_severity


# ── Internal helpers ──────────────────────────────────────────────────────────

def _compound_poisson_lognormal(
    expected_events: float,
    mean_severity: float,
    cv_severity: float,
    n_sims: int,
    n_years: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Vectorised Compound Poisson-LogNormal simulation. Returns (n_sims, n_years)."""
    sigma2 = np.log(1.0 + cv_severity ** 2)
    mu_sev = np.log(mean_severity) - 0.5 * sigma2
    sigma_sev = float(np.sqrt(sigma2))

    k_mat = rng.poisson(lam=expected_events, size=(n_sims, n_years))
    max_k = int(k_mat.max())

    losses = np.zeros((n_sims, n_years), dtype=np.float64)
    # Vectorised loop: iterate over event count, accumulate masked severity draws
    for j in range(1, max_k + 1):
        mask = k_mat >= j
        if mask.any():
            sev = rng.lognormal(mu_sev, sigma_sev, size=(n_sims, n_years))
            losses += sev * mask
    return losses


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pool_member_specs(
    operator: OperatorInput,
    assumptions: PoolingAssumptions,
    rng: np.random.Generator,
) -> List[PoolMemberSpec]:
    """Return PoolMemberSpec list: member 0 = operator, 1..N-1 = synthetic peers.

    Synthetic parameters are drawn by multiplying the operator's risk params by a
    factor uniformly distributed in [1 - spread, 1 + spread].
    """
    rp = operator.risk_params
    spread = assumptions.similarity_spread
    specs: List[PoolMemberSpec] = [
        PoolMemberSpec(
            member_id=0,
            label="Operator (you)",
            expected_events=rp.expected_annual_events,
            mean_severity=rp.mean_loss_severity,
            cv_severity=rp.cv_loss_severity,
            expected_annual_loss=rp.expected_annual_events * rp.mean_loss_severity,
        )
    ]
    for i in range(1, assumptions.n_members):
        f_ev = max(1.0 + rng.uniform(-spread, spread), 0.10)
        f_sev = max(1.0 + rng.uniform(-spread, spread), 0.10)
        ev = rp.expected_annual_events * f_ev
        sev = rp.mean_loss_severity * f_sev
        specs.append(PoolMemberSpec(
            member_id=i,
            label=f"Synthetic Member {i + 1}",
            expected_events=ev,
            mean_severity=sev,
            cv_severity=rp.cv_loss_severity,
            expected_annual_loss=ev * sev,
        ))
    return specs


def simulate_raw_member_losses(
    specs: List[PoolMemberSpec],
    operator_losses: np.ndarray,  # (N, T) already simulated
    n_sims: int,
    n_years: int,
    rng: np.random.Generator,
) -> List[np.ndarray]:
    """Return list of (n_sims, n_years) loss arrays, one per member.

    Member 0 re-uses the pre-computed operator losses (no re-simulation).
    Members 1..N-1 get fresh Compound Poisson-LogNormal draws.
    """
    raw: List[np.ndarray] = []
    for spec in specs:
        if spec.member_id == 0:
            raw.append(operator_losses.copy())
        else:
            losses = _compound_poisson_lognormal(
                spec.expected_events, spec.mean_severity, spec.cv_severity,
                n_sims, n_years, rng,
            )
            raw.append(losses)
    return raw


def apply_rank_correlation(
    raw_losses: List[np.ndarray],  # list of (N, T)
    rho: float,
    rng: np.random.Generator,
) -> List[np.ndarray]:
    """Inject inter-member correlation via rank-based Gaussian factor blending.

    Mechanism (v2.1 approximation):
        For each year t, each member's losses are reordered to match the rank of a
        blended factor:  F = sqrt(rho) * Z_common + sqrt(1-rho) * Z_idiosyncratic
        This yields Spearman correlation ≈ rho.  Simultaneous extreme events are
        slightly underestimated compared to a Gaussian copula (known limitation).
    """
    if rho <= 0.0 or len(raw_losses) <= 1:
        return raw_losses

    N, T = raw_losses[0].shape
    w = float(np.sqrt(rho))
    w_idio = float(np.sqrt(max(1.0 - rho, 0.0)))
    Z_common = rng.standard_normal((N, T))

    correlated: List[np.ndarray] = []
    for losses in raw_losses:
        Z_idio = rng.standard_normal((N, T))
        blend = w * Z_common + w_idio * Z_idio           # (N, T)
        L_corr = np.empty_like(losses)
        for t in range(T):
            sorted_losses = np.sort(losses[:, t])
            rank_order = np.argsort(np.argsort(blend[:, t]))
            L_corr[:, t] = sorted_losses[rank_order]
        correlated.append(L_corr)
    return correlated


def build_pool(
    operator: OperatorInput,
    operator_losses: np.ndarray,  # (N, T) from existing simulation
    assumptions: PoolingAssumptions,
    n_sims: int,
    n_years: int = 5,
) -> Tuple[List[PoolMemberSpec], List[np.ndarray]]:
    """Build the full pool: specs + correlated loss arrays.

    Returns
    -------
    specs
        One PoolMemberSpec per member (member 0 = operator).
    correlated_losses
        List of (n_sims, n_years) arrays with inter-member correlation applied.
    """
    rng = np.random.default_rng(assumptions.rng_seed)
    specs = generate_pool_member_specs(operator, assumptions, rng)
    raw = simulate_raw_member_losses(specs, operator_losses, n_sims, n_years, rng)
    correlated = apply_rank_correlation(raw, assumptions.inter_member_correlation, rng)
    return specs, correlated
