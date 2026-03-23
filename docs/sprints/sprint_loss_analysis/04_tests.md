# Tests — Tapsanalyse Sprint

## Test File: `tests/test_loss_analysis.py`

30 tests, 0 failures, 2 warnings (existing matplotlib deprecation).

| Group | Tests | Coverage |
|---|---|---|
| `TestComputeLossAnalysisStructure` | 9 | Required keys, site count, field presence, domain keys, method note, driver sorting |
| `TestComputeLossAnalysisQuantitative` | 5 | EAL sum ≈ portfolio EAL, SCR allocation sum = total_scr, SCR shares sum to 100%, largest-site ordering, domain breakdown per site ≈ site EAL |
| `TestComputeLossAnalysisMitigated` | 5 | Absent when no data; present when supplied; per-site EAL lower; delta_eal negative; delta_scr negative |
| `TestComputeLossAnalysisEdgeCases` | 4 | None site_distribution → empty; empty dict → empty; None domain breakdown → no crash; single site → 100% SCR share |
| `TestLossAnalysisSchema` | 3 | LossAnalysisBlock validates; FeasibilityResponse backward compat (no loss_analysis); FeasibilityResponse accepts loss_analysis |
| `TestLossAnalysisAPIEndToEnd` | 4 | Response key present; structure when populated; domain keys canonical; per_site non-empty |

## Frontend Tests

Not added in this sprint (no existing React testing infrastructure). Verified manually via:
- `npm run build` — 0 errors, 95 modules
- Visual inspection via dev server

## Full Suite

```
1465 passed, 47 warnings  (was 1435 before sprint)
```
