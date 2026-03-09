"""
Global configuration and constants for the PCC Feasibility Tool.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class Settings:
    # ── Simulation ────────────────────────────────────────────────────────────
    default_simulations: int = 10_000
    random_seed: int = 42
    projection_years: int = 5

    # ── Discount / Finance ────────────────────────────────────────────────────
    risk_free_rate: float = 0.04          # 4% p.a. – used for NPV & investment income
    cost_of_capital_rate: float = 0.06   # 6% Solvency II CoC for risk margin
    inflation_rate: float = 0.025        # 2.5% cost inflation p.a.

    # ── SCR (simplified Solvency II) ─────────────────────────────────────────
    scr_confidence_level: float = 0.995   # 99.5 % VaR
    risk_margin_factor: float = 0.06      # CoC applied to SCR to derive Risk Margin
    technical_provision_load: float = 0.10  # 10 % prudence margin on best-estimate

    # ── PCC Captive defaults (overridden by operator input if provided) ────────
    pcc_setup_cost: float = 1_250_000      # NOK – Legal, regulatory, actuarial set-up
    pcc_annual_cell_fee: float = 475_000   # NOK – Annual cell management / rent
    pcc_fronting_fee_rate: float = 0.03    # 3 % of fronted premium
    pcc_premium_discount: float = 0.22    # 22 % saving vs full-market premium
    pcc_investment_return: float = 0.04   # Return on cell reserves

    # ── PCC Calibration (Sprint 8) – reinsurance structure defaults ──────────
    pcc_default_retention_nok: float = 25_000_000    # Annual aggregate XL retention
    pcc_ri_limit_nok: float = 150_000_000            # XL limit above retention
    pcc_ri_loading_factor: float = 2.5               # Burning-cost loading for RI premium
    target_market_loss_ratio: float = 0.65           # Benchmark: E[loss] / LR

    # ── Hybrid strategy defaults ───────────────────────────────────────────────
    hybrid_retention_pct: float = 0.25    # 25 % of expected loss retained
    hybrid_premium_discount: float = 0.30  # 30 % reduction on ceded portion

    # ── Self-insurance defaults ───────────────────────────────────────────────
    self_insurance_reserve_factor: float = 1.5   # Reserve = 1.5× expected annual loss
    self_insurance_admin_rate: float = 0.015      # 1.5 % of TIV for administration

    # ── Suitability thresholds ────────────────────────────────────────────────
    min_premium_for_captive: float = 5_250_000    # NOK – absolutt nedre grense
    ideal_premium_for_captive: float = 10_500_000 # NOK
    max_cv_for_captive: float = 1.0            # Loss coefficient of variation
    min_years_commitment: int = 5

    # ── Reporting / Branding ─────────────────────────────────────────────────
    brand_navy: tuple = (0.09, 0.18, 0.35)      # RGB normalised (deep navy)
    brand_teal: tuple = (0.05, 0.56, 0.60)      # RGB normalised (teal)
    brand_gold: tuple = (0.80, 0.60, 0.10)      # RGB normalised (gold accent)
    brand_light_grey: tuple = (0.94, 0.94, 0.94)
    brand_dark_grey: tuple = (0.30, 0.30, 0.30)

    report_author: str = "Shield Risk Consulting"
    report_classification: str = "CONFIDENTIAL – Board Use Only"


# Module-level singleton
SETTINGS = Settings()
