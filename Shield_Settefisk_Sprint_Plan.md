# Shield Risk Platform — Settefisk Extension
## Complete Sprint Plan for Claude Code
**Dato:** Mars 2026 | **Versjon:** 1.0 | **Status:** Klar til utførelse

---

## Kontekst og mål

Plattformen er i dag bygget for **sjøoppdrett**. Kjerne-TIV-kalkulatoren
bruker `biomass_value_per_tonne` som eneste inngangspunkt — men for
settefisk (landbasert smolt) utgjør biomasse kun ~6–9 % av TIV.
Dominerende poster er RAS-infrastruktur (30 %), bygg (22 %) og
driftsavbrudd (36 %). Kjøres et settefiskkonsern gjennom dagens modell
gir den feil TIV, feil SCR og feil egnethetscore.

**Disse fem sprintene** gjør plattformen settefisk-klar uten å bryte
eksisterende sjøoppdrett-funksjonalitet. Alle endringer er additive.
Eksisterende testsuit (1 092 tester, 0 feilet) skal bestå umodifisert
etter hver sprint.

---

## Sprint-oversikt

| Sprint | Navn | Arbeidsomfang | Prioritet |
|--------|------|---------------|-----------|
| S1 | Settefisk TIV-modell og operator-builder | Backend — ny datamodell | 🔴 Kritisk |
| S2 | RAS-risikodomener og Monte Carlo-kalibering | Backend — ny risikomodell | 🔴 Kritisk |
| S3 | Settefisk C5AI+ forecasters | Backend — ny biologisk intelligens | 🟡 Viktig |
| S4 | Generasjonstracker og BI-kalkulator | Backend — ny forretningslogikk | 🟡 Viktig |
| S5 | Frontend — settefisk-modus i GUI | Frontend — ny UI-flyt | 🟢 Ønsket |

---

---

# SPRINT S1 — Settefisk TIV-modell og operator-builder

**Mål:** Plattformen aksepterer settefisk-spesifikk input og beregner
korrekt TIV fordelt på bygg, maskiner/RAS, biomasse og BI.

---

## S1.1 — Ny datamodell: `SmoltFacilityProfile`

**Fil:** `data/input_schema.py`

Legg til følgende dataclasses **etter** eksisterende `SiteProfile`:

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

class FacilityType(str, Enum):
    SEA_BASED   = "sea_based"
    SMOLT_RAS   = "smolt_ras"          # Resirkuleringsanlegg
    SMOLT_FLOW  = "smolt_flow"         # Gjennomstrøm
    SMOLT_HYBRID = "smolt_hybrid"      # RAS + gjennomstrøm

@dataclass
class BuildingComponent:
    """Enkelt bygningsdeldelement med areal og verdi per m²."""
    name: str                          # f.eks. "Hall over fish tanks"
    area_sqm: float
    value_per_sqm_nok: float = 27_000  # Bransjesnitt norsk settefisk 2024
    notes: Optional[str] = None

    @property
    def insured_value_nok(self) -> float:
        return self.area_sqm * self.value_per_sqm_nok

@dataclass
class SmoltFacilityTIV:
    """
    Full TIV-spesifikasjon for ett landbasert settefiskanlegg.
    Alle beløp i NOK.
    """
    facility_name: str
    facility_type: FacilityType = FacilityType.SMOLT_RAS

    # Bygg
    building_components: List[BuildingComponent] = field(default_factory=list)
    site_clearance_nok: float = 0.0        # Rydding branntomt

    # Maskiner og teknologi
    machinery_nok: float = 0.0             # RAS-system, pumper, kar, teknologi
    machinery_notes: Optional[str] = None

    # Biomasse — se GenerationProfile i Sprint S4
    # Her brukes gjennomsnittlig forsikringsverdi for cellen
    avg_biomass_insured_value_nok: float = 0.0

    # Driftsavbrudd — se SmoltBICalculator i Sprint S4
    # Her legges beregnet BI-sum fra kalkulatoren
    bi_sum_insured_nok: float = 0.0
    bi_indemnity_months: int = 24

    # Geografisk plassering
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    municipality: Optional[str] = None

    @property
    def building_total_nok(self) -> float:
        return sum(b.insured_value_nok for b in self.building_components) + self.site_clearance_nok

    @property
    def property_total_nok(self) -> float:
        """Bygg + maskiner."""
        return self.building_total_nok + self.machinery_nok

    @property
    def total_tiv_nok(self) -> float:
        return (self.property_total_nok
                + self.avg_biomass_insured_value_nok
                + self.bi_sum_insured_nok)

    @property
    def tiv_breakdown(self) -> Dict[str, float]:
        return {
            "buildings":  self.building_total_nok,
            "machinery":  self.machinery_nok,
            "biomass":    self.avg_biomass_insured_value_nok,
            "bi":         self.bi_sum_insured_nok,
        }

    @property
    def tiv_shares(self) -> Dict[str, float]:
        total = self.total_tiv_nok
        if total == 0:
            return {k: 0.0 for k in self.tiv_breakdown}
        return {k: v / total for k, v in self.tiv_breakdown.items()}


@dataclass
class SmoltOperatorInput:
    """
    Fullt input-objekt for et settefiskkonsern med ett eller flere anlegg.
    Erstatter OperatorInput for facility_type != SEA_BASED.
    """
    operator_name: str
    org_number: Optional[str] = None
    facilities: List[SmoltFacilityTIV] = field(default_factory=list)

    # Finansielle data (fra årsregnskap)
    annual_revenue_nok: Optional[float] = None
    ebitda_nok: Optional[float] = None
    equity_nok: Optional[float] = None
    operating_cf_nok: Optional[float] = None
    liquidity_nok: Optional[float] = None

    # Skadehistorikk
    claims_history_years: int = 0          # Antall skadefrie år
    total_claims_paid_nok: float = 0.0

    # Eksisterende forsikring
    current_market_premium_nok: Optional[float] = None
    current_insurer: Optional[str] = None
    current_bi_indemnity_months: Optional[int] = None

    @property
    def total_tiv_nok(self) -> float:
        return sum(f.total_tiv_nok for f in self.facilities)

    @property
    def n_facilities(self) -> int:
        return len(self.facilities)

    @property
    def consolidated_tiv_breakdown(self) -> Dict[str, float]:
        result = {"buildings": 0.0, "machinery": 0.0, "biomass": 0.0, "bi": 0.0}
        for f in self.facilities:
            for k, v in f.tiv_breakdown.items():
                result[k] += v
        return result
