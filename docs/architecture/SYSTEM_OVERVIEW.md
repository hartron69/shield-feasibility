# Shield Risk Platform — System Architecture Overview

**Version:** C5AI+ v5.0 | **Date:** 2026-03-10

---

## 1. Purpose

Shield Risk Platform answers a single business question for Norwegian salmon farming operators:

> *Is a Protected Cell Captive (PCC) insurance structure economically viable for this operator, and by how much does it reduce the total cost of risk compared with conventional insurance?*

It answers this by combining stochastic loss simulation with biological risk intelligence (C5AI+), producing a 13-page board-ready PDF report alongside an interactive web GUI.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        React GUI (port 5173)                │
│  Overview · Inputs · C5AI+ · Alerts · Feasibility ·        │
│  Strategy Comparison · Learning · Reports                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST / JSON
┌──────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend (port 8000)                 │
│  POST /api/feasibility/run                                   │
│  POST /api/feasibility/example                              │
│  GET  /api/mitigation/library                               │
│  GET  /static/reports/<uuid>.pdf                            │
└──────┬────────────────────────────────────────┬─────────────┘
       │                                        │
┌──────▼──────────┐                  ┌──────────▼──────────────┐
│  PCC Pipeline   │                  │     C5AI+ v5.0          │
│  (9 steps)      │                  │     (7 steps)           │
│                 │                  │                         │
│  MonteCarloEng  │◄─── scale ───────│  ForecastPipeline       │
│  SuitabilityEng │     factor       │  HAB / Lice / Jellyfish │
│  CostAnalyzer   │                  │  Pathogen forecasters   │
│  PDFReport      │                  │  AlertEngine            │
│  StrategyModels │                  │  LearningLoop           │
└─────────────────┘                  └─────────────────────────┘
```

---

## 3. Backend Layer

### FastAPI Application (`backend/main.py`)
- **CORS** allows `http://localhost:5173`
- Generated PDFs are written to `backend/static/reports/` and served as static files
- The API is stateless — each `/run` call executes the full pipeline independently

### Operator Builder (`backend/services/operator_builder.py`)
Translates the simplified GUI form into a full `OperatorInput`:

```
SimplifiedProfile (from GUI)
  ↓
build_operator_input()
  ├── TIV-scale risk severity vs. template operator
  ├── √(n_sites)-scale expected annual events
  ├── Derive financial ratios (EBITDA, equity, FCF, assets) from revenue
  ├── Compute biomass valuation: ref_price × 1000 × realisation × (1 − haircut)
  └── Return (OperatorInput, AllocationSummary)
```

### Pydantic Schema (`backend/schemas.py`)
Key models: `FeasibilityRequest`, `FeasibilityResponse`, `AllocationSummary`, `BiomassValuationSummary`, `HistoricalLossSummary`, `PoolingResult`.

---

## 4. PCC Feasibility Pipeline

Implemented in `main.py` and `backend/services/run_analysis.py`. Nine sequential steps:

```
Step 1  Load & validate OperatorInput
Step 2  Monte Carlo simulation (N × 5yr annual losses)
Step 3  Apply cross-domain correlation to loss fractions
Step 4  Evaluate selected insurance strategy (PCC / full / hybrid / self)
Step 5  Apply mitigation actions (probability + severity reduction)
Step 6  6-criterion suitability scoring → verdict
Step 7  Cost analysis — TCOR, 5yr comparison baseline vs. mitigated
Step 8  Correlated risk analytics — scenarios, tail analysis, board narratives
Step 9  PDF report generation (optional) → /static/reports/<uuid>.pdf
```

### Monte Carlo Engine (`models/monte_carlo.py`)

**Loss model:**
```
Annual aggregate loss  S_t = Σ_{i=1}^{N_t} X_i
N_t ~ Poisson(λ)              event frequency
X_i ~ LogNormal(μ_X, σ_X)    individual severity
```

Parameters are derived from `(mean, CV)`:
```
σ_X = √(ln(1 + CV²))
μ_X = ln(mean) − σ_X²/2
```

CAT overlay: with probability `p_cat`, inject one additional event at `cat_multiplier × base_mean`.

**Correlation extensions:**
- `RiskCorrelationMatrix` — Gaussian copula via Cholesky for site-level correlation
- `RegimeModel` — three regimes (75% normal, 20% elevated ×1.8, 5% catastrophic ×3.5)
- `DomainCorrelationMatrix` — 4×4 cross-domain (bio / env / structural / operational); expert default: bio-struct=0.20, env-struct=0.60, env-bio=0.40, ops-struct=0.35
- Domain perturbation: additive Gaussian shift on simplex, clip ≥ 0, renormalise

### Suitability Engine (`analysis/suitability_engine.py`)

Six weighted criteria assessed on a 0–100 scale:

| # | Criterion | Weight |
|---|---|---|
| 1 | Premium Volume | 22.5% |
| 2 | Loss Stability | 18.0% |
| 3 | Balance Sheet Strength | 18.0% |
| 4 | Cost Savings Potential | 18.0% |
| 5 | Operational Readiness | 13.5% |
| 6 | Biological Operational Readiness | 10.0% |

Verdicts: ≥72 STRONGLY RECOMMENDED · 55–71 RECOMMENDED · 40–54 POTENTIALLY SUITABLE · 25–39 NOT RECOMMENDED · <25 NOT SUITABLE.

Hard gates: >5% PCC/FI excess → cap at POTENTIALLY SUITABLE; >15% → NOT RECOMMENDED.

### PCC Captive Economics (`models/pcc_economics.py`, `models/strategies/pcc_captive.py`)

```
RI structure:   net = min(loss, retention)
                ri_recovery = min(max(loss − retention, 0), ri_limit)
RI premium:     E[ri_recovery] × loading_factor   (burning-cost)
SCR:            VaR(99.5%) of net retained loss distribution (bounded at retention)
Presets:        conservative (2.5× RI loading) · base (1.75×) · optimised (1.25×)
```

### Mitigation Library (`analysis/mitigation.py`)
12 predefined actions covering biological, environmental, structural, and operational domains. Each action specifies: `probability_reduction`, `severity_reduction`, `annual_cost_nok`, `capex_nok`, `targeted_risk_types`.

---

## 5. C5AI+ Module

### Forecasting Pipeline (`c5ai_plus/pipeline.py`)

Seven steps executed per operator:

```
Step 1  Load & validate biological input data
Step 2  Build site risk network (networkx, optional)
Step 3  Run per-site forecasters for all 4 risk types
Step 4  Apply network risk multipliers (connected sites amplify each other)
Step 5  Aggregate site forecasts to operator level
Step 6  Assemble metadata + validate
Step 7  Export to risk_forecast.json (optional)
```

### Risk Types and Forecasters

| Risk Type | Forecaster | Key Drivers |
|---|---|---|
| HAB | `HABForecaster` | Surface temperature, nitrate, chlorophyll-a |
| Sea Lice | `LiceForecaster` | Lice count, water temp, treatment history, exposure |
| Jellyfish | `JellyfishForecaster` | Seasonal patterns, current data, sightings history |
| Pathogen | `PathogenForecaster` | Neighbour outbreaks, biomass density, operational stress |

Output per site per year per risk type: `event_probability`, `expected_loss_mean/p50/p90`, `confidence_score`, `data_quality_flag`, `model_used`.

### Data Quality Flags
`SUFFICIENT` (high confidence) · `LIMITED` (medium) · `POOR` (low) · `PRIOR_ONLY` (no site data)

### C5AI+ ↔ PCC Integration Point
```python
ForecastPipeline.run(operator_input, static_mean_annual_loss)
  → RiskForecast.operator_aggregate.c5ai_vs_static_ratio
  → RiskForecast.operator_aggregate.loss_breakdown_fractions
```
These feed into PCC cell pricing and the Biological Operational Readiness criterion (10% weight).

---

## 6. Alert Engine

### Architecture (`c5ai_plus/alerts/`)

```
AlertEngine.generate_alerts(site_forecasts, previous_probabilities, env_data)
  │
  ├── PatternDetector.detect(site_id, risk_type, current_prob, env_data)
  │     → (precursor_score ∈ [0,1], List[PatternSignal])
  │     15 AlertRules across 4 risk types; weighted combination
  │     Graceful fallback when env_data absent (probability proxy)
  │
  ├── ProbabilityShiftDetector.detect(...)
  │     → ProbabilityShiftSignal
  │     Triggers on: |Δp| > 0.10 (absolute) OR Δp/p_prev > 0.50 (relative)
  │     OR threshold crossing at p=0.10 or p=0.20
  │
  ├── _determine_level(precursor_score, current_prob, shift_triggered)
  │     CRITICAL  : score ≥ 0.70  OR  prob ≥ 0.35
  │     WARNING   : score ≥ 0.45  OR  prob ≥ 0.25
  │     WATCH     : score ≥ 0.25  OR  shift triggered
  │     NORMAL    : otherwise
  │
  └── AlertExplainer.explain(alert, pattern_signals, shift_signal)
        Fills explanation_text and recommended_actions
        Sets board_visibility=True for CRITICAL
```

### AlertRecord Fields
`alert_id` · `site_id` · `risk_type` · `alert_type` (pattern / probability_shift / composite) · `alert_level` · `current_probability` · `previous_probability` · `probability_delta` · `top_drivers` · `triggered_rules` · `explanation_text` · `recommended_actions` · `workflow_status` · `board_visibility` · `generated_at`

### Alert Store
JSON persistence at `{root}/alerts/{site_id}/{year}.json`.

---

## 7. Self-Learning Module

### Loop (`c5ai_plus/learning/learning_loop.py`)

