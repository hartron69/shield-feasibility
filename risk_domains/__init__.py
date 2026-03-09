"""
Risk Domain Architecture – Shield Captive Risk Platform.

Provides a registry-based framework for pluggable risk domains:
  - biological  (backed by C5AI+)
  - structural  (stub)
  - environmental (stub)
  - operational (stub)

Usage
-----
    from risk_domains import DOMAIN_REGISTRY
    domain = DOMAIN_REGISTRY["biological"]
    summaries = domain.assess(site_data)
"""

from risk_domains.domain_registry import DOMAIN_REGISTRY, get_domain

__all__ = ["DOMAIN_REGISTRY", "get_domain"]