```

---

## S1.2 — Ny builder: `SmoltOperatorBuilder`

**Fil:** `backend/services/smolt_operator_builder.py` (ny fil)

```python
"""
SmoltOperatorBuilder

Konverterer SmoltOperatorInput → (OperatorInput, AllocationSummary)
slik at resten av PCC-pipeline (Monte Carlo, SCR, suitability) kan
kjøres uendret på settefisk-data.

Nøkkelforskjeller fra sjøbasert OperatorBuilder:
- TIV er bygd opp fra komponentene, ikke fra biomasse × pris/tonn
- Risk severity skalerer mot maskin+bygg TIV (ikke biomasse TIV)
- BI-posten dominerer som trigger for katastrofetap, ikke biomasse
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Optional

from data.input_schema import OperatorInput, AllocationSummary, SmoltOperatorInput


@dataclass
class SmoltAllocationSummary:
    """Utvidet AllocationSummary med settefisk-spesifikke felter."""
    # Arvede felter fra AllocationSummary
    total_tiv_nok: float
    biomass_share: float
    property_share: float
    bi_share: float
    # Nye settefisk-felter
    machinery_share: float
    building_share: float
    n_facilities: int
    facility_names: list
    consolidated_breakdown: dict
    # Finansielle nøkkeltall
    scr_capacity_ratio: float       # operating_cf / estimated_base_scr
    liquidity_post_scr_nok: float   # likvider etter antatt SCR-innbetaling


class SmoltOperatorBuilder:
    """
    Bygger OperatorInput fra SmoltOperatorInput.

    Tilnærming:
    1. Beregn total TIV og komponentfordeling
    2. Utled risikoparametre basert på TIV-profil og historikk
    3. Sett finansielle ratioer fra faktiske regnskapsdata
    4. Returner (OperatorInput, SmoltAllocationSummary)
    """

    # Standard risikoparametre for norsk settefisk (kalibrert fra markedsdata)
    SMOLT_BASE_LOSS_FREQUENCY  = 0.08   # Forventet ant. hendelser/år (skadefri profil)
    SMOLT_BASE_SEVERITY_FACTOR = 0.035  # Forventet tap som % av property TIV
    SMOLT_CAT_PROBABILITY      = 0.03   # Sannsynlighet for katastrofehendelse/år
    SMOLT_CAT_MULTIPLIER       = 4.5    # Katastrofetap × normal forventet tap

    # RI-defaults for settefisk
    DEFAULT_RI_RETENTION_SHARE = 0.01   # 1 % av total TIV som default retention
    DEFAULT_RI_LIMIT_SHARE     = 0.25   # 25 % av total TIV som RI-kapasitet
    DEFAULT_RI_LOADING         = 1.75   # Base preset

    def build(
        self,
        smolt_input: SmoltOperatorInput,
        estimated_market_premium_nok: Optional[float] = None,
    ) -> Tuple[OperatorInput, SmoltAllocationSummary]:
        """
        Hovedmetode. Returnerer OperatorInput klar for PCC-pipeline
        og SmoltAllocationSummary for rapportering.

        Args:
            smolt_input: Fylt SmoltOperatorInput
            estimated_market_premium_nok: Howden-indikasjon hvis tilgjengelig;
                ellers estimert fra TIV-rater

        Returns:
            (OperatorInput, SmoltAllocationSummary)
        """
        tiv = smolt_input.total_tiv_nok
        breakdown = smolt_input.consolidated_tiv_breakdown
        prop_tiv = breakdown["buildings"] + breakdown["machinery"]
        bi_tiv   = breakdown["bi"]
        bio_tiv  = breakdown["biomass"]

        # --- Premie ---
        if estimated_market_premium_nok:
            premium = estimated_market_premium_nok
        else:
            # Estimat basert på standard rater
            prop_prem = prop_tiv   * 0.0042   # 0.42 % property rate
            bi_prem   = (bi_tiv / 2) * 0.007  # 0.70 % av BI per år
            bio_prem  = bio_tiv  * 0.025       # 2.50 % biomasse
            premium   = prop_prem + bi_prem + bio_prem

        # --- Risikoparametere — justert for skadehistorikk ---
        history_discount = self._history_discount(smolt_input.claims_history_years)
        base_loss_freq   = self.SMOLT_BASE_LOSS_FREQUENCY * history_discount
        base_severity    = prop_tiv * self.SMOLT_BASE_SEVERITY_FACTOR

        # --- Finansielle ratioer ---
        revenue = smolt_input.annual_revenue_nok or (tiv * 0.20)
        equity  = smolt_input.equity_nok          or (tiv * 0.10)
        op_cf   = smolt_input.operating_cf_nok    or (revenue * 0.18)
        liquid  = smolt_input.liquidity_nok        or (revenue * 0.08)
        ebitda  = smolt_input.ebitda_nok           or (revenue * 0.22)

        # --- RI-struktur ---
        retention = max(tiv * self.DEFAULT_RI_RETENTION_SHARE, 5_000_000)
        ri_limit  = tiv * self.DEFAULT_RI_LIMIT_SHARE

        # --- OperatorInput ---
        op_input = OperatorInput(
            name                    = smolt_input.operator_name,
            country                 = "Norway",
            n_sites                 = smolt_input.n_facilities,
            total_tiv_nok           = tiv,
            annual_revenue_nok      = revenue,
            annual_premium_nok      = premium,
            ebitda_nok              = ebitda,
            equity_nok              = equity,
            fcf_nok                 = op_cf,
            total_assets_nok        = smolt_input.equity_nok or tiv * 0.35,
            expected_annual_events  = base_loss_freq * smolt_input.n_facilities,
            mean_loss_severity_nok  = base_severity,
            cv_loss_severity        = 0.65,           # Lavere enn sjø (kontrollert miljø)
            catastrophe_probability = self.SMOLT_CAT_PROBABILITY,
            catastrophe_multiplier  = self.SMOLT_CAT_MULTIPLIER,
            inter_site_correlation  = 0.10,           # Lav — separate nedbørsfelt
            bi_daily_revenue_nok    = revenue / 365,
            bi_avg_interruption_days= 90,
            # RI
            retention_nok           = retention,
            ri_limit_nok            = ri_limit,
            ri_loading_factor       = self.DEFAULT_RI_LOADING,
            facility_type           = "smolt",
        )

        # --- SCR-kapasitetsanalyse ---
        est_scr  = op_input.total_tiv_nok * 0.015   # Grovestimat: 1.5 % av TIV
        scr_cap  = op_cf / est_scr if est_scr > 0 else 0
        liq_post = liquid - est_scr

        alloc = SmoltAllocationSummary(
            total_tiv_nok           = tiv,
            biomass_share           = bio_tiv  / tiv if tiv else 0,
            property_share          = prop_tiv / tiv if tiv else 0,
            bi_share                = bi_tiv   / tiv if tiv else 0,
            machinery_share         = breakdown["machinery"] / tiv if tiv else 0,
            building_share          = breakdown["buildings"] / tiv if tiv else 0,
            n_facilities            = smolt_input.n_facilities,
            facility_names          = [f.facility_name for f in smolt_input.facilities],
            consolidated_breakdown  = breakdown,
            scr_capacity_ratio      = scr_cap,
            liquidity_post_scr_nok  = liq_post,
        )

        return op_input, alloc

    # ------------------------------------------------------------------ #
    @staticmethod
    def _history_discount(years_claims_free: int) -> float:
        """
        Rabattfaktor på tapsfrekvens basert på skadefri historikk.
        10 år skadefri → 35 % reduksjon i antatt frekvens.
        """
        if years_claims_free <= 0:  return 1.00
        if years_claims_free <= 2:  return 0.92
        if years_claims_free <= 4:  return 0.85
        if years_claims_free <= 6:  return 0.78
        if years_claims_free <= 8:  return 0.72
        return 0.65   # 9+ år skadefri
```

---

## S1.3 — Pydantic request-modell for settefisk

**Fil:** `backend/schemas.py`

Legg til følgende **etter** eksisterende `OperatorProfileInput`:

```python
class BuildingComponentInput(BaseModel):
    name: str
    area_sqm: float = Field(gt=0)
    value_per_sqm_nok: float = Field(default=27_000, gt=0)
    notes: Optional[str] = None

class SmoltFacilityInput(BaseModel):
    facility_name: str
    facility_type: str = "smolt_ras"           # smolt_ras | smolt_flow | smolt_hybrid
    building_components: List[BuildingComponentInput] = []
    site_clearance_nok: float = Field(default=0.0, ge=0)
    machinery_nok: float = Field(default=0.0, ge=0)
    avg_biomass_insured_value_nok: float = Field(default=0.0, ge=0)
    bi_sum_insured_nok: float = Field(default=0.0, ge=0)
    bi_indemnity_months: int = Field(default=24, ge=6, le=36)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    municipality: Optional[str] = None

class SmoltOperatorRequest(BaseModel):
    """
    Toppnivå-request for settefisk-analyse.
    Sendes til POST /api/feasibility/smolt/run
    """
    operator_name: str
    org_number: Optional[str] = None
    facilities: List[SmoltFacilityInput] = Field(min_length=1)

    # Finansielle data
    annual_revenue_nok: Optional[float] = Field(default=None, gt=0)
    ebitda_nok: Optional[float] = None
    equity_nok: Optional[float] = None
    operating_cf_nok: Optional[float] = None
    liquidity_nok: Optional[float] = None

    # Skadehistorikk
    claims_history_years: int = Field(default=0, ge=0)
    total_claims_paid_nok: float = Field(default=0.0, ge=0)

    # Forsikring i dag
    current_market_premium_nok: Optional[float] = None
    current_insurer: Optional[str] = None
    current_bi_indemnity_months: Optional[int] = None

    # Modellinnstillinger (gjenbrukes fra eksisterende schema)
    model: ModelSettingsInput = Field(default_factory=ModelSettingsInput)
    generate_pdf: bool = True
```

---

## S1.4 — Nytt API-endepunkt

**Fil:** `backend/api/smolt_feasibility.py` (ny fil)

```python
"""POST /api/feasibility/smolt/run — settefisk-specifik analyse-rute."""
from fastapi import APIRouter
from backend.schemas import SmoltOperatorRequest, FeasibilityResponse
from backend.services.smolt_operator_builder import SmoltOperatorBuilder
from backend.services.run_analysis import run_feasibility_analysis
from data.input_schema import SmoltOperatorInput, SmoltFacilityTIV, BuildingComponent

router = APIRouter(prefix="/api/feasibility/smolt", tags=["smolt"])

@router.post("/run", response_model=FeasibilityResponse)
async def run_smolt_feasibility(req: SmoltOperatorRequest) -> FeasibilityResponse:
    """
    Kjører full 9-stegs PCC-pipeline for et landbasert settefiskkonsern.
    TIV beregnes fra komponentstruktur (bygg, maskiner, biomasse, BI).
    """
    # Konverter Pydantic → domene-dataclass
    smolt_input = _build_smolt_input(req)

    # Bygg OperatorInput via SmoltOperatorBuilder
    builder = SmoltOperatorBuilder()
    op_input, alloc = builder.build(
        smolt_input,
        estimated_market_premium_nok=req.current_market_premium_nok,
    )

    # Kjør eksisterende pipeline uendret
    return run_feasibility_analysis(
        op_input          = op_input,
        model_settings    = req.model,
        allocation_summary= alloc,
    )


@router.get("/example/agaqua")
async def get_agaqua_example() -> SmoltOperatorRequest:
    """Returnerer pre-fylt Agaqua AS-eksempel for testing og demo."""
    return _agaqua_example()


# ------------------------------------------------------------------ #
def _build_smolt_input(req: SmoltOperatorRequest) -> SmoltOperatorInput:
    facilities = []
    for f in req.facilities:
        components = [
            BuildingComponent(name=b.name, area_sqm=b.area_sqm,
                              value_per_sqm_nok=b.value_per_sqm_nok)
            for b in f.building_components
        ]
        facilities.append(SmoltFacilityTIV(
            facility_name                = f.facility_name,
            building_components          = components,
            site_clearance_nok           = f.site_clearance_nok,
            machinery_nok                = f.machinery_nok,
            avg_biomass_insured_value_nok= f.avg_biomass_insured_value_nok,
            bi_sum_insured_nok           = f.bi_sum_insured_nok,
            bi_indemnity_months          = f.bi_indemnity_months,
            latitude                     = f.latitude,
            longitude                    = f.longitude,
        ))
    return SmoltOperatorInput(
        operator_name              = req.operator_name,
        org_number                 = req.org_number,
        facilities                 = facilities,
        annual_revenue_nok         = req.annual_revenue_nok,
        ebitda_nok                 = req.ebitda_nok,
        equity_nok                 = req.equity_nok,
        operating_cf_nok           = req.operating_cf_nok,
        liquidity_nok              = req.liquidity_nok,
        claims_history_years       = req.claims_history_years,
        total_claims_paid_nok      = req.total_claims_paid_nok,
        current_market_premium_nok = req.current_market_premium_nok,
    )


def _agaqua_example() -> SmoltOperatorRequest:
    """Agaqua AS / Settefisk 1-gruppen — faktiske 2024-data."""
    return SmoltOperatorRequest(
        operator_name   = "Agaqua AS",
        org_number      = "930529591",
        facilities      = [
            SmoltFacilityInput(
                facility_name  = "Villa Smolt AS",
                facility_type  = "smolt_ras",
                building_components=[
                    BuildingComponentInput(name="Hall over fish tanks", area_sqm=1370, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="RAS 1-2",              area_sqm=530,  value_per_sqm_nok=27000),
                    BuildingComponentInput(name="RAS 3-4",              area_sqm=610,  value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Gamledelen",           area_sqm=1393, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Forlager",             area_sqm=275,  value_per_sqm_nok=27000),
                ],
                site_clearance_nok           = 20_000_000,
                machinery_nok                = 200_000_000,
                avg_biomass_insured_value_nok= 39_680_409,
                bi_sum_insured_nok           = 243_200_000,
                bi_indemnity_months          = 24,
                latitude=62.29425, longitude=5.62739, municipality="Herøy",
            ),
            SmoltFacilityInput(
                facility_name  = "Olden Oppdrettsanlegg AS",
                facility_type  = "smolt_flow",
                building_components=[
                    BuildingComponentInput(name="Påvekstavdeling",        area_sqm=2204, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Yngel",                  area_sqm=899,  value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Klekkeri/startforing",   area_sqm=221,  value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Teknisk/vannbehandling",  area_sqm=77,   value_per_sqm_nok=27000),
                ],
                site_clearance_nok           = 20_000_000,
                machinery_nok                = 120_000_000,
                avg_biomass_insured_value_nok= 18_260_208,
                bi_sum_insured_nok           = 102_000_000,
                bi_indemnity_months          = 24,
                latitude=63.87241, longitude=9.93298, municipality="Ørland",
            ),
            SmoltFacilityInput(
                facility_name  = "Setran Settefisk AS",
                facility_type  = "smolt_flow",
                building_components=[
                    BuildingComponentInput(name="Hall A",            area_sqm=280, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Vannbehandling",    area_sqm=170, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Hall B",            area_sqm=715, value_per_sqm_nok=27000),
                    BuildingComponentInput(name="Hall C",            area_sqm=979, value_per_sqm_nok=27000),
                ],
                site_clearance_nok           = 15_000_000,
                machinery_nok                = 45_000_000,
                avg_biomass_insured_value_nok= 13_287_917,
                bi_sum_insured_nok           = 85_100_000,
                bi_indemnity_months          = 24,
                latitude=64.27887, longitude=10.45008, municipality="Osen",
            ),
        ],
        annual_revenue_nok     = 232_248_232,
        ebitda_nok             = 70_116_262,
        equity_nok             = 39_978_809,
        operating_cf_nok       = 46_510_739,
        liquidity_nok          = 55_454_950,
        claims_history_years   = 10,
        total_claims_paid_nok  = 0.0,
    )
```

**Registrer router i `backend/main.py`:**
```python
from backend.api.smolt_feasibility import router as smolt_router
app.include_router(smolt_router)
```

---

## S1.5 — Tester for Sprint S1

**Fil:** `tests/test_smolt_tiv_model.py` (ny fil)

Krav til testdekning — alle tester skal passere:

```python
"""
Test-suite for Sprint S1: Settefisk TIV-modell og operator-builder.
Minimum 35 tester.
"""

# ── Gruppe 1: SmoltFacilityTIV ──────────────────────────────────────
# test_building_total_sums_components()
#   → sum av alle BuildingComponent.insured_value_nok + site_clearance
# test_property_total_includes_machinery()
#   → building_total + machinery = property_total
# test_total_tiv_is_sum_of_all_parts()
#   → property + biomass + bi = total_tiv
# test_tiv_breakdown_sums_to_total()
#   → sum(tiv_breakdown.values()) == total_tiv (innen 1 NOK float-toleranse)
# test_tiv_shares_sum_to_one()
#   → sum(tiv_shares.values()) ≈ 1.0 (±1e-6)
# test_zero_tiv_shares_returns_zeros()
#   → Ingen ZeroDivisionError for tom facility

# ── Gruppe 2: SmoltOperatorInput ─────────────────────────────────────
# test_consolidated_breakdown_sums_three_facilities()
#   → Agaqua-eksempel: buildings ≈ 262.5M, machinery ≈ 365M, bi ≈ 430.3M
# test_n_facilities_correct()
# test_total_tiv_agaqua_within_tolerance()
#   → total_tiv ≈ 1_184_000_000 NOK (±1 % toleranse)

# ── Gruppe 3: SmoltOperatorBuilder ───────────────────────────────────
# test_build_returns_operator_input_and_alloc()
# test_operator_input_has_facility_type_smolt()
# test_premium_uses_howden_if_provided()
# test_premium_estimated_when_no_howden()
# test_estimated_premium_above_pcc_minimum()
#   → estimert premie > 5_250_000 NOK for Agaqua
# test_history_discount_10_years()
#   → discount factor == 0.65
# test_history_discount_zero_years()
#   → discount factor == 1.0
# test_inter_site_correlation_is_low()
#   → inter_site_correlation == 0.10
# test_scr_capacity_ratio_agaqua()
#   → scr_cap > 1.0 (Agaqua har mer enn nok CF til å dekke SCR)
# test_alloc_summary_facility_names()
# test_alloc_bi_share_agaqua()
#   → bi_share ≈ 0.36 (±0.02)
# test_alloc_machinery_share_agaqua()
#   → machinery_share ≈ 0.31 (±0.02)

# ── Gruppe 4: Pydantic schema ─────────────────────────────────────────
# test_smolt_operator_request_validates_agaqua()
# test_bi_indemnity_months_range()
#   → ValidationError for bi_indemnity_months < 6 og > 36
# test_facilities_min_length_one()
#   → ValidationError for tom facilities-liste

# ── Gruppe 5: API-endepunkt (TestClient) ──────────────────────────────
# test_smolt_run_endpoint_returns_200()
# test_smolt_example_endpoint_agaqua()
# test_smolt_run_verdict_not_not_suitable()
#   → Agaqua skal score >= POTENTIALLY_SUITABLE
# test_smolt_run_premium_in_allocation()
#   → allocation.total_tiv_nok ≈ 1_184_000_000 NOK

# ── Gruppe 6: Regresjonstest — sjømodell uberørt ─────────────────────
# test_sea_based_pipeline_unchanged_after_smolt_sprint()
#   → Nordic Aqua Partners eksempel via eksisterende endepunkt gir
#     samme total_tiv og verdict som før Sprint S1 ble innført
```

---

## S1 — Akseptansekriterier

- [ ] `pytest tests/test_smolt_tiv_model.py` — alle tester grønne
- [ ] `pytest tests/` (original suite) — fortsatt 1 092 passert, 0 feilet
- [ ] `POST /api/feasibility/smolt/run` med Agaqua-data returnerer HTTP 200
- [ ] `GET /api/feasibility/smolt/example/agaqua` returnerer total TIV ≈ 1,18 milliarder NOK
- [ ] Sjøoppdrett-endepunkt `/api/feasibility/run` er uendret

---
---

# SPRINT S2 — RAS-risikodomener og Monte Carlo-kalibering

**Mål:** Plattformen modellerer settefisk-spesifikke hendelsestyper
(RAS-kollapser, oksygenkriser, strømbortfall) korrekt i Monte Carlo.

---

## S2.1 — Nytt risikodomene: RAS-systemer

**Fil:** `risk_domains/ras_systems.py` (ny fil)

```python
"""
RAS-risikodomene for landbasert settefisk.

