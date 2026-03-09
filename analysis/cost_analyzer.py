"""
5-Year Total Cost of Risk (TCOR) Analyser.

TCOR components
---------------
    TCOR = Premiums + Retained Losses + Administrative Costs
           + Capital Opportunity Cost − Investment Income
           + Risk Financing Costs (setup / exit)

The analyser computes:
  – Undiscounted TCOR (sticker price view)
  – NPV TCOR (economic view at risk-free discount rate)
  – Annual TCOR trajectory
  – Cost savings of each alternative vs. Full Insurance baseline
  – 5-year cumulative cost curves (for charting)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from data.input_schema import OperatorInput
from models.strategies.base_strategy import StrategyResult
from config.settings import SETTINGS


@dataclass
class CostSummary:
    strategy_name: str
    annual_costs: List[float]
    cumulative_costs: List[float]
    total_5yr_undiscounted: float
    total_5yr_npv: float
    vs_baseline_savings_5yr: float       # $ saving vs. Full Insurance
    vs_baseline_savings_pct: float       # % saving vs. Full Insurance
    cost_per_dollar_tiv: float           # TCOR / TIV – efficiency metric
    cost_as_pct_revenue: float           # TCOR / Annual Revenue
    best_year: int                       # Year with lowest net cost
    worst_year: int                      # Year with highest net cost


@dataclass
class CostAnalysis:
    summaries: Dict[str, CostSummary]
    baseline_name: str
    cheapest_strategy: str
    safest_strategy: str                 # Lowest 99.5% VaR
    best_risk_adjusted: str             # Lowest CVaR / cost trade-off


class CostAnalyzer:
    """Compute and compare 5-year TCOR across all strategies."""

    def __init__(self, operator: OperatorInput, strategy_results: Dict[str, StrategyResult]):
        self.operator = operator
        self.strategy_results = strategy_results
        self.baseline = "Full Insurance"

    def analyze(self) -> CostAnalysis:
        baseline_result = self.strategy_results[self.baseline]
        baseline_5yr = baseline_result.total_5yr_cost

        tiv = self.operator.total_insured_value
        revenue = self.operator.total_annual_revenue

        summaries: Dict[str, CostSummary] = {}
        for name, result in self.strategy_results.items():
            cumulative: List[float] = []
            running = 0.0
            for c in result.expected_annual_costs:
                running += c
                cumulative.append(running)

            savings = baseline_5yr - result.total_5yr_cost
            savings_pct = savings / max(baseline_5yr, 1)

            best_yr = int(
                min(range(len(result.expected_annual_costs)),
                    key=lambda i: result.expected_annual_costs[i])
            ) + 1
            worst_yr = int(
                max(range(len(result.expected_annual_costs)),
                    key=lambda i: result.expected_annual_costs[i])
            ) + 1

            summaries[name] = CostSummary(
                strategy_name=name,
                annual_costs=result.expected_annual_costs,
                cumulative_costs=cumulative,
                total_5yr_undiscounted=result.total_5yr_cost,
                total_5yr_npv=result.total_5yr_cost_npv,
                vs_baseline_savings_5yr=savings,
                vs_baseline_savings_pct=savings_pct,
                cost_per_dollar_tiv=result.total_5yr_cost / max(tiv, 1),
                cost_as_pct_revenue=result.total_5yr_cost / max(revenue * 5, 1),
                best_year=best_yr,
                worst_year=worst_yr,
            )

        cheapest = min(summaries, key=lambda n: summaries[n].total_5yr_undiscounted)

        # Safest = lowest simulated 99.5% VaR cost
        safest = min(
            self.strategy_results,
            key=lambda n: self.strategy_results[n].cost_var_995,
        )

        # Best risk-adjusted = lowest coefficient of variation of 5-yr cost
        def _cv(name: str) -> float:
            r = self.strategy_results[name]
            return r.cost_std / max(r.total_5yr_cost / 5, 1)

        best_risk_adj = min(self.strategy_results, key=_cv)

        return CostAnalysis(
            summaries=summaries,
            baseline_name=self.baseline,
            cheapest_strategy=cheapest,
            safest_strategy=safest,
            best_risk_adjusted=best_risk_adj,
        )
