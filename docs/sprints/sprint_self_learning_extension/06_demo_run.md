# Self-Learning Extension – Demo Run

## How to Run

```bash
# From the project root directory
python examples/run_learning_loop_demo.py
```

No extra dependencies beyond the base requirements. The demo uses a temporary
directory for storage and cleans up on exit.

---

## What the Demo Does

### Step 1 – Generate synthetic operator input
Creates a 3-site, 5-year (2018–2022) synthetic `C5AIOperatorInput` using
`SiteDataSimulator` with seed=42:

- 3 sites at Norwegian fjord latitudes (~63.5°N)
- Seasonal temperature model, HAB alerts, lice counts, jellyfish, pathogens
- ~150 environmental observations, ~780 lice weekly records

### Step 2 – Run 5 learning cycles (2020–2024)
Each cycle:
1. Runs `ForecastPipeline` to generate a `RiskForecast`
2. Enriches forecasts with Bayesian posteriors from `ModelRegistry`
3. Saves predictions to `PredictionStore`
4. Simulates observed events via `EventSimulator`
5. Saves events and updates models
6. Evaluates matched pairs → Brier score per risk type
7. Triggers retraining when criterion met
8. Evaluates shadow model for promotion

Cycle labels:
- Cycle 1 (2020): cold baseline, prior only
- Cycle 2 (2021): first observations stored
- Cycle 3 (2022): Bayesian posterior diverges from prior
- Cycle 4 (2023): retraining triggered
- Cycle 5 (2024): shadow model evaluated

### Step 3 – Brier score table
Printed to stdout; shows convergence across cycles per risk type.

### Step 4 – Model version history
Shows `ModelRegistry.model_versions()` — version strings like `v1.15` indicate
15 updates per model (4 risk types × ~3–4 sites × events).

### Step 5 – PCC integration check
Runs `ForecastPipeline` one more time and verifies the three PCC-consumed values:
- `scale_factor` (c5ai_vs_static_ratio)
- `loss_fractions` (sum to exactly 1.0)
- `total_expected_annual_loss`

### Step 6 – Backward compatibility assertion
Confirms that `scale_factor`, `loss_fractions` are accessible and sum-correct — the
MonteCarloEngine can consume the forecast without any changes.

---

## Expected Output

```
=================================================================
C5AI+ Self-Learning Loop Demo
=================================================================

Step 1: Generating synthetic 3-site, 5-year operator input...
  Operator: Demo Salmon AS (DEMO_OP)
  Sites: 3
  Env observations: 150
  Lice observations: 780

Step 2: Running 5 learning cycles (2020-2024)...
  Cycle 1 (year=2020) [cold]    - cold baseline, prior only
  Cycle 2 (year=2021) [cold]    - first observations stored
  Cycle 3 (year=2022) [warming] - Bayesian posterior diverges from prior
  Cycle 4 (year=2023) [warming] - retraining triggered
  Cycle 5 (year=2024) [warming] - shadow model evaluated

Step 3: Brier Score Table (lower = better; 0.25 = uninformative)
-----------------------------------------------------------------
Risk Type       Cycle 1  Cycle 2  Cycle 3  Cycle 4  Cycle 5
-----------------------------------------------------------------
hab              0.2677   0.2539   0.1879   0.1495   0.1706
lice             0.0900   0.0626   0.0479   0.0388   0.0326
jellyfish        0.2864   0.2668   0.2564   0.2070   0.1736
pathogen         0.8100   0.5632   0.4313   0.3493   0.3248
-----------------------------------------------------------------

Step 4: Model Version History
  Risk Type       Version
  hab             v1.15
  jellyfish       v1.15
  lice            v1.15
  pathogen        v1.15

Step 5: Integrating final enriched forecast with MonteCarloEngine...
  Scale factor vs. static: 11.0655
  Total E[annual loss]: NOK 55.33M
  Loss fractions: {'hab': '16.3%', 'lice': '4.3%', 'jellyfish': '4.3%', 'pathogen': '75.1%'}

Step 6: PCC Compatibility Check
  scale_factor accessible:   True
  loss_fractions accessible: True
  loss_fractions sum to 1:   True
  [OK] PCC interface fully backward-compatible

Final learning status: warming
Cycles completed:      5
Models promoted:       none
```

---

## Reading the Brier Score Table

| Risk type | Pattern | Explanation |
|---|---|---|
| lice | Starts low (0.09), improves steadily | Dense weekly data → prior was already well-calibrated; small refinement |
| hab | Starts near uninformative (0.27), drops to 0.15 | Summer seasonality captured after 3–4 cycles |
| jellyfish | Slow convergence | Low event rate, sparse alerts → needs more cycles |
| pathogen | Starts very high (0.81), halves by cycle 5 | Low prior (10%) vs. high simulated event rate; Bayesian update corrects rapidly |

A Brier score > 0.25 (uninformative) occurs when the model's predicted probability
is consistently on the wrong side of the observed frequency — this is expected for
pathogen on cycle 1 because the default prior (10%) is far below the simulated event
rate in the synthetic data.

---

## Using LearningLoop in Your Own Code

```python
from c5ai_plus.learning.learning_loop import LearningLoop
from c5ai_plus.simulation.site_data_simulator import SiteDataSimulator

# 1. Build or load your operator input
sim = SiteDataSimulator(seed=42)
operator_input = sim.generate_operator_input(n_sites=3, n_years=5)

# 2. Create loop (persistent store)
loop = LearningLoop(store_dir="/data/c5ai_learning", verbose=True)

# 3. Run annual cycles
for year in range(2020, 2025):
    result = loop.run_cycle(
        operator_input,
        static_mean_annual_loss=22_600_000,
        forecast_year=year,
        observed_events=None,   # or provide real ObservedEvent list
    )
    print(f"Year {year}: status={result.learning_status}, "
          f"retrained={result.retrain_triggered}")

# 4. Use final forecast with PCC MonteCarloEngine (unchanged interface)
from c5ai_plus.pipeline import ForecastPipeline
pipeline = ForecastPipeline(verbose=False)
forecast = pipeline.run(operator_input, static_mean_annual_loss=22_600_000)
print(f"Scale factor: {forecast.scale_factor:.4f}")
print(f"Loss fractions: {forecast.loss_fractions}")
```

---

## Providing Real Observed Events

When operator-reported losses are available, pass them directly:

```python
from c5ai_plus.data_models.learning_schema import ObservedEvent
from datetime import datetime, timezone

events = [
    ObservedEvent(
        operator_id="MY_OP",
        site_id="MY_OP_S01",
        risk_type="hab",
        event_year=2023,
        observed_at=datetime.now(timezone.utc).isoformat(),
        event_occurred=True,
        actual_loss_nok=1_800_000.0,
        source="operator_reported",
    ),
    ObservedEvent(
        operator_id="MY_OP",
        site_id="MY_OP_S01",
        risk_type="lice",
        event_year=2023,
        observed_at=datetime.now(timezone.utc).isoformat(),
        event_occurred=False,
        actual_loss_nok=0.0,
        source="operator_reported",
    ),
]

result = loop.run_cycle(operator_input, 22_600_000, 2023, observed_events=events)
```