Seks sub-periler med kalibrerte frekvens- og alvorlighetsparametere
basert på norsk RAS-bransjedata og Agaqua-profil (10 år skadefri).

Domenekodestring: "ras"
"""
from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass(frozen=True)
class RASPerilProfile:
    """Risikoprofil for én RAS-hendelsestype."""
    name: str
    code: str
    annual_frequency_base: float   # λ for Poisson
    severity_as_pct_of_property: Tuple[float, float]  # (mean, cv) LogNormal
    bi_trigger: bool               # Utløser BI-tap?
    intra_facility_correlation: float   # Korrelasjon mellom avdelinger INNEN anlegg
    inter_facility_correlation: float   # Korrelasjon mellom ANLEGG

RAS_PERILS: Dict[str, RASPerilProfile] = {
    "biofilter_failure": RASPerilProfile(
        name="Biofiltersvikt",
        code="ras_bio",
        annual_frequency_base=0.12,
        severity_as_pct_of_property=(0.04, 0.70),
        bi_trigger=True,
        intra_facility_correlation=0.60,
        inter_facility_correlation=0.05,
    ),
    "oxygen_collapse": RASPerilProfile(
        name="Oksygenkollaps",
        code="ras_o2",
        annual_frequency_base=0.06,
        severity_as_pct_of_property=(0.12, 0.90),
        bi_trigger=True,
        intra_facility_correlation=0.75,
        inter_facility_correlation=0.03,
    ),
    "pump_failure": RASPerilProfile(
        name="Pumpehavari",
        code="ras_pump",
        annual_frequency_base=0.18,
        severity_as_pct_of_property=(0.02, 0.60),
        bi_trigger=False,
        intra_facility_correlation=0.40,
        inter_facility_correlation=0.02,
    ),
    "power_outage": RASPerilProfile(
        name="Strømbortfall",
        code="ras_power",
        annual_frequency_base=0.08,
        severity_as_pct_of_property=(0.06, 0.80),
        bi_trigger=True,
        intra_facility_correlation=0.85,   # Hele anlegget rammes
        inter_facility_correlation=0.02,
    ),
    "water_quality": RASPerilProfile(
        name="Vannkvalitetssvikt (CO₂/pH)",
        code="ras_wq",
        annual_frequency_base=0.10,
        severity_as_pct_of_property=(0.05, 0.75),
        bi_trigger=True,
        intra_facility_correlation=0.55,
        inter_facility_correlation=0.03,
    ),
    "water_source_contamination": RASPerilProfile(
        name="Vannkildeforurensning",
        code="ras_source",
        annual_frequency_base=0.02,        # Sjelden, men katastrofal
        severity_as_pct_of_property=(0.35, 1.20),
        bi_trigger=True,
        intra_facility_correlation=0.95,   # Rammer hele anlegget
        inter_facility_correlation=0.01,
    ),
}


class RASRiskDomain:
    """
    Aggregert RAS-risikodomene.
    Brukes av SmoltMonteCarloEngine for å kalibrere simuleringsparametre.
    """

    def __init__(self, property_tiv_nok: float, claims_free_years: int = 0):
        self.property_tiv = property_tiv_nok
        self.discount = self._history_discount(claims_free_years)

    @property
    def aggregate_frequency(self) -> float:
        """Aggregert frekvens for alle RAS-periler, justert for historikk."""
        raw = sum(p.annual_frequency_base for p in RAS_PERILS.values())
        return raw * self.discount

    @property
    def expected_annual_loss_nok(self) -> float:
        total = 0.0
        for peril in RAS_PERILS.values():
            freq = peril.annual_frequency_base * self.discount
            sev_mean, _ = peril.severity_as_pct_of_property
            total += freq * sev_mean * self.property_tiv
        return total

    def catastrophe_scenario(self) -> Dict[str, float]:
        """
        Worst-case: oksygenkollaps + strømbortfall simulant.
        Representerer 99.5th percentile hendelse.
        """
        o2   = RAS_PERILS["oxygen_collapse"]
        pwr  = RAS_PERILS["power_outage"]
        combined_sev = (o2.severity_as_pct_of_property[0] +
                        pwr.severity_as_pct_of_property[0]) * 0.80
        return {
            "combined_probability": o2.annual_frequency_base * pwr.annual_frequency_base * 0.3,
            "severity_pct_of_property": combined_sev,
            "estimated_loss_nok": combined_sev * self.property_tiv,
        }

    @staticmethod
    def _history_discount(years: int) -> float:
        if years <= 0: return 1.00
        if years < 5:  return 0.85
        if years < 10: return 0.72
        return 0.65
```

---

## S2.2 — Settefisk Monte Carlo-kalibering

**Fil:** `models/smolt_calibration.py` (ny fil)

```python
"""
SmoltMCCalibrator

