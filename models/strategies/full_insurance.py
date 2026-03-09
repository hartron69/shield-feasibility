"""
Strategy 1 – Full Market Insurance.

The operator transfers virtually all risk to external insurers.
Retained cost = annual premium + expected deductible losses + admin.
Premium escalates at market_rating_trend each year.
"""

from __future__ import annotations

import numpy as np
from typing import List

from models.strategies.base_strategy import BaseStrategy, StrategyResult, AnnualCostBreakdown
from config.settings import SETTINGS


class FullInsuranceStrategy(BaseStrategy):
    """Full external market insurance – baseline comparator strategy."""

    def calculate(self) -> StrategyResult:
        ins = self.operator.current_insurance
        base_premium = ins.annual_premium
        deductible = ins.per_occurrence_deductible
        rating_trend = ins.market_rating_trend  # annual premium escalation

        # ── Expected retained (deductible) losses per year ────────────────────
        # E[min(X, d)] where X ~ loss severity, d = deductible per occurrence
        # Approximated as: E[events] * E[min(severity, d)]
        rp = self.operator.risk_params
        # For LogNormal X, E[min(X,d)] ≈ mu_ln * Phi(z_d) + d * (1 - Phi(z_d))
        # Using empirical deductible burn from simulation
        annual_losses = self.sim.annual_losses   # (N, T)
        n_events = self.sim.event_counts          # (N, T)

        # Retained = sum of min(event_loss, deductible) per year (simulation approximation)
        # We proxy: each year, expected deductible burn = min(agg_loss, agg_deductible)
        # using per-occurrence cap = deductible, aggregate cap = annual aggregate deductible
        agg_ded = ins.annual_aggregate_deductible

        # Per-simulation retained costs (capped at agg deductible per year)
        retained_per_sim = np.minimum(annual_losses, agg_ded)  # (N, T)
        expected_retained = retained_per_sim.mean(axis=0)      # (T,)

        # ── Annual cost breakdown ─────────────────────────────────────────────
        annual_breakdown: List[AnnualCostBreakdown] = []
        expected_annual_costs: List[float] = []

        for yr in range(1, self.years + 1):
            # Premium escalates with market trend + inflation
            premium = base_premium * ((1 + rating_trend) ** (yr - 1))
            retained = expected_retained[yr - 1] * self._inflation_factor(yr)
            admin = base_premium * 0.008 * self._inflation_factor(yr)  # ~0.8% admin

            bd = AnnualCostBreakdown(
                year=yr,
                premium_paid=premium,
                retained_losses=retained,
                admin_costs=admin,
                capital_opportunity_cost=0.0,   # no capital tied
                investment_income=0.0,
                setup_or_exit_cost=0.0,
            )
            annual_breakdown.append(bd)
            expected_annual_costs.append(bd.net_cost)

        total_5yr = sum(expected_annual_costs)
        total_5yr_npv = self._npv(expected_annual_costs)

        # ── Simulated 5-year cost distribution ───────────────────────────────
        # For full insurance: variability comes only from retained deductible
        sim_annual_premium = np.array([
            base_premium * (1 + rating_trend) ** (yr - 1)
            for yr in range(1, self.years + 1)
        ])  # (T,)
        # Simulated retained per year, per path
        sim_retained = np.minimum(annual_losses, agg_ded)      # (N, T)
        sim_5yr_costs = (sim_annual_premium + sim_retained).sum(axis=1)   # (N,)

        cost_std, cost_var_95, cost_var_995 = self._compute_cost_percentiles(sim_5yr_costs)

        return StrategyResult(
            strategy_name="Full Insurance",
            annual_breakdown=annual_breakdown,
            total_5yr_cost=total_5yr,
            total_5yr_cost_npv=total_5yr_npv,
            simulated_5yr_costs=sim_5yr_costs,
            expected_annual_costs=expected_annual_costs,
            cost_std=cost_std,
            cost_var_95=cost_var_95,
            cost_var_995=cost_var_995,
            required_capital=0.0,    # no capital requirement for fully insured
            breakeven_year=None,     # this is the baseline
            assumptions={
                "Arlig basispremie": f"NOK {base_premium/1e6:,.1f} M",
                "Premietrend (p.a.)": f"{rating_trend:.1%}",
                "Egenandel per skade": f"NOK {deductible/1e6:,.1f} M",
                "Arlig maksegenandel": f"NOK {agg_ded/1e6:,.1f} M",
                "Dekningsgrense": f"NOK {ins.coverage_limit/1e6:,.1f} M",
                "Administrasjonskostnad": "0,8 % av basispremie",
            },
        )
