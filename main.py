"""
PCC Feasibility & Suitability Tool – Main Entry Point
======================================================
Fish Farming Risk Management Platform

Usage
-----
    python main.py                              # run with sample data
    python main.py --input path/to/input.json  # custom operator input
    python main.py --input input.json --output report.pdf --simulations 20000

Arguments
---------
    --input  / -i   Path to operator input JSON file (default: data/sample_input.json)
    --output / -o   Output PDF file path (default: auto-named with timestamp)
    --simulations / -n  Number of Monte Carlo simulations (default: 10,000)
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


def _banner():
    print()
    print("=" * 62)
    print("   PCC FEASIBILITY & SUITABILITY TOOL  v1.0")
    print("   Fish Farming Risk Management Platform")
    print("   Shield Risk Consulting")
    print("=" * 62)


def _progress(step: int, total: int, label: str):
    bar_len = 28
    filled = int(bar_len * step / total)
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"  [{bar}] {step}/{total}  {label}", flush=True)


def load_input(input_path: str) -> dict:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    with open(path, "r") as fh:
        return json.load(fh)


def run_analysis(input_data: dict, output_path: str, n_simulations: int = 10_000):
    """Execute the full analysis pipeline and generate the PDF report."""

    total_steps = 9
    t0 = time.time()

    # ── 1. Validate input ────────────────────────────────────────────────────
    _progress(1, total_steps, "Validating input data...")
    from data.input_schema import validate_input
    operator = validate_input(input_data)
    def _nok(v): return f"NOK {v/1_000_000:,.1f} M"
    print(f"       Operator  : {operator.name}")
    print(f"       Land      : {operator.country}")
    print(f"       TIV       : {_nok(operator.total_insured_value)}")
    print(f"       Omsetning : {_nok(operator.total_annual_revenue)}")
    print(f"       Premie    : {_nok(operator.current_insurance.annual_premium)}")

    # ── 2. Monte Carlo ───────────────────────────────────────────────────────
    _progress(2, total_steps, f"Monte Carlo-simulering ({n_simulations:,} kjøringer x 5 år)...")
    from models.monte_carlo import MonteCarloEngine
    from models.domain_correlation import DomainCorrelationMatrix
    engine = MonteCarloEngine(
        operator,
        n_simulations=n_simulations,
        domain_correlation=DomainCorrelationMatrix.expert_default(),
    )
    sim = engine.run()
    print(f"       E[arlig tap]    : {_nok(sim.mean_annual_loss)}")
    print(f"       VaR 99.5%       : {_nok(sim.var_995)}")
    print(f"       TVaR 95%        : {_nok(sim.tvar_95)}")

    # ── 3. Strategy models ───────────────────────────────────────────────────
    _progress(3, total_steps, "Modellerer risikostrategi...")
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
    for name, res in strategy_results.items():
        print(f"       {name:<22}: 5-ars kostnad = {_nok(res.total_5yr_cost)}")

    # ── 4. SCR calculation ───────────────────────────────────────────────────
    _progress(4, total_steps, "Beregner solvenskapitalkrav (SCR)...")
    from analysis.scr_calculator import SCRCalculator
    scr_calc = SCRCalculator(sim, strategy_results)
    scr_results = scr_calc.calculate_all()
    pcc_scr = scr_results.get("PCC Captive Cell")
    if pcc_scr:
        print(f"       PCC SCR (netto) : {_nok(pcc_scr.scr_net)}")
        print(f"       Solvensgrad     : {pcc_scr.solvency_ratio:.1%}")

    # ── 5. Cost analysis ─────────────────────────────────────────────────────
    _progress(5, total_steps, "Analyserer 5-ars total risikokostnad...")
    from analysis.cost_analyzer import CostAnalyzer
    cost_analyzer = CostAnalyzer(operator, strategy_results)
    cost_analysis = cost_analyzer.analyze()
    pcc_sum = cost_analysis.summaries.get("PCC Captive Cell")
    if pcc_sum:
        print(f"       PCC vs Full Ins  : {_nok(pcc_sum.vs_baseline_savings_5yr)} besparelse "
              f"({pcc_sum.vs_baseline_savings_pct:.1%})")

    # ── 6. Volatility analysis ────────────────────────────────────────────────
    _progress(6, total_steps, "Beregner volatilitet og halerisiko...")
    from analysis.volatility_metrics import VolatilityAnalyzer
    vol_analyzer = VolatilityAnalyzer(sim, strategy_results)
    vol_metrics = vol_analyzer.analyze()
    print(f"       Most stable     : {vol_metrics.most_stable}")
    print(f"       Best tail cover : {vol_metrics.best_tail_protection}")

    # ── 7. Suitability assessment ─────────────────────────────────────────────
    _progress(7, total_steps, "Genererer egnethetsvurdering...")
    from analysis.suitability_engine import SuitabilityEngine
    suitability = SuitabilityEngine(operator, sim, strategy_results, cost_analysis)
    recommendation = suitability.assess()
    print(f"       Verdict         : {recommendation.verdict}")
    print(f"       Score           : {recommendation.composite_score:.1f}/100  "
          f"({recommendation.confidence_level} confidence)")
    for c in recommendation.criterion_scores:
        bar = "#" * int(c.raw_score / 10) + "-" * (10 - int(c.raw_score / 10))
        print(f"         {c.name:<26}: [{bar}] {c.raw_score:.0f}")

    # ── 8. Generate PDF ───────────────────────────────────────────────────────
    _progress(8, total_steps, "Bygger styreklar PDF-rapport...")
    from reporting.pdf_report import PDFReportGenerator
    reporter = PDFReportGenerator(
        operator=operator,
        simulation_results=sim,
        strategy_results=strategy_results,
        scr_results=scr_results,
        cost_analysis=cost_analysis,
        vol_metrics=vol_metrics,
        recommendation=recommendation,
        output_path=output_path,
        domain_loss_breakdown=sim.domain_loss_breakdown,
        domain_correlation=DomainCorrelationMatrix.expert_default(),
    )
    reporter.generate()

    # ── 9. Done ───────────────────────────────────────────────────────────────
    _progress(9, total_steps, "Complete.")
    elapsed = time.time() - t0
    print()
    print("=" * 62)
    print(f"  Report saved : {output_path}")
    print(f"  Elapsed      : {elapsed:.1f}s")
    print("=" * 62)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="PCC Feasibility & Suitability Tool – Fish Farming Risk Management",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        default="data/sample_input.json",
        help="Path to operator input JSON file",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output PDF path (auto-generated if omitted)",
    )
    parser.add_argument(
        "--simulations", "-n",
        type=int,
        default=10_000,
        help="Number of Monte Carlo simulations",
    )
    args = parser.parse_args()

    _banner()

    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"pcc_report_{ts}.pdf"

    try:
        data = load_input(args.input)
        run_analysis(data, args.output, args.simulations)
    except FileNotFoundError as exc:
        print(f"\n  ERROR: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(0)
    except Exception as exc:
        print(f"\n  UNEXPECTED ERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
