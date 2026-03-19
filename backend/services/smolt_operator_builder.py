"""
SmoltOperatorBuilder

Converts SmoltOperatorInput -> (OperatorInput, SmoltAllocationSummary)
so the existing PCC pipeline (Monte Carlo, SCR, suitability) can run
unchanged on smolt data.

Key differences from sea-based OperatorBuilder:
- TIV is built from component structure, not biomass × price/tonne
- Risk severity scales against machinery + building TIV (not biomass TIV)
- BI-component dominates as catastrophe-loss trigger, not biomass
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from backend.schemas import AllocationSummary, SiteAllocationRow
from data.input_schema import OperatorInput, SmoltOperatorInput, validate_input


_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_input.json"


def _load_template() -> dict:
    with open(_SAMPLE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class SmoltAllocationSummary:
    """Smolt-specific allocation summary returned by SmoltOperatorBuilder."""
    # TIV breakdown
    total_tiv_nok: float
    biomass_share: float
    property_share: float
    bi_share: float
    machinery_share: float
    building_share: float
    # Facility info
    n_facilities: int
    facility_names: List[str]
    consolidated_breakdown: dict
    # Financial capacity
    scr_capacity_ratio: float       # operating_cf / estimated_base_scr
    liquidity_post_scr_nok: float   # liquidity after estimated SCR

    def to_allocation_summary(
        self,
        risk_severity_scaled: float = 0.0,
        risk_events_scaled: float = 0.0,
    ) -> AllocationSummary:
        """Convert to API-compatible AllocationSummary."""
        return AllocationSummary(
            template_exposure_nok=0.0,           # n/a for smolt
            user_exposure_nok=self.total_tiv_nok,
            tiv_ratio=1.0,
            risk_severity_scaled=risk_severity_scaled,
            risk_events_scaled=risk_events_scaled,
            financial_ratios={
                "biomass_share":  round(self.biomass_share, 4),
                "property_share": round(self.property_share, 4),
                "bi_share":       round(self.bi_share, 4),
                "machinery_share": round(self.machinery_share, 4),
                "building_share": round(self.building_share, 4),
                "scr_capacity_ratio": round(self.scr_capacity_ratio, 4),
            },
            sites=[
                SiteAllocationRow(
                    name=name,
                    biomass_tonnes=0,
                    biomass_value_nok=0.0,
                    equipment_value_nok=0.0,
                    infrastructure_value_nok=0.0,
                    annual_revenue_nok=0.0,
                    tiv_nok=0.0,
                    weight_pct=round(100.0 / self.n_facilities, 1),
                )
                for name in self.facility_names
            ],
            warnings=[],
        )


class SmoltOperatorBuilder:
    """
    Builds OperatorInput from SmoltOperatorInput.

    Approach:
    1. Compute total TIV and component breakdown
    2. Derive risk parameters from TIV profile and claims history
    3. Set financial ratios from actual accounting data
    4. Return (OperatorInput, SmoltAllocationSummary)
    """

    # Base risk parameters for Norwegian smolt (calibrated from market data)
    SMOLT_BASE_LOSS_FREQUENCY  = 0.08   # Expected events/year (clean profile)
    SMOLT_BASE_SEVERITY_FACTOR = 0.035  # Expected loss as % of property TIV
    SMOLT_CAT_PROBABILITY      = 0.03   # Probability of catastrophe event/year
    SMOLT_CAT_MULTIPLIER       = 4.5    # Catastrophe loss × normal expected loss

    # RI defaults for smolt
    DEFAULT_RI_RETENTION_SHARE = 0.01   # 1% of total TIV as default retention
    DEFAULT_RI_LIMIT_SHARE     = 0.25   # 25% of total TIV as RI capacity
    DEFAULT_RI_LOADING         = 1.75   # Base preset

    def build(
        self,
        smolt_input: SmoltOperatorInput,
        estimated_market_premium_nok: Optional[float] = None,
    ) -> Tuple[OperatorInput, SmoltAllocationSummary]:
        """
        Main method. Returns OperatorInput ready for PCC pipeline
        and SmoltAllocationSummary for reporting.

        Args:
            smolt_input: Populated SmoltOperatorInput
            estimated_market_premium_nok: Howden indication if available;
                otherwise estimated from TIV rates

        Returns:
            (OperatorInput, SmoltAllocationSummary)
        """
        tiv       = smolt_input.total_tiv_nok
        breakdown = smolt_input.consolidated_tiv_breakdown
        prop_tiv  = breakdown["buildings"] + breakdown["machinery"]
        bi_tiv    = breakdown["bi"]
        bio_tiv   = breakdown["biomass"]
        n         = smolt_input.n_facilities

        # ── Premium ───────────────────────────────────────────────────────────
        if estimated_market_premium_nok:
            premium = estimated_market_premium_nok
        else:
            prop_prem = prop_tiv   * 0.0042   # 0.42% property rate
            bi_prem   = (bi_tiv / 2) * 0.007  # 0.70% of BI sum per year
            bio_prem  = bio_tiv  * 0.025       # 2.50% biomass rate
            premium   = prop_prem + bi_prem + bio_prem

        # ── Risk parameters — adjusted for claims history ──────────────────
        history_discount = self._history_discount(smolt_input.claims_history_years)
        base_loss_freq   = self.SMOLT_BASE_LOSS_FREQUENCY * history_discount
        base_severity    = prop_tiv * self.SMOLT_BASE_SEVERITY_FACTOR
        expected_events  = base_loss_freq * n

        # ── Financial ratios ──────────────────────────────────────────────
        revenue = smolt_input.annual_revenue_nok or (tiv * 0.20)
        equity  = smolt_input.equity_nok          or (tiv * 0.10)
        op_cf   = smolt_input.operating_cf_nok    or (revenue * 0.18)
        liquid  = smolt_input.liquidity_nok        or (revenue * 0.08)
        ebitda  = smolt_input.ebitda_nok           or (revenue * 0.22)

        # ── RI structure ──────────────────────────────────────────────────
        retention = max(tiv * self.DEFAULT_RI_RETENTION_SHARE, 5_000_000)
        ri_limit  = tiv * self.DEFAULT_RI_LIMIT_SHARE

        # ── Load template and overlay smolt values ─────────────────────────
        tmpl = _load_template()
        tmpl["name"]    = smolt_input.operator_name
        tmpl["country"] = "Norway"

        # Insurance
        tmpl["current_insurance"]["annual_premium"]          = premium
        tmpl["current_insurance"]["per_occurrence_deductible"] = retention
        tmpl["current_insurance"]["coverage_limit"]          = ri_limit

        # Financials
        tmpl["financials"]["annual_revenue"] = revenue
        tmpl["financials"]["ebitda"]         = ebitda
        tmpl["financials"]["net_equity"]     = equity
        tmpl["financials"]["free_cash_flow"] = op_cf
        tmpl["financials"]["total_assets"]   = smolt_input.equity_nok or (tiv * 0.35)

        # Risk parameters
        tmpl["risk_params"]["expected_annual_events"]   = expected_events
        tmpl["risk_params"]["mean_loss_severity"]       = base_severity
        tmpl["risk_params"]["cv_loss_severity"]         = 0.65
        tmpl["risk_params"]["catastrophe_probability"]  = self.SMOLT_CAT_PROBABILITY
        tmpl["risk_params"]["catastrophe_loss_multiplier"] = self.SMOLT_CAT_MULTIPLIER
        tmpl["risk_params"]["inter_site_correlation"]   = 0.10
        tmpl["risk_params"]["bi_daily_revenue_loss"]    = revenue / 365
        tmpl["risk_params"]["bi_average_interruption_days"] = 90

        # Sites — one virtual site per facility
        sites = []
        for f in smolt_input.facilities:
            prop = f.building_total_nok + f.machinery_nok
            sites.append({
                "name":                   f.facility_name,
                "location":               f.municipality or "Norway",
                "species":                "Smolt",
                # Represent biomass TIV as 1 tonne × value so total_insured_value is correct
                "biomass_tonnes":         1,
                "biomass_value_per_tonne": f.avg_biomass_insured_value_nok,
                "equipment_value":        prop,
                "infrastructure_value":   f.bi_sum_insured_nok,
                "annual_revenue":         revenue / n,
                "site_type":              "land_based",
            })
        tmpl["sites"] = sites

        op_input = validate_input(tmpl)
        op_input.facility_type = "smolt"  # mark as smolt

        # ── SCR capacity analysis ─────────────────────────────────────────
        est_scr  = tiv * 0.015   # rough estimate: 1.5% of TIV
        scr_cap  = op_cf / est_scr if est_scr > 0 else 0.0
        liq_post = liquid - est_scr

        alloc = SmoltAllocationSummary(
            total_tiv_nok          = tiv,
            biomass_share          = bio_tiv  / tiv if tiv else 0.0,
            property_share         = prop_tiv / tiv if tiv else 0.0,
            bi_share               = bi_tiv   / tiv if tiv else 0.0,
            machinery_share        = breakdown["machinery"] / tiv if tiv else 0.0,
            building_share         = breakdown["buildings"] / tiv if tiv else 0.0,
            n_facilities           = n,
            facility_names         = [f.facility_name for f in smolt_input.facilities],
            consolidated_breakdown = breakdown,
            scr_capacity_ratio     = scr_cap,
            liquidity_post_scr_nok = liq_post,
        )

        return op_input, alloc

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _history_discount(years_claims_free: int) -> float:
        """
        Frequency discount factor based on claims-free history.
        10 years claims-free → 35% reduction in assumed frequency.
        """
        if years_claims_free <= 0: return 1.00
        if years_claims_free <= 2: return 0.92
        if years_claims_free <= 4: return 0.85
        if years_claims_free <= 6: return 0.78
        if years_claims_free <= 8: return 0.72
        return 0.65   # 9+ years claims-free
