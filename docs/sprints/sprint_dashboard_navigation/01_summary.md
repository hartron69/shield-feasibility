# Sprint Summary — Dashboard-First Navigation

## Objective

Replace the 8-item flat top navigation bar with a 2-level navigation structure and a new
dashboard landing page, making it easier for users to orient between the two major workflows
(C5AI+ Risk Intelligence and PCC Captive Feasibility).

## Deliverables

| Item | Status |
|---|---|
| `DashboardPage.jsx` — hero, KPI row, workflow cards, quick-links | Done |
| `App.jsx` — 2-level nav state, `navigateTo()`, legacy compat | Done |
| `ResultPanel.jsx` — `initialTab` prop for deep-linking | Done |
| `App.css` — `.app-shell`, `.sub-nav`, dashboard styles | Done |

## Navigation Structure

**Level 1 (main-nav — navy bar):** Dashboard | Risk Intelligence | PCC Feasibility

**Level 2 (sub-nav — light grey bar):**

| Section | Sub-tabs |
|---|---|
| Risk Intelligence | Oversikt · Målinger · Risiko · Varsler · Læring |
| PCC Feasibility   | Oversikt · Tapsanalyse · Tiltak · Strategi · Rapporter |

Dashboard has no sub-nav.

## Component Mapping

| Old page ID | New section | New sub-tab | Component |
|---|---|---|---|
| `overview`    | `risk`        | `oversikt`    | `OverviewPage` |
| `inputs`      | `risk`        | `maaling`     | `InputsPage` |
| `c5ai`        | `risk`        | `risiko`      | `C5AIModule` |
| `alerts`      | `risk`        | `varsler`     | `AlertsPage` |
| `learning`    | `risk`        | `laering`     | `LearningPage` |
| `feasibility` | `feasibility` | `oversikt`    | `ResultPanel` (initialTab=Summary) |
| —             | `feasibility` | `tapsanalyse` | `ResultPanel` (initialTab=Tapsanalyse) |
| —             | `feasibility` | `tiltak`      | `ResultPanel` (initialTab=Mitigation) |
| `strategy`    | `feasibility` | `strategi`    | `StrategyComparisonPage` |
| `reports`     | `feasibility` | `rapporter`   | `ReportsPage` |

## Test Results

Backend: 1 465 passed, 0 failed (unchanged — backend-only sprint)
Frontend build: 0 errors, 96 modules

## Default Landing

Default entry point changed from `overview` page to `dashboard` section.
