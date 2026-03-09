"""
Solvency Capital Requirement (SCR) Calculator.

Methodology: simplified Solvency II framework, applicable to captive cells
and internal self-insurance reserves.

    SCR = max(0,  VaR(99.5%, 1-year net loss)  −  Technical Provisions)

Technical Provisions = Best Estimate Liability + Risk Margin

    BEL = E[net annual loss]  (undiscounted)
    Risk Margin = CoC_rate × SCR × annuity_factor   (iterated approximation)
    Technical Provisions = BEL × (1 + prudence_load)

For fully-insured strategies: SCR ≈ 0 (counterparty risk module only,
treated as immaterial for this tool).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np

from models.monte_carlo import SimulationResults
from models.strategies.base_strategy import StrategyResult
from config.settings import SETTINGS


@dataclass
class SCRResult:
    strategy_name: str
    best_estimate_liability: float    # E[net annual loss]
    technical_provisions: float       # BEL + Risk Margin
    risk_margin: float
    scr_gross: float                  # 99.5% VaR of net loss
    scr_net: float                    # SCR after deducting TPs (capital to hold)
    capital_ratio: float              # SCR / Annual Revenue
    solvency_ratio: float             # Required capital / SCR (target ≥ 100%)
    required_capital: float           # = SCR_net (the capital the operator must provide)
    interpretation: str


class SCRCalculator:
    """
    Calculates SCR for each strategy and returns structured results.
    """

    def __init__(
        self,
        sim: SimulationResults,
        strategy_results: Dict[str, StrategyResult],
    ):
        self.sim = sim
        self.strategy_results = strategy_results
        self.coc = SETTINGS.cost_of_capital_rate
        self.tp_load = SETTINGS.technical_provision_load
        self.discount_rate = SETTINGS.risk_free_rate

    def _risk_margin(self, scr: float) -> float:
        """Simplified risk margin using Cost-of-Capital method (T=5 years)."""
        # RM = CoC × SCR × Σ(1/(1+r)^t) for t=1..T
        annuity = sum(1.0 / (1 + self.discount_rate) ** t for t in range(1, 6))
        return self.coc * scr * annuity / (1 + self.coc)   # 1-step approximation

    def _calculate_for_strategy(self, name: str, result: StrategyResult) -> SCRResult:
        """Derive SCR components for a single strategy."""

        # ── Base computation from simulated TCOR distribution ─────────────────
        # Used for all strategies; may be overridden below for PCC.
        net_costs = result.simulated_5yr_costs / self.sim.projection_years  # annualised
        bel = float(net_costs.mean())
        var_995 = float(np.percentile(net_costs, 99.5))

        tp_total = bel * (1 + self.tp_load)
        rm = self._risk_margin(max(0.0, var_995 - tp_total))
        tp_with_rm = tp_total + rm
        scr_gross = var_995
        scr_net = max(0.0, scr_gross - tp_with_rm)

        # For full insurance: only counterparty risk module (~5% haircut)
        if name == "Full Insurance":
            scr_net = max(0.0, scr_net * 0.05)

        # ── PCC override: use net retained loss SCR from PCCCaptiveStrategy ───
        # The TCOR distribution (above) mixes fixed costs with loss volatility,
        # giving a misleading SCR.  PCCCaptiveStrategy computes SCR correctly
        # from the *net retained loss* distribution (losses capped at RI retention).
        # We override BEL, SCR gross, and SCR net with those authoritative values,
        # so every report section shows a consistent, economically correct number.
        if result.net_loss_scr_data is not None:
            d = result.net_loss_scr_data
            bel = d["bel"]
            scr_gross = d["scr_gross"]
            scr_net = d["scr_net"]
            # Recompute TP/RM using net-loss BEL for consistency
            tp_total = bel * (1 + self.tp_load)
            rm = self._risk_margin(max(0.0, scr_gross - tp_total))
            tp_with_rm = tp_total + rm

        annual_revenue = self.sim.mean_annual_loss  # proxy for exposure base
        capital_ratio = scr_net / max(annual_revenue, 1)

        # Solvency ratio: operator-provided capital vs. SCR requirement
        provided_capital = result.required_capital
        solvency_ratio = provided_capital / max(scr_net, 1)

        # Interpretation
        if scr_net <= 0:
            interp = "No regulatory capital required; risk fully transferred."
        elif solvency_ratio >= 1.5:
            interp = "Well-capitalised. Surplus capital may be optimised."
        elif solvency_ratio >= 1.0:
            interp = "Adequately capitalised at 100% SCR coverage."
        elif solvency_ratio >= 0.75:
            interp = "Under-capitalised. Top-up required before inception."
        else:
            interp = "Materially under-capitalised. Strategy not viable as modelled."

        return SCRResult(
            strategy_name=name,
            best_estimate_liability=bel,
            technical_provisions=tp_with_rm,
            risk_margin=rm,
            scr_gross=scr_gross,
            scr_net=scr_net,
            capital_ratio=capital_ratio,
            solvency_ratio=solvency_ratio,
            required_capital=provided_capital,
            interpretation=interp,
        )

    def calculate_all(self) -> Dict[str, SCRResult]:
        return {
            name: self._calculate_for_strategy(name, result)
            for name, result in self.strategy_results.items()
        }
