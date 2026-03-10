# Shield Risk Platform – Project State

**Date:** 2026-03-10
**Test suite:** 1 092 passed, 0 failed (38 deprecation warnings)
**Frontend build:** 0 errors · 76 modules · 28.4 kB CSS · 289 kB JS
**Backend:** FastAPI · Python · uvicorn
**Frontend:** React 18 · Vite 5 · pure SVG charts (no charting library)

---

## 1. Repository Layout

```
shield-feasibility/
│
├── main.py                          # CLI entry: 9-step PCC pipeline
├── data/sample_input.json           # Nordic Aqua Partners AS (demo operator)
│
├── config/settings.py               # Global constants (NOK thresholds, CAT params)
├── data/input_schema.py             # OperatorInput, SiteProfile dataclasses
│
├── models/                          # Core stochastic models
│   ├── monte_carlo.py               # Compound Poisson-LogNormal MC engine
│   ├── correlation.py               # RiskCorrelationMatrix (equicorrelation, Cholesky)
│   ├── regime_model.py              # RegimeModel (3 regimes: 75%/1×, 20%/1.8×, 5%/3.5×)
│   ├── domain_correlation.py        # DomainCorrelationMatrix 4×4 (Sprint 7)
│   ├── domain_loss_breakdown.py     # DomainLossBreakdown + correlated simplex perturbation
│   ├── loss_model.py                # LossView (gross/net/retained per strategy)
│   ├── pcc_economics.py             # PCCAssumptions presets, RI structure helpers
│   ├── captive_structure.py         # Cell captive capital structure
│   └── strategies/
│       ├── base_strategy.py         # AnnualCostBreakdown, StrategyResult
│       ├── full_insurance.py
│       ├── hybrid.py
│       ├── pcc_captive.py           # Fixed RI/SCR/TCOR bugs (Sprint 8b)
│       ├── pooled_pcc.py
│       └── self_insurance.py
│
├── analysis/
│   ├── suitability_engine.py        # 6-criterion suitability model → verdict
│   ├── cost_analyzer.py             # TCOR, 5yr cost comparison
│   ├── mitigation.py                # 12 PREDEFINED_MITIGATIONS
│   ├── scr_calculator.py            # Solvency Capital Requirement
│   └── volatility_metrics.py
│
├── reporting/
│   ├── pdf_report.py                # ReportLab Platypus · 13-page board PDF
│   ├── chart_generator.py           # 10 matplotlib charts → BytesIO
│   └── correlated_risk_analytics.py # Scenario extraction, tail analysis, narratives
│
├── c5ai_plus/                       # C5AI+ v5.0 – biological risk intelligence
│   ├── pipeline.py                  # ForecastPipeline (7-step orchestration)
│   ├── config/c5ai_settings.py      # C5AI_SETTINGS (priors, thresholds, version)
│   ├── data_models/
│   │   ├── biological_input.py      # C5AIOperatorInput, SiteInput
│   │   ├── forecast_schema.py       # RiskForecast, SiteForecast, RiskTypeForecast
│   │   └── learning_schema.py       # PredictionRecord, ObservedEvent, LearningCycleResult
│   ├── forecasting/
│   │   ├── base_forecaster.py       # BaseForecaster (optional model_registry= param)
│   │   ├── hab_forecaster.py
│   │   ├── lice_forecaster.py
│   │   ├── jellyfish_forecaster.py
│   │   └── pathogen_forecaster.py
│   ├── ingestion/data_loader.py     # DataLoader, SiteData
│   ├── network/site_network.py      # SiteRiskNetwork (networkx optional)
│   ├── validation/forecast_validator.py
│   ├── export/forecast_exporter.py  # → risk_forecast.json
│   ├── feature_engineering/features.py
│   ├── causal/cate_module.py
│   ├── alerts/                      # Early Warning / Alert Layer (Sprint – Alert Layer)
│   │   ├── alert_models.py
│   │   ├── alert_rules.py
│   │   ├── pattern_detector.py
│   │   ├── probability_shift_detector.py
│   │   ├── alert_engine.py
│   │   ├── alert_explainer.py
│   │   ├── alert_store.py
│   │   └── alert_simulator.py
│   ├── models/                      # Self-learning probability/severity models
│   │   ├── probability_model.py     # BetaBinomialModel, SklearnProbabilityModel
│   │   ├── severity_model.py        # LogNormalSeverityModel (Welford online MLE)
│   │   └── model_registry.py        # ModelRegistry (load/save/version/shadow/promote)
│   ├── learning/                    # predict → observe → evaluate → retrain
│   │   ├── learning_loop.py         # LearningLoop.run_cycle() – 10-step orchestration
│   │   ├── prediction_store.py
│   │   ├── event_store.py
│   │   ├── evaluator.py             # Brier, log-loss, MAE, calibration slope
│   │   ├── retraining_pipeline.py   # BetaBinomial (<20 obs) or RF (≥20 obs)
│   │   └── shadow_mode.py           # ShadowModeManager
│   └── simulation/                  # Synthetic data for learning demos
│       ├── site_data_simulator.py   # SiteDataSimulator (seasonal temp, HAB, lice)
│       └── event_simulator.py       # EventSimulator (Bernoulli + LogNormal + HAB correlation)
│
├── backend/                         # FastAPI adapter
│   ├── main.py                      # FastAPI app, CORS, static file mount
│   ├── schemas.py                   # Pydantic request/response models
│   ├── api/
│   │   ├── feasibility.py           # POST /api/feasibility/run, /example
│   │   └── mitigation.py            # GET /api/mitigation/library
│   ├── services/
│   │   ├── operator_builder.py      # SimplifiedProfile → (OperatorInput, AllocationSummary)
│   │   ├── run_analysis.py          # 9-step pipeline adapter → FeasibilityResponse
│   │   └── history_analytics.py     # Historical loss domain analytics
│   └── static/reports/              # Generated PDFs served at /static/reports/<uuid>.pdf
│
├── risk_domains/structural.py
│
├── tests/                           # 1 092 tests total across 36 test files
│
├── frontend/                        # React 18 + Vite 5 GUI
│   └── src/
│       ├── App.jsx                  # Root: 8-page nav, state, API wiring
│       ├── App.css                  # ~28 kB – all styles
│       ├── api/client.js            # fetchMitigationLibrary, fetchExample, runFeasibility
│       ├── data/
│       │   ├── c5ai_mock.js         # C5AI_MOCK – static forecast data for C5AI+ module
│       │   ├── mockAlertsData.js    # MOCK_ALERTS (10 records), MOCK_ALERT_SUMMARY
│       │   ├── mockInputsData.js    # MOCK_SITE_PROFILES, MOCK_BIOLOGICAL_INPUTS,
│       │   │                        # MOCK_ALERT_SIGNALS, MOCK_DATA_QUALITY,
│       │   │                        # SCENARIO_BASELINE, SCENARIO_PRESETS, BIO_READING_LABELS
│       │   └── mockBioTimeseries.js # MOCK_BIO_TIMESERIES, PARAM_THRESHOLDS, PARAM_COLORS
│       └── components/
│           ├── InputForm/           # PCC feasibility input accordion
│           ├── results/             # 8-tab result panel (PCC feasibility)
│           ├── c5ai/                # C5AI+ Risk Intelligence module
│           ├── alerts/              # Early warning alert components
│           └── inputs/              # Inputs page with 5 tabs
│
├── docs/sprints/SPRINT_HISTORY.md   # Chronological sprint log
└── examples/                        # Standalone demo scripts
```

