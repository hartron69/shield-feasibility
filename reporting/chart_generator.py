"""
Chart Generator – Professional matplotlib visualisations for the PDF report.

All charts are rendered into BytesIO buffers (PNG, 150 dpi) so that
ReportLab can embed them without touching the filesystem.
"""

from __future__ import annotations

import io
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")   # non-interactive backend – safe for server / report use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import matplotlib.ticker as mticker
import seaborn as sns

from models.monte_carlo import SimulationResults
from models.strategies.base_strategy import StrategyResult
from analysis.scr_calculator import SCRResult
from analysis.cost_analyzer import CostAnalysis
from analysis.volatility_metrics import VolatilityAnalysis
from analysis.suitability_engine import Recommendation
from config.settings import SETTINGS
from reporting.correlated_risk_analytics import (
    CorrelatedRiskSummary, ScenarioYear, TailAnalysis,
    DOMAIN_COLOURS, DOMAIN_LABELS,
)

# ── Colour palette ─────────────────────────────────────────────────────────────
NAVY  = tuple(SETTINGS.brand_navy)
TEAL  = tuple(SETTINGS.brand_teal)
GOLD  = tuple(SETTINGS.brand_gold)
LGREY = tuple(SETTINGS.brand_light_grey)
DGREY = tuple(SETTINGS.brand_dark_grey)

STRATEGY_COLOURS = {
    "Full Insurance":    "#1565C0",   # strong blue
    "Hybrid":            "#00897B",   # teal-green
    "PCC Captive Cell":  "#F9A825",   # gold/amber
    "Self-Insurance":    "#C62828",   # alert red
}

def _buf() -> io.BytesIO:
    return io.BytesIO()

def _fmt_m(x, _=None) -> str:
    """Formater aksetiketter i millioner NOK."""
    if abs(x) >= 1_000_000_000:
        return f"{x/1_000_000_000:.1f} Mrd"
    elif abs(x) >= 1_000_000:
        return f"{x/1_000_000:.0f} M"
    elif abs(x) >= 1_000:
        return f"{x/1_000:.0f}k"
    return f"{x:.0f}"

def _style_ax(ax, title: str, xlabel: str = "", ylabel: str = ""):
    ax.set_title(title, fontsize=11, fontweight="bold", color=NAVY, pad=10)
    ax.set_xlabel(xlabel, fontsize=9, color=DGREY)
    ax.set_ylabel(ylabel, fontsize=9, color=DGREY)
    ax.tick_params(colors=DGREY, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LGREY)
    ax.spines["bottom"].set_color(LGREY)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, alpha=0.6, color=LGREY)
    ax.set_axisbelow(True)


# ─────────────────────────────────────────────────────────────────────────────
# Chart 1 – Loss Distribution (Histogram + VaR markers)
# ─────────────────────────────────────────────────────────────────────────────

def chart_loss_distribution(sim: SimulationResults) -> io.BytesIO:
    flat = sim.annual_losses.flatten()
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.hist(flat, bins=120, color=TEAL, alpha=0.75, edgecolor="white", linewidth=0.3,
            density=True, label="Simulated annual loss")

    for pct, val, label, col in [
        (90,   sim.var_90,  "VaR 90%",   "#F9A825"),
        (95,   sim.var_95,  "VaR 95%",   "#EF6C00"),
        (99.5, sim.var_995, "VaR 99.5%", "#B71C1C"),
    ]:
        ax.axvline(val, color=col, linewidth=1.6, linestyle="--",
                   label=f"{label}: {_fmt_m(val)}")

    ax.axvline(sim.mean_annual_loss, color=NAVY, linewidth=1.8, linestyle="-",
               label=f"Mean: {_fmt_m(sim.mean_annual_loss)}")

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_m))
    _style_ax(ax, "Arlig bruttotapsfordeling  (Monte Carlo-simulering)",
              "Arlig tap (NOK)", "Sannsynlighetstetthet")
    ax.legend(fontsize=8, framealpha=0.85)
    fig.tight_layout()

    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 2 – 5-Year Cumulative Cost Curves
# ─────────────────────────────────────────────────────────────────────────────

def chart_cumulative_costs(cost_analysis: CostAnalysis) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(8, 4))
    years = list(range(1, 6))

    for name, summary in cost_analysis.summaries.items():
        colour = STRATEGY_COLOURS.get(name, "#607D8B")
        lw = 2.4 if name == "PCC Captive Cell" else 1.6
        ax.plot(years, summary.cumulative_costs, marker="o", markersize=5,
                linewidth=lw, color=colour, label=name)

    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_m))
    _style_ax(ax, "5-arig kumulativ total risikokostnad per strategi",
              "Ar", "Kumulativ kostnad (NOK)")
    ax.legend(fontsize=8, framealpha=0.85, loc="upper left")
    fig.tight_layout()

    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 3 – Annual Cost Stack (Grouped Bar)
