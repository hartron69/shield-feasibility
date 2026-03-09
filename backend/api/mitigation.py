"""
Mitigation library endpoint.

GET /api/mitigation/library – list all predefined mitigation actions
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter

from analysis.mitigation import PREDEFINED_MITIGATIONS
from backend.schemas import MitigationActionInfo

router = APIRouter()


@router.get("/library", response_model=List[MitigationActionInfo])
def get_mitigation_library() -> List[MitigationActionInfo]:
    """Return all predefined mitigation actions."""
    result = []
    for action_id, action in PREDEFINED_MITIGATIONS.items():
        result.append(
            MitigationActionInfo(
                id=action_id,
                name=action.name,
                description=action.description,
                affected_domains=action.applies_to_domains,
                probability_reduction=action.probability_reduction,
                severity_reduction=action.severity_reduction,
                annual_cost_nok=action.annual_cost_nok,
                capex_nok=action.capex_nok,
                targeted_risk_types=action.targeted_risk_types,
            )
        )
    return result
