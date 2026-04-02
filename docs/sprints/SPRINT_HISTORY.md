# C5AI+ / PCC Feasibility Tool – Sprint History

Sprints are listed chronologically. Each entry links to the full sprint artifact folder.

---

## Sprint – ILA Live Data Integration (2026-04-02)
**Tests after:** 2116 passed, 0 failed (unchanged) | Frontend: 109 modules, 0 errors (+1 file)
**Artifacts:** `docs/sprints/sprint_ila_live_data/`
**Summary:** Wired ILA motor inputs to live operational data. `input_builder.py` rewritten: `biomasse_tetthet_norm` = `biomass_tonnes/mtb_tonnes`; `stressniva_norm` = 7-day weighted composite (lice 0.30, temp 0.15, O₂ 0.35, treatment 0.20); `antall_nabo_med_ila` from neighbor disease flags; `i_fraksjon_naboer` from neighbor lice proxy; `e0` for MRE-2 from disease flag recency (7d→0.03, 21d→0.01). New neighbor group map covers KH_S01/02/03 and LM_S01. `backend/api/ila.py` updated: MRE-2 endpoint now calls `bygg_mre2_e0()` and passes `e0` to SEIR motor. `LiveRiskFeedPage.jsx` gains "ILA" column: fetches `/api/ila/portfolio` on mount, renders `IlaBadge` per row (GRØNN/ILA01–ILA04).

## Sprint – ILA Risk Module (2026-04-02)
**Tests after:** 2116 passed, 0 failed (+68 new) | Frontend: 108 modules, 0 errors (+2 files)
**Artifacts:** `docs/sprints/sprint_ila_risk_module/`
**Summary:** Integrated ILA (Infeksiøs lakseanemi) risk models as a new sub-module of the C5AI+ v5.0 biological domain. New `c5ai_plus/biological/ila/` package: `mre1.py` (7-source instantaneous P_total snapshot ported from `/reference/mre_full_comparison.py`), `mre2.py` (52-week SEIR seasonal hazard model ported from `/reference/mre2_progression.py`), `patogen_kobling.py` (blends ILA P_total into existing C5AI+ pathogen prior, vekt=0.60, cap=0.70), `input_builder.py` (mock profiles for KH_S01/02/03 and LM_S01). New API: `GET /api/ila/{id}/mre1`, `GET /api/ila/{id}/mre2`, `GET /api/ila/portfolio`. Frontend: `ILARiskTab.jsx` with varselnivå-header (ILA01–ILA04), source attribution table with bar charts, pure SVG 52-week seasonal curve with threshold bands, SEIR badge; wired as "ILA-risiko" tab (9th) in `LocalityLiveRiskPage`. 68 new tests across 5 files. DB/Celery components (ORM models, Alembic, Celery tasks, auth) documented and ready for production DB integration.

## Sprint – Locality Monte Carlo Integration Sprint 2 (2026-03-30)
**Tests after:** 2048 passed, 0 failed (+97 new) | Frontend: 107 modules, 0 errors (+3 files)
**Artifacts:** `docs/sprints/sprint_locality_mc_integration/`
**Summary:** Bridged `LocalityRiskProfile` (Sprint 1) into the existing `MonteCarloEngine` for per-locality stochastic loss distributions. New `models/locality_mc_inputs.py`: `build_locality_mc_inputs()` translates profile into `LocalityMonteCarloInput` via sigmoid score multipliers (freq range 0.40–1.60, sev range 0.70–1.30, both neutral at score=50), domain-weighted multiplier blends (bio/env/ops → freq; struct/ops/bio → sev), and `non_bio_domain_fracs` from `domain_weights`. New `backend/services/locality_mc_runner.py`: `LocalityMCResult` with EAL, SCR (VaR 99.5%), VaR 95/99, TVaR 95, std, domain_eal_nok, domain_fractions, transparency fields; `run_locality_mc()` and `run_locality_mc_batch()`. New API: `GET /api/localities/{id}/mc?n_simulations=5000` and `POST /api/localities/mc-batch`. Frontend: `LocalityMCPanel.jsx` with KPI cards, pure SVG stacked domain bar, collapsible transparency table; wired as "Tap (MC)" tab in `LocalityLiveRiskPage.jsx`. 97 new tests across 10 classes including monotonicity and KH known-value range checks.

