# Shield Risk Platform

**Aquaculture risk intelligence for the Norwegian salmon industry**

Shield Risk Platform is a decision-support tool for fish farming operators evaluating whether a Protected Cell Captive (PCC) insurance structure is financially viable. It combines stochastic loss modelling, biological risk intelligence (C5AI+), and an early warning alert engine into a single integrated platform — delivered through a React GUI and a FastAPI backend.

---

## What It Does

| Module | Purpose |
|---|---|
| **C5AI+ v5.0** | Biological risk forecasting — HAB, sea lice, jellyfish, pathogens |
| **Alert Engine** | Early warning signals from pattern detection and probability shift monitoring |
| **Monte Carlo Engine** | Compound Poisson-LogNormal simulation with cross-domain correlation (N=10 000, T=5 yr) |
| **PCC Feasibility** | 9-step pipeline: simulation → suitability scoring → strategy comparison → PDF board report |
| **Self-Learning Loop** | Bayesian and ML model retraining from observed outcomes |
| **React GUI** | 8-page interface: Overview, Inputs, C5AI+ Risk Intelligence, Alerts, PCC Feasibility, Strategy Comparison, Learning, Reports |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- `pip install -r requirements.txt`

### Backend
```bash
uvicorn backend.main:app --reload --port 8000
```

API available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### Frontend
```bash
cd frontend
npm install
npm run dev
```

GUI available at `http://localhost:5173`

### CLI (headless)
```bash
python main.py                                  # Demo: Nordic Aqua Partners AS
python main.py --input my_input.json -n 20000   # Custom operator, 20k simulations
```

---

## Repository Structure

```
shield-feasibility/
│
├── main.py                          # CLI entry point — 9-step PCC pipeline
├── config/settings.py               # Global constants and thresholds
├── data/
│   ├── input_schema.py              # OperatorInput, SiteProfile dataclasses
│   └── sample_input.json            # Nordic Aqua Partners AS (demo operator)
│
├── models/                          # Stochastic models
│   ├── monte_carlo.py               # Compound Poisson-LogNormal MC engine
│   ├── domain_correlation.py        # 4×4 cross-domain correlation matrix
│   ├── pcc_economics.py             # PCC captive economics + RI structure
│   └── strategies/                  # Full insurance, hybrid, PCC captive, pooling
│
├── analysis/
│   ├── suitability_engine.py        # 6-criterion suitability model
│   ├── mitigation.py                # 12 predefined mitigation actions
│   └── cost_analyzer.py             # TCOR and 5-year cost comparison
│
├── reporting/
│   ├── pdf_report.py                # 13-page board PDF (ReportLab)
│   └── chart_generator.py           # 10 matplotlib charts
│
├── c5ai_plus/                       # C5AI+ v5.0 — biological risk intelligence
│   ├── pipeline.py                  # 7-step forecasting orchestration
│   ├── forecasting/                 # HAB, lice, jellyfish, pathogen forecasters
│   ├── alerts/                      # Early warning alert engine (8 modules)
│   ├── learning/                    # Self-learning loop (predict → observe → retrain)
│   ├── models/                      # BetaBinomial, Random Forest, LogNormal severity
│   └── simulation/                  # Synthetic data generation for demos
│
├── backend/                         # FastAPI REST adapter
│   ├── main.py                      # App entry, CORS, static file mount
│   ├── schemas.py                   # Pydantic request/response models
│   ├── api/                         # Route handlers
│   └── services/                    # operator_builder, run_analysis, history_analytics
│
├── frontend/                        # React 18 + Vite 5 GUI (no charting library)
│   └── src/
│       ├── App.jsx                  # Root: 8-page nav, state, API wiring
│       ├── components/
│       │   ├── inputs/              # Inputs page — 5 tabs including SVG line charts
│       │   ├── alerts/              # Alert components (table, detail, badges)
│       │   ├── c5ai/                # C5AI+ Risk Intelligence module (5 tabs)
│       │   ├── results/             # PCC feasibility result panel (8 tabs)
│       │   └── InputForm/           # Feasibility accordion input form
│       └── data/                    # Mock data for demo mode
│
├── tests/                           # 1 092 tests, 0 failures
├── docs/                            # Architecture, sprint history, roadmap
├── examples/                        # Standalone demo scripts
└── PROJECT_STATE.md                 # Current system state (auto-maintained)
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/mitigation/library` | All 12 mitigation actions |
| `POST` | `/api/feasibility/run` | Full PCC feasibility analysis |
| `POST` | `/api/feasibility/example` | Pre-filled Nordic Aqua Partners example |

---

## Key Numbers (Nordic Aqua Partners AS — Demo)

| Metric | Value |
|---|---|
| TIV | NOK 886.9M |
| E[annual loss] | NOK 22.6M |
| VaR 99.5% | NOK 134.2M |
| PCC 5yr TCOR | NOK 64M |
| Full Insurance TCOR | NOK 97M |
| TCOR saving | ~34% |
| Test suite | 1 092 passed, 0 failed |
| Suitability verdict | POTENTIALLY SUITABLE |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, uvicorn |
| Simulation | NumPy, SciPy (vectorised, ~1s for N=10k) |
| PDF reports | ReportLab Platypus |
| Charts (backend) | Matplotlib, Seaborn |
| ML / Learning | Scikit-learn (Random Forest), Bayesian conjugate models |
| Frontend | React 18, Vite 5 |
| Charts (frontend) | Pure SVG — no charting library |
| API contract | Pydantic v2 |
| Tests | pytest (1 092 tests) |

---

## Documentation

- [`docs/architecture/SYSTEM_OVERVIEW.md`](docs/architecture/SYSTEM_OVERVIEW.md) — full architecture reference
- [`docs/architecture/ROADMAP.md`](docs/architecture/ROADMAP.md) — development roadmap
- [`docs/sprints/SPRINT_HISTORY.md`](docs/sprints/SPRINT_HISTORY.md) — sprint-by-sprint changelog
- [`PROJECT_STATE.md`](PROJECT_STATE.md) — current system state across all modules
- [`CLAUDE.md`](CLAUDE.md) — AI assistant conventions for this repository

---

## License

Proprietary. All rights reserved.