```
LearningLoop.run_cycle(operator_id, risk_type, year)
  1.  Fetch pending predictions (PredictionStore)
  2.  Load observed events (EventStore)
  3.  Match predictions ↔ events
  4.  Evaluate: Brier, log-loss, MAE, calibration slope
  5.  Decide: retrain or skip
  6.  RetrainingPipeline.retrain() → new model version
  7.  ShadowModeManager: shadow-validate new model
  8.  Promote if shadow score validates
  9.  Persist to ModelRegistry
  10. Return LearningCycleResult
```

### Model Selection
| Observations | Model |
|---|---|
| n < 20 | `BetaBinomialModel` — conjugate Bayesian, works from first sample |
| n ≥ 20 | `SklearnProbabilityModel` — Random Forest |

Severity: `LogNormalSeverityModel` using online Welford MLE throughout.

**Learning status:** cold (<3 cycles) · warming (3–9) · active (≥10)

---

## 8. Frontend Architecture

### Navigation Model (`frontend/src/App.jsx`)

All state is managed in the root `App` component. Navigation is client-side with no routing library.

```
FEASIBILITY_PAGES = {'feasibility', 'strategy'}
  → These pages render the left accordion panel (PCC inputs)
  → All other pages are full-width
```

### 8 Pages

| Page | Component | Data Source |
|---|---|---|
| Overview | `OverviewPage` | `C5AI_MOCK`, `MOCK_ALERTS`, `mockInputsData` |
| Inputs | `InputsPage` (5 tabs) | `mockInputsData`, `mockBioTimeseries` |
| C5AI+ Risk Intelligence | `C5AIModule` (5 tabs) | `C5AI_MOCK`, live `result` |
| Alerts | `AlertsPage` | `MOCK_ALERTS` |
| PCC Feasibility | `ResultPanel` (8 tabs) | live `result` from API |
| Strategy Comparison | `StrategyComparisonPage` | live `result` + static illustrative values |
| Learning | `LearningPage` | `C5AI_MOCK` learning fields |
| Reports | `ReportsPage` | `result.report.pdf_url` |

### Inputs Page — Biological Charts

The Biological Inputs tab renders interactive SVG time-series charts for 11 environmental parameters across 3 sites:
- **No charting library** — pure SVG with Catmull-Rom smooth spline
- Baseline reference line (dashed grey) + risk threshold line (dashed red)
- Hover tooltip (nearest-point detection via viewBox coordinate scaling)
- Threshold-breached cards highlighted in red
- Group filter: Temperatur & oksygen · Næringsstoffer & alger · Salinitet · Lus & behandlinger · Biologiske hendelser

### API Client (`frontend/src/api/client.js`)
Three functions: `fetchMitigationLibrary()`, `fetchExample()`, `runFeasibility(payload)`.
All target `http://localhost:8000`.

---

## 9. Data Consistency

All mock data references the same three demo sites:

| ID | Name | Character |
|---|---|---|
| `DEMO_OP_S01` | Frohavet North | Open coast · exposure 1.40 · highest risk |
| `DEMO_OP_S02` | Sunndalsfjord | Semi-exposed · exposure 1.10 |
| `DEMO_OP_S03` | Storfjorden South | Sheltered · exposure 0.85 · lowest risk |

Files that reference these IDs: `mockInputsData.js`, `mockAlertsData.js`, `mockBioTimeseries.js`, `c5ai_mock.js`, `alert_simulator.py`.

---

## 10. Test Coverage

```
tests/
  test_alert_layer.py              64 tests — alert engine, rules, store, simulator
  test_learning_loop.py            66 tests — 9 test classes (full learning cycle)
  test_operator_builder.py         31 tests — TIV scaling, financial ratios
  test_pcc_calibration.py          37 tests — PCCAssumptions, RI structure, SCR
  test_pcc_report_fixes.py         21 tests — TCOR correctness, cost breakdown
  test_biomass_valuation.py        25 tests — formula, override, schema
  test_backend_api.py              16 tests — FastAPI endpoints (TestClient)
  test_correlation.py              44 tests — RiskCorrelationMatrix
  test_regime_model.py             28 tests — RegimeModel
  + 27 additional test files            — risk domains, mitigation, forecasting, pooling
                                   ─────
  Total                          1 092 passed · 0 failed
```

---

## 11. Deployment Notes

| Component | Command | Port |
|---|---|---|
| Backend API | `uvicorn backend.main:app --reload --port 8000` | 8000 |
| Frontend dev | `cd frontend && npm run dev` | 5173 |
| Frontend build | `cd frontend && npm run build` | — |
| CLI (headless) | `python main.py` | — |

**Production:** The frontend `dist/` folder can be served by any static file host. The backend requires Python 3.11+ and access to the file system for PDF generation.

**Not yet production-ready:**
- Learning store uses local JSON files (not suitable for multi-user)
- `/api/c5ai/scenario` route is not yet implemented (scenario panel runs client-side stub)
- No authentication layer
