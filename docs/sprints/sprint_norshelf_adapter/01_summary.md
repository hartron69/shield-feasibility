# Sprint: NorShelf Adapter — BW Havdata til ILA Motor

**Date:** 2026-04-03
**Status:** Complete
**Tests:** 2153 passed, 0 failed (+37 new)
**Frontend:** 109 modules, 0 errors

---

## Objective

Integrere BarentsWatch NorShelf-data (havstrøm u/v, overflatetemperatur T_water,
bølgehøyde Hs) i ILA risiko-motoren. Data brukes til å forbedre tre
MRE-1 input-parametre som tidligere var basert på mock-verdier.

---

## Architecture

```
BarentsWatch NorShelf API
  GET /v2/geodata/ocean/currents      → u, v  (m/s)
  GET /v2/geodata/ocean/temperature   → T_water (°C)
  GET /v2/geodata/weather/wave        → Hs (m)
        ↓ (OAuth2 Bearer — samme token som barentswatch_client)
backend/services/norshelf_adapter.py
  get_norshelf(lat, lon) → NorShelfData(u, v, t_water, hs, dqi)
        ↓ (cache TTL 55 min)
c5ai_plus/biological/ila/input_builder.py
  _compute_stressniva(..., norshelf)      → stressniva_norm (forbedret)
  _compute_nabo_smittepress(..., norshelf) → i_fraksjon_naboer (strøm-skalert)
  bygg_mre1_input_live()                  → ILAMre1Input
        ↓
backend/api/ila.py   GET /api/ila/{id}/mre1  → { norshelf_dqi, norshelf, ... }
```

---

## New file: `backend/services/norshelf_adapter.py`

### DQI-logikk

| Alder på cache | Situasjon | DQI |
|---|---|---|
| < 55 min | Ferske BW-data | 1 |
| 55 min – 6 t | BW midlertidig utilgjengelig | 2 |
| > 6 t / ingen cache | BW utilgjengelig — fallback | 3 |

### Fallback-verdier (Møre og Romsdal, april)

| Felt | Verdi |
|---|---|
| u | 0.05 m/s |
| v | 0.03 m/s |
| T_water | 6.5 °C |
| Hs | 0.8 m |

### Cache-nøkkel
`(lat, lon)` avrundet til 2 desimaler (~1 km grid). In-process dict.
Auth: re-bruker `_get_token()` fra `barentswatch_client.py`.

### Responsformat-toleranse
Parsere (`_parse_u_v`, `_parse_temperature`, `_parse_hs`) håndterer
BW-tidsserie (liste av dict) og punkt-respons, samt alternative feltnavn
(`u/eastward`, `temperature/value/seaSurfaceTemperature`, `hs/significantWaveHeight`).
Delvis respons aksepteres — manglende felt fylles med fallback-verdi.

---

## Changes to `input_builder.py`

### `_compute_stressniva()` — 5 komponenter

Ny vektfordeling (gammel: lice=0.30, temp=0.15, oxy=0.35, treat=0.20):

| Komponent | Vekt | Kilde |
|---|---|---|
| `lice_stress` | 0.25 | Live BW |
| `temp_stress` | 0.15 | **NorShelf T_water** (DQI≤2) / mock-temp (DQI=3) |
| `oxy_stress` | 0.30 | Live BW |
| `treat_stress` | 0.15 | Live BW |
| `bolge_stress` | 0.15 | **NorShelf Hs** (DQI≤2) / 0.0 (DQI=3) |

`bolge_stress = min(1.0, max(0, Hs − 1.0) / 3.0)`
Begrunnelse: Hs > 1 m gir operasjonelle hindringer og økt virusspredning via
bølge-aerosol. Terskel 1 m, maks stress ved 4 m.

### `_compute_nabo_smittepress()` — strømfaktor

```
current_speed = sqrt(u² + v²)
current_factor = 1.0 + min(1.0, current_speed / 0.3)  # ∈ [1.0, 2.0]
i_fraksjon_proxy = min(1.0, base_lice_proxy × current_factor)
```

Begrunnelse: høy strøm (≥ 0.3 m/s) dobler effektiv HPR0-transport fra naboer.
Gjelder kun ved DQI ≤ 2.

---

## Changes to `backend/api/ila.py`

`GET /api/ila/{locality_id}/mre1` returnerer nå:

```json
{
  "norshelf_dqi": 1,
  "norshelf": {
    "u": 0.12,
    "v": 0.04,
    "t_water": 7.1,
    "hs": 0.9,
    "dqi": 1,
    "current_speed": 0.1265
  },
  ...eksisterende MRE-1 felt...
}
```

Cache treffer: `get_norshelf()` kalles to ganger per request (i `input_builder`
og i `ila.py`) — returnerer samme cache-entry begge ganger (ingen ekstra BW-kall).

---

## Tests: `tests/ila/test_norshelf_adapter.py` (37 nye tester)

| Klasse | Tests | Dekning |
|---|---|---|
| `TestNorShelfData` | 4 | current_speed, to_dict |
| `TestCacheDqi` | 5 | DQI-grenseverdier (55 min, 6 t) |
| `TestFallback` | 3 | DQI=3, sane values |
| `TestParsers` | 12 | u/v, temp, Hs — alle feltnavn og listeformat |
| `TestGetNorshelfNoToken` | 2 | Ingen BW-token → fallback |
| `TestGetNorshelfLiveFetch` | 5 | Cache, stale/refresh, DQI-overgang |
| `TestNorShelfInputBuilderIntegration` | 6 | Bølgestress, temp-prioritering, strømfaktor |

Alle BW API-kall patches — ingen nettverkstilgang i tester.

---

## Build status

```
pytest tests/ -q    → 2153 passed, 0 failed (+37)
npm run build       → 109 modules, 0 errors
```

---

## What's NOT implemented (requires production infra)

- Persistent disk-cache (Redis / Postgres) — nåværende er in-process
- BW NorShelf presis responsformat-verifisering (avhenger av BW-miljøet)
- Historisk NorShelf tidsserie for retroaktiv kalibrering
- `bolge_stress` og `current_factor` i frontend-forklaring (ILARiskTab)
