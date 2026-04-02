# Sprint: ILA Risk Module

**Date:** 2026-04-02
**Status:** Complete
**Tests:** 2116 passed, 0 failed (+68 new)
**Frontend:** 108 modules, 0 errors (+2 files)

---

## Objective

Integrate two ILA risk models (MRE-1 and MRE-2) as a new sub-module of the C5AI+ v5.0
biological domain. MRE-1 produces an instantaneous P_total snapshot from 7 transmission
sources. MRE-2 runs a 52-week SEIR seasonal progression with cumulative hazard. Both models
are ported from the reference implementations in `/reference/` — mathematics unchanged,
input/output adapted to the Shield data model.

---

## Architecture

This sprint implements the **pure computation and API layer** of the ILA module, adapted
to the current mock-based architecture (no PostgreSQL / Celery). The DB-backed components
(ORM models, Alembic migrations, Celery tasks, auth-gated endpoints) are documented in
`CLAUDE_CODE_ILA_SHIELD_PLATFORM.md` and ready for integration when the production DB layer
is available.

```
ILAMre1Input (7 risk sources)
    ↓ kjor_mre1()                            c5ai_plus/biological/ila/mre1.py
    → ILAMre1Resultat (P_total, varselnivå, per-kilde P, attribusjon, e_tap_mnok)

ILALokalitetProfil (mock per-locality params)   c5ai_plus/biological/ila/input_builder.py
    ↓ bygg_mre1_input()
    → ILAMre1Input

kjor_mre2(sesong_uker=52, hpr0_tetthet, ...)    c5ai_plus/biological/ila/mre2.py
    → List[SEIRUke]  (S/E/I/R fraksjon, λ, p_uke, p_kumulativ, varselnivå per uke)

juster_patogen_prior(statisk, ila_p_total)       c5ai_plus/biological/ila/patogen_kobling.py
    → blended prior, capped at 0.70
```

### Varselterskler (identisk med spesifikasjon)

| P_total   | Nivå  | Alvorlighet |
|-----------|-------|-------------|
| < 0.05    | GRØNN | ingen       |
| ≥ 0.05    | ILA01 | lav         |
| ≥ 0.20    | ILA02 | middels     |
| ≥ 0.50    | ILA03 | høy         |
| ≥ 0.80    | ILA04 | kritisk     |

### MRE-1 kildeformler

| Kilde  | Formel (port fra reference/mre_full_comparison.py)          |
|--------|-------------------------------------------------------------|
| HYDRO  | `1 − exp(−hpr0 × i_naboer × 8)`                           |
| WB     | `1 − (1 − hpr0×(1−desinfeksjon))^besøk`                   |
| OPS    | `0.01 × delte_ops × (1+tetthet) × (1+2×stress)`, max 0.40 |
| SMOLT  | `0.15 × exp(−0.15 × uker_siden_utsett)`                    |
| WILD   | `0.005 × villfisk × hpr0 × 52`                             |
| MUTATE | `mutasjonsrate × (1 + tetthet)`                            |
| BIRD   | `0.01` (sesong) / `0.002` (utenfor sesong)                 |
| Total  | `1 − ∏_k(1 − P_k)`, capped 0.999                          |

### MRE-2 SEIR parametere

| Konstant | Verdi  | Betydning                     |
|----------|--------|-------------------------------|
| σ        | 1/3    | E→I overgangsrate (uke⁻¹)    |
| ρ        | 1/10   | I→R overgangsrate (uke⁻¹)    |
| λ_intro  | `base_rate × hpr0`              |
| λ_amp    | `amp_faktor × I × 2.5`         |
| λ_hydro  | `hydro_faktor × hpr0 × 0.3`   |

---

## New files

