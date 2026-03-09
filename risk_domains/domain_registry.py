"""
Shield Captive Risk Platform – Domain Registry.

Provides a central factory for all registered risk domains.
New domains can be added by inserting into DOMAIN_REGISTRY.
"""

from __future__ import annotations

from typing import Dict, Optional

from risk_domains.base_domain import RiskDomain
from risk_domains.biological import BiologicalRiskDomain
from risk_domains.structural import StructuralRiskDomain
from risk_domains.environmental import EnvironmentalRiskDomain
from risk_domains.operational import OperationalRiskDomain


# Registry maps domain name → instantiated domain object
DOMAIN_REGISTRY: Dict[str, RiskDomain] = {
    "biological":    BiologicalRiskDomain(),
    "structural":    StructuralRiskDomain(),
    "environmental": EnvironmentalRiskDomain(),
    "operational":   OperationalRiskDomain(),
}


def get_domain(name: str) -> RiskDomain:
    """
    Retrieve a registered risk domain by name.

    Parameters
    ----------
    name : str
        Domain name: "biological", "structural", "environmental", "operational".

    Raises
    ------
    KeyError
        If the domain name is not registered.
    """
    if name not in DOMAIN_REGISTRY:
        available = list(DOMAIN_REGISTRY.keys())
        raise KeyError(
            f"Domain '{name}' not found in registry. "
            f"Available domains: {available}"
        )
    return DOMAIN_REGISTRY[name]
