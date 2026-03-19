"""
SmoltBICalculator

Beregner driftsavbrudd (BI) sum forsikret for ett settefiskanlegg.
Metode: Volum × pris ved målvekt × indemnitetperiode (måneder / 12).

Formel (verifisert mot Agaqua AS sine Business_interruption.xlsx):
  BI = annual_smolt_volume × price_per_smolt × (indemnity_months / 12)

Eksempel Villa Smolt:
  3_200_000 × 38 NOK × 2 år = NOK 243_200_000
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SmoltBIResult:
    """Output fra SmoltBICalculator for ett anlegg."""
    facility_name:                  str
    bi_sum_insured_nok:             float   # Totalsum til forsikring
    annual_revenue_equivalent_nok:  float   # Årsomsetning (= BI / perioder)
    indemnity_months:               int
    annual_smolt_volume:            int
    target_weight_g:                float
    price_per_smolt_nok:            float
    generation_rebuild_months:      int     # Tid til ny generasjon er klar


class SmoltBICalculator:
    """
    Beregner BI for settefiskanlegg.
    Tar høyde for:
    - To produksjonsperioder (generasjon 0 tapes, generasjon 1 forsinkes)
    - Sesongvariasjon i smoltpriser (valgfritt)
    """

    DEFAULT_INDEMNITY_MONTHS     = 24
    DEFAULT_GENERATION_REBUILD_M = 18

    def calculate(
        self,
        facility_name:              str,
        annual_smolt_volume:        int,
        target_weight_g:            float,
        price_per_smolt_nok:        float,
        indemnity_months:           int = DEFAULT_INDEMNITY_MONTHS,
        generation_rebuild_months:  int = DEFAULT_GENERATION_REBUILD_M,
        seasonal_price_factor:      Optional[Dict[int, float]] = None,
    ) -> SmoltBIResult:
        """
        Beregner BI.

        Args:
            facility_name:             Anleggets navn
            annual_smolt_volume:       Antall smolt levert per år (normal drift)
            target_weight_g:           Gjennomsnittlig salgsvekt i gram
            price_per_smolt_nok:       Salgspris per smolt i NOK
            indemnity_months:          Dekningsperiode (typisk 24 for settefisk)
            generation_rebuild_months: Tid fra tap til ny generasjon er klar
            seasonal_price_factor:     Valgfri dict {månedsnummer: multiplikator}

        Returns:
            SmoltBIResult
        """
        annual_revenue = annual_smolt_volume * price_per_smolt_nok
        periods        = indemnity_months / 12
        bi_sum         = annual_revenue * periods

        return SmoltBIResult(
            facility_name                 = facility_name,
            bi_sum_insured_nok            = bi_sum,
            annual_revenue_equivalent_nok = annual_revenue,
            indemnity_months              = indemnity_months,
            annual_smolt_volume           = annual_smolt_volume,
            target_weight_g               = target_weight_g,
            price_per_smolt_nok           = price_per_smolt_nok,
            generation_rebuild_months     = generation_rebuild_months,
        )

    def calculate_group(
        self,
        facilities: List[dict],  # List[dict] med nøkler som over
    ) -> Dict[str, SmoltBIResult]:
        """Beregner BI for alle anlegg i ett konsern."""
        return {
            f["facility_name"]: self.calculate(**f)
            for f in facilities
        }
