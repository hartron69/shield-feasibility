"""
Shield Captive Risk Platform – Platform Report Data Model.

Defines the structured data objects that represent a full platform assessment
report.  These objects are populated by the analysis pipeline and consumed
by the PDF generator and any future API/JSON export layer.

All monetary values are in NOK unless explicitly stated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Executive summary
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExecutiveSummary:
    """
    One-page executive summary for board / investor consumption.

    Attributes
    ----------
    operator_name : str
    assessment_date : str
        ISO-8601 date string.
    verdict : str
        Suitability verdict (e.g. "POTENTIALLY SUITABLE").
    composite_score : float
        0–100 composite suitability score.
    recommended_structure : str
        Short label for the recommended insurance structure.
    expected_5yr_savings : float
        Expected 5-year savings vs. full market insurance (NOK).
    scr_requirement : float
        Estimated Solvency Capital Requirement for captive cell (NOK).
    top_3_risks : List[str]
        Three highest-impact risk sub-types identified.
    key_actions : List[str]
        Three to five priority actions.
    platform_disclaimer : str
        Standard disclaimer text.
    """
    operator_name: str
    assessment_date: str
    verdict: str
    composite_score: float
    recommended_structure: str
    expected_5yr_savings: float
    scr_requirement: float
    top_3_risks: List[str]
    key_actions: List[str]
    platform_disclaimer: str = (
        "Dette er en risikomotorrapport produsert av Shield Captive Risk Platform. "
        "Rapporten er ikke et varslingssystem og erstatter ikke profesjonell "
        "aktuarfaglig eller forsikringsmeglerrådgivning. Alle anslag er basert "
        "på Monte Carlo-simulering og statistiske modeller med iboende usikkerhet."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Risk metrics summary
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskMetricsSummary:
    """
    Key risk statistics from the Monte Carlo simulation.

    Attributes
    ----------
    mean_annual_loss : float
    var_95 : float
    var_995 : float
    tvar_95 : float
    loss_by_domain : Dict[str, float]
        Expected annual loss broken down by domain name (NOK).
    c5ai_enriched : bool
        Whether C5AI+ dynamic biological risk estimates were used.
    data_quality : str
        Overall data quality flag: "SUFFICIENT" | "LIMITED" | "POOR" | "PRIOR_ONLY".
    """
    mean_annual_loss: float
    var_95: float
    var_995: float
    tvar_95: float
    loss_by_domain: Dict[str, float] = field(default_factory=dict)
    c5ai_enriched: bool = False
    data_quality: str = "PRIOR_ONLY"


# ─────────────────────────────────────────────────────────────────────────────
# Insurance structure comparison
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StrategyComparison:
    """Summary of one strategy for comparison table."""
    strategy_name: str
    total_5yr_cost: float
    total_5yr_cost_npv: float
    required_capital: float
    expected_annual_cost: float
    cost_var_995: float
    breakeven_year: Optional[int]
    vs_baseline_savings_pct: float


@dataclass
class InsuranceStructureComparison:
    """
    Side-by-side comparison of all evaluated strategies.

    Attributes
    ----------
    strategies : List[StrategyComparison]
    recommended : str
        Name of the recommended strategy.
    rationale : str
        Plain-English rationale for the recommendation.
    """
    strategies: List[StrategyComparison]
    recommended: str
    rationale: str


# ─────────────────────────────────────────────────────────────────────────────
# Capital efficiency and mitigation impact summaries (Sprint 3)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CapitalEfficiencySummary:
    """
    Summary of the capital optimisation outcome.

    Intended to be populated by the capital optimiser (Phase 3).
    Fields are included here now so PlatformReport is forward-compatible.

    Attributes
    ----------
    optimal_retention : float
        Retention level that minimises total cost of risk (NOK).
    minimum_tcor : float
        Minimum achievable TCOR at optimal retention (NOK).
    current_tcor_estimate : float
        TCOR under the current structure (NOK).
    potential_saving_nok : float
        current_tcor_estimate − minimum_tcor (NOK).
    recommended_structure_description : str
        Plain-English description of the optimal structure.
    """
    optimal_retention: float
    minimum_tcor: float
    current_tcor_estimate: float
    potential_saving_nok: float
    recommended_structure_description: str


@dataclass
class MitigationImpactSummary:
    """
    Board-ready summary of the best mitigation scenario's capital impact.

    Attributes
    ----------
    baseline_expected_loss : float
    best_scenario_expected_loss : float
    best_scenario_name : str
    total_mitigation_cost_annual : float
    net_5yr_benefit : float
        (baseline_loss − mitigated_loss − annual_cost) × 5 (NOK).
    recommended_actions : List[str]
        Action names in the best scenario.
    baseline_scr : float
    best_scenario_scr : float
    delta_scr : float
    baseline_tcor : float
    best_scenario_tcor : float
    delta_tcor : float
    """
    baseline_expected_loss: float
    best_scenario_expected_loss: float
    best_scenario_name: str
    total_mitigation_cost_annual: float
    net_5yr_benefit: float
    recommended_actions: List[str]
    baseline_scr: float = 0.0
    best_scenario_scr: float = 0.0
    delta_scr: float = 0.0
    baseline_tcor: float = 0.0
    best_scenario_tcor: float = 0.0
    delta_tcor: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Top-level report
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PlatformReport:
    """
    Complete Shield Captive Risk Platform assessment report.

    This is the top-level container populated by the analysis pipeline.
    All sections are optional to allow partial reports during development.

    Attributes
    ----------
    executive_summary : ExecutiveSummary
    risk_metrics : RiskMetricsSummary
    suitability : Recommendation (from analysis.suitability_engine)
    suitability_path : SuitabilityPath (from analysis.suitability_engine)
    insurance_comparison : InsuranceStructureComparison
    mitigation_scenarios : List[MitigationScenario]
    data_confidence : str
        Overall confidence label for the report.
    generated_at : str
        ISO-8601 datetime when the report was generated.
    """
    executive_summary: ExecutiveSummary
    risk_metrics: RiskMetricsSummary
    suitability: object          # analysis.suitability_engine.Recommendation
    suitability_path: object     # analysis.suitability_engine.SuitabilityPath
    insurance_comparison: InsuranceStructureComparison
    mitigation_scenarios: List[object] = field(default_factory=list)  # List[MitigationScenario]
    data_confidence: str = "Medium"
    generated_at: str = ""

    # Sprint 3 additions (all optional, backward-compatible)
    capital_efficiency: Optional[CapitalEfficiencySummary] = None
    mitigation_impact: Optional[MitigationImpactSummary] = None
    site_risk_explanations: List[object] = field(default_factory=list)
