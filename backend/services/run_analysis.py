"""
Full analysis pipeline for the Shield Risk Platform GUI.

Mirrors the 9-step pipeline from main.py but returns structured data
instead of printing to stdout or generating a file unconditionally.
"""

from __future__ import annotations

import base64
import io
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from backend.schemas import (
    AllocationSummary,
    ComparisonBlock,
    FeasibilityRequest,
    FeasibilityResponse,
    KPISummary,
    MetadataBlock,
    PoolingMemberStats,
    PoolingResult,
    ReportBlock,
    ScenarioBlock,
)
from backend.services.history_analytics import build_historical_loss_summary
from backend.services.operator_builder import build_operator_input, load_template_history


from data.input_schema import OperatorInput

_REPORTS_DIR = Path(__file__).resolve().parents[2] / "backend" / "static" / "reports"


def _buf_to_b64(buf: io.BytesIO) -> str:
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _charts_to_b64(charts: Dict[str, io.BytesIO]) -> Dict[str, str]:
    return {k: _buf_to_b64(v) for k, v in charts.items()}


def _build_smolt_history_summary(
    claims_history_years: int,
    total_claims_paid_nok: float,
    historical_losses: list | None = None,
    use_history_calibration: bool = False,
) -> "HistoricalLossSummary":
    """Build a HistoricalLossSummary from operator-declared smolt claims data.

    For claims-free operators (total_claims_paid_nok == 0) the observation
    window is preserved so the LossHistoryTab can show years monitored / events.
    When claims exist they are recorded as a single aggregate mortality event.
    """
    from backend.schemas import HistoricalLossSummary, HistoryEventRow, HistoricalDomainSummary
    from backend.services.history_analytics import build_smolt_self_handled_summary

    # When detailed self-handled logs are provided, delegate to the richer analytics
    if historical_losses:
        return build_smolt_self_handled_summary(
            historical_losses,
            use_history_calibration=use_history_calibration,
        )

    if claims_history_years <= 0:
        # No observation window — return completely empty summary
        return HistoricalLossSummary(
            history_loaded=False, history_source="smolt_operator_declared",
            record_count=0, years_covered=[], n_years_observed=0,
            portfolio_total_gross=0.0, portfolio_total_insured=0.0,
            portfolio_total_retained=0.0, portfolio_mean_severity=0.0,
            portfolio_events_per_year=0.0, domain_summaries=[], records=[],
            calibration_active=False, calibration_source="none",
            calibration_mode="none", calibrated_parameters={},
        )

    current_year = 2026
    first_year   = current_year - claims_history_years
    years_covered = list(range(first_year + 1, current_year + 1))

    if total_claims_paid_nok <= 0:
        # Claims-free: observation window with zero events
        return HistoricalLossSummary(
            history_loaded=True, history_source="smolt_operator_declared",
            record_count=0, years_covered=years_covered,
            n_years_observed=claims_history_years,
            portfolio_total_gross=0.0, portfolio_total_insured=0.0,
            portfolio_total_retained=0.0, portfolio_mean_severity=0.0,
            portfolio_events_per_year=0.0, domain_summaries=[], records=[],
            calibration_active=False, calibration_source="none",
            calibration_mode="none", calibrated_parameters={},
        )

    # Claims exist: one aggregate biological event at mid-window
    mid_year     = first_year + claims_history_years // 2
    insured_loss = total_claims_paid_nok               # declared = insured
    retained     = insured_loss * 0.10                 # assume 10% deductible

    row = HistoryEventRow(
        year=mid_year,
        event_type="mortality",
        domain="biological",
        gross_loss=insured_loss,
        insured_loss=insured_loss,
        retained_loss=retained,
    )
    domain_summary = HistoricalDomainSummary(
        domain="biological",
        event_count=1,
        total_gross_loss=insured_loss,
        total_insured_loss=insured_loss,
        total_retained_loss=retained,
        mean_severity=insured_loss,
        events_per_year=1.0 / claims_history_years,
        loss_share_pct=100.0,
        years_with_events=[mid_year],
    )
    return HistoricalLossSummary(
        history_loaded=True, history_source="smolt_operator_declared",
        record_count=1, years_covered=years_covered,
        n_years_observed=claims_history_years,
        portfolio_total_gross=insured_loss,
        portfolio_total_insured=insured_loss,
        portfolio_total_retained=retained,
        portfolio_mean_severity=insured_loss,
        portfolio_events_per_year=1.0 / claims_history_years,
        domain_summaries=[domain_summary],
        records=[row],
        calibration_active=False, calibration_source="none",
        calibration_mode="none", calibrated_parameters={},
    )


