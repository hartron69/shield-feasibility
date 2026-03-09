"""
Monte Carlo Simulation Engine – Compound Poisson-LogNormal Loss Model.

Methodology
-----------
Annual aggregate loss is modelled as a compound process:

    S_t = Σ_{i=1}^{N_t} X_i

where
    N_t ~ Poisson(λ)                   – event frequency in year t
    X_i ~ LogNormal(μ_X, σ_X)         – individual event severity

Parameters (μ_X, σ_X) are derived from (mean, CV) of severity:
    σ_X = sqrt(ln(1 + CV²))
    μ_X = ln(mean) - σ_X²/2

Catastrophic tail: with probability p_cat an additional CAT event is injected,
severity drawn from LogNormal with mean = multiplier × base_mean, same CV.

5-year horizon: each simulation draws 5 independent annual totals.
"""

from __future__ import annotations

import warnings
from typing import Dict, List, Optional

import numpy as np
from dataclasses import dataclass, field
from scipy.stats import norm as _scipy_norm

from data.input_schema import OperatorInput
from config.settings import SETTINGS
from models.loss_model import LossView, compute_loss_view
from models.correlation import RiskCorrelationMatrix
from models.regime_model import RegimeModel
from models.domain_correlation import DomainCorrelationMatrix
from models.domain_loss_breakdown import build_domain_loss_breakdown


