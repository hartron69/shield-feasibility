# Sprint: Site Risk GUI — Smolt / RAS Site-Level Risk Visibility

**Date:** 2026-03-22
**Status:** Complete
**Tests:** 1 413 passed, 0 failed (unchanged — frontend-only sprint)
**Build:** ✓ 95 modules, 0 errors (was 88)

---

## Objective

Make individual smolt/RAS facility risk visible in the existing browser-based GUI.
Previously the platform showed only operator-level totals for settefisk operators.
This sprint adds site-level EAL, SCR contribution, risk ranking, domain breakdown,
top drivers, and data confidence — across two locations in the GUI.

---

## Deliverables

### New files

| File | Purpose |
|---|---|
| `frontend/src/data/mockSmoltSiteRiskData.js` | Mock data — 5 smolt facilities with full risk profile |
| `frontend/src/components/smolt/SiteRiskSummaryCards.jsx` | 3 clickable cards for top-3 sites |
| `frontend/src/components/smolt/TopRiskSitesTable.jsx` | Full ranked table with score bars |
| `frontend/src/components/smolt/SiteEALChart.jsx` | SVG horizontal bar chart — EAL per site |
| `frontend/src/components/smolt/SiteSCRContributionChart.jsx` | SVG horizontal bar chart — SCR per site |
| `frontend/src/components/smolt/SiteRiskDetailPanel.jsx` | Detail panel (domain breakdown, drivers, confidence) |
| `frontend/src/components/smolt/SmoltSiteRiskTab.jsx` | Full "Anlegg" tab with table/charts view toggle |

### Modified files

| File | Change |
|---|---|
| `frontend/src/components/OverviewPage.jsx` | Added "Topp risikoanlegg — Settefisk" section (Top 3 cards + detail panel) |
| `frontend/src/components/c5ai/C5AIModule.jsx` | Added 8th tab "Anlegg" → `SmoltSiteRiskTab` |
| `frontend/src/App.css` | +~160 lines — site card, detail panel, driver rows, chart label, table row styles |

---

## Demo Site Data

5 mock smolt facilities (all in Western Norway):

| # | Name | Type | Score | EAL | SCR contrib. | Alerts |
|---|---|---|---|---|---|---|
| 1 | Agaqua Jelsa | RAS | 74 | NOK 8.42M | NOK 21.8M | 3 CRITICAL |
| 2 | Agaqua Tau | RAS | 61 | NOK 5.18M | NOK 13.9M | 1 WARNING |
| 3 | Nordic Smolt Fjord | RAS | 48 | NOK 3.64M | NOK 9.1M | 1 WARNING |
| 4 | SalmoSet Ryfylke | flow-through | 35 | NOK 1.92M | NOK 5.2M | 0 WATCH |
| 5 | AquaGen Sunnfjord | RAS | 28 | NOK 1.24M | NOK 3.84M | 0 NORMAL |

Portfolio totals: EAL NOK 20.4M · SCR NOK 53.8M

---

## GUI Features Added

### 1. Overview Page — "Topp risikoanlegg" section

- Positioned between Active Alerts and Domain Loss Breakdown
- Shows top 3 smolt sites as clickable cards
- Each card: rank badge, alert level badge, site name + municipality + type,
  risk score ring, dominant domain (color-coded), EAL, SCR contribution,
  alert count, data confidence
- Click any card → inline `SiteRiskDetailPanel` expands below
- "Se alle anlegg →" button navigates to C5AI+ / Anlegg tab

### 2. SiteRiskDetailPanel

- Domain breakdown horizontal bars (dominant domain highlighted + ▲ marker)
- Top drivers list with HIGH/MEDIUM/LOW severity badges
- 4 KPI cells: risk score, EAL, SCR contribution, open alerts
- Data confidence bar (green ≥ 80%, amber ≥ 60%, red < 60%)
- Close button (✕)

### 3. C5AI+ "Anlegg" tab (SmoltSiteRiskTab)

- Portfolio summary: 4 KPI cards (total EAL, total SCR, critical sites, open alerts)
- Top 3 summary cards (SiteRiskSummaryCards)
- Toggle: Tabell / Grafer view
  - Table view: full ranked table with score bars, type badge, EAL, SCR, alerts
  - Charts view: 2-column SVG charts (EAL per site + SCR per site, sorted desc)
- Click any card or table row → inline SiteRiskDetailPanel
- Smolt domain legend (5 RAS-specific domains with colors)

### 4. Charts (pure SVG)

Both charts are horizontal bar charts, sorted highest to lowest:

**SiteEALChart** — bar color = dominant domain color, value in NOK M
**SiteSCRContributionChart** — navy gradient shading (darkest = highest SCR contributor),
value in NOK M with share percentage

---

## Design Consistency

- Cards follow existing `.card` pattern
- Badge styling matches existing alert level badge pattern
- Risk score rings reuse `.risk-score-ring.high/medium/low`
- Domain colors: RAS-specific palette in `SMOLT_DOMAIN_META`
  (ras_failure=#0D9488, oxygen=#0284C7, power=#CA8A04, bio=#059669, ops=#7C3AED)
- KPI cards reuse `.kpi-grid` / `.kpi-card` / `.kpi-label` / `.kpi-value`
- Tables reuse `.data-table`
- All charts are pure SVG — no external chart libraries

---

## Backward Compatibility

- No changes to existing Python backend or test suite
- Sea-site operators: unaffected (smolt data only shown with mock data)
- All existing tabs in C5AIModule remain at same indices (new "Anlegg" appended)
- CSS additions are append-only (no existing rules modified)
- OverviewPage remains fully functional for sea-site operators

---

## Architecture Notes

The smolt site risk data is currently mock-only. Backend wiring path when ready:

1. Add `GET /api/feasibility/smolt/sites/risk` endpoint returning list of `SmoltSiteRiskItem`
2. Pass data as prop through `App.jsx → C5AIModule → SmoltSiteRiskTab`
3. Replace `SMOLT_SITE_RISK` import with prop in `SmoltSiteRiskTab` and child components
4. Same prop path for `OverviewPage` (already receives `onNavigate`)

---

## Test Results

```
1413 passed, 0 failed, 45 warnings  (unchanged — no Python changes)
npm run build: 95 modules, 0 errors
```
