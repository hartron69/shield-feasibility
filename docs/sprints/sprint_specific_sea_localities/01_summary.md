# Sprint: Specific Sea Localities

**Objective:** Allow sea-site PCC feasibility to use actual registered BarentsWatch localities instead of only a generic "number of sites" model.

## Deliverables

| # | Item | Status |
|---|------|--------|
| 1 | Mode toggle UI: Generisk portefølje / Spesifikke lokaliteter | Done |
| 2 | `SeaLocalitySelector.jsx` — multi-select from site registry | Done |
| 3 | `SeaLocalityAllocationTable.jsx` — per-site biomass/value editor | Done |
| 4 | Backend validation via `validate_selected_sites()` (HTTP 422 on error) | Done |
| 5 | `operator_builder` specific-locality path — fix missing `location` field | Done |
| 6 | `MetadataBlock` populated with `site_selection_mode`, `selected_site_count`, `selected_locality_numbers` | Done |
| 7 | `TraceabilityBlock.site_selection_mode` propagated from `alloc_summary` | Done |
| 8 | TraceabilityPanel chip: "Spesifikke lokaliteter" / "Generisk portefølje" | Done |
| 9 | 20 new tests (schema, validation, builder, metadata/API) | Done |
| 10 | Sprint docs | Done |

## Test Results

- **Backend:** 1600 passed, 0 failed (was 1092 before sprint series; +20 this sprint)
- **Frontend build:** 0 errors, 102 modules

## Key Design Decisions

- Generic sea mode is fully unchanged and backward-compatible
- Specific mode only activates when `site_selection_mode="specific"` AND `selected_sites` is non-empty
- Backend validation calls `validate_selected_sites()` before the pipeline runs
- `location` field added to `_build_specific_sites()` site_dict (bug fix; was missing, causing `SiteProfile` init failure)
- `build_traceability_block()` now accepts `site_selection_mode` parameter — avoids MagicMock fragility in tests
- Auto-derived biomass values are labelled "Auto-fordelt" in UI and emit an allocation warning
