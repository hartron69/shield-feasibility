"""
c5ai_plus/biological/ila/input_builder.py

Bygger ILAMre1Input fra lokalitetsprofil og levende observasjonsdata.

Dataflyt
--------
Live Risk Mock → live_signals → _compute_live_scalars()
                                    ↓
ILA-profil (statisk)          →  bygg_mre1_input_live()  → ILAMre1Input
                                    ↓
Nabolokaliteter               →  _nabo_smittepress()

Parametre som nå hentes fra live-data (vs. statisk hardkodet v1):
  biomasse_tetthet_norm   ← biomass_tonnes / mtb_tonnes  (fra locality_config)
  stressniva_norm         ← f(lus, temp, O₂, behandling) siste 7 dager
  antall_nabo_med_ila     ← antall nabolokaliteter med aktiv sykdomsflagg
  i_fraksjon_naboer       ← gjennomsnittlig lusenivå hos nabolokaliteter (proxy)
  e0 (MRE-2)              ← siste 21 dagers sykdomsflagg → initial eksponert-fraksjon
"""
from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Tuple

from c5ai_plus.biological.ila.mre1 import ILAMre1Input


# ── Statiske ILA-profiler (tilsvarer ILALokalitetProfil-tabellen) ────────────
#
# Felter som krever DB/API i produksjon og som IKKE kan utledes fra live-data:
#   hpr0_tetthet             — Barentswatch genotype-screening (ukentlig)
#   klekkeriet_risiko        — settefisk-leverandørens HPR0-historikk
#   ila_sone                 — Mattilsynets sone-klassifisering
#   bronnbat_besok_per_ar    — serviceselskap-logg
#   bronnbat_desinfeksjon_rate — biosikkerhetsrapport
#   delte_ops_per_ar         — operasjonelle tillatelser
#   smolt_uker_siden_utsett  — settefisk-register
#   biomasse_verdi_mnok      — TIV fra forsikringsmodellen

_ILA_PROFILER: Dict[str, dict] = {
    "KH_S01": {
        "hpr0_tetthet":               0.28,
        "klekkeriet_risiko":          0.05,
        "ila_sone":                   "fri",
        "bronnbat_besok_per_ar":      14,
        "bronnbat_desinfeksjon_rate": 0.85,
        "delte_ops_per_ar":           8,
        "smolt_uker_siden_utsett":    20,
        "siste_smolt_utsett":         None,
        "biomasse_verdi_mnok":        19.5,
    },
    "KH_S02": {
        "hpr0_tetthet":               0.32,
        "klekkeriet_risiko":          0.08,
        "ila_sone":                   "overvaking",
        "bronnbat_besok_per_ar":      16,
        "bronnbat_desinfeksjon_rate": 0.80,
        "delte_ops_per_ar":           10,
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
        "smolt_uker_siden_utsett":    10,
        "siste_smolt_utsett":         None,
        "biomasse_verdi_mnok":        22.75,
    },
}

# Nabogrupper — lokaliteter i samme fjord-nettverk som påvirker hverandre
# (i produksjon: spatial query på avstand ≤ N km)
_NABO_GRUPPER: Dict[str, List[str]] = {
    "KH_S01": ["KH_S02", "KH_S03"],
    "KH_S02": ["KH_S01", "KH_S03"],
    "KH_S03": ["KH_S01", "KH_S02"],
    "LM_S01": ["KH_S01"],          # LM_S01 deler farvann med Kornstad
}

