"""
Strategy 4 – Self-Insurance (No Transfer).

The operator absorbs all losses internally.  A pre-funded reserve is
established and maintained at 1.5× the expected annual loss (configurable).
The reserve earns investment income but its opportunity cost is explicit.

Risk: unlimited upside exposure – catastrophic losses are fully retained.
This strategy serves as a lower-cost floor benchmark and highlights the
tail risk the operator accepts without a transfer mechanism.
"""

from __future__ import annotations

import numpy as np
from typing import List

from models.strategies.base_strategy import BaseStrategy, StrategyResult, AnnualCostBreakdown
from config.settings import SETTINGS


class SelfInsuranceStrategy(BaseStrategy):
    """Full risk retention – internal self-insurance reserve model."""

    def calculate(self) -> StrategyResult:
        ins = self.operator.current_insurance
        base_premium = ins.annual_premium         # Reference only (not paid)
        rp = self.operator.risk_params

        annual_losses = self.sim.annual_losses    # (N, T)
        expected_annual_loss = self.sim.mean_annual_loss

        # ── Reserve requirement ───────────────────────────────────────────────
        # Fund = SETTINGS.self_insurance_reserve_factor × E[annual loss]
        # Minimum = 99th percentile (regulatory / board prudence floor)
        reserve_target = max(
            expected_annual_loss * SETTINGS.self_insurance_reserve_factor,
            self.sim.var_99,
        )

        invest_return = SETTINGS.risk_free_rate
        inv_income_annual = reserve_target * invest_return

        # Admin cost: internal risk management staff + TPA + actuarial
        tiv = self.operator.total_insured_value
        admin_annual = max(
            tiv * SETTINGS.self_insurance_admin_rate,
            80_000,   # floor – basic admin costs
        )

        # ── Simulated 5-year costs ────────────────────────────────────────────
        # Operator pays actual losses + admin each year; earns investment income
        sim_5yr_costs = (
            annual_losses.sum(axis=1)
            + admin_annual * self.years
            - inv_income_annual * self.years
        )   # (N,)

        # ── Expected annual breakdown ─────────────────────────────────────────
        annual_breakdown: List[AnnualCostBreakdown] = []
        expected_annual_costs: List[float] = []

        # Year 1 includes reserve funding (opportunity cost of tying up capital)
        for yr in range(1, self.years + 1):
            infl = self._inflation_factor(yr)
            exp_loss_yr = float(annual_losses[:, yr - 1].mean()) * infl
            admin_yr = admin_annual * infl
            opp_cost = reserve_target * SETTINGS.cost_of_capital_rate  # CoC on reserve

            bd = AnnualCostBreakdown(
                year=yr,
                premium_paid=0.0,
                retained_losses=exp_loss_yr,
                admin_costs=admin_yr,
                capital_opportunity_cost=opp_cost,
                investment_income=inv_income_annual,
                setup_or_exit_cost=0.0,
            )
            annual_breakdown.append(bd)
            expected_annual_costs.append(bd.net_cost)

        total_5yr = sum(expected_annual_costs)
        total_5yr_npv = self._npv(expected_annual_costs)

        cost_std, cost_var_95, cost_var_995 = self._compute_cost_percentiles(sim_5yr_costs)

        # ── Break-even vs. full insurance ─────────────────────────────────────
        full_ins_annual = [
            base_premium * ((1 + ins.market_rating_trend) ** (yr - 1))
            for yr in range(1, self.years + 1)
        ]
        breakeven_yr = self._find_breakeven(expected_annual_costs, full_ins_annual)

        return StrategyResult(
            strategy_name="Self-Insurance",
            annual_breakdown=annual_breakdown,
            total_5yr_cost=total_5yr,
            total_5yr_cost_npv=total_5yr_npv,
            simulated_5yr_costs=sim_5yr_costs,
            expected_annual_costs=expected_annual_costs,
            cost_std=cost_std,
            cost_var_95=cost_var_95,
            cost_var_995=cost_var_995,
            required_capital=reserve_target,
            breakeven_year=breakeven_yr,
            assumptions={
                "Reservefinansieringsmal": f"NOK {reserve_target/1e6:,.1f} M",
                "Reservefaktor": f"{SETTINGS.self_insurance_reserve_factor:.1f}x E[arlig tap]",
                "Investeringsavkastning pa reserve": f"{invest_return:.1%}",
                "Arlig administrasjonsrate (% av TIV)": f"{SETTINGS.self_insurance_admin_rate:.1%}",
                "Arlig administrasjonskostnad": f"NOK {admin_annual/1e6:,.2f} M",
                "Kapitalkostnad (alternativkostnad)": f"{SETTINGS.cost_of_capital_rate:.1%}",
                "ADVARSEL": "Haletap beholdes fullt ut - ingen katastrofebeskyttelse.",
            },
        )