## Sprint – Locality Risk Engine Sprint 1 (2026-03-30)
**Tests after:** 1940 passed, 0 failed (+82 new) | Frontend build: unchanged (backend-only)
**Artifacts:** `docs/sprints/sprint_locality_risk_engine/`
**Summary:** Established `LocalityRiskProfile` as the single source of truth for per-locality risk. New model (`models/locality_risk_profile.py`) with 4 dataclasses: `LocalityRiskProfile`, `DomainRiskScores`, `DomainRiskWeights`, `RiskSourceSummary`. New builder service (`backend/services/locality_risk_builder.py`) with `build_locality_risk_profile(locality_id, cages=None)` and `build_locality_risk_profiles(ids, cages_by_locality=None)` that compose Live Risk feed + confidence scoring + cage weighting without re-implementing their internals. Profile fields: domain_scores (raw 0–100), domain_weights (normalized weighted contributions, sum=1), scale_factors (fixed model weights bio=0.35/struct=0.25/env=0.25/ops=0.15), domain_multipliers (cage-derived or 1.0 defaults), concentration_flags, top_risk_drivers, confidence_level/notes, source_summary, used_defaults. New API router (`backend/api/localities.py`): `GET /api/localities/{id}/risk-profile` and `POST /api/localities/risk-profiles` (batch, partial-failure tolerant). All 3 KH localities tested with known values. 82 new tests across 8 classes. No existing module broken.

## Sprint – Inputs Live Risk Integration (2026-03-30)
**Tests after:** 1858 passed, 0 failed | Frontend build: 0 errors, 109 modules
**Artifacts:** `docs/sprints/sprint_inputs_live_risk_integration/`
**Summary:** Connected all C5AI+ Input Data tabs to Live Risk backend. BarentsWatch client updated to use default CLIENT_ID (`"harald@fender.link:Shield Data Client"`) so only `BW_CLIENT_SECRET` is required. `SiteProfileForm.jsx` rewritten to use `sources` dict and `bw_live` flag from API for correct badge rendering. All 7 input panels (`BiologicalInputsPanel`, `StructuralInputsPanel`, `EnvironmentalInputsPanel`, `OperationalInputsPanel`, `AlertSignalsPanel`, `DataQualityPanel`, `InputsPage`) wired to live fetch functions. `OverviewPage.jsx` completely rewritten: removed 5 mock-data sections (MOCK_ALERTS, AlertSummaryCards, Learning Status KPI, Top Alert by Domain, biomass-weighted EAL), replaced with live data from `fetchC5AIRiskOverview()` and `fetchDataQuality()`, added `RiskLevelBadge` and `Total Biomasse` KPI. Scenario endpoint default sea operator changed from empty profile to KH portfolio built from Live Risk config (`_build_kh_default()`). Fixed 3 scenario engine bugs causing baseline to show non-zero change: (1) biomass override normalization — portfolio ratio instead of per-site division; (2) float precision threshold `> 0.02` → `> 0.03` for `operational_factor`; (3) asymmetric `SEA_DIVERSIFICATION` now applied to both baseline and scenario. Added `effective_change` guard to skip scenario MC re-run when no parameters change. Added model disclaimer text to `ScenarioOverridePanel.jsx`.

## Sprint – Live Feed → C5AI Risk Score Wiring (2026-03-27)
**Tests after:** 1858 passed, 0 failed | Frontend build: 0 errors, 109 modules
**Artifacts:** `docs/sprints/sprint_live_feed_c5ai_wiring/`
**Summary:** Connected the Live Risk feed to the C5AI+ Risk Intelligence module. Added `GET /api/c5ai/risk-overview` backend endpoint that derives `overall_risk_score`, per-site risk scores, and domain breakdown fractions from the current live risk feed snapshot (biomass-weighted, consistent with `_compute_risk()` domain weights). Frontend: new `c5aiRiskData` state in `App.jsx` fetched on mount and on every manual "Oppdater feed" click (via `onFeedRefreshed` callback passed to `LiveRiskFeedPage`). C5AIModule receives a merged object where the live risk scores override the static `C5AI_MOCK` while forecast data stays mock. Falls back silently to static mock if backend is unreachable.

