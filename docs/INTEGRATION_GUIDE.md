# C5AI+ ↔ PCC Feasibility Tool – Integrasjonsguide

## Arkitekturoversikt

```
┌─────────────────────────┐      risk_forecast.json      ┌────────────────────────┐
│       C5AI+ v5.0        │ ──────────────────────────→  │  PCC Feasibility Tool  │
│  (separat prosess)      │                              │                        │
│                         │  c5ai_vs_static_ratio        │  MonteCarloEngine      │
│  pipeline.py            │  loss_breakdown_fractions    │    ↓ (scaled losses)   │
│  ↓                      │  total_expected_annual_loss  │  Strategy models       │
│  HABForecaster          │                              │  SCR beregning         │
│  LiceForecaster         │                              │  SuitabilityEngine     │
│  JellyfishForecaster    │                              │    ↓ (6 kriterier)     │
│  PathogenForecaster     │                              │  PDF-rapport           │
│  SiteRiskNetwork        │                              │                        │
└─────────────────────────┘                              └────────────────────────┘
```

### Designprinsipper

| Prinsipp | Implementering |
|---|---|
| Løst koblet | JSON-fil som eneste grensesnitt |
| Bakoverkompatibel | `c5ai_forecast_path = None` → statisk modell (uendret) |
| Graceful degradation | Manglende/ugyldig fil → automatisk fallback med advarsel |
| Disaggregert risiko | `bio_loss_breakdown` per risikotype i SimulationResults |

---

## Endringer i eksisterende PCC-kodebase

### 1. `data/input_schema.py`

Nye valgfrie felt i `OperatorInput`:

```python
c5ai_forecast_path: Optional[str] = None
bio_readiness_score: Optional[int] = None
```

Legg til i `sample_input.json` for å aktivere C5AI+:
```json
{
  "c5ai_forecast_path": "risk_forecast.json",
  "bio_readiness_score": 55
}
```

### 2. `models/monte_carlo.py`

Nye felt i `SimulationResults`:
```python
c5ai_scale_factor: Optional[float]      # Skalafaktoren som ble brukt
bio_loss_breakdown: Optional[Dict[str, np.ndarray]]  # (N, T) per risikotype
c5ai_enriched: bool                      # True hvis C5AI+ ble brukt
```

Ny privat metode:
```python
MonteCarloEngine._apply_c5ai_forecast(annual_losses, c5ai_path)
    → (scaled_losses, scale_factor, bio_breakdown, enriched_flag)
```

Fallback-logikk:
- `FileNotFoundError` → advarsel, statisk modell brukes
- `ValidationError` → advarsel, statisk modell brukes
- Ugyldig JSON → advarsel, statisk modell brukes

### 3. `analysis/suitability_engine.py`

Nytt kriterium (vekt 10%):
```
Criterion 6: Biologisk Operasjonell Beredskap (10%)
```

Eksisterende vekter skalert ned med 0.9:
```
Premium Volume:          25.0% → 22.5%
Loss Stability:          20.0% → 18.0%
Balance Sheet Strength:  20.0% → 18.0%
Cost Savings Potential:  20.0% → 18.0%
Operational Readiness:   15.0% → 13.5%
Bio Readiness (ny):       0.0% → 10.0%
```

Scoring av Criterion 6 (prioritert rekkefølge):
1. `operator.bio_readiness_score` (0–100) hvis angitt
2. C5AI+ `overall_data_quality` fra forecast-fil
3. Proxy fra `has_risk_manager` og `governance_maturity`

### 4. `requirements.txt`

Nye avhengigheter:
```
scikit-learn>=1.3.0
networkx>=3.1
pytest>=7.4.0
```

---

## Integrasjonseksempel – Steg for steg

### Steg 1: Generer C5AI+ prognose

```bash
python examples/run_c5ai_demo.py
```

Dette genererer `examples/demo_risk_forecast.json`.

### Steg 2: Oppdater PCC-input

Rediger `data/sample_input.json` og legg til:
```json
"c5ai_forecast_path": "examples/demo_risk_forecast.json"
```

### Steg 3: Kjør PCC-verktøy som normalt

```bash
python main.py
```

Forventet output:
```
[C5AI+] Forecast loaded: scale=0.632 | HAB=51.6% | Lice=25.3% | ...
E[arlig tap]: NOK 14.3 M  (ned fra NOK 22.6 M)
```

---

## Biologisk risikofordeling i rapport

Når C5AI+ er aktiv, inneholder `SimulationResults.bio_loss_breakdown` et
`Dict[str, np.ndarray]` der hvert array har form `(N, T)` og representerer
den forventede årsaksandelen av tapene fra hver biologisk risikotype.

Dette kan brukes i `chart_generator.py` til å lage et stablet stolpediagram:

```python
if sim.c5ai_enriched and sim.bio_loss_breakdown:
    annual_means = {
        rt: arr.mean(axis=0)       # (T,) – mean across simulations
        for rt, arr in sim.bio_loss_breakdown.items()
    }
    # Plot stacked bar chart by risk type over 5 years
```

---

## Feilhåndtering og fallback

| Scenarie | Atferd |
|---|---|
| `c5ai_forecast_path` ikke satt | Statisk modell brukes (ingen endring) |
| Fil finnes ikke | `RuntimeWarning`, statisk modell |
| Ugyldig JSON | `RuntimeWarning`, statisk modell |
| Valideringsfeil | `RuntimeWarning`, statisk modell |
| `c5ai_vs_static_ratio = 0` | `ValidationError` kastes under validering |
| Scale > 5.0 | `ValidationError` – usannsynlig verdi flagges |

---

## Testing

```bash
# Kjør alle tester
pytest tests/ -v

# Kjør kun integrasjonstester
pytest tests/test_monte_carlo_integration.py -v

# Kjør kun suitability-tester
pytest tests/test_suitability_bio_criterion.py -v
```

---

## Ytelse og skalering

| Parameter | Anbefaling |
|---|---|
| Monte Carlo simuleringer | 10,000 (standard), uendret |
| C5AI+ kjøretid | < 5 sekunder for 3 lokaliteter (prior-mode) |
| C5AI+ kjøretid med ML | 10–30 sekunder avhengig av datasett |
| JSON-filstørrelse | Typisk 50–200 KB |

C5AI+ trenger ikke kjøres på nytt for hver PCC-analyse – `risk_forecast.json`
kan gjenbrukes inntil nye observasjonsdata gjør prognosen utdatert.
Anbefalt: oppdater prognose kvartalsvis eller ved vesentlige hendelser.

---

## Antakelser og begrensninger

1. **C5AI+ og PCC-verktøyet bruker samme valuta (NOK)** – ingen konvertering
2. **C5AI+ antar stasjonær risiko over 5 år** – trendmodellering er Phase 3
3. **Scale-faktor er operatørnivå** – ikke disaggregert per år. For fasespesifikke risikoer bør fremtidig versjon støtte år-for-år skalering
4. **Nettverksrisiko** krever `networkx`. Uten det er nettverksjusteringer deaktivert
5. **HAB-modellen** har lavere presisjon uten klorofyll-data
6. **Kleine operatører** (< 3 lokaliteter, < 2 års data) vil typisk få `PRIOR_ONLY` quality flag
