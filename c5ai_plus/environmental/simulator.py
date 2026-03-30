"""C5AI+ v5.0 – Mock Environmental Site Simulator."""

from __future__ import annotations

from typing import Dict

from c5ai_plus.environmental.inputs import EnvironmentalSiteInput

_DEMO_ENVIRONMENTAL: Dict[str, dict] = {
    'KH_S01': dict(  # Kornstad — open coast, highest exposure
        site_id='KH_S01',
        dissolved_oxygen_mg_l=6.8,
        oxygen_saturation_pct=78.0,
        surface_temp_c=16.2,
        current_speed_ms=0.72,
        significant_wave_height_m=2.8,
        ice_risk_score=0.02,
        site_exposure_class='open',
    ),
    'KH_S02': dict(  # Leite — semi-exposed
        site_id='KH_S02',
        dissolved_oxygen_mg_l=8.2,
        oxygen_saturation_pct=92.0,
        surface_temp_c=12.4,
        current_speed_ms=0.38,
        significant_wave_height_m=1.1,
        ice_risk_score=0.05,
        site_exposure_class='semi',
    ),
    'KH_S03': dict(  # Hogsnes — sheltered
        site_id='KH_S03',
        dissolved_oxygen_mg_l=9.5,
        oxygen_saturation_pct=106.0,
        surface_temp_c=9.8,
        current_speed_ms=0.18,
        significant_wave_height_m=0.4,
        ice_risk_score=0.10,
        site_exposure_class='sheltered',
    ),
}


class MockEnvironmentalSimulator:
    """Return pre-calibrated EnvironmentalSiteInput for each demo site."""

    def simulate(self, site_id: str) -> EnvironmentalSiteInput:
        data = _DEMO_ENVIRONMENTAL.get(site_id)
        if data is None:
            raise ValueError(f"Unknown demo site_id: {site_id!r}")
        return EnvironmentalSiteInput(**data)

    def simulate_all(self) -> Dict[str, EnvironmentalSiteInput]:
        return {sid: self.simulate(sid) for sid in _DEMO_ENVIRONMENTAL}
