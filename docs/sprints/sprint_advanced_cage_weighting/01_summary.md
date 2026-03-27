# Sprint: Advanced Cage Weighting

**Date:** 2026-03-26
**Status:** Complete
**Tests:** 1734 passed, 0 failed (+82 new)
**Build:** 0 errors, 105 modules

---

## Objective

Extend the cage portfolio model (Sprint 2) from biomass-only weighting to a
multi-factor weighting engine. A locality's effective domain risk multipliers
are now driven by up to five components per cage: biomass, economic value,
consequence severity, operational complexity, and structural criticality.

---

## Deliverables

### New files
| File | Description |
|---|---|
| `config/cage_weighting.py` | Pure constants: DOMAIN_COMPONENT_WEIGHTS, CAGE_TYPE_DEFAULT_SCORES, failure-mode multipliers, SPOF/redundancy scales |
| `models/cage_weighting.py` | Multi-factor weighting engine: `compute_locality_domain_multipliers_advanced()`, `CageWeightDetail`, `AdvancedWeightingResult` |
| `tests/test_cage_weighting.py` | 82 tests across 13 classes |

### Modified files
| File | Changes |
|---|---|
| `models/cage_technology.py` | `CagePenConfig` +7 optional advanced fields; `__post_init__` validation; `to_dict`/`from_dict` updated |
| `backend/schemas.py` | `CagePenInput` +7 fields; new `CageWeightDetail` Pydantic model; `LocalityCageRiskProfile` +`cage_weight_details`, `weighting_mode`, `warnings` |
| `backend/services/operator_builder.py` | Uses `compute_locality_domain_multipliers_advanced()`; maps internal dataclass to Pydantic schema |
| `frontend/src/data/cageTechnologyMeta.js` | Added `CAGE_TYPE_DEFAULT_SCORES`, `FAILURE_MODE_OPTIONS`, `REDUNDANCY_OPTIONS` |
| `frontend/src/components/InputForm/CagePortfolioPanel.jsx` | Per-cage "Avansert" collapsible panel with 6 advanced fields + default badges |
| `frontend/src/components/results/CageRiskProfileTab.jsx` | Weighting mode badge, warnings display, collapsible per-cage domain weight details table |
| `frontend/src/App.css` | CSS for `.cage-adv-*` classes |

---

## Formula

Five weighting components per cage:

| Component | Derivation |
|---|---|
| biomass | `cage.biomass_tonnes` |
| value | `cage.biomass_value_nok` (0 if not set) |
| consequence | `value × consequence_factor × failure_mode_multiplier` |
| complexity | `operational_complexity_score` or cage-type default |
| criticality | `base_criticality × spof_mult × redundancy_scale` |

Steps:
1. Derive raw components per cage
2. Max-normalise each component across the locality
3. Compute domain raw weight: `Σ_k DOMAIN_COMPONENT_WEIGHTS[domain][k] × norm_k`
4. Normalise raw weights across cages per domain
5. `locality_mult[domain] = Σ_cage weight[cage][domain] × CAGE_DOMAIN_MULT[type][domain]`

**Domain component weights:**

| Domain | biomass | value | consequence | complexity | criticality |
|---|---|---|---|---|---|
| biological | 0.50 | 0.25 | 0.15 | 0.05 | 0.05 |
| structural | 0.25 | 0.15 | 0.30 | 0.15 | 0.15 |
| environmental | 0.30 | 0.10 | 0.25 | 0.25 | 0.10 |
| operational | 0.15 | 0.10 | 0.25 | 0.30 | 0.20 |

---

## Backward Compatibility

If no cage carries any advanced data → exact fall-back to biomass-only
`compute_locality_domain_multipliers()` with `weighting_mode="biomass_only"`.

Advanced data detection: any of `biomass_value_nok`, non-unit `consequence_factor`,
`operational_complexity_score`, `structural_criticality_score`, `single_point_of_failure=True`,
`redundancy_level`, or non-proportional `failure_mode_class`.

---

## Test Results

```
tests/test_cage_weighting.py: 82 passed
Full suite: 1734 passed, 0 failed
```

Test classes:
- `TestConfigIntegrity` — DOMAIN_COMPONENT_WEIGHTS row sums = 1.0
- `TestCageHasAdvancedData` — trigger detection for each field
- `TestRawComponentDerivation` — per-component calculation
- `TestMaxNormalise` — normalisation helper
- `TestBackwardCompatibility` — biomass-only exact match
- `TestAdvancedWeightingFormula` — formula correctness, mode detection
- `TestScenarioA_ValueWeighting` — high-value cage gets more structural weight
- `TestScenarioB_SPOFandClosed` — closed SPOF cage elevates structural/ops
- `TestScenarioC_SubmergedCriticality` — criticality overrides biomass share
- `TestScenarioD_BackwardCompat` — old inputs unchanged
- `TestValidation` — invalid fields raise ValueError
- `TestDomainWeightNormalization` — per-domain weights sum to 1.0
- `TestEdgeCases` — all open_net → mult=1.0, binary_high_consequence, warnings

---

## Non-Goals (explicitly out of scope)

- Per-cage Monte Carlo simulations (locality remains the simulation unit)
- Bayesian failure propagation across cages
- Real-time cage sensor integration
- Time-varying cage risk profiles
