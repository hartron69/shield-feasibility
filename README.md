# Shield Risk Platform

**Aquaculture risk intelligence for the Norwegian salmon industry**

Shield Risk Platform is a decision-support tool for fish farming operators evaluating whether a
Protected Cell Captive (PCC) insurance structure is financially viable. It combines stochastic
loss modelling, biological risk intelligence (C5AI+), a cage portfolio risk model, and an early
warning alert engine into a single integrated platform — delivered through a React GUI and a
FastAPI backend.

---

## What It Does

| Module | Purpose |
|---|---|
| **C5AI+ v5.0** | Multi-domain risk forecasting — biological (HAB, lice, jellyfish, pathogens), structural, environmental, operational |
| **Alert Engine** | Early warning signals from pattern detection and probability-shift monitoring |
| **Cage Portfolio Model** | Per-locality cage technology risk profiling — `open_net`, `semi_closed`, `fully_closed`, `submerged` — with advanced 5-component weighting |
| **Monte Carlo Engine** | Compound Poisson-LogNormal simulation with cross-domain correlation (N=10 000, T=5 yr) |
| **PCC Feasibility** | 9-step pipeline: simulation → suitability scoring → strategy comparison → PDF board report |
| **Self-Learning Loop** | Bayesian and ML model retraining from observed outcomes |
| **React GUI** | 9-page interface: Overview, Inputs, C5AI+ Risk Intelligence, Alerts, PCC Feasibility, Strategy Comparison, Learning, Reports — plus cage portfolio panel |

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
├── config/
│   ├── settings.py                  # Global constants and thresholds
│   └── cage_weighting.py            # Advanced cage weighting constants
├── data/
│   ├── input_schema.py              # OperatorInput, SiteProfile dataclasses
│   └── sample_input.json            # Nordic Aqua Partners AS (demo operator)
│
├── models/                          # Stochastic and risk models
│   ├── monte_carlo.py               # Compound Poisson-LogNormal MC engine
│   ├── domain_correlation.py        # 4×4 cross-domain correlation matrix
│   ├── cage_technology.py           # CagePenConfig, CAGE_DOMAIN_MULTIPLIERS
│   ├── cage_weighting.py            # 5-component advanced weighting engine
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
│   └── chart_generator.py           # 10+ matplotlib charts
│
├── c5ai_plus/                       # C5AI+ v5.0 — multi-domain risk intelligence
│   ├── pipeline.py                  # 7-step forecasting orchestration
│   ├── forecasting/                 # Biological: HAB, lice, jellyfish, pathogen
│   ├── structural/                  # Structural domain forecasting
│   ├── environmental/               # Environmental domain forecasting
│   ├── operational/                 # Operational domain forecasting
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
│       ├── App.jsx                  # Root: 9-page nav, state, API wiring
│       ├── components/
│       │   ├── InputForm/           # Feasibility accordion — includes CagePortfolioPanel
│       │   ├── results/             # PCC result panel (8 tabs + Merd-profil)
│       │   ├── inputs/              # Inputs page — 5 tabs, SVG line charts
│       │   ├── alerts/              # Alert components (table, detail, badges)
│       │   └── c5ai/                # C5AI+ Risk Intelligence module (7 tabs)
│       └── data/                    # Mock data — Kornstad Havbruk AS localities
│
├── tests/                           # 1 734 tests, 0 failures
├── docs/                            # Architecture, sprint history, roadmap
├── examples/                        # Standalone demo scripts
├── CHANGELOG.md                     # Version history
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
| `GET` | `/api/inputs/audit` | Input data audit report (JSON) |

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
| Test suite | **1 734 passed, 0 failed** |
| Suitability verdict | POTENTIALLY SUITABLE |

---

## Cage Portfolio Model

A locality (sjølokalitet) is modelled as a **portfolio of net-pen cages** (merder), each with
a technology type and its own domain risk multiplier profile:

| Type | Biological | Structural | Environmental | Operational |
|---|---|---|---|---|
| `open_net` | 1.00× | 1.00× | 1.00× | 1.00× |
| `semi_closed` | 0.75× | 0.95× | 0.80× | 1.10× |
| `fully_closed` | 0.45× | 1.20× | 0.60× | 1.25× |
| `submerged` | 0.70× | 1.15× | 0.55× | 1.15× |

The **advanced weighting engine** (`models/cage_weighting.py`) computes locality multipliers
from five per-cage components: biomass share, economic value, consequence severity,
operational complexity, and structural criticality (with SPOF/redundancy modifiers).

Cage biomass is entered as **% of the locality total** — a control-sum bar enforces ≤ 100%.
Empty/fallow cages (0%) are allowed and excluded from risk calculations.

---

## Real Localities (Kornstad Havbruk AS)

All Risk Intelligence mock data uses actual BW-registered localities:

| ID | Name | BW No. | Exposure |
|---|---|---|---|
| `KH_S01` | Kornstad | 12855 | 1.15 — semi-exposed |
| `KH_S02` | Leite | 12870 | 1.10 — semi-exposed |
| `KH_S03` | Hogsnes | 12871 | 0.85 — sheltered |

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
| Tests | pytest (1 734 tests) |

---

## Documentation

- [`CHANGELOG.md`](CHANGELOG.md) — version history with all sprint changes
- [`PROJECT_STATE.md`](PROJECT_STATE.md) — current system state across all modules
- [`docs/architecture/SYSTEM_OVERVIEW.md`](docs/architecture/SYSTEM_OVERVIEW.md) — full architecture reference
- [`docs/architecture/ROADMAP.md`](docs/architecture/ROADMAP.md) — development roadmap
- [`docs/sprints/SPRINT_HISTORY.md`](docs/sprints/SPRINT_HISTORY.md) — sprint-by-sprint detail log
- [`CLAUDE.md`](CLAUDE.md) — AI assistant conventions for this repository

---

## License

Proprietary. All rights reserved.
