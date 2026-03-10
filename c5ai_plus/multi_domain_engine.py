"""
C5AI+ v5.0 – Multi-Domain Forecast Engine.

Orchestrates all 4 domains and produces a MultiDomainForecast.
The biological pipeline remains unchanged; this module wraps it alongside
the three new structural/environmental/operational forecasters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from c5ai_plus.structural.inputs import StructuralSiteInput
from c5ai_plus.structural.forecaster import StructuralForecaster
from c5ai_plus.environmental.inputs import EnvironmentalSiteInput
from c5ai_plus.environmental.forecaster import EnvironmentalForecaster
from c5ai_plus.operational.inputs import OperationalSiteInput
from c5ai_plus.operational.forecaster import OperationalForecaster


@dataclass
class DomainForecastResult:
    """Forecast results for one domain at one site."""
    domain: str
    site_id: str
    risk_forecasts: List[dict]   # one dict per risk_type

    def to_dict(self) -> dict:
        return {
            'domain': self.domain,
            'site_id': self.site_id,
            'risk_forecasts': self.risk_forecasts,
        }


@dataclass
class MultiDomainForecast:
    """
    Aggregated forecast across all 4 domains for an operator.

    biological is a list of existing SiteForecast-style dicts (passed through
    from the existing biological pipeline).
    """
    operator_id: str
    generated_at: str
    biological: List[dict] = field(default_factory=list)
    structural: List[DomainForecastResult] = field(default_factory=list)
    environmental: List[DomainForecastResult] = field(default_factory=list)
    operational: List[DomainForecastResult] = field(default_factory=list)
    domain_summary: Dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'operator_id': self.operator_id,
            'generated_at': self.generated_at,
            'biological': self.biological,
            'structural': [r.to_dict() for r in self.structural],
            'environmental': [r.to_dict() for r in self.environmental],
            'operational': [r.to_dict() for r in self.operational],
            'domain_summary': self.domain_summary,
        }


class MultiDomainEngine:
    """
    Orchestrates structural, environmental, and operational forecasting
    across multiple sites. Biological forecasts are provided externally
    (from the existing C5AI+ pipeline) and stored verbatim.

    Usage
    -----
    engine = MultiDomainEngine()
    forecast = engine.run(
        operator_id='DEMO_OP',
        site_metas=[{'site_id': 'DEMO_OP_S01', 'biomass_value_nok': 207_360_000, ...}],
        structural_inputs={'DEMO_OP_S01': StructuralSiteInput(...)},
        environmental_inputs={'DEMO_OP_S01': EnvironmentalSiteInput(...)},
        operational_inputs={'DEMO_OP_S01': OperationalSiteInput(...)},
        biological_forecasts=[...],   # existing output, passed through
    )
    """

    def __init__(self) -> None:
        self._structural = StructuralForecaster()
        self._environmental = EnvironmentalForecaster()
        self._operational = OperationalForecaster()

    def run(
        self,
        operator_id: str,
        site_metas: List[Dict],
        structural_inputs: Dict[str, StructuralSiteInput],
        environmental_inputs: Dict[str, EnvironmentalSiteInput],
        operational_inputs: Dict[str, OperationalSiteInput],
        biological_forecasts: Optional[List[dict]] = None,
    ) -> MultiDomainForecast:
        """
        Run all 3 new domain forecasters across all sites and return a
        MultiDomainForecast.
        """
        struct_results: List[DomainForecastResult] = []
        env_results: List[DomainForecastResult] = []
        ops_results: List[DomainForecastResult] = []

        for meta in site_metas:
            sid = meta['site_id']

            if sid in structural_inputs:
                forecasts = self._structural.forecast(structural_inputs[sid], meta)
                struct_results.append(DomainForecastResult('structural', sid, forecasts))

            if sid in environmental_inputs:
                forecasts = self._environmental.forecast(environmental_inputs[sid], meta)
                env_results.append(DomainForecastResult('environmental', sid, forecasts))

            if sid in operational_inputs:
                forecasts = self._operational.forecast(operational_inputs[sid], meta)
                ops_results.append(DomainForecastResult('operational', sid, forecasts))

        domain_summary = self._build_domain_summary(
            struct_results, env_results, ops_results
        )

        return MultiDomainForecast(
            operator_id=operator_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            biological=biological_forecasts or [],
            structural=struct_results,
            environmental=env_results,
            operational=ops_results,
            domain_summary=domain_summary,
        )

    @staticmethod
    def _build_domain_summary(
        structural: List[DomainForecastResult],
        environmental: List[DomainForecastResult],
        operational: List[DomainForecastResult],
    ) -> Dict[str, dict]:
        summary: Dict[str, dict] = {}
        for domain_name, results in [
            ('structural', structural),
            ('environmental', environmental),
            ('operational', operational),
        ]:
            if not results:
                continue
            all_forecasts = [f for r in results for f in r.risk_forecasts]
            if not all_forecasts:
                continue
            total_loss = sum(f['expected_loss_mean'] for f in all_forecasts)
            top = max(all_forecasts, key=lambda f: f['event_probability'])
            summary[domain_name] = {
                'total_expected_loss': total_loss,
                'top_risk': top['risk_type'],
                'top_risk_probability': top['event_probability'],
                'n_sites': len(results),
            }
        return summary
