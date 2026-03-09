# Self-Learning Extension – Sprint Summary

**Date:** 2026-03-10
**Status:** Complete
**Test count:** 1028 passed, 0 failed (826 before sprint → +202 new, 66 in this sprint's test file)

---

## Objective

Add a full **predict → observe → evaluate → retrain** loop to C5AI+, enabling the
biological risk forecaster to improve its probability and severity estimates over time
as real (or simulated) observations accumulate.

Prior to this sprint, C5AI+ made one-shot predictions using RandomForest ML or config
priors with no memory of past outcomes and no mechanism to improve. This sprint adds:

| Capability | Before | After |
|---|---|---|
| Tracks past predictions | No | Yes – JSON per (operator, risk_type, year) |
| Incorporates observed outcomes | No | Yes – Bayesian update + MLE |
| Evaluates its own accuracy | No | Yes – Brier, log-loss, MAE, calibration |
| Retrains from accumulated data | No | Yes – BetaBinomial or RandomForest |
| Shadow model promotion | No | Yes – only promotes when materially better |
| Synthetic test data | No | Yes – seasonal + domain-correlated simulator |

---

## Key Design Principles

1. **Feasibility-grade, not production MLOps.** Storage is JSON, models are lightweight
   sklearn + Bayesian conjugates. No Kafka, no feature stores, no model servers.

2. **100% backward-compatible PCC interface.** `RiskForecast.scale_factor` and
   `RiskForecast.loss_fractions` are untouched. `MonteCarloEngine` is unaware of the
   learning layer.

3. **Individually testable.** Every component (store, model, evaluator, simulator,
   retrainer, loop) has its own test class and can be used independently.

4. **Safe defaults everywhere.** Missing data → Bayesian prior. Missing sklearn →
   BetaBinomial fallback. Cold start → prior probability. All new schema fields have
   defaults so existing JSON round-trips are unaffected.

---

## Learning Status Model

| Cycles completed | Status |
|---|---|
| 0–2 | `cold` – prior only, no meaningful posterior |
| 3–9 | `warming` – Bayesian posterior diverges from prior |
| ≥ 10 | `active` – enough history for robust evaluation |

---

## Demo Output (5 cycles, 3 sites, 2020–2024)

```
Brier Score Table (lower = better; 0.25 = uninformative)
-----------------------------------------------------------------
Risk Type       Cycle 1  Cycle 2  Cycle 3  Cycle 4  Cycle 5
-----------------------------------------------------------------
hab              0.2677   0.2539   0.1879   0.1495   0.1706
lice             0.0900   0.0626   0.0479   0.0388   0.0326
jellyfish        0.2864   0.2668   0.2564   0.2070   0.1736
pathogen         0.8100   0.5632   0.4313   0.3493   0.3248
-----------------------------------------------------------------
```

Sea lice shows the fastest learning (dense weekly observations → prior is already
well-calibrated). Pathogen starts worst (low base rate, sparse events) but converges
steadily.
