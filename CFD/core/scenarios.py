"""
core/scenarios.py — User-editable scenario settings for AquaGuard

Edit the dicts below to change the scenario without touching the engine code.
These are the same settings as the USER SETTINGS section in v1.22b, now in a
dedicated module so that Sprint 2+ can replace them with file-based input.

Units:
  length / depth / radius : m
  velocity                : m/s
  time                    : s
  diffusion               : m2/s
  solidity, factors       : dimensionless [-]
"""
from __future__ import annotations

# =============================================================================
# FLOW
# =============================================================================
FLOW_USER_SETTINGS: dict = {
    # Reference free-stream velocity [m/s].
    'U_inf': 0.5,

    # Output folder for PNG/CSV/JSON. None -> "output/" next to main script.
    'output_dir': None,
}

# =============================================================================
# NETS — list of pen configurations
# =============================================================================
NET_USER_SETTINGS: list[dict] = [
    {
        'name': 'Net 1',
        'center': (-100.0, 0.0),
        'radius': 25.0,
        'depth': 5.0,
        'solidity': 0.25,
        'Cr': 0.8,
    },
    {
        'name': 'Net 2',
        'center': (0.0, 0.0),
        'radius': 25.0,
        'depth': 5.0,
        'solidity': 0.60,
        'Cr': 0.8,
    },
    {
        'name': 'Net 3',
        'center': (100.0, 0.0),
        'radius': 25.0,
        'depth': 5.0,
        'solidity': 0.95,
        'Cr': 0.8,
    },
]

# =============================================================================
# COASTLINE
# =============================================================================
COAST_USER_SETTINGS: dict = {
    'y_coast': -150.0,
    'alongshore_length_scale_m': 220.0,
    'offshore_decay_m': 120.0,
    'temporal_period_s': 900.0,
    'alongshore_variation_fraction': 0.30,
    'wall_image_weight': 0.85,
}

# =============================================================================
# COMPUTATION DOMAIN
# =============================================================================
DOMAIN_USER_SETTINGS: dict = {
    'x': (-260.0, 260.0),
    'y_top': 180.0,
    'nx': 241,
    'ny': 181,
}

# =============================================================================
# PATHOGEN TRANSPORT
# =============================================================================
PATHOGEN_USER_SETTINGS: dict = {
    'pathogen_name': 'Generic pathogen',
    'dt_s': 10.0,
    'total_time_s': 1200.0,
    'particles_per_step': 9,
    'source_mode': 'upstream_line',     # 'upstream_line' | 'infected_net'
    'source_net_name': 'Net 1',
    'source_load': 1.0,
    'shedding_rate_relative_per_s': 1.0,
    'source_patch_radius_fraction': 0.35,
    'source_infectivity': 1.0,
    'diffusion_m2_s': 0.12,
    'biology_enabled': True,
    'base_inactivation_rate_1_s': 1.65e-6,
    'temperature_c': 10.0,
    'reference_temperature_c': 10.0,
    'q10_inactivation': 1.5,
    'uv_inactivation_factor': 1.0,
    'species_infectivity_factor': 1.0,
    'vertical_preference_mode': 'none',
    'minimum_infectivity': 1.0e-3,
    'random_seed': 42,
    'verbose': True,
    'progress_every_pct': 10.0,
}

# Legacy alias (kept for backward compatibility with v1.22b imports)
pathogen_USER_SETTINGS = PATHOGEN_USER_SETTINGS

# =============================================================================
# OPERATIVE RISK THRESHOLDS
# =============================================================================
RISK_USER_SETTINGS: dict = {
    'arrival_alarm_threshold_s': 900.0,
    'exposure_alarm_threshold_mass_seconds': 80.0,
    'yellow_arrival_threshold_s': 1200.0,
    'yellow_peak_risk_concentration': 0.010,
    'yellow_exposure_threshold_mass_seconds': 40.0,
    'red_arrival_threshold_s': 600.0,
    'red_peak_risk_concentration': 0.025,
    'red_exposure_threshold_mass_seconds': 100.0,
    'no_arrival_means_green': True,
    'auto_calibrate_from_first_case': True,
    'baseline_case_name': 'langs',
    'baseline_peak_reference': 'max',
    'baseline_exposure_reference': 'max',
    'yellow_peak_factor': 1.50,
    'red_peak_factor': 2.50,
    'yellow_exposure_factor': 1.50,
    'red_exposure_factor': 2.50,
    'baseline_min_peak': 0.0020,
    'baseline_min_exposure': 10.0,
}

# =============================================================================
# RUN CONTROL
# =============================================================================
RUN_USER_SETTINGS: dict = {
    'cases': ['langs', 'tverrs', 'diagonal'],
    'auto_run_when_main': True,
}
