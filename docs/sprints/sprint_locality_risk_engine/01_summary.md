# Sprint – Locality Risk Engine (Sprint 1)

**Date:** 2026-03-30
**Tests after:** 1940 passed, 0 failed (+82 new)
**Frontend build:** unchanged (backend-only sprint)

---

## Objective

Establish `LocalityRiskProfile` as the single source of truth for risk per locality.
The profile combines Live Risk signals, static locality metadata, and cage portfolio
weighting into one explicit, structured, inspectable object.

This is a foundation sprint. No full locality Monte Carlo, no frontend redesign,
no existing modules rewritten.

---

## Architecture Note

The new layer sits between Live Risk (operational feed) and future simulation/aggregation:

```
Live Risk feed                ← existing (unchanged)
     ↓
LocalityRiskBuilder           ← new (Sprint 1)
     ↓
LocalityRiskProfile           ← new (Sprint 1)
     ↓
API /api/localities/…         ← new (Sprint 1)
     ↓
(future) locality Monte Carlo, portfolio aggregation, mitigation, optimisation
```

The builder is purely compositional — it calls existing services (live_risk_mock,
confidence_scoring, cage_weighting) and assembles results into the profile model.
It does not recalculate Live Risk internals.

---

## Files Created

| File | Purpose |
|---|---|
| `models/locality_risk_profile.py` | Data models: `LocalityRiskProfile`, `DomainRiskScores`, `DomainRiskWeights`, `RiskSourceSummary` |
| `backend/services/locality_risk_builder.py` | Builder: `build_locality_risk_profile()`, `build_locality_risk_profiles()` |
| `backend/api/localities.py` | API router: `GET /api/localities/{id}/risk-profile`, `POST /api/localities/risk-profiles` |
| `tests/test_locality_risk_profile.py` | 82 tests (8 test classes) |

## Files Modified

| File | Change |
|---|---|
| `backend/main.py` | Registered `localities_router` |

---

## LocalityRiskProfile Structure

```python
@dataclass
class LocalityRiskProfile:
    # Identity
    locality_id, locality_name, company_name, region, drift_type

    # Exposure & biomass
    biomass_tonnes, biomass_value_nok, exposure_factor

    # Cage portfolio
    cage_count, cage_weighting_mode  # "advanced" | "biomass_only" | "none"

    # Risk signal
    domain_scores:      DomainRiskScores     # raw 0–100 per domain
    domain_weights:     DomainRiskWeights    # normalized contribution fractions (sum=1)
    domain_multipliers: Dict[str, float]     # cage-derived, or 1.0 defaults
    scale_factors:      Dict[str, float]     # fixed model weights {bio:0.35, ...}

    # Pattern detection
    concentration_flags: List[str]   # e.g. ["high_biological_dominance", "high_exposure"]
    top_risk_drivers:    List[str]   # domains sorted by weighted contribution

    # Confidence & provenance
    confidence_level: str            # "high" | "medium" | "low"
    confidence_notes: List[str]
    source_summary:   RiskSourceSummary
    used_defaults:    List[str]      # explicit when defaults substitute missing data

    metadata: Dict[str, Any]         # lat, lon, locality_no, mtb_tonnes, etc.
```

---

## Design Decisions

### domain_weights vs scale_factors
- `scale_factors` = **fixed** model-level domain weights `{bio:0.35, struct:0.25, env:0.25, ops:0.15}` (from `_compute_risk` in live_risk_mock).
- `domain_weights` = **dynamic** per-locality, per-day normalized contributions: `weight_i = (score_i × scale_factor_i) / Σ(score × sf)`. Reflects "how much of today's risk is from each domain."

### Cage weighting
- If cages are supplied: `compute_locality_domain_multipliers_advanced(cages)` is called and result stored.
- If no cages: `domain_multipliers = {all: 1.0}`, `cage_weighting_mode = "none"`, noted in `used_defaults`.

### Biomass value
- Derived as `biomass_tonnes × 65,000 NOK/t` (standard valuation constant).
- Not pulled from `_C5AI_SITE_META` to keep the builder generic for all localities.

### Concentration flags
- `high_{domain}_dominance` — when any domain's normalized weighted contribution ≥ 50%
- `high_exposure` — when `exposure_factor ≥ 1.1`

### bw_live heuristic
- `bw_live = sync_delay_hours < 6.0` — fast proxy for BarentsWatch freshness without making a network call in the builder.

---

## API Endpoints

### `GET /api/localities/{id}/risk-profile`
Returns the full `LocalityRiskProfile` as JSON.
Returns 404 for unknown locality IDs.

### `POST /api/localities/risk-profiles`
Body: `{"locality_ids": ["KH_S01", "KH_S02", ...]}`
Returns a list of profiles. Unknown IDs produce `{"locality_id": "...", "error": "..."}` entries
(partial failure handling, no 4xx for the whole batch).

---

## Test Coverage (82 tests, 8 classes)

| Class | Tests |
|---|---|
| `TestDomainRiskScores` | to_dict, from_dict roundtrip |
| `TestDomainRiskWeights` | from_dict roundtrip |
| `TestRiskSourceSummary` | roundtrip |
| `TestLocalityRiskProfileSerialisation` | all keys, from_dict, drift_type |
| `TestComputeDomainWeights` | sum=1, zero scores, high-bio, scale_factors applied |
| `TestTopRiskDrivers` | all 4 domains, sorted descending |
| `TestConcentrationFlags` | high_biological, high_exposure, no flags |
| `TestBuilderStandardLocality` | profile created, all fields, all KH localities |
| `TestBuilderNoCages` | weighting_mode=none, multipliers=1, defaults listed |
| `TestBuilderWithCages` | cage_count, mode, source summary, multipliers |
| `TestConfidenceAndDefaults` | notes, source summary, KH_S02/S03 |
| `TestMultiLocalityBuild` | all 3 KH, subset, empty input |
| `TestLocalityRiskProfileAPI` | 200/404, structure, batch, partial failure, domain_weights=1 |
| `TestKHPortfolioValues` | known biomass, exposure, region, lat/lon, locality_no |

---

## Assumptions & Fallbacks

| Situation | Behaviour |
|---|---|
| No cage portfolio | `cage_weighting_mode="none"`, multipliers all 1.0, noted in `used_defaults` |
| All domain scores zero | `domain_weights` falls back to uniform 0.25 per domain |
| Unknown locality ID in batch | Returns `{"locality_id": ..., "error": ...}` entry (no 4xx for whole batch) |
| No BW credentials | `bw_live=False`, "BarentsWatch" not in `sources_used` |

---

## Definition of Done — All Met

- [x] Each KH locality produces a structured `LocalityRiskProfile`
- [x] Profile combines Live Risk + locality metadata + cage weighting where available
- [x] Missing data / defaults are explicit in `used_defaults`
- [x] Profile accessible through `GET /api/localities/{id}/risk-profile` and `POST /api/localities/risk-profiles`
- [x] 82 new tests pass, 0 existing tests broken (1940 total)
- [x] No existing module modified beyond `backend/main.py` router registration
