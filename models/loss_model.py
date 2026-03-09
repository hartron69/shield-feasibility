"""
Shield Captive Risk Platform – Financial Loss Model.

Provides the LossView dataclass that separates gross, retained, and reinsured
losses from Monte Carlo simulation output.  This is the foundation for
captive structure analysis and per-layer reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class LossView:
    """
    Decomposed loss view across the insurance tower.

    All arrays have shape (N, T) where N = number of simulations, T = years.

    Attributes
    ----------
    gross_loss : np.ndarray
        Total simulated loss before any risk-transfer mechanism.
    retained_loss : np.ndarray
        Loss absorbed by the operator (below attachment point or within
        aggregate retention).
    reinsured_loss : np.ndarray
        Loss ceded to reinsurers / captive cell layers.
    net_captive_loss : np.ndarray
        Net loss remaining in the captive cell after reinsurance.
    attachment_point : float
        XS attachment: losses above this are ceded to reinsurers (per event).
    limit : float
        Maximum reinsurance recovery per event.
    retention_layer : float
        Operator annual aggregate retention (self-insured retention).
    """
    gross_loss: np.ndarray
    retained_loss: np.ndarray
    reinsured_loss: np.ndarray
    net_captive_loss: np.ndarray

    attachment_point: float
    limit: float
    retention_layer: float

    # ── Derived scalar statistics ─────────────────────────────────────────────

    @property
    def mean_gross(self) -> float:
        return float(self.gross_loss.mean())

    @property
    def mean_retained(self) -> float:
        return float(self.retained_loss.mean())

    @property
    def mean_reinsured(self) -> float:
        return float(self.reinsured_loss.mean())

    @property
    def mean_net_captive(self) -> float:
        return float(self.net_captive_loss.mean())

    @property
    def gross_var_995(self) -> float:
        return float(np.percentile(self.gross_loss.flatten(), 99.5))

    @property
    def net_captive_var_995(self) -> float:
        return float(np.percentile(self.net_captive_loss.flatten(), 99.5))


def compute_loss_view(
    annual_losses: np.ndarray,
    attachment_point: float = 0.0,
    limit: float = float("inf"),
    retention_layer: float = 0.0,
) -> LossView:
    """
    Compute a LossView from a gross annual loss matrix.

    Parameters
    ----------
    annual_losses : np.ndarray
        Shape (N, T) – gross simulated losses.
    attachment_point : float
        Per-occurrence XS attachment.  Losses below this stay with the operator.
    limit : float
        Per-occurrence reinsurance limit (max recovery per event).
    retention_layer : float
        Annual aggregate self-insured retention.  Applied to the total
        annual loss before cession to the captive.

    Returns
    -------
    LossView
    """
    gross = annual_losses  # (N, T)

    # Per-year aggregate losses above the aggregate retention stay with captive
    # Simple model: per-occurrence structure applied to annual aggregates
    excess_over_retention = np.maximum(gross - retention_layer, 0.0)

    # Reinsured = min(excess, limit) per year per simulation
    reinsured = np.minimum(excess_over_retention, limit) if not np.isinf(limit) else excess_over_retention

    # XS attachment further narrows what's ceded:
    # Only the portion above attachment_point is reinsured
    reinsured_xs = np.maximum(reinsured - attachment_point, 0.0)

    retained = gross - reinsured_xs
    net_captive = reinsured_xs  # captive absorbs what was ceded

    return LossView(
        gross_loss=gross,
        retained_loss=retained,
        reinsured_loss=reinsured_xs,
        net_captive_loss=net_captive,
        attachment_point=attachment_point,
        limit=float(limit),
        retention_layer=retention_layer,
    )
