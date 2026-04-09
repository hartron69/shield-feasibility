"""
main_v123.py — AquaGuard v1.23 entry point

Sprint 1: modularized from aquaguard_three_nets_pathogen_coast_status_v1.22b.py.
Sprint 2: file-driven scenarios via run_from_scenario_dir().
Sprint 3: PolylineCoastline physics; multi-site analysis via run_multi_site_scenario().
Sprint 5: Physical transfer engine via run_transfer_analysis().

Usage (Spyder / terminal):

  # Classic single-site demo (identical to v1.22b):
    from main_v123 import run_demo
    outputs = run_demo()

  # File-driven scenario (Sprint 2+):
    from main_v123 import run_from_scenario_dir
    outputs = run_from_scenario_dir('scenarios/example_fjord')

  # Multi-site transfer analysis (Sprint 3+):
    from main_v123 import run_multi_site_scenario
    outputs = run_multi_site_scenario('scenarios/example_fjord')

  # Physical transfer engine (Sprint 5):
    from main_v123 import run_transfer_analysis
    library = run_transfer_analysis('scenarios/example_fjord')
    print(library.risk_matrix())
    print(library.transfer_matrix())

  # MC transfer library (Sprint 6):
    from main_v123 import build_mc_library, load_mc_library
    mc_lib = build_mc_library('scenarios/example_fjord', n_ensemble=5)
    mc_lib2 = load_mc_library('scenarios/example_fjord')
    rng = __import__('numpy').random.default_rng(0)
    print(mc_lib.sample_tc('SITE_A', 'SITE_A', n=5, rng=rng))

  # Create a new scenario template to customise:
    from main_v123 import create_scenario_template
    create_scenario_template('scenarios/my_fjord')

   # from main_v123 import run_from_scenario_dir
   outputs = run_from_scenario_dir(
    r'C:\\Users\\haral\\dev\\shield-feasibility\\CFD\\scenarios\\example_fjord'
    )
   print(outputs['summary'])

Or run directly:
    python main_v123.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.transfer_engine import TransferLibrary
    from core.transfer_library import MCTransferLibrary
    from core.mc_risk_engine import MonteCarloRiskEngine as _MCRiskEngine

# Ensure MPLCONFIGDIR is writable before any matplotlib import
os.environ.setdefault(
    'MPLCONFIGDIR',
    str(Path(tempfile.gettempdir()) / 'mplconfig_aquaguard'),
)

# Add CFD directory to path so `core` package is importable from Spyder
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pandas as pd

from core.flow_engine import CoastalThreeNetFlowModel
from core.pathogen_transport import CoastalpathogenTimeMarcher
from core.scenarios import (
    FLOW_USER_SETTINGS,
    NET_USER_SETTINGS,
    COAST_USER_SETTINGS,
    DOMAIN_USER_SETTINGS,
    PATHOGEN_USER_SETTINGS,
    RISK_USER_SETTINGS,
    RUN_USER_SETTINGS,
    pathogen_USER_SETTINGS,
)
from core.scenarios_io import load_scenario, save_scenario_template
from core.validation import validate_scenario
from core.preview import plot_geometry_preview


def print_user_settings() -> None:
    """Print all active user settings to the console."""
    print('=== USER SETTINGS (v1.23) ===')
    print('FLOW_USER_SETTINGS =', FLOW_USER_SETTINGS)
    print('NET_USER_SETTINGS =', NET_USER_SETTINGS)
    print('COAST_USER_SETTINGS =', COAST_USER_SETTINGS)
    print('DOMAIN_USER_SETTINGS =', DOMAIN_USER_SETTINGS)
    print('PATHOGEN_USER_SETTINGS =', PATHOGEN_USER_SETTINGS)
    print('RISK_USER_SETTINGS =', RISK_USER_SETTINGS)
    print('RUN_USER_SETTINGS =', RUN_USER_SETTINGS)


def run_demo(verbose: bool | None = None) -> dict:
    """
    Run the standard demo using settings from core/scenarios.py.

    Identical output to v1.22b run_demo(). All parameters are read from
    USER_SETTINGS in core/scenarios.py — edit there to change the scenario.

    Parameters
    ----------
    verbose : bool, optional
        Override the verbose flag from PATHOGEN_USER_SETTINGS.

    Returns
    -------
    dict with keys: 'results', 'summary', 'summary_path', 'metadata_path'
    """
    model = CoastalThreeNetFlowModel()

    pathogen_cfg = dict(PATHOGEN_USER_SETTINGS)
    pathogen_cfg.update(RISK_USER_SETTINGS)

    if verbose is not None:
        pathogen_cfg['verbose'] = bool(verbose)

    marcher = CoastalpathogenTimeMarcher(model, **pathogen_cfg)
    return marcher.run_all(case_list=list(RUN_USER_SETTINGS['cases']))


def run_from_scenario_dir(
    scenario_dir,
    verbose: bool = True,
    preview: bool = True,
    validate: bool = True,
) -> dict:
    """
    Run a full analysis from a file-based scenario directory.

    Steps:
      1. Load scenario from JSON/CSV files
      2. Validate scenario (raises ValidationError on error)
      3. Plot geometry preview
      4. Run pathogen transport for all forcing cases

    Parameters
    ----------
    scenario_dir : path to directory containing sites.json, coastline.csv, etc.
    verbose      : log progress to console
    preview      : generate and save geometry preview PNG
    validate     : run scenario validation before analysis

    Returns
    -------
    dict with keys: 'scenario', 'results', 'summary', 'summary_path',
                    'metadata_path', 'preview_path' (if preview=True)
    """
    d = Path(scenario_dir).resolve()
    print(f"\n{'='*60}")
    print(f"AquaGuard v1.23 — Fil-styrt scenario: {d.name}")
    print(f"{'='*60}\n")

    # 1. Load
    scenario = load_scenario(d)

    # 2. Validate
    if validate:
        validate_scenario(scenario, raise_on_error=True)

    # 3. Preview
    output_dir = d / 'output'
    preview_path = None
    if preview:
        preview_path = plot_geometry_preview(scenario, output_dir=output_dir)

    # 4. Build flow model and run
    forcing = scenario.forcing
    U_inf = float(forcing.get('U_inf', FLOW_USER_SETTINGS['U_inf']))

    # Sprint 4: resolve case list and optional CurrentForcing
    current_forcing = forcing.get('_current_forcing', None)   # set by load_scenario
    if forcing.get('mode') == 'timeseries' and current_forcing is not None:
        # Single synthetic case name representing the full time series
        case_list = ['timeseries']
    else:
        case_list = forcing.get('cases', list(RUN_USER_SETTINGS['cases']))

    flow_model = scenario.build_flow_model(U_inf=U_inf, output_dir=output_dir)

    # Merge pathogen source settings with risk settings
    psrc = dict(scenario.pathogen_source)
    # Remove scenario-only keys not recognised by CoastalpathogenTimeMarcher
    for k in ('source_site_id',):
        psrc.pop(k, None)

    # Fill in risk thresholds from RISK_USER_SETTINGS defaults where not set
    for k, v in RISK_USER_SETTINGS.items():
        psrc.setdefault(k, v)

    psrc['verbose'] = verbose
    psrc['current_forcing'] = current_forcing  # None for named-case mode

    marcher = CoastalpathogenTimeMarcher(flow_model, **psrc)
    analysis = marcher.run_all(case_list=case_list)

    print(f"\n{'='*60}")
    print(f"Analyse fullført for scenario '{scenario.name}'")
    print(f"{'='*60}")
    cols = ['case_name', 'site_id', 'net', 'risk_status',
            'first_arrival_min', 'peak_relative_risk_concentration',
            'total_risk_exposure_mass_seconds']
    avail = [c for c in cols if c in analysis['summary'].columns]
    print(analysis['summary'][avail].to_string())

    return {
        'scenario': scenario,
        'preview_path': preview_path,
        **analysis,
    }


def run_multi_site_scenario(
    scenario_dir,
    verbose: bool = True,
    preview: bool = True,
    validate: bool = True,
) -> dict:
    """
    Run a site-to-site transfer analysis for a multi-site scenario.

    For each site that contains at least one net, the pathogen is seeded from
    that site's nets (infected_net mode) and transport to all other sites' nets
    is recorded.  Results are combined into a single summary DataFrame with
    columns ``source_site_id`` and ``site_id`` (target).

    A transfer matrix (worst risk status per source→target pair across all
    forcing cases) is printed and returned as ``outputs['transfer_matrix']``.

    Parameters
    ----------
    scenario_dir : path to scenario directory
    verbose, preview, validate : same as run_from_scenario_dir

    Returns
    -------
    dict with keys: 'scenario', 'site_results', 'summary',
                    'transfer_matrix', 'preview_path'
    """
    d = Path(scenario_dir).resolve()
    print(f"\n{'='*60}")
    print(f"AquaGuard v1.23 — Multi-site analyse: {d.name}")
    print(f"{'='*60}\n")

    from core.scenarios_io import load_scenario
    from core.validation import validate_scenario
    from core.preview import plot_geometry_preview

    scenario = load_scenario(d)

    if validate:
        validate_scenario(scenario, raise_on_error=True)

    output_dir = d / 'output'
    preview_path = None
    if preview:
        preview_path = plot_geometry_preview(scenario, output_dir=output_dir)

    forcing = scenario.forcing
    U_inf = float(forcing.get('U_inf', FLOW_USER_SETTINGS['U_inf']))
    current_forcing = forcing.get('_current_forcing', None)
    if forcing.get('mode') == 'timeseries' and current_forcing is not None:
        case_list = ['timeseries']
    else:
        case_list = forcing.get('cases', list(RUN_USER_SETTINGS['cases']))

    # Build shared flow model (all sites' nets in a single field)
    flow_model = scenario.build_flow_model(U_inf=U_inf, output_dir=output_dir)

    # Merge risk settings with pathogen source defaults
    psrc_base = dict(scenario.pathogen_source)
    for k in ('source_site_id',):
        psrc_base.pop(k, None)
    for k, v in RISK_USER_SETTINGS.items():
        psrc_base.setdefault(k, v)
    psrc_base['verbose'] = verbose
    psrc_base['current_forcing'] = current_forcing

    site_results: dict = {}
    all_summaries = []

    sites_with_nets = [s for s in scenario.sites if s.nets]
    if not sites_with_nets:
        print("Ingen lokaliteter med nøter funnet. Ingen analyse å kjøre.")
        return {'scenario': scenario, 'site_results': {}, 'summary': pd.DataFrame(),
                'transfer_matrix': pd.DataFrame(), 'preview_path': preview_path}

    for src_site in sites_with_nets:
        print(f"\n--- Kilde-lokalitet: {src_site.site_id} ({src_site.name}) ---")
        psrc = dict(psrc_base)
        psrc['source_mode'] = 'infected_net'
        # Use the first net of this site as the seeding net
        psrc['source_net_name'] = src_site.nets[0].name
        # Reset auto-calibrate per source run so thresholds recalibrate each time
        psrc['auto_calibrate_from_first_case'] = True

        marcher = CoastalpathogenTimeMarcher(flow_model, **psrc)
        analysis = marcher.run_all(case_list=case_list)

        site_results[src_site.site_id] = analysis
        # The source_site_id column is auto-set from site_assignments in run_case
        all_summaries.append(analysis['summary'])

    summary = pd.concat(all_summaries, ignore_index=True)

    # Build transfer matrix: source_site_id × target site_id → worst risk
    _order = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}
    transfer_rows = []
    for src_id, grp in summary.groupby('source_site_id'):
        for tgt_id, tgrp in grp.groupby('site_id'):
            if not tgt_id:
                tgt_id = '(unknown)'
            worst_status = max(
                tgrp['risk_status'].tolist(),
                key=lambda s: _order.get(str(s).upper(), 0),
            )
            transfer_rows.append({
                'source_site_id': src_id,
                'target_site_id': tgt_id,
                'worst_risk_status': worst_status,
            })
    transfer_matrix = (
        pd.DataFrame(transfer_rows)
        .pivot(index='source_site_id', columns='target_site_id', values='worst_risk_status')
        if transfer_rows else pd.DataFrame()
    )

    print(f"\n{'='*60}")
    print("Overforingsmatrise (verste risikostatus per kilde -> mal):")
    print(transfer_matrix.to_string() if not transfer_matrix.empty else '  (ingen resultater)')
    print(f"{'='*60}")

    return {
        'scenario': scenario,
        'site_results': site_results,
        'summary': summary,
        'transfer_matrix': transfer_matrix,
        'preview_path': preview_path,
    }


def run_transfer_analysis(
    scenario_dir,
    verbose: bool = True,
    preview: bool = True,
    validate: bool = True,
    shedding_rate_relative_per_s: float = 1.0,
    dt_s: float = 10.0,
    total_time_s: float = 1200.0,
    particles_per_step: int = 9,
) -> 'TransferLibrary':
    """
    Run the physical transfer engine for a scenario directory (Sprint 5).

    For each site that contains at least one net the pathogen is shed from
    that site's primary net and transport to every other net is computed.
    Normalised transfer coefficients and peak mass fractions are returned in
    a TransferLibrary alongside the full flat result table.

    Parameters
    ----------
    scenario_dir           : path to scenario directory
    verbose                : log progress to console
    preview                : generate geometry preview
    validate               : validate scenario files before run
    shedding_rate_relative_per_s : relative shedding rate [mass/s] for source
    dt_s                   : time step [s]
    total_time_s           : simulation duration [s]
    particles_per_step     : Lagrangian particles released per time step

    Returns
    -------
    TransferLibrary  (also saved to scenario_dir/output/)
    """
    from core.transfer_engine import TransferEngine, TransferLibrary

    d = Path(scenario_dir).resolve()
    print(f"\n{'='*60}")
    print(f"AquaGuard v1.23 — Transfer Engine: {d.name}")
    print(f"{'='*60}\n")

    scenario = load_scenario(d)

    if validate:
        validate_scenario(scenario, raise_on_error=True)

    output_dir = d / 'output'
    if preview:
        plot_geometry_preview(scenario, output_dir=output_dir)

    forcing = scenario.forcing
    current_forcing = forcing.get('_current_forcing', None)
    if forcing.get('mode') == 'timeseries' and current_forcing is not None:
        case_list = ['timeseries']
    else:
        case_list = forcing.get('cases', list(RUN_USER_SETTINGS['cases']))

    # Build marcher kwargs from scenario + risk defaults
    psrc = dict(scenario.pathogen_source)
    for k in ('source_site_id',):
        psrc.pop(k, None)
    for k, v in RISK_USER_SETTINGS.items():
        psrc.setdefault(k, v)

    # Override with function-level params
    psrc['shedding_rate_relative_per_s'] = shedding_rate_relative_per_s
    psrc['dt_s'] = dt_s
    psrc['total_time_s'] = total_time_s
    psrc['particles_per_step'] = particles_per_step

    engine = TransferEngine(psrc, verbose=verbose)
    library = engine.run_all_pairs(
        scenario=scenario,
        output_dir=output_dir,
        current_forcing=current_forcing,
        case_list=case_list,
    )

    print(f"\n{'='*60}")
    print(f"Transfer Engine ferdig — {len(library.results)} resultater")
    print(f"{'='*60}")
    print("\nRisikomatrise (verste status per kilde -> mal):")
    rm = library.risk_matrix()
    print(rm.to_string() if not rm.empty else "  (ingen resultater)")
    print("\nOverforingskoeffisient-matrise (max tc [s] per kilde -> mal):")
    tc = library.transfer_matrix('transfer_coefficient_s', 'max')
    print(tc.to_string() if not tc.empty else "  (ingen resultater)")
    print(f"{'='*60}\n")

    return library


def build_mc_library(
    scenario_dir,
    n_ensemble: int = 10,
    base_seed: int = 0,
    verbose: bool = True,
    preview: bool = True,
    validate: bool = True,
    shedding_rate_relative_per_s: float = 1.0,
    dt_s: float = 10.0,
    total_time_s: float = 1200.0,
    particles_per_step: int = 9,
) -> 'MCTransferLibrary':
    """
    Build a Monte-Carlo transfer library for a scenario directory (Sprint 6).

    Runs the transfer engine n_ensemble times with different random seeds,
    fits lognormal distributions to the transfer coefficients, and returns
    a queryable MCTransferLibrary.

    Outputs saved to scenario_dir/output/:
      ensemble/run_NNN/           — per-run CSV and JSON
      ensemble_results.csv        — all runs combined
      mc_transfer_library.json    — fitted distributions (load with load_mc_library)
      mc_distribution_summary.csv — flat table of distribution parameters

    Parameters
    ----------
    scenario_dir  : path to scenario directory
    n_ensemble    : number of ensemble members (different random seeds)
    base_seed     : first random seed; member i uses base_seed + i
    verbose       : log progress
    preview, validate : same as run_transfer_analysis

    Returns
    -------
    MCTransferLibrary
    """
    from core.transfer_library import EnsembleRunner, MCTransferLibrary as _MCLib

    d = Path(scenario_dir).resolve()
    print(f"\n{'='*60}")
    print(f"AquaGuard v1.23 — MC Library Builder: {d.name}")
    print(f"n_ensemble={n_ensemble} | base_seed={base_seed}")
    print(f"{'='*60}\n")

    scenario = load_scenario(d)

    if validate:
        validate_scenario(scenario, raise_on_error=True)

    output_dir = d / 'output'
    if preview:
        plot_geometry_preview(scenario, output_dir=output_dir)

    forcing = scenario.forcing
    current_forcing = forcing.get('_current_forcing', None)
    if forcing.get('mode') == 'timeseries' and current_forcing is not None:
        case_list = ['timeseries']
    else:
        case_list = forcing.get('cases', list(RUN_USER_SETTINGS['cases']))

    psrc = dict(scenario.pathogen_source)
    for k in ('source_site_id',):
        psrc.pop(k, None)
    for k, v in RISK_USER_SETTINGS.items():
        psrc.setdefault(k, v)
    psrc['shedding_rate_relative_per_s'] = shedding_rate_relative_per_s
    psrc['dt_s'] = dt_s
    psrc['total_time_s'] = total_time_s
    psrc['particles_per_step'] = particles_per_step

    runner = EnsembleRunner(psrc, n_ensemble=n_ensemble, base_seed=base_seed, verbose=verbose)
    ensemble = runner.build(
        scenario=scenario,
        output_dir=output_dir,
        current_forcing=current_forcing,
        case_list=case_list,
        save_runs=True,
    )

    if verbose:
        ensemble.save(output_dir, log_func=print)

    mc_lib = ensemble.to_mc_library()
    mc_lib.save(output_dir, log_func=print if verbose else None)

    print(f"\n{'='*60}")
    print(f"MC Library ferdig — {mc_lib.n_ensemble} ensemble-kjøringer")
    print(f"{'='*60}")
    summary = mc_lib.risk_summary_df()
    if not summary.empty:
        tc_cols = ['source_site_id', 'target_site_id', 'mean_tc_s', 'p50_tc_s',
                   'p90_tc_s', 'zero_fraction', 'dist_type']
        avail = [c for c in tc_cols if c in summary.columns]
        print(summary[avail].to_string(index=False))
    print(f"\nForventet dose-matrise (shed_rate=1.0):")
    dose = mc_lib.expected_dose_matrix(shed_rate=1.0)
    print(dose.round(2).to_string() if not dose.empty else "  (ingen resultater)")
    print(f"{'='*60}\n")

    return mc_lib


def run_mc_risk(
    scenario_dir,
    n_samples: int = 10_000,
    shed_rate: float = 1.0,
    n_ensemble: int = 10,
    rebuild_library: bool = False,
    verbose: bool = True,
    seed: int = 42,
    dt_s: float = 10.0,
    total_time_s: float = 1200.0,
    particles_per_step: int = 9,
) -> dict:
    """
    Run probabilistic Monte Carlo risk analysis for a scenario (Sprint 7).

    If an MCTransferLibrary is already saved in scenario_dir/output/ it is
    loaded directly (fast).  Set rebuild_library=True to re-run the ensemble.

    Parameters
    ----------
    scenario_dir    : path to scenario directory
    n_samples       : MC sample count per (source, target) pair
    shed_rate       : shedding rate multiplier (1.0 = library default)
    n_ensemble      : ensemble size if library must be (re)built
    rebuild_library : force rebuild even if library exists
    verbose         : print progress and results
    seed            : random seed for MC sampling
    dt_s, total_time_s, particles_per_step : transport params for rebuild

    Returns
    -------
    dict with keys:
      'mc_library'  : MCTransferLibrary
      'results'     : List[MCRiskResult]
      'summary_df'  : pd.DataFrame
      'p_red_matrix': pd.DataFrame  — P(RED) pivot
      'modal_matrix': pd.DataFrame  — modal risk status pivot
    """
    from core.transfer_library import MCTransferLibrary as _MCLib
    from core.mc_risk_engine import MonteCarloRiskEngine

    d = Path(scenario_dir).resolve()
    output_dir = d / 'output'
    mc_json = output_dir / 'mc_transfer_library.json'

    print(f"\n{'='*60}")
    print(f"AquaGuard v1.23 — MC Risk Engine: {d.name}")
    print(f"n_samples={n_samples} | shed_rate={shed_rate}")
    print(f"{'='*60}\n")

    # Load or build MCTransferLibrary
    if mc_json.exists() and not rebuild_library:
        mc_lib = _MCLib.load(output_dir)
        if verbose:
            print(f"Lastet bibliotek: {mc_lib}")
    else:
        if verbose:
            print("Bygger MC-bibliotek (dette tar tid) ...")
        mc_lib = build_mc_library(
            scenario_dir,
            n_ensemble=n_ensemble,
            verbose=verbose,
            preview=False,
            validate=True,
            dt_s=dt_s,
            total_time_s=total_time_s,
            particles_per_step=particles_per_step,
        )

    engine = MonteCarloRiskEngine(
        mc_lib,
        n_samples=n_samples,
        shed_rate=shed_rate,
        total_time_s=total_time_s,
        seed=seed,
    )
    results = engine.run_all()

    paths = engine.save_results(results, output_dir, log_func=print if verbose else None)

    summary = engine.summary_df(results)
    p_red = engine.risk_probability_matrix('RED', results)
    modal = engine.modal_risk_matrix(results)
    score = engine.expected_risk_score_matrix(results)

    print(f"\n{'='*60}")
    print(f"MC Risikoanalyse ferdig — {len(results)} par | {n_samples} samples")
    print(f"{'='*60}")
    print("\nModal risikostatus (meste sannsynlige utfall):")
    print(modal.to_string() if not modal.empty else "  (ingen resultater)")
    print("\nP(RED) matrise:")
    print(p_red.round(3).to_string() if not p_red.empty else "  (ingen resultater)")
    print("\nForventet risikoscore-matrise (0=GREEN, 1=YELLOW, 2=RED):")
    print(score.round(3).to_string() if not score.empty else "  (ingen resultater)")
    if not summary.empty:
        cols = ['source_site_id', 'target_site_id', 'p_green', 'p_yellow', 'p_red',
                'mean_tc_s', 'p90_tc_s', 'var99_exposure_ms', 'p_no_arrival']
        avail = [c for c in cols if c in summary.columns]
        print(f"\nDetaljert MC-oppsummering:")
        print(summary[avail].round(4).to_string(index=False))
    print(f"{'='*60}\n")

    return {
        'mc_library': mc_lib,
        'results': results,
        'summary_df': summary,
        'p_red_matrix': p_red,
        'modal_matrix': modal,
        'score_matrix': score,
    }


def generate_mc_report(
    scenario_dir,
    n_samples: int = 10_000,
    shed_rate: float = 1.0,
    rebuild_library: bool = False,
    verbose: bool = True,
    seed: int = 42,
    total_time_s: float = 1200.0,
) -> dict:
    """
    Generate all Monte-Carlo risk reporting artefacts (Sprint 8).

    Runs (or re-uses) the MC risk analysis and renders:
      mc_risk_heatmap.png         — modal status / P(RED) / E[score] heatmaps
      mc_transfer_heatmap.png     — mean TC / p90 TC / VaR99 heatmaps
      mc_pair_profiles.png        — stacked probability bar charts
      mc_management_summary.png   — single-page dashboard
      mc_summary.txt              — plain-text management summary

    Parameters
    ----------
    scenario_dir    : path to scenario directory
    n_samples       : MC samples per pair
    shed_rate       : shedding rate multiplier (1.0 = library default)
    rebuild_library : force rebuild of MC library
    verbose         : log progress
    seed            : random seed for MC sampling
    total_time_s    : simulation duration (must match library)

    Returns
    -------
    dict with keys: 'mc_output', 'report_paths'
    """
    from core.mc_reporter import MCReporter

    d = Path(scenario_dir).resolve()
    print(f"\n{'='*60}")
    print(f"AquaGuard v1.23 — MC Rapport: {d.name}")
    print(f"{'='*60}\n")

    mc_output = run_mc_risk(
        scenario_dir,
        n_samples=n_samples,
        shed_rate=shed_rate,
        rebuild_library=rebuild_library,
        verbose=verbose,
        seed=seed,
        total_time_s=total_time_s,
    )

    output_dir = d / 'output'
    reporter = MCReporter(
        mc_library=mc_output['mc_library'],
        results=mc_output['results'],
        output_dir=output_dir,
    )

    report_paths = reporter.render_all(log_func=print if verbose else None)

    print(f"\n{'='*60}")
    print(f"Rapport generert — {len(report_paths)} filer:")
    for key, path in report_paths.items():
        print(f"  {key:<22}: {path.name}")
    print(f"{'='*60}\n")

    return {
        'mc_output': mc_output,
        'report_paths': report_paths,
    }


def load_mc_library(scenario_dir) -> 'MCTransferLibrary':
    """
    Load a previously built MCTransferLibrary from scenario_dir/output/.

    Parameters
    ----------
    scenario_dir : path to scenario directory (same as passed to build_mc_library)

    Returns
    -------
    MCTransferLibrary
    """
    from core.transfer_library import MCTransferLibrary as _MCLib
    output_dir = Path(scenario_dir).resolve() / 'output'
    mc_lib = _MCLib.load(output_dir)
    print(f"Loaded {mc_lib}")
    return mc_lib


def create_scenario_template(
    scenario_dir,
    n_sites: int = 2,
    overwrite: bool = False,
) -> None:
    """
    Create a template scenario directory that users can edit.

    Parameters
    ----------
    scenario_dir : path where template files should be written
    n_sites      : number of example sites to include (1 or 2)
    overwrite    : if True, overwrite existing files
    """
    save_scenario_template(scenario_dir, n_sites=n_sites, overwrite=overwrite)


if __name__ == '__main__' and RUN_USER_SETTINGS.get('auto_run_when_main', True):
    outputs = run_demo()
    print(outputs['summary'])