## Sprint – Mitigation Tab Fixes & CV Transparency (2026-03-27)
**Tests after:** 1858 passed, 0 failed | Frontend build: 0 errors, 109 modules
**Artifacts:** `docs/sprints/sprint_mitigation_tab_fixes/`
**Summary:** Fixed two bugs in the Mitigation results tab: (1) NaN % in Vekt column — root cause was missing `"weight"` key in `crit_deltas` dicts in `run_analysis.py` (both smolt and sea paths); (2) misleading "Score improves by +0.0 pts" note — replaced with Norwegian message "Tiltakene krysser ingen kriterieterskler — poengsummen er uendret." Added CV transparency to Loss Stability finding in `suitability_engine.py`: `"CV≈0.78"` → `"CV: 0.92 → 0.78 (terskel <0.75 for neste band)"`. Balance Sheet finding translated to Norwegian. `MitigationTab.jsx` now renders the `finding` text as italic subtitle below criterion name in the Kriterievis table.

## Sprint – Risk Intelligence Copy & Label Cleanup (2026-03-27)
**Tests after:** 1858 passed, 0 failed | Frontend build: 0 errors, 109 modules
**Artifacts:** `docs/sprints/sprint_risk_intelligence_copy_cleanup/`
**Summary:** Applied comprehensive Norwegian-language copy pass across all six C5AI+ module files. Added strategic banner (blue callout) and footer disclaimer in `RiskOverviewTab.jsx`. Replaced all English labels: Portfolio Risk → Selskapets risikobilde, Risk Score → Strategisk risikonivå, Site Risk Ranking → Viktigste lokaliteter, Domain → Risikotype, Learning → Strategiske mønstre, and 15+ other labels. All 20 risk type identifiers now have Norwegian display names. `C5AIModule.jsx` header updated. Captive bridge wording strengthened with italic contextual helper text under every section.

## Sprint – Risk Intelligence Refactor (2026-03-27)
**Tests after:** unchanged (backend unmodified) | Frontend build: 0 errors, 109 modules
**Artifacts:** `docs/sprints/sprint_risk_intelligence_refactor/`
**Summary:** Separated Risk Intelligence (strategic portfolio/captive dashboard) from Live Risk (operational source of truth). Removed 3 overlapping tabs from C5AIModule: Alerts, BarentsWatch, and Anlegg — these are operational views now owned by Live Risk. Removed AlertSummaryCards from RiskOverviewTab. Added: concentration analysis panel with biomass distribution bar and HHI badge, "Live Risk →" per-site link-out buttons that navigate directly to locality detail, Norwegian tab labels throughout. App.jsx wires `onNavigateToLiveRisk` callback to C5AIModule so site link-outs land on the correct locality page.

## Sprint – Live Risk Intelligence (2026-03-27)
**Tests after:** 1810 passed, 0 failed (+76 new) | Frontend build: 0 errors, 113 modules
**Artifacts:** `docs/sprints/sprint_live_risk_intelligence/`
**Summary:** Added a dedicated "Live Risk" top-level module (4th L1 nav item) giving full transparency into locality data feeds. Backend: 6 new service files (`live_risk_mock.py`, `source_health.py`, `confidence_scoring.py`, `event_timeline.py`, `risk_change_explainer.py`, `live_risk_feed.py`) and 1 new API router (`backend/api/live_risk.py`) with 9 endpoints at `/api/live-risk/`. Mock data uses deterministic seeded synthetic time series for the 3 Kornstad Havbruk AS localities (90 days, 5 measurement parameters). Frontend: 8 new components (`LiveRiskFeedPage.jsx`, `LocalityLiveRiskPage.jsx`, `RawDataChart.jsx`, `RiskHistoryChart.jsx`, `SourceStatusPanel.jsx`, `RiskChangeBreakdownPanel.jsx`, `RiskEventsTimeline.jsx`, `ConfidenceBadge.jsx`) plus 9 fetch functions in `client.js` and `lr-*` CSS classes. No new npm dependencies — all charts are pure SVG.

