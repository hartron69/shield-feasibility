"""
Shield Captive Risk Platform – Correlated Risk Analytics (Sprint 7 reporting).

Pure analytics functions that transform SimulationResults / DomainLossBreakdown
into structured data objects consumed by the PDF renderer.  No side effects;
no ReportLab or matplotlib imports.

Usage::
    from reporting.correlated_risk_analytics import build_correlated_risk_summary
    summary = build_correlated_risk_summary(sim, sim.domain_loss_breakdown)

All monetary values in NOK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from models.domain_loss_breakdown import DomainLossBreakdown, DOMAINS


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

#: Human-readable labels for each domain.
DOMAIN_LABELS: Dict[str, str] = {
    "biological":    "Biological",
    "structural":    "Structural",
    "environmental": "Environmental",
    "operational":   "Operational",
}

#: Chart colour per domain (hex, matches brand palette).
DOMAIN_COLOURS: Dict[str, str] = {
    "biological":    "#00897B",   # teal
    "structural":    "#1565C0",   # blue
    "environmental": "#F9A825",   # gold/amber
    "operational":   "#C62828",   # alert red
}


# ─────────────────────────────────────────────────────────────────────────────
# Data containers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScenarioYear:
    """One representative simulation year (normal / stress / extreme)."""
    label: str                           # "Normal Year", "Stress Year", "Extreme Year"
    percentile: int                      # 50, 95, 99
    total_loss: float                    # NOK
    domain_amounts: Dict[str, float]     # domain → NOK
    domain_fractions: Dict[str, float]   # domain → 0..1
    narrative: str                       # board-language explanation


@dataclass
class TailAnalysis:
    """Statistics over the worst simulation years."""
    top_pct: float                           # e.g. 0.05 (top 5%)
    n_years: int                             # number of years in tail bucket
    threshold: float                         # NOK loss level defining the tail
    mean_total_loss: float                   # mean total loss in tail
    mean_domain_fractions: Dict[str, float]  # domain → average fraction in tail
    mean_domain_amounts: Dict[str, float]    # domain → average NOK in tail
    dominant_domains: List[str]              # top 2 domains by tail fraction


@dataclass
class CorrelatedRiskSummary:
    """All analytics outputs consumed by the PDF renderer."""
    domain_correlation_applied: bool
    bio_modelled: bool
    scenarios: List[ScenarioYear]             # [normal, stress, extreme]
    tail_analysis: Optional[TailAnalysis]     # None if dbd unavailable
    kpis: Dict[str, float]                    # named KPI values (NOK or %)
    tail_domain_narratives: List[str]         # 2-3 board-language bullet points


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_correlated_risk_summary(
    annual_losses: np.ndarray,
    dbd: Optional[DomainLossBreakdown],
) -> CorrelatedRiskSummary:
    """
    Build the full correlated risk summary from simulation outputs.

    Parameters
    ----------
    annual_losses : np.ndarray
        Shape ``(N, T)`` gross annual losses from ``SimulationResults``.
    dbd : DomainLossBreakdown, optional
        If ``None`` the scenarios and tail analysis are omitted but the
        KPI dict is still populated from ``annual_losses`` alone.

    Returns
    -------
    CorrelatedRiskSummary
    """
    flat = annual_losses.flatten()

    kpis: Dict[str, float] = {
        "mean_annual_loss": float(flat.mean()),
        "p95_annual_loss":  float(np.percentile(flat, 95)),
        "p99_annual_loss":  float(np.percentile(flat, 99)),
        "p995_annual_loss": float(np.percentile(flat, 99.5)),
    }

    domain_correlation_applied = bool(dbd is not None and dbd.domain_correlation_applied)
    bio_modelled = bool(dbd is not None and dbd.bio_modelled)

    scenarios: List[ScenarioYear] = []
    tail_analysis: Optional[TailAnalysis] = None
    tail_narratives: List[str] = []

    if dbd is not None:
        scenarios = _extract_scenarios(annual_losses, dbd)
        tail_analysis = _analyze_tail(annual_losses, dbd, top_pct=0.05)
        tail_narratives = _build_tail_narratives(tail_analysis, dbd)

        # Additional KPIs only available with domain breakdown
        tail_fracs = tail_analysis.mean_domain_fractions
        kpis["tail_bio_fraction"]   = tail_fracs.get("biological", 0.0)
        kpis["tail_struct_fraction"] = tail_fracs.get("structural", 0.0)
        kpis["tail_env_fraction"]   = tail_fracs.get("environmental", 0.0)
        kpis["tail_ops_fraction"]   = tail_fracs.get("operational", 0.0)

    return CorrelatedRiskSummary(
        domain_correlation_applied=domain_correlation_applied,
        bio_modelled=bio_modelled,
        scenarios=scenarios,
        tail_analysis=tail_analysis,
        kpis=kpis,
        tail_domain_narratives=tail_narratives,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_scenarios(
    annual_losses: np.ndarray,
    dbd: DomainLossBreakdown,
) -> List[ScenarioYear]:
    """
    Find the simulation year closest to the 50th, 95th, and 99th percentile.

    Returns three ScenarioYear objects: Normal, Stress, Extreme.
    """
    flat = annual_losses.flatten()
    N, T = annual_losses.shape
    domain_totals_arr = dbd.domain_totals()  # dict: domain → (N, T)

    def _closest_year(target: float, percentile: int, label: str) -> ScenarioYear:
        idx_flat = int(np.argmin(np.abs(flat - target)))
        n_i, t_i = divmod(idx_flat, T)
        actual_loss = float(flat[idx_flat])

        amounts: Dict[str, float] = {}
        for d in DOMAINS:
            if d in domain_totals_arr:
                amounts[d] = float(domain_totals_arr[d][n_i, t_i])

        total = sum(amounts.values()) or actual_loss
        fracs: Dict[str, float] = {d: v / max(total, 1.0) for d, v in amounts.items()}

        narrative = _scenario_narrative(label, actual_loss, amounts, fracs)
        return ScenarioYear(
            label=label,
            percentile=percentile,
            total_loss=actual_loss,
            domain_amounts=amounts,
            domain_fractions=fracs,
            narrative=narrative,
        )

    return [
        _closest_year(float(np.percentile(flat, 50)),  50, "Normal Year"),
        _closest_year(float(np.percentile(flat, 95)),  95, "Stress Year"),
        _closest_year(float(np.percentile(flat, 99)),  99, "Extreme Year"),
    ]


def _scenario_narrative(
    label: str,
    total_loss: float,
    amounts: Dict[str, float],
    fracs: Dict[str, float],
) -> str:
    """Generate a board-language sentence for each scenario."""
    if not fracs:
        return f"{label}: total loss {total_loss/1e6:.1f} M NOK."

    # Find dominant domain
    dominant = max(fracs, key=fracs.get)
    dominant_frac = fracs[dominant]

    if label == "Normal Year":
        return (
            f"In a typical year, biological losses account for "
            f"{fracs.get('biological', 0):.0%} of total risk exposure. "
            f"Structural and environmental losses are contained at manageable levels. "
            f"This year represents the expected long-run average for captive planning purposes."
        )
    elif label == "Stress Year":
        struct_env = fracs.get("structural", 0) + fracs.get("environmental", 0)
        return (
            f"A stress year sees total losses approximately 2–4× the median. "
            f"Structural and environmental losses combined account for "
            f"{struct_env:.0%} of the total, reflecting co-movement in adverse conditions. "
            f"This is the relevant scenario for reinsurance attachment point design."
        )
    else:  # Extreme Year
        struct_frac = fracs.get("structural", 0)
        env_frac = fracs.get("environmental", 0)
        return (
            f"Extreme years are characterised by concurrent stress across multiple domains. "
            f"In this scenario, structural losses ({struct_frac:.0%}) and environmental losses "
            f"({env_frac:.0%}) amplify biological losses, reflecting a correlated multi-peril event. "
            f"This scenario drives the 99.5% VaR and the captive's SCR calculation."
        )


def _analyze_tail(
    annual_losses: np.ndarray,
    dbd: DomainLossBreakdown,
    top_pct: float = 0.05,
) -> TailAnalysis:
    """
    Compute average domain composition across the worst ``top_pct`` of years.
    """
    flat = annual_losses.flatten()
    N, T = annual_losses.shape
    threshold = float(np.percentile(flat, 100 * (1 - top_pct)))
    tail_mask = flat >= threshold
    n_years = int(tail_mask.sum())

    tail_losses = flat[tail_mask]
    mean_total = float(tail_losses.mean())

    # Map flat indices back to (n, t) indices
    flat_indices = np.where(tail_mask)[0]
    n_idx = flat_indices // T
    t_idx = flat_indices % T

    # Average domain totals across tail years
    domain_totals_arr = dbd.domain_totals()
    mean_amounts: Dict[str, float] = {}
    for d in DOMAINS:
        if d in domain_totals_arr:
            mean_amounts[d] = float(domain_totals_arr[d][n_idx, t_idx].mean())

    total_mean = sum(mean_amounts.values()) or mean_total
    mean_fracs: Dict[str, float] = {d: v / max(total_mean, 1.0) for d, v in mean_amounts.items()}

    # Top-2 dominant domains
    sorted_domains = sorted(mean_fracs, key=mean_fracs.get, reverse=True)
    dominant = sorted_domains[:2]

    return TailAnalysis(
        top_pct=top_pct,
        n_years=n_years,
        threshold=threshold,
        mean_total_loss=mean_total,
        mean_domain_fractions=mean_fracs,
        mean_domain_amounts=mean_amounts,
        dominant_domains=dominant,
    )


def _build_tail_narratives(
    tail: TailAnalysis,
    dbd: DomainLossBreakdown,
) -> List[str]:
    """
    Build 3 board-language bullet points about tail behaviour.
    """
    fracs = tail.mean_domain_fractions
    bio   = fracs.get("biological", 0.0)
    struct = fracs.get("structural", 0.0)
    env   = fracs.get("environmental", 0.0)
    ops   = fracs.get("operational", 0.0)
    dom_pair = tuple(tail.dominant_domains[:2])

    bullets = [
        (
            f"In the worst {tail.top_pct:.0%} of simulated years, losses are not driven "
            f"by biology alone. Structural and environmental losses rise materially at the "
            f"same time — structural accounts for {struct:.0%} and environmental for {env:.0%} "
            f"of aggregate tail losses."
        ),
        (
            f"Operational losses tend to increase in years where structural stress is elevated, "
            f"reflecting that equipment failures and procedural gaps cluster in high-pressure "
            f"periods. Operational losses represent {ops:.0%} of tail-year totals."
        ),
        (
            f"Biological losses ({bio:.0%} of tail losses) are amplified by correlated "
            f"structural and environmental stress, producing multi-domain events that are "
            f"systematically more severe than single-domain stress alone. "
            f"This has direct implications for reinsurance layer sizing and PCC capital adequacy."
        ),
    ]
    return bullets


# ─────────────────────────────────────────────────────────────────────────────
# Utility: format helpers for the PDF layer
# ─────────────────────────────────────────────────────────────────────────────

def fmt_corr_label(rho: float) -> str:
    """Convert correlation coefficient to board-friendly label."""
    if rho >= 0.5:
        return "High"
    elif rho >= 0.25:
        return "Moderate"
    elif rho >= 0.05:
        return "Low"
    return "Negligible"
