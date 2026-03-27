# Shield Risk Platform – Project State

**Date:** 2026-03-27
**Test suite:** 1 810 passed, 0 failed (4 pre-existing errors in smolt test, 71 warnings)
**Frontend build:** 0 errors · 113 modules · 63.3 kB CSS · 501 kB JS
**Backend:** FastAPI · Python 3.11 · uvicorn
**Frontend:** React 18 · Vite 5 · pure SVG charts (no charting library)

---

## 1. Repository Layout

```
shield-feasibility/
│
├── main.py                          # CLI entry: 9-step PCC pipeline
├── data/sample_input.json           # Nordic Aqua Partners AS (demo operator)
│
├── config/
│   ├── settings.py                  # Global constants (NOK thresholds, CAT params)
│   └── cage_weighting.py            # Advanced cage weighting constants (NEW Sprint 11)
│
├── data/input_schema.py             # OperatorInput, SiteProfile dataclasses
│
├── models/                          # Core stochastic and risk models
│   ├── monte_carlo.py               # Compound Poisson-LogNormal MC engine
│   ├── correlation.py               # RiskCorrelationMatrix (equicorrelation, Cholesky)
│   ├── regime_model.py              # RegimeModel (3 regimes)
│   ├── domain_correlation.py        # DomainCorrelationMatrix 4×4
│   ├── domain_loss_breakdown.py     # DomainLossBreakdown + cage multiplier application
│   ├── cage_technology.py           # CagePenConfig, CAGE_DOMAIN_MULTIPLIERS (NEW Sprint 9)
│   ├── cage_weighting.py            # 5-component advanced weighting engine (NEW Sprint 11)
│   ├── loss_model.py                # LossView (gross/net/retained per strategy)
│   ├── pcc_economics.py             # PCCAssumptions presets, RI structure helpers
│   ├── captive_structure.py         # Cell captive capital structure
│   └── strategies/
│       ├── base_strategy.py         # AnnualCostBreakdown, StrategyResult
│       ├── full_insurance.py
│       ├── hybrid.py
│       ├── pcc_captive.py           # Fixed RI/SCR/TCOR (Sprint 8b)
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
│   ├── chart_generator.py           # 10+ matplotlib charts → BytesIO
│   └── correlated_risk_analytics.py # Scenario extraction, tail analysis, narratives
│
├── c5ai_plus/                       # C5AI+ v5.0 – multi-domain risk intelligence
│   ├── pipeline.py                  # ForecastPipeline (7-step orchestration)
│   ├── multi_domain_engine.py       # MultiDomainEngine, MultiDomainForecast
│   ├── config/c5ai_settings.py      # C5AI_SETTINGS (priors, thresholds, version)
│   ├── data_models/
│   │   ├── biological_input.py      # C5AIOperatorInput, SiteInput
│   │   ├── forecast_schema.py       # RiskForecast, SiteForecast, RiskTypeForecast
│   │   └── learning_schema.py       # PredictionRecord, ObservedEvent, LearningCycleResult
│   ├── forecasting/                 # Biological: HAB, lice, jellyfish, pathogen
│   ├── structural/                  # Structural domain forecasting
│   ├── environmental/               # Environmental domain forecasting
│   ├── operational/                 # Operational domain forecasting
│   ├── ingestion/, network/, validation/, export/, feature_engineering/, causal/
│   ├── alerts/                      # Early Warning / Alert Layer (8 modules)
│   ├── models/                      # Self-learning probability/severity models
│   ├── learning/                    # predict → observe → evaluate → retrain
│   └── simulation/                  # Synthetic data for learning demos
│
├── backend/                         # FastAPI adapter
│   ├── main.py                      # FastAPI app, CORS, static file mount
│   ├── schemas.py                   # Pydantic request/response models
│   ├── api/
│   │   ├── feasibility.py           # POST /api/feasibility/run, /example
│   │   ├── mitigation.py            # GET /api/mitigation/library
│   │   └── inputs_audit.py          # GET /api/inputs/audit
│   ├── services/
│   │   ├── operator_builder.py      # SimplifiedProfile → (OperatorInput, AllocationSummary)
│   │   ├── run_analysis.py          # 9-step pipeline adapter → FeasibilityResponse
│   │   └── history_analytics.py     # Historical loss domain analytics
│   └── static/reports/              # Generated PDFs served at /static/reports/<uuid>.pdf
│
├── tests/                           # 1 734 tests across 40+ test files (0 failed)
│
├── frontend/                        # React 18 + Vite 5 GUI
│   └── src/
│       ├── App.jsx                  # Root: 9-page nav, state, API wiring
│       ├── App.css                  # ~53 kB – all styles
│       ├── api/client.js            # fetchMitigationLibrary, fetchExample, runFeasibility, fetchInputsAudit
│       ├── data/
│       │   ├── cageTechnologyMeta.js  # Cage types, multipliers, default scores, labels
│       │   ├── c5ai_mock.js           # C5AI_MOCK – multi-domain forecast data
│       │   ├── mockAlertsData.js      # MOCK_ALERTS (18 records across 3 domains)
│       │   ├── mockInputsData.js      # MOCK_SITE_PROFILES, MOCK_BIOLOGICAL_INPUTS, etc.
│       │   ├── mockBioTimeseries.js   # 12-month biological time series (3 sites)
│       │   └── mockMultiDomainData.js # Multi-domain C5AI+ mock forecasts
│       └── components/
│           ├── InputForm/           # PCC feasibility input accordion
│           │   ├── CagePortfolioPanel.jsx   # Per-cage % allocation + advanced fields
│           │   ├── SeaLocalityAllocationTable.jsx
│           │   └── SeaLocalitySelector.jsx
│           ├── results/             # 9-tab result panel
│           │   └── CageRiskProfileTab.jsx   # Merd-profil tab
│           ├── c5ai/                # C5AI+ module (7 tabs)
│           ├── alerts/              # Early warning alert components
│           └── inputs/              # Inputs page with 5 tabs
│
├── CHANGELOG.md                     # Version history
├── docs/sprints/SPRINT_HISTORY.md   # Chronological sprint log
└── examples/                        # Standalone demo scripts
```

