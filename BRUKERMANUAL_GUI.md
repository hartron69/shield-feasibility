# Shield Risk Platform
## Brukermanual – Grafisk grensesnitt (GUI) v2.1

**Utarbeidet av:** Shield Risk Consulting
**Versjon:** 2.1 (Nettbasert GUI med Pooling-analyse)
**Klassifisering:** Konfidensielt — Kun for operatør og rådgiver
**Plattform:** Nettleser (Chrome / Edge / Firefox) + Python-backend

---

## Innholdsfortegnelse

1. [Systemoversikt](#1-systemoversikt)
2. [Oppstart](#2-oppstart)
3. [Venstre panel – Inndata](#3-venstre-panel--inndata)
   - 3.1 [Operatørprofil](#31-operatørprofil)
   - 3.2 [Modellinnstillinger](#32-modellinnstillinger)
   - 3.3 [Strategiinnstillinger](#33-strategiinnstillinger)
   - 3.4 [Risikoreduserende tiltak](#34-risikoreduserende-tiltak)
   - 3.5 [Pooling-innstillinger](#35-pooling-innstillinger)
4. [Kjøreknapper og statuslinje](#4-kjøreknapper-og-statuslinje)
5. [Høyre panel – Resultater](#5-høyre-panel--resultater)
   - 5.1 [Summary – Sammendrag](#51-summary--sammendrag)
   - 5.2 [Charts – Diagrammer](#52-charts--diagrammer)
   - 5.3 [Mitigation – Tiltak](#53-mitigation--tiltak)
   - 5.4 [Recommendation – Anbefaling](#54-recommendation--anbefaling)
   - 5.5 [Allocation – Eksponeringsfordeling](#55-allocation--eksponeringsfordeling)
   - 5.6 [Loss History – Taphistorikk](#56-loss-history--taphistorikk)
   - 5.7 [Pooling – Sammenslutningsanalyse](#57-pooling--sammenslutningsanalyse)
   - 5.8 [Report – PDF-rapport](#58-report--pdf-rapport)
6. [Typisk arbeidsflyt](#6-typisk-arbeidsflyt)
7. [Feltforklaringer – oppslagstabell](#7-feltforklaringer--oppslagstabell)
8. [Tolkning av nøkkeltall](#8-tolkning-av-nøkkeltall)
9. [Feilsøking](#9-feilsøking)
10. [Teknisk arkitektur (kortfattet)](#10-teknisk-arkitektur-kortfattet)

---

## 1. Systemoversikt

Shield Risk Platform er et beslutningsstøtteverktøy for havbruksoperatører som vurderer om en **Protected Cell Company (PCC)** er en egnet forsikringsstruktur. Verktøyet simulerer tapsdistribusjoner med Monte Carlo-metoden og sammenligner fire strategier:

| Strategi | Beskrivelse |
|---|---|
| **Full forsikring** | Tradisjonell kommersielle forsikring dekker alle tap |
| **Hybrid** | Kombinasjon av egenrisiko og forsikring |
| **PCC Captive Cell** | Operatøren finansierer risiko i en beskyttet celle |
| **Selvforsikring** | Operatøren bærer all risiko selv |

Dersom Pooling er aktivert, analyseres i tillegg en **Pooled PCC Cell** der operatøren inngår i et syntetisk risikodelingsbasseng med likeverdige aktører.

**Nøkkelbegreper:**
- **VaR 99,5 %** – Value at Risk ved 99,5 % konfidensnivå; det taptallet som bare overskrides i 0,5 % av scenariene. Brukes som tilnærming til Solvency Capital Requirement (SCR).
- **CV** – Variasjonskoeffisient (standardavvik / forventningsverdi). Lav CV = jevnt tap; høy CV = stor usikkerhet.
- **TCOR** – Total Cost of Risk over 5 år (summen av alle direkte og indirekte kostnader).
- **E[tap]** – Forventet årlig tap (gjennomsnitt over alle simuleringer).

---

## 2. Oppstart

### Forutsetninger

```
Python 3.10+  med pakkene fra requirements.txt
Node.js 18+   (kun nødvendig første gang; npm install i frontend/)
```

### Start backend

```bash
# Fra rotkatalogen til prosjektet
uvicorn backend.main:app --reload --port 8000
```

Du skal se:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Start frontend (utviklingsmodus)

```bash
cd frontend
npm install          # bare første gang
npm run dev
```

Åpne nettleseren på **http://localhost:5173**.

### Prod-bygg (valgfritt)

```bash
cd frontend && npm run build
# Statiske filer havner i frontend/dist/ og serveres automatisk av backend på port 8000
```

---

## 3. Venstre panel – Inndata

Venstrekolonnen er delt inn i fem trekkspillseksjoner. Klikk på seksjonstittel for å åpne/lukke.

---

### 3.1 Operatørprofil

Denne seksjonen beskriver operatørens virksomhet og danner grunnlaget for alle beregninger.

| Felt | Beskrivelse | Eksempel |
|---|---|---|
| **Operatørnavn** | Navn på selskapet | Nordic Aqua Partners AS |
| **Land** | Driftsnasjon | Norge |
| **Antall lokaliteter** | Totalt antall produksjonslokaliteter | 3 |
| **Total biomasse (t)** | Total stående biomasse på tvers av alle lokaliteter | 9 200 t |

#### Biomasseverdsetting

Verktøyet beregner en *foreslått verdi* per tonn basert på tre parametre:

```
Foreslått verdi = Referansepris (NOK/kg) × 1 000 × Realisasjonsfaktor × (1 – Forsiktighetskutt)
```

| Felt | Standard | Beskrivelse |
|---|---|---|
| **Referansepris (NOK/kg)** | 80 | Markedspris for laks |
| **Realisasjonsfaktor** | 0,90 | Andel av markedspris oppnådd ved nødslakt |
| **Forsiktighetskutt** | 0,10 | Konservativ buffer for prisusikkerhet |
| **Foreslått verdi (NOK/t)** | 64 800 | Beregnet automatisk, skrivebeskyttet |
| **Anvendt verdi (NOK/t)** | 64 800 | Redigerbar. Trykk «Bruk foreslått» for å tilbakestille |

> **Tips:** Hvis du kjenner den faktiske forsikringsverdien per tonn, skriv den direkte inn i *Anvendt verdi*. Feltet viser da en oransje «OVERSTYRT»-badge som påminnelse.

Følgende felter beregnes automatisk og er skrivebeskyttet (markert med lås-ikon):

- **Årsomsetning (NOK)** = Biomasse × Anvendt verdi × 1,35 (realiseringskoeffisient)
- **Årlig premie (NOK)** = Årsomsetning × 2,17 % (bransjenorm)

---

### 3.2 Modellinnstillinger

| Felt | Standard | Beskrivelse |
|---|---|---|
| **Antall simuleringer** | 5 000 | Antall Monte Carlo-kjøringer. 5 000 gir god presisjon (~1 sekund). 20 000 gir høyere presisjon (~4 sekunder). |
| **Domenekorrelasjon** | `expert_default` | Korrelasjonsprofil mellom biologiske, miljø-, strukturelle og operasjonelle tapsdrivere. Se tabell under. |
| **Generer PDF** | Ja | Produserer en 13-siders styrerapporten i PDF-format. |
| **Bruk historikkalibrering** | Nei | Kalibrerer Monte Carlo-modellen mot historiske tapsposter (krever at historikkdata er tilgjengelig i malen). |

#### Tilgjengelige korrelasjonsprofiler

| Profil | Beskrivelse |
|---|---|
| `expert_default` | Ekspertkalibrert: moderat bio–miljø (0,40), høy miljø–struktur (0,60). Anbefalt for norsk oppdrett. |
| `uncorrelated` | Alle domener uavhengige (kun for benchmarking). |
| `high_correlation` | Sterk kopling mellom alle domener; konservativt worst-case. |

---

### 3.3 Strategiinnstillinger

| Felt | Beskrivelse |
|---|---|
| **Strategi** | Velg hvilken strategi som er *primærfokus* for analysen. Alle fire strategier beregnes alltid; dette feltet bestemmer hvilken PCC-type som fremheves. |
| **Egenrisiko (NOK)** | Opptil dette beløpet bærer operatøren tapet selv. Tomt felt betyr at verktøyet beregner optimal egenrisiko. |

Tilgjengelige strategier:

| Valg | Intern nøkkel |
|---|---|
| PCC Captive Cell | `pcc_captive` |
| Full forsikring | `full_insurance` |
| Hybrid | `hybrid` |
| Selvforsikring | `self_insurance` |

---

### 3.4 Risikoreduserende tiltak

Her velger du hvilke risikoreduserende tiltak operatøren har implementert eller vurderer å implementere. Tiltakene påvirker tapssannsynlighet og -alvorlighet i den mitigerte kjøringen.

Tiltakene er gruppert etter domene:

#### Strukturelle tiltak
| Tiltak | Beskrivelse | P-red. | Alv-red. | Kostnad/år |
|---|---|---|---|---|
| Sterkere not | Forsterket notmateriale med høyere bruddstyrke | 35 % | 30 % | 450 000 NOK |
| Sterkere fortøyning | Oppgradert fortøyningssystem | 30 % | 25 % | 300 000 NOK |
| Deformasjonsovervåking | Sanntidssensorer for notgeometri og fortøyningsavvik | 30 % | 20 % | 250 000 NOK |

#### Miljøtiltak
| Tiltak | Beskrivelse | P-red. | Alv-red. | Kostnad/år |
|---|---|---|---|---|
| Miljøsensorer | Temperatur, oksygen og strømmåling | 25 % | 20 % | 200 000 NOK |
| Maneter-avskjerming | Fysisk og biologisk beskyttelse mot maneter | 40 % | 35 % | 180 000 NOK |

#### Operasjonelle tiltak
| Tiltak | Beskrivelse | P-red. | Alv-red. | Kostnad/år |
|---|---|---|---|---|
| Opplæringsprogram | Systematisk HMS- og beredskapsopplæring | 20 % | 15 % | 120 000 NOK |
| Risikostyrer | Dedikert risikostyringsansvarlig | — | 25 % | 800 000 NOK |
| Stormkontingensplan | Dokumentert prosedyre ved ekstremvær | — | 20 % | 50 000 NOK |
| Beredskapsprogram | Responsprotokoller for kritiske hendelser | — | 20 % | 80 000 NOK |

#### AI-integrerte tiltak
| Tiltak | Beskrivelse | P-red. | Alv-red. | Kostnad/år |
|---|---|---|---|---|
| AI tidligvarsling | Integrert AI-varsling på tvers av alle domener | 20 % | 15 % | 600 000 NOK |

> **P-red.** = reduksjon i hendelsessannsynlighet. **Alv-red.** = reduksjon i tap per hendelse.
> Tiltak kombineres multiplikativt, ikke additivt (f.eks. to tiltak med 30 % og 20 % gir ikke 50 %, men 44 %).

---

### 3.5 Pooling-innstillinger

Aktivér med avkrysningsboksen **«Aktiver poolet PCC-scenario»** for å evaluere om operatøren drar nytte av å inngå i et risikodelingsbasseng med likeverdige aktører.

#### Bassengstruktur

| Felt | Standard | Beskrivelse |
|---|---|---|
| **Antall medlemmer** | 4 | Totalt antall operatører i bassenget (inkl. denne operatøren). Min 2, maks 10. |
| **Korrelasjonskoeffisient** | 0,25 | Grad av samvariasjon mellom members' tapsår. 0 = fullstendig uavhengige; 0,95 = nesten perfekt sammenheng. |
| **Likhetsvariasjonsbredde (±)** | 0,15 | Hvor like de syntetiske bassengmedlemmene er denne operatøren. 0 = identiske; 0,50 = ±50 % variasjon. |

#### Poolet gjenforsikring

| Felt | Standard | Beskrivelse |
|---|---|---|
| **Egenrisiko for pool (Mill NOK)** | 25 | Totalt behold for hele bassenget før gjenforsikring trer inn. |
| **GF-grense for pool (Mill NOK)** | 400 | Maksimal gjenforsikringsdekning for hele bassenget. |
| **GF-lastefaktor** | 1,40 | Gjenforsikringspremie = forventet GF-utbetaling × lasfaktor. |
| **Delt administrasjonsinsparing** | 20 % | Forventet kostnadsbesparelse på felles administrasjon. |

#### Allokeringsgrunnlag

| Valg | Beskrivelse |
|---|---|
| Forventet tap (anbefalt) | Hvert members andel av kostnader tilsvarer andelen av bassengents forventede tap |
| Premieproposjonal | Andel basert på innbetalt premie |

> **Merk (v2.1):** Bassengmedlemmene er syntetisk genererte – faktiske peer-data lastes ikke opp. Korrelasjonen er rangbasert blending (ikke Gaussisk kopula). Se Pooling-fanen i resultatpanelet for fullstendig liste over forenklinger.

---

## 4. Kjøreknapper og statuslinje

Nederst i venstrekolonnen finner du tre knapper:

| Knapp | Funksjon |
|---|---|
| **Kjør analyse** | Sender inndata til backend, kjører Monte Carlo-simulering og returnerer resultater. Typisk kjøretid: 1–5 sekunder. |
| **Last eksempel** | Fyller inn Nordic Aqua Partners AS (norsk lakseoppdretter, 9 200 t, 3 lokaliteter) som referansecase. |
| **Nullstill** | Tømmer alle felt og resultater til standardverdier. |

### Statuslinje

Under knappene vises fremdriften gjennom seks steg:

```
① Bygg operatørmodell  →  ② Simuler tap  →  ③ Beregn strategier
④ SCR-analyse  →  ⑤ Egnethetsvurdering  →  ⑥ Ferdig
```

Aktivt steg er uthevet. Eventuelle feilmeldinger vises i rødt under statuslinjen.

---

## 5. Høyre panel – Resultater

Resultater vises i åtte faner. Fanene er tilgjengelige etter at en analyse er kjørt.

---

### 5.1 Summary – Sammendrag

Gir et øyeblikksbilde av nøkkeltall for baseline-scenario (uten tiltak) og, dersom tiltak er valgt, for det mitigerte scenariet.

#### KPI-kort (per scenario)

| Nøkkeltall | Beskrivelse |
|---|---|
| **E[Årlig tap]** | Forventet gjennomsnittlig tap per år |
| **VaR 95 %** | Tap som overskrides i 5 % av årsscenarioene |
| **VaR 99,5 %** | Tap som overskrides i 0,5 % av årsscenarioene (= tilnærmet SCR) |
| **SCR (netto)** | Solvenskapitalkrav etter gjenforsikring og egenandelsstruktur |
| **Anbefalt strategi** | Verktøyets vurdering av best egnet risikostrategi |
| **Egnethetsscore** | Samlet score 0–100 for PCC-egnethet |
| **Konfidensnivå** | Grad av sikkerhet i anbefalingen (lav / moderat / høy) |

#### Delta-kort (kun ved mitigert kjøring)

Grønne piler viser forbedringer; røde viser forverringer. Delta beregnes som %-endring fra baseline.

---

### 5.2 Charts – Diagrammer

Viser opptil ti diagrammer generert av backend. Klikk på hvert bilde for å se det i full oppløsning (høyreklikk → Lagre bilde for nedlasting).

| Diagram | Innhold |
|---|---|
| Tapsdistribusjon | Histogram over simulerte årstap med percentil-markører |
| Kumulativ fordelingsfunksjon | S-kurve; les av VaR direkte på y-aksen |
| Domainefordeling | Kakediagram: andelen tap per risikodomene |
| Strategi-TCOR | Søylediagram: 5-års TCOR for alle fire strategier |
| Kovariasjonsvarmekart | Heatmap av korrelasjon mellom domener |
| Scenariosammenligning | Stablet søylediagram for p50/p95/p99 scenarios per domene |
| Haledomenesammensetning | Strekdiagram for bidrag per domene ved hale-scenarios |
| Haletapsdekomponering | Nedbrytning av tapene i haleende av fordelingen |
| Mitigeringseffekt | Før/etter-sammenligning per tiltak (kun ved mitigert kjøring) |
| Kostnads-/nyttekurve | Tiltakskostnad vs. tap-reduksjon per tiltak |

---

### 5.3 Mitigation – Tiltak

Detaljert analyse av de valgte tiltakenes effekt.

- **Oversiktstabell**: Hvert valgt tiltak vises med domene, P-reduksjon, alvorlighetsreduksjon og estimert tapsnedgang.
- **Domenepåvirkning**: Prosentvis reduksjon per risikodomene.
- **Tapsnedgang (NOK)**: Estimert reduksjon i forventet årlig tap.
- **SCR-reduksjon (NOK)**: Estimert reduksjon i solvenskapitalkrav.

> En verdi vises kun dersom tiltak er valgt *og* analysen ble kjørt med tiltak aktivert.

---

### 5.4 Recommendation – Anbefaling

Kjernevurderingen av PCC-egnethet basert på seks kriterier.

#### Vurderingsbanner

Banneret øverst viser ett av tre utfall:

| Utfall | Betingelse |
|---|---|
| **ANBEFALT** | Alle seks kriterier bestått; composite score ≥ 70 |
| **POTENSIELT EGNET** | Minst fire kriterier bestått; moderate kostnadsforhold |
| **IKKE ANBEFALT** | Kritisk kriterium feilet (f.eks. PCC-kostnad > 15 % over FI-kostnad) |

#### Seks kriterier

| Kriterium | Hva måles |
|---|---|
| Tapsstabilitet | CV av simulerte tap (lav CV = stabilt, lettere å styre i PCC) |
| Kapitaleffektivitet | Forholdet mellom SCR og egenkapital |
| Premieeffektivitet | PCC-totalkostnad vs. markedspremie |
| Selvforsikringsegnethet | Om operatøren kan finansiere worst-case tap |
| Diversifikasjonspotensial | Mulighet for å spre risiko mellom lokaliteter |
| Tapskonsentrasjon | Grad av dominans fra ett enkelt risikodomene |

Hvert kriterium vises med score, statusfarge (grønn/gul/rød) og narrativ forklaring.

---

### 5.5 Allocation – Eksponeringsfordeling

Viser hvordan operatørinndataene er oversatt til den fullstendige interne modellen.

#### Eksponeringsforhold

| Nøkkeltall | Beskrivelse |
|---|---|
| Biomasse-TIV-ratio | Forholdet mellom oppgitt biomasseverdi og malobjektets totale forsikringsverdi |
| Biomasseverdi per tonn | Anvendt verdi fra operatørprofilen |
| Antatt TIV | Total forsikringsverdi som brukes i modellen |

#### Biomasseverdsettelsesoversikt

Viser tre verdier side om side:
- **Referanseverdi**: Markedspris-basert verdi
- **Foreslått verdi**: Beregnet fra formel (se seksjon 3.1)
- **Anvendt verdi**: Faktisk verdi brukt i analysen

Et oransje advarselsbanner vises dersom anvendt verdi avviker mer enn 10 % fra foreslått verdi.

#### Finansielle forholdstall

| Forholdstall | Beskrivelse |
|---|---|
| SCR / Egenkapital | Solvens-ratio; bør være < 40 % for at PCC skal være kapitalmessig forsvarlig |
| E[tap] / EBITDA | Tapsbyrde relativt til driftsresultat |
| VaR 99,5 % / FCF | Worst-case tap vs. fri kontantstrøm |

#### Per-lokalitet-tabell

Viser estimerte verdier, risikoparametere og eksponeringsandel for hver lokalitet i modellen.

---

### 5.6 Loss History – Taphistorikk

Vises kun dersom operatørmalen inneholder historiske tapsposter.

#### Oversikstkort

| Nøkkeltall | Beskrivelse |
|---|---|
| Antall poster | Totalt antall registrerte tapshendelser |
| Observasjonsperiode | Antall år med historikk |
| Hendelser per år | Gjennomsnittlig hendelsesfrekvens |
| Gj.sn. bruttotap per hendelse | Gjennomsnittlig tapsstørrelse |
| Gj.sn. bruttotap per år | Gjennomsnittlig årstap over hele perioden |
| Totalt bruttotap | Sum over alle observasjonsår |

#### Kalibreringsstatus

Et blått banner viser om modellen er kalibrert mot historikken:

| Status | Betingelse |
|---|---|
| Aktiv (porteføljekalibrering) | Historikkalibrering slått på i Modellinnstillinger og ≥ 3 poster finnes |
| Ikke aktiv | Historikkalibrering er deaktivert |

Dersom kalibrering er aktiv, vises kalibrerte parametre:
- Gjennomsnittlig tapsskadesverdi (NOK)
- Forventet antall hendelser per år

#### Domenekort

Tapsposter er automatisk gruppert i domener etter hendelsestype:

| Hendelsestype | Domene |
|---|---|
| Mortalitet, sykdom, HAB, lus | **Biologisk** |
| Utstyrsskade, not, fortøyning, storm | **Strukturell** |
| Driftsavbrudd, tyveri, personell | **Operasjonell** |
| Andre / ukjente typer | **Ukjent** |

For hvert domene vises: antall hendelser, totalt tap, gjennomsnitt per år, andel av totalt tap.

#### Domenefrekvenstabell

Viser frekvens og alvorlighetsstatistikk per domene side om side, slik at du kan identifisere hvilke risikodomener som dominerer historikken.

#### Postliste

Alle historiske tapsposter vises i en tabell med:
- År, dato (om tilgjengelig)
- Domenebadge (fargekodet)
- Hendelsestype
- Bruttotap (NOK)
- Beskrivelse

---

### 5.7 Pooling – Sammenslutningsanalyse

Vises kun dersom Pooling er aktivert og analyse er kjørt.

#### Vurderingsbanner

| Utfall | Betingelse |
|---|---|
| **Poolet PCC: LEVEDYKTIG** | Pooled TCOR < Standalone TCOR **og** CV-reduksjon > 5 % |
| **Poolet PCC: Begrenset fordel** | En av betingelsene over er ikke oppfylt |

#### A. Diversifikasjonsgevinst

Fire KPI-kort viser effekten av risikodeling:

| Nøkkeltall | Forklaring |
|---|---|
| **Standalone CV** | Variasjonskoeffisient for operatøren alene |
| **Pooled CV (operatørandel)** | CV for operatørens andel i bassenget |
| **CV-reduksjon** | %-forbedring; grønn pil = fordel |
| **Standalone VaR 99,5 %** | Operatørens standalone worst-case tap |
| **Pooled VaR 99,5 % (operatørandel)** | Operatørens andel av bassengexposure |
| **VaR-reduksjon** | %-forbedring |

#### B. Økonomisammenligning

Tabell som viser *standalone PCC* mot *Poolet PCC* på tre nøkkeltall:

| Nøkkeltall | Forklaring |
|---|---|
| Årlig GF-premie | Gjenforsikringspremie per år |
| SCR (netto) | Solvenskapitalkrav etter GF |
| 5-års TCOR | Total kostnad over 5-årshorisont |

#### C. Bassengmedlemsoversikt

Tabell over alle syntetiske bassengmedlemmer der Operatøren (Member 0, blå bakgrunn) sammenlignes med de syntetiske jevnaldrende på:
- Forventet årstap
- Vekt (andel av bassengkostnader)
- Standalone og Pooled CV
- Allokert GF-premie, SCR og 5-års TCOR

#### D. Forenklinger og modellforutsetninger

Bunnen av fanen inneholder en nedtrekkbar liste over v2.1-modellforutsetningene. Disse er viktige for rådgivere som skal kommunisere usikkerhet til styret.

---

### 5.8 Report – PDF-rapport

Viser nedlastingsstatus for den genererte PDF-rapporten.

| Status | Betingelse |
|---|---|
| **Klar for nedlasting** | `generate_pdf = true` og PDF ble generert |
| **PDF ikke aktivert** | `generate_pdf = false` i modellinnstillinger |

Klikk på lenken for å åpne rapporten i nettleseren. Rapporten er en 13-siders styredokument med:
- Sammendrag og anbefaling
- Monte Carlo-resultater og diagrammer
- Domenekorrelert risikoanalyse
- Scenariosammenligning (p50/p95/p99)
- PCC-kostnadsstruktur
- Mitigerings-ROI (om tiltak er valgt)

---

## 6. Typisk arbeidsflyt

### Enkel vurdering (10 minutter)

```
1. Klikk "Last eksempel"        → fyller Nordic Aqua-profil
2. Klikk "Kjør analyse"         → ~2 sek
3. Les "Recommendation"-fanen   → er PCC anbefalt?
4. Åpne "Summary"-fanen         → sammenlign TCOR for alle strategier
5. Last ned PDF-rapport         → del med styre/rådgiver
```

### Fullstendig vurdering med tiltak (20 minutter)

```
1. Fyll inn Operatørprofil med riktige tall
2. Aktiver relevante risikoreduserende tiltak
3. Kjør analyse
4. Les "Mitigation"-fanen       → hvilke tiltak gir størst verdi?
5. Sammenlign baseline og mitigert i "Summary"
6. Last ned PDF
```

### Pooling-evaluering

```
1. Fullfør standard vurdering (steg 1–4 ovenfor)
2. Åpne "Pooling"-seksjonen i venstrekolonnen
3. Aktiver pooling; juster evt. antall medlemmer og korrelasjonskoeffisient
4. Kjør analyse på nytt
5. Les "Pooling"-fanen          → er pooled PCC levedyktig?
6. Sammenlign TCOR: standalone PCC vs. Pooled PCC vs. Full forsikring
```

### Sensitivitetsanalyse

For å teste usikkerhet i nøkkelparametre:

```
1. Kjør baseline
2. Endre ett felt (f.eks. antall simuleringer 5 000 → 20 000 eller korrelasjonskoeffisient 0,25 → 0,50)
3. Kjør analyse på nytt
4. Sammenlign nøkkeltallene
```

---

## 7. Feltforklaringer – oppslagstabell

| Felt / parameter | Norsk forklaring | Enhet |
|---|---|---|
| `n_sites` | Antall produksjonslokaliteter | stk |
| `total_biomass_tonnes` | Total stående biomasse | tonn |
| `biomass_value_per_tonne` | Forsikringsverdi per tonn biomasse | NOK/t |
| `annual_revenue_nok` | Estimert årsomsetning | NOK |
| `annual_premium_nok` | Estimert forsikringspremie | NOK |
| `n_simulations` | Antall Monte Carlo-iterasjoner | stk |
| `domain_correlation` | Korrelasjonsprofil for risikodomener | kode |
| `generate_pdf` | Generer PDF-styresrapport | ja/nei |
| `use_history_calibration` | Kalibrér mot historiske tap | ja/nei |
| `strategy` | Valgt primærstrategi | kode |
| `retention_nok` | Egenrisiko-grense | NOK |
| `pooled_retention_nok` | Total basseng-egenrisiko | NOK |
| `pooled_ri_limit_nok` | Maksimal basseng-GF-dekning | NOK |
| `pooled_ri_loading_factor` | GF-premie = E[utbetaling] × faktor | × |
| `inter_member_correlation` | Korrelasjon mellom bassengmedlemmer | 0–1 |
| `similarity_spread` | Variasjon i syntetiske jevnaldrende | ± fraksjon |
| `shared_admin_saving_pct` | Forventet administrasjonsbesparelse | % |
| `allocation_basis` | Kostnadsforderingsgrunnlag i bassenget | kode |

---

## 8. Tolkning av nøkkeltall

### Forventet tap – hva er normalt?

For en norsk lakseoppdretter med 9 000–12 000 t biomasse:

| Indikator | Lavt | Moderat | Høyt |
|---|---|---|---|
| E[tap] / Biomasse-TIV | < 1 % | 1–3 % | > 3 % |
| CV | < 1,5 | 1,5–2,5 | > 2,5 |
| VaR 99,5 % / E[tap] | < 5× | 5–8× | > 8× |

### SCR-vurdering

- **SCR < 10 M NOK**: PCC kan etableres med minimal kapital. Svært gunstig.
- **SCR 10–50 M NOK**: Typisk for mellomstore operatører. PCC er gjerne levedyktig med riktig GF-struktur.
- **SCR > 100 M NOK**: Krever betydelig egenkapitalreserve. Pooling eller hybrid kan være bedre.

### Egnethetsscore

| Score | Tolkning |
|---|---|
| 80–100 | PCC er klart anbefalt |
| 60–79 | PCC kan fungere; nøye vurdering anbefales |
| 40–59 | Betinget egnet; vurder tiltak eller hybrid |
| < 40 | PCC anbefales ikke i nåværende konfigurasjon |

### Poolingfordel

| CV-reduksjon | Tolkning |
|---|---|
| > 20 % | Sterk diversifikasjonsgevinst; pooling klart fordelaktig |
| 10–20 % | Moderat gevinst; pooling bør vurderes |
| 5–10 % | Marginal gevinst; avhenger av kostnadsstruktur |
| < 5 % | Liten diversifikasjonsgevinst; pooling gir begrenset fordel |

---

## 9. Feilsøking

### «Failed to connect to backend»

Backend kjører ikke. Kjør:
```bash
uvicorn backend.main:app --reload --port 8000
```

### «Failed to load example»

Sjekk at backend er oppe og at `data/sample_input.json` finnes.

### Analysen henger / spinner aldri ferdig

- Øk timeout i nettleseren (f.eks. deaktiver nettleserutvidelser som blokkerer lange forespørsler)
- Sjekk backend-loggene for Python-feilmeldinger
- Reduser `n_simulations` til 1 000 for rask test

### PDF-lenken fungerer ikke

- Sjekk at mappen `backend/static/reports/` eksisterer
- Sjekk at backend har skriverettigheter til denne mappen
- Forsikre deg om at `generate_pdf = true` i modellinnstillingene

### Pooled CV er ikke lavere enn standalone CV

Dette kan skje med veldig høy korrelasjonskoeffisient (> 0,7) eller kun 2 bassengmedlemmer. Prøv:
- Reduser korrelasjonskoeffisienten
- Øk antall bassengmedlemmer

### Kalibreringsstatus viser «Ikke aktiv» selv om det finnes historikk

Historikkalibrering må aktiveres eksplisitt i **Modellinnstillinger** med **«Bruk historikkalibrering»**-bryteren.

---

## 10. Teknisk arkitektur (kortfattet)

```
┌─────────────────────────────────────────────────────────────────┐
│  Nettleser (localhost:5173)                                     │
│  React 18 + Vite 5                                              │
│  ├── Venstre panel: accordion-inndataskjema                     │
│  └── Høyre panel: resultattabs (8 faner)                        │
└───────────────────────┬─────────────────────────────────────────┘
                        │ POST /api/feasibility/run (JSON)
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI backend (localhost:8000)                               │
│  ├── backend/api/feasibility.py   – HTTP-adapter               │
│  ├── backend/api/mitigation.py    – tiltaksbibliotek           │
│  ├── backend/services/operator_builder.py  – profil → modell   │
│  └── backend/services/run_analysis.py      – full pipeline     │
└───────────────────────┬─────────────────────────────────────────┘
                        │ Python-modulkall
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Analysemotor (eksisterende Python-moduler)                     │
│  ├── models/monte_carlo.py          – Monte Carlo-simulering    │
│  ├── models/domain_correlation.py   – Domenekorrelasjonsmatrise │
│  ├── models/strategies/             – Fire (+ pooled) strategier│
│  ├── models/pooling/                – Bassenganalyse            │
│  ├── analysis/mitigation.py         – 12 tiltaksdefinisjoner   │
│  ├── analysis/suitability_engine.py – 6-kriterium vurdering    │
│  ├── reporting/chart_generator.py   – 10 diagrammer (base64)   │
│  └── reporting/pdf_report.py        – 13-siders PDF            │
└─────────────────────────────────────────────────────────────────┘
```

**Dataflyt:**
1. Brukeren fyller inn skjemaet og klikker *Kjør analyse*
2. Frontend sender én POST-forespørsel til `/api/feasibility/run`
3. Backend bygger en fullstendig `OperatorInput` fra den forenklede profilen
4. Monte Carlo-motoren kjører N simuleringer (vektorisert NumPy, ~1 sekund for 5 000 sims)
5. Fire (eller fem) strategier beregnes parallelt
6. Egnethetsmotoren skårer 6 kriterier og setter en anbefaling
7. Valgfritt: PDF genereres og lagres i `backend/static/reports/`
8. Hele svaret returneres som JSON; frontend rendrer resultattabsene

---

*Shield Risk Platform v2.1 — © Shield Risk Consulting*
*Dokumentet er konfidensielt. Ikke distribuer uten tillatelse.*