---

## 2. Backend Architecture

### FastAPI Application (`backend/main.py`)
- **Title:** Shield Risk Platform API v1.0.0
- **CORS:** `http://localhost:5173` / `http://127.0.0.1:5173`
- **Static files:** `backend/static/` mounted at `/static` — PDFs served at `/static/reports/<uuid>.pdf`
- **Start:** `uvicorn backend.main:app --reload --port 8000`

### API Routes

| Method | Path | Handler |
|---|---|---|
| `GET` | `/` | Health check → `{"status": "ok"}` |
| `GET` | `/api/mitigation/library` | All 12 predefined mitigation actions |
| `POST` | `/api/feasibility/run` | Full 9-step pipeline → `FeasibilityResponse` |
| `POST` | `/api/feasibility/example` | Nordic Aqua Partners pre-filled request |

### Request Model (`FeasibilityRequest`)
```
OperatorProfileInput
  name, country, n_sites, total_biomass_tonnes
  biomass_value_per_tonne (64 800 NOK/t default)
  reference_price_per_kg, realisation_factor, prudence_haircut  ← valuation formula
  biomass_value_per_tonne_override  ← optional manual override
  annual_revenue_nok, annual_premium_nok

ModelSettingsInput
  n_simulations (100–100 000, default 5 000)
  domain_correlation: 'independent' | 'expert_default' | 'low' | 'moderate'
  generate_pdf: bool
  use_history_calibration: bool

StrategySettingsInput
  strategy: 'full_insurance' | 'hybrid' | 'pcc_captive' | 'self_insurance'
  retention_nok: Optional[float]

PoolingSettingsInput
  enabled, n_members, inter_member_correlation, similarity_spread,
  pooled_retention_nok, pooled_ri_limit_nok, pooled_ri_loading_factor,
  shared_admin_saving_pct, allocation_basis

MitigationInput
  selected_actions: List[str]  ← IDs from mitigation library
```

