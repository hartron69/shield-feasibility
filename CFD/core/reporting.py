"""
core/reporting.py — Reporter: figures and summary tables for AquaGuard

Reporter wraps all matplotlib rendering that was previously inlined in
CoastalpathogenTimeMarcher. It takes a flow_model, output_dir, and
risk_engine reference so it can draw threshold lines without tight coupling.

All plot logic is identical to v1.22b.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

os.environ.setdefault(
    'MPLCONFIGDIR',
    str(Path(tempfile.gettempdir()) / 'mplconfig_aquaguard'),
)
import matplotlib
import matplotlib.colors
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core.io_utils import standardize_summary_df


class Reporter:
    """Renders snapshots, concentration time-series, risk plots, and heatmaps."""

    VERSION = 'v1.23'

    def __init__(self, flow_model, output_dir: Path, risk_engine):
        self.flow_model = flow_model
        self.output_dir = Path(output_dir)
        self.risk = risk_engine

    # ── Snapshot grid ─────────────────────────────────────────────────────────

    def render_snapshot_grid(
        self,
        case_result: dict,
        filename: str,
        log_func: Optional[Callable] = None,
    ) -> Path:
        _log = log_func or (lambda m: None)
        case_name = case_result['case_name']
        _log(f"Renderer snapshot-grid for '{case_name}' -> {filename}")

        sample_times = [0, 200, 400, 600, 800, 1000, 1200]
        fig, axes = plt.subplots(2, 4, figsize=(17.5, 8.8), constrained_layout=True)
        axes = axes.flatten()

        # case_dir may be stored in result dict (e.g. for 'timeseries' mode)
        rep_case_dir = case_result.get('case_dir', None)

        for idx, (ax, t_s) in enumerate(zip(axes, sample_times), start=1):
            _log(
                f"  Beregner felt {idx}/{len(sample_times)} "
                f"for '{case_name}' ved t={t_s} s"
            )
            field = self.flow_model.evaluate_field(
                case_name, t_s, nx=111, ny=81, case_dir=rep_case_dir
            )
            X, Y, U, V = field['X'], field['Y'], field['U'], field['V']
            speed = np.where(np.isfinite(field['speed']), field['speed'], np.nan)
            finite_speed = speed[np.isfinite(speed)]
            levels = np.linspace(float(np.nanmin(finite_speed)), float(np.nanmax(finite_speed)), 22)
            ax.contourf(X, Y, speed, levels=levels, cmap='viridis', alpha=0.78)
            ax.streamplot(
                X[0, :], Y[:, 0],
                np.nan_to_num(U), np.nan_to_num(V),
                color='white', density=1.2, linewidth=0.55, arrowsize=0.7,
            )
            snap = case_result['snapshots'].get(
                t_s,
                {'xy': np.empty((0, 2)), 'mass': np.empty((0,)), 'risk_mass': np.empty((0,))},
            )
            xy = snap['xy']
            mass = snap['mass']
            if len(xy) > 0:
                ax.hexbin(
                    xy[:, 0], xy[:, 1], C=mass,
                    reduce_C_function=np.sum,
                    gridsize=46, cmap='magma', mincnt=1, alpha=0.82,
                )
            ax.axhline(self.flow_model.coast.y_coast, color='saddlebrown', lw=3)
            ax.fill_between(
                self.flow_model.domain['x'],
                self.flow_model.coast.y_coast - 25,
                self.flow_model.coast.y_coast,
                color='burlywood', alpha=0.95,
            )
            for net, color in zip(self.flow_model.nets, ['tab:green', 'tab:orange', 'tab:red']):
                circle = plt.Circle(
                    net.center, net.radius,
                    edgecolor='black', facecolor=color, alpha=0.30, lw=1.6,
                )
                ax.add_patch(circle)
            ax.set_title(f't = {t_s} s')
            ax.set_aspect('equal')
            ax.set_xlim(self.flow_model.domain['x'])
            ax.set_ylim(self.flow_model.domain['y'])
            ax.grid(True, alpha=0.15)
            ax.set_xlabel('x [m]')
            ax.set_ylabel('y [m]')

        axes[-1].axis('off')
        fig.suptitle(
            f"AquaGuard coastal pathogen – {case_name} – 3 nets + coastline + biology {self.VERSION}",
            fontsize=14, y=1.01,
        )
        out = self.output_dir / filename
        fig.savefig(out, dpi=170, bbox_inches='tight')
        plt.close(fig)
        _log(f"  Ferdig lagret: {out}")
        return out

    # ── Concentration time-series ─────────────────────────────────────────────

    def render_concentration_timeseries(
        self,
        case_result: dict,
        filename: str,
        species_infectivity_factor: float = 1.0,
        log_func: Optional[Callable] = None,
    ) -> Path:
        _log = log_func or (lambda m: None)
        case_name = case_result['case_name']
        _log(f"Renderer konsentrasjonstidsserie for '{case_name}' -> {filename}")

        ts = case_result['time_series']
        t_min = ts['time_s'].to_numpy() / 60.0
        fig, ax = plt.subplots(figsize=(10.8, 5.8))

        for net, color in zip(self.flow_model.nets, ['tab:green', 'tab:orange', 'tab:red']):
            safe = net.name.lower().replace(' ', '_')
            ax.plot(
                t_min, ts[f'{safe}_conc_rel'],
                lw=2.0, color=color,
                label=f'{net.name} aktiv conc (S={net.solidity:.2f})',
            )
            if species_infectivity_factor != 1.0:
                ax.plot(
                    t_min, ts[f'{safe}_risk_conc_rel'],
                    lw=1.2, ls='--', color=color, alpha=0.85,
                    label=f'{net.name} risiko-vektet',
                )

        ax.set_title(
            f"Relativ biologisk aktiv pathogen-konsentrasjon inne i nøtene – "
            f"{case_name} – kystcase"
        )
        ax.set_xlabel('Tid [min]')
        ax.set_ylabel('Relativ aktiv konsentrasjon [masse / m²]')
        ax.grid(True, alpha=0.25)
        ax.legend()
        out = self.output_dir / filename
        fig.tight_layout()
        fig.savefig(out, dpi=180, bbox_inches='tight')
        plt.close(fig)
        _log(f"  Ferdig lagret: {out}")
        return out

    # ── Operational risk plot ─────────────────────────────────────────────────

    def render_operational_risk_plot(
        self,
        case_result: dict,
        filename: str,
        log_func: Optional[Callable] = None,
    ) -> Path:
        _log = log_func or (lambda m: None)
        case_name = case_result['case_name']
        _log(f"Renderer operativt risikoplot for '{case_name}' -> {filename}")

        summary = standardize_summary_df(case_result['summary'])
        if summary.empty:
            raise ValueError("case_result['summary'] is empty; cannot render risk plot.")

        status_order = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}
        status_color = {'GREEN': '#2ca02c', 'YELLOW': '#ffbf00', 'RED': '#d62728'}
        nets = summary['net'].tolist()
        y = np.arange(len(nets))
        colors = [status_color.get(str(s).upper(), '#808080') for s in summary['risk_status']]

        fig, axes = plt.subplots(1, 3, figsize=(16.8, 5.8), constrained_layout=True)

        # Status bar
        ax = axes[0]
        status_vals = [status_order.get(str(s).upper(), 0) for s in summary['risk_status']]
        ax.barh(y, status_vals, color=colors, edgecolor='black', alpha=0.85)
        ax.set_yticks(y)
        ax.set_yticklabels(nets)
        ax.set_xlim(0, 2.6)
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(['GREEN', 'YELLOW', 'RED'])
        ax.set_title('Operativ risikostatus')
        ax.grid(True, axis='x', alpha=0.2)
        for i, row in summary.iterrows():
            alarm_txt = 'ALARM' if bool(row.get('operational_alarm', False)) else 'OK'
            ax.text(
                min(status_vals[i] + 0.05, 2.45), i,
                f"{row['risk_status']} | {alarm_txt}",
                va='center', fontsize=9,
            )

        # Arrival bar
        ax = axes[1]
        arrival_min = [
            np.nan if pd.isna(v) else float(v) / 60.0
            for v in summary['first_arrival_s']
        ]
        arr_plot = [v if np.isfinite(v) else 0.0 for v in arrival_min]
        ax.barh(y, arr_plot, color=colors, edgecolor='black', alpha=0.85)
        ax.set_yticks(y)
        ax.set_yticklabels(nets)
        ax.set_title('Første ankomsttid')
        ax.set_xlabel('Tid [min]')
        ax.grid(True, axis='x', alpha=0.2)
        ax.axvline(
            self.risk.red_arrival_threshold_s / 60.0,
            color='#d62728', ls='--', lw=1.5, label='Rød terskel',
        )
        ax.axvline(
            self.risk.yellow_arrival_threshold_s / 60.0,
            color='#ffbf00', ls='--', lw=1.5, label='Gul terskel',
        )
        max_arr = max([v for v in arr_plot if np.isfinite(v)] + [1.0])
        for i, v in enumerate(arrival_min):
            label = 'Ingen ankomst' if not np.isfinite(v) else f'{v:.1f} min'
            ax.text(arr_plot[i] + 0.03 * max_arr, i, label, va='center', fontsize=9)
        ax.legend(loc='lower right')

        # Exposure bar
        ax = axes[2]
        exposure = summary['total_risk_exposure_mass_seconds'].astype(float).to_numpy()
        ax.barh(y, exposure, color=colors, edgecolor='black', alpha=0.85)
        ax.set_yticks(y)
        ax.set_yticklabels(nets)
        ax.set_title('Total risiko-vektet eksponering')
        ax.set_xlabel('Relativ masse · s')
        ax.grid(True, axis='x', alpha=0.2)
        ax.axvline(
            self.risk.red_exposure_threshold_mass_seconds,
            color='#d62728', ls='--', lw=1.5, label='Rød terskel',
        )
        ax.axvline(
            self.risk.yellow_exposure_threshold_mass_seconds,
            color='#ffbf00', ls='--', lw=1.5, label='Gul terskel',
        )
        max_exp = max(list(exposure) + [1.0])
        for i, v in enumerate(exposure):
            ax.text(v + 0.02 * max_exp, i, f'{v:.2f}', va='center', fontsize=9)
        ax.legend(loc='lower right')

        fig.suptitle(
            f"Operativt risikobilde – {case_name} – AquaGuard {self.VERSION}",
            fontsize=14,
        )
        out = self.output_dir / filename
        fig.savefig(out, dpi=180, bbox_inches='tight')
        plt.close(fig)
        _log(f"  Ferdig lagret: {out}")
        return out

    # ── Risk heatmap ──────────────────────────────────────────────────────────

    def render_risk_heatmap(
        self,
        summary_df: pd.DataFrame,
        filename: str,
        log_func: Optional[Callable] = None,
    ) -> Path:
        _log = log_func or (lambda m: None)
        _log(f"Renderer samlet risiko-heatmap -> {filename}")
        summary_df = standardize_summary_df(summary_df)
        if summary_df.empty:
            raise ValueError("summary_df is empty; cannot render risk heatmap.")

        status_order = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}
        case_col = 'case_name'
        cases = list(dict.fromkeys(summary_df[case_col].tolist()))
        nets = list(dict.fromkeys(summary_df['net'].tolist()))
        mat = np.full((len(cases), len(nets)), np.nan)
        labels = [['' for _ in nets] for _ in cases]

        for i, case in enumerate(cases):
            for j, net in enumerate(nets):
                sub = summary_df[
                    (summary_df[case_col] == case) & (summary_df['net'] == net)
                ]
                if not sub.empty:
                    row = sub.iloc[0]
                    mat[i, j] = status_order.get(str(row['risk_status']).upper(), np.nan)
                    arr = row.get('first_arrival_s', np.nan)
                    arr_txt = 'na' if pd.isna(arr) else f"{float(arr)/60.0:.1f}m"
                    labels[i][j] = f"{row['risk_status']}\n{arr_txt}"

        fig, ax = plt.subplots(figsize=(1.8 * len(nets) + 2.0, 1.1 * len(cases) + 2.4))
        cmap = matplotlib.colors.ListedColormap(['#2ca02c', '#ffbf00', '#d62728'])
        bounds = [-0.5, 0.5, 1.5, 2.5]
        norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
        im = ax.imshow(mat, cmap=cmap, norm=norm, aspect='auto')

        ax.set_xticks(np.arange(len(nets)))
        ax.set_xticklabels(nets)
        ax.set_yticks(np.arange(len(cases)))
        ax.set_yticklabels(cases)
        ax.set_title('Samlet operativ risiko per retning og nøt')
        ax.set_xlabel('Nøt')
        ax.set_ylabel('Strømretning')

        for i in range(len(cases)):
            for j in range(len(nets)):
                if np.isfinite(mat[i, j]):
                    ax.text(j, i, labels[i][j], ha='center', va='center', fontsize=9, color='black')

        cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2], fraction=0.05, pad=0.04)
        cbar.ax.set_yticklabels(['GREEN', 'YELLOW', 'RED'])

        out = self.output_dir / filename
        fig.tight_layout()
        fig.savefig(out, dpi=180, bbox_inches='tight')
        plt.close(fig)
        _log(f"  Ferdig lagret: {out}")
        return out
