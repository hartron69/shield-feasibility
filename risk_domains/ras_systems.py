"""
RAS risk domain for land-based smolt / recirculating aquaculture systems.

Six sub-perils with calibrated frequency and severity parameters based on
Norwegian RAS industry data and the Agaqua AS profile (10 years claims-free).

Domain code: "ras"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class RASPerilProfile:
    """Risk profile for one RAS event type."""
    name: str
    code: str
    annual_frequency_base: float        # Poisson λ
    severity_as_pct_of_property: Tuple[float, float]   # (mean, cv) LogNormal
    bi_trigger: bool                    # Triggers BI loss?
    intra_facility_correlation: float   # Correlation between departments WITHIN facility
    inter_facility_correlation: float   # Correlation BETWEEN separate facilities


RAS_PERILS: Dict[str, RASPerilProfile] = {
    "biofilter_failure": RASPerilProfile(
        name="Biofiltersvikt",
        code="ras_bio",
        annual_frequency_base=0.12,
        severity_as_pct_of_property=(0.04, 0.70),
        bi_trigger=True,
        intra_facility_correlation=0.60,
        inter_facility_correlation=0.05,
    ),
    "oxygen_collapse": RASPerilProfile(
        name="Oksygenkollaps",
        code="ras_o2",
        annual_frequency_base=0.06,
        severity_as_pct_of_property=(0.12, 0.90),
        bi_trigger=True,
        intra_facility_correlation=0.75,
        inter_facility_correlation=0.03,
    ),
    "pump_failure": RASPerilProfile(
        name="Pumpehavari",
        code="ras_pump",
        annual_frequency_base=0.18,
        severity_as_pct_of_property=(0.02, 0.60),
        bi_trigger=False,
        intra_facility_correlation=0.40,
        inter_facility_correlation=0.02,
    ),
    "power_outage": RASPerilProfile(
        name="Strømbortfall",
        code="ras_power",
        annual_frequency_base=0.08,
        severity_as_pct_of_property=(0.06, 0.80),
        bi_trigger=True,
        intra_facility_correlation=0.85,   # Whole facility affected
        inter_facility_correlation=0.02,
    ),
    "water_quality": RASPerilProfile(
        name="Vannkvalitetssvikt (CO\u2082/pH)",
        code="ras_wq",
        annual_frequency_base=0.10,
        severity_as_pct_of_property=(0.05, 0.75),
        bi_trigger=True,
        intra_facility_correlation=0.55,
        inter_facility_correlation=0.03,
    ),
    "water_source_contamination": RASPerilProfile(
        name="Vannkildeforurensning",
        code="ras_source",
        annual_frequency_base=0.02,         # Rare but catastrophic
        severity_as_pct_of_property=(0.35, 1.20),
        bi_trigger=True,
        intra_facility_correlation=0.95,    # Whole facility affected
        inter_facility_correlation=0.01,
    ),
}


class RASRiskDomain:
    """
    Aggregated RAS risk domain.
    Used by SmoltMCCalibrator to calibrate simulation parameters.
    """

    def __init__(self, property_tiv_nok: float, claims_free_years: int = 0):
        self.property_tiv = property_tiv_nok
        self.discount = self._history_discount(claims_free_years)

    @property
    def aggregate_frequency(self) -> float:
        """Aggregated frequency for all RAS perils, adjusted for history."""
        raw = sum(p.annual_frequency_base for p in RAS_PERILS.values())
        return raw * self.discount

    @property
    def expected_annual_loss_nok(self) -> float:
        """Expected annual loss across all perils."""
        total = 0.0
        for peril in RAS_PERILS.values():
            freq = peril.annual_frequency_base * self.discount
            sev_mean, _ = peril.severity_as_pct_of_property
            total += freq * sev_mean * self.property_tiv
        return total

    def catastrophe_scenario(self) -> Dict[str, float]:
        """
        Worst-case: oxygen collapse + simultaneous power outage.
        Represents approximate 99.5th percentile event.
        """
        o2  = RAS_PERILS["oxygen_collapse"]
        pwr = RAS_PERILS["power_outage"]
        combined_sev = (o2.severity_as_pct_of_property[0]
                        + pwr.severity_as_pct_of_property[0]) * 0.80
        return {
            "combined_probability": o2.annual_frequency_base * pwr.annual_frequency_base * 0.3,
            "severity_pct_of_property": combined_sev,
            "estimated_loss_nok": combined_sev * self.property_tiv,
        }

    @staticmethod
    def _history_discount(years: int) -> float:
        if years <= 0: return 1.00
        if years < 5:  return 0.85
        if years < 10: return 0.72
        return 0.65
