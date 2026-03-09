"""
Shield Captive Risk Platform – Operational Risk Domain (Sprint 6).

Covers human error, procedural failures, equipment malfunction, and
operational incidents not attributable to biological or structural causes.

Modelling status
----------------
This is a **feasibility-grade operational risk model**, not a full management
system assessment or ISO-certified operational risk analysis.  Loss estimates
are derived from transparent industry-informed priors scaled by site total
insured value (TIV) and an optional operational risk factor.

    model_type = "operational_prior"
    confidence = 0.15 (low, appropriate for prior-only modelling)

Sub-types (must match DOMAIN_SUBTYPES["operational"])
-----------------------------------------------------
human_error
    Mistakes made by operational staff: feeding errors, incorrect medication
    dosing, improper mooring checks, navigation incidents.  Annual prob ~12%.

procedure_failure
    Failure to follow established SOPs, permit non-compliance, inadequate
    record-keeping, or process breakdowns during routine operations.
    Annual probability ~8%.

equipment
    Equipment malfunction including automatic feeders, sensors, pumps, and
    ancillary systems.  More frequent than structural failures; lower severity.
    Annual probability ~10%.

incident
    Operational incidents including vessel collisions, dive accidents, chemical
    spills, or other discrete events requiring emergency response.
    Annual probability ~5%.

Limitations
-----------
* Probabilities are site-class priors informed by Norwegian aquaculture incident
  data and expert judgment.  Not site-specific operational assessments.
* An operational risk factor can be supplied to scale base probabilities
  (e.g. excellent management ×0.5, below-average management ×2.0).
* No correlation between operational sub-types is modelled.
* Full operational risk modelling (FMEA, bow-tie analysis) is planned for a
  future production release.

Platform principle
------------------
This is a risk modelling and insurance decision support platform, NOT an
operational management assessment or safety audit tool.
"""

from __future__ import annotations

import warnings
from typing import List

from risk_domains.base_domain import DomainRiskSummary, RiskDomain


# ─────────────────────────────────────────────────────────────────────────────
# Feasibility-grade operational risk priors
# ─────────────────────────────────────────────────────────────────────────────

#: Per-sub-type risk profile.
#:
#: annual_probability : float
#:     Baseline annual event probability for a median-management aquaculture site.
#: loss_fraction_of_tiv : float
#:     Expected loss per event as a fraction of site TIV (conditional on event).
#: description : str
#:     Plain-language description for board/investor reporting.
OPERATIONAL_RISK_PROFILES = {
    "human_error": {
        "annual_probability": 0.12,      # 1-in-8 year event – relatively common
        "loss_fraction_of_tiv": 0.03,    # 3% of site TIV per event
        "description": (
            "Mistakes made by operational staff including feeding errors, "
            "incorrect medication dosing, improper mooring checks, or navigation "
            "incidents.  Frequency depends strongly on training, supervision, "
            "and management culture."
        ),
    },
    "procedure_failure": {
        "annual_probability": 0.08,      # 1-in-12 year event
        "loss_fraction_of_tiv": 0.02,    # 2% of site TIV per event
        "description": (
            "Failure to follow established standard operating procedures (SOPs), "
            "permit non-compliance, inadequate record-keeping, or process "
            "breakdowns during routine operations.  Often precedes or compounds "
            "other incident types."
        ),
    },
    "equipment": {
        "annual_probability": 0.10,      # 1-in-10 year event
        "loss_fraction_of_tiv": 0.02,    # 2% of site TIV per event – low severity
        "description": (
            "Equipment malfunction including automatic feeders, environmental "
            "sensors, pumps, lighting, and ancillary systems.  More frequent "
            "than structural failures but with lower individual severity.  "
            "Modern remote monitoring reduces both frequency and severity."
        ),
    },
    "incident": {
        "annual_probability": 0.05,      # 1-in-20 year event – less common, higher severity
        "loss_fraction_of_tiv": 0.05,    # 5% of site TIV per event
        "description": (
            "Discrete operational incidents including vessel collisions, dive "
            "accidents, chemical spills, fire, or other events requiring "
            "emergency response.  Lower frequency but material financial impact "
            "and potential regulatory consequences."
        ),
    },
}

#: Minimum operational risk factor (excellent management: certified, low turnover).
_RISK_FACTOR_MIN = 0.50
#: Maximum operational risk factor (below-average management: high turnover, limited training).
_RISK_FACTOR_MAX = 2.00


class OperationalRiskDomain(RiskDomain):
    """
    Operational risk domain – feasibility-grade prior model (Sprint 6).

    Returns sub-type risk summaries scaled by site TIV and an optional
    operational risk factor reflecting management quality.

    All four sub-types use ``model_type = "operational_prior"`` to distinguish
    them from the old generic ``"stub"`` classification.

    Parameters
    ----------
    operational_risk_factor : float, default 1.0
        Multiplier on base annual probabilities to reflect management quality.
        Factor > 1.0 = higher risk (poor management, high turnover).
        Factor < 1.0 = lower risk (excellent management, certified, low turnover).
        Typical range: 0.50 to 2.00.
        Values outside [0.50, 2.00] are clipped with a UserWarning.
    """

    domain_name = "operational"

    def __init__(self, operational_risk_factor: float = 1.0) -> None:
        lo, hi = _RISK_FACTOR_MIN, _RISK_FACTOR_MAX
        if not (lo <= operational_risk_factor <= hi):
            warnings.warn(
                f"OperationalRiskDomain: operational_risk_factor {operational_risk_factor:.2f} "
                f"is outside recommended range [{lo}, {hi}]. "
                f"Clipping to nearest bound.",
                UserWarning,
                stacklevel=2,
            )
        self.operational_risk_factor = float(max(lo, min(hi, operational_risk_factor)))

    def assess(self, site_tiv_nok: float = 0.0) -> List[DomainRiskSummary]:
        """
        Return feasibility-grade operational risk summaries.

        Expected annual loss per sub-type:
            adjusted_prob = min(1.0, base_prob × operational_risk_factor)
            EAL = adjusted_prob × loss_fraction × TIV

        Parameters
        ----------
        site_tiv_nok : float
            Total insured value for the site in NOK.  If zero, monetary
            estimates are zero but probabilities are still returned.

        Returns
        -------
        List[DomainRiskSummary]
            One entry per operational sub-type.
        """
        summaries: List[DomainRiskSummary] = []

        for sub_type, profile in OPERATIONAL_RISK_PROFILES.items():
            base_prob = profile["annual_probability"]
            adjusted_prob = min(1.0, base_prob * self.operational_risk_factor)
            expected_loss = adjusted_prob * site_tiv_nok * profile["loss_fraction_of_tiv"]

            summaries.append(DomainRiskSummary(
                domain=self.domain_name,
                sub_type=sub_type,
                event_probability=adjusted_prob,
                expected_annual_loss_nok=expected_loss,
                model_type="operational_prior",
                confidence=0.15,
                data_quality="PRIOR_ONLY",
                metadata={
                    "description": profile["description"],
                    "base_probability": base_prob,
                    "operational_risk_factor": self.operational_risk_factor,
                    "loss_fraction_of_tiv": profile["loss_fraction_of_tiv"],
                    "modelling_note": (
                        "Feasibility-grade operational prior. "
                        "Not a site-specific operational management assessment. "
                        "Full operational risk modelling planned for future release."
                    ),
                },
            ))

        return summaries
