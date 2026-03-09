# Self-Learning Extension – Architecture

## Package Layout

```
c5ai_plus/
  learning/                    NEW PACKAGE – orchestration layer
    __init__.py
    prediction_store.py        Persist / load PredictionRecord (JSON)
    event_store.py             Persist / load ObservedEvent + matched-pair join
    evaluator.py               Brier, log-loss, severity MAE, calibration slope
    retraining_pipeline.py     Choose BetaBinomial or RF; register as shadow
    shadow_mode.py             Shadow prediction + promote-if-better
    learning_loop.py           LearningLoop.run_cycle() – 10-step orchestration
    store/                     RUNTIME storage root (gitignored)
      registry/{op}/{rt}.json
      predictions/{op}/{rt}_{year}.json
      events/{op}/{year}.json

  models/                      NEW PACKAGE – per-risk-type model objects
    __init__.py
    probability_model.py       BetaBinomialModel + SklearnProbabilityModel
    severity_model.py          LogNormalSeverityModel (Welford online MLE)
    model_registry.py          ModelRegistry – load/save/version/shadow/promote

  simulation/                  NEW PACKAGE – plausible synthetic data
    __init__.py
    site_data_simulator.py     SiteDataSimulator → C5AIOperatorInput
    event_simulator.py         EventSimulator → ObservedEvent list

  data_models/
    learning_schema.py         NEW – PredictionRecord, ObservedEvent,
                                      EvaluationMetrics, LearningCycleResult
    forecast_schema.py         MODIFIED – +learning fields (all optional)

  config/
    c5ai_settings.py           MODIFIED – +6 learning constants

  forecasting/
    base_forecaster.py         MODIFIED – forecast(model_registry=None)
```

---

## Data Flow

```
C5AIOperatorInput
        │
        ▼
  ForecastPipeline.run()          (existing, unchanged)
        │
        ▼
  RiskForecast
   ├─ scale_factor  ──────────────────────── MonteCarloEngine (unchanged)
   ├─ loss_fractions ─────────────────────── MonteCarloEngine (unchanged)
   └─ site_forecasts[].annual_forecasts[]
         ├─ event_probability      (static C5AI estimate)
         ├─ baseline_probability   (same as above, for audit)
         └─ adjusted_probability   (Bayesian posterior from ModelRegistry)

LearningLoop.run_cycle()
  Step 1  ForecastPipeline.run()
  Step 2  Enrich adjusted_probability from ModelRegistry
  Step 3  Save PredictionRecord → PredictionStore
  Step 4  ObservedEvents (provided or EventSimulator)
  Step 5  Save ObservedEvent → EventStore
  Step 6  ModelRegistry.update_probability_model()
          ModelRegistry.update_severity_model()
  Step 7  EventStore.matched_pairs() → Evaluator.evaluate() → EvaluationMetrics
  Step 8  Evaluator.should_retrain() → RetrainingPipeline.retrain()
  Step 9  ShadowModeManager.evaluate_and_promote()
  Step 10 Return LearningCycleResult
```

---

## Probability Model Selection

```
n_observations < 20  →  BetaBinomialModel
                         Prior: Beta(α₀, β₀)
                         α₀ = prior_prob × concentration  (default conc = 5.0)
                         Update: α += event; β += (1 - event)
                         Posterior mean = α / (α + β)

n_observations ≥ 20  →  SklearnProbabilityModel
                         RandomForestClassifier(n_estimators=50, class_weight="balanced")
                         Falls back to BetaBinomial if sklearn unavailable
```

---

## Severity Model

```
LogNormalSeverityModel
  Online Welford's algorithm for running log-space mean + variance
  n_obs < 3  →  prior prediction: E[loss] = biomass_value × 0.10
  n_obs ≥ 3  →  predict() → (mean, p50, p90) from fitted LogNormal
```

---

## Storage Layout

```
{learning_store_dir}/
  registry/{operator_id}/{risk_type}.json
    {
      "probability_model": { BetaBinomial or RF state },
      "severity_model":    { LogNormal state }
    }

  predictions/{operator_id}/{risk_type}_{year}.json
    { PredictionRecord fields }

  events/{operator_id}/{year}.json
    [ { ObservedEvent fields }, ... ]   ← list, merged on (site_id, risk_type)
```

Default `learning_store_dir = "c5ai_plus/learning/store"` (configurable via `C5AISettings`).

---

## Shadow Model Lifecycle

```
RetrainingPipeline.retrain()
  → new candidate model
  → ModelRegistry.register_shadow()         (NOT yet in production)

ShadowModeManager.evaluate_and_promote()
  → current metrics vs. shadow metrics
  → if shadow.brier_score < current.brier_score - 0.05
     AND shadow.n_samples ≥ 10
  → ModelRegistry.promote_shadow()          (replaces production model)
```

---

## PCC Compatibility Guarantee

The learning layer is a **read-only enrichment** from the PCC engine's perspective:

| PCC interface | Change | Guarantee |
|---|---|---|
| `RiskForecast.scale_factor` | None | Identical to pre-learning pipeline |
| `RiskForecast.loss_fractions` | None | Identical to pre-learning pipeline |
| `MonteCarloEngine` inputs | None | Only reads scale_factor + loss_fractions |
| `BaseForecaster.forecast()` | `model_registry=None` | Default = original behaviour |
| `ForecastPipeline.run()` | None | Unchanged signature |
| `RiskForecast.from_dict()` | Handles new optional fields via defaults | Zero breakage on old JSON |
