"""
backend/services/risk_change_explainer.py

Computes attributable risk change breakdowns for a locality over a period.
Explains which factors drove changes in each domain.
"""
from __future__ import annotations

from typing import List

from backend.services.live_risk_mock import (
    get_locality_data,
    slice_by_period,
    DAYS,
    structural_fouling,
    structural_wave_load,
)

# Explanation templates
_FACTOR_EXPLANATIONS = {
    "lice_increase":      "Økt lusenivå gir høyere biologisk risiko",
    "lice_decrease":      "Redusert lusenivå senker biologisk risiko",
    "lice_stable":        "Lusenivå er stabilt — ingen vesentlig endring",
    "disease_onset":      "Ny sykdomsregistrering gir markant biologisk risikoøkning",
    "disease_cleared":    "Avsluttet sykdomsregistrering — biologisk risiko redusert",
    "disease_stable":     "Ingen sykdomsregistreringer i perioden",
    "temp_anomaly_up":    "Temperaturen er over biologisk grense — bidrar til økt miljørisiko",
    "temp_anomaly_down":  "Temperaturen faller mot biologisk grense — miljørisiko reduseres",
    "temp_normal":        "Temperatur er under biologisk stressgrense (10 °C) — ingen bidrag",
    "temp_stable":        "Temperatur er innenfor normalvariasjon",
    "oxygen_stress":      "Lavt oksygennivå øker miljørisiko",
    "oxygen_improve":     "Bedret oksygennivå reduserer miljørisiko",
    "oxygen_normal":      "Oksygennivå er normalt",
    "treatment_burden":   "Økt behandlingsbelastning gir operasjonell risiko",
    "treatment_low":      "Lav behandlingsfrekvens — operasjonell risiko stabil",
    "fouling_increase":   "Økt begroing av not gir høyere vekt og vannmotstand — strukturell risiko øker",
    "fouling_decrease":   "Redusert begroing (sesong/rengjøring) — strukturell belastning avtar",
    "fouling_stable":     "Begroingsnivå er stabilt",
    "wave_increase":      "Økt bølge- og strømbelastning — storm/lavtrykk gir mekanisk påkjenning",
    "wave_decrease":      "Roligere værforhold — bølge- og strømbelastning avtar",
    "wave_stable":        "Bølge- og strømbetingelser er stabile",
    "lining_active":      "Intensiv behandlingsperiode medfører ekstra nothåndtering (lining/rens)",
    "lining_inactive":    "Lav operasjonell aktivitet — minimal nothåndtering",
    "structural_stable":  "Strukturell risiko er stabil",
}


def _mean(vals: list, default: float = 0.0) -> float:
    non_null = [v for v in vals if v is not None]
    return sum(non_null) / len(non_null) if non_null else default


