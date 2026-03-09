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


_REPORTS_DIR = Path(__file__).resolve().parents[2] / "backend" / "static" / "reports"


def _buf_to_b64(buf: io.BytesIO) -> str:
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _charts_to_b64(charts: Dict[str, io.BytesIO]) -> Dict[str, str]:
    return {k: _buf_to_b64(v) for k, v in charts.items()}


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

            mit_kpi = KPISummary(
                expected_annual_loss=mit_e_loss,
                p95_loss=mit_p95,
                p99_loss=mit_p99,
                scr=mit_scr,
                recommended_strategy=recommendation.verdict,
                verdict=recommendation.verdict,
                composite_score=recommendation.composite_score,
                confidence_level=recommendation.confidence_level,
            )
            mitigated_block = ScenarioBlock(
                summary=mit_kpi,
                charts={},  # reuse baseline charts
                criterion_scores=criterion_scores,
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

            comparison_block = ComparisonBlock(
                expected_loss_delta=mit_e_loss - baseline_e_loss,
                expected_loss_delta_pct=delta_pct,
                p95_delta=mit_p95 - baseline_p95,
                p99_delta=mit_p99 - baseline_p99,
                scr_delta=mit_scr - baseline_scr,
                annual_cost_saving=annual_cost_saving,
                top_benefit_domains=top_domains,
                narrative=(
                    f"Applying {len(actions)} mitigation action(s) reduces expected annual loss "
                    f"by {abs(delta_pct):.1f}%. Top benefiting domains: {', '.join(top_domains)}."
                ),
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

    return FeasibilityResponse(
        baseline=baseline_block,
        mitigated=mitigated_block,
        comparison=comparison_block,
        report=ReportBlock(available=pdf_available, pdf_url=pdf_url),
        metadata=MetadataBlock(
            domain_correlation_active=(domain_corr is not None),
            mitigation_active=bool(selected),
            n_simulations=model.n_simulations,
        ),
        allocation=alloc_summary,
        history=hist_summary,
        pooling=pooling_response,
    )
