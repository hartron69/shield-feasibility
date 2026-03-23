# Architecture — C5AI+ Traceability Refinement

## Data Flow

```
POST /api/c5ai/run
  └─► _run_c5ai_pipeline_safe()
        returns: site_ids, site_names, data_mode, risk_type_count, ...
  └─► store_run_extra({ site_ids, site_names, data_mode, domains_used, ... })
        stored in: backend/services/c5ai_state._extra_run_meta (dict, thread-safe)
  └─► record_c5ai_run()
        stored in: _c5ai_run_id, _c5ai_last_run_at

POST /api/feasibility/run
  └─► run_feasibility_service()
        └─► compute_loss_analysis() → LossAnalysisBlock (per_site, per_domain, top_drivers)
        └─► build_traceability_block() → TraceabilityBlock (site_ids, domains_used, ...)
        └─► _build_c5ai_meta(loss_analysis, traceability)
              reads: c5ai_state.get_status() → run_id, freshness, is_fresh
              reads: c5ai_state.get_run_extra() → site_ids, site_names, data_mode, ...
              builds: site_trace from loss_analysis.per_site (exact EAL, approx SCR)
              returns: C5AIRunMeta (14 fields total)
        └─► FeasibilityResponse.c5ai_meta = C5AIRunMeta
```

## C5AIRunMeta Schema

```python
class C5AISiteTrace(BaseModel):
    site_id: str
    site_name: str
    expected_annual_loss_nok: float = 0.0   # exact (Monte Carlo)
    scr_contribution_nok: float = 0.0        # approx (proportional allocation)
    dominant_domain: str = ""
    top_risk_types: List[str] = []

class C5AIRunMeta(BaseModel):
    # Freshness (Sprint 3)
    run_id: Optional[str] = None
    generated_at: Optional[str] = None
    is_fresh: bool = False
    freshness: str = "missing"
    # Extended (this sprint)
    site_count: int = 0
    site_ids: List[str] = []
    site_names: List[str] = []
    data_mode: str = "simulated"     # simulated | real | mixed
    domains_used: List[str] = []
    risk_type_count: int = 0
    source_labels: List[str] = []
    site_trace: List[C5AISiteTrace] = []
```

## Site Trace Method

The `site_trace` in `C5AIRunMeta` is built from `loss_analysis.per_site` (the same
data shown in the Tapsanalyse tab). This is intentional: it shows exactly which sites
the feasibility Monte Carlo actually distributed losses to.

| Field | Source | Precision |
|---|---|---|
| `site_id` | `loss_analysis.per_site[i].site_id` | Exact |
| `site_name` | `loss_analysis.per_site[i].site_name` | Exact |
| `expected_annual_loss_nok` | Monte Carlo mean annual | Exact |
| `scr_contribution_nok` | Proportional VaR99.5 allocation | Approximate |
| `dominant_domain` | Max domain in domain_breakdown | Approximate (portfolio-level domain mix allocated proportionally) |

## Stale Modal Logic

```
handleRun()
  ├─ if freshness === 'missing' → show modal (no "Kjør likevel" option)
  ├─ if freshness === 'stale'   → show modal (with "Kjør likevel" option)
  └─ if freshness === 'fresh'   → call _doRun() directly

Modal responses:
  "Oppdater C5AI+ først" → handleC5AIRun() → setC5aiStatus → (user must click "Kjør Feasibility" again)
  "Kjør likevel"         → _doRun() directly (only for stale)
  "Avbryt"               → close modal, no action
```

## What is NOT wired (documented limitations)

- The `site_trace` shows feasibility sites (derived from operator n_sites + template),
  not C5AI+ demo sites (DEMO_OP_S01-S03). The two datasets are parallel, not identical.
- `data_mode` reflects whether the C5AI+ pipeline ran (real/simulated), not whether
  the Monte Carlo used live C5AI+ forecasts (it currently uses the static model always).
- `source_labels` is populated from C5AI+ run metadata, not from live data providers.
  Future: link to BarentsWatch / Seacloud sources when real ingestion is wired.