def run_feasibility_analysis(
    op_input: OperatorInput,
    model_settings: "ModelSettingsInput",
    allocation_summary: Optional[AllocationSummary] = None,
    selected_actions: Optional[List[str]] = None,
    claims_history_years: int = 0,
    total_claims_paid_nok: float = 0.0,
    historical_losses: list | None = None,
    use_history_calibration: bool = False,
) -> FeasibilityResponse:
    """
    Run PCC pipeline steps 2–9 on a pre-built OperatorInput.

    Used by alternative entry points (e.g. smolt route) that build the
    operator object themselves rather than using the GUI operator builder.
    Mitigation and pooling are not applied; use run_feasibility_service for
    those features.
    """
    import numpy as np

    model = model_settings

    # Step 2: Domain correlation
    from models.domain_correlation import (
        DomainCorrelationMatrix,
        PREDEFINED_DOMAIN_CORRELATIONS,
    )
    domain_corr = PREDEFINED_DOMAIN_CORRELATIONS.get(model.domain_correlation)
    if domain_corr is None:
        domain_corr = DomainCorrelationMatrix.expert_default()

    # Step 3: Monte Carlo
    from models.monte_carlo import MonteCarloEngine
    engine = MonteCarloEngine(op_input, n_simulations=model.n_simulations, domain_correlation=domain_corr)
    sim = engine.run()

    # Step 4: Strategy models
    from models.strategies.full_insurance import FullInsuranceStrategy
    from models.strategies.hybrid import HybridStrategy
    from models.strategies.pcc_captive import PCCCaptiveStrategy
    from models.strategies.self_insurance import SelfInsuranceStrategy
    from models.pcc_economics import PCCAssumptions

    # Smolt: pure captive structure (no RI layer) — land-based RAS with claims-free history.
    # Low formation/admin fees reflect simplified regulatory structure vs. marine operations.
    # Expected losses are low (claims-free discount applied), so RI burning cost ≈ 0;
    # savings come primarily from the 22% premium discount and investment income on reserves.
    smolt_assump = (
        PCCAssumptions(
            ri_loading_factor=1.75,
            premium_discount_pct=0.22,
            reinsurance_limit_nok=0.0,   # pure captive — no external RI layer
            formation_cost_nok=500_000,  # simpler land-based structure
            admin_fee_nok=350_000,       # lean captive admin for single-operator cell
        )
        if getattr(op_input, "facility_type", None) == "smolt" else None
    )

    strategies = {
        "Full Insurance":   FullInsuranceStrategy(op_input, sim),
        "Hybrid":           HybridStrategy(op_input, sim),
        "PCC Captive Cell": PCCCaptiveStrategy(op_input, sim, pcc_assumptions=smolt_assump),
        "Self-Insurance":   SelfInsuranceStrategy(op_input, sim),
    }
    strategy_results = {name: s.calculate() for name, s in strategies.items()}

    # Step 5: SCR, cost, volatility, suitability
    from analysis.scr_calculator import SCRCalculator
    from analysis.cost_analyzer import CostAnalyzer
    from analysis.volatility_metrics import VolatilityAnalyzer
    from analysis.suitability_engine import SuitabilityEngine

    scr_results    = SCRCalculator(sim, strategy_results).calculate_all()
    cost_analysis  = CostAnalyzer(op_input, strategy_results).analyze()
    vol_metrics    = VolatilityAnalyzer(sim, strategy_results).analyze()
    suitability    = SuitabilityEngine(op_input, sim, strategy_results, cost_analysis)
    recommendation = suitability.assess()

    # Step 6: Charts
    from reporting.chart_generator import generate_all_charts
    from reporting.correlated_risk_analytics import build_correlated_risk_summary

    corr_summary = build_correlated_risk_summary(sim.annual_losses, sim.domain_loss_breakdown)
    raw_charts   = generate_all_charts(
        sim, strategy_results, scr_results, cost_analysis, vol_metrics, recommendation,
        correlated_risk_summary=corr_summary,
        domain_correlation=domain_corr,
    )
    b64_charts = _charts_to_b64(raw_charts)

    # Step 7: Baseline KPI block
    pcc_scr      = scr_results.get("PCC Captive Cell")
    baseline_scr = pcc_scr.scr_net if pcc_scr else sim.var_995

    annual_losses  = sim.annual_losses   # shape (N, T)
    per_sim_loss   = annual_losses.sum(axis=1) / annual_losses.shape[1]
    baseline_e_loss = float(per_sim_loss.mean())
    baseline_p95   = float(np.percentile(per_sim_loss, 95))
    baseline_p99   = float(np.percentile(per_sim_loss, 99))

    baseline_kpi = KPISummary(
        expected_annual_loss=baseline_e_loss,
        p95_loss=baseline_p95,
        p99_loss=baseline_p99,
        scr=baseline_scr,
        recommended_strategy=recommendation.verdict,
        verdict=recommendation.verdict,
        composite_score=recommendation.composite_score,
        confidence_level=recommendation.confidence_level,
    )
    criterion_scores = [
        {
            "name": c.name,
            "weight": c.weight,
            "raw_score": c.raw_score,
            "weighted_score": c.weighted_score,
            "finding": c.finding,
        }
        for c in recommendation.criterion_scores
    ]
    baseline_block = ScenarioBlock(
        summary=baseline_kpi,
        charts=b64_charts,
        criterion_scores=criterion_scores,
    )

    # Step 9: PDF (optional)
    pdf_available = False
    pdf_url: Optional[str] = None
    if model.generate_pdf:
        try:
            _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            report_id = uuid.uuid4().hex
            out_path  = _REPORTS_DIR / f"report_{report_id}.pdf"
            from reporting.pdf_report import PDFReportGenerator
            reporter = PDFReportGenerator(
                operator=op_input,
                simulation_results=sim,
                strategy_results=strategy_results,
                scr_results=scr_results,
                cost_analysis=cost_analysis,
                vol_metrics=vol_metrics,
                recommendation=recommendation,
                output_path=str(out_path),
                domain_loss_breakdown=sim.domain_loss_breakdown,
                domain_correlation=domain_corr,
            )
            reporter.generate()
            pdf_available = True
            pdf_url = f"/static/reports/report_{report_id}.pdf"
        except Exception:
            pdf_available = False

    # ── Mitigation (optional) ─────────────────────────────────────────────────
    mitigated_block: Optional[ScenarioBlock] = None
    comparison_block: Optional[ComparisonBlock] = None
    _la_mit_losses_1d: Optional["np.ndarray"] = None
    _la_mit_e_loss: Optional[float] = None
    _la_mit_scr: Optional[float] = None

    if selected_actions:
        from analysis.mitigation import PREDEFINED_MITIGATIONS, MitigationAnalyzer

        actions = [PREDEFINED_MITIGATIONS[k] for k in selected_actions if k in PREDEFINED_MITIGATIONS]
        if actions:
            analyzer = MitigationAnalyzer(sim)
            mit_scenario = analyzer.compare(
                actions,
                domain_loss_breakdown=sim.domain_loss_breakdown,
            )

            mit_losses = mit_scenario.mitigated_annual_losses
            mit_losses_1d = None
            if mit_losses is not None:
                mit_losses_1d = mit_losses if mit_losses.ndim == 1 else mit_losses.sum(axis=1) / mit_losses.shape[1]
                mit_e_loss = float(mit_losses_1d.mean())
                mit_p95    = float(np.percentile(mit_losses_1d, 95))
                mit_p99    = float(np.percentile(mit_losses_1d, 99))
            else:
                ratio      = 1.0 - mit_scenario.delta_vs_baseline_pct / 100
                mit_e_loss = baseline_e_loss * ratio
                mit_p95    = baseline_p95 * ratio
                mit_p99    = baseline_p99 * ratio

            mit_scr = baseline_scr * (mit_e_loss / baseline_e_loss) if baseline_e_loss > 0 else baseline_scr
            _la_mit_losses_1d = mit_losses_1d
            _la_mit_e_loss    = mit_e_loss
            _la_mit_scr       = mit_scr

            # Recompute suitability score for the mitigated scenario
            mit_composite, mit_verdict, mit_criteria = suitability.estimate_mitigated_score(
                recommendation, mit_e_loss, mit_scr,
                selected_action_ids=selected_actions,
            )

            mit_criterion_scores = [
                {
                    "name": c.name,
                    "weight": c.weight,
                    "raw_score": c.raw_score,
                    "weighted_score": c.weighted_score,
                    "finding": c.finding,
                }
                for c in mit_criteria
            ]
            mit_kpi = KPISummary(
                expected_annual_loss=mit_e_loss,
                p95_loss=mit_p95,
                p99_loss=mit_p99,
                scr=mit_scr,
                recommended_strategy=mit_verdict,
                verdict=mit_verdict,
                composite_score=mit_composite,
                confidence_level=recommendation.confidence_level,
            )
            mitigated_block = ScenarioBlock(
                summary=mit_kpi,
                charts={},
                criterion_scores=mit_criterion_scores,
            )

            domain_counts: Dict[str, float] = {}
            for a in actions:
                for d in a.applies_to_domains:
                    domain_counts[d] = domain_counts.get(d, 0) + a.combined_loss_reduction
            top_domains = sorted(domain_counts, key=lambda x: domain_counts[x], reverse=True)[:3]

            annual_cost_saving = baseline_e_loss - mit_e_loss - sum(a.annual_cost_nok for a in actions)
            delta_pct = (mit_e_loss - baseline_e_loss) / baseline_e_loss * 100 if baseline_e_loss > 0 else 0.0
            score_delta = mit_composite - recommendation.composite_score

            # Build per-criterion delta table for frontend display
            crit_deltas = []
            base_crit_map = {c["name"]: c for c in criterion_scores}
            for mc in mit_criterion_scores:
                bc = base_crit_map.get(mc["name"], {})
                crit_deltas.append({
                    "name":           mc["name"],
                    "weight":         mc.get("weight", 0),
                    "baseline_raw":   bc.get("raw_score", 0),
                    "mitigated_raw":  mc["raw_score"],
                    "delta_weighted": round(mc["weighted_score"] - bc.get("weighted_score", 0), 3),
                    "finding":        mc["finding"],
                })

            # Explain the score change in plain language
            improved = [d for d in crit_deltas if d["delta_weighted"] > 0.05]
            worsened = [d for d in crit_deltas if d["delta_weighted"] < -0.05]
            if abs(score_delta) < 0.05 and not improved and not worsened:
                note = (
                    "Tiltakene krysser ingen kriterieterskler — poengsummen er uendret. "
                    "Risikogevinsten er synlig i forventet tapsdelta og SCR-endring ovenfor."
                )
            elif score_delta > 0:
                note = (
                    f"Poengsummen forbedres med {score_delta:+.1f} pkt. "
                    + (f"Kriterier som forbedres: {', '.join(d['name'] for d in improved)}." if improved else "")
                )
            else:
                note = (
                    f"Poengsummen endres med {score_delta:+.1f} pkt. "
                    + (f"Kriterier som forbedres: {', '.join(d['name'] for d in improved)}. " if improved else "")
                    + (f"Kriterier som svekkes: {', '.join(d['name'] for d in worsened)}." if worsened else "")
                )

            comparison_block = ComparisonBlock(
                expected_loss_delta=mit_e_loss - baseline_e_loss,
                expected_loss_delta_pct=delta_pct,
                p95_delta=mit_p95 - baseline_p95,
                p99_delta=mit_p99 - baseline_p99,
                scr_delta=mit_scr - baseline_scr,
                annual_cost_saving=annual_cost_saving,
                top_benefit_domains=top_domains,
                narrative=(
                    f"{len(actions)} tiltak reduserer forventet arlig tap med "
                    f"{abs(delta_pct):.1f} %. Beste risikodomener: {', '.join(top_domains)}."
                ),
                composite_score_delta=score_delta,
                criterion_deltas=crit_deltas,
                mitigation_score_note=note,
            )

    # ── History — build from operator-declared claims window ──────────────────
    hist_summary = _build_smolt_history_summary(
        claims_history_years, total_claims_paid_nok,
        historical_losses=historical_losses,
        use_history_calibration=use_history_calibration,
    )

    # ── Loss analysis (Tapsanalyse tab) ──────────────────────────────────────
    from backend.services.loss_analysis import compute_loss_analysis
    from backend.schemas import LossAnalysisBlock, LossAnalysisSite, LossAnalysisDriver, LossAnalysisMitigated, LossAnalysisMitigatedSite
    try:
        _la_raw = compute_loss_analysis(
            sim, op_input, baseline_scr,
            mit_losses_1d=_la_mit_losses_1d,
            mit_e_loss=_la_mit_e_loss,
            mit_scr=_la_mit_scr,
        )
        _la_block = LossAnalysisBlock(
            per_site=[LossAnalysisSite(**s) for s in _la_raw["per_site"]],
            per_domain=_la_raw["per_domain"],
            top_drivers=[LossAnalysisDriver(**d) for d in _la_raw["top_drivers"]],
            mitigated=LossAnalysisMitigated(
                per_site=[LossAnalysisMitigatedSite(**s) for s in _la_raw["mitigated"]["per_site"]],
                per_domain=_la_raw["mitigated"]["per_domain"],
                delta_total_eal_nok=_la_raw["mitigated"]["delta_total_eal_nok"],
                delta_total_scr_nok=_la_raw["mitigated"]["delta_total_scr_nok"],
            ) if _la_raw.get("mitigated") else None,
            method_note=_la_raw["method_note"],
        )
    except Exception:
        _la_block = None

    # ── Traceability block ────────────────────────────────────────────────────
    from backend.services.traceability import build_traceability_block
    try:
        _traceability = build_traceability_block(
            sim, op_input, selected_actions or [], _la_block
        )
    except Exception:
        _traceability = None

    return FeasibilityResponse(
        baseline=baseline_block,
        mitigated=mitigated_block,
        comparison=comparison_block,
        report=ReportBlock(available=pdf_available, pdf_url=pdf_url),
        metadata=MetadataBlock(
            domain_correlation_active=(domain_corr is not None),
            mitigation_active=bool(selected_actions and mitigated_block),
            n_simulations=model.n_simulations,
        ),
        allocation=allocation_summary,
        history=hist_summary,
        pooling=None,
        loss_analysis=_la_block,
        traceability=_traceability,
        c5ai_meta=_build_c5ai_meta(_la_block, _traceability),
    )


