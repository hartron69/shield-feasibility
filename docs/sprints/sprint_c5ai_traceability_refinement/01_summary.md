# Sprint: C5AI+ Traceability Refinement

## Objective
Strengthen trust, traceability, and site-level visibility between C5AI+ and
PCC Feasibility. Three goals:
1. Richer audit trail on every feasibility result (Part 1)
2. Site-level C5AI+ → Feasibility linkage visible to user (Part 2)
3. Stale-data confirmation modal before feasibility runs on outdated data (Part 3)

## Deliverables

### Part 1 — Extended C5AIRunMeta

| File | Change |
|---|---|
| `backend/services/c5ai_state.py` | Added `_extra_run_meta` dict; `store_run_extra()` and `get_run_extra()` helpers |
| `backend/api/c5ai.py` | `_run_c5ai_pipeline_safe()` now returns `site_ids`, `site_names`, `data_mode`; `run_c5ai()` calls `store_run_extra()` before recording run |
| `backend/schemas.py` | New `C5AISiteTrace` model; `C5AIRunMeta` extended with 8 new optional fields |
| `backend/services/run_analysis.py` | `_build_c5ai_meta()` accepts `loss_analysis` + `traceability`; builds `site_trace` from per-site loss data; populates all new meta fields |

New `C5AIRunMeta` fields (all optional, backward-compatible):
```
site_count, site_ids, site_names, data_mode,
domains_used, risk_type_count, source_labels, site_trace
```

### Part 2 — Site-level visibility in ResultPanel

| File | Change |
|---|---|
| `frontend/src/components/results/ResultPanel.jsx` | Replaced simple `c5ai-meta-bar` with full `c5ai-trace-strip` (freshness badge, run ID, timestamp, chips for site count / data mode / domain count); added `C5AISiteTracePanel` below strip |
| `frontend/src/components/results/C5AISiteTracePanel.jsx` | NEW — collapsible table showing per-site: site name/ID, dominant domain pill, EAL, SCR contribution; "Se i C5AI+ Risiko →" deep-link |
| `frontend/src/App.css` | New CSS sections: `.c5ai-trace-strip`, `.site-trace-panel`, `.modal-backdrop` |

### Part 3 — Stale confirmation modal

| File | Change |
|---|---|
| `frontend/src/components/ConfirmStaleC5AIModal.jsx` | NEW — modal with contextual messaging for stale vs missing; buttons: "Oppdater C5AI+ først" / "Kjør likevel" (only for stale) / "Avbryt" |
| `frontend/src/App.jsx` | `handleRun()` intercepts stale/missing state and sets `showStaleModal`; original run logic renamed to `_doRun()`; modal wired to `handleC5AIRun()` and `_doRun()` |

## Test Results
- `test_c5ai_gate.py`: **24 passed** (19 original + 5 new `TestExtendedC5AIRunMeta`)
- Full suite: **1 508 passed, 0 failed**

## Build
- `npm run build`: 0 errors, 100 modules, 930ms
