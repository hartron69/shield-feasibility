"""POST /api/feasibility/smolt/run — smolt-specific analysis route."""

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import (
    BuildingComponentInput,
    FeasibilityResponse,
    SmoltFacilityInput,
    SmoltOperatorRequest,
)
from backend.services.smolt_operator_builder import SmoltOperatorBuilder
from backend.services.run_analysis import run_feasibility_analysis
from data.input_schema import (
    BuildingComponent,
    FacilityType,
    SmoltFacilityTIV,
    SmoltOperatorInput,
)

router = APIRouter(prefix="/api/feasibility/smolt", tags=["smolt"])


@router.post("/run", response_model=FeasibilityResponse)
async def run_smolt_feasibility(req: SmoltOperatorRequest) -> FeasibilityResponse:
    """
    Run the full 9-step PCC pipeline for a land-based smolt operator.
    TIV is computed from component structure (buildings, machinery, biomass, BI).
    """
    smolt_input = _build_smolt_input(req)

    builder = SmoltOperatorBuilder()
    op_input, smolt_alloc = builder.build(
        smolt_input,
        estimated_market_premium_nok=req.current_market_premium_nok,
    )

    # Convert to API-compatible AllocationSummary
    alloc_summary = smolt_alloc.to_allocation_summary(
        risk_severity_scaled=op_input.risk_params.mean_loss_severity,
        risk_events_scaled=op_input.risk_params.expected_annual_events,
    )

    # Override generate_pdf from top-level field if provided
    model = req.model
    if not req.generate_pdf:
        model = model.model_copy(update={"generate_pdf": False})

    return run_feasibility_analysis(
        op_input=op_input,
        model_settings=model,
        allocation_summary=alloc_summary,
    )


@router.get("/example/agaqua", response_model=SmoltOperatorRequest)
async def get_agaqua_example() -> SmoltOperatorRequest:
    """Return pre-filled Agaqua AS example for testing and demo."""
    return _agaqua_example()


# ─────────────────────────────────────────────────────────────────────────────
def _build_smolt_input(req: SmoltOperatorRequest) -> SmoltOperatorInput:
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
            site_clearance_nok            = f.site_clearance_nok,
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
        org_number                 = req.org_number,
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


def _agaqua_example() -> SmoltOperatorRequest:
    """Agaqua AS / Settefisk 1-gruppen — actual 2024 data."""
    return SmoltOperatorRequest(
        operator_name = "Agaqua AS",
        org_number    = "930529591",
        facilities    = [
            SmoltFacilityInput(
                facility_name  = "Villa Smolt AS",
                facility_type  = "smolt_ras",
                building_components=[
                    BuildingComponentInput(name="Hall over fish tanks", area_sqm=1370, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="RAS 1-2",              area_sqm=530,  value_per_sqm_nok=27000),
                    BuildingComponentInput(name="RAS 3-4",              area_sqm=610,  value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Gamledelen",           area_sqm=1393, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Forlager",             area_sqm=275,  value_per_sqm_nok=27000),
                ],
                site_clearance_nok            = 20_000_000,
                machinery_nok                 = 200_000_000,
                avg_biomass_insured_value_nok = 39_680_409,
                bi_sum_insured_nok            = 243_200_000,
                bi_indemnity_months           = 24,
                latitude=62.29425, longitude=5.62739, municipality="Herøy",
            ),
            SmoltFacilityInput(
                facility_name  = "Olden Oppdrettsanlegg AS",
                facility_type  = "smolt_flow",
                building_components=[
                    BuildingComponentInput(name="Påvekstavdeling",       area_sqm=2204, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Yngel",                 area_sqm=899,  value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Klekkeri/startforing",  area_sqm=221,  value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Teknisk/vannbehandling", area_sqm=77,  value_per_sqm_nok=27000),
                ],
                site_clearance_nok            = 20_000_000,
                machinery_nok                 = 120_000_000,
                avg_biomass_insured_value_nok = 18_260_208,
                bi_sum_insured_nok            = 102_000_000,
                bi_indemnity_months           = 24,
                latitude=63.87241, longitude=9.93298, municipality="Ørland",
            ),
            SmoltFacilityInput(
                facility_name  = "Setran Settefisk AS",
                facility_type  = "smolt_flow",
                building_components=[
                    BuildingComponentInput(name="Hall A",          area_sqm=280, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Vannbehandling",  area_sqm=170, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Hall B",          area_sqm=715, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Hall C",          area_sqm=979, value_per_sqm_nok=27000),
                ],
                site_clearance_nok            = 15_000_000,
                machinery_nok                 = 45_000_000,
                avg_biomass_insured_value_nok = 13_287_917,
                bi_sum_insured_nok            = 85_100_000,
                bi_indemnity_months           = 24,
                latitude=64.27887, longitude=10.45008, municipality="Osen",
            ),
        ],
        annual_revenue_nok    = 232_248_232,
        ebitda_nok            = 70_116_262,
        equity_nok            = 39_978_809,
        operating_cf_nok      = 46_510_739,
        liquidity_nok         = 55_454_950,
        claims_history_years  = 10,
        total_claims_paid_nok = 0.0,
    )