Kalibrerer MonteCarloEngine-parametere for settefisk-risikoprofil.
Outputen sendes direkte inn i eksisterende MonteCarloEngine.
"""
from dataclasses import dataclass
from typing import Optional
from risk_domains.ras_systems import RASRiskDomain
from data.input_schema import SmoltOperatorInput


@dataclass
class SmoltMCParameters:
    """Kalibrerte Monte Carlo-parametere for ett settefiskkonsern."""
    # Kjernemodell-parametere (kompatible med OperatorInput)
    expected_annual_events:    float
    mean_loss_severity_nok:    float
    cv_loss_severity:          float
    catastrophe_probability:   float
    catastrophe_multiplier:    float
    inter_site_correlation:    float
    # Tilleggsinfo for rapportering
    dominant_peril:            str
    ras_expected_annual_loss:  float
    history_discount_applied:  float


class SmoltMCCalibrator:
    """
    Kalibrerer MC-parametere fra SmoltOperatorInput.
    Tar hensyn til:
    - Antall anlegg og deres RAS-type
    - Skadefri historikk (frekvensrabatt)
    - TIV-fordeling (maskintung → høyere severity CV)
    - BI-dominans (høy BI-share → lengre PD-hale)
    """

    def calibrate(self, smolt_input: SmoltOperatorInput) -> SmoltMCParameters:
        prop_tiv = sum(
            f.building_total_nok + f.machinery_nok
            for f in smolt_input.facilities
        )
        n = smolt_input.n_facilities
        ras = RASRiskDomain(prop_tiv, smolt_input.claims_history_years)

        # BI-dominans øker tap-severity
        total_tiv = smolt_input.total_tiv_nok
        bi_share = sum(f.bi_sum_insured_nok for f in smolt_input.facilities) / total_tiv if total_tiv else 0
        bi_severity_adder = bi_share * 0.40   # BI-tung → 40 % høyere severity

        # Inter-site korrelasjon — separate nedbørsfelt betyr lav korrelasjon
        # men deles noe operasjonell risiko (samme ledelse, prosedyrer)
        inter_corr = max(0.05, 0.15 - (n - 1) * 0.02)   # Avtar svakt med antall anlegg

        dominant_peril = max(
            RAS_PERILS.items(),
            key=lambda kv: kv[1].annual_frequency_base * kv[1].severity_as_pct_of_property[0]
        )[0]

        return SmoltMCParameters(
            expected_annual_events    = ras.aggregate_frequency * n,
            mean_loss_severity_nok    = ras.expected_annual_loss_nok / max(ras.aggregate_frequency * n, 1e-9),
            cv_loss_severity          = 0.65 + bi_severity_adder,
            catastrophe_probability   = 0.03,
            catastrophe_multiplier    = 4.5,
            inter_site_correlation    = inter_corr,
            dominant_peril            = dominant_peril,
            ras_expected_annual_loss  = ras.expected_annual_loss_nok,
            history_discount_applied  = ras.discount,
        )
```

---

## S2.3 — Settefisk-scenariopreset

**Fil:** `config/smolt_scenarios.py` (ny fil)

```python
"""
4 settefisk-spesifikke scenariopreset til bruk i GUI og rapportering.
Tilsvarer SCENARIO_PRESETS i frontend men med RAS-logikk.
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class SmoltScenarioPreset:
    id: str
    label_no: str
    description_no: str
    parameter_overrides: Dict[str, Any]
    highest_risk_driver: str

