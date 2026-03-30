"""
Shield Captive Risk Platform – Domain Loss Breakdown Model (Sprint 4).

Provides a clean decomposition of simulated losses across all four main
aquaculture risk domains.  This enables mitigation actions to target
domain-level or sub-type-level loss slices without falling back to
portfolio-wide scaling.

Domain model
------------
Four domains, each with named sub-types:

    biological  → hab, lice, jellyfish, pathogen
    structural  → mooring_failure, net_integrity, cage_structural, feed_system
    environmental → oxygen_stress, temperature_extreme, current_storm, ice
    operational → human_error, procedure_failure, equipment, incident

Data quality notes
------------------
* biological – actively modelled by C5AI+ (RandomForest for HAB/lice,
  temperature-adjusted prior for jellyfish, network-contagion for pathogen).
  When a C5AI+ forecast is loaded the sub-type arrays are derived from the
  forecast's ``loss_breakdown_fractions``.
* structural / environmental / operational – **stub-based prior fractions**.
  There is no ML model for these domains.  Loss slices are computed by
  applying fixed fraction constants to the non-biological residual (or to
  the total when no C5AI+ forecast is available).  ``model_type = "stub"``.

The stub priors are conservative estimates suitable for feasibility-grade
captive analysis.  They should be replaced by domain-specific models in a
future production release.

Platform principle
------------------
This is a risk modelling and insurance decision platform, NOT an early-warning
system.  Domain loss decomposition is used purely for mitigation routing and
capital impact analysis.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Dict, Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from models.domain_correlation import DomainCorrelationMatrix


# ─────────────────────────────────────────────────────────────────────────────
# Domain and sub-type constants
# ─────────────────────────────────────────────────────────────────────────────

#: Names of all recognised domains.
DOMAINS = ("biological", "structural", "environmental", "operational")

#: Sub-types within each domain.
DOMAIN_SUBTYPES: Dict[str, tuple] = {
    "biological":    ("hab", "lice", "jellyfish", "pathogen"),
    "structural":    ("mooring_failure", "net_integrity", "cage_structural", "feed_system"),
    "environmental": ("oxygen_stress", "temperature_extreme", "current_storm", "ice"),
    "operational":   ("human_error", "procedure_failure", "equipment", "incident"),
}

# ── Prior fractions (all fractions within a domain must sum to 1.0) ──────────

#: Biological sub-type priors (used when no C5AI+ forecast available).
_BIO_SUBTYPE_FRACTIONS: Dict[str, float] = {
    "hab":       0.40,
    "lice":      0.30,
    "jellyfish": 0.20,
    "pathogen":  0.10,
}

#: Structural sub-type priors (stub model).
_STRUCT_SUBTYPE_FRACTIONS: Dict[str, float] = {
    "mooring_failure":  0.35,
    "net_integrity":    0.30,
    "cage_structural":  0.25,
    "feed_system":      0.10,
}

#: Environmental sub-type priors (stub model).
_ENV_SUBTYPE_FRACTIONS: Dict[str, float] = {
    "oxygen_stress":      0.40,
    "temperature_extreme": 0.30,
    "current_storm":      0.20,
    "ice":                0.10,
}

#: Operational sub-type priors (stub model).
_OPS_SUBTYPE_FRACTIONS: Dict[str, float] = {
    "human_error":       0.40,
    "procedure_failure": 0.30,
    "equipment":         0.20,
    "incident":          0.10,
}

#: Default domain fractions of total portfolio loss when NO bio breakdown is
#: available.  Derived from expert priors; not empirically calibrated.
DEFAULT_DOMAIN_FRACTIONS: Dict[str, float] = {
    "biological":    0.60,
    "structural":    0.20,
    "environmental": 0.10,
    "operational":   0.10,
}

#: Non-bio domain split fractions of the residual (total − biological).
#: Structural is the dominant non-bio domain in salmon aquaculture.
_NON_BIO_DOMAIN_FRACTIONS: Dict[str, float] = {
    "structural":    0.50,
    "environmental": 0.25,
    "operational":   0.25,
}

_SUBTYPE_FRACTIONS: Dict[str, Dict[str, float]] = {
    "biological":    _BIO_SUBTYPE_FRACTIONS,
    "structural":    _STRUCT_SUBTYPE_FRACTIONS,
    "environmental": _ENV_SUBTYPE_FRACTIONS,
    "operational":   _OPS_SUBTYPE_FRACTIONS,
}

# ── Structural sub-type mitigation caps (Sprint 5) ───────────────────────────

#: Maximum combined mitigation reduction allowed per structural sub-type.
#:
#: When multiple mitigation actions target the same structural sub-type (e.g.
#: both ``stronger_anchors`` and ``stronger_moorings`` target ``mooring_failure``),
#: their multiplicative combined reduction is capped at this fraction to prevent
#: unrealistic near-elimination of structural failure risk.
#:
#: Rationale for mooring_failure cap (0.48 = 48%):
#: - ``stronger_anchors`` alone: ~35% probability reduction
#: - ``stronger_moorings`` alone: ~30% probability + 20% severity reduction
#: - Multiplicative combined: (1-0.35)×(1-0.30) ≈ 54.5% — exceeds plausible limit
#: - Cap at 48% reflects that physical and environmental failure modes always remain
#: - This is a conservative feasibility-grade constraint, not an engineering bound
#:
#: No cap is applied to net_integrity, cage_structural, or feed_system because
#: no overlapping actions currently target those sub-types.  Caps can be added
#: as new actions are introduced.
STRUCTURAL_SUBTYPE_CAPS: Dict[str, float] = {
    # Sea structural sub-type caps
    "mooring_failure": 0.48,   # max 48% combined loss reduction (sea)
    # Smolt RAS operational sub-type caps — calibrated for multiple-action overlap.
    # Three actions target oxygen, two each target power and biofilter.
    # Caps prevent unrealistic near-elimination when actions are combined.
    "oxygen":          0.55,   # residual O₂-collapse risk: ~45% irreducible (e.g. sensor failure)
    "power":           0.70,   # grid + mains both failing: ~30% irreducible even with generator
    "biofilter":       0.55,   # biological community: ~45% irreducible despite monitoring
    # Smolt biological sub-type caps (two actions each can target these)
    "water_quality":   0.70,   # temperature/CO₂/pH collectively: 30% irreducible process risk
    "biosecurity":     0.65,   # contamination risk: 35% irreducible (water intake, visitors)
}

# ── Smolt / RAS domain fractions and sub-type priors ─────────────────────────
# Land-based RAS facility: operational risk dominates (~70%); biological from
# water quality and biosecurity (~22%); structural (building) and environmental
# (flood, utility) are minor.

#: Smolt domain fractions of total portfolio loss.
SMOLT_DOMAIN_FRACTIONS: Dict[str, float] = {
    "operational":   0.70,
    "biological":    0.22,
    "structural":    0.05,
    "environmental": 0.03,
}

#: Smolt operational sub-types — RAS-specific peril names used as mitigation targets.
_SMOLT_OPS_SUBTYPE_FRACTIONS: Dict[str, float] = {
    "biofilter":    0.31,  # biofilter failure / nitrification breakdown
    "oxygen":       0.36,  # O₂ collapse, hypoxia events
    "power":        0.26,  # power outage, pump failure
    "general_ops":  0.07,  # procedure failures, human error
}

#: Smolt biological sub-types — water-quality and biosecurity effects on fish.
_SMOLT_BIO_SUBTYPE_FRACTIONS: Dict[str, float] = {
    "water_quality": 0.60,  # CO₂/pH/nitrate stress, temperature fluctuation
    "biosecurity":   0.40,  # pathogen, contamination, VHS/IHN risk
}

#: Smolt structural sub-types — land-based building and equipment damage.
_SMOLT_STRUCT_SUBTYPE_FRACTIONS: Dict[str, float] = {
    "building":          0.70,  # fire, flood, structural collapse
    "equipment_damage":  0.30,  # tank/pipe/mechanical damage
}

#: Smolt environmental sub-types — external utility and weather events.
_SMOLT_ENV_SUBTYPE_FRACTIONS: Dict[str, float] = {
    "flood":           0.70,  # site flooding
    "utility_failure": 0.30,  # grid/water supply failure (non-power)
}

_SMOLT_SUBTYPE_FRACTIONS: Dict[str, Dict[str, float]] = {
    "operational":   _SMOLT_OPS_SUBTYPE_FRACTIONS,
    "biological":    _SMOLT_BIO_SUBTYPE_FRACTIONS,
    "structural":    _SMOLT_STRUCT_SUBTYPE_FRACTIONS,
    "environmental": _SMOLT_ENV_SUBTYPE_FRACTIONS,
}


# ─────────────────────────────────────────────────────────────────────────────
# DomainLossBreakdown dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DomainLossBreakdown:
    """
    Loss arrays decomposed by risk domain and sub-type.

    All arrays have shape ``(N, T)`` matching
    ``SimulationResults.annual_losses``.

    Attributes
    ----------
    biological : Dict[str, np.ndarray]
        Sub-type arrays for ``hab``, ``lice``, ``jellyfish``, ``pathogen``.
        Modelled by C5AI+ when a forecast is available; prior fractions otherwise.
    structural : Dict[str, np.ndarray]
        Sub-type arrays for ``mooring_failure``, ``net_integrity``,
        ``cage_structural``, ``feed_system``.
        **Stub model** – prior fractions of the non-biological residual.
    environmental : Dict[str, np.ndarray]
        Sub-type arrays for ``oxygen_stress``, ``temperature_extreme``,
        ``current_storm``, ``ice``.
        **Stub model**.
    operational : Dict[str, np.ndarray]
        Sub-type arrays for ``human_error``, ``procedure_failure``,
        ``equipment``, ``incident``.
        **Stub model**.
    bio_modelled : bool
        True when biological slices originate from a C5AI+ forecast.
        False when prior fractions were used for all domains.
    structural_model_type : str
        Always ``"stub"`` until a dedicated structural forecaster is built.
    environmental_model_type : str
        Always ``"stub"``.
    operational_model_type : str
        Always ``"stub"``.
    """

    biological:    Dict[str, np.ndarray] = field(default_factory=dict)
    structural:    Dict[str, np.ndarray] = field(default_factory=dict)
    environmental: Dict[str, np.ndarray] = field(default_factory=dict)
    operational:   Dict[str, np.ndarray] = field(default_factory=dict)

    # Data-quality metadata
    bio_modelled:              bool = False
    structural_model_type:    str  = "stub"
    environmental_model_type: str  = "stub"
    operational_model_type:   str  = "stub"

    # Sprint 7 – domain correlation provenance
    domain_correlation_applied: bool = False

    # ── Computed properties ───────────────────────────────────────────────────

    def total(self) -> np.ndarray:
        """
        Portfolio total loss array ``(N, T)`` as the element-wise sum of all
        sub-type arrays across all domains.
        """
        arrays = list(self._all_arrays())
        if not arrays:
            raise ValueError("DomainLossBreakdown contains no arrays.")
        return sum(arrays)

    def domain_totals(self) -> Dict[str, np.ndarray]:
        """
        Per-domain ``(N, T)`` aggregate (sum of all sub-type arrays).

        Returns
        -------
        dict with keys ``"biological"``, ``"structural"``,
        ``"environmental"``, ``"operational"``.
        """
        result = {}
        for domain in DOMAINS:
            d = getattr(self, domain)
            if d:
                arrs = list(d.values())
                result[domain] = sum(arrs)
        return result

    def flat_lookup(self) -> Dict[str, np.ndarray]:
        """
        Build a unified lookup dict for ``MitigationAnalyzer``.

        The lookup exposes two levels of granularity:

        * **Sub-type level** – individual risk-type arrays (e.g. ``"jellyfish"``,
          ``"mooring_failure"``).  Used by risk-type-targeted actions.
        * **Domain level** – per-domain aggregate (e.g. ``"structural"``,
          ``"environmental"``).  Used by domain-targeted actions such as
          ``stronger_nets`` (``targeted_risk_types = ["structural"]``).

        Sub-types are always included; domain aggregates are added as
        additional keys so that domain-level targeting works without
        double-counting (the ``_apply_domain_specific()`` method routes via
        sub-types internally).

        Returns
        -------
        Dict[str, np.ndarray]
            Combined flat dictionary.
        """
        lookup: Dict[str, np.ndarray] = {}
        for domain in DOMAINS:
            d = getattr(self, domain)
            if d:
                # Sub-type entries
                for st, arr in d.items():
                    lookup[st] = arr
                # Domain-aggregate entry
                lookup[domain] = sum(d.values())
        return lookup

    def all_subtypes(self) -> Dict[str, np.ndarray]:
        """
        Flat dict of all sub-type arrays (no domain-aggregate entries).

        Returns
        -------
        Dict[str, np.ndarray]
        """
        result: Dict[str, np.ndarray] = {}
        for domain in DOMAINS:
            result.update(getattr(self, domain))
        return result

    def _all_arrays(self):
        """Yield all sub-type arrays across all domains."""
        for domain in DOMAINS:
            yield from getattr(self, domain).values()

    # ── Constructors ──────────────────────────────────────────────────────────

    @classmethod
    def from_bio_breakdown(
        cls,
        bio_breakdown: Dict[str, np.ndarray],
        annual_losses: np.ndarray,
    ) -> "DomainLossBreakdown":
        """
        Create a ``DomainLossBreakdown`` from an existing C5AI+ bio breakdown
        plus stub-prior non-biological domains.

        The non-bio residual is:
            ``residual = clip(annual_losses − sum(bio), 0)``

        This residual is split 50 / 25 / 25 % into structural /
        environmental / operational, then further subdivided by
        sub-type priors.

        Backward-compatible wrapper around the old ``bio_loss_breakdown``
        pattern: any code that already computes C5AI+ bio slices can create
        a full domain breakdown with one call.

        Parameters
        ----------
        bio_breakdown : Dict[str, np.ndarray]
            Per-risk-type arrays from ``SimulationResults.bio_loss_breakdown``.
        annual_losses : np.ndarray
            Shape ``(N, T)`` gross simulated losses.

        Returns
        -------
        DomainLossBreakdown
            With ``bio_modelled = True``.
        """
        # Biological slices from C5AI+
        biological = {k: v.copy() for k, v in bio_breakdown.items()}

        # Non-bio residual (clip at 0 in case of floating-point overshoot)
        bio_total = sum(biological.values())
        residual = np.maximum(annual_losses - bio_total, 0.0)

        structural    = _split_domain(residual, "structural",    _NON_BIO_DOMAIN_FRACTIONS)
        environmental = _split_domain(residual, "environmental", _NON_BIO_DOMAIN_FRACTIONS)
        operational   = _split_domain(residual, "operational",   _NON_BIO_DOMAIN_FRACTIONS)

        return cls(
            biological=biological,
            structural=structural,
            environmental=environmental,
            operational=operational,
            bio_modelled=True,
        )

    @classmethod
    def prior_only(
        cls,
        annual_losses: np.ndarray,
    ) -> "DomainLossBreakdown":
        """
        Create a ``DomainLossBreakdown`` using prior fractions only
        (no C5AI+ forecast available).

        Domain fractions of ``annual_losses``:
            biological = 60 %, structural = 20 %,
            environmental = 10 %, operational = 10 %

        Each domain is then split by sub-type priors.

        Parameters
        ----------
        annual_losses : np.ndarray
            Shape ``(N, T)`` gross simulated losses.

        Returns
        -------
        DomainLossBreakdown
            With ``bio_modelled = False``.
        """
        biological    = _split_domain(annual_losses, "biological",    DEFAULT_DOMAIN_FRACTIONS)
        structural    = _split_domain(annual_losses, "structural",    DEFAULT_DOMAIN_FRACTIONS)
        environmental = _split_domain(annual_losses, "environmental", DEFAULT_DOMAIN_FRACTIONS)
        operational   = _split_domain(annual_losses, "operational",   DEFAULT_DOMAIN_FRACTIONS)

        return cls(
            biological=biological,
            structural=structural,
            environmental=environmental,
            operational=operational,
            bio_modelled=False,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Cage technology helpers
# ─────────────────────────────────────────────────────────────────────────────

def apply_cage_multipliers_to_domain_fractions(
    domain_fractions: Dict[str, float],
    cage_multipliers: Dict[str, float],
) -> Dict[str, float]:
    """
    Scale domain fractions by cage technology multipliers and renormalise.

    Only domains present in ``domain_fractions`` are scaled; multipliers for
    domains not in the fractions dict are ignored.  The result is always
    renormalised to sum to 1.0.  If all scaled fractions are zero the
    original fractions are returned unchanged.

    Parameters
    ----------
    domain_fractions : Dict[str, float]
        Base fractions to scale (e.g. DEFAULT_DOMAIN_FRACTIONS).
    cage_multipliers : Dict[str, float]
        Per-domain multipliers from ``compute_locality_domain_multipliers()``.

    Returns
    -------
    Dict[str, float]
        Renormalised fractions after cage-technology adjustment.
    """
    scaled = {d: f * cage_multipliers.get(d, 1.0) for d, f in domain_fractions.items()}
    total = sum(scaled.values())
    if total == 0.0:
        return dict(domain_fractions)  # safety fallback
    return {d: v / total for d, v in scaled.items()}


# ─────────────────────────────────────────────────────────────────────────────
# Factory function
# ─────────────────────────────────────────────────────────────────────────────

def build_domain_loss_breakdown(
    annual_losses: np.ndarray,
    bio_breakdown: Optional[Dict[str, np.ndarray]] = None,
    domain_correlation: Optional["DomainCorrelationMatrix"] = None,
    rng: Optional[np.random.Generator] = None,
    cage_multipliers: Optional[Dict[str, float]] = None,
    non_bio_fracs_override: Optional[Dict[str, float]] = None,
) -> DomainLossBreakdown:
    """
    Convenience factory for ``DomainLossBreakdown``.

    If ``bio_breakdown`` is provided the biological slices are taken from it
    (C5AI+-modelled) and the remaining domains are filled with stub priors on
    the non-bio residual.  Otherwise all four domains use default prior
    fractions.

    When ``domain_correlation`` is provided the fixed domain fractions are
    perturbed by correlated Gaussian noise each simulation year so that
    domain losses co-vary realistically across years.

    When ``cage_multipliers`` is provided the domain fractions are scaled by
    the per-domain multipliers (from ``compute_locality_domain_multipliers()``)
    before loss decomposition.  For the C5AI+ path only the non-bio residual
    fractions are adjusted (biological domain is already modelled).

    Parameters
    ----------
    annual_losses : np.ndarray
        Shape ``(N, T)`` gross simulated losses.
    bio_breakdown : Dict[str, np.ndarray], optional
        Per-risk-type arrays from ``SimulationResults.bio_loss_breakdown``.
    domain_correlation : DomainCorrelationMatrix, optional
        Sprint 7 – governs co-movement of domain weight fractions.
    rng : np.random.Generator, optional
        Random number generator for the Gaussian perturbation.  If
        ``domain_correlation`` is provided and ``rng`` is None a default
        generator seeded at 0 is used and a ``UserWarning`` is emitted.
    cage_multipliers : Dict[str, float], optional
        Per-domain technology multipliers from cage portfolio aggregation.
        Scales domain fractions before loss decomposition.

    Returns
    -------
    DomainLossBreakdown
    """
    if bio_breakdown:
        if cage_multipliers:
            # Apply cage multipliers to non-bio residual fractions only
            _base_non_bio = non_bio_fracs_override if non_bio_fracs_override else _NON_BIO_DOMAIN_FRACTIONS
            eff_non_bio = apply_cage_multipliers_to_domain_fractions(
                _base_non_bio, cage_multipliers
            )
            biological = {k: v.copy() for k, v in bio_breakdown.items()}
            bio_total = sum(biological.values())
            residual = np.maximum(annual_losses - bio_total, 0.0)
            structural    = _split_domain(residual, "structural",    eff_non_bio)
            environmental = _split_domain(residual, "environmental", eff_non_bio)
            operational   = _split_domain(residual, "operational",   eff_non_bio)
            dbd = DomainLossBreakdown(
                biological=biological,
                structural=structural,
                environmental=environmental,
                operational=operational,
                bio_modelled=True,
            )
        else:
            if non_bio_fracs_override:
                biological = {k: v.copy() for k, v in bio_breakdown.items()}
                bio_total = sum(biological.values())
                residual = np.maximum(annual_losses - bio_total, 0.0)
                structural    = _split_domain(residual, "structural",    non_bio_fracs_override)
                environmental = _split_domain(residual, "environmental", non_bio_fracs_override)
                operational   = _split_domain(residual, "operational",   non_bio_fracs_override)
                dbd = DomainLossBreakdown(
                    biological=biological,
                    structural=structural,
                    environmental=environmental,
                    operational=operational,
                    bio_modelled=True,
                )
            else:
                dbd = DomainLossBreakdown.from_bio_breakdown(bio_breakdown, annual_losses)
    else:
        if cage_multipliers:
            # Apply cage multipliers to all domain fractions
            eff_fracs = apply_cage_multipliers_to_domain_fractions(
                DEFAULT_DOMAIN_FRACTIONS, cage_multipliers
            )
            biological    = _split_domain(annual_losses, "biological",    eff_fracs)
            structural    = _split_domain(annual_losses, "structural",    eff_fracs)
            environmental = _split_domain(annual_losses, "environmental", eff_fracs)
            operational   = _split_domain(annual_losses, "operational",   eff_fracs)
            dbd = DomainLossBreakdown(
                biological=biological,
                structural=structural,
                environmental=environmental,
                operational=operational,
                bio_modelled=False,
            )
        else:
            dbd = DomainLossBreakdown.prior_only(annual_losses)

    if domain_correlation is not None:
        if rng is None:
            warnings.warn(
                "domain_correlation provided without rng — results are not reproducible.",
                UserWarning,
                stacklevel=2,
            )
            rng = np.random.default_rng(0)
        dbd = apply_domain_correlation(dbd, annual_losses, domain_correlation, rng)

    return dbd


def build_smolt_domain_loss_breakdown(
    annual_losses: np.ndarray,
    domain_correlation: Optional["DomainCorrelationMatrix"] = None,
    rng: Optional[np.random.Generator] = None,
) -> "DomainLossBreakdown":
    """
    Build a DomainLossBreakdown using smolt / land-based RAS sub-types.

    Sub-type keys match the ``targeted_risk_types`` in smolt mitigation actions:
        operational → biofilter, oxygen, power, general_ops
        biological  → water_quality, biosecurity
        structural  → building, equipment_damage
        environmental → flood, utility_failure

    Domain fractions (SMOLT_DOMAIN_FRACTIONS):
        operational 70%, biological 22%, structural 5%, environmental 3%.
    """
    shape = annual_losses.shape

    def _split(domain_loss: np.ndarray, fractions: Dict[str, float]) -> Dict[str, np.ndarray]:
        return {k: domain_loss * v for k, v in fractions.items()}

    # Allocate total loss to domains
    op_losses  = annual_losses * SMOLT_DOMAIN_FRACTIONS["operational"]
    bio_losses = annual_losses * SMOLT_DOMAIN_FRACTIONS["biological"]
    str_losses = annual_losses * SMOLT_DOMAIN_FRACTIONS["structural"]
    env_losses = annual_losses * SMOLT_DOMAIN_FRACTIONS["environmental"]

    dbd = DomainLossBreakdown(
        operational   = _split(op_losses,  _SMOLT_OPS_SUBTYPE_FRACTIONS),
        biological    = _split(bio_losses, _SMOLT_BIO_SUBTYPE_FRACTIONS),
        structural    = _split(str_losses, _SMOLT_STRUCT_SUBTYPE_FRACTIONS),
        environmental = _split(env_losses, _SMOLT_ENV_SUBTYPE_FRACTIONS),
        bio_modelled              = False,
        structural_model_type    = "smolt_stub",
        environmental_model_type = "smolt_stub",
        operational_model_type   = "smolt_stub",
    )

    if domain_correlation is not None:
        if rng is None:
            rng = np.random.default_rng(0)
        dbd = apply_domain_correlation(dbd, annual_losses, domain_correlation, rng)

    return dbd


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 7 – correlated domain weight perturbation
# ─────────────────────────────────────────────────────────────────────────────

def _perturb_domain_weights(
    base_fracs: np.ndarray,
    N: int,
    T: int,
    domain_corr: "DomainCorrelationMatrix",
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate correlated domain weight fractions for each (N, T) year cell.

    Algorithm
    ---------
    1. Draw ``Z_raw ~ N(0, I_D)`` of shape ``(N·T, D)``.
    2. Apply Cholesky: ``Z_corr = Z_raw @ L.T``.
    3. Additive shift: ``w = base_fracs + α × Z_corr``.
    4. Clip to non-negative.
    5. Renormalise each row to sum to 1.

    Parameters
    ----------
    base_fracs : np.ndarray
        Shape ``(D,)`` — must sum to 1.
    N, T : int
        Simulation dimensions.
    domain_corr : DomainCorrelationMatrix
    rng : np.random.Generator

    Returns
    -------
    np.ndarray
        Shape ``(N, T, D)`` where each ``[n, t, :]`` sums to 1.
    """
    D = len(domain_corr.domains)
    L = domain_corr.cholesky()          # (D, D) lower-triangular

    Z_raw = rng.standard_normal((N * T, D))
    Z_corr = Z_raw @ L.T               # (N·T, D) correlated standard normals
    Z_corr = Z_corr.reshape(N, T, D)

    w = base_fracs[np.newaxis, np.newaxis, :] + domain_corr.perturbation_strength * Z_corr
    w = np.clip(w, 0.0, None)

    s = w.sum(axis=-1, keepdims=True)
    # When ALL fracs clip to zero (rare but possible with large perturbation_strength),
    # fall back to base_fracs so that totals are always preserved exactly.
    all_zero = s == 0.0
    w = np.where(all_zero, base_fracs[np.newaxis, np.newaxis, :], w)
    s = np.where(all_zero, 1.0, s)
    return w / s


