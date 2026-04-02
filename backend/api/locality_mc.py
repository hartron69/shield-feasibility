"""
backend/api/locality_mc.py

Locality Monte Carlo endpoints.

GET  /api/localities/{id}/mc
POST /api/localities/mc-batch
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.live_risk_mock import get_all_locality_ids
from backend.services.locality_mc_runner import (
    run_locality_mc,
    run_locality_mc_batch,
    _DEFAULT_N_SIMS,
)

router = APIRouter(prefix="/api/localities", tags=["localities"])

_KNOWN_IDS = set(get_all_locality_ids())


class MCBatchRequest(BaseModel):
    locality_ids: List[str]
    n_simulations: int = Field(default=_DEFAULT_N_SIMS, ge=500, le=20_000)


@router.get("/{locality_id}/mc")
def get_locality_mc(
    locality_id: str,
    n_simulations: int = _DEFAULT_N_SIMS,
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation for a single locality and return results.

    Returns EAL, SCR (VaR 99.5%), domain breakdown, and input transparency fields.
    """
    if locality_id not in _KNOWN_IDS:
        raise HTTPException(
            status_code=404,
            detail=f"Locality '{locality_id}' not found. Known: {sorted(_KNOWN_IDS)}",
        )
    if not (500 <= n_simulations <= 20_000):
        raise HTTPException(status_code=422, detail="n_simulations must be 500–20000")

    result = run_locality_mc(locality_id, n_simulations=n_simulations)
    return result.to_dict()


@router.post("/mc-batch")
def post_locality_mc_batch(req: MCBatchRequest) -> List[Dict[str, Any]]:
    """
    Run Monte Carlo for multiple localities.

    Unknown IDs produce error entries rather than aborting the whole batch.
    """
    return run_locality_mc_batch(req.locality_ids, n_simulations=req.n_simulations)
