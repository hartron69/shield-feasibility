# User Guide: Datagrunnlag tab

## What is the Datagrunnlag tab?

Every time you run a feasibility analysis, the platform records exactly what risk data was
used. The **Datagrunnlag** tab (the last tab in the result panel) shows you this complete
data lineage — from the risk model input all the way to the PCC suitability conclusion.

## What you will see

### Header card
- **Analyse-ID** — a unique identifier for this specific run (useful for support or auditing)
- **Kjørt** — the exact UTC timestamp the analysis was executed
- **Data mode badge** — one of:
  - **Statisk modell** (grey) — no live C5AI+ forecast was loaded; parameters are scaled from template data based on your TIV and exposure
  - **C5AI+ prognose** (green) — a C5AI+ forecast was loaded and used to adjust the Monte Carlo directly via scale_factor and loss_fractions
  - **C5AI+ mitigert** (blue) — as above, with selected mitigations applied to the forecast

### Pipeline diagram
Shows the four computational steps in sequence:
1. Risk model (static or C5AI+ forecast)
2. Monte Carlo simulation (LogNormal severity, vectorised NumPy)
3. Loss analysis (per-site EAL is exact; SCR contribution is proportional approximation)
4. PCC suitability assessment (6-criterion model)

**EKSAKT** means the number is computed precisely from the simulation.
**TILNÆRMET** means the number is a proportional approximation (SCR attribution per site).

### Summary KPIs
Four quick counts: simulated sites, risk domains, risk subtypes, mitigation actions.

### Site table
Lists every site included in the run with:
- Expected Annual Loss (EAL) — exact, TIV-weighted
- SCR contribution — proportional approximation (shown with a warning label)
- Top 2 risk domains for that site

The **Se anlegg i C5AI+ Risiko →** button navigates directly to the C5AI+ Risk module
so you can cross-reference the forecast for those same sites.

### Domains and risk types
All risk domains and subtypes that were modelled. When running in static model mode,
all four domains (biological, structural, environmental, operational) are present using
stub fractions. When C5AI+ is connected live, the biological domain uses forecast-derived
fractions and the scale factor adjusts the overall loss level.

### Metodenotat
A collapsible Norwegian-language description of exactly how the risk parameters were
derived for this run. Expand it to understand the assumptions behind the numbers.

## When does the data mode change from "Statisk" to "C5AI+ prognose"?

When the backend C5AI+ pipeline is connected live and a `pre_loaded_forecast` is passed
to `MonteCarloEngine`, the engine sets `sim.c5ai_enriched = True` and stores the
scale factor. The traceability block will then show the C5AI+ badge automatically.
Currently (sprint traceability), the live connection is not yet wired — all runs show
"Statisk modell". The infrastructure is ready.
