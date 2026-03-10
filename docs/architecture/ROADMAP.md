# Shield Risk Platform — Development Roadmap

**Last updated:** 2026-03-10

This roadmap describes the development arc of Shield Risk Platform from its current feasibility-grade state toward a production-ready aquaculture risk intelligence product. Items are grouped by theme, not strict timeline, as priorities may shift with partner feedback.

---

## Current State (Baseline)

The platform is **feasibility-grade** — complete enough to demonstrate the full value proposition to partners and operators, but not yet production-hardened.

| Capability | Status |
|---|---|
| Monte Carlo simulation (N=10k, 5yr) | Complete |
| 4-risk-type C5AI+ forecasting | Complete |
| 6-criterion suitability engine | Complete |
| PCC captive economics (RI, SCR, TCOR) | Complete (bugs fixed Sprint 8b) |
| 12-action mitigation library | Complete |
| 13-page board PDF report | Complete |
| Cross-domain correlation model | Complete (Sprint 7) |
| Early warning alert engine | Complete (Sprint – Alert Layer) |
| Self-learning Bayesian/ML loop | Complete (Sprint 9) |
| React GUI — 8 pages | Complete |
| Biological time-series charts | Complete |
| Scenario override (client-side stub) | Partial — backend not yet wired |
| Historical loss calibration | Complete (basic; domain-level in progress) |
| Multi-user / auth | Not started |
| Real data integration | Not started |

---

## Near-Term (Next 2–4 Sprints)

### 1. Scenario Engine — Backend Wiring
**Priority: High**

The Scenario Inputs tab in the GUI is UI-complete but runs a client-side approximation.
Wiring to a proper backend route will make scenario outputs trustworthy for operator conversations.

- Implement `POST /api/c5ai/scenario` — accepts parameter overrides, reruns Monte Carlo with modified inputs
- Connect `ScenarioOverridePanel.jsx` to live endpoint
- Return scale factor, updated loss distribution, KPI delta vs. baseline
- Add 15–20 tests for the new route and service

**Files affected:** `backend/api/`, `backend/services/`, `ScenarioOverridePanel.jsx`

---

### 2. Real Data Ingestion
**Priority: High**

Replace mock data with a structured ingestion pipeline for real operator data.

- Define canonical input formats (CSV, Excel, JSON) for biological readings
- Build `ingestion/operator_data_loader.py` with validation and cleaning
- Extend `DataLoader` to accept file uploads via `POST /api/inputs/upload`
- Map external data fields to `C5AIOperatorInput` and `MOCK_SITE_PROFILES` schema
- Add data completeness scoring that feeds into `InputCompletenessCard`

---

### 3. Alert Engine — Live Wiring
**Priority: Medium**

The GUI currently displays `MOCK_ALERTS`. The backend `AlertEngine` is fully implemented but not connected to the API.

- Add `GET /api/alerts/{operator_id}` — runs `AlertEngine.generate_alerts()` from stored forecasts
- Add `PATCH /api/alerts/{alert_id}/status` — workflow status updates (OPEN → ACKNOWLEDGED → IN_PROGRESS → CLOSED)
- Wire `AlertsPage` and `C5AIModule Alerts` tab to live endpoint
- Persist alert history in `AlertStore`

---

### 4. Historical Loss Calibration — Domain-Level
**Priority: Medium**

`use_history_calibration=True` currently calibrates at portfolio level. Domain-level calibration would improve accuracy for operators with multi-year loss records.

- Extend `HistoricalLossSummary` with per-domain severity and frequency statistics
- Pass domain-level parameters into `MonteCarloEngine` per domain weight
- Update `AllocationSummary.calibration_mode` to distinguish `"domain"` from `"portfolio"`
- Add 20–30 tests

---

## Medium-Term (4–8 Sprints)

### 5. Authentication and Multi-Tenancy
**Priority: High for production**

- JWT-based authentication (FastAPI + python-jose)
- Operator-scoped data isolation — each operator sees only their own data, alerts, learning history
- Role-based access: `operator`, `risk_manager`, `board`, `admin`
- Secure PDF report storage (operator-scoped S3 or equivalent)

---

### 6. Persistent Operator Profiles
**Priority: High for production**