def apply_domain_correlation(
    dbd: "DomainLossBreakdown",
    annual_losses: np.ndarray,
    domain_corr: "DomainCorrelationMatrix",
    rng: np.random.Generator,
) -> "DomainLossBreakdown":
    """
    Re-distribute domain losses using correlated Gaussian weight perturbation.

    When ``bio_modelled=False`` all four domain fractions are jointly perturbed
    using the full 4×4 matrix.  When ``bio_modelled=True`` (C5AI+ enriched)
    the bio slices are kept unchanged and only the non-bio residual split
    (structural / environmental / operational) is perturbed using the 3×3
    sub-matrix.

    In both cases the portfolio total is preserved exactly:
    ``new_dbd.total() ≈ annual_losses`` (within floating-point precision).

    Parameters
    ----------
    dbd : DomainLossBreakdown
        Existing breakdown (created by ``prior_only`` or ``from_bio_breakdown``).
    annual_losses : np.ndarray
        Shape ``(N, T)`` gross simulated losses.  Used to determine shape and
        to derive domain base losses when ``bio_modelled=True``.
    domain_corr : DomainCorrelationMatrix
        4×4 (or compatible) correlation object.
    rng : np.random.Generator

    Returns
    -------
    DomainLossBreakdown
        New instance with ``domain_correlation_applied=True``.
    """
    N, T = annual_losses.shape

    if not dbd.bio_modelled:
        # ── Prior-only path: perturb all 4 domain fractions ──────────────────
        # Use smolt or sea fractions depending on facility type
        is_smolt = dbd.operational_model_type == "smolt_stub"
        domain_fracs_map = SMOLT_DOMAIN_FRACTIONS if is_smolt else DEFAULT_DOMAIN_FRACTIONS
        subtype_fracs_map = _SMOLT_SUBTYPE_FRACTIONS if is_smolt else _SUBTYPE_FRACTIONS

        domain_names = list(DOMAINS)
        base_fracs = np.array(
            [domain_fracs_map[d] for d in domain_names], dtype=float
        )

        # Use sub_matrix in case domain_corr covers a subset; default is 4-domain
        dcm = domain_corr.sub_matrix(domain_names) if set(domain_names) != set(domain_corr.domains) else domain_corr
        weights = _perturb_domain_weights(base_fracs, N, T, dcm, rng)  # (N, T, 4)

        domain_losses: Dict[str, np.ndarray] = {}
        for di, dname in enumerate(domain_names):
            domain_losses[dname] = annual_losses * weights[:, :, di]

        def _split_domain(arr: np.ndarray, domain: str) -> Dict[str, np.ndarray]:
            return {st: arr * frac for st, frac in subtype_fracs_map[domain].items()}

        biological    = _split_domain(domain_losses["biological"],    "biological")
        structural    = _split_domain(domain_losses["structural"],    "structural")
        environmental = _split_domain(domain_losses["environmental"], "environmental")
        operational   = _split_domain(domain_losses["operational"],   "operational")

        op_type = "smolt_stub" if is_smolt else "stub"
        return DomainLossBreakdown(
            biological=biological,
            structural=structural,
            environmental=environmental,
            operational=operational,
            bio_modelled=False,
            structural_model_type=op_type,
            environmental_model_type=op_type,
            operational_model_type=op_type,
            domain_correlation_applied=True,
        )

    else:
        # ── C5AI+ enriched path: keep bio slices, perturb non-bio residual ───
        bio_total = sum(dbd.biological.values())
        residual = np.maximum(annual_losses - bio_total, 0.0)

        non_bio_names = ["structural", "environmental", "operational"]
        base_non_bio = np.array(
            [_NON_BIO_DOMAIN_FRACTIONS[d] for d in non_bio_names], dtype=float
        )

        # Extract 3×3 sub-matrix for non-bio domains
        sub_dcm = domain_corr.sub_matrix(non_bio_names)
        weights = _perturb_domain_weights(base_non_bio, N, T, sub_dcm, rng)  # (N, T, 3)

        non_bio_losses: Dict[str, np.ndarray] = {}
        for di, dname in enumerate(non_bio_names):
            non_bio_losses[dname] = residual * weights[:, :, di]

        structural    = _split_by_subtype(non_bio_losses["structural"],    "structural")
        environmental = _split_by_subtype(non_bio_losses["environmental"], "environmental")
        operational   = _split_by_subtype(non_bio_losses["operational"],   "operational")

        # Bio slices are unchanged (copy)
        biological = {k: v.copy() for k, v in dbd.biological.items()}

        return DomainLossBreakdown(
            biological=biological,
            structural=structural,
            environmental=environmental,
            operational=operational,
            bio_modelled=True,
            domain_correlation_applied=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _split_by_subtype(
    domain_total: np.ndarray,
    domain: str,
) -> Dict[str, np.ndarray]:
    """
    Split a domain-total array into sub-type arrays using fixed sub-type priors.

    Unlike ``_split_domain``, this function takes the already-computed domain
    total directly (no domain-level fraction multiplication).  Used by the
    correlation perturbation path where domain totals are computed first, then
    sub-divided.

    Parameters
    ----------
    domain_total : np.ndarray
        Shape ``(N, T)`` — total losses for this domain.
    domain : str
        Domain name (must exist in ``_SUBTYPE_FRACTIONS``).

    Returns
    -------
    Dict[str, np.ndarray]
        Sub-type name → ``(N, T)`` array.
    """
    subtype_fracs = _SUBTYPE_FRACTIONS[domain]
    return {st: domain_total * f for st, f in subtype_fracs.items()}


def _split_domain(
    base: np.ndarray,
    domain: str,
    domain_fractions: Dict[str, float],
) -> Dict[str, np.ndarray]:
    """
    Split ``base * domain_fraction`` into sub-type arrays using the
    domain's sub-type fraction constants.

    Parameters
    ----------
    base : np.ndarray
        Array to split (either annual_losses or non-bio residual).
    domain : str
        Domain name key (must exist in ``domain_fractions`` and
        ``_SUBTYPE_FRACTIONS``).
    domain_fractions : Dict[str, float]
        Fraction of ``base`` allocated to ``domain``.

    Returns
    -------
    Dict[str, np.ndarray]
        Sub-type name → (N, T) array.
    """
    domain_f = domain_fractions.get(domain, 0.0)
    domain_base = base * domain_f
    subtype_fracs = _SUBTYPE_FRACTIONS[domain]
    return {st: domain_base * f for st, f in subtype_fracs.items()}
