# Architecture — Dashboard-First Navigation

## State Model

```
App.jsx
  activeMainSection: 'dashboard' | 'risk' | 'feasibility'  (default: 'dashboard')
  activeRiskTab:       'oversikt' | 'maaling' | 'risiko' | 'varsler' | 'laering'
  activeFeasibilityTab: 'oversikt' | 'tapsanalyse' | 'tiltak' | 'strategi' | 'rapporter'
```

The old `activePage: string` state is replaced by three orthogonal states.

## Navigation Function

```js
function navigateTo(sectionOrLegacy, tab) {
  // Accepts new-style ('risk', 'varsler') or legacy string ('alerts')
  if (tab === undefined && LEGACY_PAGE_MAP[sectionOrLegacy]) { ... }
  setActiveMainSection(sectionOrLegacy)
  if (sectionOrLegacy === 'risk') setActiveRiskTab(tab || 'oversikt')
  else if (sectionOrLegacy === 'feasibility') setActiveFeasibilityTab(tab || 'oversikt')
}
```

`LEGACY_PAGE_MAP` maps old page IDs used by `OverviewPage.onNavigate` to new
`(section, tab)` pairs — no changes needed to `OverviewPage.jsx`.

## ResultPanel Deep-Linking

`ResultPanel` accepts a new `initialTab` prop. A `useEffect` keeps the internal
`activeTab` state synchronised when the parent navigates to a different feasibility sub-tab.

```
activeFeasibilityTab  →  ResultPanel initialTab
─────────────────────────────────────────────────
oversikt              →  'Summary'
tapsanalyse           →  'Tapsanalyse'
tiltak                →  'Mitigation'
```

`strategi` and `rapporter` bypass `ResultPanel` entirely and render
`StrategyComparisonPage` / `ReportsPage` directly.

## Layout

```
<div class="app-shell">          flex-direction: column; height: 100vh
  <header class="app-header">   fixed height (~50px)
  <nav class="main-nav">        Level 1 — navy; 3 items
  <nav class="sub-nav">         Level 2 — light grey; conditional
  <div class="app-body">        flex: 1; min-height: 0   ← key: no more calc()
    <div class="left-panel">    shown only when activeMainSection === 'feasibility'
    <div class="right-panel">   flex: 1; overflow-y: auto
```

`app-shell` flex layout eliminates the previous `height: calc(100vh - 56px)` hack that
under-accounted for nav bar heights.

## DashboardPage

```
DashboardPage({ onNavigate })
  ├─ Hero banner (navy gradient)
  ├─ KPI row (4 cards): Risikoindeks, Kritiske varsler, Forventet tap/år, Analyselokaliteter
  ├─ Workflow cards (2): Risk Intelligence, PCC Feasibility (click → navigateTo)
  └─ Quick-links bar: 7 pill buttons → deep-links into sub-sections
```

Data: reads `C5AI_MOCK` and `MOCK_ALERTS` (same sources as `OverviewPage`).
