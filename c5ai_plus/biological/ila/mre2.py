"""
c5ai_plus/biological/ila/mre2.py

MRE-2 Ukentlig SEIR hazard-modell for ILA-risiko.

Portert fra /reference/mre2_progression.py :: run_mre2()
SEIR: S→E→I→R med ukentlig hazard λ_i(t).

λ_i(t) = λ_intro(t) + λ_amp(t) + λ_hydro(t)
p_i(t) = 1 − exp(−λ_i(t))
P_i(0,T) = 1 − ∏_{t=1}^{T} (1 − p_i(t))

SEIR per lokalitet:
  S[t+1] = S[t] − p_t·S[t]
  E[t+1] = E[t] + p_t·S[t] − σ·E[t]      σ = 1/3 uke⁻¹
  I[t+1] = I[t] + σ·E[t] − ρ·I[t]        ρ = 1/10 uke⁻¹
  R[t+1] = R[t] + ρ·I[t]

INVARIANTER (testet i test_mre2.py):
  - S + E + I + R = 1.0 etter hvert steg
  - P_kumulativ er monotont stigende
  - P_kumulativ(uke=1) > 0 og < 1 for realistiske parametere
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List


SIGMA: float = 1 / 3   # E→I overgangsrate (uke⁻¹) — uendret fra referanse
RHO:   float = 1 / 10  # I→R overgangsrate (uke⁻¹) — uendret fra referanse


# ── Per-uke dataklasse ───────────────────────────────────────────────────────

@dataclass
class SEIRUke:
    """SEIR-tilstand for én uke."""
    uke_nr:        int
    s:             float
    e:             float
    i:             float
    r:             float
    lambda_intro:  float
    lambda_amp:    float
    lambda_hydro:  float
    p_uke:         float
    p_kumulativ:   float
    varselniva:    str

    def to_dict(self) -> Dict:
        return {
            "uke_nr":       self.uke_nr,
            "s":            self.s,
            "e":            self.e,
            "i":            self.i,
            "r":            self.r,
            "lambda_intro": self.lambda_intro,
            "lambda_amp":   self.lambda_amp,
            "lambda_hydro": self.lambda_hydro,
            "p_uke":        self.p_uke,
            "p_kumulativ":  self.p_kumulativ,
            "varselniva":   self.varselniva,
        }


# ── Beregningskjerne ─────────────────────────────────────────────────────────

def kjor_mre2(
    sesong_uker:       int   = 52,
    intro_rate_base:   float = 0.002,
    amp_faktor:        float = 1.0,
    hydro_faktor:      float = 0.5,
    hpr0_tetthet:      float = 0.25,
    e0:                float = 0.0,
) -> List[SEIRUke]:
    """
    Port av run_mre2() fra /reference/mre2_progression.py

    Beregner 52-ukers SEIR-forløp med ukentlig hazard.
    Returnerer en SEIRUke per uke i sesongen.

    Parameters
    ----------
    sesong_uker     : antall uker (default 52)
    intro_rate_base : grunnrate for introduksjonshazard
    amp_faktor      : forsterker hazard fra infisert biomasse (I-fraksjon)
    hydro_faktor    : hydrodynamisk hazard-multiplikator
    hpr0_tetthet    : HPR0-tetthet 0–1
    e0              : initial eksponert-fraksjon (0 = sesongstart)
    """
    S, E, I, R = 1.0 - e0, e0, 0.0, 0.0
    p_kum  = 0.0
    resultat: List[SEIRUke] = []

    for uke in range(1, sesong_uker + 1):
        # Hazard-ledd (identisk med referanse)
        lambda_intro = intro_rate_base * hpr0_tetthet
        lambda_amp   = amp_faktor * I * 2.5
        lambda_hydro = hydro_faktor * hpr0_tetthet * 0.3

        lambda_total = lambda_intro + lambda_amp + lambda_hydro
        p_uke = 1 - math.exp(-lambda_total)

        # SEIR-steg
        ny_eksponert = p_uke * S
        S_ny = S - ny_eksponert
        E_ny = E + ny_eksponert - SIGMA * E
        I_ny = I + SIGMA * E - RHO * I
        R_ny = R + RHO * I

        # Numerisk korreksjon — summer skal være 1.0
        total = S_ny + E_ny + I_ny + R_ny
        S, E, I, R = S_ny / total, E_ny / total, I_ny / total, R_ny / total

        # Kumulativ sesong-risiko: P_i(0,t) = 1 − ∏(1 − p_k) for k=1..t
        p_kum = 1 - (1 - p_kum) * (1 - p_uke)

        varselniva = (
            "ILA04" if p_kum >= 0.80 else
            "ILA03" if p_kum >= 0.50 else
            "ILA02" if p_kum >= 0.20 else
            "ILA01" if p_kum >= 0.05 else
            "GRØNN"
        )

        resultat.append(SEIRUke(
            uke_nr=uke,
            s=round(S, 6),
            e=round(E, 6),
            i=round(I, 6),
            r=round(R, 6),
            lambda_intro=round(lambda_intro, 6),
            lambda_amp=round(lambda_amp, 6),
            lambda_hydro=round(lambda_hydro, 6),
            p_uke=round(p_uke, 6),
            p_kumulativ=round(p_kum, 6),
            varselniva=varselniva,
        ))

    return resultat
