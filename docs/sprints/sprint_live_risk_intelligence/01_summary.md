# Sprint: Live Risk Intelligence

**Date:** 2026-03-27
**Status:** Complete

---

## Objective

Build a dedicated Live Risk Intelligence module giving full transparency into which localities receive
BarentsWatch data updates, what raw measurements are received, how risk parameters change over time,
and how confident the system is in each estimate.

---

## Deliverables

### Backend (7 new files)

| File | Purpose |
|---|---|
| `backend/services/live_risk_mock.py` | Deterministic seeded synthetic data generator (3 localities, 90 days) |
| `backend/services/source_health.py` | Per-source health status and sync metadata |
| `backend/services/confidence_scoring.py` | 4-component confidence scoring (freshness, coverage, gaps, stability) |
| `backend/services/event_timeline.py` | Threshold-based event detection and timeline assembly |
| `backend/services/risk_change_explainer.py` | Factor attribution for risk changes over a period |
| `backend/services/live_risk_feed.py` | Feed overview, locality detail, timeseries, risk history, cage impact |
| `backend/api/live_risk.py` | 9 FastAPI endpoints at `/api/live-risk/` |

`backend/main.py` modified to register `live_risk_router`.

### API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/live-risk/feed` | All-locality feed overview with risk scores, confidence, freshness |
| `GET /api/live-risk/localities/{id}` | Single-locality metadata + current risk snapshot |
| `GET /api/live-risk/localities/{id}/timeseries?period=` | Raw measurement time series (lice, temp, oxygen, salinity, treatment) |
| `GET /api/live-risk/localities/{id}/risk-history?period=` | Per-domain risk score history |
| `GET /api/live-risk/localities/{id}/sources` | Per-source health status |
| `GET /api/live-risk/localities/{id}/change-breakdown?period=` | Risk change attribution by factor |
| `GET /api/live-risk/localities/{id}/events?period=` | Risk events timeline (threshold crossings, disease, spikes) |
| `GET /api/live-risk/localities/{id}/confidence` | Confidence score with component breakdown |
| `GET /api/live-risk/localities/{id}/cage-impact` | Indicative cage-type exposure impact |

Valid periods: `7d`, `30d`, `90d`, `12m`.

### Frontend (8 new components + 1 modified)

| File | Purpose |
|---|---|
| `frontend/src/components/live_risk/ConfidenceBadge.jsx` | Reusable confidence level badge (Norwegian labels) |
| `frontend/src/components/live_risk/RawDataChart.jsx` | Pure SVG line chart with quality-coded segments, gaps, thresholds |
| `frontend/src/components/live_risk/RiskHistoryChart.jsx` | Pure SVG multi-domain risk history chart |
| `frontend/src/components/live_risk/SourceStatusPanel.jsx` | Source health table with error details |
| `frontend/src/components/live_risk/RiskChangeBreakdownPanel.jsx` | Factor attribution panel with domain delta cards |
| `frontend/src/components/live_risk/RiskEventsTimeline.jsx` | Vertical event timeline with severity chips |
| `frontend/src/components/live_risk/LiveRiskFeedPage.jsx` | Feed overview with filtering, sorting, and table |
| `frontend/src/components/live_risk/LocalityLiveRiskPage.jsx` | Locality detail with period selector and 6 sub-tabs |
| `frontend/src/api/client.js` | 9 new fetch functions appended |

`frontend/src/App.jsx` modified: imports, `L1_NAV` (`live_risk` added as 4th item), `liveRiskLocalityId` state, render block for live risk section.
`frontend/src/App.css` extended with `lr-*` CSS classes.

---

## Mock Data Sites

Uses the consistent Kornstad Havbruk AS localities:

| ID | Name | Characteristic |
|---|---|---|
| `KH_S01` | Kornstad | Moderate lice, disease event ~30 days ago, fresh sync |
| `KH_S02` | Leite | Higher variation, BW environmental source delayed (stale sync) |
| `KH_S03` | Hogsnes | Cleanest — sheltered, lowest risk, all sources fresh |

---

## Test Results

```
tests/test_live_risk.py: 80 passed in 1.92s
Full suite: 1810 passed (was 1734), 4 pre-existing errors in test_smolt_tiv_model.py
Frontend build: 113 modules transformed, 0 errors
```

---

## Architecture Notes

- **No new npm dependencies** — pure SVG charts, all fetch via existing `client.js`.
- **Deterministic mock data** — NumPy seeded RNG; output is stable across restarts.
- **Clean layering**: `live_risk_mock.py` → service layer → API layer. No service imports another service except through the mock.
- **Confidence scoring**: weighted average of 4 components; HIGH >= 0.75, MEDIUM >= 0.50, LOW < 0.50.
- **Event deduplication**: same-day same-type events are deduplicated in `event_timeline.py`.
- **Cage impact**: labeled indicative — uses `CAGE_DOMAIN_MULTIPLIERS` from `models/cage_technology.py`. Not stochastic per-cage attribution.

---

## Limitations

- Data is synthetic (deterministic mock); no real BarentsWatch API integration yet.
- Timeseries is fixed at 90 days of history; `12m` period clips to available 90-day window.
- No live polling / WebSocket updates — page refresh fetches current mock state.
- Cage impact tab only appears when cage portfolio data is returned (future: when real cage data exists per locality).
