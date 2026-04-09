"""
core/mc_reporter.py — Sprint 8: Monte-Carlo risk reporting

Renders matplotlib figures and a plain-text management summary from
MCRiskResult lists and MCTransferLibrary objects.

Figures produced
----------------
mc_risk_heatmap.png          — modal risk + P(RED) + E[score] heatmaps
mc_transfer_heatmap.png      — mean TC and p90 TC heatmaps
mc_pair_profiles.png         — stacked P(GREEN/YELLOW/RED) bars per pair
mc_management_summary.png    — single-page dashboard (all key panels)
mc_summary.txt               — plain-text management summary

Usage
-----
    from core.mc_reporter import MCReporter
    reporter = MCReporter(mc_library, results, output_dir)
    paths = reporter.render_all()
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

os.environ.setdefault(
    'MPLCONFIGDIR',
    str(Path(tempfile.gettempdir()) / 'mplconfig_aquaguard'),
)
import matplotlib
import matplotlib.colors
import matplotlib.patches as mpatches
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core.mc_risk_engine import MCRiskResult
from core.transfer_library import MCTransferLibrary


# ── Colour helpers ────────────────────────────────────────────────────────────

_STATUS_COLOR = {'GREEN': '#2ca02c', 'YELLOW': '#ffbf00', 'RED': '#d62728'}
_STATUS_ORDER = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}
_RISK_CMAP = matplotlib.colors.ListedColormap(
    [_STATUS_COLOR['GREEN'], _STATUS_COLOR['YELLOW'], _STATUS_COLOR['RED']]
)
_RISK_NORM = matplotlib.colors.BoundaryNorm([-0.5, 0.5, 1.5, 2.5], _RISK_CMAP.N)


def _status_to_score(s: str) -> float:
    return float(_STATUS_ORDER.get(str(s).upper(), 0))


# ── Reporter ──────────────────────────────────────────────────────────────────

class MCReporter:
    """
    Renders all Monte-Carlo risk reporting artefacts.

    Parameters
    ----------
    mc_library  : MCTransferLibrary (Sprint 6)
    results     : list of MCRiskResult (Sprint 7)
    output_dir  : destination directory for all files
    scenario_name : used in figure titles
    """

    VERSION = 'v1.23-sprint8'

    def __init__(
        self,
        mc_library: MCTransferLibrary,
        results: List[MCRiskResult],
        output_dir: Path,
        scenario_name: str = '',
    ):
        self.lib = mc_library
        self.results = list(results)
        self.output_dir = Path(output_dir)
        self.scenario_name = scenario_name or mc_library.scenario_name
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Build summary DataFrame once
        self._df = pd.DataFrame([r.to_dict() for r in results]) if results else pd.DataFrame()

        # Ordered unique source/target IDs
        self._sources = sorted({r.source_site_id for r in results})
        self._targets = sorted({r.target_site_id for r in results})

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _log(self, msg: str, log_func: Optional[Callable] = None) -> None:
        if log_func:
            log_func(msg)

    def _pivot(self, column: str) -> np.ndarray:
        """
        Build a (n_sources × n_targets) matrix for the given column.
        Missing pairs → NaN.
        """
        mat = np.full((len(self._sources), len(self._targets)), np.nan)
        for r in self.results:
            i = self._sources.index(r.source_site_id)
            j = self._targets.index(r.target_site_id)
            v = r.to_dict().get(column)
            mat[i, j] = float('nan') if v is None else float(v)
        return mat

    def _draw_heatmap_cell_labels(
        self, ax, mat, fmt='{:.2f}', fontsize=9, color='black'
    ) -> None:
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat[i, j]
                if np.isfinite(v):
                    ax.text(j, i, fmt.format(v),
                            ha='center', va='center',
                            fontsize=fontsize, color=color)

    def _axis_labels(self, ax) -> None:
        ax.set_xticks(range(len(self._targets)))
        ax.set_xticklabels(self._targets, rotation=30, ha='right')
        ax.set_yticks(range(len(self._sources)))
        ax.set_yticklabels(self._sources)
        ax.set_xlabel('Malokalitet (target)')
        ax.set_ylabel('Kildeokalitet (source)')

    # ── Figure 1: risk heatmap ────────────────────────────────────────────────

    def render_risk_heatmap(
        self,
        filename: str = 'mc_risk_heatmap.png',
        log_func: Optional[Callable] = None,
    ) -> Path:
        """Three-panel heatmap: modal status | P(RED) | E[risk score]."""
        self._log(f"Rendering risk heatmap -> {filename}", log_func)

        modal_mat = np.full((len(self._sources), len(self._targets)), np.nan)
        for r in self.results:
            i = self._sources.index(r.source_site_id)
            j = self._targets.index(r.target_site_id)
            modal_mat[i, j] = _status_to_score(r.modal_risk_status)

        p_red_mat = self._pivot('p_red')
        score_mat = self._pivot('expected_risk_score')

        fig, axes = plt.subplots(1, 3, figsize=(14, 0.9 * len(self._sources) + 3.5),
                                 constrained_layout=True)

        # Panel 1: modal status
        ax = axes[0]
        im = ax.imshow(modal_mat, cmap=_RISK_CMAP, norm=_RISK_NORM, aspect='auto')
        self._axis_labels(ax)
        ax.set_title('Modal risikostatus')
        for i in range(len(self._sources)):
            for j in range(len(self._targets)):
                v = modal_mat[i, j]
                if np.isfinite(v):
                    lbl = ['GREEN', 'YELLOW', 'RED'][int(round(v))]
                    ax.text(j, i, lbl, ha='center', va='center',
                            fontsize=9, fontweight='bold', color='white')
        cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2], fraction=0.046, pad=0.04)
        cbar.ax.set_yticklabels(['GREEN', 'YELLOW', 'RED'])

        # Panel 2: P(RED)
        ax = axes[1]
        p_cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            'grn_red', ['#2ca02c', '#ffbf00', '#d62728']
        )
        im2 = ax.imshow(p_red_mat, cmap=p_cmap, vmin=0.0, vmax=1.0, aspect='auto')
        self._axis_labels(ax)
        ax.set_title('P(RED)')
        self._draw_heatmap_cell_labels(ax, p_red_mat, fmt='{:.2f}', color='white')
        fig.colorbar(im2, ax=ax, fraction=0.046, pad=0.04)

        # Panel 3: expected risk score
        ax = axes[2]
        im3 = ax.imshow(score_mat, cmap=p_cmap, vmin=0.0, vmax=2.0, aspect='auto')
        self._axis_labels(ax)
        ax.set_title('E[risikoscore]  (0=G, 1=Y, 2=R)')
        self._draw_heatmap_cell_labels(ax, score_mat, fmt='{:.2f}', color='white')
        fig.colorbar(im3, ax=ax, fraction=0.046, pad=0.04)

        fig.suptitle(
            f"Monte-Carlo risikoanalyse — {self.scenario_name} — {self.VERSION}",
            fontsize=13,
        )
        out = self.output_dir / filename
        fig.savefig(out, dpi=160, bbox_inches='tight')
        plt.close(fig)
        self._log(f"  Saved: {out}", log_func)
        return out

    # ── Figure 2: transfer heatmap ────────────────────────────────────────────

    def render_transfer_heatmap(
        self,
        filename: str = 'mc_transfer_heatmap.png',
        log_func: Optional[Callable] = None,
    ) -> Path:
        """Two-panel heatmap: mean TC [s] | p90 TC [s]."""
        self._log(f"Rendering transfer heatmap -> {filename}", log_func)

        mean_tc = self._pivot('mean_tc_s')
        p90_tc = self._pivot('p90_tc_s')
        var99 = self._pivot('var99_exposure_ms')

        fig, axes = plt.subplots(1, 3, figsize=(14, 0.9 * len(self._sources) + 3.5),
                                 constrained_layout=True)
        tc_cmap = 'YlOrRd'

        for ax, mat, title, unit in zip(
            axes,
            [mean_tc, p90_tc, var99],
            ['Middelverdi TC [s]', 'p90 TC [s]', 'VaR99 eksponering [masse·s]'],
            ['{:.1f}', '{:.1f}', '{:.0f}'],
        ):
            finite = mat[np.isfinite(mat)]
            vmax = float(np.nanmax(finite)) if finite.size > 0 else 1.0
            im = ax.imshow(mat, cmap=tc_cmap, vmin=0.0, vmax=vmax, aspect='auto')
            self._axis_labels(ax)
            ax.set_title(title)
            self._draw_heatmap_cell_labels(ax, mat, fmt=unit, color='black')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        fig.suptitle(
            f"Overforingskoeffisienter — {self.scenario_name} — {self.VERSION}",
            fontsize=13,
        )
        out = self.output_dir / filename
        fig.savefig(out, dpi=160, bbox_inches='tight')
        plt.close(fig)
        self._log(f"  Saved: {out}", log_func)
        return out

    # ── Figure 3: pair risk profiles ──────────────────────────────────────────

    def render_pair_risk_profiles(
        self,
        filename: str = 'mc_pair_profiles.png',
        log_func: Optional[Callable] = None,
    ) -> Path:
        """Stacked P(GREEN/YELLOW/RED) bars, one bar per (source, target) pair."""
        self._log(f"Rendering pair risk profiles -> {filename}", log_func)

        n_pairs = len(self.results)
        if n_pairs == 0:
            self._log("  No results — skipped.", log_func)
            return self.output_dir / filename

        labels = [f"{r.source_site_id}\n->{r.target_site_id}" for r in self.results]
        p_g = np.array([r.p_green for r in self.results])
        p_y = np.array([r.p_yellow for r in self.results])
        p_r = np.array([r.p_red for r in self.results])
        x = np.arange(n_pairs)
        width = 0.55

        fig, axes = plt.subplots(1, 2,
                                 figsize=(max(9, n_pairs * 1.6), 6),
                                 constrained_layout=True)

        # Left: stacked risk probabilities
        ax = axes[0]
        b1 = ax.bar(x, p_g, width, label='P(GREEN)', color=_STATUS_COLOR['GREEN'], alpha=0.88)
        b2 = ax.bar(x, p_y, width, bottom=p_g, label='P(YELLOW)', color=_STATUS_COLOR['YELLOW'], alpha=0.88)
        b3 = ax.bar(x, p_r, width, bottom=p_g + p_y, label='P(RED)', color=_STATUS_COLOR['RED'], alpha=0.88)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylim(0, 1.08)
        ax.set_ylabel('Sannsynlighet')
        ax.set_title('Risikostatus-sannsynlighet per par')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, axis='y', alpha=0.25)
        for xi, (g, y, r) in enumerate(zip(p_g, p_y, p_r)):
            if r > 0.02:
                ax.text(xi, g + y + r / 2, f'{r:.2f}', ha='center', va='center',
                        fontsize=7, color='white', fontweight='bold')

        # Right: expected risk score + VaR99 exposure (dual axis)
        ax2 = axes[1]
        scores = np.array([r.expected_risk_score for r in self.results])
        color_score = '#1f77b4'
        bars = ax2.bar(x, scores, width, color=color_score, alpha=0.80, label='E[risikoscore]')
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, fontsize=8)
        ax2.set_ylim(0, 2.3)
        ax2.set_ylabel('E[risikoscore]  (0=G, 1=Y, 2=R)', color=color_score)
        ax2.tick_params(axis='y', labelcolor=color_score)
        ax2.set_title('Forventet risikoscore per par')
        ax2.axhline(1.0, color=_STATUS_COLOR['YELLOW'], ls='--', lw=1.2, alpha=0.7, label='YELLOW grense')
        ax2.axhline(2.0, color=_STATUS_COLOR['RED'], ls='--', lw=1.2, alpha=0.7, label='RED grense')
        ax2.legend(loc='upper left', fontsize=8)
        ax2.grid(True, axis='y', alpha=0.25)
        for xi, s in enumerate(scores):
            ax2.text(xi, s + 0.05, f'{s:.2f}', ha='center', va='bottom', fontsize=8)

        fig.suptitle(
            f"Par-vise risikoprofiler — {self.scenario_name} — {self.VERSION}",
            fontsize=13,
        )
        out = self.output_dir / filename
        fig.savefig(out, dpi=160, bbox_inches='tight')
        plt.close(fig)
        self._log(f"  Saved: {out}", log_func)
        return out

    # ── Figure 4: management summary dashboard ────────────────────────────────

    def render_management_summary(
        self,
        filename: str = 'mc_management_summary.png',
        log_func: Optional[Callable] = None,
    ) -> Path:
        """
        Single-page dashboard combining:
          Row 1: modal status heatmap | P(RED) heatmap | pair risk bars
          Row 2: mean TC heatmap      | VaR99 exposure  | summary table
        """
        self._log(f"Rendering management summary -> {filename}", log_func)

        n_src = len(self._sources)
        n_tgt = len(self._targets)

        fig = plt.figure(figsize=(18, 11), constrained_layout=True)
        gs = fig.add_gridspec(2, 3)
        ax_modal = fig.add_subplot(gs[0, 0])
        ax_pred = fig.add_subplot(gs[0, 1])
        ax_bars = fig.add_subplot(gs[0, 2])
        ax_tc = fig.add_subplot(gs[1, 0])
        ax_var = fig.add_subplot(gs[1, 1])
        ax_tbl = fig.add_subplot(gs[1, 2])

        # ── Modal status ──
        modal_mat = np.full((n_src, n_tgt), np.nan)
        for r in self.results:
            i = self._sources.index(r.source_site_id)
            j = self._targets.index(r.target_site_id)
            modal_mat[i, j] = _status_to_score(r.modal_risk_status)
        ax_modal.imshow(modal_mat, cmap=_RISK_CMAP, norm=_RISK_NORM, aspect='auto')
        for i in range(n_src):
            for j in range(n_tgt):
                v = modal_mat[i, j]
                if np.isfinite(v):
                    lbl = ['GREEN', 'YELLOW', 'RED'][int(round(v))]
                    ax_modal.text(j, i, lbl, ha='center', va='center',
                                  fontsize=8, fontweight='bold', color='white')
        ax_modal.set_xticks(range(n_tgt)); ax_modal.set_xticklabels(self._targets, fontsize=7)
        ax_modal.set_yticks(range(n_src)); ax_modal.set_yticklabels(self._sources, fontsize=7)
        ax_modal.set_title('Modal risikostatus', fontsize=10)
        ax_modal.set_xlabel('Mal', fontsize=8); ax_modal.set_ylabel('Kilde', fontsize=8)

        # ── P(RED) ──
        p_red_mat = self._pivot('p_red')
        p_cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            'grn_red', ['#2ca02c', '#ffbf00', '#d62728']
        )
        im2 = ax_pred.imshow(p_red_mat, cmap=p_cmap, vmin=0, vmax=1, aspect='auto')
        self._draw_heatmap_cell_labels(ax_pred, p_red_mat, fmt='{:.2f}', color='white', fontsize=8)
        ax_pred.set_xticks(range(n_tgt)); ax_pred.set_xticklabels(self._targets, fontsize=7)
        ax_pred.set_yticks(range(n_src)); ax_pred.set_yticklabels(self._sources, fontsize=7)
        ax_pred.set_title('P(RED)', fontsize=10)
        ax_pred.set_xlabel('Mal', fontsize=8)
        fig.colorbar(im2, ax=ax_pred, fraction=0.046, pad=0.04)

        # ── Stacked bars ──
        n_pairs = len(self.results)
        x = np.arange(n_pairs)
        labels_bar = [f"{r.source_site_id}->{r.target_site_id}" for r in self.results]
        p_g = np.array([r.p_green  for r in self.results])
        p_y = np.array([r.p_yellow for r in self.results])
        p_r = np.array([r.p_red    for r in self.results])
        ax_bars.bar(x, p_g, 0.6, color=_STATUS_COLOR['GREEN'],  alpha=0.88, label='P(G)')
        ax_bars.bar(x, p_y, 0.6, bottom=p_g, color=_STATUS_COLOR['YELLOW'], alpha=0.88, label='P(Y)')
        ax_bars.bar(x, p_r, 0.6, bottom=p_g + p_y, color=_STATUS_COLOR['RED'], alpha=0.88, label='P(R)')
        ax_bars.set_xticks(x); ax_bars.set_xticklabels(labels_bar, fontsize=6, rotation=25, ha='right')
        ax_bars.set_ylim(0, 1.12); ax_bars.set_ylabel('Sannsynlighet', fontsize=8)
        ax_bars.set_title('Risikosannsynligheter per par', fontsize=10)
        ax_bars.legend(loc='upper right', fontsize=7)
        ax_bars.grid(True, axis='y', alpha=0.2)

        # ── Mean TC ──
        mean_tc = self._pivot('mean_tc_s')
        finite_tc = mean_tc[np.isfinite(mean_tc)]
        vmax_tc = float(np.nanmax(finite_tc)) if finite_tc.size > 0 else 1.0
        im_tc = ax_tc.imshow(mean_tc, cmap='YlOrRd', vmin=0, vmax=vmax_tc, aspect='auto')
        self._draw_heatmap_cell_labels(ax_tc, mean_tc, fmt='{:.1f}s', fontsize=8)
        ax_tc.set_xticks(range(n_tgt)); ax_tc.set_xticklabels(self._targets, fontsize=7)
        ax_tc.set_yticks(range(n_src)); ax_tc.set_yticklabels(self._sources, fontsize=7)
        ax_tc.set_title('Middelverdi TC [s]', fontsize=10)
        ax_tc.set_xlabel('Mal', fontsize=8); ax_tc.set_ylabel('Kilde', fontsize=8)
        fig.colorbar(im_tc, ax=ax_tc, fraction=0.046, pad=0.04)

        # ── VaR99 exposure ──
        var99_mat = self._pivot('var99_exposure_ms')
        finite_v = var99_mat[np.isfinite(var99_mat)]
        vmax_v = float(np.nanmax(finite_v)) if finite_v.size > 0 else 1.0
        im_v = ax_var.imshow(var99_mat, cmap='YlOrRd', vmin=0, vmax=vmax_v, aspect='auto')
        self._draw_heatmap_cell_labels(ax_var, var99_mat, fmt='{:.0f}', fontsize=7)
        ax_var.set_xticks(range(n_tgt)); ax_var.set_xticklabels(self._targets, fontsize=7)
        ax_var.set_yticks(range(n_src)); ax_var.set_yticklabels(self._sources, fontsize=7)
        ax_var.set_title('VaR99 eksponering [masse·s]', fontsize=10)
        ax_var.set_xlabel('Mal', fontsize=8)
        fig.colorbar(im_v, ax=ax_var, fraction=0.046, pad=0.04)

        # ── Summary table ──
        ax_tbl.axis('off')
        rows_tbl = []
        for r in self.results:
            arr_txt = (
                'ingen'
                if np.isnan(r.mean_first_arrival_s)
                else f"{r.mean_first_arrival_s/60:.1f} min"
            )
            rows_tbl.append([
                r.source_site_id,
                r.target_site_id,
                r.modal_risk_status,
                f"{r.p_red:.2f}",
                f"{r.mean_tc_s:.1f}",
                arr_txt,
            ])
        col_hdrs = ['Kilde', 'Mal', 'Modal', 'P(RED)', 'E[TC] s', 'E[arr]']
        tbl = ax_tbl.table(
            cellText=rows_tbl,
            colLabels=col_hdrs,
            cellLoc='center',
            loc='center',
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1.0, 1.6)
        # Colour the Modal column
        for row_idx, r in enumerate(self.results, start=1):
            cell = tbl[row_idx, 2]
            cell.set_facecolor(_STATUS_COLOR.get(r.modal_risk_status, '#cccccc'))
            cell.set_text_props(color='white', fontweight='bold')
        ax_tbl.set_title('Oppsummeringstabell', fontsize=10, pad=4)

        # Legend patches
        legend_patches = [
            mpatches.Patch(color=c, label=s)
            for s, c in _STATUS_COLOR.items()
        ]
        fig.legend(handles=legend_patches, loc='lower center',
                   ncol=3, fontsize=9, framealpha=0.8)

        fig.suptitle(
            f"AquaGuard MC-risikodashboard — {self.scenario_name} — {self.VERSION}  "
            f"[{datetime.now().strftime('%Y-%m-%d')}]",
            fontsize=14, fontweight='bold',
        )

        out = self.output_dir / filename
        fig.savefig(out, dpi=160, bbox_inches='tight')
        plt.close(fig)
        self._log(f"  Saved: {out}", log_func)
        return out

    # ── Text summary ──────────────────────────────────────────────────────────

    def write_text_summary(
        self,
        filename: str = 'mc_summary.txt',
        log_func: Optional[Callable] = None,
    ) -> Path:
        """Plain-text management summary suitable for pasting into reports."""
        self._log(f"Writing text summary -> {filename}", log_func)
        lines = [
            '=' * 68,
            f'AquaGuard MC-risikoanalyse — {self.scenario_name}',
            f'Generert: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            f'Versjon: {self.VERSION}',
            '=' * 68,
            '',
        ]

        if self.results:
            n = self.results[0].n_samples
            lines += [
                f'Antall MC-samples per par : {n:,}',
                f'Ensemble-storrelse        : {self.lib.n_ensemble}',
                f'Antall kilde-lokaliteter  : {len(self._sources)}',
                f'Antall mal-lokaliteter    : {len(self._targets)}',
                '',
                '-' * 68,
                'RESULTATER PER PAR',
                '-' * 68,
                f'{"Kilde":<14} {"Mal":<14} {"Modal":<8} {"P(RED)":>7} '
                f'{"P(GRN)":>7} {"E[TC] s":>9} {"VaR99":>10} {"E[arr]":>10}',
                '-' * 68,
            ]
            for r in self.results:
                arr_txt = (
                    'ingen'
                    if np.isnan(r.mean_first_arrival_s)
                    else f'{r.mean_first_arrival_s/60:.1f} min'
                )
                lines.append(
                    f'{r.source_site_id:<14} {r.target_site_id:<14} '
                    f'{r.modal_risk_status:<8} {r.p_red:>7.3f} '
                    f'{r.p_green:>7.3f} {r.mean_tc_s:>9.1f} '
                    f'{r.var99_exposure_ms:>10.1f} {arr_txt:>10}'
                )
            lines += ['', '-' * 68, 'VURDERING', '-' * 68]

            red_pairs = [r for r in self.results if r.modal_risk_status == 'RED']
            yel_pairs = [r for r in self.results if r.modal_risk_status == 'YELLOW']
            grn_pairs = [r for r in self.results if r.modal_risk_status == 'GREEN']

            if red_pairs:
                lines.append(
                    f'ROD RISIKO ({len(red_pairs)} par): '
                    + ', '.join(f'{r.source_site_id}->{r.target_site_id}' for r in red_pairs)
                )
            if yel_pairs:
                lines.append(
                    f'GUL RISIKO ({len(yel_pairs)} par): '
                    + ', '.join(f'{r.source_site_id}->{r.target_site_id}' for r in yel_pairs)
                )
            if grn_pairs:
                lines.append(
                    f'GRONN RISIKO ({len(grn_pairs)} par): '
                    + ', '.join(f'{r.source_site_id}->{r.target_site_id}' for r in grn_pairs)
                )

            # Highest-risk self-infection
            self_pairs = [r for r in self.results
                          if r.source_site_id == r.target_site_id]
            if self_pairs:
                worst = max(self_pairs, key=lambda r: r.expected_risk_score)
                lines += [
                    '',
                    f'Hoyeste egenkontaminering : {worst.source_site_id} '
                    f'(E[score]={worst.expected_risk_score:.2f}, P(RED)={worst.p_red:.3f})',
                ]

            cross_pairs = [r for r in self.results
                           if r.source_site_id != r.target_site_id and r.p_red > 0.05]
            if cross_pairs:
                worst_cross = max(cross_pairs, key=lambda r: r.p_red)
                lines.append(
                    f'Hoyeste krysskontaminering: '
                    f'{worst_cross.source_site_id}->{worst_cross.target_site_id} '
                    f'(P(RED)={worst_cross.p_red:.3f})'
                )
            else:
                lines.append(
                    'Ingen signifikant krysskontaminering (P(RED) < 5% for alle krysspar).'
                )

        lines += ['', '=' * 68]
        text = '\n'.join(lines)
        out = self.output_dir / filename
        out.write_text(text, encoding='utf-8')
        self._log(f"  Saved: {out}", log_func)
        return out

    # ── Render all ────────────────────────────────────────────────────────────

    def render_all(self, log_func: Optional[Callable] = None) -> Dict[str, Path]:
        """Render all figures and text summary. Returns dict of output paths."""
        self._log(
            f"MCReporter: rendering all artefacts for '{self.scenario_name}'",
            log_func,
        )
        paths = {}
        paths['risk_heatmap'] = self.render_risk_heatmap(log_func=log_func)
        paths['transfer_heatmap'] = self.render_transfer_heatmap(log_func=log_func)
        paths['pair_profiles'] = self.render_pair_risk_profiles(log_func=log_func)
        paths['management_summary'] = self.render_management_summary(log_func=log_func)
        paths['text_summary'] = self.write_text_summary(log_func=log_func)
        self._log(
            f"MCReporter done: {len(paths)} artefacts written to {self.output_dir}",
            log_func,
        )
        return paths
