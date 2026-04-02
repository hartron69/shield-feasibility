# Sprint: Locality Monte Carlo Integration

**Date:** 2026-03-30
**Status:** Complete
**Tests:** 2048 passed, 0 failed (+97 new)
**Frontend:** 107 modules, 0 errors

---

## Objective

Bridge `LocalityRiskProfile` (Sprint 1) into the existing `MonteCarloEngine` to produce
per-locality stochastic loss distributions: EAL, SCR (VaR 99.5%), VaR 95/99, TVaR 95, and
a domain-level breakdown. No new simulation engine — reuse the compound Poisson-LogNormal
engine with `DomainCorrelationMatrix.expert_default()`.

---

## Deliverables

### Backend — new files
| File | Description |
|---|---|
| `models/locality_mc_inputs.py` | Bridge: `LocalityRiskProfile` → `LocalityMonteCarloInput` → `MonteCarloEngine` |
| `backend/services/locality_mc_runner.py` | `run_locality_mc()`, `run_locality_mc_batch()`, `LocalityMCResult` |
| `backend/api/locality_mc.py` | `GET /api/localities/{id}/mc`, `POST /api/localities/mc-batch` |
| `tests/test_locality_mc.py` | 97 tests, 10 classes |

### Frontend — new/modified files
| File | Change |
|---|---|
| `frontend/src/api/client.js` | Added `fetchLocalityMC(id, nSims)` |
| `frontend/src/components/live_risk/LocalityMCPanel.jsx` | New panel: KPI cards, domain bar, transparency table |
| `frontend/src/components/live_risk/LocalityLiveRiskPage.jsx` | Added "Tap (MC)" tab wired to `LocalityMCPanel` |

---

## Architecture

```
LocalityRiskProfile (Sprint 1)
    → build_locality_mc_inputs()            models/locality_mc_inputs.py
        → score_to_frequency_multiplier()   sigmoid, score=50 → 1.0, range 0.40–1.60
        → score_to_severity_multiplier()    sigmoid, score=50 → 1.0, range 0.70–1.30
        → domain_freq_factor               bio×0.60 + env×0.25 + ops×0.15
        → domain_sev_factor                struct×0.60 + ops×0.25 + bio×0.15
        → non_bio_domain_fracs             struct/env/ops normalized from domain_weights
    → LocalityMonteCarloInput
    → MonteCarloEngine (existing, unchanged)
        + DomainCorrelationMatrix.expert_default()
        + cage_multipliers
        + non_bio_domain_fracs
    → SimulationResults
    → LocalityMCResult
```

### Key mapping constants
- `_BIOMASS_VALUE_PER_TONNE_NOK = 65_000`
- `base_loss_frequency`: `{open_coast: 0.22, semi_exposed: 0.15, sheltered: 0.09}`
- `base_severity_nok`: 18% of biomass value
- `lice_pressure_factor = hab_risk_factor = 1.0` (already integrated in domain_scores — no double-counting)
- Domain correlation: `expert_default()` — bio-struct=0.20, env-struct=0.60, env-bio=0.40, ops-struct=0.35

### API
```
GET  /api/localities/{id}/mc?n_simulations=5000
POST /api/localities/mc-batch  { locality_ids: [...], n_simulations: 5000 }
```

Validation: `500 ≤ n_simulations ≤ 20_000`. Unknown IDs → 404 (single) or error entry (batch).
Batch reproducibility: each locality uses `seed + index`.

---

## Test coverage (97 tests, 10 classes)

| Class | Tests | What |
|---|---|---|
| `TestSigmoidFunctions` | 9 | Neutrality at 50, monotonicity, extremes, exact calibration |
| `TestBuildLocalityMCInputs` | 12 | All three KH localities, effective events/severity, non-bio fracs |
| `TestOperatorInput` | 8 | Valid `OperatorInput` structure, `RiskParameters` consistency |
| `TestDomainMultiplierApplication` | 6 | High bio → higher freq; high struct → higher sev |
| `TestRunLocalityMC` | 12 | Result structure, non-negative, EAL ≤ SCR, all fields present |
| `TestDomainBreakdownWithCages` | 6 | domain_fracs sum=1, domain_eal_nok non-negative |
| `TestBatchRunner` | 8 | Unknown IDs produce error entries, valid IDs return results |
| `TestLocalityMCAPI` | 11 | HTTP 200/404/422, batch partial failure |
| `TestKHKnownValues` | 15 | EAL ranges: Kornstad/Leite 1–25 MNOK, Hogsnes 0.5–20 MNOK |
| `TestMonotonicity` | 10 | Higher risk score → higher EAL (seed-stable, N=2000) |

---

## Frontend panel — LocalityMCPanel

- Simulations selector: 1 000 / 2 000 / 5 000 / 10 000 (default 5 000)
- "Kjør simulering" button — re-runs on demand; auto-runs on mount
- KPI cards: EAL, SCR (VaR 99.5%), VaR 99%, VaR 95%, Std. avvik, TVaR 95%
- Domain bar: pure SVG stacked bar (biological/structural/environmental/operational)
- Domain table: per-domain EAL in NOK + fraction %
- Transparency section (collapsible): base freq, freq multiplier, effective freq, base severity, severity multiplier, effective severity, total_risk_score, n_simulations, domain correlation flag

---

## Build status

```
pytest tests/ -q        → 2048 passed, 0 failed
npm run build           → 107 modules, 0 errors
```
