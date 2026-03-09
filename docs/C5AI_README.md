# C5AI+ v5.0 – Biologisk Risikoprognose for Akvakultur

## Oversikt

C5AI+ v5.0 er en modulær AI-plattform for biologisk risikovurdering i norsk akvakultur.
Den fungerer som en frittstående modul som produserer `risk_forecast.json`-filer,
som kan konsumeres av PCC Feasibility Tool.

### Støttede risikodomener

| Domene | Status | Modell |
|---|---|---|
| HAB (skadelige algeoppblomstringer) | Fase 1 (aktiv) | RandomForest + prior |
| Lakselus | Fase 1 (aktiv) | RandomForest + prior |
| Manet | Fase 2 (placeholder) | Prior-only |
| Patogener | Fase 2 (placeholder) | Prior-only |

---

## Installasjon

```bash
# Grunnleggende avhengigheter
pip install -r requirements.txt

# Avanserte ML-funksjoner (valgfritt, for CATE/T-Learner)
pip install econml lightgbm xgboost
```

---

## Katalogstruktur

```
c5ai_plus/
  config/
    c5ai_settings.py        # Alle C5AI+-konstanter og terskler
  data_models/
    biological_input.py     # Inputskjema: SiteMetadata, EnvironmentalObservation, osv.
    forecast_schema.py      # Outputskjema: RiskForecast, SiteForecast, RiskTypeForecast
  ingestion/
    data_loader.py          # Last og valider biologiske inputdata
  feature_engineering/
    features.py             # Bygg feature-vektorer for ML-modeller
  forecasting/
    base_forecaster.py      # Abstrakt baseklasse (fit/predict/forecast)
    hab_forecaster.py       # HAB-prognose (RandomForestClassifier)
    lice_forecaster.py      # Luseprognoseregressjon (RandomForestRegressor)
    jellyfish_forecaster.py # Placeholder (Phase 2)
    pathogen_forecaster.py  # Placeholder (Phase 2)
  network/
    site_network.py         # Nettverksbasert risikospredning (networkx)
  causal/
    cate_module.py          # Valgfri T-Learner CATE (krever econml)
  export/
    forecast_exporter.py    # Serialiser RiskForecast → JSON
  validation/
    forecast_validator.py   # Valider forecast-fil
  pipeline.py               # Hoved-orkestreringsklasse
```

---

## Quickstart

### 1. Kjør C5AI+ pipeline (programmatisk)

```python
from c5ai_plus.pipeline import ForecastPipeline
from c5ai_plus.data_models.biological_input import (
    C5AIOperatorInput, SiteMetadata, EnvironmentalObservation
)

sites = [
    SiteMetadata(
        site_id="site-001",
        site_name="Min Lokalitet",
        latitude=60.45,
        longitude=6.10,
        species="Atlantic Salmon",
        biomass_tonnes=1500,
        biomass_value_nok=108_000_000,
    )
]

env_obs = [
    EnvironmentalObservation(site_id="site-001", year=2024, month=7, sea_temp_celsius=16.2)
]

operator_input = C5AIOperatorInput(
    operator_id="min-operatoer-001",
    operator_name="Min Oppdrett AS",
    sites=sites,
    env_observations=env_obs,
    forecast_years=5,
)

pipeline = ForecastPipeline()
forecast = pipeline.run(
    operator_input,
    static_mean_annual_loss=22_600_000,    # Fra PCC-verktoyets statiske modell
    output_path="risk_forecast.json",
)

print(f"Skalafaktor: {forecast.scale_factor:.3f}")
print(f"Total E[arlig tap]: NOK {forecast.total_expected_annual_loss/1e6:,.1f} M")
```

### 2. Kjør som CLI

```bash
python -m c5ai_plus.pipeline \
  --input c5ai_input.json \
  --output risk_forecast.json \
  --static-loss 22600000
```

### 3. Integrer med PCC-verktoy

Legg til i `sample_input.json`:
```json
{
  "c5ai_forecast_path": "risk_forecast.json"
}
```

Deretter kjor PCC-verktoyets som normalt:
```bash
python main.py --input sample_input.json
```

---

## Datakrav

### Minimumskrav (prior-based prediksjon)

Systemet fungerer uten noen observasjoner – det bruker da konfigurasjonsbaserte
prior-distribusjoner. Resultater vil ha `data_quality_flag = "PRIOR_ONLY"`.

### Anbefalt (ML-basert prediksjon)

| Datakilde | Minimum | Ideelt |
|---|---|---|
| Havtemperatur (månedlig) | 24 måneder | 5 år |
| Saltholdighet | Valgfritt | Anbefalt |
| Klorofyll-a | Valgfritt | Nyttig for HAB |
| Lusregistreringer (ukentlig) | 8 uker | 2 år |
| HAB-varsler (historisk) | Ingen krav | 3+ hendelser |

### Datakvalitetsflagg

| Flagg | Dekning | Modell brukt |
|---|---|---|
| `SUFFICIENT` | ≥70% obs, ≥24 måneder | RandomForest ML |
| `LIMITED` | 40–69% dekning | Blanding prior/ML |
| `POOR` | 10–39% dekning | Prior med historisk justering |
| `PRIOR_ONLY` | <10% dekning | Ren prior |

---

## Eksportformat (risk_forecast.json)

Se `examples/risk_forecast_example.json` for et komplett eksempel.

Nøkkelfelter som PCC-verktøyet bruker:

```json
{
  "operator_aggregate": {
    "total_expected_annual_loss": 14280000,
    "c5ai_vs_static_ratio": 0.632,
    "loss_breakdown_fractions": {
      "hab": 0.5156,
      "lice": 0.2533,
      "jellyfish": 0.0924,
      "pathogen": 0.1387
    }
  }
}
```

- `c5ai_vs_static_ratio`: Multipliseres med simulerte tap i MonteCarloEngine
- `loss_breakdown_fractions`: Brukes til disaggregert biologisk risikorapportering

---

## Læringsloop (Phase 3 – fremtidig)

```
OBSERVE   → Innsamle nye tapshendelser og biologiske observasjoner
PREDICT   → Kjøre C5AI+ med oppdaterte data
ACT       → Oppdatert risikoprising til PCC-modell
MEASURE   → Sammenligne prediksjoner med faktiske hendelser
LEARN     → Inkrementell retrening av modeller (shadow mode)
```

Shadow mode: Ny modell kjøres parallelt med produksjonsmodell. Overgang til ny
modell krever eksplisitt godkjenning.

---

## Anbefalinger for videre arbeid

1. **Dataanskaffelse**: Inngå datadelingsavtaler med Havforskningsinstituttet (NorKyst800), Barentswatch (lusedata), og Mattilsynet (HAB-varsler)
2. **HAB-modell**: Integrer klorofyll-a data for å forbedre presisjonen vesentlig
3. **Jellyfish/Pathogen**: Implementer ML-modeller i Fase 2 med tilgjengelige datasett
4. **CATE**: Aktiver T-Learner (econml) for å estimere behandlingseffekter (lusebehandling, forebyggende tiltak)
5. **Kontinuerlig læring**: Implementer inkrementell retrening og shadow mode deployment
