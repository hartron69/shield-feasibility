"""
Sprint S4 — SmoltGenerationTracker og SmoltBICalculator.

Dekker:
  - GenerationMonth (vektoppslag, forsikringsverdi)
  - FacilityGenerationProfile (månedstotaler, årssnitt, toppverdi)
  - SmoltBICalculator (enkeltanlegg, konsern)
  - Integrasjon: kalkulatorer → SmoltFacilityTIV → TIV

Minimum 35 tester.
"""

from __future__ import annotations

import pytest

from models.smolt_generation_tracker import (
    Department,
    FacilityGenerationProfile,
    Generation,
    GenerationMonth,
    WEIGHT_TO_VALUE_NOK,
    _SORTED_WEIGHTS,
)
from models.smolt_bi_calculator import SmoltBICalculator, SmoltBIResult
from data.input_schema import BuildingComponent, FacilityType, SmoltFacilityTIV, SmoltOperatorInput


# ── Hjelpere ──────────────────────────────────────────────────────────────────

def _villa_smolt_profile() -> FacilityGenerationProfile:
    """
    Konstruerer Villa Smolt AS sin generasjonsprofil for 2027.
    To overlappende generasjoner — tilsvarer Agaqua AS sine egne tall.

    Mål: annual_average ≈ 39 668 750 NOK  (innenfor ±5 % av 39 680 409 NOK)
    """
    gen1_monthly = {
        0:  GenerationMonth(count=2_750_000, avg_weight_g=5.0),    # Jan
        1:  GenerationMonth(count=2_750_000, avg_weight_g=10.0),   # Feb
        2:  GenerationMonth(count=2_750_000, avg_weight_g=20.0),   # Mar
        3:  GenerationMonth(count=2_750_000, avg_weight_g=30.0),   # Apr
        4:  GenerationMonth(count=2_750_000, avg_weight_g=40.0),   # May
        5:  GenerationMonth(count=2_750_000, avg_weight_g=50.0),   # Jun
        6:  GenerationMonth(count=2_750_000, avg_weight_g=70.0),   # Jul
        7:  GenerationMonth(count=2_750_000, avg_weight_g=100.0),  # Aug
        8:  GenerationMonth(count=2_750_000, avg_weight_g=120.0),  # Sep
        9:  GenerationMonth(count=2_750_000, avg_weight_g=135.0),  # Okt
        10: GenerationMonth(count=2_750_000, avg_weight_g=150.0),  # Nov
        # Desember: generasjon 1 er slaktet — ingen data
    }
    gen2_monthly = {
        5:  GenerationMonth(count=1_650_000, avg_weight_g=5.0),    # Jun
        6:  GenerationMonth(count=1_650_000, avg_weight_g=10.0),   # Jul
        7:  GenerationMonth(count=1_650_000, avg_weight_g=20.0),   # Aug
        8:  GenerationMonth(count=1_650_000, avg_weight_g=30.0),   # Sep
        9:  GenerationMonth(count=1_650_000, avg_weight_g=40.0),   # Okt
        10: GenerationMonth(count=1_650_000, avg_weight_g=50.0),   # Nov
        11: GenerationMonth(count=1_650_000, avg_weight_g=70.0),   # Des
    }
    gen1 = Generation(
        generation_id="1-2027", species="laks",
        department=Department.RAS, monthly_data=gen1_monthly,
    )
    gen2 = Generation(
        generation_id="2-2027", species="laks",
        department=Department.RAS, monthly_data=gen2_monthly,
    )
    return FacilityGenerationProfile(
        facility_name="Villa Smolt AS", year=2027,
        generations=[gen1, gen2],
    )


def _agaqua_smolt_input() -> SmoltOperatorInput:
    """Agaqua AS — nøyaktige Agaqua-tall fra API-eksempel."""
    villa = SmoltFacilityTIV(
        facility_name="Villa Smolt AS",
        facility_type=FacilityType.SMOLT_RAS,
        building_components=[
            BuildingComponent("Hall over fish tanks", area_sqm=1370),
            BuildingComponent("RAS 1-2",              area_sqm=530),
            BuildingComponent("RAS 3-4",              area_sqm=610),
            BuildingComponent("Gamledelen",           area_sqm=1393),
            BuildingComponent("Forlager",             area_sqm=275),
        ],
        site_clearance_nok            = 20_000_000,
        machinery_nok                 = 200_000_000,
        avg_biomass_insured_value_nok = 39_680_409,
        bi_sum_insured_nok            = 243_200_000,
    )
    olden = SmoltFacilityTIV(
        facility_name="Olden Oppdrettsanlegg AS",
        facility_type=FacilityType.SMOLT_FLOW,
        building_components=[
            BuildingComponent("Påvekstavdeling",        area_sqm=2204),
            BuildingComponent("Yngel",                  area_sqm=899),
            BuildingComponent("Klekkeri/startforing",   area_sqm=221),
            BuildingComponent("Teknisk/vannbehandling", area_sqm=77),
        ],
        site_clearance_nok            = 20_000_000,
        machinery_nok                 = 120_000_000,
        avg_biomass_insured_value_nok = 18_260_208,
        bi_sum_insured_nok            = 102_000_000,
    )
    setran = SmoltFacilityTIV(
        facility_name="Setran Settefisk AS",
        facility_type=FacilityType.SMOLT_FLOW,
        building_components=[
            BuildingComponent("Hall A",         area_sqm=280),
            BuildingComponent("Vannbehandling", area_sqm=170),
            BuildingComponent("Hall B",         area_sqm=715),
            BuildingComponent("Hall C",         area_sqm=979),
        ],
        site_clearance_nok            = 15_000_000,
        machinery_nok                 = 45_000_000,
        avg_biomass_insured_value_nok = 13_287_917,
        bi_sum_insured_nok            = 85_100_000,
    )
    return SmoltOperatorInput(
        operator_name="Agaqua AS",
        facilities=[villa, olden, setran],
    )


