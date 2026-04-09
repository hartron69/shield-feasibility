"""
core/ — AquaGuard physical transfer engine package

Sprint 1: Modularized from aquaguard_three_nets_pathogen_coast_status_v1.22b.py
Physics and numerical methods are unchanged from the baseline.

Module layout:
  geometry.py          — Net, StraightCoastline dataclasses
  scenarios.py         — User-editable scenario settings
  flow_engine.py       — CoastalThreeNetFlowModel (local potential-flow + Loland)
  risk_engine.py       — RiskEngine (thresholds, classification, auto-calibration)
  pathogen_transport.py — PathogenParticle, CoastalpathogenTimeMarcher
  reporting.py         — Reporter (plots, figures)
  io_utils.py          — CSV/JSON output, summary validation
"""
