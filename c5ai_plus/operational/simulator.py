"""C5AI+ v5.0 – Mock Operational Site Simulator."""

from __future__ import annotations

from typing import Dict

from c5ai_plus.operational.inputs import OperationalSiteInput

_DEMO_OPERATIONAL: Dict[str, dict] = {
    'KH_S01': dict(  # Kornstad — open coast, most complex operations
        site_id='KH_S01',
        staffing_score=0.55,
        training_compliance_pct=72.0,
        incident_rate_12m=1.4,
        maintenance_backlog_score=0.48,
        critical_ops_frequency_per_month=6.5,
        equipment_readiness_score=0.65,
    ),
    'KH_S02': dict(  # Leite — average operations
        site_id='KH_S02',
        staffing_score=0.78,
        training_compliance_pct=88.0,
        incident_rate_12m=0.6,
        maintenance_backlog_score=0.22,
        critical_ops_frequency_per_month=3.8,
        equipment_readiness_score=0.82,
    ),
    'KH_S03': dict(  # Hogsnes — best operational standards
        site_id='KH_S03',
        staffing_score=0.92,
        training_compliance_pct=97.0,
        incident_rate_12m=0.2,
        maintenance_backlog_score=0.08,
        critical_ops_frequency_per_month=2.1,
        equipment_readiness_score=0.95,
    ),
}


class MockOperationalSimulator:
    """Return pre-calibrated OperationalSiteInput for each demo site."""

    def simulate(self, site_id: str) -> OperationalSiteInput:
        data = _DEMO_OPERATIONAL.get(site_id)
        if data is None:
            raise ValueError(f"Unknown demo site_id: {site_id!r}")
        return OperationalSiteInput(**data)

    def simulate_all(self) -> Dict[str, OperationalSiteInput]:
        return {sid: self.simulate(sid) for sid in _DEMO_OPERATIONAL}
