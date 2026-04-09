"""
core/transfer_engine.py — Sprint 5: Physical transfer engine

Computes normalised pathogen transfer coefficients between sites.
Each (source_site, target_net, case) triple is represented by a
TransferResult.  A TransferLibrary aggregates results and handles IO.

Usage
-----
    from core.transfer_engine import TransferEngine

    library = TransferEngine(marcher_kwargs).run_all_pairs(
        scenario, output_dir, current_forcing, case_list
    )
    print(library.risk_matrix())
    library.save(output_dir)

Physics notes
-------------
Source mode is always 'infected_net'.  Each time step sheds

    shed_per_step = shedding_rate_relative_per_s * dt_s   [mass / step]

Total shed over the simulation:

    total_shed_mass = shedding_rate_relative_per_s * total_time_s   [mass]

Transfer coefficient (sprint 5 primary metric):

    transfer_coefficient_s = total_exposure_mass_seconds / total_shed_mass
        units: [s]  — effective cumulative exposure seconds per unit shed mass

Peak mass fraction (dimensionless):

    peak_mass_fraction = peak_relative_concentration * net.plan_area / total_shed_mass

Both metrics are suitable for Monte-Carlo sampling in Sprint 6.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from core.forcing import CurrentForcing
from core.pathogen_transport import CoastalpathogenTimeMarcher
from core.scenarios import RISK_USER_SETTINGS


# ── Result record ─────────────────────────────────────────────────────────────

@dataclass
class TransferResult:
    """
    Pathogen transfer result for one (source_net, target_net, case) triple.

    Attributes
    ----------
    source_site_id   : site_id of the shedding farm
    target_site_id   : site_id of the receiving net
    source_net_name  : net name used as pathogen source
    target_net_name  : net name where concentration is measured
    case_name        : forcing case (e.g. 'langs', 'timeseries')
    transfer_coefficient_s : total_exposure_mass_s / total_shed_mass  [s]
    peak_mass_fraction     : peak mass in net / total shed mass  [-]
    first_arrival_s        : first particle arrival time (NaN if none)
    total_exposure_mass_seconds : raw cumulative exposure integral  [mass·s]
    total_shed_mass        : total pathogen mass released by source  [mass]
    risk_status      : 'GREEN' | 'YELLOW' | 'RED'
    forcing_mean_speed_m_s : mean current speed during case  [m/s]
    forcing_dir_deg        : dominant current direction (oceanographic, towards) [deg]
    target_net_plan_area_m2: plan area of target net  [m²]
    """
    source_site_id: str
    target_site_id: str
    source_net_name: str
    target_net_name: str
    case_name: str
    transfer_coefficient_s: float
    peak_mass_fraction: float
    first_arrival_s: float          # NaN when no arrival
    total_exposure_mass_seconds: float
    total_shed_mass: float
    risk_status: str
    forcing_mean_speed_m_s: float
    forcing_dir_deg: float
    target_net_plan_area_m2: float

    # ── serialisation ──

    def to_dict(self) -> dict:
        d = asdict(self)
        # JSON-safe NaN
        for k, v in d.items():
            if isinstance(v, float) and math.isnan(v):
                d[k] = None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'TransferResult':
        d = dict(d)
        # Restore None -> NaN for float fields
        float_fields = {
            'transfer_coefficient_s', 'peak_mass_fraction', 'first_arrival_s',
            'total_exposure_mass_seconds', 'total_shed_mass',
            'forcing_mean_speed_m_s', 'forcing_dir_deg', 'target_net_plan_area_m2',
        }
        for k in float_fields:
            if k in d and d[k] is None:
                d[k] = float('nan')
            elif k in d:
                d[k] = float(d[k])
        return cls(**d)


# ── Library ───────────────────────────────────────────────────────────────────

class TransferLibrary:
    """
    Collection of TransferResult records with pivot and IO helpers.

    This is the output artefact for Sprint 5 and the input feed for
    Sprint 6 (precomputed Monte-Carlo library).
    """

    VERSION = 'v1.23-sprint5'

    def __init__(
        self,
        results: List[TransferResult],
        scenario_name: str = '',
        metadata: Optional[dict] = None,
    ):
        self.results = list(results)
        self.scenario_name = str(scenario_name)
        self.metadata = metadata or {}

    # ── DataFrame views ───────────────────────────────────────────────────────

    def to_df(self) -> pd.DataFrame:
        """All results as a flat DataFrame."""
        if not self.results:
            return pd.DataFrame()
        return pd.DataFrame([r.to_dict() for r in self.results])

    def transfer_matrix(
        self,
        metric: str = 'transfer_coefficient_s',
        aggfunc: str = 'max',
    ) -> pd.DataFrame:
        """
        Pivot table: source_site_id (rows) x target_site_id (columns).

        metric   : any numeric column from to_dict() — default is
                   'transfer_coefficient_s'.
        aggfunc  : 'max' | 'mean' | 'sum' — aggregated over cases and nets
                   within each (source, target) pair.
        """
        df = self.to_df()
        if df.empty:
            return pd.DataFrame()
        agg = {'max': np.max, 'mean': np.mean, 'sum': np.sum}.get(aggfunc, np.max)
        rows = []
        for (src, tgt), grp in df.groupby(['source_site_id', 'target_site_id']):
            rows.append({
                'source_site_id': src,
                'target_site_id': tgt,
                metric: float(agg(grp[metric].dropna())),
            })
        if not rows:
            return pd.DataFrame()
        pivot_df = (
            pd.DataFrame(rows)
            .pivot(index='source_site_id', columns='target_site_id', values=metric)
        )
        pivot_df.columns.name = None
        pivot_df.index.name = 'source_site_id'
        return pivot_df

    def risk_matrix(self) -> pd.DataFrame:
        """
        Pivot: source_site_id x target_site_id -> worst risk_status across
        all cases and nets.
        """
        df = self.to_df()
        if df.empty:
            return pd.DataFrame()
        _ord = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}

        def _worst(series):
            return max(series.tolist(), key=lambda s: _ord.get(str(s).upper(), 0))

        rows = []
        for (src, tgt), grp in df.groupby(['source_site_id', 'target_site_id']):
            rows.append({
                'source_site_id': src,
                'target_site_id': tgt,
                'worst_risk_status': _worst(grp['risk_status']),
            })
        if not rows:
            return pd.DataFrame()
        pivot_df = (
            pd.DataFrame(rows)
            .pivot(index='source_site_id', columns='target_site_id', values='worst_risk_status')
        )
        pivot_df.columns.name = None
        pivot_df.index.name = 'source_site_id'
        return pivot_df

    # ── IO ────────────────────────────────────────────────────────────────────

    def save(self, output_dir: Path, log_func=None) -> dict:
        """
        Save results to output_dir.

        Writes:
          transfer_results.csv     — flat table of all TransferResult records
          transfer_library.json    — same + metadata + pivot matrices

        Returns dict with 'csv_path' and 'json_path'.
        """
        _log = log_func or (lambda m: None)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_path = output_dir / 'transfer_results.csv'
        json_path = output_dir / 'transfer_library.json'

        df = self.to_df()
        if not df.empty:
            df.to_csv(csv_path, index=False)
            _log(f"Transfer results saved: {csv_path}")

        # Build JSON payload
        tc_mat = self.transfer_matrix('transfer_coefficient_s', 'max')
        risk_mat = self.risk_matrix()

        payload = {
            'version': self.VERSION,
            'scenario_name': self.scenario_name,
            'metadata': self.metadata,
            'n_results': len(self.results),
            'results': [r.to_dict() for r in self.results],
            'transfer_matrix_tc_s': (
                tc_mat.to_dict() if not tc_mat.empty else {}
            ),
            'risk_matrix': (
                risk_mat.to_dict() if not risk_mat.empty else {}
            ),
        }
        with open(json_path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        _log(f"Transfer library saved: {json_path}")

        return {'csv_path': csv_path, 'json_path': json_path}

    @classmethod
    def load(cls, output_dir: Path) -> 'TransferLibrary':
        """Load a TransferLibrary previously saved with .save()."""
        json_path = Path(output_dir) / 'transfer_library.json'
        with open(json_path, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)
        results = [TransferResult.from_dict(d) for d in payload.get('results', [])]
        return cls(
            results=results,
            scenario_name=payload.get('scenario_name', ''),
            metadata=payload.get('metadata', {}),
        )

    # ── repr ──────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"TransferLibrary(scenario='{self.scenario_name}', "
            f"n_results={len(self.results)})"
        )


# ── Engine ────────────────────────────────────────────────────────────────────

class TransferEngine:
    """
    Runs pathogen transport from each source site and computes normalised
    transfer coefficients to all target nets.

    Parameters
    ----------
    marcher_kwargs : dict
        Base keyword arguments forwarded to CoastalpathogenTimeMarcher.
        'source_mode' and 'source_net_name' are overridden per source site.
        'auto_calibrate_from_first_case' is forced False so thresholds are
        consistent across all source runs.
    verbose : bool
    """

    VERSION = 'v1.23-sprint5'

    def __init__(self, marcher_kwargs: dict, verbose: bool = True):
        self.base_kwargs = dict(marcher_kwargs)
        # Disable auto-calibration: we want fixed thresholds for a fair comparison
        self.base_kwargs['auto_calibrate_from_first_case'] = False
        self.verbose = bool(verbose)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[TransferEngine] {msg}", flush=True)

    def _forcing_stats(
        self,
        case_name: str,
        current_forcing: Optional[CurrentForcing],
        flow_model,
    ) -> tuple[float, float]:
        """Return (mean_speed_m_s, dir_deg) for a given case."""
        if current_forcing is not None:
            stats = current_forcing.summary_stats()
            mean_speed = float(stats.get('mean_speed_m_s', float('nan')))
            dominant_dir = current_forcing.dominant_direction()
        else:
            try:
                cv = flow_model.case_vector(case_name)
            except Exception:
                cv = np.array([1.0, 0.0])
            u_inf = float(flow_model.U_inf)
            mean_speed = u_inf
            # Oceanographic convention: direction the flow is heading toward
            # 0=N, 90=E, measured clockwise from North
            angle_rad = math.atan2(cv[0], cv[1])   # atan2(east, north) -> CW from N
            dominant_dir = np.array([cv[0], cv[1]])
        # Convert direction vector to degrees (oceanographic CW from North)
        dx, dy = float(dominant_dir[0]), float(dominant_dir[1])
        speed_from_dir = math.hypot(dx, dy)
        if speed_from_dir < 1e-12:
            dir_deg = float('nan')
        else:
            dir_deg = math.degrees(math.atan2(dx, dy)) % 360.0
        if current_forcing is None:
            mean_speed = float(flow_model.U_inf)
        return mean_speed, dir_deg

    # ── Per-source run ────────────────────────────────────────────────────────

    def run_source(
        self,
        flow_model,
        source_site,
        case_list: List[str],
        current_forcing: Optional[CurrentForcing],
    ) -> List[TransferResult]:
        """
        Run pathogen transport from source_site for all cases.

        Returns a list of TransferResult, one per (case, target_net) pair.
        """
        src_id = source_site.site_id
        src_net = source_site.nets[0]  # primary net of source site
        self._log(
            f"Source site '{src_id}' ({source_site.name}) "
            f"-> net '{src_net.name}' | cases: {case_list}"
        )

        kwargs = dict(self.base_kwargs)
        kwargs['source_mode'] = 'infected_net'
        kwargs['source_net_name'] = src_net.name
        kwargs['current_forcing'] = current_forcing
        kwargs['verbose'] = self.verbose

        marcher = CoastalpathogenTimeMarcher(flow_model, **kwargs)

        shedding_rate = float(kwargs.get('shedding_rate_relative_per_s', 1.0))
        total_time_s = marcher.total_time_s
        total_shed_mass = shedding_rate * total_time_s

        # Net plan_area lookup
        net_area: Dict[str, float] = {
            net.name: float(net.plan_area) for net in flow_model.nets
        }
        site_of_net: Dict[str, str] = dict(flow_model.site_assignments)

        results: List[TransferResult] = []

        for case_name in case_list:
            self._log(f"  Running case '{case_name}' ...")
            case_result = marcher.run_case(case_name)
            summary_df = case_result['summary']

            mean_speed, dir_deg = self._forcing_stats(case_name, current_forcing, flow_model)

            for _, row in summary_df.iterrows():
                tgt_net_name = str(row['net'])
                tgt_site_id = str(row.get('site_id', ''))

                raw_exp = float(row.get('total_exposure_mass_seconds', 0.0) or 0.0)
                peak_conc = float(row.get('peak_relative_concentration', 0.0) or 0.0)
                plan_area = net_area.get(tgt_net_name, 1.0)

                tc = raw_exp / total_shed_mass if total_shed_mass > 0 else float('nan')
                peak_frac = (peak_conc * plan_area / total_shed_mass
                             if total_shed_mass > 0 else float('nan'))

                first_arr = row.get('first_arrival_s', float('nan'))
                if first_arr is None or (isinstance(first_arr, float) and math.isnan(first_arr)):
                    first_arr = float('nan')
                else:
                    first_arr = float(first_arr)

                results.append(TransferResult(
                    source_site_id=src_id,
                    target_site_id=tgt_site_id,
                    source_net_name=src_net.name,
                    target_net_name=tgt_net_name,
                    case_name=case_name,
                    transfer_coefficient_s=tc,
                    peak_mass_fraction=peak_frac,
                    first_arrival_s=first_arr,
                    total_exposure_mass_seconds=raw_exp,
                    total_shed_mass=total_shed_mass,
                    risk_status=str(row.get('risk_status', 'GREEN')),
                    forcing_mean_speed_m_s=mean_speed,
                    forcing_dir_deg=dir_deg,
                    target_net_plan_area_m2=plan_area,
                ))

        self._log(
            f"  Source '{src_id}' done — "
            f"{len(results)} result records ({len(case_list)} cases x "
            f"{len(flow_model.nets)} nets)."
        )
        return results

    # ── Full analysis ─────────────────────────────────────────────────────────

    def run_all_pairs(
        self,
        scenario,
        output_dir: Path,
        current_forcing: Optional[CurrentForcing] = None,
        case_list: Optional[List[str]] = None,
    ) -> TransferLibrary:
        """
        Run transfer analysis for all sites as sources.

        Parameters
        ----------
        scenario       : FjordScenario (must have been built via load_scenario)
        output_dir     : directory for outputs (created if absent)
        current_forcing: CurrentForcing or None (named-case mode)
        case_list      : list of case names; defaults to ['timeseries'] or
                         scenario forcing cases

        Returns
        -------
        TransferLibrary with all TransferResult records
        """
        from core.scenarios import FLOW_USER_SETTINGS, RUN_USER_SETTINGS

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        forcing = scenario.forcing
        U_inf = float(forcing.get('U_inf', FLOW_USER_SETTINGS['U_inf']))

        if case_list is None:
            if forcing.get('mode') == 'timeseries' and current_forcing is not None:
                case_list = ['timeseries']
            else:
                case_list = forcing.get('cases', list(RUN_USER_SETTINGS['cases']))

        flow_model = scenario.build_flow_model(U_inf=U_inf, output_dir=output_dir)

        sites_with_nets = [s for s in scenario.sites if s.nets]
        if not sites_with_nets:
            self._log("No sites with nets found. Returning empty library.")
            return TransferLibrary([], scenario_name=scenario.name)

        self._log(
            f"Transfer analysis: scenario='{scenario.name}' | "
            f"{len(sites_with_nets)} source sites | "
            f"cases={case_list}"
        )

        all_results: List[TransferResult] = []
        for src_site in sites_with_nets:
            site_results = self.run_source(
                flow_model, src_site, case_list, current_forcing
            )
            all_results.extend(site_results)

        # Forcing metadata
        if current_forcing is not None:
            forcing_meta = current_forcing.summary_stats()
        else:
            forcing_meta = {'type': 'named_cases', 'cases': case_list}

        library = TransferLibrary(
            results=all_results,
            scenario_name=scenario.name,
            metadata={
                'version': self.VERSION,
                'scenario_name': scenario.name,
                'n_source_sites': len(sites_with_nets),
                'case_list': case_list,
                'n_nets': len(flow_model.nets),
                'forcing': forcing_meta,
                'shedding_rate_relative_per_s': float(
                    self.base_kwargs.get('shedding_rate_relative_per_s', 1.0)
                ),
                'total_time_s': float(
                    self.base_kwargs.get(
                        'total_time_s',
                        CoastalpathogenTimeMarcher.__init__.__defaults__[2]
                        if hasattr(CoastalpathogenTimeMarcher.__init__, '__defaults__')
                        else 1200.0,
                    )
                ),
            },
        )

        paths = library.save(output_dir, log_func=self._log)
        self._log(
            f"Transfer library complete: {len(all_results)} results | "
            f"CSV: {paths['csv_path'].name} | JSON: {paths['json_path'].name}"
        )

        return library
