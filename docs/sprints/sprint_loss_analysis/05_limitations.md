# Known Limitations — Tapsanalyse Sprint

## Approximations

### Per-site domain breakdown
All sites receive the same domain composition (portfolio mix × site loss share).
Real per-site domain distributions depend on site-specific risk parameters (fjord
exposure, lice pressure factor, mooring age, etc.) that are not yet available in a
per-site format at the simulation stage.

**Future improvement:** Run separate DomainLossBreakdown per site using each site's
risk parameter set, or extend MonteCarloEngine to generate site-level domain arrays.

### Mitigated per-site losses
The mitigated site breakdown uses proportional scaling: `mit_site_eal = base_site_eal × (mit_total_eal / base_total_eal)`.
This preserves site ranking and relative shares but does not capture which sites
benefit more from specific mitigation actions (e.g. biological actions help
high-lice-risk sites more than structural mitigations).

**Future improvement:** Apply MitigationAnalyzer at the site level using per-site
DomainLossBreakdown.

### SCR Allocation
The VaR-contribution method allocates total portfolio SCR proportionally to each
site's 99.5th percentile standalone loss. This overstates site-level SCR (sum > portfolio
SCR due to diversification) but is corrected by normalisation. The method is
transparent and auditable but not the Euler contribution method.

## Data Availability

### Sea-site example operator (3 sites)
`sim.site_loss_distribution` is always populated because `MonteCarloEngine` calls
`_distribute_to_sites_rng()` for any operator with > 0 sites.

### Smolt operators
Per-facility distributions work the same way if `SmoltOperatorInput` is converted to an
`OperatorInput` with one `SiteProfile` per facility. If smolt facilities map to a single
aggregated site, `per_site` will contain one row.

## What is NOT shown yet

- **Time-series view**: loss trend over the 5-year projection horizon per site
- **Stress scenarios**: per-site loss under domain-specific stress
- **Confidence intervals**: EAL ± σ per site
- **Exact site-domain decomposition**: requires per-site DomainLossBreakdown
