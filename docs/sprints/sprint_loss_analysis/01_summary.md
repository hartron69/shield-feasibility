# Sprint: Tapsanalyse — Real Loss Analysis in PCC Feasibility GUI

## Objective

Replace the empty "Ingen per-lokalitet tapsdata tilgjengelig" placeholder in the Tapsanalyse tab with real, structured loss analysis data showing which sites and domains drive losses and how mitigation changes the picture.

---

## Root Cause of Empty Tapsanalyse

Three issues combined to produce the placeholder:

1. **Missing field in `FeasibilityResponse`**: The schema had no `facility_results` or `loss_analysis` field.
2. **Dead wiring in `ResultPanel.jsx`**: `result.facility_results || []` always evaluated to `[]` because `facility_results` never exists in the response.
3. **Untapped data source**: `SimulationResults.site_loss_distribution` (a `Dict[str, np.ndarray]` of per-site (N, T) loss arrays) was being populated by `MonteCarloEngine._distribute_to_sites_rng()` but never extracted into the API response.

---

## Delivered Features

### 1. KPI Summary Row
- Total portfolio EAL / SCR
- Mitigated EAL (with green delta) when mitigation is active
- Number of sites

### 2. Domain Breakdown Bar
- Stacked colour bar across biological / environmental / structural / operational
- Per-domain EAL with absolute value, percentage, and mitigated delta

### 3. Per-Site Loss Table
- Site name, EAL with mini bar chart (colour-coded by dominant domain)
- EAL share %, SCR contribution, SCR share % with bar
- Dominant domain badge
- Domain mix stacked bar
- Mitigated delta column when mitigation is active
- Expandable rows showing per-domain breakdown + mitigated per-domain delta

### 4. Top Risk Drivers
- Top 10 risk types by EAL (from `DomainLossBreakdown.all_subtypes()`)
- Domain badge, impact NOK, bar showing portfolio share %

### 5. Method Note
- Grey info box explaining whether numbers are exact or approximated

---

## Test Results

```
1465 passed, 47 warnings  (+30 new tests vs 1435 before sprint)
```

New test file: `tests/test_loss_analysis.py` (30 tests, 5 groups)

---

## Build Status

```
npm run build: ✓ 95 modules, 0 errors
```
