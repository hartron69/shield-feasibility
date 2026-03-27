"""
Feasibility API endpoints.

POST /api/feasibility/run    – run full pipeline
POST /api/feasibility/example – return pre-filled example request
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas import FeasibilityRequest, FeasibilityResponse
from backend.services.run_analysis import run_feasibility_service

router = APIRouter()

# ── Pre-filled example request (Nordic Aqua Partners) ────────────────────────
EXAMPLE_REQUEST = FeasibilityRequest(
    operator_profile={
        "name": "Nordic Aqua Partners AS",
        "country": "Norge",
        "n_sites": 3,
        "total_biomass_tonnes": 9200,
        # Valuation: 80 NOK/kg × 1000 × 0.90 × (1 - 0.0) = 72,000 NOK/t (no prudence haircut)
        "biomass_value_per_tonne": 72000,
        "reference_price_per_kg": 80.0,
        "realisation_factor": 0.90,
        "prudence_haircut": 0.0,
        "annual_revenue_nok": 897_000_000,
        "annual_premium_nok": 19_500_000,
    },
    model_settings={
        "n_simulations": 5000,
        "domain_correlation": "expert_default",
        "generate_pdf": True,
    },
    strategy_settings={"strategy": "pcc_captive", "retention_nok": None},
    mitigation={"selected_actions": ["stronger_nets", "environmental_sensors", "staff_training_program"]},
    output_options={"generate_pdf": True},
)


@router.post("/run", response_model=FeasibilityResponse)
def run_feasibility(request: FeasibilityRequest) -> FeasibilityResponse:
    """Run the full feasibility analysis pipeline."""
    profile = request.operator_profile
    if (
        getattr(profile, "site_selection_mode", "generic") == "specific"
        and profile.selected_sites
    ):
        from backend.services.site_registry import validate_selected_sites
        errors = validate_selected_sites(profile.selected_sites)
        if errors:
            raise HTTPException(status_code=422, detail={"selected_sites_errors": errors})
    return run_feasibility_service(request)


@router.post("/example")
def get_example() -> dict:
    """Return a pre-filled example request payload."""
    return EXAMPLE_REQUEST.model_dump()
