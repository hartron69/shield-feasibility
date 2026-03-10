"""
C5AI+ v5.0 – Alert Simulator.

Generates canonical demo alert scenarios for frontend development and
integration testing. Returns fully-populated AlertRecord objects.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from c5ai_plus.alerts.alert_models import AlertRecord
from c5ai_plus.alerts.alert_explainer import AlertExplainer, RECOMMENDED_ACTIONS

_EXPLAINER = AlertExplainer()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


from c5ai_plus.alerts.alert_models import RISK_TYPE_DOMAIN


def _make_alert(
    site_id: str,
    risk_type: str,
    alert_type: str,
    alert_level: str,
    current_probability: float,
    previous_probability: float,
    triggered_rules: List[str],
    top_drivers: List[str],
    workflow_status: str = 'OPEN',
) -> AlertRecord:
    alert = AlertRecord(
        alert_id=uuid.uuid4().hex,
        site_id=site_id,
        risk_type=risk_type,
        alert_type=alert_type,
        alert_level=alert_level,
        current_probability=current_probability,
        previous_probability=previous_probability,
        probability_delta=current_probability - previous_probability,
        top_drivers=top_drivers,
        triggered_rules=triggered_rules,
        explanation_text='',
        recommended_actions=[],
        workflow_status=workflow_status,
        generated_at=_now(),
        domain=RISK_TYPE_DOMAIN.get(risk_type, ''),
    )
    _EXPLAINER.explain(alert)
    return alert


class AlertSimulator:
    """Generate canonical demo alert scenarios."""

    def simulate_hab_warning(self, site_id: str = 'DEMO_S01') -> AlertRecord:
        """HAB WARNING — warm surface + low oxygen detected."""
        return _make_alert(
            site_id=site_id,
            risk_type='hab',
            alert_type='composite',
            alert_level='WARNING',
            current_probability=0.28,
            previous_probability=0.12,
            triggered_rules=['hab_warm_surface', 'hab_low_oxygen', 'hab_high_prior'],
            top_drivers=[
                'Surface water temperature above HAB threshold (>15°C)',
                'Dissolved oxygen below safety threshold (<7 mg/L)',
                'Prior event probability above baseline (>15%)',
            ],
        )

    def simulate_lice_watch(self, site_id: str = 'DEMO_S02') -> AlertRecord:
        """Sea lice WATCH — temperature rising, early season."""
        return _make_alert(
            site_id=site_id,
            risk_type='lice',
            alert_type='pattern',
            alert_level='WATCH',
            current_probability=0.18,
            previous_probability=0.14,
            triggered_rules=['lice_warm_water'],
            top_drivers=[
                'Water temperature above lice reproduction threshold (>10°C)',
            ],
        )

    def simulate_jellyfish_critical(self, site_id: str = 'DEMO_S01') -> AlertRecord:
        """Jellyfish CRITICAL — bloom confirmed in neighbouring fjord."""
        return _make_alert(
            site_id=site_id,
            risk_type='jellyfish',
            alert_type='composite',
            alert_level='CRITICAL',
            current_probability=0.42,
            previous_probability=0.08,
            triggered_rules=['jellyfish_warm_seasonal', 'jellyfish_current_pattern', 'jellyfish_prior_sightings'],
            top_drivers=[
                'Seasonal warm period coinciding with jellyfish bloom window',
                'Onshore current pattern directing bloom toward site',
                'Recent jellyfish sightings reported in neighbouring fjords',
            ],
        )

    def simulate_pathogen_warning(self, site_id: str = 'DEMO_S03') -> AlertRecord:
        """Pathogen WARNING — neighbouring site outbreak reported."""
        return _make_alert(
            site_id=site_id,
            risk_type='pathogen',
            alert_type='pattern',
            alert_level='WARNING',
            current_probability=0.26,
            previous_probability=0.10,
            triggered_rules=['pathogen_neighbor_outbreak', 'pathogen_high_biomass'],
            top_drivers=[
                'Active pathogen outbreak at neighbouring site within 50 km',
                'Biomass density above threshold increasing transmission risk',
            ],
        )

    # ── Structural scenarios ──────────────────────────────────────────────────

    def simulate_mooring_warning(self, site_id: str = 'DEMO_S01') -> AlertRecord:
        """Mooring WARNING — inspection overdue and load index elevated."""
        return _make_alert(
            site_id=site_id,
            risk_type='mooring_failure',
            alert_type='composite',
            alert_level='WARNING',
            current_probability=0.22,
            previous_probability=0.05,
            triggered_rules=['mooring_overload', 'inspection_overdue'],
            top_drivers=[
                'Mooring inspection score low (<0.60)',
                'Inspection overdue (>180 days)',
            ],
        )

    def simulate_net_critical(self, site_id: str = 'DEMO_S01') -> AlertRecord:
        """Net integrity CRITICAL — net strength below safe limit."""
        return _make_alert(
            site_id=site_id,
            risk_type='net_integrity',
            alert_type='pattern',
            alert_level='CRITICAL',
            current_probability=0.38,
            previous_probability=0.08,
            triggered_rules=['net_degradation', 'cage_deformation'],
            top_drivers=[
                'Net strength residual below 70%',
                'Deformation load index elevated above baseline',
            ],
        )

    # ── Environmental scenarios ───────────────────────────────────────────────

    def simulate_oxygen_warning(self, site_id: str = 'DEMO_S01') -> AlertRecord:
        """Oxygen stress WARNING — DO below safe threshold."""
        return _make_alert(
            site_id=site_id,
            risk_type='oxygen_stress',
            alert_type='pattern',
            alert_level='WARNING',
            current_probability=0.25,
            previous_probability=0.10,
            triggered_rules=['low_oxygen_env'],
            top_drivers=['Dissolved oxygen below critical threshold (<7 mg/L)'],
        )

    def simulate_storm_critical(self, site_id: str = 'DEMO_S01') -> AlertRecord:
        """Storm CRITICAL — current speed and wave height exceeding design limits."""
        return _make_alert(
            site_id=site_id,
            risk_type='current_storm',
            alert_type='composite',
            alert_level='CRITICAL',
            current_probability=0.42,
            previous_probability=0.07,
            triggered_rules=['high_current_wave', 'exposure_event'],
            top_drivers=[
                'Current speed and wave height exceed design limits',
                'Open-coast exposure with anomalous combined loading',
            ],
        )

    def simulate_temp_watch(self, site_id: str = 'DEMO_S02') -> AlertRecord:
        """Temperature WATCH — surface temperature rising above safe range."""
        return _make_alert(
            site_id=site_id,
            risk_type='temperature_extreme',
            alert_type='probability_shift',
            alert_level='WATCH',
            current_probability=0.14,
            previous_probability=0.08,
            triggered_rules=[],
            top_drivers=[],
        )

    # ── Operational scenarios ─────────────────────────────────────────────────

    def simulate_staffing_warning(self, site_id: str = 'DEMO_S02') -> AlertRecord:
        """Staffing WARNING — staffing gap and training deficit."""
        return _make_alert(
            site_id=site_id,
            risk_type='human_error',
            alert_type='composite',
            alert_level='WARNING',
            current_probability=0.28,
            previous_probability=0.12,
            triggered_rules=['staffing_gap', 'training_deficit'],
            top_drivers=[
                'Staffing score below safe threshold (<0.60)',
                'Training compliance below 80% requirement',
            ],
        )

    def simulate_equipment_watch(self, site_id: str = 'DEMO_S03') -> AlertRecord:
        """Equipment readiness WATCH — declining readiness score."""
        return _make_alert(
            site_id=site_id,
            risk_type='equipment_failure',
            alert_type='pattern',
            alert_level='WATCH',
            current_probability=0.16,
            previous_probability=0.10,
            triggered_rules=['equipment_readiness_low'],
            top_drivers=['Equipment readiness score below operational minimum (0.70)'],
        )

    def simulate_maintenance_warning(self, site_id: str = 'DEMO_S03') -> AlertRecord:
        """Maintenance backlog WARNING — backlog score elevated."""
        return _make_alert(
            site_id=site_id,
            risk_type='maintenance_backlog',
            alert_type='pattern',
            alert_level='WARNING',
            current_probability=0.26,
            previous_probability=0.09,
            triggered_rules=['maintenance_overdue'],
            top_drivers=['Maintenance backlog score above safe level (0.30)'],
        )

    def simulate_all(self) -> List[AlertRecord]:
        """
        Return ~18 diverse alert records covering all 4 domains,
        4 alert levels, 3 sites, and mixed workflow statuses.
        """
        alerts = [
            # ── CRITICAL ─────────────────────────────────────────────────────
            self.simulate_jellyfish_critical('DEMO_S01'),
            _make_alert('DEMO_S02', 'hab', 'composite', 'CRITICAL',
                        0.38, 0.12, ['hab_warm_surface', 'hab_low_oxygen', 'hab_high_nitrate', 'hab_high_prior'],
                        ['Surface temp >15°C', 'Low oxygen', 'High nitrate load', 'High prior'], 'OPEN'),
            self.simulate_net_critical('DEMO_S01'),
            self.simulate_storm_critical('DEMO_S01'),
            # ── WARNING ───────────────────────────────────────────────────────
            self.simulate_hab_warning('DEMO_S01'),
            self.simulate_pathogen_warning('DEMO_S03'),
            _make_alert('DEMO_S02', 'lice', 'composite', 'WARNING',
                        0.30, 0.18, ['lice_elevated_counts', 'lice_treatment_fatigue'],
                        ['Elevated lice counts', 'Treatment fatigue'], 'IN_PROGRESS'),
            self.simulate_mooring_warning('DEMO_S01'),
            self.simulate_oxygen_warning('DEMO_S01'),
            self.simulate_staffing_warning('DEMO_S02'),
            self.simulate_maintenance_warning('DEMO_S03'),
            # ── WATCH ─────────────────────────────────────────────────────────
            self.simulate_lice_watch('DEMO_S02'),
            _make_alert('DEMO_S03', 'jellyfish', 'pattern', 'WATCH',
                        0.12, 0.08, ['jellyfish_warm_seasonal'],
                        ['Seasonal bloom window active'], 'ACKNOWLEDGED'),
            _make_alert('DEMO_S01', 'pathogen', 'probability_shift', 'WATCH',
                        0.14, 0.10, [], [], 'OPEN'),
            self.simulate_temp_watch('DEMO_S02'),
            self.simulate_equipment_watch('DEMO_S03'),
            # ── NORMAL ────────────────────────────────────────────────────────
            _make_alert('DEMO_S03', 'lice', 'probability_shift', 'NORMAL',
                        0.20, 0.22, [], [], 'CLOSED'),
            _make_alert('DEMO_S01', 'lice', 'pattern', 'NORMAL',
                        0.15, 0.18, [], [], 'CLOSED'),
        ]
        return alerts