def _build_c5ai_meta(loss_analysis=None, traceability=None):
    """Read current C5AI+ state and return a C5AIRunMeta instance."""
    from backend.services import c5ai_state as _c5ai_state
    from backend.services.c5ai_state import get_run_extra
    from backend.schemas import C5AIRunMeta, C5AISiteTrace
    s = _c5ai_state.get_status()
    extra = get_run_extra()

    # Whether the C5AI+ biological forecast was actually wired into Monte Carlo
    c5ai_enriched: bool = bool(getattr(traceability, "c5ai_enriched", False))

    # Domain-source map: only biological can ever be c5ai_plus (all others are stub priors)
    _ALL_DOMAINS = ["biological", "structural", "environmental", "operational"]

    def _domain_sources(c5ai_enriched: bool) -> dict:
        return {
            d: ("c5ai_plus" if (d == "biological" and c5ai_enriched) else "estimated")
            for d in _ALL_DOMAINS
        }

    def _confidence(c5ai_enriched: bool, has_site_data: bool) -> tuple:
        """
        Heuristic confidence score for per-site domain breakdown.

        Hard cap at 0.55 (Middels) because structural/environmental/operational
        are always stub-estimated, and domain breakdown is portfolio-proportional
        (not site-specific). A score of 1.0 would require per-site data for all
        four domains — not possible with the current model.

        Score components:
          0.25  base (template-scaled Monte Carlo always runs)
          +0.10 if site-level EAL data is available (loss_analysis populated)
          +0.20 if biological domain is C5AI+-informed
          ────
          max:  0.55 (Middels)
        """
        score = 0.25
        if has_site_data:
            score += 0.10
        if c5ai_enriched:
            score += 0.20
        # Never "Høy" — non-bio domains are always estimated
        score = min(score, 0.55)
        if score >= 0.50:
            label = "Middels"
        elif score >= 0.35:
            label = "Lav–Middels"
        else:
            label = "Lav"
        return round(score, 2), label

    has_site_data = (loss_analysis is not None and
                     len(getattr(loss_analysis, "per_site", [])) > 0)
    conf_score, conf_label = _confidence(c5ai_enriched, has_site_data)
    dom_sources = _domain_sources(c5ai_enriched)

    # Build site_trace from loss_analysis.per_site if available
    from backend.services.site_registry import get_site_by_site_id as _get_site
    site_trace = []
    if loss_analysis is not None:
        for st in getattr(loss_analysis, "per_site", []):
            top_risk_types = sorted(
                getattr(st, "domain_breakdown", {}).keys(),
                key=lambda d: getattr(st, "domain_breakdown", {}).get(d, 0),
                reverse=True,
            )[:2]
            _reg = _get_site(st.site_id)
            site_trace.append(C5AISiteTrace(
                site_id=st.site_id,
                site_name=st.site_name,
                expected_annual_loss_nok=float(st.expected_annual_loss_nok),
                scr_contribution_nok=float(st.scr_contribution_nok),
                dominant_domain=getattr(st, "dominant_domain", ""),
                top_risk_types=list(top_risk_types),
                domain_sources=dom_sources,
                confidence_score=conf_score,
                confidence_label=conf_label,
                locality_no=_reg.locality_no if _reg is not None else None,
            ))

    domains_used = extra.get("domains_used", []) or (
        list(getattr(traceability, "domains_used", [])) if traceability else []
    )
    risk_type_count = extra.get("risk_type_count", 0) or (
        getattr(traceability, "risk_type_count", 0) if traceability else 0
    )

    ratio = extra.get("c5ai_vs_static_ratio")
    c5ai_vs_static_ratio = float(ratio) if ratio is not None else None

    return C5AIRunMeta(
        run_id=s.get("run_id"),
        generated_at=s.get("c5ai_last_run_at"),
        is_fresh=s.get("is_fresh", False),
        freshness=s.get("freshness", "missing"),
        site_count=len(extra.get("site_ids", [])),
        site_ids=extra.get("site_ids", []),
        site_names=extra.get("site_names", []),
        data_mode=extra.get("data_mode", "simulated"),
        domains_used=domains_used,
        risk_type_count=risk_type_count,
        source_labels=extra.get("source_labels", []),
        site_trace=site_trace,
        c5ai_vs_static_ratio=c5ai_vs_static_ratio,
    )