SMOLT_SCENARIO_PRESETS = [
    SmoltScenarioPreset(
        id                   = "ras_total_collapse",
        label_no             = "RAS-totalkollaps",
        description_no       = "Biofiltersvikt kombinert med strømbortfall. Rammer én hel produksjonsavdeling.",
        parameter_overrides  = {
            "loss_multiplier":        4.20,
            "bi_trigger":             True,
            "affected_facilities":    1,
            "frequency_multiplier":   1.0,
        },
        highest_risk_driver  = "ras_systems",
    ),
    SmoltScenarioPreset(
        id                   = "oxygen_crisis",
        label_no             = "Oksygenkrise (4t)",
        description_no       = "Pumpesvikt gir O₂ < 6 mg/L i 4 timer. Tap av 30–80 % av berørt generasjon.",
        parameter_overrides  = {
            "loss_multiplier":        2.80,
            "bi_trigger":             True,
            "affected_facilities":    1,
            "frequency_multiplier":   1.0,
        },
        highest_risk_driver  = "ras_systems",
    ),
    SmoltScenarioPreset(
        id                   = "water_contamination",
        label_no             = "Vannforurensning",
        description_no       = "Ekstern forurensing i vannkilde. Kan ramme hele anlegget. Sjelden men katastrofal.",
        parameter_overrides  = {
            "loss_multiplier":        6.50,
            "bi_trigger":             True,
            "affected_facilities":    1,
            "frequency_multiplier":   0.25,
        },
        highest_risk_driver  = "environmental",
    ),
    SmoltScenarioPreset(
        id                   = "extended_power_outage",
        label_no             = "Strømbortfall 48 timer",
        description_no       = "Nett og aggregat feiler. Hele anlegget mister sirkulasjon. BI-eksponering aktiveres.",
        parameter_overrides  = {
            "loss_multiplier":        3.20,
            "bi_trigger":             True,
            "affected_facilities":    1,
            "frequency_multiplier":   1.0,
        },
        highest_risk_driver  = "operational",
    ),
]
```

---

## S2.4 — Tester for Sprint S2

**Fil:** `tests/test_smolt_risk_domains.py` (ny fil)

Minimum 30 tester:

```python
# ── RASRiskDomain ────────────────────────────────────────────────────
# test_aggregate_frequency_sum_of_all_perils()
# test_history_discount_10_years_reduces_frequency()
# test_expected_annual_loss_positive_for_nonzero_tiv()
# test_catastrophe_scenario_returns_dict_with_required_keys()
# test_zero_claims_free_years_no_discount()
# test_inter_facility_correlation_is_low()
#   → alle periler har inter_facility_correlation < 0.10

# ── SmoltMCCalibrator ────────────────────────────────────────────────
# test_calibrate_returns_smolt_mc_parameters()
# test_calibrated_frequency_lower_for_claims_free_operator()
# test_calibrated_frequency_agaqua_within_range()
#   → 0.30 < expected_annual_events < 1.50 for Agaqua (10 år skadefri)
# test_calibrated_severity_covers_retention_layer()
#   → mean_loss_severity > 0
# test_bi_heavy_portfolio_increases_cv()
#   → Agaqua (BI-share ≈ 0.36): cv_loss_severity > 0.80
# test_inter_site_corr_decreases_with_more_facilities()
# test_dominant_peril_is_ras_peril()

# ── Scenariopreset ───────────────────────────────────────────────────
# test_four_smolt_presets_defined()
# test_all_presets_have_unique_ids()
# test_ras_collapse_has_highest_loss_multiplier_among_likely_scenarios()
# test_water_contamination_has_lowest_frequency_multiplier()
# test_all_presets_trigger_bi()
#   → bi_trigger == True for alle 4 presets

# ── Integrasjon: SmoltMCCalibrator → MonteCarloEngine ────────────────
# test_calibrated_parameters_accepted_by_mc_engine()
#   → MonteCarloEngine kjører uten unntak med SmoltMCParameters
# test_mc_output_has_positive_var_99_5()
# test_agaqua_var_99_5_below_bi_sum()
#   → VaR 99.5% < 430_300_000 NOK (total BI-eksponering)
```

## S2 — Akseptansekriterier

- [ ] `pytest tests/test_smolt_risk_domains.py` — alle tester grønne
- [ ] `pytest tests/` — fortsatt 1 092+ passert, 0 feilet
- [ ] Agaqua-eksempel via `/api/feasibility/smolt/run` gir VaR 99.5% i rimelig område
- [ ] Eksisterende sjø-domenefiler (`risk_domains/structural.py`) er uendret

---
---

# SPRINT S3 — Settefisk C5AI+ Forecasters

**Mål:** C5AI+ pipeline erstatter sjøbaserte forecasters med fire
settefisk-spesifikke forecasters. Eksisterende forecasters beholdes
for sjøoppdrett.

---

## S3.1 — Fire nye forecasters

**Filer:** `c5ai_plus/forecasting/` (fire nye filer)

### `ras_water_quality_forecaster.py`

```python
"""
RASWaterQualityForecaster

Erstatter HABForecaster + JellyfishForecaster for RAS-anlegg.
Modellerer risiko for vannkvalitetssvikt (O₂, CO₂, pH, temperatur).

Risikotype: "ras_water_quality"
Inndataavhengigheter:
  - dissolved_oxygen_mg_l (primær)
  - surface_temp_c (sekundær — påvirker O₂-løselighet)
  - nitrate_umol_l (biofilterindikator)
  - co2_ppm (hvis tilgjengelig)
"""
from c5ai_plus.forecasting.base_forecaster import BaseForecaster
from c5ai_plus.data_models.biological_input import SiteInput
from c5ai_plus.data_models.forecast_schema import RiskTypeForecast
from typing import List

class RASWaterQualityForecaster(BaseForecaster):
    RISK_TYPE = "ras_water_quality"

    # Terskler basert på norske RAS-standarder
    O2_CRITICAL_THRESHOLD   = 6.0   # mg/L
    O2_WARNING_THRESHOLD    = 7.5
    TEMP_HIGH_THRESHOLD     = 18.0  # °C (stress for laks/ørret i RAS)
    NITRATE_HIGH_THRESHOLD  = 12.0  # µmol/L (biofilterbelastning)

    def forecast(self, site: SiteInput, forecast_years: int = 5) -> List[RiskTypeForecast]:
        """
        Returnerer List[RiskTypeForecast] for ras_water_quality.
        Sannsynlighet øker med:
          - Antall observerte O₂-brudd < WARNING_THRESHOLD
          - Høye nitrat-verdier (biofilterbelastning)
          - Temperaturstress
        """
        ...   # Implementer etter BaseForecaster-mønster
```

### `biofilter_forecaster.py`

```python
"""
BiofilterForecaster

Modellerer risiko for biofiltersvikt i RAS-systemer.
Biofilter er det viktigste enkeltpunktet i RAS — svikt gir rask
akkumulering av ammonium/nitritt og potensielt totaltap av generasjon.

Risikotype: "biofilter"
Inndataavhengigheter:
  - nitrite_mg_l (primær)
  - ammonia_mg_l (primær)
  - nitrate_umol_l (sekundær)
  - days_since_last_filter_maintenance (operasjonell)
"""
...   # Implementer etter RASWaterQualityForecaster-mønster
```

### `smolt_health_forecaster.py`

```python
"""
SmoltHealthForecaster

Erstatter PathogenForecaster for RAS-settefisk.
Modellerer helse-hendelser spesifikke for RAS-miljø:
  - Katarakt (øyeskade ved for høyt CO₂)
  - AGD (amøbisk gjellesykdom — forekommer i RAS)
  - Bakteriell infeksjon (Flavobacterium, Yersinia)

Risikotype: "smolt_health"
"""
...
```

### `power_supply_forecaster.py`

```python
"""
PowerSupplyForecaster

Ny — ingen pendant i sjøoppdrett.
Modellerer risiko for strømbortfall × backup-kapasitet.
Kritisk for RAS: uten sirkulasjon kollapser O₂ på < 30 minutter.

Risikotype: "power_supply"
Inndataavhengigheter:
  - backup_power_hours (UPS + aggregat kapasitet)
  - grid_reliability_score (lokal nettleverandør)
  - last_power_test_days (dager siden siste test av backup)
"""
...
```

---

## S3.2 — Settefisk C5AI+ biologisk input-skjema

**Fil:** `c5ai_plus/data_models/smolt_biological_input.py` (ny fil)

```python
"""
Biologisk inputskjema for settefisk / RAS-anlegg.
Tilsvarer C5AIOperatorInput men med RAS-spesifikke felter.
"""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RASMonitoringData:
    """Sanntids / periodisk overvåkingsdata fra ett RAS-anlegg."""
    site_id: str
    site_name: str
    timestamp_iso: str

    # Vannkvalitet (månedlig gjennomsnitt)
    dissolved_oxygen_mg_l: Optional[float] = None
    co2_ppm: Optional[float] = None
    ph: Optional[float] = None
    water_temp_c: Optional[float] = None
    nitrate_umol_l: Optional[float] = None
    nitrite_mg_l: Optional[float] = None
    ammonia_mg_l: Optional[float] = None
    turbidity_ntu: Optional[float] = None

    # Biofilter-status
    days_since_last_filter_maintenance: Optional[int] = None
    biofilter_efficiency_pct: Optional[float] = None   # 0–100

    # Strøm og backup
    backup_power_hours: Optional[float] = None         # UPS + aggregat kapasitet
    grid_reliability_score: Optional[float] = None     # 0–1
    last_power_test_days: Optional[int] = None

    # Biologiske observasjoner
    cataract_prevalence_pct: Optional[float] = None    # % fisk med katarakt
    agd_score_mean: Optional[float] = None
    mortality_rate_7d_pct: Optional[float] = None

    # Operasjonell belastning
    biomass_kg: Optional[float] = None
    stocking_density_kg_m3: Optional[float] = None
    feeding_rate_pct_bw_day: Optional[float] = None

@dataclass
class SmoltC5AIInput:
    """Toppnivå-input for settefisk C5AI+ pipeline."""
    operator_id: str
    operator_name: str
    sites: List[RASMonitoringData] = field(default_factory=list)
    forecast_years: int = 5
