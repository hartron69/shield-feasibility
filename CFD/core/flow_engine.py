"""
core/flow_engine.py — CoastalThreeNetFlowModel

Fast local flow model combining:
  1. Coastal background current (along + cross-shore, time-varying)
  2. Scaled potential-flow perturbation around each net
  3. Image-source wall correction for the coastline
  4. Sequential Loland transmission through net layers

Physics are identical to v1.22b. The class now imports geometry and scenario
settings from the core package instead of relying on module-level globals.

Sprint 3+: StraightCoastline -> PolylineCoastline, multi-site support.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from core.geometry import Net, PolylineCoastline, StraightCoastline
from core.scenarios import (
    COAST_USER_SETTINGS,
    DOMAIN_USER_SETTINGS,
    FLOW_USER_SETTINGS,
    NET_USER_SETTINGS,
)


class CoastalThreeNetFlowModel:
    """
    Fast local 2D-plan flow model for fish-farm nets near a straight coastline.

    Combines:
    - Background coastal current (redirected along coast)
    - Scaled potential-flow perturbation around each circular net
    - Loland sequential transmission through net layers

    This is a screening model, not a full CFD solver.
    """

    def __init__(
        self,
        U_inf: Optional[float] = None,
        output_dir: Optional[Path] = None,
        nets: Optional[List[Net]] = None,
        coast=None,  # StraightCoastline | PolylineCoastline
        domain: Optional[dict] = None,
    ):
        U_inf = FLOW_USER_SETTINGS['U_inf'] if U_inf is None else U_inf
        output_dir = FLOW_USER_SETTINGS['output_dir'] if output_dir is None else output_dir

        self.U_inf = float(U_inf)
        self.nets = [Net(**cfg) for cfg in NET_USER_SETTINGS] if nets is None else list(nets)
        self.coast = StraightCoastline(**COAST_USER_SETTINGS) if coast is None else coast

        if domain is None:
            self.domain = {
                'x': DOMAIN_USER_SETTINGS['x'],
                'y': (self.coast.y_coast, DOMAIN_USER_SETTINGS['y_top']),
                'nx': DOMAIN_USER_SETTINGS['nx'],
                'ny': DOMAIN_USER_SETTINGS['ny'],
            }
        else:
            self.domain = dict(domain)

        base_dir = Path(__file__).resolve().parent.parent
        self.output_dir = (output_dir or (base_dir / 'output')).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # net_name -> site_id; populated by FjordScenario.build_flow_model()
        self.site_assignments: Dict[str, str] = {}

    # ── Parameter logging ────────────────────────────────────────────────────

    def _log_parameter_summary(self, log_func=print) -> None:
        log_func('Strømningsmodell – parameteroppsett:')
        log_func(f'  U_inf={self.U_inf:.3f} m/s -> fri referansestrøm')
        log_func(f'  output_dir={self.output_dir}')
        log_func('  Nøter:')
        for n in self.nets:
            log_func(
                f"    {n.name}: center={n.center} m | diameter={2*n.radius:.1f} m | "
                f"depth={n.depth:.1f} m | soliditet={n.solidity:.2f} | "
                f"beta={n.beta:.3f} | beta²={n.beta2:.3f}"
            )
        log_func('  Kystlinje:')
        if isinstance(self.coast, PolylineCoastline):
            log_func(
                f'    PolylineCoastline: {self.coast.n_segments} segmenter | '
                f'y_coast(mean)={self.coast.y_coast:.1f} m'
            )
        else:
            log_func(f'    y_coast={self.coast.y_coast:.1f} m')
        log_func(
            f'    alongshore_length_scale_m={self.coast.alongshore_length_scale_m:.1f} m | '
            f'offshore_decay_m={self.coast.offshore_decay_m:.1f} m'
        )
        log_func(
            f'    temporal_period_s={self.coast.temporal_period_s:.1f} s | '
            f'alongshore_variation_fraction={self.coast.alongshore_variation_fraction:.2f} | '
            f'wall_image_weight={self.coast.wall_image_weight:.2f}'
        )
        log_func(
            f"  Domene: x={self.domain['x']} m | y={self.domain['y']} m | "
            f"nx={self.domain['nx']} | ny={self.domain['ny']}"
        )

    # ── Vector utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _unit(vec: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(vec)
        if n < 1e-12:
            return np.array([1.0, 0.0])
        return vec / n

    @staticmethod
    def _rotate_to_local(
        vec: np.ndarray, e: np.ndarray, ep: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        xloc = vec[..., 0] * e[0] + vec[..., 1] * e[1]
        yloc = vec[..., 0] * ep[0] + vec[..., 1] * ep[1]
        return xloc, yloc

    @staticmethod
    def _rotate_to_global(
        uloc: np.ndarray, vloc: np.ndarray, e: np.ndarray, ep: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        ug = uloc * e[0] + vloc * ep[0]
        vg = uloc * e[1] + vloc * ep[1]
        return ug, vg

    @staticmethod
    def _transmit(velocity: np.ndarray, pass_normal: np.ndarray, beta: float) -> np.ndarray:
        q = float(np.dot(velocity, pass_normal))
        if q <= 0.0:
            return velocity.copy()
        v_n = q * pass_normal
        v_t = velocity - v_n
        return v_t + beta * v_n

    # ── Case directions ───────────────────────────────────────────────────────

    @staticmethod
    def case_vector(case_name: str) -> np.ndarray:
        """Return standard current direction unit vector for a named scenario.

        'tverrs' and 'diagonal' point from open sea toward the coast so that
        the upstream_line source is placed on the open-sea side.
        """
        cases = {
            'langs':    np.array([1.0, 0.0]),
            'tverrs':   np.array([0.0, -1.0]),
            'diagonal': np.array([1.0, -1.0]) / np.sqrt(2.0),
        }
        return cases[case_name]

    # ── Geometry helpers ──────────────────────────────────────────────────────

    def _point_inside_net(self, x: float, y: float, net: Net) -> bool:
        dx = x - net.center[0]
        dy = y - net.center[1]
        return dx * dx + dy * dy <= net.radius ** 2 + 1e-12

    # ── Coastline-type-aware helpers (Sprint 3) ───────────────────────────────

    def _coast_local_frame(
        self, x: float, y: float
    ) -> Tuple[float, np.ndarray, np.ndarray]:
        """Return (dist_offshore, along_tangent, seaward_normal) at (x, y).

        Works for both StraightCoastline and PolylineCoastline.
        dist_offshore is clamped to >= 0 (on-land points get dist=0).
        """
        if isinstance(self.coast, PolylineCoastline):
            dist = max(self.coast.signed_distance(x, y), 0.0)
            along = self.coast.local_tangent(x, y)
            normal = self.coast.local_normal_seaward(x, y)
        else:
            dist = max(y - self.coast.y_coast, 0.0)
            along = np.array([1.0, 0.0])
            normal = np.array([0.0, 1.0])
        return dist, along, normal

    def _is_on_land(self, x: float, y: float) -> bool:
        """True if point is on the land side of the coastline."""
        if isinstance(self.coast, PolylineCoastline):
            return self.coast.is_on_land(x, y)
        return y < self.coast.y_coast

    def _mirror_center_across_coast(self, cx: float, cy: float) -> Tuple[float, float]:
        """Mirror a net center across the coastline for image-source correction."""
        if isinstance(self.coast, PolylineCoastline):
            return self.coast.reflect_particle(cx, cy)
        return cx, 2.0 * self.coast.y_coast - cy

    def _clamp_point_offshore(
        self, x: float, y: float, min_dist: float = 2.0
    ) -> Tuple[float, float]:
        """Return (x, y) guaranteed to be at least min_dist offshore from the coast."""
        if isinstance(self.coast, PolylineCoastline):
            sd = self.coast.signed_distance(x, y)
            if sd < min_dist:
                _, foot, _ = self.coast._nearest_segment_and_foot(x, y)
                n = self.coast.local_normal_seaward(x, y)
                x = float(foot[0] + min_dist * n[0])
                y = float(foot[1] + min_dist * n[1])
        else:
            if y < self.coast.y_coast + min_dist:
                y = self.coast.y_coast + min_dist
        return x, y

    # ── Background coastal velocity ───────────────────────────────────────────

    def coastal_background_velocity_at_point_time(
        self, point: np.ndarray, t_s: float, case_dir: np.ndarray
    ) -> np.ndarray:
        x, y = float(point[0]), float(point[1])
        dist, along, normal = self._coast_local_frame(x, y)

        case_dir = self._unit(case_dir)
        U_along_base = self.U_inf * float(np.dot(case_dir, along))
        U_cross_base = self.U_inf * float(np.dot(case_dir, normal))

        ramp = np.tanh(dist / 25.0)
        U_cross = U_cross_base * ramp

        # Along-shore coordinate for spatial phase (dot with local tangent)
        s_along = float(np.dot(np.array([x, y]), along))
        spatial_phase = 2.0 * np.pi * s_along / self.coast.alongshore_length_scale_m
        temporal_phase = 2.0 * np.pi * t_s / self.coast.temporal_period_s
        variation = (
            1.0
            + self.coast.alongshore_variation_fraction
            * np.sin(spatial_phase + temporal_phase)
        )
        offshore_decay = np.exp(-dist / self.coast.offshore_decay_m)
        U_along_variable = (0.35 * self.U_inf) * variation * offshore_decay

        return (U_along_base + U_along_variable) * along + U_cross * normal

    # ── Net perturbations ─────────────────────────────────────────────────────

    def _outer_perturbation_from_net(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        net: Net,
        local_bg: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        U_mag = float(np.linalg.norm(local_bg))
        if U_mag < 1e-10:
            return np.zeros_like(X), np.zeros_like(Y)

        e = self._unit(local_bg)
        ep = np.array([-e[1], e[0]])
        dx = X - net.center[0]
        dy = Y - net.center[1]
        xloc, yloc = self._rotate_to_local(np.stack([dx, dy], axis=-1), e, ep)
        r2 = xloc ** 2 + yloc ** 2
        theta = np.arctan2(yloc, xloc)

        a = net.radius
        u_total = U_mag * (1.0 - (a ** 2 / np.maximum(r2, 1e-12)) * np.cos(2.0 * theta))
        v_total = -U_mag * (a ** 2 / np.maximum(r2, 1e-12)) * np.sin(2.0 * theta)
        u_pert = net.opacity * (u_total - U_mag)
        v_pert = net.opacity * v_total
        ug, vg = self._rotate_to_global(u_pert, v_pert, e, ep)
        mask_inside = np.sqrt(np.maximum(r2, 0.0)) <= a
        ug = np.where(mask_inside, 0.0, ug)
        vg = np.where(mask_inside, 0.0, vg)
        return ug, vg

    def _image_perturbation_from_net(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        net: Net,
        local_bg: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        mx, my = self._mirror_center_across_coast(net.center[0], net.center[1])
        mirrored = Net(
            name=f'{net.name}_image',
            center=(mx, my),
            radius=net.radius,
            depth=net.depth,
            solidity=net.solidity,
            Cr=net.Cr,
        )
        ug, vg = self._outer_perturbation_from_net(X, Y, mirrored, local_bg)
        return self.coast.wall_image_weight * ug, self.coast.wall_image_weight * vg

    def _events_for_point_and_net(
        self, point: np.ndarray, flow_dir: np.ndarray, net: Net
    ) -> List[Tuple[float, np.ndarray, float]]:
        e = self._unit(flow_dir)
        ep = np.array([-e[1], e[0]])
        c = np.array(net.center)
        q = point - c
        s_p = float(np.dot(point, e))
        s_c = float(np.dot(c, e))
        eta = float(np.dot(q, ep))

        if abs(eta) > net.radius + 1e-12:
            return []

        xi_half = math.sqrt(max(net.radius ** 2 - eta ** 2, 0.0))
        s_front = s_c - xi_half
        s_back = s_c + xi_half
        if s_p < s_front - 1e-12:
            return []

        front_point = c + (-xi_half) * e + eta * ep
        back_point = c + (+xi_half) * e + eta * ep
        n_front_out = (front_point - c) / net.radius
        n_back_out = (back_point - c) / net.radius

        events: List[Tuple[float, np.ndarray, float]] = []
        events.append((s_front, -n_front_out, net.beta))
        if s_p > s_back + 1e-12:
            events.append((s_back, n_back_out, net.beta))
        return events

    # ── Full velocity at a point ──────────────────────────────────────────────

    def background_velocity_at_point_time(
        self,
        point: np.ndarray,
        t_s: float,
        case_dir: np.ndarray,
        exclude_index: Optional[int] = None,
    ) -> np.ndarray:
        bg = self.coastal_background_velocity_at_point_time(point, t_s, case_dir)
        vx, vy = float(bg[0]), float(bg[1])
        X = np.array([[point[0]]])
        Y = np.array([[point[1]]])
        local_bg = bg.copy()
        for idx, net in enumerate(self.nets):
            if exclude_index is not None and idx == exclude_index:
                continue
            up, vp = self._outer_perturbation_from_net(X, Y, net, local_bg)
            vx += float(up[0, 0])
            vy += float(vp[0, 0])
            ui, vi = self._image_perturbation_from_net(X, Y, net, local_bg)
            vx += float(ui[0, 0])
            vy += float(vi[0, 0])
        return np.array([vx, vy])

    def velocity_at_point_time(
        self, x: float, y: float, t_s: float, case_dir: np.ndarray
    ) -> np.ndarray:
        point = np.array([x, y], dtype=float)
        bg0 = self.coastal_background_velocity_at_point_time(point, t_s, case_dir)
        transport_dir = self._unit(bg0 if np.linalg.norm(bg0) > 1e-12 else case_dir)

        inside_indices = [
            i for i, net in enumerate(self.nets) if self._point_inside_net(x, y, net)
        ]
        if len(inside_indices) > 1:
            inside_indices = inside_indices[:1]
        exclude_idx = inside_indices[0] if inside_indices else None

        v = self.background_velocity_at_point_time(
            point, t_s, case_dir, exclude_index=exclude_idx
        )
        events: List[Tuple[float, np.ndarray, float]] = []
        for net in self.nets:
            events.extend(self._events_for_point_and_net(point, transport_dir, net))
        events.sort(key=lambda tup: tup[0])
        for _, pass_normal, beta in events:
            v = self._transmit(v, pass_normal, beta)

        # No-flow-into-coast BC: remove coast-normal component pointing landward
        dist, _, coast_n = self._coast_local_frame(x, y)
        if dist < 1.0:
            vn = float(np.dot(v, coast_n))
            if vn < 0.0:
                v = v - vn * coast_n
        return v

    # ── Field evaluation (for plots / snapshots) ──────────────────────────────

    def evaluate_field(
        self,
        case_name: str,
        t_s: float,
        nx: Optional[int] = None,
        ny: Optional[int] = None,
        case_dir: Optional[np.ndarray] = None,
    ) -> dict:
        if case_dir is None:
            case_dir = self.case_vector(case_name)
        nx = self.domain['nx'] if nx is None else int(nx)
        ny = self.domain['ny'] if ny is None else int(ny)
        x = np.linspace(*self.domain['x'], nx)
        y = np.linspace(*self.domain['y'], ny)
        X, Y = np.meshgrid(x, y)
        U = np.zeros_like(X)
        V = np.zeros_like(X)
        # Build land mask — vectorized for PolylineCoastline (much faster)
        if isinstance(self.coast, PolylineCoastline):
            water_mask = self.coast.land_mask(X, Y)
        else:
            water_mask = Y >= self.coast.y_coast

        for i in range(Y.shape[0]):
            for j in range(X.shape[1]):
                if not water_mask[i, j]:
                    U[i, j] = np.nan
                    V[i, j] = np.nan
                    continue
                v = self.velocity_at_point_time(
                    float(X[i, j]), float(Y[i, j]), t_s, case_dir
                )
                U[i, j] = v[0]
                V[i, j] = v[1]

        speed = np.sqrt(U ** 2 + V ** 2)
        return {
            'X': X, 'Y': Y, 'U': U, 'V': V,
            'speed': speed, 'case_name': case_name, 'time_s': t_s,
        }
