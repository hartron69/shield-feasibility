# Code Changes — Tapsanalyse Sprint

## New Files

| File | Purpose |
|---|---|
| `backend/services/loss_analysis.py` | `compute_loss_analysis()` — derives per-site EAL, SCR, domain breakdown, top drivers, and mitigated block from SimulationResults |
| `tests/test_loss_analysis.py` | 30 tests across 5 groups |
| `docs/sprints/sprint_loss_analysis/` | Sprint artifacts |

## Modified Files

### `backend/schemas.py`
Added before `FeasibilityResponse`:
- `LossAnalysisSite` — per-site fields
- `LossAnalysisMitigatedSite` — per-site mitigated fields
- `LossAnalysisMitigated` — mitigated block
- `LossAnalysisDriver` — driver record
- `LossAnalysisBlock` — top-level container

Added to `FeasibilityResponse`:
```python
loss_analysis: Optional[LossAnalysisBlock] = None
```

### `backend/services/run_analysis.py`
Both `run_feasibility_analysis` (smolt) and `run_feasibility_service` (sea):

1. Added `_la_mit_losses_1d`, `_la_mit_e_loss`, `_la_mit_scr` tracking variables initialised to `None` before the mitigation block
2. Set them when mitigation is computed
3. Added loss analysis computation block before each `return FeasibilityResponse(...)`:
   ```python
   from backend.services.loss_analysis import compute_loss_analysis
   _la_raw = compute_loss_analysis(sim, op, baseline_scr, ...)
   _la_block = LossAnalysisBlock(...)
   ```
4. Passed `loss_analysis=_la_block` to `FeasibilityResponse`
5. Wrapped in `try/except` to preserve backward compatibility on error

### `frontend/src/components/results/ResultPanel.jsx`
Changed Tapsanalyse tab wiring from:
```jsx
<SeaSiteLossTable facilityResults={result.facility_results || []} operatorName={result.operator_name} ... />
```
to:
```jsx
<SeaSiteLossTable lossAnalysis={result.loss_analysis || null} baseline={baseline} mitigated={mitigated} />
```

### `frontend/src/components/results/SeaSiteLossTable.jsx`
Complete rewrite. New structure:
- `fmtNOK` / `fmtDelta` — formatting helpers
- `DomainBadge` — colour-coded domain label
- `MiniBar` — inline horizontal bar (pure CSS, no SVG library)
- `DomainBar` — stacked domain colour bar
- `KpiCard` — reusable KPI card with optional delta
- `SeaSiteLossTable` (default export) — full component with 5 sections
