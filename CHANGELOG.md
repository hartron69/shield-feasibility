# Changelog — Shield Risk Platform

All notable changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [0.12.0] — 2026-03-27

### Added
- **Biomass percentage allocation** for cage portfolio. Each cage now stores `biomass_pct`
  (0–100% of the locality total) instead of absolute tonnes. `biomass_tonnes` is always
  derived: `pct × siteTotal / 100`. New `ControlSumBar` shows sum of cage percentages
  with green/blue/red status and unallocated remainder. "Fordel jevnt" button distributes
  100% equally. Empty/fallow cages (0%) are explicitly allowed and dimmed.

### Changed
- `CagePortfolioPanel.jsx` primary input changed from `biomass_tonnes` to `biomass_pct`.
- `SeaLocalityAllocationTable.jsx` recomputes cage tonnes when site biomass changes.
- `operator_builder._build_cage_pen_configs()` silently skips 0-tonne cages.

---

## [0.11.0] — 2026-03-26

### Added
- **Advanced cage weighting engine** (`models/cage_weighting.py`, `config/cage_weighting.py`).
  Locality domain risk multipliers are now driven by up to five weighting components per cage:
  biomass, economic value, consequence (value × consequence_factor × failure_mode_multiplier),
  operational complexity, and structural criticality (with SPOF/redundancy modifiers).
- `compute_locality_domain_multipliers_advanced()` — 5-step formula returning
  `AdvancedWeightingResult` with `domain_multipliers`, `weighting_mode`, `cage_weight_details`,
  and `warnings`.
- `DOMAIN_COMPONENT_WEIGHTS` — per-domain blend of the five components (config-driven).
- `CAGE_TYPE_DEFAULT_SCORES` — per cage-type defaults for all optional fields.
- Failure mode classes: `proportional` (1.0×), `threshold` (1.5×), `binary_high_consequence` (2.5×).
- SPOF multiplier (2.0×) and redundancy scale (levels 1–5: 2.0× → 0.5×).
- `CagePenConfig` extended with 7 optional advanced fields: `biomass_value_nok`,
  `consequence_factor`, `operational_complexity_score`, `structural_criticality_score`,
  `single_point_of_failure`, `redundancy_level`, `failure_mode_class`.
- Backend API: `LocalityCageRiskProfile` now returns `cage_weight_details`,
  `weighting_mode`, `warnings`.
- Frontend: per-cage collapsible "Avansert" panel in `CagePortfolioPanel.jsx` with
  default-indicator badges.
- Frontend: weighting mode badge, warnings, and collapsible per-cage domain weight
  detail table in `CageRiskProfileTab.jsx`.
- 82 new tests (`tests/test_cage_weighting.py`, 13 test classes).

### Changed
- `backend/schemas.py`: new `CageWeightDetail` Pydantic model; `CagePenInput` +7 fields;
  `LocalityCageRiskProfile` extended.
- `backend/services/operator_builder.py`: uses `compute_locality_domain_multipliers_advanced()`.
- `frontend/src/data/cageTechnologyMeta.js`: added `CAGE_TYPE_DEFAULT_SCORES`,
  `FAILURE_MODE_OPTIONS`, `REDUNDANCY_OPTIONS`.

### Notes
- Backward compatible: inputs with no advanced data → exact biomass-only fallback
  (`weighting_mode="biomass_only"`).

---

## [0.10.0] — 2026-03-26

### Added
- **Specific sea localities mode** for the PCC feasibility input form.
- `SeaLocalitySelector.jsx` — multi-select component with BW quality badges to choose
  from the Kornstad Havbruk AS locality registry (KH_S01/KH_S02/KH_S03).
- `SeaLocalityAllocationTable.jsx` — per-site biomass/value editor with "Auto-fordelt"
  labelling and collapsible cage sub-sections.
- Mode toggle: "Generisk portefølje" (unchanged) vs. "Spesifikke lokaliteter".
- Backend: `validate_selected_sites()` returns HTTP 422 on invalid/duplicate `site_ids`.
- `MetadataBlock` carries `site_selection_mode`, `selected_site_count`,
  `selected_locality_numbers`.
- `TraceabilityPanel` shows "Spesifikke lokaliteter" / "Generisk portefølje" chip.

### Changed
- All Risk Intelligence mock data updated from simulated sites (DEMO_OP_S01/02/03,
  Nordic Aqua Partners) to real Kornstad Havbruk AS localities (KH_S01/02/03:
  Kornstad, Leite, Hogsnes).
- `build_traceability_block()` accepts `site_selection_mode` parameter.
- Fixed missing `location` field in `_build_specific_sites()`.

---

## [0.9.0] — 2026-03-26

### Added
- **Cage portfolio model** — a sea locality is now a portfolio of named net-pen cages
  (merder), each with its own technology type and risk multipliers.
- `models/cage_technology.py` — `CagePenConfig` dataclass, `CAGE_DOMAIN_MULTIPLIERS`
  table, `compute_locality_domain_multipliers()`, `cage_type_summary()`.
- Four cage types: `open_net` (baseline), `semi_closed`, `fully_closed`, `submerged` —
  each with per-domain multipliers for biological, structural, environmental, operational.
