"""
SeaSiteBuilder

Converts a list of SiteProfile objects → List[OperatorInput],
one OperatorInput per site, using the template-based approach.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import List, Tuple, Optional

from data.input_schema import OperatorInput, SiteProfile, validate_input

_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_input.json"


def _load_template() -> dict:
    with open(_SAMPLE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


class SeaSiteBuilder:
    """
    Converts List[SiteProfile] → List[OperatorInput], one per site.

    Risk parameters per site are derived from:
    - SiteProfile.base_loss_frequency  (exposure + lice/HAB factors)
    - SiteProfile.base_severity_nok    (18 % of biomass value)
    """

    # Sea CV and CAT parameters
    CV_LOSS_SEVERITY:       float = 0.85
    CAT_PROBABILITY:        float = 0.05
    CAT_MULTIPLIER:         float = 3.5
    INTRA_SITE_CORRELATION: float = 0.0   # treated independently per site
    INTER_SITE_CORRELATION: float = 0.20  # used at group level

    def build_per_site(
        self,
        sites: List[SiteProfile],
        operator_name: str,
        annual_premium_nok: float,
    ) -> List[OperatorInput]:
        """Return one OperatorInput per site with site-specific risk params."""
        total_biomass = sum(
            s.biomass_tonnes * s.biomass_value_per_tonne for s in sites
        ) or 1.0

        result = []
        for site in sites:
            site_biomass = site.biomass_tonnes * site.biomass_value_per_tonne
            premium_share = site_biomass / total_biomass
            site_premium  = annual_premium_nok * premium_share

            tmpl = _load_template()
            tmpl["name"]    = f"{operator_name} — {site.name}"
            tmpl["country"] = "Norway"
            tmpl["current_insurance"]["annual_premium"] = site_premium

            # Override sites to single site
            tmpl["sites"] = [{
                "name":                  site.name,
                "location":              site.location,
                "species":               site.species,
                "biomass_tonnes":        site.biomass_tonnes,
                "biomass_value_per_tonne": site.biomass_value_per_tonne,
                "equipment_value":       site.equipment_value,
                "infrastructure_value":  site.infrastructure_value,
                "annual_revenue":        site.annual_revenue,
                "site_type":             site.site_type,
            }]

            # Financials: scale from site revenue
            rev = site.annual_revenue
            tmpl["financials"]["annual_revenue"] = rev
            tmpl["financials"]["ebitda"]         = rev * 0.20
            tmpl["financials"]["net_equity"]     = rev * 0.60
            tmpl["financials"]["free_cash_flow"] = rev * 0.11
            tmpl["financials"]["total_assets"]   = rev * 1.30

            # Risk parameters from site profile
            tmpl["risk_params"]["expected_annual_events"]   = site.base_loss_frequency
            tmpl["risk_params"]["mean_loss_severity"]       = site.base_severity_nok
            tmpl["risk_params"]["cv_loss_severity"]         = self.CV_LOSS_SEVERITY
            tmpl["risk_params"]["catastrophe_probability"]  = self.CAT_PROBABILITY
            tmpl["risk_params"]["catastrophe_loss_multiplier"] = self.CAT_MULTIPLIER
            tmpl["risk_params"]["inter_site_correlation"]   = self.INTRA_SITE_CORRELATION

            op_input = validate_input(tmpl)
            op_input.facility_type = "sea"
            # Attach site_profile for scenario engine
            op_input.site_profile = site  # type: ignore[attr-defined]
            result.append(op_input)
        return result

    def build_group(
        self,
        sites: List[SiteProfile],
        operator_name: str,
        annual_premium_nok: float,
    ) -> Tuple[OperatorInput, List[OperatorInput]]:
        """
        Return (group_op, per_site_ops).
        group_op uses summed events and average severity with inter-site correlation.
        """
        per_site = self.build_per_site(sites, operator_name, annual_premium_nok)
        n = len(per_site)

        tmpl = _load_template()
        tmpl["name"]    = operator_name
        tmpl["country"] = "Norway"
        tmpl["current_insurance"]["annual_premium"] = annual_premium_nok

        total_rev = sum(s.annual_revenue for s in sites)
        tmpl["financials"]["annual_revenue"] = total_rev
        tmpl["financials"]["ebitda"]         = total_rev * 0.20
        tmpl["financials"]["net_equity"]     = total_rev * 0.60
        tmpl["financials"]["free_cash_flow"] = total_rev * 0.11
        tmpl["financials"]["total_assets"]   = total_rev * 1.30

        total_events   = sum(op.risk_params.expected_annual_events for op in per_site)
        mean_severity  = (sum(op.risk_params.mean_loss_severity for op in per_site) / n
                          if n else 0.0)

        tmpl["risk_params"]["expected_annual_events"]   = total_events
        tmpl["risk_params"]["mean_loss_severity"]       = mean_severity
        tmpl["risk_params"]["cv_loss_severity"]         = self.CV_LOSS_SEVERITY
        tmpl["risk_params"]["catastrophe_probability"]  = self.CAT_PROBABILITY
        tmpl["risk_params"]["catastrophe_loss_multiplier"] = self.CAT_MULTIPLIER
        tmpl["risk_params"]["inter_site_correlation"]   = self.INTER_SITE_CORRELATION

        # Replicate all sites
        tmpl["sites"] = [
            {
                "name":                  s.name,
                "location":              s.location,
                "species":               s.species,
                "biomass_tonnes":        s.biomass_tonnes,
                "biomass_value_per_tonne": s.biomass_value_per_tonne,
                "equipment_value":       s.equipment_value,
                "infrastructure_value":  s.infrastructure_value,
                "annual_revenue":        s.annual_revenue,
                "site_type":             s.site_type,
            }
            for s in sites
        ]

        group_op = validate_input(tmpl)
        group_op.facility_type = "sea"
        return group_op, per_site
