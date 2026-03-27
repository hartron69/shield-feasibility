"""
backend/services/source_health.py

Builds source-level health summaries for each locality.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from backend.services.live_risk_mock import (
    get_locality_config,
    get_source_definitions,
    NOW,
)


def get_source_status(locality_id: str) -> dict:
    """Return sources list and health summary for a locality."""
    cfg = get_locality_config(locality_id)
    degraded_source = cfg.get("source_degraded")
    base_delay = cfg.get("sync_delay_hours", 1.0)
    sources = []

    for sdef in get_source_definitions():
        sid = sdef["source_id"]
        is_degraded = sid == degraded_source

        if is_degraded:
            status = "delayed"
            delay_h = 18.0
            records = 0
            last_error = "Timeout ved henting av miljødata fra BarentsWatch API"
        else:
            status = "ok"
            delay_h = base_delay
            # Simulate record counts per source
            records = {
                "bw_lice": 7, "bw_disease": 3, "bw_environmental": 12,
                "norkyst": 24, "c5ai_risk": 1,
            }.get(sid, 5)
            last_error = None

        last_sync = NOW - timedelta(hours=delay_h)
        contributes = status == "ok"

        sources.append({
            "source_id": sid,
            "source_name": sdef["source_name"],
            "source_type": sdef["source_type"],
            "status": status,
            "last_sync": last_sync.isoformat(),
            "records_received": records,
            "last_error": last_error,
            "contributes_to_risk": contributes,
            "freshness_hours": round(delay_h, 1),
        })

    failed = sum(1 for s in sources if s["status"] == "failed")
    delayed = sum(1 for s in sources if s["status"] == "delayed")
    if failed > 0:
        health_summary = "critical"
    elif delayed > 0:
        health_summary = "partial"
    else:
        health_summary = "all_ok"

    return {
        "locality_id": locality_id,
        "sources": sources,
        "health_summary": health_summary,
        "critical_failures": failed,
    }
