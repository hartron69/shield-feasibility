"""
C5AI+ v5.0 – Configuration and constants.

All thresholds and model defaults are centralised here so they can be
adjusted without touching model code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class C5AISettings:
    # ── Forecasting horizon ────────────────────────────────────────────────
    forecast_years: int = 5            # Number of years to forecast forward
    forecast_quarters_per_year: int = 4

    # ── HAB model defaults ─────────────────────────────────────────────────
    # Prior event probability used when training data is absent
    hab_prior_event_probability: float = 0.12   # 12% annual probability per site
    # Expected loss when HAB occurs (NOK, as fraction of site biomass value)
    hab_loss_fraction_mean: float = 0.18         # 18% of biomass value
    hab_loss_fraction_cv: float = 0.55
    # Temperature thresholds driving HAB risk (Celsius)
    hab_temp_threshold_low: float = 12.0
    hab_temp_threshold_high: float = 20.0

    # ── Sea lice model defaults ────────────────────────────────────────────
    lice_prior_event_probability: float = 0.30   # 30% annual probability per site
    lice_loss_fraction_mean: float = 0.06        # 6% of biomass value
    lice_loss_fraction_cv: float = 0.60
    # Temperature threshold above which lice risk escalates
    lice_temp_threshold: float = 10.0

    # ── Jellyfish defaults (Phase 2 placeholder) ──────────────────────────
    jellyfish_prior_event_probability: float = 0.08
    jellyfish_loss_fraction_mean: float = 0.04
    jellyfish_loss_fraction_cv: float = 0.70

    # ── Pathogen defaults (Phase 2 placeholder) ───────────────────────────
    pathogen_prior_event_probability: float = 0.10
    pathogen_loss_fraction_mean: float = 0.12
    pathogen_loss_fraction_cv: float = 0.65

    # ── Data quality thresholds ────────────────────────────────────────────
    # Minimum number of observations per site to use ML model vs. prior
    min_obs_for_ml_model: int = 24      # 24 monthly records (2 years)
    # Max allowed missing fraction before degrading to prior
    max_missing_fraction: float = 0.30

    # ── Network risk propagation ───────────────────────────────────────────
    # Maximum distance (km) within which sites share risk
    network_max_distance_km: float = 50.0
    # Correlation decay (how fast risk sharing diminishes with distance)
    network_distance_decay: float = 0.05

    # ── Model schema version ───────────────────────────────────────────────
    model_version: str = "5.0.0"

    # ── Learning loop constants ────────────────────────────────────────────
    learning_store_dir: str = "c5ai_plus/learning/store"
    learning_min_samples_to_evaluate: int = 5
    learning_retrain_trigger_samples: int = 5
    learning_shadow_min_samples: int = 10
    learning_shadow_min_improvement: float = 0.05
    learning_bayesian_concentration: float = 5.0


C5AI_SETTINGS = C5AISettings()
