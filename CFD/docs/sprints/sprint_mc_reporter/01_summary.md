# Sprint 8 — Risk Reporting (MCReporter)

## Objective
Generate publication-quality PNG figures and a plain-text management summary from
Monte Carlo risk results, supporting both technical review and operator briefings.

## Deliverables

### core/mc_reporter.py (new)

**`MCReporter(mc_library, results, output_dir, scenario_name)`**:

| Method | Output file | Contents |
|---|---|---|
| `render_risk_heatmap()` | `mc_risk_heatmap.png` | 3 panels: modal status · P(RED) · E[score] |
| `render_transfer_heatmap()` | `mc_transfer_heatmap.png` | 3 panels: mean TC · p90 TC · VaR99 exposure |
| `render_pair_risk_profiles()` | `mc_pair_profiles.png` | Stacked P(G/Y/R) bars + E[score] dual-axis |
| `render_management_summary()` | `mc_management_summary.png` | 2×3 dashboard + coloured summary table |
| `write_text_summary()` | `mc_text_summary.txt` | UTF-8 management text with colour bands |
| `render_all()` | — | Returns `Dict[str, Path]` with all 5 keys |

**Colour scheme** (consistent across all figures):
```python
_STATUS_COLOR = {'GREEN': '#2ca02c', 'YELLOW': '#ffbf00', 'RED': '#d62728'}
```

**Text summary structure** (`write_text_summary`):
- Header with scenario name, date, n_samples (formatted with thousands separator)
- VURDERING section: RED pairs → `ROD RISIKO`, YELLOW → `GUL RISIKO`, GREEN → `GRONN RISIKO`
- `egenkontaminering` section: self-pairs (SA→SA, SB→SB)
- `krysskontaminering` section: cross-pairs; flags if any cross-pair is non-GREEN

### main_v123.py additions
- `generate_mc_report(scenario_dir, n_samples, shed_rate, rebuild_library, ...)` → dict
  with `mc_output` (risk engine outputs) + `report_paths` (5 output files)

## Technical Details
- `matplotlib.use('Agg')` — no display required (server/batch safe)
- `constrained_layout=True` — consistent figure margins
- `ListedColormap` used for modal-status tiles (exact colour control)
- Empty-results guard in `render_pair_risk_profiles` — returns path without crashing
- `log_func` parameter in `render_all()` — caller can inject print/logging callback

## Build Status
- No new dependencies (matplotlib + seaborn already required)
- All PNG outputs validated via magic bytes check `b'\x89PNG'`
- Text output UTF-8 encoded; Norwegian characters (Ø, æ) written correctly on Windows
