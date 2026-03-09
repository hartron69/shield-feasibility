# C5AI+ / PCC Feasibility Tool – Sprint History

Sprints are listed chronologically. Each entry links to the full sprint artifact folder.

---

## Sprint 1 – Portfolio Risk Core
**Date:** 2026-03-06
**Tests after:** 404 passed, 2 skipped

New Monte Carlo correlation and regime model infrastructure:
- `models/correlation.py` – `RiskCorrelationMatrix` (equicorrelation, Cholesky, nearest-PSD)
- `models/regime_model.py` – `RiskRegime`, `PREDEFINED_REGIMES`, `RegimeModel` (3 regimes: 75%/1×, 20%/1.8×, 5%/3.5×)
- `MonteCarloEngine`: Gaussian copula site distribution when correlation given; regime overlays
- Tests: `test_correlation.py`, `test_regime_model.py` (44 + 28 new)

---

## Sprint 2–6 – Core PCC Pipeline
**Approximate dates:** 2026-03-06 – 2026-03-07
**Tests after:** 586 passed

Key deliverables across multiple sprints:
- Full 9-step PCC feasibility pipeline (`main.py`)
- PDF report generation (ReportLab Platypus, 13 pages, 10 charts)
- Suitability engine (6-criterion model)
- Mitigation library (10 actions)
- Domain loss breakdown (`DomainLossBreakdown`)
- PCC Captive strategy (`PCCCaptiveStrategy`)
- Forecast schema (`c5ai_plus/`) with HAB, lice, jellyfish, pathogen forecasters
- FastAPI backend + React 18 frontend (Sprint 8 GUI)

---

## Sprint 7 – Cross-Domain Risk Correlation
**Date:** 2026-03-07
**Tests after:** 694 passed, 2 skipped

See `docs/SPRINT7_DOMAIN_CORRELATION.md` for full details.

Key additions:
- `models/domain_correlation.py` – `DomainCorrelationMatrix` (4×4), expert default, `equicorrelation()`, `from_dict()`
- Additive Gaussian perturbation on simplex (base_fracs + α×Z_corr, clip≥0, renorm)
- `reporting/correlated_risk_analytics.py` – scenario extraction, tail analysis, board narratives
- 3 new PDF charts: domain correlation heatmap, scenario domain stacks, tail domain composition
- Expert-default matrix: bio-struct=0.20, env-struct=0.60, env-bio=0.40, ops-struct=0.35
- Tests: `test_domain_correlation.py`, `test_mc_domain_correlation.py`

---

## Sprint 8 – GUI Layer + PCC Calibration Fixes
**Date:** 2026-03-07 – 2026-03-08
**Tests after:** 826 passed

### GUI Layer (Sprint 8a)
- `backend/` – FastAPI thin adapter: `GET /api/mitigation/library`, `POST /api/feasibility/run`, `POST /api/feasibility/example`
- `backend/schemas.py` – Pydantic request/response models
- `backend/services/operator_builder.py` – SimplifiedProfile → OperatorInput (TIV-scaled)
- `backend/services/run_analysis.py` – 9-step pipeline adapter
- `frontend/` – React 18 + Vite 5; accordion input panel, 6-tab result panel
- Tests: `test_backend_api.py` (16 tests), `test_operator_builder.py` (31 tests)

### PCC Calibration Fixes (Sprint 8b)
- `models/pcc_economics.py` – `PCCAssumptions` presets (conservative/base/optimised)
- Fixed 3 bugs in `PCCCaptiveStrategy`: double-count of retained losses, gross vs. net SCR, annual-aggregate XL structure
- PCC 5yr TCOR: 210M (incorrect) → 64M (correct)
- Tests: `test_pcc_calibration.py` (37), `test_pcc_report_fixes.py` (21)

### Biomass Valuation Suggestion System
- Formula: `suggested = ref_price × 1000 × realisation × (1 − haircut)`
- Defaults: ref=80 NOK/kg, realisation=0.90, haircut=0.10 → 64,800 NOK/t
- GUI: Ref Price / Realisation / Haircut / Suggested (read-only) / Applied (editable) / "Use suggested" button
- Tests: `test_biomass_valuation.py` (25 tests)

---

## Sprint 9 – Self-Learning Extension
**Date:** 2026-03-10
**Tests after:** 1028 passed, 0 failed

See `docs/sprints/sprint_self_learning_extension/` for full sprint artifacts.

Adds a full **predict → observe → evaluate → retrain** loop to C5AI+:
- 3 new packages: `c5ai_plus/learning/`, `c5ai_plus/models/`, `c5ai_plus/simulation/`
- 13 new files + 3 modified (settings, forecast schema, base forecaster)
- **BetaBinomialModel** (conjugate Bayesian, works from sample 1) + **SklearnProbabilityModel** (RF, n≥20)
- **LogNormalSeverityModel** (Welford online MLE)
- **ModelRegistry**: load/save/version/shadow/promote per (operator_id, risk_type)
- **LearningLoop.run_cycle()**: 10-step orchestration, returns `LearningCycleResult`
- **SiteDataSimulator**: synthetic `C5AIOperatorInput` with seasonal temperature, HAB, lice, jellyfish, pathogens
- **EventSimulator**: Bernoulli events + LogNormal losses + cross-risk HAB correlation
- Learning status: cold (<3 cycles) → warming (3–9) → active (≥10)
- 100% backward-compatible PCC interface (`scale_factor`, `loss_fractions` unchanged)
- Tests: `test_learning_loop.py` (66 tests, 9 classes)
- Demo: `examples/run_learning_loop_demo.py`

**Sprint artifacts:**
| File | Contents |
|---|---|
| `01_summary.md` | Objective, design principles, demo output |
| `02_architecture.md` | Package layout, data flow diagram, storage layout |
| `03_code_changes.md` | Every new and modified file documented |
| `04_tests.md` | All 66 tests described with assertions |
| `05_limitations.md` | 10 known limitations + follow-on work |
| `06_demo_run.md` | How to run demo, expected output, code snippets |