```

---

## S3.3 — Settefisk C5AI+ varslingsregler

**Fil:** `c5ai_plus/alerts/smolt_alert_rules.py` (ny fil)

```python
"""
15 varslingsregler for settefisk / RAS.
Erstatter sjøbaserte alert_rules for smolt-modus.
"""
from c5ai_plus.alerts.alert_models import AlertRule

SMOLT_ALERT_RULES: list[AlertRule] = [
    # ── Oksygen (4 regler) ──────────────────────────────────────────
    AlertRule(
        rule_id="ras_o2_critical",
        risk_type="ras_water_quality",
        condition_description="Dissolved O₂ < 6.0 mg/L",
        probability_weight=0.35,
        triggered_when=lambda data: (data.get("dissolved_oxygen_mg_l") or 99) < 6.0,
    ),
    AlertRule(
        rule_id="ras_o2_warning",
        risk_type="ras_water_quality",
        condition_description="Dissolved O₂ < 7.5 mg/L",
        probability_weight=0.20,
        triggered_when=lambda data: 6.0 <= (data.get("dissolved_oxygen_mg_l") or 99) < 7.5,
    ),
    AlertRule(
        rule_id="ras_nitrate_high",
        risk_type="biofilter",
        condition_description="Nitrate > 12 µmol/L (biofilter overload)",
        probability_weight=0.18,
        triggered_when=lambda data: (data.get("nitrate_umol_l") or 0) > 12.0,
    ),
    AlertRule(
        rule_id="ras_temp_stress",
        risk_type="ras_water_quality",
        condition_description="Water temperature > 18°C",
        probability_weight=0.15,
        triggered_when=lambda data: (data.get("water_temp_c") or 0) > 18.0,
    ),
    # ── Biofilter (3 regler) ─────────────────────────────────────────
    AlertRule(
        rule_id="biofilter_maintenance_overdue",
        risk_type="biofilter",
        condition_description="No filter maintenance in > 90 days",
        probability_weight=0.25,
        triggered_when=lambda data: (data.get("days_since_last_filter_maintenance") or 0) > 90,
    ),
    AlertRule(rule_id="biofilter_efficiency_low", ...),
    AlertRule(rule_id="nitrite_elevated",         ...),
    # ── Strøm (3 regler) ─────────────────────────────────────────────
    AlertRule(rule_id="power_backup_insufficient", ...),  # backup < 4 timer
    AlertRule(rule_id="power_test_overdue",        ...),  # siste test > 30 dager
    AlertRule(rule_id="grid_reliability_low",      ...),  # score < 0.85
    # ── Fiskehelse (3 regler) ────────────────────────────────────────
    AlertRule(rule_id="cataract_prevalence_high",  ...),  # > 5 %
    AlertRule(rule_id="mortality_elevated",        ...),  # 7d > 0.5 %
    AlertRule(rule_id="high_stocking_density",     ...),  # > 80 kg/m³
    # ── Biomasse (2 regler) ──────────────────────────────────────────
    AlertRule(rule_id="generation_peak_stress",    ...),
    AlertRule(rule_id="feeding_rate_anomaly",      ...),
]
```

---

## S3.4 — Tester for Sprint S3

**Fil:** `tests/test_smolt_c5ai.py` (ny fil) — minimum 28 tester

```python
# ── RASWaterQualityForecaster ────────────────────────────────────────
# test_forecaster_returns_list_of_risk_type_forecasts()
# test_forecast_risk_type_is_ras_water_quality()
# test_low_oxygen_increases_event_probability()
#   → O₂ = 5.5 mg/L gir høyere prob enn O₂ = 9.0 mg/L
# test_high_nitrate_increases_biofilter_risk()
# test_data_quality_flag_prior_only_without_measurements()
# test_confidence_score_range_0_to_1()

# ── BiofilterForecaster ──────────────────────────────────────────────
# test_overdue_maintenance_raises_probability()
# test_low_efficiency_raises_probability()
# test_forecast_years_returns_correct_length()

# ── PowerSupplyForecaster ────────────────────────────────────────────
# test_low_backup_hours_raises_probability()
# test_overdue_power_test_raises_probability()
# test_adequate_backup_gives_low_probability()

# ── SmoltC5AIInput ───────────────────────────────────────────────────
# test_ras_monitoring_data_instantiates_with_nulls()
# test_smolt_c5ai_input_aggregates_sites()

# ── Varslingsregler ──────────────────────────────────────────────────
# test_15_smolt_alert_rules_defined()
# test_o2_critical_triggers_below_6()
# test_o2_warning_triggers_between_6_and_7_5()
# test_maintenance_overdue_triggers_above_90_days()
# test_adequate_conditions_trigger_no_rules()

# ── Integrasjon: Sjøbaserte forecasters uberørt ──────────────────────
# test_hab_forecaster_still_works()
# test_lice_forecaster_still_works()
# test_jellyfish_forecaster_still_works()
# test_pathogen_forecaster_still_works()
```

## S3 — Akseptansekriterier

- [ ] Fire nye forecasters er registrert i C5AI+ pipeline
- [ ] `RISK_TYPES` for smolt: `["ras_water_quality", "biofilter", "smolt_health", "power_supply"]`
- [ ] 15 smolt-varslingsregler definert
- [ ] Eksisterende fire forecasters (`hab`, `lice`, `jellyfish`, `pathogen`) uendret
- [ ] Full testsuit passerer

---
---

# SPRINT S4 — Generasjonstracker og BI-kalkulator

**Mål:** Plattformen kan beregne gjennomsnittlig forsikringsverdi for
biomasse på tvers av parallelle generasjoner, og beregne BI korrekt
fra smoltvolum og salgspris.

---

## S4.1 — Generasjonstracker

**Fil:** `models/smolt_generation_tracker.py` (ny fil)

```python
"""
SmoltGenerationTracker

Beregner gjennomsnittlig forsikringsverdi for biomasse i et settefiskanlegg
basert på parallelle generasjoner og månedlig tilvekstprofil.

Verdisetting: Interpolert fra bransjens vekttabell (NOK per fisk, 17 steg
fra 0.001g til 150g) — identisk med Agaqua AS sine egne beregninger.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class Department(str, Enum):
    HATCHERY    = "klekkeri"
    START_FEED  = "startforing"
    GROWTH      = "vekst"
    OUTDOOR_VAT = "utekar"
    RAS         = "ras"


# Versikringsverditabell (gram → NOK per fisk)
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


@dataclass
class GenerationMonth:
    """Biomassestatus for én generasjon i én måned."""
    count: int
    avg_weight_g: float

    @property
    def insured_value_nok(self) -> float:
        return self.count * self._lookup_value(self.avg_weight_g)

    @staticmethod
    def _lookup_value(weight_g: float) -> float:
        """
        Interpolerer NOK-verdi fra WEIGHT_TO_VALUE_NOK.
        Bruker nærmeste støttepunkt (ikke lineær interpolasjon —
        i tråd med Agaqua-metodikk).
        """
        keys = sorted(WEIGHT_TO_VALUE_NOK.keys())
        if weight_g <= keys[0]:  return WEIGHT_TO_VALUE_NOK[keys[0]]
        if weight_g >= keys[-1]: return WEIGHT_TO_VALUE_NOK[keys[-1]]
        # Finn nærmeste nøkkel
        nearest = min(keys, key=lambda k: abs(k - weight_g))
        return WEIGHT_TO_VALUE_NOK[nearest]


@dataclass
class Generation:
    """
    En produksjonsgenerasjon med månedsprofil.
    Én linje per generasjon — f.eks. "1-2027 laks".
    """
    generation_id: str              # f.eks. "1-2027"
    species: str                    # "laks" | "ørret" | "regnbueørret"
    department: Department
    # Månedsprofil: {måned_index: GenerationMonth} (0=Jan, 11=Des)
    monthly_data: Dict[int, GenerationMonth] = field(default_factory=dict)


@dataclass
class FacilityGenerationProfile:
    """Alle generasjoner i ett anlegg for ett år."""
    facility_name: str
    year: int
    generations: List[Generation] = field(default_factory=list)

    def monthly_total_value_nok(self, month: int) -> float:
        """Sum av forsikringsverdier for alle aktive generasjoner i én måned."""
        return sum(
            gen.monthly_data[month].insured_value_nok
            for gen in self.generations
            if month in gen.monthly_data
        )

    def annual_average_value_nok(self) -> float:
        """Gjennomsnittlig stående forsikringsverdi gjennom året (12 måneder)."""
        monthly = [self.monthly_total_value_nok(m) for m in range(12)]
        active  = [v for v in monthly if v > 0]
        return sum(active) / len(active) if active else 0.0

    def peak_value_nok(self) -> float:
        return max(self.monthly_total_value_nok(m) for m in range(12))
```

---

## S4.2 — BI-kalkulator for smoltproduksjon

**Fil:** `models/smolt_bi_calculator.py` (ny fil)

```python
"""
SmoltBICalculator

Beregner driftsavbrudd (BI) sum forsikret for ett settefiskanlegg.
Metode: Volum × pris ved målvekt × indemnitetperiode (måneder / 12).