## Sprint – Biomass Percentage Allocation (2026-03-27)
**Tests after:** 1734 passed, 0 failed (no change — UI-only + minor backend guard) | Frontend build: 0 errors, 105 modules
**Artifacts:** `docs/sprints/sprint_biomass_pct_allocation/`
**Summary:** Changed cage biomass input from absolute tonnes to percentage of the locality's total biomass. Each cage stores `biomass_pct` (0–100); `biomass_tonnes` is always derived as `pct × siteTotal / 100`. New `ControlSumBar` in `CagePortfolioPanel.jsx` shows sum of cage percentages with green/blue/red status and the unallocated remainder in tonnes. "Fordel jevnt" button distributes 100% equally. Empty/fallow cages (0%) dimmed with "Tom" label. `SeaLocalityAllocationTable.jsx` passes `totalSiteBiomass` prop and recomputes cage tonnes when site biomass changes. Backend: `_build_cage_pen_configs()` silently skips 0-tonne cages.

## Sprint – Advanced Cage Weighting (2026-03-26)
**Tests after:** 1734 passed, 0 failed (+82 new) | Frontend build: 0 errors, 105 modules
**Artifacts:** `docs/sprints/sprint_advanced_cage_weighting/`
**Summary:** Extended cage portfolio model (Sprint 2) with multi-factor weighting engine. A locality's effective domain risk multipliers are now driven by five components: biomass, economic value, consequence (value × consequence_factor × failure_mode_multiplier), operational complexity, and structural criticality (with SPOF/redundancy modifiers). New files: `config/cage_weighting.py` (constants), `models/cage_weighting.py` (engine with `compute_locality_domain_multipliers_advanced()`). `CagePenConfig` extended with 7 optional advanced fields. Backend API now returns `cage_weight_details`, `weighting_mode`, and `warnings` per locality. Backward compatible: no advanced data → exact biomass-only fallback. Frontend: per-cage collapsible "Avansert" panel in `CagePortfolioPanel.jsx`; per-locality weighting mode badge and collapsible weight detail table in `CageRiskProfileTab.jsx`.

## Sprint – Specific Sea Localities (2026-03-26)
**Tests after:** 1600 passed, 0 failed (+20 new) | Frontend build: 0 errors, 102 modules
**Artifacts:** `docs/sprints/sprint_specific_sea_localities/`
**Summary:** Added specific-locality mode for sea PCC feasibility. Users can now toggle between "Generisk portefølje" (existing behavior unchanged) and "Spesifikke lokaliteter" (select actual BW-registered sites). New frontend components: `SeaLocalitySelector.jsx` (fetch registry, multi-select with BW quality badges) and `SeaLocalityAllocationTable.jsx` (per-site biomass/value editor with "Auto-fordelt" labelling). Backend: validation via `validate_selected_sites()` returns HTTP 422 on invalid/duplicate site_ids; `MetadataBlock` now carries `site_selection_mode`, `selected_site_count`, `selected_locality_numbers`; `TraceabilityBlock.site_selection_mode` propagated from `alloc_summary`; fixed missing `location` field in `_build_specific_sites()`. TraceabilityPanel displays "Spesifikke lokaliteter" / "Generisk portefølje" chip. Limitations: domain modelling remains portfolio-level; registry currently limited to Kornstad Havbruk AS (3 sites).

---

## Sprint – Input Data Audit Report (2026-03-23)
**Tests after:** 1 533 passed, 0 failed (+18 new) | Frontend build: 0 errors, 100 modules
**Artifacts:** `docs/sprints/sprint_input_audit/` (pending)
**Summary:** Delivered the Input Data Audit Report as a live, downloadable JSON report. Backend: new `backend/api/inputs_audit.py` — `GET /api/inputs/audit` returns an `InputsAuditReport` with Pydantic models `RiskTypeAudit`, `SiteAudit`, `DomainCoverage`, `AuditSummary`, `C5AIStatusSnap`. Per-site quality data for all three demo sites (DEMO_OP_S01–S03, 19 risk types each) mirrors `mockInputsData.js MOCK_DATA_QUALITY` for frontend/backend consistency. Domain coverage is live: biological is `c5ai_plus` when C5AI+ is fresh, falls back to `estimated` when missing; structural/environmental/operational are always `estimated`. Model limitations documented in Norwegian (6 items). Router registered in `backend/main.py`. Frontend: `ReportsPage.jsx` rewritten with `useState` — `input_audit` status changed from `planned` to `available`; "Last ned rapport (JSON)" button fetches `/api/inputs/audit`, triggers JSON file download, and renders inline `AuditSummaryPanel` showing C5AI+ freshness badge, 6 KPI cards, domain coverage badges, per-site completeness bars, and model limitations list. `fetchInputsAudit()` added to `client.js`. CSS appended to `App.css`. Tests: `tests/test_inputs_audit.py` — 18 tests across 3 classes (endpoint shape, data correctness, live C5AI+ state reflection).

