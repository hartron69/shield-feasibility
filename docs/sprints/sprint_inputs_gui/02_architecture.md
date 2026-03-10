# Sprint – Inputs GUI: Architecture

## Navigation Architecture

The old 3-button inline `<nav className="page-nav">` in the app header is replaced
by a full-width secondary nav bar (`<nav className="main-nav">`) rendered between
the header and the app body. The left accordion panel (Feasibility inputs) is only
visible for pages in `FEASIBILITY_PAGES = {'feasibility', 'strategy'}`. All other
pages use the full-width right panel with `class="app-body no-left-panel"`.

```
Header (brand + tagline)
Secondary Nav (9 items, gold underline on active)
App Body
  Left Panel (accordion, only for feasibility/strategy)
  Right Panel
    ├── Overview        → OverviewPage
    ├── Inputs          → InputsPage (5 tabs)
    ├── C5AI+           → C5AIModule (existing, 5 tabs)
    ├── Alerts          → AlertsPage (existing)
    ├── PCC Feasibility → ResultPanel (existing)
    ├── Strategy Comp.  → StrategyComparisonPage
    ├── Learning        → LearningPage (wraps LearningStatusTab)
    └── Reports         → ReportsPage
```

## Inputs Page Architecture

```
InputsPage
  Tab: Site Profile     → SiteProfileForm
  Tab: Biological       → BiologicalInputsPanel
  Tab: Alert Signals    → AlertSignalsPanel
  Tab: Data Quality     → DataQualityPanel (uses InputCompletenessCard)
  Tab: Scenario Inputs  → ScenarioOverridePanel
```

### Data Flow

```
mockInputsData.js
  MOCK_SITE_PROFILES    → SiteProfileForm
  MOCK_BIOLOGICAL_INPUTS → BiologicalInputsPanel
  MOCK_ALERT_SIGNALS    → AlertSignalsPanel
  MOCK_DATA_QUALITY     → DataQualityPanel, OverviewPage
  SCENARIO_BASELINE     → ScenarioOverridePanel
  SCENARIO_PRESETS      → ScenarioOverridePanel
```

### Reusable Components

| Component | Purpose | Used by |
|---|---|---|
| `InputSourceBadge` | Colour-coded source pill (real/sim/est/missing) | SiteProfileForm, BiologicalInputsPanel, DataQualityPanel |
| `InputCompletenessCard` | Per-site completeness bar + flags | DataQualityPanel, OverviewPage |

## Mock Data Structure

`MOCK_SITE_PROFILES[]` — `site_id, site_name, region, species, biomass_tonnes, biomass_value_nok, equipment_value_nok, infra_value_nok, annual_revenue_nok, exposure_factor, operational_factor, fjord_exposure, years_in_operation, license_number, nis_certification, data_source`

`MOCK_BIOLOGICAL_INPUTS[]` — `{site_id, readings: {key: {value, baseline, unit, source}}}`

`MOCK_ALERT_SIGNALS[]` — `{site_id, risk_type, signal_name, current_value, baseline_value, delta, threshold, unit, triggered}`

`MOCK_DATA_QUALITY[]` — `{site_id, overall_completeness, overall_confidence, risk_types: {rt: {source, completeness, confidence, flag, n_obs, missing_fields}}}`

`SCENARIO_BASELINE` — single object with 6 editable keys

`SCENARIO_PRESETS[]` — `{id, label, description, overrides: {}}`
