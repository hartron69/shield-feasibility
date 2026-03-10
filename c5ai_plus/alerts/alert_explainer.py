"""
C5AI+ v5.0 – Alert Explainer.

Stateless. Fills explanation_text and recommended_actions on an AlertRecord
based on alert level, risk type, and triggered signals.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from c5ai_plus.alerts.alert_models import AlertRecord, PatternSignal, ProbabilityShiftSignal


RECOMMENDED_ACTIONS: Dict[str, List[str]] = {
    'hab': [
        'Deploy environmental sensors to monitor algal concentrations',
        'Prepare emergency harvest protocol for early biomass removal',
        'Activate aeration systems to maintain dissolved oxygen levels',
        'Notify feed management team to reduce feeding intensity',
        'Contact local authorities and neighbouring sites to coordinate response',
    ],
    'lice': [
        'Apply lice treatment protocol per current veterinary guidance',
        'Install lice barriers (skirts) to reduce infestation from ambient water',
        'Increase monitoring frequency to daily lice counts',
        'Evaluate cleaner fish (wrasse/lumpsucker) deployment',
        'Report infestation level to authorities per regulatory requirements',
    ],
    'jellyfish': [
        'Deploy jellyfish barriers (screens) around net pen perimeter',
        'Monitor current patterns and Metocean forecasts for bloom direction',
        'Prepare contingency feeding reduction schedule',
        'Increase surface net inspection frequency',
        'Coordinate with neighbouring sites for shared early warning',
    ],
    'pathogen': [
        'Activate emergency response plan per site health protocol',
        'Engage fish health veterinarian for immediate site assessment',
        'Implement strict biosecurity measures (PPE, equipment disinfection)',
        'Consider early harvest of affected compartments',
        'Report to national fish health authority (Mattilsynet)',
    ],
    # Structural
    'mooring_failure': [
        'Deploy dive team for immediate mooring system inspection',
        'Reduce biomass load if mooring capacity is compromised',
        'Notify harbor master and adjacent operators of potential hazard',
        'Activate contingency anchoring plan as precaution',
        'Document findings and schedule remediation works',
    ],
    'net_integrity': [
        'Inspect net panels for tears, abrasions, and fouling',
        'Reduce stocking density to lower net stress loading',
        'Schedule net replacement or repair crew within 48 hours',
        'Increase underwater camera monitoring frequency',
        'Review fouling management and anti-fouling treatment schedule',
    ],
    'cage_structural': [
        'Conduct full structural inspection of cage frame and collar',
        'Remove excess load (excess biomass or equipment) from cage',
        'Engage structural engineer for assessment if deformation is visible',
        'Review storm load forecasts and prepare contingency securing plan',
        'Document structural condition and report to insurer if required',
    ],
    'deformation': [
        'Increase inspection frequency to daily visual checks',
        'Review deformation load index against design specification',
        'Schedule engineering assessment if load index exceeds 0.7',
        'Check weather forecast and prepare for load reduction if storm approaching',
        'Update maintenance log and notify operations manager',
    ],
    'anchor_deterioration': [
        'Conduct underwater anchor line inspection within 72 hours',
        'Replace any anchor lines with condition score below 0.4',
        'Review anchoring system design against current load requirements',
        'Document deterioration rate and schedule preventive replacement',
        'Notify insurer of anchor condition status',
    ],
    # Environmental
    'oxygen_stress': [
        'Activate aeration and oxygenation systems immediately',
        'Reduce feeding rate to lower biological oxygen demand',
        'Monitor dissolved oxygen every 30 minutes at multiple depths',
        'Prepare emergency harvest if oxygen levels fall below 6 mg/L',
        'Investigate upstream current conditions and nutrient loading',
    ],
    'temperature_extreme': [
        'Monitor fish behaviour for signs of thermal stress',
        'Adjust feeding schedule to match reduced metabolic capacity',
        'Prepare thermal curtain deployment if surface heating persists',
        'Contact feed supplier to adjust nutritional profile for temperature',
        'Log temperature profile at depth and compare to design range',
    ],
    'current_storm': [
        'Secure all loose equipment on walkways and service boats',
        'Verify mooring system integrity before storm arrival',
        'Reduce feeding or suspend operations during peak current/wave loading',
        'Activate storm protocol and notify all site personnel',
        'Monitor net deformation and anchor tension during event',
    ],
    'ice': [
        'Inspect surface floats, collar, and mooring lines for ice formation',
        'Deploy ice management measures (air bubbling, mechanical breaking)',
        'Suspend operations until ice risk is below safe threshold',
        'Notify insurer and authorities if ice damage is observed',
        'Increase monitoring frequency during cold snap',
    ],
    'exposure_anomaly': [
        'Review combined environmental loading against site design limits',
        'Inspect all exposed equipment for anomalous wear or damage',
        'Reduce biomass stocking if anomalous loading is persistent',
        'Update exposure risk assessment and notify risk manager',
        'Coordinate with metocean service for extended forecast',
    ],
    # Operational
    'human_error': [
        'Review staffing levels and schedule immediate gap cover',
        'Conduct team briefing on high-risk activities planned this week',
        'Activate buddy-system protocol for critical operations',
        'Review incident log for recent near-misses requiring follow-up',
        'Notify operations manager of staffing shortfall risk',
    ],
    'procedure_failure': [
        'Conduct emergency refresher training for procedures with low compliance',
        'Audit procedure documentation for accuracy and accessibility',
        'Assign compliance champion for each high-risk procedure category',
        'Review recent deviations and implement corrective actions',
        'Schedule competency assessment for all site personnel within 30 days',
    ],
    'equipment_failure': [
        'Conduct immediate equipment readiness audit across all site systems',
        'Prioritise repair or replacement of equipment with readiness score < 0.6',
        'Activate backup equipment protocols for critical systems',
        'Review maintenance schedule and address all overdue items',
        'Document equipment status and escalate to technical manager',
    ],
    'incident': [
        'Review all incidents from last 12 months for root cause patterns',
        'Implement targeted corrective actions for recurring incident types',
        'Increase supervisory presence during high-risk activities',
        'Report incident trends to HSE officer and management',
        'Consider third-party safety audit if rate remains elevated',
    ],
    'maintenance_backlog': [
        'Prioritise and schedule all overdue maintenance within 14 days',
        'Allocate additional technical resource to clear backlog',
        'Review criticality of deferred items — escalate safety-critical work',
        'Update CMMS (maintenance management system) with revised plan',
        'Notify operations manager and risk committee of backlog status',
    ],
}

_LEVEL_PREAMBLE: Dict[str, str] = {
    'NORMAL': 'Risk conditions are within expected range.',
    'WATCH': 'Early precursor conditions detected — elevated monitoring advised.',
    'WARNING': 'Significant risk escalation detected — immediate operational review required.',
    'CRITICAL': 'CRITICAL risk conditions. Board-level escalation and immediate action required.',
}


class AlertExplainer:
    """
    Generates human-readable explanations and action lists for AlertRecords.
    """

    def explain(
        self,
        alert: AlertRecord,
        pattern_signals: Optional[List[PatternSignal]] = None,
        shift_signal: Optional[ProbabilityShiftSignal] = None,
    ) -> AlertRecord:
        """
        Populate explanation_text and recommended_actions on the alert.
        Also sets board_visibility=True for CRITICAL alerts.

        Parameters
        ----------
        alert : AlertRecord  (mutated in-place and returned)
        pattern_signals : list of PatternSignal for this alert (optional)
        shift_signal : ProbabilityShiftSignal for this alert (optional)

        Returns
        -------
        AlertRecord with explanation_text and recommended_actions filled.
        """
        preamble = _LEVEL_PREAMBLE.get(alert.alert_level, '')
        parts = [preamble]

        # Add probability context
        pct_curr = alert.current_probability * 100
        pct_prev = alert.previous_probability * 100
        delta = alert.probability_delta * 100
        parts.append(
            f"Current {alert.risk_type.upper()} event probability: {pct_curr:.1f}% "
            f"(previously {pct_prev:.1f}%, change {delta:+.1f}pp)."
        )

        # Add pattern signal context
        if pattern_signals:
            triggered = [s for s in pattern_signals if s.triggered]
            if triggered:
                names = ', '.join(s.signal_name for s in triggered)
                parts.append(f"Triggered precursor signals: {names}.")

        # Add shift signal context
        if shift_signal and shift_signal.triggered:
            if shift_signal.threshold_crossed:
                parts.append(
                    f"Probability crossed a key watch threshold "
                    f"({shift_signal.previous_probability:.2f} → {shift_signal.current_probability:.2f})."
                )
            elif abs(shift_signal.absolute_change) >= 0.10:
                direction = 'increased' if shift_signal.absolute_change > 0 else 'decreased'
                parts.append(
                    f"Probability {direction} by {abs(shift_signal.absolute_change):.2f} "
                    f"({shift_signal.relative_change * 100:+.0f}% relative)."
                )

        alert.explanation_text = ' '.join(parts)

        # Recommended actions: take first N actions based on severity
        all_actions = RECOMMENDED_ACTIONS.get(alert.risk_type, [])
        n_actions = {
            'NORMAL': 1,
            'WATCH': 2,
            'WARNING': 3,
            'CRITICAL': len(all_actions),
        }.get(alert.alert_level, 2)
        alert.recommended_actions = all_actions[:n_actions]

        # Board visibility for CRITICAL
        if alert.alert_level == 'CRITICAL':
            alert.board_visibility = True

        return alert