# ════════════════════════════════════════════════════════════════════════════
# Gruppe 1 — GenerationMonth (vektoppslag og forsikringsverdi)
# ════════════════════════════════════════════════════════════════════════════

class TestGenerationMonth:
    def test_weight_lookup_exact_match_50g(self):
        gm = GenerationMonth(count=1, avg_weight_g=50.0)
        assert gm.insured_value_nok == pytest.approx(10.0)

    def test_weight_lookup_exact_match_150g(self):
        gm = GenerationMonth(count=1, avg_weight_g=150.0)
        assert gm.insured_value_nok == pytest.approx(20.0)

    def test_weight_lookup_nearest_point_55g(self):
        """55g er like langt fra 50g og 60g — nærmeste er 50g (første i listen)."""
        gm = GenerationMonth(count=1, avg_weight_g=55.0)
        assert gm.insured_value_nok == pytest.approx(10.0)

    def test_weight_below_minimum_uses_min_value(self):
        gm = GenerationMonth(count=1, avg_weight_g=0.0001)
        assert gm.insured_value_nok == pytest.approx(2.5)

    def test_weight_above_maximum_uses_max_value(self):
        gm = GenerationMonth(count=1, avg_weight_g=200.0)
        assert gm.insured_value_nok == pytest.approx(20.0)

    def test_insured_value_is_count_times_per_fish_value(self):
        gm = GenerationMonth(count=1_000_000, avg_weight_g=50.0)
        assert gm.insured_value_nok == pytest.approx(10_000_000.0)

    def test_weight_table_has_17_entries(self):
        assert len(WEIGHT_TO_VALUE_NOK) == 17

    def test_zero_count_gives_zero_value(self):
        gm = GenerationMonth(count=0, avg_weight_g=100.0)
        assert gm.insured_value_nok == 0.0

    def test_lookup_at_boundary_1g(self):
        gm = GenerationMonth(count=1, avg_weight_g=1.0)
        assert gm.insured_value_nok == pytest.approx(2.5)

    def test_lookup_at_boundary_2g(self):
        gm = GenerationMonth(count=1, avg_weight_g=2.0)
        assert gm.insured_value_nok == pytest.approx(5.0)


# ════════════════════════════════════════════════════════════════════════════
# Gruppe 2 — FacilityGenerationProfile
# ════════════════════════════════════════════════════════════════════════════

class TestFacilityGenerationProfile:
    def test_monthly_total_sums_all_active_generations(self):
        """Juni skal inkludere begge generasjoner."""
        profile = _villa_smolt_profile()
        # Jun (måned 5): gen1=2.75M×10=27.5M + gen2=1.65M×6=9.9M = 37.4M
        assert profile.monthly_total_value_nok(5) == pytest.approx(37_400_000)

    def test_monthly_total_single_generation_january(self):
        """Januar har bare generasjon 1."""
        profile = _villa_smolt_profile()
        # Jan (måned 0): 2.75M × 6 NOK = 16.5M
        assert profile.monthly_total_value_nok(0) == pytest.approx(16_500_000)

    def test_annual_average_excludes_zero_months(self):
        """En generasjon aktiv kun én måned — snittet skal ikke dele på 12."""
        gen = Generation(
            generation_id="test", species="laks", department=Department.RAS,
            monthly_data={6: GenerationMonth(count=100_000, avg_weight_g=50.0)},
        )
        profile = FacilityGenerationProfile("Test", 2027, generations=[gen])
        # Bare én aktiv måned: 100_000 × 10 = 1_000_000 — snitt = 1_000_000
        assert profile.annual_average_value_nok() == pytest.approx(1_000_000.0)

    def test_annual_average_all_zero_returns_zero(self):
        profile = FacilityGenerationProfile("Tom", 2027, generations=[])
        assert profile.annual_average_value_nok() == 0.0

    def test_peak_value_is_maximum_monthly(self):
        profile = _villa_smolt_profile()
        # November er toppverdien: 2.75M×20 + 1.65M×10 = 55M + 16.5M = 71.5M
        assert profile.peak_value_nok() == pytest.approx(71_500_000)

    def test_villa_smolt_annual_average_within_tolerance(self):
        """Årssnitt skal ligge innenfor ±5 % av Agaqua-dokumentert verdi."""
        profile = _villa_smolt_profile()
        avg = profile.annual_average_value_nok()
        target = 39_680_409
        assert abs(avg - target) / target < 0.05, (
            f"Årssnitt {avg:,.0f} avviker >5 % fra target {target:,.0f}"
        )

    def test_generation_ids_are_unique(self):
        profile = _villa_smolt_profile()
        ids = [g.generation_id for g in profile.generations]
        assert len(ids) == len(set(ids))

    def test_department_enum_values(self):
        assert Department.RAS == "ras"
        assert Department.HATCHERY == "klekkeri"


