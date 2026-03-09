"""
Shield Captive Risk Platform – RiskDomain Abstract Base Class.

All risk domains implement the RiskDomain ABC and return a list of
DomainRiskSummary objects from their assess() method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DomainRiskSummary:
    """
    Standardised risk summary for one sub-type within a domain.

    Attributes
    ----------
    domain : str
        Top-level domain label: "biological" | "structural" |
        "environmental" | "operational".
    sub_type : str
        Specific risk sub-type, e.g. "jellyfish", "mooring_failure".
    event_probability : float
        Annual probability of an adverse event (0–1).
    expected_annual_loss_nok : float
        Expected annual loss in NOK (probability × conditional loss).
    model_type : str
        One of: "prior" | "temp_adjusted_prior" | "network_prior" |
        "observation_based" | "ml_hab" | "ml_lice" | "prior_fallback" | "stub".
    confidence : float
        Model confidence score (0–1).
    data_quality : str
        "SUFFICIENT" | "LIMITED" | "POOR" | "PRIOR_ONLY".
    metadata : dict
        Any additional domain-specific information.
    """
    domain: str
    sub_type: str
    event_probability: float
    expected_annual_loss_nok: float
    model_type: str
    confidence: float
    data_quality: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RiskDomain(ABC):
    """
    Abstract base class for all risk domain assessors.

    Subclasses implement assess() and return a list of DomainRiskSummary
    objects covering each sub-type they model.
    """

    domain_name: str = "base"

    @abstractmethod
    def assess(self, *args, **kwargs) -> List[DomainRiskSummary]:
        """
        Run the domain assessment and return a list of DomainRiskSummary.

        Parameters vary by domain (e.g. biological domains accept SiteData,
        structural domains accept site geometry, etc.).
        """
        ...

    def total_expected_annual_loss(self, summaries: List[DomainRiskSummary]) -> float:
        """Convenience: sum expected annual loss across all sub-types."""
        return sum(s.expected_annual_loss_nok for s in summaries)
