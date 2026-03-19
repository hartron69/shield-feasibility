# PCC Feasibility & Suitability Tool v2.0
## Brukermanual — med C5AI+ Biologisk Risikoprognose

**Utarbeidet av:** Shield Risk Consulting
**Versjon:** 2.0 (C5AI+ Integrasjon)
**Klassifisering:** Konfidensielt — Kun for operatør og rådgiver
**Plattform:** Python 3.10+ | Windows / macOS / Linux

---

## Innholdsfortegnelse

1. [Introduksjon og systemoversikt](#1-introduksjon-og-systemoversikt)
2. [Hva er nytt i versjon 2.0](#2-hva-er-nytt-i-versjon-20)
3. [Systemkrav og installasjon](#3-systemkrav-og-installasjon)
4. [Hurtigstart](#4-hurtigstart)
   - 4.1 [Modus A: Kun PCC-verktøy (statisk modell)](#41-modus-a-kun-pcc-verktøy-statisk-modell)
   - 4.2 [Modus B: Full C5AI+ integrert analyse](#42-modus-b-full-c5ai-integrert-analyse)
5. [Inputdata-guide: PCC-verktøyet](#5-inputdata-guide-pcc-verktøyet)
   - 5.1 [Filformat og struktur](#51-filformat-og-struktur)
   - 5.2 [Operatøridentitet](#52-operatøridentitet)
   - 5.3 [Lokaliteter (sites)](#53-lokaliteter-sites)
   - 5.4 [Forsikringsprogram](#54-forsikringsprogram)
   - 5.5 [Historiske tap](#55-historiske-tap)
   - 5.6 [Finansielt profil](#56-finansielt-profil)
   - 5.7 [Risikoparametere](#57-risikoparametere)
   - 5.8 [Strategipreferanser og C5AI+-felter](#58-strategipreferanser-og-c5ai-felter)
6. [Inputdata-guide: C5AI+ biologisk risikomodul](#6-inputdata-guide-c5ai-biologisk-risikomodul)
   - 6.1 [Hva C5AI+ trenger](#61-hva-c5ai-trenger)
   - 6.2 [Lokalitetsmetadata](#62-lokalitetsmetadata)
   - 6.3 [Miljøobservasjoner](#63-miljøobservasjoner)
   - 6.4 [Luseregistreringer](#64-luseregistreringer)
   - 6.5 [HAB-varsler](#65-hab-varsler)
   - 6.6 [Minimumskrav og datakvalitet](#66-minimumskrav-og-datakvalitet)
7. [Kjøre systemet](#7-kjøre-systemet)
   - 7.1 [PCC-verktøy: kommandolinje-argumenter](#71-pcc-verktøy-kommandolinje-argumenter)
   - 7.2 [C5AI+ pipeline: kommandolinje-argumenter](#72-c5ai-pipeline-kommandolinje-argumenter)
   - 7.3 [Anbefalt arbeidsflyt i to trinn](#73-anbefalt-arbeidsflyt-i-to-trinn)
   - 7.4 [Kjøre demo-eksemplet](#74-kjøre-demo-eksemplet)
   - 7.5 [Tolke fremdriftsvisningen](#75-tolke-fremdriftsvisningen)
8. [C5AI+ risikodomener og modeller](#8-c5ai-risikodomener-og-modeller)
   - 8.1 [HAB – Skadelige algeoppblomstringer](#81-hab--skadelige-algeoppblomstringer)
   - 8.2 [Lakselus](#82-lakselus)
   - 8.3 [Manet (Fase 2)](#83-manet-fase-2)
   - 8.4 [Patogener (Fase 2)](#84-patogener-fase-2)
   - 8.5 [Nettverksbasert risikospredning](#85-nettverksbasert-risikospredning)
9. [C5AI+ prognoseformat (risk_forecast.json)](#9-c5ai-prognoseformat-risk_forecastjson)
   - 9.1 [Feltbeskrivelse](#91-feltbeskrivelse)
   - 9.2 [Datakvalitetsflagg](#92-datakvalitetsflagg)
   - 9.3 [Skalafaktoren forklart](#93-skalafaktoren-forklart)
10. [De fire risikostrategiene](#10-de-fire-risikostrategiene)
    - 10.1 [Full forsikring](#101-full-forsikring)
    - 10.2 [Hybrid (stor egenandel)](#102-hybrid-stor-egenandel)
    - 10.3 [PCC Captive Cell](#103-pcc-captive-cell)
    - 10.4 [Selvforsikring](#104-selvforsikring)
11. [Analytiske moduler](#11-analytiske-moduler)
    - 11.1 [Monte Carlo-simulering](#111-monte-carlo-simulering)
    - 11.2 [Solvenskapitalkrav (SCR)](#112-solvenskapitalkrav-scr)
    - 11.3 [5-års totalkostnad for risiko (TCOR)](#113-5-års-totalkostnad-for-risiko-tcor)
    - 11.4 [Volatilitetsmetrikk](#114-volatilitetsmetrikk)
    - 11.5 [Egnethetsmotoren (6 kriterier)](#115-egnethetsmotoren-6-kriterier)
12. [Forstå PDF-rapporten](#12-forstå-pdf-rapporten)
    - 12.1 [Rapportstruktur](#121-rapportstruktur)
    - 12.2 [Tolke diagrammene](#122-tolke-diagrammene)
    - 12.3 [Tolke egnethetsscoren](#123-tolke-egnethetsscoren)
13. [Konfigurasjonsreferanse](#13-konfigurasjonsreferanse)
14. [Tilpasse til ny operatør](#14-tilpasse-til-ny-operatør)
15. [Testing og verifisering](#15-testing-og-verifisering)
16. [Vanlige spørsmål (FAQ)](#16-vanlige-spørsmål-faq)
17. [Feilsøking](#17-feilsøking)
18. [Metodikk og antakelser](#18-metodikk-og-antakelser)
19. [Ordliste](#19-ordliste)

---

## 1. Introduksjon og systemoversikt

**PCC Feasibility & Suitability Tool v2.0** er et kvantitativt analyseverktøy for norske og internasjonale akvakulturoperatører som vurderer om etablering av en Protected Cell Company (PCC) captive-forsikringsstruktur er hensiktsmessig.

### Systemet består av to integrerte komponenter

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   C5AI+ v5.0                    PCC Feasibility Tool v2.0           │
│   ──────────────                ──────────────────────────          │
│   Biologisk risikoprognose  →   Monte Carlo-simulering              │
│   HAB / Lus / Manet /           SCR-beregning                       │
│   Patogen                       4 strategimodeller                  │
│                                 Egnethetsanalyse (6 kriterier)      │
│   risk_forecast.json        →   PDF-rapport (styrenivå)             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**C5AI+ v5.0** er en AI/ML-plattform som analyserer biologiske og miljørelaterte risikofaktorer (havtemperatur, saltholdighet, historiske HAB-hendelser, luseregistreringer) og produserer disaggregerte risikoprognoser per lokalitet og risikotype.

**PCC Feasibility Tool** bruker disse prognosene til å kjøre en Monte Carlo-simulering med dynamiske, biologisk forankrede tapestimat — i stedet for den forenklede statiske Poisson-modellen. Resultatet er en mer realistisk og nyansert analyse som danner grunnlag for en profesjonell styreanbefaling.

### Hva systemet besvarer

- Er vår premie stor nok til at en PCC captive er levedyktig?
- Hva er den forventede totalkostnaden for risiko (TCOR) over 5 år under ulike strategier?
- Hva er vår biologiske tapseksponering, disaggregert per HAB / lus / manet / patogen?
- Hvilken solvenskapital (SCR) kreves, og kan vi finansiere den?
- Er vi klare til å drifte en captive-struktur?
- Hva er styrets anbefalte neste steg?

---

## 2. Hva er nytt i versjon 2.0

### C5AI+ biologisk risikointegrasjon

| Funksjon | v1.0 | v2.0 |
|---|---|---|
| Monte Carlo-tapmodell | Statisk Compound Poisson | Dynamisk — skalert av C5AI+ |
| Biologisk risiko | Samlet (ikke disaggregert) | HAB / Lus / Manet / Patogen separat |
| Lokalitetsrisikonett | Nei | networkx-basert naboskapsrisiko |
| Egnethetsscoring | 5 kriterier (100%) | 6 kriterier (100% med nytt biologisk kriterie) |
| Datakvalitetsrapportering | Nei | Ja — SUFFICIENT / LIMITED / POOR / PRIOR_ONLY |
| Fallback ved manglende data | N/A | Automatisk til statisk modell |

### Oppdaterte vekter i egnethetsmotoren

| Kriterie | v1.0 | v2.0 |
|---|---|---|
| 1. Premiumvolum | 25,0% | 22,5% |
| 2. Tapsstabilitet | 20,0% | 18,0% |
| 3. Balanseregnskapsstyrke | 20,0% | 18,0% |
| 4. Kostnadsbesparelsespotensial | 20,0% | 18,0% |
| 5. Operasjonell beredskap | 15,0% | 13,5% |
| 6. Biologisk operasjonell beredskap | — | 10,0% |

### Nye inputfelter

To nye valgfrie felter i PCC-verktøyets JSON-input:
- `c5ai_forecast_path` — sti til prognosefilens `risk_forecast.json`
- `bio_readiness_score` — operatørens egenvurderte biologiske beredskapsscore (0–100)

---

## 3. Systemkrav og installasjon

### Krav

| Krav | Minimum | Anbefalt |
|---|---|---|
| Python | 3.10 | 3.12+ |
| RAM | 4 GB | 8 GB |
| Diskplass | 500 MB | 1 GB |
| OS | Windows 10 / macOS 12 / Ubuntu 20.04 | Nyeste versjon |

### Installasjon

**Steg 1 — Klon eller pakk ut prosjektet**
```bash
cd C:\Users\<bruker>\dev\shield-feasibility
```

**Steg 2 — Opprett og aktiver virtuelt miljø**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**Steg 3 — Installer avhengigheter**
```bash
pip install -r requirements.txt
```

**Steg 4 — Verifiser installasjonen**
```bash
python main.py
```
Forventet output: Rapporten `pcc_report_<dato>_<tid>.pdf` opprettes og systemet skriver ut nøkkelresultater.

**Steg 5 — Verifiser C5AI+ (valgfritt)**
```bash
python examples/run_c5ai_demo.py
```

### Valgfrie avanserte pakker (for CATE/T-Learner)

```bash
pip install econml lightgbm xgboost
```

Disse pakkene er ikke nødvendige for grunnleggende drift. C5AI+ fungerer fullt ut uten dem ved å bruke enklere prediksjonsmodeller.

---

## 4. Hurtigstart

### 4.1 Modus A: Kun PCC-verktøy (statisk modell)

Bruk dette når du ikke har biologiske observasjonsdata tilgjengelig, eller ønsker en rask analyse basert på de statistiske parameterne alene.

```bash
python main.py --input data/sample_input.json
```

Systemet kjører den komplette analysen på under 10 sekunder og produserer en PDF-rapport.

### 4.2 Modus B: Full C5AI+ integrert analyse

Bruk dette for en biologisk forankret analyse med disaggregerte risikoprognoser.

**Trinn 1 — Forbered C5AI+ inputdata**

Opprett en JSON-fil (se seksjon 6) med biologiske observasjoner, eller bruk demo-inndataene:
```bash
# Bygg syntetiske inputdata og generer prognosen
python examples/run_c5ai_demo.py
```
Dette oppretter `examples/demo_risk_forecast.json`.

**Trinn 2 — Koble prognosen til PCC-analysen**

Legg til feltet `c5ai_forecast_path` i din operatørinputs JSON-fil:
```json
{
  "name": "Nordic Aqua Partners AS",
  ...
  "c5ai_forecast_path": "examples/demo_risk_forecast.json"
}
```

**Trinn 3 — Kjør PCC-analysen**
```bash
python main.py --input data/sample_input.json --simulations 20000
```

Systemet oppdager automatisk prognosen, viser skalafaktoren og produserer en beriket rapport.

---

## 5. Inputdata-guide: PCC-verktøyet

### 5.1 Filformat og struktur

Input er en JSON-fil med UTF-8-enkoding. Filen har følgende toppnivåstruktur:

```json
{
  "name": "Operatørnavn AS",
  "registration_number": "987654321",
  "country": "Norway",
  "reporting_currency": "NOK",
  "sites": [...],
  "current_insurance": {...},
  "historical_losses": [...],
  "financials": {...},
  "risk_params": {...},
  "captive_domicile_preference": "Guernsey",
  "management_commitment_years": 7,
  "willing_to_provide_capital": true,
  "has_risk_manager": false,
  "governance_maturity": "developing",
  "c5ai_forecast_path": null,
  "bio_readiness_score": null
}
```

Alle beløp er i **NOK (norske kroner)**. Formater store beløp som heltall uten tusenskilletegn i JSON (f.eks. `19500000`, ikke `19.500.000`).

### 5.2 Operatøridentitet

| Felt | Type | Beskrivelse | Eksempel |
|---|---|---|---|
| `name` | tekst | Selskapets fulle juridiske navn | `"Nordic Aqua Partners AS"` |
| `registration_number` | tekst | Organisasjonsnummer | `"987654321"` |
| `country` | tekst | Registreringsland | `"Norway"` |
| `reporting_currency` | tekst | Alltid `"NOK"` for norske operatører | `"NOK"` |

### 5.3 Lokaliteter (sites)

En liste med ett objekt per produksjonslokalitet. Minst én lokalitet kreves.

```json
{
  "name": "Hardanger Nord",
  "location": "Hardangerfjorden, Hordaland",
  "species": "Atlantic Salmon",
  "biomass_tonnes": 2100,
  "biomass_value_per_tonne": 72000,
  "equipment_value": 45000000,
  "infrastructure_value": 22000000,
  "annual_revenue": 320000000
}
```

| Felt | Enhet | Beskrivelse |
|---|---|---|
| `name` | — | Lokalitetsnavn |
| `location` | — | Geografisk beskrivelse |
| `species` | — | Primær art (f.eks. `"Atlantic Salmon"`) |
| `biomass_tonnes` | tonn | Maksimal stående biomasse |
| `biomass_value_per_tonne` | NOK/t | Markedsverdi per tonn levende fisk |
| `equipment_value` | NOK | Verdi av nøter, fôringsanlegg, båter, merder |
| `infrastructure_value` | NOK | Verdi av fortøyninger, bygg, rør |
| `annual_revenue` | NOK | Lokalitetens årlige omsetning |

**Total forsikringsverdi (TIV)** beregnes automatisk:
```
TIV = (biomass_tonnes × biomass_value_per_tonne) + equipment_value + infrastructure_value
```

### 5.4 Forsikringsprogram

Beskriver eksisterende forsikringsstruktur.

```json
{
  "annual_premium": 19500000,
  "per_occurrence_deductible": 500000,
  "annual_aggregate_deductible": 1000000,
  "coverage_limit": 500000000,
  "aggregate_limit": 750000000,
  "coverage_lines": ["Mortality", "Property", "Business Interruption"],
  "insurer_names": ["Gard AS", "Storebrand"],
  "current_loss_ratio": 0.52,
  "market_rating_trend": 0.05
}
```

| Felt | Enhet | Beskrivelse |
|---|---|---|
| `annual_premium` | NOK | Total forsikringspremie per år |
| `per_occurrence_deductible` | NOK | Egenandel per hendelse |
| `annual_aggregate_deductible` | NOK | Samlet egenandel per år |
| `coverage_limit` | NOK | Maksimal utbetaling per hendelse |
| `aggregate_limit` | NOK | Maksimal utbetaling per år |
| `coverage_lines` | liste | Forsikringslinjer som er dekket |
| `insurer_names` | liste | Navn på assurandører/syndikater |
| `current_loss_ratio` | desimal | Historisk skadeprosent (tap/premie) |
| `market_rating_trend` | desimal | Forventet årlig premievekst (f.eks. `0.05` = +5%/år) |

> **Tips:** `market_rating_trend` har stor effekt på prissammenligningen over 5 år. En positiv verdi (stigning) gjør captive-alternativet relativt mer attraktivt over tid.

### 5.5 Historiske tap

En liste med tapshendelser. Kan være tom, men minst 3 år med data gir bedre beregninger.

```json
[
  {
    "year": 2022,
    "event_type": "mortality",
    "gross_loss": 8500000,
    "insured_loss": 7200000,
    "retained_loss": 1300000
  }
]
```

| Felt | Beskrivelse |
|---|---|
| `year` | Kalenderår for hendelsen |
| `event_type` | `"mortality"`, `"property"`, `"liability"` eller `"business_interruption"` |
| `gross_loss` | Totalt økonomisk tap (NOK) før forsikringsoppgjør |
| `insured_loss` | Beløp dekket av forsikring (NOK) |
| `retained_loss` | Operatørens egne tap (NOK) |

### 5.6 Finansielt profil

Nøkkeltall fra regnskapet. Brukes av solvens- og egnethetsmodulene.

```json
{
  "annual_revenue": 897000000,
  "ebitda": 179400000,
  "total_assets": 1450000000,
  "net_equity": 620000000,
  "credit_rating": "BB+",
  "free_cash_flow": 98000000,
  "years_in_operation": 12
}
```

| Felt | Enhet | Beskrivelse |
|---|---|---|
| `annual_revenue` | NOK | Konsolidert omsetning |
| `ebitda` | NOK | EBITDA (resultat før renter, skatt, avskrivninger) |
| `total_assets` | NOK | Sum eiendeler (balansesum) |
| `net_equity` | NOK | Egenkapital |
| `credit_rating` | tekst | Kredittvurdering eller `null` |
| `free_cash_flow` | NOK | Tilgjengelig kontantstrøm for kapitalformål |
| `years_in_operation` | år | Antall driftsår |

> **Viktig:** `net_equity` og `free_cash_flow` påvirker direkte Kriterie 3 (Balanseregnskapsstyrke) i egnethetsscoren. Lave verdier her kan gjøre PCC uhensiktsmessig selv om premien er stor.

### 5.7 Risikoparametere

Statistiske parametere for tapsdistribusjonen. Disse leveres av aktuaren eller estimeres fra historiske data.

```json
{
  "expected_annual_events": 3.2,
  "mean_loss_severity": 7100000,
  "cv_loss_severity": 1.2,
  "catastrophe_probability": 0.05,
  "catastrophe_loss_multiplier": 5.0,
  "inter_site_correlation": 0.35,
  "bi_trigger_threshold": 2000000,
  "bi_daily_revenue_loss": 130000,
  "bi_average_interruption_days": 25
}
```

| Felt | Enhet | Beskrivelse |
|---|---|---|
| `expected_annual_events` | hendelser/år | Forventet antall tap-genererende hendelser |
| `mean_loss_severity` | NOK | Forventet tap per hendelse |
| `cv_loss_severity` | desimal | Variasjonskoeffisient for tapenes størrelse |
| `catastrophe_probability` | desimal | Sannsynlighet for katastrofehendelse per år |
| `catastrophe_loss_multiplier` | x | Katastrofetap som multiplikator av gjennomsnittlig tap |
| `inter_site_correlation` | desimal | Korrelasjon mellom lokaliteters tap (0–1) |
| `bi_trigger_threshold` | NOK | Tap som utløser driftsavbruddsforsikring |
| `bi_daily_revenue_loss` | NOK/dag | Daglig omsetningsbortfall ved avbrudd |
| `bi_average_interruption_days` | dager | Gjennomsnittlig avbruddstid per hendelse |

> **Veiledning — Calibrering av risikoparametere:**
>
> Dersom historiske tap er tilgjengelige, kan disse brukes til å estimere `expected_annual_events` og `mean_loss_severity`. Som utgangspunkt:
> - `expected_annual_events` ≈ antall rapporterte hendelser / antall år
> - `mean_loss_severity` ≈ total tapsvolumet / antall hendelser
> - `cv_loss_severity`: bruk 0.8–1.5 for akvakultur (høy naturlig variasjon)
> - `catastrophe_probability`: typisk 3–10% for norsk lakseoppdrett

### 5.8 Strategipreferanser og C5AI+-felter

```json
{
  "captive_domicile_preference": "Guernsey",
  "management_commitment_years": 7,
  "willing_to_provide_capital": true,
  "has_risk_manager": false,
  "governance_maturity": "developing",
  "c5ai_forecast_path": "risk_forecast.json",
  "bio_readiness_score": 55
}
```

| Felt | Gyldige verdier | Beskrivelse |
|---|---|---|
| `captive_domicile_preference` | tekst / `null` | Ønsket domisil (f.eks. `"Guernsey"`, `"Cayman Islands"`, `"Malta"`) |
| `management_commitment_years` | heltall | Ledelsens forpliktelseshorisont i år |
| `willing_to_provide_capital` | `true`/`false` | Villighet til å kapitalisere PCC-celle |
| `has_risk_manager` | `true`/`false` | Har dedikert risikostyringsansvarlig |
| `governance_maturity` | `"basic"`, `"developing"`, `"mature"` | Selskapets governance-modenhet |
| `c5ai_forecast_path` | filsti / `null` | Sti til `risk_forecast.json` fra C5AI+ |
| `bio_readiness_score` | 0–100 / `null` | Egenvurdert biologisk beredskapsscore |

**Om `governance_maturity`:**
- `"basic"` — Grunnleggende styring, ingen formelle risikokomiteer
- `"developing"` — Risikorapportering er etablert, men ikke fullt integrert
- `"mature"` — Formell risikostyring med dedikert komité og årsrapportering

**Om `bio_readiness_score` (0–100):**
- 0–20: Ingen biologisk risikostyring
- 21–40: Grunnleggende overvåking (manuelle telleringer, sporadiske kontroller)
- 41–60: Jevnlig overvåking, skriftlige respons-protokoller
- 61–80: Integrerte overvakningssystemer, trenet personell
- 81–100: Sanntidsovervåking, automatiserte varsler, PhD-kompetanse internt

Dersom `null`, beregner systemet scoren automatisk basert på C5AI+-datakvalitet eller governance-proxy.

---

## 6. Inputdata-guide: C5AI+ biologisk risikomodul

### 6.1 Hva C5AI+ trenger

C5AI+ tar en separat JSON-inputfil med biologiske og miljørelaterte observasjoner. Denne filen er **uavhengig** av PCC-verktøyets inputfil.

```
c5ai_input.json → C5AI+ pipeline → risk_forecast.json → PCC-verktøyet
```

Eksempel på C5AI+-inputfilstruktur:

```json
{
  "operator_id": "nordic-aqua-001",
  "operator_name": "Nordic Aqua Partners AS",
  "forecast_years": 5,
  "sites": [...],
  "env_observations": [...],
  "lice_observations": [...],
  "hab_alerts": [...]
}
```

### 6.2 Lokalitetsmetadata

Én post per lokalitet. Koordinater brukes til nettverksrisikoanalyse.

```json
{
  "site_id": "hardanger-nord",
  "site_name": "Hardanger Nord",
  "latitude": 60.45,
  "longitude": 6.10,
  "species": "Atlantic Salmon",
  "biomass_tonnes": 2100,
  "biomass_value_nok": 151200000,
  "years_in_operation": 9,
  "fjord_exposure": "semi_exposed"
}
```

| Felt | Beskrivelse |
|---|---|
| `site_id` | Unik nøkkel (brukes internt) |
| `site_name` | Lesbart navn |
| `latitude` / `longitude` | Desimalgrader (WGS84) |
| `biomass_value_nok` | Total biomasseverdi i NOK — brukes til tapsberegning |
| `fjord_exposure` | `"open_coast"`, `"semi_exposed"` eller `"sheltered"` |

> `site_id` skal være konsistent mellom `sites`, `env_observations`, `lice_observations` og `hab_alerts`.

### 6.3 Miljøobservasjoner

Månedlige målinger per lokalitet. Havtemperatur er den viktigste driveren for alle biologiske risikomodeller.

```json
{
  "site_id": "hardanger-nord",
  "year": 2024,
  "month": 7,
  "sea_temp_celsius": 16.2,
  "salinity_ppt": 33.1,
  "chlorophyll_ug_l": null,
  "current_speed_ms": null
}
```

| Felt | Enhet | Beskrivelse |
|---|---|---|
| `site_id` | — | Lokalitetsnøkkel |
| `year` | — | Kalenderår |
| `month` | 1–12 | Kalendermåned |
| `sea_temp_celsius` | °C | Overflatetemperatur (viktigst) |
| `salinity_ppt` | ppt | Saltholdighet i promille |
| `chlorophyll_ug_l` | µg/L | Klorofyll-a konsentrasjon (HAB-indikator) |
| `current_speed_ms` | m/s | Strømhastighet |

**Manglende data:** Sett felter til `null` der målinger ikke foreligger. Systemet imputerer med stedsspesifikke gjennomsnitter. Høy andel `null` degraderer datakvalitetsflagget.

**Datakilder tilgjengelig for Norge:**
- Havforskningsinstituttet NorKyst800 (havtemperatur og saltholdighet)
- Meteorologisk institutt (overflatetemperatur)
- Nansen senter (satellittbasert havoverflatetemperatur)

### 6.4 Luseregistreringer

Ukentlige lusetellinger per lokalitet. Brukes av `LiceForecaster`.

```json
{
  "site_id": "hardanger-nord",
  "year": 2024,
  "week": 25,
  "avg_lice_per_fish": 0.48,
  "treatment_applied": false,
  "treatment_type": null
}
```

| Felt | Beskrivelse |
|---|---|
| `week` | ISO-ukenummer (1–53) |
| `avg_lice_per_fish` | Gjennomsnittlig antall voksne hunnlus per fisk |
| `treatment_applied` | `true` hvis behandling ble gjennomført denne uken |
| `treatment_type` | `"bath"`, `"in-feed"`, `"mechanical"`, `"laser"` eller `null` |

**Norsk regulatorisk grense:** 0,5 voksne hunnlus per fisk. Overskridelse er en triggerhendelse i modellen.

**Datakilde:** Barentswatch Lakselus API (offentlig tilgjengelig for alle norske matfiskanlegg).

### 6.5 HAB-varsler

Registrerte hendelser med skadelige algeoppblomstringer.

```json
{
  "site_id": "hardanger-nord",
  "year": 2023,
  "month": 7,
  "alert_level": "medium",
  "species": "Chrysochromulina leadbeateri",
  "duration_days": 8,
  "loss_nok": 2800000
}
```

| Felt | Gyldige verdier | Beskrivelse |
|---|---|---|
| `alert_level` | `"low"`, `"medium"`, `"high"`, `"critical"` | Alarmsnivå |
| `species` | tekst / `null` | Årsaksorganisme |
| `duration_days` | heltall / `null` | Varighet i dager |
| `loss_nok` | NOK / `null` | Registrert økonomisk tap |

**Datakilder:**
- Mattilsynet HAB-kart
- Algae24 (Havforskningsinstituttet)
- Interne driftslogger

### 6.6 Minimumskrav og datakvalitet

C5AI+ fungerer med **null observasjoner** — det bruker da prior-distribusjoner fra konfigurasjonen. Men resultatkvaliteten er sterkt knyttet til tilgjengelig data:

| Datakvalitetsflagg | Krav | Modell som brukes |
|---|---|---|
| `SUFFICIENT` | ≥24 månedlige obs., ≥70% ikke-manglende temp. | RandomForest ML-modell |
| `LIMITED` | 10–23 måneder eller 40–69% dekning | Prior justert med historikk |
| `POOR` | <10 måneder eller 10–39% dekning | Prior-distribusjon |
| `PRIOR_ONLY` | <10% dekning eller ingen data | Ren prior fra konfig. |

Datakvalitetsflagget vises tydelig i prognosefilen og rapporten, slik at brukeren alltid er klar over usikkerhetsnivået.

---

## 7. Kjøre systemet

### 7.1 PCC-verktøy: kommandolinje-argumenter

```
python main.py [--input INPUTFIL] [--output OUTPUTFIL] [--simulations N]
```

| Argument | Kort | Standard | Beskrivelse |
|---|---|---|---|
| `--input` | `-i` | `data/sample_input.json` | Sti til operatørens JSON-inputfil |
| `--output` | `-o` | Autogenerert (tidsstempel) | Navn og sti på PDF-rapport |
| `--simulations` | `-n` | `10000` | Antall Monte Carlo-simuleringer |

**Eksempler:**
```bash
# Standard kjøring med eksempeldata
python main.py

# Egendefinert operatørinput
python main.py --input min_operatoer.json

# Høy presisjon (20 000 simuleringer) med navngitt rapport
python main.py --input min_operatoer.json --output styreanalyse_2026.pdf --simulations 20000

# Rask test (2 000 simuleringer)
python main.py -n 2000
```

**Presisjonsveiledning:**
- 5 000 sim: Rask test, ±3% presisjon på VaR 99,5%
- 10 000 sim: Standardanbefaling, god presisjon for styreformål
- 20 000 sim: Høy presisjon, anbefalt ved endelig rapport til styre/revisor

### 7.2 C5AI+ pipeline: kommandolinje-argumenter

```
python -m c5ai_plus.pipeline [--input INPUTFIL] [--output OUTPUTFIL] [--static-loss BELOEP]
```

| Argument | Kort | Standard | Beskrivelse |
|---|---|---|---|
| `--input` | `-i` | (påkrevd) | Sti til C5AI+ biologisk inputfil |
| `--output` | `-o` | `risk_forecast.json` | Sti til prognosefil som skal opprettes |
| `--static-loss` | `-s` | `0` | Statisk modellens E[arlig tap] i NOK (for skalafaktorberegning) |

**Eksempler:**
```bash
# Enkel kjøring med syntetiske data
python -m c5ai_plus.pipeline --input c5ai_input.json --output risk_forecast.json

# Med korrekt statisk tapsreferanse
python -m c5ai_plus.pipeline \
  --input c5ai_input.json \
  --output risk_forecast.json \
  --static-loss 22600000
```

> **Tips:** `--static-loss` hentes fra PCC-verktøyets konsoloutput etter første kjøring (se linjen `E[arlig tap]`). Kjør PCC-verktøyet uten C5AI+ først for å få dette tallet.

### 7.3 Anbefalt arbeidsflyt i to trinn

```
Trinn 1: Kjør PCC-verktøy uten C5AI+ for å få statisk tapsvurdering
──────────────────────────────────────────────────────────────────
python main.py --input min_operatoer.json

  → Noter: E[arlig tap] = NOK 22.6 M
  → Lagrer: pcc_rapport_v1.pdf (statisk analyse)

Trinn 2: Kjør C5AI+ med statisk tap som referanse
──────────────────────────────────────────────────────────────────
python -m c5ai_plus.pipeline \
  --input c5ai_input.json \
  --output risk_forecast.json \
  --static-loss 22600000

  → Oppretter: risk_forecast.json
  → Viser: Skalafaktor = 1.281, HAB=46%, Lus=37%, ...

Trinn 3: Kjør PCC-verktøy med C5AI+ integrert
──────────────────────────────────────────────────────────────────
# Legg til i min_operatoer.json:
# "c5ai_forecast_path": "risk_forecast.json"

python main.py --input min_operatoer.json --simulations 20000

  → Produserer: pcc_rapport_v2_c5ai_beriket.pdf
```

### 7.4 Kjøre demo-eksemplet

For å se hele systemet i aksjon med syntetiske data for Nordic Aqua Partners AS:

```bash
python examples/run_c5ai_demo.py
```

Demoet:
1. Bygger syntetisk C5AI+ input (3 lokaliteter, 3 år med havtemperatur, lusestatus, én HAB-hendelse)
2. Kjører C5AI+ pipeline og viser prognose per risikotype
3. Kjører PCC-verktøyet med C5AI+ integrert
4. Sammenligner nøkkeltall: statisk vs. C5AI+-beriket modell

### 7.5 Tolke fremdriftsvisningen

Typisk konsoloutput med C5AI+ aktiv:

```
==============================================================
   PCC FEASIBILITY & SUITABILITY TOOL  v2.0
   C5AI+ Biologisk Risikoprognose Integrert
   Shield Risk Consulting
==============================================================

  [####------------------------] 1/9  Validering av inputdata...
       Operator  : Nordic Aqua Partners AS
       Land      : Norway
       TIV       : NOK 886.9 M
       Omsetning : NOK 897.0 M
       Premie    : NOK 19.5 M

  [########--------------------] 2/9  Monte Carlo-simulering (10 000 kjoringer x 5 ar)...
       [C5AI+] Forecast loaded: scale=1.281 | HAB=46.0% | Lice=37.0% | Jellyfish=3.6% | Pathogen=13.5%
       E[arlig tap]    : NOK 28.9 M
       VaR 99.5%       : NOK 171.9 M
       TVaR 95%        : NOK 111.6 M

  [############----------------] 3/9  Modellerer risikostrategi...
  ...
  [############################] 9/9  Genererer PDF-rapport...
       Report saved : pcc_report_20260306_102500.pdf
       Elapsed      : 6.8s
```

| Linje | Forklaring |
|---|---|
| `scale=1.281` | C5AI+ anslår 28,1% høyere biologisk risiko enn statisk modell |
| `HAB=46.0%` | 46% av forventet biologisk tap skyldes HAB |
| `E[arlig tap]` | Forventet gjennomsnittlig årlig bruttotap |
| `VaR 99.5%` | Tapsgrense som overskrides kun i 0,5% av scenariene — SCR-anker |
| `TVaR 95%` | Forventet tap gitt at vi befinner oss i de 5% verste scenariene |

---

## 8. C5AI+ risikodomener og modeller

### 8.1 HAB – Skadelige algeoppblomstringer

**Hva modelleres:** Sannsynligheten for at en HAB-hendelse inntreffer og medfører biomassedød.

**Viktigste HAB-typer i norsk akvakultur:**
- *Chrysochromulina leadbeateri* — Flagellat, dreper fisk ved høye konsentrasjoner
- *Karenia mikimotoi* — Dinoflagellat, lavt oksygennivå
- *Chattonella* spp. — Raphidophyt, gjelleskader

**Modelllogikk:**
- ML-modell (RandomForestClassifier) trenes på havtemperatur, klorofyll-a, saltholdighet
- Prior: 12% årlig sannsynlighet per lokalitet (konfigurerbart)
- Temperaturjustering: HAB-risiko øker ved temperaturer over 20°C
- Nettverkseffekt: Lokaliteter innen 50 km deler vannmassene og risikovurderes som koblet

**Tapsfunksjon:** Betinget på HAB-hendelse, modelleres tap som LogNormal med gjennomsnitt = 18% av biomasseverdi.

### 8.2 Lakselus

**Hva modelleres:** Sannsynligheten for å overskride 0,5 voksne hunnlus per fisk, og de tilhørende behandlingskostnadene og biomassatapene.

**Modelllogikk:**
- ML-modell (RandomForestRegressor) predikerer ukentlig lusebyrde
- Features: havtemperatur, forrige målings lusenivå, sesong, behandlingsstatus
- Prior: 30% årlig overskridelsessannsynlighet (konfigurerbart)
- Behandlingskostnad: NOK 4 500 per tonn biomasse (konfigurerbart)

**Tapsfunksjon:**
```
Totalt tap = Behandlingskostnad + Biomassatap
           = 4 500 × tonnasje + 6% × biomasseverdi (betinget på hendelse)
```

**Regulatorisk relevans:** Mattilsynet kan pålegge tidlig slakt ved vedvarende overskridelse, noe som medfører store margintap.

### 8.3 Manet (Fase 2)

**Status:** Placeholder — bruker prior-distribusjon fra konfigurasjon.

**Prior (standard):**
- Hendelsessannsynlighet: 8% per år per lokalitet
- Tapsfunksjon: 4% av biomasseverdi (betinget LogNormal, CV=0,70)

**Planlagt for Fase 2:** ML-modell basert på fjordobservasjoner fra Havforskningsinstituttet og kameradata fra manettellings-sensornettverk.

### 8.4 Patogener (Fase 2)

**Status:** Placeholder — bruker prior-distribusjon fra konfigurasjon.

**Dekker:** Bakterielle (Moritella viscosa, Aeromonas salmonicida) og virale (IHN, ISA, VHS) patogener.

**Prior (standard):**
- Hendelsessannsynlighet: 10% per år per lokalitet
- Tapsfunksjon: 12% av biomasseverdi (betinget LogNormal, CV=0,65)

**Planlagt for Fase 2:** Barentswatch veterinærrapporter og Fiskeridirektoratets slaktedata.

### 8.5 Nettverksbasert risikospredning

**Hva dette betyr:** Lokaliteter innen 50 km (konfigurerbart) anses som biologisk koblet gjennom delte vannmasser, strømsystemer og smittevektorer.

**Effekt i modellen:**
- En lokalitet med to naboer innen 30 km får en risikoulempe (multiplikator > 1,0)
- Multiplikatoren beregnes som: `1 + min(0,50, Σ nabo-vekter × 0,15)`
- Nabovekten avtar eksponentielt med avstand (decay = 0,05 per km)

**Eksempel:**
- Site A har to naboer på 15 km og 25 km
- Vekter: exp(-0,05×15)=0,47 og exp(-0,05×25)=0,29
- Risikomultiplikator: 1 + min(0,50, (0,47+0,29)×0,15) = 1 + 0,114 = **1,114**
- Alle biologiske tapestimater for Site A skaleres med 1,114

---

## 9. C5AI+ prognoseformat (risk_forecast.json)

### 9.1 Feltbeskrivelse

Prognosefilen er den eneste koblingen mellom C5AI+ og PCC-verktøyet.

**Toppnivåstruktur:**
```json
{
  "metadata": {...},
  "site_forecasts": [...],
  "operator_aggregate": {...}
}
```

**`metadata`-felter:**

| Felt | Beskrivelse |
|---|---|
| `model_version` | C5AI+-versjon (f.eks. `"5.0.0"`) |
| `generated_at` | ISO 8601 tidsstempel for genereringstidspunkt |
| `operator_id` | Unik identifikator |
| `forecast_horizon_years` | Antall år prognosen gjelder |
| `overall_confidence` | `"high"`, `"medium"` eller `"low"` |
| `overall_data_quality` | `"SUFFICIENT"`, `"LIMITED"`, `"POOR"` eller `"PRIOR_ONLY"` |
| `warnings` | Liste med advarsler om datakvalitet eller modellbegrensninger |

**`site_forecasts[].annual_forecasts[]`-felter (én per år per risikotype):**

| Felt | Enhet | Beskrivelse |
|---|---|---|
| `risk_type` | — | `"hab"`, `"lice"`, `"jellyfish"` eller `"pathogen"` |
| `year` | — | Prognoseår (1 = første år) |
| `event_probability` | 0–1 | Sannsynlighet for minst én signifikant tapshendelse |
| `expected_loss_mean` | NOK | Forventet tap (gjennomsnitt av distribusjon) |
| `expected_loss_p50` | NOK | Median forventet tap |
| `expected_loss_p90` | NOK | 90. persentil — stressert scenario |
| `confidence_score` | 0–1 | Modellens selvvurderte tillit til prognosen |
| `data_quality_flag` | — | Datakvalitetsflagg for denne lokalitet og risikotype |

**`operator_aggregate`-felter (konsumeres direkte av MonteCarloEngine):**

| Felt | Beskrivelse |
|---|---|
| `annual_expected_loss_by_type` | NOK per risikotype per år (gjennomsnitt over prognoseperioden) |
| `total_expected_annual_loss` | Sum av alle risikotypers forventede årstap |
| `c5ai_vs_static_ratio` | **Skalafaktor** — brukes i Monte Carlo-simulering |
| `loss_breakdown_fractions` | Andel av total tapslast per risikotype (summerer til 1,0) |

### 9.2 Datakvalitetsflagg

| Flagg | Datadekning | Modell | Anbefalt tolkning |
|---|---|---|---|
| `SUFFICIENT` | ≥70%, ≥24 måneder | RandomForest ML | Pålitelig — bruk i styredokumenter |
| `LIMITED` | 40–69% | Prior + historikk | Forsvarlig — noter usikkerhet |
| `POOR` | 10–39% | Prior-distribusjon | Indikativ — krev bedre data |
| `PRIOR_ONLY` | <10% | Ren prior | Svært usikker — kun foreløpig screening |

### 9.3 Skalafaktoren forklart

`c5ai_vs_static_ratio` er kjerneresultatet fra C5AI+ i integrasjonssammenheng.

**Tolkning:**

| Skalafaktor | Betydning |
|---|---|
| < 0,80 | C5AI+ anslår vesentlig lavere biologisk risiko enn statisk modell |
| 0,80–1,20 | C5AI+ og statisk modell er i rimelig overensstemmelse |
| > 1,20 | C5AI+ identifiserer vesentlig høyere biologisk risiko enn antatt |
| > 2,00 | Uvanlig høy — sjekk inputdata og advarsler i metadata |

**Hva som skjer i Monte Carlo:**
```
Justerte simulerte tap = Statiske simulerte tap × skalafaktor
```

Fordelingens form (Poisson-frekvens, LogNormal-alvorlighet) bevares. Bare nivået skaleres. Dette betyr at VaR, TVaR og standardavvik alle skaleres proporsjonalt.

---

## 10. De fire risikostrategiene

### 10.1 Full forsikring

**Konsept:** Operatøren fortsetter med eksisterende markedsforsikring, eventuelt med justeringer for premietrender.

**Kostnadsstruktur:**
```
Arlig kostnad = Premie × (1 + premietrend)^ar + Forventet egenandelsforbruk + Admin
```

**Nøkkelantakelse:** Premien stiger med `market_rating_trend` per år (typisk 3–8% for norsk fiskeoppdrett).

**Bruk som:** Referansebaseline. Alle andre strategiers kostnader sammenlignes mot denne.

### 10.2 Hybrid (stor egenandel)

**Konsept:** Operatøren tar høyere egenandel (retention layer), kjøper overskytende dekning (XS) fra markedet. Premierabatt kompenserer for beholdt risiko.

**Standard parametere:**
- Egenandel: 25% av forventet arlig tap (konfigurerbart)
- Premierabatt på beholdt risiko: 30%
- Administrativt tillegg: 1,5% av basispremie

**Passer for:** Operatører med sterk kontantstrøm som tåler mer frekvensrisiko, men ønsker katastrofebeskyttelse.

### 10.3 PCC Captive Cell

**Konsept:** Operatøren etablerer en beskyttet celle i en Protected Cell Company (PCC). Cellen skriver forsikring mot egne tapseksponeringer, finansierer reservekapital og investerer premieoverskuddet.

**Kostnadsstruktur:**
```
Arlig nettokostnad = Premie til celle + Frontingavgift + Celleforvaltningsavgift
                   + Forventede tap betalt av celle
                   - Investeringsinntekt på reservekapital
                   - Kapitalfrigjøring ved gunstig skadeerfaring
```

**Nøkkelparametere (konfigurerbart i `config/settings.py`):**

| Parameter | Standard | Beskrivelse |
|---|---|---|
| Etableringskostnad | NOK 1,25 M | Juridisk, aktuarielt og regulatorisk |
| Arlig celleforvaltningsavgift | NOK 475 000 | Administrasjon og rapportering |
| Premierabatt | 22% | Sparing vs. markedspremie |
| Frontingavgift | 3% av premie | Frontingsassurandøren |
| Investeringsavkastning på reserver | 4% | Konservativt rentenivå |
| Startkapital | = SCR (99,5% VaR) | Solvens II-inspirert |

**Minimum for levedyktighet:** NOK 5,25 M i arlig premie.

**Anbefalte domisiler for norske operatører:**
- **Guernsey** — Robust regulatorisk rammeverk, anerkjent av norske tilsynsmyndigheter
- **Isle of Man** — Fleksibel PCC-lovgivning
- **Malta** — EU-basert, enkel tilgang til europeiske markeder
- **Cayman Islands** — Populær for komplekse strukturer

### 10.4 Selvforsikring

**Konsept:** Operatøren bærer alle tap internt. Et reservefond opprettholdes tilsvarende 1,5× forventet årstap eller 99. persentil (det høyeste).

**Kostnadsstruktur:**
```
Arlig kostnad = Faktiske tap + Administrasjon + Alternativkostnad pa reservekapital
              - Investeringsinntekt pa reservefond
```

**Nøkkelrisiko:** Operatøren har ubegrenset eksponering mot katastrofetap. Modellen inkluderer en eksplisitt ADVARSEL om dette.

**Bruk som:** Nedre grense-benchmark. Viser lavest mulig forventet kostnad, men avslører den fulle halerisikoen operatøren påtar seg uten transfermekanisme.

---

## 11. Analytiske moduler

### 11.1 Monte Carlo-simulering

**Modell:** Sammensatt Poisson-LogNormal (Compound Poisson-LogNormal)

```
Arlig tap S = Σ(i=1 til N) Xi

der:
  N ~ Poisson(λ)           Antall hendelser per år
  Xi ~ LogNormal(μ, σ)     Tapsstørrelse per hendelse
  CAT-hendelse injiseres med sannsynlighet p_cat
```

**Med C5AI+ integrert:**
```
Justert arlig tap = S × c5ai_vs_static_ratio
Bio-fordeling = Justert tap × loss_breakdown_fractions[risikotype]
```

**Output:** 10 000 × 5 matrise (N simuleringer × T år) med simulerte årstap.

**Statistikk som beregnes:**
- E[arlig tap], Std[arlig tap], Median[arlig tap]
- VaR 90%, VaR 95%, VaR 99%, VaR 99,5%
- TVaR 95% (forventet tap i de 5% verste scenariene)
- 5-ars aggregat: E[5ar tap], Std[5ar tap], VaR 99,5% [5ar]

### 11.2 Solvenskapitalkrav (SCR)

Beregnes etter forenklet Solvens II-metodikk:

```
Beste estimat ansvar (BEL) = E[tap over prognoseperioden]
Tekniske avsetninger (TP)  = BEL × (1 + teknisk prudensmargin, 10%)
Solvenskapital (SCR)       = VaR 99,5% − TP
Risikomargin               = SCR × Kapitalkostnad (6%) × Annuitetsfaktor
```

Risikomargin og BEL summeres til tekniske avsetninger inklusiv risikomargin.

For full forsikring inkluderes en 5% motpartsrisiko-rabatt (motstykkerisiko mot assurandøren).

### 11.3 5-års totalkostnad for risiko (TCOR)

For hver strategi beregnes:

| Mål | Formel |
|---|---|
| Udiskontert 5-ars TCOR | Sum av nominelle arskostnader |
| NPV TCOR | Sum av diskonterte arskostnader (risikofri rente = 4%) |
| Besparelse vs. full forsikring | (Full ins. 5-ar − Strategi 5-ar) / Full ins. 5-ar |
| Kostnad som % av TIV | 5-ars TCOR / TIV |
| Kostnad som % av omsetning | 5-ars TCOR / 5-ars omsetning |

### 11.4 Volatilitetsmetrikk

Per strategi beregnes:

| Metrikk | Formel | Tolkning |
|---|---|---|
| Standardavvik | σ[arlig kostnad] | Absolutt variasjon |
| Variasjonskoeffisient (CV) | σ / μ | Relativ variasjon — lavt = stabilt |
| Skjevhet | Pearson tredje moment | Positiv = lang høyre hale (katastrofeutfall) |
| Kurtose | Fjerde moment − 3 | Positiv = tyngre haler enn normalfordeling |
| VaR 95% arlig | Persentil av arlig kostnad | Kostnadsgrense i normale uår |
| TVaR 95% arlig | E[kostnad | kostnad > VaR95%] | Forventet kostnad i krisescenariene |

### 11.5 Egnethetsmotoren (6 kriterier)

Seks vektede kriterier scores uavhengig på 0–100-skalaen:

#### Kriterie 1: Premiumvolum (22,5%)

| Arlig premie | Score | Vurdering |
|---|---|---|
| ≥ NOK 21 M | 100 | Svært god captive-masse |
| ≥ NOK 10,5 M | 80 | God captive-masse |
| ≥ NOK 5,25 M | 60 | Tilstrekkelig, marginale tall |
| ≥ NOK 2,1 M | 30 | Under foretrukket terskel |
| < NOK 2,1 M | 5 | Utilstrekkelig |

#### Kriterie 2: Tapsstabilitet (18%)

| CV (σ/μ) | Score | Vurdering |
|---|---|---|
| < 0,30 | 100 | Svært stabil tapsprofil |
| 0,30–0,49 | 80 | Stabil med håndterbar volatilitet |
| 0,50–0,74 | 55 | Moderat — celleprising er mulig |
| 0,75–0,99 | 30 | Høy volatilitet — økt risikoprising |
| ≥ 1,00 | 10 | Ekstrem volatilitet — captive uegnet |

#### Kriterie 3: Balanseregnskapsstyrke (18%)

Vurderer kapitalbelastning som andel av egenkapital:

| Kapital/egenkapital | Score | Vurdering |
|---|---|---|
| < 10% og kapital/FCF < 1,0x | 100 | Svært komfortabelt |
| < 20% og kapital/FCF < 2,0x | 75 | Håndterbart |
| < 35% | 50 | Strekker balansen |
| < 50% | 25 | Vesentlig begrensning |
| ≥ 50% | 5 | Overskrider kapasiteten |

#### Kriterie 4: Kostnadsbesparelsespotensial (18%)

| 5-ars besparelse vs. full forsikring | Score |
|---|---|
| ≥ 20% | 100 |
| ≥ 12% | 75 |
| ≥ 6% | 50 |
| ≥ 2% | 25 |
| < 2% | 5 |

#### Kriterie 5: Operasjonell beredskap (13,5%)

Gjennomsnitt av fem delkomponenter:

| Delkomponent | 100p | 70p | 30p / 0p |
|---|---|---|---|
| Forpliktelseshorisont | ≥7 år | ≥5 år | <5 år |
| Governance-modenhet | Moden | Utviklende | Grunnleggende |
| Risikostyringsansvarlig | Ja | — | Nei |
| Driftserfaring | ≥10 år | ≥5 år | <5 år |
| Villighet til å kapitalisere | Ja | — | Nei (blokkerer) |

#### Kriterie 6: Biologisk operasjonell beredskap (10%)

Scores i prioritert rekkefølge:

1. **Eksplisitt score** (`bio_readiness_score` i JSON): Brukes direkte
2. **C5AI+-datakvalitet** (hvis prognose er lastet):
   - `SUFFICIENT` → 85 poeng
   - `LIMITED` → 55 poeng
   - `POOR` → 30 poeng
   - `PRIOR_ONLY` → 15 poeng
3. **Proxy** (uten C5AI+): Gjennomsnitt av risikostyringsansvarlig-score og governance-score

#### Sammensatt score og konklusjon

| Score | Konklusjon | Tillitsnivå |
|---|---|---|
| ≥ 72 | STERKT ANBEFALT | Høy |
| 55–71 | ANBEFALT | Middels |
| 40–54 | POTENSIELT EGNET | Lav |
| 25–39 | IKKE ANBEFALT | Middels |
| < 25 | IKKE EGNET | Høy |

---

## 12. Forstå PDF-rapporten

### 12.1 Rapportstruktur

PDF-rapporten er bygget for presentasjon til styre og finanskomité:

| Side | Innhold |
|---|---|
| 1 | Forside med operatørnavn, dato og klassifisering |
| 2 | Styrets sammendrag — konklusjon og nøkkelresultater |
| 3 | Operatørprofil — lokaliteter, TIV, forsikringsstruktur |
| 4 | Monte Carlo-resultater — tapsdistribusjon og statistikk |
| 5 | Solvenskapitalkrav (SCR) — alle fire strategier |
| 6 | 5-ars TCOR-sammenligning — nominelt og NPV |
| 7 | Diagram: Tapsfordeling (histogram) |
| 8 | Diagram: Kumulativ kostnadskurve (alle strategier) |
| 9 | Diagram: Arlig kostnad per strategi |
| 10 | Volatilitetsmetrikk — CV, VaR, TVaR, skjevhet |
| 11 | Egnethetsanalyse — radarkart og scoreoversikt |
| 12 | Anbefalte neste steg og forutsetninger |
| 13 | Forutsetninger, begrensninger og metodikk |

### 12.2 Tolke diagrammene

**Tapsdistribusjon (Histogram)**
- X-akse: Arlig bruttotap (NOK M)
- Y-akse: Relativ hyppighet (% av simuleringer)
- Vertikale linjer: VaR 95% (gul), VaR 99,5% (rød)
- Lang høyre hale indikerer høy katastrofepotensiale

**Kumulativ kostnadskurve**
- Viser akkumulert kostnad over 5 år per strategi
- Brattere stigning = høyere arlig kostnad
- Divergerende kurver i år 2–3 indikerer at break-even ikke er nådd

**Arlig kostnadsammenligning (stolpediagram)**
- Stablet per kostnadskategori: Premie, Egenandel, Admin, Kapital, Investering
- Gir intuisjon om kostnadsstrukturforskjeller mellom strategier

**Kostnads-risiko-grense (scatter)**
- X-akse: Standardavvik for arlig kostnad (risiko)
- Y-akse: Forventet arlig kostnad (kostnad)
- Strategier i nedre venstre hjørne er best (lav kostnad + lav risiko)
- Full forsikring er vanligvis i midten; selvforsikring til høyre

**Egnethetsradarkart**
- Sekskant med ett akser per kriterie (versjon 2.0)
- Jo større areal, jo bedre egnethet
- En smal akse indikerer et spesifikt svakhetspunkt

### 12.3 Tolke egnethetsscoren

```
STERKT ANBEFALT  (≥72) — Sterk sak. Gå videre med captive manager-prosess.
ANBEFALT         (55–71) — God sak med noen betingelser. Se forutsetningslisten.
POTENSIELT EGNET (40–54) — Lovende, men krever mer analyse. Oftest lav premie
                           eller høy tapsvariasjon som trekker ned.
IKKE ANBEFALT    (25–39) — Captive er ikke hensiktsmessig på nåværende tidspunkt.
                           Vurder hybridstruktur i mellomtiden.
IKKE EGNET       (<25)   — Captive-strukturer ikke levedyktige. Kjerne er utilstrekkelig
                           premie eller manglende kapitalevne.
```

**Viktig:** Egnethetsscoren er ett av flere beslutningsgrunnlag. Styret bør alltid kombinere denne analysen med aktuarielt arbeid, domisil-due diligence og juridisk rådgivning.

---

## 13. Konfigurasjonsreferanse

Alle konstanter finnes i `config/settings.py`. Endre her for å kalibrere verktøyet til en spesifikk operatørkontekst.

### PCC Captive defaults

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `pcc_setup_cost` | NOK 1 250 000 | Etablerings- og registreringskostnad |
| `pcc_annual_cell_fee` | NOK 475 000 | Arlig celleforvaltningsavgift |
| `pcc_fronting_fee_rate` | 3% | Frontingavgift som andel av premie |
| `pcc_premium_discount` | 22% | Premierabatt vs. markedspremie |
| `pcc_investment_return` | 4% | Avkastning på cellereserver |

### Solvens og finans

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `risk_free_rate` | 4% | Diskonteringsrente for NPV |
| `cost_of_capital_rate` | 6% | Kapitalkostnad for SCR-risikomargin |
| `inflation_rate` | 2,5% | Kostnadsinflasjon per år |
| `technical_provision_load` | 10% | Prudensmargin på beste estimat |

### Egnethetsterskel

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `min_premium_for_captive` | NOK 5 250 000 | Absolutt nedre grense |
| `ideal_premium_for_captive` | NOK 10 500 000 | Ideelt premienivå |
| `max_cv_for_captive` | 1,0 | Maksimal tapsvariasjon (CV) |

### C5AI+ defaults (`c5ai_plus/config/c5ai_settings.py`)

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `hab_prior_event_probability` | 12% | HAB-sannsynlighet uten data |
| `lice_prior_event_probability` | 30% | Luseprobabilitet uten data |
| `hab_loss_fraction_mean` | 18% av biomasse | Betinget HAB-tap |
| `lice_loss_fraction_mean` | 6% av biomasse | Betinget lusetap |
| `network_max_distance_km` | 50 km | Nettverkstilkobling-radius |
| `min_obs_for_ml_model` | 24 | Minimum observasjoner for ML |

---

## 14. Tilpasse til ny operatør

### Steg-for-steg prosess

**1. Kopier eksempelfilen og gi den nytt navn**
```bash
cp data/sample_input.json data/min_ny_operatoer.json
```

**2. Rediger operatøridentitet, lokaliteter og forsikringsdata**
Bruk seksjon 5 i denne manualen som referanse for hvert felt.

**3. Fyll ut finansielt profil**
Hent tall fra siste årsregnskap (årsrapport eller RegnskapRegister).

**4. Kalibrere risikoparametere (samarbeid med aktuaren)**
```bash
# Hjelpeberegning: Fra historisk tapsliste
expected_events = antall_hendelser / antall_ar
mean_severity = total_tap / antall_hendelser
```

**5. Sett governance-parametere realistisk**
En for optimistisk vurdering vil gi misvisende egnethetsscore.

**6. Kjør initial analyse (uten C5AI+)**
```bash
python main.py --input data/min_ny_operatoer.json
```

**7. Sammenstill C5AI+ biologisk inputdata (valgfritt, men anbefalt)**
Se seksjon 6 for felt-for-felt guide.

**8. Kjør full integrert analyse**
```bash
python -m c5ai_plus.pipeline \
  --input c5ai_data/min_operatoer_bio.json \
  --output risk_forecast.json \
  --static-loss <E_arlig_tap_fra_trinn_6>

# Legg til c5ai_forecast_path i JSON-filen, kjør på nytt
python main.py --input data/min_ny_operatoer.json --simulations 20000
```

---

## 15. Testing og verifisering

### Kjøre testpakken

```bash
# Alle 41 tester
pytest tests/ -v

# Kun C5AI+-skjematester (11 tester)
pytest tests/test_forecast_schema.py -v

# Kun validatortester (11 tester)
pytest tests/test_forecast_validator.py -v

# Kun Monte Carlo-integrasjonstester (12 tester)
pytest tests/test_monte_carlo_integration.py -v

# Kun egnethets-kriterie-6-tester (7 tester)
pytest tests/test_suitability_bio_criterion.py -v
```

### Forventing
```
41 passed in < 1 sek
```

### Viktige testscenarier som dekkes

| Test | Hva verifiseres |
|---|---|
| `test_c5ai_not_enriched_by_default` | Statisk modell brukes uten `c5ai_forecast_path` |
| `test_missing_c5ai_file_falls_back` | Manglende fil gir advarsel + statisk fallback |
| `test_malformed_c5ai_file_falls_back` | Ugyldig JSON gir advarsel + statisk fallback |
| `test_scale_above_one_increases_losses` | Skalafaktor > 1,0 øker faktisk E[tap] |
| `test_bio_breakdown_fractions_consistent` | Bio-fordeling summerer til totalt tap |
| `test_all_weights_sum_to_one` | Egnethetsscorens vekter = 100% |
| `test_explicit_bio_score_high_raises_raw_score` | Kriterie 6 reagerer på input |

---

## 16. Vanlige spørsmål (FAQ)

**Q: Kan jeg bruke USD i stedet for NOK?**
A: Systemet er konfigurert for NOK. Alle terskelverdier i `settings.py` og `c5ai_settings.py` er i NOK. For USD-baserte operatører: konverter alle verdier til NOK ved å multiplisere med gjeldende kurs (vanligvis ~10,5), eller oppdater alle konfigurasjonsparametere manuelt.

**Q: Hva skjer hvis `c5ai_forecast_path` peker på en fil som ikke eksisterer?**
A: Systemet sender en `RuntimeWarning` til konsollen og bruker automatisk den statiske Compound Poisson-modellen. Ingen feilmelding eller avbrudd — analysen fullføres normalt. Rapporten vil ikke inneholde biologisk risikofordeling.

**Q: Hva er minstekrav for at PCC skal anbefales?**
A: Premie ≥ NOK 5,25 M, villighet til å stille kapital = `true`, og et positivt NPV basert på 5-ars projeksjon. Men egnethetsscoren er helhetlig — en lav balanse kan blokkere selv om premien er stor nok.

**Q: Hvor ofte bør risk_forecast.json oppdateres?**
A: Anbefalt frekvens:
- Kvartalsvis ved normale forhold
- Umiddelbart ved signifikante HAB-hendelser eller luseoppblomstringer
- Arlig som minimum for å reflektere oppdatert sesongdata

**Q: Kan C5AI+ brukes uten PCC-verktøyet?**
A: Ja. C5AI+ er en frittstående modul. `risk_forecast.json` kan brukes av andre systemer som leser JSON. Pipeline-skriptet (`python -m c5ai_plus.pipeline`) kjøres uavhengig.

**Q: Hva betyr skalafaktor > 2,0?**
A: En skalafaktor over 2,0 er usansynlig under normale forhold og indikerer sannsynligvis feil i inputdata, urealistiske prior-parametere, eller en spesielt eksponert lokalitet. Sjekk `metadata.warnings` i prognosefilen. Systemet vil flagge dette med en valideringsadvarsel.

**Q: Støtter systemet norsk laks i merder (pen) og settefisk?**
A: Systemet modellerer biomasse-baserte tap generelt og er best kalibrert for matfisk i sjøanlegg. For settefiskanlegg bør `biomass_value_per_tonne` justeres til smoltpris, og biologiske prior-parametere bør rekalibreres (lavere HAB-eksponering, annen luseprofil).

---

## 17. Feilsøking

### Systemet starter ikke

**Feil:** `ModuleNotFoundError: No module named 'numpy'`
**Løsning:** Kjør `pip install -r requirements.txt`

**Feil:** `ModuleNotFoundError: No module named 'scipy'`
**Løsning:** Som over. Sørg for at virtuelt miljø er aktivert.

### JSON-inputfeil

**Feil:** `ValueError: Annual premium must be positive`
**Årsak:** `annual_premium` er 0 eller negativ.
**Løsning:** Sjekk og korriger verdien i inputfilen.

**Feil:** `KeyError: 'sites'`
**Årsak:** Påkrevd felt mangler i JSON.
**Løsning:** Bruk `data/sample_input.json` som mal og kontroller at alle nødvendige felter er til stede.

### C5AI+-advarsler

**Advarsel:** `RuntimeWarning: C5AI+ forecast file not found`
**Årsak:** `c5ai_forecast_path` peker på en fil som ikke eksisterer.
**Løsning:** Kjør `python -m c5ai_plus.pipeline --input ...` for å generere filen, eller fjern feltet fra JSON for å bruke statisk modell.

**Advarsel:** `Site 'X': only 18 observations (need 24 for ML model). Using prior.`
**Årsak:** Utilstrekkelig observasjonsdata.
**Løsning:** Samle inn mer data (minimum 24 månedlige observasjoner). Prognosen vil fremdeles kjøre med prior-distribusjon.

### PDF-rapporten genereres ikke

**Feil:** `LayoutError: frame overflow`
**Årsak:** Svært langt operatørnavn eller ekstremt lange tabellverdier.
**Løsning:** Forkorte operatørnavnet i inputfilen eller kontakt Shield Risk Consulting.

**Feil:** `UnicodeEncodeError` på Windows
**Årsak:** Terminal bruker cp1252-enkoding.
**Løsning:** Kjør `chcp 65001` i kommandovinduet, eller sett `PYTHONIOENCODING=utf-8`.

### Tester feiler

**Feil:** `pytest: command not found`
**Løsning:** `pip install pytest>=7.4.0`

**Feil:** `ImportError: cannot import name 'CostAnalyzer'`
**Løsning:** Sørg for at arbeidskataloget er `shield-feasibility/` og at alle `__init__.py`-filer er på plass.

---

## 18. Metodikk og antakelser

### Monte Carlo-modellering

| Antagelse | Verdi | Begrunnelse |
|---|---|---|
| Tapshendelsesfrekvens | Poisson(λ) | Vanlig for forsikringsfrekvensmodellering |
| Tapssørrelse | LogNormal(μ, σ) | Typisk for skadeutfall i akvakultur — positiv skjevhet |
| Katastrofetap | Bernoulli(p) × LogNormal | Skiller mellom attritional og katastrofaltap |
| Simuleringshorisont | 5 år | Standard evaluering for captive-strukturer |
| Simuleringer | 10 000 (standard) | Gir < 1% usikkerhet på VaR 99,5% |
| Korrelasjon | Modelleres indirekte via nettverksmultiplikator (C5AI+) | |

### Solvensmodellering

Systemet implementerer en **forenklet Solvens II-proxy**, ikke en fullstendig intern modell. Formell solvensberegning for en faktisk PCC-celle krever en godkjent aktuariel modell og regulatorisk revisjon.

### C5AI+ modellbegrensninger

| Begrensning | Konsekvens | Håndtering |
|---|---|---|
| Sesongstasjonæritet antas | Fremtidige klimaendringer fanges ikke | Rekalibrering arlig |
| LogNormal betinget tapsdistribusjon | Kan undervurdere ekstremt store HAB-tap | Konservative CV-verdier |
| Nettverksmultiplikator er lineær | Overforenkler smittedynamikk | Fase 3: Stokastisk nettverksmodell |
| T-Learner (CATE) er valgfritt | Behandlingseffekter ikke inkludert i v1 | Aktiveres med econml |

### Historisk validering

Systemet har ikke vært gjennom en formell backtesting-prosess mot reelle norske oppdrettstap. Priorverdier er kalibrert mot åpent tilgjengelig statistikk fra Fiskeridirektoratet (tapsprosenter per art og tapskategori) og fagfellevurdert litteratur om biologisk risiko i nordatlantisk akvakultur.

---

## 19. Ordliste

| Term | Forklaring |
|---|---|
| **Bio-breakdown** | Fordeling av simulert tap på biologiske risikotyper (HAB, lus, manet, patogen) |
| **BEL** | Best Estimate Liability — beste estimat av fremtidige forpliktelser |
| **CAT-hendelse** | Katastrofehendelse med tap vesentlig høyere enn gjennomsnittet |
| **C5AI+** | Biological risk forecasting module — produserer risk_forecast.json |
| **Captive** | Selskapseget forsikringsselskap |
| **CV** | Variasjonskoeffisient = standardavvik / gjennomsnitt — mål på relativ volatilitet |
| **Datakvalitetsflagg** | SUFFICIENT / LIMITED / POOR / PRIOR_ONLY — indikerer pålitelighet av C5AI+-prognosen |
| **Domisil** | Land/jurisdiksjon der PCC er registrert |
| **Fronting** | Lisensiert assurandør som skriver policyen utad mens risiko holdes internt |
| **HAB** | Harmful Algal Bloom — skadelig algeoppblomstring |
| **LogNormal** | Sannsynlighetsfordeling der logaritmen er normalfordelt — positivt skjev |
| **Monte Carlo** | Simuleringsmetode som trekker tilfeldige utfall gjentatte ganger |
| **NPV** | Net Present Value — nåverdi diskontert til risikofri rente |
| **PCC** | Protected Cell Company — selskapstruktur med beskyttede celler |
| **Poisson** | Sannsynlighetsfordeling for antall hendelser i et tidsintervall |
| **Prior** | Antakelse om sannsynlighet/tap basert på ekspertskjønn eller konfigurasjon, uten data |
| **RandomForest** | Ensemble ML-modell basert på mange beslutningstrær |
| **Skalafaktor** | c5ai_vs_static_ratio — multipliseres med simulerte tap |
| **SCR** | Solvency Capital Requirement — kapital som holder solvens på 99,5% konfidensnivå |
| **TCOR** | Total Cost of Risk — all risikofinansieringskostnad over analyseperioden |
| **T-Learner** | Meta-learner for kausal effektestimering (CATE) via econml |
| **TVaR** | Tail Value-at-Risk / Expected Shortfall — forventet tap gitt at vi er over VaR |
| **TIV** | Total Insured Value — total forsikringsverdi |
| **VaR** | Value-at-Risk — tap som overskrides med en gitt sannsynlighet |
| **XS** | Excess of Loss — forsikring som dekker tap over en definert egenandel |

---

*PCC Feasibility & Suitability Tool v2.0 med C5AI+ Integrasjon*
*Shield Risk Consulting — Konfidensielt — Kun for operatør og rådgiver*
*Versjon 2.0 — Mars 2026*
