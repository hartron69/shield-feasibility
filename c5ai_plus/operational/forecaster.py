"""C5AI+ v5.0 – Operational Risk Forecaster.

Score-based probability model. No ML in Sprint 1.
"""

from __future__ import annotations

import math
from typing import Dict, List

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.operational.inputs import OperationalSiteInput

_RISK_TYPES = [
    'human_error',
    'procedure_failure',
    'equipment_failure',
    'incident',
    'maintenance_backlog',
]


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


class OperationalForecaster:
    """Score-based operational risk forecaster."""

    def forecast(
        self,
        site_input: OperationalSiteInput,
        site_meta: Dict,
    ) -> List[dict]:
        biomass_value = site_meta.get('biomass_value_nok', 100_000_000)
        results = []

        for risk_type in _RISK_TYPES:
            score, drivers = self._score_risk(risk_type, site_input)
            prior = getattr(C5AI_SETTINGS, f'{risk_type}_prior_probability')
            prob = min(0.95, prior * (1.0 + 2.5 * score))
            mean_frac = getattr(C5AI_SETTINGS, f'{risk_type}_loss_fraction_mean')
            cv = getattr(C5AI_SETTINGS, f'{risk_type}_loss_fraction_cv')
            loss = _lognormal_loss(mean_frac, cv, biomass_value)
            confidence = round(max(0.35, 0.65 - 0.15 * score), 2)
            results.append(dict(
                risk_type=risk_type,
                event_probability=round(prob, 4),
                confidence_score=confidence,
                data_quality_flag='LIMITED',
                model_used='score_operational',
                drivers=drivers,
                **loss,
            ))

        return results

    def _score_risk(
        self,
        risk_type: str,
        inp: OperationalSiteInput,
    ) -> tuple[float, List[str]]:
        drivers: List[str] = []
        score = 0.0

        if risk_type == 'human_error':
            if inp.staffing_score < 0.6:
                score += 0.50
                drivers.append(f'Staffing score {inp.staffing_score:.2f} below safe threshold (0.60)')
            if inp.critical_ops_frequency_per_month > 5:
                score += 0.30
                drivers.append(
                    f'High-risk operations frequency {inp.critical_ops_frequency_per_month:.1f}/month'
                )
            if inp.incident_rate_12m > 0.5:
                score += 0.20
                drivers.append(f'Elevated incident rate ({inp.incident_rate_12m:.1f}/month)')

        elif risk_type == 'procedure_failure':
            if inp.training_compliance_pct < 80.0:
                deficit = 80.0 - inp.training_compliance_pct
                score += min(0.70, deficit / 20.0)
                drivers.append(f'Training compliance {inp.training_compliance_pct:.0f}% below 80% requirement')
            if inp.staffing_score < 0.7:
                score += 0.30
                drivers.append('Low staffing increases procedure shortcuts risk')

        elif risk_type == 'equipment_failure':
            if inp.equipment_readiness_score < 0.7:
                deficit = 0.7 - inp.equipment_readiness_score
                score += min(0.80, deficit / 0.3)
                drivers.append(
                    f'Equipment readiness {inp.equipment_readiness_score:.2f} below operational minimum (0.70)'
                )
            if inp.maintenance_backlog_score > 0.3:
                score += 0.20
                drivers.append(f'Maintenance backlog contributing to equipment degradation ({inp.maintenance_backlog_score:.2f})')

        elif risk_type == 'incident':
            if inp.incident_rate_12m > 1.0:
                score += min(0.80, (inp.incident_rate_12m - 1.0) / 1.0)
                drivers.append(f'Incident rate {inp.incident_rate_12m:.1f}/month above baseline (1.0/month)')
            if inp.staffing_score < 0.65:
                score += 0.20
                drivers.append('Low staffing correlated with elevated incident rates')

        elif risk_type == 'maintenance_backlog':
            if inp.maintenance_backlog_score > 0.3:
                score += min(1.0, (inp.maintenance_backlog_score - 0.3) / 0.5)
                drivers.append(f'Maintenance backlog score {inp.maintenance_backlog_score:.2f} above safe level (0.30)')

        return min(1.0, score), drivers if drivers else [
            f'{risk_type.replace("_", " ").title()} within expected range'
        ]
