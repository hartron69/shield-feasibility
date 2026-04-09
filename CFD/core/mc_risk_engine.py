"""
core/mc_risk_engine.py — Sprint 7: Monte-Carlo risk engine

Draws N samples from MCTransferLibrary distributions, classifies each
sample with the RiskEngine thresholds, and aggregates the results into
risk-probability summaries.

Usage
-----
    from core.transfer_library import MCTransferLibrary
    from core.mc_risk_engine import MonteCarloRiskEngine

    mc_lib = MCTransferLibrary.load(output_dir)
    engine = MonteCarloRiskEngine(mc_lib, n_samples=10_000)
    results = engine.run_all()

    print(engine.risk_probability_matrix('RED', results))
    engine.summary_df(results).to_csv('mc_risk_summary.csv', index=False)

Dose scaling
------------
    exposure_ms  = TC_sample      * shed_rate * total_time_s   [mass·s]
    peak_conc    = PMF_sample     * shed_rate * total_time_s
                   / target_net_plan_area_m2                   [mass/m²]
    arrival_s    = arrival_sample (raw seconds)                [s]

These map directly to the three KPIs used by RiskEngine.classify().
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.risk_engine import RiskEngine
from core.transfer_library import MCTransferLibrary, TransferDistribution


# ── Result record ─────────────────────────────────────────────────────────────

@dataclass
class MCRiskResult:
    """
    Monte Carlo risk result for one (source_site, target_site, case) pair.

    All probability fields are in [0, 1] and sum to 1.0.
    """
    source_site_id: str
    target_site_id: str
    case_name: str
    n_samples: int
    # Status probabilities
    p_green: float
    p_yellow: float
    p_red: float
    # Derived status summary
    modal_risk_status: str      # status with highest probability
    expected_risk_score: float  # E[GREEN=0, YELLOW=1, RED=2]
    # Transfer coefficient statistics
    mean_tc_s: float
    p10_tc_s: float
    p50_tc_s: float
    p90_tc_s: float
    # Exposure statistics [mass·s]
    mean_exposure_ms: float
    var95_exposure_ms: float
    var99_exposure_ms: float
    # Arrival statistics [s]; NaN when no arrival in majority of samples
    mean_first_arrival_s: float
    p_no_arrival: float         # fraction of samples with no pathogen arrival
    p90_first_arrival_s: float  # 90th percentile of finite arrival times

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, float) and math.isnan(v):
                d[k] = None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'MCRiskResult':
        d = dict(d)
        float_fields = {
            'p_green', 'p_yellow', 'p_red', 'expected_risk_score',
            'mean_tc_s', 'p10_tc_s', 'p50_tc_s', 'p90_tc_s',
            'mean_exposure_ms', 'var95_exposure_ms', 'var99_exposure_ms',
            'mean_first_arrival_s', 'p_no_arrival', 'p90_first_arrival_s',
        }
        for k in float_fields:
            if k in d:
                d[k] = float('nan') if d[k] is None else float(d[k])
        return cls(**d)


# ── Vectorised classifier ─────────────────────────────────────────────────────

def _classify_vectorised(
    arrival_s: np.ndarray,      # NaN = no arrival; shape (N,)
    peak_conc: np.ndarray,      # [mass/m²]; shape (N,)
    exposure_ms: np.ndarray,    # [mass·s]; shape (N,)
    risk: RiskEngine,
    no_arrival_means_green: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Vectorised risk classification for N Monte Carlo samples.

    Returns (is_green, is_yellow, is_red) boolean arrays of shape (N,).
    """
    no_arrival = np.isnan(arrival_s)

    # Shortcut: no arrival + zero exposure + zero peak = GREEN
    all_green_mask = (
        no_arrival
        & (peak_conc <= 0.0)
        & (exposure_ms <= 0.0)
        & no_arrival_means_green
    )

    # RED criteria (any one triggers RED)
    red_arr = ~no_arrival & (arrival_s <= risk.red_arrival_threshold_s)
    red_peak = peak_conc >= risk.red_peak_risk_concentration
    red_exp = exposure_ms >= risk.red_exposure_threshold_mass_seconds
    is_red = (red_arr | red_peak | red_exp) & ~all_green_mask

    # YELLOW criteria (any one, but not RED)
    yel_arr = ~no_arrival & (arrival_s <= risk.yellow_arrival_threshold_s) & ~red_arr
    yel_peak = (peak_conc >= risk.yellow_peak_risk_concentration) & ~red_peak
    yel_exp = (exposure_ms >= risk.yellow_exposure_threshold_mass_seconds) & ~red_exp
    is_yellow = (yel_arr | yel_peak | yel_exp) & ~is_red & ~all_green_mask

    is_green = ~is_red & ~is_yellow

    return is_green, is_yellow, is_red


# ── Engine ────────────────────────────────────────────────────────────────────