---

## Sprint – C5AI+ Traceability Refinement (2026-03-23)
**Tests after:** 1 508 passed, 0 failed (+5 new) | Frontend build: 0 errors, 100 modules
**Artifacts:** `docs/sprints/sprint_c5ai_traceability_refinement/`
**Summary:** Strengthened trust, traceability, and site-level visibility between C5AI+ and PCC Feasibility. Part 1 — Extended `C5AIRunMeta` with 8 new optional fields: `site_count`, `site_ids`, `site_names`, `data_mode` (simulated/real/mixed), `domains_used`, `risk_type_count`, `source_labels`, `site_trace` (per-site EAL+SCR from loss analysis). `c5ai_state.py` gains `store_run_extra()` / `get_run_extra()` to persist run-time metadata. `_build_c5ai_meta()` now accepts `loss_analysis` and `traceability` arguments and builds a full `site_trace`. Part 2 — `ResultPanel.jsx` meta bar replaced with a richer `c5ai-trace-strip` showing freshness badge, run ID, timestamp, and chips for site count / data mode / domains. New `C5AISiteTracePanel.jsx` is a collapsible table beneath the strip showing per-site: dominant domain pill, EAL, SCR contribution, with "Se anlegg i C5AI+ Risiko →" deep-link. Part 3 — New `ConfirmStaleC5AIModal.jsx` intercepts "Kjør Feasibility" when C5AI+ is stale (offers "Oppdater C5AI+ først" / "Kjør likevel") or missing (blocks with only "Oppdater" option). `App.jsx` `handleRun()` checks freshness and shows modal; original run logic renamed to `_doRun()`.

---

## Sprint – C5AI+ Activation and Freshness Gate (2026-03-22)
**Tests after:** 1 503 passed, 0 failed (+19 new) | Frontend build: 0 errors, 98 modules
**Artifacts:** `docs/sprints/sprint_c5ai_gate/`
**Summary:** Implemented a gate requiring users to explicitly run C5AI+ before feasibility analysis. Backend: new `backend/services/c5ai_state.py` — thread-safe in-memory singleton tracking `_c5ai_last_run_at` and `_inputs_last_updated_at`; freshness rules: `missing` (never run), `stale` (inputs changed after last run), `fresh` (run is up to date). New `backend/api/c5ai.py` — `POST /api/c5ai/run` (triggers `MultiDomainEngine`, stubs on failure), `GET /api/c5ai/status`, `POST /api/c5ai/inputs/updated`. `backend/schemas.py` gains `C5AIRunResponse`, `C5AIStatusResponse`, `C5AIRunMeta`; `FeasibilityResponse` gains `c5ai_meta` field so every feasibility result carries its C5AI+ lineage metadata. Frontend: new `C5AIStatusBar.jsx` (green/yellow/red dot, timestamp, "Oppdater C5AI+" button with spinner). `RunControls.jsx` accepts `c5aiStatus` and shows yellow warning banner when stale/missing; labels translated to Norwegian. `App.jsx` gains `c5aiStatus`/`c5aiLoading` state, `handleC5AIRun()`, on-mount status fetch, and `notifyInputsUpdated()` calls after example loads. `ResultPanel.jsx` shows a colour-coded "Basert på C5AI+ kjøring…" meta bar above the tab strip.

---