# ─────────────────────────────────────────────────────────────────────────────

def chart_annual_cost_comparison(strategy_results: Dict[str, StrategyResult]) -> io.BytesIO:
    names = list(strategy_results.keys())
    years = list(range(1, 6))
    n_strategies = len(names)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    bar_width = 0.18
    x = np.arange(len(years))

    for i, name in enumerate(names):
        costs = strategy_results[name].expected_annual_costs
        offset = (i - n_strategies / 2 + 0.5) * bar_width
        colour = STRATEGY_COLOURS.get(name, "#607D8B")
        bars = ax.bar(x + offset, costs, bar_width, label=name, color=colour, alpha=0.88)

    ax.set_xticks(x)
    ax.set_xticklabels([f"Ar {y}" for y in years], fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_m))
    _style_ax(ax, "Forventet arlig netto risikokostnad – strategisammenligning",
              "", "Arlig kostnad (NOK)")
    ax.legend(fontsize=8, framealpha=0.85)
    fig.tight_layout()

    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 4 – SCR Comparison (Horizontal Bar)
# ─────────────────────────────────────────────────────────────────────────────

def chart_scr_comparison(scr_results: Dict[str, SCRResult]) -> io.BytesIO:
    names = list(scr_results.keys())
    scr_vals = [scr_results[n].scr_net for n in names]
    cap_vals = [scr_results[n].required_capital for n in names]
    colours = [STRATEGY_COLOURS.get(n, "#607D8B") for n in names]

    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8, 3.5))

    bars_scr = ax.barh(y - 0.18, scr_vals, 0.34, label="SCR Required", color=colours, alpha=0.85)
    bars_cap = ax.barh(y + 0.18, cap_vals, 0.34, label="Capital Provided",
                       color=colours, alpha=0.40, hatch="//", edgecolor="white")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_m))
    _style_ax(ax, "Solvenskapitalkrav (SCR) vs. stilt kapital",
              "Belop (NOK)", "")
    ax.legend(fontsize=8, framealpha=0.85)
    ax.invert_yaxis()
    fig.tight_layout()

    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 5 – Cost vs. Volatility (Risk-Return Frontier)
# ─────────────────────────────────────────────────────────────────────────────

def chart_risk_return_frontier(
    strategy_results: Dict[str, StrategyResult],
    vol_analysis: VolatilityAnalysis,
) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7, 4.5))

    for name, result in strategy_results.items():
        vol_m = vol_analysis.metrics.get(name)
        if vol_m is None:
            continue
        x = vol_m.std_annual_cost / 1e6       # volatility in $M
        y = result.total_5yr_cost / 5e6        # mean annual cost in $M
        colour = STRATEGY_COLOURS.get(name, "#607D8B")

        ax.scatter(x, y, s=180, color=colour, zorder=5, edgecolors="white", linewidth=1.5)
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(8, 4),
                    fontsize=8, color=colour, fontweight="bold")

    ax.set_xlabel("Arlig kostnadvolatilitet – Std.avvik (M NOK)", fontsize=9, color=DGREY)
    ax.set_ylabel("Forventet arlig kostnad (M NOK)", fontsize=9, color=DGREY)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f} M"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f} M"))

    # Ideal quadrant annotation
    ax.axhline(y=0, color=LGREY, linewidth=0.5)
    ax.annotate("← Lower Cost, Lower Risk →", xy=(0.02, 0.04), xycoords="axes fraction",
                fontsize=7.5, color=DGREY, style="italic")

    _style_ax(ax, "Cost–Risk Frontier: Expected Cost vs. Volatility", "", "")
    fig.tight_layout()

    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 6 – Suitability Radar / Spider Chart
# ─────────────────────────────────────────────────────────────────────────────

