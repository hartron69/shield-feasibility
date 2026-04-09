"""
core/geometry.py — Geometry dataclasses for AquaGuard

Contains:
  Net               — circular fish-farm pen (2D plan view)
  StraightCoastline — simple straight coastline parameterisation (v1.22b)
  PolylineCoastline — arbitrary polyline coastline (Sprint 2+)
  Site              — a fish-farm location holding one or more nets (Sprint 2+)
  FjordScenario     — complete file-driven scenario (Sprint 2+)

Sprint 1: Net, StraightCoastline extracted from v1.22b without physics changes.
Sprint 2: PolylineCoastline, Site, FjordScenario added.
Sprint 3: PolylineCoastline plugged into flow physics.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np


@dataclass
class Net:
    """Circular fish-farm pen in 2D plan view."""

    name: str
    center: tuple[float, float]
    radius: float
    depth: float
    solidity: float
    Cr: float = 0.8

    @property
    def is_impermeable(self) -> bool:
        """True if the net should be treated as fully solid (Sn >= 1)."""
        return self.solidity >= 1.0 - 1e-12

    @property
    def beta(self) -> float:
        """
        Single-screen transmission factor for normal velocity through the net.

        If solidity >= 1.0 the net is impermeable (beta = 0).
        Otherwise: beta = max(0, 1 - Sn * Cr)  [Loland formula]
        """
        if self.is_impermeable:
            return 0.0
        return max(0.0, 1.0 - self.solidity * self.Cr)

    @property
    def beta2(self) -> float:
        """Two-screen transmission: beta squared."""
        return self.beta ** 2

    @property
    def opacity(self) -> float:
        """Visual/flow opacity used in potential-flow perturbation scaling."""
        if self.is_impermeable:
            return 1.0
        return min(1.0, max(0.0, 1.0 - self.beta))

    @property
    def plan_area(self) -> float:
        """Horizontal plan area [m²]."""
        return math.pi * self.radius ** 2


@dataclass
class StraightCoastline:
    """
    Simple straight coastline parameterisation used in the local screening model.

    All points with y < y_coast are considered land.

    Sprint 3+: replace with PolylineCoastline for real fjord geometry.
    """

    y_coast: float = -150.0
    """Coastline y-position [m] in the model plane."""

    alongshore_length_scale_m: float = 220.0
    """Spatial length scale [m] for along-shore current variation."""

    offshore_decay_m: float = 120.0
    """Decay length [m] for offshore attenuation of along-shore component."""

    temporal_period_s: float = 900.0
    """Period [s] for simple pulsed along-shore current."""

    alongshore_variation_fraction: float = 0.30
    """Relative amplitude [-] for spatial/temporal variation along shore."""

    wall_image_weight: float = 0.85
    """Weight [-] for image-source contribution from the coast wall."""


# =============================================================================
# Sprint 2 additions
# =============================================================================

class PolylineCoastline:
    """
    Arbitrary polyline coastline for real fjord geometry.

    The coastline is defined as an ordered sequence of (x, y) vertices forming
    a connected polyline. The seaward side is assumed to be above the line
    (higher y values for a roughly east-west coast).

    Sprint 2: geometry and preview support.
    Sprint 3: plugged into the flow engine for reflection and normal-flow BC.
    """

    def __init__(
        self,
        vertices: np.ndarray,
        alongshore_length_scale_m: float = 220.0,
        offshore_decay_m: float = 120.0,
        temporal_period_s: float = 900.0,
        alongshore_variation_fraction: float = 0.30,
        wall_image_weight: float = 0.85,
    ):
        """
        Parameters
        ----------
        vertices : array-like, shape (N, 2)
            Ordered (x, y) coordinates of the coastline vertices [m].
            Must have at least 2 points.
        alongshore_length_scale_m, offshore_decay_m, temporal_period_s,
        alongshore_variation_fraction, wall_image_weight :
            Same physics parameters as StraightCoastline — required so the
            flow engine can use PolylineCoastline directly (Sprint 3).
        """
        verts = np.asarray(vertices, dtype=float)
        if verts.ndim != 2 or verts.shape[1] != 2:
            raise ValueError("vertices must be shape (N, 2)")
        if len(verts) < 2:
            raise ValueError("PolylineCoastline requires at least 2 vertices")
        self.vertices = verts
        self.alongshore_length_scale_m = float(alongshore_length_scale_m)
        self.offshore_decay_m = float(offshore_decay_m)
        self.temporal_period_s = float(temporal_period_s)
        self.alongshore_variation_fraction = float(alongshore_variation_fraction)
        self.wall_image_weight = float(wall_image_weight)

    # ── Segment helpers ───────────────────────────────────────────────────────

    @property
    def n_segments(self) -> int:
        return len(self.vertices) - 1

    def segment_tangent(self, seg_idx: int) -> np.ndarray:
        """Unit tangent vector of segment seg_idx (pointing in increasing index dir)."""
        d = self.vertices[seg_idx + 1] - self.vertices[seg_idx]
        n = np.linalg.norm(d)
        return d / n if n > 1e-12 else np.array([1.0, 0.0])

    def segment_normal_seaward(self, seg_idx: int) -> np.ndarray:
        """Unit normal vector of segment pointing toward the seaward (high-y) side."""
        t = self.segment_tangent(seg_idx)
        # Rotate 90° counter-clockwise: (-ty, tx) points left of travel direction.
        # For an eastward coastline this points northward (seaward).
        n = np.array([-t[1], t[0]])
        # Ensure it points to the higher-y side
        if n[1] < 0:
            n = -n
        return n

    def _nearest_segment_and_foot(
        self, x: float, y: float
    ) -> Tuple[int, np.ndarray, float]:
        """
        Find the nearest segment and the foot of the perpendicular from (x, y).

        Returns (seg_idx, foot_point, signed_distance)
        where signed_distance > 0 means the point is on the seaward side.
        """
        pt = np.array([x, y])
        best_idx = 0
        best_foot = self.vertices[0].copy()
        best_dist2 = np.inf

        for i in range(self.n_segments):
            a = self.vertices[i]
            b = self.vertices[i + 1]
            ab = b - a
            ab2 = float(np.dot(ab, ab))
            if ab2 < 1e-24:
                foot = a.copy()
            else:
                t = float(np.dot(pt - a, ab)) / ab2
                t = max(0.0, min(1.0, t))
                foot = a + t * ab
            d2 = float(np.dot(pt - foot, pt - foot))
            if d2 < best_dist2:
                best_dist2 = d2
                best_idx = i
                best_foot = foot

        normal = self.segment_normal_seaward(best_idx)
        signed = float(np.dot(pt - best_foot, normal))
        return best_idx, best_foot, signed

    # ── Public interface ──────────────────────────────────────────────────────

    def nearest_segment_idx(self, x: float, y: float) -> int:
        idx, _, _ = self._nearest_segment_and_foot(x, y)
        return idx

    def local_tangent(self, x: float, y: float) -> np.ndarray:
        idx, _, _ = self._nearest_segment_and_foot(x, y)
        return self.segment_tangent(idx)

    def local_normal_seaward(self, x: float, y: float) -> np.ndarray:
        idx, _, _ = self._nearest_segment_and_foot(x, y)
        return self.segment_normal_seaward(idx)

    def signed_distance(self, x: float, y: float) -> float:
        """Signed distance to coastline (>0 = seaward, <0 = land side)."""
        _, _, sd = self._nearest_segment_and_foot(x, y)
        return sd

    def is_on_land(self, x: float, y: float) -> bool:
        """True if the point is on the land side of the coastline."""
        return self.signed_distance(x, y) < 0.0

    def land_mask(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """
        Vectorized land mask for a 2-D grid (shape matching X and Y).

        Returns bool array: True = water, False = land.
        Much faster than calling is_on_land() per cell.
        """
        pts = np.stack([X.ravel(), Y.ravel()], axis=1)  # (N, 2)
        n_pts = pts.shape[0]

        best_d2 = np.full(n_pts, np.inf)
        best_signed = np.zeros(n_pts)

        for i in range(self.n_segments):
            a = self.vertices[i]
            b = self.vertices[i + 1]
            ab = b - a
            ab2 = float(np.dot(ab, ab))
            if ab2 < 1e-24:
                foot = np.broadcast_to(a, (n_pts, 2)).copy()
            else:
                t = np.clip(((pts - a) @ ab) / ab2, 0.0, 1.0)
                foot = a + t[:, None] * ab
            diff = pts - foot
            d2 = np.einsum('ij,ij->i', diff, diff)
            n_vec = self.segment_normal_seaward(i)
            signed = diff @ n_vec
            improve = d2 < best_d2
            best_d2 = np.where(improve, d2, best_d2)
            best_signed = np.where(improve, signed, best_signed)

        return (best_signed >= 0.0).reshape(X.shape)

    def reflect_particle(self, x: float, y: float) -> Tuple[float, float]:
        """
        Reflect point (x, y) across the nearest coastline segment.
        Used for particle reflection in the time-marcher.
        """
        _, foot, sd = self._nearest_segment_and_foot(x, y)
        normal = self.local_normal_seaward(x, y)
        reflected = np.array([x, y]) - 2.0 * sd * normal
        return float(reflected[0]), float(reflected[1])

    def mean_y_coast(self) -> float:
        """Mean y-coordinate of all vertices — used as StraightCoastline approx."""
        return float(np.mean(self.vertices[:, 1]))

    @property
    def y_coast(self) -> float:
        """Mean coastline y — compatibility shim so flow engine logging works unchanged."""
        return self.mean_y_coast()

    def dominant_seaward_normal(self) -> np.ndarray:
        """Length-weighted mean seaward normal across all segments."""
        total = np.zeros(2)
        for i in range(self.n_segments):
            seg_len = float(np.linalg.norm(self.vertices[i + 1] - self.vertices[i]))
            total += self.segment_normal_seaward(i) * seg_len
        n = np.linalg.norm(total)
        return total / n if n > 1e-12 else np.array([0.0, 1.0])

    def to_straight_approx(self, **coast_kwargs) -> 'StraightCoastline':
        """
        Return a StraightCoastline approximation using the mean coastline y position.
        Used in Sprint 2 to keep the existing flow engine compatible.
        Sprint 3 replaces this with direct PolylineCoastline physics.
        """
        return StraightCoastline(y_coast=self.mean_y_coast(), **coast_kwargs)

    def x_range(self) -> Tuple[float, float]:
        return float(self.vertices[:, 0].min()), float(self.vertices[:, 0].max())

    def y_range(self) -> Tuple[float, float]:
        return float(self.vertices[:, 1].min()), float(self.vertices[:, 1].max())

    @classmethod
    def from_csv(cls, path) -> 'PolylineCoastline':
        """Load from a two-column CSV file with headers 'x' and 'y'."""
        import csv
        from pathlib import Path
        rows = []
        with open(Path(path), newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append([float(row['x']), float(row['y'])])
        return cls(np.array(rows))

    def to_csv(self, path) -> None:
        """Save vertices to a two-column CSV file with headers 'x' and 'y'."""
        from pathlib import Path
        import csv
        with open(Path(path), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['x', 'y'])
            for v in self.vertices:
                writer.writerow([v[0], v[1]])


@dataclass
class Site:
    """
    A fish-farm location holding one or more nets.

    Coordinates (x, y) are in the local model plane [m].
    Real-world (lat, lon) are stored for Sprint 4+ forcing integration.
    """

    site_id: str
    name: str
    x: float
    y: float
    nets: List[Net]
    site_type: str = "production"    # production | source | receiver
    lat: float = 0.0                 # WGS84 latitude (future use)
    lon: float = 0.0                 # WGS84 longitude (future use)
    metadata: Dict = field(default_factory=dict)

    def net_by_name(self, name: str) -> Optional[Net]:
        for n in self.nets:
            if n.name == name:
                return n
        return None

    def all_net_centers(self) -> List[Tuple[float, float]]:
        return [n.center for n in self.nets]


@dataclass
class FjordScenario:
    """
    Complete file-driven scenario for a coastal / fjord system.

    Replaces hard-coded USER_SETTINGS dicts. Users edit JSON/CSV files in a
    scenario directory and call load_scenario() — no engine code changes needed.

    Sprint 2: scenario loading, preview, domain auto-computation.
    Sprint 3: PolylineCoastline plugged into flow physics.
    Sprint 4: forcing_timeseries replaces named cases.
    Sprint 5+: source_site / target_site transfer engine.
    """

    name: str
    sites: List[Site]
    coastline: Union[StraightCoastline, PolylineCoastline]
    domain: Dict                      # {'x': (xmin,xmax), 'y': (ymin,ymax), 'nx':, 'ny':}
    pathogen_source: Dict             # mirrors PATHOGEN_USER_SETTINGS + source routing
    forcing: Dict                     # {'mode': 'named_cases'|'timeseries', 'cases': [...]}
    description: str = ""
    scenario_dir: Optional[str] = None

    # ── Convenience accessors ─────────────────────────────────────────────────

    def all_nets(self) -> List[Net]:
        """Return all nets from all sites in a flat list."""
        return [net for site in self.sites for net in site.nets]

    def site_by_id(self, site_id: str) -> Optional[Site]:
        for s in self.sites:
            if s.site_id == site_id:
                return s
        return None

    def source_site(self) -> Optional[Site]:
        """Return the designated source site (if source_mode = 'infected_net')."""
        sid = self.pathogen_source.get('source_site_id')
        return self.site_by_id(sid) if sid else None

    # ── Domain helpers ────────────────────────────────────────────────────────

    @staticmethod
    def auto_domain(
        sites: List[Site],
        coastline: Union[StraightCoastline, PolylineCoastline],
        padding: float = 120.0,
        nx: int = 200,
        ny: int = 150,
    ) -> Dict:
        """Compute a domain bounding box from site positions and coastline."""
        xs: List[float] = []
        ys: List[float] = []
        for site in sites:
            xs.append(site.x)
            ys.append(site.y)
            for net in site.nets:
                xs.append(net.center[0])
                ys.append(net.center[1])
        if isinstance(coastline, PolylineCoastline):
            xs += list(coastline.vertices[:, 0])
            ys += list(coastline.vertices[:, 1])
        elif isinstance(coastline, StraightCoastline):
            ys.append(coastline.y_coast)

        if not xs:
            return {'x': (-300.0, 300.0), 'y': (-200.0, 200.0), 'nx': nx, 'ny': ny}

        return {
            'x': (min(xs) - padding, max(xs) + padding),
            'y': (min(ys) - padding, max(ys) + padding),
            'nx': nx,
            'ny': ny,
        }

    # ── Flow model factory ────────────────────────────────────────────────────

    def build_flow_model(self, U_inf: float = 0.5, output_dir=None):
        """
        Build a CoastalThreeNetFlowModel from this scenario.

        Sprint 3: PolylineCoastline is plugged directly into flow physics.
        """
        from core.flow_engine import CoastalThreeNetFlowModel

        coast = self.coastline  # polyline or straight — flow engine handles both

        # Use coastline's own y_coast (mean for polyline, exact for straight) as domain bottom
        y_top = self.domain['y'][1]
        domain = {
            'x': self.domain['x'],
            'y': (self.domain['y'][0], y_top),
            'nx': self.domain.get('nx', 200),
            'ny': self.domain.get('ny', 150),
        }

        # Build net→site mapping so the time-marcher can report site_id per net
        site_assignments = {
            net.name: site.site_id
            for site in self.sites
            for net in site.nets
        }

        flow_model = CoastalThreeNetFlowModel(
            U_inf=U_inf,
            output_dir=output_dir,
            nets=self.all_nets(),
            coast=coast,
            domain=domain,
        )
        flow_model.site_assignments = site_assignments
        return flow_model
