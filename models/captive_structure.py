"""
Shield Captive Risk Platform – Captive Structure Objects.

Provides explicit data objects for defining the financial structure of
a Protected Cell Company (PCC) captive, including retention layers,
reinsurance layers, and composite captive structures.

These objects are used by PCCCaptiveStrategy and the SCR calculator to
compute net-of-reinsurance loss distributions and capital requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from models.monte_carlo import SimulationResults


# ─────────────────────────────────────────────────────────────────────────────
# Building blocks
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RetentionLayer:
    """
    Operator self-insured retention parameters.

    Attributes
    ----------
    name : str
        Descriptive label, e.g. "Per-Occurrence Deductible".
    per_occurrence_retention : float
        Maximum loss borne by the operator per individual event (NOK).
    annual_aggregate_retention : float
        Maximum total loss borne by the operator across all events in a year.
        When the aggregate is exhausted the captive / reinsurers absorb excess.
    """
    name: str
    per_occurrence_retention: float = 0.0
    annual_aggregate_retention: float = float("inf")


@dataclass
class ReinsuranceLayer:
    """
    A single reinsurance or captive layer in the insurance tower.

    Attributes
    ----------
    name : str
        Layer label, e.g. "1st XS Layer".
    attachment_point : float
        Loss amount above which this layer begins to respond (NOK).
    limit : float
        Maximum recovery from this layer per occurrence (NOK).
    participation_pct : float
        Fraction of the layer placed (0–100 %).  100 = fully placed.
    estimated_premium : float
        Annual estimated reinsurance premium for this layer (NOK).
    """
    name: str
    attachment_point: float
    limit: float
    participation_pct: float = 100.0
    estimated_premium: float = 0.0

    def recovery(self, gross_loss: np.ndarray) -> np.ndarray:
        """
        Compute reinsurance recovery for given gross loss array.

        Parameters
        ----------
        gross_loss : np.ndarray
            Gross loss values (any shape).

        Returns
        -------
        np.ndarray
            Recovery amounts (same shape as gross_loss).
        """
        xs = np.maximum(gross_loss - self.attachment_point, 0.0)
        capped = np.minimum(xs, self.limit)
        return capped * (self.participation_pct / 100.0)


# ─────────────────────────────────────────────────────────────────────────────
# Composite structure
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CaptiveStructure:
    """
    Complete PCC captive insurance structure definition.

    Attributes
    ----------
    operator_name : str
    retention : RetentionLayer
        Operator's self-insured retention (first layer).
    captive_layer : Optional[ReinsuranceLayer]
        The captive cell layer sitting XS of the retention.
    reinsurance_layers : List[ReinsuranceLayer]
        External reinsurance layers above the captive layer.
    """
    operator_name: str
    retention: RetentionLayer
    captive_layer: Optional[ReinsuranceLayer] = None
    reinsurance_layers: List[ReinsuranceLayer] = field(default_factory=list)

    def compute_net_loss(self, gross_losses: np.ndarray) -> np.ndarray:
        """
        Compute operator net loss after all recoveries.

        All layers respond to GROSS losses (industry-standard XL tower
        structure).  Each layer's attachment_point is a gross attachment,
        so all recoveries are calculated from the original gross amount
        and then subtracted to arrive at net.

        Parameters
        ----------
        gross_losses : np.ndarray
            Shape (N,) or (N, T) gross annual losses.

        Returns
        -------
        np.ndarray
            Net loss retained by operator (same shape).
        """
        gross = gross_losses.astype(float)
        net = gross.copy()

        # Captive layer recovery (XS retention, responds to gross losses)
        if self.captive_layer is not None:
            net = net - self.captive_layer.recovery(gross)

        # External reinsurance layers (each responds to gross losses)
        for layer in self.reinsurance_layers:
            net = net - layer.recovery(gross)

        return np.maximum(net, 0.0)

    def compute_captive_loss(self, gross_losses: np.ndarray) -> np.ndarray:
        """
        Compute the net loss absorbed by the captive cell.

        Returns
        -------
        np.ndarray
            Captive cell loss (same shape as gross_losses).
        """
        if self.captive_layer is None:
            return np.zeros_like(gross_losses, dtype=float)
        return self.captive_layer.recovery(gross_losses.astype(float))

    def compute_reinsured_loss(self, gross_losses: np.ndarray) -> np.ndarray:
        """
        Compute total recoveries from external reinsurance layers.

        Each external layer responds to GROSS losses via its own attachment.

        Returns
        -------
        np.ndarray
            Total external reinsurance recovery (same shape as gross_losses).
        """
        if not self.reinsurance_layers:
            return np.zeros_like(gross_losses, dtype=float)

        gross = gross_losses.astype(float)
        total_ri = np.zeros_like(gross, dtype=float)
        for layer in self.reinsurance_layers:
            total_ri += layer.recovery(gross)

        return total_ri

    def capital_requirement(self, sim: SimulationResults) -> float:
        """
        Estimate captive cell capital requirement.

        Uses the 99.5th percentile of the captive net loss distribution as
        the Solvency II-inspired SCR proxy.

        Parameters
        ----------
        sim : SimulationResults
            Monte Carlo results containing annual_losses.

        Returns
        -------
        float
            Required capital in NOK.
        """
        captive_losses = self.compute_captive_loss(sim.annual_losses)
        flat = captive_losses.flatten()
        scr = float(np.percentile(flat, 99.5))
        expected = float(flat.mean())
        # Capital = SCR net of expected loss (technical provisions fund expected)
        return max(0.0, scr - expected)

    def annual_reinsurance_premium(self) -> float:
        """Sum all layer estimated premiums."""
        total = 0.0
        if self.captive_layer:
            total += self.captive_layer.estimated_premium
        for layer in self.reinsurance_layers:
            total += layer.estimated_premium
        return total