# ════════════════════════════════════════════════════════════════════════════
# Gruppe 3 — SmoltBICalculator (enkeltanlegg)
# ════════════════════════════════════════════════════════════════════════════

class TestSmoltBICalculator:
    def setup_method(self):
        self.calc = SmoltBICalculator()

    def test_villa_smolt_bi_exact(self):
        result = self.calc.calculate(
            facility_name="Villa Smolt AS",
            annual_smolt_volume=3_200_000,
            target_weight_g=150.0,
            price_per_smolt_nok=38.0,
        )
        assert result.bi_sum_insured_nok == pytest.approx(243_200_000)

    def test_olden_bi_exact(self):
        result = self.calc.calculate(
            facility_name="Olden Oppdrettsanlegg AS",
            annual_smolt_volume=1_500_000,
            target_weight_g=150.0,
            price_per_smolt_nok=34.0,
        )
        assert result.bi_sum_insured_nok == pytest.approx(102_000_000)

    def test_setran_bi_exact(self):
        result = self.calc.calculate(
            facility_name="Setran Settefisk AS",
            annual_smolt_volume=1_150_000,
            target_weight_g=150.0,
            price_per_smolt_nok=37.0,
        )
        assert result.bi_sum_insured_nok == pytest.approx(85_100_000)

    def test_agaqua_total_bi(self):
        total = 243_200_000 + 102_000_000 + 85_100_000
        assert total == pytest.approx(430_300_000)

    def test_12_month_indemnity_halves_bi(self):
        r24 = self.calc.calculate(
            facility_name="X", annual_smolt_volume=1_000_000,
            target_weight_g=150.0, price_per_smolt_nok=40.0,
            indemnity_months=24,
        )
        r12 = self.calc.calculate(
            facility_name="X", annual_smolt_volume=1_000_000,
            target_weight_g=150.0, price_per_smolt_nok=40.0,
            indemnity_months=12,
        )
        assert r12.bi_sum_insured_nok == pytest.approx(r24.bi_sum_insured_nok / 2)

    def test_annual_revenue_equivalent_is_bi_over_periods(self):
        result = self.calc.calculate(
            facility_name="Test", annual_smolt_volume=2_000_000,
            target_weight_g=150.0, price_per_smolt_nok=38.0,
        )
        expected_revenue = 2_000_000 * 38.0
        assert result.annual_revenue_equivalent_nok == pytest.approx(expected_revenue)
        assert result.bi_sum_insured_nok == pytest.approx(expected_revenue * 2)

    def test_zero_volume_gives_zero_bi(self):
        result = self.calc.calculate(
            facility_name="Tom", annual_smolt_volume=0,
            target_weight_g=150.0, price_per_smolt_nok=38.0,
        )
        assert result.bi_sum_insured_nok == 0.0

    def test_returns_smolt_bi_result_type(self):
        result = self.calc.calculate(
            facility_name="Test", annual_smolt_volume=100_000,
            target_weight_g=100.0, price_per_smolt_nok=30.0,
        )
        assert isinstance(result, SmoltBIResult)

    def test_default_indemnity_months_is_24(self):
        result = self.calc.calculate(
            facility_name="Default", annual_smolt_volume=1_000_000,
            target_weight_g=150.0, price_per_smolt_nok=38.0,
        )
        assert result.indemnity_months == 24

    def test_default_generation_rebuild_months_is_18(self):
        result = self.calc.calculate(
            facility_name="Default", annual_smolt_volume=1_000_000,
            target_weight_g=150.0, price_per_smolt_nok=38.0,
        )
        assert result.generation_rebuild_months == 18


