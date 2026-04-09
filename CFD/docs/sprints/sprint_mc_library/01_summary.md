# Sprint 6 — Precomputed MC-Ready Transfer Library

## Objective
Build an ensemble runner that executes N CFD realisations with different random seeds,
fits lognormal (zero-inflated) distributions to each (source, target, metric) triplet,
and serialises the result as an `MCTransferLibrary` ready for fast Monte Carlo sampling.

## Deliverables

### core/transfer_library.py (new)

**`TransferDistribution`** dataclass:
- `dist_type`: `'zero'` | `'lognormal'`
- `lognormal_mu`, `lognormal_sigma` — MLE on log(nonzero values); NaN if <2 nonzero
- `zero_fraction` — fraction of ensemble members with TC=0
- `nonzero_count`, `mean`, `p25`, `p50`, `p75`, `p90`
- `empirical: List[float]` — raw values from all runs
- `target_net_plan_area_m2: float = 1.0` — stored for MC peak-concentration scaling
- `sample(n, rng)` — zero-inflated lognormal draw:
  ```python
  draws = rng.lognormal(mu, sigma, n)
  draws[rng.random(n) < zero_fraction] = 0.0
  ```
- `to_dict()` / `from_dict()` — NaN ↔ None; backward-compat `setdefault('target_net_plan_area_m2', 1.0)`

**`_fit_distribution(src, tgt, case, metric, values, target_net_plan_area_m2=1.0)`**:
- All-zero → `dist_type='zero'`
- NaN treated as zero for TC metric
- MLE: `mu = mean(log(nonzero))`, `sigma = std(log(nonzero))`
- Single nonzero → `sigma=NaN` (can't compute std)

**`EnsembleLibrary`**:
- Holds N `TransferLibrary` runs
- `fit_distributions()` — aggregates per run: TC=sum across nets, PMF=max, arrival=min;
  passes `mean(target_net_plan_area_m2)` per group to `_fit_distribution`
- `to_mc_library()` → `MCTransferLibrary`
- `save(output_dir)` — writes `ensemble/run_NNN/` sub-folders + `ensemble_results.csv`

**`MCTransferLibrary`**:
- `_index: Dict[Tuple, TransferDistribution]` — O(1) lookup by (src, tgt, case, metric)
- `sample_tc/peak/arrival(src, tgt, n, rng, case_name)` — unknown pair → zeros/NaN
- `expected_dose_matrix(shed_rate)` — DataFrame pivot of mean TC × shed_rate × area
- `risk_summary_df()` — summary DataFrame with `mean_tc_s`, `zero_fraction`, etc.
- `save(output_dir)` / `load(output_dir)` — `mc_transfer_library.json` + `mc_distribution_summary.csv`

**`EnsembleRunner`**:
- `build(scenario, output_dir, current_forcing, case_list)` → `EnsembleLibrary`
- Suppresses per-step logs in sub-engine runs (`verbose=False`)

### main_v123.py additions
- `build_mc_library(scenario_dir, n_ensemble, base_seed, ...)` → `MCTransferLibrary`
- `load_mc_library(scenario_dir)` → `MCTransferLibrary`

## Build Status
- No new dependencies
- Zero-inflated lognormal handles cross-site pairs where some runs show no transfer
- `target_net_plan_area_m2` stored in distribution enables later MC peak-concentration scaling
- TYPE_CHECKING imports used for optional heavy imports in `main_v123.py`
