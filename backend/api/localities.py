"""
backend/api/localities.py

Locality Risk Profile API endpoints.

GET  /api/localities/{id}/risk-profile
POST /api/localities/risk-profiles
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.live_risk_mock import get_all_locality_ids
from backend.services.locality_risk_builder import (
    build_locality_risk_profile,
    build_locality_risk_profiles,
)

router = APIRouter(prefix="/api/localities", tags=["localities"])

_KNOWN_IDS = set(get_all_locality_ids())


def _check_locality(locality_id: str) -> None:
    if locality_id not in _KNOWN_IDS:
        raise HTTPException(
            status_code=404,
            detail=f"Locality '{locality_id}' not found. Known IDs: {sorted(_KNOWN_IDS)}",
        )


# ── Request / response models ───────────────────────────────────────────────────

class LocalityRiskProfilesRequest(BaseModel):
    locality_ids: List[str]


# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.get("/{locality_id}/risk-profile")
def get_locality_risk_profile(locality_id: str) -> Dict[str, Any]:
    """
    Return the full LocalityRiskProfile for a single locality.

    Combines Live Risk signals, locality metadata, and (if available) cage
    portfolio weighting into a single, inspectable risk profile object.
    """
    _check_locality(locality_id)
    profile = build_locality_risk_profile(locality_id)
    return profile.to_dict()


@router.post("/risk-profiles")
def get_locality_risk_profiles(req: LocalityRiskProfilesRequest) -> List[Dict[str, Any]]:
    """
    Return LocalityRiskProfile objects for a list of locality IDs.

    Unknown IDs are returned as 404 entries embedded in the list under an
    'error' key so callers can handle partial failures gracefully.
    """
    results = []
    for lid in req.locality_ids:
        if lid not in _KNOWN_IDS:
            results.append({"locality_id": lid, "error": f"Locality '{lid}' not found"})
            continue
        profile = build_locality_risk_profile(lid)
        results.append(profile.to_dict())
    return results
