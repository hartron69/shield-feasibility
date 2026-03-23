# Sprint: Smolt Mitigation Composite Score Fix

## Objective

Fix a bug where selecting mitigation actions for a smolt/hatchery operator caused the
composite suitability score to worsen (negative delta) even when expected loss, P95,
P99, and SCR all improved significantly.

---

## Root Cause

`SuitabilityEngine.estimate_mitigated_score()` recomputed **Loss Stability** using the
aggregate simulated CV (`std / mean`) for all operator types. For smolt operators this is
wrong: the baseline `_score_loss_stability()` method uses the **per-event** CV
(`cv_loss_severity = 0.65`) because compound-Poisson zero-inflation massively inflates
the aggregate CV regardless of mitigation quality.

**Concrete example (λ = 0.32/yr, CV_sev = 0.65):**

| Metric | Value |
|---|---|
| Aggregate CV formula | √((1 + CV²) / λ) = √(1.4225 / 0.32) ≈ 2.11 |
| Baseline Loss Stability raw score | 65 (per-event CV = 0.65) |
| Mitigated Loss Stability raw score (bug) | 10 (aggregate CV ≈ 2.11) |
| Weighted penalty | −9.9 pts on 18% criterion |
| Net composite delta (bug) | −0.9 pts despite 30–50% loss reduction |

The aggregate CV does not change when mitigation reduces event frequency, because it is
dominated by the zero-inflation term `1/λ` (most years have zero claims).

---

## Fix

### 1. Loss Stability carry-forward for smolt (suitability_engine.py)

In `estimate_mitigated_score()`, added an `is_smolt` branch that copies the baseline
`Loss Stability` criterion forward unchanged, with an explanatory finding string:

```python
if is_smolt:
    new_criteria.append(CriterionScore(
        c.name, c.weight, c.raw_score, c.weighted_score,
        f"CV={cv_label:.2f} (per hendelse, uendret av tiltak)",
        c.rationale,
    ))
```

Sea operators continue to use proportional aggregate CV scaling.

### 2. Bounded readiness uplifts for smolt operational actions (suitability_engine.py)

Added `_SMOLT_READINESS_UPLIFTS` class-level dict mapping smolt action IDs to bounded
raw score improvements on Operational Readiness and Bio Readiness:

| Action | Criterion | Max uplift |
|---|---|---|
| `smolt_staff_training` | Operational Readiness | +8 pts |
| `smolt_emergency_plan` | Operational Readiness | +5 pts |
| `smolt_emergency_plan` | Biologisk Operasjonell Beredskap | +5 pts |
| `smolt_alarm_system` | Biologisk Operasjonell Beredskap | +5 pts |

Uplifts are additive, bounded at 100, and only applied when the action is present in
`selected_action_ids`. Sea actions (`stronger_nets`, `ai_early_warning`, etc.) are not
in the map and have no effect on smolt criteria.

### 3. 3-tuple return value

`estimate_mitigated_score()` now returns `(composite: float, verdict: str, criteria: List[CriterionScore])`.
Both sea and smolt paths in `run_analysis.py` were updated to unpack all three values and
pass the actual mitigated criteria to the `ScenarioBlock.criterion_scores` field.

### 4. Backend schema extension (schemas.py)

`ComparisonBlock` gained three fields:
- `composite_score_delta: float = 0.0`
- `criterion_deltas: List[Dict]` — per-criterion baseline/mitigated raw scores and weighted delta
- `mitigation_score_note: str = ""` — plain-language explanation for any score change

### 5. Frontend updates

**MitigationTab.jsx** now shows:
- `mitigation_score_note` banner (blue info box) when present
- "Kriterievis score-endring" table with baseline raw / mitigated raw / weighted delta per criterion

**RecommendationTab.jsx** already showed:
- Mitigated verdict callout with `scoreDelta` and "Verdict oppgradert" badge
- Dual score bars (baseline teal / mitigated green)

---

## Files Changed

| File | Change |
|---|---|
| `analysis/suitability_engine.py` | `_SMOLT_READINESS_UPLIFTS`, smolt Loss Stability carry-forward, 3-tuple return |
| `backend/schemas.py` | `ComparisonBlock` + 3 new fields |
| `backend/services/run_analysis.py` | Both sea/smolt paths: 3-tuple unpack, criterion_deltas, note building |
| `frontend/src/components/results/MitigationTab.jsx` | Note banner + criterion delta table |
| `tests/test_smolt_mitigation_score.py` | New — 22 tests |

---

## Test Results

```
1435 passed, 45 warnings   (+22 new tests vs 1413 before sprint)
```

New test file: `tests/test_smolt_mitigation_score.py` (22 tests, 5 groups)

| Group | Coverage |
|---|---|
| `TestSmoltLossStabilityCarryForward` | Loss Stability unchanged; composite not worse; 3-tuple return |
| `TestSmoltReadinessUplifts` | Per-action uplift values; stacking; sea-action non-interference |
| `TestSeaCaseLossStability` | Sea aggregate CV scaling; smolt uplift isolation |
| `TestVerdictThresholds` | Verdict bands respected |
| `TestCriterionDeltaSigns` | Balance Sheet improves with SCR drop; finding text |

---

## Build Status

```
npm run build: ✓ 95 modules, 0 errors
```

---

## Behaviour Before / After

| Case | Before | After |
|---|---|---|
| Smolt, 30% loss reduction, `smolt_staff_training` | Composite −0.9 pts (spurious) | Composite ≥ baseline + readiness uplift |
| Smolt, 50% loss reduction, no actions | Composite −13 pts (Loss Stability collapsed) | Composite ≥ baseline |
| Sea, 50% loss reduction | Composite improves (correct) | Unchanged — sea path unaffected |
| `criterion_deltas` in API response | Empty list | Per-criterion before/after with delta |
| `mitigation_score_note` in API response | Empty string | Explanation of score change |
