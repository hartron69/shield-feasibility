"""
core/risk_engine.py — Operative risk classification and auto-calibration

RiskEngine encapsulates:
  - Green / Yellow / Red classification based on KPIs
  - Alarm flags (arrival and exposure)
  - Auto-calibration of peak and exposure thresholds from a baseline case

All threshold logic is identical to v1.22b.
Sprint 7+: replaced/extended by MonteCarloRiskEngine.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


class RiskEngine:
    """
    Operative risk classification with optional auto-calibration.

    Parameters mirror the RISK_USER_SETTINGS dict from scenarios.py.
    """

    def __init__(
        self,
        arrival_alarm_threshold_s: float = 900.0,
        exposure_alarm_threshold_mass_seconds: float = 80.0,
        yellow_arrival_threshold_s: float = 1200.0,
        yellow_peak_risk_concentration: float = 0.010,
        yellow_exposure_threshold_mass_seconds: float = 40.0,
        red_arrival_threshold_s: float = 600.0,
        red_peak_risk_concentration: float = 0.025,
        red_exposure_threshold_mass_seconds: float = 100.0,
        no_arrival_means_green: bool = True,
        auto_calibrate_from_first_case: bool = True,
        baseline_case_name: str = 'langs',
        baseline_peak_reference: str = 'max',
        baseline_exposure_reference: str = 'max',
        yellow_peak_factor: float = 1.50,
        red_peak_factor: float = 2.50,
        yellow_exposure_factor: float = 1.50,
        red_exposure_factor: float = 2.50,
        baseline_min_peak: float = 0.0020,
        baseline_min_exposure: float = 10.0,
    ):
        self.arrival_alarm_threshold_s = float(arrival_alarm_threshold_s)
        self.exposure_alarm_threshold_mass_seconds = float(exposure_alarm_threshold_mass_seconds)
        self.yellow_arrival_threshold_s = float(yellow_arrival_threshold_s)
        self.yellow_peak_risk_concentration = float(yellow_peak_risk_concentration)
        self.yellow_exposure_threshold_mass_seconds = float(yellow_exposure_threshold_mass_seconds)
        self.red_arrival_threshold_s = float(red_arrival_threshold_s)
        self.red_peak_risk_concentration = float(red_peak_risk_concentration)
        self.red_exposure_threshold_mass_seconds = float(red_exposure_threshold_mass_seconds)
        self.no_arrival_means_green = bool(no_arrival_means_green)
        self.auto_calibrate_from_first_case = bool(auto_calibrate_from_first_case)
        self.baseline_case_name = str(baseline_case_name)
        self.baseline_peak_reference = str(baseline_peak_reference)
        self.baseline_exposure_reference = str(baseline_exposure_reference)
        self.yellow_peak_factor = float(yellow_peak_factor)
        self.red_peak_factor = float(red_peak_factor)
        self.yellow_exposure_factor = float(yellow_exposure_factor)
        self.red_exposure_factor = float(red_exposure_factor)
        self.baseline_min_peak = float(baseline_min_peak)
        self.baseline_min_exposure = float(baseline_min_exposure)
        self._autocalibrated = False
        self._baseline_info: dict = {}
        self._thresholds_before_calibration: dict = {}

    # ── Classification ────────────────────────────────────────────────────────

    def classify(
        self,
        first_arrival_s: Optional[float],
        peak_risk_conc: float,
        total_risk_exposure: float,
    ) -> tuple[str, list[str], bool, bool]:
        """
        Return (status, reasons, arrival_alarm, exposure_alarm).

        status: 'GREEN' | 'YELLOW' | 'RED'
        reasons: list of human-readable explanation strings
        arrival_alarm / exposure_alarm: bool flags
        """
        reasons: list[str] = []
        no_arrival = first_arrival_s is None or (
            isinstance(first_arrival_s, float) and np.isnan(first_arrival_s)
        )

        if (
            no_arrival
            and self.no_arrival_means_green
            and peak_risk_conc <= 0
            and total_risk_exposure <= 0
        ):
            return 'GREEN', ['Ingen registrert ankomst i analyseperioden.'], False, False

        arrival_alarm = (not no_arrival) and (
            first_arrival_s <= self.arrival_alarm_threshold_s
        )
        exposure_alarm = total_risk_exposure >= self.exposure_alarm_threshold_mass_seconds

        is_red = False
        if (not no_arrival) and (first_arrival_s <= self.red_arrival_threshold_s):
            is_red = True
            reasons.append(
                f'Rask ankomst: {first_arrival_s:.0f} s <= rød terskel '
                f'{self.red_arrival_threshold_s:.0f} s'
            )
        elif (not no_arrival) and (first_arrival_s <= self.yellow_arrival_threshold_s):
            reasons.append(
                f'Tidlig ankomst: {first_arrival_s:.0f} s <= gul terskel '
                f'{self.yellow_arrival_threshold_s:.0f} s'
            )

        if peak_risk_conc >= self.red_peak_risk_concentration:
            is_red = True
            reasons.append(
                f'Høy topp-konsentrasjon: {peak_risk_conc:.4f} >= rød terskel '
                f'{self.red_peak_risk_concentration:.4f}'
            )
        elif peak_risk_conc >= self.yellow_peak_risk_concentration:
            reasons.append(
                f'Moderat/høy topp-konsentrasjon: {peak_risk_conc:.4f} >= gul terskel '
                f'{self.yellow_peak_risk_concentration:.4f}'
            )

        if total_risk_exposure >= self.red_exposure_threshold_mass_seconds:
            is_red = True
            reasons.append(
                f'Høy total eksponering: {total_risk_exposure:.2f} >= rød terskel '
                f'{self.red_exposure_threshold_mass_seconds:.2f}'
            )
        elif total_risk_exposure >= self.yellow_exposure_threshold_mass_seconds:
            reasons.append(
                f'Økt total eksponering: {total_risk_exposure:.2f} >= gul terskel '
                f'{self.yellow_exposure_threshold_mass_seconds:.2f}'
            )

        if is_red:
            status = 'RED'
        elif reasons:
            status = 'YELLOW'
        else:
            status = 'GREEN'
            reasons.append('Alle operative terskler ligger under gule alarmgrenser.')

        return status, reasons, arrival_alarm, exposure_alarm

    def recommended_action(self, status: str) -> str:
        actions = {
            'GREEN': 'Fortsett normal overvåking og rutinemessig prøvetaking.',
            'YELLOW': 'Øk prøvetaking og følg utviklingen tett. Vurder driftsjusteringer og ekstra varsling.',
            'RED': 'Utløs alarm, varsle drift umiddelbart og vurder strakstiltak for å redusere eksponering.',
        }
        return actions.get(status.upper(), 'Ingen anbefalt handling definert.')

    # ── Auto-calibration ──────────────────────────────────────────────────────

    def _derive_baseline_value(
        self, values: pd.Series, mode: str, minimum: float
    ) -> float:
        vals = (
            pd.to_numeric(values, errors='coerce')
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
        )
        if vals.empty:
            return float(minimum)
        return float(max(minimum, vals.mean() if mode == 'mean' else vals.max()))

    def calibrate(
        self,
        baseline_summary: pd.DataFrame,
        baseline_case_name: Optional[str] = None,
        log_func=None,
    ) -> None:
        """Update peak and exposure thresholds from a baseline case summary."""
        if not self.auto_calibrate_from_first_case or baseline_summary is None or baseline_summary.empty:
            return

        case_name = baseline_case_name or self.baseline_case_name
        old = {
            'yellow_peak_risk_concentration': self.yellow_peak_risk_concentration,
            'red_peak_risk_concentration': self.red_peak_risk_concentration,
            'yellow_exposure_threshold_mass_seconds': self.yellow_exposure_threshold_mass_seconds,
            'red_exposure_threshold_mass_seconds': self.red_exposure_threshold_mass_seconds,
            'exposure_alarm_threshold_mass_seconds': self.exposure_alarm_threshold_mass_seconds,
        }
        self._thresholds_before_calibration = old

        peak_baseline = self._derive_baseline_value(
            baseline_summary['peak_relative_risk_concentration'],
            self.baseline_peak_reference,
            self.baseline_min_peak,
        )
        exposure_baseline = self._derive_baseline_value(
            baseline_summary['total_risk_exposure_mass_seconds'],
            self.baseline_exposure_reference,
            self.baseline_min_exposure,
        )

        self.yellow_peak_risk_concentration = peak_baseline * self.yellow_peak_factor
        self.red_peak_risk_concentration = peak_baseline * self.red_peak_factor
        self.yellow_exposure_threshold_mass_seconds = (
            exposure_baseline * self.yellow_exposure_factor
        )
        self.red_exposure_threshold_mass_seconds = (
            exposure_baseline * self.red_exposure_factor
        )
        self.exposure_alarm_threshold_mass_seconds = self.red_exposure_threshold_mass_seconds
        self._autocalibrated = True
        self._baseline_info = {
            'baseline_case_name': case_name,
            'peak_baseline': peak_baseline,
            'exposure_baseline': exposure_baseline,
            'baseline_peak_reference': self.baseline_peak_reference,
            'baseline_exposure_reference': self.baseline_exposure_reference,
            'yellow_peak_factor': self.yellow_peak_factor,
            'red_peak_factor': self.red_peak_factor,
            'yellow_exposure_factor': self.yellow_exposure_factor,
            'red_exposure_factor': self.red_exposure_factor,
            'yellow_peak_risk_concentration': self.yellow_peak_risk_concentration,
            'red_peak_risk_concentration': self.red_peak_risk_concentration,
            'yellow_exposure_threshold_mass_seconds': self.yellow_exposure_threshold_mass_seconds,
            'red_exposure_threshold_mass_seconds': self.red_exposure_threshold_mass_seconds,
            'exposure_alarm_threshold_mass_seconds': self.exposure_alarm_threshold_mass_seconds,
            'previous_thresholds': old,
        }
        if log_func:
            log_func(
                f"Auto-kalibrerte risikoterskler fra baseline-case '{case_name}': "
                f"peak_baseline={peak_baseline:.4f} -> yellow/red peak="
                f"{self.yellow_peak_risk_concentration:.4f}/"
                f"{self.red_peak_risk_concentration:.4f}, "
                f"exposure_baseline={exposure_baseline:.2f} -> yellow/red exposure="
                f"{self.yellow_exposure_threshold_mass_seconds:.2f}/"
                f"{self.red_exposure_threshold_mass_seconds:.2f}"
            )
            self._log_calibration_summary(log_func)

    def _log_calibration_summary(self, log_func) -> None:
        if not self._autocalibrated or not self._baseline_info:
            return
        old = self._thresholds_before_calibration
        info = self._baseline_info
        log_func("Risikokalibrering – baseline og terskeloppdatering:")
        log_func(
            f"  Baseline-case: {info.get('baseline_case_name')} | "
            f"peak baseline={float(info.get('peak_baseline', 0)):.4f} "
            f"({info.get('baseline_peak_reference')}) | "
            f"exposure baseline={float(info.get('exposure_baseline', 0)):.2f} "
            f"({info.get('baseline_exposure_reference')})"
        )
        log_func(
            f"  Peak terskler: gul {old.get('yellow_peak_risk_concentration', float('nan')):.4f} "
            f"-> {self.yellow_peak_risk_concentration:.4f} | "
            f"rød {old.get('red_peak_risk_concentration', float('nan')):.4f} "
            f"-> {self.red_peak_risk_concentration:.4f}"
        )
        log_func(
            f"  Exposure terskler: gul "
            f"{old.get('yellow_exposure_threshold_mass_seconds', float('nan')):.2f} "
            f"-> {self.yellow_exposure_threshold_mass_seconds:.2f} | "
            f"rød {old.get('red_exposure_threshold_mass_seconds', float('nan')):.2f} "
            f"-> {self.red_exposure_threshold_mass_seconds:.2f} | "
            f"alarm {old.get('exposure_alarm_threshold_mass_seconds', float('nan')):.2f} "
            f"-> {self.exposure_alarm_threshold_mass_seconds:.2f}"
        )
        log_func(
            f"  Faktorer: peak gul/rød = {self.yellow_peak_factor:.2f}/{self.red_peak_factor:.2f} | "
            f"exposure gul/rød = {self.yellow_exposure_factor:.2f}/{self.red_exposure_factor:.2f}"
        )

    def thresholds_dict(self) -> dict:
        """Return current threshold values as a plain dict (for metadata/JSON)."""
        return {
            'arrival_alarm_threshold_s': self.arrival_alarm_threshold_s,
            'exposure_alarm_threshold_mass_seconds': self.exposure_alarm_threshold_mass_seconds,
            'yellow_arrival_threshold_s': self.yellow_arrival_threshold_s,
            'yellow_peak_risk_concentration': self.yellow_peak_risk_concentration,
            'yellow_exposure_threshold_mass_seconds': self.yellow_exposure_threshold_mass_seconds,
            'red_arrival_threshold_s': self.red_arrival_threshold_s,
            'red_peak_risk_concentration': self.red_peak_risk_concentration,
            'red_exposure_threshold_mass_seconds': self.red_exposure_threshold_mass_seconds,
            'no_arrival_means_green': self.no_arrival_means_green,
            'auto_calibrate_from_first_case': self.auto_calibrate_from_first_case,
            'baseline_case_name': self.baseline_case_name,
            'baseline_peak_reference': self.baseline_peak_reference,
            'baseline_exposure_reference': self.baseline_exposure_reference,
            'yellow_peak_factor': self.yellow_peak_factor,
            'red_peak_factor': self.red_peak_factor,
            'yellow_exposure_factor': self.yellow_exposure_factor,
            'red_exposure_factor': self.red_exposure_factor,
            'baseline_min_peak': self.baseline_min_peak,
            'baseline_min_exposure': self.baseline_min_exposure,
        }

    # ── Convenience: reclassify a summary DataFrame ───────────────────────────

    def reclassify_summary_df(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        """Re-run classify() on every row in summary_df with current thresholds."""
        from core.io_utils import standardize_summary_df
        summary_df = standardize_summary_df(summary_df).copy()
        if summary_df.empty:
            return summary_df
        new_rows = []
        for _, row in summary_df.iterrows():
            first_arrival_s = row.get('first_arrival_s', np.nan)
            if pd.isna(first_arrival_s):
                first_arrival_s = None
            peak_risk_conc = float(row.get('peak_relative_risk_concentration', 0.0) or 0.0)
            total_risk_exposure = float(row.get('total_risk_exposure_mass_seconds', 0.0) or 0.0)
            status, reasons, arrival_alarm, exposure_alarm = self.classify(
                first_arrival_s, peak_risk_conc, total_risk_exposure
            )
            row = row.copy()
            row['risk_status'] = status
            row['risk_reasons'] = '; '.join(reasons)
            row['arrival_alarm'] = bool(arrival_alarm)
            row['exposure_alarm'] = bool(exposure_alarm)
            row['operational_alarm'] = bool(arrival_alarm or exposure_alarm or status == 'RED')
            row['recommended_action'] = self.recommended_action(status)
            new_rows.append(row)
        return pd.DataFrame(new_rows)
