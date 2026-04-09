"""
core/scenarios_io.py — File-based scenario loading and saving

A scenario directory contains:
  coastline.csv        — polyline coastline vertices (x, y)
  sites.json           — site list with nets
  pathogen_source.json — source routing and biology settings
  forcing.json         — flow forcing configuration (named cases or timeseries ref)
  scenario.json        — metadata (name, description, domain override)

Usage:
    from core.scenarios_io import load_scenario, save_scenario_template
    scenario = load_scenario('scenarios/example_fjord')
    save_scenario_template('scenarios/my_new_fjord')

Sprint 2: load / save / template generation.
Sprint 4: CurrentForcing loaded from currents.csv; template file added.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from core.forcing import CurrentForcing
from core.geometry import (
    FjordScenario,
    Net,
    PolylineCoastline,
    Site,
    StraightCoastline,
)
from core.scenarios import (
    COAST_USER_SETTINGS,
    DOMAIN_USER_SETTINGS,
    PATHOGEN_USER_SETTINGS,
    RISK_USER_SETTINGS,
    RUN_USER_SETTINGS,
)


# =============================================================================
# Loading
# =============================================================================

def load_scenario(scenario_dir: Union[str, Path]) -> FjordScenario:
    """
    Load a FjordScenario from a directory.

    Required files: sites.json
    Optional files: coastline.csv, pathogen_source.json, forcing.json, scenario.json

    Missing optional files fall back to module-level defaults from scenarios.py.
    """
    d = Path(scenario_dir).resolve()
    if not d.is_dir():
        raise FileNotFoundError(f"Scenario directory not found: {d}")

    print(f"[scenarios_io] Loading scenario from: {d}")

    # ── scenario.json (metadata + optional domain override) ──────────────────
    meta = _load_json_or_default(d / 'scenario.json', {})
    name = meta.get('name', d.name)
    description = meta.get('description', '')
    domain_override = meta.get('domain', None)

    # ── coastline ────────────────────────────────────────────────────────────
    coastline_path = d / 'coastline.csv'
    if coastline_path.exists():
        coastline = PolylineCoastline.from_csv(coastline_path)
        print(f"[scenarios_io]   coastline.csv: {len(coastline.vertices)} vertices")
    else:
        coastline = StraightCoastline(**COAST_USER_SETTINGS)
        print(f"[scenarios_io]   coastline.csv not found — using StraightCoastline default")

    # ── sites ─────────────────────────────────────────────────────────────────
    sites_path = d / 'sites.json'
    if not sites_path.exists():
        raise FileNotFoundError(f"sites.json is required but not found in {d}")
    sites = _load_sites(sites_path)
    print(f"[scenarios_io]   sites.json: {len(sites)} sites, "
          f"{sum(len(s.nets) for s in sites)} nets total")

    # ── pathogen source ───────────────────────────────────────────────────────
    source_path = d / 'pathogen_source.json'
    pathogen_source = _load_json_or_default(source_path, _default_pathogen_source())
    if source_path.exists():
        print(f"[scenarios_io]   pathogen_source.json loaded")
    else:
        print(f"[scenarios_io]   pathogen_source.json not found — using defaults")

    # ── forcing ───────────────────────────────────────────────────────────────
    forcing_path = d / 'forcing.json'
    forcing = _load_json_or_default(forcing_path, _default_forcing())
    if forcing_path.exists():
        print(f"[scenarios_io]   forcing.json loaded: mode={forcing.get('mode')}")
    else:
        print(f"[scenarios_io]   forcing.json not found — using named_cases default")

    # Load CurrentForcing when mode is 'timeseries'
    if forcing.get('mode') == 'timeseries':
        ts_file = forcing.get('timeseries_file') or 'currents.csv'
        ts_path = d / ts_file
        if ts_path.exists():
            forcing['_current_forcing'] = CurrentForcing.from_csv(ts_path)
            stats = forcing['_current_forcing'].summary_stats()
            print(
                f"[scenarios_io]   {ts_file}: {stats['n_points']} points, "
                f"duration={stats['duration_s']:.0f}s, "
                f"mean_speed={stats['mean_speed_m_s']:.3f} m/s"
            )
        else:
            raise FileNotFoundError(
                f"forcing.mode='timeseries' but '{ts_file}' not found in {d}"
            )

    # ── domain ────────────────────────────────────────────────────────────────
    if domain_override:
        domain = domain_override
        print(f"[scenarios_io]   domain: from scenario.json override")
    else:
        domain = FjordScenario.auto_domain(sites, coastline)
        print(
            f"[scenarios_io]   domain: auto-computed "
            f"x={domain['x']}, y={domain['y']}"
        )

    return FjordScenario(
        name=name,
        sites=sites,
        coastline=coastline,
        domain=domain,
        pathogen_source=pathogen_source,
        forcing=forcing,
        description=description,
        scenario_dir=str(d),
    )


# =============================================================================
# Saving / template generation
# =============================================================================

def save_scenario_template(
    scenario_dir: Union[str, Path],
    n_sites: int = 2,
    overwrite: bool = False,
) -> None:
    """
    Write a complete example scenario directory that users can edit.

    Parameters
    ----------
    scenario_dir : path to create
    n_sites      : 1 or 2 sites in the template
    overwrite    : if False (default), skip files that already exist
    """
    d = Path(scenario_dir).resolve()
    d.mkdir(parents=True, exist_ok=True)
    print(f"[scenarios_io] Writing template to: {d}")

    _write_if_new(d / 'scenario.json', _template_scenario_json(d.name), overwrite)
    _write_if_new(d / 'coastline.csv', _template_coastline_csv(), overwrite)
    _write_if_new(d / 'sites.json', _template_sites_json(n_sites), overwrite)
    _write_if_new(d / 'pathogen_source.json',
                  json.dumps(_default_pathogen_source(), indent=2, ensure_ascii=False),
                  overwrite)
    _write_if_new(d / 'forcing.json',
                  json.dumps(_default_forcing(), indent=2, ensure_ascii=False),
                  overwrite)
    _write_if_new(d / 'currents.csv', _template_currents_csv(), overwrite)
    print(f"[scenarios_io] Template ready. Edit files in {d} then call load_scenario().")


def save_scenario(scenario: FjordScenario, out_dir: Union[str, Path]) -> None:
    """Persist the current state of a FjordScenario back to disk."""
    d = Path(out_dir).resolve()
    d.mkdir(parents=True, exist_ok=True)

    if isinstance(scenario.coastline, PolylineCoastline):
        scenario.coastline.to_csv(d / 'coastline.csv')

    sites_data = {'sites': [_site_to_dict(s) for s in scenario.sites]}
    (d / 'sites.json').write_text(
        json.dumps(sites_data, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    (d / 'pathogen_source.json').write_text(
        json.dumps(scenario.pathogen_source, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    (d / 'forcing.json').write_text(
        json.dumps(scenario.forcing, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    meta = {
        'name': scenario.name,
        'description': scenario.description,
        'domain': scenario.domain,
    }
    (d / 'scenario.json').write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    print(f"[scenarios_io] Scenario '{scenario.name}' saved to {d}")


# =============================================================================
# Internal helpers
# =============================================================================

def _load_json_or_default(path: Path, default: dict) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return default


def _load_sites(path: Path) -> List[Site]:
    data = json.loads(path.read_text(encoding='utf-8'))
    raw_sites = data.get('sites', data) if isinstance(data, dict) else data
    sites = []
    for s in raw_sites:
        nets = _build_nets(
            s.get('nets', []),
            site_x=float(s.get('x', 0.0)),
            site_y=float(s.get('y', 0.0)),
        )
        sites.append(Site(
            site_id=str(s.get('site_id', s.get('id', f"SITE_{len(sites)+1}"))),
            name=str(s.get('name', s.get('site_id', f"Site {len(sites)+1}"))),
            x=float(s.get('x', 0.0)),
            y=float(s.get('y', 0.0)),
            nets=nets,
            site_type=str(s.get('site_type', 'production')),
            lat=float(s.get('lat', 0.0)),
            lon=float(s.get('lon', 0.0)),
            metadata=s.get('metadata', {}),
        ))
    return sites


def _build_nets(raw_nets: list, site_x: float, site_y: float) -> List[Net]:
    nets = []
    for n in raw_nets:
        # Accept either absolute 'center' [x, y] or 'center_offset' [dx, dy]
        if 'center' in n:
            cx, cy = float(n['center'][0]), float(n['center'][1])
        elif 'center_offset' in n:
            cx = site_x + float(n['center_offset'][0])
            cy = site_y + float(n['center_offset'][1])
        else:
            cx, cy = site_x, site_y
        nets.append(Net(
            name=str(n.get('name', f"Net {len(nets)+1}")),
            center=(cx, cy),
            radius=float(n.get('radius', 25.0)),
            depth=float(n.get('depth', 5.0)),
            solidity=float(n.get('solidity', 0.25)),
            Cr=float(n.get('Cr', 0.8)),
        ))
    return nets


def _site_to_dict(site: Site) -> dict:
    return {
        'site_id': site.site_id,
        'name': site.name,
        'x': site.x,
        'y': site.y,
        'site_type': site.site_type,
        'lat': site.lat,
        'lon': site.lon,
        'nets': [
            {
                'name': n.name,
                'center': list(n.center),
                'radius': n.radius,
                'depth': n.depth,
                'solidity': n.solidity,
                'Cr': n.Cr,
            }
            for n in site.nets
        ],
        'metadata': site.metadata,
    }


def _default_pathogen_source() -> dict:
    src = {k: PATHOGEN_USER_SETTINGS[k] for k in PATHOGEN_USER_SETTINGS}
    src.update({
        'source_site_id': None,      # None = regional upstream line
        'source_net_name': None,
    })
    return src


def _default_forcing() -> dict:
    return {
        'mode': 'named_cases',
        'cases': list(RUN_USER_SETTINGS['cases']),
        'U_inf': 0.5,
        # Sprint 4+: timeseries forcing
        'timeseries_file': None,
    }


def _write_if_new(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        print(f"[scenarios_io]   SKIP (exists): {path.name}")
        return
    path.write_text(content, encoding='utf-8')
    print(f"[scenarios_io]   WRITE: {path.name}")


# =============================================================================
# Template content generators
# =============================================================================

def _template_scenario_json(name: str) -> str:
    meta = {
        'name': name,
        'description': 'Example fjord scenario — edit sites.json and coastline.csv to customise.',
        'domain': None,   # null = auto-compute from site positions
    }
    return json.dumps(meta, indent=2, ensure_ascii=False)


def _template_coastline_csv() -> str:
    lines = ['x,y']
    # Slightly curved coastline, roughly east-west
    pts = [
        (-350, -155), (-250, -162), (-150, -148), (-50, -158),
        (0, -150), (50, -143), (150, -152), (250, -145), (350, -148),
    ]
    for x, y in pts:
        lines.append(f"{x},{y}")
    return '\n'.join(lines) + '\n'


def _template_sites_json(n_sites: int) -> str:
    sites = [
        {
            'site_id': 'SITE_A',
            'name': 'Anlegg A (vest)',
            'x': -100.0,
            'y': 0.0,
            'site_type': 'production',
            'lat': 0.0,
            'lon': 0.0,
            'nets': [
                {
                    'name': 'A-Not 1',
                    'center_offset': [-30.0, 0.0],
                    'radius': 25.0,
                    'depth': 5.0,
                    'solidity': 0.25,
                    'Cr': 0.8,
                },
                {
                    'name': 'A-Not 2',
                    'center_offset': [30.0, 0.0],
                    'radius': 25.0,
                    'depth': 5.0,
                    'solidity': 0.60,
                    'Cr': 0.8,
                },
            ],
        },
    ]
    if n_sites >= 2:
        sites.append({
            'site_id': 'SITE_B',
            'name': 'Anlegg B (øst)',
            'x': 150.0,
            'y': 15.0,
            'site_type': 'production',
            'lat': 0.0,
            'lon': 0.0,
            'nets': [
                {
                    'name': 'B-Not 1',
                    'center_offset': [0.0, 0.0],
                    'radius': 25.0,
                    'depth': 5.0,
                    'solidity': 0.95,
                    'Cr': 0.8,
                },
            ],
        })
    return json.dumps({'sites': sites}, indent=2, ensure_ascii=False)


def _template_currents_csv() -> str:
    """
    Generate a template currents.csv with a 20-minute tidal-ish cycle.

    Format A (Cartesian): time_s, u_m_s (East), v_m_s (North).
    Replace with real observations or NorShelf model output for production use.
    """
    import math
    lines = ['time_s,u_m_s,v_m_s']
    # 1200 s total, dt=120 s — 11 rows
    # Sinusoidal variation: dominant eastward (langs) with northward tidal modulation
    T_tidal = 1200.0
    for i in range(11):
        t = i * 120.0
        phase = 2.0 * math.pi * t / T_tidal
        u = 0.40 + 0.15 * math.cos(phase)           # 0.25 – 0.55 m/s eastward
        v = -0.10 * math.sin(phase)                  # ±0.10 m/s northward oscillation
        lines.append(f"{t:.1f},{u:.4f},{v:.4f}")
    return '\n'.join(lines) + '\n'
