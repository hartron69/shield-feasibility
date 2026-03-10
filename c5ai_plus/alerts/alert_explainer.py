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
