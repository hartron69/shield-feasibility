"""
Shield Captive Risk Platform – Mitigation Model (Sprint 2).

Provides a library of predefined mitigation actions and an analyser that
models how adopting a set of actions affects the expected loss, SCR, and
overall cost of risk.

Sprint 2 improvements
---------------------
* Risk-specific mitigation: actions now carry ``targeted_risk_types`` that
  restrict which C5AI+ risk-type slices (hab, lice, jellyfish, pathogen) are
  affected.  Portfolio-wide scaling is used as fallback when bio_loss_breakdown
  is unavailable.
* Uncertain effectiveness: ``MitigationAction.sample_effectiveness()`` draws
  from a Beta distribution, enabling stochastic scenario analysis.
* Forecast-level mitigation: ``apply_mitigations_to_forecast()`` adjusts
  C5AI+ probability / severity estimates *before* Monte Carlo runs, so that
  the simulation operates on mitigated risk levels rather than scaling losses
  afterwards.

Feasibility-grade notes
-----------------------
* Uncertainty is scenario-level (one Beta draw per action per compare() call),
  not path-level.  This is clearly documented and sufficient for board-level
  scenario planning.
* Severity reduction is applied as a uniform multiplier on expected_loss_mean,
  expected_loss_p50, and expected_loss_p90.  Tail behaviour changes are
  approximated, not re-derived from first principles.
* Structural / environmental / operational risk types do not appear in
  bio_loss_breakdown and therefore cannot benefit from risk-specific
  mitigation in compare() — those actions fall back to portfolio-wide scaling.
  This is logged as ``fallback_to_portfolio_scaling = True``.

Platform principle
------------------
This is a risk modelling and insurance decision platform, NOT an early-warning
system.  All mitigation analysis targets site-level risk assessment, expected
loss modelling, and capital requirement analysis.
"""

from __future__ import annotations

import copy
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from models.monte_carlo import SimulationResults
from models.domain_loss_breakdown import (
    DomainLossBreakdown,
    DOMAIN_SUBTYPES,
    STRUCTURAL_SUBTYPE_CAPS,
)


# ─────────────────────────────────────────────────────────────────────────────
# MitigationAction
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MitigationAction:
    """
    A single risk-mitigation intervention.

    Core attributes (unchanged from Sprint 1)
    -----------------------------------------
    name : str
    description : str
    applies_to_domains : List[str]
        Broad domain labels for human-readable categorisation.
    probability_reduction : float
        Fraction by which event probability is reduced (0–1).
    severity_reduction : float
        Fraction by which event severity is reduced (0–1).
    annual_cost_nok : float
    capex_nok : float

    Sprint 2 additions (all have backward-compatible defaults)
    ----------------------------------------------------------
    targeted_risk_types : List[str]
        C5AI+ risk types this action specifically targets.
        Allowed values: "hab", "lice", "jellyfish", "pathogen", "structural".
        Empty list → portfolio-wide action (original behaviour preserved).
    mitigation_mode : str
        "probability" – action reduces event frequency only.
        "severity"    – action reduces loss magnitude only.
        "both"        – action reduces both (default).
    target_level : str
        "risk_type"  – effect applied per targeted risk type.
        "domain"     – effect applied across a broad domain.
        "portfolio"  – portfolio-wide effect (default for empty targeted_risk_types).
    effectiveness_alpha : float
        Alpha parameter of the Beta distribution used for uncertainty sampling.
        Default 8.0 → mean effectiveness ≈ 0.80 of configured reduction.
    effectiveness_beta : float
        Beta parameter. Default 2.0 → Beta(8, 2), std ≈ 0.12.
    """

    name: str
    description: str
    applies_to_domains: List[str]
    probability_reduction: float = 0.0
    severity_reduction: float = 0.0
    annual_cost_nok: float = 0.0
    capex_nok: float = 0.0

    # Sprint 2 additions
    targeted_risk_types: List[str] = field(default_factory=list)
    mitigation_mode: str = "both"        # "probability" | "severity" | "both"
    target_level: str = "portfolio"      # "risk_type" | "domain" | "portfolio"
    effectiveness_alpha: float = 8.0
    effectiveness_beta: float = 2.0

    @property
    def combined_loss_reduction(self) -> float:
        """
        Deterministic expected-loss reduction factor.

        E[L_mitigated] = E[L] × (1 − p_red) × (1 − s_red)

        Returns the fractional loss reduction (1 − remaining_fraction).
        """
        remaining = (1 - self.probability_reduction) * (1 - self.severity_reduction)
        return round(1.0 - remaining, 4)

    def sample_effectiveness(
        self,
        rng: np.random.Generator,
        n_samples: int = 1,
    ) -> np.ndarray:
        """
        Sample stochastic effectiveness factors from Beta(alpha, beta).

        Each sample represents a fraction of ``combined_loss_reduction``
        that is actually realised in practice.

        Example
        -------
        With default Beta(8, 2): mean factor ≈ 0.80, std ≈ 0.12.
        If ``combined_loss_reduction = 0.40``, effective reduction
        per sample ≈ 0.40 × 0.80 = 0.32 (central estimate).

        Parameters
        ----------
        rng : np.random.Generator
        n_samples : int

        Returns
        -------
        np.ndarray shape (n_samples,)
            Effective loss reduction fractions in (0, combined_loss_reduction).
        """
        factors = rng.beta(self.effectiveness_alpha, self.effectiveness_beta, n_samples)
        return factors * self.combined_loss_reduction


# ─────────────────────────────────────────────────────────────────────────────
# Predefined action library
# ─────────────────────────────────────────────────────────────────────────────