Formel (verifisert mot Agaqua AS sine Business_interruption.xlsx):
  BI = annual_smolt_volume × price_per_smolt × (indemnity_months / 12)

Eksempel Villa Smolt:
  3_200_000 × 38 NOK × 2 år = NOK 243_200_000
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class SmoltBIResult:
    """Output fra SmoltBICalculator for ett anlegg."""
    facility_name: str
    bi_sum_insured_nok: float          # Totalsum til forsikring
    annual_revenue_equivalent_nok: float   # Årsomsetning (= BI / perioder)
    indemnity_months: int
    annual_smolt_volume: int
    target_weight_g: float
    price_per_smolt_nok: float
    generation_rebuild_months: int     # Tid til ny generasjon er klar


class SmoltBICalculator:
    """
    Beregner BI for settefiskanlegg.
    Tar høyde for:
    - To produksjonsperioder (generasjon 0 tapes, generasjon 1 forsinkes)
    - Sesongvariasjon i smoltpriser (valgfritt)
    """

    DEFAULT_INDEMNITY_MONTHS      = 24
    DEFAULT_GENERATION_REBUILD_M  = 18

    def calculate(
        self,
        facility_name: str,
        annual_smolt_volume: int,
        target_weight_g: float,
        price_per_smolt_nok: float,
        indemnity_months: int = DEFAULT_INDEMNITY_MONTHS,
        generation_rebuild_months: int = DEFAULT_GENERATION_REBUILD_M,
        seasonal_price_factor: Optional[Dict[int, float]] = None,
    ) -> SmoltBIResult:
        """
        Beregner BI.

        Args:
            annual_smolt_volume:    Antall smolt levert per år (normal drift)
            target_weight_g:        Gjennomsnittlig salgsvekt i gram
            price_per_smolt_nok:    Salgspris per smolt i NOK
            indemnity_months:       Dekningsperiode (typisk 24 for settefisk)
            generation_rebuild_months: Tid fra tap til ny generasjon er klar
            seasonal_price_factor:  Valgfri dict {månedsnummer: multiplikator}

        Returns:
            SmoltBIResult
        """
        annual_revenue = annual_smolt_volume * price_per_smolt_nok
        periods = indemnity_months / 12
        bi_sum  = annual_revenue * periods

        return SmoltBIResult(
            facility_name                = facility_name,
            bi_sum_insured_nok           = bi_sum,
            annual_revenue_equivalent_nok= annual_revenue,
            indemnity_months             = indemnity_months,
            annual_smolt_volume          = annual_smolt_volume,
            target_weight_g              = target_weight_g,
            price_per_smolt_nok          = price_per_smolt_nok,
            generation_rebuild_months    = generation_rebuild_months,
        )

    def calculate_group(
        self,
        facilities: list,  # List[dict] med nøkler som over
    ) -> Dict[str, SmoltBIResult]:
        """Beregner BI for alle anlegg i ett konsern."""
        return {
            f["facility_name"]: self.calculate(**f)
            for f in facilities
        }
```

---

## S4.3 — Tester for Sprint S4

**Fil:** `tests/test_smolt_generation_bi.py` (ny fil) — minimum 35 tester

```python
# ── GenerationMonth ──────────────────────────────────────────────────
# test_weight_lookup_exact_match()
#   → 50g → NOK 10.0 per fisk
# test_weight_lookup_nearest_point()
#   → 55g → NOK 10.0 (nærmeste er 50g, ikke 60g → 14.0)
# test_weight_below_minimum_uses_min_value()
#   → 0.0001g → NOK 2.5
# test_weight_above_maximum_uses_max_value()
#   → 200g → NOK 20.0
# test_insured_value_is_count_times_per_fish_value()

# ── FacilityGenerationProfile ────────────────────────────────────────
# test_monthly_total_sums_all_active_generations()
# test_annual_average_excludes_zero_months()
# test_peak_value_is_maximum_monthly()
# test_villa_smolt_annual_average_within_tolerance()
#   → annual_average ≈ 39_680_409 NOK (±5 %, fra Agaqua-data)

# ── SmoltBICalculator ────────────────────────────────────────────────
# test_villa_smolt_bi_exact()
#   → 3_200_000 × 38 × 2 = 243_200_000 NOK
# test_olden_bi_exact()
#   → 1_500_000 × 34 × 2 = 102_000_000 NOK
# test_setran_bi_exact()
#   → 1_150_000 × 37 × 2 = 85_100_000 NOK
# test_agaqua_total_bi()
#   → Sum ≈ 430_300_000 NOK
# test_12_month_indemnity_halves_bi()
# test_calculate_group_returns_all_facilities()
# test_annual_revenue_equivalent_is_bi_over_periods()
# test_zero_volume_gives_zero_bi()

# ── Integrasjon: Generator → SmoltFacilityTIV ────────────────────────
# test_generation_average_feeds_into_facility_tiv()
# test_bi_calculator_feeds_into_facility_tiv()
# test_full_agaqua_tiv_with_calculated_biomass_and_bi()
#   → total_tiv ≈ 1_184_000_000 NOK (±2 %)
```

## S4 — Akseptansekriterier

- [ ] Villa Smolt BI = NOK 243 200 000 (eksakt match med Agaqua-data)
- [ ] Agaqua annual average biomasse ≈ NOK 71 228 534 (±5 %)
- [ ] Full agaqua TIV via kalkulatorer ≈ NOK 1 184 000 000 (±2 %)
- [ ] Alle tester grønne, original suite uendret

---
---

# SPRINT S5 — Frontend: Settefisk-modus i GUI

**Mål:** GUI tilbyr en «Settefisk»-modus med korrekte inputfelter,
settefisk-spesifikke scenarioer, og oppdatert Allocation-tab.

---

## S5.1 — Operator-type velger

**Fil:** `frontend/src/components/InputForm/OperatorTypeSelector.jsx` (ny fil)

```jsx
/**
 * OperatorTypeSelector
 * Vises øverst i venstre panel. Lar bruker velge mellom:
 *   - Sjøoppdrett (eksisterende flyt)
 *   - Settefisk / RAS (ny flyt)
 * Valget styrer hvilke inputfelter som vises.
 */
export function OperatorTypeSelector({ value, onChange }) {
  return (
    <div className="operator-type-selector">
      <button
        className={`type-btn ${value === 'sea' ? 'active' : ''}`}
        onClick={() => onChange('sea')}
      >
        🐟  Sjøoppdrett
      </button>
      <button
        className={`type-btn ${value === 'smolt' ? 'active' : ''}`}
        onClick={() => onChange('smolt')}
      >
        🏭  Settefisk / RAS
      </button>
    </div>
  );
}
```

---

## S5.2 — Settefisk TIV-inputpanel

**Fil:** `frontend/src/components/InputForm/SmoltTIVPanel.jsx` (ny fil)

```jsx
/**
 * SmoltTIVPanel
 *
 * Viser ett akkordeon-kort per anlegg.
 * Hvert kort har:
 *   - Anleggnavn og type (smolt_ras / smolt_flow / smolt_hybrid)
 *   - Bygningskomponenter (dynamisk liste: m² + verdi/m²)
 *   - Maskiner/RAS (NOK, fritekst)
 *   - Branntomt/rydding (NOK)
 *   - Biomasse (NOK — kan fylles manuelt eller fra GenerationTracker)
 *   - BI (NOK — kan fylles manuelt eller fra BICalculator)
 *   - TIV-sammendrag (live, beregnes i frontend)
 *
 * Props:
 *   facilities    : Array av SmoltFacilityInput
 *   onChange      : (updatedFacilities) => void
 *   onAddFacility : () => void
 *   onRemoveFacility: (index) => void
 */
export function SmoltTIVPanel({ facilities, onChange, onAddFacility, onRemoveFacility }) {
  // Implementer etter eksisterende InputForm-mønster
  // Bruk nummerformater med tusenskille (norsk)
  // Live TIV-oppsummering per anlegg og totalt nederst
}
```

---

## S5.3 — BI-kalkulator-widget

**Fil:** `frontend/src/components/InputForm/SmoltBIWidget.jsx` (ny fil)

```jsx
/**
 * SmoltBIWidget
 * Enkel kalkulatorwidget i inputpanelet.
 * Bruker kan taste inn:
 *   - Smoltvolum per år
 *   - Målvekt (g)
 *   - Salgspris per stk (NOK)
 *   - Indemnitetperiode (12 / 24 måneder)
 * Widget viser beregnet BI-sum live.
 * "Bruk denne verdien" → fyller inn i SmoltFacilityInput.bi_sum_insured_nok
 */
export function SmoltBIWidget({ onApply, facilityName }) {
  // Formel: volum × pris × (måneder / 12)
  // Vis forklaring: "3 200 000 × NOK 38 × 2 år = NOK 243 200 000"
}
```

---

## S5.4 — Settefisk scenariopreset-oppdatering

**Fil:** `frontend/src/data/smoltScenariosData.js` (ny fil)

```javascript
/**
 * Settefisk-spesifikke scenariopreset.
 * Tilsvarer SCENARIO_PRESETS men for smolt-modus.
 */
