"""
Strategy 2 – Hybrid (Large Deductible / Working-Layer Retention).

The operator takes a materially higher deductible / retention layer and
purchases excess-of-loss cover for losses above the retention point.
The insurer provides a premium credit reflecting the transferred frequency risk.

Structure
---------
    Retention  : R  (25% of expected annual aggregate loss by default)
    Excess     : XS cover from R xs R up to the original coverage limit
    External premium : reduced by hybrid_premium_discount × (retained % of risk)
    Retained losses  : actual losses up to R per year (simulation-driven)
"""

from __future__ import annotations

import numpy as np
from typing import List

from models.strategies.base_strategy import BaseStrategy, StrategyResult, AnnualCostBreakdown
from config.settings import SETTINGS


class HybridStrategy(BaseStrategy):
    """Large-deductible / working-layer retention hybrid programme."""

    def calculate(self) -> StrategyResult:
        ins = self.operator.current_insurance
        base_premium = ins.annual_premium
        rating_trend = ins.market_rating_trend

        # ── Retention layer ────────────────────────────────────────────────────
        expected_annual_loss = self.sim.mean_annual_loss
        retention = max(
            expected_annual_loss * SETTINGS.hybrid_retention_pct,
            ins.per_occurrence_deductible,   # floor at existing deductible
        )

        # Premium on retained layer not charged externally → direct discount
        discount = SETTINGS.hybrid_premium_discount
        reduced_premium_rate = 1.0 - (SETTINGS.hybrid_retention_pct * discount)

        annual_losses = self.sim.annual_losses   # (N, T)

        # ── Retained losses per simulation path ───────────────────────────────
        # Each year: operator pays min(annual_loss, retention)
        # Above retention: covered by XS policy (paid in external premium)
        retained_sim = np.minimum(annual_losses, retention)       # (N, T)
        expected_retained = retained_sim.mean(axis=0)             # (T,)

        # ── Annual cost breakdown ─────────────────────────────────────────────
        annual_breakdown: List[AnnualCostBreakdown] = []
        expected_annual_costs: List[float] = []

        for yr in range(1, self.years + 1):
            xs_premium = (
                base_premium
                * reduced_premium_rate
                * ((1 + rating_trend) ** (yr - 1))
                * self._inflation_factor(yr)
            )
            retained = expected_retained[yr - 1] * self._inflation_factor(yr)
            admin = (base_premium * 0.015) * self._inflation_factor(yr)  # slightly higher admin

            bd = AnnualCostBreakdown(
                year=yr,
                premium_paid=xs_premium,
                retained_losses=retained,
                admin_costs=admin,
                capital_opportunity_cost=0.0,
                investment_income=0.0,
                setup_or_exit_cost=0.0,
            )
            annual_breakdown.append(bd)
            expected_annual_costs.append(bd.net_cost)

        total_5yr = sum(expected_annual_costs)
        total_5yr_npv = self._npv(expected_annual_costs)

        # ── Simulated distribution ────────────────────────────────────────────
        xs_premiums_arr = np.array([
            base_premium * reduced_premium_rate * ((1 + rating_trend) ** (yr - 1))
            for yr in range(1, self.years + 1)
        ])  # (T,)
        sim_5yr_costs = (xs_premiums_arr + retained_sim).sum(axis=1)   # (N,)

        cost_std, cost_var_95, cost_var_995 = self._compute_cost_percentiles(sim_5yr_costs)

        # ── Baseline for break-even (cost must be vs. full insurance) ──────────
        full_ins_annual = [
            base_premium * ((1 + rating_trend) ** (yr - 1))
            for yr in range(1, self.years + 1)
        ]
        breakeven_yr = self._find_breakeven(expected_annual_costs, full_ins_annual)

        return StrategyResult(
            strategy_name="Hybrid",
            annual_breakdown=annual_breakdown,
            total_5yr_cost=total_5yr,
            total_5yr_cost_npv=total_5yr_npv,
            simulated_5yr_costs=sim_5yr_costs,
            expected_annual_costs=expected_annual_costs,
            cost_std=cost_std,
            cost_var_95=cost_var_95,
            cost_var_995=cost_var_995,
            required_capital=retention * 1.5,   # Working capital buffer
            breakeven_year=breakeven_yr,
            assumptions={
                "Egenbehold (lag)": f"NOK {retention/1e6:,.1f} M",
                "Premierabatt pa beholdt risiko": f"{discount:.0%}",
                "Effektiv XS-premiemultiplikator": f"{reduced_premium_rate:.2f}x",
                "Premietrend (p.a.)": f"{rating_trend:.1%}",
                "Administrasjonskostnad": "1,5 % av basispremie",
                "Egenbeholdsgrunnlag": "Arlig aggregat",
            },
        )
