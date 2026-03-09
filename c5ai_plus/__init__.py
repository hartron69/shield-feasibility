"""
C5AI+ v5.0 – Biological Risk Forecasting Module for Aquaculture.

Architecture: Loosely coupled module that generates risk_forecast.json,
consumed optionally by the PCC Feasibility Tool's MonteCarloEngine.

Risk domains covered
--------------------
  – HAB  (Harmful Algal Bloom)
  – Lice (Sea lice burden)
  – Jellyfish (placeholder – Phase 2)
  – Pathogen (placeholder – Phase 2)

Learning loop (Phase 3)
-----------------------
  OBSERVE → PREDICT → ACT → MEASURE → LEARN
"""

__version__ = "5.0.0"
__all__ = ["pipeline"]