### Response Model (`FeasibilityResponse`)
```
baseline: ScenarioBlock          ← KPIs + base64 charts + criterion scores
mitigated: Optional[ScenarioBlock]
comparison: Optional[ComparisonBlock]
report: ReportBlock              ← pdf_url if generate_pdf
metadata: MetadataBlock
allocation: Optional[AllocationSummary]   ← TIV ratio, site breakdown, biomass valuation
history: Optional[HistoricalLossSummary]  ← domain breakdown, calibration metadata
pooling: Optional[PoolingResult]          ← diversification stats, TCOR comparison
```

### Operator Builder (`backend/services/operator_builder.py`)
Converts `OperatorProfileInput` → `(OperatorInput, AllocationSummary)`:
- Risk severity scales with TIV ratio vs. template
- Risk event frequency scales with `sqrt(n_sites)`
- Financial fields (EBITDA, equity, FCF, assets) derived from revenue via template ratios
- Biomass valuation formula: `suggested = ref_price × 1000 × realisation × (1 − haircut)`
- `applied = override if set, else biomass_value_per_tonne`

### Biomass Valuation Formula
```
suggested_NOK_per_tonne = ref_price_per_kg × 1000 × realisation_factor × (1 − prudence_haircut)
defaults: 80 × 1000 × 0.90 × 0.90 = 64 800 NOK/t
```

---

## 3. PCC Feasibility Pipeline (9 Steps — `main.py`)

1. **Load & validate** `OperatorInput` from JSON
2. **Monte Carlo simulation** — Compound Poisson-LogNormal, N simulations × 5 years
3. **Domain correlation** — Additive Gaussian perturbation on simplex
4. **Strategy evaluation** — Run selected strategy against simulation results
5. **Mitigation application** — Apply selected mitigation actions (probability + severity reduction)
6. **Suitability scoring** — 6-criterion model → composite score → verdict
7. **Cost analysis** — TCOR, 5yr cost comparison baseline vs. mitigated
8. **Correlated risk analytics** — Scenario extraction, tail analysis, board narratives
9. **PDF report** — ReportLab Platypus, 13 pages, 10 charts

### Monte Carlo Engine (`models/monte_carlo.py`)
- **Model:** Compound Poisson-LogNormal — `S_t = Σ X_i` where `N_t ~ Poisson(λ)`, `X_i ~ LogNormal`
- **CAT overlay:** With probability `p_cat`, inject extra event at `multiplier × base_mean`
- **Horizon:** N × 5 annual totals per simulation
- **Site correlation:** Gaussian copula via Cholesky decomposition when `RiskCorrelationMatrix` provided
- **Regime model:** 3 regimes (75% normal, 20% elevated ×1.8, 5% catastrophic ×3.5)
- **Domain correlation:** `DomainCorrelationMatrix` (4×4, expert-default: bio-struct=0.20, env-struct=0.60, env-bio=0.40, ops-struct=0.35)

### Suitability Engine (`analysis/suitability_engine.py`)
Six weighted criteria, 0–100 scale each:

| Criterion | Weight |
|---|---|
| Premium Volume | 22.5% |
| Loss Stability | 18.0% |
| Balance Sheet Strength | 18.0% |
| Cost Savings Potential | 18.0% |
| Operational Readiness | 13.5% |
| Biological Operational Readiness (C5AI+) | 10.0% |