- `MonteCarloEngine` accepts `cage_multipliers` dict.
- `build_domain_loss_breakdown()` accepts `cage_multipliers` for domain-level scaling.
- Backend: `FeasibilityResponse.cage_profiles` returned when cages present.
- Frontend: `CagePortfolioPanel.jsx`, `CageRiskProfileTab.jsx` ("Merd-profil" tab),
  `cageTechnologyMeta.js`.
- 52 new tests (`tests/test_cage_technology.py`).

---

## [0.8.0] — 2026-03-23

### Added
- **Input Data Audit Report** (`GET /api/inputs/audit`).
- `InputsAuditReport` Pydantic model with per-site quality data, domain coverage,
  `AuditSummary`, `C5AIStatusSnap`.
- `ReportsPage.jsx` rewritten — "Last ned rapport (JSON)" fetches audit, triggers download,
  renders inline `AuditSummaryPanel`.

---

## [0.7.0] — 2026-03-23

### Added
- **C5AI+ Traceability Refinement** — `C5AIRunMeta` extended with 8 new fields
  including `site_trace` (per-site EAL+SCR).
- `C5AISiteTracePanel.jsx` — collapsible per-site traceability table in result panel.
- `ConfirmStaleC5AIModal.jsx` — intercepts "Kjør Feasibility" when C5AI+ data is stale.
- C5AI+ trace strip in `ResultPanel.jsx` with freshness badge, run ID, site count, data mode.

---

## [0.6.0] — 2026-03-10

### Added
- **Multi-domain C5AI+ extension** — structural, environmental, operational forecasting
  added alongside existing biological module.
- `MultiDomainEngine` + three new domain packages
  (`c5ai_plus/structural/`, `/environmental/`, `/operational/`).
- 19 risk types (was 4); `RISK_TYPE_DOMAIN` mapping; `simulate_all()` → 18 alert records.
- Frontend: 3 new C5AI+ forecast tabs; 3 new input panels; domain filter on Alerts.

---

## [0.5.0] — 2026-03-10

### Added
- **Self-learning extension** — Bayesian + Random Forest model retraining from observed outcomes.
- `BetaBinomialModel`, `SklearnProbabilityModel`, `LogNormalSeverityModel`, `ModelRegistry`.
- `LearningLoop.run_cycle()` — 10-step orchestration (predict → observe → evaluate → retrain → promote).
- `ShadowModeManager` for safe model promotion.
- 66 new tests (`tests/test_learning_loop.py`).

---

## [0.4.0] — 2026-03-10

### Added
- **Alert engine** (`c5ai_plus/alerts/`, 8 modules).
- Pattern detection, probability-shift detection, level mapping, explainer, store.
- `AlertsPage` frontend with filter pills, table, detail panel.
- 64 new tests (`tests/test_alert_layer.py`).

---

## [0.3.0] — 2026-03-10

### Added
- **Inputs GUI** — 9-item nav bar, `OverviewPage`, `InputsPage` (5 tabs),
  `StrategyComparisonPage`, `LearningPage`, `ReportsPage`.
- `BioLineChart.jsx` — pure SVG Catmull-Rom spline charts for biological time series.
- `InputSourceBadge`, `InputCompletenessCard` shared components.
- `ScenarioOverridePanel.jsx` — UI-complete stub; backend route not yet wired.

---

## [0.2.0] — 2026-03-08

### Added
- **FastAPI backend** with 3 routes: `/api/mitigation/library`,
  `/api/feasibility/run`, `/api/feasibility/example`.
- **Biomass valuation suggestion system** —
  `suggested = ref_price_per_kg × 1000 × realisation × (1 − haircut)`.
- `AllocationSummary` with site breakdown, exposure ratios, financial ratios.
- **PCC calibration fixes** — correct RI/SCR/TCOR calculations:
  `retained_losses=0`, SCR from net loss distribution, annual-aggregate XL RI.
  PCC 5yr TCOR: NOK 64M (was NOK 210M with double-count bug).
- `PCCAssumptions` presets: conservative (2.5× RI loading), base (1.75×), optimised (1.25×).
- React 18 + Vite 5 GUI with left accordion panel (Operator/Model/Strategy/Mitigation/Pooling)
  and 8-tab result panel.

---

## [0.1.0] — 2026-03-07

### Added
- **Monte Carlo engine** — Compound Poisson-LogNormal, N=10k × T=5yr, vectorised NumPy.
- **Domain correlation** — `DomainCorrelationMatrix` 4×4; additive Gaussian perturbation on simplex.
- **Correlated risk analytics** — scenario extraction (p50/p95/p99), tail analysis, board narratives.
- **PDF board report** — ReportLab Platypus, 13 pages, 10 charts.
- **6-criterion suitability model** with hard cost gate.
- **12 mitigation actions** covering biological, structural, environmental, operational.
- **C5AI+ v5.0** — biological risk forecasting (HAB, lice, jellyfish, pathogen), 7-step pipeline.
- `RiskCorrelationMatrix`, `RegimeModel` (3 regimes).
- CLI entry point (`main.py`), 9-step pipeline.