---

## 2. Backend Architecture

### FastAPI Application (`backend/main.py`)
- **Title:** Shield Risk Platform API v1.0.0
- **CORS:** `http://localhost:5173` / `http://127.0.0.1:5173`
- **Static files:** `backend/static/` mounted at `/static` — PDFs at `/static/reports/<uuid>.pdf`
- **Start:** `uvicorn backend.main:app --reload --port 8000`

### API Routes

| Method | Path | Handler |
|---|---|---|
| `GET` | `/` | Health check → `{"status": "ok"}` |
| `GET` | `/api/mitigation/library` | All 12 predefined mitigation actions |
| `POST` | `/api/feasibility/run` | Full 9-step pipeline → `FeasibilityResponse` |
| `POST` | `/api/feasibility/example` | Nordic Aqua Partners pre-filled request |
| `GET` | `/api/inputs/audit` | Input data audit report → `InputsAuditReport` |

### Request Model (`FeasibilityRequest`)

```
OperatorProfileInput
  name, country, n_sites, total_biomass_tonnes
  biomass_value_per_tonne (64 800 NOK/t default)
  reference_price_per_kg, realisation_factor, prudence_haircut
  biomass_value_per_tonne_override  ← optional manual override
  annual_revenue_nok, annual_premium_nok
  site_selection_mode: 'generic' | 'specific'
  selected_sites: Optional[List[SelectedSeaSite]]
    site_id, locality_no, site_name, biomass_tonnes, biomass_value_nok
    cages: Optional[List[CagePenInput]]   ← per-cage portfolio

CagePenInput
  cage_id, cage_type, biomass_tonnes
  # Advanced weighting fields (all optional):
  biomass_value_nok, consequence_factor
  operational_complexity_score [0–1]
  structural_criticality_score [0–1]
  single_point_of_failure: bool
  redundancy_level [1–5]
  technology_maturity_score [0–1]
  failure_mode_class: 'proportional' | 'threshold' | 'binary_high_consequence'

ModelSettingsInput
  n_simulations (100–100 000, default 5 000)
  domain_correlation: 'independent' | 'expert_default' | 'low' | 'moderate'
  generate_pdf: bool
  use_history_calibration: bool

StrategySettingsInput / PoolingSettingsInput / MitigationInput
```

