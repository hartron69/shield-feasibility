"""
config/live_risk_economics.py

Config-driven methodology for translating locality risk score deltas
into financial impact estimates (EL, SCR, indicative premium).

All parameters are explicit and auditable. Change any constant here to
recalibrate the entire Live Risk Economics pipeline.
"""

# ── Risk-to-EL translation ──────────────────────────────────────────────────

# Base annual EL rate at the reference risk score, as a fraction of TIV.
# Calibrated to ~2 % of TIV per year at risk score 50 for Norwegian aquaculture.
BASE_EL_RATE_AT_REF: float = 0.020
REFERENCE_RISK_SCORE: float = 50.0

# Linear EL elasticity: change in EL rate per risk score point.
# Derived: BASE_EL_RATE_AT_REF / REFERENCE_RISK_SCORE = 0.020 / 50 = 0.0004
# Interpretation: +10 pts risk on 100 M NOK TIV → +400 k NOK annual EL delta.
EL_ELASTICITY_PER_POINT: float = BASE_EL_RATE_AT_REF / REFERENCE_RISK_SCORE  # 0.0004

# Domain weights — must match the total risk aggregation formula in live_risk_mock.py.
# total = 0.35*bio + 0.25*struct + 0.25*env + 0.15*ops
DOMAIN_WEIGHTS: dict = {
    "biological":    0.35,
    "structural":    0.25,
    "environmental": 0.25,
    "operational":   0.15,
}

# ── SCR loading ─────────────────────────────────────────────────────────────

# SCR = current_annual_EL × SCR_LOADING.
# Derived from empirical VaR(99.5 %) / E[loss] ratio for single-locality
# aquaculture exposure (cat-dominated, heavy tail). Typical range 3.0–4.5.
SCR_LOADING: float = 3.5

# ── Premium loading ──────────────────────────────────────────────────────────

# Indicative market premium = current_annual_EL × PREMIUM_LOADING.
# Based on target market loss ratio ~57 %: 1 / 0.57 ≈ 1.75.
PREMIUM_LOADING: float = 1.75

# ── Locality financial profiles ───────────────────────────────────────────────
# In production these would come from a live operator database.
# biomass_tonnes:      average standing biomass (tonnes live weight)
# value_per_tonne_nok: applied biomass value (NOK / tonne)
# n_cages:             number of active pens at this locality
# cage_biomass_split:  optional list of relative biomass weights per pen;
#                      None → equal split across all pens

LOCALITY_FINANCIALS: dict = {
    "KH_S01": {
        "biomass_tonnes": 1_500,
        "value_per_tonne_nok": 68_000,
        "n_cages": 8,
        "cage_biomass_split": None,       # equal split
    },
    "KH_S02": {
        "biomass_tonnes": 1_200,
        "value_per_tonne_nok": 68_000,
        "n_cages": 6,
        "cage_biomass_split": None,
    },
    "KH_S03": {
        "biomass_tonnes": 900,
        "value_per_tonne_nok": 68_000,
        "n_cages": 6,
        "cage_biomass_split": None,
    },
    "LM_S01": {
        "biomass_tonnes": 1_800,
        "value_per_tonne_nok": 68_000,
        "n_cages": 10,
        "cage_biomass_split": None,
    },
}
