"""
backend/api/ila.py

ILA-risikomodul API-endepunkter.

GET  /api/ila/{locality_id}/mre1          — Øyeblikks-snapshot (MRE-1)
GET  /api/ila/{locality_id}/mre2          — 52-ukers SEIR-sesongkurve (MRE-2)
GET  /api/ila/portfolio                   — Porteføljeoversikt (alle kjente lokaliteter)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from backend.services.live_risk_mock import get_all_locality_ids
from c5ai_plus.biological.ila.input_builder import (
    bygg_mre1_input,
    bygg_mre2_e0,
    hent_ila_profil,
)
from c5ai_plus.biological.ila.mre1 import kjor_mre1
from c5ai_plus.biological.ila.mre2 import kjor_mre2

router = APIRouter(prefix="/api/ila", tags=["ila"])

_KNOWN_IDS = set(get_all_locality_ids())


# ── MRE-1 snapshot ───────────────────────────────────────────────────────────

@router.get("/{locality_id}/mre1")
def get_ila_mre1(locality_id: str) -> Dict[str, Any]:
    """
    Øyeblikks-snapshot: P_total, varselnivå, per-kilde P-verdier og attribusjon.

    Returns 404 for unknown locality IDs.
    Returns 422 if the locality has no ILA profile.
    """
    if locality_id not in _KNOWN_IDS:
        raise HTTPException(
            status_code=404,
            detail=f"Locality '{locality_id}' not found. Known: {sorted(_KNOWN_IDS)}",
        )

    profil = hent_ila_profil(locality_id)
    if profil is None:
        raise HTTPException(
            status_code=422,
            detail=f"Locality '{locality_id}' has no ILA profile.",
        )

    ila_input = bygg_mre1_input(locality_id)
    resultat  = kjor_mre1(ila_input, biomasse_verdi_mnok=profil["biomasse_verdi_mnok"])

    return {
        "locality_id":        locality_id,
        "ila_sone":           profil.get("ila_sone", "fri"),
        "hpr0_tetthet":       profil["hpr0_tetthet"],
        **resultat.to_dict(),
    }


# ── MRE-2 sesongkurve ────────────────────────────────────────────────────────

@router.get("/{locality_id}/mre2")
def get_ila_mre2(
    locality_id: str,
    sesong_uker: int = 52,
) -> Dict[str, Any]:
    """
    52-ukers SEIR hazard-modell for inneværende sesong.

    Returns list of weekly states with SEIR fractions and cumulative probability.
    """
    if locality_id not in _KNOWN_IDS:
        raise HTTPException(status_code=404, detail=f"Locality '{locality_id}' not found.")

    profil = hent_ila_profil(locality_id)
    if profil is None:
        raise HTTPException(status_code=422, detail=f"No ILA profile for '{locality_id}'.")

    if not (4 <= sesong_uker <= 104):
        raise HTTPException(status_code=422, detail="sesong_uker must be 4–104.")

    e0 = bygg_mre2_e0(locality_id)
    uker = kjor_mre2(
        sesong_uker=sesong_uker,
        hpr0_tetthet=profil["hpr0_tetthet"],
        e0=e0,
    )

    return {
        "locality_id": locality_id,
        "sesong_uker": sesong_uker,
        "antall":      len(uker),
        "uker":        [u.to_dict() for u in uker],
    }


# ── Porteføljeoversikt ───────────────────────────────────────────────────────

@router.get("/portfolio")
def get_ila_portfolio() -> Dict[str, Any]:
    """
    ILA-porteføljeoversikt — siste MRE-1 snapshot for alle lokaliteter
    med aktiv ILA-profil, sortert etter P_total (høyest risiko øverst).
    """
    lokaliteter: List[Dict[str, Any]] = []

    for lid in sorted(_KNOWN_IDS):
        profil = hent_ila_profil(lid)
        if profil is None:
            continue

        ila_input = bygg_mre1_input(lid)
        resultat  = kjor_mre1(ila_input, biomasse_verdi_mnok=profil["biomasse_verdi_mnok"])

        lokaliteter.append({
            "locality_id":        lid,
            "ila_sone":           profil.get("ila_sone", "fri"),
            "hpr0_tetthet":       profil["hpr0_tetthet"],
            "biomasse_verdi_mnok": profil["biomasse_verdi_mnok"],
            **resultat.to_dict(),
        })

    lokaliteter.sort(key=lambda x: x["p_total"], reverse=True)

    return {
        "antall":      len(lokaliteter),
        "lokaliteter": lokaliteter,
    }
