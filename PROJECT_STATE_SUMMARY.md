# Shield Risk Platform — Project State Summary

**Generated:** 2026-03-22
**Test suite:** 1 413 passed, 0 failed
**Frontend build:** ✓ 0 errors (React 18 + Vite 5)

---

## What the Platform Does

Shield Risk Platform is a Norwegian aquaculture risk intelligence and PCC (Protected Cell Company captive insurance) feasibility tool. It serves salmon farming operators who want to understand their risk exposure and evaluate whether forming or joining a captive insurance cell is economically viable.

Two operator types are fully supported:

| Type | Description | Example |
|---|---|---|
| **Sea-site** (havbruk) | Open-water salmon grow-out | Nordic Aqua Partners AS |
| **Smolt / RAS** (settefisk) | Land-based recirculating aquaculture | Agaqua AS |

The platform ingests operator parameters, runs a 10 000-simulation Monte Carlo model, evaluates five insurance strategies, scores PCC suitability on a 6-criterion model, and generates a board-level PDF report. A React GUI exposes the full pipeline interactively.

---

## Repository Layout

```
shield-feasibility/
│
├── main.py                        # CLI entry: 9-step pipeline
├── config/settings.py             # All numeric constants
├── data/
│   ├── input_schema.py            # OperatorInput, SiteProfile dataclasses
│   └── sample_input.json          # Nordic Aqua Partners AS (3 sites)
│
├── models/
│   ├── monte_carlo.py             # MonteCarloEngine — vectorised NumPy (N=10k, T=5)
│   ├── domain_correlation.py      # DomainCorrelationMatrix (4×4)
│   ├── domain_loss_breakdown.py   # DomainLossBreakdown + correlated perturbation
│   ├── smolt_loss_categories.py   # SmoltLossCategory dataclass tree
│   ├── sea_loss_categories.py     # SeaLossCategory dataclass tree
│   ├── smolt_bi_calculator.py     # Business interruption for RAS
│   ├── smolt_calibration.py       # RAS-specific severity calibration
│   ├── smolt_generation_tracker.py# Fish generation lifecycle model
│   ├── pcc_economics.py           # PCCAssumptions presets + XL helpers
│   ├── regime_model.py            # Hidden Markov regime-switching
│   ├── scenario_engine.py         # Scenario override / stress testing
│   ├── pooling/                   # Multi-operator risk pooling analytics
│   └── strategies/
│       ├── base_strategy.py       # AnnualCostBreakdown, StrategyResult
│       ├── full_insurance.py
│       ├── partial_insurance.py
│       ├── self_insurance.py
│       ├── pcc_captive.py         # PCCCaptiveStrategy — XL RI structure
│       └── hybrid_strategy.py
│
├── analysis/
│   ├── mitigation.py              # 24 mitigations (12 sea + 12 smolt), SMOLT_DOMAIN_MAPPING
│   ├── scr_calculator.py          # SCR = VaR(99.5%) net retained loss
│   ├── suitability_engine.py      # 6-criterion PCC suitability scoring
│   ├── cost_analyzer.py           # 5-strategy TCOR comparison
│   └── volatility_metrics.py
│
├── reporting/
│   ├── pdf_report.py              # 13-page ReportLab board PDF
│   ├── chart_generator.py         # 10 SVG/PNG charts
│   └── correlated_risk_analytics.py  # Cross-domain scenario narratives
│
├── c5ai_plus/                     # C5AI+ v5.0 biological risk intelligence
│   ├── pipeline.py                # 7-step forecast pipeline
│   ├── multi_domain_engine.py     # MultiDomainEngine (bio + structural + env + ops)
│   ├── forecasting/               # BaseForecaster, risk-specific forecasters
│   ├── biological/                # HAB, lice, jellyfish, pathogen rules
│   ├── structural/                # Net integrity, mooring, cage structural rules
│   ├── environmental/             # Temperature extreme, storm, flood rules
│   ├── operational/               # Equipment failure, staff, power rules
│   ├── alerts/                    # AlertEngine, pattern detector, explainer
│   ├── models/                    # BetaBinomial, LogNormal, ModelRegistry
│   ├── learning/                  # Self-learning loop (Bayesian + RF)
│   ├── simulation/                # Synthetic data + event simulator
│   └── causal/                    # Causal graph inference
│
├── backend/
│   ├── main.py                    # FastAPI app — 4 routers
│   ├── schemas.py                 # Pydantic request/response models
│   ├── api/
│   │   ├── feasibility.py         # POST /api/feasibility/run
│   │   ├── smolt_feasibility.py   # POST /api/feasibility/smolt/run
│   │   ├── mitigation.py          # GET  /api/mitigation/library
│   │   └── scenario.py            # POST /api/c5ai/scenario
│   └── services/
│       ├── operator_builder.py    # SimplifiedProfile → OperatorInput (sea)
│       ├── smolt_operator_builder.py  # SmoltOperatorBuilder + SmoltAllocationSummary
│       ├── sea_site_builder.py    # Sea site scaling helpers
│       ├── run_analysis.py        # Full 9-step pipeline → FeasibilityResponse
│       └── history_analytics.py   # Self-handled loss history analytics
│
├── frontend/src/
│   ├── App.jsx                    # Root — state, routing, payload builders
│   ├── App.css                    # All styles (append-only convention)
│   ├── components/
│   │   ├── InputForm/             # OperatorProfile, SmoltTIVPanel, SmoltBIWidget,
│   │   │                          #   OperatorTypeSelector, ModelSettings, …
│   │   ├── results/               # SummaryTab, ChartsTab, MitigationTab,
│   │   │                          #   AllocationTab, SmoltAllocationTab,
│   │   │                          #   LossHistoryTab, RecommendationTab, …
│   │   ├── c5ai/                  # C5AIModule (7 tabs), RiskOverviewTab, …
│   │   ├── alerts/                # AlertTable, AlertDetailPanel, AlertLevelBadge
│   │   ├── inputs/                # Inputs page panels (5 tabs)
│   │   ├── OverviewPage.jsx
│   │   ├── StrategyComparisonPage.jsx
│   │   ├── LearningPage.jsx
│   │   └── ReportsPage.jsx
│   └── data/
│       ├── mockInputsData.js      # Site profiles, bio inputs, alert signals
│       ├── mockAlertsData.js      # 18 alert records across 3 demo sites
│       ├── mockBioTimeseries.js   # Biological time-series for charts
│       ├── mockMultiDomainData.js # Structural / environmental / operational forecasts
│       ├── c5ai_mock.js           # C5AI+ forecast mock (all 4 domains)
│       ├── smoltScenariosData.js  # RAS scenario presets
│       └── agaquaExample.js       # Agaqua AS full example payload
│
└── tests/                         # 40 test files, 1 413 assertions
```