export const SMOLT_SCENARIO_PRESETS = [
  {
    id: "ras_total_collapse",
    label: "RAS-totalkollaps",
    description: "Biofiltersvikt kombinert med strømbortfall. Rammer én produksjonsavdeling.",
    icon: "⚡",
    params: { loss_multiplier: 4.20, bi_trigger: true }
  },
  {
    id: "oxygen_crisis",
    label: "Oksygenkrise (4t)",
    description: "Pumpesvikt → O₂ < 6 mg/L. Tap av 30–80 % av berørt generasjon.",
    icon: "💧",
    params: { loss_multiplier: 2.80, bi_trigger: true }
  },
  {
    id: "water_contamination",
    label: "Vannforurensning",
    description: "Ekstern kilde. Sjelden men katastrofal for hele anlegget.",
    icon: "☣",
    params: { loss_multiplier: 6.50, frequency_multiplier: 0.25 }
  },
  {
    id: "power_outage_48h",
    label: "Strømbortfall 48 timer",
    description: "Nett og aggregat feiler. BI-eksponering hele anlegget.",
    icon: "🔌",
    params: { loss_multiplier: 3.20, bi_trigger: true }
  }
];
```

---

## S5.5 — Oppdatert Allocation-tab for settefisk

**Fil:** `frontend/src/components/results/SmoltAllocationTab.jsx` (ny fil)

```jsx
/**
 * SmoltAllocationTab
 * Viser TIV-fordeling spesifikk for settefisk.
 * Erstatter generisk AllocationTab når operator_type == "smolt".
 *
 * Innhold:
 *   1. TIV-breakdown (4 kolonner: Bygg, Maskiner/RAS, Biomasse, BI)
 *      - Inkluderer donut-diagram (SVG, ingen bibliotek)
 *   2. Per-anlegg tabell med alle komponenter
 *   3. BI-analyse: Indemnitetperiode + årsomsetning
 *   4. SCR-kapasitetsanalyse: Likvider vs SCR, CF/SCR-ratio
 *   5. Nøkkelobservasjoner (fra backend SmoltAllocationSummary)
 *
 * Props:
 *   allocationSummary : SmoltAllocationSummary fra backend
 *   facilities        : Array av SmoltFacilityInput (for detaljert tabell)
 */
export function SmoltAllocationTab({ allocationSummary, facilities }) {
  // SVG donut: 4 segmenter med farger
  // DARK_BLUE=bygg, MID_BLUE=maskiner, TEAL=biomasse, AMBER=BI
}
```

---

## S5.6 — Agaqua demo-eksempel i GUI

**Fil:** `frontend/src/data/agaquaExample.js` (ny fil)

```javascript
/**
 * Agaqua AS / Settefisk 1-gruppen — fullstendig demo-eksempel.
 * Tilgjengelig via "Last Agaqua-eksempel"-knapp i GUI.
 */
export const AGAQUA_EXAMPLE = {
  operator_name: "Agaqua AS",
  org_number: "930529591",
  facilities: [
    {
      facility_name: "Villa Smolt AS",
      facility_type: "smolt_ras",
      building_components: [
        { name: "Hall over fish tanks", area_sqm: 1370, value_per_sqm_nok: 27000 },
        { name: "RAS 1-2",              area_sqm: 530,  value_per_sqm_nok: 27000 },
        { name: "RAS 3-4",              area_sqm: 610,  value_per_sqm_nok: 27000 },
        { name: "Gamledelen",           area_sqm: 1393, value_per_sqm_nok: 27000 },
        { name: "Forlager",             area_sqm: 275,  value_per_sqm_nok: 27000 },
      ],
      site_clearance_nok:            20_000_000,
      machinery_nok:                200_000_000,
      avg_biomass_insured_value_nok: 39_680_409,
      bi_sum_insured_nok:           243_200_000,
      bi_indemnity_months: 24,
    },
    // ... Olden og Setran tilsvarende
  ],
  annual_revenue_nok:   232_248_232,
  equity_nok:            39_978_809,
  operating_cf_nok:      46_510_739,
  liquidity_nok:         55_454_950,
  claims_history_years:  10,
  total_claims_paid_nok: 0,
};
```

---

## S5.7 — App.jsx-integrasjon

**Fil:** `frontend/src/App.jsx`

Følgende endringer:

```jsx
// 1. Legg til operator_type i state
const [operatorType, setOperatorType] = useState('sea');  // 'sea' | 'smolt'

// 2. Kondisjonelt vis SmoltTIVPanel eller eksisterende panel
{operatorType === 'smolt'
  ? <SmoltTIVPanel facilities={smoltFacilities} onChange={setSmoltFacilities} />
  : <OperatorSection operator={operator} onChange={setOperator} />
}

// 3. Rut til riktig API-endepunkt
const apiUrl = operatorType === 'smolt'
  ? '/api/feasibility/smolt/run'
  : '/api/feasibility/run';

// 4. handleAgaquaExample() henter fra /api/feasibility/smolt/example/agaqua
```

---

## S5 — Akseptansekriterier

- [ ] Operator-type-velger vises og bytter mellom sjø og settefisk-flyt
- [ ] SmoltTIVPanel viser live TIV-beregning ved endring av inputs
- [ ] BI-kalkulator-widget fungerer med Agaqua-tall og gir riktig sum
- [ ] Agaqua-eksempel-knapp fyller alle felter korrekt
- [ ] SmoltAllocationTab viser donut-diagram og per-anlegg tabell
- [ ] Eksisterende sjøoppdrett-GUI er uberørt

---
---

## Samlet akseptansetest — alle sprintar fullført

```bash
# 1. Python-testsuite
pytest tests/ -q
# Forventet: 1 092 + (≥128 nye) tester passert, 0 feilet

# 2. Backend health check
curl http://localhost:8000/
# → {"status": "ok"}

# 3. Agaqua-eksempel via ny rute
curl http://localhost:8000/api/feasibility/smolt/example/agaqua | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['facilities'][0]['facility_name'])"
# → "Villa Smolt AS"

# 4. Full Agaqua-analyse
curl -X POST http://localhost:8000/api/feasibility/smolt/run \
  -H "Content-Type: application/json" \
  -d @data/agaqua_input.json | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
tiv = d['allocation']['total_tiv_nok']
verdict = d['baseline']['suitability_verdict']
print(f'TIV: NOK {tiv:,.0f}')
print(f'Verdict: {verdict}')
assert tiv > 1_100_000_000, f'TIV for lav: {tiv}'
assert verdict != 'NOT_SUITABLE', f'Feil verdict: {verdict}'
print('✅  Agaqua-analyse OK')
"

# 5. Frontend-build
cd frontend && npm run build
# → 0 errors

# 6. Sjø-pipeline regresjonstest
curl -X POST http://localhost:8000/api/feasibility/example | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Nordic Aqua Partners verdict:', d['verdict'])
print('✅  Sjø-pipeline uberørt')
"
```

---

## Fil-oversikt: nye filer per sprint

| Sprint | Ny fil | Kategori |
|--------|--------|----------|
| S1 | `data/input_schema.py` (utvidet) | Datamodell |
| S1 | `backend/services/smolt_operator_builder.py` | Service |
| S1 | `backend/schemas.py` (utvidet) | API |
| S1 | `backend/api/smolt_feasibility.py` | API |
| S1 | `tests/test_smolt_tiv_model.py` | Test |
| S2 | `risk_domains/ras_systems.py` | Domene |
| S2 | `models/smolt_calibration.py` | Modell |
| S2 | `config/smolt_scenarios.py` | Konfig |
| S2 | `tests/test_smolt_risk_domains.py` | Test |
| S3 | `c5ai_plus/forecasting/ras_water_quality_forecaster.py` | C5AI+ |
| S3 | `c5ai_plus/forecasting/biofilter_forecaster.py` | C5AI+ |
| S3 | `c5ai_plus/forecasting/smolt_health_forecaster.py` | C5AI+ |
| S3 | `c5ai_plus/forecasting/power_supply_forecaster.py` | C5AI+ |
| S3 | `c5ai_plus/data_models/smolt_biological_input.py` | C5AI+ |
| S3 | `c5ai_plus/alerts/smolt_alert_rules.py` | Alerts |
| S3 | `tests/test_smolt_c5ai.py` | Test |
| S4 | `models/smolt_generation_tracker.py` | Modell |
| S4 | `models/smolt_bi_calculator.py` | Modell |
| S4 | `tests/test_smolt_generation_bi.py` | Test |
| S5 | `frontend/src/components/InputForm/OperatorTypeSelector.jsx` | Frontend |
| S5 | `frontend/src/components/InputForm/SmoltTIVPanel.jsx` | Frontend |
| S5 | `frontend/src/components/InputForm/SmoltBIWidget.jsx` | Frontend |
| S5 | `frontend/src/components/results/SmoltAllocationTab.jsx` | Frontend |
| S5 | `frontend/src/data/smoltScenariosData.js` | Frontend |
| S5 | `frontend/src/data/agaquaExample.js` | Frontend |

**Totalt: 25 nye filer · 4 utvidede filer · 0 slettede filer**
**Estimert testdekning etter alle sprintar: ≥ 1 220 tester, 0 feilet**
