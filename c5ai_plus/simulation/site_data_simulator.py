"""
C5AI+ v5.0 – Site Data Simulator.

Generates plausible synthetic C5AIOperatorInput for testing and demos.

Domain logic:
  - Temperature : T(m) = T_mean + A*sin(2π(m-3)/12) + ε
  - HAB         : higher P in summer, higher at open_coast, higher in warm years
  - Lice        : spring + autumn peaks, correlated with temp, reduced by treatment
  - Jellyfish   : summer peak, low base rate
  - Pathogen    : year-round low base, slight winter elevation
"""

from __future__ import annotations

import math
import random
from datetime import date
from typing import List, Optional

from c5ai_plus.data_models.biological_input import (
    C5AIOperatorInput,
    EnvironmentalObservation,
    HABAlert,
    JellyfishObservation,
    LiceObservation,
    PathogenObservation,
    SiteMetadata,
)


_FJORD_EXPOSURES = ("open_coast", "semi_exposed", "sheltered")
_HAB_SPECIES = ["Chrysochromulina leadbeateri", "Karenia mikimotoi", None]
_PATHOGEN_TYPES = ["ILA", "PD", "Moritella_viscosa", "Aeromonas_salmonicida"]


class SiteDataSimulator:
    """
    Generate synthetic C5AIOperatorInput for any number of sites and years.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility.
    base_latitude : float
        Approximate latitude for the site cluster (affects temperatures).
    """

    def __init__(self, seed: int = 42, base_latitude: float = 63.5):
        self._rng = random.Random(seed)
        self._base_lat = base_latitude

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_operator_input(
        self,
        operator_id: str = "SIM_OP_001",
        operator_name: str = "Synthetic Salmon AS",
        n_sites: int = 3,
        n_years: int = 5,
        base_year: int = 2020,
        biomass_per_site_tonnes: float = 3_000.0,
        biomass_value_nok_per_tonne: float = 65_000.0,
    ) -> C5AIOperatorInput:
        """
        Generate a complete C5AIOperatorInput with synthetic observations.

        Parameters
        ----------
        n_sites : int
            Number of production sites to simulate.
        n_years : int
            Number of calendar years of historical observations.
        base_year : int
            First observation year.

        Returns
        -------
        C5AIOperatorInput
        """
        sites = self._make_sites(
            operator_id, n_sites, biomass_per_site_tonnes, biomass_value_nok_per_tonne
        )

        env_obs: List[EnvironmentalObservation] = []
        hab_alerts: List[HABAlert] = []
        lice_obs: List[LiceObservation] = []
        jellyfish_obs: List[JellyfishObservation] = []
        pathogen_obs: List[PathogenObservation] = []

        for site in sites:
            for yr in range(base_year, base_year + n_years):
                temps = self._monthly_temperatures(site, yr)
                env_obs.extend(self._make_env_obs(site, yr, temps))
                hab_alerts.extend(self._make_hab_alerts(site, yr, temps))
                lice_obs.extend(self._make_lice_obs(site, yr, temps))
                jellyfish_obs.extend(self._make_jellyfish_obs(site, yr))
                pathogen_obs.extend(self._make_pathogen_obs(site, yr))

        return C5AIOperatorInput(
            operator_id=operator_id,
            operator_name=operator_name,
            sites=sites,
            env_observations=env_obs,
            lice_observations=lice_obs,
            hab_alerts=hab_alerts,
            jellyfish_observations=jellyfish_obs,
            pathogen_observations=pathogen_obs,
            forecast_years=5,
        )

    # ── Site generation ───────────────────────────────────────────────────────

    def _make_sites(
        self,
        operator_id: str,
        n_sites: int,
        biomass_tonnes: float,
        value_nok_per_tonne: float,
    ) -> List[SiteMetadata]:
        sites = []
        for i in range(n_sites):
            exposure = _FJORD_EXPOSURES[i % len(_FJORD_EXPOSURES)]
            sites.append(
                SiteMetadata(
                    site_id=f"{operator_id}_S{i+1:02d}",
                    site_name=f"Site {i+1}",
                    latitude=self._base_lat + self._rng.uniform(-0.5, 0.5),
                    longitude=7.0 + self._rng.uniform(-1.0, 1.0),
                    species="Atlantic Salmon",
                    biomass_tonnes=biomass_tonnes * self._rng.uniform(0.8, 1.2),
                    biomass_value_nok=biomass_tonnes * value_nok_per_tonne,
                    years_in_operation=self._rng.randint(3, 15),
                    fjord_exposure=exposure,
                )
            )
        return sites

    # ── Temperature model ─────────────────────────────────────────────────────

    def _monthly_temperatures(
        self, site: SiteMetadata, year: int
    ) -> List[float]:
        """T(m) = T_mean + A*sin(2π(m-3)/12) + ε"""
        T_mean = 10.5 - (site.latitude - 60.0) * 0.3   # colder further north
        A = 5.5
        warm_year_factor = self._rng.gauss(0, 0.8)
        temps = []
        for m in range(1, 13):
            seasonal = A * math.sin(2 * math.pi * (m - 3) / 12)
            noise = self._rng.gauss(0, 0.5)
            temps.append(round(T_mean + seasonal + noise + warm_year_factor * 0.3, 2))
        return temps

    # ── Environmental observations ────────────────────────────────────────────

    def _make_env_obs(
        self, site: SiteMetadata, year: int, temps: List[float]
    ) -> List[EnvironmentalObservation]:
        obs = []
        for m, temp in enumerate(temps, start=1):
            if self._rng.random() < 0.15:   # 15% chance of missing month
                continue
            salinity = self._rng.uniform(30, 35)
            chlorophyll = max(0.0, self._rng.gauss(2.0 + (1.5 if 4 <= m <= 8 else 0.0), 1.0))
            obs.append(
                EnvironmentalObservation(
                    site_id=site.site_id,
                    year=year,
                    month=m,
                    sea_temp_celsius=temp,
                    salinity_ppt=round(salinity, 2),
                    chlorophyll_ug_l=round(chlorophyll, 3),
                    current_speed_ms=round(self._rng.uniform(0.05, 0.40), 3),
                )
            )
        return obs

    # ── HAB alerts ────────────────────────────────────────────────────────────

    def _make_hab_alerts(
        self, site: SiteMetadata, year: int, temps: List[float]
    ) -> List[HABAlert]:
        """HAB probability higher in summer, at open_coast, in warm years."""
        alerts = []
        mean_summer_temp = sum(temps[5:9]) / 4   # Jun–Sep
        base_p = 0.06 if site.fjord_exposure == "sheltered" else (
            0.12 if site.fjord_exposure == "semi_exposed" else 0.18
        )
        # Temperature bonus
        if mean_summer_temp > 14.0:
            base_p *= 1.4
        for m in range(4, 10):   # Apr–Sep only
            if self._rng.random() < base_p / 6:
                level = self._rng.choice(["low", "medium", "high"])
                loss = None
                if level in ("high",):
                    loss = float(self._rng.uniform(0.5e6, 5e6))
                alerts.append(
                    HABAlert(
                        site_id=site.site_id,
                        year=year,
                        month=m,
                        alert_level=level,
                        species=self._rng.choice(_HAB_SPECIES),
                        duration_days=self._rng.randint(3, 21),
                        loss_nok=loss,
                    )
                )
        return alerts

    # ── Lice observations ─────────────────────────────────────────────────────

    def _make_lice_obs(
        self, site: SiteMetadata, year: int, temps: List[float]
    ) -> List[LiceObservation]:
        """Spring + autumn peaks, reduced by treatment."""
        obs = []
        for week in range(1, 53):
            month = min(12, (week - 1) // 4 + 1)
            temp = temps[month - 1]
            # Spring (wk 12-20) and autumn (wk 36-44) peaks
            season_factor = (
                1.8 if 12 <= week <= 20 else
                1.5 if 36 <= week <= 44 else
                0.6
            )
            temp_factor = max(0.3, temp / 12.0)
            base_lice = self._rng.gauss(0.3 * season_factor * temp_factor, 0.1)
            base_lice = max(0.0, base_lice)
            treatment = base_lice > 0.5 and self._rng.random() < 0.7
            if treatment:
                base_lice *= self._rng.uniform(0.2, 0.5)
            obs.append(
                LiceObservation(
                    site_id=site.site_id,
                    year=year,
                    week=week,
                    avg_lice_per_fish=round(base_lice, 3),
                    treatment_applied=treatment,
                    treatment_type=self._rng.choice(["bath", "in-feed", "mechanical"]) if treatment else None,
                )
            )
        return obs

    # ── Jellyfish observations ────────────────────────────────────────────────

    def _make_jellyfish_obs(
        self, site: SiteMetadata, year: int
    ) -> List[JellyfishObservation]:
        obs = []
        for m in range(1, 13):
            # Summer peak Jul–Sep
            p_bloom = 0.25 if 7 <= m <= 9 else 0.05
            if self._rng.random() < p_bloom:
                density = self._rng.uniform(1.0, 3.0)
                impact = self._rng.choice(["none", "minor", "moderate", "severe"])
                obs.append(
                    JellyfishObservation(
                        site_id=site.site_id,
                        year=year,
                        month=m,
                        density_index=round(density, 2),
                        impact_level=impact,
                    )
                )
        return obs

    # ── Pathogen observations ─────────────────────────────────────────────────

    def _make_pathogen_obs(
        self, site: SiteMetadata, year: int
    ) -> List[PathogenObservation]:
        obs = []
        # 1–2 events per year on average
        n_events = self._rng.randint(0, 2)
        for _ in range(n_events):
            week = self._rng.randint(1, 52)
            confirmed = self._rng.random() < 0.6
            obs.append(
                PathogenObservation(
                    site_id=site.site_id,
                    year=year,
                    week=week,
                    pathogen_type=self._rng.choice(_PATHOGEN_TYPES),
                    confirmed=confirmed,
                    mortality_rate=round(self._rng.uniform(0.01, 0.15), 3) if confirmed else None,
                )
            )
        return obs
