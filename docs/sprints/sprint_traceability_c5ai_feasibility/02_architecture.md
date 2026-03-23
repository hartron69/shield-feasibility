# Architecture: C5AI+ → Feasibility Traceability

## Data Flow

```
FeasibilityRequest
      │
      ▼
run_feasibility_service() / run_feasibility_analysis()
      │
      ├─── MonteCarloEngine.run()  ─── SimulationResults
      │         (sim.c5ai_enriched, sim.domain_loss_breakdown, ...)
      │
      ├─── compute_loss_analysis() ─── LossAnalysisBlock
      │         (per_site: site_id, eal_nok, scr_contribution_nok, ...)
      │
      ├─── build_traceability_block(sim, op, mitigations, la_block)
      │         ─── TraceabilityBlock
      │
      └─── FeasibilityResponse(
               ...,
               loss_analysis=_la_block,
               traceability=_traceability,   ← NEW
           )
```

## New Pydantic Models (backend/schemas.py)

### `TraceabilitySiteTrace`
Per-site attribution fields: `site_id`, `site_name`, `eal_nok`, `scr_contribution_nok`,
`top_domains` (list of top 2 domains by loss magnitude).

### `TraceabilityBlock`
Full lineage record:
- `analysis_id` — random 12-char hex (unique per run)
- `generated_at` — UTC ISO timestamp
- `source` — `"static_model"` | `"c5ai_plus"` | `"c5ai_plus_mitigated"`
- `data_mode` — same three values (more descriptive alias)
- `c5ai_enriched` / `c5ai_scale_factor` — from `sim.c5ai_enriched`
- `site_count`, `domain_count`, `risk_type_count` — cardinalities
- `site_ids`, `domains_used`, `risk_types_used` — full lists
- `mitigated_forecast_used`, `applied_mitigations` — mitigation context
- `mapping_note` — Norwegian human-readable method note (~200 chars)
- `site_trace: List[TraceabilitySiteTrace]` — per-site EAL/SCR attribution

### `FeasibilityResponse` (updated)
Added `traceability: Optional[TraceabilityBlock] = None` as the last field.
Fully backward-compatible — existing API consumers receive `null` if the field is absent.

## Traceability Service (backend/services/traceability.py)

`build_traceability_block(sim, op, selected_mitigations, loss_analysis_block)`:
1. Reads `sim.c5ai_enriched`, `sim.c5ai_scale_factor`, `sim.mitigated` to determine `source`
2. Reads `loss_analysis_block.per_site` for site IDs (falls back to `op.sites`, then `sim.site_loss_distribution`)
3. Reads `sim.domain_loss_breakdown.domain_totals()` for active domains
4. Reads `sim.domain_loss_breakdown.all_subtypes()` for risk type list
5. Builds `site_trace` from loss analysis `per_site` (EAL + SCR + top 2 domains by amount)
6. Selects `mapping_note` from two pre-written Norwegian narratives (static vs C5AI+)
7. Returns `TraceabilityBlock` — all exceptions caught, never raises

## Frontend Components

### `TraceabilityPanel.jsx` (new)
Props: `traceability` (block or null), `onNavigateToRisk` (optional callback).
Renders:
- Header card: analysis ID, timestamp, data mode badge
- Pipeline flow diagram (4 nodes + arrows, pure CSS/inline styles, no SVG library)
- 4 KPI cards: sites, domains, risk types, mitigation count
- Site trace table (EAL + SCR + domain pills per site)
- Domain pills grid + risk type chips grid
- Collapsible method note (Norwegian)

### `ResultPanel.jsx` (updated)
- `TABS` array extended with `'Datagrunnlag'` (10th tab)
- `TraceabilityPanel` import added
- `onNavigate` prop added to function signature
- New tab renders `<TraceabilityPanel traceability={result.traceability} onNavigateToRisk={onNavigate} />`

### `App.jsx` (updated)
- `onNavigate={navigateTo}` prop passed to `<ResultPanel>` in the feasibility section

## Invariants Preserved

- `FeasibilityResponse` backward-compatible (traceability defaults to `null`)
- No new npm packages
- Pure SVG/CSS — no charting libraries in TraceabilityPanel
- Norwegian UI text throughout TraceabilityPanel
- Both `run_feasibility_analysis` and `run_feasibility_service` produce traceability
- Traceability build is wrapped in try/except — never breaks the feasibility response
