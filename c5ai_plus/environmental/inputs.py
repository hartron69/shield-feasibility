"""C5AI+ v5.0 – Environmental domain input schema."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnvironmentalSiteInput:
    """
    Observed environmental conditions for a single site.
    """
    site_id: str
    dissolved_oxygen_mg_l: float        # mg/L; safe range typically 7-12
    oxygen_saturation_pct: float        # %; safe range 80-120
    surface_temp_c: float               # Celsius
    current_speed_ms: float             # m/s
    significant_wave_height_m: float    # m
    ice_risk_score: float               # 0-1; 0 = no ice risk, 1 = severe
    site_exposure_class: str            # 'open' | 'semi' | 'sheltered'

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> 'EnvironmentalSiteInput':
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
