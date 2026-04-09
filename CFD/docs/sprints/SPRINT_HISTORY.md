# CFD AquaGuard — Sprint History

Sprints are listed newest-first.

---

## Sprint 9 — Testing and Validation
**Status:** ✅ Complete
**Tests:** 118 passed, 0 failed
**Doc:** `sprint_testing/01_summary.md`

Full pytest suite for Sprints 4–8. Session-scoped fixtures, `@pytest.mark.slow` marker,
114 fast tests + 4 integration tests running actual particle simulations.

---

## Sprint 8 — Risk Reporting (MCReporter)
**Status:** ✅ Complete
**Doc:** `sprint_mc_reporter/01_summary.md`

5-artefact reporter: 4 PNG figures (risk heatmap, transfer heatmap, pair profiles,
management dashboard) + 1 UTF-8 text summary with Norwegian risk-band labels.

---

## Sprint 7 — MonteCarloRiskEngine
**Status:** ✅ Complete
**Doc:** `sprint_mc_risk_engine/01_summary.md`

Vectorised NumPy classifier over N samples. GREEN/YELLOW/RED probabilities, VaR
exposure percentiles, modal risk matrices. `run_all()` covers all N² site pairs.

---

## Sprint 6 — Precomputed MC-Ready Transfer Library
**Status:** ✅ Complete
**Doc:** `sprint_mc_library/01_summary.md`

Ensemble runner (N CFD realisations), zero-inflated lognormal distribution fitting,
`MCTransferLibrary` with O(1) lookup, JSON + CSV persistence.

---

## Sprint 5 — Physical Transfer Engine
**Status:** ✅ Complete
**Doc:** `sprint_transfer_engine/01_summary.md`

`TransferEngine` runs source→target particle simulations; computes TC, PMF, first
arrival. `TransferLibrary` saves/loads results; provides transfer and risk matrix pivots.

---

## Sprint 4 — CurrentForcing from CSV Time Series
**Status:** ✅ Complete
**Doc:** `sprint_current_forcing/01_summary.md`

Time-varying current forcing (Cartesian and polar CSV); linear interpolation;
`from_named_case` backward-compat; marcher updates speed + direction each timestep.

---

## Sprint 3 — Polyline Physics
**Status:** ✅ Complete
**Doc:** `sprint_polyline_physics/01_summary.md`

Polyline coastline geometry; realistic flow field along coastline; net polygon intersection.
