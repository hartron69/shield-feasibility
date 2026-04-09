# Sprint 7 — MonteCarloRiskEngine

## Objective
Implement a vectorised Monte Carlo risk classifier that samples transfer distributions
N times and returns probability distributions over GREEN / YELLOW / RED risk states
for every source→target site pair.

## Deliverables

### core/mc_risk_engine.py (new)

**`_classify_vectorised(arrival_s, peak_conc, exposure_ms, risk, no_arrival_means_green=True)`**:
Pure NumPy — no Python loop. Returns `(is_green, is_yellow, is_red)` bool arrays:
```python
no_arrival      = np.isnan(arrival_s)
all_green_mask  = no_arrival & (peak_conc <= 0) & (exposure_ms <= 0) & no_arrival_means_green
red_arr         = ~no_arrival & (arrival_s <= risk.red_arrival_threshold_s)
red_peak        = peak_conc >= risk.red_peak_risk_concentration
red_exp         = exposure_ms >= risk.red_exposure_threshold_mass_seconds
is_red          = (red_arr | red_peak | red_exp) & ~all_green_mask
yel_arr         = ~no_arrival & (arrival_s <= risk.yellow_arrival_threshold_s) & ~red_arr
...
is_yellow       = (yel_arr | yel_peak | yel_exp) & ~is_red & ~all_green_mask
is_green        = ~is_red & ~is_yellow
```
Guarantees: exactly one of {GREEN, YELLOW, RED} is True per sample.

**`MCRiskResult`** dataclass (18 fields):
- Probabilities: `p_green`, `p_yellow`, `p_red`
- `modal_risk_status` — argmax of {p_green, p_yellow, p_red}
- `expected_risk_score` — 0×p_green + 1×p_yellow + 2×p_red
- TC percentiles: `mean_tc_s`, `p10/50/90_tc_s`
- Exposure: `mean_exposure_ms`, `var95/99_exposure_ms`
- Arrival: `mean_first_arrival_s`, `p_no_arrival`, `p90_first_arrival_s`
- `to_dict()` / `from_dict()` with NaN handling

**`MonteCarloRiskEngine`**:
- `__init__(mc_library, n_samples, shed_rate, total_time_s, seed)`
- Dose scaling:
  ```
  exposure_ms = TC × shed_rate × total_time_s × sif
  peak_conc   = PMF × shed_rate × total_time_s × sif / net_area
  ```
- `run_pair(src, tgt, case_name)` → `MCRiskResult`
- `run_all()` → `List[MCRiskResult]` — all N² site pairs
- Matrix helpers: `risk_probability_matrix(status)`, `modal_risk_matrix()`,
  `expected_risk_score_matrix()`, `summary_df()`
- `save_results(results, output_dir)` → `{csv_path, json_path}`

### main_v123.py additions
- `run_mc_risk(scenario_dir, n_samples, shed_rate, rebuild_library, ...)` → dict with
  `mc_library`, `results`, `summary_df`, `p_red_matrix`, `modal_matrix`, `score_matrix`

## Design Notes
- `target_net_plan_area_m2` added to `TransferDistribution` in Sprint 6 → used here for
  peak concentration back-calculation
- `shed_rate` parameter scales all exposure metrics; doubling it → higher VaR but same
  modal status when already RED
- SIF (scenario intensity factor) reserved for future parametric sensitivity runs

## Build Status
- No new dependencies (pure NumPy + dataclasses)
- Vectorised over N=5 000–100 000 samples; typically <1 s for N=10 000, 4-pair scenario