---

## Core Pipeline (9 Steps — Sea-Site)

```
1. Load OperatorInput               data/input_schema.py
2. Compute TIV & financial ratios   models/domain_loss_breakdown.py
3. Run Monte Carlo (10k × 5yr)      models/monte_carlo.py
4. Apply mitigations                analysis/mitigation.py
5. Evaluate 5 strategies            models/strategies/
6. Score PCC suitability            analysis/suitability_engine.py
7. Build correlated risk analytics  reporting/correlated_risk_analytics.py
8. Generate charts                  reporting/chart_generator.py
9. Render board PDF                 reporting/pdf_report.py
```

The smolt pipeline follows the same 9 steps but uses `SmoltOperatorBuilder` to translate the compact RAS input into a full `OperatorInput`, with smolt-specific loss categories, BI calculation, and generation tracking.

---

## Monte Carlo Model

- **Compound Poisson-LogNormal** frequency-severity model
- **N = 10 000 simulations, T = 5 years** — vectorised NumPy, ~1 s runtime
- **Output shape:** `(N, T)` annual loss matrix
- **Domain loss breakdown:** 4 domains (biological, structural, environmental, operational) with correlated perturbation (additive Gaussian shift on simplex)
- **CAT overlay:** extreme-tail event injection
- **Key invariant:** SCR = VaR(99.5%) of net retained loss after XL reinsurance, bounded at retention

---

## Insurance Strategies

| Strategy | Key Economics |
|---|---|
| Full Insurance | Market premium + loading |
| Partial Insurance | Retention layer + partial premium |
| Self Insurance | Reserve accumulation, no premium |
| **PCC Captive** | Cell SCR as required capital; XL RI structure with burning-cost premium; fronting fee separate |
| Hybrid | Blend of PCC + commercial |

PCC TCOR (5yr, Nordic Aqua example): **NOK 64M** (corrected from NOK 210M double-count in Sprint 8b).

---

## Mitigation Library

24 predefined mitigation actions split by operator type:

**Sea-site (12):** jellyfish_barrier, lice_treatment_protocol, oxygenation_system, net_monitoring, anchor_inspection, emergency_contingency, vaccine_program, sensor_network, mooring_upgrade, deformation_monitoring, ai_early_warning, insurance_deductible_reduction

**Smolt / RAS (12):** smolt_oxygen_backup, smolt_backup_power, smolt_ups_aggregat, smolt_water_source_backup, smolt_biofilter_redundancy, smolt_temperature_control, smolt_automated_monitoring, smolt_emergency_plan, smolt_staff_training, smolt_fish_health_program, smolt_biosecurity_protocol, smolt_maintenance_program

