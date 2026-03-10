"""C5AI+ v5.0 – Structural Risk Forecaster.

Score-based probability model. No ML in Sprint 1.
Returns one forecast dict per structural risk subtype.
"""

from __future__ import annotations

import math
from typing import Dict, List

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.structural.inputs import StructuralSiteInput

_RISK_TYPES = [
    'mooring_failure',
    'net_integrity',
    'cage_structural',
    'deformation',
    'anchor_deterioration',
]


def _lognormal_loss(mean_fraction: float, cv: float, biomass_value_nok: float) -> dict:
    """Derive expected_loss_mean, p50, p90 from LogNormal(mean, cv)."""
    mu = math.log(mean_fraction) - 0.5 * math.log(1 + cv ** 2)
    sigma = math.sqrt(math.log(1 + cv ** 2))
    mean_loss = biomass_value_nok * mean_fraction
    p50 = biomass_value_nok * math.exp(mu)
    p90 = biomass_value_nok * math.exp(mu + 1.2816 * sigma)
    return dict(
        expected_loss_mean=round(mean_loss),
        expected_loss_p50=round(p50),
        expected_loss_p90=round(p90),
    )


class StructuralForecaster:
    """Score-based structural risk forecaster."""

    def forecast(
        self,
        site_input: StructuralSiteInput,
        site_meta: Dict,
    ) -> List[dict]:
        """
        Returns list of dicts (one per structural risk subtype) matching
        RiskTypeForecast fields.
        """
        biomass_value = site_meta.get('biomass_value_nok', 100_000_000)
        results = []

        for risk_type in _RISK_TYPES:
            score, drivers = self._score_risk(risk_type, site_input)
            prior = getattr(C5AI_SETTINGS, f'{risk_type}_prior_probability')
            prob = min(0.95, prior * (1.0 + 2.5 * score))
            mean_frac = getattr(C5AI_SETTINGS, f'{risk_type}_loss_fraction_mean')
            cv = getattr(C5AI_SETTINGS, f'{risk_type}_loss_fraction_cv')
            loss = _lognormal_loss(mean_frac, cv, biomass_value)
            confidence = round(0.60 - 0.15 * score, 2)  # lower when risk is elevated
            results.append(dict(
                risk_type=risk_type,
                event_probability=round(prob, 4),
                confidence_score=round(max(0.35, confidence), 2),
                data_quality_flag='LIMITED',
                model_used='score_structural',
                drivers=drivers,
                **loss,
            ))

        return results

    # ── Scoring helpers ───────────────────────────────────────────────────────

    def _score_risk(
        self,
        risk_type: str,
        inp: StructuralSiteInput,
    ) -> tuple[float, List[str]]:
        drivers: List[str] = []
        score = 0.0

        if risk_type == 'mooring_failure':
            if inp.mooring_inspection_score < 0.6:
                score += 0.50
                drivers.append(f'Mooring inspection score low ({inp.mooring_inspection_score:.2f} < 0.60)')
            if inp.deformation_load_index > 0.5:
                score += 0.30
                drivers.append(f'Deformation load index elevated ({inp.deformation_load_index:.2f})')
            if inp.last_inspection_days_ago > 180:
                score += 0.20
                drivers.append(f'Inspection overdue ({inp.last_inspection_days_ago}d > 180d)')

        elif risk_type == 'net_integrity':
            if inp.net_strength_residual_pct < 70.0:
                score += 0.50
                drivers.append(f'Net strength below 70% (current {inp.net_strength_residual_pct:.0f}%)')
            if inp.net_age_years > 3.0:
                score += 0.30
                drivers.append(f'Net age {inp.net_age_years:.1f} years exceeds 3-year guideline')
            if inp.deformation_load_index > 0.6:
                score += 0.20
                drivers.append(f'High load index increasing net stress ({inp.deformation_load_index:.2f})')

        elif risk_type == 'cage_structural':
            if inp.deformation_load_index > 0.5:
                score += 0.50
                drivers.append(f'Deformation load index {inp.deformation_load_index:.2f} above threshold')
            if inp.last_inspection_days_ago > 90:
                score += 0.30
                drivers.append(f'No structural inspection in {inp.last_inspection_days_ago}d')
            if inp.net_strength_residual_pct < 75.0:
                score += 0.20
                drivers.append(f'Low net residual strength ({inp.net_strength_residual_pct:.0f}%)')

        elif risk_type == 'deformation':
            if inp.deformation_load_index > 0.4:
                score += 0.60
                drivers.append(f'Deformation load index {inp.deformation_load_index:.2f} above 0.40')
            if inp.last_inspection_days_ago > 120:
                score += 0.40
                drivers.append(f'Deformation monitoring overdue ({inp.last_inspection_days_ago}d)')

        elif risk_type == 'anchor_deterioration':
            if inp.anchor_line_condition < 0.5:
                score += 0.60
                drivers.append(f'Anchor line condition critical ({inp.anchor_line_condition:.2f} < 0.50)')
            if inp.last_inspection_days_ago > 150:
                score += 0.40
                drivers.append(f'Anchor inspection overdue ({inp.last_inspection_days_ago}d > 150d)')

        return min(1.0, score), drivers if drivers else [f'{risk_type.replace("_", " ").title()} within expected range']
