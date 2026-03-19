"""
SmoltGenerationTracker

Beregner gjennomsnittlig forsikringsverdi for biomasse i et settefiskanlegg
basert på parallelle generasjoner og månedlig tilvekstprofil.

Verdisetting: Interpolert fra bransjens vekttabell (NOK per fisk, 17 steg
fra 0.001g til 150g) — identisk med Agaqua AS sine egne beregninger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Department(str, Enum):
    HATCHERY    = "klekkeri"
    START_FEED  = "startforing"
    GROWTH      = "vekst"
    OUTDOOR_VAT = "utekar"
    RAS         = "ras"


# Forsikringsverditabell (gram → NOK per fisk)
# Kilde: Agaqua AS forsikringsverdi-skjema, bekreftet mot markedsnormer
WEIGHT_TO_VALUE_NOK: Dict[float, float] = {
    0.001: 2.5,
    0.002: 2.5,
    0.200: 2.5,
    1.0:   2.5,
    2.0:   5.0,
    5.0:   6.0,
    10.0:  7.0,
    20.0:  8.0,
    30.0:  8.5,
    40.0:  9.0,
    50.0:  10.0,
    60.0:  14.0,
    70.0:  15.0,
    100.0: 16.0,
    120.0: 17.0,
    135.0: 18.5,
    150.0: 20.0,
}

_SORTED_WEIGHTS: List[float] = sorted(WEIGHT_TO_VALUE_NOK.keys())


@dataclass
class GenerationMonth:
    """Biomassestatus for én generasjon i én måned."""
    count:         int
    avg_weight_g:  float

    @property
    def insured_value_nok(self) -> float:
        return self.count * self._lookup_value(self.avg_weight_g)

    @staticmethod
    def _lookup_value(weight_g: float) -> float:
        """
        Slår opp NOK-verdi fra WEIGHT_TO_VALUE_NOK.
        Bruker nærmeste støttepunkt (ikke lineær interpolasjon —
        i tråd med Agaqua-metodikk). Ved lik avstand velges laveste vekt.
        """
        if weight_g <= _SORTED_WEIGHTS[0]:
            return WEIGHT_TO_VALUE_NOK[_SORTED_WEIGHTS[0]]
        if weight_g >= _SORTED_WEIGHTS[-1]:
            return WEIGHT_TO_VALUE_NOK[_SORTED_WEIGHTS[-1]]
        nearest = min(_SORTED_WEIGHTS, key=lambda k: abs(k - weight_g))
        return WEIGHT_TO_VALUE_NOK[nearest]


@dataclass
class Generation:
    """
    En produksjonsgenerasjon med månedsprofil.
    Én linje per generasjon — f.eks. "1-2027 laks".
    """
    generation_id: str               # f.eks. "1-2027"
    species:       str               # "laks" | "ørret" | "regnbueørret"
    department:    Department
    # Månedsprofil: {måned_index: GenerationMonth} (0=Jan, 11=Des)
    monthly_data:  Dict[int, GenerationMonth] = field(default_factory=dict)


@dataclass
class FacilityGenerationProfile:
    """Alle generasjoner i ett anlegg for ett år."""
    facility_name: str
    year:          int
    generations:   List[Generation] = field(default_factory=list)

    def monthly_total_value_nok(self, month: int) -> float:
        """Sum av forsikringsverdier for alle aktive generasjoner i én måned."""
        return sum(
            gen.monthly_data[month].insured_value_nok
            for gen in self.generations
            if month in gen.monthly_data
        )

    def annual_average_value_nok(self) -> float:
        """
        Gjennomsnittlig stående forsikringsverdi gjennom året (12 måneder).
        Måneder uten aktiv biomasse (= 0) ekskluderes fra snittet.
        """
        monthly = [self.monthly_total_value_nok(m) for m in range(12)]
        active  = [v for v in monthly if v > 0]
        return sum(active) / len(active) if active else 0.0

    def peak_value_nok(self) -> float:
        """Høyeste månedlige forsikringsverdi i løpet av året."""
        return max(self.monthly_total_value_nok(m) for m in range(12))