### Response Model (`FeasibilityResponse`)

```
baseline: ScenarioBlock          ← KPIs + base64 charts + criterion scores
mitigated: Optional[ScenarioBlock]
comparison: Optional[ComparisonBlock]
report: ReportBlock              ← pdf_url if generate_pdf
metadata: MetadataBlock          ← site_selection_mode, selected_site_count
allocation: Optional[AllocationSummary]
  cage_profiles: Optional[List[LocalityCageRiskProfile]]
    site_id, site_name, cage_count, cage_types_present
    biomass_by_cage_type, effective_domain_multipliers
    cage_weight_details: List[CageWeightDetail]   ← per-cage breakdown
    weighting_mode: 'advanced' | 'biomass_only'
    warnings: List[str]
history: Optional[HistoricalLossSummary]
pooling: Optional[PoolingResult]
```

### Operator Builder (`backend/services/operator_builder.py`)

Key responsibilities:
- Converts `OperatorProfileInput` → `(OperatorInput, AllocationSummary)`
- Supports two site modes: `generic` (scale from template) and `specific` (use selected BW localities)
- In specific mode: validates site_ids, builds per-site cage configs, calls
  `compute_locality_domain_multipliers_advanced()` per locality
- Cage configs with `biomass_tonnes == 0` (empty/fallow merder) are silently skipped
- Risk severity scales with TIV ratio vs. template
- Risk event frequency scales with `sqrt(n_sites)`
- Financial fields derived from revenue via template ratios

### Biomass Valuation Formula
```
suggested_NOK_per_tonne = ref_price_per_kg × 1000 × realisation_factor × (1 − prudence_haircut)
defaults: 80 × 1000 × 0.90 × 0.90 = 64 800 NOK/t
applied = override if set, else biomass_value_per_tonne
```

---

## 3. PCC Feasibility Pipeline (9 Steps — `main.py`)

1. **Load & validate** `OperatorInput` from JSON
2. **Monte Carlo simulation** — Compound Poisson-LogNormal, N simulations × 5 years
3. **Domain correlation** — Additive Gaussian perturbation on simplex
4. **Strategy evaluation** — Run selected strategy against simulation results
5. **Mitigation application** — Apply selected mitigation actions
6. **Suitability scoring** — 6-criterion model → composite score → verdict
7. **Cost analysis** — TCOR, 5yr cost comparison baseline vs. mitigated
8. **Correlated risk analytics** — Scenario extraction, tail analysis, board narratives
9. **PDF report** — ReportLab Platypus, 13 pages, 10+ charts

### Monte Carlo Engine (`models/monte_carlo.py`)
- **Model:** Compound Poisson-LogNormal — `S_t = Σ X_i` where `N_t ~ Poisson(λ)`, `X_i ~ LogNormal`
- **CAT overlay:** With probability `p_cat`, inject extra event at `multiplier × base_mean`
- **Horizon:** N × 5 annual totals per simulation
- **Site correlation:** Gaussian copula via Cholesky decomposition
- **Regime model:** 3 regimes (75% normal, 20% elevated ×1.8, 5% catastrophic ×3.5)
- **Domain correlation:** `DomainCorrelationMatrix` 4×4 (expert-default: bio-struct=0.20,
  env-struct=0.60, env-bio=0.40, ops-struct=0.35)
- **Cage multipliers:** `cage_multipliers` dict → applied per domain after simulation

### Suitability Engine (`analysis/suitability_engine.py`)

| Criterion | Weight |
|---|---|
| Premium Volume | 22.5% |
| Loss Stability | 18.0% |
| Balance Sheet Strength | 18.0% |
| Cost Savings Potential | 18.0% |
| Operational Readiness | 13.5% |
| Biological Operational Readiness (C5AI+) | 10.0% |

