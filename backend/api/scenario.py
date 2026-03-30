"""
POST /api/c5ai/scenario — parametric scenario Monte Carlo for sea and smolt operators.

Replaces the client-side stub (~900 ms timeout + scale formula) in
ScenarioOverridePanel.jsx with a real MonteCarloEngine run.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import ScenarioRequest, ScenarioResponse, ScenarioFacilityResultResponse
from backend.services.operator_builder import build_operator_input
from backend.services.smolt_operator_builder import SmoltOperatorBuilder
from models.scenario_engine import ScenarioEngine, ScenarioParameters
from data.input_schema import (
    BuildingComponent,
    FacilityType,
    SiteProfile,
    SmoltFacilityTIV,
    SmoltOperatorInput,
)

router = APIRouter(prefix="/api/c5ai", tags=["scenario"])


@router.post("/scenario", response_model=ScenarioResponse)
async def run_scenario(req: ScenarioRequest) -> ScenarioResponse:
    """
    Run a parametric Monte Carlo scenario for the given facility type.

    Sea:   uses lice_pressure_index, exposure_factor, dissolved_oxygen_mg_l, …
    Smolt: uses ras_failure_multiplier, oxygen_level_mg_l, power_backup_hours,
           affected_facility_index (None = all facilities, 0..N-1 = single).
    """
    engine = ScenarioEngine()
    params = ScenarioParameters(
        facility_type           = req.facility_type,
        preset_id               = req.preset_id,
        total_biomass_override  = req.total_biomass_override,
        dissolved_oxygen_mg_l   = req.dissolved_oxygen_mg_l,
        nitrate_umol_l          = req.nitrate_umol_l,
        lice_pressure_index     = req.lice_pressure_index,
        exposure_factor         = req.exposure_factor,
        operational_factor      = req.operational_factor,
        ras_failure_multiplier  = req.ras_failure_multiplier,
        power_backup_hours      = req.power_backup_hours,
        oxygen_level_mg_l       = req.oxygen_level_mg_l,
        affected_facility_index = req.affected_facility_index,
    )

    if req.facility_type == "smolt" and req.smolt_operator:
        smolt_input = _build_smolt_input(req.smolt_operator)
        builder = SmoltOperatorBuilder()
        group_op, _ = builder.build(smolt_input)
        facility_inputs = builder.build_per_facility(smolt_input)
        result = engine.run(group_op, params, facility_inputs=facility_inputs)
    else:
        operator_profile = req.operator
        if operator_profile is None:
            # No operator provided — use KH portfolio from Live Risk config
            op_input, site_inputs = _build_kh_default()
        else:
            op_input, _ = build_operator_input(operator_profile)
            site_inputs = None
            if operator_profile.sites:
                from backend.services.sea_site_builder import SeaSiteBuilder
                sea_builder = SeaSiteBuilder()
                _, site_inputs = sea_builder.build_group(
                    sites=[_to_site_profile(s) for s in operator_profile.sites],
                    operator_name=operator_profile.name,
                    annual_premium_nok=operator_profile.annual_premium_nok,
                )
        result = engine.run(op_input, params, site_inputs=site_inputs)

    return ScenarioResponse(
        preset_id           = result.preset_id,
        facility_type       = result.facility_type,
        baseline_total_loss = result.baseline_total_loss,
        scenario_total_loss = result.scenario_total_loss,
        total_change_pct    = result.total_change_pct,
        facility_results    = [
            ScenarioFacilityResultResponse(**fr.__dict__)
            for fr in result.facility_results
        ],
        highest_risk_driver = result.highest_risk_driver,
        narrative           = result.narrative,
    )


def _build_kh_default():
    """
    Build KH portfolio (Kornstad / Leite / Hogsnes) from Live Risk config
    for sea scenarios when no operator is supplied by the frontend.

    Returns (group_op_input, site_inputs_list) ready for ScenarioEngine.run().
    """
    from backend.services.live_risk_feed import get_locality_config, _OPERATOR_FINANCIALS
    from backend.services.sea_site_builder import SeaSiteBuilder

    _EXPOSURE_MAP = {
        (0.0, 1.0):  "sheltered",
        (1.0, 1.12): "semi_exposed",
        (1.12, 9.9): "open_coast",
    }

    def exposure_class(factor):
        for (lo, hi), label in _EXPOSURE_MAP.items():
            if lo <= factor < hi:
                return label
        return "semi_exposed"

    KH_SITES = ["KH_S01", "KH_S02", "KH_S03"]
    BIOMASS_VALUE_PER_TONNE = 65_000  # NOK — matches get_site_profile()

    sites = []
    for site_id in KH_SITES:
        cfg = get_locality_config(site_id)
        fin = _OPERATOR_FINANCIALS.get(site_id, {})
        biomass_t = cfg.get("biomass_tonnes", 0)
        sites.append(SiteProfile(
            name                  = cfg["name"],
            location              = cfg["region"],
            species               = "Atlantic Salmon",
            biomass_tonnes        = biomass_t,
            biomass_value_per_tonne = BIOMASS_VALUE_PER_TONNE,
            equipment_value       = fin.get("equipment_value_nok", biomass_t * BIOMASS_VALUE_PER_TONNE * 0.10),
            infrastructure_value  = fin.get("infra_value_nok",      biomass_t * BIOMASS_VALUE_PER_TONNE * 0.07),
            annual_revenue        = fin.get("annual_revenue_nok",    biomass_t * BIOMASS_VALUE_PER_TONNE * 1.20),
            fjord_exposure        = exposure_class(cfg["exposure"]),
            lice_pressure_factor  = 1.0,  # neutral baseline; scenario params override
            mooring_age_years     = None,
            latitude              = cfg["lat"],
            longitude             = cfg["lon"],
            municipality          = cfg["region"],
        ))

    total_revenue = sum(s.annual_revenue for s in sites)
    annual_premium = total_revenue * 0.025  # ~2.5 % of revenue as market premium proxy

    builder = SeaSiteBuilder()
    group_op, site_inputs = builder.build_group(
        sites             = sites,
        operator_name     = "Kornstad Havbruk AS",
        annual_premium_nok = annual_premium,
    )
    return group_op, site_inputs


def _to_site_profile(s) -> SiteProfile:
    """Convert SiteProfileInput (Pydantic) → SiteProfile (dataclass)."""
    return SiteProfile(
        name                  = s.site_name,
        location              = s.municipality or "Norway",
        species               = "Atlantic Salmon",
        biomass_tonnes        = s.biomass_value_nok / 64_800,  # approx tonnes from NOK
        biomass_value_per_tonne = 64_800,
        equipment_value       = s.biomass_value_nok * 0.20,
        infrastructure_value  = s.biomass_value_nok * 0.15,
        annual_revenue        = s.biomass_value_nok * 1.20,
        fjord_exposure        = s.fjord_exposure,
        lice_pressure_factor  = s.lice_pressure_factor,
        hab_risk_factor       = s.hab_risk_factor,
        mooring_age_years     = s.mooring_age_years,
        latitude              = s.latitude,
        longitude             = s.longitude,
        municipality          = s.municipality,
        licence_count         = s.licence_count,
    )


def _build_smolt_input(req) -> SmoltOperatorInput:
    """Convert SmoltOperatorRequest (Pydantic) → SmoltOperatorInput (dataclass)."""
    facilities = []
    for f in req.facilities:
        components = [
            BuildingComponent(
                name=b.name,
                area_sqm=b.area_sqm,
                value_per_sqm_nok=b.value_per_sqm_nok,
            )
            for b in f.building_components
        ]
        facilities.append(SmoltFacilityTIV(
            facility_name                 = f.facility_name,
            facility_type                 = FacilityType(f.facility_type),
            building_components           = components,
            site_clearance_nok            = getattr(f, "site_clearance_nok", 0.0),
            machinery_nok                 = f.machinery_nok,
            avg_biomass_insured_value_nok = f.avg_biomass_insured_value_nok,
            bi_sum_insured_nok            = f.bi_sum_insured_nok,
            bi_indemnity_months           = f.bi_indemnity_months,
            latitude                      = f.latitude,
            longitude                     = f.longitude,
            municipality                  = f.municipality,
        ))
    return SmoltOperatorInput(
        operator_name              = req.operator_name,
        org_number                 = getattr(req, "org_number", None),
        facilities                 = facilities,
        annual_revenue_nok         = req.annual_revenue_nok,
        ebitda_nok                 = req.ebitda_nok,
        equity_nok                 = req.equity_nok,
        operating_cf_nok           = req.operating_cf_nok,
        liquidity_nok              = req.liquidity_nok,
        claims_history_years       = req.claims_history_years,
        total_claims_paid_nok      = req.total_claims_paid_nok,
        current_market_premium_nok = req.current_market_premium_nok,
    )
