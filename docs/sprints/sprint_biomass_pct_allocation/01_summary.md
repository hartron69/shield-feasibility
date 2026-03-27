# Sprint: Biomass Percentage Allocation for Cage Portfolio

**Date:** 2026-03-27
**Status:** Complete
**Tests:** 1734 passed, 0 failed (no net change — UI-only and minor backend change)
**Build:** 0 errors, 105 modules

---

## Objective

Change cage biomass input from absolute tonnes to **percentage of the locality's total biomass**.
This eliminates double-counting, enforces a natural constraint (sum ≤ 100%), and makes
the cage breakdown immediately interpretable relative to the locality total already entered
at the site level.

---

## Problem Solved

Previously each cage held an independent `biomass_tonnes` field. Users had to mentally
calculate and track how individual cage tonnes related to the locality total, and there
was nothing preventing the cage sum from exceeding the site total.

---

## Design

### Data model
Each cage now stores `biomass_pct` (0–100) as the user-editable source of truth.
`biomass_tonnes` is always derived:

```
biomass_tonnes = (biomass_pct / 100) × site.biomass_tonnes
```

The backend continues to receive `biomass_tonnes` — the conversion is transparent to the API.

### Empty / fallow cages
Cages with 0% are explicitly allowed (empty merder, resting cycle). They appear in the
UI with a dimmed "Tom" label. The backend skips 0-tonne cages in `_build_cage_pen_configs()`
since `CagePenConfig` requires `biomass_tonnes > 0`.

### Site total changes
When the user changes `biomass_tonnes` at the site level in `SeaLocalityAllocationTable`,
all cage `biomass_tonnes` values are recomputed from their stored `biomass_pct`.

---

## Deliverables

### Modified files

| File | Change |
|---|---|
| `frontend/src/components/InputForm/CagePortfolioPanel.jsx` | % input replaces tonnes; `ControlSumBar`; "Fordel jevnt" button; `totalSiteBiomass` prop; "Tom" empty-cage label |
| `frontend/src/components/InputForm/SeaLocalityAllocationTable.jsx` | Passes `totalSiteBiomass` to panel; recomputes cage tonnes on site-biomass change |
| `backend/services/operator_builder.py` | `_build_cage_pen_configs()` skips cages with `biomass_tonnes ≤ 0` |
| `frontend/src/App.css` | `.cage-control-sum*` CSS classes |

---

## Control Sum Bar

```
Kontrollsum  80.0%   (20% ufordelt ≈ 600 t)
[████████░░░░░░░░░░░]  blue
```

| Condition | Bar colour | Message |
|---|---|---|
| sum = 100% ± 0.5% | Green | "Fullt fordelt ✓" |
| sum < 100% | Blue | "X% ufordelt ≈ Y t" |
| sum > 100% | Red | "⚠ Overskrider 100%!" |

---

## UX Details

- "Fordel jevnt" button distributes 100% equally across all cages
- Warning banner shown when `totalSiteBiomass` is 0 (not yet entered)
- Derived tonnes column shown read-only alongside the % input
- Cage rows with 0% are dimmed (opacity 0.6)
- `onChange` always emits `biomass_tonnes` in sync with pct × site total

---

## Non-Goals

- No change to backend schema — `biomass_pct` is a UI-only concept
- No change to risk weighting formula — all calculations still use `biomass_tonnes`