Currently every `/run` call starts from scratch. Operators need saved profiles.

- Database backend (PostgreSQL via SQLAlchemy or SQLModel)
- `POST /api/operators` — create/update operator profile
- `GET /api/operators/{id}/history` — full run history with KPI trends
- GUI: save/load profile, run history timeline
- Learning loop reads from persistent event store (not local JSON)

---

### 7. C5AI+ Real Forecaster Models
**Priority: High**

Current forecasters use rule-based logic with biological priors. Replace with calibrated models trained on Norwegian aquaculture data.

- Integrate Norwegian Meteorological Institute (MET) sea temperature and current data APIs
- Integrate Barentswatch lice count API (public)
- Train HAB model on historical Folkehelseinstituttet algae bloom data
- Upgrade `SklearnProbabilityModel` to gradient boosting (XGBoost/LightGBM)
- Model versioning via existing `ModelRegistry`

---

### 8. Regulatory and Reporting Integration
**Priority: Medium**

Norwegian aquaculture operators face Mattilsynet and Fiskeridirektoratet reporting obligations.

- Map platform risk outputs to regulatory reporting formats
- Export alert history as CSV / Excel for Mattilsynet submissions
- Add Solvency II SCR narrative to PDF report (already partially implemented)
- Timestamp and audit trail for all run outputs

---

### 9. Portfolio View — Multi-Operator
**Priority: Medium for insurer/broker users**

Partners (brokers, insurers) need to see risk across multiple operators simultaneously.

- `GET /api/portfolio/summary` — aggregate KPIs across all operators in a portfolio
- Portfolio-level correlation model (`RiskCorrelationMatrix` across operators)
- Portfolio heat map in GUI: risk by site, by region, by risk type
- Pooling calculator: show diversification benefit of grouping operators into a mutual pool

---

### 10. PCC Cell Structure — Legal and Capital Module
**Priority: Medium for pilot**

Move from economics modelling to operational PCC readiness.

- Cell Articles of Association template generator
- Minimum capital requirement calculator (Solvency II SCR + Bermuda/Guernsey regimes)
- Fronting carrier requirements checklist
- Board resolution template

---

## Longer-Term

### 11. Real-Time Monitoring Integration
- WebSocket or SSE push from backend to GUI for live alert updates
- Integration with in-cage sensor APIs (oxygen, temperature, feeding)
- Automated daily `LearningLoop.run_cycle()` job

### 12. API Productisation
- Public REST API with API keys and rate limiting
- OpenAPI spec published as partner integration guide
- Webhook support for alert delivery (email, Slack, SMS)

### 13. Machine Learning Enhancements
- Ensemble forecasters: combine rule-based, Bayesian, and ML predictions
- Causal inference module (`c5ai_plus/causal/cate_module.py`) — estimate treatment effect of mitigation interventions
- Uncertainty quantification: prediction intervals on all forecast outputs
- Anomaly detection on biological time series (complement to rule-based alert engine)

### 14. Mobile and Offline Support
- Progressive Web App (PWA) for field use at remote sites
- Offline-capable biological readings entry
- Sync when connectivity restored

---

## Technical Debt

| Item | Priority | Notes |
|---|---|---|
| Learning store: local JSON → database | High | Blocks multi-user |
| Alert engine not wired to GUI | High | Currently MOCK_ALERTS only |
| `/api/c5ai/scenario` not implemented | High | Client-side stub only |
| `networkx` optional — network model disabled by default | Medium | Install and enable for production |
| `deformation_monitoring` targeted risk types mismatch | Low | Non-fatal warning; targeted types not in bio domain map |
| Frontend has no test suite | Medium | Add Vitest / React Testing Library |
| No CI/CD pipeline | Medium | Add GitHub Actions for pytest + npm build on push |
| PDF generation is synchronous (blocking) | Low | Move to background job + websocket notification |

---

## Partner and Pilot Milestones

| Milestone | Description |
|---|---|
| **Demo-ready** | Current state — full GUI, mock data, PDF report |
| **Pilot-ready** | Real data ingestion + live alerts + auth + persistent profiles |
| **Operator production** | Regulatory integration + real forecaster models + mobile |
| **Insurer/broker production** | Portfolio view + API productisation + multi-tenancy |
