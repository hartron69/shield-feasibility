# Architecture — Tapsanalyse Loss Analysis

## Data Flow

```
MonteCarloEngine.run()
  └─ _distribute_to_sites_rng()
       └─ sim.site_loss_distribution: Dict[site_name, np.ndarray (N,T)]

SimulationResults
  ├─ annual_losses (N,T) — portfolio
  ├─ site_loss_distribution (Dict) — per site
  └─ domain_loss_breakdown — DomainLossBreakdown

backend/services/loss_analysis.py :: compute_loss_analysis()
  ├─ Per-site EAL, VaR95, VaR99.5
  ├─ SCR allocation (proportional tail method)
  ├─ Domain breakdown per site (proportional approximation)
  ├─ Top risk drivers (from all_subtypes())
  └─ Mitigated block (proportional scaling)

backend/schemas.py :: LossAnalysisBlock
  ├─ per_site: List[LossAnalysisSite]
  ├─ per_domain: Dict[str, float]
  ├─ top_drivers: List[LossAnalysisDriver]
  ├─ mitigated: Optional[LossAnalysisMitigated]
  └─ method_note: str

FeasibilityResponse.loss_analysis: Optional[LossAnalysisBlock]  (new field, backward-compatible)

run_analysis.py (both sea + smolt paths)
  └─ compute_loss_analysis() → LossAnalysisBlock → FeasibilityResponse.loss_analysis

ResultPanel.jsx
  └─ Tapsanalyse tab → SeaSiteLossTable(lossAnalysis=result.loss_analysis)

SeaSiteLossTable.jsx (full rewrite)
  ├─ KPI row
  ├─ Domain bar
  ├─ Per-site table (expandable)
  ├─ Top drivers table
  └─ Method note
```

## Site Distribution Keys

Keys in `sim.site_loss_distribution` are **site names** (strings) from `SiteProfile.name` for sea operators and facility names for smolt.

The MonteCarloEngine uses TIV-weighted Gaussian copula allocation:
- Base weights = TIV per site / total TIV
- Perturbed with Gaussian copula noise (amplitude 1.0)
- Normalised to preserve portfolio totals exactly

## SCR Allocation Method

```
site_var99 = np.percentile(site_annual_losses, 99.5)
scr_share  = site_var99 / sum(all site_var99)
scr_alloc  = total_portfolio_scr × scr_share
```

Limitation: sum of site VaR99.5 > portfolio VaR99.5 (diversification). Each site's
allocated SCR is therefore less than its standalone SCR. The method is conservative
and additive.

## Domain Breakdown Per Site (Approximation)

```
portfolio_domain_eal = {d: arr.mean() for d in domains}
site_loss_share      = site_eal / portfolio_eal
site_domain_eal[d]   = portfolio_domain_eal[d] × site_loss_share
```

All sites receive the same domain mix proportional to their loss share.
Limitation: sites with different exposure profiles (e.g. open coast vs. sheltered)
likely have different domain distributions in reality.
