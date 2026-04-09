# Sprint 9 — Testing and Validation

## Objective
Build a full pytest suite covering all core modules introduced in Sprints 4–8, with
session-scoped fixtures to minimise I/O and a `slow` marker to deselect integration tests
that run full particle simulations.

## Deliverables

### pytest.ini (new)
```ini
[pytest]
testpaths = tests
addopts = -q --tb=short
markers =
    slow: marks tests that run a full particle simulation (deselect with -m "not slow")
```

### tests/conftest.py (new)
Session-scoped fixtures (built once per test run):
- `straight_coast` — `CoastlineGeometry` with two straight segments
- `net_a`, `net_b` — `AquacultureNet` objects (plan area ~2827 m²)
- `site_a`, `site_b` — `AquacultureSite` with two nets each
- `minimal_scenario` — `Scenario` with SA + SB, 500 m spacing
- `minimal_flow_model` — `FlowModel` built from `minimal_scenario`
- `simple_mc_library` — `MCTransferLibrary` with 4 pairs × 3 metrics = 12 distributions:
  - SA→SA, SB→SB: lognormal TC ~100–120 s (self-transfer)
  - SA→SB, SB→SA: zero TC (no cross-site transfer)

Function-scoped factories:
- `make_transfer_result(**kwargs)` — `TransferResult` with sensible defaults
- `two_result_library` — `TransferLibrary` with SA→SA (RED) + SA→SB (GREEN)
- `make_mc_result(**kwargs)` — `MCRiskResult` with default all-GREEN probabilities
- `four_mc_results` — list of 4 `MCRiskResult` objects (2 RED self-pairs, 2 GREEN cross-pairs)

### Test Files

| File | Tests | Scope |
|---|---|---|
| `test_forcing.py` | 18 | Construction, interpolation, stats, CSV round-trip (A+B) |
| `test_transfer_engine.py` | 18 | 14 unit + 4 `@slow` integration (full particle sim) |
| `test_transfer_library.py` | 30 | Fit, sampling, serialisation, MCTransferLibrary, EnsembleLibrary |
| `test_mc_risk_engine.py` | 29 | Classifier conditions, MCRiskResult, MonteCarloRiskEngine |
| `test_mc_reporter.py` | 23 | File creation, PNG validation, text content |
| **Total** | **118** | **0 failed** |

## Test Results
```
platform win32 -- Python 3.14.3, pytest-9.0.2
collected 118 items

tests/test_forcing.py ..................              [15%]
tests/test_mc_reporter.py .......................    [34%]
tests/test_mc_risk_engine.py .......................  [59%]
tests/test_transfer_engine.py ..................     [74%]
tests/test_transfer_library.py ..............................  [100%]

==================== 118 passed in 15.90s ====================
```

Fast subset (excluding slow integration tests): `pytest -m "not slow"` → 114 passed in ~20s.

## Key Test Patterns

**PNG magic bytes validation**:
```python
PNG_MAGIC = b'\x89PNG'
assert paths[key].read_bytes()[:4] == PNG_MAGIC
```

**Zero-inflated fraction tolerance**:
```python
observed_zero = (s == 0.0).mean()
assert 0.35 < observed_zero < 0.45  # ±0.05 band around 0.4
```

**Vectorised classifier — all samples sum to 1**:
```python
total = g.astype(int) + y.astype(int) + r.astype(int)
assert np.all(total == 1)
```

**Threshold boundary fix (not a code bug)**:
- `red_arrival_threshold_s = 600` → 300 s is RED ✓
- `yellow_arrival_threshold_s = 1200` → 700 s is YELLOW (not GREEN) ✓; 1300 s is GREEN ✓

## Build Status
- No new runtime dependencies
- `tests/__init__.py` present for package import resolution
- All 118 tests deterministic (fixed seeds throughout)
