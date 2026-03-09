"""
Strategy 3 – Protected Cell Company (PCC) Captive Cell.

Economics
---------
Year 0 (setup)
  – Formation cost (legal, actuarial, regulatory filing)
  – Initial capital contribution (= net SCR after reinsurance at 99.5% VaR)

Years 1–5 (operating)
  – Annual cell management fee (rent + governance)
  – Fronting insurer fee (% of premium written through fronter)
  – Reduced external reinsurance premium (savings vs. market)
  – Annual-aggregate XL reinsurance premium (explicit cost)
  – Net losses paid by cell (gross losses minus RI recovery)
  – Investment income earned on cell reserves
  – Replenishment premium to the cell where reserve is depleted

Year 5 (exit / continuation)
  – Released capital returned to operator (if solvency maintained)

Net benefit materialises through:
  1. Premium savings (below-market cost once expenses loaded)
  2. RI structure caps tail losses; cell capital based on net (not gross) VaR
  3. Investment income on reserve capital
  4. Profit commission / reserve release if loss experience favourable

Key calibration changes (Sprint 8)
-----------------------------------
  * Losses are split using annual-aggregate XL: cell retains up to
    `assumptions.retention_nok`; RI covers excess up to `reinsurance_limit_nok`.
  * Cell SCR is computed on the *net retained* loss distribution, not gross VaR.
    This correctly reflects that RI transfers tail risk, reducing required capital.
  * RI premium appears as an explicit cost line (reinsurance_cost in breakdown).
  * `retained_losses` in AnnualCostBreakdown is set to 0 because expected losses
    are paid from the cell reserve (funded by premium), not from operator cash flow.
    Only unexpected shortfalls (reserve depletion) are additional operator costs,
    and those are captured in the simulation distribution.
"""

from __future__ import annotations

import numpy as np
from typing import List, Optional

from models.strategies.base_strategy import BaseStrategy, StrategyResult, AnnualCostBreakdown
from models.captive_structure import CaptiveStructure, RetentionLayer, ReinsuranceLayer
from models.pcc_economics import (
    PCCAssumptions,
    apply_pcc_reinsurance_structure,
    compute_net_var,
    compute_ri_premium,
    calibrate_market_premium,
)
from config.settings import SETTINGS


