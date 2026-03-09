"""
Strategy: Pooled PCC Cell

The operator participates in a multi-operator risk pool. Pool losses are
simulated (with inter-member correlation), RI is applied at the pool level,
and resulting costs are allocated to each member by their expected-loss weight.

This strategy integrates into the standard StrategyResult framework so it
appears alongside Full Insurance, Hybrid, PCC Captive Cell, and Self-Insurance.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from config.settings import SETTINGS
from models.pcc_economics import PCCAssumptions, apply_pcc_reinsurance_structure
from models.pooling.assumptions import PoolingAssumptions
from models.pooling.pool_economics import PooledEconomicsResult, compute_pooled_economics
from models.pooling.pool_simulator import build_pool
from models.strategies.base_strategy import (
    AnnualCostBreakdown,
    BaseStrategy,
    StrategyResult,
)


class PooledPCCStrategy(BaseStrategy):
    """Pooled PCC captive cell: operator joins a peer risk-sharing pool."""

    def __init__(
        self,
        operator,
        sim,
        pooling_assumptions: Optional[PoolingAssumptions] = None,
        standalone_pcc_assumptions: Optional[PCCAssumptions] = None,
        standalone_ri_premium: float = 0.0,
        standalone_scr: float = 0.0,
    ):
        super().__init__(operator, sim)
        self.pooling_assumptions = pooling_assumptions or PoolingAssumptions()
        self.standalone_pcc = standalone_pcc_assumptions or PCCAssumptions.base()
        self.standalone_ri_premium = standalone_ri_premium
        self.standalone_scr = standalone_scr
        # Populated by calculate(); accessed by run_analysis for the API response
        self.pooled_economics: Optional[PooledEconomicsResult] = None

    def calculate(self) -> StrategyResult:
        assump = self.pooling_assumptions
        N = self.sim.annual_losses.shape[0]
        T = self.years

        # ── 1. Build pool (synthetic members + correlated losses) ─────────────
        specs, correlated_losses = build_pool(
            self.operator,
            self.sim.annual_losses,
            assump,
            n_sims=N,
            n_years=T,
        )

        # ── 2. Compute pooled economics + operator allocation ─────────────────
        economics = compute_pooled_economics(
            specs=specs,
            correlated_losses=correlated_losses,
            operator_losses=self.sim.annual_losses,
            operator_standalone_ri_premium=self.standalone_ri_premium,
            operator_standalone_scr=self.standalone_scr,
            assumptions=assump,
            standalone_pcc_assumptions=self.standalone_pcc,
            n_years=T,
        )
        self.pooled_economics = economics
        op_alloc = economics.operator_allocation

        # ── 3. Expected annual cost breakdown ─────────────────────────────────
        inv_return = self.standalone_pcc.investment_return_pct
        coc = SETTINGS.cost_of_capital_rate
        setup_total = self.standalone_pcc.formation_cost_nok * assump.n_members * 0.75
        setup_per_member = setup_total / assump.n_members

        annual_breakdown: List[AnnualCostBreakdown] = []
        expected_annual_costs: List[float] = []

        for yr in range(1, T + 1):
            infl = self._inflation_factor(yr)
            ri_yr = op_alloc.allocated_ri_premium_annual * infl
            admin_yr = op_alloc.allocated_admin_annual * infl
            cap_opp = op_alloc.allocated_scr * coc
            inv_income = op_alloc.allocated_scr * inv_return
            setup_yr = setup_per_member if yr == 1 else 0.0

            bd = AnnualCostBreakdown(
                year=yr,
                premium_paid=0.0,
                fronting_fee_paid=0.0,
                retained_losses=0.0,
                reinsurance_cost=ri_yr,
                admin_costs=admin_yr,
                capital_opportunity_cost=cap_opp,
                investment_income=inv_income,
                setup_or_exit_cost=setup_yr,
            )
            annual_breakdown.append(bd)
            expected_annual_costs.append(bd.net_cost)

        total_5yr = sum(expected_annual_costs)
        total_5yr_npv = self._npv(expected_annual_costs)

        # ── 4. Simulated 5yr cost distribution ───────────────────────────────
        # Operator's allocated share of pool losses (for reserve dynamics)
        w = op_alloc.allocation_weight
        pooled_annual = sum(correlated_losses)               # (N, T)
        op_share_losses = pooled_annual * w                  # (N, T)

        # Net retained by operator (allocated portion of pool RI)
        net_op, _ = apply_pcc_reinsurance_structure(
            op_share_losses,
            assump.pooled_retention_nok * w,
            assump.pooled_ri_limit_nok * w,
        )

        # 5yr total: fixed costs + reserve shortfalls when losses exceed allocated net budget
        fixed_5yr_costs = (
            op_alloc.allocated_ri_premium_annual * T
            + op_alloc.allocated_admin_annual * T
            + op_alloc.allocated_scr * coc * T
            - op_alloc.allocated_scr * inv_return * T
            + setup_per_member
        )
        # Shortfall = if actual allocated losses exceed expected, reserve makes up the rest
        expected_annual_loss = op_alloc.expected_annual_loss
        sim_net_annual = net_op.mean(axis=1)                 # (N,) mean annual net loss
        reserve_shortfall = np.maximum(
            sim_net_annual * T - expected_annual_loss * T, 0.0
        )
        sim_5yr_costs = fixed_5yr_costs + reserve_shortfall

        cost_std, cost_var_95, cost_var_995 = self._compute_cost_percentiles(sim_5yr_costs)

        # ── 5. Break-even vs full insurance ───────────────────────────────────
        ins = self.operator.current_insurance
        full_ins_annual = [
            ins.annual_premium * ((1 + ins.market_rating_trend) ** (yr - 1))
            for yr in range(1, T + 1)
        ]
        breakeven_yr = self._find_breakeven(expected_annual_costs, full_ins_annual)

        # SCR data for SCRCalculator override
        bel = float(net_op.mean())
        net_var = float(np.percentile(sim_net_annual, 99.5))

        return StrategyResult(
            strategy_name="Pooled PCC Cell",
            annual_breakdown=annual_breakdown,
            total_5yr_cost=total_5yr,
            total_5yr_cost_npv=total_5yr_npv,
            simulated_5yr_costs=sim_5yr_costs,
            expected_annual_costs=expected_annual_costs,
            cost_std=cost_std,
            cost_var_95=cost_var_95,
            cost_var_995=cost_var_995,
            required_capital=op_alloc.allocated_scr,
            breakeven_year=breakeven_yr,
            net_loss_scr_data={
                "bel": bel,
                "scr_gross": net_var,
                "scr_net": op_alloc.allocated_scr,
            },
            assumptions={
                "Pool members": str(assump.n_members),
                "Inter-member correlation": f"{assump.inter_member_correlation:.0%}",
                "CV reduction (diversification)": f"{economics.cv_reduction_pct:.1f}%",
                "Pooled retention": f"NOK {assump.pooled_retention_nok / 1e6:.0f} M",
                "Pooled RI limit": f"NOK {assump.pooled_ri_limit_nok / 1e6:.0f} M",
                "RI loading factor (pool)": f"{assump.pooled_ri_loading_factor:.2f}",
                "Shared admin saving": f"{assump.shared_admin_saving_pct:.0%}",
                "Allocation basis": assump.allocation_basis,
                "RI premium reduction": f"{economics.ri_premium_reduction_pct:.1f}%",
                "SCR reduction": f"{economics.scr_reduction_pct:.1f}%",
            },
        )
