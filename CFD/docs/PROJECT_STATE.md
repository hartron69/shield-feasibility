# CFD AquaGuard — Project State

Last updated: Sprint 9 (testing and validation complete).

---

## Architecture Overview

```
CFD/
├── core/
│   ├── geometry.py            # CoastlineGeometry, AquacultureNet, AquacultureSite
│   ├── flow_engine.py         # FlowModel — potential-flow velocity field
│   ├── pathogen_transport.py  # CoastalPathogenTimeMarcher — particle transport
│   ├── forcing.py             # CurrentForcing — time-varying current (Sprint 4)
│   ├── scenarios.py           # Scenario dataclass, site/net collections
│   ├── scenarios_io.py        # load_scenario(), save_scenario_template()
│   ├── risk_engine.py         # RiskEngine — deterministic GREEN/YELLOW/RED thresholds
│   ├── reporting.py           # Single-run report figures
│   ├── validation.py          # Geometry and scenario validation helpers
│   ├── io_utils.py            # General JSON/CSV helpers
│   ├── preview.py             # Quick matplotlib preview of scenario layout
│   ├── transfer_engine.py     # TransferResult, TransferLibrary, TransferEngine (Sprint 5)
│   ├── transfer_library.py    # TransferDistribution, MCTransferLibrary, EnsembleLibrary (Sprint 6)
│   ├── mc_risk_engine.py      # MCRiskResult, MonteCarloRiskEngine (Sprint 7)
│   └── mc_reporter.py         # MCReporter — 5-artefact output (Sprint 8)
├── scenarios/
│   └── example_fjord/         # Example two-site scenario (SA + SB)
│       ├── scenario.json
│       ├── forcing.json
│       └── currents.csv
├── tests/                     # pytest suite — 118 tests (Sprint 9)
│   ├── conftest.py
│   ├── test_forcing.py
│   ├── test_transfer_engine.py
│   ├── test_transfer_library.py
│   ├── test_mc_risk_engine.py
│   └── test_mc_reporter.py
├── docs/
│   └── sprints/               # Sprint summaries (Sprints 3–9)
├── main_v123.py               # CLI entry point + pipeline functions
├── pytest.ini
└── aquaguard_three_nets_pathogen_coast_status_v1.22b.py  # Legacy monolith (reference)
```

---

## Pipeline (end-to-end)

```
Scenario JSON  ──► load_scenario()
                        │
                        ▼
              TransferEngine.run_all_pairs()     [Sprint 5]
                        │ TransferLibrary
                        ▼
              EnsembleRunner.build()             [Sprint 6]
                        │ EnsembleLibrary
                        ▼
              EnsembleLibrary.to_mc_library()   [Sprint 6]
                        │ MCTransferLibrary
                        ▼
              MonteCarloRiskEngine.run_all()    [Sprint 7]
                        │ List[MCRiskResult]
                        ▼
              MCReporter.render_all()           [Sprint 8]
                        │
                        ▼
              5 output artefacts (4 PNG + 1 TXT)
```

---

## Key Invariants

1. **Transfer coefficient formula**: `TC = total_exposure_mass_seconds / total_shed_mass` [s]
2. **Peak mass fraction**: `PMF = peak_concentration × net_plan_area / total_shed_mass` [-]
3. **Zero-inflated lognormal**: cross-site pairs where some ensemble members show no
   transfer → `zero_fraction` field in `TransferDistribution`; `sample()` honours it
4. **Vectorised MC classifier**: no Python loop — pure NumPy; exactly one of
   {GREEN, YELLOW, RED} is True per sample
5. **`target_net_plan_area_m2`** stored in `TransferDistribution` — required for MC
   peak-concentration back-calculation in `MonteCarloRiskEngine`
6. **`auto_calibrate_from_first_case=False`** forced in `TransferEngine` — deterministic
7. **NaN ↔ None serialisation**: all `to_dict()` / `from_dict()` methods; used for
   `first_arrival_s` (no-arrival case) and lognormal parameters (single-nonzero case)

---

## Test Suite

| File | Tests | Covers |
|---|---|---|
| `test_forcing.py` | 18 | `CurrentForcing` (Sprint 4) |
| `test_transfer_engine.py` | 18 | `TransferResult`, `TransferLibrary`, `TransferEngine` (Sprint 5) |
| `test_transfer_library.py` | 30 | `TransferDistribution`, `MCTransferLibrary`, `EnsembleLibrary` (Sprint 6) |
| `test_mc_risk_engine.py` | 29 | `_classify_vectorised`, `MCRiskResult`, `MonteCarloRiskEngine` (Sprint 7) |
| `test_mc_reporter.py` | 23 | `MCReporter` figures + text (Sprint 8) |
| **Total** | **118** | **0 failed** |

Run fast subset: `pytest -m "not slow"` (114 tests, ~20 s)
Run full suite: `pytest` (118 tests, ~16 s)

---

## Output Files

All outputs written under `output/<scenario_name>/`:

| Subdirectory | File | Producer |
|---|---|---|
| `transfer/` | `transfer_results.csv`, `transfer_library.json` | Sprint 5 |
| `ensemble/` | `ensemble_results.csv`, `run_NNN/...` | Sprint 6 |
| `mc_library/` | `mc_transfer_library.json`, `mc_distribution_summary.csv` | Sprint 6 |
| `mc_risk/` | `mc_risk_results.csv`, `mc_risk_results.json` | Sprint 7 |
| `report/` | `mc_risk_heatmap.png`, `mc_transfer_heatmap.png`, `mc_pair_profiles.png`, `mc_management_summary.png`, `mc_text_summary.txt` | Sprint 8 |
