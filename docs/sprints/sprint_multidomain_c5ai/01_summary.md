# Sprint – Multi-Domain C5AI+ Extension

**Date:** 2026-03-10
**Status:** COMPLETE

---

## Objective

Extend C5AI+ from biological-only forecasting to cover all four risk domains
(biological, structural, environmental, operational) with the same explainable,
prior-based, feasibility-grade architecture — updating both backend and GUI
without breaking any existing functionality.

---

## Deliverables

### Backend (Python)

| File | Description |
|---|---|
| `c5ai_plus/config/c5ai_settings.py` | +52 new constants: priors, loss fractions, CVs for 15 new risk types + 3 domain loss fractions |
| `c5ai_plus/alerts/alert_models.py` | `domain: str = ''` field on `AlertRecord`; `RISK_TYPE_DOMAIN` dict (19 risk types) |
| `c5ai_plus/alerts/alert_rules.py` | `STRUCTURAL_RULES`, `ENVIRONMENTAL_RULES`, `OPERATIONAL_RULES` (5 each); `ALL_RULES` extended to 19 keys |
| `c5ai_plus/alerts/alert_explainer.py` | `RECOMMENDED_ACTIONS` for all 15 new risk types (5 actions each) |
| `c5ai_plus/alerts/alert_engine.py` | `domain` field auto-populated; `_RISK_TYPE_PRIORS` extended to all 19 types |
| `c5ai_plus/alerts/pattern_detector.py` | `_evaluate_rule()` extended with 15 new rule proxy mappings |
| `c5ai_plus/alerts/alert_simulator.py` | 8 new simulate_*() methods; `simulate_all()` → 18 records |
| `c5ai_plus/structural/` | New package: inputs, simulator, forecaster, rules, `__init__` |
| `c5ai_plus/environmental/` | New package: inputs, simulator, forecaster, rules, `__init__` |
| `c5ai_plus/operational/` | New package: inputs, simulator, forecaster, rules, `__init__` |
| `c5ai_plus/multi_domain_engine.py` | `MultiDomainEngine`, `MultiDomainForecast`, `DomainForecastResult` |
| `tests/test_multidomain_c5ai.py` | 63 new tests |
| `tests/test_alert_layer.py` | 3 test assertions updated for expanded rule registry |

### Frontend (React)

| File | Description |
|---|---|
| `frontend/src/data/mockMultiDomainData.js` | New: structural/environmental/operational mock inputs for 3 sites |
| `frontend/src/data/c5ai_mock.js` | Extended: `structural_forecast`, `environmental_forecast`, `operational_forecast` keys |
| `frontend/src/data/mockAlertsData.js` | Extended: 8 new alerts (2 structural, 3 environmental, 3 operational) → 18 total |
| `frontend/src/components/inputs/StructuralInputsPanel.jsx` | New: structural condition table |
| `frontend/src/components/inputs/EnvironmentalInputsPanel.jsx` | New: environmental readings table |
| `frontend/src/components/inputs/OperationalInputsPanel.jsx` | New: operational indicators table |
| `frontend/src/components/inputs/InputsPage.jsx` | Extended: 5 tabs → 8 tabs |
| `frontend/src/components/c5ai/StructuralForecastTab.jsx` | New: risk card grid for structural subtypes |
| `frontend/src/components/c5ai/EnvironmentalForecastTab.jsx` | New: risk card grid for environmental subtypes |
| `frontend/src/components/c5ai/OperationalForecastTab.jsx` | New: risk card grid for operational subtypes |
| `frontend/src/components/c5ai/C5AIModule.jsx` | Extended: 5 tabs → 7 tabs; 'forecast' renamed to 'biological'; 'drivers' dropped |
| `frontend/src/components/alerts/AlertsPage.jsx` | Extended: domain filter row added |
| `frontend/src/components/alerts/AlertDetailPanel.jsx` | Extended: domain badge in header |
| `frontend/src/components/OverviewPage.jsx` | Extended: top-alert-per-domain summary section |
| `frontend/src/App.css` | ~140 lines appended: domain-forecast-grid, domain-badge, threshold-badge, delta classes |

---

## Test Results

```
pytest tests/ -q
1155 passed, 38 warnings in ~34s   (was 1092 + 63 new)
```

New test file: `tests/test_multidomain_c5ai.py` — **63 tests** across 8 classes.

---

## Build Status

```
cd frontend && npm run build
82 modules transformed, 0 errors
```

---

## Architecture Notes

- Biological pipeline unchanged internally — `MultiDomainEngine` wraps it externally
- Score-based probability model (no ML in Sprint 1); consistent with biological prior-based approach
- `RISK_TYPE_DOMAIN` (19 entries) is the single source of truth for domain classification
- `AlertRecord.domain = ''` default preserves full backward compatibility
- All 3 new domain packages follow identical pattern: inputs / simulator / forecaster / rules / `__init__`
