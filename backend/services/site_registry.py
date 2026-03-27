"""
backend/services/site_registry.py

Single source of truth for BarentsWatch locality <-> Shield site_id mapping.

The registry is built at import time from c5ai_plus/Barentswatch/bw_config.py
(OPERATOR_LOCALITIES). It provides:

  SiteRecord                           -- immutable record for one registered site
  get_site_by_locality_no(n)           -> Optional[SiteRecord]
  get_site_by_site_id(s)               -> Optional[SiteRecord]
  resolve_barentswatch_record(n, name) -> (SiteRecord|None, warning|None)
  list_all_sites()                     -> list[SiteRecord]
  get_registry_summary()               -> dict  (API-serialisable)

Primary mapping rule: match by locality_no (BW primary key).
Name-based fallback: used only when locality_no is None; emits a warning string.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SiteRecord:
    """Immutable record describing one registered aquaculture site."""

    site_id: str
    locality_no: int
    site_name: str
    bw_locality_name: Optional[str]   # BW API name; initially same as site_name
    operator_id: str
    operator_name: str
    lat: float
    lon: float
    facility_type: str = "sea_cage"

    def to_dict(self) -> dict:
        return {
            "site_id":           self.site_id,
            "locality_no":       self.locality_no,
            "site_name":         self.site_name,
            "bw_locality_name":  self.bw_locality_name,
            "operator_id":       self.operator_id,
            "operator_name":     self.operator_name,
            "lat":               self.lat,
            "lon":               self.lon,
            "facility_type":     self.facility_type,
        }


# ---------------------------------------------------------------------------
# Registry build (singleton, constructed at import time)
# ---------------------------------------------------------------------------

def _build_registry() -> Tuple[Dict[int, SiteRecord], Dict[str, SiteRecord]]:
    """
    Read OPERATOR_LOCALITIES from bw_config.py and build two lookup dicts:
      _by_locality_no  : localityNo (int) -> SiteRecord
      _by_site_id      : site_id (str)    -> SiteRecord
    """
    from c5ai_plus.Barentswatch.bw_config import OPERATOR_LOCALITIES  # type: ignore

    by_locality: Dict[int, SiteRecord] = {}
    by_site_id: Dict[str, SiteRecord] = {}

    for op in OPERATOR_LOCALITIES:
        op_id   = op["operator_id"]
        op_name = op["operator_name"]

        for loc in op.get("localities", []):
            rec = SiteRecord(
                site_id=loc["site_id"],
                locality_no=int(loc["localityNo"]),
                site_name=loc["site_name"],
                bw_locality_name=loc.get("bw_locality_name", loc["site_name"]),
                operator_id=op_id,
                operator_name=op_name,
                lat=float(loc["lat"]),
                lon=float(loc["lon"]),
                facility_type=loc.get("facility_type", "sea_cage"),
            )
            by_locality[rec.locality_no] = rec
            by_site_id[rec.site_id] = rec

    return by_locality, by_site_id


_BY_LOCALITY_NO: Dict[int, SiteRecord]
_BY_SITE_ID: Dict[str, SiteRecord]
_BY_LOCALITY_NO, _BY_SITE_ID = _build_registry()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_site_by_locality_no(locality_no: int) -> Optional[SiteRecord]:
    """Return the SiteRecord for the given BW locality number, or None."""
    return _BY_LOCALITY_NO.get(locality_no)


def get_site_by_site_id(site_id: str) -> Optional[SiteRecord]:
    """Return the SiteRecord for the given Shield site_id, or None."""
    return _BY_SITE_ID.get(site_id)


def list_all_sites() -> List[SiteRecord]:
    """Return all registered SiteRecords (stable order by locality_no)."""
    return sorted(_BY_LOCALITY_NO.values(), key=lambda r: r.locality_no)


def resolve_barentswatch_record(
    locality_no: Optional[int],
    bw_name: Optional[str] = None,
) -> Tuple[Optional[SiteRecord], Optional[str]]:
    """
    Resolve a BarentsWatch observation to a SiteRecord.

    Primary rule  : match by locality_no (BW primary key).
    Fallback rule : case-insensitive name match when locality_no is None.

    Returns
    -------
    (record, warning)
      record  : SiteRecord if matched, else None
      warning : human-readable string when something is imperfect or failed
    """
    # --- Primary path: locality_no provided ---
    if locality_no is not None:
        rec = _BY_LOCALITY_NO.get(int(locality_no))
        if rec is not None:
            return rec, None
        return None, f"locality_no {locality_no} not in registry"

    # --- Fallback: name-based lookup ---
    if bw_name is not None:
        bw_lower = bw_name.strip().lower()
        matches = [
            r for r in _BY_LOCALITY_NO.values()
            if r.site_name.lower() == bw_lower
            or (r.bw_locality_name and r.bw_locality_name.lower() == bw_lower)
        ]
        if len(matches) == 1:
            return (
                matches[0],
                f"WARNING: matched by name '{bw_name}' — locality_no missing",
            )
        return (
            None,
            f"WARNING: name '{bw_name}' not uniquely matched",
        )

    # --- Neither provided ---
    return None, "WARNING: no locality_no or name provided"


def get_bw_coverage(site_id: str) -> Optional[dict]:
    """
    Return BW coverage metadata for a site_id.

    Best-effort: imports bw_quality_summary from the adapter; returns None if
    BW data is unavailable or the adapter is not importable.
    """
    try:
        from c5ai_plus.Barentswatch.bw_to_c5ai_adapter import bw_quality_summary  # type: ignore
        summary = bw_quality_summary()
        for entry in summary.get("sites", []):
            if entry.get("site_id") == site_id:
                return entry
    except Exception:
        pass
    return None


def validate_selected_sites(
    selected_sites: list,
    allow_facility_types: tuple = ("sea_cage",),
) -> list[str]:
    """
    Validate a list of SelectedSeaSiteInput objects against the registry.

    Returns a list of error strings. Empty list = valid.

    Checks:
      1. Each site_id exists in registry.
      2. If locality_no is provided, it matches the registry record for that site_id.
      3. No duplicate site_ids.
      4. facility_type is in allow_facility_types.
    """
    errors: list[str] = []
    seen_ids: set[str] = set()

    for sel in selected_sites:
        sid = sel.site_id

        # Duplicate check
        if sid in seen_ids:
            errors.append(f"Duplicate site_id: {sid}")
            continue
        seen_ids.add(sid)

        # Registry lookup
        rec = get_site_by_site_id(sid)
        if rec is None:
            errors.append(f"site_id '{sid}' not found in registry")
            continue

        # facility_type check
        if rec.facility_type not in allow_facility_types:
            errors.append(
                f"site_id '{sid}' has facility_type '{rec.facility_type}', "
                f"expected one of {allow_facility_types}"
            )

        # locality_no consistency
        if sel.locality_no is not None and sel.locality_no != rec.locality_no:
            errors.append(
                f"site_id '{sid}': provided locality_no {sel.locality_no} "
                f"does not match registry ({rec.locality_no})"
            )

    return errors


def get_registry_summary() -> dict:
    """
    Return a dict with all sites and operator info, suitable for an API response.

    Structure
    ---------
    {
      "site_count": int,
      "operator_count": int,
      "operators": [{"operator_id": ..., "operator_name": ..., "site_count": ...}],
      "sites": [SiteRecord.to_dict(), ...],
    }
    """
    all_sites = list_all_sites()

    # Collect unique operators
    operators: Dict[str, dict] = {}
    for rec in all_sites:
        if rec.operator_id not in operators:
            operators[rec.operator_id] = {
                "operator_id":   rec.operator_id,
                "operator_name": rec.operator_name,
                "site_count":    0,
            }
        operators[rec.operator_id]["site_count"] += 1

    return {
        "site_count":     len(all_sites),
        "operator_count": len(operators),
        "operators":      list(operators.values()),
        "sites":          [r.to_dict() for r in all_sites],
    }