### Smolt Mitigation Routing

Smolt actions use `SMOLT_DOMAIN_MAPPING` (35 keys) to translate RAS-specific risk type names (`ras_failure`, `oxygen_event`, `power_outage`, `water_source`, `biological`, `operational`) to the correct `DomainLossBreakdown` sub-types. This prevents spurious "not found" warnings and ensures effects are applied to the right loss categories.

`_SMOLT_CATEGORY_TO_SUBTYPES` maps each canonical smolt category to its sub-type list or to `"DOMAIN"` for domain-level application:

| Smolt Category | Applied to sub-types |
|---|---|
| `ras_failure` | `biofilter`, `water_quality` |
| `oxygen_event` | `oxygen` |
| `power_outage` | `power` |
| `water_source` | `biosecurity` |
| `biological` | domain-level (all bio sub-types) |
| `operational` | domain-level (all ops sub-types) |

### Combined Effect Calibration

Sub-type caps in `STRUCTURAL_SUBTYPE_CAPS` prevent physically impossible combined reductions:

| Sub-type | Cap |
|---|---|
| `mooring_failure` | 48% |
| `oxygen` | 55% |
| `biofilter` | 55% |
| `power` | 70% |
| `water_quality` | 70% |
| `biosecurity` | 65% |

5-action combined smolt scenario achieves approximately **−44%** total loss reduction. All-12 smolt scenario achieves approximately **−55%** — consistent with physical realism for a fully optimised RAS facility.

---

## C5AI+ Risk Intelligence (v5.0)

**7-step forecast pipeline** per operator and risk type:

1. Ingest time-series inputs
2. Feature engineering
3. Probability model (BetaBinomial or RandomForest)
4. Severity model (LogNormal MLE)
5. Domain correlation
6. Alert generation
7. Self-learning update

**4 domains, 19 risk types:**
- Biological: HAB, lice, jellyfish, pathogen
- Structural: net_integrity, mooring_failure, cage_structural
- Environmental: temperature_extreme, storm, flood, utility_failure
- Operational: equipment_failure, staff_error, power_outage, water_quality

**Alert engine:** score ≥ 0.70 or probability shift ≥ 0.35 → CRITICAL. 18 mock alert records across 3 demo sites.

**Self-learning loop:** BetaBinomial conjugate updates (< 20 observations), RandomForest switch (≥ 20). Brier score, log-loss, MAE, calibration slope tracked. Shadow mode before production promotion.

---

## Smolt (RAS) Operator Support

Complete parallel pipeline for land-based recirculating aquaculture:

**Backend:**
- `SmoltOperatorBuilder` — builds `OperatorInput` from compact smolt form; computes `SmoltAllocationSummary` with TIV breakdown, BI, generation tracker
- `SmoltBICalculator` — annualised BI from generation duration, daily value, and cycle disruption probability
- `SmoltGenerationTracker` — fish-in-water weight across lifecycle phases
- `SmoltCalibration` — RAS-specific severity and frequency calibration factors

**API endpoints:**
- `POST /api/feasibility/smolt/run` — full smolt PCC feasibility run
- `GET /api/feasibility/smolt/example/agaqua` — Agaqua AS prefill (2024 annual report data)

**Frontend:**
- `SmoltTIVPanel` — facility count, TIV by category (biomass / property / BI / machinery / building)
- `SmoltBIWidget` — BI estimation from generation parameters
- `SmoltAllocationTab` — KPI cards reading from `financial_ratios.*` in `AllocationSummary`
- `LossHistoryTab` — split view: sea-site (domain bar chart) vs smolt (self-handled history table)

**Payload builder `buildSmoltPayload()`** includes: TIV breakdown, financials (ebitda_nok), `model` object (n_simulations, domain_correlation, use_history_calibration), and `mitigation.selected_actions`.

