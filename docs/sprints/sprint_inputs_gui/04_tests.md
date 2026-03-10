# Sprint – Inputs GUI: Tests

## Python Backend Tests
**1092 passed, 0 failed, 38 warnings** — no regressions from GUI changes.

## Frontend Build Verification
`npm run build` — 0 errors, 0 warnings, 74 modules transformed.

## Manual Verification Checklist

### Navigation
- [ ] 9-item nav bar visible below header
- [ ] Active item highlighted in gold
- [ ] Left panel visible only on PCC Feasibility / Strategy Comparison pages
- [ ] All 8 nav routes render without error

### Overview Page
- [ ] 5 KPI cards visible (Risk Score, Critical Alerts, Completeness, E[Loss], Learning)
- [ ] Domain loss bar chart renders
- [ ] Input completeness cards for 3 sites
- [ ] "View all alerts" link navigates to Alerts page
- [ ] "View full inputs" link navigates to Inputs page

### Inputs Page – Site Profile tab
- [ ] 3 site cards render with all fields
- [ ] Biomass row highlighted in teal
- [ ] Source badge "Simulated" shown

### Inputs Page – Biological Inputs tab
- [ ] Site selector buttons switch site context
- [ ] Delta column colour-coded (red/amber/green)
- [ ] All 11 parameters shown
- [ ] Source badge shown per row

### Inputs Page – Alert Signals tab
- [ ] Site and risk type dropdowns work
- [ ] "Triggered only" checkbox filters rows
- [ ] Triggered rows highlighted amber
- [ ] Signal count shows e.g. "11 / 12 signals"

### Inputs Page – Data Quality tab
- [ ] 3 completeness cards with progress bars
- [ ] Per-risk-type detail table with 12 rows (3 sites × 4 risks)
- [ ] Flag pills colour-coded (SUFFICIENT green, LIMITED amber, POOR red)
- [ ] Missing fields listed

### Inputs Page – Scenario Inputs tab
- [ ] 4 preset buttons apply overrides
- [ ] Number inputs and sliders are linked (change one → other updates)
- [ ] % deviation from baseline shown
- [ ] "Run Scenario" button shows loading state then result KPIs
- [ ] "Reset to Baseline" restores original values

### Strategy Comparison
- [ ] 3 cards visible (PCC Captive, FI, Pooling)
- [ ] Verdict badges colour-coded
- [ ] Pros/cons lists render

### Learning Page
- [ ] Data context banner shows training source
- [ ] LearningStatusTab renders normally (Brier history, evaluation metrics)

### Reports Page
- [ ] 4 report types listed
- [ ] Available vs Planned badges

## Known Test Limitations
No Jest/Vitest unit tests were written for the new components in this sprint.
Prioritised working prototype per sprint spec. Unit tests would cover:
- `computeDelta()` logic in BiologicalInputsPanel
- `deltaClass()` for oxygen direction-inversion
- `ScenarioOverridePanel` preset application
- `DataQualityPanel` sorting by FLAG_ORDER
- `InputCompletenessCard` colour thresholds

These should be added in a follow-up sprint once the mock→API wiring is complete.
