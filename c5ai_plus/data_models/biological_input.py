"""
C5AI+ v5.0 – Input data models for biological and environmental observations.

These structures represent the data fed into C5AI+ forecasters.
They are kept separate from the PCC tool's input schema so C5AI+
can operate fully independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EnvironmentalObservation:
    """
    A single environmental observation at a site for one time period.

    Attributes
    ----------
    site_id : str
        Unique identifier for the site.
    year : int
        Calendar year of the observation.
    month : int
        Month (1–12) of the observation.
    sea_temp_celsius : Optional[float]
        Mean sea surface temperature in Celsius (None = missing).
    salinity_ppt : Optional[float]
        Salinity in parts per thousand (None = missing).
    chlorophyll_ug_l : Optional[float]
        Chlorophyll-a concentration µg/L – HAB precursor (None = missing).
    current_speed_ms : Optional[float]
        Mean current speed m/s (None = missing).
    """
    site_id: str
    year: int
    month: int
    sea_temp_celsius: Optional[float] = None
    salinity_ppt: Optional[float] = None
    chlorophyll_ug_l: Optional[float] = None
    current_speed_ms: Optional[float] = None


@dataclass
class LiceObservation:
    """
    Weekly or monthly sea lice count per site.

    Attributes
    ----------
    site_id : str
    year : int
    week : int
        ISO week number (1–53).
    avg_lice_per_fish : float
        Mean adult female lice per fish (regulatory threshold = 0.5 in Norway).
    treatment_applied : bool
        Whether a treatment was applied this period.
    treatment_type : Optional[str]
        "bath", "in-feed", "mechanical", "laser", or None.
    """
    site_id: str
    year: int
    week: int
    avg_lice_per_fish: float
    treatment_applied: bool = False
    treatment_type: Optional[str] = None


@dataclass
class HABAlert:
    """
    A recorded or reported harmful algal bloom alert.

    Attributes
    ----------
    site_id : str
    year : int
    month : int
    alert_level : str
        "low", "medium", "high", or "critical".
    species : Optional[str]
        Causative algal species if known (e.g. "Chrysochromulina leadbeateri").
    duration_days : Optional[int]
        Number of days the alert lasted.
    loss_nok : Optional[float]
        Recorded economic loss in NOK (if known).
    """
    site_id: str
    year: int
    month: int
    alert_level: str
    species: Optional[str] = None
    duration_days: Optional[int] = None
    loss_nok: Optional[float] = None


@dataclass
class SiteMetadata:
    """
    Static site descriptors consumed by C5AI+ feature engineering.

    Attributes
    ----------
    site_id : str
    site_name : str
    latitude : float
    longitude : float
    species : str
        Primary farmed species (e.g. "Atlantic Salmon").
    biomass_tonnes : float
        Maximum standing biomass capacity.
    biomass_value_nok : float
        Total standing biomass value in NOK (used for loss normalisation).
    years_in_operation : int
    fjord_exposure : str
        "open_coast", "semi_exposed", or "sheltered".
    """
    site_id: str
    site_name: str
    latitude: float
    longitude: float
    species: str
    biomass_tonnes: float
    biomass_value_nok: float
    years_in_operation: int = 5
    fjord_exposure: str = "semi_exposed"


@dataclass
class JellyfishObservation:
    """
    A recorded jellyfish observation at a site.

    Attributes
    ----------
    site_id : str
    year : int
    month : int
        Month (1–12) of the observation.
    density_index : float
        Relative bloom density (0 = none, 1 = low, 2 = moderate, 3 = severe).
    species : Optional[str]
        Dominant jellyfish species if identified (e.g. "Aurelia aurita").
    impact_level : Optional[str]
        "none", "minor", "moderate", "severe" – observed operational impact.
    """
    site_id: str
    year: int
    month: int
    density_index: float = 0.0
    species: Optional[str] = None
    impact_level: Optional[str] = None

    def __post_init__(self):
        if not (1 <= self.month <= 12):
            raise ValueError(f"month must be in [1, 12], got {self.month}")


@dataclass
class PathogenObservation:
    """
    A recorded pathogen event or confirmed disease observation at a site.

    Attributes
    ----------
    site_id : str
    year : int
    week : int
        ISO week number (1–53).
    pathogen_type : str
        E.g. "ILA", "PD", "Moritella_viscosa", "Aeromonas_salmonicida".
    confirmed : bool
        Whether the outbreak was laboratory-confirmed.
    mortality_rate : Optional[float]
        Fraction of biomass lost to disease (0–1), if measured.
    """
    site_id: str
    year: int
    week: int
    pathogen_type: str
    confirmed: bool = False
    mortality_rate: Optional[float] = None

    def __post_init__(self):
        if not (1 <= self.week <= 53):
            raise ValueError(f"week must be in [1, 53], got {self.week}")


@dataclass
class C5AIOperatorInput:
    """
    Top-level input container for a full C5AI+ run.

    One operator → one or more sites → environmental + biological timeseries.
    """
    operator_id: str
    operator_name: str
    sites: List[SiteMetadata]
    env_observations: List[EnvironmentalObservation] = field(default_factory=list)
    lice_observations: List[LiceObservation] = field(default_factory=list)
    hab_alerts: List[HABAlert] = field(default_factory=list)
    jellyfish_observations: List[JellyfishObservation] = field(default_factory=list)
    pathogen_observations: List[PathogenObservation] = field(default_factory=list)
    forecast_years: int = 5
