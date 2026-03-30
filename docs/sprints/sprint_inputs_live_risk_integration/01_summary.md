# Sprint – Inputs Live Risk Integration

**Date:** 2026-03-30
**Tests after:** 1858 passed, 0 failed
**Frontend build:** 0 errors, 109 modules

---

## Objective

Connect all C5AI+ Input Data tabs to the Live Risk backend (BarentsWatch + synthetic feed)
and eliminate mock-data misrepresentations in the Portfolio Overview page.
Fix three scenario engine bugs causing baseline scenario to show non-zero change.

---

## Deliverables

### 1. BarentsWatch Client — Default CLIENT_ID (`backend/services/barentswatch_client.py`)
- Set default `CLIENT_ID = "harald@fender.link:Shield Data Client"` (matches `barentswatch_c5ai_fetcher_2.0.py`)
- Only `BW_CLIENT_SECRET` is now required; `BW_CLIENT_ID` env var is optional
- Changed guard from `if not client_id or not client_secret` → `if not client_secret`

### 2. InputSourceBadge — `operator` source type (`frontend/src/components/inputs/InputSourceBadge.jsx`)
- Added `operator` source type (yellow, "Operatør")
- Renamed `real` label from "Real" → "BarentsWatch" (green)
- Added `derived` → "Live Risk" (green) — for model-computed values

### 3. SiteProfileForm — Source-aware badges (`frontend/src/components/inputs/SiteProfileForm.jsx`)
- Fully rewritten to use `site.sources` dict and `site.bw_live` flag from `/api/live-risk/locality/{id}/inputs`
- Each field row shows the correct `InputSourceBadge` based on its data origin
- `org_number` and `bw_status` rows rendered conditionally
- Footer note: "live fra BarentsWatch" when connected vs. "Sett BW_CLIENT_SECRET" when not

### 4. Inputs panels — Live data wiring (7 panel files)
Connected to backend APIs:
- `BiologicalInputsPanel.jsx` → `/api/live-risk/locality/{id}/inputs` (temperature, oxygen, salinity, turbidity, lice)
- `StructuralInputsPanel.jsx` → same endpoint (mooring_age, net_condition, cage_count)
- `EnvironmentalInputsPanel.jsx` → same endpoint (wave_height, current_speed, wind_speed)
- `OperationalInputsPanel.jsx` → same endpoint (feed_conversion, mortality_rate, fish_density)
- `AlertSignalsPanel.jsx` → `/api/live-risk/locality/{id}/events`
- `DataQualityPanel.jsx` → `/api/c5ai/data-quality/{id}`
- `InputsPage.jsx` → `fetchInputsSnapshot()` shared across tabs

### 5. OverviewPage — Live Risk data, removed mock sections (`frontend/src/components/OverviewPage.jsx`)
**Removed** (all mock-data-driven, caused misrepresentation):
- `MOCK_ALERTS` import and `AlertSummaryCards` component
- `Learning Status` KPI card (was hardcoded "Aktiv")
- `Critical Alerts` KPI card (was mock count)
- `Top Alert by Domain` section (was mock alerts for all 4 domains)
- `AlertBadge` on site cards
- Biomass-weighted `EAL (est.)` on site cards (counterintuitive: lower-risk Hogsnes showed higher EAL due to more biomass)

**Added / replaced**:
- `fetchC5AIRiskOverview()` → `overall_risk_score`, per-site `risk_score`, `domain_breakdown`
- `fetchDataQuality(id)` → `avgCompleteness` across portfolio
- `RiskLevelBadge` (HIGH/MEDIUM/LOW derived from actual risk score)
- `Total Biomasse` KPI card (sum biomass_tonnes + biomasseverdi)
- `Biomasseverdi` shown on site cards instead of misleading EAL
- `· Live Risk` annotations on KPI subtexts for data provenance
- Loading/empty states: "Laster…" / "—" / "Ingen lokalitetsdata — start backend"

