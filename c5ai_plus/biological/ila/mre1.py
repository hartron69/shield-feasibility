"""
c5ai_plus/biological/ila/mre1.py

MRE-1 Øyeblikks-snapshot for ILA-risiko.

Portert fra /reference/mre_full_comparison.py :: run_mre1_at()
Matematikken er identisk — kun input/output er tilpasset Shield-datamodellen.

P_total = 1 − ∏_k (1 − P_k)

Kilder k ∈ {HYDRO, WB, OPS, SMOLT, WILD, MUTATE, BIRD}

Varselterskler:
  P_total < 0.05  → GRØNN   (ingen varsling)
  P_total ≥ 0.05  → ILA01   alvorlighet=lav
  P_total ≥ 0.20  → ILA02   alvorlighet=middels
  P_total ≥ 0.50  → ILA03   alvorlighet=høy
  P_total ≥ 0.80  → ILA04   alvorlighet=kritisk
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional


# ── Input dataclass ──────────────────────────────────────────────────────────

@dataclass
class ILAMre1Input:
    """
    Bygges av input_builder.py fra lokalitetsprofil og observasjonsdata.
    Alle felter tilsvarer parametere i run_mre1_at() i referanseimplementasjonen.
    """
    # Hydrodynamisk risiko (HPR0-tetthet + I-fraksjon fra nabo-lokaliteter)
    hpr0_tetthet:          float = 0.25   # HPR0-variant tetthet 0–1
    i_fraksjon_naboer:     float = 0.02   # fra MRE-2 I-fraksjon nabosett

    # Brønnbåt
    bronnbat_besok_per_ar:       int   = 12
    bronnbat_desinfeksjon_rate:  float = 0.85   # 0–1
    antall_nabo_med_ila:         int   = 0

    # Operasjonelt
    delte_ops_per_ar:         int   = 8
    biomasse_tetthet_norm:    float = 0.50   # 0–1
    stressniva_norm:          float = 0.10   # 0–1

    # Smolt
    smolt_uker_siden_utsett: int = 4

    # Villfisk og mutasjon
    villfisk_tetthet_norm:   float = 0.30
    mutasjonsrate_prior:     float = 0.002

    # Fugl (sesongavhengig)
    fugl_sesong_aktiv: bool = False


# ── Output dataclass ─────────────────────────────────────────────────────────

@dataclass
class ILAMre1Resultat:
    """Svarer til output fra run_mre1_at() i referanseimplementasjonen."""
    p_total:           float
    varselniva:        str            # GRØNN | ILA01 | ILA02 | ILA03 | ILA04
    dominerende_kilde: str
    e_tap_mnok:        Optional[float]

    p_hydro:   float = 0.0
    p_wb:      float = 0.0
    p_ops:     float = 0.0
    p_smolt:   float = 0.0
    p_wild:    float = 0.0
    p_mutate:  float = 0.0
    p_bird:    float = 0.0

    attrib_hydro:  float = 0.0
    attrib_wb:     float = 0.0
    attrib_ops:    float = 0.0
    attrib_smolt:  float = 0.0
    attrib_wild:   float = 0.0
    attrib_mutate: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "p_total":           self.p_total,
            "varselniva":        self.varselniva,
            "dominerende_kilde": self.dominerende_kilde,
            "e_tap_mnok":        self.e_tap_mnok,
            "p_hydro":           self.p_hydro,
            "p_wb":              self.p_wb,
            "p_ops":             self.p_ops,
            "p_smolt":           self.p_smolt,
            "p_wild":            self.p_wild,
            "p_mutate":          self.p_mutate,
            "p_bird":            self.p_bird,
            "attrib_hydro":      self.attrib_hydro,
            "attrib_wb":         self.attrib_wb,
            "attrib_ops":        self.attrib_ops,
            "attrib_smolt":      self.attrib_smolt,
            "attrib_wild":       self.attrib_wild,
            "attrib_mutate":     self.attrib_mutate,
        }


# ── Varselnivå-mapping ───────────────────────────────────────────────────────

def beregn_varselniva(p_total: float) -> str:
    """Mapper P_total til ILA-varselnivå."""
    if p_total >= 0.80:
        return "ILA04"
    elif p_total >= 0.50:
        return "ILA03"
    elif p_total >= 0.20:
        return "ILA02"
    elif p_total >= 0.05:
        return "ILA01"
    return "GRØNN"


# ── Beregningskjerne ─────────────────────────────────────────────────────────

def kjor_mre1(
    input: ILAMre1Input,
    biomasse_verdi_mnok: float = 10.0,
) -> ILAMre1Resultat:
    """
    Port av run_mre1_at() fra /reference/mre_full_comparison.py
    Matematikken er identisk — se referansefilen for full utledning.

    P_total = 1 − ∏_k (1 − P_k)
    """
    # HYDRO: hydrodynamisk smitterisiko via nærliggende smittet bestand
    p_hydro = 1 - math.exp(-input.hpr0_tetthet * input.i_fraksjon_naboer * 8.0)

    # WB: brønnbåt-smitte
    p_wb_per_visit = input.hpr0_tetthet * (1 - input.bronnbat_desinfeksjon_rate)
    p_wb = 1 - (1 - p_wb_per_visit) ** input.bronnbat_besok_per_ar
    if input.antall_nabo_med_ila > 0:
        p_wb = min(1.0, p_wb * (1 + 0.3 * input.antall_nabo_med_ila))

    # OPS: delte operasjoner
    p_ops_base = 0.01 * input.delte_ops_per_ar
    p_ops = p_ops_base * (1 + input.biomasse_tetthet_norm) * (1 + 2 * input.stressniva_norm)
    p_ops = min(p_ops, 0.40)

    # SMOLT: smolt-introduksjonsrisiko (avtar eksponentielt med uker siden utsett)
    p_smolt = 0.15 * math.exp(-0.15 * input.smolt_uker_siden_utsett)

    # WILD: villfisk-reservoir
    p_wild = 0.005 * input.villfisk_tetthet_norm * input.hpr0_tetthet * 52

    # MUTATE: HPR3→HPR0 mutasjonsrisiko
    p_mutate = input.mutasjonsrate_prior * (1 + input.biomasse_tetthet_norm)

    # BIRD: fugle-vektorfase (kun i sesong)
    p_bird = 0.01 if input.fugl_sesong_aktiv else 0.002

    # Total: P_total = 1 − ∏(1 − P_k)
    p_verdier = {
        "hydro":  p_hydro,
        "wb":     p_wb,
        "ops":    p_ops,
        "smolt":  p_smolt,
        "wild":   p_wild,
        "mutate": p_mutate,
        "bird":   p_bird,
    }
    p_total = 1.0 - math.prod(1 - p for p in p_verdier.values())
    p_total = min(p_total, 0.999)

    # Kilde-attribusjon (andel av summen, ikke av P_total)
    total_sum = sum(p_verdier.values()) or 1e-9
    attrib = {k: v / total_sum for k, v in p_verdier.items()}

    dominerende    = max(attrib, key=attrib.get)
    varselniva     = beregn_varselniva(p_total)
    e_tap_mnok     = round(p_total * biomasse_verdi_mnok, 3) if biomasse_verdi_mnok else None

    return ILAMre1Resultat(
        p_total=round(p_total, 6),
        varselniva=varselniva,
        dominerende_kilde=dominerende.upper(),
        e_tap_mnok=e_tap_mnok,
        p_hydro=round(p_hydro, 6),
        p_wb=round(p_wb, 6),
        p_ops=round(p_ops, 6),
        p_smolt=round(p_smolt, 6),
        p_wild=round(p_wild, 6),
        p_mutate=round(p_mutate, 6),
        p_bird=round(p_bird, 6),
        attrib_hydro=round(attrib["hydro"], 4),
        attrib_wb=round(attrib["wb"], 4),
        attrib_ops=round(attrib["ops"], 4),
        attrib_smolt=round(attrib["smolt"], 4),
        attrib_wild=round(attrib["wild"], 4),
        attrib_mutate=round(attrib["mutate"], 4),
    )
