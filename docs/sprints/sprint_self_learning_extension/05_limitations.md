# Self-Learning Extension – Known Limitations

## Scope Boundaries (by Design)

These are deliberate simplifications for a feasibility-grade tool, not defects:

### 1. File-based storage — no concurrent access safety
Each JSON file is overwritten atomically per Python's `open(..., 'w')` call.
In a production setting with multiple workers, a proper database or append-only log
would be needed. For a single-operator CLI or API server this is safe.

### 2. Shadow model uses same pairs as production
In `LearningLoop._step9`, shadow evaluation passes the same matched pairs as the
production model. A rigorous A/B test would require the shadow to have made its own
stored predictions for independent pairs. This is architecturally possible (shadow
predictions are separate in-memory), but was deferred as the current approach is
sufficient to detect gross quality differences.

### 3. Prediction store saves only `year=1` forecast per cycle
`_save_predictions` skips `rtf.year > 1` to avoid storing duplicate records for the
same calendar year across multi-year forecast horizons. This means only the first
forecast year is matched against observations. Years 2–5 of the RiskForecast are
available for planning but not tracked in the learning loop.

### 4. SklearnProbabilityModel uses index-as-feature only
The RF model is trained on `[[0], [1], ..., [n]]` as features — just the temporal
index. It will not outperform BetaBinomial until there are enough observations to
reveal a non-trivial temporal trend. Real improvement requires domain features
(temperature, prior lice counts, season) to be passed into `predict(features=...)`.

### 5. Cross-risk correlation in EventSimulator is one-directional
HAB occurrence elevates other bio-event probabilities by 15%. The reverse (e.g., high
lice burden elevating pathogen risk) is not modelled. A full conditional dependency
graph would require more data to parameterise.

### 6. Shadow promotion uses Brier on the same dataset twice
The shadow Brier is computed from the same observed events as the production model
(both use `current_pairs`). This is intentional for the first implementation — a true
holdout set requires a longer observation history than feasibility-grade operators
typically have.

### 7. Severity model has no site-level segmentation
`LogNormalSeverityModel` is per `(operator_id, risk_type)`, averaging across all sites.
Sites with systematically different exposure levels (open coast vs. sheltered fjord)
are not distinguished in the severity model.

### 8. No model expiry / staleness detection
A model is never marked stale if it has not been updated for several years. In a
production system, a model trained on 2020–2022 data should be weighted less when
predicting 2030 outcomes. This was deferred.

### 9. `learning_store_dir` defaults to a relative path
`"c5ai_plus/learning/store"` is relative to the current working directory. If the tool
is invoked from a different directory the store will be created there instead. Users
running from outside the project root should set `C5AI_SETTINGS.learning_store_dir`
to an absolute path.

### 10. No persistence of cycle counter across process restarts
`LearningLoop._cycle_counters` is an in-memory dict. After a process restart, the
counter resets to 0, so `get_learning_status()` will return `"cold"` even for an
operator with many stored predictions. A follow-on sprint should persist the cycle
count alongside the model registry.

---

## Potential Follow-On Work

| Item | Effort | Priority |
|---|---|---|
| Persist cycle counter in registry JSON | XS | High |
| Site-level severity segmentation | S | Medium |
| Domain features in RF model (temp, season, biomass) | M | Medium |
| True holdout set for shadow evaluation | M | Medium |
| Reverse cross-risk correlation (lice → pathogen) | S | Low |
| Model staleness detection + expiry | M | Low |
| Async / background retraining trigger | L | Low |
| REST endpoint: `POST /api/learning/cycle` | M | Low |
