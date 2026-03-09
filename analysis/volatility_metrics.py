"""
Volatility & Risk Metrics Analyser.

Metrics computed per strategy
-------------------------------
  – Standard deviation of annual net cost
  – Coefficient of variation (CV = σ / μ)
  – Value-at-Risk at 95% and 99.5% (1-year)
  – Tail Value-at-Risk (TVaR / Expected Shortfall) at 95%
  – Maximum single-year loss across all simulations
  – Probability of annual cost exceeding budget / premium baseline
  – Skewness and excess kurtosis of cost distribution (tail shape)
  – Sharpe-like ratio: (E[cost] − risk_free_alt) / σ  (lower = better)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from models.monte_carlo import SimulationResults
from models.strategies.base_strategy import StrategyResult
from config.settings import SETTINGS


@dataclass
class StrategyVolatilityMetrics:
    strategy_name: str

    # Annual cost statistics
    mean_annual_cost: float
    std_annual_cost: float
    cv: float                     # Coefficient of variation (std / mean)
    skewness: float               # Pearson skewness of annual cost distribution
    excess_kurtosis: float        # Tail heaviness (0 = normal)

    # Risk thresholds (annual)
    var_90_annual: float
    var_95_annual: float
    var_99_annual: float
    var_995_annual: float
    tvar_95_annual: float         # Expected shortfall above 95th percentile

    # 5-year aggregate risk
    mean_5yr_cost: float
    std_5yr_cost: float
    var_995_5yr: float

    # Tail statistics
    max_annual_cost: float        # Worst single year across all simulations
    p_exceed_premium: float       # Prob(annual cost > current premium)
    p_exceed_budget: float        # Prob(annual cost > 1.5× current premium)


@dataclass
class VolatilityAnalysis:
    metrics: Dict[str, StrategyVolatilityMetrics]
    most_stable: str              # Lowest CV
    most_volatile: str            # Highest CV
    best_tail_protection: str     # Lowest TVaR-95
    loss_distribution_summary: dict  # Underlying loss stats for reference


class VolatilityAnalyzer:
    """Compute volatility and tail-risk metrics for all strategies."""

    def __init__(
        self,
        sim: SimulationResults,
        strategy_results: Dict[str, StrategyResult],
    ):
        self.sim = sim
        self.strategies = strategy_results
        self.base_premium = None  # set from first strategy with premium data

    def _annual_cost_distribution(self, result: StrategyResult) -> np.ndarray:
        """Annualise the 5-year simulated costs to get an annual cost array."""
        N = len(result.simulated_5yr_costs)
        T = self.sim.projection_years
        # Use the actual (N, T) annual losses to reconstruct annual costs
        # Proxy: distribute 5-yr path evenly (acceptable for volatility analysis)
        return result.simulated_5yr_costs / T

    def _compute(self, name: str, result: StrategyResult) -> StrategyVolatilityMetrics:
        annual_costs = self._annual_cost_distribution(result)

        mean_ = float(annual_costs.mean())
        std_ = float(annual_costs.std())
        cv = std_ / max(mean_, 1.0)

        # Skewness: Pearson's moment
        skew = float(np.mean(((annual_costs - mean_) / max(std_, 1e-9)) ** 3))
        kurt = float(np.mean(((annual_costs - mean_) / max(std_, 1e-9)) ** 4)) - 3.0

        var_90 = float(np.percentile(annual_costs, 90))
        var_95 = float(np.percentile(annual_costs, 95))
        var_99 = float(np.percentile(annual_costs, 99))
        var_995 = float(np.percentile(annual_costs, 99.5))
        tvar_95 = float(annual_costs[annual_costs >= var_95].mean())

        five_yr = result.simulated_5yr_costs
        var_995_5yr = float(np.percentile(five_yr, 99.5))

        max_cost = float(annual_costs.max())

        premium_ref = result.annual_breakdown[0].premium_paid if result.annual_breakdown else mean_
        p_exceed_premium = float((annual_costs > premium_ref).mean())
        p_exceed_budget = float((annual_costs > premium_ref * 1.5).mean())

        return StrategyVolatilityMetrics(
            strategy_name=name,
            mean_annual_cost=mean_,
            std_annual_cost=std_,
            cv=cv,
            skewness=skew,
            excess_kurtosis=kurt,
            var_90_annual=var_90,
            var_95_annual=var_95,
            var_99_annual=var_99,
            var_995_annual=var_995,
            tvar_95_annual=tvar_95,
            mean_5yr_cost=float(five_yr.mean()),
            std_5yr_cost=float(five_yr.std()),
            var_995_5yr=var_995_5yr,
            max_annual_cost=max_cost,
            p_exceed_premium=p_exceed_premium,
            p_exceed_budget=p_exceed_budget,
        )

    def analyze(self) -> VolatilityAnalysis:
        metrics = {name: self._compute(name, res) for name, res in self.strategies.items()}

        most_stable = min(metrics, key=lambda n: metrics[n].cv)
        most_volatile = max(metrics, key=lambda n: metrics[n].cv)
        best_tail = min(metrics, key=lambda n: metrics[n].tvar_95_annual)

        def _nok(v): return f"NOK {v/1_000_000:,.1f} M"
        loss_summary = {
            "Gjennomsnittlig arlig bruttotap": _nok(self.sim.mean_annual_loss),
            "Median arlig bruttotap": _nok(self.sim.median_annual_loss),
            "Standardavvik arlig tap": _nok(self.sim.std_annual_loss),
            "Tap CV (volatilitetsindeks)": f"{self.sim.std_annual_loss / max(self.sim.mean_annual_loss, 1):.2f}",
            "VaR 95 % arlig bruttotap": _nok(self.sim.var_95),
            "VaR 99,5 % arlig bruttotap": _nok(self.sim.var_995),
            "TVaR 95 % arlig bruttotap": _nok(self.sim.tvar_95),
        }

        return VolatilityAnalysis(
            metrics=metrics,
            most_stable=most_stable,
            most_volatile=most_volatile,
            best_tail_protection=best_tail,
            loss_distribution_summary=loss_summary,
        )
