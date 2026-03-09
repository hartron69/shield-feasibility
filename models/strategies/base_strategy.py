"""
Abstract base class for all risk-transfer strategy models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

from data.input_schema import OperatorInput
from models.monte_carlo import SimulationResults
from config.settings import SETTINGS


# ─────────────────────────────────────────────────────────────────────────────
# Shared result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AnnualCostBreakdown:
    """Cost components for a single year of a strategy."""
    year: int
    premium_paid: float           # Net premium to cell / external insurer (excl. fronting)
    retained_losses: float        # Expected losses absorbed by operator (0 for PCC cell)
    admin_costs: float            # Management / admin fees
    capital_opportunity_cost: float  # Opportunity cost of tied capital
    investment_income: float      # Return earned on reserves / cell assets
    setup_or_exit_cost: float     # One-time costs (year 0 = setup, year N = wind-down)
    reinsurance_cost: float = 0.0      # Explicit XL reinsurance premium (captive strategies)
    fronting_fee_paid: float = 0.0     # Fronting insurer fee (% of premium; captive only)

    @property
    def net_cost(self) -> float:
        return (
            self.premium_paid
            + self.retained_losses
            + self.fronting_fee_paid
            + self.reinsurance_cost
            + self.admin_costs
            + self.capital_opportunity_cost
            + self.setup_or_exit_cost
            - self.investment_income
        )


@dataclass
class StrategyResult:
    """Aggregated output for a strategy evaluated over the projection horizon."""
    strategy_name: str

    # Per-year cost breakdown (list of length = projection_years)
    annual_breakdown: List[AnnualCostBreakdown]

    # 5-year NPV total cost of risk (discounted at risk-free rate)
    total_5yr_cost: float
    total_5yr_cost_npv: float

    # Per-simulation 5-year cost paths (shape: n_simulations)
    simulated_5yr_costs: np.ndarray

    # Annual expected costs (list of length = projection_years)
    expected_annual_costs: List[float]

    # Volatility of annual net cost (based on simulation)
    cost_std: float
    cost_var_95: float
    cost_var_995: float

    # Capital requirement for this strategy
    required_capital: float

    # Break-even year vs. full insurance (None if never)
    breakeven_year: Optional[int]

    # Human-readable key assumptions
    assumptions: dict

    # ── Loss decomposition (optional, populated by captive strategies) ─────────
    # Mean annual gross loss across all simulations
    gross_loss_mean: Optional[float] = None
    # Mean annual loss absorbed by captive cell
    captive_loss_mean: Optional[float] = None
    # Mean annual loss ceded to external reinsurers
    reinsured_loss_mean: Optional[float] = None

    # ── Net-loss SCR data (PCC only) ───────────────────────────────────────────
    # When present, SCRCalculator uses these values as authoritative cell SCR inputs
    # computed from the net retained loss distribution (after RI), not the TCOR.
    # Keys: "bel" (E[net loss]), "scr_gross" (net VaR99.5%), "scr_net" (capital SCR).
    net_loss_scr_data: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────────────────────────────────────

class BaseStrategy(ABC):
    """
    All concrete strategies inherit from this class and must implement
    `calculate()`, returning a fully-populated StrategyResult.
    """

    def __init__(self, operator: OperatorInput, sim: SimulationResults):
        self.operator = operator
        self.sim = sim
        self.years = SETTINGS.projection_years
        self.discount_rate = SETTINGS.risk_free_rate
        self.inflation = SETTINGS.inflation_rate

    # ── shared helpers ────────────────────────────────────────────────────────

    def _npv(self, annual_costs: List[float]) -> float:
        """Net-present-value discount a list of annual costs (year 1 = index 0)."""
        total = 0.0
        for t, cost in enumerate(annual_costs, start=1):
            total += cost / ((1 + self.discount_rate) ** t)
        return total

    def _inflation_factor(self, year: int) -> float:
        """Cost inflation multiplier for a given projection year (1-indexed)."""
        return (1 + self.inflation) ** (year - 1)

    def _compute_cost_percentiles(self, costs: np.ndarray):
        return (
            float(costs.std()),
            float(np.percentile(costs, 95)),
            float(np.percentile(costs, 99.5)),
        )

    def _find_breakeven(
        self, own_annual: List[float], baseline_annual: List[float]
    ) -> Optional[int]:
        """Return the first year where cumulative cost < baseline cumulative cost."""
        cum_own = 0.0
        cum_base = 0.0
        for yr, (o, b) in enumerate(zip(own_annual, baseline_annual), start=1):
            cum_own += o
            cum_base += b
            if cum_own < cum_base:
                return yr
        return None

    @abstractmethod
    def calculate(self) -> StrategyResult:
        """Model the strategy and return a StrategyResult."""
        ...