## Sprint – C5AI+ → Feasibility Traceability (2026-03-22)
**Tests after:** 1 484 passed, 0 failed (+19 new) | Frontend build: 0 errors, 97 modules
**Artifacts:** `docs/sprints/sprint_traceability_c5ai_feasibility/`
**Summary:** Introduced full data lineage between the C5AI+ risk intelligence module and the PCC feasibility analysis. Added `TraceabilitySiteTrace` and `TraceabilityBlock` Pydantic models to `backend/schemas.py`, with `traceability: Optional[TraceabilityBlock]` as the last field on `FeasibilityResponse` (backward-compatible, defaults to `null`). New `backend/services/traceability.py` builds the block from simulation results — capturing `source` (`static_model`/`c5ai_plus`/`c5ai_plus_mitigated`), `c5ai_scale_factor`, active domains and risk types from `DomainLossBreakdown`, per-site EAL and SCR from `LossAnalysisBlock`, and a Norwegian method note explaining model assumptions. Both `run_feasibility_analysis` and `run_feasibility_service` now populate `traceability`. Frontend: new `TraceabilityPanel.jsx` renders pipeline flow diagram, KPI cards, site trace table, domain pills, risk type chips, and collapsible method note. `ResultPanel.jsx` extended with 10th tab "Datagrunnlag". `App.jsx` passes `onNavigate={navigateTo}` to `ResultPanel` for cross-navigation to C5AI+ Risk from within the Datagrunnlag tab.

---

## Sprint – Dashboard-First Navigation (2026-03-22)
**Tests after:** 1 465 passed, 0 failed (unchanged — frontend-only) | Frontend build: 0 errors, 96 modules
**Artifacts:** `docs/sprints/sprint_dashboard_navigation/`
**Summary:** Replaced the 8-item flat top navigation bar with a 2-level structure and a new `DashboardPage` as the default landing page. Level 1 (navy bar): Dashboard | Risk Intelligence | PCC Feasibility. Level 2 (light grey sub-nav): conditional per section — Risk: Oversikt/Målinger/Risiko/Varsler/Læring; Feasibility: Oversikt/Tapsanalyse/Tiltak/Strategi/Rapporter. New `DashboardPage.jsx` shows hero banner, 4 KPI cards, two workflow cards (C5AI+ and PCC), and 7 quick-link pills. `App.jsx` refactored: `activePage` replaced by `activeMainSection`/`activeRiskTab`/`activeFeasibilityTab`; `navigateTo()` function handles both new-style `(section, tab)` and legacy string IDs for backward compat with `OverviewPage.onNavigate`. `ResultPanel` gains `initialTab` prop for deep-linking from feasibility sub-nav. CSS layout switched from `calc(100vh - 56px)` to proper `app-shell` flexbox to correctly account for both nav bars.

---

## Sprint – Tapsanalyse: Real Loss Analysis (2026-03-22)
**Tests after:** 1 465 passed, 0 failed (+30 new) | Frontend build: 0 errors, 95 modules
**Artifacts:** `docs/sprints/sprint_loss_analysis/`
**Summary:** Replaced empty "Ingen per-lokalitet tapsdata tilgjengelig" placeholder in Tapsanalyse tab with real structured loss analysis. Root cause: `FeasibilityResponse` had no loss_analysis field; ResultPanel read `result.facility_results` which was always undefined; `sim.site_loss_distribution` was populated but never extracted. Fix: new `backend/services/loss_analysis.py` derives per-site EAL (exact, from Monte Carlo site distribution), SCR contribution (proportional tail method), per-site domain breakdown (proportional approximation), and top risk drivers (from DomainLossBreakdown subtypes). New `LossAnalysisBlock` Pydantic model added to `FeasibilityResponse`. Full `SeaSiteLossTable.jsx` rewrite shows KPI row, domain bar, per-site expandable table, top drivers, and method note. Mitigated deltas shown when mitigation is active.

---

## Sprint – Smolt Mitigation Composite Score Fix (2026-03-22)
**Tests after:** 1 435 passed, 0 failed (+22 new) | Frontend build: 0 errors, 95 modules
**Artifacts:** `docs/sprints/sprint_smolt_mitigation_score_fix/`
**Summary:** Fixed bug where smolt operator mitigation produced a negative composite score delta despite improving loss/SCR. Root cause: `estimate_mitigated_score()` used aggregate simulated CV (≈2.1 due to compound-Poisson zero-inflation) to recompute Loss Stability for smolt, whereas `assess()` correctly uses per-event `cv_loss_severity=0.65`. Fix carries Loss Stability forward unchanged for smolt. Added `_SMOLT_READINESS_UPLIFTS` for bounded additive score improvements when smolt operational actions (`smolt_staff_training`, `smolt_emergency_plan`, `smolt_alarm_system`) are selected. API `ComparisonBlock` extended with `composite_score_delta`, `criterion_deltas`, and `mitigation_score_note`. MitigationTab now shows per-criterion before/after table and note banner.

