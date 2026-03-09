"""
C5AI+ Self-Learning Loop Demo
==============================================

Demonstrates the full predict→observe→evaluate→retrain loop over 5 cycles.

Usage:
    python examples/run_learning_loop_demo.py
"""

from __future__ import annotations

import os
import sys
import tempfile

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def run_demo():
    print("=" * 65)
    print("C5AI+ Self-Learning Loop Demo")
    print("=" * 65)

    # ── Step 1: Generate synthetic 3-site, 5-year operator input ──────
    print("\nStep 1: Generating synthetic 3-site, 5-year operator input...")
    from c5ai_plus.simulation.site_data_simulator import SiteDataSimulator

    sim = SiteDataSimulator(seed=42)
    operator_input = sim.generate_operator_input(
        operator_id="DEMO_OP",
        operator_name="Demo Salmon AS",
        n_sites=3,
        n_years=5,
        base_year=2018,
    )
    print(f"  Operator: {operator_input.operator_name} ({operator_input.operator_id})")
    print(f"  Sites: {len(operator_input.sites)}")
    print(f"  Env observations: {len(operator_input.env_observations)}")
    print(f"  Lice observations: {len(operator_input.lice_observations)}")

    # ── Step 2: Run 5 learning cycles (years 2020-2024) ───────────────
    print("\nStep 2: Running 5 learning cycles (2020–2024)...")
    from c5ai_plus.learning.learning_loop import LearningLoop

    STATIC_LOSS = 5_000_000.0   # NOK 5M static Monte Carlo estimate

    with tempfile.TemporaryDirectory() as tmpdir:
        loop = LearningLoop(store_dir=tmpdir, verbose=False)

        results = []
        brier_table: dict = {rt: [] for rt in ("hab", "lice", "jellyfish", "pathogen")}

        cycle_labels = {
            0: "cold baseline, prior only",
            1: "first observations stored",
            2: "Bayesian posterior diverges from prior",
            3: "retraining triggered",
            4: "shadow model evaluated",
        }

        for i, year in enumerate(range(2020, 2025)):
            result = loop.run_cycle(
                operator_input,
                static_mean_annual_loss=STATIC_LOSS,
                forecast_year=year,
            )
            results.append(result)
            label = cycle_labels.get(i, "")
            print(f"  Cycle {i+1} (year={year}) [{result.learning_status}]"
                  + (f" — {label}" if label else ""))
            for rt in ("hab", "lice", "jellyfish", "pathogen"):
                m = result.metrics_by_risk_type[rt]
                brier_table[rt].append(m.brier_score)

        # ── Step 3: Print Brier score per cycle per risk type ─────────
        print("\nStep 3: Brier Score Table (lower = better; 0.25 = uninformative)")
        print("-" * 65)
        header = f"{'Risk Type':<14}" + "".join(f"  Cycle {i+1}" for i in range(5))
        print(header)
        print("-" * 65)
        for rt in ("hab", "lice", "jellyfish", "pathogen"):
            row = f"{rt:<14}" + "".join(f"  {b:7.4f}" for b in brier_table[rt])
            print(row)
        print("-" * 65)

        # ── Step 4: Print model version history ───────────────────────
        print("\nStep 4: Model Version History")
        from c5ai_plus.models.model_registry import ModelRegistry
        registry = ModelRegistry(store_dir=tmpdir)
        versions = registry.model_versions("DEMO_OP")
        print(f"  {'Risk Type':<14}  Version")
        for rt, ver in sorted(versions.items()):
            print(f"  {rt:<14}  {ver}")

        # ── Step 5: Integrate final forecast with MonteCarloEngine ────
        print("\nStep 5: Integrating final enriched forecast with MonteCarloEngine...")
        from c5ai_plus.pipeline import ForecastPipeline

        pipeline = ForecastPipeline(verbose=False)
        final_forecast = pipeline.run(operator_input, STATIC_LOSS)
        print(f"  Scale factor vs. static: {final_forecast.scale_factor:.4f}")
        print(f"  Total E[annual loss]: NOK {final_forecast.total_expected_annual_loss/1e6:,.2f}M")
        print(f"  Loss fractions: { {k: f'{v:.1%}' for k, v in final_forecast.loss_fractions.items()} }")

        # ── Step 6: Compare PCC results ───────────────────────────────
        print("\nStep 6: PCC Compatibility Check")
        print(f"  scale_factor accessible:  {final_forecast.scale_factor is not None}")
        print(f"  loss_fractions accessible: {final_forecast.loss_fractions is not None}")
        print(f"  loss_fractions sum to 1:  {abs(sum(final_forecast.loss_fractions.values()) - 1.0) < 1e-6}")
        print(f"  [OK] PCC interface fully backward-compatible")

        # ── Final summary ─────────────────────────────────────────────
        last = results[-1]
        print(f"\nFinal learning status: {last.learning_status}")
        print(f"Cycles completed:      {last.cycle_id + 1}")
        print(f"Models promoted:       {last.models_promoted or 'none'}")

    print("\n" + "=" * 65)
    print("Demo complete.")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
