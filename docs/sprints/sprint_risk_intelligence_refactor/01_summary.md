# Sprint: Risk Intelligence Refactor — Strategic Portfolio & Captive Dashboard

## Objective

Separate Risk Intelligence (strategic, forward-looking, portfolio-level) from Live Risk
(operational, real-time, locality-level). Remove all content from Risk Intelligence that
duplicates what Live Risk already provides more accurately.

## Deliverables

### Removed from Risk Intelligence

| Content | Why removed |
|---|---|
| Alerts tab | Operational — Live Risk alert layer is the source of truth |
| BarentsWatch tab | Operational sync detail — belongs with the data source, not the model layer |
| Anlegg / SmoltSiteRiskTab | Operational site view — superseded by Live Risk per-locality pages |
| AlertSummaryCards in RiskOverviewTab | Short-term event view — not strategic |

### Added / rebuilt

| Content | File | Description |
|---|---|---|
| Concentration analysis panel | `RiskOverviewTab.jsx` | Biomass distribution bar + HHI badge (Low/Moderate/High) + top-site exposure summary |
| Live Risk link-out per site | `RiskOverviewTab.jsx` | "Live Risk →" button in site ranking table; navigates to locality detail page |
| Norwegian tab labels | `C5AIModule.jsx` | All tabs relabelled in Bokmål to match rest of UI |
| Improved domain labels | `RiskOverviewTab.jsx` | Domain names in Norwegian throughout; colored badges use domain colors |
| Improved captive bridge | `RiskOverviewTab.jsx` | Labels in Norwegian; clearer call-to-action when feasibility not yet run |

### Navigation wiring

`App.jsx` passes `onNavigateToLiveRisk` callback to `C5AIModule` → `RiskOverviewTab`.
Clicking "Live Risk →" for a site sets `liveRiskLocalityId` and switches to the
`live_risk` section, opening the locality detail page directly.

## Architectural separation (documented)

```
Risk Intelligence (C5AI+ tab)          Live Risk (Live Risk tab)
─────────────────────────────          ──────────────────────────
Strategic / 1–3 year horizon           Operational / real-time
Portfolio aggregations                 Per-locality detail
Bayesian learning model status         Raw sensor measurements
Domain loss forecasts (C5AI+)          Source status & BW sync
PCC feasibility integration            Alerts & events
Concentration analysis                 Risk history & timeseries
  └─ link-outs → Live Risk             Economics tab
```

The site IDs used in C5AI mock data (`KH_S01`, `KH_S02`, `KH_S03`) map directly to
Live Risk locality IDs, enabling seamless link-out navigation.

## Test results

- Backend: unchanged — all existing tests pass
- Frontend: 109 modules, 0 errors, 0 warnings (build clean)

## Build status

```
✓ built in 1.17s  (109 modules, 0 errors)
```

## Files changed

| File | Change |
|---|---|
| `frontend/src/components/c5ai/C5AIModule.jsx` | Remove 3 tabs + BW/alert imports; add `onNavigateToLiveRisk` prop; Norwegian labels |
| `frontend/src/components/c5ai/RiskOverviewTab.jsx` | Remove AlertSummaryCards; add concentration panel + HHI; add Live Risk link-out buttons; Norwegian throughout |
| `frontend/src/App.jsx` | Pass `onNavigateToLiveRisk` callback to C5AIModule |
