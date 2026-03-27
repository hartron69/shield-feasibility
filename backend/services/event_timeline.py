"""
backend/services/event_timeline.py

Generates risk event timelines for each locality by scanning for
threshold crossings, sync failures, and significant risk changes.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from backend.services.live_risk_mock import (
    get_locality_data,
    get_locality_config,
    slice_by_period,
    DAYS,
)

# ── Thresholds ─────────────────────────────────────────────────────────────────

LICE_WARN_THRESHOLD = 0.5
LICE_CRIT_THRESHOLD = 1.0
TEMP_WARN_THRESHOLD = 14.0
OXYGEN_WARN_THRESHOLD = 7.0
RISK_SPIKE_THRESHOLD = 8.0      # points change in one day
RISK_HIGH_THRESHOLD = 60.0      # absolute total risk score


def _make_event(
    timestamp: datetime,
    event_type: str,
    severity: str,
    title: str,
    description: str,
    locality_id: str,
    domain: Optional[str] = None,
    risk_impact: Optional[float] = None,
) -> dict:
    return {
        "event_id": f"{locality_id}_{event_type}_{timestamp.strftime('%Y%m%d%H%M')}",
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "severity": severity,
        "title": title,
        "description": description,
        "domain": domain,
        "risk_impact": risk_impact,
        "locality_id": locality_id,
    }


def get_events(locality_id: str, period: str = "30d") -> dict:
    data = get_locality_data(locality_id)
    cfg = get_locality_config(locality_id)
    timestamps = data["timestamps"]
    lice = data["lice"]
    temperature = data["temperature"]
    oxygen = data["oxygen"]
    disease = data["disease"]
    risk_scores = data["risk_scores"]

    sliced_ts, start_idx = slice_by_period(timestamps, period)
    events: list = []

    prev_disease = 0
    prev_total = risk_scores[start_idx]["total"] if start_idx < DAYS else 50.0

    for i, d_idx in enumerate(range(start_idx, DAYS)):
        ts = timestamps[d_idx]
        lv = lice[d_idx]
        tv = temperature[d_idx]
        ov = oxygen[d_idx]
        dv = disease[d_idx]
        risk = risk_scores[d_idx]

        # Lice threshold events
        if lv is not None:
            if lv > LICE_CRIT_THRESHOLD:
                events.append(_make_event(
                    ts, "lice_threshold", "critical",
                    "Kritisk luseveldi overskredet",
                    f"Lakselus: {lv:.2f} lus/fisk — over behandlingsterskel ({LICE_CRIT_THRESHOLD})",
                    locality_id, "biological",
                    risk_impact=round((lv - LICE_CRIT_THRESHOLD) * 10, 1),
                ))
            elif lv > LICE_WARN_THRESHOLD:
                events.append(_make_event(
                    ts, "lice_warning", "warning",
                    "Lusenivå over varslingsterskel",
                    f"Lakselus: {lv:.2f} lus/fisk — over varslingsterskel ({LICE_WARN_THRESHOLD})",
                    locality_id, "biological",
                    risk_impact=round((lv - LICE_WARN_THRESHOLD) * 6, 1),
                ))

        # Disease onset
        if dv == 1 and prev_disease == 0:
            events.append(_make_event(
                ts, "disease_registered", "warning",
                "Sykdomsstatus registrert",
                "Ny sykdomsregistrering fra BarentsWatch — overvåking intensivert",
                locality_id, "biological", risk_impact=25.0,
            ))
        if dv == 0 and prev_disease == 1:
            events.append(_make_event(
                ts, "disease_cleared", "info",
                "Sykdomsstatus avsluttet",
                "Sykdomsregistreringen er avsluttet — tilbake til normalt overvåkingsnivå",
                locality_id, "biological", risk_impact=-20.0,
            ))
        prev_disease = dv

        # Temperature warning
        if tv is not None and tv > TEMP_WARN_THRESHOLD:
            events.append(_make_event(
                ts, "temperature_anomaly", "warning",
                "Temperaturanomalí — over varslingsterskel",
                f"Overflatetemperatur: {tv:.1f}°C — over {TEMP_WARN_THRESHOLD}°C",
                locality_id, "environmental", risk_impact=5.0,
            ))

        # Oxygen warning
        if ov is not None and ov < OXYGEN_WARN_THRESHOLD:
            events.append(_make_event(
                ts, "oxygen_low", "warning",
                "Lavt oksygennivå",
                f"Oksygen: {ov:.1f} mg/L — under terskel ({OXYGEN_WARN_THRESHOLD} mg/L)",
                locality_id, "environmental", risk_impact=8.0,
            ))

        # Risk spike
        current_total = risk["total"]
        delta = current_total - prev_total
        if delta >= RISK_SPIKE_THRESHOLD:
            events.append(_make_event(
                ts, "risk_spike", "warning",
                "Markant risikoøkning",
                f"Total risikoscore økte med {delta:.1f} poeng til {current_total:.1f}",
                locality_id, None, risk_impact=round(delta, 1),
            ))
        elif delta <= -RISK_SPIKE_THRESHOLD:
            events.append(_make_event(
                ts, "risk_drop", "info",
                "Markant risikoreduksjon",
                f"Total risikoscore falt med {abs(delta):.1f} poeng til {current_total:.1f}",
                locality_id, None, risk_impact=round(delta, 1),
            ))
        prev_total = current_total

    # Add a sync event for delayed localities
    delay_h = cfg.get("sync_delay_hours", 1.0)
    if delay_h > 12:
        from backend.services.live_risk_mock import NOW
        from datetime import timedelta
        sync_ts = NOW - timedelta(hours=delay_h)
        events.append(_make_event(
            sync_ts, "source_delayed", "warning",
            "Datakilde forsinket",
            f"BarentsWatch miljødata er {delay_h:.0f} timer forsinket — siste vellykkede sync avventes",
            locality_id, None,
        ))

    # Deduplicate same-day same-type events (keep first)
    seen = set()
    unique_events = []
    for e in events:
        key = (e["event_type"], e["timestamp"][:10])
        if key not in seen:
            seen.add(key)
            unique_events.append(e)

    # Sort most recent first
    unique_events.sort(key=lambda e: e["timestamp"], reverse=True)

    return {
        "locality_id": locality_id,
        "events": unique_events,
        "total_count": len(unique_events),
    }