# Terskel-konstanter for live-signal-skalering
_LICE_STRESS_THRESHOLD: float = 0.5   # lus/fisk — under er greit
_LICE_STRESS_SCALE:     float = 2.0   # lus/fisk → 1.0 stress ved +2.0 over terskel
_TEMP_STRESS_THRESHOLD: float = 10.0  # °C — varmetrøbbel over 10°C
_TEMP_STRESS_SCALE:     float = 5.0   # +5°C over terskel → 1.0 stress
_OXY_STRESS_THRESHOLD:  float = 9.0   # mg/L — lavt oksygen under 9 mg/L
_OXY_STRESS_SCALE:      float = 4.0   # 4 mg/L under terskel → 1.0 stress
_TREAT_STRESS_SCALE:    float = 5.0   # 5 behandlinger siste 7 dager → 1.0 stress
_E0_DISEASE_21D:        float = 0.01  # 1% eksponert om sykdom siste 21 dager
_E0_DISEASE_7D:         float = 0.03  # 3% eksponert om sykdom siste 7 dager


# ── Offentlig API ─────────────────────────────────────────────────────────────

def hent_ila_profil(lokalitet_id: str) -> Optional[dict]:
    """Returnerer statisk ILA-profil, eller None hvis ingen profil fins."""
    return _ILA_PROFILER.get(lokalitet_id)


def bygg_mre1_input_live(lokalitet_id: str) -> Optional[ILAMre1Input]:
    """
    Bygger ILAMre1Input ved å kombinere statisk ILA-profil med levende
    Barentswatch-signaler fra live_risk_mock.

    Dynamisk beregnede parametere (vs. v1 hardkodede):
      biomasse_tetthet_norm   — biomass_tonnes / mtb_tonnes
      stressniva_norm         — f(lus, temp, O₂, behandling) siste 7 dager
      antall_nabo_med_ila     — naboer med aktiv sykdomsflagg siste 21 dager
      i_fraksjon_naboer       — normalisert lusenivå hos naboer (smittepressProxy)

    Returns None hvis lokaliteten mangler ILA-profil.
    """
    profil = _ILA_PROFILER.get(lokalitet_id)
    if profil is None:
        return None

    # Importer her for å unngå sirkulær import på modulnivå
    from backend.services.live_risk_mock import get_locality_data, get_locality_config

    live   = get_locality_data(lokalitet_id)
    config = get_locality_config(lokalitet_id)

    # ── Dynamiske parametere ──────────────────────────────────────────────────
    biomasse_norm = _compute_biomasse_tetthet(config)
    stress_norm   = _compute_stressniva(live)
    nabo_ila, i_fraksjon = _compute_nabo_smittepress(lokalitet_id)

    # ── Statiske parametere (krever DB i produksjon) ──────────────────────────
    smolt_uker = _compute_smolt_uker(profil)
    fugl_sesong = _er_fuglesesong()

    return ILAMre1Input(
        hpr0_tetthet=profil["hpr0_tetthet"],
        i_fraksjon_naboer=i_fraksjon,
        bronnbat_besok_per_ar=profil["bronnbat_besok_per_ar"],
        bronnbat_desinfeksjon_rate=profil["bronnbat_desinfeksjon_rate"],
        antall_nabo_med_ila=nabo_ila,
        delte_ops_per_ar=profil["delte_ops_per_ar"],
        biomasse_tetthet_norm=biomasse_norm,
        stressniva_norm=stress_norm,
        smolt_uker_siden_utsett=smolt_uker,
        fugl_sesong_aktiv=fugl_sesong,
    )


def bygg_mre2_e0(lokalitet_id: str) -> float:
    """
    Beregner initial eksponert-fraksjon (e0) for MRE-2 fra sykdomsflagg.

    e0 > 0 indikerer at det allerede er smittede fisk ved sesongstart /
    siste beregningstidspunkt.
    """
    profil = _ILA_PROFILER.get(lokalitet_id)
    if profil is None:
        return 0.0

    from backend.services.live_risk_mock import get_locality_data
    live = get_locality_data(lokalitet_id)
    return _compute_e0(live)


