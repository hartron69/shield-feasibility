# C5AI+ Risk Intelligence – GUI Integration

**Date:** 2026-03-10
**Build status:** ✓ 0 errors, 0 warnings

---

## 1. Updated GUI Architecture

```
frontend/src/
  App.jsx                              MODIFIED — page nav + C5AI+ routing
  App.css                              MODIFIED — nav + C5AI+ component styles
  data/
    c5ai_mock.js                       NEW — comprehensive mock data (6 sections)
  components/
    c5ai/                              NEW PACKAGE
      C5AIModule.jsx                   Container with 4 tabs + module header
      RiskOverviewTab.jsx              A. Risk Overview
      BiologicalForecastTab.jsx        B. Biological Forecast
      RiskDriversTab.jsx               C. Risk Drivers + Explainability
      LearningStatusTab.jsx            D. Learning Status + Brier history
    results/
      ResultPanel.jsx                  (unchanged — C5AI enrichment shows in SummaryTab)
      SummaryTab.jsx                   MODIFIED — C5AI enrichment bar
```

**New files:** 6
**Modified files:** 3
**New CSS rules:** ~200 lines

---

## 2. Navigation

A two-button page navigator appears in the top-right of the header:

```
[ Shield Risk Platform ]        [ Feasibility ]  [ C5AI+ Risk Intelligence ]
```

- **Feasibility** (default): existing left panel + ResultPanel unchanged
- **C5AI+ Risk Intelligence**: right panel replaced by C5AIModule; left panel remains for context

The navigator is styled with pill buttons. The active page uses the page's accent colour:
- Feasibility → teal (`#1B8A7A`)
- C5AI+ Risk Intelligence → violet (`#7C3AED`)

---

## 3. C5AI+ Module — Four Tabs

### A. Risk Overview
- Overall portfolio risk score (0–100) in a colour-coded ring (green/amber/red)
- Domain breakdown: 4-domain horizontal bar chart with NOK/yr figures
- Site risk ranking table: exposure, biomass, risk score bar, dominant risks
- PCC Integration panel: scale factor, biological loss fraction, bio criterion score + finding

### B. Biological Forecast
- Site filter: All Sites | per-site toggle buttons
- 4 risk-type cards (HAB/Lice/Jellyfish/Pathogen):
  - Probability bar (green < 15%, amber 15–30%, red > 30%)
  - Trend badge (↑ increasing / → stable / ↓ decreasing)
  - E[Loss]/yr and P90 loss in NOK
  - Model badge (ML model / prior / prior fallback)
  - Confidence score
- Per-site breakdown table: probability + E[loss] for all 4 risk types
- Bayesian enrichment note explaining adjusted vs. baseline probability

### C. Risk Drivers
- Interactive driver list: ranked by feature importance, colour-coded by direction
  (red = risk amplifier, green = risk reducer)
- Click any driver to show explainability panel
- Explainability panel: driver name, domain badges, importance %, full description
- Driver summary statistics
- Mitigation pointer: links back to Mitigation accordion on Feasibility page

### D. Learning Status
- Status pill: COLD / WARMING / ACTIVE with dot-meter progress (cycles to active)
- Training source: simulated vs. operator reported
- Last retrained date, cycles completed
- Model versions per risk type
- Brier score history table across all cycles (colour-coded: green < 0.10, amber 0.10–0.20, red > 0.20)
- Current evaluation metrics: Brier, log-loss, bias, severity MAE, calibration slope (with ✓/≈/⚠ indicator)

---

## 4. Cross-Module Connections

| Connection | Implementation |
|---|---|
| C5AI enriched? | `C5AIEnrichmentBar` in `SummaryTab.jsx` — shows when `baseline.c5ai_scale_factor` is present |
| Scale factor visible | Risk Overview tab → PCC Integration panel |
| Mitigation link | Risk Drivers tab → "Mitigation connection" warning note |
| Bio criterion score | Risk Overview tab → PCC Integration panel |
| Navigate back | Risk Overview tab → "Switch to Feasibility page" text |

---

## 5. Mock Data — `c5ai_mock.js`

Calibrated to Nordic Aqua Partners AS (9 200 t, 3 sites, Norway).
Contains:

| Section | Key values |
|---|---|
| `metadata` | operator_id, learning_status, model_versions, cycles_completed |
| `overall_risk_score` | 62/100 (MEDIUM-HIGH) |
| `sites` | 3 sites: Frohavet North (72), Sunndalsfjord (58), Storfjorden South (41) |
| `domain_breakdown` | bio 52%, struct 22%, env 17%, ops 9% |
| `biological_forecast` | per-site per-risk-type: probability, loss mean/p50/p90, confidence, trend, model |
| `risk_drivers` | 7 ranked drivers with importance, direction, description |
| `learning.brier_history` | 5 cycles (2020–2024) per sprint 9 demo run |
| `learning.evaluation_metrics` | Brier, log-loss, bias, MAE, calibration slope per risk type |
| `pcc_integration` | scale_factor=1.18, biological_fraction=0.52, bio criterion 68/100 |

---

## 6. Backend Integration (when ready)

Replace mock data by adding a `fetchC5AIForecast()` call to `api/client.js`:

```javascript
// api/client.js
export async function fetchC5AIForecast(operatorId) {
  const res = await fetch(`/api/c5ai/forecast/${operatorId}`)
  if (!res.ok) throw new Error(`C5AI fetch failed: ${res.status}`)
  return res.json()
}
```

Then in `App.jsx`, add a `useEffect` that calls `fetchC5AIForecast` after running
feasibility (or on page load), and passes the result to `C5AIModule` instead of
`C5AI_MOCK`.

The backend would call `LearningLoop.run_cycle()` and return the enriched
`RiskForecast` plus `LearningCycleResult` converted to the mock data schema.

---

## 7. How to Run

```bash
# Frontend dev server
cd frontend && npm install && npm run dev
# → http://localhost:5173

# Backend (required for Feasibility page)
uvicorn backend.main:app --reload --port 8000

# C5AI+ module works immediately with mock data — no backend needed
```