Verdicts: ≥72 STRONGLY RECOMMENDED · 55–71 RECOMMENDED · 40–54 POTENTIALLY SUITABLE · 25–39 NOT RECOMMENDED · <25 NOT SUITABLE

Hard cost gate: >5% PCC/FI excess → cap at POTENTIALLY SUITABLE; >15% → NOT RECOMMENDED.

### PCC Captive Economics (`models/pcc_economics.py`, `models/strategies/pcc_captive.py`)
- **RI structure:** Annual-aggregate XL — `net = min(loss, retention)`, `ri_recovery = min(max(loss−retention, 0), ri_limit)`
- **RI premium:** Burning-cost method — `E[RI recovery] × loading_factor`
- **SCR:** VaR(99.5%) of net retained loss distribution (bounded at retention)
- **Presets:** conservative (2.5× RI loading), base (1.75×), optimised (1.25×)
- **Corrected 5yr TCOR:** ~64M NOK (was ~210M before bug fixes)

### Mitigation Library (`analysis/mitigation.py`)
12 predefined actions covering: `lice_barrier`, `automatic_feeding`, `deep_light`, `oxygenation_system`, `real_time_monitoring`, `emergency_harvest_protocol`, `net_integrity_system`, `mooring_upgrade`, `deformation_monitoring`, `ai_early_warning`, and others. Each action specifies: affected domains, probability reduction, severity reduction, annual cost, capex, targeted risk types.

### PDF Report (`reporting/pdf_report.py`)
ReportLab BaseDocTemplate · 13 pages · 10+ charts:
- Cover page (canvas callback), executive summary, loss distribution, domain breakdown
- Domain correlation heatmap, scenario domain stacks, tail domain composition (Sprint 7)
- PCC cost breakdown table with RI premium highlighted (Sprint 8b)
- Strategy comparison, mitigation impact, recommendation narrative

---

## 4. C5AI+ Modules

### ForecastPipeline (`c5ai_plus/pipeline.py`) — 7 Steps
1. Load & validate biological input data (`DataLoader`)
2. Build site risk network (`SiteRiskNetwork`, requires networkx)
3. Run per-site forecasters for all 4 risk types
4. Apply network risk multipliers to loss estimates
5. Aggregate to operator level (sum across sites, mean across years)
6. Assemble metadata + validate (`ForecastValidator`)
7. Export to `risk_forecast.json` if `output_path` given

### Risk Types
`hab` · `lice` · `jellyfish` · `pathogen`

### Forecasters (`c5ai_plus/forecasting/`)
Each forecaster (`HABForecaster`, `LiceForecaster`, `JellyfishForecaster`, `PathogenForecaster`) extends `BaseForecaster`:
- Accepts `SiteData` + `forecast_years`
- Returns `List[RiskTypeForecast]` — one per year
- Each `RiskTypeForecast`: `event_probability`, `expected_loss_mean/p50/p90`, `confidence_score`, `data_quality_flag`, `model_used`
- `BaseForecaster` accepts optional `model_registry=` param for self-learning integration

### Data Quality Flags
`SUFFICIENT` · `LIMITED` · `POOR` · `PRIOR_ONLY`

### Site Risk Network (`c5ai_plus/network/site_network.py`)
- networkx-based graph of sites
- `get_risk_multiplier(site_id)` — amplifies event probabilities and loss estimates for connected sites
- Gracefully disabled when networkx not installed

### Self-Learning Extension (`c5ai_plus/learning/`, `c5ai_plus/models/`)

**Model types:**
- `BetaBinomialModel` — conjugate Bayesian; works from sample 1; prior = C5AI_SETTINGS priors
- `SklearnProbabilityModel` — Random Forest; activated when n_obs ≥ 20
- `LogNormalSeverityModel` — online Welford MLE for severity

**Learning loop (`LearningLoop.run_cycle()`):**
1. Fetch pending predictions from store
2. Load observed events from event store
3. Match predictions ↔ events by (operator, risk_type, year)
4. Evaluate (Brier score, log-loss, MAE, calibration slope)
5. Decide retrain vs. skip (insufficient data or score already good)
6. Run retraining pipeline → new model version
7. Shadow mode: compare new vs. current
8. Promote if shadow validates
9. Persist to ModelRegistry
10. Return `LearningCycleResult`

