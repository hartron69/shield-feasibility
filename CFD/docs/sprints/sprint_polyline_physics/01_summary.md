# Sprint 3 — PolylineCoastline Physics + Multi-Site Analysis

## Objective
Plug `PolylineCoastline` directly into the flow engine and particle transport model,
replacing the Sprint 2 `to_straight_approx()` workaround. Add multi-site transfer
analysis so each farm can be run as a pathogen source with results per target site.

## Deliverables

### core/geometry.py
- `PolylineCoastline.__init__` now accepts `alongshore_length_scale_m`,
  `offshore_decay_m`, `temporal_period_s`, `alongshore_variation_fraction`,
  `wall_image_weight` — same physics params as `StraightCoastline`, same defaults
- Added `y_coast` property (returns `mean_y_coast()`) — backward-compat shim for
  logging and approximate clamping
- Added `dominant_seaward_normal()` — length-weighted mean seaward normal across
  all segments; used by `_inlet_line` to orient the upstream particle source
- `FjordScenario.build_flow_model()` passes `PolylineCoastline` directly (Sprint 2
  `to_straight_approx()` call removed); populates `flow_model.site_assignments`
  (net_name → site_id dict)

### core/flow_engine.py
- Import `PolylineCoastline`; add `Dict` to typing imports
- `__init__`: add `site_assignments: Dict[str, str] = {}`
- `_log_parameter_summary`: prints `PolylineCoastline` segment count when applicable
- **New helper methods** (all type-dispatch on `isinstance(self.coast, PolylineCoastline)`):
  - `_coast_local_frame(x, y)` → `(dist, along_tangent, seaward_normal)`
  - `_is_on_land(x, y)` → bool
  - `_mirror_center_across_coast(cx, cy)` → `(mx, my)`
  - `_clamp_point_offshore(x, y, min_dist=2.0)` → `(x, y)` guaranteed offshore
- `coastal_background_velocity_at_point_time`: uses `_coast_local_frame` for local
  along/normal basis; spatial phase computed along local tangent (`s_along = dot([x,y], along)`)
- `_image_perturbation_from_net`: uses `_mirror_center_across_coast` instead of
  hardcoded `2*y_coast - cy` reflection
- `velocity_at_point_time`: no-normal-flow BC uses `_coast_local_frame` + removes
  coast-normal velocity component when within 1 m of coast (works for curved coast)
- `evaluate_field`: land mask uses `coast.is_on_land()` per grid cell for PolylineCoastline

### core/pathogen_transport.py
- Import `PolylineCoastline`
- `_reflect_off_coast`: uses `coast.is_on_land()` + `coast.reflect_particle()` for
  polyline; fallback: foot + 2 m normal offset if reflected point is still on land
- `_inlet_line`: uses `coast.dominant_seaward_normal()` for open-sea side detection
- `_spawn_particles`: both `upstream_line` and `infected_net` modes use
  `flow_model._clamp_point_offshore()` instead of hardcoded `y_coast + 2.0` clamp
- `run_case` summary rows: new columns `site_id` (from `site_assignments`) and
  `source_site_id` (non-empty when `source_mode='infected_net'`)
- `run_all` metadata: `coast` dict with `type`, `y_coast_m`, `n_segments` (polyline)

### main_v123.py
- `run_from_scenario_dir` result print includes `site_id` column
- **New function `run_multi_site_scenario(scenario_dir)`**: iterates over all sites
  with nets, seeds pathogen from each site's first net (infected_net mode), runs all
  forcing cases, combines summaries, and prints a pivot transfer matrix
  (source_site_id × target_site_id → worst risk status across cases)

## Test Results

```
coast type: PolylineCoastline
site_assignments: {'A-Not 1': 'SITE_A', 'A-Not 2': 'SITE_A', 'B-Not 1': 'SITE_B'}

Single source run (SITE_A infects A-Not 1, case=langs):
  site_id    net      source_site_id  risk_status
  SITE_A   A-Not 1   SITE_A          RED
  SITE_A   A-Not 2   SITE_A          GREEN
  SITE_B   B-Not 1   SITE_A          GREEN
```

- `PolylineCoastline` passes through `build_flow_model()` directly — no straight approx
- `local_tangent` / `local_normal_seaward` used at every evaluation point
- Image-source mirror reflects across nearest polyline segment
- Particle reflection uses signed-distance geometry
- `site_id` and `source_site_id` columns present in all summary DataFrames
- `import main_v123` imports cleanly (fixed `\U` escape in module docstring)

## Build Status
- No new dependencies
- `run_demo()` backward-compat maintained (StraightCoastline path unchanged)
- All four hardcoded `y_coast` references in flow_engine.py replaced with type-aware helpers
