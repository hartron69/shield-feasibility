# Sprint: Live Feed → C5AI Risk Score Wiring (2026-03-27)

## Objective

Connect the Live Risk feed to the C5AI+ Risk Intelligence module so that clicking
"Oppdater feed" in Live Risk propagates updated risk scores into the C5AI overview
(overall score, per-site scores, domain breakdown) in real time.

## Problem

Before this sprint the C5AI module used `C5AI_MOCK` — a static hardcoded JS import.
`overall_risk_score: 62` and the three site scores (62 / 58 / 41) never changed
regardless of feed state. The "Oppdater feed" button only refreshed the Live Risk
table; Risk Intelligence was completely siloed.

This matters operationally: if a HAB spike raises Leite's feed risk score from 38
to 53, the C5AI portfolio dashboard should reflect this change within the same session.
The 24–36 hour early warning window for mortality mitigation requires that all
risk-facing modules show consistent, current data.

## Architecture after sprint

```
Oppdater feed (click)
     │
     ▼
GET /api/live-risk/feed            ← refreshes feed table UI
     │
     │  onFeedRefreshed callback
     ▼
GET /api/c5ai/risk-overview        ← new endpoint
     │
     │  setC5aiRiskData(override)
     ▼
C5AIModule receives:
  { ...C5AI_MOCK,                   ← forecast data (biological/structural/etc.) static
    overall_risk_score: <live>,      ← from feed, recalculated on each call
    sites: <live per-site scores>,   ← from feed
    domain_breakdown: <live fracs>   ← from feed
  }
```

Forecast data (biological_forecast, structural_forecast, etc.) remains mock — those
are model pipeline outputs that require a `POST /api/c5ai/run` to update.
Only the portfolio-level risk picture (scores and domain fractions) is now live.

## Backend changes

### New function: `get_c5ai_risk_overview()` (live_risk_feed.py)

Reads the current (last-day) risk score snapshot for each Kornstad Havbruk locality
(KH_S01, KH_S02, KH_S03) from `live_risk_mock.py` and maps to C5AI format:

- **`overall_risk_score`**: biomass-weighted average of site total scores
- **`sites[]`**: per-site `risk_score`, `dominant_risks` (top 2 domains), and
  portfolio metadata (biomass, exposure) from `_C5AI_SITE_META`
- **`domain_breakdown`**: normalize biomass-weighted domain scores to fractions;
  scale to estimated annual loss (NOK 22.6M baseline)

Domain weights are consistent with `_compute_risk()` in `live_risk_mock.py`:
35% biological · 25% structural · 25% environmental · 15% operational.

### New endpoint: `GET /api/c5ai/risk-overview` (c5ai.py)

```
GET /api/c5ai/risk-overview
→ { overall_risk_score, sites, domain_breakdown, generated_at }
```

Re-computed on every call. No caching — the underlying mock data is deterministic
(seeded) so the result is stable within a session and changes when NOW advances.

## Frontend changes

### `api/client.js`

Added `fetchC5AIRiskOverview()` → `GET /api/c5ai/risk-overview`.

### `App.jsx`

- New state: `c5aiRiskData` (initially `null`)
- `useEffect` on mount: fetches risk overview alongside existing status fetch
- `refreshC5AIRiskOverview()` helper: re-fetches and updates state
- `C5AIModule` receives merged data:
  ```jsx
  c5aiData={c5aiRiskData
    ? { ...C5AI_MOCK, overall_risk_score: c5aiRiskData.overall_risk_score,
        sites: c5aiRiskData.sites, domain_breakdown: c5aiRiskData.domain_breakdown }
    : C5AI_MOCK}
  ```
  Falls back to static mock if backend unreachable.
- `LiveRiskFeedPage` receives `onFeedRefreshed={refreshC5AIRiskOverview}` prop.

### `LiveRiskFeedPage.jsx`

Added `onFeedRefreshed` prop. Called after a successful manual refresh (not on
initial load — avoids double-fetch on mount).

## Test results

- Backend: 1858 passed, 0 failed
- Frontend: 109 modules, 0 errors

## Build status

```
✓ built in 1.15s  (109 modules, 0 errors)
```

## Files changed

| File | Change |
|---|---|
| `backend/services/live_risk_feed.py` | Add `get_c5ai_risk_overview()`, `_C5AI_SITE_META`, `_C5AI_OPERATOR_SITES` constants |
| `backend/api/c5ai.py` | Add `GET /api/c5ai/risk-overview` endpoint |
| `frontend/src/api/client.js` | Add `fetchC5AIRiskOverview()` |
| `frontend/src/App.jsx` | Add `c5aiRiskData` state, fetch on mount, `refreshC5AIRiskOverview()`, merge into C5AIModule, pass `onFeedRefreshed` to LiveRiskFeedPage |
| `frontend/src/components/live_risk/LiveRiskFeedPage.jsx` | Accept and call `onFeedRefreshed` prop after successful manual refresh |