**Agaqua AS example data** (`agaquaExample.js`): sourced from 2024 annual report — ebitda_nok = 70 116 262.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/feasibility/run` | Sea-site PCC feasibility run |
| `POST` | `/api/feasibility/example` | Sea-site example prefill |
| `POST` | `/api/feasibility/smolt/run` | Smolt/RAS PCC feasibility run |
| `GET` | `/api/feasibility/smolt/example/agaqua` | Agaqua AS example prefill |
| `GET` | `/api/mitigation/library` | All mitigations, filtered by `facility_type` |
| `POST` | `/api/c5ai/scenario` | C5AI+ scenario override run |

PDF reports served at `/static/reports/<uuid>.pdf`.

---

## Frontend Navigation (9 items)

1. **Oversikt** — OverviewPage, top alert per domain + KPI summary
2. **Risikovurdering (C5AI+)** — 7-tab C5AI module with forecast, alert, learning tabs
3. **Varsler** — AlertsPage, filterable alert table + detail panel
4. **Inndata** — InputsPage, 5-tab input completeness + scenario overrides
5. **PCC Gjennomførbarhet** — main feasibility accordion + result tabs *(left accordion)*
6. **Strategisammenligning** — StrategyComparisonPage *(left accordion)*
7. **Læringsmodul** — LearningPage
8. **Rapporter** — ReportsPage
9. *(Operator type selector integrated into InputForm)*

`FEASIBILITY_PAGES = {'feasibility', 'strategy'}` — only these pages render the left accordion panel.

Default landing page: `overview`.

---

## Demo Sites

| ID | Name | Exposure Factor |
|---|---|---|
| `DEMO_OP_S01` | Frohavet North | 1.40 — open coast, highest risk |
| `DEMO_OP_S02` | Sunndalsfjord | 1.10 — semi-exposed |
| `DEMO_OP_S03` | Storfjorden South | 0.85 — sheltered, lowest risk |

These IDs are used consistently in all mock data files and `alert_simulator.py`.

---

## Key Economic Invariants

| Invariant | Value |
|---|---|
| Biomass valuation formula | `ref_price × 1000 × realisation × (1 − haircut)` |
| Default ref price | 80 NOK/kg → 64 800 NOK/t (with realisation=0.90, haircut=0.10) |
| SCR definition | VaR(99.5%) of net retained loss, bounded at retention |
| PCC TCOR (Nordic Aqua 5yr) | NOK 64M |
| E[annual loss] | NOK 22.6M |
| VaR 99.5% (gross) | NOK 134.2M |
| TIV | NOK 886.9M |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Python | 3.11+ |
| Numerics | NumPy (vectorised), SciPy |
| Data | Pandas |
| ML | scikit-learn (RandomForest), statsmodels |
| PDF | ReportLab Platypus |
| Charts | Matplotlib / Seaborn |
| API | FastAPI + Uvicorn |
| Validation | Pydantic v2 |
| Frontend | React 18 + Vite 5 |
| Charts (UI) | Pure SVG (no chart libraries) |
| CSS | Single `App.css` (append-only) |
| Tests | pytest (40 files, 1 413 assertions) |

---

## Architecture Invariants (Must Not Change Without Explicit Instruction)

1. **PCC pipeline is 9 steps** — do not reorder or merge
2. **C5AI+ pipeline is 7 steps** — `c5ai_plus/pipeline.py`
3. **Alert level mapping is transparent** — `alert_engine.py`
4. **Biomass valuation formula** — see above
5. **Monte Carlo:** vectorised NumPy, compound Poisson-LogNormal, N×5 matrix
6. **Domain correlation:** additive Gaussian perturbation on simplex — not multiplicative
7. **SCR = VaR(99.5%)** of net retained loss — bounded at retention
8. **`FEASIBILITY_PAGES = {'feasibility', 'strategy'}`** — only these pages show left accordion

---

## Running the Platform

```bash
# Tests
python -m pytest tests/ -q

# Backend API
uvicorn backend.main:app --reload --port 8000

# Frontend (dev)
cd frontend && npm run dev

# Frontend (build check)
cd frontend && npm run build

# CLI (sea-site)
python main.py

# CLI (C5AI+ pipeline)
python -m c5ai_plus.pipeline --input c5ai_input.json

# Self-learning demo
python examples/run_learning_loop_demo.py
```

---

## Known Tricky Areas

| Area | Note |
|---|---|
| `from_dict` abbreviation parsing | Try all `_` split positions — not just first — for keys like `env_struct` |
| `equicorrelation(0.999)` | IS positive-definite; use negative rho for non-PD matrix in tests |
| Simplex normalisation | High positive rho → MORE negative pairwise output after renorm (Aitchison geometry) |
| CSS heredoc on Windows | Fails with special chars (°, µ, backticks) — use Python script append |
| `sim.annual_losses` shape | Is `(N, T)` — use `np.percentile`, not `sorted()` |
| PCC TCOR history | Was NOK 210M (double-count bug) → corrected to NOK 64M in Sprint 8b |
| Smolt SMOLT_DOMAIN_MAPPING | 35-key alias dict required because mitigation targeted_risk_types use RAS-domain names, not DomainLossBreakdown sub-type keys |
| Smolt allocation tab | All share values are nested under `financial_ratios.*` in AllocationSummary — read from there, not top-level |
| Smolt portfolio-wide actions | `targeted_risk_types=[]` applies to ALL loss categories including structural/environmental — smolt domain-only actions must use explicit domain targets |
