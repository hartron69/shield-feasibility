# Sprint 7 – Cross-Domain Risk Correlation

## 1. What it does

Prior to Sprint 7, domain losses (biological / structural / environmental / operational) were fixed
proportions of each simulation year's total loss.  A storm year and a calm year produced identical
biological-to-structural ratios — domains were 100% correlated by construction.

Sprint 7 introduces a **`DomainCorrelationMatrix`** (4 × 4) that governs how those proportions
co-vary across simulation years.  Concretely:

- Each simulation year receives a correlated random perturbation to the domain weight fractions.
- The perturbation is drawn from a multivariate Gaussian whose covariance is the
  `DomainCorrelationMatrix`, scaled by `perturbation_strength` (default 0.20).
- Weights are clipped to ≥ 0 and renormalised so they always sum to 1 — total losses are
  preserved exactly.

This means storm years now see elevated environmental **and** structural losses simultaneously,
warm low-oxygen years amplify biological losses relative to structural, and operational incidents
cluster in high-structural-stress years — all governed by the correlation matrix entries.


## 2. How to enable / disable it

### Enabled (default in `main.py`)

```python
from models.domain_correlation import DomainCorrelationMatrix
from models.monte_carlo import MonteCarloEngine

engine = MonteCarloEngine(
    operator,
    n_simulations=10_000,
    domain_correlation=DomainCorrelationMatrix.expert_default(),   # <-- enables Sprint 7
)
sim = engine.run()
# sim.domain_loss_breakdown.domain_correlation_applied == True
```

Pass the same object to the PDF generator to unlock the new report sections:

```python
from reporting.pdf_report import PDFReportGenerator

reporter = PDFReportGenerator(
    ...,
    domain_loss_breakdown=sim.domain_loss_breakdown,   # <-- feeds the new sections
    domain_correlation=DomainCorrelationMatrix.expert_default(),
)
reporter.generate()
```

### Disabled (backward-compatible)

Omit both parameters entirely:

```python
engine = MonteCarloEngine(operator, n_simulations=10_000)
# sim.domain_loss_breakdown is None
# PDFReportGenerator without domain_loss_breakdown silently omits the new sections
```

All 586 pre-Sprint-7 tests pass unchanged with no parameters set.


## 3. Presets

Four named presets are available in `PREDEFINED_DOMAIN_CORRELATIONS`:

| Key | Description |
|---|---|
| `"independent"` | Zero off-diagonal correlation — domains move independently |
| `"low"` | Equicorrelation ρ = 0.20 — mild co-movement |
| `"moderate"` | Equicorrelation ρ = 0.40 — moderate co-movement |
| `"expert_default"` | Asymmetric 4×4 matrix (see below) — **recommended for production** |

```python
from models.domain_correlation import PREDEFINED_DOMAIN_CORRELATIONS, DomainCorrelationMatrix

m = PREDEFINED_DOMAIN_CORRELATIONS["expert_default"]
# or equivalently:
m = DomainCorrelationMatrix.expert_default()
```

### Expert-default matrix (domain order: bio, struct, env, ops)

|           | bio  | struct | env  | ops  |
|-----------|------|--------|------|------|
| **bio**   | 1.00 | 0.20   | 0.40 | 0.15 |
| **struct**| 0.20 | 1.00   | 0.60 | 0.35 |
| **env**   | 0.40 | 0.60   | 1.00 | 0.15 |
| **ops**   | 0.15 | 0.35   | 0.15 | 1.00 |

Rationale:
- **env ↔ struct 0.60** — storms damage both water quality and physical structures simultaneously.
- **env ↔ bio 0.40** — warm/hypoxic conditions increase biological event probability.
- **ops ↔ struct 0.35** — operational incidents cluster in high structural-stress periods.
- **bio ↔ struct 0.20** — large biomass events stress cage and mooring systems.

You can also build a custom matrix from named pairs:

```python
m = DomainCorrelationMatrix.from_dict({
    "env_struct": 0.55,
    "env_bio": 0.35,
    "ops_struct": 0.30,
})
```

Or extract a subset for non-bio residual work:

```python
sub = m.sub_matrix(["structural", "environmental", "operational"])
```


## 4. How it affects the PDF report

Two new sections are inserted between **Simulation Results** and **Strategy Comparison**:

### Page: Correlated Cross-Domain Risk
- Narrative introduction explaining domain co-variance in board language.
- 4 × 4 correlation matrix table with board-friendly labels (High / Moderate / Low / Negligible).
- Correlation heatmap chart (RdYlGn colourmap).
- Key pair explanations (env ↔ struct, env ↔ bio, etc.).
- Tail domain composition table — average domain breakdown across the worst 5% of simulated years.
- Tail domain stacked bar chart.

### Page: Scenario Comparison — Normal / Stress / Extreme Year
- Three-column table comparing p50 / p95 / p99 loss years.
- Stacked horizontal bar chart showing domain mix per scenario.
- Per-scenario board-language narratives.

### Extended Recommendation section
- "Risk Profile" paragraph: isolated events vs correlated stress framing.
- "Implications for PCC Structure" — readiness-dependent bullets.
- "Implications for Risk Mitigation" — four cross-domain mitigation insights.

If `domain_loss_breakdown` is `None`, all new sections are silently omitted and the report
renders identically to the pre-Sprint-7 format.


## 5. Generate a sample report

```bash
cd /c/Users/haral/dev/shield-feasibility

# Full run (10 000 simulations, ~4 s)
python main.py --output pcc_report_sprint7.pdf

# Fast smoke-test (2 000 simulations, ~1 s)
python main.py -n 2000 --output pcc_report_sprint7.pdf

# Custom operator input
python main.py --input data/my_operator.json --output pcc_report_my_operator.pdf
```

Output file location: `C:\Users\haral\dev\shield-feasibility\pcc_report_sprint7.pdf`

If `--output` is omitted the file is auto-named `pcc_report_<YYYYMMDD_HHMMSS>.pdf` in the
working directory.


## 6. Entry points for future maintenance

| File | Role |
|---|---|
| `models/domain_correlation.py` | **Primary model file.** Edit correlation matrix values, add presets, adjust `perturbation_strength` default, or add new factory methods here. |
| `models/domain_loss_breakdown.py` | **Perturbation engine.** Edit `_perturb_domain_weights()` to change the mathematical model (e.g. switch from additive to multiplicative perturbations), or `apply_domain_correlation()` to change how bio-modelled vs prior-only paths diverge. |
| `models/monte_carlo.py` | **Integration point.** The `domain_correlation` parameter wiring and `build_domain_loss_breakdown()` call live here. |
| `reporting/correlated_risk_analytics.py` | **Analytics layer.** Edit scenario percentiles, tail threshold, board narratives, KPI definitions — no rendering dependencies, safe to unit-test in isolation. |
| `reporting/chart_generator.py` | **Chart layer.** Edit `chart_domain_correlation_heatmap`, `chart_scenario_domain_stacks`, `chart_tail_domain_composition` for visual changes. |
| `reporting/pdf_report.py` | **PDF layout.** Edit `_build_correlated_risk()` and `_build_scenario_comparison()` for section copy, table layout, or page order changes. |
| `tests/test_domain_correlation.py` | 38 tests — run after any change to `domain_correlation.py`. |
| `tests/test_domain_loss_breakdown.py` | 8 new tests in `TestBuildWithCorrelation` — run after changes to the perturbation engine. |
| `tests/test_mc_domain_correlation.py` | 10 integration tests — run after any change to `monte_carlo.py`. |
| `tests/test_correlated_risk_report.py` | 52 tests — run after any change to analytics, charts, or PDF sections. |

Run the full suite before merging any change:

```bash
pytest tests/ -q
# Expected: 694 passed, 2 skipped, 0 failed
```
