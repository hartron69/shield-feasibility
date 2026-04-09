# Sprint 4 — CurrentForcing from CSV Time Series

## Objective
Replace hardcoded named current directions (`langs`/`tverrs`/`diagonal`) with
time-varying forcing read from a CSV file. The marcher now updates both flow
direction AND speed at every time step from the forcing.

## Deliverables

### core/forcing.py (new)
`CurrentForcing` class:
- Constructor: `times_s`, `u`, `v` (East/North components)
- `velocity_at(t_s)` → `np.ndarray` — linear interpolation, hold-last outside range
- `speed_at(t_s)` → float
- `direction_at(t_s)` → unit vector (fallback `[1,0]` if speed ~ 0)
- `mean_speed()`, `dominant_direction()`, `summary_stats()`
- `CurrentForcing.constant(u, v, duration_s)` — constant forcing for testing
- `CurrentForcing.from_named_case(case_name, U_inf, duration_s)` — convert v1.22b case
- `CurrentForcing.from_csv(path)` — two accepted CSV formats:
  - **Format A** (Cartesian): `time_s, u_m_s, v_m_s`
  - **Format B** (polar): `time_s, speed_m_s, direction_deg`
    (oceanographic toward: 0=N, 90=E)
- `to_csv(path, fmt='cartesian'|'polar')` — save back to CSV

### core/scenarios_io.py
- `load_scenario`: when `forcing.mode == 'timeseries'`, loads `currents.csv`
  (or `forcing.timeseries_file`) and attaches a `CurrentForcing` object to
  `forcing['_current_forcing']`
- `save_scenario_template`: writes template `currents.csv` (11-row sinusoidal cycle)
- `_template_currents_csv()`: 1200 s at 120 s intervals, eastward dominant + tidal swing

### core/pathogen_transport.py
- `CoastalpathogenTimeMarcher.__init__`: new `current_forcing: Optional[CurrentForcing] = None`
- New helpers:
  - `_get_case_dir(case_name, t_s)` — returns `forcing.direction_at(t_s)` or `case_vector(case_name)`
  - `_set_u_inf_for_step(t_s)` — sets `flow_model.U_inf = forcing.speed_at(t_s)`, returns original
- Time loop: calls `_set_u_inf_for_step(t)` + `_get_case_dir(case_name, t)` each step
- `_spawn_particles` upstream_line: uses `_get_case_dir(case_name, current_t)` for inlet direction
- `U_inf` restored to original value after `run_case()` completes
- `_log_parameter_summary`: prints forcing label, n points, duration, mean speed
- `run_all` metadata: `forcing` key with `summary_stats()` or `{'type': 'named_cases'}`

### main_v123.py
- `run_from_scenario_dir`: extracts `_current_forcing` from scenario forcing dict;
  uses `case_list = ['timeseries']` when mode is `timeseries`; passes
  `current_forcing` kwarg to `CoastalpathogenTimeMarcher`
- `run_multi_site_scenario`: same treatment

### scenarios/example_fjord/
- `currents.csv`: 11-row example time series (Format A, tidal-like cycle)
- `forcing.json`: updated with `timeseries_file` field and comment; mode remains
  `named_cases` by default so existing tests are unaffected

## Backward Compatibility
- `current_forcing=None` (default) → named-case mode, identical behavior to v1.22b
- `run_demo()` unaffected
- `case_vector('langs'|'tverrs'|'diagonal')` still works; `'timeseries'` is only
  used when `current_forcing` is set

## Test Results
```
# Named-case mode (no forcing)
current_forcing: None
       net  risk_status
A-Not 1      GREEN
A-Not 2      GREEN
B-Not 1      GREEN

# Timeseries mode (currents.csv)
       net  risk_status
A-Not 1      GREEN
A-Not 2      GREEN
B-Not 1      GREEN

# load_scenario timeseries mode
mode: timeseries
_current_forcing: CurrentForcing(label='currents', n=11, duration=1200s, mean_speed=0.255 m/s)

# CurrentForcing interpolation
vel at t=0s:   [0.55, 0.0]
vel at t=600s: [0.0424, -0.1519]
U_inf at t=0:   0.550 m/s
U_inf at t=600: 0.158 m/s
```

## Build Status
- No new dependencies
- `import main_v123` clean
- Named-case mode fully backward-compatible