**Learning status:** cold (<3 cycles) → warming (3–9) → active (≥10)

**Storage paths:**
```
c5ai_plus/learning/store/
  registry/{operator_id}/...
  predictions/{operator_id}/...
  events/{operator_id}/...
```

---

## 5. Alert Engine (`c5ai_plus/alerts/`)

### Architecture
```
AlertEngine.generate_alerts(site_forecasts, previous_probabilities, env_data)
  ├── PatternDetector.detect()         → (precursor_score [0,1], List[PatternSignal])
  ├── ProbabilityShiftDetector.detect() → ProbabilityShiftSignal
  ├── _determine_level()               → NORMAL | WATCH | WARNING | CRITICAL
  └── AlertExplainer.explain()         → fills explanation_text + recommended_actions
```

### Level Mapping (transparent)
| Condition | Level |
|---|---|
| precursor_score ≥ 0.70 OR current_prob ≥ 0.35 | CRITICAL |
| precursor_score ≥ 0.45 OR current_prob ≥ 0.25 | WARNING |
| precursor_score ≥ 0.25 OR shift.triggered | WATCH |
| otherwise | NORMAL |

### Alert Rules (`alert_rules.py`)
15 `AlertRule(frozen=True)` instances:
- HAB (4): warm surface, low oxygen, high nitrate, high prior probability
- Lice (4): warm water, elevated counts, treatment fatigue, open coast exposure
- Jellyfish (3): warm seasonal, current pattern, prior sightings
- Pathogen (4): neighbour outbreak, high biomass, operational stress, high prior

### Key Dataclasses
```
AlertRecord
  alert_id (uuid4), site_id, risk_type
  alert_type: 'pattern' | 'probability_shift' | 'composite'
  alert_level: 'NORMAL' | 'WATCH' | 'WARNING' | 'CRITICAL'
  current_probability, previous_probability, probability_delta
  top_drivers (List[str]), triggered_rules (List[str])
  explanation_text, recommended_actions (List[str])
  workflow_status: 'OPEN' | 'ACKNOWLEDGED' | 'IN_PROGRESS' | 'CLOSED'
  board_visibility: bool  (True for CRITICAL)
  generated_at: ISO timestamp

AlertSummary
  site_id, total_alerts, critical_alerts, warning_alerts,
  top_risk_type, latest_alert_at
```

### Alert Store (`alert_store.py`)
JSON persistence: `{root}/alerts/{site_id}/{year}.json`
Methods: `save`, `load_all`, `load_recent(n=20)`, `filter_by_level`, `filter_by_risk_type`

### Alert Simulator (`alert_simulator.py`)
4 canonical demo scenarios: `simulate_hab_warning`, `simulate_lice_watch`, `simulate_jellyfish_critical`, `simulate_pathogen_warning`. `simulate_all()` returns 10 records across 3 sites and 4 alert levels.

---

## 6. GUI Architecture

### Navigation (`App.jsx`)
8-item secondary nav bar below the app header:

| Page ID | Label | Left Panel |
|---|---|---|
| `overview` | Overview | No |
| `inputs` | Inputs | No |
| `c5ai` | C5AI+ Risk Intelligence | No |
| `alerts` | Alerts | No |
| `feasibility` | PCC Feasibility | **Yes** |
| `strategy` | Strategy Comparison | **Yes** |
| `learning` | Learning | No |
| `reports` | Reports | No |

`FEASIBILITY_PAGES = {'feasibility', 'strategy'}` — only these pages render the left accordion panel. All others use `app-body.no-left-panel` (full-width layout).

### State Management
All state lives in `App.jsx`:
- `operator`, `model`, `strategy`, `pooling`, `selectedMitigations` — feasibility form state
- `result` — `FeasibilityResponse` from last API call
- `activePage` — controls navigation and left panel visibility
- `loading`, `step`, `error` — run progress
- `library` — mitigation library fetched on mount

### Left Panel (PCC Feasibility Inputs)
5-section accordion: **Operator** | **Model** | **Strategy** | **Mitigation** | **Pooling**

