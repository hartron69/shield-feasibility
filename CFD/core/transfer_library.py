"""
core/transfer_library.py — Sprint 6: Precomputed Monte-Carlo transfer library

Builds an ensemble of transfer runs (N realisations with different random seeds)
and fits parametric distributions to the transfer coefficients.  The resulting
MCTransferLibrary can draw thousands of samples per second during Sprint 7 MC runs.

Workflow
--------
    # Build (one-off, ~N * 3 min per scenario)
    from core.transfer_library import EnsembleRunner
    mc_lib = EnsembleRunner(marcher_kwargs, n_ensemble=10).build(
        scenario, output_dir, current_forcing, case_list
    )
    mc_lib.save(output_dir)

    # Use in Sprint 7
    from core.transfer_library import MCTransferLibrary
    mc_lib = MCTransferLibrary.load(output_dir)
    rng = np.random.default_rng(0)
    tc_samples = mc_lib.sample_tc('SITE_A', 'SITE_B', n=10_000, rng=rng)

Distribution model
------------------
For each (source_site, target_site, case, metric) key:

  - All values == 0              → dist_type = 'zero'
  - Any nonzero values present   → dist_type = 'lognormal'
      * zero_fraction  = fraction of ensemble members with value == 0
      * lognormal_mu, lognormal_sigma fitted to log(nonzero values)
  - Empirical sample values are always stored (for diagnostics and small N).

Metrics fitted
--------------
  'transfer_coefficient_s'  — primary MC feed [s]
  'peak_mass_fraction'      — dimensionless peak [-]
  'first_arrival_s'         — arrival time [s]; NaN → 'no_arrival_fraction'
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.forcing import CurrentForcing
from core.transfer_engine import TransferEngine, TransferLibrary, TransferResult


# ── Distribution record ───────────────────────────────────────────────────────

@dataclass
class TransferDistribution:
    """
    Fitted distribution for one (source_site, target_site, case, metric) key.

    Parameters
    ----------
    source_site_id  : source locality
    target_site_id  : target locality
    case_name       : forcing case (e.g. 'timeseries', 'langs')
    metric          : 'transfer_coefficient_s' | 'peak_mass_fraction' |
                      'first_arrival_s'
    n_ensemble      : number of ensemble members
    nonzero_count   : number of members with finite nonzero value
    mean            : mean of all values (zeros included, NaN treated as 0)
    std             : std of all values
    p10, p50, p90   : percentiles of all values
    dist_type       : 'zero' | 'lognormal'
    lognormal_mu    : mu of log(x) for nonzero values (nan if dist_type=zero)
    lognormal_sigma : sigma of log(x) (nan if dist_type=zero or n_nonzero<2)
    zero_fraction   : fraction of ensemble members with value == 0 or NaN
    empirical       : raw values from all ensemble members (for diagnostics)
    """
    source_site_id: str
    target_site_id: str
    case_name: str
    metric: str
    n_ensemble: int
    nonzero_count: int
    mean: float
    std: float
    p10: float
    p50: float
    p90: float
    dist_type: str          # 'zero' | 'lognormal'
    lognormal_mu: float
    lognormal_sigma: float
    zero_fraction: float
    empirical: List[float] = field(default_factory=list)
    # Mean plan area of target nets in this (source, target, case) group [m²]
    # Used by MCRiskEngine to convert peak_mass_fraction -> peak_conc [mass/m²]
    target_net_plan_area_m2: float = 1.0

    # ── sampling ──────────────────────────────────────────────────────────────

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """
        Draw n independent samples from the fitted distribution.

        If dist_type == 'zero' all samples are 0.
        Otherwise samples the lognormal, then zeros a zero_fraction of them.
        """
        if self.dist_type == 'zero' or self.nonzero_count == 0:
            return np.zeros(n, dtype=float)

        sigma = self.lognormal_sigma
        if not math.isfinite(sigma) or sigma < 1e-9:
            # Effectively constant — return the mean of the nonzero values
            sigma = 1e-9

        samples = rng.lognormal(self.lognormal_mu, sigma, n)

        if self.zero_fraction > 0.0:
            zero_mask = rng.random(n) < self.zero_fraction
            samples[zero_mask] = 0.0

        return samples

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, float) and math.isnan(v):
                d[k] = None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'TransferDistribution':
        d = dict(d)
        float_fields = {
            'mean', 'std', 'p10', 'p50', 'p90',
            'lognormal_mu', 'lognormal_sigma', 'zero_fraction',
            'target_net_plan_area_m2',
        }
        for k in float_fields:
            if k in d:
                d[k] = float('nan') if d[k] is None else float(d[k])
        d.setdefault('target_net_plan_area_m2', 1.0)
        d['empirical'] = [
            float('nan') if v is None else float(v)
            for v in d.get('empirical', [])
        ]
        return cls(**d)


# ── Fitting helpers ───────────────────────────────────────────────────────────

_METRICS = ('transfer_coefficient_s', 'peak_mass_fraction', 'first_arrival_s')


def _fit_distribution(
    source_id: str,
    target_id: str,
    case_name: str,
    metric: str,
    values: List[float],                # raw values from all ensemble members; NaN = no arrival
    target_net_plan_area_m2: float = 1.0,
) -> TransferDistribution:
    """Fit a TransferDistribution from a list of raw values."""
    arr = np.array([v if math.isfinite(v) else 0.0 for v in values], dtype=float)
    nz = arr[arr > 0.0]
    n_ensemble = len(arr)
    nonzero_count = int(len(nz))
    zero_fraction = float((arr == 0.0).sum()) / n_ensemble if n_ensemble > 0 else 0.0

    mean_v = float(np.mean(arr))
    std_v = float(np.std(arr))
    p10, p50, p90 = (
        float(np.percentile(arr, 10)),
        float(np.percentile(arr, 50)),
        float(np.percentile(arr, 90)),
    )

    if nonzero_count == 0:
        return TransferDistribution(
            source_site_id=source_id, target_site_id=target_id,
            case_name=case_name, metric=metric,
            n_ensemble=n_ensemble, nonzero_count=0,
            mean=mean_v, std=std_v, p10=p10, p50=p50, p90=p90,
            dist_type='zero',
            lognormal_mu=float('nan'), lognormal_sigma=float('nan'),
            zero_fraction=zero_fraction,
            empirical=list(arr),
            target_net_plan_area_m2=target_net_plan_area_m2,
        )

    log_nz = np.log(nz)
    mu = float(np.mean(log_nz))
    sigma = float(np.std(log_nz)) if nonzero_count > 1 else float('nan')

    return TransferDistribution(
        source_site_id=source_id, target_site_id=target_id,
        case_name=case_name, metric=metric,
        n_ensemble=n_ensemble, nonzero_count=nonzero_count,
        mean=mean_v, std=std_v, p10=p10, p50=p50, p90=p90,
        dist_type='lognormal',
        lognormal_mu=mu, lognormal_sigma=sigma,
        zero_fraction=zero_fraction,
        empirical=list(arr),
        target_net_plan_area_m2=target_net_plan_area_m2,
    )


# ── Ensemble library ──────────────────────────────────────────────────────────

class EnsembleLibrary:
    """
    N independent TransferLibrary runs (one per random seed).

    Provides distribution fitting and conversion to MCTransferLibrary.
    """

    VERSION = 'v1.23-sprint6'

    def __init__(
        self,
        runs: List[TransferLibrary],
        scenario_name: str = '',
        metadata: Optional[dict] = None,
    ):
        self.runs = list(runs)
        self.scenario_name = str(scenario_name)
        self.metadata = metadata or {}

    # ── Fitting ───────────────────────────────────────────────────────────────

    def fit_distributions(self) -> List[TransferDistribution]:
        """
        For each (source_site, target_site, case_name, metric) key present in
        any run, collect values across runs and fit a distribution.
        """
        # Gather all values: key -> list of values (one per run)
        bucket: Dict[Tuple[str, str, str, str], List[float]] = {}
        # Net area: key (src, tgt, case) -> list of mean areas across runs
        area_bucket: Dict[Tuple[str, str, str], List[float]] = {}

        for run in self.runs:
            df = run.to_df()
            if df.empty:
                continue
            # Aggregate per (source_site, target_site, case_name):
            # sum TC and exposure, take max peak, take min arrival across nets
            # (so each run gives one value per site-pair-case triple)
            for (src, tgt, case), grp in df.groupby(
                ['source_site_id', 'target_site_id', 'case_name']
            ):
                # transfer_coefficient_s: sum across nets in this pair
                tc_sum = float(grp['transfer_coefficient_s'].fillna(0.0).sum())
                bucket.setdefault((src, tgt, case, 'transfer_coefficient_s'), []).append(tc_sum)

                # peak_mass_fraction: max across nets
                pmf_max = float(grp['peak_mass_fraction'].fillna(0.0).max())
                bucket.setdefault((src, tgt, case, 'peak_mass_fraction'), []).append(pmf_max)

                # first_arrival_s: min across nets (NaN if none arrived)
                arrivals = grp['first_arrival_s'].dropna()
                arr_val = float(arrivals.min()) if not arrivals.empty else float('nan')
                bucket.setdefault((src, tgt, case, 'first_arrival_s'), []).append(arr_val)

                # Mean target net area for peak-conc scaling in MCRiskEngine
                if 'target_net_plan_area_m2' in grp.columns:
                    area_vals = grp['target_net_plan_area_m2'].dropna()
                    if not area_vals.empty:
                        area_bucket.setdefault((src, tgt, case), []).append(
                            float(area_vals.mean())
                        )

        distributions: List[TransferDistribution] = []
        for (src, tgt, case, metric), values in bucket.items():
            # Pad to n_ensemble with zeros/NaN if some runs had no result for this key
            n_pad = len(self.runs) - len(values)
            if n_pad > 0:
                pad = float('nan') if metric == 'first_arrival_s' else 0.0
                values = values + [pad] * n_pad
            # Mean net area across all runs for this (src, tgt, case)
            area_vals = area_bucket.get((src, tgt, case), [1.0])
            mean_area = float(np.mean(area_vals)) if area_vals else 1.0
            distributions.append(
                _fit_distribution(src, tgt, case, metric, values,
                                  target_net_plan_area_m2=mean_area)
            )

        return distributions

    # ── Conversion ────────────────────────────────────────────────────────────

    def to_mc_library(self) -> 'MCTransferLibrary':
        """Fit distributions and return a queryable MCTransferLibrary."""
        dists = self.fit_distributions()
        return MCTransferLibrary(
            distributions=dists,
            scenario_name=self.scenario_name,
            n_ensemble=len(self.runs),
            metadata=self.metadata,
        )

    # ── IO ────────────────────────────────────────────────────────────────────

    def save(self, output_dir: Path, log_func=None) -> dict:
        """
        Save all runs' flat CSV files and an ensemble summary.

        Each run is saved under output_dir/ensemble/run_{i:03d}/.
        A combined ensemble_results.csv is written to output_dir.
        """
        _log = log_func or (lambda m: None)
        output_dir = Path(output_dir)
        (output_dir / 'ensemble').mkdir(parents=True, exist_ok=True)

        combined_rows = []
        for i, run in enumerate(self.runs):
            run_dir = output_dir / 'ensemble' / f'run_{i:03d}'
            run.save(run_dir, log_func=_log)
            df = run.to_df()
            if not df.empty:
                df['ensemble_member'] = i
                combined_rows.append(df)

        ensemble_csv = output_dir / 'ensemble_results.csv'
        if combined_rows:
            pd.concat(combined_rows, ignore_index=True).to_csv(ensemble_csv, index=False)
            _log(f"Ensemble results saved: {ensemble_csv}")

        return {'ensemble_csv': ensemble_csv}

    def __repr__(self) -> str:
        return (
            f"EnsembleLibrary(scenario='{self.scenario_name}', "
            f"n_runs={len(self.runs)})"
        )


# ── MC library ────────────────────────────────────────────────────────────────

class MCTransferLibrary:
    """
    Monte-Carlo queryable transfer coefficient library.

    Built from an EnsembleLibrary; each (source, target, case, metric) key
    holds a fitted TransferDistribution from which N samples can be drawn
    efficiently.

    Primary entry points for Sprint 7
    -----------------------------------
    sample_tc(src, tgt, n, rng)            — N samples of transfer_coefficient_s
    sample_peak(src, tgt, n, rng)          — N samples of peak_mass_fraction
    sample_arrival(src, tgt, n, rng)       — N samples of first_arrival_s
    expected_dose_matrix(shed_rate)        — E[TC] * shed_rate pivot table
    """

    VERSION = 'v1.23-sprint6'

    def __init__(
        self,
        distributions: List[TransferDistribution],
        scenario_name: str = '',
        n_ensemble: int = 0,
        metadata: Optional[dict] = None,
    ):
        self.distributions = list(distributions)
        self.scenario_name = str(scenario_name)
        self.n_ensemble = int(n_ensemble)
        self.metadata = metadata or {}
        # Index for fast lookup
        self._index: Dict[Tuple[str, str, str, str], TransferDistribution] = {
            (d.source_site_id, d.target_site_id, d.case_name, d.metric): d
            for d in self.distributions
        }
        # Unique keys
        self._source_ids = sorted({d.source_site_id for d in self.distributions})
        self._target_ids = sorted({d.target_site_id for d in self.distributions})
        self._case_names = sorted({d.case_name for d in self.distributions})

    # ── Lookup helpers ────────────────────────────────────────────────────────

    def _get_dist(
        self,
        source_id: str,
        target_id: str,
        metric: str,
        case_name: Optional[str] = None,
    ) -> Optional[TransferDistribution]:
        """Return distribution for given key, trying each known case if none given."""
        if case_name is not None:
            return self._index.get((source_id, target_id, case_name, metric))
        # Fall back: return first matching case
        for c in self._case_names:
            d = self._index.get((source_id, target_id, c, metric))
            if d is not None:
                return d
        return None

    # ── Sampling API ──────────────────────────────────────────────────────────

    def sample_tc(
        self,
        source_id: str,
        target_id: str,
        n: int,
        rng: np.random.Generator,
        case_name: Optional[str] = None,
    ) -> np.ndarray:
        """Draw n samples of transfer_coefficient_s [s]."""
        dist = self._get_dist(source_id, target_id, 'transfer_coefficient_s', case_name)
        return dist.sample(n, rng) if dist is not None else np.zeros(n, dtype=float)

    def sample_peak(
        self,
        source_id: str,
        target_id: str,
        n: int,
        rng: np.random.Generator,
        case_name: Optional[str] = None,
    ) -> np.ndarray:
        """Draw n samples of peak_mass_fraction [-]."""
        dist = self._get_dist(source_id, target_id, 'peak_mass_fraction', case_name)
        return dist.sample(n, rng) if dist is not None else np.zeros(n, dtype=float)

    def sample_arrival(
        self,
        source_id: str,
        target_id: str,
        n: int,
        rng: np.random.Generator,
        case_name: Optional[str] = None,
    ) -> np.ndarray:
        """
        Draw n samples of first_arrival_s [s].

        Returns NaN for samples where no arrival occurs (zero_fraction of
        ensemble had no arrival → that fraction of drawn samples are NaN).
        """
        dist = self._get_dist(source_id, target_id, 'first_arrival_s', case_name)
        if dist is None:
            return np.full(n, float('nan'))
        if dist.dist_type == 'zero':
            return np.full(n, float('nan'))
        sigma = dist.lognormal_sigma
        if not math.isfinite(sigma) or sigma < 1e-9:
            sigma = 1e-9
        samples = rng.lognormal(dist.lognormal_mu, sigma, n)
        # Zero-fraction for arrivals means no-arrival → NaN
        if dist.zero_fraction > 0.0:
            no_arr_mask = rng.random(n) < dist.zero_fraction
            samples[no_arr_mask] = float('nan')
        return samples

    # ── Summary views ─────────────────────────────────────────────────────────

    def expected_dose_matrix(
        self,
        shed_rate: float = 1.0,
        case_name: Optional[str] = None,
        metric: str = 'transfer_coefficient_s',
    ) -> pd.DataFrame:
        """
        Expected dose = E[TC] * shed_rate.

        Returns a pivot DataFrame: source_site_id x target_site_id -> value.
        """
        rows = []
        for src in self._source_ids:
            for tgt in self._target_ids:
                dist = self._get_dist(src, tgt, metric, case_name)
                if dist is not None:
                    rows.append({
                        'source_site_id': src,
                        'target_site_id': tgt,
                        'expected_dose': dist.mean * shed_rate,
                    })
        if not rows:
            return pd.DataFrame()
        pivot = (
            pd.DataFrame(rows)
            .pivot(index='source_site_id', columns='target_site_id', values='expected_dose')
        )
        pivot.columns.name = None
        pivot.index.name = 'source_site_id'
        return pivot

    def distribution_summary_df(self) -> pd.DataFrame:
        """Flat DataFrame of all fitted distributions (without empirical values)."""
        rows = []
        for d in self.distributions:
            row = d.to_dict()
            row.pop('empirical', None)
            rows.append(row)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def risk_summary_df(self) -> pd.DataFrame:
        """
        For each (source, target) pair: mean TC, zero_fraction, dist_type.
        Useful for quick risk screening.
        """
        tc_dists = [
            d for d in self.distributions
            if d.metric == 'transfer_coefficient_s'
        ]
        if not tc_dists:
            return pd.DataFrame()
        rows = [{
            'source_site_id': d.source_site_id,
            'target_site_id': d.target_site_id,
            'case_name': d.case_name,
            'mean_tc_s': d.mean,
            'p50_tc_s': d.p50,
            'p90_tc_s': d.p90,
            'zero_fraction': d.zero_fraction,
            'dist_type': d.dist_type,
            'n_ensemble': d.n_ensemble,
        } for d in tc_dists]
        return pd.DataFrame(rows)

    # ── IO ────────────────────────────────────────────────────────────────────

    def save(self, output_dir: Path, log_func=None) -> dict:
        """
        Save to output_dir.

        Writes:
          mc_transfer_library.json  — full library with all distributions
          mc_distribution_summary.csv — flat table of fitted parameters
        """
        _log = log_func or (lambda m: None)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / 'mc_transfer_library.json'
        csv_path = output_dir / 'mc_distribution_summary.csv'

        payload = {
            'version': self.VERSION,
            'scenario_name': self.scenario_name,
            'n_ensemble': self.n_ensemble,
            'metadata': self.metadata,
            'n_distributions': len(self.distributions),
            'distributions': [d.to_dict() for d in self.distributions],
        }
        with open(json_path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        _log(f"MC library saved: {json_path}")

        summary = self.distribution_summary_df()
        if not summary.empty:
            summary.to_csv(csv_path, index=False)
            _log(f"Distribution summary saved: {csv_path}")

        return {'json_path': json_path, 'csv_path': csv_path}

    @classmethod
    def load(cls, output_dir: Path) -> 'MCTransferLibrary':
        """Load a previously saved MCTransferLibrary."""
        json_path = Path(output_dir) / 'mc_transfer_library.json'
        with open(json_path, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)
        dists = [
            TransferDistribution.from_dict(d)
            for d in payload.get('distributions', [])
        ]
        return cls(
            distributions=dists,
            scenario_name=payload.get('scenario_name', ''),
            n_ensemble=int(payload.get('n_ensemble', 0)),
            metadata=payload.get('metadata', {}),
        )

    def __repr__(self) -> str:
        return (
            f"MCTransferLibrary(scenario='{self.scenario_name}', "
            f"n_ensemble={self.n_ensemble}, "
            f"n_distributions={len(self.distributions)})"
        )


# ── Ensemble runner ───────────────────────────────────────────────────────────

class EnsembleRunner:
    """
    Runs TransferEngine N times with different random seeds and returns an
    EnsembleLibrary ready for distribution fitting.

    Parameters
    ----------
    marcher_kwargs   : base kwargs forwarded to CoastalpathogenTimeMarcher
                       (random_seed is overridden per run)
    n_ensemble       : number of ensemble members (default 10)
    base_seed        : seed offset; member i uses random_seed = base_seed + i
    verbose          : log progress
    """

    VERSION = 'v1.23-sprint6'

    def __init__(
        self,
        marcher_kwargs: dict,
        n_ensemble: int = 10,
        base_seed: int = 0,
        verbose: bool = True,
    ):
        self.base_kwargs = dict(marcher_kwargs)
        self.base_kwargs.pop('random_seed', None)   # managed per run
        self.n_ensemble = int(n_ensemble)
        self.base_seed = int(base_seed)
        self.verbose = bool(verbose)

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[EnsembleRunner] {msg}", flush=True)

    def build(
        self,
        scenario,
        output_dir: Path,
        current_forcing: Optional[CurrentForcing] = None,
        case_list: Optional[List[str]] = None,
        save_runs: bool = True,
    ) -> EnsembleLibrary:
        """
        Run the transfer engine N times and return an EnsembleLibrary.

        Parameters
        ----------
        scenario       : FjordScenario
        output_dir     : base directory (ensemble members saved under ensemble/)
        current_forcing: time-varying forcing or None
        case_list      : forcing case list; auto-detected if None
        save_runs      : if True, save each run's CSV/JSON under output_dir/ensemble/

        Returns
        -------
        EnsembleLibrary
        """
        output_dir = Path(output_dir)

        self._log(
            f"Building ensemble: scenario='{scenario.name}' | "
            f"n_ensemble={self.n_ensemble} | base_seed={self.base_seed}"
        )

        # Resolve case_list once
        from core.scenarios import FLOW_USER_SETTINGS, RUN_USER_SETTINGS
        forcing = scenario.forcing
        U_inf = float(forcing.get('U_inf', FLOW_USER_SETTINGS['U_inf']))

        if case_list is None:
            if forcing.get('mode') == 'timeseries' and current_forcing is not None:
                case_list = ['timeseries']
            else:
                case_list = forcing.get('cases', list(RUN_USER_SETTINGS['cases']))

        runs: List[TransferLibrary] = []

        for i in range(self.n_ensemble):
            seed = self.base_seed + i
            self._log(f"  Member {i+1}/{self.n_ensemble} (seed={seed}) ...")

            kwargs = dict(self.base_kwargs)
            kwargs['random_seed'] = seed

            run_output = output_dir / 'ensemble' / f'run_{i:03d}' if save_runs else output_dir
            engine = TransferEngine(kwargs, verbose=False)   # suppress per-step logs
            lib = engine.run_all_pairs(
                scenario=scenario,
                output_dir=run_output,
                current_forcing=current_forcing,
                case_list=case_list,
            )
            runs.append(lib)
            self._log(
                f"    Member {i+1} done: {len(lib.results)} results."
            )

        # Forcing metadata
        if current_forcing is not None:
            forcing_meta = current_forcing.summary_stats()
        else:
            forcing_meta = {'type': 'named_cases', 'cases': case_list}

        ensemble = EnsembleLibrary(
            runs=runs,
            scenario_name=scenario.name,
            metadata={
                'version': self.VERSION,
                'scenario_name': scenario.name,
                'n_ensemble': self.n_ensemble,
                'base_seed': self.base_seed,
                'case_list': case_list,
                'forcing': forcing_meta,
            },
        )

        self._log(
            f"Ensemble complete: {len(runs)} runs | "
            f"{sum(len(r.results) for r in runs)} total results."
        )
        return ensemble
