"""
c5ai_plus/biological/ila/input_builder.py

Bygger ILAMre1Input fra lokalitetsprofil og observasjonsdata.

Tilsvarer rollen til kpi_readings-spørringen i originalversjonen,
men bruker Shield-plattformens mock-datalag i stedet for DB-spørringer.
"""
from __future__ import annotations

import datetime
from typing import Dict, Optional

from c5ai_plus.biological.ila.mre1 import ILAMre1Input


# ── Statiske ILA-profiler (tilsvarer ILALokalitetProfil-tabellen) ────────────
#
# I produksjon hentes disse fra databasen.
# I mock-arkitekturen er de hard-kodet per kjente lokalitet.

_ILA_PROFILER: Dict[str, dict] = {
    "KH_S01": {
        "hpr0_tetthet":               0.28,
        "klekkeriet_risiko":          0.05,
        "ila_sone":                   "fri",
        "bronnbat_besok_per_ar":      14,
        "bronnbat_desinfeksjon_rate": 0.85,
        "delte_ops_per_ar":           8,
        "biomasse_tetthet_norm":      0.62,
        "stressniva_norm":            0.12,
        "smolt_uker_siden_utsett":    20,
        "siste_smolt_utsett":         None,
        "biomasse_verdi_mnok":        19.5,   # ~3000 tonn × 65k NOK/t / 1e6
    },
    "KH_S02": {
        "hpr0_tetthet":               0.32,
        "klekkeriet_risiko":          0.08,
        "ila_sone":                   "overvaking",
        "bronnbat_besok_per_ar":      16,
        "bronnbat_desinfeksjon_rate": 0.80,
        "delte_ops_per_ar":           10,
        "biomasse_tetthet_norm":      0.70,
        "stressniva_norm":            0.18,
        "smolt_uker_siden_utsett":    14,
        "siste_smolt_utsett":         None,
        "biomasse_verdi_mnok":        16.25,
    },
    "KH_S03": {
        "hpr0_tetthet":               0.15,
        "klekkeriet_risiko":          0.03,
        "ila_sone":                   "fri",
        "bronnbat_besok_per_ar":      10,
        "bronnbat_desinfeksjon_rate": 0.90,
        "delte_ops_per_ar":           5,
        "biomasse_tetthet_norm":      0.40,
        "stressniva_norm":            0.05,
        "smolt_uker_siden_utsett":    30,
        "siste_smolt_utsett":         None,
        "biomasse_verdi_mnok":        9.75,
    },
    "LM_S01": {
        "hpr0_tetthet":               0.35,
        "klekkeriet_risiko":          0.07,
        "ila_sone":                   "fri",
        "bronnbat_besok_per_ar":      18,
        "bronnbat_desinfeksjon_rate": 0.82,
        "delte_ops_per_ar":           12,
        "biomasse_tetthet_norm":      0.75,
        "stressniva_norm":            0.20,
        "smolt_uker_siden_utsett":    10,
        "siste_smolt_utsett":         None,
        "biomasse_verdi_mnok":        22.75,
    },
}


def hent_ila_profil(lokalitet_id: str) -> Optional[dict]:
    """Returnerer ILA-profil for lokaliteten, eller None hvis ingen profil fins."""
    return _ILA_PROFILER.get(lokalitet_id)


def bygg_mre1_input(
    lokalitet_id: str,
    i_fraksjon_naboer: float = 0.01,
    antall_nabo_med_ila: int = 0,
) -> Optional[ILAMre1Input]:
    """
    Bygger ILAMre1Input fra mock-lokalitetsprofil.

    Returns None hvis lokaliteten mangler ILA-profil.

    Parameters
    ----------
    lokalitet_id        : shield-intern ID (f.eks. KH_S01)
    i_fraksjon_naboer   : I-fraksjon fra MRE-2 naboberegning (0–1)
    antall_nabo_med_ila : antall naboer med aktiv ILA
    """
    profil = _ILA_PROFILER.get(lokalitet_id)
    if profil is None:
        return None

    # Smolt-uker siden utsett: beregn fra dato hvis satt
    smolt_uker = profil["smolt_uker_siden_utsett"]
    if profil.get("siste_smolt_utsett"):
        delta = (datetime.date.today() - profil["siste_smolt_utsett"]).days
        smolt_uker = max(0, delta // 7)

    # Fuglesesong: uke 18–39 (mai–september)
    iso_uke = datetime.date.today().isocalendar()[1]
    fugl_sesong = 18 <= iso_uke <= 39

    return ILAMre1Input(
        hpr0_tetthet=profil["hpr0_tetthet"],
        i_fraksjon_naboer=i_fraksjon_naboer,
        bronnbat_besok_per_ar=profil["bronnbat_besok_per_ar"],
        bronnbat_desinfeksjon_rate=profil["bronnbat_desinfeksjon_rate"],
        antall_nabo_med_ila=antall_nabo_med_ila,
        delte_ops_per_ar=profil["delte_ops_per_ar"],
        biomasse_tetthet_norm=profil["biomasse_tetthet_norm"],
        stressniva_norm=profil["stressniva_norm"],
        smolt_uker_siden_utsett=smolt_uker,
        fugl_sesong_aktiv=fugl_sesong,
    )
