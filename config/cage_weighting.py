"""
config/cage_weighting.py — Configuration for the multi-factor cage weighting model.

This module defines how different risk-relevant properties of a cage contribute
to the locality-level domain risk aggregation.  Changing these values changes
the relative importance of biomass, value, consequence, operational complexity,
and structural criticality across the four risk domains.

Design principles
-----------------
* All numbers are dimensionless — they are ratios used in a normalised formula.
* Row sums within DOMAIN_COMPONENT_WEIGHTS do NOT need to equal 1.0; each row
  defines relative importance.  The cross-cage normalisation step means only
  the ratios between columns matter.
* CAGE_TYPE_DEFAULT_SCORES provide sensible starting points for complexity and
  criticality when a cage has not been explicitly scored.  They should reflect
  typical engineering knowledge about each technology.
* This module is intentionally free of business logic — it is a pure config
  table that can be overridden or version-controlled separately.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Component weight table — how each weighting component influences each domain
# ─────────────────────────────────────────────────────────────────────────────

#: For each domain, the relative contribution of each weighting component.
#: Keys: "biomass", "value", "consequence", "complexity", "criticality"
#: Columns must sum to 1.0 for each domain (enforced at startup).
DOMAIN_COMPONENT_WEIGHTS: dict = {
    "biological": {
        "biomass":     0.50,   # standing biomass drives bio exposure
        "value":       0.25,   # high-value stock = greater loss if affected
        "consequence": 0.15,   # loss consequence amplified by system design
        "complexity":  0.05,   # operational complexity has minor bio effect
        "criticality": 0.05,   # structural criticality has minor bio effect
    },
    "structural": {
        "biomass":     0.25,   # biomass matters less for structural failure
        "value":       0.15,   # higher-value sites warrant better infrastructure
        "consequence": 0.30,   # structural failures often have catastrophic consequences
        "complexity":  0.15,   # complex structures have more failure modes
        "criticality": 0.15,   # single-point-of-failure structural elements
    },
    "environmental": {
        "biomass":     0.30,   # exposed biomass drives environmental loss
        "value":       0.10,   # value weighting is lower for environmental events
        "consequence": 0.25,   # weather/HAB consequence depends on system exposure
        "complexity":  0.25,   # complex systems have more environmental dependencies
        "criticality": 0.10,   # criticality moderately relevant for environmental
    },
    "operational": {
        "biomass":     0.15,   # ops risk is not strongly proportional to biomass
        "value":       0.10,   # value matters but less than for bio/structural
        "consequence": 0.25,   # operational failures can have large consequences
        "complexity":  0.30,   # operational complexity is the primary driver
        "criticality": 0.20,   # critical systems (SPOF, low redundancy) have high ops risk
    },
}

# Validate that each domain row sums to 1.0
for _domain, _weights in DOMAIN_COMPONENT_WEIGHTS.items():
    _total = sum(_weights.values())
    if abs(_total - 1.0) > 1e-9:
        raise ValueError(
            f"DOMAIN_COMPONENT_WEIGHTS['{_domain}'] sums to {_total}, expected 1.0"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Cage-type default scores
# ─────────────────────────────────────────────────────────────────────────────

#: Default operational complexity, structural criticality, redundancy level, and
#: failure_mode_class for each cage type.  Used when a cage has not been
#: explicitly scored by the operator.
#:
#: Rationale:
#:   open_net     — mature, low-tech, well-understood failure modes
#:   semi_closed  — more complex systems, moderate failure consequence
#:   fully_closed — high-complexity RAS-like systems; high consequence if failed
#:   submerged    — complex logistics, elevated structural loading, less redundancy
CAGE_TYPE_DEFAULT_SCORES: dict = {
    "open_net": {
        "complexity":         0.20,   # 0–1 scale
        "criticality":        0.20,   # 0–1 scale
        "redundancy_level":   3,      # 1–5 integer (3 = standard)
        "failure_mode_class": "proportional",
    },
    "semi_closed": {
        "complexity":         0.55,
        "criticality":        0.45,
        "redundancy_level":   2,
        "failure_mode_class": "proportional",
    },
    "fully_closed": {
        "complexity":         0.80,
        "criticality":        0.65,
        "redundancy_level":   2,
        "failure_mode_class": "proportional",
    },
    "submerged": {
        "complexity":         0.70,
        "criticality":        0.60,
        "redundancy_level":   2,
        "failure_mode_class": "proportional",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Failure mode class — consequence amplification
# ─────────────────────────────────────────────────────────────────────────────

#: Multiplier applied to the consequence component based on failure mode class.
#: "proportional"           — normal, smooth risk behaviour
#: "threshold"              — step-change when a threshold is crossed (higher consequence)
#: "binary_high_consequence"— failure is near-total or catastrophic (much higher consequence)
FAILURE_MODE_CONSEQUENCE_MULTIPLIER: dict = {
    "proportional":           1.0,
    "threshold":              1.5,
    "binary_high_consequence": 2.5,
}

VALID_FAILURE_MODE_CLASSES: frozenset = frozenset(FAILURE_MODE_CONSEQUENCE_MULTIPLIER.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Criticality modifiers
# ─────────────────────────────────────────────────────────────────────────────

#: When a cage is the single point of failure for a locality (e.g. sole power
#: supply, sole feed system), multiply criticality by this factor.
SPOF_CRITICALITY_MULTIPLIER: float = 2.0

#: Criticality scale factor based on redundancy level (1–5).
#: 1 = no redundancy; 5 = highly redundant / fail-safe design.
#: Values < 1.0 reduce the cage's criticality contribution.
REDUNDANCY_CRITICALITY_SCALE: dict = {
    1: 2.0,    # no redundancy  — much higher criticality
    2: 1.5,    # low redundancy — elevated criticality
    3: 1.0,    # standard       — baseline criticality
    4: 0.75,   # good redundancy — reduced criticality
    5: 0.50,   # full redundancy — substantially reduced criticality
}

VALID_REDUNDANCY_LEVELS: frozenset = frozenset(REDUNDANCY_CRITICALITY_SCALE.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Score range constraints
# ─────────────────────────────────────────────────────────────────────────────

COMPLEXITY_SCORE_RANGE: tuple = (0.0, 1.0)
CRITICALITY_SCORE_RANGE: tuple = (0.0, 1.0)
MATURITY_SCORE_RANGE:    tuple = (0.0, 1.0)
CONSEQUENCE_FACTOR_MIN:  float = 0.0
