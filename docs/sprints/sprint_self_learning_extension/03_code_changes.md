# Self-Learning Extension – Code Changes

## New Files (13 + 3 `__init__.py`)

### `c5ai_plus/data_models/learning_schema.py`
Four JSON-serialisable dataclasses:

| Class | Purpose |
|---|---|
| `PredictionRecord` | One stored prediction: operator/site/risk_type/year + probability + loss mean |
| `ObservedEvent` | One observed outcome: event_occurred (bool) + actual_loss_nok |
| `EvaluationMetrics` | Brier, log-loss, severity MAE/RMSE, calibration slope, n_samples |
| `LearningCycleResult` | Full cycle summary: metrics by risk type, retrain flag, models promoted, status |

All classes implement `to_dict()` / `from_dict()` for JSON persistence.

---

### `c5ai_plus/models/probability_model.py`

**`BetaBinomialModel`**
- Beta-Binomial conjugate. Prior: `Beta(prior_prob × conc, (1-prior_prob) × conc)`.
- `update(event_occurred)` → α += event, β += (1-event). Posterior mean = α/(α+β).
- Works from the very first observation. No sklearn required.
- Version string increments monotonically on each update.

**`SklearnProbabilityModel`**
- RandomForestClassifier wrapper. Only viable when `n_observations ≥ 20`.
- Falls back gracefully to BetaBinomial if sklearn is unavailable (via `probability_model_from_dict()` factory).
- Stores full observation history to allow refit from scratch.

Both share `BaseProbabilityModel` ABC: `predict()`, `update()`, `version`, `to_dict()`, `from_dict()`.

---

### `c5ai_plus/models/severity_model.py`

**`LogNormalSeverityModel`**
- Online Welford's algorithm for running log-space mean and M2 (no history stored).
- `predict(biomass_value_nok=None)` → `(mean, p50, p90)` in NOK.
- Falls back to prior-based estimate when `n_obs < 3`.
- Ignores non-positive loss values silently.

---

### `c5ai_plus/models/model_registry.py`

**`ModelRegistry`**
- Manages one probability model + one severity model per `(operator_id, risk_type)`.
- Lazy-loads from disk on first access; writes on each update.
- Shadow model dict is in-memory only (not persisted); promotion writes to disk.
- `model_versions(operator_id)` → `Dict[risk_type, version_str]`.

Key methods:
```
get_probability_model(op, rt) → BaseProbabilityModel
update_probability_model(op, rt, event_occurred) → version_str
get_severity_model(op, rt) → LogNormalSeverityModel
update_severity_model(op, rt, loss_nok) → version_str
register_shadow(op, rt, candidate)
get_shadow_model(op, rt) → Optional[BaseProbabilityModel]
promote_shadow(op, rt) → bool
model_versions(op) → Dict[str, str]
```

---

### `c5ai_plus/learning/prediction_store.py`

**`PredictionStore`**
- `save(record)` → `predictions/{op}/{rt}_{year}.json` (overwrites same key).
- `load(op, rt, year)` → `Optional[PredictionRecord]`.
- `load_all(op)` → `List[PredictionRecord]` (all risk types and years).
- `list_years(op, rt)` → `List[int]`.

---

### `c5ai_plus/learning/event_store.py`

**`EventStore`**
- `save(events)` → merges into `events/{op}/{year}.json` keyed by `(site_id, risk_type)`.
- `load(op, year)` → `Optional[List[ObservedEvent]]`.
- `load_all(op)` → `List[ObservedEvent]` (all years).
- `matched_pairs(op, rt, predictions)` → `List[Tuple[PredictionRecord, ObservedEvent]]`
  — inner join on `(risk_type, year)`.

---

### `c5ai_plus/learning/evaluator.py`

**`Evaluator`** (stateless)

| Metric | Formula | Perfect | Uninformative |
|---|---|---|---|
| Brier score | E[(p − y)²] | 0.0 | 0.25 |
| Log loss | −E[y·log p + (1−y)·log(1−p)] | 0.0 | log(2) ≈ 0.693 |
| Mean prob. error | mean(p) − mean(y) | 0.0 | — |
| Severity MAE | Mean \|pred − actual\| on events | 0.0 | — |
| Severity RMSE | RMS of above | 0.0 | — |
| Calibration slope | Linear regression slope actuals ~ probs | 1.0 | — |

`should_retrain(metrics, min_samples)` → True when `n_samples ≥ min_samples AND brier > 0.10`.
`is_shadow_better(current, shadow, min_improvement)` → True when shadow Brier is at least `min_improvement` lower and `shadow.n_samples ≥ learning_shadow_min_samples`.

