# Sprint: Risk Intelligence Copy & Label Cleanup (2026-03-27)

## Objective

Apply a comprehensive Norwegian-language copy pass across all six C5AI+ Risk Intelligence
module files. Replace English labels and add strategic framing copy so the module reads
as a professional strategic portfolio tool rather than a technical interface.

## Deliverables

### Strategic banner and footer (RiskOverviewTab.jsx)

- **Top banner** (blue callout): "Strategisk analyse av selskapets samlede risikobilde..."
  with italic disclaimer pointing users to Live Risk for operational detail.
- **Footer disclaimer**: italic grey text at bottom of each visit: "Dette er en strategisk,
  modellert visning basert på analysegrunnlaget. For operativ sannhet, bruk Live Risk."

### Label replacements (all six C5AI module files)

| Old (English) | New (Norwegian) | File |
|---|---|---|
| Portfolio Risk | Selskapets risikobilde | RiskOverviewTab |
| Risk Score | Strategisk risikonivå | RiskOverviewTab |
| Site Risk Ranking | Viktigste lokaliteter | RiskOverviewTab |
| Dominant Risks | Viktigste risikotyper | RiskOverviewTab |
| Domain | Risikotype | RiskOverviewTab |
| Learning | Strategiske mønstre | LearningStatusTab |
| Learning Loop Status | Strategiske mønstre — læringsmodell | LearningStatusTab |
| Training Source | Treningskilde | LearningStatusTab |
| Last Retrained | Sist oppdatert | LearningStatusTab |
| Brier Score History | Historisk modellnøyaktighet | LearningStatusTab |
| ↓ Better / ↑ Worse | ↓ Bedre / ↑ Svakere | LearningStatusTab |
| Annual Event Probability | Årlig hendelsessannsynlighet | BiologicalForecastTab |
| All Sites | Alle anlegg | BiologicalForecastTab |
| Per-Site Breakdown | Fordeling per anlegg | BiologicalForecastTab |
| E[Loss]/yr | Forv. tap/år | BiologicalForecastTab |
| P90 Loss | P90-tap | all forecast tabs |
| Confidence | Modellsikkerhet | all forecast tabs |
| Key Drivers | Viktigste drivere | all forecast tabs |
| Structural Risk Forecast | Strukturell risikoprognose | StructuralForecastTab |
| Environmental Risk Forecast | Miljørisikoprognose | EnvironmentalForecastTab |
| Operational Risk Forecast | Operasjonell risikoprognose | OperationalForecastTab |

### Risk type labels translated (all domains)

All 20 risk type identifiers now have Norwegian display names in their respective tab
files: e.g. `mooring_failure → Fortøyningssvikt`, `oxygen_stress → Oksygenstress`,
`human_error → Menneskelig feil`, `hab → Skadelig algeblomst (HAB)`, etc.

### C5AI module header (C5AIModule.jsx)

- Title: "C5AI+ Strategisk risikoanalyse"
- Stat labels: "anlegg", "Horisont X år", "Modell X", "Læringssykluser fullført"

### Captive bridge strengthening (RiskOverviewTab.jsx)

Section header updated to "Konsekvens for captive og feasibility". Italic helper text
beneath every section explains what the panel shows and its strategic purpose.
When no feasibility result is available, text prompts user to run the analysis to see
how C5AI+ scale factor affects expected loss and SCR.

## Test results

- Backend: 1858 passed, 0 failed (unmodified)
- Frontend: 109 modules, 0 errors

## Build status

```
✓ built in 1.15s  (109 modules, 0 errors)
```

## Files changed

| File | Change |
|---|---|
| `frontend/src/components/c5ai/RiskOverviewTab.jsx` | Strategic banner, footer, all Norwegian labels, domain RISK_TYPE_LABELS |
| `frontend/src/components/c5ai/C5AIModule.jsx` | Header copy, tab labels all Norwegian |
| `frontend/src/components/c5ai/LearningStatusTab.jsx` | All English labels → Norwegian; risk type display names |
| `frontend/src/components/c5ai/BiologicalForecastTab.jsx` | All English labels → Norwegian; TREND_LABELS dict |
| `frontend/src/components/c5ai/StructuralForecastTab.jsx` | All risk labels and field labels → Norwegian |
| `frontend/src/components/c5ai/EnvironmentalForecastTab.jsx` | All risk labels and field labels → Norwegian |
| `frontend/src/components/c5ai/OperationalForecastTab.jsx` | All risk labels and field labels → Norwegian |
