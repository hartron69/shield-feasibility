"""
core/forcing.py — Time-varying current forcing

Contains:
  CurrentForcing — interpolated (u, v) time series loaded from CSV

CSV formats accepted:
  Format A (Cartesian):  time_s, u_m_s, v_m_s
  Format B (polar):      time_s, speed_m_s, direction_deg
      direction_deg follows oceanographic "toward" convention:
      0 = current flows northward, 90 = eastward.

Sprint 4: FirstForcing from CSV time series — replaces hardcoded case vectors.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Optional, Union

import numpy as np


class CurrentForcing:
    """
    Time-interpolated current forcing for the AquaGuard flow engine.

    The forcing provides (u, v) [m/s] at any time by linear interpolation
    between CSV rows.  Values before the first row are held at the first
    row's values; values after the last row are held at the last row's values.

    Parameters
    ----------
    times_s : array-like, shape (N,)
        Monotonically increasing simulation times [s].
    u : array-like, shape (N,)
        East-ward current component [m/s] at each time.
    v : array-like, shape (N,)
        North-ward current component [m/s] at each time.
    label : str, optional
        Short descriptive label used in logging.
    """

    def __init__(
        self,
        times_s,
        u,
        v,
        label: str = 'timeseries',
    ):
        times = np.asarray(times_s, dtype=float)
        u_arr = np.asarray(u, dtype=float)
        v_arr = np.asarray(v, dtype=float)
        if times.ndim != 1 or u_arr.ndim != 1 or v_arr.ndim != 1:
            raise ValueError("times_s, u, v must be 1-D arrays")
        if len(times) < 2:
            raise ValueError("CurrentForcing requires at least 2 time points")
        if not np.all(np.diff(times) > 0):
            raise ValueError("times_s must be strictly monotonically increasing")
        if len(u_arr) != len(times) or len(v_arr) != len(times):
            raise ValueError("u and v must have the same length as times_s")

        self.times_s = times
        self.u = u_arr
        self.v = v_arr
        self.label = str(label)

    # ── Interpolation ─────────────────────────────────────────────────────────

    def velocity_at(self, t_s: float) -> np.ndarray:
        """Interpolated (u, v) velocity vector at time t_s [m/s]."""
        u = float(np.interp(t_s, self.times_s, self.u))
        v = float(np.interp(t_s, self.times_s, self.v))
        return np.array([u, v])

    def speed_at(self, t_s: float) -> float:
        """Current speed [m/s] at time t_s."""
        return float(np.linalg.norm(self.velocity_at(t_s)))

    def direction_at(self, t_s: float) -> np.ndarray:
        """Unit direction vector at time t_s (falls back to [1, 0] if speed ~ 0)."""
        vel = self.velocity_at(t_s)
        mag = float(np.linalg.norm(vel))
        return vel / mag if mag > 1e-12 else np.array([1.0, 0.0])

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def duration_s(self) -> float:
        """Total duration covered by the time series [s]."""
        return float(self.times_s[-1] - self.times_s[0])

    @property
    def n_points(self) -> int:
        return len(self.times_s)

    def mean_speed(self) -> float:
        """Mean speed averaged over all time points [m/s]."""
        return float(np.mean(np.sqrt(self.u ** 2 + self.v ** 2)))

    def dominant_direction(self) -> np.ndarray:
        """Speed-weighted mean unit direction vector."""
        speeds = np.sqrt(self.u ** 2 + self.v ** 2)
        total = float(np.sum(speeds))
        if total < 1e-12:
            return np.array([1.0, 0.0])
        wu = float(np.sum(speeds * self.u)) / total
        wv = float(np.sum(speeds * self.v)) / total
        mag = math.hypot(wu, wv)
        return np.array([wu, wv]) / mag if mag > 1e-12 else np.array([1.0, 0.0])

    def summary_stats(self) -> dict:
        """Return a dict of summary statistics for logging and metadata."""
        speeds = np.sqrt(self.u ** 2 + self.v ** 2)
        dom = self.dominant_direction()
        return {
            'label': self.label,
            'n_points': self.n_points,
            'duration_s': self.duration_s,
            'mean_speed_m_s': float(np.mean(speeds)),
            'max_speed_m_s': float(np.max(speeds)),
            'min_speed_m_s': float(np.min(speeds)),
            'dominant_u': float(dom[0]),
            'dominant_v': float(dom[1]),
        }

    # ── Factory constructors ──────────────────────────────────────────────────

    @classmethod
    def constant(
        cls,
        u: float,
        v: float,
        duration_s: float = 3600.0,
        label: str = 'constant',
    ) -> 'CurrentForcing':
        """Constant current (u, v) over duration_s. Useful for testing."""
        return cls([0.0, float(duration_s)], [u, u], [v, v], label=label)

    @classmethod
    def from_named_case(
        cls,
        case_name: str,
        U_inf: float = 0.5,
        duration_s: float = 1200.0,
        label: Optional[str] = None,
    ) -> 'CurrentForcing':
        """Convert a v1.22b named case (langs/tverrs/diagonal) to a CurrentForcing."""
        _CASES = {
            'langs':    np.array([1.0, 0.0]),
            'tverrs':   np.array([0.0, -1.0]),
            'diagonal': np.array([1.0, -1.0]) / math.sqrt(2.0),
        }
        if case_name not in _CASES:
            raise ValueError(f"Unknown case '{case_name}'. Choose from: {list(_CASES)}")
        d = _CASES[case_name] * U_inf
        return cls(
            [0.0, float(duration_s)],
            [float(d[0]), float(d[0])],
            [float(d[1]), float(d[1])],
            label=label or case_name,
        )

    @classmethod
    def from_csv(cls, path: Union[str, Path]) -> 'CurrentForcing':
        """
        Load from CSV.

        Supported formats (detected by column names):
          Format A: time_s, u_m_s, v_m_s          (Cartesian, East/North)
          Format B: time_s, speed_m_s, direction_deg  (polar, toward convention)
              direction_deg: 0 = flows N, 90 = flows E, 180 = flows S, 270 = flows W

        Missing values / blank rows are skipped.
        """
        p = Path(path)
        rows = []
        with open(p, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]
            for row in reader:
                cleaned = {k.strip().lower(): v.strip() for k, v in row.items() if v.strip()}
                if 'time_s' not in cleaned:
                    continue
                try:
                    t = float(cleaned['time_s'])
                except (ValueError, KeyError):
                    continue
                # Format A
                if 'u_m_s' in cleaned and 'v_m_s' in cleaned:
                    try:
                        rows.append((t, float(cleaned['u_m_s']), float(cleaned['v_m_s'])))
                    except ValueError:
                        pass
                # Format B
                elif 'speed_m_s' in cleaned and 'direction_deg' in cleaned:
                    try:
                        spd = float(cleaned['speed_m_s'])
                        deg = float(cleaned['direction_deg'])
                        rad = math.radians(deg)
                        # toward: u = spd * sin(deg), v = spd * cos(deg)
                        rows.append((t, spd * math.sin(rad), spd * math.cos(rad)))
                    except ValueError:
                        pass

        if len(rows) < 2:
            raise ValueError(
                f"CurrentForcing.from_csv: need >= 2 valid rows in {p} "
                f"(found {len(rows)}). Check column names: time_s + u_m_s/v_m_s "
                f"or time_s + speed_m_s/direction_deg."
            )

        rows.sort(key=lambda r: r[0])
        times = np.array([r[0] for r in rows])
        u_arr = np.array([r[1] for r in rows])
        v_arr = np.array([r[2] for r in rows])
        return cls(times, u_arr, v_arr, label=p.stem)

    # ── Export ────────────────────────────────────────────────────────────────

    def to_csv(self, path: Union[str, Path], fmt: str = 'cartesian') -> None:
        """
        Save to CSV.

        Parameters
        ----------
        fmt : 'cartesian' (u_m_s, v_m_s) or 'polar' (speed_m_s, direction_deg)
        """
        p = Path(path)
        with open(p, 'w', newline='', encoding='utf-8') as f:
            if fmt == 'polar':
                f.write('time_s,speed_m_s,direction_deg\n')
                for t, u, v in zip(self.times_s, self.u, self.v):
                    spd = math.hypot(u, v)
                    deg = math.degrees(math.atan2(u, v)) % 360.0
                    f.write(f"{t:.1f},{spd:.4f},{deg:.1f}\n")
            else:
                f.write('time_s,u_m_s,v_m_s\n')
                for t, u, v in zip(self.times_s, self.u, self.v):
                    f.write(f"{t:.1f},{u:.4f},{v:.4f}\n")

    def __repr__(self) -> str:
        return (
            f"CurrentForcing(label={self.label!r}, n={self.n_points}, "
            f"duration={self.duration_s:.0f}s, "
            f"mean_speed={self.mean_speed():.3f} m/s)"
        )
