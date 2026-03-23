# Code Changes — Dashboard-First Navigation

## New Files

| File | Purpose |
|---|---|
| `frontend/src/components/DashboardPage.jsx` | Landing page with hero, KPI row, workflow cards, quick-links |
| `docs/sprints/sprint_dashboard_navigation/` | Sprint artifacts |

## Modified Files

### `frontend/src/App.jsx`

- Added import: `DashboardPage`
- Replaced `activePage` state with `activeMainSection`, `activeRiskTab`, `activeFeasibilityTab`
- Removed `NAV_ITEMS` array (8 items) and `FEASIBILITY_PAGES` set
- Added `L1_NAV` (3 items), `L2_RISK_NAV` (5 items), `L2_FEASIBILITY_NAV` (5 items)
- Added `FEASIBILITY_TO_RESULT_TAB` map for deep-linking
- Added `LEGACY_PAGE_MAP` for backward-compatible `onNavigate` calls from `OverviewPage`
- Added `navigateTo(sectionOrLegacy, tab)` function
- Updated `handleExample()`: `setActivePage('feasibility')` → `navigateTo('feasibility', 'oversikt')`
- Updated `handleAgaquaExample()`: same
- Updated `showLeftPanel` condition: `activeMainSection === 'feasibility'`
- Rendered Level-1 `<nav class="main-nav">` with 3 items
- Rendered Level-2 `<nav class="sub-nav">` conditional on `activeMainSection`
- Wrapped root element in `<div class="app-shell">`
- Replaced 8 `activePage === ...` conditionals with section/tab conditionals
- PCC Feasibility: ResultPanel shown for `oversikt`/`tapsanalyse`/`tiltak`; standalone pages for `strategi`/`rapporter`
- ResultPanel now receives `initialTab={FEASIBILITY_TO_RESULT_TAB[activeFeasibilityTab]}`

### `frontend/src/components/results/ResultPanel.jsx`

- Added `useEffect` to import
- Added `initialTab` prop
- `useState` initial value: `initialTab || 'Summary'`
- Added `useEffect(() => { if (initialTab) setActiveTab(initialTab) }, [initialTab])`

### `frontend/src/App.css`

- Modified `.app-body`: removed `height: calc(100vh - 56px)`; added `flex: 1; min-height: 0`
- Added `.app-shell`: `display: flex; flex-direction: column; height: 100vh; overflow: hidden`
- Replaced "9-item secondary nav bar" comment with "Level-1 main navigation"
- Added `.sub-nav` and `.sub-nav-btn` styles (light grey bg, teal active underline)
- Added dashboard styles: `.dashboard-page`, `.dashboard-hero`, `.dashboard-kpi-row`,
  `.dashboard-kpi-card`, `.dashboard-workflow-row`, `.dashboard-workflow-card`,
  `.dashboard-workflow-icon`, `.dashboard-quicklinks`, `.dashboard-quicklink-btn`
