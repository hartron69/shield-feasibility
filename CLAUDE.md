# CLAUDE.md — AI Assistant Conventions

This file provides working conventions for AI assistants (Claude Code and similar tools)
operating on the Shield Risk Platform repository.

---

## Project Identity

**Shield Risk Platform** is an aquaculture risk intelligence and PCC feasibility tool for
Norwegian salmon farming operators. The platform integrates:
- Biological risk forecasting (C5AI+ v5.0)
- Early warning alert engine
- Stochastic loss simulation (Monte Carlo)
- PCC captive insurance feasibility analysis
- Self-learning Bayesian and ML models
- React 18 + FastAPI GUI

Working directory: `C:/Users/haral/dev/shield-feasibility/`

---

## Language and Tone

- **Code comments and docstrings:** English
- **User-facing UI text and labels:** Norwegian (Bokmål)
- **Documentation files (docs/, README, CLAUDE.md):** English
- **Sprint docs:** English unless the user instructs otherwise

---

## Technology Constraints

### Python
- Python 3.11+
- Do not add new top-level dependencies without checking `requirements.txt` first
- NumPy is vectorised — avoid per-simulation Python loops in Monte Carlo code
- All new dataclasses must implement `to_dict()` / `from_dict()` for JSON serialisation

### Frontend
- React 18 + Vite 5
- **No new npm packages** without explicit user approval — check `frontend/package.json` first
- Charts are pure SVG (no recharts, chart.js, d3, or similar)
- CSS is written in `frontend/src/App.css` — append new sections at end
- When appending CSS with special characters (°, µ, backticks), use a Python script rather than bash heredoc to avoid encoding issues

### Testing
- Test framework: pytest
- Current count: **1 092 passed, 0 failed**
- All new backend modules require corresponding tests
- Do not break existing tests

---

## Architecture Invariants

These must not change without explicit user instruction:

1. **PCC pipeline is 9 steps** — do not reorder or merge steps in `main.py`
2. **C5AI+ pipeline is 7 steps** — `c5ai_plus/pipeline.py`
3. **Alert level mapping is transparent and documented** — see `alert_engine.py`
4. **Biomass valuation formula:** `ref_price_per_kg × 1000 × realisation × (1 − haircut)`
5. **Monte Carlo:** vectorised NumPy, compound Poisson-LogNormal, N×5 simulation matrix
6. **Domain correlation:** additive Gaussian perturbation on simplex — do not switch to multiplicative
7. **SCR = VaR(99.5%) of net retained loss distribution** — bounded at retention (post Sprint 8b fix)
8. **FEASIBILITY_PAGES = {'feasibility', 'strategy'}** — only these pages show the left accordion panel

---

## File Naming Conventions

| Type | Convention | Example |
|---|---|---|
| Python modules | `snake_case.py` | `alert_engine.py` |
| React components | `PascalCase.jsx` | `BioLineChart.jsx` |
| Data files | `camelCase.js` | `mockBioTimeseries.js` |
| Mock data exports | `SCREAMING_SNAKE_CASE` | `MOCK_ALERTS` |
| Sprint docs | `NN_topic.md` in sprint folder | `01_summary.md` |

---

## Git Conventions

- **Never auto-commit** — only commit when the user explicitly asks
- **Never amend** published commits — always create new commits
- **Commit message style:** imperative subject line, bullet body if needed, `Co-Authored-By` trailer
- **Branch:** `master` (single branch — no feature branch workflow currently)
- **Never force-push to master**

---

## Mock Data Sites

Three demo sites used consistently across all mock data:

| ID | Name | Exposure |
|---|---|---|
| `DEMO_OP_S01` | Frohavet North | 1.40 — open coast, highest risk |
| `DEMO_OP_S02` | Sunndalsfjord | 1.10 — semi-exposed |
| `DEMO_OP_S03` | Storfjorden South | 0.85 — sheltered, lowest risk |

These site IDs are referenced in: `mockInputsData.js`, `mockAlertsData.js`, `mockBioTimeseries.js`, `c5ai_mock.js`, and `alert_simulator.py`. Keep them consistent.

---

## Sprint Documentation

Every sprint that changes code must produce:
1. Sprint folder: `docs/sprints/sprint_<topic>/`
2. `01_summary.md` at minimum (objective, deliverables, test results, build status)
3. Entry in `docs/sprints/SPRINT_HISTORY.md` at the top of the sprint list
4. `PROJECT_STATE.md` updated if architecture changes

---

## Known Tricky Areas

| Area | Note |
|---|---|
| `from_dict` abbreviation parsing | Must try all `_` split positions — not just first — for keys like `env_struct` |
| `equicorrelation(0.999)` | IS positive-definite; use negative rho to get non-PD matrix in tests |
| Simplex normalisation | High positive rho → MORE negative pairwise output after renorm (Aitchison geometry) |
| CSS heredoc on Windows | Fails with special chars (°, µ, backticks) — use Python script append instead |
| `colPadding` in ReportLab Table | Not a valid `__init__` arg — use `TableStyle` |
| `ROUNDEDCORNERS` in TableStyle | Not valid — remove |
| `sim.annual_losses` | Shape is (N, T) — use `np.percentile`, not `sorted()` |
| PCC TCOR history | Was NOK 210M (double-count bug) → corrected to NOK 64M in Sprint 8b |

---

## Running the Platform

```bash
# Tests
pytest tests/ -q

# Backend
uvicorn backend.main:app --reload --port 8000

# Frontend (dev)
cd frontend && npm run dev

# Frontend (build verification)
cd frontend && npm run build

# CLI
python main.py
python -m c5ai_plus.pipeline --input c5ai_input.json

# Self-learning demo
python examples/run_learning_loop_demo.py
```