def chart_suitability_radar(recommendation: Recommendation) -> io.BytesIO:
    criteria = recommendation.criterion_scores
    labels = [c.name for c in criteria]
    scores = [c.raw_score for c in criteria]

    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    scores_plot = scores + scores[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 5), subplot_kw=dict(polar=True))
    ax.set_facecolor(LGREY)

    # Shaded fill
    ax.fill(angles, scores_plot, color=TEAL, alpha=0.25)
    ax.plot(angles, scores_plot, color=TEAL, linewidth=2.2)

    # Reference circle at 60 (threshold)
    ref = [60] * N + [60]
    ax.plot(angles, ref, color=GOLD, linewidth=1.2, linestyle="--", alpha=0.7, label="Target (60)")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8.5, color=NAVY, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7, color=DGREY)
    ax.tick_params(axis="x", pad=12)

    composite = recommendation.composite_score
    ax.set_title(
        f"PCC Suitability Radar\nComposite Score: {composite:.1f}/100  |  {recommendation.verdict}",
        fontsize=10, fontweight="bold", color=NAVY, pad=22,
    )
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)
    fig.tight_layout()

    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 7 – Simulated Cost Fan (Box & Whisker per Strategy)
# ─────────────────────────────────────────────────────────────────────────────

def chart_cost_box_whisker(strategy_results: Dict[str, StrategyResult]) -> io.BytesIO:
    names = list(strategy_results.keys())
    data = [strategy_results[n].simulated_5yr_costs / 5 for n in names]   # annual avg
    colours = [STRATEGY_COLOURS.get(n, "#607D8B") for n in names]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bp = ax.boxplot(
        data,
        vert=True,
        patch_artist=True,
        notch=False,
        showfliers=True,
        flierprops=dict(marker=".", markersize=2, alpha=0.3),
        medianprops=dict(color="white", linewidth=2),
        whiskerprops=dict(linewidth=1.2),
        capprops=dict(linewidth=1.4),
        boxprops=dict(linewidth=1.2),
    )
    for patch, col in zip(bp["boxes"], colours):
        patch.set_facecolor(col)
        patch.set_alpha(0.80)

    ax.set_xticks(range(1, len(names) + 1))
    ax.set_xticklabels(names, fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_m))
    _style_ax(ax, "Fordeling av annualisert 5-ars risikokostnad  (10 000 simuleringer)",
              "", "Annualisert kostnad (NOK)")
    fig.tight_layout()

    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 8 – Domain Correlation Heatmap (Sprint 7, optional)
# ─────────────────────────────────────────────────────────────────────────────

def chart_domain_correlation_heatmap(domain_corr_matrix) -> io.BytesIO:
    """
    Render a labelled heatmap of the 4×4 domain correlation matrix.

    Parameters
    ----------
    domain_corr_matrix : DomainCorrelationMatrix
        From ``models.domain_correlation``.

    Returns
    -------
    io.BytesIO  PNG buffer.
    """
    mat = domain_corr_matrix.correlation_matrix
    labels = [DOMAIN_LABELS.get(d, d) for d in domain_corr_matrix.domains]

    fig, ax = plt.subplots(figsize=(5.5, 4.5))

    im = ax.imshow(mat, cmap="RdYlGn", vmin=-0.2, vmax=1.0, aspect="auto")
    plt.colorbar(im, ax=ax, shrink=0.75, label="Correlation (ρ)")

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9, color=NAVY)
    ax.set_yticklabels(labels, fontsize=9, color=NAVY)

    # Annotate each cell with value + board label
    for i in range(len(labels)):
        for j in range(len(labels)):
            rho = mat[i, j]
            text_col = "white" if rho > 0.7 or rho < 0.0 else NAVY
            ax.text(
                j, i,
                f"{rho:.2f}",
                ha="center", va="center",
                fontsize=8.5, fontweight="bold",
                color=text_col,
            )

    ax.set_title(
        "Domain Risk Correlation Matrix",
        fontsize=11, fontweight="bold", color=NAVY, pad=10,
    )
    ax.tick_params(axis="both", which="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.tight_layout()
    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 9 – Scenario Domain Stacks: Normal / Stress / Extreme (Sprint 7)
# ─────────────────────────────────────────────────────────────────────────────

def chart_scenario_domain_stacks(scenarios: List[ScenarioYear]) -> io.BytesIO:
    """
    Stacked horizontal bar chart showing domain composition in three
    representative simulation years.

    Parameters
    ----------
    scenarios : List[ScenarioYear]
        Output of ``extract_scenario_years()`` – three entries expected.
    """
    from models.domain_loss_breakdown import DOMAINS

    labels = [s.label for s in scenarios]
    n = len(labels)

    fig, ax = plt.subplots(figsize=(8, 3.5))

    lefts = np.zeros(n)
    for domain in DOMAINS:
        fracs = np.array([s.domain_fractions.get(domain, 0.0) for s in scenarios])
        colour = DOMAIN_COLOURS.get(domain, "#607D8B")
        d_label = DOMAIN_LABELS.get(domain, domain)
        bars = ax.barh(range(n), fracs, left=lefts, color=colour,
                       label=d_label, alpha=0.88, height=0.55)
        # Annotate if fraction > 8%
        for i, (frac, left) in enumerate(zip(fracs, lefts)):
            if frac > 0.08:
                ax.text(
                    left + frac / 2, i,
                    f"{frac:.0%}",
                    ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold",
                )
        lefts += fracs

    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=9, color=NAVY)
    ax.set_xlim(0, 1.0)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
    ax.tick_params(axis="x", labelsize=8)
    ax.set_title(
        "Domain Loss Composition: Normal / Stress / Extreme Year",
        fontsize=11, fontweight="bold", color=NAVY, pad=10,
    )
    ax.legend(loc="lower right", fontsize=8, framealpha=0.85,
              bbox_to_anchor=(1.0, -0.05))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Chart 10 – Tail Domain Composition (Sprint 7)