### 6. Scenario endpoint — KH default operator (`backend/api/scenario.py`)
- When `facility_type == 'sea'` and no operator provided: uses `_build_kh_default()` instead of empty `OperatorProfileInput()`
- `_build_kh_default()` builds KH portfolio (Kornstad/Leite/Hogsnes) from Live Risk config
- Premium set at ~2.5% of total revenue (market proxy)

### 7. Scenario engine — Three bug fixes (`models/scenario_engine.py`)

**Bug 1 — Biomass override normalization** (caused +168% false change):
```python
# Before: divided portfolio override by per-site biomass
site_biomass_override = params.total_biomass_override / site_biomass  # WRONG

# After: scales per-site proportionally to portfolio ratio
biomass_ratio = params.total_biomass_override / portfolio_biomass
site_override = site_biomass * biomass_ratio
```

**Bug 2 — Float precision on operational_factor** (caused +2% spurious change):
```python
# abs(1.02 - 1.0) = 0.020000000000000018 > 0.02 = True (IEEE 754)
# Before: threshold > 0.02
# After: threshold > 0.03
if params.operational_factor is not None and abs(params.operational_factor - 1.0) > 0.03:
```

**Bug 3 — Asymmetric diversification** (caused -11% artificial offset):
```python
# Before: SEA_DIVERSIFICATION applied only to scenario total
# After: applied symmetrically to both baseline and scenario
total_baseline_adj = total_baseline * SEA_DIVERSIFICATION
total_scenario_adj = total_scenario * SEA_DIVERSIFICATION
```

**Additional: `effective_change` guard** — skips MC re-run entirely when no parameters change,
eliminating deepcopy float drift as residual source of false non-zero baseline.

### 8. ScenarioOverridePanel — Model disclaimer (`frontend/src/components/inputs/ScenarioOverridePanel.jsx`)
Added disclaimer after narrative output:
> "Scenarioresultatet viser modellert endring i forventet årlig tap under feasibility-modellen.
> Absolutte NOK-verdier kan avvike fra Live Risk, mens prosentvis endring er best egnet for scenario-sammenlikning."

---

## Test Results

```
1858 passed, 0 failed
```

Updated test:
- `test_post_scenario_sea_without_sites_uses_kh_portfolio`: now asserts `len == 3` and
  verifies site names include Kornstad, Leite, Hogsnes.

---

## Build Status

Frontend: **0 errors, 0 warnings** (109 modules)

---

## Files Changed

| File | Change |
|---|---|
| `backend/services/barentswatch_client.py` | Default CLIENT_ID; only secret required |
| `backend/api/scenario.py` | `_build_kh_default()` for sea scenarios |
| `models/scenario_engine.py` | 3 bug fixes + effective_change guard |
| `frontend/src/components/OverviewPage.jsx` | Full rewrite — Live Risk data, mock sections removed |
| `frontend/src/components/inputs/SiteProfileForm.jsx` | Source-aware badges |
| `frontend/src/components/inputs/InputSourceBadge.jsx` | `operator` type, BarentsWatch label |
| `frontend/src/components/inputs/BiologicalInputsPanel.jsx` | Live data |
| `frontend/src/components/inputs/StructuralInputsPanel.jsx` | Live data |
| `frontend/src/components/inputs/EnvironmentalInputsPanel.jsx` | Live data |
| `frontend/src/components/inputs/OperationalInputsPanel.jsx` | Live data |
| `frontend/src/components/inputs/AlertSignalsPanel.jsx` | Live events |
| `frontend/src/components/inputs/DataQualityPanel.jsx` | Live data quality |
| `frontend/src/components/inputs/InputsPage.jsx` | Shared fetch wiring |
| `frontend/src/components/inputs/ScenarioOverridePanel.jsx` | Model disclaimer |
| `tests/test_sea_site_breakdown.py` | Updated for KH 3-site default |