# ─────────────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SimulationResults:
    """All outputs produced by the Monte Carlo engine."""

    # Shape: (n_simulations, 5) – annual aggregate gross losses
    annual_losses: np.ndarray          # 2-D array

    # Derived 1-D statistics (across all simulation-years)
    mean_annual_loss: float
    std_annual_loss: float
    median_annual_loss: float

    # Percentile thresholds (1-year)
    var_90: float
    var_95: float
    var_99: float
    var_995: float    # SCR anchor – 99.5th pctl
    tvar_95: float    # Tail VaR (expected shortfall above 95th pctl)

    # 5-year aggregate statistics (per simulation path)
    mean_5yr_loss: float
    std_5yr_loss: float
    var_5yr_995: float

    # Frequency / severity decomposition
    mean_event_count: float
    mean_event_severity: float

    # Raw simulation paths for downstream strategy models
    # Shape: (n_simulations, 5) – event count per year (stored as float)
    event_counts: np.ndarray
    # Shape: (n_simulations, 5, max_events) – per-event severities (ragged → padded)
    # For memory efficiency we store only the annual aggregates plus the raw arrays.

    n_simulations: int
    projection_years: int

    # ── C5AI+ enrichment (optional) ───────────────────────────────────────────
    # Populated when a C5AI+ forecast file is loaded. None = static model only.
    c5ai_scale_factor: Optional[float] = None
    # Disaggregated loss contributions by biological risk type.
    # Dict[risk_type, np.ndarray of shape (n_simulations, T)]
    bio_loss_breakdown: Optional[Dict[str, np.ndarray]] = None
    # True if the simulation was enriched with C5AI+ biological risk estimates.
    c5ai_enriched: bool = False

    # ── Financial loss view (optional) ────────────────────────────────────────
    # Populated by MonteCarloEngine when a captive structure is provided.
    # Separates gross / retained / reinsured / net-captive losses.
    loss_view: Optional[LossView] = None

    # Convenience aggregates derived from loss_view (None if not computed)
    gross_annual_losses: Optional[np.ndarray] = None   # (N, T)
    retained_annual_losses: Optional[np.ndarray] = None  # (N, T)

    # ── Mitigation provenance (Sprint 2, optional) ────────────────────────────
    # True when the simulation was run against an adjusted (mitigated) forecast.
    mitigated: bool = False
    # Names of MitigationActions applied upstream to the forecast (if any).
    mitigation_summary: Optional[List[str]] = None

    # ── Portfolio / site decomposition (Sprint 1, optional) ───────────────────
    # 5-year aggregate loss per simulation path (N,).  Always populated.
    portfolio_loss_distribution: Optional[np.ndarray] = None  # (N,)
    # Per-site annual losses: site_name → (N, T).  Populated when sites > 0.
    site_loss_distribution: Optional[Dict[str, np.ndarray]] = None
    # Regime multiplier per (N, T) cell.  None when no RegimeModel supplied.
    cluster_year_indicator: Optional[np.ndarray] = None  # (N, T)
    # Tower aggregate-exhaustion events per (N, T).  Phase 2 – always None here.
    aggregate_exhaustion_events: Optional[np.ndarray] = None  # (N, T) bool

    # ── Domain loss decomposition (Sprint 4, optional) ────────────────────────
    # Full four-domain breakdown: biological / structural / environmental /
    # operational.  Populated by build_domain_loss_breakdown() when a
    # DomainLossBreakdown is computed for this simulation.  None by default
    # (backward compatible).
    domain_loss_breakdown: Optional[object] = None  # DomainLossBreakdown


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class MonteCarloEngine:
    """
    Vectorised Monte Carlo loss simulation engine.

    Parameters
    ----------
    operator : OperatorInput
        Validated operator data package.
    n_simulations : int
        Number of Monte Carlo trials (default 10,000).
    seed : int
        Random seed for reproducibility.
    """

    def __init__(
        self,
        operator: OperatorInput,
        n_simulations: int = SETTINGS.default_simulations,
        seed: int = SETTINGS.random_seed,
        correlation: Optional[RiskCorrelationMatrix] = None,
        regime_model: Optional[RegimeModel] = None,
        pre_loaded_forecast=None,   # Optional[RiskForecast] – avoids circular import
        domain_correlation: Optional[DomainCorrelationMatrix] = None,
    ):
        self.operator = operator
        self.n_simulations = n_simulations
        self.rng = np.random.default_rng(seed)
        self.years = SETTINGS.projection_years
        self.correlation = correlation
        self.regime_model = regime_model
        # Pre-loaded C5AI+ forecast (e.g. an adjusted/mitigated forecast).
        # When provided, overrides operator.c5ai_forecast_path file loading.
        self.pre_loaded_forecast = pre_loaded_forecast
        # Sprint 7 – domain-level correlation for cross-domain loss co-movement.
        self.domain_correlation = domain_correlation

        rp = operator.risk_params
        self.lam = rp.expected_annual_events
        self.mean_sev = rp.mean_loss_severity
        self.cv_sev = rp.cv_loss_severity
        self.p_cat = rp.catastrophe_probability
        self.cat_mult = rp.catastrophe_loss_multiplier

        # Derive log-normal parameters from (mean, CV)
        self._lognorm_mu, self._lognorm_sigma = self._lognorm_params(
            self.mean_sev, self.cv_sev
        )
        # CAT severity parameters
        cat_mean = self.mean_sev * self.cat_mult
        self._cat_mu, self._cat_sigma = self._lognorm_params(cat_mean, self.cv_sev)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _lognorm_params(mean: float, cv: float):
        """Return (mu, sigma) of the underlying normal for a log-normal with given mean & CV."""
        sigma = np.sqrt(np.log(1.0 + cv ** 2))
        mu = np.log(mean) - 0.5 * sigma ** 2
        return mu, sigma

    # ── main simulation ───────────────────────────────────────────────────────

    def run(self) -> SimulationResults:
        """
        Execute the simulation and return a fully-populated SimulationResults.

        C5AI+ integration
        -----------------
        If operator.c5ai_forecast_path is set and the file exists, the static
        Compound Poisson model is scaled by the C5AI+ predicted loss ratio.
        The biological risk breakdown is stored in SimulationResults for
        disaggregated reporting. If the file is missing or cannot be parsed,
        a warning is emitted and the static model is used unchanged.
        """

        N = self.n_simulations
        T = self.years

        # ── Step 1: draw annual event counts  N_t ~ Poisson(λ × regime)
        # With regime model: each (N, T) cell gets an independent regime
        # multiplier that scales λ before the Poisson draw.
        # Without regime model: identical to the original single Poisson draw.
        if self.regime_model is not None:
            regime_multipliers = self.regime_model.sample_regimes(N, T, self.rng)  # (N, T)
            event_counts = self.rng.poisson(self.lam * regime_multipliers).astype(float)
            cluster_year_indicator = regime_multipliers
        else:
            event_counts = self.rng.poisson(self.lam, size=(N, T)).astype(float)
            cluster_year_indicator = None

        # ── Step 2: simulate aggregate attritional losses
        max_events = int(event_counts.max()) + 1

        severity_pool = np.exp(
            self._lognorm_mu
            + self._lognorm_sigma * self.rng.standard_normal(size=(N, T, max_events))
        )

        idx = np.arange(max_events)
        mask = idx[np.newaxis, np.newaxis, :] < event_counts[:, :, np.newaxis]
        attritional_losses = (severity_pool * mask).sum(axis=2)   # (N, T)

        # ── Step 3: inject CAT events
        cat_occurs = self.rng.random(size=(N, T)) < self.p_cat
        cat_severity = np.exp(
            self._cat_mu + self._cat_sigma * self.rng.standard_normal(size=(N, T))
        )
        cat_losses = np.where(cat_occurs, cat_severity, 0.0)

        # ── Step 4: aggregate static simulation
        annual_losses = attritional_losses + cat_losses   # (N, T)

        # ── Step 5: C5AI+ enrichment (optional) ──────────────────────────
        c5ai_scale = None
        bio_breakdown: Optional[Dict[str, np.ndarray]] = None
        c5ai_enriched = False
        sim_mitigated = False
        mitigation_summary: Optional[List[str]] = None

        if self.pre_loaded_forecast is not None:
            # Use the pre-loaded (possibly mitigated) forecast directly
            annual_losses, c5ai_scale, bio_breakdown, c5ai_enriched = (
                self._apply_c5ai_forecast_obj(annual_losses, self.pre_loaded_forecast)
            )
            # Detect mitigation provenance from forecast metadata
            applied = getattr(
                self.pre_loaded_forecast.metadata, "applied_mitigations", []
            )
            if applied:
                sim_mitigated = True
                mitigation_summary = list(applied)
        else:
            c5ai_path = getattr(self.operator, "c5ai_forecast_path", None)
            if c5ai_path:
                annual_losses, c5ai_scale, bio_breakdown, c5ai_enriched = (
                    self._apply_c5ai_forecast(annual_losses, c5ai_path)
                )

        # ── Step 6: site-level decomposition
        site_loss_dist = self._distribute_to_sites_rng(
            annual_losses, self.operator.sites, self.correlation
        )

        # ── Step 7: statistics
        flat = annual_losses.flatten()
        five_yr = annual_losses.sum(axis=1)

        mean_annual = float(flat.mean())
        std_annual = float(flat.std())
        median_annual = float(np.median(flat))

        var_90 = float(np.percentile(flat, 90))
        var_95 = float(np.percentile(flat, 95))
        var_99 = float(np.percentile(flat, 99))
        var_995 = float(np.percentile(flat, 99.5))
        tvar_95 = float(flat[flat >= var_95].mean())

        mean_5yr = float(five_yr.mean())
        std_5yr = float(five_yr.std())
        var_5yr_995 = float(np.percentile(five_yr, 99.5))

        # ── Step 8: domain loss breakdown (Sprint 7, optional) ───────────────
        domain_breakdown = None
        if self.domain_correlation is not None:
            domain_breakdown = build_domain_loss_breakdown(
                annual_losses=annual_losses,
                bio_breakdown=bio_breakdown if bio_breakdown else None,
                domain_correlation=self.domain_correlation,
                rng=self.rng,
            )

        return SimulationResults(
            annual_losses=annual_losses,
            mean_annual_loss=mean_annual,
            std_annual_loss=std_annual,
            median_annual_loss=median_annual,
            var_90=var_90,
            var_95=var_95,
            var_99=var_99,
            var_995=var_995,
            tvar_95=tvar_95,
            mean_5yr_loss=mean_5yr,
            std_5yr_loss=std_5yr,
            var_5yr_995=var_5yr_995,
            mean_event_count=float(event_counts.mean()),
            mean_event_severity=float(severity_pool[mask].mean()) if mask.any() else self.mean_sev,
            event_counts=event_counts,
            n_simulations=N,
            projection_years=T,
            c5ai_scale_factor=c5ai_scale,
            bio_loss_breakdown=bio_breakdown,
            c5ai_enriched=c5ai_enriched,
            gross_annual_losses=annual_losses,
            retained_annual_losses=annual_losses,  # no structure by default; full retention
            # Sprint 1 – portfolio / site decomposition
            portfolio_loss_distribution=five_yr,
            site_loss_distribution=site_loss_dist if site_loss_dist else None,
            cluster_year_indicator=cluster_year_indicator,
            aggregate_exhaustion_events=None,  # Phase 2
            # Sprint 2 – mitigation provenance
            mitigated=sim_mitigated,
            mitigation_summary=mitigation_summary,
            # Sprint 7 – domain correlation breakdown
            domain_loss_breakdown=domain_breakdown,
        )

    @staticmethod
    def _compute_loss_view(
        annual_losses: np.ndarray,
        attachment_point: float = 0.0,
        limit: float = float("inf"),
        retention_layer: float = 0.0,
    ) -> LossView:
        """
        Decompose gross annual losses into retained / reinsured / net-captive.

        Parameters
        ----------
        annual_losses : np.ndarray
            Shape (N, T) gross losses.
        attachment_point, limit, retention_layer
            Layer structure parameters passed to compute_loss_view().
        """
        return compute_loss_view(
            annual_losses,
            attachment_point=attachment_point,
            limit=limit,
            retention_layer=retention_layer,
        )

    @staticmethod
    def _distribute_to_sites(
        annual_losses: np.ndarray,
        sites: list,
        correlation: Optional[RiskCorrelationMatrix],
        rng: Optional[np.random.Generator] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Decompose portfolio losses into per-site allocations.

        When correlation is None (or there is only one site) the allocation is
        purely proportional to Total Insured Value (TIV).

        When a RiskCorrelationMatrix is provided the allocation uses a Gaussian
        copula so that correlated sites receive jointly-skewed weights while
        the portfolio total is preserved exactly.

        Algorithm (Gaussian copula path)
        ---------------------------------
        1. Draw Z ~ N(0, I) of shape (N, T, S).
        2. Apply Cholesky: Z_corr = Z @ L.T  → correlated standard normals.
        3. Transform to uniform: U = Φ(Z_corr) ∈ (0, 1).
        4. Perturb TIV weights: w_pert = w_i × (1 + 1.0 × (U_i − 0.5)).
        5. Clip to ≥ 0, normalise so weights sum to 1 across sites.
        6. site_loss_i = w_norm_i × annual_losses (portfolio total preserved).

        Parameters
        ----------
        annual_losses : np.ndarray
            Shape (N, T) portfolio gross annual losses.
        sites : list of SiteProfile
            Ordered list matching site_ids in correlation (if provided).
        correlation : RiskCorrelationMatrix or None
        rng : np.random.Generator, optional
            RNG for the Gaussian copula draw.  If None, a fresh default RNG
            is created (non-reproducible; fine for standalone/test use).

        Returns
        -------
        Dict[str, np.ndarray]
            Maps site name → (N, T) loss array.  Empty dict if no sites.
        """
        S = len(sites)
        if S == 0:
            return {}

        tiv = np.array([s.total_insured_value for s in sites], dtype=float)
        total_tiv = tiv.sum()
        w = tiv / total_tiv if total_tiv > 0 else np.ones(S, dtype=float) / S

        N, T = annual_losses.shape

        if S == 1 or correlation is None:
            # Simple proportional allocation – identical to existing behaviour
            return {sites[i].name: annual_losses * w[i] for i in range(S)}

        # Gaussian copula path
        L = correlation.cholesky()  # (S, S) lower-triangular
        _rng = rng if rng is not None else np.random.default_rng()

        Z = _rng.standard_normal(size=(N, T, S))
        Z_corr = Z @ L.T  # (N, T, S) – each [n,t,:] is correlated

        # Transform to uniform marginals
        U = _scipy_norm.cdf(Z_corr)  # (N, T, S) in (0, 1)

        # Perturb TIV weights (amplitude = 1.0 as per spec)
        w_pert = w[np.newaxis, np.newaxis, :] * (1.0 + 1.0 * (U - 0.5))  # (N, T, S)
        w_pert = np.maximum(w_pert, 0.0)

        # Normalise across sites so they sum to 1
        w_sum = w_pert.sum(axis=2, keepdims=True)  # (N, T, 1)
        w_sum = np.where(w_sum == 0.0, 1.0, w_sum)
        w_norm = w_pert / w_sum  # (N, T, S)

        # Allocate portfolio losses
        site_loss_array = annual_losses[:, :, np.newaxis] * w_norm  # (N, T, S)

        return {sites[i].name: site_loss_array[:, :, i] for i in range(S)}

    def _distribute_to_sites_rng(
        self,
        annual_losses: np.ndarray,
        sites: list,
        correlation: Optional[RiskCorrelationMatrix],
    ) -> Dict[str, np.ndarray]:
        """
        Instance version of _distribute_to_sites that uses self.rng.

        This is the method called from run() to ensure reproducibility.
        The static version is kept for external / test use.
        """
        S = len(sites)
        if S == 0:
            return {}

        tiv = np.array([s.total_insured_value for s in sites], dtype=float)
        total_tiv = tiv.sum()
        w = tiv / total_tiv if total_tiv > 0 else np.ones(S, dtype=float) / S

        N, T = annual_losses.shape

        if S == 1 or correlation is None:
            return {sites[i].name: annual_losses * w[i] for i in range(S)}

        L = correlation.cholesky()  # (S, S)
        Z = self.rng.standard_normal(size=(N, T, S))
        Z_corr = Z @ L.T  # (N, T, S)
        U = _scipy_norm.cdf(Z_corr)  # (N, T, S)

        w_pert = w[np.newaxis, np.newaxis, :] * (1.0 + 1.0 * (U - 0.5))
        w_pert = np.maximum(w_pert, 0.0)

        w_sum = w_pert.sum(axis=2, keepdims=True)
        w_sum = np.where(w_sum == 0.0, 1.0, w_sum)
        w_norm = w_pert / w_sum

        site_loss_array = annual_losses[:, :, np.newaxis] * w_norm
        return {sites[i].name: site_loss_array[:, :, i] for i in range(S)}

    def _apply_c5ai_forecast(
        self,
        annual_losses: np.ndarray,
        c5ai_path: str,
    ) -> tuple:
        """
        Load C5AI+ forecast and apply it to the simulated loss matrix.

        Strategy
        --------
        1. Load risk_forecast.json via ForecastExporter.load().
        2. Extract operator_aggregate.c5ai_vs_static_ratio (scale factor).
        3. Scale annual_losses by this factor (preserves shape/percentile structure).
        4. Build bio_loss_breakdown by distributing scaled losses across risk types
           using operator_aggregate.loss_breakdown_fractions.

        Returns
        -------
        (scaled_losses, scale_factor, bio_breakdown, enriched_flag)
        """
        try:
            from c5ai_plus.export.forecast_exporter import ForecastExporter
            from c5ai_plus.validation.forecast_validator import ForecastValidator, ValidationError

            forecast = ForecastExporter.load(c5ai_path)
            validator = ForecastValidator()
            validator.validate_or_raise(forecast)

            scale = forecast.scale_factor
            fractions = forecast.loss_fractions

            scaled = annual_losses * scale

            # Distribute scaled losses by biological risk type
            bio_breakdown: Dict[str, np.ndarray] = {
                rt: scaled * frac for rt, frac in fractions.items()
            }

            print(
                f"       [C5AI+] Forecast loaded: scale={scale:.3f} | "
                f"HAB={fractions.get('hab', 0):.1%} | "
                f"Lice={fractions.get('lice', 0):.1%} | "
                f"Jellyfish={fractions.get('jellyfish', 0):.1%} | "
                f"Pathogen={fractions.get('pathogen', 0):.1%}"
            )
            return scaled, scale, bio_breakdown, True

        except FileNotFoundError as exc:
            warnings.warn(
                f"C5AI+ forecast file not found: {c5ai_path}\n"
                f"Falling back to static Compound Poisson model.\n"
                f"Detail: {exc}",
                RuntimeWarning,
                stacklevel=3,
            )
        except Exception as exc:
            warnings.warn(
                f"Failed to load C5AI+ forecast from '{c5ai_path}': {exc}\n"
                f"Falling back to static model.",
                RuntimeWarning,
                stacklevel=3,
            )

        return annual_losses, None, None, False

    def _apply_c5ai_forecast_obj(
        self,
        annual_losses: np.ndarray,
        forecast,      # RiskForecast – type hint omitted to avoid circular import
    ) -> tuple:
        """
        Apply a pre-loaded (possibly mitigated) RiskForecast to the loss matrix.

        This is used when MonteCarloEngine receives a ``pre_loaded_forecast``
        (e.g. an adjusted forecast from apply_mitigations_to_forecast) rather
        than a file path.  Logic is identical to _apply_c5ai_forecast but
        skips the file I/O and validation steps.

        Returns
        -------
        (scaled_losses, scale_factor, bio_breakdown, enriched_flag)
        """
        try:
            from c5ai_plus.validation.forecast_validator import ForecastValidator, ValidationError

            validator = ForecastValidator()
            validator.validate_or_raise(forecast)

            scale = forecast.scale_factor
            fractions = forecast.loss_fractions

            scaled = annual_losses * scale
            bio_breakdown: Dict[str, np.ndarray] = {
                rt: scaled * frac for rt, frac in fractions.items()
            }
            return scaled, scale, bio_breakdown, True

        except Exception as exc:
            warnings.warn(
                f"Failed to apply pre-loaded C5AI+ forecast: {exc}\n"
                f"Falling back to static model.",
                RuntimeWarning,
                stacklevel=3,
            )
        return annual_losses, None, None, False