Verdicts: ≥72 STRONGLY RECOMMENDED · 55–71 RECOMMENDED · 40–54 POTENTIALLY SUITABLE ·
25–39 NOT RECOMMENDED · <25 NOT SUITABLE

Hard cost gate: >5% PCC/FI excess → cap at POTENTIALLY SUITABLE; >15% → NOT RECOMMENDED.

### PCC Captive Economics
- **RI structure:** Annual-aggregate XL — `net = min(loss, retention)`,
  `ri_recovery = min(max(loss−retention, 0), ri_limit)`
- **RI premium:** Burning-cost method — `E[RI recovery] × loading_factor`
- **SCR:** VaR(99.5%) of net retained loss distribution (bounded at retention)
- **Corrected 5yr TCOR:** ~64M NOK (was ~210M before Sprint 8b bug fixes)

---

## 4. Cage Portfolio Model

### Architecture
Each sea locality is modelled as a portfolio of named net-pen cages (merder).

```
locality
  └── cages: List[CagePenConfig]
        ├── cage_id, cage_type, biomass_pct / biomass_tonnes
        ├── domain_multipliers  ← from CAGE_DOMAIN_MULTIPLIERS[cage_type]
        └── advanced fields: biomass_value_nok, consequence_factor,
            operational_complexity_score, structural_criticality_score,
            single_point_of_failure, redundancy_level, failure_mode_class
```

### Cage Type Multipliers (`CAGE_DOMAIN_MULTIPLIERS`)

| Type | Biological | Structural | Environmental | Operational |
|---|---|---|---|---|
| `open_net` | 1.00 | 1.00 | 1.00 | 1.00 |
| `semi_closed` | 0.75 | 0.95 | 0.80 | 1.10 |
| `fully_closed` | 0.45 | 1.20 | 0.60 | 1.25 |
| `submerged` | 0.70 | 1.15 | 0.55 | 1.15 |

### Advanced Weighting Engine (`models/cage_weighting.py`)

Five components per cage:

| Component | Derivation |
|---|---|
| biomass | `cage.biomass_tonnes` |
| value | `cage.biomass_value_nok` (0 if not set) |
| consequence | `value × consequence_factor × failure_mode_multiplier` |
| complexity | `operational_complexity_score` or cage-type default |
| criticality | `base_criticality × spof_mult × redundancy_scale` |

Domain component weights:

| Domain | biomass | value | consequence | complexity | criticality |
|---|---|---|---|---|---|
| biological | 0.50 | 0.25 | 0.15 | 0.05 | 0.05 |
| structural | 0.25 | 0.15 | 0.30 | 0.15 | 0.15 |
| environmental | 0.30 | 0.10 | 0.25 | 0.25 | 0.10 |
| operational | 0.15 | 0.10 | 0.25 | 0.30 | 0.20 |

Backward compatible: no advanced data → exact biomass-only fallback.

### Biomass Percentage Allocation (GUI)
- Each cage enters `biomass_pct` (0–100% of locality total).
- `biomass_tonnes` derived: `pct × site.biomass_tonnes / 100`.
- Control-sum bar enforces ≤ 100%; empty/fallow cages (0%) allowed.
- When site-level biomass changes, cage tonnes recompute from stored pct.
- Backend skips 0-tonne cages in `_build_cage_pen_configs()`.

---

## 5. Specific Sea Localities Mode

Users toggle between two site input modes:

| Mode | Description |
|---|---|
| `generic` | Scale from template — existing behaviour unchanged |
| `specific` | Select actual BW-registered localities from registry |

Real locality registry (Kornstad Havbruk AS):

| ID | Name | BW No. | Exposure |
|---|---|---|---|
| `KH_S01` | Kornstad | 12855 | 1.15 — semi-exposed |
| `KH_S02` | Leite | 12870 | 1.10 — semi-exposed |
| `KH_S03` | Hogsnes | 12871 | 0.85 — sheltered |

Backend validation: `validate_selected_sites()` → HTTP 422 on invalid/duplicate site_ids.
`MetadataBlock` carries `site_selection_mode`, `selected_site_count`, `selected_locality_numbers`.

---

## 6. C5AI+ Modules

