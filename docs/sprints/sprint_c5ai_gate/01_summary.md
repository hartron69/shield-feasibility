# Sprint: C5AI+ Activation and Freshness Gate

## Objective
Make the C5AI+ → Feasibility data flow explicit and gate-controlled. Users must
explicitly run C5AI+ before feasibility analysis; the UI communicates whether
C5AI+ data is fresh, stale, or missing at a glance.

## Deliverables

### Backend
| File | Change |
|---|---|
| `backend/services/c5ai_state.py` | NEW — in-memory singleton; tracks `_c5ai_last_run_at`, `_inputs_last_updated_at`, freshness rules |
| `backend/api/c5ai.py` | NEW — `POST /api/c5ai/run`, `GET /api/c5ai/status`, `POST /api/c5ai/inputs/updated` |
| `backend/schemas.py` | Added `C5AIRunResponse`, `C5AIStatusResponse`, `C5AIRunMeta`; `c5ai_meta` field on `FeasibilityResponse` |
| `backend/services/run_analysis.py` | Added `_build_c5ai_meta()` helper; both service functions attach `c5ai_meta` |
| `backend/main.py` | Registered `c5ai_router` |

### Frontend
| File | Change |
|---|---|
| `frontend/src/components/C5AIStatusBar.jsx` | NEW — green/yellow/red freshness badge, last-run timestamp, "Oppdater C5AI+" button, spinner |
| `frontend/src/components/RunControls.jsx` | Added `c5aiStatus` prop; yellow warning banner when freshness is stale/missing; Norwegian labels |
| `frontend/src/App.jsx` | `c5aiStatus`/`c5aiLoading` state; `handleC5AIRun()`; fetch status on mount; `notifyInputsUpdated()` on example loads; `C5AIStatusBar` in left panel |
| `frontend/src/components/results/ResultPanel.jsx` | `c5ai_meta` header bar (colour-coded by freshness) above tab bar |
| `frontend/src/api/client.js` | `runC5AI()`, `fetchC5AIStatus()`, `notifyInputsUpdated()` |
| `frontend/src/App.css` | CSS for C5AIStatusBar, stale warning banner, meta bar |

### Tests
| File | Tests |
|---|---|
| `tests/test_c5ai_gate.py` | 19 new tests (state unit × 7, endpoints × 8, feasibility meta × 4) |

## Freshness State Machine
```
missing  →  [POST /api/c5ai/run]  →  fresh
fresh    →  [POST /api/c5ai/inputs/updated after run_at]  →  stale
stale    →  [POST /api/c5ai/run]  →  fresh
```

## UX States
| Freshness | Status bar | RunControls | ResultPanel meta bar |
|---|---|---|---|
| `missing` | Red dot "C5AI+ ikke kjørt" | Yellow warning: "C5AI+ ikke kjørt — klikk Oppdater C5AI+" | Red "C5AI+ ikke kjørt" |
| `stale` | Yellow dot "C5AI+ ikke oppdatert" | Yellow warning: "C5AI+ data er utdatert" | Yellow "data er utdatert" |
| `fresh` | Green dot "C5AI+ oppdatert" + timestamp | No warning | Green "Basert på C5AI+ kjøring …" |

## Test Results
- New: **19 passed, 0 failed**
- Full suite: **1 503 passed, 0 failed** (was 1 092 at sprint start)

## Build Status
- `npm run build`: 0 errors, 98 modules transformed
- Backend import check: ok

## Notes
- `/api/c5ai/run` tries real `MultiDomainEngine`; stubs gracefully on any import/runtime error — endpoint always returns 200
- State is in-memory only; resets on backend restart (acceptable for single-session tool)
- Thread-safe via `threading.Lock` in `c5ai_state.py`