---

## Sprint – Site Risk GUI: Smolt / RAS Site-Level Risk (2026-03-22)
**Tests after:** 1 413 passed, 0 failed (unchanged — frontend-only) | Frontend build: 0 errors, 95 modules
**Artifacts:** `docs/sprints/sprint_site_risk_gui/`
**Summary:** Made individual smolt/RAS facility risk visible in the existing GUI. New mock data for 5 demo facilities (`mockSmoltSiteRiskData.js`). New component package `components/smolt/`: `SiteRiskSummaryCards`, `TopRiskSitesTable`, `SiteEALChart`, `SiteSCRContributionChart`, `SiteRiskDetailPanel`, `SmoltSiteRiskTab`. OverviewPage gains "Topp risikoanlegg" section (top-3 cards + inline detail panel). C5AIModule gains 8th tab "Anlegg" with table/charts toggle, portfolio KPIs, and full site ranking. All charts are pure SVG. Backward compatible — sea-site operators unaffected.

---

## Sprint – Multi-Domain C5AI+ Extension (2026-03-10)
**Tests after:** 1155 passed, 0 failed | Frontend build: 0 errors, 82 modules
**Artifacts:** `docs/sprints/sprint_multidomain_c5ai/`
**Summary:** Extended C5AI+ to cover structural, environmental, and operational risk domains alongside biological. New packages: `c5ai_plus/structural/`, `c5ai_plus/environmental/`, `c5ai_plus/operational/`, `c5ai_plus/multi_domain_engine.py`. Alert layer extended with 15 new risk types and domain field. GUI updated with 3 new input panels, 3 new forecast tabs, domain filters, and domain badges. 63 new tests.

---

## Sprint – Biological Input Line Charts (2026-03-10)
**Tests after:** 1092 passed, 0 failed | Frontend build: 0 errors, 76 modules
**Artifacts:** `docs/sprints/sprint_bio_charts/`

Pure SVG time-series charts (no new npm deps) on the Inputs → Biological Inputs tab.
New: `mockBioTimeseries.js` (12 months × 11 params × 3 sites), `BioLineChart.jsx` (smooth Catmull-Rom spline, hover tooltip, baseline + threshold reference lines, risk-zone fill).
Updated: `BiologicalInputsPanel.jsx` (Grafer/Tabell toggle, 5-group filter, breached-threshold card highlighting). CSS: ~3.8 kB appended to App.css.

---

## Sprint – Inputs GUI (2026-03-10)
**Tests after:** 1092 passed, 0 failed | Frontend build: 0 errors
**Artifacts:** `docs/sprints/sprint_inputs_gui/`

Navigation expanded from 3 to 9 items. New Inputs page with 5 tabs (Site Profile, Biological Inputs, Alert Signals, Data Quality, Scenario Inputs). New reusable components: `InputSourceBadge`, `InputCompletenessCard`, `SiteProfileForm`, `BiologicalInputsPanel`, `AlertSignalsPanel`, `DataQualityPanel`, `ScenarioOverridePanel`. New lightweight pages: `OverviewPage`, `StrategyComparisonPage`, `LearningPage`, `ReportsPage`. Mock data in `mockInputsData.js`. Zero breaking changes.

---

## Sprint – Alert Layer (2026-03-10)
**Tests after:** 1092 passed (+64) | Frontend build: 0 errors
**Artifacts:** `docs/sprints/sprint_alert_layer/`

Early warning / alert layer. 8 new Python files in `c5ai_plus/alerts/`. 64 new tests. React alert components: `AlertsPage`, `AlertTable`, `AlertDetailPanel`, `AlertSummaryCards`, `AlertLevelBadge`, `ProbabilityShiftBadge`. Mock data in `mockAlertsData.js`.

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
