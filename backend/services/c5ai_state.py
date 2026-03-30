"""
C5AI+ run state — in-memory singleton.

Tracks the most recent C5AI+ pipeline run and whether the analysis is
considered "fresh" relative to the last time operator inputs changed.

In-memory only — resets on backend restart (acceptable for a single-session
feasibility tool). Thread-safe via a module-level lock.

Freshness rules
---------------
  missing  — C5AI+ has never been run in this session
  stale    — C5AI+ was run before the most recent input change
  fresh    — C5AI+ was run after (or at) the most recent input change
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

_lock = threading.Lock()

_c5ai_run_id: Optional[str] = None
_c5ai_last_run_at: Optional[datetime] = None
_inputs_last_updated_at: Optional[datetime] = None
_extra_run_meta: dict = {}
_last_forecast = None          # Optional[RiskForecast] — in-memory only
_live_risk_domain_fracs: dict = {}  # domain fractions from latest Live Risk overview


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_c5ai_run(run_id: Optional[str] = None) -> tuple[str, datetime]:
    """Record a completed C5AI+ pipeline run. Returns (run_id, run_at)."""
    global _c5ai_run_id, _c5ai_last_run_at
    with _lock:
        _c5ai_run_id = run_id or uuid.uuid4().hex[:12]
        _c5ai_last_run_at = _now()
        return _c5ai_run_id, _c5ai_last_run_at


def mark_inputs_updated() -> datetime:
    """Record that operator inputs have changed. Returns updated timestamp."""
    global _inputs_last_updated_at
    with _lock:
        _inputs_last_updated_at = _now()
        return _inputs_last_updated_at


def store_run_extra(extra: dict) -> None:
    """Store extra run metadata (site_ids, site_names, data_mode, etc.) under lock."""
    global _extra_run_meta
    with _lock:
        _extra_run_meta.update(extra)


def get_run_extra() -> dict:
    """Return a copy of the extra run metadata under lock."""
    with _lock:
        return dict(_extra_run_meta)


def store_forecast(forecast) -> None:
    """Store the most recent RiskForecast object from the C5AI+ pipeline."""
    global _last_forecast
    with _lock:
        _last_forecast = forecast


def get_forecast():
    """Return the stored RiskForecast, or None if C5AI+ has not been run."""
    with _lock:
        return _last_forecast


def store_domain_fracs(fracs: dict) -> None:
    """Store per-domain fractions derived from Live Risk overview."""
    global _live_risk_domain_fracs
    with _lock:
        _live_risk_domain_fracs = dict(fracs)


def get_domain_fracs() -> dict:
    """Return stored Live Risk domain fractions, or empty dict if not set."""
    with _lock:
        return dict(_live_risk_domain_fracs)


def get_status() -> dict:
    """Return current C5AI+ freshness status as a plain dict."""
    with _lock:
        run_id = _c5ai_run_id
        run_at = _c5ai_last_run_at
        inp_at = _inputs_last_updated_at

    if run_at is None:
        freshness = "missing"
        is_fresh = False
    elif inp_at is not None and run_at < inp_at:
        freshness = "stale"
        is_fresh = False
    else:
        freshness = "fresh"
        is_fresh = True

    return {
        "run_id":                  run_id,
        "c5ai_last_run_at":        run_at.isoformat() if run_at else None,
        "inputs_last_updated_at":  inp_at.isoformat() if inp_at else None,
        "is_fresh":                is_fresh,
        "freshness":               freshness,
    }
