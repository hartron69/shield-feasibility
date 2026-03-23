"""
C5AI+ API endpoints — freshness gate and pipeline trigger.

POST /api/c5ai/run
    Trigger the C5AI+ analysis pipeline for the configured operator.
    Records the run in the in-memory state store.
    Returns run_id, generated_at, and freshness metadata.

GET /api/c5ai/status
    Return current C5AI+ freshness status (fresh / stale / missing).

POST /api/c5ai/inputs/updated
    Notify the backend that operator inputs have changed since the last run.
    Called by the frontend after the operator form is submitted or an
    example is loaded.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter

from backend.schemas import C5AIRunResponse, C5AIStatusResponse
from backend.services import c5ai_state

router = APIRouter(prefix="/api/c5ai", tags=["c5ai"])


def _run_c5ai_pipeline_safe() -> dict:
    """
    Attempt to run the C5AI+ multi-domain engine with the demo operator.

    Tries the real MultiDomainEngine with demo site data.
    Always returns metadata — falls back to stub values on any error
    so the endpoint never returns 500.
    """
    try:
        from c5ai_plus.data_models.biological_input import C5AIOperatorInput, SiteInput
        from c5ai_plus.multi_domain_engine import MultiDomainEngine

        sites = [
            SiteInput(
                site_id="DEMO_OP_S01",
                site_name="Frohavet North",
                latitude=63.5,
                longitude=8.2,
                biomass_tonnes=3200,
                temperature_c=9.5,
                salinity_ppt=33.5,
                dissolved_oxygen_mg_l=9.2,
                lice_count_per_fish=0.35,
                jellyfish_risk_index=0.25,
            ),
            SiteInput(
                site_id="DEMO_OP_S02",
                site_name="Sunndalsfjord",
                latitude=62.7,
                longitude=8.6,
                biomass_tonnes=3500,
                temperature_c=10.1,
                salinity_ppt=32.0,
                dissolved_oxygen_mg_l=9.8,
                lice_count_per_fish=0.28,
                jellyfish_risk_index=0.15,
            ),
            SiteInput(
                site_id="DEMO_OP_S03",
                site_name="Storfjorden South",
                latitude=62.1,
                longitude=7.1,
                biomass_tonnes=2500,
                temperature_c=8.8,
                salinity_ppt=34.0,
                dissolved_oxygen_mg_l=10.2,
                lice_count_per_fish=0.18,
                jellyfish_risk_index=0.08,
            ),
        ]
        op = C5AIOperatorInput(
            operator_id="DEMO_OP",
            operator_name="Nordic Aqua Partners AS",
            sites=sites,
        )
        engine = MultiDomainEngine()
        result = engine.run(op)
        risk_types = getattr(result, "risk_types_active", None) or []
        site_ids = [s.site_id for s in sites]
        site_names = [s.site_name for s in sites]
        data_mode = "real"
        return {
            "site_count":      len(sites),
            "domain_count":    4,
            "risk_type_count": len(risk_types) if risk_types else 15,
            "pipeline_ran":    True,
            "message":         "C5AI+ pipeline kjørt (alle domener)",
            "site_ids":        site_ids,
            "site_names":      site_names,
            "data_mode":       data_mode,
        }
    except Exception as exc:  # noqa: BLE001
        # Stub fallback — pipeline failed but run is still recorded
        return {
            "site_count":      3,
            "domain_count":    4,
            "risk_type_count": 15,
            "pipeline_ran":    False,
            "message":         f"C5AI+ pipeline stub (feil: {exc})",
            "site_ids":        ["DEMO_OP_S01", "DEMO_OP_S02", "DEMO_OP_S03"],
            "site_names":      ["Frohavet North", "Sunndalsfjord", "Storfjorden South"],
            "data_mode":       "simulated",
        }


@router.post("/run", response_model=C5AIRunResponse)
def run_c5ai() -> C5AIRunResponse:
    """
    Trigger the C5AI+ analysis pipeline and record the run timestamp.

    Returns run metadata so the frontend can display freshness status.
    """
    run_meta = _run_c5ai_pipeline_safe()
    from backend.services.c5ai_state import store_run_extra
    store_run_extra({
        "site_ids": run_meta["site_ids"],
        "site_names": run_meta["site_names"],
        "data_mode": run_meta["data_mode"],
        "domains_used": ["biological", "structural", "environmental", "operational"],
        "risk_type_count": run_meta["risk_type_count"],
        "source_labels": ["Simulert — demo data"] if not run_meta["pipeline_ran"] else ["C5AI+ MultiDomainEngine"],
    })
    run_id, run_at = c5ai_state.record_c5ai_run()
    status = c5ai_state.get_status()

    return C5AIRunResponse(
        run_id=run_id,
        generated_at=run_at.isoformat(),
        status="ok" if run_meta["pipeline_ran"] else "stub",
        site_count=run_meta["site_count"],
        domain_count=run_meta["domain_count"],
        risk_type_count=run_meta["risk_type_count"],
        pipeline_ran=run_meta["pipeline_ran"],
        message=run_meta["message"],
        freshness=status["freshness"],
    )


@router.get("/status", response_model=C5AIStatusResponse)
def get_c5ai_status() -> C5AIStatusResponse:
    """Return the current C5AI+ freshness status."""
    s = c5ai_state.get_status()
    return C5AIStatusResponse(
        run_id=s["run_id"],
        c5ai_last_run_at=s["c5ai_last_run_at"],
        inputs_last_updated_at=s["inputs_last_updated_at"],
        is_fresh=s["is_fresh"],
        freshness=s["freshness"],
    )


@router.post("/inputs/updated")
def inputs_updated() -> dict:
    """
    Notify the backend that operator inputs have changed.

    Marks the C5AI+ analysis as stale if it has not been re-run since.
    """
    ts = c5ai_state.mark_inputs_updated()
    status = c5ai_state.get_status()
    return {
        "inputs_last_updated_at": ts.isoformat(),
        "freshness": status["freshness"],
    }
