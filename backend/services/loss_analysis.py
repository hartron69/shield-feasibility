"""
Loss Analysis Service — per-site and per-domain loss attribution for the
Tapsanalyse tab.

Method
------
Per-site EAL
    Exact: drawn directly from SimulationResults.site_loss_distribution, which
    is populated by MonteCarloEngine._distribute_to_sites_rng().  Each site
    receives a (N, T) loss array.  EAL = array.mean().

Per-site VaR95
    Exact (given site distribution): np.percentile(site_annual_losses, 95)
    where site_annual_losses = site_arr.mean(axis=1).

Per-site SCR contribution
    Approximation: total portfolio SCR is allocated to sites proportionally
    to each site's 99.5th-percentile annual loss.  This is the "VaR
    contribution" method — transparent, additive, and conservative.

    Limitation: due to diversification the sum of individual site VaR99.5 is
    greater than the portfolio VaR99.5, so each site's allocated SCR will be
    less than its standalone SCR.

Per-site domain breakdown
    Approximation: portfolio domain EALs (from DomainLossBreakdown) are
    allocated to each site proportionally to that site's loss share.  This
    assumes all sites have the same domain mix, which is a simplification.
    Operators with highly differentiated sites (e.g. one open-coast + one
    sheltered) may see inaccurate per-site domain profiles in this first
    version.

Top risk drivers
    Exact portfolio-level: derived from DomainLossBreakdown.all_subtypes()
    sorted by mean annual loss.

Mitigated block
    When mitigated_annual_losses is a (N, T) array (from MitigationAnalyzer),
    per-site losses are scaled proportionally by (mit_eal / baseline_eal).
    This preserves site ranking.  The per-domain mitigated breakdown is derived
    from the comparison block's top_benefit_domains list if available.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Method note (shown in GUI)
# ─────────────────────────────────────────────────────────────────────────────

_METHOD_NOTE = (
    "Per-anlegg EAL er eksakt (Monte Carlo-fordelt via TIV-vektet Gaussian copula). "
    "SCR-bidrag er estimert som proporsjonal andel av totalt portefølje-SCR basert på "
    "hvert anleggs 99.5%-persentil. Domenefordeling per anlegg er en proporsjonell "
    "approksimering (alle anlegg får samme domenemix vektet av anleggets tapsbidrag). "
    "Mitigert per-anlegg tap er skalert proporsjonalt fra baseline."
)


def _site_annual_losses(arr: np.ndarray) -> np.ndarray:
    """Return mean-over-years annual losses, shape (N,)."""
    if arr.ndim == 2:
        return arr.mean(axis=1)
    return arr.flatten()


def compute_loss_analysis(
    sim: Any,
    op: Any,
    total_scr: float,
    mit_losses_1d: Optional[np.ndarray] = None,
    mit_e_loss: Optional[float] = None,
    mit_scr: Optional[float] = None,
) -> Dict:
    """
    Build the loss_analysis payload for FeasibilityResponse.

    Parameters
    ----------
    sim : SimulationResults
    op : OperatorInput (sea) or SmoltOperatorInput (smolt)
    total_scr : float
        Portfolio SCR (NOK) — used for proportional site allocation.
    mit_losses_1d : np.ndarray, optional
        Shape (N,) mitigated annual losses already available from mitigation
        step.  If provided, mitigated block is built.
    mit_e_loss : float, optional
        Expected annual loss after mitigation (for delta computation).
    mit_scr : float, optional
        SCR after mitigation.

    Returns
    -------
    dict — structure matching LossAnalysisBlock schema.
    """
    site_dist: Optional[Dict[str, np.ndarray]] = getattr(sim, "site_loss_distribution", None)
    dld = getattr(sim, "domain_loss_breakdown", None)

    # ── Per-site loss stats ───────────────────────────────────────────────────
    per_site = []
    site_eal_map: Dict[str, float] = {}
    site_var99_map: Dict[str, float] = {}

    if site_dist:
        for site_name, arr in site_dist.items():
            annual = _site_annual_losses(arr)
            eal  = float(annual.mean())
            var95 = float(np.percentile(annual, 95))
            var99 = float(np.percentile(annual, 99.5))
            site_eal_map[site_name]  = eal
            site_var99_map[site_name] = var99
            per_site.append({
                "site_id":   site_name,
                "site_name": site_name,
                "_eal": eal,
                "_var95": var95,
                "_var99": var99,
            })

    # ── Per-domain portfolio EAL ──────────────────────────────────────────────
    per_domain: Dict[str, float] = {}
    per_domain_subtype: Dict[str, float] = {}
    if dld is not None:
        try:
            dom_totals = dld.domain_totals()
            per_domain = {d: float(arr.mean()) for d, arr in dom_totals.items() if arr.size > 0}
        except Exception:
            pass
        try:
            all_sub = dld.all_subtypes() if hasattr(dld, "all_subtypes") else {}
            per_domain_subtype = {k: float(arr.mean()) for k, arr in all_sub.items() if arr.size > 0}
        except Exception:
            pass

    # ── Distribute domain breakdown to sites (proportional approximation) ────
    total_eal = sum(site_eal_map.values()) or max(float(sim.mean_annual_loss), 1.0)
    domain_list = list(per_domain.keys())

    for entry in per_site:
        sname = entry["site_id"]
        loss_share = site_eal_map.get(sname, 0.0) / total_eal if total_eal > 0 else 0.0
        dom_breakdown = {d: round(per_domain[d] * loss_share, 0) for d in domain_list}
        dominant = max(dom_breakdown, key=lambda d: dom_breakdown[d]) if dom_breakdown else "biological"
        entry["domain_breakdown"] = dom_breakdown
        entry["dominant_domain"]  = dominant

    # ── SCR allocation (proportional tail method) ─────────────────────────────
    total_var99 = sum(site_var99_map.values()) or 1.0
    for entry in per_site:
        sname = entry["site_id"]
        scr_share = site_var99_map.get(sname, 0.0) / total_var99
        entry["scr_contribution_nok"] = round(total_scr * scr_share, 0)
        entry["scr_share_pct"]        = round(scr_share * 100, 1)

    # ── Clean up internal keys; build final per_site list ────────────────────
    final_per_site = []
    for entry in sorted(per_site, key=lambda x: x["_eal"], reverse=True):
        final_per_site.append({
            "site_id":               entry["site_id"],
            "site_name":             entry["site_name"],
            "expected_annual_loss_nok": round(entry["_eal"], 0),
            "var95_nok":             round(entry["_var95"], 0),
            "scr_contribution_nok":  entry["scr_contribution_nok"],
            "scr_share_pct":         entry["scr_share_pct"],
            "dominant_domain":       entry["dominant_domain"],
            "domain_breakdown":      {k: round(v, 0) for k, v in entry["domain_breakdown"].items()},
        })

    # ── Top risk drivers (portfolio-level, exact) ─────────────────────────────
    top_drivers = []
    if per_domain_subtype:
        sorted_sub = sorted(per_domain_subtype.items(), key=lambda x: x[1], reverse=True)
        _DOMAIN_MAP = {
            "hab": "biological", "lice": "biological", "jellyfish": "biological",
            "pathogen": "biological", "biosecurity": "biological",
            "mooring_failure": "structural", "net_integrity": "structural",
            "cage_structural": "structural", "deformation": "structural",
            "anchor_deterioration": "structural",
            "oxygen_stress": "environmental", "temperature_extreme": "environmental",
            "current_storm": "environmental", "ice": "environmental",
            "exposure_anomaly": "environmental",
            "human_error": "operational", "procedure_failure": "operational",
            "equipment_failure": "operational", "incident": "operational",
            "maintenance_backlog": "operational",
            # smolt subtypes
            "biofilter_failure": "biological", "oxygen_depletion": "environmental",
            "power_failure": "operational", "water_quality": "environmental",
        }
        _LABELS = {
            "hab": "HAB (algeoppblomstring)", "lice": "Lakselus",
            "jellyfish": "Manet-invasjon", "pathogen": "Sykdomsutbrudd",
            "biosecurity": "Biosikkerhet",
            "mooring_failure": "Fortøyningssvikt", "net_integrity": "Not-integritet",
            "cage_structural": "Merdestruktur", "deformation": "Deformasjon",
            "anchor_deterioration": "Anker-svekkelse",
            "oxygen_stress": "Oksygenstress", "temperature_extreme": "Temperaturekstrem",
            "current_storm": "Strøm/storm", "ice": "Is-hendelse",
            "exposure_anomaly": "Eksponeringsanomal",
            "human_error": "Menneskelig feil", "procedure_failure": "Prosedyresvikt",
            "equipment_failure": "Utstyrsvikt", "incident": "Hendelse",
            "maintenance_backlog": "Vedlikeholdsefterslep",
            "biofilter_failure": "Biofilterfeil", "oxygen_depletion": "Oksygensvikt",
            "power_failure": "Strømsfall", "water_quality": "Vannkvalitet",
        }
        portfolio_total = sum(per_domain_subtype.values()) or 1.0
        for sub, eal in sorted_sub[:10]:
            top_drivers.append({
                "label":      _LABELS.get(sub, sub.replace("_", " ").title()),
                "risk_type":  sub,
                "domain":     _DOMAIN_MAP.get(sub, "operational"),
                "impact_nok": round(eal, 0),
                "impact_share_pct": round(eal / portfolio_total * 100, 1),
            })

    # ── Mitigated block ───────────────────────────────────────────────────────
    mitigated_block = None
    if mit_losses_1d is not None and mit_e_loss is not None:
        scale = mit_e_loss / total_eal if total_eal > 0 else 1.0
        mit_per_site = []
        for s in final_per_site:
            mit_eal = round(s["expected_annual_loss_nok"] * scale, 0)
            mit_per_site.append({
                "site_id":   s["site_id"],
                "site_name": s["site_name"],
                "expected_annual_loss_nok": mit_eal,
                "dominant_domain":         s["dominant_domain"],
                "domain_breakdown": {
                    d: round(v * scale, 0) for d, v in s["domain_breakdown"].items()
                },
            })
        mit_per_domain = {d: round(v * scale, 0) for d, v in per_domain.items()}
        mitigated_block = {
            "per_site":          mit_per_site,
            "per_domain":        mit_per_domain,
            "delta_total_eal_nok": round((mit_e_loss or 0.0) - total_eal, 0),
            "delta_total_scr_nok": round((mit_scr or 0.0) - total_scr, 0),
        }

    return {
        "per_site":   final_per_site,
        "per_domain": {k: round(v, 0) for k, v in per_domain.items()},
        "top_drivers": top_drivers,
        "mitigated":   mitigated_block,
        "method_note": _METHOD_NOTE,
    }