# Bakoverkompatibel wrapper — brukes i tester som ikke tester live-kobling
def bygg_mre1_input(
    lokalitet_id: str,
    i_fraksjon_naboer: float = 0.01,
    antall_nabo_med_ila: int = 0,
) -> Optional[ILAMre1Input]:
    """
    Bygger ILAMre1Input.  Prøver live-data; faller tilbake til statisk profil
    hvis live-data ikke er tilgjengelig (f.eks. i isolerte tester).
    """
    try:
        return bygg_mre1_input_live(lokalitet_id)
    except Exception:
        return _bygg_fra_statisk_profil(lokalitet_id, i_fraksjon_naboer, antall_nabo_med_ila)


# ── Private helpers ───────────────────────────────────────────────────────────

def _compute_biomasse_tetthet(config: dict) -> float:
    """
    Biomasse-tetthet = nåværende biomasse / maks tillatt biomasse (MTB).

    Verdi 0–1 der 1.0 = fullt utnyttet MTB.
    """
    mtb = config.get("mtb_tonnes") or 1.0
    bio = config.get("biomass_tonnes") or 0.0
    return round(min(1.0, bio / mtb), 4)


def _compute_stressniva(live: dict, lookback_days: int = 7) -> float:
    """
    Stressnivå 0–1 beregnet fra siste N dagers levende signaler.

    Komponenter (like vektede):
      lice_stress   — lus over terskel 0.5 lus/fisk
      temp_stress   — temperatur over 10°C
      oxy_stress    — oksygen under 9 mg/L
      treat_stress  — behandlingsintensitet siste 7 dager

    Kalibrert slik at normalt frisk lokalitet gir ≈ 0.05–0.15.
    """
    lice      = live.get("lice",        [])
    temp      = live.get("temperature", [])
    oxy       = live.get("oxygen",      [])
    treatment = live.get("treatment",   [])

    # Siste N dager (siste elementer i listene)
    def last_n(lst: list) -> list:
        return [v for v in lst[-lookback_days:] if v is not None]

    lice_vals  = last_n(lice)
    temp_vals  = last_n(temp)
    oxy_vals   = last_n(oxy)
    treat_vals = last_n(treatment)

    # Luse-stress: gjennomsnitt over terskel, normalisert
    avg_lice = sum(lice_vals) / len(lice_vals) if lice_vals else 0.0
    lice_stress = min(1.0, max(0.0, avg_lice - _LICE_STRESS_THRESHOLD) / _LICE_STRESS_SCALE)

    # Temperatur-stress: varme over 10°C
    avg_temp = sum(temp_vals) / len(temp_vals) if temp_vals else 7.0
    temp_stress = min(1.0, max(0.0, avg_temp - _TEMP_STRESS_THRESHOLD) / _TEMP_STRESS_SCALE)

    # Oksygen-stress: hypoksi under 9 mg/L
    avg_oxy = sum(oxy_vals) / len(oxy_vals) if oxy_vals else 9.0
    oxy_stress = min(1.0, max(0.0, _OXY_STRESS_THRESHOLD - avg_oxy) / _OXY_STRESS_SCALE)

    # Behandlings-stress: behandlinger siste 7 dager (rullende sum fra siste element)
    last_treat = treat_vals[-1] if treat_vals else 0
    # treatment er en rullende 30-dagers sum — ta differansen for å estimere siste 7 dager
    prev_treat = treat_vals[0] if len(treat_vals) > 1 else last_treat
    treat_7d   = max(0, last_treat - prev_treat) if len(treat_vals) > 1 else last_treat
    treat_stress = min(1.0, treat_7d / _TREAT_STRESS_SCALE)

    # Vektet gjennomsnitt (lus og O₂ mest relevante for ILA)
    stress = (
        0.30 * lice_stress
        + 0.15 * temp_stress
        + 0.35 * oxy_stress
        + 0.20 * treat_stress
    )
    return round(min(1.0, stress), 4)


