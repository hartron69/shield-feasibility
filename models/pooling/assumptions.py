"""
PoolingAssumptions – configuration for multi-operator PCC pool feasibility analysis.

v2.1 known simplifications (tracked in KNOWN_SIMPLIFICATIONS):
  1. Synthetic members: actual peer data not available; parameters perturbed from operator
  2. Correlation: rank-based blending → approximate Pearson = rho (not Gaussian copula)
  3. Common shock: Binomial member count (simplified contagion model)
  4. Pooled RI premium: loading-factor method (not actuarial RI pricing)
"""

from __future__ import annotations

from dataclasses import dataclass


# v2.1 transparency record — surfaced in API responses
KNOWN_SIMPLIFICATIONS = [
    "Synthetic members: parameters perturbed from operator (actual peer data not loaded)",
    "Correlation: rank-based blending → approximate Pearson = rho (Gaussian copula not used; "
    "simultaneous catastrophe losses may be underestimated)",
    "Common shock: Binomial member count (simplified; contagion network not modelled)",
    "Pooled RI premium: loading-factor burning-cost method (not actuarially priced from "
    "reinsurer's perspective)",
]


@dataclass
class PoolingAssumptions:
    """Parameters for the pooled PCC scenario."""

    # ── Pool structure ────────────────────────────────────────────────────────
    enabled: bool = False
    n_members: int = 4                       # total pool members (incl. operator)
    inter_member_correlation: float = 0.25   # pairwise loss correlation ρ ∈ [0, 0.95]
    similarity_spread: float = 0.15          # ±spread% variation in synthetic member params

    # ── Pooled reinsurance layer ──────────────────────────────────────────────
    pooled_retention_nok: float = 25_000_000      # aggregate pool retention
    pooled_ri_limit_nok: float = 400_000_000      # pool RI layer limit
    pooled_ri_loading_factor: float = 1.40        # lower loading than standalone (diversified)

    # ── Economics ─────────────────────────────────────────────────────────────
    shared_admin_saving_pct: float = 0.20         # admin cost reduction from shared governance
    allocation_basis: str = "expected_loss"        # "expected_loss" | "premium"

    # ── Reproducibility ───────────────────────────────────────────────────────
    rng_seed: int = 42

    def __post_init__(self) -> None:
        if not 2 <= self.n_members <= 10:
            raise ValueError(f"n_members must be 2–10, got {self.n_members}")
        if not 0.0 <= self.inter_member_correlation <= 0.95:
            raise ValueError("inter_member_correlation must be in [0.0, 0.95]")
        if not 0.0 <= self.similarity_spread <= 0.50:
            raise ValueError("similarity_spread must be in [0.0, 0.50]")
        if self.pooled_retention_nok <= 0:
            raise ValueError("pooled_retention_nok must be positive")
        if self.pooled_ri_limit_nok <= 0:
            raise ValueError("pooled_ri_limit_nok must be positive")
        if not 1.0 <= self.pooled_ri_loading_factor <= 3.0:
            raise ValueError("pooled_ri_loading_factor must be in [1.0, 3.0]")
        if not 0.0 <= self.shared_admin_saving_pct <= 0.50:
            raise ValueError("shared_admin_saving_pct must be in [0.0, 0.50]")
        if self.allocation_basis not in ("expected_loss", "premium"):
            raise ValueError("allocation_basis must be 'expected_loss' or 'premium'")

    @classmethod
    def default(cls) -> "PoolingAssumptions":
        return cls()

    @classmethod
    def conservative(cls) -> "PoolingAssumptions":
        """Higher correlation, higher RI loading, lower admin saving."""
        return cls(
            inter_member_correlation=0.40,
            pooled_ri_loading_factor=1.60,
            shared_admin_saving_pct=0.10,
        )

    @classmethod
    def optimistic(cls) -> "PoolingAssumptions":
        """Larger pool, lower correlation, better economics."""
        return cls(
            n_members=6,
            inter_member_correlation=0.15,
            pooled_ri_loading_factor=1.25,
            shared_admin_saving_pct=0.30,
        )