### ForecastPipeline — 7 Steps
1. Load & validate biological input data
2. Build site risk network (networkx, gracefully disabled if absent)
3. Run per-site forecasters for 19 risk types across 4 domains
4. Apply network risk multipliers
5. Aggregate to operator level
6. Assemble metadata + validate
7. Export to `risk_forecast.json` if `output_path` given

### Risk Type Coverage (19 types)

| Domain | Risk Types |
|---|---|
| Biological | `hab`, `lice`, `jellyfish`, `pathogen` |
| Structural | `net_integrity`, `mooring_failure`, `cage_structural`, `anchor_failure`, `storm_structural` |
| Environmental | `current_storm`, `ice`, `oxygen_depletion`, `temperature_extreme`, `algae_bloom` |
| Operational | `human_error`, `equipment_failure`, `procedure_failure`, `feed_system`, `vessel_incident` |

### Self-Learning Extension

**Model types:**
- `BetaBinomialModel` — conjugate Bayesian; works from sample 1
- `SklearnProbabilityModel` — Random Forest; activated when n_obs ≥ 20
- `LogNormalSeverityModel` — online Welford MLE

**Learning loop status:** cold (<3 cycles) → warming (3–9) → active (≥10)

---

## 7. Alert Engine (`c5ai_plus/alerts/`)

### Level Mapping

| Condition | Level |
|---|---|
| precursor_score ≥ 0.70 OR current_prob ≥ 0.35 | CRITICAL |
| precursor_score ≥ 0.45 OR current_prob ≥ 0.25 | WARNING |
| precursor_score ≥ 0.25 OR shift.triggered | WATCH |
| otherwise | NORMAL |

15 alert rules (HAB×4, Lice×4, Jellyfish×3, Pathogen×4).
`simulate_all()` returns 18 records across 3 sites.

---

## 8. GUI Architecture

### Navigation (`App.jsx`)
9-page nav:

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

`FEASIBILITY_PAGES = {'feasibility', 'strategy'}` — only these render the left accordion.

### Left Panel (PCC Feasibility Inputs)
5-section accordion: **Operator** | **Model** | **Strategy** | **Mitigation** | **Pooling**

Operator section includes:
- Site mode toggle (Generic / Specific sea localities)
- `SeaLocalitySelector.jsx` (specific mode)
- `SeaLocalityAllocationTable.jsx` with `CagePortfolioPanel.jsx` per locality:
  - Per-cage % input, technology select, cage ID
  - Collapsible "Avansert" panel (6 advanced risk fields + default badges)
  - Control-sum bar (sum of % with green/blue/red status)
  - "Fordel jevnt" button

### Right Panel — Result Tabs
9 tabs (PCC Feasibility):
1. Summary — KPI cards, C5AI+ enrichment bar
2. Charts — base64 PNG charts
3. Mitigation — cost/benefit per action
4. Recommendation — narrative text
5. Report — PDF download
6. Allocation — exposure/financial ratios, per-site table, biomass valuation
7. History — domain loss breakdown, calibration metadata
8. Pooling — diversification stats, member breakdown
9. **Merd-profil** — per-locality cage composition, multiplier cards, weighting mode badge,
   cage weight detail table (collapsible), warnings

### Mock Data Sites
All demo data uses Kornstad Havbruk AS (KH_S01/02/03 — Kornstad/Leite/Hogsnes).
Previous DEMO_OP_S01/02/03 (Nordic Aqua Partners) references removed.

---

## 9. Data Flow (PCC Feasibility)

```
GUI (App.jsx)
  └── POST /api/feasibility/run (FeasibilityRequest)
        └── operator_builder.build_operator_input()
              ├── specific mode: validate_selected_sites()
              │   └── per-site: _build_cage_pen_configs()
              │         └── compute_locality_domain_multipliers_advanced()
              │               → AdvancedWeightingResult (domain_multipliers, cage_weight_details)
              └─→ (OperatorInput, AllocationSummary with cage_profiles)
            run_analysis.run_feasibility_analysis()
              ├── MonteCarloEngine.run(cage_multipliers=...)  → SimulationResults
              ├── [strategy].evaluate()                       → StrategyResult
              ├── MitigationLibrary.apply()                   → mitigated SimulationResults
              ├── SuitabilityEngine.score()                   → SuitabilityScore
              ├── CostAnalyzer.analyse()                      → CostAnalysis
              ├── build_correlated_risk_summary()             → narratives + scenarios
              └── PDFReportGenerator.generate()               → PDF
```

