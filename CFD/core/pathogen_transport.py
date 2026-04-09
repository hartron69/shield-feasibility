"""
core/pathogen_transport.py — Pathogen particle transport time-marcher

Contains:
  PathogenParticle (= pathogenParticle in v1.22b, alias kept)
  CoastalpathogenTimeMarcher — orchestrates particle release, advection,
      diffusion, biology, exposure accounting, and output.

Physics are identical to v1.22b.
Risk classification is delegated to RiskEngine.
Rendering is delegated to Reporter.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.flow_engine import CoastalThreeNetFlowModel
from core.forcing import CurrentForcing
from core.geometry import Net, PolylineCoastline
from core.io_utils import save_csv, save_json, standardize_summary_df
from core.reporting import Reporter
from core.risk_engine import RiskEngine
from core.scenarios import PATHOGEN_USER_SETTINGS, RISK_USER_SETTINGS, RUN_USER_SETTINGS


# ── Particle ──────────────────────────────────────────────────────────────────

@dataclass
class PathogenParticle:
    """Single Lagrangian pathogen particle."""
    x: float
    y: float
    mass: float
    birth_time_s: float
    infectivity: float = 1.0
    alive: bool = True
    entered_once: Dict[str, bool] = field(default_factory=dict)
    exposure_s: Dict[str, float] = field(default_factory=dict)


# Legacy alias for v1.22b compatibility
pathogenParticle = PathogenParticle


# ── Time-marcher ──────────────────────────────────────────────────────────────

class CoastalpathogenTimeMarcher:
    """
    Time-marching pathogen transport model for local screening around fish-farm
    nets near a straight coastline.

    Delegates:
      risk classification  → RiskEngine (core/risk_engine.py)
      figure rendering     → Reporter  (core/reporting.py)
    """

    VERSION = 'v1.23'

    def __init__(
        self,
        flow_model: CoastalThreeNetFlowModel,
        # --- forcing (Sprint 4) ---
        current_forcing: Optional[CurrentForcing] = None,
        # --- transport ---
        dt_s: float = 10.0,
        total_time_s: float = 1200.0,
        particles_per_step: int = 9,
        pathogen_name: str = 'Generic pathogen',
        source_mode: str = 'upstream_line',
        source_net_name: Optional[str] = 'Net 1',
        source_load: float = 1.0,
        shedding_rate_relative_per_s: float = 1.0,
        source_patch_radius_fraction: float = 0.35,
        source_infectivity: float = 1.0,
        diffusion_m2_s: float = 0.12,
        # --- biology ---
        biology_enabled: bool = True,
        base_inactivation_rate_1_s: float = 5.0e-4,
        temperature_c: float = 10.0,
        reference_temperature_c: float = 10.0,
        q10_inactivation: float = 1.5,
        uv_inactivation_factor: float = 1.0,
        species_infectivity_factor: float = 1.0,
        vertical_preference_mode: str = 'none',
        minimum_infectivity: float = 1.0e-3,
        # --- risk thresholds (forwarded to RiskEngine) ---
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
        # --- misc ---
        random_seed: int = 42,
        verbose: bool = True,
        progress_every_pct: float = 10.0,
    ):
        # Validation (same as v1.22b)
        if dt_s <= 0:
            raise ValueError('dt_s må være > 0 sekunder.')
        if total_time_s <= 0:
            raise ValueError('total_time_s må være > 0 sekunder.')
        if particles_per_step < 1:
            raise ValueError('particles_per_step må være minst 1.')
        if source_mode not in {'upstream_line', 'infected_net'}:
            raise ValueError("source_mode må være 'upstream_line' eller 'infected_net'.")
        if source_load < 0:
            raise ValueError('source_load kan ikke være negativ.')
        if not (0.0 < source_patch_radius_fraction <= 1.0):
            raise ValueError('source_patch_radius_fraction må ligge i (0, 1].')
        if not (0.0 <= source_infectivity <= 1.0):
            raise ValueError('source_infectivity må ligge i [0, 1].')
        if diffusion_m2_s < 0:
            raise ValueError('diffusion_m2_s kan ikke være negativ.')
        if q10_inactivation <= 0:
            raise ValueError('q10_inactivation må være > 0.')
        if not (0.0 <= minimum_infectivity <= 1.0):
            raise ValueError('minimum_infectivity må ligge i [0, 1].')
        if red_arrival_threshold_s > yellow_arrival_threshold_s:
            raise ValueError('red_arrival_threshold_s bør være <= yellow_arrival_threshold_s.')
        if red_peak_risk_concentration < yellow_peak_risk_concentration:
            raise ValueError('red_peak_risk_concentration bør være >= yellow_peak_risk_concentration.')
        if red_exposure_threshold_mass_seconds < yellow_exposure_threshold_mass_seconds:
            raise ValueError('red_exposure_threshold_mass_seconds bør være >= yellow_exposure_threshold_mass_seconds.')
        if baseline_peak_reference not in {'max', 'mean'}:
            raise ValueError("baseline_peak_reference må være 'max' eller 'mean'.")
        if baseline_exposure_reference not in {'max', 'mean'}:
            raise ValueError("baseline_exposure_reference må være 'max' eller 'mean'.")
        if progress_every_pct <= 0:
            raise ValueError('progress_every_pct må være > 0.')

        self.flow_model = flow_model
        self.current_forcing = current_forcing  # None = named-case mode (v1.22b compat)
        self.dt_s = float(dt_s)
        self.total_time_s = float(total_time_s)
        self.particles_per_step = int(particles_per_step)
        self.pathogen_name = str(pathogen_name)
        self.source_mode = str(source_mode)
        self.source_net_name = source_net_name
        self.source_load = float(source_load)
        self.shedding_rate_relative_per_s = float(shedding_rate_relative_per_s)
        self.source_patch_radius_fraction = float(source_patch_radius_fraction)
        self.source_infectivity = float(source_infectivity)
        self.diffusion_m2_s = float(diffusion_m2_s)
        self.biology_enabled = bool(biology_enabled)
        self.base_inactivation_rate_1_s = float(base_inactivation_rate_1_s)
        self.temperature_c = float(temperature_c)
        self.reference_temperature_c = float(reference_temperature_c)
        self.q10_inactivation = float(q10_inactivation)
        self.uv_inactivation_factor = float(uv_inactivation_factor)
        self.species_infectivity_factor = float(species_infectivity_factor)
        self.vertical_preference_mode = str(vertical_preference_mode)
        self.minimum_infectivity = float(minimum_infectivity)
        self.random_seed = int(random_seed)
        self.rng = np.random.default_rng(self.random_seed)
        self.verbose = bool(verbose)
        self.progress_every_pct = float(progress_every_pct)
        self.output_dir = self.flow_model.output_dir
        self._run_start = time.perf_counter()

        # Delegate risk to RiskEngine
        self.risk = RiskEngine(
            arrival_alarm_threshold_s=arrival_alarm_threshold_s,
            exposure_alarm_threshold_mass_seconds=exposure_alarm_threshold_mass_seconds,
            yellow_arrival_threshold_s=yellow_arrival_threshold_s,
            yellow_peak_risk_concentration=yellow_peak_risk_concentration,
            yellow_exposure_threshold_mass_seconds=yellow_exposure_threshold_mass_seconds,
            red_arrival_threshold_s=red_arrival_threshold_s,
            red_peak_risk_concentration=red_peak_risk_concentration,
            red_exposure_threshold_mass_seconds=red_exposure_threshold_mass_seconds,
            no_arrival_means_green=no_arrival_means_green,
            auto_calibrate_from_first_case=auto_calibrate_from_first_case,
            baseline_case_name=baseline_case_name,
            baseline_peak_reference=baseline_peak_reference,
            baseline_exposure_reference=baseline_exposure_reference,
            yellow_peak_factor=yellow_peak_factor,
            red_peak_factor=red_peak_factor,
            yellow_exposure_factor=yellow_exposure_factor,
            red_exposure_factor=red_exposure_factor,
            baseline_min_peak=baseline_min_peak,
            baseline_min_exposure=baseline_min_exposure,
        )

        # Delegate rendering to Reporter
        self.reporter = Reporter(self.flow_model, self.output_dir, self.risk)

        # Expose thresholds directly for backward compat (read-only proxies)
        # (callers that read self.yellow_peak_risk_concentration etc. get live values)

    # ── Threshold proxies (backward compat) ───────────────────────────────────

    def __getattr__(self, name):
        # Forward threshold attribute reads to self.risk
        _RISK_ATTRS = {
            'arrival_alarm_threshold_s',
            'exposure_alarm_threshold_mass_seconds',
            'yellow_arrival_threshold_s',
            'yellow_peak_risk_concentration',
            'yellow_exposure_threshold_mass_seconds',
            'red_arrival_threshold_s',
            'red_peak_risk_concentration',
            'red_exposure_threshold_mass_seconds',
            'no_arrival_means_green',
            'auto_calibrate_from_first_case',
            'baseline_case_name',
            'yellow_peak_factor',
            'red_peak_factor',
            'yellow_exposure_factor',
            'red_exposure_factor',
        }
        if name in _RISK_ATTRS:
            return getattr(self.risk, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # ── Biology ───────────────────────────────────────────────────────────────

    def _temperature_factor(self) -> float:
        return self.q10_inactivation ** (
            (self.temperature_c - self.reference_temperature_c) / 10.0
        )

    def effective_inactivation_rate_1_s(self) -> float:
        if not self.biology_enabled:
            return 0.0
        return max(
            0.0,
            self.base_inactivation_rate_1_s
            * self._temperature_factor()
            * self.uv_inactivation_factor,
        )

    def _infectious_mass(self, p: PathogenParticle) -> float:
        return p.mass * max(0.0, min(1.0, p.infectivity))

    def _risk_mass(self, p: PathogenParticle) -> float:
        return self._infectious_mass(p) * self.species_infectivity_factor

    def _apply_biology_step(self, p: PathogenParticle) -> None:
        if not self.biology_enabled or not p.alive:
            return
        k_eff = self.effective_inactivation_rate_1_s()
        if k_eff > 0.0:
            p.infectivity *= math.exp(-k_eff * self.dt_s)
            p.infectivity = max(0.0, min(1.0, p.infectivity))
        if p.infectivity < self.minimum_infectivity:
            p.alive = False

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        if self.verbose:
            elapsed = time.perf_counter() - self._run_start
            print(f"[AquaGuard +{elapsed:7.1f}s] {message}", flush=True)

    def _log_parameter_summary(self) -> None:
        self._log('pathogen-parameteroppsett:')
        self._log(f"  dt_s={self.dt_s:.2f} s | total_time_s={self.total_time_s:.1f} s")
        self._log(f"  pathogen_name={self.pathogen_name}")
        self._log(f"  particles_per_step={self.particles_per_step} | source_mode={self.source_mode}")
        if self.source_mode == 'upstream_line':
            self._log(f"  source_load={self.source_load:.4g}")
        else:
            self._log(
                f"  source_net_name={self._resolve_source_net().name} | "
                f"shedding_rate={self.shedding_rate_relative_per_s:.4g} masse/s"
            )
        self._log(f"  diffusion_m2_s={self.diffusion_m2_s:.4g} m²/s")
        self._log(
            f"  biology_enabled={self.biology_enabled} | "
            f"base_inactivation_rate_1_s={self.base_inactivation_rate_1_s:.4g} 1/s | "
            f"effective={self.effective_inactivation_rate_1_s():.4g} 1/s"
        )
        self._log(
            f"  temperature_c={self.temperature_c:.2f} °C | "
            f"q10={self.q10_inactivation:.3f} | "
            f"uv_factor={self.uv_inactivation_factor:.3f} | "
            f"species_factor={self.species_infectivity_factor:.3f}"
        )
        self._log(
            f"  auto_calibrate={self.risk.auto_calibrate_from_first_case} | "
            f"baseline={self.risk.baseline_case_name}"
        )
        if self.current_forcing is not None:
            stats = self.current_forcing.summary_stats()
            self._log(
                f"  current_forcing: {stats['label']} | {stats['n_points']} punkter | "
                f"duration={stats['duration_s']:.0f}s | "
                f"mean_speed={stats['mean_speed_m_s']:.3f} m/s"
            )
        self._log(f"  random_seed={self.random_seed} | verbose={self.verbose}")

    def _log_operational_case_table(
        self, summary_df: pd.DataFrame, case_name: str
    ) -> None:
        summary_df = standardize_summary_df(summary_df)
        sub = summary_df[summary_df['case_name'] == case_name].copy()
        if sub.empty:
            self._log(f"Ingen summary-rader å vise for case '{case_name}'.")
            return
        self._log(f"Operativ risikotabell for case '{case_name}':")
        header = (
            f"{'Nøt':<8} {'Status':<8} {'Alarm':<7} {'Ankomst [min]':>14} "
            f"{'Peak risk conc':>16} {'Eksponering':>14}  Handling"
        )
        self._log(f"  {header}")
        self._log(f"  {'-' * len(header)}")
        for _, row in sub.iterrows():
            arrival_s = row.get('first_arrival_s', np.nan)
            arrival_txt = 'na' if pd.isna(arrival_s) else f"{float(arrival_s)/60.0:6.1f}"
            peak_txt = f"{float(row.get('peak_relative_risk_concentration', 0.0)):.4f}"
            exposure_txt = f"{float(row.get('total_risk_exposure_mass_seconds', 0.0)):.1f}"
            alarm_txt = 'YES' if bool(row.get('operational_alarm', False)) else 'NO'
            action = str(row.get('recommended_action', ''))
            self._log(
                f"  {str(row.get('net', '')):<8} {str(row.get('risk_status', '')):<8} "
                f"{alarm_txt:<7} {arrival_txt:>14} {peak_txt:>16} {exposure_txt:>14}  {action}"
            )

    # ── Forcing helpers (Sprint 4) ────────────────────────────────────────────

    def _get_case_dir(self, case_name: str, t_s: float) -> np.ndarray:
        """Return flow direction unit vector for this time step."""
        if self.current_forcing is not None:
            return self.current_forcing.direction_at(t_s)
        return self.flow_model.case_vector(case_name)

    def _set_u_inf_for_step(self, t_s: float) -> float:
        """
        When current_forcing is set, update flow_model.U_inf from the forcing
        speed and return the original value so it can be restored afterwards.
        """
        original = self.flow_model.U_inf
        if self.current_forcing is not None:
            spd = self.current_forcing.speed_at(t_s)
            self.flow_model.U_inf = spd if spd > 1e-12 else 1e-12
        return original

    # ── Source placement ──────────────────────────────────────────────────────

    def _resolve_source_net(self) -> Net:
        if self.source_net_name is None:
            return self.flow_model.nets[0]
        for net in self.flow_model.nets:
            if net.name == self.source_net_name:
                return net
        raise ValueError(
            f"Fant ikke source_net_name={self.source_net_name!r} blant "
            f"{[n.name for n in self.flow_model.nets]}"
        )

    def _inlet_line(
        self, case_dir: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute upstream inlet line for regional source (always on open-sea side)."""
        e = self.flow_model._unit(case_dir)
        coast = self.flow_model.coast
        coast_normal = (
            coast.dominant_seaward_normal()
            if isinstance(coast, PolylineCoastline)
            else np.array([0.0, 1.0])
        )
        flipped_for_open_sea = False
        if float(np.dot(e, coast_normal)) > 0.0:
            e = -e
            flipped_for_open_sea = True
        ep = np.array([-e[1], e[0]])
        corners = np.array([
            [self.flow_model.domain['x'][0], self.flow_model.domain['y'][0]],
            [self.flow_model.domain['x'][0], self.flow_model.domain['y'][1]],
            [self.flow_model.domain['x'][1], self.flow_model.domain['y'][0]],
            [self.flow_model.domain['x'][1], self.flow_model.domain['y'][1]],
        ])
        s_vals = corners @ e
        eta_vals = corners @ ep
        s_min = float(np.min(s_vals)) - 15.0
        eta_min = float(np.min(eta_vals)) + 15.0
        eta_max = float(np.max(eta_vals)) - 15.0
        origin = s_min * e
        if self.verbose:
            y_source = float(origin[1])
            boundary_label = (
                'åpen sjø-side'
                if y_source > self.flow_model.coast.y_coast + 20.0
                else 'kystsiden/nær land'
            )
            msg = f"Regional kilde legges på {boundary_label}: origin=({origin[0]:.1f}, {origin[1]:.1f}) m"
            if flipped_for_open_sea:
                msg += ' | case_dir ble snudd for å sikre åpen rand.'
            self._log(msg)
        return origin, ep, np.array([eta_min, eta_max])

    def _spawn_particles(
        self,
        particles: List[PathogenParticle],
        current_t: float,
        case_name: str,
    ) -> int:
        added = 0
        if self.source_mode == 'upstream_line':
            case_dir = self._get_case_dir(case_name, current_t)
            origin, ep, eta_range = self._inlet_line(case_dir)
            width = eta_range[1] - eta_range[0]
            if self.particles_per_step <= 1:
                etas = np.array([(eta_range[0] + eta_range[1]) / 2.0])
            else:
                etas = np.linspace(eta_range[0], eta_range[1], self.particles_per_step)
                etas = np.unique(np.concatenate([etas, np.array([0.0])]))
            mass_per_particle = self.source_load * width / max(len(etas), 1)
            for eta in etas:
                p = origin + eta * ep
                px, py = self.flow_model._clamp_point_offshore(float(p[0]), float(p[1]))
                p = np.array([px, py])
                particles.append(
                    PathogenParticle(
                        x=float(p[0]), y=float(p[1]),
                        mass=float(mass_per_particle),
                        birth_time_s=float(current_t),
                        infectivity=float(self.source_infectivity),
                        entered_once={net.name: False for net in self.flow_model.nets},
                        exposure_s={net.name: 0.0 for net in self.flow_model.nets},
                    )
                )
                added += 1
            return added

        # infected_net mode
        source_net = self._resolve_source_net()
        patch_radius = max(0.5, self.source_patch_radius_fraction * source_net.radius)
        total_mass = self.shedding_rate_relative_per_s * self.dt_s
        mass_per_particle = total_mass / max(self.particles_per_step, 1)
        for i in range(self.particles_per_step):
            if i == 0:
                r, theta = 0.0, 0.0
            else:
                r = patch_radius * np.sqrt(self.rng.uniform(0.0, 1.0))
                theta = self.rng.uniform(0.0, 2.0 * np.pi)
            x = source_net.center[0] + r * np.cos(theta)
            y = source_net.center[1] + r * np.sin(theta)
            x, y = self.flow_model._clamp_point_offshore(x, y)
            particles.append(
                PathogenParticle(
                    x=float(x), y=float(y),
                    mass=float(mass_per_particle),
                    birth_time_s=float(current_t),
                    infectivity=float(self.source_infectivity),
                    entered_once={net.name: False for net in self.flow_model.nets},
                    exposure_s={net.name: 0.0 for net in self.flow_model.nets},
                )
            )
            added += 1
        return added

    # ── Domain / coast helpers ────────────────────────────────────────────────

    def _inside_domain(self, x: float, y: float) -> bool:
        x_min, x_max = self.flow_model.domain['x']
        y_min, y_max = self.flow_model.domain['y']
        pad = 60.0
        return (x_min - pad <= x <= x_max + pad) and (y_min - 1.0 <= y <= y_max + pad)

    def _reflect_off_coast(self, p: PathogenParticle) -> None:
        coast = self.flow_model.coast
        if isinstance(coast, PolylineCoastline):
            if coast.is_on_land(p.x, p.y):
                p.x, p.y = coast.reflect_particle(p.x, p.y)
                # Safety: if reflection itself landed on land, push to foot + 2 m offshore
                if coast.is_on_land(p.x, p.y):
                    _, foot, _ = coast._nearest_segment_and_foot(p.x, p.y)
                    n = coast.local_normal_seaward(p.x, p.y)
                    p.x = float(foot[0] + 2.0 * n[0])
                    p.y = float(foot[1] + 2.0 * n[1])
        else:
            y0 = coast.y_coast
            if p.y < y0:
                p.y = 2.0 * y0 - p.y

    def _crossed_into_impermeable_net(
        self, x_old: float, y_old: float, x_new: float, y_new: float
    ) -> Optional[Net]:
        for net in self.flow_model.nets:
            if not net.is_impermeable:
                continue
            was_inside = self.flow_model._point_inside_net(x_old, y_old, net)
            is_inside = self.flow_model._point_inside_net(x_new, y_new, net)
            if (not was_inside) and is_inside:
                return net
        return None

    def _push_outside_impermeable_net(
        self,
        x_old: float, y_old: float,
        x_new: float, y_new: float,
        net: Net,
    ) -> Tuple[float, float]:
        cx, cy = net.center
        if not self.flow_model._point_inside_net(x_old, y_old, net):
            base_x, base_y = x_old, y_old
        else:
            base_x, base_y = x_new, y_new
        dx = base_x - cx
        dy = base_y - cy
        r = math.hypot(dx, dy)
        if r < 1e-12:
            dx, dy, r = 1.0, 0.0, 1.0
        ux, uy = dx / r, dy / r
        eps = max(0.05, 1.0e-3 * net.radius)
        return cx + (net.radius + eps) * ux, cy + (net.radius + eps) * uy

    # ── Main time-stepping loop ───────────────────────────────────────────────

    def run_case(self, case_name: str) -> dict:
        case_start = time.perf_counter()
        particles: List[PathogenParticle] = []
        times = np.arange(0.0, self.total_time_s + self.dt_s, self.dt_s)
        total_steps = len(times)

        first_arrival_s: Dict[str, Optional[float]] = {
            net.name: None for net in self.flow_model.nets
        }
        concentration_ts: Dict[str, list] = {net.name: [] for net in self.flow_model.nets}
        risk_concentration_ts: Dict[str, list] = {net.name: [] for net in self.flow_model.nets}
        inside_count_ts: Dict[str, list] = {net.name: [] for net in self.flow_model.nets}
        mean_infectivity_ts: Dict[str, list] = {net.name: [] for net in self.flow_model.nets}
        total_exposure_particle_seconds: Dict[str, float] = {
            net.name: 0.0 for net in self.flow_model.nets
        }
        total_risk_exposure_mass_seconds: Dict[str, float] = {
            net.name: 0.0 for net in self.flow_model.nets
        }
        snapshots: dict = {}
        snapshot_times = [0, 200, 400, 600, 800, 1000, 1200]
        snapshot_indices = {int(round(t / self.dt_s)) for t in snapshot_times}
        last_announced_pct = -1.0

        self._log(
            f"Starter case '{case_name}' med {total_steps} tidssteg, "
            f"dt={self.dt_s:.1f} s, particles_per_step={self.particles_per_step}, "
            f"k_eff={self.effective_inactivation_rate_1_s():.4g} 1/s."
        )

        _orig_u_inf = self.flow_model.U_inf  # restored after run_case

        for it, t in enumerate(times):
            # Sprint 4: set U_inf from forcing speed (no-op when current_forcing is None)
            self._set_u_inf_for_step(t)
            case_dir = self._get_case_dir(case_name, t)

            spawned_now = self._spawn_particles(particles, t, case_name)
            alive_before = sum(1 for p in particles if p.alive)

            for p in particles:
                if not p.alive:
                    continue
                x_old, y_old = p.x, p.y
                v = self.flow_model.velocity_at_point_time(p.x, p.y, t, case_dir)

                if self.diffusion_m2_s > 0.0:
                    sigma = math.sqrt(2.0 * self.diffusion_m2_s * self.dt_s)
                    dx_diff, dy_diff = self.rng.normal(0.0, sigma, size=2)
                else:
                    dx_diff, dy_diff = 0.0, 0.0

                x_new = float(p.x + v[0] * self.dt_s + dx_diff)
                y_new = float(p.y + v[1] * self.dt_s + dy_diff)

                crossed_net = self._crossed_into_impermeable_net(x_old, y_old, x_new, y_new)
                if crossed_net is not None:
                    x_new, y_new = self._push_outside_impermeable_net(
                        x_old, y_old, x_new, y_new, crossed_net
                    )

                p.x, p.y = x_new, y_new
                self._reflect_off_coast(p)

                # Safety: never leave active particles inside impermeable nets
                for tight_net in self.flow_model.nets:
                    if tight_net.is_impermeable and self.flow_model._point_inside_net(
                        p.x, p.y, tight_net
                    ):
                        p.x, p.y = self._push_outside_impermeable_net(
                            x_old, y_old, p.x, p.y, tight_net
                        )

                if not self._inside_domain(p.x, p.y):
                    p.alive = False
                    continue

                self._apply_biology_step(p)
                if not p.alive:
                    continue

                for net in self.flow_model.nets:
                    inside = self.flow_model._point_inside_net(p.x, p.y, net)
                    if inside:
                        if not p.entered_once[net.name]:
                            p.entered_once[net.name] = True
                            if first_arrival_s[net.name] is None:
                                first_arrival_s[net.name] = t + self.dt_s
                                self._log(
                                    f"  Første ankomst i {net.name} for case '{case_name}' "
                                    f"ved t={t + self.dt_s:.0f} s."
                                )
                        p.exposure_s[net.name] += self.dt_s
                        total_exposure_particle_seconds[net.name] += (
                            self._infectious_mass(p) * self.dt_s
                        )
                        total_risk_exposure_mass_seconds[net.name] += (
                            self._risk_mass(p) * self.dt_s
                        )

            for net in self.flow_model.nets:
                inside_particles = [
                    p for p in particles
                    if p.alive and self.flow_model._point_inside_net(p.x, p.y, net)
                ]
                total_infectious = sum(self._infectious_mass(p) for p in inside_particles)
                total_risk = sum(self._risk_mass(p) for p in inside_particles)
                concentration_ts[net.name].append(total_infectious / net.plan_area)
                risk_concentration_ts[net.name].append(total_risk / net.plan_area)
                inside_count_ts[net.name].append(len(inside_particles))
                mean_infectivity_ts[net.name].append(
                    float(np.mean([p.infectivity for p in inside_particles]))
                    if inside_particles else float('nan')
                )

            if it in snapshot_indices:
                alive_xy = np.array([[p.x, p.y] for p in particles if p.alive], dtype=float)
                alive_mass = np.array(
                    [self._infectious_mass(p) for p in particles if p.alive], dtype=float
                )
                alive_risk_mass = np.array(
                    [self._risk_mass(p) for p in particles if p.alive], dtype=float
                )
                snapshots[int(round(t))] = {
                    'xy': alive_xy, 'mass': alive_mass, 'risk_mass': alive_risk_mass
                }
                self._log(
                    f"  Snapshot lagret for case '{case_name}' ved t={t:.0f} s "
                    f"med {len(alive_xy)} aktive partikler."
                )

            pct = 100.0 * (it + 1) / total_steps
            if pct >= last_announced_pct + self.progress_every_pct or it == total_steps - 1:
                alive_after = sum(1 for p in particles if p.alive)
                peak_now = max(concentration_ts[net.name][-1] for net in self.flow_model.nets)
                mean_inf = (
                    float(np.mean([p.infectivity for p in particles if p.alive]))
                    if alive_after > 0 else float('nan')
                )
                self._log(
                    f"  Fremdrift '{case_name}': {pct:5.1f}% | t={t:6.1f} s | "
                    f"nye={spawned_now:3d} | "
                    f"aktive før/etter={alive_before:4d}/{alive_after:4d} | "
                    f"peak conc={peak_now:.4f} | mean infectivity={mean_inf:.3f}"
                )
                last_announced_pct = pct

        # Build summary rows
        summary_rows = []
        k_eff = self.effective_inactivation_rate_1_s()
        temp_factor = self._temperature_factor()
        site_asgn = self.flow_model.site_assignments  # net_name -> site_id (may be empty)
        source_site_id = (
            site_asgn.get(self.source_net_name, '')
            if self.source_mode == 'infected_net' and self.source_net_name
            else ''
        )
        for net in self.flow_model.nets:
            entered = [p for p in particles if p.exposure_s[net.name] > 0.0]
            mean_residence = float(np.mean([p.exposure_s[net.name] for p in entered])) if entered else float('nan')
            max_residence = float(np.max([p.exposure_s[net.name] for p in entered])) if entered else float('nan')
            mean_inf_entered = float(np.mean([p.infectivity for p in entered])) if entered else float('nan')
            peak_rel = float(np.max(concentration_ts[net.name])) if concentration_ts[net.name] else 0.0
            mean_rel = float(np.mean(concentration_ts[net.name])) if concentration_ts[net.name] else 0.0
            peak_risk_rel = float(np.max(risk_concentration_ts[net.name])) if risk_concentration_ts[net.name] else 0.0
            mean_risk_rel = float(np.mean(risk_concentration_ts[net.name])) if risk_concentration_ts[net.name] else 0.0
            total_exp = float(total_exposure_particle_seconds[net.name])
            total_risk_exp = float(total_risk_exposure_mass_seconds[net.name])

            status, reasons, arrival_alarm, exposure_alarm = self.risk.classify(
                first_arrival_s[net.name], peak_risk_rel, total_risk_exp
            )
            action = self.risk.recommended_action(status)

            if status in ('YELLOW', 'RED') or arrival_alarm or exposure_alarm:
                self._log(
                    f"  Risk {status} i {net.name} ({case_name}) | "
                    f"arrival_alarm={arrival_alarm} | exposure_alarm={exposure_alarm} | "
                    f"årsaker: {'; '.join(reasons)}"
                )

            summary_rows.append({
                'case_name': case_name,
                'direction': case_name,
                'net': net.name,
                'site_id': site_asgn.get(net.name, ''),
                'source_site_id': source_site_id,
                'soliditet': net.solidity,
                'beta_1screen': net.beta,
                'beta_2screens': net.beta2,
                'biology_enabled': self.biology_enabled,
                'base_inactivation_rate_1_s': self.base_inactivation_rate_1_s,
                'effective_inactivation_rate_1_s': k_eff,
                'temperature_c': self.temperature_c,
                'temperature_factor': temp_factor,
                'uv_inactivation_factor': self.uv_inactivation_factor,
                'species_infectivity_factor': self.species_infectivity_factor,
                'first_arrival_s': first_arrival_s[net.name],
                'first_arrival_min': (
                    None if first_arrival_s[net.name] is None
                    else first_arrival_s[net.name] / 60.0
                ),
                'mean_residence_s': mean_residence,
                'max_residence_s': max_residence,
                'mean_infectivity_of_entered_particles': mean_inf_entered,
                'peak_relative_concentration': peak_rel,
                'mean_relative_concentration': mean_rel,
                'peak_relative_risk_concentration': peak_risk_rel,
                'mean_relative_risk_concentration': mean_risk_rel,
                'total_exposure_mass_seconds': total_exp,
                'total_risk_exposure_mass_seconds': total_risk_exp,
                'risk_status': status,
                'recommended_action': action,
                'risk_reasons': ' | '.join(reasons),
                'arrival_alarm': bool(arrival_alarm),
                'exposure_alarm': bool(exposure_alarm),
                'operational_alarm': bool(arrival_alarm or exposure_alarm or status == 'RED'),
            })

        time_series_df = pd.DataFrame({'time_s': times})
        for net in self.flow_model.nets:
            safe = net.name.lower().replace(' ', '_')
            time_series_df[f'{safe}_conc_rel'] = concentration_ts[net.name]
            time_series_df[f'{safe}_risk_conc_rel'] = risk_concentration_ts[net.name]
            time_series_df[f'{safe}_inside_count'] = inside_count_ts[net.name]
            time_series_df[f'{safe}_mean_infectivity'] = mean_infectivity_ts[net.name]

        self.flow_model.U_inf = _orig_u_inf  # restore after forcing overrides
        self._log(f"Case '{case_name}' ferdig pa {time.perf_counter() - case_start:.1f} s.")

        # Representative flow direction for field visualisation (Reporter uses this)
        if self.current_forcing is not None:
            rep_case_dir = self.current_forcing.dominant_direction()
        else:
            rep_case_dir = self.flow_model.case_vector(case_name)

        return {
            'case_name': case_name,
            'times': times,
            'time_series': time_series_df,
            'summary': pd.DataFrame(summary_rows),
            'snapshots': snapshots,
            'case_dir': rep_case_dir,  # used by Reporter.render_snapshot_grid
        }

    # ── run_all ───────────────────────────────────────────────────────────────

    def run_all(self, case_list: Optional[List[str]] = None) -> dict:
        """
        Run transport analysis for all cases in case_list (default: RUN_USER_SETTINGS).

        Returns dict with 'results', 'summary', 'summary_path', 'metadata_path'.
        """
        if case_list is None:
            case_list = list(RUN_USER_SETTINGS['cases'])

        self._run_start = time.perf_counter()
        self._log(f"Output-mappe: {self.output_dir}")
        self.flow_model._log_parameter_summary(self._log)
        self._log_parameter_summary()

        results = {}
        summary_frames = []
        output_files: List[str] = []

        coast = self.flow_model.coast
        coast_meta: dict = {'y_coast_m': coast.y_coast}
        if isinstance(coast, PolylineCoastline):
            coast_meta['type'] = 'polyline'
            coast_meta['n_segments'] = coast.n_segments
        else:
            coast_meta['type'] = 'straight'

        forcing_meta: dict = (
            self.current_forcing.summary_stats()
            if self.current_forcing is not None
            else {'type': 'named_cases'}
        )

        metadata: dict = {
            'version': self.VERSION,
            'case': f'three_nets_coastline_pathogen_{self.VERSION}_risk_autocal',
            'coast': coast_meta,
            'coast_y_m': coast.y_coast,  # kept for backward compat
            'forcing': forcing_meta,
            'biology': {
                'enabled': self.biology_enabled,
                'base_inactivation_rate_1_s': self.base_inactivation_rate_1_s,
                'effective_inactivation_rate_1_s': self.effective_inactivation_rate_1_s(),
                'temperature_c': self.temperature_c,
                'reference_temperature_c': self.reference_temperature_c,
                'q10_inactivation': self.q10_inactivation,
                'uv_inactivation_factor': self.uv_inactivation_factor,
                'species_infectivity_factor': self.species_infectivity_factor,
                'minimum_infectivity': self.minimum_infectivity,
            },
            'risk_thresholds': self.risk.thresholds_dict(),
            'nets': [
                {
                    'name': n.name, 'center': n.center,
                    'diameter_m': 2 * n.radius, 'depth_m': n.depth,
                    'soliditet': n.solidity, 'beta': n.beta,
                }
                for n in self.flow_model.nets
            ],
        }

        self._log(
            f"Starter full analyse for {len(case_list)} strømretninger: "
            + ', '.join(case_list)
        )

        ver = self.VERSION.replace('.', '')
        for idx, case_name in enumerate(case_list, start=1):
            self._log(f"=== Case {idx}/{len(case_list)}: {case_name} ===")
            res = self.run_case(case_name)

            # Auto-calibrate from baseline case
            if self.risk.auto_calibrate_from_first_case and not self.risk._autocalibrated:
                should_calibrate = (
                    case_name == self.risk.baseline_case_name
                    or (idx == 1 and self.risk.baseline_case_name not in case_list)
                )
                if should_calibrate:
                    self.risk.calibrate(
                        res['summary'],
                        baseline_case_name=case_name,
                        log_func=self._log,
                    )
                    res['summary'] = self.risk.reclassify_summary_df(res['summary'])

            results[case_name] = res
            summary_frames.append(res['summary'])

            if not res['summary'].empty:
                order = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}
                worst = max(
                    res['summary'].to_dict('records'),
                    key=lambda r: order.get(str(r.get('risk_status', 'GREEN')).upper(), 0),
                )
                self._log(
                    f"Case '{case_name}' høyeste operative risiko: "
                    f"{worst['risk_status']} i {worst['net']} | "
                    f"handling: {worst['recommended_action']}"
                )
            self._log_operational_case_table(res['summary'], case_name)

            # Render and save outputs
            output_files.append(str(
                self.reporter.render_snapshot_grid(
                    res,
                    f'aquaguard_coast_pathogen_{case_name}_7samples_{ver}.png',
                    log_func=self._log,
                )
            ))
            output_files.append(str(
                self.reporter.render_concentration_timeseries(
                    res,
                    f'aquaguard_coast_pathogen_{case_name}_concentration_{ver}.png',
                    species_infectivity_factor=self.species_infectivity_factor,
                    log_func=self._log,
                )
            ))
            output_files.append(str(
                self.reporter.render_operational_risk_plot(
                    res,
                    f'aquaguard_coast_pathogen_{case_name}_risk_{ver}.png',
                    log_func=self._log,
                )
            ))
            ts_path = self.output_dir / f'aquaguard_coast_pathogen_{case_name}_timeseries_{ver}.csv'
            save_csv(res['time_series'], ts_path, log_func=self._log)
            output_files.append(str(ts_path))

        summary = pd.concat(summary_frames, ignore_index=True)
        summary_path = self.output_dir / f'aquaguard_coast_pathogen_summary_{ver}.csv'
        save_csv(summary, summary_path, log_func=self._log)
        output_files.append(str(summary_path))

        heatmap_path = self.reporter.render_risk_heatmap(
            summary,
            f'aquaguard_coast_pathogen_risk_heatmap_{ver}.png',
            log_func=self._log,
        )
        output_files.append(str(heatmap_path))

        if self.risk._baseline_info:
            metadata['risk_baseline'] = self.risk._baseline_info
        metadata['outputs'] = output_files

        metadata_path = self.output_dir / f'aquaguard_coast_pathogen_metadata_{ver}.json'
        save_json(metadata, metadata_path, log_func=self._log)

        self._log("Analyse ferdig.")
        return {
            'results': results,
            'summary': summary,
            'summary_path': summary_path,
            'metadata_path': metadata_path,
        }

    # ── Convenience render wrappers (backward compat with v1.22b callers) ────

    def render_snapshot_grid(self, case_result: dict, filename: str) -> Path:
        return self.reporter.render_snapshot_grid(
            case_result, filename, log_func=self._log
        )

    def render_concentration_timeseries(self, case_result: dict, filename: str) -> Path:
        return self.reporter.render_concentration_timeseries(
            case_result, filename,
            species_infectivity_factor=self.species_infectivity_factor,
            log_func=self._log,
        )

    def render_operational_risk_plot(self, case_result: dict, filename: str) -> Path:
        return self.reporter.render_operational_risk_plot(
            case_result, filename, log_func=self._log
        )

    def render_risk_heatmap(self, summary_df: pd.DataFrame, filename: str) -> Path:
        return self.reporter.render_risk_heatmap(
            summary_df, filename, log_func=self._log
        )