PREDEFINED_MITIGATIONS: Dict[str, MitigationAction] = {
    "stronger_nets": MitigationAction(
        name="stronger_nets",
        description=(
            "Upgrade to HDPE high-strength nets with predator protection and "
            "improved UV-resistant mesh.  Reduces net tear probability and "
            "limits cage deformation severity under structural loading."
        ),
        applies_to_domains=["structural"],
        probability_reduction=0.25,
        severity_reduction=0.15,
        annual_cost_nok=500_000,
        capex_nok=3_000_000,
        # Sprint 5: explicit sub-type targeting (net_integrity primary,
        # cage_structural secondary — stronger nets reduce cage stress)
        targeted_risk_types=["net_integrity", "cage_structural"],
        mitigation_mode="both",
        target_level="risk_type",
    ),
    "stronger_anchors": MitigationAction(
        name="stronger_anchors",
        description=(
            "Install high-holding-power (HHP) or drag-embedment anchors with "
            "increased fluke area and corrosion-resistant coating.  Primarily "
            "reduces the probability of anchor drag and mooring-system loss of "
            "station.  Little direct effect on loss severity once a failure occurs."
        ),
        applies_to_domains=["structural"],
        probability_reduction=0.35,
        severity_reduction=0.05,   # minimal — once anchor drags, loss is similar
        annual_cost_nok=150_000,   # periodic inspection and maintenance
        capex_nok=2_500_000,
        # Sprint 5: targets mooring_failure only — anchor holding capacity
        targeted_risk_types=["mooring_failure"],
        mitigation_mode="probability",   # primary effect is on event frequency
        target_level="risk_type",
    ),
    "stronger_moorings": MitigationAction(
        name="stronger_moorings",
        description=(
            "Upgrade the full mooring system: replace lines with higher-grade "
            "chain, improve connector corrosion protection, and optimise mooring "
            "geometry for current load.  Reduces both mooring failure probability "
            "and the structural overload consequences on cage frames."
        ),
        applies_to_domains=["structural"],
        probability_reduction=0.30,
        severity_reduction=0.20,
        annual_cost_nok=200_000,
        capex_nok=4_500_000,
        # Sprint 5: mooring_failure primary, cage_structural secondary
        # (better mooring geometry reduces cage frame stress)
        targeted_risk_types=["mooring_failure", "cage_structural"],
        mitigation_mode="both",
        target_level="risk_type",
    ),
    "lice_barriers": MitigationAction(
        name="lice_barriers",
        description="Install submerged snorkel / lice barrier curtains",
        applies_to_domains=["biological", "lice"],
        probability_reduction=0.30,
        severity_reduction=0.20,
        annual_cost_nok=800_000,
        capex_nok=5_000_000,
        targeted_risk_types=["lice"],
        mitigation_mode="both",
        target_level="risk_type",
    ),
    "jellyfish_mitigation": MitigationAction(
        name="jellyfish_mitigation",
        description="Deploy jellyfish barriers and early-warning sensor buoys",
        applies_to_domains=["biological", "jellyfish"],
        probability_reduction=0.40,
        severity_reduction=0.30,
        annual_cost_nok=600_000,
        capex_nok=2_000_000,
        targeted_risk_types=["jellyfish"],
        mitigation_mode="both",
        target_level="risk_type",
    ),
    "environmental_sensors": MitigationAction(
        name="environmental_sensors",
        description="Deploy real-time oxygen, temperature, and chlorophyll sensors",
        applies_to_domains=["environmental", "biological", "hab"],
        probability_reduction=0.15,
        severity_reduction=0.25,
        annual_cost_nok=400_000,
        capex_nok=1_500_000,
        targeted_risk_types=["hab", "oxygen_stress", "temperature_extreme"],
        mitigation_mode="both",
        target_level="risk_type",
    ),
    "storm_contingency_plan": MitigationAction(
        name="storm_contingency_plan",
        description="Develop and rehearse storm contingency plans; reinforce mooring inspection protocols",
        applies_to_domains=["environmental"],
        probability_reduction=0.05,
        severity_reduction=0.25,
        annual_cost_nok=100_000,
        capex_nok=300_000,
        targeted_risk_types=["current_storm", "ice"],
        mitigation_mode="severity",
        target_level="risk_type",
    ),
    "staff_training_program": MitigationAction(
        name="staff_training_program",
        description="Structured competency training and certification programme for all site staff",
        applies_to_domains=["operational"],
        probability_reduction=0.20,
        severity_reduction=0.15,
        annual_cost_nok=300_000,
        capex_nok=200_000,
        targeted_risk_types=["human_error", "procedure_failure"],
        mitigation_mode="both",
        target_level="risk_type",
    ),
    "deformation_monitoring": MitigationAction(
        name="deformation_monitoring",
        description=(
            "Real-time cage geometry sensors detecting net deformation and mooring "
            "deviation before structural failure."
        ),
        applies_to_domains=["structural"],
        probability_reduction=0.30,
        severity_reduction=0.20,
        annual_cost_nok=250_000,
        capex_nok=2_000_000,
        targeted_risk_types=["net_integrity", "mooring_failure", "cage_structural"],
        mitigation_mode="both",
        target_level="risk_type",
    ),
    "ai_early_warning": MitigationAction(
        name="ai_early_warning",
        description=(
            "AI-driven integrated early warning combining environmental, biological, "
            "and structural sensor feeds to predict multi-domain stress events."
        ),
        applies_to_domains=["biological", "environmental", "structural"],
        probability_reduction=0.20,
        severity_reduction=0.15,
        annual_cost_nok=600_000,
        capex_nok=3_500_000,
        targeted_risk_types=["hab", "oxygen_stress", "temperature_extreme", "net_integrity"],
        mitigation_mode="both",
        target_level="risk_type",
    ),
    "risk_manager_hire": MitigationAction(
        name="risk_manager_hire",
        description="Hire a dedicated Risk Manager with aquaculture insurance expertise",
        applies_to_domains=["operational", "all"],
        probability_reduction=0.10,
        severity_reduction=0.10,
        annual_cost_nok=1_200_000,
        capex_nok=0,
        targeted_risk_types=[],        # portfolio-wide
        mitigation_mode="severity",
        target_level="portfolio",
    ),
    "emergency_response_plan": MitigationAction(
        name="emergency_response_plan",
        description="Develop and exercise a formal biological and structural ERP",
        applies_to_domains=["operational", "biological"],
        probability_reduction=0.05,
        severity_reduction=0.20,
        annual_cost_nok=150_000,
        capex_nok=300_000,
        targeted_risk_types=[],        # portfolio-wide
        mitigation_mode="severity",
        target_level="portfolio",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Scenario output
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MitigationScenario:
    """
    Result of evaluating a combination of mitigation actions.

    Core fields (unchanged from Sprint 1)
    --------------------------------------
    name, actions, adjusted_expected_loss, adjusted_scr,
    annual_mitigation_cost, net_benefit_annual, delta_vs_baseline_pct

    Sprint 2 additions (all have backward-compatible defaults)
    ----------------------------------------------------------
    baseline_expected_loss : float
        Un-mitigated baseline mean annual loss (NOK).
    affected_risk_types : List[str]
        Risk types that received targeted (non-portfolio-wide) reduction.
    risk_type_deltas : Dict[str, float]
        Per-risk-type change in expected annual loss (NOK, negative = improvement).
    fallback_to_portfolio_scaling : bool
        True when bio_loss_breakdown was not available and all actions
        fell back to portfolio-wide scaling.
    effective_reduction_mean : float or None
        Mean effective loss reduction fraction across stochastic samples
        (populated when use_uncertainty=True).
    effective_reduction_p10, effective_reduction_p90 : float or None
        10th / 90th percentile of effective reduction distribution.
    """

    name: str
    actions: List[MitigationAction]
    adjusted_expected_loss: float
    adjusted_scr: float
    annual_mitigation_cost: float
    net_benefit_annual: float
    delta_vs_baseline_pct: float

    # Sprint 2 reporting additions
    baseline_expected_loss: float = 0.0
    affected_risk_types: List[str] = field(default_factory=list)
    risk_type_deltas: Dict[str, float] = field(default_factory=dict)
    fallback_to_portfolio_scaling: bool = False
    effective_reduction_mean: Optional[float] = None
    effective_reduction_p10: Optional[float] = None
    effective_reduction_p90: Optional[float] = None

    # Sprint 3: full mitigated loss matrix for capital decomposition
    mitigated_annual_losses: Optional[np.ndarray] = field(default=None, repr=False)


# ─────────────────────────────────────────────────────────────────────────────
# Mitigation analyser
# ─────────────────────────────────────────────────────────────────────────────

class MitigationAnalyzer:
    """
    Evaluate the effect of mitigation actions on simulated loss distributions.

    Parameters
    ----------
    sim : SimulationResults
        Monte Carlo results representing the un-mitigated baseline.
    """

    def __init__(self, sim: SimulationResults) -> None:
        self.sim = sim
        self._baseline_mean = sim.mean_annual_loss
        self._baseline_scr = sim.var_995

    def compare(
        self,
        actions: List[MitigationAction],
        scenario_name: str = "Mitigation Scenario",
        bio_loss_breakdown: Optional[Dict[str, np.ndarray]] = None,
        use_uncertainty: bool = False,
        rng: Optional[np.random.Generator] = None,
        domain_loss_breakdown: Optional[DomainLossBreakdown] = None,
    ) -> MitigationScenario:
        """
        Compute the effect of applying the given mitigation actions.

        Domain breakdown path (preferred, Sprint 4)
        --------------------------------------------
        When ``domain_loss_breakdown`` is provided all four domains
        (biological, structural, environmental, operational) are available
        as named slices.  Actions can target:

        * Sub-type keys: ``"jellyfish"``, ``"lice"``, ``"hab"``, ``"pathogen"``
          → reduces only the matching biological sub-type.
        * Domain keys: ``"structural"``, ``"environmental"``, ``"operational"``
          → reduces *all* sub-types within that domain proportionally.

        Portfolio-wide actions (empty ``targeted_risk_types``) and actions
        whose targets are not found in the breakdown still fall back to a
        combined multiplier applied after the slice adjustments.

        This path supersedes ``bio_loss_breakdown`` when both are provided.

        Bio-only path (Sprint 2, backward compatible)
        -----------------------------------------------
        When only ``bio_loss_breakdown`` is provided the behaviour is
        identical to Sprint 2: biological sub-type slices are targeted and
        the non-bio residual is scaled by the portfolio multiplier.

        Fallback path (neither breakdown provided)
        ------------------------------------------
        All actions contribute to a single portfolio-wide multiplier.
        ``fallback_to_portfolio_scaling = True`` is set.

        Uncertainty mode (use_uncertainty=True)
        ----------------------------------------
        One Beta draw per action is taken.  Effective reduction =
        ``combined_loss_reduction × beta_sample``.  Scenario-level only.

        Parameters
        ----------
        actions : List[MitigationAction]
        scenario_name : str
        bio_loss_breakdown : Dict[str, np.ndarray], optional
            Per-risk-type loss arrays (Sprint 2 path).
        use_uncertainty : bool
        rng : np.random.Generator, optional
        domain_loss_breakdown : DomainLossBreakdown, optional
            Full four-domain breakdown (Sprint 4 preferred path).

        Returns
        -------
        MitigationScenario
        """
        if not actions:
            return MitigationScenario(
                name=scenario_name,
                actions=[],
                adjusted_expected_loss=self._baseline_mean,
                adjusted_scr=self._baseline_scr,
                annual_mitigation_cost=0.0,
                net_benefit_annual=0.0,
                delta_vs_baseline_pct=0.0,
                baseline_expected_loss=self._baseline_mean,
                mitigated_annual_losses=self.sim.annual_losses,
            )

        if use_uncertainty and rng is None:
            rng = np.random.default_rng()

        # ── Resolve effective reductions per action ───────────────────────────
        if use_uncertainty:
            eff_reductions = [
                float(a.sample_effectiveness(rng, n_samples=1)[0]) for a in actions
            ]
        else:
            eff_reductions = [a.combined_loss_reduction for a in actions]

        # ── Apply reductions to loss distribution ─────────────────────────────
        if domain_loss_breakdown is not None:
            # Sprint 4: full four-domain decomposition (preferred path)
            adjusted_losses, affected_types, risk_type_deltas, fallback = (
                self._apply_domain_specific(
                    actions, eff_reductions, domain_loss_breakdown
                )
            )
        elif bio_loss_breakdown is not None:
            # Sprint 2: bio-only breakdown (backward compatible)
            adjusted_losses, affected_types, risk_type_deltas, fallback = (
                self._apply_risk_specific(
                    actions, eff_reductions, bio_loss_breakdown
                )
            )
        else:
            adjusted_losses, affected_types, risk_type_deltas, fallback = (
                self._apply_portfolio_wide(actions, eff_reductions)
            )

        # ── Compute statistics ────────────────────────────────────────────────
        flat = adjusted_losses.flatten()
        adjusted_mean = float(flat.mean())
        adjusted_scr = float(np.percentile(flat, 99.5))

        annual_cost = sum(a.annual_cost_nok for a in actions)
        annual_loss_reduction = self._baseline_mean - adjusted_mean
        net_benefit = annual_loss_reduction - annual_cost
        delta_pct = (
            (adjusted_mean - self._baseline_mean) / max(self._baseline_mean, 1)
        ) * 100.0

        # ── Uncertainty summary ───────────────────────────────────────────────
        eff_mean = eff_p10 = eff_p90 = None
        if use_uncertainty:
            eff_mean = float(np.mean(eff_reductions))
            eff_p10 = float(np.percentile(eff_reductions, 10))
            eff_p90 = float(np.percentile(eff_reductions, 90))

        return MitigationScenario(
            name=scenario_name,
            actions=actions,
            adjusted_expected_loss=round(adjusted_mean, 0),
            adjusted_scr=round(adjusted_scr, 0),
            annual_mitigation_cost=round(annual_cost, 0),
            net_benefit_annual=round(net_benefit, 0),
            delta_vs_baseline_pct=round(delta_pct, 2),
            baseline_expected_loss=round(self._baseline_mean, 0),
            affected_risk_types=sorted(affected_types),
            risk_type_deltas={k: round(v, 0) for k, v in risk_type_deltas.items()},
            fallback_to_portfolio_scaling=fallback,
            effective_reduction_mean=eff_mean,
            effective_reduction_p10=eff_p10,
            effective_reduction_p90=eff_p90,
            mitigated_annual_losses=adjusted_losses,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _apply_risk_specific(
        self,
        actions: List[MitigationAction],
        eff_reductions: List[float],
        bio_loss_breakdown: Dict[str, np.ndarray],
    ):
        """
        Apply risk-specific reductions to bio_loss_breakdown slices.

        Returns (adjusted_losses, affected_types, risk_type_deltas, fallback_flag).

        Portfolio-wide actions accumulate into ``portfolio_multiplier`` which is
        applied to the fully-rebuilt loss matrix at the end, so they correctly
        reduce both bio and residual (structural/operational) losses.
        """
        # Work on copies of bio slices; residual is the non-bio portion.
        adjusted_slices: Dict[str, np.ndarray] = {
            k: v.copy() for k, v in bio_loss_breakdown.items()
        }
        total_bio = sum(adjusted_slices.values())
        residual = self.sim.annual_losses - total_bio  # structural/operational portion

        portfolio_multiplier = 1.0
        affected_types: set = set()
        # Track initial means for delta computation
        initial_means: Dict[str, float] = {
            k: float(v.mean()) for k, v in adjusted_slices.items()
        }
        any_fallback = False

        for action, eff_red in zip(actions, eff_reductions):
            matched = [
                rt for rt in action.targeted_risk_types
                if rt in adjusted_slices
            ]

            if matched:
                # Risk-specific: reduce only matching slices
                for rt in matched:
                    adjusted_slices[rt] = adjusted_slices[rt] * (1.0 - eff_red)
                    affected_types.add(rt)
            else:
                # Portfolio-wide: no match or empty targeted_risk_types
                portfolio_multiplier *= (1.0 - eff_red)
                if action.targeted_risk_types:
                    # Action had targets but none matched – note fallback
                    any_fallback = True
                    warnings.warn(
                        f"MitigationAction '{action.name}': targeted_risk_types "
                        f"{action.targeted_risk_types} not found in bio_loss_breakdown "
                        f"({list(adjusted_slices.keys())}). Falling back to "
                        f"portfolio-wide scaling for this action.",
                        UserWarning,
                        stacklevel=4,
                    )

        # Rebuild and apply portfolio multiplier
        rebuilt = np.maximum(
            (sum(adjusted_slices.values()) + residual) * portfolio_multiplier,
            0.0,
        )

        # Risk-type deltas: compare initial vs final slice means × portfolio_multiplier
        final_means: Dict[str, float] = {
            k: float(v.mean()) * portfolio_multiplier
            for k, v in adjusted_slices.items()
        }
        risk_type_deltas: Dict[str, float] = {
            k: final_means[k] - initial_means[k]
            for k in adjusted_slices
        }

        return rebuilt, affected_types, risk_type_deltas, any_fallback

    def _apply_domain_specific(
        self,
        actions: List[MitigationAction],
        eff_reductions: List[float],
        domain_bd: DomainLossBreakdown,
    ):
        """
        Apply mitigation reductions using a full DomainLossBreakdown (Sprint 4).

        Targeting rules
        ---------------
        * ``targeted_risk_types = ["jellyfish"]``   → sub-type match: reduces
          ``domain_bd.biological["jellyfish"]`` only.
        * ``targeted_risk_types = ["structural"]``  → domain match: reduces
          *all* sub-type arrays in ``domain_bd.structural`` by the same factor.
        * ``targeted_risk_types = []``              → portfolio-wide: accumulates
          into ``portfolio_multiplier`` applied after all slice adjustments.
        * Unmatched targets (not in any domain or sub-type) → portfolio-wide
          fallback with UserWarning.

        The portfolio total is preserved by construction:
            rebuilt = sum(all_adjusted_subtypes) × portfolio_multiplier

        Returns
        -------
        (adjusted_losses, affected_types, risk_type_deltas, any_fallback)
        """
        # Build mapping: domain name → list of sub-type keys it contains
        domain_subtypes: Dict[str, List[str]] = {
            domain: list(getattr(domain_bd, domain).keys())
            for domain in ("biological", "structural", "environmental", "operational")
        }

        # Build flat mutable copy of all sub-type arrays
        adjusted: Dict[str, np.ndarray] = {}
        for domain in ("biological", "structural", "environmental", "operational"):
            for st, arr in getattr(domain_bd, domain).items():
                adjusted[st] = arr.copy()

        # Pre-loop copies needed for cap enforcement (Sprint 5)
        initial_adjusted_copies: Dict[str, np.ndarray] = {
            k: v.copy() for k, v in adjusted.items()
        }

        # Initial means for delta computation
        initial_means: Dict[str, float] = {k: float(v.mean()) for k, v in adjusted.items()}
        initial_domain_means: Dict[str, float] = {
            domain: sum(initial_means.get(st, 0.0) for st in stypes)
            for domain, stypes in domain_subtypes.items()
        }

        portfolio_multiplier = 1.0
        affected_types: set = set()
        any_fallback = False

        for action, eff_red in zip(actions, eff_reductions):
            matched: List[tuple] = []  # list of (target_key, [subtype_keys])

            for rt in action.targeted_risk_types:
                if rt in adjusted:
                    # Direct sub-type match (e.g. "jellyfish", "hab")
                    matched.append((rt, [rt]))
                elif rt in domain_subtypes and domain_subtypes[rt]:
                    # Domain-level match (e.g. "structural") → all sub-types
                    matched.append((rt, domain_subtypes[rt]))

            if matched:
                for target_key, subtypes in matched:
                    for st in subtypes:
                        if st in adjusted:
                            adjusted[st] = adjusted[st] * (1.0 - eff_red)
                    affected_types.add(target_key)
            else:
                portfolio_multiplier *= (1.0 - eff_red)
                if action.targeted_risk_types:
                    any_fallback = True
                    warnings.warn(
                        f"MitigationAction '{action.name}': targeted_risk_types "
                        f"{action.targeted_risk_types} not found in "
                        f"domain_loss_breakdown. Falling back to portfolio-wide "
                        f"scaling for this action.",
                        UserWarning,
                        stacklevel=4,
                    )

        # Sprint 5: apply structural sub-type caps to prevent unrealistic
        # combined reductions (e.g. stronger_anchors + stronger_moorings on
        # mooring_failure capped at 48%).
        for st, cap_fraction in STRUCTURAL_SUBTYPE_CAPS.items():
            if st in adjusted:
                min_allowed = initial_adjusted_copies[st] * (1.0 - cap_fraction)
                adjusted[st] = np.maximum(adjusted[st], min_allowed)

        # Rebuild portfolio total and apply portfolio multiplier
        rebuilt = np.maximum(sum(adjusted.values()) * portfolio_multiplier, 0.0)

        # Compute risk_type_deltas at the level that was targeted
        final_means: Dict[str, float] = {
            k: float(v.mean()) * portfolio_multiplier for k, v in adjusted.items()
        }
        risk_type_deltas: Dict[str, float] = {}
        for target_key in affected_types:
            if target_key in domain_subtypes:
                # Domain-level target: aggregate delta across its sub-types
                final_dom = sum(
                    final_means.get(st, 0.0) for st in domain_subtypes[target_key]
                )
                initial_dom = initial_domain_means[target_key]
                risk_type_deltas[target_key] = final_dom - initial_dom
            else:
                # Sub-type level target
                risk_type_deltas[target_key] = (
                    final_means.get(target_key, 0.0)
                    - initial_means.get(target_key, 0.0)
                )

        return rebuilt, affected_types, risk_type_deltas, any_fallback

    def _apply_portfolio_wide(
        self,
        actions: List[MitigationAction],
        eff_reductions: List[float],
    ):
        """
        Original Sprint 1 behaviour: single combined multiplier on all losses.

        Used when no bio_loss_breakdown is available.
        """
        combined_multiplier = 1.0
        for eff_red in eff_reductions:
            combined_multiplier *= (1.0 - eff_red)
        combined_multiplier = max(0.0, min(1.0, combined_multiplier))

        adjusted_losses = self.sim.annual_losses * combined_multiplier
        return adjusted_losses, set(), {}, True

    def compare_all_predefined(
        self,
        bio_loss_breakdown: Optional[Dict[str, np.ndarray]] = None,
        domain_loss_breakdown: Optional[DomainLossBreakdown] = None,
    ) -> List[MitigationScenario]:
        """
        Evaluate each predefined action individually and the full bundle.

        Returns len(PREDEFINED_MITIGATIONS) + 1 scenarios.
        """
        scenarios = []
        for key, action in PREDEFINED_MITIGATIONS.items():
            scenarios.append(
                self.compare(
                    [action],
                    scenario_name=action.name,
                    bio_loss_breakdown=bio_loss_breakdown,
                    domain_loss_breakdown=domain_loss_breakdown,
                )
            )
        all_actions = list(PREDEFINED_MITIGATIONS.values())
        scenarios.append(
            self.compare(
                all_actions,
                scenario_name="full_mitigation_bundle",
                bio_loss_breakdown=bio_loss_breakdown,
                domain_loss_breakdown=domain_loss_breakdown,
            )
        )
        return scenarios


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3 – Capital impact of mitigation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MitigationCapitalImpact:
    """
    Capital and insurance-structure impact of a mitigation scenario.

    Captures how a set of mitigation actions affects the full capital stack:
    expected loss, SCR / VaR 99.5%, retained loss, reinsured loss,
    net captive loss, and total cost of risk (TCOR).

    All monetary values are in NOK.  Delta fields are signed (negative = improvement).

    Parameters
    ----------
    scenario_name : str
    actions : List[MitigationAction]
    annual_mitigation_cost : float
        Sum of annual_cost_nok across all actions.

    Loss impact
    -----------
    baseline_expected_loss, mitigated_expected_loss, delta_expected_loss,
    delta_expected_loss_pct

    SCR impact (VaR 99.5 % of gross losses)
    ----------------------------------------
    baseline_scr, mitigated_scr, delta_scr, delta_scr_pct

    Capital decomposition (requires CaptiveStructure)
    --------------------------------------------------
    baseline_retained_mean, mitigated_retained_mean, delta_retained_mean
    baseline_reinsured_mean, mitigated_reinsured_mean, delta_reinsured_mean
    baseline_net_captive_mean, mitigated_net_captive_mean, delta_net_captive_mean

    Total cost of risk
    ------------------
    TCOR = E[loss] + annual_mitigation_cost.
    baseline_tcor = baseline_expected_loss (no mitigation cost in baseline).
    mitigated_tcor = mitigated_expected_loss + annual_mitigation_cost.
    baseline_tcor, mitigated_tcor, delta_tcor, delta_tcor_pct

    Capital release
    ---------------
    capital_release = baseline_scr − mitigated_scr
        Positive value means capital freed up by mitigation.

    Suitability linkage (optional)
    -------------------------------
    estimated_suitability_delta : float or None
        Rough estimate of composite suitability score improvement (0–100 scale)
        driven by balance-sheet-strength (18 %) and cost-savings (18 %) criteria.
        Populated by MitigationCapitalAnalyzer.analyze() when an operator is
        provided.  None when no operator context is available.
    top_improved_criteria : List[str]
        Suitability criteria most likely improved by this scenario.
    """

    scenario_name: str
    actions: List[MitigationAction]
    annual_mitigation_cost: float

    # Expected loss
    baseline_expected_loss: float
    mitigated_expected_loss: float
    delta_expected_loss: float
    delta_expected_loss_pct: float

    # SCR
    baseline_scr: float
    mitigated_scr: float
    delta_scr: float
    delta_scr_pct: float

    # Capital decomposition
    baseline_retained_mean: float
    mitigated_retained_mean: float
    delta_retained_mean: float

    baseline_reinsured_mean: float
    mitigated_reinsured_mean: float
    delta_reinsured_mean: float

    baseline_net_captive_mean: float
    mitigated_net_captive_mean: float
    delta_net_captive_mean: float

    # TCOR
    baseline_tcor: float
    mitigated_tcor: float
    delta_tcor: float
    delta_tcor_pct: float

    # Capital freed up
    capital_release: float

    # Suitability linkage (optional)
    estimated_suitability_delta: Optional[float] = None
    top_improved_criteria: List[str] = field(default_factory=list)


class MitigationCapitalAnalyzer:
    """
    Evaluate the capital and insurance-structure impact of mitigation actions.

    Wraps ``MitigationAnalyzer`` and additionally decomposes the mitigated
    loss distribution into retained / reinsured / net-captive layers using
    a ``CaptiveStructure`` (optional).  Without a captive structure all losses
    are treated as retained.

    Parameters
    ----------
    sim : SimulationResults
        Monte Carlo results representing the un-mitigated baseline.
    captive_structure : CaptiveStructure or None
        If provided, retained / reinsured / net-captive decomposition is
        computed.  When None, ``baseline_retained_mean = baseline_expected_loss``
        and reinsured / net-captive are set to 0.
    """

    def __init__(self, sim: SimulationResults, captive_structure=None) -> None:
        self.sim = sim
        self.captive = captive_structure
        self._analyzer = MitigationAnalyzer(sim)

        gross = sim.annual_losses
        self._baseline_mean = sim.mean_annual_loss
        self._baseline_scr = sim.var_995

        if captive_structure is not None:
            self._baseline_retained = float(
                captive_structure.compute_net_loss(gross).mean()
            )
            self._baseline_reinsured = float(
                captive_structure.compute_reinsured_loss(gross).mean()
            )
            self._baseline_captive = float(
                captive_structure.compute_captive_loss(gross).mean()
            )
        else:
            self._baseline_retained = self._baseline_mean
            self._baseline_reinsured = 0.0
            self._baseline_captive = self._baseline_mean

    def analyze(
        self,
        actions: List[MitigationAction],
        scenario_name: str = "Mitigation Scenario",
        bio_loss_breakdown: Optional[Dict[str, np.ndarray]] = None,
        use_uncertainty: bool = False,
        rng: Optional[np.random.Generator] = None,
        domain_loss_breakdown: Optional[DomainLossBreakdown] = None,
    ) -> MitigationCapitalImpact:
        """
        Compute the capital impact of applying the given mitigation actions.

        Runs ``MitigationAnalyzer.compare()`` internally, then decomposes the
        mitigated loss distribution through the captive structure layers.

        Parameters
        ----------
        actions : List[MitigationAction]
        scenario_name : str
        bio_loss_breakdown : Dict[str, np.ndarray], optional
            Sprint 2 bio-only path.
        use_uncertainty : bool
        rng : np.random.Generator, optional
        domain_loss_breakdown : DomainLossBreakdown, optional
            Sprint 4 full-domain path (supersedes bio_loss_breakdown when given).

        Returns
        -------
        MitigationCapitalImpact
        """
        scenario = self._analyzer.compare(
            actions,
            scenario_name=scenario_name,
            bio_loss_breakdown=bio_loss_breakdown,
            use_uncertainty=use_uncertainty,
            rng=rng,
            domain_loss_breakdown=domain_loss_breakdown,
        )

        mitigated_losses = scenario.mitigated_annual_losses   # (N, T)

        # SCR on mitigated losses
        mitigated_scr = float(np.percentile(mitigated_losses.flatten(), 99.5))

        # Capital decomposition
        if self.captive is not None:
            mit_retained = float(self.captive.compute_net_loss(mitigated_losses).mean())
            mit_reinsured = float(
                self.captive.compute_reinsured_loss(mitigated_losses).mean()
            )
            mit_captive = float(
                self.captive.compute_captive_loss(mitigated_losses).mean()
            )
        else:
            mit_retained = float(scenario.adjusted_expected_loss)
            mit_reinsured = 0.0
            mit_captive = float(scenario.adjusted_expected_loss)

        # TCOR = E[loss] + annual_mitigation_cost
        mit_cost = float(scenario.annual_mitigation_cost)
        baseline_tcor = self._baseline_mean   # no mitigation cost in baseline
        mitigated_tcor = float(scenario.adjusted_expected_loss) + mit_cost
        delta_tcor = mitigated_tcor - baseline_tcor
        delta_tcor_pct = (delta_tcor / max(baseline_tcor, 1.0)) * 100.0

        delta_expected = float(scenario.adjusted_expected_loss) - self._baseline_mean
        delta_expected_pct = (
            (delta_expected / max(self._baseline_mean, 1.0)) * 100.0
        )
        delta_scr = mitigated_scr - self._baseline_scr
        delta_scr_pct = (delta_scr / max(self._baseline_scr, 1.0)) * 100.0

        capital_release = self._baseline_scr - mitigated_scr

        # Suitability linkage: rough composite-score delta
        # Balance Sheet criterion (18 %): SCR reduction improves required-capital ratio
        # Cost Savings criterion (18 %): expected-loss reduction → more PCC savings
        # Loss Stability criterion (18 %): expected-loss reduction often correlates
        estimated_suit_delta, top_criteria = self._estimate_suitability_delta(
            delta_scr_pct, delta_expected_pct
        )

        return MitigationCapitalImpact(
            scenario_name=scenario_name,
            actions=actions,
            annual_mitigation_cost=mit_cost,
            baseline_expected_loss=self._baseline_mean,
            mitigated_expected_loss=float(scenario.adjusted_expected_loss),
            delta_expected_loss=delta_expected,
            delta_expected_loss_pct=round(delta_expected_pct, 2),
            baseline_scr=self._baseline_scr,
            mitigated_scr=mitigated_scr,
            delta_scr=delta_scr,
            delta_scr_pct=round(delta_scr_pct, 2),
            baseline_retained_mean=self._baseline_retained,
            mitigated_retained_mean=mit_retained,
            delta_retained_mean=mit_retained - self._baseline_retained,
            baseline_reinsured_mean=self._baseline_reinsured,
            mitigated_reinsured_mean=mit_reinsured,
            delta_reinsured_mean=mit_reinsured - self._baseline_reinsured,
            baseline_net_captive_mean=self._baseline_captive,
            mitigated_net_captive_mean=mit_captive,
            delta_net_captive_mean=mit_captive - self._baseline_captive,
            baseline_tcor=baseline_tcor,
            mitigated_tcor=mitigated_tcor,
            delta_tcor=delta_tcor,
            delta_tcor_pct=round(delta_tcor_pct, 2),
            capital_release=capital_release,
            estimated_suitability_delta=estimated_suit_delta,
            top_improved_criteria=top_criteria,
        )

    def analyze_all_predefined(
        self,
        bio_loss_breakdown: Optional[Dict[str, np.ndarray]] = None,
        domain_loss_breakdown: Optional[DomainLossBreakdown] = None,
    ) -> List[MitigationCapitalImpact]:
        """Evaluate each predefined action individually plus the full bundle."""
        impacts = []
        for key, action in PREDEFINED_MITIGATIONS.items():
            impacts.append(
                self.analyze(
                    [action],
                    scenario_name=action.name,
                    bio_loss_breakdown=bio_loss_breakdown,
                    domain_loss_breakdown=domain_loss_breakdown,
                )
            )
        impacts.append(
            self.analyze(
                list(PREDEFINED_MITIGATIONS.values()),
                scenario_name="full_mitigation_bundle",
                bio_loss_breakdown=bio_loss_breakdown,
                domain_loss_breakdown=domain_loss_breakdown,
            )
        )
        return impacts

    @staticmethod
    def rank_by_tcor_impact(
        impacts: List[MitigationCapitalImpact],
    ) -> List[MitigationCapitalImpact]:
        """Return impacts sorted by TCOR reduction, most beneficial first."""
        return sorted(impacts, key=lambda x: x.delta_tcor)

    @staticmethod
    def rank_by_scr_impact(
        impacts: List[MitigationCapitalImpact],
    ) -> List[MitigationCapitalImpact]:
        """Return impacts sorted by SCR reduction, most capital-efficient first."""
        return sorted(impacts, key=lambda x: x.delta_scr)

    @staticmethod
    def rank_by_suitability_impact(
        impacts: List[MitigationCapitalImpact],
    ) -> List[MitigationCapitalImpact]:
        """Return impacts sorted by estimated suitability score improvement."""
        return sorted(
            impacts,
            key=lambda x: -(x.estimated_suitability_delta or 0.0),
        )

    @staticmethod
    def _estimate_suitability_delta(
        delta_scr_pct: float,
        delta_expected_loss_pct: float,
    ):
        """
        Rough estimate of composite suitability score improvement.

        Three criteria are approximated (combined weight 54 %):
        - Balance Sheet Strength (18 %): SCR reduction eases capital burden
        - Cost Savings Potential (18 %): lower expected loss → more PCC savings
        - Loss Stability (18 %): lower expected loss often reduces variance too

        For a 10 % loss reduction the improvement in each criterion's raw score
        is capped at 20 points (heuristic).  The weighted composite delta is
        therefore at most ~10.8 points for a single criterion.

        Returns (estimated_delta, top_criteria_list).
        """
        top: List[str] = []
        composite_delta = 0.0

        # Balance sheet: SCR reduction
        if delta_scr_pct < 0:
            raw_improvement = min(20.0, abs(delta_scr_pct) * 0.5)
            composite_delta += raw_improvement * 0.18
            top.append("Balance Sheet Strength")

        # Cost savings: expected-loss reduction → more PCC savings
        if delta_expected_loss_pct < 0:
            raw_improvement = min(20.0, abs(delta_expected_loss_pct) * 0.5)
            composite_delta += raw_improvement * 0.18
            top.append("Cost Savings Potential")

        # Loss stability: expected-loss reduction as proxy for variance reduction
        if delta_expected_loss_pct < 0:
            raw_improvement = min(10.0, abs(delta_expected_loss_pct) * 0.25)
            composite_delta += raw_improvement * 0.18
            top.append("Loss Stability")

        return round(composite_delta, 3), top


def build_mitigation_impact_summary(
    impacts: List[MitigationCapitalImpact],
    projection_years: int = 5,
) -> "MitigationImpactSummary":
    """
    Produce a board-ready ``MitigationImpactSummary`` from a list of
    ``MitigationCapitalImpact`` objects.

    The best scenario is identified as the one with the lowest TCOR.
    5-year net benefit is computed as:
        (baseline_expected_loss − mitigated_expected_loss − annual_mitigation_cost)
        × projection_years

    Parameters
    ----------
    impacts : List[MitigationCapitalImpact]
    projection_years : int, default 5

    Returns
    -------
    MitigationImpactSummary (from reporting.report_model)
    """
    from reporting.report_model import MitigationImpactSummary

    if not impacts:
        raise ValueError("impacts list must not be empty")

    best = min(impacts, key=lambda x: x.delta_tcor)

    annual_saving = best.baseline_expected_loss - best.mitigated_expected_loss
    net_5yr = (annual_saving - best.annual_mitigation_cost) * projection_years

    recommended = [a.name for a in best.actions]

    return MitigationImpactSummary(
        baseline_expected_loss=best.baseline_expected_loss,
        best_scenario_expected_loss=best.mitigated_expected_loss,
        best_scenario_name=best.scenario_name,
        total_mitigation_cost_annual=best.annual_mitigation_cost,
        net_5yr_benefit=net_5yr,
        recommended_actions=recommended,
        baseline_scr=best.baseline_scr,
        best_scenario_scr=best.mitigated_scr,
        delta_scr=best.delta_scr,
        baseline_tcor=best.baseline_tcor,
        best_scenario_tcor=best.mitigated_tcor,
        delta_tcor=best.delta_tcor,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Forecast-level mitigation (Part C)
# ─────────────────────────────────────────────────────────────────────────────

def apply_mitigations_to_forecast(
    forecast,                          # RiskForecast (avoid circular import)
    actions: List[MitigationAction],
    use_uncertainty: bool = False,
    rng: Optional[np.random.Generator] = None,
):
    """
    Apply mitigation actions to a C5AI+ RiskForecast before Monte Carlo runs.

    This is the upstream mitigation path: rather than scaling Monte Carlo
    output losses, this function adjusts the forecast probabilities and
    expected losses that feed into the simulation.

    How reductions are applied
    --------------------------
    * ``mitigation_mode = "probability"``: action.probability_reduction applied
      to each targeted RiskTypeForecast.event_probability.
    * ``mitigation_mode = "severity"``: action.severity_reduction applied to
      expected_loss_mean, expected_loss_p50, expected_loss_p90.
    * ``mitigation_mode = "both"``: both reductions are applied.

    Portfolio-wide actions (empty targeted_risk_types) apply to ALL risk types
    across all sites.

    Original values are preserved in:
        rtf.baseline_event_probability
        rtf.baseline_expected_loss_mean
    Applied action names are recorded in ``rtf.applied_mitigations``.

    The operator_aggregate is recomputed from the adjusted site forecasts so
    that MonteCarloEngine receives consistent scale factors.

    Uncertainty
    -----------
    When ``use_uncertainty=True`` and ``rng`` is provided, one Beta draw per
    action is sampled and used to scale the nominal reduction.  This gives a
    stochastic adjusted forecast for scenario analysis.

    Limitations
    -----------
    * Feasibility-grade: p50 and p90 are scaled by the same factor as mean.
      In production a re-derived severity distribution would be preferable.
    * Probability reductions are multiplicative and may produce low but
      non-zero probabilities; they never go negative.
    * Only C5AI+ biological risk types ("hab", "lice", "jellyfish", "pathogen")
      are present in site_forecasts; structural / environmental / operational
      risk types cannot be targeted here.

    Parameters
    ----------
    forecast : RiskForecast
        Baseline forecast to be adjusted.  Not modified in-place; a deep
        copy is returned.
    actions : List[MitigationAction]
        Actions to apply.  If empty, the original forecast is returned unchanged.
    use_uncertainty : bool
        If True, effectiveness is sampled from Beta distributions.
    rng : np.random.Generator, optional
        Required when use_uncertainty=True.

    Returns
    -------
    RiskForecast
        Adjusted forecast (deep copy of input with modified values).
    """
    from c5ai_plus.data_models.forecast_schema import RISK_TYPES

    if not actions:
        return forecast  # nothing to do – return original unchanged

    if use_uncertainty and rng is None:
        rng = np.random.default_rng()

    # Sample effectiveness once per action (scenario-level uncertainty)
    if use_uncertainty:
        prob_eff = {
            a.name: float(rng.beta(a.effectiveness_alpha, a.effectiveness_beta))
            for a in actions
        }
        sev_eff = prob_eff  # same draw: one Beta sample per action
    else:
        prob_eff = {a.name: 1.0 for a in actions}
        sev_eff = {a.name: 1.0 for a in actions}

    # Build lookup: risk_type → actions that target it (or [] if portfolio-wide)
    risk_type_to_actions: Dict[str, List] = {rt: [] for rt in RISK_TYPES}
    portfolio_actions: List = []
    for action in actions:
        if action.targeted_risk_types:
            for rt in action.targeted_risk_types:
                if rt in risk_type_to_actions:
                    risk_type_to_actions[rt].append(action)
        else:
            portfolio_actions.append(action)

    # Deep-copy so we never mutate the original
    adjusted = copy.deepcopy(forecast)

    applied_action_names = sorted({a.name for a in actions})

    for sf in adjusted.site_forecasts:
        for rtf in sf.annual_forecasts:
            # Collect relevant actions for this risk type
            relevant = risk_type_to_actions.get(rtf.risk_type, []) + portfolio_actions
            if not relevant:
                continue

            # Preserve baselines (only on first modification)
            if rtf.baseline_event_probability is None:
                rtf.baseline_event_probability = rtf.event_probability
            if rtf.baseline_expected_loss_mean is None:
                rtf.baseline_expected_loss_mean = rtf.expected_loss_mean

            for action in relevant:
                p_eff = prob_eff[action.name]
                s_eff = sev_eff[action.name]

                if action.mitigation_mode in ("probability", "both"):
                    rtf.event_probability = max(
                        0.0,
                        rtf.event_probability * (1.0 - action.probability_reduction * p_eff),
                    )

                if action.mitigation_mode in ("severity", "both"):
                    sev_factor = 1.0 - action.severity_reduction * s_eff
                    rtf.expected_loss_mean *= sev_factor
                    rtf.expected_loss_p50 *= sev_factor
                    rtf.expected_loss_p90 *= sev_factor

                if action.name not in rtf.applied_mitigations:
                    rtf.applied_mitigations.append(action.name)

    # ── Recompute operator_aggregate ──────────────────────────────────────────
    T = adjusted.metadata.forecast_horizon_years
    new_loss_by_type: Dict[str, float] = {rt: 0.0 for rt in RISK_TYPES}
    for sf in adjusted.site_forecasts:
        for rtf in sf.annual_forecasts:
            if rtf.risk_type in new_loss_by_type:
                new_loss_by_type[rtf.risk_type] += rtf.expected_loss_mean

    # Divide by years to get annual average per type
    if T > 0:
        new_loss_by_type = {rt: v / T for rt, v in new_loss_by_type.items()}

    new_total = sum(new_loss_by_type.values())
    old_total = forecast.operator_aggregate.total_expected_annual_loss

    # Update ratio: preserve static baseline denominator via scaling
    old_ratio = forecast.operator_aggregate.c5ai_vs_static_ratio
    new_ratio = old_ratio * (new_total / old_total) if old_total > 0 else old_ratio

    new_fractions: Dict[str, float] = (
        {rt: v / new_total for rt, v in new_loss_by_type.items()}
        if new_total > 0
        else {rt: 0.0 for rt in RISK_TYPES}
    )

    agg = adjusted.operator_aggregate
    agg.baseline_total_expected_annual_loss = old_total
    agg.annual_expected_loss_by_type = new_loss_by_type
    agg.total_expected_annual_loss = new_total
    agg.c5ai_vs_static_ratio = new_ratio
    agg.loss_breakdown_fractions = new_fractions

    # Record which actions were applied in metadata
    adjusted.metadata.applied_mitigations = applied_action_names

    return adjusted
