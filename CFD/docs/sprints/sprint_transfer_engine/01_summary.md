# Sprint 5 — Physical Transfer Engine

## Objective
Implement the pathogen transfer engine that runs CFD particle simulations for every
source→target site pair and computes dimensionless transfer coefficients, peak
concentrations, and first-arrival times.

## Deliverables

### core/transfer_engine.py (new)

**`TransferResult`** dataclass (14 fields):
- `source_site_id`, `target_site_id`, `source_net_name`, `target_net_name`, `case_name`
- `transfer_coefficient_s` — TC = total_exposure / total_shed_mass [s]
- `peak_mass_fraction` — PMF = peak_concentration × net_area / total_shed_mass [-]
- `first_arrival_s` — first time a particle reaches the target net [s]; NaN if never
- `total_exposure_mass_seconds` — integrated mass·time in target net [mass·s]
- `total_shed_mass` — shed_rate × total_time_s [mass]
- `risk_status` — GREEN / YELLOW / RED from `RiskEngine`
- `forcing_mean_speed_m_s`, `forcing_dir_deg` — metadata for the forcing applied
- `target_net_plan_area_m2` — net plan area used for peak concentration
- `to_dict()` / `from_dict()` with NaN ↔ None serialisation

**`TransferLibrary`**:
- `to_df()` — DataFrame (N rows × 14 columns)
- `transfer_matrix(metric, aggfunc)` — pivot: source rows × target columns
- `risk_matrix()` — modal risk status pivot
- `save(output_dir)` → `{csv_path, json_path}` — writes `transfer_results.csv` + `transfer_library.json`
- `load(output_dir)` — classmethod, restores NaN from None in JSON

**`TransferEngine`**:
- `__init__(marcher_kwargs)` — forces `auto_calibrate_from_first_case=False`
- `run_source(flow_model, src_site, case_list, current_forcing)` → `List[TransferResult]`
- `run_all_pairs(scenario, output_dir, current_forcing, case_list)` → `TransferLibrary`

Transfer coefficient formula:
```
TC  = total_exposure_mass_seconds / total_shed_mass          [s]
PMF = peak_concentration × net_plan_area / total_shed_mass   [-]
```

### main_v123.py additions
- `run_transfer_analysis(scenario_dir, shedding_rate_relative_per_s, ...)` → `TransferLibrary`
  Builds scenario + flow model, runs all pairs, saves to `output/<scenario>/transfer/`

## Test Results (manual run)
```
Transfer matrix (transfer_coefficient_s):
SA -> SA: 120.3 s  (RED)
SA -> SB: 0.0 s    (GREEN)
SB -> SA: 0.0 s    (GREEN)
SB -> SB: 98.7 s   (RED)
```
Diagonal RED, off-diagonal GREEN — confirms particle dispersion is localised to source site.

## Build Status
- No new dependencies
- `auto_calibrate_from_first_case=False` forced — deterministic across runs
- Backward compatible: `run_from_scenario_dir` unaffected
