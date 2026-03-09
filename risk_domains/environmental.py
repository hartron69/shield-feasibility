"""
Shield Captive Risk Platform – Environmental Risk Domain (Sprint 6).

Covers oxygen stress, extreme temperature events, current/storm damage,
and ice exposure for salmon aquaculture sites.

Modelling status
----------------
This is a **feasibility-grade environmental risk model**, not a full
oceanographic or meteorological analysis.  Loss estimates are derived from
transparent industry-informed priors scaled by site total insured value (TIV)
and an optional site exposure factor.

    model_type = "environmental_prior"
    confidence = 0.15 (low, appropriate for prior-only modelling)

Sub-types (must match DOMAIN_SUBTYPES["environmental"])
-------------------------------------------------------
oxygen_stress
    Hypoxic water intrusion, algal bloom oxygen depletion, or thermocline
    stratification causing low-oxygen stress events.  Annual probability ~10%.

temperature_extreme
    Extreme cold snaps or unusually warm surface layers causing thermal stress,
    increased lice reproduction, or gill damage.  Annual probability ~7%.

current_storm
    Strong current or storm wave damage to cages, moorings, or infrastructure.
    Higher impact on exposed sites.  Annual probability ~6%.

ice
    Sea ice formation causing physical damage to equipment, blocking vessel
    access, or compromising cage integrity.  Annual probability ~3%.

Limitations
-----------
* Probabilities are site-class priors, not site-specific oceanographic values.
* A site exposure factor scales base probabilities (e.g. sheltered fjord ×0.5,
  northern exposed coast ×2.0).  Transparency feature, not a calibrated model.
* No correlation between environmental sub-types is modelled.
* Full oceanographic modelling is planned for a future production release.

Platform principle
------------------
This is a risk modelling and insurance decision support platform, NOT an
environmental monitoring or early-warning system.
"""

from __future__ import annotations

import warnings
from typing import List

from risk_domains.base_domain import DomainRiskSummary, RiskDomain


# ─────────────────────────────────────────────────────────────────────────────
# Feasibility-grade environmental risk priors
# ─────────────────────────────────────────────────────────────────────────────

#: Per-sub-type risk profile.
#:
#: annual_probability : float
#:     Baseline annual event probability for a median-exposure aquaculture site.
#: loss_fraction_of_tiv : float
#:     Expected loss per event as a fraction of site TIV (conditional on event).
#: description : str
#:     Plain-language description for board/investor reporting.
ENVIRONMENTAL_RISK_PROFILES = {
    "oxygen_stress": {
        "annual_probability": 0.10,      # 1-in-10 year event
        "loss_fraction_of_tiv": 0.05,    # 5% of site TIV per event
        "description": (
            "Hypoxic water intrusion, algal bloom oxygen depletion, or thermocline "
            "stratification causing low-oxygen stress events leading to mortality "
            "or reduced growth.  More common in inner fjords and sheltered bays."
        ),
    },
    "temperature_extreme": {
        "annual_probability": 0.07,      # 1-in-14 year event
        "loss_fraction_of_tiv": 0.04,    # 4% of site TIV per event
        "description": (
            "Extreme cold snaps or unusually warm surface layers causing thermal "
            "stress, increased sea lice reproduction rates, or gill damage.  "
            "Northern sites are more exposed to ice-related temperature extremes."
        ),
    },
    "current_storm": {
        "annual_probability": 0.06,      # 1-in-17 year event
        "loss_fraction_of_tiv": 0.07,    # 7% of site TIV per event – higher severity
        "description": (
            "Damage from strong tidal currents or storm-driven wave action to "
            "cages, moorings, and ancillary infrastructure.  Severity depends "
            "strongly on site exposure; exposed coastal sites significantly more "
            "vulnerable than sheltered fjord locations."
        ),
    },
    "ice": {
        "annual_probability": 0.03,      # 1-in-33 year event – rarer, geographic
        "loss_fraction_of_tiv": 0.06,    # 6% of site TIV per event
        "description": (
            "Sea ice formation causing physical damage to equipment, blocking "
            "vessel access, compromising cage integrity, or creating extreme "
            "operational conditions.  Primarily relevant for northern Norwegian "
            "and Arctic aquaculture locations."
        ),
    },
}

#: Minimum site exposure factor (sheltered inner fjord / enclosed bay).
_EXPOSURE_FACTOR_MIN = 0.50
#: Maximum site exposure factor (northern exposed coast / open sea).
_EXPOSURE_FACTOR_MAX = 2.00


class EnvironmentalRiskDomain(RiskDomain):
    """
    Environmental risk domain – feasibility-grade prior model (Sprint 6).

    Returns sub-type risk summaries scaled by site TIV and an optional
    site exposure factor.

    All four sub-types use ``model_type = "environmental_prior"`` to distinguish
    them from the old generic ``"stub"`` classification.

    Parameters
    ----------
    site_exposure_factor : float, default 1.0
        Multiplier on base annual probabilities to reflect site exposure.
        Typical range: 0.50 (sheltered inner fjord) to 2.00 (northern exposed
        coast).  Values outside [0.50, 2.00] are clipped with a UserWarning.
    """

    domain_name = "environmental"

    def __init__(self, site_exposure_factor: float = 1.0) -> None:
        lo, hi = _EXPOSURE_FACTOR_MIN, _EXPOSURE_FACTOR_MAX
        if not (lo <= site_exposure_factor <= hi):
            warnings.warn(
                f"EnvironmentalRiskDomain: site_exposure_factor {site_exposure_factor:.2f} "
                f"is outside recommended range [{lo}, {hi}]. "
                f"Clipping to nearest bound.",
                UserWarning,
                stacklevel=2,
            )
        self.site_exposure_factor = float(max(lo, min(hi, site_exposure_factor)))

    def assess(self, site_tiv_nok: float = 0.0) -> List[DomainRiskSummary]:
        """
        Return feasibility-grade environmental risk summaries.

        Expected annual loss per sub-type:
            adjusted_prob = min(1.0, base_prob × site_exposure_factor)
            EAL = adjusted_prob × loss_fraction × TIV

        Parameters
        ----------
        site_tiv_nok : float
            Total insured value for the site in NOK.  If zero, monetary
            estimates are zero but probabilities are still returned.

        Returns
        -------
        List[DomainRiskSummary]
            One entry per environmental sub-type.
        """
        summaries: List[DomainRiskSummary] = []

        for sub_type, profile in ENVIRONMENTAL_RISK_PROFILES.items():
            base_prob = profile["annual_probability"]
            adjusted_prob = min(1.0, base_prob * self.site_exposure_factor)
            expected_loss = adjusted_prob * site_tiv_nok * profile["loss_fraction_of_tiv"]

            summaries.append(DomainRiskSummary(
                domain=self.domain_name,
                sub_type=sub_type,
                event_probability=adjusted_prob,
                expected_annual_loss_nok=expected_loss,
                model_type="environmental_prior",
                confidence=0.15,
                data_quality="PRIOR_ONLY",
                metadata={
                    "description": profile["description"],
                    "base_probability": base_prob,
                    "site_exposure_factor": self.site_exposure_factor,
                    "loss_fraction_of_tiv": profile["loss_fraction_of_tiv"],
                    "modelling_note": (
                        "Feasibility-grade environmental prior. "
                        "Not a site-specific oceanographic or meteorological assessment. "
                        "Full environmental modelling planned for future release."
                    ),
                },
            ))

        return summaries
