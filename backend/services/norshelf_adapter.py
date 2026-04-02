"""
backend/services/norshelf_adapter.py

BarentsWatch NorShelf-adapter — henter havstrøm, temperatur og bølgehøyde
for en gitt (lat, lon) og leverer dem til ILA input_builder.

Endepunkter
-----------
  NorShelf strøm:       GET /v2/geodata/ocean/currents?lat=&lon=
  Overflatetemperatur:  GET /v2/geodata/ocean/temperature?lat=&lon=
  Bølge (Hs):           GET /v2/geodata/weather/wave?lat=&lon=

Oppdateringsfrekvens BW: 1 time
Cache TTL: 55 min (litt under BW-oppdatering)

DQI-verdier
-----------
  1  Live BW-data, hentet denne timen
  2  Cache > 55 min (BW midlertidig utilgjengelig)
  3  Fallback-estimat (BW utilgjengelig > 6 t)

Cache-nøkkel: (lat, lon) avrundet til 2 desimaler (≈ 1 km grid).
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import requests

# Re-use the OAuth2 token function from the existing BW client
from backend.services.barentswatch_client import (
    BW_API_BASE,
    _REQUEST_TIMEOUT,
    _get_token,
)

logger = logging.getLogger(__name__)

# ── Konstanter ────────────────────────────────────────────────────────────────

_TTL_LIVE_S:     float = 55 * 60      # 55 min — data regnes som "live" (DQI=1)
_TTL_STALE_S:    float = 6 * 60 * 60  # 6 t   — stale cache gir DQI=2; eldre → DQI=3
_COORD_DECIMALS: int   = 2            # avrunding for cache-nøkkel (~1 km grid)

# Klimatologiske fallback-verdier for norskekysten (Møre og Romsdal, vår)
_FALLBACK = {
    "u":       0.05,   # m/s svak østgående strøm
    "v":       0.03,   # m/s svak nordgående strøm
    "t_water": 6.5,    # °C overflatetemperatur april
    "hs":      0.8,    # m signifikant bølgehøyde, typisk vår/indre farvann
}


# ── Dataklasse ────────────────────────────────────────────────────────────────

@dataclass
class NorShelfData:
    """Havoseanografiske øyeblikksdata for én lokalitet."""
    u:          float   # Østgående strøm  (m/s)
    v:          float   # Nordgående strøm  (m/s)
    t_water:    float   # Overflatetemperatur (°C)
    hs:         float   # Signifikant bølgehøyde (m)
    dqi:        int     # 1=live, 2=stale cache, 3=fallback
    fetched_at: float   # Unix-epoch da dataene ble hentet fra BW (0 = aldri)

    def current_speed(self) -> float:
        """Strømhastighet |u,v| (m/s)."""
        return math.sqrt(self.u ** 2 + self.v ** 2)

    def to_dict(self) -> dict:
        return {
            "u":            self.u,
            "v":            self.v,
            "t_water":      self.t_water,
            "hs":           self.hs,
            "dqi":          self.dqi,
            "current_speed": round(self.current_speed(), 4),
        }


def _fallback_data(dqi: int = 3) -> NorShelfData:
    return NorShelfData(
        u=_FALLBACK["u"],
        v=_FALLBACK["v"],
        t_water=_FALLBACK["t_water"],
        hs=_FALLBACK["hs"],
        dqi=dqi,
        fetched_at=0.0,
    )


# ── In-process cache ──────────────────────────────────────────────────────────

# Key: (lat_rounded, lon_rounded) → {"data": NorShelfData, "fetched_at": float}
_CACHE: Dict[Tuple[float, float], Dict] = {}


def _cache_key(lat: float, lon: float) -> Tuple[float, float]:
    return (round(lat, _COORD_DECIMALS), round(lon, _COORD_DECIMALS))


def _cache_dqi(fetched_at: float, now: float) -> int:
    age = now - fetched_at
    if age < _TTL_LIVE_S:
        return 1
    if age < _TTL_STALE_S:
        return 2
    return 3


# ── BW API-kall ───────────────────────────────────────────────────────────────

def _fetch_one(endpoint: str, lat: float, lon: float, token: str) -> Optional[dict]:
    """Henter ett BW NorShelf-endepunkt. Returnerer parsed JSON eller None."""
    url = f"{BW_API_BASE}{endpoint}"
    try:
        resp = requests.get(
            url,
            params={"lat": lat, "lon": lon},
            headers={"Authorization": f"Bearer {token}"},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("NorShelf %s failed for (%.3f, %.3f): %s", endpoint, lat, lon, exc)
        return None


def _parse_u_v(payload: Optional[dict]) -> Tuple[Optional[float], Optional[float]]:
    """
    Tolker strøm-responsen fra BW.

    BW returnerer liste av tidspunkter med u/v — vi tar siste/første element.
    Mulige feltnavn observert i BW-dokumentasjon:
      {"u": ..., "v": ...}  eller  {"eastward": ..., "northward": ...}
    Payload kan være et dict eller en liste av dict (tidsserie).
    """
    if payload is None:
        return None, None
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    if not isinstance(payload, dict):
        return None, None
    u = payload.get("u") or payload.get("eastward") or payload.get("uCurrentSpeed")
    v = payload.get("v") or payload.get("northward") or payload.get("vCurrentSpeed")
    try:
        return float(u), float(v)
    except (TypeError, ValueError):
        return None, None


def _parse_temperature(payload: Optional[dict]) -> Optional[float]:
    if payload is None:
        return None
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    if not isinstance(payload, dict):
        return None
    val = (
        payload.get("temperature")
        or payload.get("value")
        or payload.get("seaSurfaceTemperature")
        or payload.get("waterTemperature")
    )
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _parse_hs(payload: Optional[dict]) -> Optional[float]:
    if payload is None:
        return None
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    if not isinstance(payload, dict):
        return None
    val = (
        payload.get("hs")
        or payload.get("significantWaveHeight")
        or payload.get("Hs")
        or payload.get("waveHeight")
    )
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _fetch_norshelf(lat: float, lon: float) -> Optional[NorShelfData]:
    """
    Henter alle tre NorShelf-endepunkter og returnerer NorShelfData (DQI=1)
    eller None hvis BW er utilgjengelig.
    """
    token = _get_token()
    if token is None:
        logger.debug("NorShelf: ingen BW-token — hopper over live-henting")
        return None

    now = time.time()

    curr  = _fetch_one("/v2/geodata/ocean/currents",    lat, lon, token)
    temp  = _fetch_one("/v2/geodata/ocean/temperature", lat, lon, token)
    wave  = _fetch_one("/v2/geodata/weather/wave",      lat, lon, token)

    u, v   = _parse_u_v(curr)
    t_water = _parse_temperature(temp)
    hs     = _parse_hs(wave)

    # Aksepter delvis respons — bruk fallback for manglende felt
    if u is None:
        u = _FALLBACK["u"]
    if v is None:
        v = _FALLBACK["v"]
    if t_water is None:
        t_water = _FALLBACK["t_water"]
    if hs is None:
        hs = _FALLBACK["hs"]

    # Hvis alle tre kall feilet: returner None (trigger cache/fallback-logikk)
    if curr is None and temp is None and wave is None:
        return None

    return NorShelfData(u=u, v=v, t_water=t_water, hs=hs, dqi=1, fetched_at=now)


# ── Offentlig API ─────────────────────────────────────────────────────────────

def get_norshelf(lat: float, lon: float) -> NorShelfData:
    """
    Returnerer NorShelf-data for (lat, lon) med cache og DQI-logikk.

    Prioritert:
      1. Live BW-data (DQI=1) — hvis < 55 min gammel i cache
      2. Stale cache (DQI=2) — hvis 55 min < alder < 6 t
      3. Fallback-estimat (DQI=3) — klimatologisk gjennomsnitt
    """
    key = _cache_key(lat, lon)
    now = time.time()

    cached = _CACHE.get(key)
    if cached is not None:
        dqi = _cache_dqi(cached["fetched_at"], now)
        if dqi == 1:
            # Cache er fersk — returner direkte
            return cached["data"]
        # Cache er stale — prøv live BW
        fresh = _fetch_norshelf(lat, lon)
        if fresh is not None:
            _CACHE[key] = {"data": fresh, "fetched_at": fresh.fetched_at}
            return fresh
        # BW utilgjengelig — oppdater DQI på eksisterende data
        stale = NorShelfData(
            u=cached["data"].u,
            v=cached["data"].v,
            t_water=cached["data"].t_water,
            hs=cached["data"].hs,
            dqi=dqi,
            fetched_at=cached["fetched_at"],
        )
        return stale

    # Ingen cache — hent fra BW
    fresh = _fetch_norshelf(lat, lon)
    if fresh is not None:
        _CACHE[key] = {"data": fresh, "fetched_at": fresh.fetched_at}
        return fresh

    # BW utilgjengelig og ingen cache — returner fallback
    return _fallback_data(dqi=3)


def clear_cache() -> None:
    """Tøm cache — brukes i tester."""
    _CACHE.clear()
