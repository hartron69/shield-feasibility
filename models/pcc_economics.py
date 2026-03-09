"""
PCC Captive Economics – pure helpers and configurable assumptions.

All functions are stateless so they can be used independently in tests
and in the strategy model without coupling to operator or simulation data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Configurable assumption set
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PCCAssumptions:
    """
    Economic assumptions for a PCC captive cell structure.

    All monetary amounts are in NOK.  Rates are expressed as fractions
    (e.g. 0.03 = 3 %).  Defaults represent a 'base case' calibration
    suitable for a mid-size Norwegian aquaculture operator.
    """
    # ── Annual-aggregate XL reinsurance structure ──────────────────────────
    retention_nok: float = 25_000_000         # Cell retains up to this per year
    reinsurance_limit_nok: float = 150_000_000  # RI limit above retention

    # RI premium = E[RI recovery] × loading (accounts for RI expenses + margin).
    # Market-calibrated range: 1.25 (diversified pool) – 2.5 (single-risk worst case).
    # Default 1.75 = base case for a standalone captive with adequate loss data.
    ri_loading_factor: float = 1.75

    # ── Cell economics ─────────────────────────────────────────────────────
    fronting_fee_pct: float = 0.03            # % of ceded premium paid to fronter
    admin_fee_nok: float = 475_000            # Annual cell management / governance fee
    formation_cost_nok: float = 1_250_000     # One-time legal/regulatory setup cost
    investment_return_pct: float = 0.04       # Return on cell reserves
    premium_discount_pct: float = 0.22        # Savings vs. full-market premium

    # ── Capital / SCR ──────────────────────────────────────────────────────
    scr_confidence: float = 0.995             # VaR confidence for SCR
    tp_load: float = 0.10                     # Prudence loading on BEL (Technical Provisions)

    # ── Market premium calibration (optional) ─────────────────────────────
    use_market_premium_calibration: bool = False
    target_market_loss_ratio: float = 0.65    # benchmark = E[loss] / target_LR

    # ── Presets ────────────────────────────────────────────────────────────

    @classmethod
    def conservative(cls) -> "PCCAssumptions":
        """Lower retention, higher RI loading (2.5×), conservative premium discount."""
        return cls(
            retention_nok=15_000_000,
            ri_loading_factor=2.5,
            premium_discount_pct=0.15,
        )

    @classmethod
    def base(cls) -> "PCCAssumptions":
        """Default mid-case assumptions."""
        return cls()

    @classmethod
    def optimised(cls) -> "PCCAssumptions":
        """Higher retention accepted, best RI terms (1.25×), higher premium savings."""
        return cls(
            retention_nok=35_000_000,
            ri_loading_factor=1.25,
            premium_discount_pct=0.28,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Pure helper functions
# ─────────────────────────────────────────────────────────────────────────────

def apply_pcc_reinsurance_structure(
    gross_annual_losses: np.ndarray,
    retention: float,
    reinsurance_limit: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Split gross losses using an annual-aggregate XL reinsurance layer.

    The cell retains losses up to `retention` per year; RI recovers the
    excess up to `reinsurance_limit` per year.  This is the standard
    working layer structure for a captive-backed programme.

    Parameters
    ----------
    gross_annual_losses : np.ndarray  (any shape)
        Gross loss amounts.
    retention : float
        Annual aggregate retention (attachment point of RI layer).
    reinsurance_limit : float
        Maximum recovery from RI per year (limit of RI layer).

    Returns
    -------
    net_retained : np.ndarray  (same shape as input)
    ri_recovery  : np.ndarray  (same shape as input)
    """
    net_retained = np.minimum(gross_annual_losses, retention)
    ri_recovery = np.minimum(
        np.maximum(gross_annual_losses - retention, 0.0),
        reinsurance_limit,
    )
    return net_retained, ri_recovery


def compute_ri_premium(
    gross_annual_losses: np.ndarray,
    assumptions: PCCAssumptions,
) -> float:
    """
    Estimate the annual reinsurance premium using burning-cost × loading.

    E[RI recovery] is derived from the simulation; the loading factor
    accounts for RI expenses and underwriting profit margin.

    Parameters
    ----------
    gross_annual_losses : np.ndarray  shape (N,) or (N, T)
        Gross simulated annual losses.
    assumptions : PCCAssumptions

    Returns
    -------
    float : annual RI premium in NOK
    """
    _, ri_recovery = apply_pcc_reinsurance_structure(
        gross_annual_losses,
        assumptions.retention_nok,
        assumptions.reinsurance_limit_nok,
    )
    expected_ri_recovery = float(ri_recovery.mean())
    return expected_ri_recovery * assumptions.ri_loading_factor


def compute_net_var(
    net_annual_losses: np.ndarray,
    confidence: float = 0.995,
) -> float:
    """
    VaR of the per-simulation *mean annual* net retained loss distribution.

    If a 2-D array (N, T) is passed, we average across years first to get
    a per-simulation mean annual loss before computing the percentile.
    This is consistent with how the gross VaR is computed elsewhere.

    Parameters
    ----------
    net_annual_losses : np.ndarray  shape (N,) or (N, T)
    confidence : float  (e.g. 0.995 for 99.5 %)
    """
    if net_annual_losses.ndim == 2:
        per_sim = net_annual_losses.mean(axis=1)
    else:
        per_sim = net_annual_losses
    return float(np.percentile(per_sim, confidence * 100))


def calibrate_market_premium(
    expected_annual_loss: float,
    target_loss_ratio: float = 0.65,
) -> float:
    """
    Derive a benchmark premium from actuarial first principles.

    benchmark_premium = expected_annual_loss / target_loss_ratio

    A loss ratio of 0.65 means the insurer expects 65 NOK of losses per
    100 NOK of premium (35 NOK covers expenses and profit).

    Parameters
    ----------
    expected_annual_loss : float  (NOK)
    target_loss_ratio : float  (0 < LR < 1)
    """
    if target_loss_ratio <= 0 or target_loss_ratio >= 1:
        raise ValueError(f"target_loss_ratio must be in (0, 1), got {target_loss_ratio}")
    return expected_annual_loss / target_loss_ratio


def build_pcc_assumption_set(preset: str = "base") -> PCCAssumptions:
    """
    Factory returning a named preset.

    Valid presets: 'base', 'conservative', 'optimised'.
    """
    presets = {
        "base": PCCAssumptions.base,
        "conservative": PCCAssumptions.conservative,
        "optimised": PCCAssumptions.optimised,
    }
    if preset not in presets:
        raise ValueError(f"Unknown preset {preset!r}. Choose from {list(presets)}")
    return presets[preset]()