### Python — backend
| File | Description |
|---|---|
| `c5ai_plus/biological/__init__.py` | Package init |
| `c5ai_plus/biological/ila/__init__.py` | ILA sub-module package |
| `c5ai_plus/biological/ila/mre1.py` | MRE-1 øyeblikks-snapshot |
| `c5ai_plus/biological/ila/mre2.py` | MRE-2 SEIR ukentlig motor |
| `c5ai_plus/biological/ila/patogen_kobling.py` | ILA → C5AI+ patogen-prior blanding |
| `c5ai_plus/biological/ila/input_builder.py` | Mock-profiler for 4 KH/LM lokaliteter |
| `backend/api/ila.py` | 3 endepunkter: `/mre1`, `/mre2`, `/portfolio` |
| `tests/ila/__init__.py` | Test-pakke |
| `tests/ila/test_mre1.py` | 35 MRE-1 tester (8 klasser) |
| `tests/ila/test_mre2.py` | 21 MRE-2 tester (4 klasser) |
| `tests/ila/test_patogen_kobling.py` | 8 patogen-prior tester |
| `tests/ila/test_ila_api.py` | 17 API-integrasjonstester |

### Python — modified
| File | Change |
|---|---|
| `backend/main.py` | Registered `ila_router` |

### Frontend
| File | Description |
|---|---|
| `frontend/src/components/live_risk/ILARiskTab.jsx` | Ny fane: varselnivå-header, kilde-tabell, SVG sesongkurve, SEIR-badge |
| `frontend/src/components/live_risk/LocalityLiveRiskPage.jsx` | Added "ILA-risiko" tab (9 total) |

---

## API endpoints

```
GET  /api/ila/{locality_id}/mre1          → P_total, varselnivå, kilde-P, attribusjon, e_tap_mnok
GET  /api/ila/{locality_id}/mre2          → 52-ukers SEIR tilstand + p_kumulativ
GET  /api/ila/portfolio                   → Alle profiler sortert etter P_total
```

Kjente lokaliteter med ILA-profil: `KH_S01`, `KH_S02`, `KH_S03`, `LM_S01`

---

## Mock ILA-profiler (input_builder.py)

| ID     | HPR0  | ILA-sone    | Desinfeksjon | Biomasse NOK |
|--------|-------|-------------|--------------|--------------|
| KH_S01 | 0.28  | fri         | 0.85         | 19.5 MNOK    |
| KH_S02 | 0.32  | overvaking  | 0.80         | 16.25 MNOK   |
| KH_S03 | 0.15  | fri         | 0.90         | 9.75 MNOK    |
| LM_S01 | 0.35  | fri         | 0.82         | 22.75 MNOK   |

---

## Test coverage (68 tests, 5 filer)

| Fil | Tests | Dekning |
|---|---|---|
| `test_mre1.py` | 35 | Varselnivå-terskler, matematiske invarianter, sensitivitet, scenarioer, KH-verdier |
| `test_mre2.py` | 21 | SEIR-sum=1, monotonisitet, dynamikk, varselnivå-konsistens, serialisering |
| `test_patogen_kobling.py` | 8 | Blanding, cap, vekt-grenseverdier |
| `test_ila_api.py` | 17 | HTTP 200/404/422, batch-struktur, SEIR-konsistens, portefølje-sortering |
| `__init__.py` | — | Pakke-init |

---

## What's NOT yet implemented (requires production DB)

Per `CLAUDE_CODE_ILA_SHIELD_PLATFORM.md`, following require PostgreSQL/Celery infrastructure:

- `db/models_ila.py` — SQLAlchemy ORM-modeller (5 tabeller)
- Alembic-migrasjoner
- `connectors/tasks_ila.py` — Celery MRE-1/MRE-2 tasks
- Automatisk trigger fra `BarentswatchDiseaseConnector.store()`
- Auth-gated endpoints (`POST /api/ila/{id}/profil`, rolle-sjekk)
- `ILAPortfolioPage.jsx` med korrelasjonsmatrise-heatmap
- Pipeline-integrasjon: `juster_patogen_prior()` i `c5ai_plus/pipeline.py`

---

## Build status

```
pytest tests/ -q        → 2116 passed, 0 failed (+68)
npm run build           → 108 modules, 0 errors
```
