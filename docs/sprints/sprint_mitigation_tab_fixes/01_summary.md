# Sprint: Mitigation Tab Fixes & CV Transparency (2026-03-27)

## Objective

Fix two bugs in the Mitigation results tab and improve transparency of why the
composite score delta may be 0 even when expected loss is significantly reduced.

## Bugs fixed

### Bug 1 — NaN % in Vekt column (criterion weights)

**Root cause:** `crit_deltas` dicts in `run_analysis.py` were built from the
mitigated criterion scores (`mc`) but never copied the `weight` key. The frontend
computed `d.weight * 100` → `NaN`.

**Fix:** Added `"weight": mc.get("weight", 0)` to the `crit_deltas.append(...)` call
in both code paths (smolt ~line 373, sea ~line 790) using `replace_all=True` since
both blocks were identical.

**Result:** Weights now display correctly, e.g. "Tap-stabilitet 22.5 %".

### Bug 2 — Misleading "Score improves by +0.0 pts" note

**Root cause:** When `score_delta == 0.0` and no criteria moved between scoring bands,
the original English code path still generated "Score improves by +0.0 pts."

**Fix:** Added guard `abs(score_delta) < 0.05 and not improved and not worsened`
that emits an informative Norwegian message:
> "Tiltakene krysser ingen kriterieterskler — poengsummen er uendret. Risikogevinsten
> er synlig i forventet tapsdelta og SCR-endring ovenfor."

Also translated the English sea-path narrative to Norwegian to match smolt-path format.

## Improvement — CV transparency in Loss Stability finding

### Background

`SuitabilityEngine.estimate_mitigated_score()` recomputes only two criteria when
mitigations are applied: Loss Stability and Balance Sheet Strength. The 0.0 pts delta
in the composite score is mathematically correct when no threshold is crossed —
e.g. base CV 0.92 → mitigated CV 0.78 stays within band [0.75, 1.00) → raw score
stays at 30 → delta = 0.

### Change to finding text (`analysis/suitability_engine.py`)

Before: `"CV≈{mit_cv:.2f} (mitigated estimate)"`

After: `"CV: {base_cv:.2f} → {mit_cv:.2f} (terskel <0.75 for neste band)"`

The note adapts to the actual threshold proximity:
- CV < 0.30 → "øverste band nådd"
- CV in [0.30, 0.50) → "terskel <0.30 for neste band"
- CV in [0.50, 0.75) → "terskel <0.50 for neste band"
- CV in [0.75, 1.00) → "terskel <0.75 for neste band"
- CV ≥ 1.00 → "høy volatilitet"

Balance Sheet finding also translated to Norwegian:
`"SCR {capital_to_equity:.1%} av egenkapital (etter tiltak)"`

### Change to criterion table (`MitigationTab.jsx`)

The `finding` field was already included in `crit_deltas` but never displayed.
The criterion name cell now renders the finding as an italic subtitle below the name:

```
Tap-stabilitet
CV: 0.92 → 0.78 (terskel <0.75 for neste band)   ← italic, grey
```

## Test results

- Backend: 1858 passed, 0 failed
- Frontend: 109 modules, 0 errors

## Build status

```
✓ built in 1.15s  (109 modules, 0 errors)
```

## Files changed

| File | Change |
|---|---|
| `backend/services/run_analysis.py` | Add `"weight"` key to crit_deltas (both paths); fix 0.0 pts note (Norwegian); translate sea-path narrative |
| `analysis/suitability_engine.py` | Improve Loss Stability finding (CV transition + threshold note); translate Balance Sheet finding |
| `frontend/src/components/results/MitigationTab.jsx` | Show `finding` as italic subtitle in criterion name cell; add `null` guard for weight |
