# Limitations — Sprint: Specific Sea Localities

## What This Sprint Does NOT Provide

1. **Per-locality domain modelling** — Selecting a specific locality does NOT change the Monte Carlo domain fractions (bio/struct/env/ops) per site. All four domains remain statically distributed from template fractions. Only biomass allocation and exposure scaling are site-specific.

2. **Locality-specific C5AI+ risk scores** — The selected localities' C5AI+ risk indicators (if available) are not yet wired into per-site risk parameter overrides. C5AI+ scale_factor is still applied at the portfolio level.

3. **Registry limited to Kornstad Havbruk AS** — Only the 3 sites in `OPERATOR_LOCALITIES` (KH_S01/S02/S03) are available for selection. Other operators' localities are not yet in the registry.

4. **Biomass auto-distribution is equal** — "Fordel biomasse jevnt" distributes total equally across selected sites. No proportional-by-exposure-factor distribution is implemented.

5. **traceability.site_selection_mode is "generic" in smolt path** — The smolt feasibility route (`run_feasibility_analysis`) does not pass `site_selection_mode` to `build_traceability_block`. It defaults to "generic".

## Transparency Labels

Where per-site values are auto-derived (biomass_value_nok from value/tonne), they are:
- Labelled "Auto-fordelt" in the allocation table UI
- Recorded as a warning in `AllocationSummary.warnings`
- Marked `biomass_value_auto_derived=True` on the `SelectedSeaSiteInput` object (set by builder)
