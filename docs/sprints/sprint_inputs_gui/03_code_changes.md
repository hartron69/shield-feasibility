# Sprint – Inputs GUI: Code Changes

## New Files

### Data
- `frontend/src/data/mockInputsData.js` — MOCK_SITE_PROFILES, MOCK_BIOLOGICAL_INPUTS, MOCK_ALERT_SIGNALS, MOCK_DATA_QUALITY, SCENARIO_BASELINE, SCENARIO_PRESETS, BIO_READING_LABELS

### Components – Inputs
- `frontend/src/components/inputs/InputsPage.jsx` — 5-tab page shell
- `frontend/src/components/inputs/SiteProfileForm.jsx` — 3-site grid of profile cards
- `frontend/src/components/inputs/BiologicalInputsPanel.jsx` — readings table with site selector
- `frontend/src/components/inputs/AlertSignalsPanel.jsx` — signal table with filter controls
- `frontend/src/components/inputs/DataQualityPanel.jsx` — completeness cards + per-risk-type detail
- `frontend/src/components/inputs/ScenarioOverridePanel.jsx` — editable fields + sliders + Run Scenario stub
- `frontend/src/components/inputs/InputSourceBadge.jsx` — colour-coded source pill
- `frontend/src/components/inputs/InputCompletenessCard.jsx` — site completeness bar + flags

### Pages
- `frontend/src/components/OverviewPage.jsx` — portfolio KPIs + alerts + domain losses + completeness
- `frontend/src/components/StrategyComparisonPage.jsx` — 3-strategy comparison grid
- `frontend/src/components/LearningPage.jsx` — wraps LearningStatusTab + data context banner
- `frontend/src/components/ReportsPage.jsx` — available/planned report types

## Modified Files

### `frontend/src/App.jsx`
- Added imports for 7 new page/component imports
- Replaced 3-button inline `page-nav` with `main-nav` bar containing 9 `NAV_ITEMS`
- Added `FEASIBILITY_PAGES` set to control left panel visibility
- Left panel conditional: `{showLeftPanel && <div className="left-panel">...`
- Added `app-body` class variant: `no-left-panel`
- Added routing for 5 new pages in right panel
- `handleExample` now also calls `setActivePage('feasibility')`
- Default `activePage` changed from `'feasibility'` to `'overview'`

### `frontend/src/App.css`
Appended ~250 lines:
- `.main-nav` / `.main-nav-btn` / `.main-nav-btn.active` — gold underline active state
- `.app-body.no-left-panel .right-panel` — 24px padding for full-width pages
- `.page-nav { display: none }` — backward compat hide
- `.overview-kpi-row`, `.overview-kpi-card` etc.
- `.inputs-page`, `.inputs-note`, `.inputs-empty`
- `.input-source-badge`, `.source-*`
- `.completeness-card`, `.dq-completeness-row`, `.dq-flag-*`
- `.site-profile-*`, `.sp-table`, `.sp-field-*`
- `.bio-site-btn`, `.bio-table`, `.delta-bad/warn/good`
- `.signal-filter-row`, `.signals-table`, `.signal-delta-*`, `.triggered-yes/no`
- `.dq-table`, `.dq-bar-track`, `.dq-bar-fill`, `.dq-completeness-inline`
- `.scenario-*`, `.btn-run-scenario`, `.btn-reset-scenario`
- `.strategy-comparison-grid`, `.strategy-card`
