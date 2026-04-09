"""
core/validation.py — Scenario and input validation for AquaGuard

validate_scenario(scenario) raises ValidationError if anything is wrong.
Prints a summary of checks to the console.

Sprint 2: basic geometric and config checks.
Sprint 3+: add per-site distance checks, domain coverage, forcing range checks.
"""
from __future__ import annotations

import math
from typing import List

from core.geometry import FjordScenario, Net, PolylineCoastline, Site, StraightCoastline


class ValidationError(Exception):
    """Raised when scenario validation fails."""


def validate_scenario(scenario: FjordScenario, raise_on_error: bool = True) -> List[str]:
    """
    Validate a FjordScenario.

    Parameters
    ----------
    scenario      : the scenario to check
    raise_on_error: if True (default), raise ValidationError on first failure;
                    if False, collect all errors and return as list.

    Returns
    -------
    List of error strings (empty if valid).
    """
    errors: List[str] = []
    warnings: List[str] = []

    def err(msg: str) -> None:
        errors.append(msg)
        if raise_on_error:
            raise ValidationError(msg)

    def warn(msg: str) -> None:
        warnings.append(msg)
        print(f"[validation] WARNING: {msg}")

    print(f"[validation] Validating scenario: '{scenario.name}'")

    # ── Coastline ─────────────────────────────────────────────────────────────
    if isinstance(scenario.coastline, PolylineCoastline):
        if len(scenario.coastline.vertices) < 2:
            err("PolylineCoastline must have at least 2 vertices.")
    elif isinstance(scenario.coastline, StraightCoastline):
        pass  # always valid
    else:
        err(f"Unknown coastline type: {type(scenario.coastline)}")

    # ── Sites ─────────────────────────────────────────────────────────────────
    if not scenario.sites:
        err("Scenario must have at least one site.")

    seen_ids = set()
    for site in scenario.sites:
        if not site.site_id:
            err(f"Site '{site.name}' has empty site_id.")
        if site.site_id in seen_ids:
            err(f"Duplicate site_id: '{site.site_id}'.")
        seen_ids.add(site.site_id)

        if not site.nets:
            warn(f"Site '{site.site_id}' has no nets.")

        for net in site.nets:
            _validate_net(net, site, err, warn)

    # ── Net overlaps ──────────────────────────────────────────────────────────
    all_nets = scenario.all_nets()
    for i, a in enumerate(all_nets):
        for b in all_nets[i + 1:]:
            dist = math.hypot(
                a.center[0] - b.center[0],
                a.center[1] - b.center[1],
            )
            if dist < a.radius + b.radius:
                warn(
                    f"Nets '{a.name}' and '{b.name}' overlap "
                    f"(distance={dist:.1f} m, sum of radii={a.radius+b.radius:.1f} m)."
                )

    # ── Nets above coastline ──────────────────────────────────────────────────
    if isinstance(scenario.coastline, StraightCoastline):
        y_c = scenario.coastline.y_coast
        for net in all_nets:
            if net.center[1] < y_c:
                err(
                    f"Net '{net.name}' center y={net.center[1]:.1f} m is below "
                    f"the coastline y={y_c:.1f} m (land side)."
                )
    elif isinstance(scenario.coastline, PolylineCoastline):
        for net in all_nets:
            if scenario.coastline.is_on_land(*net.center):
                warn(
                    f"Net '{net.name}' center appears to be on the land side "
                    f"of the PolylineCoastline."
                )

    # ── Domain ────────────────────────────────────────────────────────────────
    dom = scenario.domain
    if dom:
        x_range = dom.get('x', (None, None))
        y_range = dom.get('y', (None, None))
        if None not in x_range and x_range[0] >= x_range[1]:
            err(f"Domain x_min >= x_max: {x_range}")
        if None not in y_range and y_range[0] >= y_range[1]:
            err(f"Domain y_min >= y_max: {y_range}")
        nx = dom.get('nx', 1)
        ny = dom.get('ny', 1)
        if nx < 2 or ny < 2:
            err(f"Domain grid must have nx>=2 and ny>=2 (got nx={nx}, ny={ny}).")

    # ── Pathogen source ───────────────────────────────────────────────────────
    psrc = scenario.pathogen_source
    source_mode = psrc.get('source_mode', 'upstream_line')
    if source_mode not in {'upstream_line', 'infected_net'}:
        err(f"Invalid source_mode '{source_mode}'. Must be 'upstream_line' or 'infected_net'.")

    if source_mode == 'infected_net':
        source_site_id = psrc.get('source_site_id')
        source_net_name = psrc.get('source_net_name')
        if source_site_id and not scenario.site_by_id(source_site_id):
            err(f"source_site_id '{source_site_id}' not found in scenario sites.")
        if source_net_name:
            found_net = False
            for site in scenario.sites:
                if site.net_by_name(source_net_name):
                    found_net = True
                    break
            if not found_net:
                warn(
                    f"source_net_name '{source_net_name}' not found in any site."
                )

    for pos_key in ('source_load', 'diffusion_m2_s', 'base_inactivation_rate_1_s'):
        val = psrc.get(pos_key)
        if val is not None and float(val) < 0:
            err(f"pathogen_source['{pos_key}'] must be >= 0 (got {val}).")

    # ── Forcing ───────────────────────────────────────────────────────────────
    forcing = scenario.forcing
    fmode = forcing.get('mode', 'named_cases')
    if fmode not in {'named_cases', 'timeseries'}:
        err(f"Invalid forcing mode '{fmode}'. Must be 'named_cases' or 'timeseries'.")
    if fmode == 'named_cases':
        cases = forcing.get('cases', [])
        valid_cases = {'langs', 'tverrs', 'diagonal'}
        for c in cases:
            if c not in valid_cases:
                warn(f"Forcing case '{c}' is not one of the built-in directions {valid_cases}.")
        if not cases:
            warn("No forcing cases specified — will use default ['langs', 'tverrs', 'diagonal'].")

    # ── Report ────────────────────────────────────────────────────────────────
    if errors:
        print(f"[validation] FAILED — {len(errors)} error(s), {len(warnings)} warning(s).")
    else:
        print(
            f"[validation] OK — scenario '{scenario.name}' passed "
            f"({len(warnings)} warning(s))."
        )
    return errors


# ── Net-level checks ──────────────────────────────────────────────────────────

def _validate_net(net: Net, site: Site, err, warn) -> None:
    if net.radius <= 0:
        err(f"Net '{net.name}' in site '{site.site_id}': radius must be > 0.")
    if net.depth <= 0:
        warn(f"Net '{net.name}' in site '{site.site_id}': depth <= 0.")
    if not (0.0 <= net.solidity <= 1.0):
        err(
            f"Net '{net.name}' in site '{site.site_id}': "
            f"solidity {net.solidity} is outside [0, 1]."
        )
    if net.Cr <= 0:
        err(f"Net '{net.name}' in site '{site.site_id}': Cr must be > 0.")
