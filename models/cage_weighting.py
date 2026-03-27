"""
models/cage_weighting.py — Multi-factor cage weighting engine.

Computes locality-level domain risk multipliers from a portfolio of cages,
using up to five weighting components:

  biomass     — standing biomass in the cage
  value       — biomass value (NOK) if provided
  consequence — value × consequence_factor × failure_mode_multiplier
  complexity  — operational complexity score (0–1)
  criticality — structural criticality × SPOF × redundancy adjustment

When no advanced fields are set on any cage in the locality, the function
falls back to the existing biomass-only aggregation (exact backward compat).

When advanced data is present, each domain has its OWN cage weighting
distribution — structural risk is driven more by consequence and criticality,
while biological risk is driven more by biomass and value.

Formula summary
---------------
1.  Derive raw component values per cage (biomass, value, consequence, complexity, criticality).
2.  Normalise each component to [0, 1] across the locality (max-normalisation).
3.  Compute domain-specific raw weight per cage:
      raw_weight[cage][domain] = Σ_k DOMAIN_COMPONENT_WEIGHTS[domain][k] × norm_k[cage]
4.  Normalise raw weights across cages per domain → cage_domain_weight[cage][domain].
5.  Locality multiplier:
      locality_mult[domain] = Σ_cage cage_domain_weight[cage][domain] × CAGE_DOMAIN_MULT[type][domain]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.cage_technology import CagePenConfig

from config.cage_weighting import (
    CAGE_TYPE_DEFAULT_SCORES,
    DOMAIN_COMPONENT_WEIGHTS,
    FAILURE_MODE_CONSEQUENCE_MULTIPLIER,
    REDUNDANCY_CRITICALITY_SCALE,
    SPOF_CRITICALITY_MULTIPLIER,
    VALID_FAILURE_MODE_CLASSES,
)
from models.cage_technology import (
    CAGE_DOMAIN_MULTIPLIERS,
    DOMAINS,
    compute_locality_domain_multipliers,
)

_COMPONENTS = ("biomass", "value", "consequence", "complexity", "criticality")


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CageWeightDetail:
    """
    Per-cage weighting breakdown — exposed in FeasibilityResponse for explainability.

    Attributes
    ----------
    cage_id : str
    cage_type : str
    biomass_tonnes : float
    biomass_value_nok : float or None
        As supplied on the cage; None if not provided.
    derived_complexity : float
        Effective complexity score (0–1) after type-default resolution.
    derived_criticality : float
        Effective criticality score after SPOF / redundancy modifiers.
    failure_mode_class : str
    domain_weights : Dict[str, float]
        Normalised cage contribution per domain (sums to 1.0 across all cages
        for each domain, NOT across domains for one cage).
    defaults_used : bool
        True if any field was sourced from CAGE_TYPE_DEFAULT_SCORES.
    """
    cage_id: str
    cage_type: str
    biomass_tonnes: float
    biomass_value_nok: Optional[float]
    derived_complexity: float
    derived_criticality: float
    failure_mode_class: str
    domain_weights: Dict[str, float] = field(default_factory=dict)
    defaults_used: bool = False


@dataclass
class AdvancedWeightingResult:
    """
    Result of compute_locality_domain_multipliers_advanced().

    domain_multipliers is the only field consumed by the rest of the pipeline
    (MonteCarloEngine / build_domain_loss_breakdown).  All other fields are for
    transparency and API response construction.
    """
    domain_multipliers: Dict[str, float]
    weighting_mode: str                         # "advanced" | "biomass_only"
    cage_weight_details: List[CageWeightDetail]
    warnings: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Advanced field detection
# ─────────────────────────────────────────────────────────────────────────────

def _cage_has_advanced_data(cage: "CagePenConfig") -> bool:
    """Return True if this cage carries any explicitly-set advanced risk field."""
    return (
        cage.biomass_value_nok is not None
        or (cage.consequence_factor is not None and cage.consequence_factor != 1.0)
        or cage.operational_complexity_score is not None
        or cage.structural_criticality_score is not None
        or cage.single_point_of_failure is True
        or cage.redundancy_level is not None
        or (cage.failure_mode_class is not None
            and cage.failure_mode_class != "proportional")
    )


def _locality_has_advanced_data(cages: list) -> bool:
    """Return True if any cage in the locality has advanced risk data."""
    return any(_cage_has_advanced_data(c) for c in cages)


# ─────────────────────────────────────────────────────────────────────────────
# Raw component derivation
# ─────────────────────────────────────────────────────────────────────────────

def _derive_raw_components(cage: "CagePenConfig") -> tuple:
    """
    Compute the five raw weighting components for one cage.

    Returns
    -------
    tuple (biomass, value, consequence, complexity, criticality, fm_class, defaults_used)
    """
    defaults_used = False

    # ── Biomass (always present — validated in CagePenConfig) ─────────────────
    biomass = cage.biomass_tonnes

    # ── Value (0 if not provided) ─────────────────────────────────────────────
    value = float(cage.biomass_value_nok) if cage.biomass_value_nok is not None else 0.0

    # ── Consequence ───────────────────────────────────────────────────────────
    cf = cage.consequence_factor if cage.consequence_factor is not None else 1.0
    fm_class = cage.failure_mode_class
    if fm_class is None:
        fm_class = CAGE_TYPE_DEFAULT_SCORES[cage.cage_type]["failure_mode_class"]
        defaults_used = True
    fm_mult = FAILURE_MODE_CONSEQUENCE_MULTIPLIER[fm_class]
    consequence = value * cf * fm_mult

    # ── Operational complexity ────────────────────────────────────────────────
    if cage.operational_complexity_score is not None:
        complexity = float(cage.operational_complexity_score)
    else:
        complexity = CAGE_TYPE_DEFAULT_SCORES[cage.cage_type]["complexity"]
        defaults_used = True

    # ── Structural criticality ────────────────────────────────────────────────
    if cage.structural_criticality_score is not None:
        base_crit = float(cage.structural_criticality_score)
    else:
        base_crit = CAGE_TYPE_DEFAULT_SCORES[cage.cage_type]["criticality"]
        defaults_used = True

    spof_mult = SPOF_CRITICALITY_MULTIPLIER if cage.single_point_of_failure else 1.0

    red_level = cage.redundancy_level
    if red_level is None:
        red_level = CAGE_TYPE_DEFAULT_SCORES[cage.cage_type]["redundancy_level"]
        defaults_used = True
    red_scale = REDUNDANCY_CRITICALITY_SCALE.get(red_level, 1.0)

    criticality = base_crit * spof_mult * red_scale

    return biomass, value, consequence, complexity, criticality, fm_class, defaults_used


# ─────────────────────────────────────────────────────────────────────────────
# Component normalisation
# ─────────────────────────────────────────────────────────────────────────────

def _max_normalise(values: list) -> list:
    """
    Max-normalise a list of floats to [0, 1].

    If max is 0 (all values are zero), all outputs are 0.
    """
    max_val = max(values) if values else 0.0
    if max_val == 0.0:
        return [0.0] * len(values)
    return [v / max_val for v in values]


# ─────────────────────────────────────────────────────────────────────────────
# Core engine
# ─────────────────────────────────────────────────────────────────────────────

def compute_locality_domain_multipliers_advanced(
    cages: list,
) -> AdvancedWeightingResult:
    """
    Compute locality-level domain risk multipliers using multi-factor weighting.

    If no cage carries advanced data (biomass-only input), falls back to the
    exact biomass-weighted result from ``compute_locality_domain_multipliers()``
    and returns ``weighting_mode="biomass_only"``.

    Parameters
    ----------
    cages : List[CagePenConfig]
        Non-empty list of cage configurations for the locality.

    Returns
    -------
    AdvancedWeightingResult
        Contains domain_multipliers (Dict[str, float]) plus transparency data.

    Raises
    ------
    ValueError
        If cages is empty.
    """
    if not cages:
        raise ValueError("cages must be a non-empty list")

    warnings: list = []

    # ── Fast path: biomass-only (exact backward compat) ───────────────────────
    if not _locality_has_advanced_data(cages):
        mults = compute_locality_domain_multipliers(cages)
        details = [
            CageWeightDetail(
                cage_id=c.cage_id,
                cage_type=c.cage_type,
                biomass_tonnes=c.biomass_tonnes,
                biomass_value_nok=None,
                derived_complexity=CAGE_TYPE_DEFAULT_SCORES[c.cage_type]["complexity"],
                derived_criticality=CAGE_TYPE_DEFAULT_SCORES[c.cage_type]["criticality"],
                failure_mode_class=CAGE_TYPE_DEFAULT_SCORES[c.cage_type]["failure_mode_class"],
                domain_weights={},    # not computed in biomass-only mode
                defaults_used=True,
            )
            for c in cages
        ]
        return AdvancedWeightingResult(
            domain_multipliers=mults,
            weighting_mode="biomass_only",
            cage_weight_details=details,
            warnings=[],
        )

    # ── Advanced path ─────────────────────────────────────────────────────────

    # Step 1 — derive raw components per cage
    raw: list = []
    fm_classes: list = []
    defaults_flags: list = []
    for c in cages:
        bio, val, cons, compl, crit, fm_cls, def_used = _derive_raw_components(c)
        raw.append((bio, val, cons, compl, crit))
        fm_classes.append(fm_cls)
        defaults_flags.append(def_used)

        # Emit warnings
        if c.consequence_factor is not None and c.consequence_factor != 1.0 and c.biomass_value_nok is None:
            warnings.append(
                f"Cage {c.cage_id}: consequence_factor is set but biomass_value_nok is None "
                "— consequence component will be 0."
            )
        if c.biomass_value_nok is not None and c.biomass_value_nok > c.biomass_tonnes * 200_000:
            warnings.append(
                f"Cage {c.cage_id}: biomass_value_nok ({c.biomass_value_nok:,.0f}) seems "
                f"very high relative to biomass ({c.biomass_tonnes} t) — check units."
            )
        if c.single_point_of_failure and (
            c.structural_criticality_score is None or c.structural_criticality_score < 0.5
        ):
            warnings.append(
                f"Cage {c.cage_id}: single_point_of_failure=True but structural_criticality_score "
                "is low or absent — consider setting an explicit criticality score."
            )

    # Step 2 — normalise each component across the locality
    n = len(cages)
    comp_arrays = list(zip(*raw))  # tuple of 5 lists, one per component
    norm_arrays = [_max_normalise(list(col)) for col in comp_arrays]  # 5 × n
    # Transpose back: norm[i] = (norm_biomass, norm_value, norm_cons, norm_compl, norm_crit) for cage i
    norm = list(zip(*norm_arrays))  # n × 5

    # Step 3 — raw_weight per cage per domain
    raw_weights: list = []   # n dicts
    for i, cage_norm in enumerate(norm):
        cage_raw: dict = {}
        for domain in DOMAINS:
            coeff = DOMAIN_COMPONENT_WEIGHTS[domain]
            w = sum(coeff[comp] * cage_norm[j] for j, comp in enumerate(_COMPONENTS))
            cage_raw[domain] = w
        raw_weights.append(cage_raw)

    # Step 4 — normalise across cages per domain
    cage_domain_weights: list = [{} for _ in range(n)]
    for domain in DOMAINS:
        domain_total = sum(raw_weights[i][domain] for i in range(n))
        if domain_total == 0.0:
            # Uniform fallback (biomass always > 0 so this should never trigger, but be safe)
            for i in range(n):
                cage_domain_weights[i][domain] = 1.0 / n
        else:
            for i in range(n):
                cage_domain_weights[i][domain] = raw_weights[i][domain] / domain_total

    # Step 5 — locality domain multiplier
    domain_multipliers: dict = {}
    for domain in DOMAINS:
        mult = sum(
            cage_domain_weights[i][domain] * CAGE_DOMAIN_MULTIPLIERS[cages[i].cage_type][domain]
            for i in range(n)
        )
        domain_multipliers[domain] = mult

    # Build CageWeightDetail list
    details: list = []
    for i, c in enumerate(cages):
        bio, val, cons, compl, crit, fm_cls, def_used = (
            raw[i][0], raw[i][1], raw[i][2], raw[i][3], raw[i][4], fm_classes[i], defaults_flags[i]
        )
        details.append(CageWeightDetail(
            cage_id=c.cage_id,
            cage_type=c.cage_type,
            biomass_tonnes=c.biomass_tonnes,
            biomass_value_nok=c.biomass_value_nok,
            derived_complexity=round(compl, 4),
            derived_criticality=round(crit, 4),
            failure_mode_class=fm_cls,
            domain_weights={d: round(cage_domain_weights[i][d], 6) for d in DOMAINS},
            defaults_used=def_used,
        ))

    return AdvancedWeightingResult(
        domain_multipliers=domain_multipliers,
        weighting_mode="advanced",
        cage_weight_details=details,
        warnings=warnings,
    )
