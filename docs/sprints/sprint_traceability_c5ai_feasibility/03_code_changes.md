# Code Changes: C5AI+ → Feasibility Traceability

## Files Modified

### `backend/schemas.py`
- Added `TraceabilitySiteTrace` model (after `LossAnalysisBlock`)
- Added `TraceabilityBlock` model (after `TraceabilitySiteTrace`)
- Added `traceability: Optional[TraceabilityBlock] = None` as last field on `FeasibilityResponse`

### `backend/services/run_analysis.py`
Two insertion points, one in each service function:

**`run_feasibility_analysis`** — inserted before the final `return FeasibilityResponse(...)`:
```python
from backend.services.traceability import build_traceability_block
try:
    _traceability = build_traceability_block(sim, op_input, selected_actions or [], _la_block)
except Exception:
    _traceability = None
```
Added `traceability=_traceability` to the `FeasibilityResponse(...)` call.

**`run_feasibility_service`** — same pattern, variables `_traceability2`, `sim`, `operator`, `selected`, `_la_block2`.

### `frontend/src/components/results/ResultPanel.jsx`
- Added `import TraceabilityPanel from './TraceabilityPanel.jsx'`
- Extended `TABS` array: added `'Datagrunnlag'` as 10th tab
- Added `onNavigate` to function signature: `{ result, selectedMitigations, library, operatorType, smoltFacilities, initialTab, onNavigate }`
- Added tab render block for `'Datagrunnlag'`

### `frontend/src/App.jsx`
- Added `onNavigate={navigateTo}` prop to `<ResultPanel>` in the feasibility section (line ~540)

## Files Created

### `backend/services/traceability.py`
New module. See `02_architecture.md` for full description of `build_traceability_block()`.

### `frontend/src/components/results/TraceabilityPanel.jsx`
New React component. 230 lines. No external dependencies beyond React.

### `tests/test_traceability.py`
19 tests across 3 classes. See `04_tests.md` for details.
