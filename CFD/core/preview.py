"""
core/preview.py — Geometry preview plot for AquaGuard scenarios

plot_geometry_preview(scenario) produces a single figure showing:
  - Coastline (polyline or straight)
  - All sites with their nets (coloured circles, labelled)
  - Domain boundary (dashed rectangle)
  - Source area / inlet line for each forcing case
  - Current direction arrows for each forcing case

Saves PNG to scenario output_dir and optionally displays it.

Sprint 2: standalone preview before analysis runs.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Union

os.environ.setdefault(
    'MPLCONFIGDIR',
    str(Path(tempfile.gettempdir()) / 'mplconfig_aquaguard'),
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from core.geometry import FjordScenario, PolylineCoastline, Site, StraightCoastline
from core.flow_engine import CoastalThreeNetFlowModel


# Colour cycle for sites
_SITE_COLOURS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
    '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
]
_NET_ALPHA = 0.35


def plot_geometry_preview(
    scenario: FjordScenario,
    output_dir: Optional[Union[str, Path]] = None,
    filename: str = 'aquaguard_geometry_preview.png',
    show: bool = False,
) -> Path:
    """
    Generate and save a geometry preview figure for the scenario.

    Parameters
    ----------
    scenario   : FjordScenario to preview
    output_dir : where to save the PNG (default: scenario_dir/output/)
    filename   : output filename
    show       : if True, call plt.show() (useful in Spyder with interactive backend)

    Returns
    -------
    Path to the saved PNG file.
    """
    if output_dir is None:
        base = Path(scenario.scenario_dir) if scenario.scenario_dir else Path.cwd()
        output_dir = base / 'output'
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(13, 8))

    dom = scenario.domain
    x_range = dom.get('x', (-300, 300))
    y_range = dom.get('y', (-200, 200))

    # ── Domain boundary ────────────────────────────────────────────────────────
    rect = mpatches.Rectangle(
        (x_range[0], y_range[0]),
        x_range[1] - x_range[0],
        y_range[1] - y_range[0],
        linewidth=1.5, edgecolor='#888888', facecolor='none',
        linestyle='--', zorder=1, label='Beregningsdomene',
    )
    ax.add_patch(rect)

    # ── Coastline ─────────────────────────────────────────────────────────────
    _draw_coastline(ax, scenario.coastline, x_range)

    # ── Sites and nets ────────────────────────────────────────────────────────
    for i, site in enumerate(scenario.sites):
        colour = _SITE_COLOURS[i % len(_SITE_COLOURS)]
        _draw_site(ax, site, colour)

    # ── Forcing arrows + source lines ─────────────────────────────────────────
    forcing = scenario.forcing
    cases = forcing.get('cases', ['langs', 'tverrs', 'diagonal'])
    if forcing.get('mode', 'named_cases') == 'named_cases':
        _draw_forcing_arrows(ax, cases, x_range, y_range)

    # ── Source inlet line for upstream_line mode ──────────────────────────────
    source_mode = scenario.pathogen_source.get('source_mode', 'upstream_line')
    if source_mode == 'upstream_line' and forcing.get('mode') == 'named_cases':
        _draw_source_lines(ax, cases, scenario, x_range, y_range)
    elif source_mode == 'infected_net':
        _draw_infected_net_source(ax, scenario)

    # ── Axes ──────────────────────────────────────────────────────────────────
    ax.set_xlim(x_range[0] - 20, x_range[1] + 20)
    ax.set_ylim(y_range[0] - 20, y_range[1] + 20)
    ax.set_aspect('equal')
    ax.set_xlabel('x [m]', fontsize=11)
    ax.set_ylabel('y [m]', fontsize=11)
    ax.set_title(
        f"AquaGuard — Geometriforhåndsvisning: '{scenario.name}'\n"
        f"{len(scenario.sites)} lokaliteter, "
        f"{sum(len(s.nets) for s in scenario.sites)} nøter",
        fontsize=12,
    )
    ax.grid(True, alpha=0.2)

    # ── Legend ────────────────────────────────────────────────────────────────
    handles = [rect]
    handles += [
        mpatches.Patch(
            facecolor=_SITE_COLOURS[i % len(_SITE_COLOURS)],
            alpha=_NET_ALPHA + 0.3,
            label=f"{site.name} ({site.site_id})",
        )
        for i, site in enumerate(scenario.sites)
    ]
    if source_mode == 'upstream_line':
        handles.append(
            mpatches.Patch(facecolor='#ffd700', alpha=0.6, label='Kildeinnløp (upstream)')
        )
    ax.legend(handles=handles, loc='upper right', fontsize=9, framealpha=0.85)

    out_path = out_dir / filename
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches='tight')
    if show:
        plt.show()
    plt.close(fig)
    print(f"[preview] Geometriforhåndsvisning lagret: {out_path}")
    return out_path


# =============================================================================
# Drawing helpers
# =============================================================================

def _draw_coastline(ax, coastline, x_range) -> None:
    if isinstance(coastline, PolylineCoastline):
        v = coastline.vertices
        ax.plot(v[:, 0], v[:, 1], color='saddlebrown', lw=3, zorder=3, label='Kystlinje')
        # Fill land below the polyline
        x_fill = np.concatenate([[x_range[0]], v[:, 0], [x_range[1]]])
        y_fill = np.concatenate([[v[0, 1]], v[:, 1], [v[-1, 1]]])
        y_bottom = min(v[:, 1]) - 60
        ax.fill_between(x_fill, y_bottom, y_fill, color='burlywood', alpha=0.85, zorder=2)
    elif isinstance(coastline, StraightCoastline):
        y_c = coastline.y_coast
        ax.axhline(y_c, color='saddlebrown', lw=3, zorder=3, label='Kystlinje (rett)')
        ax.fill_between(
            [x_range[0] - 50, x_range[1] + 50],
            y_c - 60, y_c,
            color='burlywood', alpha=0.85, zorder=2,
        )


def _draw_site(ax, site: Site, colour: str) -> None:
    # Site marker
    ax.plot(
        site.x, site.y, marker='s', color=colour,
        markersize=10, zorder=5, markeredgecolor='black', markeredgewidth=1.0,
    )
    ax.annotate(
        f"  {site.name}\n  ({site.site_id})",
        xy=(site.x, site.y), fontsize=8, color=colour,
        fontweight='bold', zorder=6,
    )
    # Nets
    for net in site.nets:
        circle = plt.Circle(
            net.center, net.radius,
            edgecolor=colour, facecolor=colour,
            alpha=_NET_ALPHA, lw=1.8, zorder=4,
        )
        ax.add_patch(circle)
        ax.text(
            net.center[0], net.center[1],
            f"S={net.solidity:.2f}",
            ha='center', va='center', fontsize=7, color='black', zorder=7,
        )


def _draw_forcing_arrows(ax, cases: list, x_range, y_range) -> None:
    """Draw current direction arrows in the upper-right corner of the domain."""
    arrow_origin_x = x_range[1] - 0.12 * (x_range[1] - x_range[0])
    arrow_origin_y = y_range[1] - 0.12 * (y_range[1] - y_range[0])
    arrow_len = 0.08 * (x_range[1] - x_range[0])

    case_colors = {'langs': '#1f77b4', 'tverrs': '#ff7f0e', 'diagonal': '#2ca02c'}
    offsets = [(0, 0), (0, -arrow_len * 1.6), (0, -arrow_len * 3.2)]

    for (dx, dy), case in zip(offsets, cases):
        vec = CoastalThreeNetFlowModel.case_vector(case)
        colour = case_colors.get(case, '#888888')
        ox = arrow_origin_x + dx
        oy = arrow_origin_y + dy
        ax.annotate(
            '',
            xy=(ox + vec[0] * arrow_len, oy + vec[1] * arrow_len),
            xytext=(ox, oy),
            arrowprops=dict(arrowstyle='->', color=colour, lw=2.0),
            zorder=8,
        )
        ax.text(
            ox + vec[0] * arrow_len * 1.15,
            oy + vec[1] * arrow_len * 1.15,
            case,
            color=colour, fontsize=8, fontweight='bold', zorder=9,
        )


def _draw_source_lines(ax, cases: list, scenario: FjordScenario, x_range, y_range) -> None:
    """Draw the upstream source inlet line for each named case."""
    # Build a minimal flow model to reuse _inlet_line logic
    try:
        flow_model = scenario.build_flow_model()
    except Exception:
        return

    from core.pathogen_transport import CoastalpathogenTimeMarcher

    dummy_cfg = dict(scenario.pathogen_source)
    dummy_cfg.setdefault('verbose', False)
    # Remove keys not in marcher constructor
    for k in ('source_site_id',):
        dummy_cfg.pop(k, None)

    try:
        marcher = CoastalpathogenTimeMarcher(flow_model, verbose=False, **{
            k: dummy_cfg[k]
            for k in dummy_cfg
            if k in CoastalpathogenTimeMarcher.__init__.__code__.co_varnames
        })
    except Exception:
        return

    case_colors = {'langs': '#1f77b4', 'tverrs': '#ff7f0e', 'diagonal': '#2ca02c'}

    for case in cases:
        try:
            case_dir = CoastalThreeNetFlowModel.case_vector(case)
            origin, ep, eta_range = marcher._inlet_line(case_dir)
            p0 = origin + eta_range[0] * ep
            p1 = origin + eta_range[1] * ep
            colour = case_colors.get(case, '#ffd700')
            ax.plot(
                [p0[0], p1[0]], [p0[1], p1[1]],
                color='#ffd700', lw=4, alpha=0.55, zorder=3,
                solid_capstyle='round',
            )
        except Exception:
            pass


def _draw_infected_net_source(ax, scenario: FjordScenario) -> None:
    """Highlight the source net when source_mode = 'infected_net'."""
    net_name = scenario.pathogen_source.get('source_net_name')
    site_id = scenario.pathogen_source.get('source_site_id')
    for site in scenario.sites:
        if site_id and site.site_id != site_id:
            continue
        for net in site.nets:
            if net_name and net.name != net_name:
                continue
            circle = plt.Circle(
                net.center, net.radius * 1.15,
                edgecolor='red', facecolor='red',
                alpha=0.25, lw=2.5, linestyle='--', zorder=6,
            )
            ax.add_patch(circle)
            ax.text(
                net.center[0], net.center[1] + net.radius * 1.3,
                'KILDE',
                ha='center', va='bottom', fontsize=8,
                color='red', fontweight='bold', zorder=7,
            )