def _compute_e0(live: dict, lookback_7d: int = 7, lookback_21d: int = 21) -> float:
    """
    Beregner initial eksponert-fraksjon e0 for MRE-2 fra sykdomsflagg.

    Hvis sykdom er aktiv:
      siste 7 dager  → e0 = 0.03 (3% eksponert)
      siste 21 dager → e0 = 0.01 (1% eksponert)
      eldre / ingen  → e0 = 0.0
    """
    disease = live.get("disease", [])
    if not disease:
        return 0.0
    last_7  = disease[-lookback_7d:]
    last_21 = disease[-lookback_21d:]
    if any(d == 1 for d in last_7):
        return _E0_DISEASE_7D
    if any(d == 1 for d in last_21):
        return _E0_DISEASE_21D
    return 0.0


def _compute_nabo_smittepress(
    lokalitet_id: str,
) -> Tuple[int, float]:
    """
    Beregner nabo-ILA-press fra levende data hos nabolokaliteter.

    Returns
    -------
    antall_nabo_med_ila : int
        Antall naboer med aktiv sykdomsflagg siste 21 dager (proxy for ILA-aktivitet).
    i_fraksjon_naboer : float
        Normalisert lusenivå hos naboer — brukes som hydrodynamisk smittepress-proxy.
    """
    naboer = _NABO_GRUPPER.get(lokalitet_id, [])
    if not naboer:
        return 0, 0.01

    from backend.services.live_risk_mock import get_locality_data

    nabo_ila_count = 0
    lice_sum       = 0.0
    lice_n         = 0

    for nabo_id in naboer:
        try:
            nabo_live = get_locality_data(nabo_id)
        except Exception:
            continue

        # Sykdomsflagg siste 21 dager → proxy for aktiv ILA
        disease = nabo_live.get("disease", [])
        if any(d == 1 for d in disease[-21:]):
            nabo_ila_count += 1

        # Gjennomsnittlig lusenivå siste 7 dager
        lice_vals = [v for v in nabo_live.get("lice", [])[-7:] if v is not None]
        if lice_vals:
            lice_sum += sum(lice_vals) / len(lice_vals)
            lice_n   += 1

    # Normalisert lusepress: gjennomsnitt / referanseskala (3 lus/fisk → 1.0)
    avg_nabo_lice   = lice_sum / lice_n if lice_n else 0.0
    i_fraksjon_proxy = round(min(1.0, avg_nabo_lice / 3.0), 4)

    return nabo_ila_count, max(0.01, i_fraksjon_proxy)


def _compute_smolt_uker(profil: dict) -> int:
    """Beregner uker siden smolt-utsett (fra dato om tilgjengelig)."""
    if profil.get("siste_smolt_utsett"):
        delta = (datetime.date.today() - profil["siste_smolt_utsett"]).days
        return max(0, delta // 7)
    return profil.get("smolt_uker_siden_utsett", 4)


def _er_fuglesesong() -> bool:
    """Fuglesesong: uke 18–39 (mai–september)."""
    return 18 <= datetime.date.today().isocalendar()[1] <= 39


def _bygg_fra_statisk_profil(
    lokalitet_id: str,
    i_fraksjon_naboer: float,
    antall_nabo_med_ila: int,
) -> Optional[ILAMre1Input]:
    """Fallback: statisk profil uten live-data (brukes i isolerte tester)."""
    profil = _ILA_PROFILER.get(lokalitet_id)
    if profil is None:
        return None
    return ILAMre1Input(
        hpr0_tetthet=profil["hpr0_tetthet"],
        i_fraksjon_naboer=i_fraksjon_naboer,
        bronnbat_besok_per_ar=profil["bronnbat_besok_per_ar"],
        bronnbat_desinfeksjon_rate=profil["bronnbat_desinfeksjon_rate"],
        antall_nabo_med_ila=antall_nabo_med_ila,
        delte_ops_per_ar=profil["delte_ops_per_ar"],
        biomasse_tetthet_norm=profil.get("biomasse_tetthet_norm", 0.60),
        stressniva_norm=profil.get("stressniva_norm", 0.10),
        smolt_uker_siden_utsett=_compute_smolt_uker(profil),
        fugl_sesong_aktiv=_er_fuglesesong(),
    )