Key interactions:
- Valuation params (ref price / realisation / haircut) auto-cascade to `biomass_value_per_tonne` when no override is set
- Biomass or value changes auto-derive `annual_revenue_nok` and `annual_premium_nok`
- `handleExample()` → fetches pre-filled request, merges, switches to `feasibility` page

### Right Panel Pages

**OverviewPage** — 5 KPI cards (risk score ring, critical alerts, avg completeness, E[annual loss], learning status), alert summary, domain loss bars, completeness cards per site. `onNavigate` prop for "View all alerts →" / "View full inputs →" links.

**InputsPage** — 5-tab shell:
- *Site Profile* — 3 site cards: biomass, values, exposure/operational factors, source badges
- *Biological Inputs* — chart/table toggle + 5-group filter (see §7 below)
- *Alert Signals* — 12 signals, site/risk/triggered filters, signal table with delta coloring
- *Data Quality* — completeness cards + per-risk dq-table sorted by flag severity
- *Scenario Inputs* — 6-field override with sliders, 4 presets, stub run (§8 below)

**C5AIModule** — 5-tab panel fed from `C5AI_MOCK` + live `feasibilityResult`:
- *Risk Overview* — AlertSummaryCards at top, risk score ring, domain bars
- *Biological Forecasts* — per-site, per-risk-type forecast cards
- *Risk Drivers* — causal driver breakdown
- *Learning Status* — Brier score history table, learning phase indicator
- *Alerts* — compact AlertTable + AlertDetailPanel scoped to operator

**AlertsPage** — level filter pills + risk type filter pills → AlertTable → AlertDetailPanel. Shows total / filtered counts.

**ResultPanel (PCC Feasibility)** — 8-tab result view:
- *Summary* — KPI cards, C5AI+ enrichment bar
- *Charts* — base64 PNG charts from API
- *Mitigation* — cost/benefit per action
- *Recommendation* — narrative text
- *Report* — PDF download link
- *Allocation* — exposure ratios, financial ratios, per-site table, biomass valuation KPI cards
- *History* — domain loss breakdown, calibration metadata
- *Pooling* — diversification stats, member breakdown, TCOR comparison

**StrategyComparisonPage** — 3 strategy cards (PCC Captive RECOMMENDED NOK 64M · Full Insurance BASELINE NOK 97M · Mutual Pooling ALTERNATIVE NOK 74M). Passes live `result` for data-driven rendering if available.

**LearningPage** — wraps `LearningStatusTab` with data context banner (training source, portfolio completeness %).

**ReportsPage** — 4 report types; Board PDF available; C5AI+ Summary / Alert Log CSV / Input Audit planned.

### Shared Components
- `InputSourceBadge` — pill: real (green) · simulated (blue) · estimated (amber) · missing (red)
- `InputCompletenessCard` — progress bar + confidence label + dq-flag pills; green ≥80% · amber ≥60% · red <60%
- `AlertLevelBadge` — colour-coded pill per NORMAL/WATCH/WARNING/CRITICAL
- `ProbabilityShiftBadge` — ↑/↓/→ with pp change; `shift-up` red · `shift-down` green

---

## 7. Inputs System

### Mock Data (`frontend/src/data/mockInputsData.js`)
Three demo sites consistent across all mock data:

| Site ID | Name | Exposure |
|---|---|---|
| DEMO_OP_S01 | Frohavet North | 1.40 (open coast, highest risk) |
| DEMO_OP_S02 | Sunndalsfjord | 1.10 (semi-exposed) |
| DEMO_OP_S03 | Storfjorden South | 0.85 (sheltered, lowest risk) |

Exports: `MOCK_SITE_PROFILES`, `MOCK_BIOLOGICAL_INPUTS`, `MOCK_ALERT_SIGNALS`, `MOCK_DATA_QUALITY`, `SCENARIO_BASELINE`, `SCENARIO_PRESETS`, `BIO_READING_LABELS`.

### Biological Time Series (`frontend/src/data/mockBioTimeseries.js`)
12-month series (April 2025 – March 2026) for 11 parameters across 3 sites:

