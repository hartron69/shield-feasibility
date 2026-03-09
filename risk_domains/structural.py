"""
Shield Captive Risk Platform – Structural Risk Domain (Sprint 5).

Covers mooring failure, net integrity, cage structural failure, and feed-
system damage — the four primary structural risk sub-types for salmon
aquaculture facilities.

Modelling status
----------------
This is a **feasibility-grade structural risk model**, not a full engineering
or hydrodynamic analysis.  Loss estimates are derived from transparent
industry-informed priors scaled by site total insured value (TIV) and an
optional site exposure factor.

    model_type = "structural_prior"
    confidence = 0.15 (low, appropriate for prior-only modelling)

The model is intentionally simple and auditable so that board-level and
insurance users can understand and challenge the assumptions.

Sub-type descriptions
---------------------
mooring_failure
    Failure of anchors, mooring lines, chains, or connectors under storm
    loading, current fatigue, or corrosion.  Primary driver of total-loss
    or significant cage-drift events.  Annual probability ~5% per site.

net_integrity
    Net tears, predator breaches, corrosion of sinker tubes, or mesh
    degradation.  More frequent than structural failures; lower individual
    severity.  Annual probability ~10% per site.

cage_structural
    Deformation or collapse of the cage ring, frame, or connecting collar
    under ice load, current stress, or overloading.  Less frequent than
    net events; higher severity.  Annual probability ~4% per site.

feed_system
    Failure of automatic feeders, feed barges, pipes, or compressed-air
    systems.  Relatively common, low to moderate severity.
    Annual probability ~8% per site.

Limitations
-----------
* Probabilities are site-class priors, not site-specific engineering values.
* A site exposure factor can be supplied to scale the base probabilities
  (e.g. exposed coast ×1.5, sheltered fjord ×0.7).  This is a transparency
  feature, not a calibrated model.
* No correlation between structural sub-types is modelled — in reality,
  storm events tend to trigger multiple failure modes simultaneously.
* Full engineering-grade modelling (finite element, hydrodynamic, fatigue
  analysis) is planned for a future production release.

Platform principle
------------------
This is a risk modelling and insurance decision support platform, NOT a
structural engineering assessment tool or early-warning system.
"""

from __future__ import annotations

from typing import List

from risk_domains.base_domain import DomainRiskSummary, RiskDomain


# ─────────────────────────────────────────────────────────────────────────────
# Feasibility-grade structural risk priors
# ─────────────────────────────────────────────────────────────────────────────

#: Per-sub-type risk profile.
#:
#: annual_probability : float
#:     Baseline annual event probability for a median-exposure aquaculture site.
#:     Source: Norwegian aquaculture industry loss statistics and expert judgment.
#: loss_fraction_of_tiv : float
#:     Expected loss per event as a fraction of site TIV.
#:     Conditional on an event occurring.
#: description : str
#:     Plain-language description for board/investor reporting.
STRUCTURAL_RISK_PROFILES = {
    "mooring_failure": {
        "annual_probability": 0.05,      # 1-in-20 year event
        "loss_fraction_of_tiv": 0.12,    # 12% of site TIV per event
        "description": (
            "Mooring system failure (anchor drag, line or chain parting, connector "
            "corrosion) under storm, tidal current, or ice load.  Can lead to cage "
            "drift, biomass loss, or total site loss."
        ),
    },
    "net_integrity": {
        "annual_probability": 0.10,      # 1-in-10 year per site
        "loss_fraction_of_tiv": 0.04,    # 4% of TIV – lower severity
        "description": (
            "Net damage including mesh tear, predator breach, UV degradation, or "
            "sinker tube corrosion.  Higher frequency than structural events; "
            "individual severity lower but significant biomass escape risk."
        ),
    },
    "cage_structural": {
        "annual_probability": 0.04,      # 1-in-25 year – rare, severe
        "loss_fraction_of_tiv": 0.08,    # 8% of TIV
        "description": (
            "Deformation or collapse of cage ring, frame, or connecting collar "
            "under ice loading, extreme currents, vessel collision, or structural "
            "fatigue.  Typically triggers large biomass losses and long downtime."
        ),
    },
    "feed_system": {
        "annual_probability": 0.08,      # 1-in-12 year
        "loss_fraction_of_tiv": 0.02,    # 2% of TIV – frequent, low severity
        "description": (
            "Failure of automatic feeders, feed barges, feed pipes, or "
            "compressed-air delivery systems.  Common events with limited "
            "biomass loss but relevant for operational continuity."
        ),
    },
}

#: Minimum exposure scale factor (sheltered fjord / inner bay).
_EXPOSURE_FACTOR_MIN = 0.60
#: Maximum exposure scale factor (open coast / exposed headland).
_EXPOSURE_FACTOR_MAX = 2.00


class StructuralRiskDomain(RiskDomain):
    """
    Structural risk domain – feasibility-grade prior model (Sprint 5).

    Returns sub-type risk summaries scaled by site TIV and an optional
    site exposure factor.

    All four sub-types use ``model_type = "structural_prior"`` to distinguish
    them from the old generic ``"stub"`` classification.

    Parameters
    ----------
    site_exposure_factor : float, default 1.0
        Multiplier on base annual probabilities to reflect site exposure.
        Typical range: 0.6 (sheltered fjord) to 2.0 (open exposed coast).
        Must be positive.  Values outside [0.6, 2.0] are clipped with a warning.
    """

    domain_name = "structural"

    def __init__(self, site_exposure_factor: float = 1.0) -> None:
        import warnings
        lo, hi = _EXPOSURE_FACTOR_MIN, _EXPOSURE_FACTOR_MAX
        if not (lo <= site_exposure_factor <= hi):
            warnings.warn(
                f"StructuralRiskDomain: site_exposure_factor {site_exposure_factor:.2f} "
                f"is outside recommended range [{lo}, {hi}]. "
                f"Clipping to nearest bound.",
                UserWarning,
                stacklevel=2,
            )
        self.site_exposure_factor = float(
            max(lo, min(hi, site_exposure_factor))
        )

    def assess(self, site_tiv_nok: float = 0.0) -> List[DomainRiskSummary]:
        """
        Return feasibility-grade structural risk summaries.

        Expected annual loss per sub-type:
            EAL = annual_probability × exposure_factor × loss_fraction × TIV

        Parameters
        ----------
        site_tiv_nok : float
            Total insured value for the site in NOK.  If zero, monetary
            estimates are zero but probabilities are still returned.

        Returns
        -------
        List[DomainRiskSummary]
            One entry per structural sub-type.
        """
        summaries: List[DomainRiskSummary] = []

        for sub_type, profile in STRUCTURAL_RISK_PROFILES.items():
            base_prob = profile["annual_probability"]
            adjusted_prob = min(1.0, base_prob * self.site_exposure_factor)
            expected_loss = adjusted_prob * site_tiv_nok * profile["loss_fraction_of_tiv"]

            summaries.append(DomainRiskSummary(
                domain=self.domain_name,
                sub_type=sub_type,
                event_probability=adjusted_prob,
                expected_annual_loss_nok=expected_loss,
                model_type="structural_prior",
                confidence=0.15,
                data_quality="PRIOR_ONLY",
                metadata={
                    "description": profile["description"],
                    "base_probability": base_prob,
                    "site_exposure_factor": self.site_exposure_factor,
                    "loss_fraction_of_tiv": profile["loss_fraction_of_tiv"],
                    "modelling_note": (
                        "Feasibility-grade structural prior. "
                        "Not a site-specific engineering assessment. "
                        "Full engineering-grade modelling planned for future release."
                    ),
                },
            ))

        return summaries