---

### `c5ai_plus/simulation/site_data_simulator.py`

**`SiteDataSimulator`**

Generates a complete `C5AIOperatorInput` with domain-realistic synthetic observations:

| Signal | Domain logic |
|---|---|
| Temperature | `T(m) = T_mean + 5.5·sin(2π(m-3)/12) + ε`; latitude-dependent mean |
| HAB alerts | Higher P in months 4–9, at open_coast exposure, in warm years |
| Sea lice | Spring (wk 12–20) + autumn (wk 36–44) peaks; treatment reduces counts |
| Jellyfish | Summer bloom (Jul–Sep), low base rate |
| Pathogen | 0–2 events/year, confirmed with 60% probability |

---

### `c5ai_plus/simulation/event_simulator.py`

**`EventSimulator`**

- `simulate_year(forecast, year, op)` → `List[ObservedEvent]`.
- Two-pass: HAB events drawn first; HAB occurrence elevates other bio-event P by 15%.
- Loss drawn from `LogNormal(mean=expected_loss_mean, cv=0.60)` when event occurs.
- `simulate_multi_year(forecast, start_year, n_years, op)` → `Dict[year, List[ObservedEvent]]`.

---

### `c5ai_plus/learning/retraining_pipeline.py`

**`RetrainingPipeline`**

1. Loads all `ObservedEvent` for the operator/risk_type from `EventStore`.
2. If `n ≥ 20`: fits `SklearnProbabilityModel`; else: builds `BetaBinomialModel`.
3. Registers candidate as shadow via `ModelRegistry.register_shadow()` — does NOT auto-promote.
4. `retrain_all(op)` → `Dict[risk_type, bool]` (True = retrained, False = no data).

---

### `c5ai_plus/learning/shadow_mode.py`

**`ShadowModeManager`**

- `run_shadow_prediction(op, rt)` → `Optional[float]` (None if no shadow registered).
- `evaluate_and_promote(op, rt, current_pairs, shadow_pairs)` → `bool`.

---

### `c5ai_plus/learning/learning_loop.py`

**`LearningLoop`** — main entry point

```python
loop = LearningLoop(store_dir="c5ai_plus/learning/store", verbose=False)
result = loop.run_cycle(
    operator_input,
    static_mean_annual_loss=5_000_000,
    forecast_year=2023,
    observed_events=None,   # None → auto-simulate
)
```

`run_cycle()` executes all 10 steps; returns `LearningCycleResult`.
`get_learning_status(operator_id)` → `"cold" | "warming" | "active"`.

---

## Modified Files (3)

### `c5ai_plus/config/c5ai_settings.py`

Added to `C5AISettings` frozen dataclass (all have defaults → backward compatible):

```python
learning_store_dir: str = "c5ai_plus/learning/store"
learning_min_samples_to_evaluate: int = 5
learning_retrain_trigger_samples: int = 5
learning_shadow_min_samples: int = 10
learning_shadow_min_improvement: float = 0.05
learning_bayesian_concentration: float = 5.0
```

---

### `c5ai_plus/data_models/forecast_schema.py`

Added to `RiskTypeForecast` (all `Optional` with `None` default):
```python
baseline_probability: Optional[float] = None    # pre-enrichment probability
adjusted_probability: Optional[float] = None    # Bayesian posterior
brier_score_recent: Optional[float] = None
severity_mae_recent: Optional[float] = None
```

Added to `ForecastMetadata` (all with defaults):
```python
learning_status: str = "cold"
cycles_completed: int = 0
last_retrain_at: Optional[str] = None
probability_model_versions: Dict[str, str] = field(default_factory=dict)
severity_model_versions: Dict[str, str] = field(default_factory=dict)
```

`from_dict()` already uses field-name filtering, so existing JSON files load correctly.

---

### `c5ai_plus/forecasting/base_forecaster.py`

`forecast()` gains an optional `model_registry=None` parameter:

```python
def forecast(self, site_data, forecast_years, model_registry=None):
    ...
    if model_registry is not None:
        posterior_prob = model_registry.get_probability_model(op_id, rt).predict()
        rtf.baseline_probability = original_prob
        rtf.adjusted_probability = posterior_prob
    # event_probability is unchanged → MonteCarloEngine unaffected
```

Default `model_registry=None` → original behaviour. All subclasses (`HABForecaster`,
`LiceForecaster`, `JellyfishForecaster`, `PathogenForecaster`) inherit the change
without modification.
