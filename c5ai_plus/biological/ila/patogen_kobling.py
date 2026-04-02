"""
c5ai_plus/biological/ila/patogen_kobling.py

Kobler ILA P_total fra MRE-1 inn i C5AI+ patogen-prior.

Overskriver statisk patogen-prior (0.10) med ILA-kalibrert verdi
når lokaliteten har en aktiv ILA-profil.

Brukes i c5ai_plus/pipeline.py steg 3 (probability model).
"""
from __future__ import annotations

from typing import Optional


def juster_patogen_prior(
    statisk_prior:  float,
    ila_p_total:    Optional[float],
    vekt:           float = 0.60,
) -> float:
    """
    Blander statisk prior med ILA P_total når ILA-data foreligger.

    Parameters
    ----------
    statisk_prior : eksisterende patogen-prior fra C5AI+ steg 3
    ila_p_total   : siste MRE-1 P_total (None = ingen ILA-profil)
    vekt          : ILA-andel i blandingen (default 0.60)

    Returns
    -------
    Justert prior, capped ved 0.70 som i eksisterende prior-logikk.
    Returnerer statisk_prior uendret hvis ila_p_total er None.
    """
    if ila_p_total is None:
        return statisk_prior
    blandet = vekt * ila_p_total + (1 - vekt) * statisk_prior
    return round(min(blandet, 0.70), 4)
