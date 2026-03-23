# Tests: C5AI+ → Feasibility Traceability

## Test File: `tests/test_traceability.py`

19 tests, 3 classes, 0 failures.

### `TestBuildTraceabilityBlock` (13 tests)

Unit tests for `build_traceability_block()` using mock `sim`, `op`, and `LossAnalysisBlock` objects.

| Test | Assertion |
|---|---|
| `test_static_model_source` | `source="static_model"`, `c5ai_enriched=False`, `c5ai_scale_factor=None` |
| `test_c5ai_enriched_source` | `source="c5ai_plus"`, `data_mode="c5ai_forecast"`, `c5ai_scale_factor≈1.23` |
| `test_c5ai_mitigated_source` | `source="c5ai_plus_mitigated"`, `mitigated_forecast_used=True` |
| `test_site_ids_from_loss_analysis` | `site_ids` contains `"Site A"`, `"Site B"`, `site_count=2` |
| `test_domains_used_populated` | `"biological"` and `"structural"` in `domains_used`, `domain_count≥2` |
| `test_risk_types_used_populated` | `"hab"`, `"lice"` in `risk_types_used`; `risk_type_count==len(risk_types_used)` |
| `test_applied_mitigations` | Input mitigations appear in `applied_mitigations` |
| `test_analysis_id_non_empty` | `len(analysis_id) > 0` |
| `test_generated_at_iso_string` | `generated_at` parseable as ISO datetime |
| `test_site_trace_has_eal_and_scr` | All 2 site traces have `eal_nok > 0`, `scr_contribution_nok > 0`, `len(top_domains) >= 1` |
| `test_site_trace_matches_loss_analysis_site_ids` | `site_trace` site IDs == `loss_analysis.per_site` IDs |
| `test_graceful_with_no_loss_analysis` | `None` loss_analysis does not crash; `site_count >= 0`, `analysis_id != ""` |
| `test_mapping_note_non_empty` | `len(mapping_note) > 50` |

### `TestTraceabilitySchema` (3 tests)

Pydantic model validation tests.

| Test | Assertion |
|---|---|
| `test_traceability_block_validates` | `TraceabilityBlock(...)` constructs without error; `site_count=3` |
| `test_feasibility_response_backward_compat_without_traceability` | `FeasibilityResponse` without `traceability` sets field to `None` |
| `test_feasibility_response_accepts_traceability` | `FeasibilityResponse(traceability=tb).traceability.analysis_id == "xyz"` |

### `TestTraceabilityAPIEndToEnd` (3 tests)

Integration tests using `fastapi.testclient.TestClient` — no real HTTP.

| Test | Assertion |
|---|---|
| `test_feasibility_run_has_traceability_field` | `POST /api/feasibility/run` response JSON contains `"traceability"` key |
| `test_traceability_has_required_fields` | `analysis_id`, `generated_at`, `source`, `site_count`, `domains_used` all present |
| `test_traceability_site_ids_consistent_with_loss_analysis` | `traceability.site_ids` set == `loss_analysis.per_site[*].site_id` set |

## Full Suite

```
1484 passed, 0 failed, 53 warnings
(was 1465 before this sprint; +19 new tests)
```
