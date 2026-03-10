# Sprint – Inputs GUI: Summary

**Date:** 2026-03-10
**Status:** Complete

## Objective
Add an Inputs page to the existing Shield Risk Platform GUI so operators and analysts can inspect and work with the data used by C5AI+ for risk analysis, alert generation, and scenario testing.

Simultaneously, expand the top navigation from 3 items to 9 items, giving each functional area a dedicated page.

## Delivered

### Navigation (9 items)
Overview · Inputs · C5AI+ Risk Intelligence · Alerts · PCC Feasibility · Strategy Comparison · Learning · Reports

### Inputs Page (5 tabs)
1. **Site Profile** – static site facts, financial values, exposure/operational factors
2. **Biological Inputs** – per-site environmental readings vs. baseline, colour-coded delta
3. **Alert Signals** – precursor signals table with trigger status, filterable by site/risk type
4. **Data Quality** – completeness bars, confidence dots, quality flags, missing field inventory
5. **Scenario Inputs** – editable overrides (number + slider), preset buttons, stub "Run Scenario" result

### New Pages
- **Overview** – portfolio KPI cards + alert summary + domain loss bars + input completeness
- **Strategy Comparison** – 3-strategy side-by-side (PCC Captive / FI / Pooling)
- **Learning** – wraps existing LearningStatusTab + data context banner
- **Reports** – available and planned report types

### Reusable Components
`InputSourceBadge` · `InputCompletenessCard` · `SiteProfileForm` · `BiologicalInputsPanel` · `AlertSignalsPanel` · `DataQualityPanel` · `ScenarioOverridePanel`

### Mock Data
`frontend/src/data/mockInputsData.js` – site profiles, biological readings, alert signals, data quality, scenario baselines for 3 sites (consistent with C5AI_MOCK and MOCK_ALERTS).

## Test Results
- Python backend: **1092 passed, 0 failed** (unchanged)
- Frontend build: **0 errors, 0 warnings** (74 modules, 278 kB JS)
- Frontend tests: see `04_tests.md`
