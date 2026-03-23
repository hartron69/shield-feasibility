"""
Sea / open-water loss categories with exposure-weighted shares.

Used by ScenarioEngine._run_sea() to break per-site scenario losses into
domain-level categories (biological, environmental, structural, operational, transport).

Exposure types: "open_coast" | "semi_exposed" | "sheltered"
"""

from __future__ import annotations

SEA_LOSS_CATEGORIES: dict = {
    "biological": {
        "label":       "Biologisk (lus, ILA, AMG, patogen)",
        "description": "Lusepåslag, sykdomsutbrudd, algeoppblomstring",
        "color":       "#1A6B6B",
        "share_open":      0.42,
        "share_semi":      0.38,
        "share_sheltered": 0.27,
    },
    "environmental": {
        "label":       "Miljø (HAB, manet, storm)",
        "description": "Skadelige algeoppblomstringer, manetinvasjon, ekstremvær",
        "color":       "#2E6EA6",
        "share_open":      0.28,
        "share_semi":      0.24,
        "share_sheltered": 0.18,
    },
    "structural": {
        "label":       "Strukturell (fortøyning, not, merd)",
        "description": "Fortøyningssvikt, notsprekk, rømming fra strukturskade",
        "color":       "#C0392B",
        "share_open":      0.18,
        "share_semi":      0.22,
        "share_sheltered": 0.31,
    },
    "operational": {
        "label":       "Operasjonell (rømming, feilhåndtering)",
        "description": "Menneskelig feil, prosedyresvikt, utstyrssvikt",
        "color":       "#E67E22",
        "share_open":      0.08,
        "share_semi":      0.11,
        "share_sheltered": 0.14,
    },
    "transport": {
        "label":       "Transport og brønnbåt",
        "description": "Skade under avlusning, behandling eller transport",
        "color":       "#8E44AD",
        "share_open":      0.04,
        "share_semi":      0.05,
        "share_sheltered": 0.10,
    },
}


def get_shares_for_exposure(exposure_type: str) -> dict:
    """
    Return {cat_id: share} for the given exposure type.
    exposure_type: "open_coast" | "semi_exposed" | "sheltered"
    Falls back to "semi_exposed" for unknown values.
    """
    key = {
        "open_coast":   "share_open",
        "semi_exposed": "share_semi",
        "sheltered":    "share_sheltered",
    }.get(exposure_type, "share_semi")
    return {cat: data[key] for cat, data in SEA_LOSS_CATEGORIES.items()}