---

## 10. Test Suite

| File | Tests | Area |
|---|---|---|
| `test_cage_weighting.py` | 82 | Advanced weighting engine (NEW Sprint 11) |
| `test_cage_technology.py` | 52 | Cage technology model (NEW Sprint 9) |
| `test_alert_layer.py` | 64 | Alert engine, models, rules, store |
| `test_learning_loop.py` | 66 | Self-learning (9 test classes) |
| `test_operator_builder.py` | 31 | TIV scaling, financial ratios, MC flow |
| `test_pcc_calibration.py` | 37 | PCCAssumptions, RI structure, SCR |
| `test_pcc_report_fixes.py` | 21 | TCOR correctness, cost breakdown |
| `test_biomass_valuation.py` | 25 | Valuation formula, override, schema |
| `test_inputs_audit.py` | 18 | Audit endpoint, data correctness |
| `test_backend_api.py` | 16 | FastAPI endpoints (TestClient) |
| `test_correlation.py` | 44 | RiskCorrelationMatrix |
| `test_regime_model.py` | 28 | RegimeModel |
| *(+28 other files)* | ~1 250 | Risk domains, mitigation, forecasting, pooling, etc. |
| **Total** | **1 734** | **0 failed** |

---

## 11. Known Limitations

| Item | Status | Priority |
|---|---|---|
| `/api/c5ai/scenario` route | Not wired — `ScenarioOverridePanel.jsx` is a UI stub | Next sprint |
| C5AI+ alerts in GUI use `MOCK_ALERTS` | `AlertEngine` is backend-only; not live-wired | Future |
| Cage registry limited to 3 Kornstad localities | `SEA_LOCALITY_REGISTRY` is hardcoded | Expand per operator |
| `networkx` optional | Site risk network disabled without it; warning logged | Low |
| `biomass_pct` is UI-only | Not stored in `CagePenInput` schema — derived to `biomass_tonnes` | Acceptable |
| PDF charts use blocking `matplotlib` | Not async — acceptable at demo scale | Future |
| Learning store uses local JSON files | Not suitable for multi-user production | Future |
| Multi-domain C5AI+ uses 15 simulated risk types | Structural/env/ops are stubs vs. biological (real model) | Future |

---

## 12. Run Commands

```bash
# Python tests
pytest tests/ -q                                       # 1 734 passed

# Backend API
uvicorn backend.main:app --reload --port 8000

# Frontend (dev)
cd frontend && npm run dev                             # http://localhost:5173

# Frontend (build verification)
cd frontend && npm run build                           # 0 errors, 105 modules

# C5AI+ pipeline (standalone)
python -m c5ai_plus.pipeline --input c5ai_input.json --output risk_forecast.json

# PCC feasibility CLI
python main.py                                         # Nordic Aqua Partners demo
python main.py --input my_input.json -n 20000          # custom operator

# Self-learning demo
python examples/run_learning_loop_demo.py
```

---

## 13. Recommended Next Sprint

**Scenario Backend Route** (`POST /api/c5ai/scenario`)

The `ScenarioOverridePanel.jsx` is UI-complete with 6 editable parameters, 4 presets,
and a 900ms client-side stub. The next logical sprint wires it to a real backend endpoint
that runs a lightweight Monte Carlo with the overridden parameters and returns:

```json
{
  "scenario_id": "...",
  "scale_factor": 1.24,
  "estimated_annual_loss_nok": 28_000_000,
  "domain_breakdown": {...},
  "highest_risk_driver": "lice_pressure",
  "vs_baseline_pct": +23.8
}
```

Scope: ~1 day. New route `POST /api/c5ai/scenario` accepting `ScenarioOverrideInput`
→ lightweight `MonteCarloEngine.run()` with parameter injection → `ScenarioResult` response.
