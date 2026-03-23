"""
Smolt / RAS loss categories with expected loss shares per facility type.

Used by ScenarioEngine to break per-facility scenario losses into
domain-level categories (biofilter, oxygen, power, water quality, …).

``share_ras``  — share expected for closed RAS facilities
``share_flow`` — share expected for flow-through / hybrid facilities
"""

from __future__ import annotations

SMOLT_LOSS_CATEGORIES: dict = {
    "biofilter":     {"label": "Biofilter",        "share_ras": 0.22, "share_flow": 0.10},
    "oxygen":        {"label": "Oksygen/O₂",        "share_ras": 0.25, "share_flow": 0.30},
    "power":         {"label": "Strømforsyning",    "share_ras": 0.18, "share_flow": 0.20},
    "water_quality": {"label": "Vannkvalitet",      "share_ras": 0.15, "share_flow": 0.18},
    "biosecurity":   {"label": "Biosikkerhet",      "share_ras": 0.10, "share_flow": 0.12},
    "operational":   {"label": "Operasjonell",      "share_ras": 0.10, "share_flow": 0.10},
}
