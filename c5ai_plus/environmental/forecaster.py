"""C5AI+ v5.0 – Environmental Risk Forecaster.

Score-based probability model. No ML in Sprint 1.
"""

from __future__ import annotations

import math
from typing import Dict, List

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.environmental.inputs import EnvironmentalSiteInput

_RISK_TYPES = [
    'oxygen_stress',
    'temperature_extreme',
    'current_storm',
    'ice',
    'exposure_anomaly',
]

# Safe operating ranges
_O2_SAFE_LOW = 7.0      # mg/L
_TEMP_SAFE_LOW = 4.0    # Celsius
_TEMP_SAFE_HIGH = 16.0  # Celsius
_CURRENT_LIMIT = 0.60   # m/s design limit
_WAVE_LIMIT = 2.0       # m design limit


def _lognormal_loss(mean_fraction: float, cv: float, biomass_value_nok: float) -> dict:
    mu = math.log(mean_fraction) - 0.5 * math.log(1 + cv ** 2)
    sigma = math.sqrt(math.log(1 + cv ** 2))
    p50 = biomass_value_nok * math.exp(mu)
    p90 = biomass_value_nok * math.exp(mu + 1.2816 * sigma)
    return dict(
        expected_loss_mean=round(biomass_value_nok * mean_fraction),
        expected_loss_p50=round(p50),
        expected_loss_p90=round(p90),
    )


class EnvironmentalForecaster:
    """Score-based environmental risk forecaster."""

    def forecast(
        self,
        site_input: EnvironmentalSiteInput,
        site_meta: Dict,
    ) -> List[dict]:
        biomass_value = site_meta.get('biomass_value_nok', 100_000_000)
        results = []

        for risk_type in _RISK_TYPES:
            score, drivers = self._score_risk(risk_type, site_input)
            prior_attr = f'{risk_type}_prior_probability'
            prior = getattr(C5AI_SETTINGS, prior_attr)
            prob = min(0.95, prior * (1.0 + 2.5 * score))
            mean_frac = getattr(C5AI_SETTINGS, f'{risk_type}_loss_fraction_mean')
            cv = getattr(C5AI_SETTINGS, f'{risk_type}_loss_fraction_cv')
            loss = _lognormal_loss(mean_frac, cv, biomass_value)
            confidence = round(max(0.35, 0.65 - 0.20 * score), 2)
            results.append(dict(
                risk_type=risk_type,
                event_probability=round(prob, 4),
                confidence_score=confidence,
                data_quality_flag='LIMITED',
                model_used='score_environmental',
                drivers=drivers,
                **loss,
            ))

        return results

    def _score_risk(
        self,
        risk_type: str,
        inp: EnvironmentalSiteInput,
    ) -> tuple[float, List[str]]:
        drivers: List[str] = []
        score = 0.0

        if risk_type == 'oxygen_stress':
            if inp.dissolved_oxygen_mg_l < _O2_SAFE_LOW:
                deficit = _O2_SAFE_LOW - inp.dissolved_oxygen_mg_l
                score += min(1.0, deficit / 2.0)
                drivers.append(
                    f'Dissolved O2 {inp.dissolved_oxygen_mg_l:.1f} mg/L below safe threshold ({_O2_SAFE_LOW} mg/L)'
                )
            if inp.oxygen_saturation_pct < 80:
                score += 0.20
                drivers.append(f'O2 saturation {inp.oxygen_saturation_pct:.0f}% below 80%')

        elif risk_type == 'temperature_extreme':
            if inp.surface_temp_c > _TEMP_SAFE_HIGH:
                excess = inp.surface_temp_c - _TEMP_SAFE_HIGH
                score += min(0.80, excess / 4.0)
                drivers.append(f'Surface temp {inp.surface_temp_c:.1f}C above safe high ({_TEMP_SAFE_HIGH}C)')
            elif inp.surface_temp_c < _TEMP_SAFE_LOW:
                deficit = _TEMP_SAFE_LOW - inp.surface_temp_c
                score += min(0.60, deficit / 3.0)
                drivers.append(f'Surface temp {inp.surface_temp_c:.1f}C below safe low ({_TEMP_SAFE_LOW}C)')

        elif risk_type == 'current_storm':
            if inp.current_speed_ms > _CURRENT_LIMIT:
                score += min(0.60, (inp.current_speed_ms - _CURRENT_LIMIT) / 0.40)
                drivers.append(f'Current {inp.current_speed_ms:.2f} m/s exceeds design limit ({_CURRENT_LIMIT} m/s)')
            if inp.significant_wave_height_m > _WAVE_LIMIT:
                score += min(0.40, (inp.significant_wave_height_m - _WAVE_LIMIT) / 1.5)
                drivers.append(f'Wave height {inp.significant_wave_height_m:.1f}m exceeds design limit ({_WAVE_LIMIT}m)')

        elif risk_type == 'ice':
            if inp.ice_risk_score > 0.05:
                score += min(1.0, inp.ice_risk_score * 5.0)
                drivers.append(f'Ice risk score elevated ({inp.ice_risk_score:.2f})')

        elif risk_type == 'exposure_anomaly':
            exposure_factor = {'open': 1.0, 'semi': 0.5, 'sheltered': 0.1}.get(
                inp.site_exposure_class, 0.5
            )
            combined = (
                (inp.current_speed_ms / (_CURRENT_LIMIT or 1)) * 0.4
                + (inp.significant_wave_height_m / (_WAVE_LIMIT or 1)) * 0.4
                + exposure_factor * 0.2
            )
            score = min(1.0, combined - 0.5) if combined > 0.5 else 0.0
            if score > 0:
                drivers.append(
                    f'Combined exposure anomaly: {inp.site_exposure_class} site, '
                    f'{inp.current_speed_ms:.2f} m/s current, '
                    f'{inp.significant_wave_height_m:.1f}m waves'
                )

        return min(1.0, score), drivers if drivers else [
            f'{risk_type.replace("_", " ").title()} within normal operating range'
        ]