def get_change_breakdown(locality_id: str, period: str = "30d") -> dict:
    data = get_locality_data(locality_id)
    timestamps = data["timestamps"]
    lice = data["lice"]
    disease = data["disease"]
    temperature = data["temperature"]
    oxygen = data["oxygen"]
    treatment = data["treatment"]
    risk_scores = data["risk_scores"]

    from backend.services.live_risk_mock import period_to_days
    sliced_ts, start_idx = slice_by_period(timestamps, period)
    end_idx = DAYS - 1
    period_requested_days = period_to_days(period)
    data_limited = period_requested_days > DAYS

    from_date = timestamps[start_idx]
    to_date = timestamps[end_idx]

    # Risk at period boundaries — use 7-day windows (matches raw-data factor windows)
    # to smooth out the per-day deterministic noise in the risk formula.
    _DOMAINS = ["biological", "structural", "environmental", "operational", "total"]
    risk_start = {
        d: _mean([risk_scores[i][d] for i in range(start_idx, min(start_idx + 7, end_idx + 1))])
        for d in _DOMAINS
    }
    risk_end = {
        d: _mean([risk_scores[i][d] for i in range(max(end_idx - 6, start_idx), end_idx + 1)])
        for d in _DOMAINS
    }
    total_delta = round(risk_end["total"] - risk_start["total"], 1)

    # Domain deltas
    domain_deltas = {
        d: round(risk_end[d] - risk_start[d], 1)
        for d in ["biological", "structural", "environmental", "operational"]
    }

    # Raw factor averages: first 7d vs last 7d of period
    half = max(1, (end_idx - start_idx) // 2)
    early_lice = _mean(lice[start_idx:start_idx + 7])
    late_lice = _mean(lice[end_idx - 6:end_idx + 1])
    lice_delta = late_lice - early_lice

    early_temp = _mean(temperature[start_idx:start_idx + 7])
    late_temp = _mean(temperature[end_idx - 6:end_idx + 1])

    early_oxygen = _mean(oxygen[start_idx:start_idx + 7], default=9.0)
    late_oxygen = _mean(oxygen[end_idx - 6:end_idx + 1], default=9.0)

    disease_start = sum(disease[start_idx:start_idx + 7])
    disease_end = sum(disease[end_idx - 6:end_idx + 1])

    treatment_start = _mean(treatment[start_idx:start_idx + 7])
    treatment_end = _mean(treatment[max(end_idx - 6, start_idx):end_idx + 1])

    factor_deltas = []

    # Lice factor
    if abs(lice_delta) > 0.05:
        direction = "up" if lice_delta > 0 else "down"
        bio_impact = round(lice_delta * 30, 1)
        factor_deltas.append({
            "factor": "Lakselus",
            "domain": "biological",
            "delta": bio_impact,
            "direction": direction,
            "explanation": _FACTOR_EXPLANATIONS["lice_increase" if lice_delta > 0 else "lice_decrease"],
        })
    else:
        factor_deltas.append({
            "factor": "Lakselus",
            "domain": "biological",
            "delta": 0.0,
            "direction": "unchanged",
            "explanation": _FACTOR_EXPLANATIONS["lice_stable"],
        })

    # Disease factor
    if disease_end > 0 and disease_start == 0:
        factor_deltas.append({
            "factor": "Sykdomsstatus",
            "domain": "biological",
            "delta": 25.0,
            "direction": "up",
            "explanation": _FACTOR_EXPLANATIONS["disease_onset"],
        })
    elif disease_start > 0 and disease_end == 0:
        factor_deltas.append({
            "factor": "Sykdomsstatus",
            "domain": "biological",
            "delta": -20.0,
            "direction": "down",
            "explanation": _FACTOR_EXPLANATIONS["disease_cleared"],
        })
    else:
        factor_deltas.append({
            "factor": "Sykdomsstatus",
            "domain": "biological",
            "delta": 0.0,
            "direction": "unchanged",
            "explanation": _FACTOR_EXPLANATIONS["disease_stable"],
        })

    # Temperature factor — matches risk formula: max(0, tv - 10.0) * 8
    # Norwegian waters (5–9 °C) stay below the 10 °C stress threshold,
    # so raw °C changes do not translate to environmental risk changes.
    _TEMP_STRESS_THRESHOLD = 10.0
    early_temp_anom = max(0.0, early_temp - _TEMP_STRESS_THRESHOLD)
    late_temp_anom  = max(0.0, late_temp  - _TEMP_STRESS_THRESHOLD)
    temp_impact = round((late_temp_anom - early_temp_anom) * 8, 1)
    if abs(temp_impact) > 0.5:
        factor_deltas.append({
            "factor": "Temperatur",
            "domain": "environmental",
            "delta": temp_impact,
            "direction": "up" if temp_impact > 0 else "down",
            "explanation": _FACTOR_EXPLANATIONS[
                "temp_anomaly_up" if temp_impact > 0 else "temp_anomaly_down"
            ],
        })
    else:
        # Temperature changed but stays below stress threshold
        _temp_expl = (
            _FACTOR_EXPLANATIONS["temp_normal"]
            if max(early_temp_anom, late_temp_anom) < 0.1
            else _FACTOR_EXPLANATIONS["temp_stable"]
        )
        factor_deltas.append({
            "factor": "Temperatur",
            "domain": "environmental",
            "delta": 0.0,
            "direction": "unchanged",
            "explanation": _temp_expl,
        })

    # Oxygen factor — matches risk formula: max(0, 9.0 - ov) * 12
    early_oxy_stress = max(0.0, 9.0 - early_oxygen)
    late_oxy_stress  = max(0.0, 9.0 - late_oxygen)
    oxy_impact = round((late_oxy_stress - early_oxy_stress) * 12, 1)
    if abs(oxy_impact) > 0.5:
        factor_deltas.append({
            "factor": "Oksygennivå",
            "domain": "environmental",
            "delta": oxy_impact,
            "direction": "up" if oxy_impact > 0 else "down",
            "explanation": _FACTOR_EXPLANATIONS[
                "oxygen_stress" if oxy_impact > 0 else "oxygen_improve"
            ],
        })
    else:
        factor_deltas.append({
            "factor": "Oksygennivå",
            "domain": "environmental",
            "delta": 0.0,
            "direction": "unchanged",
            "explanation": _FACTOR_EXPLANATIONS["oxygen_normal"],
        })

    # Treatment factor
    treat_delta = treatment_end - treatment_start
    if treat_delta > 1:
        factor_deltas.append({
            "factor": "Behandlingsbelastning",
            "domain": "operational",
            "delta": round(treat_delta * 2.5, 1),
            "direction": "up",
            "explanation": _FACTOR_EXPLANATIONS["treatment_burden"],
        })
    else:
        factor_deltas.append({
            "factor": "Behandlingsbelastning",
            "domain": "operational",
            "delta": 0.0,
            "direction": "unchanged",
            "explanation": _FACTOR_EXPLANATIONS["treatment_low"],
        })

    # Structural factors — computed using the same helper functions as the risk model

    cfg = data["config"]

    # Biofouling: seasonal net growth peaks in summer
    early_fouling = _mean([structural_fouling(i) for i in range(start_idx, start_idx + 7)])
    late_fouling  = _mean([structural_fouling(i) for i in range(max(end_idx - 6, start_idx), end_idx + 1)])
    fouling_impact = round((late_fouling - early_fouling) * 12, 1)
    if abs(fouling_impact) > 0.3:
        factor_deltas.append({
            "factor": "Begroing",
            "domain": "structural",
            "delta": fouling_impact,
            "direction": "up" if fouling_impact > 0 else "down",
            "explanation": _FACTOR_EXPLANATIONS[
                "fouling_increase" if fouling_impact > 0 else "fouling_decrease"
            ],
        })
    else:
        factor_deltas.append({
            "factor": "Begroing",
            "domain": "structural",
            "delta": 0.0,
            "direction": "unchanged",
            "explanation": _FACTOR_EXPLANATIONS["fouling_stable"],
        })

    # Wave/storm load: seasonal — peaks in Norwegian winter
    early_wave = _mean([structural_wave_load(i, cfg["exposure"]) for i in range(start_idx, start_idx + 7)])
    late_wave  = _mean([structural_wave_load(i, cfg["exposure"]) for i in range(max(end_idx - 6, start_idx), end_idx + 1)])
    wave_impact = round((late_wave - early_wave) * 6, 1)
    if abs(wave_impact) > 0.3:
        factor_deltas.append({
            "factor": "Bølge- og strømbelastning",
            "domain": "structural",
            "delta": wave_impact,
            "direction": "up" if wave_impact > 0 else "down",
            "explanation": _FACTOR_EXPLANATIONS[
                "wave_increase" if wave_impact > 0 else "wave_decrease"
            ],
        })
    else:
        factor_deltas.append({
            "factor": "Bølge- og strømbelastning",
            "domain": "structural",
            "delta": 0.0,
            "direction": "unchanged",
            "explanation": _FACTOR_EXPLANATIONS["wave_stable"],
        })

    # Net operations (lining): driven by treatment intensity
    _lining_start = 1.0 if treatment_start > 2 else 0.0
    _lining_end   = 1.0 if treatment_end   > 2 else 0.0
    lining_impact = round((_lining_end - _lining_start) * 8, 1)
    if abs(lining_impact) > 0.3:
        factor_deltas.append({
            "factor": "Nothåndtering (lining)",
            "domain": "structural",
            "delta": lining_impact,
            "direction": "up" if lining_impact > 0 else "down",
            "explanation": _FACTOR_EXPLANATIONS["lining_active"],
        })
    else:
        factor_deltas.append({
            "factor": "Nothåndtering (lining)",
            "domain": "structural",
            "delta": 0.0,
            "direction": "unchanged",
            "explanation": _FACTOR_EXPLANATIONS["lining_inactive"],
        })

    _DOMAIN_LABELS_NO = {
        "biological":    "Biologisk",
        "structural":    "Strukturell",
        "environmental": "Miljø",
        "operational":   "Operasjonell",
    }

    # Build natural-language summary — include both risk drivers and reducers
    summary = []
    significant = [f for f in factor_deltas if abs(f["delta"]) > 0.5]
    if not significant:
        summary.append("Ingen vesentlige endringer ble identifisert i perioden.")
        summary.append("Alle faktorer er innenfor normalvariasjon.")
    else:
        drivers  = sorted([f for f in significant if f["delta"] > 0], key=lambda x: x["delta"], reverse=True)
        reducers = sorted([f for f in significant if f["delta"] < 0], key=lambda x: x["delta"])
        for f in (drivers[:2] + reducers[:2]):
            sign = "+" if f["delta"] > 0 else ""
            domain_no = _DOMAIN_LABELS_NO.get(f["domain"], f["domain"])
            summary.append(f"{f['factor']}: {sign}{f['delta']:.1f} pkt ({domain_no})")

    # Confidence note
    has_missing = any(v is None for v in lice[start_idx:end_idx + 1])
    confidence_note = (
        "NB: Noen datapunkter mangler — attribusjon er basert på tilgjengelige observasjoner."
        if has_missing
        else "Attribusjonen er basert på komplette observerte data for perioden."
    )

    period_days = end_idx - start_idx + 1
    return {
        "period_days": period_days,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "risk_at_start": round(risk_start["total"], 1),
        "risk_at_end": round(risk_end["total"], 1),
        "total_delta": total_delta,
        "domain_deltas": domain_deltas,
        "factor_deltas": factor_deltas,
        "explanation_summary": summary,
        "confidence_note": confidence_note,
        "data_limited": data_limited,
        "data_available_days": DAYS,
    }