class MonteCarloRiskEngine:
    """
    Probabilistic risk engine built on top of MCTransferLibrary.

    Parameters
    ----------
    mc_library              : fitted MCTransferLibrary (Sprint 6)
    risk_engine             : RiskEngine instance carrying threshold values.
                              Pass None to use RiskEngine defaults.
    n_samples               : MC sample count per pair (default 10 000)
    shed_rate               : source shedding rate multiplier [relative mass/s]
                              (1.0 = same rate used to build the library)
    total_time_s            : simulation duration for exposure scaling [s]
    species_infectivity_factor : applied to exposure_ms before classifying
    seed                    : random seed
    """

    VERSION = 'v1.23-sprint7'

    def __init__(
        self,
        mc_library: MCTransferLibrary,
        risk_engine: Optional[RiskEngine] = None,
        n_samples: int = 10_000,
        shed_rate: float = 1.0,
        total_time_s: float = 1200.0,
        species_infectivity_factor: float = 1.0,
        seed: int = 42,
    ):
        self.lib = mc_library
        self.risk = risk_engine if risk_engine is not None else RiskEngine()
        self.n_samples = int(n_samples)
        self.shed_rate = float(shed_rate)
        self.total_time_s = float(total_time_s)
        self.species_infectivity_factor = float(species_infectivity_factor)
        self.rng = np.random.default_rng(int(seed))

    # ── Single pair ───────────────────────────────────────────────────────────

    def run_pair(
        self,
        source_id: str,
        target_id: str,
        case_name: Optional[str] = None,
    ) -> MCRiskResult:
        """
        Run MC risk classification for one (source, target, [case]) pair.

        If case_name is None the first available case in the library is used.
        """
        # Resolve case_name
        if case_name is None:
            case_name = (
                self.lib._case_names[0] if self.lib._case_names else 'unknown'
            )

        # ── Sample TC ──
        tc_samples = self.lib.sample_tc(
            source_id, target_id, self.n_samples, self.rng, case_name
        )
        exposure_ms = (
            tc_samples * self.shed_rate * self.total_time_s
            * self.species_infectivity_factor
        )

        # ── Sample peak concentration ──
        pmf_dist = self.lib._get_dist(
            source_id, target_id, 'peak_mass_fraction', case_name
        )
        pmf_samples = self.lib.sample_peak(
            source_id, target_id, self.n_samples, self.rng, case_name
        )
        net_area = (
            pmf_dist.target_net_plan_area_m2
            if pmf_dist is not None and pmf_dist.target_net_plan_area_m2 > 0
            else 1.0
        )
        peak_conc = (
            pmf_samples * self.shed_rate * self.total_time_s
            * self.species_infectivity_factor
            / net_area
        )

        # ── Sample first arrival ──
        arrival_s = self.lib.sample_arrival(
            source_id, target_id, self.n_samples, self.rng, case_name
        )

        # ── Classify ──
        is_green, is_yellow, is_red = _classify_vectorised(
            arrival_s, peak_conc, exposure_ms, self.risk,
            no_arrival_means_green=self.risk.no_arrival_means_green,
        )

        p_green = float(is_green.mean())
        p_yellow = float(is_yellow.mean())
        p_red = float(is_red.mean())

        # Modal status
        scores = {p_green: 'GREEN', p_yellow: 'YELLOW', p_red: 'RED'}
        modal = scores[max(scores)]
        expected_score = float(0.0 * p_green + 1.0 * p_yellow + 2.0 * p_red)

        # TC statistics (over all samples including zeros)
        mean_tc = float(np.mean(tc_samples))
        p10_tc = float(np.percentile(tc_samples, 10))
        p50_tc = float(np.percentile(tc_samples, 50))
        p90_tc = float(np.percentile(tc_samples, 90))

        # Exposure statistics
        mean_exp = float(np.mean(exposure_ms))
        var95 = float(np.percentile(exposure_ms, 95))
        var99 = float(np.percentile(exposure_ms, 99))

        # Arrival statistics
        finite_arr = arrival_s[np.isfinite(arrival_s)]
        p_no_arrival = float(np.isnan(arrival_s).mean())
        mean_arr = float(np.mean(finite_arr)) if len(finite_arr) > 0 else float('nan')
        p90_arr = float(np.percentile(finite_arr, 90)) if len(finite_arr) > 0 else float('nan')

        return MCRiskResult(
            source_site_id=source_id,
            target_site_id=target_id,
            case_name=case_name,
            n_samples=self.n_samples,
            p_green=p_green,
            p_yellow=p_yellow,
            p_red=p_red,
            modal_risk_status=modal,
            expected_risk_score=expected_score,
            mean_tc_s=mean_tc,
            p10_tc_s=p10_tc,
            p50_tc_s=p50_tc,
            p90_tc_s=p90_tc,
            mean_exposure_ms=mean_exp,
            var95_exposure_ms=var95,
            var99_exposure_ms=var99,
            mean_first_arrival_s=mean_arr,
            p_no_arrival=p_no_arrival,
            p90_first_arrival_s=p90_arr,
        )

    # ── All pairs ─────────────────────────────────────────────────────────────

    def run_all(
        self,
        case_name: Optional[str] = None,
    ) -> List[MCRiskResult]:
        """
        Run MC for all (source, target) pairs in the library.

        Parameters
        ----------
        case_name : if None, use first available case

        Returns
        -------
        List[MCRiskResult], one per (source, target) pair
        """
        results: List[MCRiskResult] = []
        for src in self.lib._source_ids:
            for tgt in self.lib._target_ids:
                results.append(self.run_pair(src, tgt, case_name))
        return results

    # ── Summary views ─────────────────────────────────────────────────────────

    def summary_df(
        self, results: Optional[List[MCRiskResult]] = None
    ) -> pd.DataFrame:
        """Flat DataFrame with all result fields."""
        if results is None:
            results = self.run_all()
        if not results:
            return pd.DataFrame()
        return pd.DataFrame([r.to_dict() for r in results])

    def risk_probability_matrix(
        self,
        status: str = 'RED',
        results: Optional[List[MCRiskResult]] = None,
    ) -> pd.DataFrame:
        """
        Pivot: source_site_id x target_site_id -> P(status).

        status: 'RED' | 'YELLOW' | 'GREEN'
        """
        if results is None:
            results = self.run_all()
        col = f'p_{status.lower()}'
        rows = [
            {
                'source_site_id': r.source_site_id,
                'target_site_id': r.target_site_id,
                col: getattr(r, col, float('nan')),
            }
            for r in results
        ]
        if not rows:
            return pd.DataFrame()
        pivot = (
            pd.DataFrame(rows)
            .pivot(index='source_site_id', columns='target_site_id', values=col)
        )
        pivot.columns.name = None
        pivot.index.name = 'source_site_id'
        return pivot

    def modal_risk_matrix(
        self, results: Optional[List[MCRiskResult]] = None
    ) -> pd.DataFrame:
        """Pivot: source x target -> modal risk status."""
        if results is None:
            results = self.run_all()
        rows = [
            {
                'source_site_id': r.source_site_id,
                'target_site_id': r.target_site_id,
                'modal_risk_status': r.modal_risk_status,
            }
            for r in results
        ]
        if not rows:
            return pd.DataFrame()
        pivot = (
            pd.DataFrame(rows)
            .pivot(index='source_site_id', columns='target_site_id',
                   values='modal_risk_status')
        )
        pivot.columns.name = None
        pivot.index.name = 'source_site_id'
        return pivot

    def expected_risk_score_matrix(
        self, results: Optional[List[MCRiskResult]] = None
    ) -> pd.DataFrame:
        """Pivot: source x target -> E[risk_score] (0=G, 1=Y, 2=R)."""
        if results is None:
            results = self.run_all()
        rows = [
            {
                'source_site_id': r.source_site_id,
                'target_site_id': r.target_site_id,
                'expected_risk_score': r.expected_risk_score,
            }
            for r in results
        ]
        if not rows:
            return pd.DataFrame()
        pivot = (
            pd.DataFrame(rows)
            .pivot(index='source_site_id', columns='target_site_id',
                   values='expected_risk_score')
        )
        pivot.columns.name = None
        pivot.index.name = 'source_site_id'
        return pivot

    # ── IO ────────────────────────────────────────────────────────────────────

    def save_results(
        self,
        results: List[MCRiskResult],
        output_dir: Path,
        log_func=None,
    ) -> dict:
        """
        Save MC risk results to output_dir.

        Writes:
          mc_risk_results.csv          — flat table
          mc_risk_results.json         — full payload with pivot matrices
        """
        _log = log_func or (lambda m: None)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_path = output_dir / 'mc_risk_results.csv'
        json_path = output_dir / 'mc_risk_results.json'

        df = self.summary_df(results)
        if not df.empty:
            df.to_csv(csv_path, index=False)
            _log(f"MC risk results saved: {csv_path}")

        p_red_mat = self.risk_probability_matrix('RED', results)
        p_yel_mat = self.risk_probability_matrix('YELLOW', results)
        modal_mat = self.modal_risk_matrix(results)
        score_mat = self.expected_risk_score_matrix(results)

        payload = {
            'version': self.VERSION,
            'n_samples': self.n_samples,
            'shed_rate': self.shed_rate,
            'total_time_s': self.total_time_s,
            'species_infectivity_factor': self.species_infectivity_factor,
            'risk_thresholds': self.risk.thresholds_dict(),
            'n_results': len(results),
            'results': [r.to_dict() for r in results],
            'p_red_matrix': p_red_mat.to_dict() if not p_red_mat.empty else {},
            'p_yellow_matrix': p_yel_mat.to_dict() if not p_yel_mat.empty else {},
            'modal_risk_matrix': modal_mat.to_dict() if not modal_mat.empty else {},
            'expected_risk_score_matrix': (
                score_mat.to_dict() if not score_mat.empty else {}
            ),
        }
        with open(json_path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        _log(f"MC risk results JSON saved: {json_path}")

        return {'csv_path': csv_path, 'json_path': json_path}