| Parameter | Color | Threshold |
|---|---|---|
| `surface_temp_c` | Red `#DC2626` | > 15.0°C (HAB-terskel) |
| `dissolved_oxygen_mg_l` | Blue `#2563EB` | < 7.0 mg/L (Oksygentrigger) |
| `nitrate_umol_l` | Amber `#D97706` | > 12.0 µmol/L (HAB-indikator) |
| `salinity_ppt` | Cyan `#0891B2` | — |
| `chlorophyll_a_ug_l` | Green `#16A34A` | > 3.0 µg/L (Algeindikator) |
| `lice_count_per_fish` | Purple `#7C3AED` | > 1.0 lus/fisk (Behandlingstrigger) |
| `hab_alert_count` | Red | — |
| `jellyfish_sightings` | Cyan | — |
| `pathogen_obs_count` | Brown | — |
| `treatments_last_90d` | Grey | — |
| `neighbor_lice_pressure` | Purple | > 1.5 (Nettverksvarsling) |

### BioLineChart (`frontend/src/components/inputs/BioLineChart.jsx`)
Pure SVG, no library. Key features:
- `viewBox="0 0 420 {height}"` · `MARGIN = {top:18, right:16, bottom:34, left:46}`
- Smooth **Catmull-Rom** spline (converted to cubic Bézier) for line and area fill
- **Baseline** — dashed grey `#9CA3AF`, `strokeDasharray="5 4"`
- **Threshold** — dashed red `#DC2626`, `strokeDasharray="4 3"` + risk-zone fill `rgba(220,38,38,0.06)`
- **Hover tooltip** — dark overlay rect with month + value, nearest-point detection via viewBox scaling
- **Last data point** — filled circle `r=4`; hovered points also `r=4`
- **Legend row** — Målt verdi / Baseline / Terskel inline at chart bottom

### BiologicalInputsPanel (`frontend/src/components/inputs/BiologicalInputsPanel.jsx`)
- **Toolbar** — site selector buttons + recorded-at timestamp + InputSourceBadge + Grafer/Tabell toggle
- **Group filter** — 5 groups: Alle · Temperatur & oksygen · Næringsstoffer & alger · Salinitet · Lus & behandlinger · Biologiske hendelser
- **Chart grid** — `auto-fill minmax(300px, 1fr)`, one `bio-chart-card` per visible parameter
- **Alert highlight** — cards where last value breaches threshold get `bio-chart-card-alert` (red border + `#FFF5F5` bg) + "Terskel nådd" badge
- **Table view** — original table preserved (current / baseline / delta / unit / source per parameter)

---

## 8. Scenario System

### Current State: UI-Complete Stub
The Scenario Inputs tab in `ScenarioOverridePanel.jsx` is fully built as a UI but the backend route `/api/c5ai/scenario` is **not yet wired**.

### 6 Editable Parameters
| Parameter | Range | Step |
|---|---|---|
| Total Biomass | 1 000–50 000 t | 100 |
| Dissolved Oxygen | 3–12 mg/L | 0.1 |
| Nitrate | 0–40 µmol/L | 0.5 |
| Lice Pressure Index | 0.5–4 | 0.1 |
| Exposure Factor | 0.5–2.0× | 0.05 |
| Operational Factor | 0.5–2.0× | 0.05 |

Each field has a linked `<input type="range">` slider and displays % deviation from baseline.

### 4 Presets (from `SCENARIO_PRESETS`)
Warm Summer · Lice Outbreak · Severe Storm · Optimal Conditions

### Stub Run Logic (900ms client-side)
```js
scaleFactor = lice_pressure × 0.15 + exposure_factor × 0.25
            + operational_factor × 0.10 + (nitrate > 10 ? 0.12 : 0) + 0.80
```
Returns: `scenario_scale_factor`, `estimated_annual_loss_change_pct`, `highest_risk_driver`.

**Next sprint:** wire to `POST /api/c5ai/scenario` → full Monte Carlo run with overridden parameters.

---

## 9. PCC Feasibility Integration

### Data Flow
```
GUI (App.jsx)
  └── POST /api/feasibility/run (FeasibilityRequest)
        └── operator_builder.build_operator_input()
              ↓  (OperatorInput, AllocationSummary)
            run_analysis.run_feasibility_analysis()
              ├── MonteCarloEngine.run()       → SimulationResults
              ├── [strategy].evaluate()        → StrategyResult
              ├── MitigationLibrary.apply()    → mitigated SimulationResults
              ├── SuitabilityEngine.score()    → SuitabilityScore + criterion_scores
              ├── CostAnalyzer.analyse()       → CostAnalysis
              ├── build_correlated_risk_summary() → narratives + scenarios
              └── PDFReportGenerator.generate() → PDF → /static/reports/<uuid>.pdf
```

