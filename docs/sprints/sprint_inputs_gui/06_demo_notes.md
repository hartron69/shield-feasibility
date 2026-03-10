# Sprint – Inputs GUI: Demo Notes

## Quick Demo Script

### Start
```bash
cd frontend && npm run dev
# Open http://localhost:5173
```

### 1. Overview page (default landing)
The app opens on the **Overview** page. Point out:
- 5 KPI cards: Risk Score 62, 2 Critical Alerts, 73% input completeness, NOK 22.7M E[annual loss], Learning WARMING
- Click "View all alerts" → jumps to Alerts page
- Click "View full inputs" → jumps to Inputs page

### 2. Inputs → Site Profile
Click **Inputs** in the nav.
- 3 cards: Frohavet North, Sunndalsfjord, Storfjorden South
- Point out: Frohavet North has exposure_factor=1.40 (open coast), Storfjorden South=0.85 (sheltered)
- Source badges all say "Simulated"

### 3. Inputs → Biological Inputs
Click **Biological Inputs** tab.
- Select Frohavet North: surface temp 15.2°C (baseline 13.0°C) → red delta +2.20
- Dissolved oxygen 6.8 mg/L (baseline 8.5) → shown as adverse (red)
- Switch to Storfjorden South: most readings at or below baseline → green/neutral deltas

### 4. Inputs → Alert Signals
Click **Alert Signals** tab.
- 12 signals shown. Click "Triggered only" → 11 signals remain.
- Filter to "jellyfish" → 2 signals at Frohavet North, both triggered

### 5. Inputs → Data Quality
Click **Data Quality** tab.
- Jellyfish consistently shows POOR across all 3 sites (missing current_data, bloom_index)
- Lice is SUFFICIENT (highest completeness ~88–90%)

### 6. Inputs → Scenario Inputs
Click **Scenario Inputs** tab.
- Click "Warm Summer" preset → oxygen drops to 6.5, nitrate rises to 14.0, lice pressure to 1.5
- Click "Run Scenario" → shows estimated scale factor ~1.20× (+20% annual loss)
- Click "Reset to Baseline" → all values restored

### 7. Strategy Comparison
Click **Strategy Comparison** in nav.
- PCC Captive (RECOMMENDED) vs Full Insurance (BASELINE) vs Mutual Pooling (ALTERNATIVE)
- NOK 64M vs NOK 97M vs NOK 74M illustrative 5yr TCOR

### 8. Learning
Click **Learning** in nav.
- Context banner: "Training source: Simulated data. Portfolio input completeness: 73%."
- Brier score history table shows lice improving fastest (0.268 → 0.033)

### 9. PCC Feasibility (existing)
Click **PCC Feasibility** → left accordion panel reappears.
- Load example, run analysis — all existing functionality unchanged.

## Key Talking Points
- All new pages are **additive** — zero breakage to existing Feasibility flow
- Mock data is **internally consistent** with C5AI_MOCK and MOCK_ALERTS
- Scenario tab is a **UI-complete stub** — backend wiring is next sprint
- Data quality shows **why jellyfish risk confidence is low** (missing bloom index / current data)
