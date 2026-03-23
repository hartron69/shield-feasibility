"""
PCC Suitability Engine – Automated Recommendation Framework.

Scoring model
-------------
Six weighted criteria are assessed independently on a 0–100 scale.
The composite suitability score drives the verdict and narrative.

Criterion                          Weight   Rationale
────────────────────────────────────────────────────────────────────────────
1. Premium Volume                   22.5%   Captive economics require sufficient mass
2. Loss Stability                   18.0%   Unpredictable losses undermine cell pricing
3. Balance Sheet Strength           18.0%   Must fund SCR from own resources
4. Cost Savings Potential           18.0%   Must justify setup friction and complexity
5. Operational Readiness            13.5%   Governance, commitment horizon, management
6. Biological Operational Readiness 10.0%   C5AI+ data quality, monitoring, bio protocols

Note: Weights 1–5 were scaled by 0.9 to accommodate criterion 6 at 10%.
Total = 22.5 + 18.0 + 18.0 + 18.0 + 13.5 + 10.0 = 100%.

Verdicts
--------
  ≥ 72 : STRONGLY RECOMMENDED
  55–71 : RECOMMENDED
  40–54 : POTENTIALLY SUITABLE – Further Analysis Required
  25–39 : NOT RECOMMENDED
   < 25 : NOT SUITABLE – Captive Economics Not Viable
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from data.input_schema import OperatorInput
from models.monte_carlo import SimulationResults
from models.strategies.base_strategy import StrategyResult
from analysis.cost_analyzer import CostAnalysis
from config.settings import SETTINGS


# ─────────────────────────────────────────────────────────────────────────────
# Result containers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CriterionScore:
    name: str
    weight: float
    raw_score: float        # 0–100
    weighted_score: float   # raw × weight
    finding: str            # One-line quantitative finding
    rationale: str          # Plain-English explanation


@dataclass
class SuitabilityExplanation:
    """
    Explanation and improvement roadmap for a single suitability criterion.

    Attributes
    ----------
    criterion_name : str
    score : float
        Current raw score (0–100).
    gap_to_good : float
        Points needed to reach the "good" threshold (65).  Zero if already there.
    improvement_actions : List[str]
        Specific, actionable steps to improve this criterion's score.
    priority : str
        "critical" | "important" | "nice-to-have"
    timeline : str
        "immediate" | "6-12 months" | "1-3 years"
    impact_on_score : float
        Estimated composite-score uplift (weighted) if actions are taken.
    """
    criterion_name: str
    score: float
    gap_to_good: float
    improvement_actions: List[str]
    priority: str
    timeline: str
    impact_on_score: float


@dataclass
class SuitabilityPath:
    """
    Structured improvement roadmap from current verdict towards RECOMMENDED.

    Attributes
    ----------
    current_verdict : str
    target_verdict : str
    total_gap : float
        Composite score gap to reach target verdict threshold.
    prioritized_actions : List[SuitabilityExplanation]
        Ordered by impact_on_score descending.
    estimated_months_to_target : int
        Rough estimate based on action timelines.
    board_narrative : str
        Plain-language summary suitable for board presentation.
    """
    current_verdict: str
    target_verdict: str
    total_gap: float
    prioritized_actions: List[SuitabilityExplanation]
    estimated_months_to_target: int
    board_narrative: str


@dataclass
class Recommendation:
    verdict: str                   # Short verdict label
    confidence_level: str          # "High" | "Medium" | "Low"
    composite_score: float         # 0–100
    criterion_scores: List[CriterionScore]
    key_strengths: List[str]
    key_barriers: List[str]
    conditions: List[str]          # Prerequisites if recommended
    next_steps: List[str]
    executive_summary: str         # 3–4 sentence board summary
    detail_paragraphs: List[str]   # Section-by-section explanatory text


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class SuitabilityEngine:

    def __init__(
        self,
        operator: OperatorInput,
        sim: SimulationResults,
        strategy_results: Dict[str, StrategyResult],
        cost_analysis: CostAnalysis,
    ):
        self.op = operator
        self.sim = sim
        self.strategies = strategy_results
        self.cost = cost_analysis

    # ── Criterion 1: Premium Volume ────────────────────────────────────────────

    @staticmethod
    def _nok(v: float) -> str:
        """Hjelpefunksjon: formater beløp i NOK millioner."""
        if abs(v) >= 1_000_000_000:
            return f"NOK {v/1_000_000_000:,.1f} Mrd"
        elif abs(v) >= 1_000_000:
            return f"NOK {v/1_000_000:,.1f} M"
        return f"NOK {v:,.0f}"

    def _score_premium_volume(self) -> CriterionScore:
        premium = self.op.current_insurance.annual_premium
        nok = self._nok
        if premium >= 21_000_000:
            raw, finding = 100, f"{nok(premium)}/ar – svært god captive-masse"
        elif premium >= 10_500_000:
            raw, finding = 80, f"{nok(premium)}/ar – god captive-masse"
        elif premium >= 5_250_000:
            raw, finding = 60, f"{nok(premium)}/ar – tilstrekkelig, marginale tall"
        elif premium >= 2_100_000:
            raw, finding = 30, f"{nok(premium)}/ar – under foretrukket terskel"
        else:
            raw, finding = 5, f"{nok(premium)}/ar – utilstrekkelig for levedyktig captive"

        rationale = (
            f"Selskapet betaler {nok(premium)} i arlig forsikringspremie. "
            f"Captive-strukturer krever tilstrekkelig premievolumet til a dekke "
            f"etableringskostnader (~{nok(SETTINGS.pcc_setup_cost)}), lopende forvaltningsavgifter "
            f"(~{nok(SETTINGS.pcc_annual_cell_fee)}/ar) og generere meningsfull besparelse. "
            f"Bransjens nedre grense for PCC-levedyktighet er {nok(SETTINGS.min_premium_for_captive)}+/ar."
        )
        return CriterionScore("Premium Volume", 0.225, raw, raw * 0.225, finding, rationale)

    # ── Criterion 2: Loss Stability ────────────────────────────────────────────

    def _score_loss_stability(self) -> CriterionScore:
        cv = self.sim.std_annual_loss / max(self.sim.mean_annual_loss, 1)
        loss_ratio = self.op.current_insurance.current_loss_ratio

        # For smolt/RAS land-based operators: use per-event CV input + claims-free history.
        # The aggregate CV is inflated by low expected-event frequency (compound Poisson),
        # but individual loss variability (cv_loss_severity) is the relevant stability metric
        # for a captive pricing per-occurrence losses in a controlled RAS environment.
        if getattr(self.op, "facility_type", None) == "smolt":
            cv_input = self.op.risk_params.cv_loss_severity
            ch_years = getattr(self.op, "claims_history_years", 0)
            if cv_input < 0.75 and ch_years >= 7:
                raw = 85
                finding = (f"CV={cv_input:.2f} (per hendelse) – RAS-landbase, "
                           f"{ch_years} år skadefri historikk")
            elif cv_input < 0.75:
                raw = 65
                finding = f"CV={cv_input:.2f} (per hendelse) – RAS-landbase, stabilt tapsmønster"
            elif cv_input < 1.00:
                raw = 40
                finding = f"CV={cv_input:.2f} (per hendelse) – moderat volatilitet RAS"
            else:
                raw = 20
                finding = f"CV={cv_input:.2f} (per hendelse) – høy volatilitet"
            rationale = (
                f"For landbasert RAS-settefisk brukes CV per hendelse ({cv_input:.2f}) "
                f"fremfor aggregert simulerings-CV ({cv:.2f}), siden lavt hendelsestall "
                f"blaser opp aggregert CV i sammensatt Poisson-modell. "
                f"{ch_years} ar skadefri historikk underbygger stabilt tapsmønster."
            )
        else:
            if cv < 0.30:
                raw, finding = 100, f"CV={cv:.2f} – very stable loss experience"
            elif cv < 0.50:
                raw, finding = 80, f"CV={cv:.2f} – stable with manageable volatility"
            elif cv < 0.75:
                raw, finding = 55, f"CV={cv:.2f} – moderate volatility; cell pricing feasible"
            elif cv < 1.00:
                raw, finding = 30, f"CV={cv:.2f} – high volatility; pricing risk elevated"
            else:
                raw, finding = 10, f"CV={cv:.2f} – extreme volatility; captive not suitable"
            rationale = (
                f"Simulated loss coefficient of variation is {cv:.2f} (σ/μ). "
                f"A well-capitalised PCC cell can absorb moderate volatility, but "
                f"extreme loss fluctuations create reserve depletion risk and require "
                f"large capital top-ups. Historical loss ratio of "
                f"{loss_ratio:.0%} provides additional context."
            )
        return CriterionScore("Loss Stability", 0.18, raw, raw * 0.18, finding, rationale)

    # ── Criterion 3: Balance Sheet Strength ────────────────────────────────────

    def _score_balance_sheet(self) -> CriterionScore:
        fin = self.op.financials
        pcc_result = self.strategies.get("PCC Captive Cell")
        required_capital = pcc_result.required_capital if pcc_result else self.sim.var_995

        # Key ratios
        capital_to_equity = required_capital / max(fin.net_equity, 1)
        capital_to_fcf = required_capital / max(fin.free_cash_flow, 1)
        ebitda_margin = fin.ebitda / max(fin.annual_revenue, 1)

        if capital_to_equity < 0.10 and capital_to_fcf < 1.0:
            raw, finding = 100, f"Capital burden = {capital_to_equity:.1%} of equity – very comfortable"
        elif capital_to_equity < 0.20 and capital_to_fcf < 2.0:
            raw, finding = 75, f"Capital burden = {capital_to_equity:.1%} of equity – manageable"
        elif capital_to_equity < 0.35:
            raw, finding = 50, f"Capital burden = {capital_to_equity:.1%} of equity – stretching balance sheet"
        elif capital_to_equity < 0.50:
            raw, finding = 25, f"Capital burden = {capital_to_equity:.1%} of equity – significant constraint"
        else:
            raw, finding = 5, f"Capital burden = {capital_to_equity:.1%} of equity – exceeds capacity"

        nok = self._nok
        rationale = (
            f"Selskapets egenkapital er {nok(fin.net_equity)} og fri kontantstrom "
            f"er {nok(fin.free_cash_flow)}/ar. Estimert startkapitalbehov for en PCC-celle "
            f"er {nok(required_capital)} ({capital_to_equity:.1%} av egenkapital, "
            f"{capital_to_fcf:.1f}x arlig FCF). EBITDA-margin pa {ebitda_margin:.1%} "
            f"gir kontekst for inntjeningskvaliteten."
        )
        return CriterionScore("Balance Sheet Strength", 0.18, raw, raw * 0.18, finding, rationale)

    # ── Criterion 4: Cost Savings Potential ────────────────────────────────────

    def _score_cost_savings(self) -> CriterionScore:
        baseline_cost = self.cost.summaries["Full Insurance"].total_5yr_undiscounted
        pcc_summary = self.cost.summaries.get("PCC Captive Cell")
        if pcc_summary is None:
            return CriterionScore("Cost Savings Potential", 0.20, 0, 0,
                                  "PCC strategy not modelled", "N/A")

        savings_pct = pcc_summary.vs_baseline_savings_pct
        savings_abs = pcc_summary.vs_baseline_savings_5yr

        nok = self._nok
        if savings_pct >= 0.20:
            raw, finding = 100, f"{savings_pct:.1%} besparelse ({nok(savings_abs)}) over 5 ar"
        elif savings_pct >= 0.12:
            raw, finding = 75, f"{savings_pct:.1%} besparelse ({nok(savings_abs)}) over 5 ar"
        elif savings_pct >= 0.06:
            raw, finding = 50, f"{savings_pct:.1%} besparelse ({nok(savings_abs)}) over 5 ar"
        elif savings_pct >= 0.02:
            raw, finding = 25, f"{savings_pct:.1%} besparelse ({nok(savings_abs)}) – marginalt"
        else:
            raw, finding = 5, f"< 2 % besparelse – captive ikke kostnadseffektiv vs. marked"

        if savings_pct >= 0:
            rationale = (
                f"PCC Captive Cell-strategien er beregnet til a spare {nok(savings_abs)} "
                f"({savings_pct:.1%}) sammenlignet med a fortsette med full markedsforsikring over 5 ar. "
                f"Dette reflekterer kombinert fordel av: (a) {SETTINGS.pcc_premium_discount:.0%} "
                f"premierabatt pa beholdt lag, (b) investeringsinntekt pa cellereserver, "
                f"og (c) resultatprovision i ar med gunstig skadeerfaring. "
                f"Etableringskostnad ({nok(SETTINGS.pcc_setup_cost)}) er fratrukket."
            )
        else:
            rationale = (
                f"PCC Captive Cell-strategien er beregnet til a koste {nok(abs(savings_abs))} "
                f"({abs(savings_pct):.1%}) MER enn full markedsforsikring over 5 ar. "
                f"Kostnadsulempen drives primert av gjenforsikringspremien (XL-lag) og "
                f"kapitalmulighetskostnaden, som overstiger premierabatten pa "
                f"{SETTINGS.pcc_premium_discount:.0%}. "
                f"For at PCC skal bli kostnadseffektiv ma enten (a) premievolumet okes, "
                f"(b) retensjonsnivan justeres, eller (c) GjenForsikringsvilkar forbedres."
            )
        return CriterionScore("Cost Savings Potential", 0.18, raw, raw * 0.18, finding, rationale)

    # ── Criterion 5: Operational Readiness ─────────────────────────────────────

    def _score_operational_readiness(self) -> CriterionScore:
        scores = []
        details = []

        # Commitment horizon
        if self.op.management_commitment_years >= 7:
            scores.append(100); details.append(f"{self.op.management_commitment_years}-yr commitment (excellent)")
        elif self.op.management_commitment_years >= 5:
            scores.append(70); details.append(f"{self.op.management_commitment_years}-yr commitment (adequate)")
        else:
            scores.append(20); details.append(f"{self.op.management_commitment_years}-yr commitment (too short)")

        # Governance maturity
        gov_map = {"mature": 100, "developing": 65, "basic": 30}
        gov_score = gov_map.get(self.op.governance_maturity, 30)
        scores.append(gov_score)
        details.append(f"Governance: {self.op.governance_maturity} ({gov_score}/100)")

        # Risk manager
        if self.op.has_risk_manager:
            scores.append(100); details.append("Dedicated risk manager: yes")
        else:
            scores.append(40); details.append("Dedicated risk manager: no (gap)")

        # Years of operation
        yrs = self.op.financials.years_in_operation
        if yrs >= 10:
            scores.append(90); details.append(f"{yrs} yrs in operation (experienced)")
        elif yrs >= 5:
            scores.append(65); details.append(f"{yrs} yrs in operation (established)")
        else:
            scores.append(30); details.append(f"{yrs} yrs in operation (early-stage)")

        # Capital willingness
        if self.op.willing_to_provide_capital:
            scores.append(100); details.append("Willing to capitalise: yes")
        else:
            scores.append(0); details.append("Willing to capitalise: no – BLOCKER")

        raw = sum(scores) / len(scores)
        finding = " | ".join(details[:2])  # Top two for display

        rationale = (
            f"Operational readiness is assessed across five sub-factors: management "
            f"commitment horizon ({self.op.management_commitment_years} years), governance "
            f"maturity ('{self.op.governance_maturity}'), risk management function "
            f"({'present' if self.op.has_risk_manager else 'absent'}), operational track "
            f"record ({self.op.financials.years_in_operation} years), and willingness to "
            f"provide cell capital ({'yes' if self.op.willing_to_provide_capital else 'no'})."
        )
        return CriterionScore("Operational Readiness", 0.135, raw, raw * 0.135, finding, rationale)

    # ── Criterion 6: Biological Operational Readiness ──────────────────────────

    def _score_bio_readiness(self) -> CriterionScore:
        """
        Score the operator's biological risk management readiness.

        Draws from three sources (in priority order):
          1. operator.bio_readiness_score (explicit override, 0–100)
          2. C5AI+ data quality flag from the loaded forecast (if available)
          3. Proxy from has_risk_manager and governance_maturity
        """
        nok = self._nok

        # Source 1: Explicit operator score
        explicit = getattr(self.op, "bio_readiness_score", None)
        if explicit is not None:
            raw = float(max(0, min(100, explicit)))
            if raw >= 80:
                finding = f"Bio readiness score: {int(raw)}/100 – strong monitoring capability"
            elif raw >= 60:
                finding = f"Bio readiness score: {int(raw)}/100 – adequate protocols in place"
            elif raw >= 40:
                finding = f"Bio readiness score: {int(raw)}/100 – basic capability, gaps present"
            else:
                finding = f"Bio readiness score: {int(raw)}/100 – limited biological risk management"
            source = "explicit operator input"
        else:
            # Source 2: C5AI+ data quality (if forecast was loaded)
            c5ai_quality = self._get_c5ai_data_quality()
            if c5ai_quality is not None:
                quality_map = {
                    "SUFFICIENT": (85, "C5AI+ data: SUFFICIENT – robust monitoring data available"),
                    "LIMITED":    (55, "C5AI+ data: LIMITED – partial monitoring data available"),
                    "POOR":       (30, "C5AI+ data: POOR – sparse monitoring data"),
                    "PRIOR_ONLY": (15, "C5AI+ data: PRIOR_ONLY – no site-specific data available"),
                }
                raw, finding = quality_map.get(c5ai_quality, (20, f"C5AI+ data quality: {c5ai_quality}"))
                source = f"C5AI+ data quality ({c5ai_quality})"
            else:
                # Source 3a: Smolt — claims-free history is primary indicator
                if getattr(self.op, "facility_type", None) == "smolt":
                    ch_years = getattr(self.op, "claims_history_years", 0)
                    if ch_years >= 10:
                        raw = 90.0
                    elif ch_years >= 7:
                        raw = 75.0
                    elif ch_years >= 5:
                        raw = 60.0
                    elif ch_years >= 3:
                        raw = 40.0
                    else:
                        raw = 20.0
                    finding = (
                        f"Smolt: {ch_years} år skadefri historikk ({int(raw)}/100)"
                    )
                    source = f"claims_history ({ch_years} år)"
                else:
                    # Source 3b: Governance / risk manager proxy (sea-based)
                    score_parts = []
                    if self.op.has_risk_manager:
                        score_parts.append(60)
                    else:
                        score_parts.append(20)
                    gov_bio = {"mature": 80, "developing": 50, "basic": 20}
                    score_parts.append(gov_bio.get(self.op.governance_maturity, 20))
                    raw = float(sum(score_parts) / len(score_parts))
                    finding = (
                        f"Proxy: risk_manager={'yes' if self.op.has_risk_manager else 'no'}, "
                        f"governance='{self.op.governance_maturity}'"
                    )
                    source = "proxy (no C5AI+ data)"

        rationale = (
            f"Biologisk operasjonell beredskap er vurdert basert pa {source}. "
            f"Akvakultur-operatorer med gode overvakingssystemer, protokoller for biologisk "
            f"respons og kompetanse pa HAB/lus/patogenhendelser er bedre posisjonert til a "
            f"stabilisere tapsutviklingen og dra nytte av PCC-strukturens prisdisiplin. "
            f"Installering av C5AI+ og biologisk overvakningsdata vil forbedre denne scoren."
        )
        return CriterionScore(
            "Biologisk Operasjonell Beredskap", 0.10, raw, raw * 0.10, finding, rationale
        )

    def _get_c5ai_data_quality(self):
        """Extract overall data quality from C5AI+ forecast if loaded."""
        c5ai_path = getattr(self.op, "c5ai_forecast_path", None)
        if not c5ai_path:
            return None
        try:
            from c5ai_plus.export.forecast_exporter import ForecastExporter
            forecast = ForecastExporter.load(c5ai_path)
            return forecast.metadata.overall_data_quality
        except Exception:
            return None

    # ── Mitigated Score Estimate ───────────────────────────────────────────────

    # Smolt-specific operational mitigations that can improve readiness criteria.
    # Map: action_id → {criterion_name: max_raw_score_uplift}
    # Uplifts are additive, bounded at 100, and only applied when the action is
    # present in selected_action_ids.  Rationale for each cap is documented inline.
    _SMOLT_READINESS_UPLIFTS: Dict[str, Dict[str, float]] = {
        # RAS operator certification: water chemistry, alarm response, emergency
        # procedures.  Directly proxies the "training compliance" and "competence"
        # sub-factors of Operational Readiness.  Cap at 8 pts (≈ one sub-factor
        # tier upgrade on 5-factor average).
        "smolt_staff_training": {
            "Operational Readiness": 8.0,
        },
        # Documented ERP with drill schedule and supplier SLAs.  Improves both
        # the governance sub-factor of Operational Readiness and the biological
        # response capability that Biological Readiness measures.  Cap at 5 pts
        # each (moderate signal; plan alone does not substitute for system upgrades).
        "smolt_emergency_plan": {
            "Operational Readiness":            5.0,
            "Biologisk Operasjonell Beredskap": 5.0,
        },
        # 24/7 O₂/CO₂/pH/flow/power alarms with automated call-out.  Provides the
        # continuous monitoring capability that the bio-readiness criterion rewards.
        # Cap at 5 pts (monitoring capability, not biological treatment competence).
        "smolt_alarm_system": {
            "Biologisk Operasjonell Beredskap": 5.0,
        },
    }

    def estimate_mitigated_score(
        self,
        baseline: "Recommendation",
        mit_e_loss: float,
        mit_scr: float,
        selected_action_ids: Optional[List[str]] = None,
    ) -> "Tuple[float, str, List[CriterionScore]]":
        """
        Estimate composite suitability score for the mitigated scenario.

        Criteria recomputed
        -------------------
        * Loss Stability
            - Sea-based: aggregate CV re-estimated proportional to loss reduction.
            - Smolt/RAS: per-event severity CV is unchanged by mitigation (the
              smolt baseline uses cv_loss_severity, not aggregate CV, because
              compound-Poisson zero-inflation inflates aggregate CV regardless of
              mitigation effectiveness).  The baseline Loss Stability score is
              therefore carried forward unchanged.  This is the **correct**
              treatment: mitigation reduces event frequency/severity, not the
              shape of per-event severity distributions.
        * Balance Sheet Strength — capital burden recomputed using *mit_scr*.
        * Operational Readiness / Biologisk Operasjonell Beredskap (smolt only)
            — bounded additive uplift when specific smolt operational mitigations
            are selected (see _SMOLT_READINESS_UPLIFTS).

        Parameters
        ----------
        baseline : Recommendation
            The result of ``assess()`` for the un-mitigated scenario.
        mit_e_loss : float
            Expected annual loss after mitigation (NOK).
        mit_scr : float
            Solvency Capital Requirement after mitigation (NOK).
        selected_action_ids : list of str, optional
            IDs of the selected mitigation actions.  Used to determine smolt
            readiness uplifts.  If None, no uplift is applied.

        Returns
        -------
        (mitigated_composite_score, mitigated_verdict, mitigated_criterion_scores)
        """
        is_smolt  = getattr(self.op, "facility_type", None) == "smolt"
        actions   = set(selected_action_ids or [])
        new_criteria: List[CriterionScore] = []
        base_mean = max(self.sim.mean_annual_loss, 1.0)
        base_std  = self.sim.std_annual_loss

        for c in baseline.criterion_scores:

            if c.name == "Loss Stability":
                if is_smolt:
                    # BUG-FIX: smolt baseline uses per-event CV (cv_loss_severity),
                    # not aggregate simulated CV.  Aggregate CV for compound-Poisson
                    # with λ≈0.08–0.40/yr inflates to 1.5–4.0+ due to zero-inflation,
                    # regardless of mitigation.  Using it here would cause a large
                    # spurious drop in this criterion (e.g., raw 85→10) even when
                    # loss and SCR improve by 30–50%.
                    #
                    # Mitigation reduces event frequency and/or per-event severity,
                    # but does NOT change the shape of the per-event loss distribution
                    # (cv_loss_severity).  The claims-free history (ch_years) also
                    # does not change within one reporting period.
                    #
                    # Therefore: carry Loss Stability forward from baseline unchanged.
                    cv_label = getattr(self.op.risk_params, "cv_loss_severity", None)
                    new_criteria.append(CriterionScore(
                        c.name, c.weight, c.raw_score, c.weighted_score,
                        (f"CV={cv_label:.2f} (per hendelse, uendret av tiltak)"
                         if cv_label is not None else "uendret av tiltak"),
                        c.rationale,
                    ))
                else:
                    # Sea-based: aggregate CV re-estimated proportional to
                    # loss reduction.  Variance scales approximately with mean
                    # (conservative — mitigation often reduces tail
                    # disproportionately, so true CV improvement may be larger).
                    loss_ratio = mit_e_loss / base_mean if base_mean > 0 else 1.0
                    base_cv    = base_std / base_mean
                    mit_cv     = base_cv * (loss_ratio ** 0.5)

                    if mit_cv < 0.30:
                        raw = 100
                    elif mit_cv < 0.50:
                        raw = 80
                    elif mit_cv < 0.75:
                        raw = 55
                    elif mit_cv < 1.00:
                        raw = 30
                    else:
                        raw = 10

                    new_criteria.append(CriterionScore(
                        c.name, c.weight, raw, raw * c.weight,
                        f"CV≈{mit_cv:.2f} (mitigated estimate)",
                        c.rationale,
                    ))

            elif c.name == "Balance Sheet Strength":
                fin = self.op.financials
                capital_to_equity = mit_scr / max(fin.net_equity, 1)
                capital_to_fcf    = mit_scr / max(fin.free_cash_flow, 1)

                if capital_to_equity < 0.10 and capital_to_fcf < 1.0:
                    raw = 100
                elif capital_to_equity < 0.20 and capital_to_fcf < 2.0:
                    raw = 75
                elif capital_to_equity < 0.35:
                    raw = 50
                elif capital_to_equity < 0.50:
                    raw = 25
                else:
                    raw = 5

                new_criteria.append(CriterionScore(
                    c.name, c.weight, raw, raw * c.weight,
                    f"Capital burden = {capital_to_equity:.1%} of equity (mitigated)",
                    c.rationale,
                ))

            else:
                # For smolt operators, specific operational mitigations can improve
                # Operational Readiness and Biologisk Operasjonell Beredskap.
                # Each uplift is bounded (see _SMOLT_READINESS_UPLIFTS docstring).
                if is_smolt and c.name in (
                    "Operational Readiness", "Biologisk Operasjonell Beredskap"
                ):
                    uplift = 0.0
                    for action_id, crit_map in self._SMOLT_READINESS_UPLIFTS.items():
                        if action_id in actions and c.name in crit_map:
                            uplift += crit_map[c.name]
                    if uplift > 0.0:
                        raw = min(c.raw_score + uplift, 100.0)
                        new_criteria.append(CriterionScore(
                            c.name, c.weight, raw, raw * c.weight,
                            f"{c.finding} (+{uplift:.0f} pts fra tiltak)",
                            c.rationale,
                        ))
                        continue
                new_criteria.append(c)

        composite = sum(c.weighted_score for c in new_criteria)

        # Apply same verdict thresholds as assess()
        if composite >= 72:
            verdict = "STRONGLY RECOMMENDED"
        elif composite >= 55:
            verdict = "RECOMMENDED"
        elif composite >= 40:
            verdict = "POTENTIALLY SUITABLE"
        elif composite >= 25:
            verdict = "NOT RECOMMENDED"
        else:
            verdict = "NOT SUITABLE"

        # Carry forward the hard cost gate from baseline (re-running the full
        # cost model is not needed — the gate depends on strategy costs, which
        # mitigation does not change).
        VERDICT_ORDER = [
            "STRONGLY RECOMMENDED", "RECOMMENDED",
            "POTENTIALLY SUITABLE", "NOT RECOMMENDED", "NOT SUITABLE",
        ]
        pcc_summary = self.cost.summaries.get("PCC Captive Cell")
        fi_summary  = self.cost.summaries.get("Full Insurance")
        try:
            fi_total  = float(fi_summary.total_5yr_undiscounted) if fi_summary else 0.0
            pcc_total = float(pcc_summary.total_5yr_undiscounted) if pcc_summary else 0.0
            excess = (pcc_total - fi_total) / fi_total if fi_total > 0 else 0.0
        except (TypeError, ValueError, AttributeError):
            excess = 0.0

        if excess > 0.15:
            if VERDICT_ORDER.index(verdict) < VERDICT_ORDER.index("NOT RECOMMENDED"):
                verdict = "NOT RECOMMENDED"
        elif excess > 0.05:
            if VERDICT_ORDER.index(verdict) < VERDICT_ORDER.index("POTENTIALLY SUITABLE"):
                verdict = "POTENTIALLY SUITABLE"

        return round(composite, 3), verdict, new_criteria

    # ── Aggregate & Recommend ──────────────────────────────────────────────────

    def assess(self) -> Recommendation:
        criteria = [
            self._score_premium_volume(),
            self._score_loss_stability(),
            self._score_balance_sheet(),
            self._score_cost_savings(),
            self._score_operational_readiness(),
            self._score_bio_readiness(),
        ]

        composite = sum(c.weighted_score for c in criteria)

        # Verdict
        if composite >= 72:
            verdict = "STRONGLY RECOMMENDED"
            confidence = "High"
        elif composite >= 55:
            verdict = "RECOMMENDED"
            confidence = "Medium"
        elif composite >= 40:
            verdict = "POTENTIALLY SUITABLE"
            confidence = "Low"
        elif composite >= 25:
            verdict = "NOT RECOMMENDED"
            confidence = "Medium"
        else:
            verdict = "NOT SUITABLE"
            confidence = "High"

        # Strengths and barriers (criteria scoring > 60 / < 40)
        strengths = [c.name for c in criteria if c.raw_score >= 65]
        barriers = [c.name for c in criteria if c.raw_score < 40]

        # ── Hard cost-comparison gate ──────────────────────────────────────────
        # Even a well-prepared operator should not be recommended for standalone
        # PCC if the 5-yr TCOR is materially above full market insurance.
        # The weighted score alone is insufficient because other criteria can
        # compensate for poor cost savings, leading to misleading verdicts.
        pcc_summary = self.cost.summaries.get("PCC Captive Cell")
        fi_summary = self.cost.summaries.get("Full Insurance")
        pcc_cost_excess_pct: float = 0.0
        try:
            fi_total = float(fi_summary.total_5yr_undiscounted) if fi_summary else 0.0
            pcc_total = float(pcc_summary.total_5yr_undiscounted) if pcc_summary else 0.0
            if fi_total > 0:
                pcc_cost_excess_pct = (pcc_total - fi_total) / fi_total
        except (TypeError, ValueError, AttributeError):
            pcc_cost_excess_pct = 0.0

        VERDICT_ORDER = [
            "STRONGLY RECOMMENDED",
            "RECOMMENDED",
            "POTENTIALLY SUITABLE",
            "NOT RECOMMENDED",
            "NOT SUITABLE",
        ]

        if pcc_cost_excess_pct > 0.05:
            # PCC costs >5% more than full insurance: add cost barrier and cap verdict
            cost_barrier = (
                f"PCC 5-yr TCOR is {pcc_cost_excess_pct:.0%} above full market insurance. "
                "Cost savings must be positive before direct PCC entry is advisable."
            )
            if cost_barrier not in barriers:
                barriers.append(cost_barrier)
            # Cap verdict at max POTENTIALLY SUITABLE
            if VERDICT_ORDER.index(verdict) < VERDICT_ORDER.index("POTENTIALLY SUITABLE"):
                verdict = "POTENTIALLY SUITABLE"
                confidence = "Medium"

        if pcc_cost_excess_pct > 0.15:
            # PCC costs >15% more than full insurance: hard cap at NOT RECOMMENDED
            if VERDICT_ORDER.index(verdict) < VERDICT_ORDER.index("NOT RECOMMENDED"):
                verdict = "NOT RECOMMENDED"
                confidence = "High"

        # Conditions
        conditions = []
        if self.op.financials.free_cash_flow < self.sim.var_995 * 0.5:
            conditions.append("Arrange committed credit facility to backstop cell reserves")
        if not self.op.has_risk_manager:
            conditions.append("Appoint a qualified Risk Manager or engage an external captive manager")
        if self.op.governance_maturity == "basic":
            conditions.append("Establish formal risk governance framework prior to cell formation")
        if self.op.management_commitment_years < 5:
            conditions.append("Extend commitment horizon to minimum 5 years for positive NPV")

        pcc_result = self.strategies.get("PCC Captive Cell")
        if pcc_result and pcc_result.required_capital > self.op.financials.free_cash_flow:
            gap = pcc_result.required_capital - self.op.financials.free_cash_flow
            conditions.append(
                f"Sikre {self._nok(gap)} i tilleggskapital for celleopprettelse"
            )

        # Next steps
        next_steps = self._build_next_steps(verdict, conditions)

        # Executive summary
        exec_summary = self._build_exec_summary(verdict, composite, criteria)

        # Detail paragraphs
        detail_paras = [c.rationale for c in criteria]

        return Recommendation(
            verdict=verdict,
            confidence_level=confidence,
            composite_score=composite,
            criterion_scores=criteria,
            key_strengths=strengths,
            key_barriers=barriers,
            conditions=conditions,
            next_steps=next_steps,
            executive_summary=exec_summary,
            detail_paragraphs=detail_paras,
        )

    def explain(self) -> SuitabilityPath:
        """
        Generate a structured improvement roadmap towards a RECOMMENDED verdict.

        Returns
        -------
        SuitabilityPath
            Prioritised list of actions and board-level narrative.
        """
        recommendation = self.assess()
        current_score = recommendation.composite_score
        current_verdict = recommendation.verdict

        # Determine target verdict and gap
        if current_score >= 55:
            target_verdict = "STRONGLY RECOMMENDED"
            target_threshold = 72.0
        elif current_score >= 40:
            target_verdict = "RECOMMENDED"
            target_threshold = 55.0
        else:
            target_verdict = "RECOMMENDED"
            target_threshold = 55.0

        total_gap = max(0.0, target_threshold - current_score)

        # Build per-criterion explanations
        explanations: List[SuitabilityExplanation] = []
        for criterion in recommendation.criterion_scores:
            gap = max(0.0, 65.0 - criterion.raw_score)
            actions = self._actions_for_criterion(criterion)
            priority = self._priority_for_score(criterion.raw_score)
            timeline = self._timeline_for_priority(priority)
            # Weighted impact: closing gap to 65 raises composite by gap × weight
            impact = gap * criterion.weight
            explanations.append(SuitabilityExplanation(
                criterion_name=criterion.name,
                score=criterion.raw_score,
                gap_to_good=gap,
                improvement_actions=actions,
                priority=priority,
                timeline=timeline,
                impact_on_score=round(impact, 2),
            ))

        # Sort by impact descending
        explanations.sort(key=lambda e: e.impact_on_score, reverse=True)

        # Estimate months to target based on dominant timeline
        months = self._estimate_months(explanations, total_gap)

        narrative = self._board_narrative(
            current_verdict, target_verdict, current_score, total_gap,
            explanations[:3]
        )

        return SuitabilityPath(
            current_verdict=current_verdict,
            target_verdict=target_verdict,
            total_gap=round(total_gap, 1),
            prioritized_actions=explanations,
            estimated_months_to_target=months,
            board_narrative=narrative,
        )

    @staticmethod
    def _actions_for_criterion(criterion: "CriterionScore") -> List[str]:
        """Return concrete improvement actions for a low-scoring criterion."""
        name = criterion.name
        score = criterion.raw_score

        action_map: Dict[str, List[str]] = {
            "Premium Volume": [
                "Expand insured asset base by adding new sites or biomass capacity",
                "Aggregate group-level premium into a single captive programme",
                "Review coverage lines: add Business Interruption and Liability",
            ],
            "Loss Stability": [
                "Implement structured loss-prevention programme (nets, sensors, protocols)",
                "Invest in environmental monitoring to reduce HAB/lice surprise events",
                "Commission actuarial review of loss frequency and severity assumptions",
            ],
            "Balance Sheet Strength": [
                "Arrange a committed credit facility to backstop cell reserves",
                "Reduce capital burden by increasing per-occurrence retention layer",
                "Improve EBITDA margin through operational efficiency initiatives",
            ],
            "Cost Savings Potential": [
                "Negotiate multi-year premium lock-in to reduce market rate exposure",
                "Increase per-occurrence retention to lower ceded premium",
                "Review captive investment mandate to optimise reserve yield",
            ],
            "Operational Readiness": [
                "Appoint a dedicated Risk Manager or external captive manager",
                "Formalise risk governance framework with Board Risk Committee",
                "Extend management commitment horizon to minimum 7 years",
                "Confirm capital commitment in writing from Board",
            ],
            "Biologisk Operasjonell Beredskap": [
                "Deploy C5AI+ biological monitoring system on all sites",
                "Establish formal biological emergency response protocol",
                "Train operations staff in early HAB/lice/disease detection",
                "Integrate Barentswatch and Havforskningsinstituttet data feeds",
            ],
        }

        actions = action_map.get(name, ["Review and improve this criterion"])
        # For high-scoring criteria return fewer actions
        if score >= 65:
            return actions[:1]
        return actions

    @staticmethod
    def _priority_for_score(score: float) -> str:
        if score < 30:
            return "critical"
        if score < 55:
            return "important"
        return "nice-to-have"

    @staticmethod
    def _timeline_for_priority(priority: str) -> str:
        return {
            "critical": "immediate",
            "important": "6-12 months",
            "nice-to-have": "1-3 years",
        }.get(priority, "6-12 months")

    @staticmethod
    def _estimate_months(
        explanations: List["SuitabilityExplanation"], total_gap: float
    ) -> int:
        """Rough estimate: dominated by the longest timeline of impactful actions."""
        if total_gap <= 0:
            return 0
        critical = any(e.priority == "critical" for e in explanations if e.gap_to_good > 0)
        important = any(e.priority == "important" for e in explanations if e.gap_to_good > 0)
        if critical:
            return 18
        if important:
            return 12
        return 6

    def _board_narrative(
        self,
        current_verdict: str,
        target_verdict: str,
        current_score: float,
        gap: float,
        top_actions: List["SuitabilityExplanation"],
    ) -> str:
        op = self.op
        action_lines = "; ".join(
            f"{a.criterion_name}: {a.improvement_actions[0]}"
            for a in top_actions
            if a.improvement_actions
        )
        return (
            f"{op.name} oppnar for oyeblikket '{current_verdict}' med en samlet score pa "
            f"{current_score:.1f}/100. For a na '{target_verdict}' matte scoren okes med "
            f"{gap:.1f} poeng. De tre viktigste forbedringsomradene er: {action_lines}. "
            f"Med malrettet innsats pa disse omradene er det realistisk a oppna "
            f"'{target_verdict}'-status innen 12–18 maneder."
        )

    def _build_next_steps(self, verdict: str, conditions: List[str]) -> List[str]:
        steps = []
        if "RECOMMENDED" in verdict or "SUITABLE" in verdict:
            steps += [
                "Appoint a captive manager and select PCC domicile (recommend: "
                + (self.op.captive_domicile_preference or "Guernsey or Cayman Islands") + ")",
                "Commission a formal actuarial pricing study for the retained layer",
                "Identify fronting insurer and agree programme structure",
                "Prepare cell formation documents and regulatory application",
                "Establish investment mandate for cell reserves",
                "Brief Board and Finance Committee on capital commitment timeline",
            ]
            if conditions:
                steps.insert(0, "Resolve prerequisite conditions listed above before proceeding")
        else:
            steps += [
                "Re-evaluate captive suitability in 2–3 years as premium volume grows",
                "Consider hybrid (large-deductible) structure as intermediate step",
                "Review loss control programmes to improve loss stability",
                "Benchmark market premium rates annually to validate full-insurance value",
            ]
        return steps

    def _build_exec_summary(
        self, verdict: str, score: float, criteria: List[CriterionScore]
    ) -> str:
        op = self.op
        pcc_sum = self.cost.summaries.get("PCC Captive Cell")
        savings_str = ""
        if pcc_sum:
            savings_str = (
                f"PCC Captive Cell-alternativet er anslatt til a generere "
                f"{self._nok(pcc_sum.vs_baseline_savings_5yr)} i 5-ars besparelser "
                f"({pcc_sum.vs_baseline_savings_pct:.1%} vs. full markedsforsikring). "
            )

        return (
            f"{op.name} er vurdert for Protected Cell Company (PCC) captive-egnethet "
            f"ved hjelp av en vektet femkriteriemodell. Samlet score er "
            f"{score:.1f}/100, noe som gir konklusjonen '{verdict}'. "
            f"{savings_str}"
            f"Viktigste styrker: {', '.join([c.name for c in criteria if c.raw_score >= 65]) or 'ingen identifisert'}. "
            f"Vesentlige hindringer som ma loeses for celleopprettelse: "
            f"{', '.join([c.name for c in criteria if c.raw_score < 40]) or 'ingen identifisert'}. "
            f"Vurderingen er basert pa Monte Carlo-simulering av {self.sim.n_simulations:,} "
            f"scenarier over en {self.sim.projection_years}-ars prognosehorisont."
        )