### C5AI+ Integration Point
`ForecastPipeline.run(operator_input, static_mean_annual_loss)`:
- `static_mean_annual_loss` comes from `SimulationResults.mean_annual_loss`
- Returns `RiskForecast` → `c5ai_vs_static_ratio` and `loss_breakdown_fractions` pass into PCC cell pricing
- `SuitabilityEngine` criterion 6 (Biological Operational Readiness, 10%) reads `C5AI+` data quality flags from forecast metadata

### Historical Loss Calibration
When `use_history_calibration=True` and ≥3 historical records are present:
- `HistoricalLossSummary.calibration_mode` = `"portfolio"` or `"domain"`
- `calibrated_parameters` override `mean_loss_severity` and `expected_annual_events` in `MonteCarloEngine`
- `AllocationSummary.calibration_active = True`

### Sample Output (Nordic Aqua Partners AS)
```
TIV:            NOK 886.9M
Revenue:        NOK 897.0M
Premium:        NOK  19.5M
E[annual loss]: NOK  22.6M
VaR 99.5%:      NOK 134.2M
PCC 5yr TCOR:   NOK  64M   (corrected; was NOK 210M before Sprint 8b fixes)
Full ins TCOR:  NOK  97M
Verdict:        POTENTIALLY SUITABLE
PDF:            ~430 kB · 13 pages · 10 charts
```

---

## 10. Test Suite

| File | Tests | Area |
|---|---|---|
| `test_alert_layer.py` | 64 | Alert engine, models, rules, store, simulator |
| `test_learning_loop.py` | 66 | Self-learning (9 test classes) |
| `test_operator_builder.py` | 31 | TIV scaling, financial ratios, MC flow |
| `test_pcc_calibration.py` | 37 | PCCAssumptions, RI structure, SCR |
| `test_pcc_report_fixes.py` | 21 | TCOR bugs fixed, cost breakdown |
| `test_biomass_valuation.py` | 25 | Valuation formula, override, schema |
| `test_backend_api.py` | 16 | FastAPI endpoints (TestClient) |
| `test_correlation.py` | 44 | RiskCorrelationMatrix |
| `test_regime_model.py` | 28 | RegimeModel |
| `test_domain_correlation.py` | — | DomainCorrelationMatrix |
| `test_mc_domain_correlation.py` | — | MC + domain correlation integration |
| *(+24 other files)* | — | Risk domains, mitigation, forecasting, pooling, etc. |
| **Total** | **1 092** | **0 failed** |

---

## 11. Known Limitations & Pending Work

| Item | Status |
|---|---|
| `/api/c5ai/scenario` route | Not implemented — scenario panel is a stub |
| C5AI+ alerts not wired to live forecasts in GUI | GUI uses `MOCK_ALERTS`; `AlertEngine` is backend-only |
| `networkx` optional — site risk network disabled without it | Warning logged; graceful fallback |
| Mitigation `deformation_monitoring` / `ai_early_warning` targeted risk types don't match bio domains | Non-fatal warning in tests; falls back to portfolio-wide scaling |
| PDF charts use `matplotlib` (blocking) | Not async — acceptable for demo latency |
| Learning storage uses local JSON files | Not suitable for multi-user / production deployment |
| Scenario backend route | Next sprint: `POST /api/c5ai/scenario` → full MC with parameter overrides |

---

## 12. Run Commands

```bash
# Python tests
pytest tests/ -q                                       # 1 092 passed

# Backend API
uvicorn backend.main:app --reload --port 8000

# Frontend (dev)
cd frontend && npm run dev                             # http://localhost:5173

# Frontend (build)
cd frontend && npm run build                           # 0 errors

# C5AI+ pipeline (standalone)
python -m c5ai_plus.pipeline --input c5ai_input.json --output risk_forecast.json

# PCC feasibility CLI
python main.py                                         # Nordic Aqua Partners demo
python main.py --input my_input.json -n 20000          # custom operator

# Self-learning demo
python examples/run_learning_loop_demo.py
```