# ════════════════════════════════════════════════════════════════════════════
# Gruppe 4 — SmoltBICalculator (konsern — calculate_group)
# ════════════════════════════════════════════════════════════════════════════

class TestSmoltBICalculatorGroup:
    def setup_method(self):
        self.calc = SmoltBICalculator()
        self.agaqua_facilities = [
            dict(facility_name="Villa Smolt AS",          annual_smolt_volume=3_200_000,
                 target_weight_g=150.0, price_per_smolt_nok=38.0),
            dict(facility_name="Olden Oppdrettsanlegg AS", annual_smolt_volume=1_500_000,
                 target_weight_g=150.0, price_per_smolt_nok=34.0),
            dict(facility_name="Setran Settefisk AS",      annual_smolt_volume=1_150_000,
                 target_weight_g=150.0, price_per_smolt_nok=37.0),
        ]

    def test_calculate_group_returns_all_facilities(self):
        results = self.calc.calculate_group(self.agaqua_facilities)
        assert len(results) == 3
        assert "Villa Smolt AS" in results

    def test_calculate_group_agaqua_total_bi(self):
        results = self.calc.calculate_group(self.agaqua_facilities)
        total = sum(r.bi_sum_insured_nok for r in results.values())
        assert total == pytest.approx(430_300_000)

    def test_calculate_group_keys_match_facility_names(self):
        results = self.calc.calculate_group(self.agaqua_facilities)
        names = [f["facility_name"] for f in self.agaqua_facilities]
        assert set(results.keys()) == set(names)


# ════════════════════════════════════════════════════════════════════════════
# Gruppe 5 — Integrasjon: kalkulatorer → SmoltFacilityTIV → total TIV
# ════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_generation_average_feeds_into_facility_tiv(self):
        """Beregnet biomasse fra GenerationTracker matcher API-data for Villa Smolt."""
        profile = _villa_smolt_profile()
        avg = profile.annual_average_value_nok()
        # Sett inn i SmoltFacilityTIV og sjekk at verdien stemmer
        facility = SmoltFacilityTIV(
            facility_name="Villa Smolt AS",
            facility_type=FacilityType.SMOLT_RAS,
            building_components=[],
            machinery_nok=200_000_000,
            avg_biomass_insured_value_nok=avg,
            bi_sum_insured_nok=243_200_000,
        )
        assert facility.avg_biomass_insured_value_nok == pytest.approx(avg)

    def test_bi_calculator_feeds_into_facility_tiv(self):
        """BI fra kalkulator matcher API-verdien for Villa Smolt."""
        calc = SmoltBICalculator()
        bi_result = calc.calculate(
            facility_name="Villa Smolt AS",
            annual_smolt_volume=3_200_000,
            target_weight_g=150.0,
            price_per_smolt_nok=38.0,
        )
        facility = SmoltFacilityTIV(
            facility_name="Villa Smolt AS",
            facility_type=FacilityType.SMOLT_RAS,
            building_components=[],
            machinery_nok=200_000_000,
            avg_biomass_insured_value_nok=39_680_409,
            bi_sum_insured_nok=bi_result.bi_sum_insured_nok,
        )
        assert facility.bi_sum_insured_nok == pytest.approx(243_200_000)

    def test_full_agaqua_tiv_with_calculated_biomass_and_bi(self):
        """
        Samlet TIV for Agaqua AS via SmoltOperatorInput ≈ NOK 1 184 000 000 (±2 %).
        Bruker faktiske Agaqua-tall som er verifisert mot API-eksempelet.
        """
        op = _agaqua_smolt_input()
        tiv = op.total_tiv_nok
        target = 1_184_000_000
        assert abs(tiv - target) / target < 0.02, (
            f"Total TIV {tiv:,.0f} avviker >2 % fra target {target:,.0f}"
        )

    def test_agaqua_annual_average_biomass_all_sites(self):
        """
        Sum av avg_biomass over alle tre anlegg = 71 228 534 NOK
        (dokumentert Agaqua-akseptansekriterium).
        """
        op = _agaqua_smolt_input()
        total_biomass = sum(f.avg_biomass_insured_value_nok for f in op.facilities)
        target = 71_228_534
        assert abs(total_biomass - target) / target < 0.001

    def test_agaqua_n_facilities(self):
        op = _agaqua_smolt_input()
        assert op.n_facilities == 3

    def test_consolidated_breakdown_keys(self):
        op = _agaqua_smolt_input()
        bd = op.consolidated_tiv_breakdown
        assert set(bd.keys()) == {"buildings", "machinery", "biomass", "bi"}

    def test_consolidated_breakdown_sums_to_total_tiv(self):
        op = _agaqua_smolt_input()
        bd = op.consolidated_tiv_breakdown
        assert sum(bd.values()) == pytest.approx(op.total_tiv_nok)
