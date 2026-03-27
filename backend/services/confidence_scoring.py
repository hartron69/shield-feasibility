"""
backend/services/confidence_scoring.py

Computes confidence scores based on data freshness, source coverage,
and data gap analysis.
"""
from __future__ import annotations

from typing import List

from backend.services.live_risk_mock import get_locality_data, get_locality_config, NOW, DAYS
from backend.services.source_health import get_source_status


def _count_gaps(values: list) -> int:
    return sum(1 for v in values if v is None)


def _gap_rate(values: list) -> float:
    if not values:
        return 0.0
    return _count_gaps(values) / len(values)


def compute_confidence(locality_id: str) -> dict:
    """Compute confidence score for a locality."""
    data = get_locality_data(locality_id)
    cfg = get_locality_config(locality_id)
    source_data = get_source_status(locality_id)

    components = []
    scores = []

    # ── Component 1: Source freshness ──────────────────────────────────────────
    delay_h = cfg.get("sync_delay_hours", 1.0)
    if delay_h < 6:
        freshness_score = 1.0
        freshness_text = "Alle kritiske kilder er ferske (< 6 timer)"
    elif delay_h < 24:
        freshness_score = 0.65
        freshness_text = f"En eller flere kilder er forsinket ({delay_h:.0f} timer siden siste oppdatering)"
    else:
        freshness_score = 0.30
        freshness_text = f"Kritisk kildedataer er > 24 timer gammel"
    components.append({"component": "Kildekvalitet", "score": freshness_score, "explanation": freshness_text})
    scores.append(freshness_score)

    # ── Component 2: Source coverage ──────────────────────────────────────────
    ok_count = sum(1 for s in source_data["sources"] if s["status"] == "ok")
    total_sources = len(source_data["sources"])
    coverage_ratio = ok_count / total_sources
    coverage_score = coverage_ratio
    coverage_text = f"{ok_count} av {total_sources} datakilder er aktive"
    components.append({"component": "Kilddekning", "score": round(coverage_score, 2), "explanation": coverage_text})
    scores.append(coverage_score)

    # ── Component 3: Data gaps (lice + temperature) ────────────────────────────
    lice_gap = _gap_rate(data["lice"])
    temp_gap = _gap_rate(data["temperature"])
    avg_gap = (lice_gap + temp_gap) / 2
    gap_score = max(0.0, 1.0 - avg_gap * 5)  # penalize gaps heavily
    gap_text = (
        f"Lakselus: {lice_gap:.0%} manglende verdier, "
        f"temperatur: {temp_gap:.0%} manglende verdier"
    )
    components.append({"component": "Datakomplethet", "score": round(gap_score, 2), "explanation": gap_text})
    scores.append(gap_score)

    # ── Component 4: Model confidence (risk scores all non-trivial) ────────────
    recent_risks = data["risk_scores"][-7:]
    bio_avg = sum(r["biological"] for r in recent_risks) / len(recent_risks)
    model_score = 0.85 if bio_avg < 80 else 0.65
    model_text = "C5AI+ risikomodell er kalibrert og kjørt på aktuelle data" if model_score > 0.8 else "Høye risikoverdi — estimater er usikre ved ekstremsituasjoner"
    components.append({"component": "Modellstabilitet", "score": model_score, "explanation": model_text})
    scores.append(model_score)

    # ── Aggregate ──────────────────────────────────────────────────────────────
    overall_score = round(sum(scores) / len(scores), 3)
    if overall_score >= 0.75:
        level = "high"
        summary = "Risikobildet er basert på fersk og komplett data fra alle kritiske kilder."
    elif overall_score >= 0.50:
        level = "medium"
        summary = "Risikobildet er rimelig pålitelig, men én eller flere datakilder er forsinket eller ufullstendig."
    else:
        level = "low"
        summary = "Datakvaliteten er svekket — risikobildet bør tolkes med forsiktighet inntil kilder er gjenopprettet."

    missing_sources = [
        s["source_name"] for s in source_data["sources"] if not s["contributes_to_risk"]
    ]

    return {
        "overall": level,
        "score": overall_score,
        "components": components,
        "summary": summary,
        "missing_sources": missing_sources,
        "data_age_hours": round(delay_h, 1),
    }