# ─────────────────────────────────────────────────────────────────────────────

def chart_tail_domain_composition(tail: TailAnalysis) -> io.BytesIO:
    """
    Single horizontal stacked bar comparing overall average vs. tail-year
    domain composition.

    Parameters
    ----------
    tail : TailAnalysis
    """
    from models.domain_loss_breakdown import DOMAINS

    fig, ax = plt.subplots(figsize=(8, 2.2))

    scenarios_fracs = [
        ("All Years (avg)", {d: 1.0 / len(DOMAINS) for d in DOMAINS}),
        (f"Worst {tail.top_pct:.0%} of Years", tail.mean_domain_fractions),
    ]

    n = len(scenarios_fracs)
    lefts = np.zeros(n)

    for domain in DOMAINS:
        fracs = np.array([s[1].get(domain, 0.0) for s in scenarios_fracs])
        colour = DOMAIN_COLOURS.get(domain, "#607D8B")
        d_label = DOMAIN_LABELS.get(domain, domain)
        ax.barh(range(n), fracs, left=lefts, color=colour,
                label=d_label, alpha=0.88, height=0.5)
        for i, (frac, left) in enumerate(zip(fracs, lefts)):
            if frac > 0.08:
                ax.text(
                    left + frac / 2, i,
                    f"{frac:.0%}",
                    ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold",
                )
        lefts += fracs

    ax.set_yticks(range(n))
    ax.set_yticklabels([s[0] for s in scenarios_fracs], fontsize=9, color=NAVY)
    ax.set_xlim(0, 1.0)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
    ax.tick_params(axis="x", labelsize=8)
    ax.set_title(
        f"Domain Mix: Average vs. Worst {tail.top_pct:.0%} of Simulated Years",
        fontsize=10, fontweight="bold", color=NAVY, pad=8,
    )
    ax.legend(loc="lower right", fontsize=8, framealpha=0.85,
              bbox_to_anchor=(1.0, -0.15))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    buf = _buf()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: generate all charts at once
# ─────────────────────────────────────────────────────────────────────────────

def generate_all_charts(
    sim: SimulationResults,
    strategy_results: Dict[str, StrategyResult],
    scr_results: Dict[str, SCRResult],
    cost_analysis: CostAnalysis,
    vol_analysis: VolatilityAnalysis,
    recommendation: Recommendation,
    correlated_risk_summary: Optional["CorrelatedRiskSummary"] = None,
    domain_correlation=None,   # Optional[DomainCorrelationMatrix]
) -> Dict[str, io.BytesIO]:
    charts = {
        "loss_distribution":    chart_loss_distribution(sim),
        "cumulative_costs":     chart_cumulative_costs(cost_analysis),
        "annual_comparison":    chart_annual_cost_comparison(strategy_results),
        "scr_comparison":       chart_scr_comparison(scr_results),
        "risk_return_frontier": chart_risk_return_frontier(strategy_results, vol_analysis),
        "suitability_radar":    chart_suitability_radar(recommendation),
        "cost_box_whisker":     chart_cost_box_whisker(strategy_results),
    }

    # Sprint 7 – optional correlated risk charts
    if domain_correlation is not None:
        charts["domain_corr_heatmap"] = chart_domain_correlation_heatmap(domain_correlation)

    if (correlated_risk_summary is not None
            and correlated_risk_summary.scenarios):
        charts["scenario_domain_stacks"] = chart_scenario_domain_stacks(
            correlated_risk_summary.scenarios
        )

    if (correlated_risk_summary is not None
            and correlated_risk_summary.tail_analysis is not None):
        charts["tail_domain_composition"] = chart_tail_domain_composition(
            correlated_risk_summary.tail_analysis
        )

    return charts
