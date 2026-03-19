# PCC Feasibility & Suitability Tool
## User Manual — Version 1.0

**Prepared by:** Shield Risk Consulting
**Classification:** Confidential — For Operator and Adviser Use Only
**Platform:** Python 3.10+ | Windows / macOS / Linux

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements & Installation](#2-system-requirements--installation)
3. [Quick Start](#3-quick-start)
4. [Input Data Guide](#4-input-data-guide)
   - 4.1 [File Format Overview](#41-file-format-overview)
   - 4.2 [Operator Identity](#42-operator-identity)
   - 4.3 [Sites](#43-sites)
   - 4.4 [Current Insurance Programme](#44-current-insurance-programme)
   - 4.5 [Historical Loss Records](#45-historical-loss-records)
   - 4.6 [Financial Profile](#46-financial-profile)
   - 4.7 [Risk Parameters](#47-risk-parameters)
   - 4.8 [Strategy Preferences](#48-strategy-preferences)
5. [Running the Tool](#5-running-the-tool)
   - 5.1 [Command-Line Arguments](#51-command-line-arguments)
   - 5.2 [Progress Output Explained](#52-progress-output-explained)
   - 5.3 [Runtime Guidance](#53-runtime-guidance)
6. [The Four Strategies Modelled](#6-the-four-strategies-modelled)
   - 6.1 [Full Insurance](#61-full-insurance)
   - 6.2 [Hybrid](#62-hybrid)
   - 6.3 [PCC Captive Cell](#63-pcc-captive-cell)
   - 6.4 [Self-Insurance](#64-self-insurance)
7. [Analytical Modules](#7-analytical-modules)
   - 7.1 [Monte Carlo Simulation](#71-monte-carlo-simulation)
   - 7.2 [Solvency Capital Requirement (SCR)](#72-solvency-capital-requirement-scr)
   - 7.3 [5-Year Total Cost of Risk (TCOR)](#73-5-year-total-cost-of-risk-tcor)
   - 7.4 [Volatility Metrics](#74-volatility-metrics)
   - 7.5 [Suitability Engine](#75-suitability-engine)
8. [Understanding the PDF Report](#8-understanding-the-pdf-report)
   - 8.1 [Report Structure](#81-report-structure)
   - 8.2 [Reading the Charts](#82-reading-the-charts)
   - 8.3 [Suitability Score Interpretation](#83-suitability-score-interpretation)
9. [Configuration Reference](#9-configuration-reference)
10. [Customising for a New Operator](#10-customising-for-a-new-operator)
11. [Frequently Asked Questions](#11-frequently-asked-questions)
12. [Troubleshooting](#12-troubleshooting)
13. [Methodology & Assumptions Reference](#13-methodology--assumptions-reference)
14. [Glossary](#14-glossary)

---

## 1. Introduction

The **PCC Feasibility & Suitability Tool** is an actuarial modelling platform designed to help fish farming operators and their risk advisers objectively evaluate whether forming a **Protected Cell Company (PCC) captive insurance cell** makes financial and strategic sense compared to conventional market insurance or self-insurance alternatives.

### What the tool does

For any given operator it will:

- **Model annual losses** using a Monte Carlo simulation calibrated to the operator's specific risk profile (species, biomass, geography, loss history).
- **Price four risk strategies** side by side — full market insurance, a hybrid large-deductible programme, a PCC captive cell, and full self-insurance — over a 5-year horizon.
- **Calculate capital requirements** using a simplified Solvency II framework (99.5% VaR).
- **Score PCC suitability** across five weighted criteria and issue an automated recommendation with plain-language rationale.
- **Generate a board-ready PDF report** containing all charts, tables, assumptions, and decision logic in a single confidential document.

### Who should use it

| Role | How they use the tool |
|------|----------------------|
| Risk Manager / CFO | Prepare the operator input JSON, interpret results, present to board |
| Risk Adviser / Broker | Run scenarios for client, support captive feasibility discussions |
| Actuary | Validate model assumptions, review SCR outputs |
| Board / Finance Committee | Read the PDF report — no technical knowledge required |

### What the tool does NOT do

- It does not constitute insurance, legal, regulatory, or tax advice.
- It does not model multi-year loss dependency or catastrophe accumulation across portfolios.
- It does not replace a full actuarial pricing study or regulatory application for captive formation.

---

## 2. System Requirements & Installation

### Prerequisites

| Item | Minimum Version |
|------|----------------|
| Python | 3.10 |
| pip | 22.0 |
| RAM | 4 GB (8 GB recommended for n > 50,000 simulations) |
| Disk | 200 MB free |
| OS | Windows 10, macOS 12, Ubuntu 20.04 (or later) |

### Installation

**Step 1 — Clone or copy the project folder**

```
shield-feasibility/
├── main.py
├── requirements.txt
├── config/
├── data/
├── models/
├── analysis/
└── reporting/
```

**Step 2 — Create a virtual environment (recommended)**

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**Step 3 — Install dependencies**

```bash
pip install -r requirements.txt
```

The `requirements.txt` installs:

| Package | Purpose |
|---------|---------|
| `numpy` | Vectorised Monte Carlo arrays |
| `scipy` | Statistical distributions |
| `pandas` | Data manipulation |
| `matplotlib` | Chart generation |
| `seaborn` | Chart styling |
| `reportlab` | PDF generation |
| `pydantic` | Input validation |

**Step 4 — Verify installation**

```bash
python main.py --help
```

Expected output:
```
usage: main.py [-h] [--input INPUT] [--output OUTPUT] [--simulations SIMULATIONS]

PCC Feasibility & Suitability Tool - Fish Farming Risk Management

options:
  -h, --help                     show this help message and exit
  --input, -i INPUT              Path to operator input JSON file (default: data/sample_input.json)
  --output, -o OUTPUT            Output PDF path (auto-generated if omitted)
  --simulations, -n SIMULATIONS  Number of Monte Carlo simulations (default: 10000)
```

---

## 3. Quick Start

Run the included sample analysis in under 5 seconds:

```bash
python main.py
```

This uses `data/sample_input.json` (Nordic Aqua Partners AS — a fictional Norwegian salmon farming operation) and writes a timestamped PDF to the working directory.

To run your own operator:

```bash
python main.py --input my_operator.json --output board_report_2026.pdf
```

For a high-precision run (recommended for final board reports):

```bash
python main.py --input my_operator.json --output board_report.pdf --simulations 50000
```

---

## 4. Input Data Guide

All operator-specific data is provided as a single JSON file. The file is structured into seven sections.

### 4.1 File Format Overview

```json
{
  "name":                        "...",
  "registration_number":         "...",
  "country":                     "...",
  "reporting_currency":          "USD",
  "captive_domicile_preference": "Guernsey",
  "management_commitment_years": 5,
  "willing_to_provide_capital":  true,
  "has_risk_manager":            false,
  "governance_maturity":         "developing",

  "sites":              [ ... ],
  "current_insurance":  { ... },
  "historical_losses":  [ ... ],
  "financials":         { ... },
  "risk_params":        { ... }
}
```

All monetary values are in **USD**. Use consistent units throughout — do not mix currencies.

---

### 4.2 Operator Identity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Full legal name of the operating entity |
| `registration_number` | string | No | Company registration or tax ID |
| `country` | string | Yes | Country of primary operations |
| `reporting_currency` | string | No | Currency label shown in the report (default: `"USD"`) |
| `captive_domicile_preference` | string | No | Preferred captive jurisdiction (e.g. `"Guernsey"`, `"Cayman Islands"`) |
| `management_commitment_years` | integer | No | Number of years management is willing to operate the captive (default: `5`) |
| `willing_to_provide_capital` | boolean | No | Whether the operator will capitalise the cell (default: `true`) |
| `has_risk_manager` | boolean | No | Whether a qualified risk manager is in place (default: `false`) |
| `governance_maturity` | string | No | `"basic"`, `"developing"`, or `"mature"` (default: `"developing"`) |

**Governance maturity guidance:**

| Level | Description |
|-------|-------------|
| `"basic"` | No formal risk framework; ad hoc management |
| `"developing"` | Risk committee exists; policies in draft or partial implementation |
| `"mature"` | Formal risk framework, board-level risk oversight, dedicated resources |

---

### 4.3 Sites

The `sites` array lists every production location. Include all sites whose risks would be written into the captive cell. At least one site is required.

```json
"sites": [
  {
    "name":                    "Hardanger North",
    "location":                "Hardangerfjord, Hordaland",
    "species":                 "Atlantic Salmon",
    "biomass_tonnes":          4200,
    "biomass_value_per_tonne": 6800,
    "equipment_value":         3500000,
    "infrastructure_value":    2800000,
    "annual_revenue":          38500000
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Site identifier (appears in report tables) |
| `location` | string | Free-text geographic description |
| `species` | string | Primary species farmed at this site |
| `biomass_tonnes` | number | Maximum standing biomass in metric tonnes |
| `biomass_value_per_tonne` | number | Current market price per tonne (USD) |
| `equipment_value` | number | Replacement value of all movable equipment |
| `infrastructure_value` | number | Value of fixed infrastructure (moorings, buildings, pipework) |
| `annual_revenue` | number | Gross annual revenue generated by this site |

**Total Insured Value (TIV)** is calculated automatically per site as:

```
TIV = (biomass_tonnes × biomass_value_per_tonne) + equipment_value + infrastructure_value
```

> **Tip:** Use peak-biomass values. The tool models losses against the maximum exposure, consistent with insurance market practice.

---

### 4.4 Current Insurance Programme

```json
"current_insurance": {
  "annual_premium":              1850000,
  "per_occurrence_deductible":   150000,
  "annual_aggregate_deductible": 350000,
  "coverage_limit":              25000000,
  "aggregate_limit":             45000000,
  "coverage_lines":              ["Fish Mortality", "Property Damage", "Business Interruption"],
  "insurer_names":               ["Lloyd's Syndicate 1234", "Norwegian Hull Club"],
  "current_loss_ratio":          0.58,
  "market_rating_trend":         0.07
}
```

| Field | Type | Description |
|-------|------|-------------|
| `annual_premium` | number | Total gross premium paid across all coverage lines |
| `per_occurrence_deductible` | number | Deductible applied to each individual loss event |
| `annual_aggregate_deductible` | number | Annual cap on total deductible exposure |
| `coverage_limit` | number | Maximum recovery per single occurrence |
| `aggregate_limit` | number | Maximum total annual recovery across all claims |
| `coverage_lines` | array of strings | List of lines covered by the current programme |
| `insurer_names` | array of strings | Names of current insurers (for report disclosure) |
| `current_loss_ratio` | number | Gross loss ratio (total losses / total premium). Use 3–5 year average where available |
| `market_rating_trend` | number | Annual rate of market premium change as a decimal (e.g. `0.07` = +7% p.a.) |

> **Market rating trend:** This is used to project how premiums will increase under the Full Insurance strategy. Use the most recent Lloyd's / specialist market trend for aquaculture. A positive value means premiums are hardening.

---

### 4.5 Historical Loss Records

Provide one record per loss event. A minimum of 3 years of history is recommended for model credibility; 5 years is ideal.

```json
"historical_losses": [
  {
    "year":          2022,
    "event_type":    "mortality",
    "gross_loss":    1650000,
    "insured_loss":  1500000,
    "retained_loss": 150000
  },
  {
    "year":          2022,
    "event_type":    "property",
    "gross_loss":    420000,
    "insured_loss":  270000,
    "retained_loss": 150000
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `year` | integer | Calendar year of the loss event |
| `event_type` | string | One of: `"mortality"`, `"property"`, `"liability"`, `"business_interruption"` |
| `gross_loss` | number | Total economic loss before any insurance recovery |
| `insured_loss` | number | Amount actually paid by the insurer |
| `retained_loss` | number | Amount absorbed by the operator (deductible + uninsured) |

**Check:** `gross_loss` should equal `insured_loss + retained_loss` (± rounding).

> **If no loss history is available:** Leave `historical_losses` as an empty array `[]`. The model will rely entirely on the `risk_params` section. Results will be less accurate — flag this clearly in any board presentation.

---

### 4.6 Financial Profile

```json
"financials": {
  "annual_revenue":      85500000,
  "ebitda":              18200000,
  "total_assets":        112000000,
  "net_equity":          54000000,
  "credit_rating":       "BB+",
  "free_cash_flow":      9800000,
  "years_in_operation":  14
}
```

| Field | Type | Description |
|-------|------|-------------|
| `annual_revenue` | number | Total consolidated annual revenue |
| `ebitda` | number | Earnings before interest, tax, depreciation, amortisation |
| `total_assets` | number | Total balance sheet assets |
| `net_equity` | number | Shareholders' equity / net assets |
| `credit_rating` | string or null | External credit rating if available; `null` if unrated |
| `free_cash_flow` | number | Unencumbered cash available to fund capital (after capex, debt service) |
| `years_in_operation` | integer | Number of full years the business has been operating |

> **Free cash flow** is the most critical financial field. The suitability engine compares it directly against the capital required to fund the PCC cell. If FCF is less than the estimated cell capital, a condition is automatically raised in the report.

---

### 4.7 Risk Parameters

This section defines the statistical shape of the loss distribution. These are the parameters that drive the Monte Carlo engine.

```json
"risk_params": {
  "expected_annual_events":       2.8,
  "mean_loss_severity":           680000,
  "cv_loss_severity":             0.75,
  "catastrophe_probability":      0.04,
  "catastrophe_loss_multiplier":  8.5,
  "inter_site_correlation":       0.15,
  "bi_trigger_threshold":         500000,
  "bi_daily_revenue_loss":        95000,
  "bi_average_interruption_days": 18
}
```

| Field | Type | Description |
|-------|------|-------------|
| `expected_annual_events` | number | Mean number of loss-producing events per year (Poisson λ). Derived from historical frequency. |
| `mean_loss_severity` | number | Average cost per individual loss event (USD). |
| `cv_loss_severity` | number | Coefficient of variation of severity (σ/μ). Controls how spread-out loss sizes are. |
| `catastrophe_probability` | number | Annual probability (0–1) of a catastrophic event occurring. |
| `catastrophe_loss_multiplier` | number | A CAT event is modelled as this multiple of the mean severity. |
| `inter_site_correlation` | number | Correlation (0–1) between losses at different sites. Use 0 for fully independent sites, 1 for fully correlated. |
| `bi_trigger_threshold` | number | Minimum gross loss (USD) required to trigger a Business Interruption claim. |
| `bi_daily_revenue_loss` | number | Revenue lost per day during a production interruption. |
| `bi_average_interruption_days` | number | Expected duration of interruption for a major BI event (days). |

**Estimating risk parameters from history:**

| Parameter | Estimation method |
|-----------|------------------|
| `expected_annual_events` | Count total events in history ÷ number of years |
| `mean_loss_severity` | Average of all `gross_loss` values |
| `cv_loss_severity` | Standard deviation ÷ mean of all `gross_loss` values |
| `catastrophe_probability` | Number of CAT years (loss > 3× mean) ÷ years of history |
| `catastrophe_loss_multiplier` | Average CAT event size ÷ mean severity |

**Coefficient of variation guidance:**

| CV value | Interpretation | Captive suitability impact |
|----------|---------------|--------------------------|
| < 0.30 | Very stable losses | Strong positive |
| 0.30–0.50 | Stable | Positive |
| 0.50–0.75 | Moderate volatility | Neutral |
| 0.75–1.00 | High volatility | Negative |
| > 1.00 | Extreme volatility | Strong negative |

---

### 4.8 Strategy Preferences

These fields feed the Operational Readiness criterion of the suitability engine and appear in the report narrative.

| Field | Values | Effect |
|-------|--------|--------|
| `captive_domicile_preference` | `"Guernsey"`, `"Cayman Islands"`, `"Isle of Man"`, `"Malta"`, etc. | Appears in PCC assumptions and next-steps |
| `management_commitment_years` | Integer ≥ 1 | Scores higher at ≥ 5 years; ≥ 7 years = maximum score |
| `willing_to_provide_capital` | `true` / `false` | `false` is a hard blocker for captive suitability |
| `has_risk_manager` | `true` / `false` | Absence reduces Operational Readiness score |
| `governance_maturity` | `"basic"`, `"developing"`, `"mature"` | Higher maturity = higher readiness score |

---

## 5. Running the Tool

### 5.1 Command-Line Arguments

```
python main.py [--input INPUT] [--output OUTPUT] [--simulations N]
```

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--input` | `-i` | `data/sample_input.json` | Path to the operator JSON input file |
| `--output` | `-o` | `pcc_report_YYYYMMDD_HHMMSS.pdf` | Full file path for the PDF output |
| `--simulations` | `-n` | `10000` | Number of Monte Carlo iterations |

**Examples:**

```bash
# Use defaults (sample data, 10,000 simulations, auto-named PDF)
python main.py

# Custom operator, auto-named output
python main.py --input operators/nordic_aqua.json

# Fully specified
python main.py -i operators/nordic_aqua.json -o reports/board_q1_2026.pdf -n 50000

# Quick feasibility check (fewer simulations, faster)
python main.py -i operators/nordic_aqua.json -n 2000
```

**Simulation count guidance:**

| Simulations | Runtime | Use case |
|-------------|---------|---------|
| 2,000–5,000 | < 2s | Quick feasibility screening |
| 10,000 | ~3s | Standard analysis (default) |
| 20,000–50,000 | 5–15s | Final board report (smoother charts, stable tail estimates) |
| 100,000+ | 30–120s | Actuarial review / sensitivity testing |

---

### 5.2 Progress Output Explained

The tool prints a 9-step progress indicator to the console:

```
  [###-------------------------]  1/9  Validating input data...
       Operator  : Nordic Aqua Partners AS
       TIV       : $83,960,000
       Premium   : $1,850,000

  [######----------------------]  2/9  Monte Carlo simulation (10,000 runs × 5 years)...
       E[annual loss]  : $2,159,884
       VaR 99.5%       : $12,849,876

  [#########-------------------]  3/9  Modelling risk-transfer strategies...
       Full Insurance        : 5-yr cost = $12,423,072
       Hybrid                : 5-yr cost = $13,104,430
       PCC Captive Cell      : 5-yr cost = $21,042,455
       Self-Insurance        : 5-yr cost = $18,971,028

  [############----------------]  4/9  Calculating Solvency Capital Requirements...
  [###############-------------]  5/9  Analysing 5-year total cost of risk...
  [##################----------]  6/9  Computing volatility and tail-risk metrics...
  [#####################-------]  7/9  Generating suitability assessment...
       Verdict         : POTENTIALLY SUITABLE
       Score           : 48.9/100  (Low confidence)
         Premium Volume            : [########--] 80
         Loss Stability            : [###-------] 30
         ...

  [########################----]  8/9  Building board-ready PDF report...
      Rendering charts... done.

  [############################]  9/9  Complete.
  Report saved : pcc_report_20260305_094512.pdf
  Elapsed      : 3.2s
```

Each bar segment (`#`) represents approximately 3.5% completion of that step.

---

### 5.3 Runtime Guidance

- The tool runs entirely locally — no internet connection is required.
- Output PDFs are written to the current working directory unless `--output` specifies a different path.
- Multiple runs against the same operator are reproducible: the random seed is fixed at `42` in `config/settings.py`.
- To test sensitivity to loss assumptions, run the tool twice with different `cv_loss_severity` values and compare the resulting PDFs.

---

## 6. The Four Strategies Modelled

### 6.1 Full Insurance

**What it is:** The operator continues to purchase all coverage from the external market at or near current terms.

**How costs are modelled:**

```
Annual Cost = Premium × (1 + market_rating_trend)^(yr-1)
            + E[min(annual_loss, aggregate_deductible)]
            + Admin (0.8% of base premium)
```

**Key driver:** The market rating trend. At +7% p.a., a $1.85M premium becomes ~$2.59M by Year 5. This makes Full Insurance the most expensive strategy in a hardening market.

**Capital requirement:** None (risk transferred to insurer). Small counterparty risk component only.

---

### 6.2 Hybrid

**What it is:** The operator takes a materially higher retention (working-layer deductible) and buys excess-of-loss cover only above the retention point. The insurer grants a premium credit for the frequency risk retained.

**How costs are modelled:**

```
Retention = max(25% × E[annual loss], current_deductible)
XS Premium = Base Premium × (1 - hybrid_retention%) × (1 - hybrid_discount)
Annual Cost = XS Premium + E[min(annual_loss, retention)] + Admin
```

**Capital requirement:** 1.5× the retention layer as a working capital buffer.

**Best suited to:** Operators with stable, predictable working-layer losses who want premium savings without the governance burden of a formal captive.

---

### 6.3 PCC Captive Cell

**What it is:** The operator forms or rents a cell within a Protected Cell Company. The cell underwrites the operator's risks, receives premium, and pays claims. External reinsurance is purchased above the cell's retention limit.

**How costs are modelled:**

```
Year 1: Setup cost ($120,000) + Cell capital (SCR + Technical Provisions)
        + Reduced premium to cell (market premium × 78%)
        + Fronting fee (3% of cell premium)
        + Cell management fee ($45,000)
        - Investment income on reserves (4% p.a.)

Years 2–5: Annual cell fee + cell premium (no more setup cost)
           ± Shortfall replenishment if reserves depleted by large losses
           - Investment income on rolling reserve balance
```

**Capital requirement:** SCR (99.5% VaR of net annual loss) + Technical Provisions. This capital is provided by the operator, is invested, and is returned at wind-up if the cell is solvent.

**The captive advantage materialises through:**
1. Premium savings (22% below market by default, accumulating annually)
2. Investment income earned on reserve capital
3. Profit commission in years with favourable loss experience
4. Insulation from market hardening cycles

---

### 6.4 Self-Insurance

**What it is:** The operator establishes an internal reserve fund and absorbs all losses directly, with no external risk transfer.

**How costs are modelled:**

```
Annual Cost = E[annual gross loss]
            + Admin (max(1.5% of TIV, $80,000/yr))
            + Capital opportunity cost (6% of reserve fund)
            - Investment income (4% of reserve fund)

Reserve fund = max(1.5 × E[annual loss], VaR 99%)
```

**Capital requirement:** The full reserve fund (pre-funded from the operator's balance sheet).

**Warning:** Self-insurance exposes the operator to uninsured catastrophic losses. The 99.5% VaR tail is fully retained. This strategy is included as an analytical lower bound, not a recommendation.

---

## 7. Analytical Modules

### 7.1 Monte Carlo Simulation

**Model:** Compound Poisson–LogNormal

**Frequency:** The number of loss events in each year is drawn from a Poisson distribution:

```
N_t ~ Poisson(λ)
where λ = expected_annual_events
```

**Severity:** Each individual event's cost is drawn from a log-normal distribution:

```
X_i ~ LogNormal(μ, σ)
where:
  σ = sqrt(ln(1 + CV²))
  μ = ln(mean_severity) - σ²/2
```

**Catastrophe overlay:** With annual probability `catastrophe_probability`, an additional catastrophic event is injected with mean severity = `catastrophe_loss_multiplier × mean_severity`.

**Annual aggregate loss:**

```
S_t = Σ X_i (i = 1..N_t) + CAT_t
```

**Output:** A matrix of shape `(n_simulations, 5)` — one simulated annual loss for each of 10,000 scenarios over 5 years. All downstream strategy models operate on this same loss matrix, ensuring comparability.

---

### 7.2 Solvency Capital Requirement (SCR)

The SCR is calculated using a **simplified Solvency II framework** appropriate for captive feasibility analysis.

```
SCR = max(0, VaR(99.5%) of net annual loss − Technical Provisions)

Technical Provisions = Best Estimate Liability × (1 + 10% prudence)
                     + Risk Margin

Risk Margin = CoC (6%) × SCR × annuity factor (5-year, 4% discount)

Best Estimate Liability = E[net annual loss]
```

**Interpretation by strategy:**

| Strategy | SCR Treatment |
|----------|--------------|
| Full Insurance | Minimal — counterparty risk only (~5% of net SCR) |
| Hybrid | Moderate — on the retained layer only |
| PCC Captive Cell | Full SCR on retained losses within the cell |
| Self-Insurance | Full SCR on all losses |

**Solvency ratio** = Provided Capital ÷ SCR. A ratio ≥ 100% is required for cell viability. The report flags under-capitalised structures with a warning.

---

### 7.3 5-Year Total Cost of Risk (TCOR)

**TCOR components:**

```
TCOR = Premiums paid
     + Retained losses (actual or expected)
     + Administrative costs
     + Capital opportunity cost
     + Setup / exit costs
     − Investment income
```

Two TCOR measures are reported:

| Measure | Description |
|---------|-------------|
| **Nominal TCOR** | Simple sum of all annual costs over 5 years. This is the "sticker price" — what the operator will write cheques for. |
| **NPV TCOR** | Each year's cost discounted at the risk-free rate (4% p.a.). This is the economically correct comparison for decision-making. |

**Savings vs. Full Insurance** = Full Insurance TCOR − Strategy TCOR. A positive number means the alternative is cheaper.

---

### 7.4 Volatility Metrics

For each strategy, the tool calculates the following metrics on the simulated annual cost distribution:

| Metric | Definition |
|--------|-----------|
| **Standard deviation** | Year-to-year variability in net cost |
| **Coefficient of variation (CV)** | σ / μ — normalised volatility measure |
| **VaR 95% (annual)** | Cost exceeded in only 5% of simulated years |
| **VaR 99.5% (annual)** | Worst 1-in-200 year outcome |
| **TVaR 95%** | Average cost in the worst 5% of years (Expected Shortfall) |
| **Skewness** | Asymmetry of the cost distribution |
| **Excess kurtosis** | Tail heaviness relative to a normal distribution |
| **P(cost > premium)** | Probability that actual annual cost exceeds the base premium |

---

### 7.5 Suitability Engine

The engine scores the operator on five weighted criteria and maps the composite score to a verdict.

**Scoring model:**

| Criterion | Weight | What it measures |
|-----------|--------|-----------------|
| Premium Volume | 25% | Is there enough premium mass to justify captive formation costs? |
| Loss Stability | 20% | Are losses predictable enough to price and reserve accurately? |
| Balance Sheet Strength | 20% | Can the operator fund the required SCR capital? |
| Cost Savings Potential | 20% | Will the PCC strategy deliver material savings vs. the market? |
| Operational Readiness | 15% | Governance, management commitment, years in operation |

Each criterion is scored 0–100 and multiplied by its weight to produce a weighted score. The composite score is the sum of all weighted scores (maximum 100).

**Verdict thresholds:**

| Score Range | Verdict | Meaning |
|-------------|---------|---------|
| ≥ 72 | STRONGLY RECOMMENDED | All or nearly all criteria strongly support captive formation |
| 55–71 | RECOMMENDED | Majority of criteria positive; minor gaps manageable |
| 40–54 | POTENTIALLY SUITABLE | Mixed picture; further analysis required before proceeding |
| 25–39 | NOT RECOMMENDED | Significant barriers; captive unlikely to deliver value |
| < 25 | NOT SUITABLE | Captive economics fundamentally unviable at current scale |

**Confidence level** reflects how definitive the verdict is:

- **High confidence:** Score is far from a threshold boundary
- **Medium confidence:** Score is within 5 points of a threshold
- **Low confidence:** Conflicting signals across criteria; professional judgement required

---

## 8. Understanding the PDF Report

### 8.1 Report Structure

The PDF is structured as a **13-section board document**:

| Page | Section | Content |
|------|---------|---------|
| 1 | Cover | Operator name, date, verdict badge, classification |
| 2 | Executive Summary | Verdict banner, key strengths, barriers, conditions |
| 3 | Operator Risk Profile | Site table, financial profile, current insurance |
| 4 | Monte Carlo Results | Loss statistics table, loss distribution chart |
| 5 | Strategy Comparison | Full comparison matrix across all 4 strategies |
| 6 | 5-Year Cost Analysis | Cumulative cost curves, annual comparison chart |
| 7 | SCR Analysis | Capital requirement table, SCR comparison chart |
| 8 | Cost–Risk Frontier | Risk-return scatter plot, box-and-whisker chart |
| 9 | Suitability Detail | Per-criterion score cards with findings and rationale |
| 10 | Recommendation | Suitability radar chart, next-steps roadmap |
| 11 | Assumptions | Per-strategy assumption tables |
| 12 | Methodology | Model description, parameter definitions |
| 13 | Disclaimer | Legal and professional limitations |

---

### 8.2 Reading the Charts

**Figure 1 — Loss Distribution Histogram**

Shows the probability density of simulated annual gross losses. The dashed vertical lines mark key risk thresholds. Read this chart to understand the "shape" of the operator's risk — how spread out losses are and where the heavy tail begins.

- A tall, narrow histogram = stable, predictable losses → favourable for captive
- A flat, wide histogram with a long right tail = volatile losses → challenging for captive pricing

**Figure 2 — Cumulative Cost Curves**

Tracks how total spend accumulates over 5 years for each strategy. Lines that start high but grow slowly (typically PCC Captive Cell in hardening markets) signal a "delayed payback" structure — Year 1 costs are high due to setup, but the gap versus Full Insurance closes over time.

- The x-axis is years 1–5
- The y-axis is cumulative cost in USD
- The lowest line at Year 5 is the cheapest strategy over the horizon

**Figure 3 — Annual Cost Comparison (Bar Chart)**

Shows expected annual net cost side by side for each strategy, broken out by year. Use this to identify which strategy is cheapest in each individual year, not just cumulatively.

**Figure 4 — SCR Comparison**

Horizontal bars show the capital required (SCR) versus capital provided for each strategy. Strategies where the provided capital bar is shorter than the SCR bar are under-capitalised and will carry a warning in the report.

**Figure 5 — Cost–Risk Frontier**

Each strategy is plotted as a point on a scatter chart:
- **X-axis:** Annual cost volatility (standard deviation, $M)
- **Y-axis:** Mean annual expected cost ($M)

The ideal position is **lower-left** (low cost, low volatility). Full Insurance typically sits top-left (expensive but stable). Self-Insurance sits bottom-right (cheap in expectation but highly volatile).

**Figure 6 — Box-and-Whisker**

Shows the full distribution of annualised 5-year costs across all Monte Carlo simulations. The box covers the 25th–75th percentile (interquartile range). Whiskers extend to the 5th and 95th percentile. Outlier dots beyond the whiskers represent extreme scenarios.

**Figure 7 — Suitability Radar**

A spider/radar chart with five axes corresponding to the five suitability criteria. Each axis runs from 0 (centre) to 100 (outer edge). The gold dashed ring marks 60 — the target score per criterion for a positive PCC verdict. Criteria where the shaded area falls inside the gold ring are barriers to captive formation.

---

### 8.3 Suitability Score Interpretation

**How to read criterion score cards (Section 9 of the PDF):**

Each criterion card shows:
- **Score badge** (green ≥ 65, amber 40–64, red < 40)
- **Weight** — how much this criterion contributes to the composite
- **Finding** — one-line quantitative summary
- **Rationale** — plain-English explanation of the score

**What to do with barriers (red scores):**

| Barrier | Typical remediation |
|---------|-------------------|
| Low Premium Volume | Consider waiting until premium grows organically, or explore fronting a group captive with peer operators |
| High Loss Volatility | Invest in loss control; remodel after 2 additional stable years |
| Weak Balance Sheet | Arrange a committed bank facility to backstop cell reserves; restructure capital before inception |
| Low Cost Savings | Challenge market premium at renewal; if market softens, the PCC may become more attractive |
| Low Operational Readiness | Appoint a risk manager; strengthen governance framework; consider a 12-month preparation period |

---

## 9. Configuration Reference

Global model parameters are in `config/settings.py`. These can be adjusted by a qualified analyst to reflect local market conditions or regulatory requirements.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `default_simulations` | 10,000 | Monte Carlo iterations |
| `random_seed` | 42 | Fixed seed for reproducibility |
| `projection_years` | 5 | Number of years in the projection horizon |
| `risk_free_rate` | 4.0% | Discount rate for NPV; also used as investment return floor |
| `cost_of_capital_rate` | 6.0% | Solvency II Cost of Capital for Risk Margin |
| `inflation_rate` | 2.5% | Annual cost inflation applied to admin and retained losses |
| `scr_confidence_level` | 99.5% | VaR confidence level for SCR (Solvency II standard) |
| `technical_provision_load` | 10% | Prudence margin added to the Best Estimate Liability |
| `pcc_setup_cost` | $120,000 | Formation cost (legal, actuarial, regulatory filing) |
| `pcc_annual_cell_fee` | $45,000 | Annual cell rent and governance fee |
| `pcc_fronting_fee_rate` | 3.0% | Fee charged by the fronting insurer on ceded premium |
| `pcc_premium_discount` | 22% | Saving vs. full-market premium achieved by writing to the cell |
| `pcc_investment_return` | 4.0% | Expected return on cell reserves |
| `hybrid_retention_pct` | 25% | Working-layer retention as % of expected annual loss |
| `hybrid_premium_discount` | 30% | Premium reduction on the retained risk layer |
| `self_insurance_reserve_factor` | 1.5× | Reserve fund = this multiple of expected annual loss |
| `self_insurance_admin_rate` | 1.5% | Internal admin cost as % of TIV |
| `min_premium_for_captive` | $500,000 | Absolute premium floor for captive viability |
| `report_author` | Shield Risk Consulting | Firm name shown in the PDF header |
| `report_classification` | CONFIDENTIAL — Board Use Only | Footer classification label |

**To change a parameter for a single run** without editing the file, the cleanest approach is to temporarily modify `settings.py`, run the tool, then revert. A future version will support parameter overrides via the JSON input file.

---

## 10. Customising for a New Operator

**Step-by-step process:**

1. **Copy the sample file:**
   ```bash
   cp data/sample_input.json data/my_client.json
   ```

2. **Edit `data/my_client.json`** — replace all values with the operator's actual data (see Section 4 for field-by-field guidance).

3. **Verify risk parameters** with the operator's broker or actuary. The `expected_annual_events`, `mean_loss_severity`, and `cv_loss_severity` are the most impactful inputs — small changes here materially affect all outputs.

4. **Run a quick sanity check:**
   ```bash
   python main.py --input data/my_client.json --simulations 2000
   ```
   Review the console output. Check that E[annual loss] is plausible relative to the historical loss data.

5. **If results look reasonable,** run the full analysis:
   ```bash
   python main.py --input data/my_client.json --output reports/my_client_2026.pdf --simulations 20000
   ```

6. **Review the PDF**, paying particular attention to:
   - Section 5 (Strategy Comparison) — are the relative costs as expected?
   - Section 7 (SCR Analysis) — is the required capital fundable?
   - Section 9 (Suitability) — which criteria are dragging the score down?

7. **Adjust settings if needed.** For example, if the market premium discount for this operator's domicile is 15% (not 22%), update `pcc_premium_discount` in `config/settings.py` and re-run.

---

## 11. Frequently Asked Questions

**Q: How many years of loss history are needed?**

A minimum of 3 years is recommended. With fewer than 3 years, the risk parameters will be poorly calibrated and results should be treated as directional only. Always note data limitations in any board presentation. Five or more years provides sufficient statistical credibility for the frequency and severity parameters.

---

**Q: The tool shows PCC is more expensive than Full Insurance over 5 years. Does that mean the operator should not form a captive?**

Not necessarily. The model assumes mean-expected losses. In years where actual losses are below expectation, the cell retains a profit — this becomes investment income and a reserve build that reduces long-run cost. The comparison should be made on the **NPV TCOR** basis and should also consider qualitative factors: cycle management, pricing control, and long-term strategic value of owning a captive. If the suitability score is in the "Recommended" or "Strongly Recommended" range despite a marginal 5-year cost advantage, the recommendation still stands.

---

**Q: Can I model more than 5 years?**

Change `projection_years` in `config/settings.py`. Note that the SCR calculation assumes a 5-year annuity factor — this will need manual adjustment in `analysis/scr_calculator.py` if you extend the horizon.

---

**Q: What currency does the tool use?**

All monetary inputs and outputs are in USD. If the operator's accounts are in another currency (e.g. NOK, EUR), convert all values at the date of the analysis and note the exchange rate in the assumptions. The `reporting_currency` field changes only the label shown in the PDF — it does not perform currency conversion.

---

**Q: Why is the solvency ratio for the PCC strategy showing 998%?**

This happens when the provided capital (cell capital) far exceeds the SCR. It indicates the operator is well over-capitalised relative to the retained risk — possibly because the cell is sized to write a larger book than one operator's losses alone. Consider whether the cell will write third-party risks (other operators) to put that capital to work, or whether the capital contribution can be reduced once the cell establishes a track record. The report interpretation text will note this as a surplus capital situation.

---

**Q: Can I use this tool for species other than salmon?**

Yes. The loss model is species-agnostic — it works from the statistical parameters you provide. Update the `species` field in each site and calibrate `expected_annual_events`, `mean_loss_severity`, and `cv_loss_severity` to reflect the loss history and peril profile for that species (e.g. sea bass, sea bream, yellowtail, shrimp).

---

**Q: How do I present this to a board with no insurance background?**

The PDF is designed for exactly this audience. Direct the board to:
1. **Page 1 (Cover)** — the verdict badge summarises the recommendation in one line
2. **Page 2 (Executive Summary)** — the strengths/barriers boxes explain the key drivers
3. **Page 6 (Cumulative Cost Chart)** — shows how costs evolve over time
4. **Page 10 (Radar Chart + Next Steps)** — visual summary and action plan

Avoid presenting the SCR tables or volatility metrics unless board members have risk management backgrounds.

---

## 12. Troubleshooting

**Error: `FileNotFoundError: Input file not found`**

The `--input` path does not exist. Check the path is correct relative to your working directory, or use an absolute path.

```bash
python main.py --input C:/Users/me/clients/operator.json
```

---

**Error: `ValueError: At least one site must be specified`**

The `sites` array is empty in the JSON file. Add at least one site.

---

**Error: `ValueError: Annual premium must be positive`**

The `annual_premium` field in `current_insurance` is zero or negative. Correct this value.

---

**Error: `UnicodeEncodeError: 'charmap' codec...`**

Windows terminal encoding issue. Run with:

```bash
set PYTHONIOENCODING=utf-8
python main.py
```

Or add `encoding="utf-8"` to the terminal's environment settings.

---

**Error: `reportlab.platypus.doctemplate.LayoutError`**

A flowable (table, chart, or text block) is too large to fit in the page frame. This typically occurs if a site table has many columns or a single cell contains very long text. Shorten field values or contact the development team.

---

**Chart quality looks low / blurry in the PDF**

The default chart resolution is 150 dpi. For print-quality output, increase the `dpi` parameter in `reporting/chart_generator.py` from `150` to `300`. This will increase PDF size and rendering time.

---

**The PDF opens but some pages are blank**

This can occur if a chart fails to render. Check the console output for any matplotlib warnings during the "Rendering charts" step. Ensure all dependencies are correctly installed (`pip install -r requirements.txt`).

---

## 13. Methodology & Assumptions Reference

### Loss Model

| Item | Detail |
|------|--------|
| Frequency distribution | Poisson(λ) where λ = `expected_annual_events` |
| Severity distribution | LogNormal(μ, σ) parameterised from (mean, CV) |
| CAT overlay | Independent Bernoulli(p_cat) trigger; severity LogNormal with mean = multiplier × base mean |
| Simulation years | 5 (configurable) |
| Independence assumption | Annual losses are independent across years (no multi-year dependency modelled) |

### Strategy Pricing

| Assumption | Value | Source |
|-----------|-------|--------|
| PCC setup cost | $120,000 | Market estimate, Guernsey/Cayman domicile |
| PCC annual cell fee | $45,000 | Market estimate, standalone cell |
| PCC fronting fee | 3.0% of ceded premium | Market standard range 2–4% |
| PCC premium discount | 22% vs. market | Conservative market assumption |
| Hybrid discount | 30% on retained layer | Actuarial estimate |
| Self-insurance reserve | 1.5× expected annual loss | Prudent minimum; floor at VaR 99% |

### SCR Framework

| Item | Detail |
|------|--------|
| Confidence level | 99.5% VaR (Solvency II standard) |
| Time horizon | 1 year |
| Best Estimate Liability | E[net annual loss] |
| Prudence load | 10% added to BEL |
| Risk Margin method | Cost-of-Capital (6%) applied to SCR over 5-year run-off annuity |
| Discount rate | Risk-free rate = 4.0% p.a. |

### Suitability Scoring

| Criterion | Weight | Key metric |
|-----------|--------|-----------|
| Premium Volume | 25% | Annual premium vs. thresholds ($500k floor, $1M ideal, $2M+ optimal) |
| Loss Stability | 20% | Simulated loss CV |
| Balance Sheet Strength | 20% | Required capital as % of net equity and FCF |
| Cost Savings Potential | 20% | PCC 5-yr savings % vs. Full Insurance |
| Operational Readiness | 15% | Composite of 5 sub-factors (governance, commitment, FCF, risk manager, track record) |

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **Aggregate Deductible** | Maximum total deductible exposure per policy year across all events |
| **BEL (Best Estimate Liability)** | Expected present value of future claims — the central estimate without prudence margin |
| **Captive** | An insurance company wholly owned by one or more non-insurance businesses to insure the risks of those businesses |
| **CAT Event** | Catastrophic loss event modelled as a separate tail-risk overlay |
| **Cell** | A ring-fenced portion of a Protected Cell Company; the cell's assets and liabilities are legally separate from other cells |
| **Compound Poisson** | A loss model where the number of events is Poisson-distributed and the total loss is the sum of independently distributed event severities |
| **Cost of Capital (CoC)** | The minimum rate of return required on capital held for regulatory purposes (6% under Solvency II) |
| **CV (Coefficient of Variation)** | Standard deviation divided by mean; a normalised measure of variability |
| **Fronting Insurer** | A licensed insurer that issues the policy on behalf of a captive that may not be licensed in the risk's jurisdiction |
| **LogNormal Distribution** | A distribution where the natural logarithm of the variable is normally distributed; commonly used for insurance severity due to its positive skew |
| **PCC (Protected Cell Company)** | A statutory corporate structure that allows a single legal entity to maintain legally separate "cells," each with its own assets and liabilities |
| **Premium Discount** | The reduction in premium achieved by writing risks to a captive cell rather than to the external market |
| **Risk Margin** | An additional reserve above the BEL intended to compensate for the uncertainty in the BEL estimate |
| **SCR (Solvency Capital Requirement)** | The amount of capital an insurer must hold to remain solvent with 99.5% confidence over 1 year (Solvency II definition) |
| **Technical Provisions** | Total insurance reserves = BEL + Risk Margin |
| **TIV (Total Insured Value)** | The maximum amount payable by insurers in the event of a total loss across all insured assets |
| **TCOR (Total Cost of Risk)** | All-in cost of managing risk in a given year: premiums + retained losses + admin + capital costs − investment income |
| **TVaR / CVaR** | Tail Value-at-Risk / Conditional Value-at-Risk: the average loss in scenarios that exceed the VaR threshold (also called Expected Shortfall) |
| **VaR (Value at Risk)** | The loss level exceeded with probability (1 − confidence level). VaR 99.5% is the loss exceeded in 0.5% of scenarios (1-in-200 year event) |
| **Working Layer** | The layer of losses between the deductible and the XS trigger point, typically where attritional (frequent, moderate) losses fall |
| **XS / Excess of Loss** | A reinsurance structure where the reinsurer pays losses above a defined retention point up to a defined limit |

---

*This manual is issued for internal use by the operator and their authorised advisers. It should be read alongside the PDF report generated by the tool and any supplementary actuarial or legal opinion obtained in connection with captive formation. Shield Risk Consulting accepts no liability for decisions made solely on the basis of this tool's outputs.*

*PCC Feasibility & Suitability Tool — Version 1.0 — March 2026*
