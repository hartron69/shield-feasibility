"""
Pooled PCC economics: aggregate pool losses, apply reinsurance, allocate to operator.

Allocation basis: each member's share of pool costs is proportional to their
weight (expected_loss or premium basis as configured in PoolingAssumptions).

The diversification benefit arises because:
    Var(pool share) = Var(member) × (1 + (N-1)×rho) / N
    → Per-operator std dev reduces by factor sqrt((1+(N-1)×rho)/N)
    → e.g. N=4, rho=0.25: reduction to ~66% of standalone std dev
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from models.pcc_economics import PCCAssumptions, apply_pcc_reinsurance_structure
from models.pooling.assumptions import PoolingAssumptions
from models.pooling.pool_simulator import PoolMemberSpec
from config.settings import SETTINGS


@dataclass
class MemberAllocation:
    """Cost allocation result for one pool member."""
    member_id: int
    label: str
    expected_annual_loss: float
    allocation_weight: float
    standalone_cv: float           # CV of member's own standalone losses
    pooled_cv: float               # CV of member's allocated share of pool
    allocated_ri_premium_annual: float
    allocated_scr: float
    allocated_admin_annual: float
    allocated_setup: float
    allocated_5yr_tcor: float


@dataclass
class PooledEconomicsResult:
    """Full output of the pooled PCC economics calculation."""
    # ── Pool aggregate ────────────────────────────────────────────────────────
    n_members: int
    pooled_mean_annual_loss: float
    pooled_std_annual_loss: float
    pooled_cv: float
    pooled_var_995: float
    pooled_ri_premium: float
    pooled_scr: float
    pooled_retention: float
    pooled_ri_limit: float

    # ── Standalone operator (for comparison) ──────────────────────────────────
    standalone_cv: float
    standalone_var_995: float

    # ── Reduction metrics ─────────────────────────────────────────────────────
    cv_reduction_pct: float
    var_reduction_pct: float
    ri_premium_reduction_pct: float
    scr_reduction_pct: float
    tcor_improvement_pct: float

    # ── Operator allocation ───────────────────────────────────────────────────
    operator_allocation: MemberAllocation
    all_allocations: List[MemberAllocation]

    # ── TCOR comparison ───────────────────────────────────────────────────────
    operator_5yr_tcor_standalone: float
    operator_5yr_tcor_pooled: float


def _var_995(losses_1d: np.ndarray) -> float:
    return float(np.percentile(losses_1d, 99.5))


def _cv(losses_1d: np.ndarray) -> float:
    mean = float(losses_1d.mean())
    return float(losses_1d.std()) / max(mean, 1.0)


def compute_pooled_economics(
    specs: List[PoolMemberSpec],
    correlated_losses: List[np.ndarray],   # (N, T) per member
    operator_losses: np.ndarray,            # (N, T) standalone operator
    operator_standalone_ri_premium: float,
    operator_standalone_scr: float,
    assumptions: PoolingAssumptions,
    standalone_pcc_assumptions: PCCAssumptions,
    n_years: int = 5,
) -> PooledEconomicsResult:
    """Compute pooled PCC economics and allocate results to each member."""
    N, T = correlated_losses[0].shape

    # ── Pool aggregate ────────────────────────────────────────────────────────
    pooled_annual = sum(correlated_losses)           # (N, T)
    pool_per_sim = pooled_annual.mean(axis=1)        # (N,) mean annual loss per sim
    pooled_mean = float(pool_per_sim.mean())
    pooled_std = float(pool_per_sim.std())
    pool_cv = pooled_std / max(pooled_mean, 1.0)
    pool_var = _var_995(pool_per_sim)

    # ── Pool RI ───────────────────────────────────────────────────────────────
    _, pool_ri_recovery = apply_pcc_reinsurance_structure(
        pooled_annual,
        assumptions.pooled_retention_nok,
        assumptions.pooled_ri_limit_nok,
    )
    pooled_ri_premium = float(pool_ri_recovery.mean()) * assumptions.pooled_ri_loading_factor

    # ── Pool SCR (net retained) ───────────────────────────────────────────────
    net_pool_retained, _ = apply_pcc_reinsurance_structure(
        pooled_annual,
        assumptions.pooled_retention_nok,
        assumptions.pooled_ri_limit_nok,
    )
    net_pool_per_sim = net_pool_retained.mean(axis=1)
    net_pool_var = _var_995(net_pool_per_sim)
    exp_net_pool = float(net_pool_per_sim.mean())
    pooled_tp = exp_net_pool * (1 + standalone_pcc_assumptions.tp_load)
    pooled_scr = max(0.0, net_pool_var - pooled_tp)

    # ── Standalone operator metrics ───────────────────────────────────────────
    op_per_sim = operator_losses.mean(axis=1)
    sa_cv = _cv(op_per_sim)
    sa_var = _var_995(op_per_sim)

    # ── Allocation weights ────────────────────────────────────────────────────
    total_eal = sum(s.expected_annual_loss for s in specs)
    weights = [s.expected_annual_loss / max(total_eal, 1.0) for s in specs]

    # ── Admin / setup pool economics ──────────────────────────────────────────
    n_m = len(specs)
    standalone_admin = standalone_pcc_assumptions.admin_fee_nok
    pooled_admin_total = standalone_admin * n_m * (1 - assumptions.shared_admin_saving_pct)
    # Each member shares equally in admin (governance shared)
    admin_per_member = pooled_admin_total / n_m

    standalone_setup = standalone_pcc_assumptions.formation_cost_nok
    pooled_setup_total = standalone_setup * n_m * 0.75   # 25% setup saving from shared legal
    setup_per_member = pooled_setup_total / n_m

    # ── Per-member allocations ────────────────────────────────────────────────
    inv_return = standalone_pcc_assumptions.investment_return_pct
    coc = SETTINGS.cost_of_capital_rate

    all_allocations: List[MemberAllocation] = []
    for i, (spec, losses_m, w) in enumerate(zip(specs, correlated_losses, weights)):
        # Member standalone CV (their own simulated losses)
        m_per_sim = losses_m.mean(axis=1)
        m_cv = _cv(m_per_sim)

        # Member's share of pool — CV reflects diversification
        share_per_sim = pool_per_sim * w
        share_cv = _cv(share_per_sim)

        # Allocated costs (weight-proportional for RI and SCR)
        alloc_ri = pooled_ri_premium * w
        alloc_scr = pooled_scr * w
        alloc_setup = setup_per_member

        # 5yr TCOR for this member
        annual_cost = alloc_ri + admin_per_member + alloc_scr * coc - alloc_scr * inv_return
        tcor_5yr = annual_cost * n_years + alloc_setup

        all_allocations.append(MemberAllocation(
            member_id=spec.member_id,
            label=spec.label,
            expected_annual_loss=spec.expected_annual_loss,
            allocation_weight=w,
            standalone_cv=sa_cv if i == 0 else m_cv,
            pooled_cv=share_cv,
            allocated_ri_premium_annual=alloc_ri,
            allocated_scr=alloc_scr,
            allocated_admin_annual=admin_per_member,
            allocated_setup=alloc_setup,
            allocated_5yr_tcor=tcor_5yr,
        ))

    op_alloc = all_allocations[0]

    # ── Comparison metrics ────────────────────────────────────────────────────
    def _pct_reduction(old: float, new: float) -> float:
        return (old - new) / max(old, 1e-10) * 100

    cv_reduction = _pct_reduction(sa_cv, op_alloc.pooled_cv)
    var_op_pooled = pool_var * weights[0]
    var_reduction = _pct_reduction(sa_var, var_op_pooled)
    ri_reduction = _pct_reduction(operator_standalone_ri_premium, op_alloc.allocated_ri_premium_annual)
    scr_reduction = _pct_reduction(operator_standalone_scr, op_alloc.allocated_scr)

    # Standalone PCC 5yr TCOR (economics cost only, not losses)
    sa_annual_cost = (
        operator_standalone_ri_premium
        + standalone_admin
        + operator_standalone_scr * coc
        - operator_standalone_scr * inv_return
    )
    sa_5yr_tcor = sa_annual_cost * n_years + standalone_setup
    tcor_improvement = _pct_reduction(sa_5yr_tcor, op_alloc.allocated_5yr_tcor)

    return PooledEconomicsResult(
        n_members=n_m,
        pooled_mean_annual_loss=pooled_mean,
        pooled_std_annual_loss=pooled_std,
        pooled_cv=pool_cv,
        pooled_var_995=pool_var,
        pooled_ri_premium=pooled_ri_premium,
        pooled_scr=pooled_scr,
        pooled_retention=assumptions.pooled_retention_nok,
        pooled_ri_limit=assumptions.pooled_ri_limit_nok,
        standalone_cv=sa_cv,
        standalone_var_995=sa_var,
        cv_reduction_pct=cv_reduction,
        var_reduction_pct=var_reduction,
        ri_premium_reduction_pct=ri_reduction,
        scr_reduction_pct=scr_reduction,
        tcor_improvement_pct=tcor_improvement,
        operator_allocation=op_alloc,
        all_allocations=all_allocations,
        operator_5yr_tcor_standalone=sa_5yr_tcor,
        operator_5yr_tcor_pooled=op_alloc.allocated_5yr_tcor,
    )
