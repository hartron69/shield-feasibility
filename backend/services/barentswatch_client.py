"""
backend/services/barentswatch_client.py

BarentsWatch API client — fetches locality registration data from the
BarentsWatch Akvakulturregisteret, including the company (virksomhet)
linked to each locality.

Authentication:
  Set BW_CLIENT_ID and BW_CLIENT_SECRET environment variables to enable
  live API calls. Without credentials the client returns None and callers
  fall back to the locality config mock data.

Token endpoint:
  POST https://id.barentswatch.no/connect/token
  grant_type=client_credentials, scope=api

Locality endpoint:
  GET  /v1/overview/localities/{localityNo}
  Returns: name, companyName, organisationNumber, municipalityName,
           latitude, longitude, allowedBiomass, species, licenceRef, status
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BW_TOKEN_URL = "https://id.barentswatch.no/connect/token"
BW_API_BASE  = "https://www.barentswatch.no/bwapi"
_REQUEST_TIMEOUT = 6  # seconds

# Simple in-process token cache — avoids repeated token requests
_token_cache: dict = {"token": None, "expires_at": 0.0}


def _get_token() -> Optional[str]:
    """Obtain OAuth2 client-credentials token, cached until expiry."""
    client_id     = os.environ.get("BW_CLIENT_ID", "harald@fender.link:Shield Data Client")
    client_secret = os.environ.get("BW_CLIENT_SECRET", "")
    if not client_secret:
        return None

    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    try:
        resp = requests.post(
            BW_TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     client_id,
                "client_secret": client_secret,
                "scope":         "api",
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        _token_cache["token"]      = payload["access_token"]
        _token_cache["expires_at"] = now + payload.get("expires_in", 3600) - 60
        return _token_cache["token"]
    except Exception as exc:
        logger.warning("BarentsWatch token fetch failed: %s", exc)
        return None


def fetch_locality_registration(locality_no: int) -> Optional[dict]:
    """
    Fetch locality registration from BarentsWatch, including the company
    (virksomhet) that holds the licence for this locality.

    Returns a normalised dict on success, None if credentials are absent
    or the request fails. Callers must handle None gracefully.

    Returned keys (all may be None if absent in the API response):
        locality_no       int
        site_name         str   — locality name from BW
        company_name      str   — operator / rights holder
        org_number        str   — Norwegian org number (9 digits)
        municipality      str   — municipality name
        lat               float
        lon               float
        allowed_biomass   float — MTB in tonnes
        species           str
        licence_ref       str   — concession / registration reference
        status            str   — e.g. "I drift"
        bw_live           bool  — always True when this function succeeds
    """
    token = _get_token()
    if token is None:
        return None

    url = f"{BW_API_BASE}/v1/overview/localities/{locality_no}"
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code == 404:
            logger.info("BarentsWatch locality %s not found (404)", locality_no)
            return None
        resp.raise_for_status()
        raw = resp.json()
    except Exception as exc:
        logger.warning("BarentsWatch locality fetch failed for %s: %s", locality_no, exc)
        return None

    return {
        "locality_no":     raw.get("localityNo"),
        "site_name":       raw.get("name"),
        "company_name":    raw.get("companyName"),
        "org_number":      raw.get("organisationNumber"),
        "municipality":    raw.get("municipalityName"),
        "lat":             raw.get("latitude"),
        "lon":             raw.get("longitude"),
        "allowed_biomass": raw.get("allowedBiomass"),
        "species":         raw.get("species"),
        "licence_ref":     raw.get("licenceRef") or raw.get("registrationNumber"),
        "status":          raw.get("status"),
        "bw_live":         True,
    }
