"""C5AI+ v5.0 – Mock Structural Site Simulator.

Produces realistic StructuralSiteInput for the 3 canonical demo sites.
"""

from __future__ import annotations

from typing import Dict

from c5ai_plus.structural.inputs import StructuralSiteInput

# Realistic values calibrated to site exposure class
_DEMO_STRUCTURAL: Dict[str, dict] = {
    'KH_S01': dict(  # Kornstad — open coast, highest structural load
        site_id='KH_S01',
        net_age_years=3.5,
        net_strength_residual_pct=72.0,
        mooring_inspection_score=0.55,
        deformation_load_index=0.62,
        anchor_line_condition=0.58,
        last_inspection_days_ago=210,
    ),
    'KH_S02': dict(  # Leite — semi-exposed
        site_id='KH_S02',
        net_age_years=1.8,
        net_strength_residual_pct=88.0,
        mooring_inspection_score=0.78,
        deformation_load_index=0.38,
        anchor_line_condition=0.80,
        last_inspection_days_ago=95,
    ),
    'KH_S03': dict(  # Hogsnes — sheltered, lowest load
        site_id='KH_S03',
        net_age_years=0.9,
        net_strength_residual_pct=96.0,
        mooring_inspection_score=0.92,
        deformation_load_index=0.18,
        anchor_line_condition=0.94,
        last_inspection_days_ago=42,
    ),
}


class MockStructuralSimulator:
    """Return pre-calibrated StructuralSiteInput for each demo site."""

    def simulate(self, site_id: str) -> StructuralSiteInput:
        data = _DEMO_STRUCTURAL.get(site_id)
        if data is None:
            raise ValueError(f"Unknown demo site_id: {site_id!r}")
        return StructuralSiteInput(**data)

    def simulate_all(self) -> Dict[str, StructuralSiteInput]:
        return {sid: self.simulate(sid) for sid in _DEMO_STRUCTURAL}
