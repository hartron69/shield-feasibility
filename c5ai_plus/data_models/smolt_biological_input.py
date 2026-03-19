"""
Biological input schema for smolt / RAS facilities.
Mirrors C5AIOperatorInput but with RAS-specific monitoring fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RASMonitoringData:
    """Real-time / periodic monitoring data from one RAS facility."""
    site_id: str
    site_name: str
    timestamp_iso: str

    # Water quality (monthly averages)
    dissolved_oxygen_mg_l:  Optional[float] = None
    co2_ppm:                Optional[float] = None
    ph:                     Optional[float] = None
    water_temp_c:           Optional[float] = None
    nitrate_umol_l:         Optional[float] = None
    nitrite_mg_l:           Optional[float] = None
    ammonia_mg_l:           Optional[float] = None
    turbidity_ntu:          Optional[float] = None

    # Biofilter status
    days_since_last_filter_maintenance: Optional[int]   = None
    biofilter_efficiency_pct:           Optional[float] = None   # 0–100

    # Power and backup
    backup_power_hours:     Optional[float] = None   # UPS + generator capacity
    grid_reliability_score: Optional[float] = None   # 0–1
    last_power_test_days:   Optional[int]   = None

    # Biological observations
    cataract_prevalence_pct: Optional[float] = None  # % fish with cataract
    agd_score_mean:          Optional[float] = None
    mortality_rate_7d_pct:   Optional[float] = None

    # Operational loading
    biomass_kg:              Optional[float] = None
    stocking_density_kg_m3:  Optional[float] = None
    feeding_rate_pct_bw_day: Optional[float] = None

    def as_dict(self) -> dict:
        """Return all fields as a plain dict (for alert rule evaluation)."""
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class SmoltC5AIInput:
    """Top-level input for the smolt C5AI+ pipeline."""
    operator_id:    str
    operator_name:  str
    sites:          List[RASMonitoringData] = field(default_factory=list)
    forecast_years: int = 5
