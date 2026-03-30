"""
backend/services/live_risk_to_c5ai.py

Converts Live Risk mock time-series data into a C5AIOperatorInput
so the C5AI+ ForecastPipeline can be run with signals derived from
the Live Risk feed rather than static demo priors.
"""
from __future__ import annotations

from typing import List, Optional

from backend.services.live_risk_mock import get_locality_config, get_locality_data, DAYS

_KH_SITES = ["KH_S01", "KH_S02", "KH_S03"]
_SITE_META = {
    "KH_S01": {"biomass_tonnes": 3000, "biomass_value_nok": 195_000_000},
    "KH_S02": {"biomass_tonnes": 2500, "biomass_value_nok": 162_500_000},
    "KH_S03": {"biomass_tonnes": 2800, "biomass_value_nok": 182_000_000},
}


def _exposure_to_fjord_type(exposure: float) -> str:
    return "sheltered" if exposure <= 0.9 else "semi_exposed"


def _map_disease_name(name: str) -> str:
    mapping = {
        "Pancreas disease (PD)":           "PD",
        "Infectious salmon anaemia (ILA)": "ILA",
        "Moritella viscosa":               "Moritella_viscosa",
        "Aeromonas salmonicida":           "Aeromonas_salmonicida",
    }
    return mapping.get(name, name.replace(" ", "_"))


def build_c5ai_input_from_live_feed(
    locality_ids: Optional[List[str]] = None,
) -> "C5AIOperatorInput":
    """
    Build a C5AIOperatorInput from Live Risk mock time series.

    Converts daily lice, temperature, oxygen, salinity, and disease
    observations from live_risk_mock into the typed observation lists
    expected by C5AIOperatorInput and its forecasters.
    """
    from c5ai_plus.data_models.biological_input import (
        C5AIOperatorInput,
        EnvironmentalObservation,
        HABAlert,
        JellyfishObservation,
        LiceObservation,
        PathogenObservation,
        SiteMetadata,
    )

    ids = [lid for lid in (locality_ids or _KH_SITES) if lid in _SITE_META]
    if not ids:
        ids = list(_KH_SITES)

    sites: List[SiteMetadata] = []
    env_obs: List[EnvironmentalObservation] = []
    lice_obs: List[LiceObservation] = []
    pathogen_obs: List[PathogenObservation] = []

    for lid in ids:
        cfg = get_locality_config(lid)
        data = get_locality_data(lid)
        meta = _SITE_META[lid]

        sites.append(SiteMetadata(
            site_id=lid,
            site_name=cfg["name"],
            latitude=cfg["lat"],
            longitude=cfg["lon"],
            species="Atlantic Salmon",
            biomass_tonnes=meta["biomass_tonnes"],
            biomass_value_nok=meta["biomass_value_nok"],
            fjord_exposure=_exposure_to_fjord_type(cfg["exposure"]),
            years_in_operation=5,
        ))

        ts        = data["timestamps"]
        lice_ts   = data["lice"]
        temp_ts   = data["temperature"]
        oxy_ts    = data["oxygen"]
        sal_ts    = data["salinity"]
        disease_ts = data["disease"]

        # LiceObservation — weekly sample (every 7 days)
        for day in range(0, DAYS, 7):
            lv = lice_ts[day]
            if lv is None:
                continue
            dt = ts[day]
            week = min(53, max(1, (dt.timetuple().tm_yday + 6) // 7))
            disease_active = any(disease_ts[day: day + 7])
            treatment = lv > 0.5 or disease_active
            lice_obs.append(LiceObservation(
                site_id=lid,
                year=dt.year,
                week=week,
                avg_lice_per_fish=round(lv, 3),
                treatment_applied=treatment,
                treatment_type="bath" if treatment else None,
            ))

        # EnvironmentalObservation — monthly means
        for month in range(1, 13):
            month_temps, month_oxys, month_sals, month_year = [], [], [], None
            for day in range(DAYS):
                dt = ts[day]
                if dt.month == month:
                    month_year = dt.year
                    if temp_ts[day] is not None:
                        month_temps.append(temp_ts[day])
                    if oxy_ts[day] is not None:
                        month_oxys.append(oxy_ts[day])
                    if sal_ts[day] is not None:
                        month_sals.append(sal_ts[day])
            if month_year is None or not month_temps:
                continue
            env_obs.append(EnvironmentalObservation(
                site_id=lid,
                year=month_year,
                month=month,
                sea_temp_celsius=round(sum(month_temps) / len(month_temps), 2),
                salinity_ppt=round(sum(month_sals) / len(month_sals), 2) if month_sals else None,
                chlorophyll_ug_l=None,
                current_speed_ms=None,
            ))

        # PathogenObservation — from disease event in config
        disease_day = cfg.get("disease_day")
        disease_name = cfg.get("disease_name")
        if disease_day is not None and disease_name:
            dt = ts[disease_day]
            week = min(53, max(1, (dt.timetuple().tm_yday + 6) // 7))
            pathogen_obs.append(PathogenObservation(
                site_id=lid,
                year=dt.year,
                week=week,
                pathogen_type=_map_disease_name(disease_name),
                confirmed=True,
                mortality_rate=0.04,
            ))

    return C5AIOperatorInput(
        operator_id="KORNSTAD_HAVBRUK",
        operator_name="Kornstad Havbruk AS",
        sites=sites,
        env_observations=env_obs,
        lice_observations=lice_obs,
        hab_alerts=[],
        jellyfish_observations=[],
        pathogen_observations=pathogen_obs,
    )
