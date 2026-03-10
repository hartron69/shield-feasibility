# Sprint – Biological Input Line Charts

## Objective
Add interactive time-series line charts to the **Inputs → Biological Inputs** tab, showing
12 months of environmental and biological readings per site with baseline and risk-threshold
reference lines. Zero new npm dependencies; pure SVG via React.

## Deliverables
| File | Change |
|---|---|
| `frontend/src/data/mockBioTimeseries.js` | NEW – 12-month time series (Apr 2025–Mar 2026), 11 params, 3 sites |
| `frontend/src/components/inputs/BioLineChart.jsx` | NEW – pure SVG chart component |
| `frontend/src/components/inputs/BiologicalInputsPanel.jsx` | MODIFIED – charts + table toggle, group filter |
| `frontend/src/App.css` | MODIFIED – ~3.8 kB chart styles appended |

## Key Features
- **Smooth spline**: Catmull-Rom → cubic Bézier for all line paths
- **Baseline**: dashed grey reference line (seasonal average)
- **Risk threshold**: dashed red line + soft red risk-zone fill; badge "Terskel nådd" on breached cards
- **Hover tooltip**: dark overlay with month label + value + unit
- **View toggle**: "Grafer" / "Tabell" buttons in toolbar (original table preserved)
- **Group filter**: All | Temperatur & oksygen | Næringsstoffer & alger | Salinitet | Lus & behandlinger | Biologiske hendelser
- **Alert highlight**: cards with breached last value get red border + `#FFF5F5` background

## Test Results
- Python tests: 1092 passed, 0 failed (unchanged)
- Frontend build: 0 errors, 76 modules, 28.4 kB CSS, 289 kB JS