def run_feasibility_service(request: FeasibilityRequest) -> FeasibilityResponse:
    """Execute the full pipeline and return a FeasibilityResponse."""

    profile = request.operator_profile
    model = request.model_settings
    strategy = request.strategy_settings
    mitigation = request.mitigation

    # ── 1. Build operator input ───────────────────────────────────────────────
    operator, alloc_summary = build_operator_input(
        profile,
        use_history_calibration=model.use_history_calibration,
    )

    # ── 2. Domain correlation ─────────────────────────────────────────────────
    from models.domain_correlation import (
        DomainCorrelationMatrix,
        PREDEFINED_DOMAIN_CORRELATIONS,
    )
    corr_key = model.domain_correlation
    domain_corr: Optional[DomainCorrelationMatrix] = PREDEFINED_DOMAIN_CORRELATIONS.get(
        corr_key
    )
    if domain_corr is None:
        domain_corr = DomainCorrelationMatrix.expert_default()

    # ── 3. Monte Carlo ────────────────────────────────────────────────────────
    from models.monte_carlo import MonteCarloEngine
    engine = MonteCarloEngine(
        operator,
        n_simulations=model.n_simulations,
        domain_correlation=domain_corr,
        cage_multipliers=alloc_summary.cage_multipliers,
    )
    sim = engine.run()

    # ── 4. Strategy models ────────────────────────────────────────────────────
    from models.strategies.full_insurance import FullInsuranceStrategy
    from models.strategies.hybrid import HybridStrategy
    from models.strategies.pcc_captive import PCCCaptiveStrategy
    from models.strategies.self_insurance import SelfInsuranceStrategy

    strategies = {
        "Full Insurance":   FullInsuranceStrategy(operator, sim),
        "Hybrid":           HybridStrategy(operator, sim),
        "PCC Captive Cell": PCCCaptiveStrategy(operator, sim),
        "Self-Insurance":   SelfInsuranceStrategy(operator, sim),
    }
    strategy_results = {name: s.calculate() for name, s in strategies.items()}

    # ── 5. SCR, cost, volatility, suitability ────────────────────────────────
    from analysis.scr_calculator import SCRCalculator
    from analysis.cost_analyzer import CostAnalyzer
    from analysis.volatility_metrics import VolatilityAnalyzer
    from analysis.suitability_engine import SuitabilityEngine

    scr_calc = SCRCalculator(sim, strategy_results)
    scr_results = scr_calc.calculate_all()

    cost_analyzer = CostAnalyzer(operator, strategy_results)
    cost_analysis = cost_analyzer.analyze()

    vol_analyzer = VolatilityAnalyzer(sim, strategy_results)
    vol_metrics = vol_analyzer.analyze()

    suitability = SuitabilityEngine(operator, sim, strategy_results, cost_analysis)
    recommendation = suitability.assess()

    # ── 6. Charts ─────────────────────────────────────────────────────────────
    from reporting.chart_generator import generate_all_charts
    from reporting.correlated_risk_analytics import build_correlated_risk_summary

    corr_summary = build_correlated_risk_summary(sim.annual_losses, sim.domain_loss_breakdown)
    raw_charts = generate_all_charts(
        sim,
        strategy_results,
        scr_results,
        cost_analysis,
        vol_metrics,
        recommendation,
        correlated_risk_summary=corr_summary,
        domain_correlation=domain_corr,
    )
    b64_charts = _charts_to_b64(raw_charts)

    # ── 7. Build baseline KPI block ───────────────────────────────────────────
    pcc_scr = scr_results.get("PCC Captive Cell")
    baseline_scr = pcc_scr.scr_net if pcc_scr else sim.var_995

    import numpy as np
    # annual_losses shape is (N, T); sum across years to get per-simulation total annual loss
    annual_losses = sim.annual_losses  # shape (N, T)
    per_sim_loss = annual_losses.sum(axis=1) / annual_losses.shape[1]  # mean annual
    baseline_e_loss = float(per_sim_loss.mean())
    baseline_p95 = float(np.percentile(per_sim_loss, 95))
    baseline_p99 = float(np.percentile(per_sim_loss, 99))

    baseline_kpi = KPISummary(
        expected_annual_loss=baseline_e_loss,
        p95_loss=baseline_p95,
        p99_loss=baseline_p99,
        scr=baseline_scr,
        recommended_strategy=recommendation.verdict,
        verdict=recommendation.verdict,
        composite_score=recommendation.composite_score,
        confidence_level=recommendation.confidence_level,
    )
    criterion_scores = [
        {
            "name": c.name,
            "weight": c.weight,
            "raw_score": c.raw_score,
            "weighted_score": c.weighted_score,
            "finding": c.finding,
        }
        for c in recommendation.criterion_scores
    ]
    baseline_block = ScenarioBlock(
        summary=baseline_kpi,
        charts=b64_charts,
        criterion_scores=criterion_scores,
    )

    # ── 8. Mitigation (optional) ──────────────────────────────────────────────
    mitigated_block: Optional[ScenarioBlock] = None
    comparison_block: Optional[ComparisonBlock] = None
    _la_mit_losses_1d2: Optional["np.ndarray"] = None
    _la_mit_e_loss2: Optional[float] = None
    _la_mit_scr2: Optional[float] = None

    selected = mitigation.selected_actions if mitigation else []
    if selected:
        from analysis.mitigation import PREDEFINED_MITIGATIONS, MitigationAnalyzer

        actions = [PREDEFINED_MITIGATIONS[k] for k in selected if k in PREDEFINED_MITIGATIONS]
        if actions:
            analyzer = MitigationAnalyzer(sim)
            mit_scenario = analyzer.compare(
                actions,
                domain_loss_breakdown=sim.domain_loss_breakdown,
            )

            mit_losses = mit_scenario.mitigated_annual_losses
            mit_losses_1d = None
            if mit_losses is not None:
                mit_losses_1d = mit_losses if mit_losses.ndim == 1 else mit_losses.sum(axis=1) / mit_losses.shape[1]
                mit_e_loss = float(mit_losses_1d.mean())
                mit_p95 = float(np.percentile(mit_losses_1d, 95))
                mit_p99 = float(np.percentile(mit_losses_1d, 99))
            else:
                ratio = 1.0 - mit_scenario.delta_vs_baseline_pct / 100
                mit_e_loss = baseline_e_loss * ratio
                mit_p95 = baseline_p95 * ratio
                mit_p99 = baseline_p99 * ratio

            # Approximate mitigated SCR proportionally
            mit_scr = baseline_scr * (mit_e_loss / baseline_e_loss) if baseline_e_loss > 0 else baseline_scr
            _la_mit_losses_1d2 = mit_losses_1d
            _la_mit_e_loss2    = mit_e_loss
            _la_mit_scr2       = mit_scr

            # Recompute suitability score for the mitigated scenario
            mit_composite, mit_verdict, mit_criteria = suitability.estimate_mitigated_score(
                recommendation, mit_e_loss, mit_scr,
                selected_action_ids=selected,
            )

            mit_criterion_scores = [
                {
                    "name": c.name,
                    "weight": c.weight,
                    "raw_score": c.raw_score,
                    "weighted_score": c.weighted_score,
                    "finding": c.finding,
                }
                for c in mit_criteria
            ]
            mit_kpi = KPISummary(
                expected_annual_loss=mit_e_loss,
                p95_loss=mit_p95,
                p99_loss=mit_p99,
                scr=mit_scr,
                recommended_strategy=mit_verdict,
                verdict=mit_verdict,
                composite_score=mit_composite,
                confidence_level=recommendation.confidence_level,
            )
            mitigated_block = ScenarioBlock(
                summary=mit_kpi,
                charts={},  # reuse baseline charts
                criterion_scores=mit_criterion_scores,
            )

            # Identify top benefit domains from selected actions
            domain_counts: Dict[str, float] = {}
            for a in actions:
                reduction = a.combined_loss_reduction
                for d in a.applies_to_domains:
                    domain_counts[d] = domain_counts.get(d, 0) + reduction
            top_domains = sorted(domain_counts, key=lambda x: domain_counts[x], reverse=True)[:3]

            annual_cost_saving = baseline_e_loss - mit_e_loss - sum(a.annual_cost_nok for a in actions)
            delta_pct = (mit_e_loss - baseline_e_loss) / baseline_e_loss * 100 if baseline_e_loss > 0 else 0.0
            score_delta = mit_composite - recommendation.composite_score

            # Build per-criterion delta table
            crit_deltas = []
            base_crit_map = {c["name"]: c for c in criterion_scores}
            for mc in mit_criterion_scores:
                bc = base_crit_map.get(mc["name"], {})
                crit_deltas.append({
                    "name":           mc["name"],
                    "weight":         mc.get("weight", 0),
                    "baseline_raw":   bc.get("raw_score", 0),
                    "mitigated_raw":  mc["raw_score"],
                    "delta_weighted": round(mc["weighted_score"] - bc.get("weighted_score", 0), 3),
                    "finding":        mc["finding"],
                })

            improved = [d for d in crit_deltas if d["delta_weighted"] > 0.05]
            worsened = [d for d in crit_deltas if d["delta_weighted"] < -0.05]
            if abs(score_delta) < 0.05 and not improved and not worsened:
                note = (
                    "Tiltakene krysser ingen kriterieterskler — poengsummen er uendret. "
                    "Risikogevinsten er synlig i forventet tapsdelta og SCR-endring ovenfor."
                )
            elif score_delta > 0:
                note = (
                    f"Poengsummen forbedres med {score_delta:+.1f} pkt. "
                    + (f"Kriterier som forbedres: {', '.join(d['name'] for d in improved)}." if improved else "")
                )
            else:
                note = (
                    f"Poengsummen endres med {score_delta:+.1f} pkt. "
                    + (f"Kriterier som forbedres: {', '.join(d['name'] for d in improved)}. " if improved else "")
                    + (f"Kriterier som svekkes: {', '.join(d['name'] for d in worsened)}." if worsened else "")
                )

            comparison_block = ComparisonBlock(
                expected_loss_delta=mit_e_loss - baseline_e_loss,
                expected_loss_delta_pct=delta_pct,
                p95_delta=mit_p95 - baseline_p95,
                p99_delta=mit_p99 - baseline_p99,
                scr_delta=mit_scr - baseline_scr,
                annual_cost_saving=annual_cost_saving,
                top_benefit_domains=top_domains,
                narrative=(
                    f"{len(actions)} tiltak reduserer forventet årlig tap med "
                    f"{abs(delta_pct):.1f} %. Beste risikodomener: {', '.join(top_domains)}."
                ),
                composite_score_delta=score_delta,
                criterion_deltas=crit_deltas,
                mitigation_score_note=note,
            )

    # ── 8b. Pooled PCC (optional) ────────────────────────────────────────────
    pooling_response: Optional[PoolingResult] = None
    pool_settings = request.pooling_settings

    if pool_settings and pool_settings.enabled:
        from models.pooling.assumptions import PoolingAssumptions, KNOWN_SIMPLIFICATIONS
        from models.strategies.pooled_pcc import PooledPCCStrategy

        pool_assump = PoolingAssumptions(
            enabled=True,
            n_members=pool_settings.n_members,
            inter_member_correlation=pool_settings.inter_member_correlation,
            similarity_spread=pool_settings.similarity_spread,
            pooled_retention_nok=pool_settings.pooled_retention_nok,
            pooled_ri_limit_nok=pool_settings.pooled_ri_limit_nok,
            pooled_ri_loading_factor=pool_settings.pooled_ri_loading_factor,
            shared_admin_saving_pct=pool_settings.shared_admin_saving_pct,
            allocation_basis=pool_settings.allocation_basis,
        )

        # Get standalone PCC SCR for comparison
        standalone_scr_val = pcc_scr.scr_net if pcc_scr else 0.0
        # Standalone RI premium from PCC strategy assumptions
        standalone_ri = 0.0
        pcc_strat_result = strategy_results.get("PCC Captive Cell")
        if pcc_strat_result and pcc_strat_result.annual_breakdown:
            standalone_ri = pcc_strat_result.annual_breakdown[0].reinsurance_cost

        from models.pcc_economics import PCCAssumptions as _PCC
        pooled_strategy = PooledPCCStrategy(
            operator, sim,
            pooling_assumptions=pool_assump,
            standalone_pcc_assumptions=_PCC.base(),
            standalone_ri_premium=standalone_ri,
            standalone_scr=standalone_scr_val,
        )
        pooled_result = pooled_strategy.calculate()
        strategy_results["Pooled PCC Cell"] = pooled_result

        # Rebuild SCR / cost analysis to include Pooled PCC
        scr_results = scr_calc.calculate_all()
        cost_analysis = cost_analyzer.analyze()

        eco = pooled_strategy.pooled_economics
        if eco is not None:
            op_alloc = eco.operator_allocation
            members_stats = [
                PoolingMemberStats(
                    member_id=a.member_id,
                    label=a.label,
                    expected_annual_loss=a.expected_annual_loss,
                    allocation_weight=round(a.allocation_weight, 4),
                    standalone_cv=round(a.standalone_cv, 4),
                    pooled_cv=round(a.pooled_cv, 4),
                    allocated_ri_premium_annual=a.allocated_ri_premium_annual,
                    allocated_scr=a.allocated_scr,
                    allocated_5yr_tcor=a.allocated_5yr_tcor,
                )
                for a in eco.all_allocations
            ]

            # Viability: pooled TCOR is cheaper than standalone PCC cost
            pooled_tcor = eco.operator_5yr_tcor_pooled
            standalone_tcor = eco.operator_5yr_tcor_standalone
            viable = pooled_tcor < standalone_tcor and eco.cv_reduction_pct > 5

            if viable:
                narrative = (
                    f"Pooled PCC is VIABLE. Joining a {eco.n_members}-member pool reduces "
                    f"loss volatility by {eco.cv_reduction_pct:.1f}% (CV: "
                    f"{eco.standalone_cv:.2f} → {eco.pooled_cv:.2f}), cuts RI premium by "
                    f"{eco.ri_premium_reduction_pct:.1f}%, and lowers required SCR by "
                    f"{eco.scr_reduction_pct:.1f}%. 5-year TCOR improves by "
                    f"{eco.tcor_improvement_pct:.1f}% vs standalone PCC."
                )
            else:
                narrative = (
                    f"Pooled PCC delivers limited additional benefit in this scenario. "
                    f"CV reduction: {eco.cv_reduction_pct:.1f}%. "
                    f"Consider increasing pool size or reducing inter-member correlation."
                )

            pooling_response = PoolingResult(
                enabled=True,
                n_members=eco.n_members,
                pooled_mean_annual_loss=eco.pooled_mean_annual_loss,
                pooled_cv=round(eco.pooled_cv, 4),
                pooled_var_995=eco.pooled_var_995,
                standalone_cv=round(eco.standalone_cv, 4),
                standalone_var_995=eco.standalone_var_995,
                cv_reduction_pct=round(eco.cv_reduction_pct, 2),
                var_reduction_pct=round(eco.var_reduction_pct, 2),
                pooled_ri_premium_annual=eco.pooled_ri_premium,
                standalone_ri_premium_annual=standalone_ri,
                ri_premium_reduction_pct=round(eco.ri_premium_reduction_pct, 2),
                pooled_scr=eco.pooled_scr,
                standalone_scr=standalone_scr_val,
                scr_reduction_pct=round(eco.scr_reduction_pct, 2),
                operator_5yr_tcor_standalone=eco.operator_5yr_tcor_standalone,
                operator_5yr_tcor_pooled=eco.operator_5yr_tcor_pooled,
                tcor_improvement_pct=round(eco.tcor_improvement_pct, 2),
                members=members_stats,
                viable=viable,
                verdict_narrative=narrative,
                known_simplifications=KNOWN_SIMPLIFICATIONS,
            )

    # ── 9. PDF (optional) ────────────────────────────────────────────────────
    pdf_available = False
    pdf_url: Optional[str] = None

    generate_pdf = model.generate_pdf
    # Also honour legacy output_options field
    if request.output_options and isinstance(request.output_options.get("generate_pdf"), bool):
        generate_pdf = request.output_options["generate_pdf"]

    if generate_pdf:
        try:
            _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            report_id = uuid.uuid4().hex
            out_path = _REPORTS_DIR / f"report_{report_id}.pdf"

            from reporting.pdf_report import PDFReportGenerator
            reporter = PDFReportGenerator(
                operator=operator,
                simulation_results=sim,
                strategy_results=strategy_results,
                scr_results=scr_results,
                cost_analysis=cost_analysis,
                vol_metrics=vol_metrics,
                recommendation=recommendation,
                output_path=str(out_path),
                domain_loss_breakdown=sim.domain_loss_breakdown,
                domain_correlation=domain_corr,
            )
            reporter.generate()
            pdf_available = True
            pdf_url = f"/static/reports/report_{report_id}.pdf"
        except Exception:
            pdf_available = False

    # ── Build history summary ─────────────────────────────────────────────────
    raw_hist = load_template_history()
    hist_summary = build_historical_loss_summary(
        raw_records=raw_hist,
        calibration_active=alloc_summary.calibration_active,
        calibration_mode=alloc_summary.calibration_mode,
        alloc_calibrated_params=alloc_summary.calibrated_parameters,
        history_source="template",
    )

    # ── Loss analysis (Tapsanalyse tab) ──────────────────────────────────────
    from backend.services.loss_analysis import compute_loss_analysis
    from backend.schemas import LossAnalysisBlock, LossAnalysisSite, LossAnalysisDriver, LossAnalysisMitigated, LossAnalysisMitigatedSite
    try:
        _la_raw2 = compute_loss_analysis(
            sim, operator, baseline_scr,
            mit_losses_1d=_la_mit_losses_1d2,
            mit_e_loss=_la_mit_e_loss2,
            mit_scr=_la_mit_scr2,
        )
        _la_block2 = LossAnalysisBlock(
            per_site=[LossAnalysisSite(**s) for s in _la_raw2["per_site"]],
            per_domain=_la_raw2["per_domain"],
            top_drivers=[LossAnalysisDriver(**d) for d in _la_raw2["top_drivers"]],
            mitigated=LossAnalysisMitigated(
                per_site=[LossAnalysisMitigatedSite(**s) for s in _la_raw2["mitigated"]["per_site"]],
                per_domain=_la_raw2["mitigated"]["per_domain"],
                delta_total_eal_nok=_la_raw2["mitigated"]["delta_total_eal_nok"],
                delta_total_scr_nok=_la_raw2["mitigated"]["delta_total_scr_nok"],
            ) if _la_raw2.get("mitigated") else None,
            method_note=_la_raw2["method_note"],
        )
    except Exception:
        _la_block2 = None

    # ── Traceability block ────────────────────────────────────────────────────
    _sel_mode = alloc_summary.site_selection_mode if alloc_summary else "generic"
    from backend.services.traceability import build_traceability_block
    try:
        _traceability2 = build_traceability_block(
            sim, operator, selected or [], _la_block2,
            site_selection_mode=_sel_mode,
        )
    except Exception:
        _traceability2 = None

    _sel_count = len(alloc_summary.sites) if (alloc_summary and _sel_mode == "specific") else 0
    _sel_locs = alloc_summary.selected_locality_numbers if alloc_summary else []

    return FeasibilityResponse(
        baseline=baseline_block,
        mitigated=mitigated_block,
        comparison=comparison_block,
        report=ReportBlock(available=pdf_available, pdf_url=pdf_url),
        metadata=MetadataBlock(
            domain_correlation_active=(domain_corr is not None),
            mitigation_active=bool(selected),
            n_simulations=model.n_simulations,
            site_selection_mode=_sel_mode,
            selected_site_count=_sel_count,
            selected_locality_numbers=_sel_locs,
        ),
        allocation=alloc_summary,
        history=hist_summary,
        pooling=pooling_response,
        loss_analysis=_la_block2,
        traceability=_traceability2,
        c5ai_meta=_build_c5ai_meta(_la_block2, _traceability2),
        cage_profiles=alloc_summary.cage_profiles if alloc_summary else None,
    )