class PCCCaptiveStrategy(BaseStrategy):
    """Protected Cell Company captive cell risk-transfer structure."""

    def __init__(self, operator, sim, pcc_assumptions: Optional[PCCAssumptions] = None):
        super().__init__(operator, sim)
        self.pcc_assumptions = pcc_assumptions or PCCAssumptions.base()

    def calculate(self) -> StrategyResult:
        assump = self.pcc_assumptions
        ins = self.operator.current_insurance

        # ── Premium basis ─────────────────────────────────────────────────────
        # Optionally calibrate to a market benchmark derived from actuarial loss ratio
        if assump.use_market_premium_calibration:
            base_premium = calibrate_market_premium(
                self.sim.mean_annual_loss, assump.target_market_loss_ratio
            )
        else:
            base_premium = ins.annual_premium

        rating_trend = ins.market_rating_trend
        annual_losses = self.sim.annual_losses          # (N, T)
        expected_annual_loss = self.sim.mean_annual_loss

        # ── Reinsurance structure ─────────────────────────────────────────────
        # Split gross losses into net retained (cell) + RI recovery
        net_retained, ri_recovery = apply_pcc_reinsurance_structure(
            annual_losses,
            assump.retention_nok,
            assump.reinsurance_limit_nok,
        )  # both (N, T)

        # RI premium: burning-cost estimate from simulation × loading factor
        ri_premium_annual = compute_ri_premium(annual_losses, assump)

        # ── Cell capital requirement (SCR on NET retained losses) ─────────────
        # Using net retained loss distribution, not gross VaR, because RI
        # covers the tail above retention — that risk lives with the reinsurer.
        net_var_995 = compute_net_var(net_retained, confidence=assump.scr_confidence)
        exp_net_loss = float(net_retained.mean())
        tp = exp_net_loss * (1 + assump.tp_load)
        cell_scr_net = max(0.0, net_var_995 - tp)
        initial_capital = cell_scr_net + tp        # total assets held in cell

        # ── Premium structure ─────────────────────────────────────────────────
        premium_to_cell = base_premium * (1 - assump.premium_discount_pct)
        fronting_fee_base = premium_to_cell * assump.fronting_fee_pct
        setup_cost = assump.formation_cost_nok
        annual_cell_fee = assump.admin_fee_nok
        invest_return = assump.investment_return_pct

        # ── Captive structure for loss decomposition (reporting only) ─────────
        per_occ_deductible = ins.per_occurrence_deductible
        coverage_limit = ins.coverage_limit
        captive_structure = CaptiveStructure(
            operator_name=self.operator.name,
            retention=RetentionLayer(
                name="Per-Occurrence Deductible",
                per_occurrence_retention=per_occ_deductible,
                annual_aggregate_retention=ins.annual_aggregate_deductible,
            ),
            captive_layer=ReinsuranceLayer(
                name="PCC Captive Cell Layer",
                attachment_point=per_occ_deductible,
                limit=coverage_limit - per_occ_deductible,
                participation_pct=100.0,
                estimated_premium=premium_to_cell,
            ),
        )
        gross_losses = annual_losses
        captive_losses = captive_structure.compute_captive_loss(gross_losses)
        reinsured_losses = captive_structure.compute_reinsured_loss(gross_losses)
        gross_loss_mean = float(gross_losses.mean())
        captive_loss_mean = float(captive_losses.mean())
        reinsured_loss_mean = float(reinsured_losses.mean())

        # ── Per-simulation annual costs ───────────────────────────────────────
        # Reserve absorbs net losses (after RI recovery).
        # RI premium is paid each year before claims.
        # Shortfall occurs only when reserve is fully depleted.
        N, T = annual_losses.shape
        reserve = np.full(N, initial_capital, dtype=float)
        sim_annual_net: List[np.ndarray] = []

        for yr in range(T):
            infl = self._inflation_factor(yr + 1)
            premium_yr = premium_to_cell * ((1 + rating_trend) ** yr)
            fee_yr = annual_cell_fee * infl
            fronting_yr = fronting_fee_base * ((1 + rating_trend) ** yr)
            ri_yr = ri_premium_annual * infl

            # Investment income on reserve balance (start of year)
            inv_income = reserve * invest_return

            # Net losses paid by cell (after RI recovery)
            net_cell_losses = net_retained[:, yr]   # (N,)

            # Update reserve: + premium + inv_income – net_losses – fees – RI premium
            reserve = reserve + premium_yr + inv_income - net_cell_losses - fee_yr - ri_yr
            # Shortfall: operator must top up depleted reserve
            shortfall = np.maximum(-reserve, 0.0)
            reserve = np.maximum(reserve, 0.0)

            # Annual operator cash cost: premium + fronting + cell fee + RI + shortfall – inv_income
            annual_cost_sim = premium_yr + fronting_yr + fee_yr + ri_yr + shortfall - inv_income
            sim_annual_net.append(annual_cost_sim)

        sim_annual_matrix = np.stack(sim_annual_net, axis=1)            # (N, T)
        sim_5yr_costs = sim_annual_matrix.sum(axis=1) + setup_cost      # (N,)

        # ── Expected annual breakdown ─────────────────────────────────────────
        # retained_losses = 0: expected losses are paid from the cell reserve
        # (funded by premium), not from operator cash.  Only unexpected shortfalls
        # add to operator costs, and those are captured in the simulation distribution.
        annual_breakdown: List[AnnualCostBreakdown] = []
        expected_annual_costs: List[float] = []

        running_reserve = initial_capital
        for yr in range(1, self.years + 1):
            infl = self._inflation_factor(yr)
            premium_yr = premium_to_cell * ((1 + rating_trend) ** (yr - 1))
            fee_yr = annual_cell_fee * infl
            fronting_yr = fronting_fee_base * ((1 + rating_trend) ** (yr - 1))
            ri_yr = ri_premium_annual * infl
            inv_income_yr = running_reserve * invest_return

            # Expected net losses from simulation (mean of net retained, this year)
            exp_net_loss_yr = float(net_retained[:, yr - 1].mean())

            # Update expected reserve
            running_reserve += (
                premium_yr + inv_income_yr - exp_net_loss_yr - fee_yr - ri_yr
            )
            running_reserve = max(running_reserve, 0.0)

            setup_this_yr = setup_cost if yr == 1 else 0.0

            bd = AnnualCostBreakdown(
                year=yr,
                premium_paid=premium_yr,        # net premium to cell only
                fronting_fee_paid=fronting_yr,  # fronting insurer fee (transparent)
                retained_losses=0.0,            # losses paid from reserve, not cash flow
                reinsurance_cost=ri_yr,
                admin_costs=fee_yr,
                capital_opportunity_cost=initial_capital * SETTINGS.cost_of_capital_rate,
                investment_income=inv_income_yr,
                setup_or_exit_cost=setup_this_yr,
            )
            annual_breakdown.append(bd)
            expected_annual_costs.append(bd.net_cost)

        total_5yr = sum(expected_annual_costs)
        total_5yr_npv = self._npv(expected_annual_costs)

        cost_std, cost_var_95, cost_var_995 = self._compute_cost_percentiles(sim_5yr_costs)

        # ── Break-even vs. full insurance ─────────────────────────────────────
        full_ins_annual = [
            base_premium * ((1 + rating_trend) ** (yr - 1))
            for yr in range(1, self.years + 1)
        ]
        breakeven_yr = self._find_breakeven(expected_annual_costs, full_ins_annual)

        return StrategyResult(
            strategy_name="PCC Captive Cell",
            annual_breakdown=annual_breakdown,
            total_5yr_cost=total_5yr,
            total_5yr_cost_npv=total_5yr_npv,
            simulated_5yr_costs=sim_5yr_costs,
            expected_annual_costs=expected_annual_costs,
            cost_std=cost_std,
            cost_var_95=cost_var_95,
            cost_var_995=cost_var_995,
            required_capital=cell_scr_net,
            breakeven_year=breakeven_yr,
            gross_loss_mean=gross_loss_mean,
            captive_loss_mean=captive_loss_mean,
            reinsured_loss_mean=reinsured_loss_mean,
            # Net-loss SCR data for reconciliation in SCRCalculator.
            # These values are based on the net retained loss distribution (after RI),
            # not the simulated TCOR distribution, and represent the authoritative
            # SCR inputs for the cell's regulatory capital calculation.
            net_loss_scr_data={
                "bel": exp_net_loss,         # E[net retained annual loss]
                "scr_gross": net_var_995,    # VaR(99.5%) of net retained losses
                "scr_net": cell_scr_net,     # max(0, scr_gross - TP)
            },
            assumptions={
                "Etableringskostand (celle)": f"NOK {setup_cost/1e6:,.2f} M",
                "Arlig celleforvaltningsavgift": f"NOK {annual_cell_fee/1e6:,.2f} M",
                "Premierabatt vs. marked": f"{assump.premium_discount_pct:.0%}",
                "Frontingavgift": f"{assump.fronting_fee_pct:.1%}",
                "Investeringsavkastning pa reserver": f"{invest_return:.1%}",
                "Tilbakeholdt tap (XL-grense)": f"NOK {assump.retention_nok/1e6:,.0f} M",
                "GjenForsikringsgrense": f"NOK {assump.reinsurance_limit_nok/1e6:,.0f} M",
                "Arlig gjenforsikringspremie": f"NOK {ri_premium_annual/1e6:,.2f} M",
                "Nodvendig startkapital (netto)": f"NOK {initial_capital/1e6:,.1f} M",
                "SCR netto (99,5 % VaR)": f"NOK {cell_scr_net/1e6:,.1f} M",
                "Tekniske avsetninger": f"NOK {tp/1e6:,.1f} M",
                "Foretrukket domisil": self.operator.captive_domicile_preference or "Ikke angitt",
            },
        )
