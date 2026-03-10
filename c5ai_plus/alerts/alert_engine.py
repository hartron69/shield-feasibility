"""
C5AI+ v5.0 – Alert Engine.

Orchestrates PatternDetector + ProbabilityShiftDetector → List[AlertRecord].
Level mapping is transparent and documented inline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from c5ai_plus.alerts.alert_explainer import AlertExplainer
from c5ai_plus.alerts.alert_models import AlertRecord, AlertSummary, RISK_TYPE_DOMAIN
from c5ai_plus.alerts.alert_rules import ALL_RULES
from c5ai_plus.alerts.pattern_detector import PatternDetector
from c5ai_plus.alerts.probability_shift_detector import ProbabilityShiftDetector
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS

# ── Risk-type prior map (fallback when no previous_probabilities provided) ───
_RISK_TYPE_PRIORS: Dict[str, float] = {
    'hab':                  C5AI_SETTINGS.hab_prior_event_probability,
    'lice':                 C5AI_SETTINGS.lice_prior_event_probability,
    'jellyfish':            C5AI_SETTINGS.jellyfish_prior_event_probability,
    'pathogen':             C5AI_SETTINGS.pathogen_prior_event_probability,
    'mooring_failure':      C5AI_SETTINGS.mooring_failure_prior_probability,
    'net_integrity':        C5AI_SETTINGS.net_integrity_prior_probability,
    'cage_structural':      C5AI_SETTINGS.cage_structural_prior_probability,
    'deformation':          C5AI_SETTINGS.deformation_prior_probability,
    'anchor_deterioration': C5AI_SETTINGS.anchor_deterioration_prior_probability,
    'oxygen_stress':        C5AI_SETTINGS.oxygen_stress_prior_probability,
    'temperature_extreme':  C5AI_SETTINGS.temperature_extreme_prior_probability,
    'current_storm':        C5AI_SETTINGS.current_storm_prior_probability,
    'ice':                  C5AI_SETTINGS.ice_prior_probability,
    'exposure_anomaly':     C5AI_SETTINGS.exposure_anomaly_prior_probability,
    'human_error':          C5AI_SETTINGS.human_error_prior_probability,
    'procedure_failure':    C5AI_SETTINGS.procedure_failure_prior_probability,
    'equipment_failure':    C5AI_SETTINGS.equipment_failure_prior_probability,
    'incident':             C5AI_SETTINGS.incident_prior_probability,
    'maintenance_backlog':  C5AI_SETTINGS.maintenance_backlog_prior_probability,
}


def _determine_level(
    precursor_score: float,
    current_prob: float,
    shift_triggered: bool,
) -> str:
    """
    Transparent level mapping:
      precursor_score >= 0.70  OR  current_prob >= 0.35  → CRITICAL
      precursor_score >= 0.45  OR  current_prob >= 0.25  → WARNING
      precursor_score >= 0.25  OR  shift.triggered        → WATCH
      otherwise                                           → NORMAL
    """
    if precursor_score >= 0.70 or current_prob >= 0.35:
        return 'CRITICAL'
    if precursor_score >= 0.45 or current_prob >= 0.25:
        return 'WARNING'
    if precursor_score >= 0.25 or shift_triggered:
        return 'WATCH'
    return 'NORMAL'


class AlertEngine:
    """
    Main alert orchestration engine.

    Parameters
    ----------
    pattern_detector : PatternDetector | None  (creates default if None)
    shift_detector   : ProbabilityShiftDetector | None
    explainer        : AlertExplainer | None
    """

    def __init__(
        self,
        pattern_detector: Optional[PatternDetector] = None,
        shift_detector: Optional[ProbabilityShiftDetector] = None,
        explainer: Optional[AlertExplainer] = None,
    ) -> None:
        self._pattern = pattern_detector or PatternDetector()
        self._shift = shift_detector or ProbabilityShiftDetector()
        self._explainer = explainer or AlertExplainer()

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_alerts(
        self,
        site_forecasts: Dict,
        previous_probabilities: Optional[Dict[str, Dict[str, float]]] = None,
        env_data: Optional[Dict] = None,
    ) -> List[AlertRecord]:
        """
        Generate AlertRecord list from site forecast data.

        Parameters
        ----------
        site_forecasts : Dict
            Nested structure:  {site_id: {risk_type: {'event_probability': float, ...}}}
        previous_probabilities : dict | None
            {site_id: {risk_type: float}}  Previous snapshot for shift detection.
            When None, C5AI_SETTINGS priors are used as baseline.
        env_data : dict | None
            {site_id: dict}  Optional environmental context per site.

        Returns
        -------
        List[AlertRecord] — one per (site_id, risk_type) combination.
        """
        alerts: List[AlertRecord] = []
        now = datetime.now(timezone.utc).isoformat()
        env_data = env_data or {}
        previous_probabilities = previous_probabilities or {}

        for site_id, risk_map in site_forecasts.items():
            site_env = env_data.get(site_id, {})
            prev_site = previous_probabilities.get(site_id, {})

            for risk_type, forecast in risk_map.items():
                current_prob = float(forecast.get('event_probability', 0.0))
                prior = _RISK_TYPE_PRIORS.get(risk_type, 0.10)
                previous_prob = float(prev_site.get(risk_type, prior))

                # 1. Pattern detection
                precursor_score, pattern_signals = self._pattern.detect(
                    site_id=site_id,
                    risk_type=risk_type,
                    current_probability=current_prob,
                    env_data=site_env,
                )

                # 2. Probability shift detection
                shift_signal = self._shift.detect(
                    site_id=site_id,
                    risk_type=risk_type,
                    previous_probability=previous_prob,
                    current_probability=current_prob,
                )

                # 3. Level determination
                level = _determine_level(precursor_score, current_prob, shift_signal.triggered)

                # 4. Identify triggered rules
                triggered_rules = [s.signal_name for s in pattern_signals if s.triggered]

                # 5. Determine alert_type
                has_pattern = bool(triggered_rules)
                has_shift = shift_signal.triggered
                if has_pattern and has_shift:
                    alert_type = 'composite'
                elif has_pattern:
                    alert_type = 'pattern'
                else:
                    alert_type = 'probability_shift'

                # 6. Build top_drivers from rules
                rules = ALL_RULES.get(risk_type, [])
                top_drivers = [r.description for r in rules if r.rule_id in triggered_rules][:3]

                alert = AlertRecord(
                    alert_id=uuid.uuid4().hex,
                    site_id=site_id,
                    risk_type=risk_type,
                    alert_type=alert_type,
                    alert_level=level,
                    current_probability=current_prob,
                    previous_probability=previous_prob,
                    probability_delta=current_prob - previous_prob,
                    top_drivers=top_drivers,
                    triggered_rules=triggered_rules,
                    explanation_text='',
                    recommended_actions=[],
                    generated_at=now,
                    domain=RISK_TYPE_DOMAIN.get(risk_type, ''),
                )

                # 7. Explain
                self._explainer.explain(alert, pattern_signals, shift_signal)
                alerts.append(alert)

        return alerts

    def summarise(self, alerts: List[AlertRecord]) -> List[AlertSummary]:
        """
        Aggregate alerts into per-site AlertSummary records.

        Parameters
        ----------
        alerts : List[AlertRecord]

        Returns
        -------
        List[AlertSummary]  one per unique site_id.
        """
        from collections import Counter

        sites: Dict[str, List[AlertRecord]] = {}
        for a in alerts:
            sites.setdefault(a.site_id, []).append(a)

        summaries = []
        for site_id, site_alerts in sites.items():
            crit = sum(1 for a in site_alerts if a.alert_level == 'CRITICAL')
            warn = sum(1 for a in site_alerts if a.alert_level == 'WARNING')
            risk_counts = Counter(a.risk_type for a in site_alerts
                                  if a.alert_level in ('CRITICAL', 'WARNING', 'WATCH'))
            top_risk = risk_counts.most_common(1)[0][0] if risk_counts else (
                site_alerts[0].risk_type if site_alerts else ''
            )
            latest = max((a.generated_at for a in site_alerts), default='')
            summaries.append(AlertSummary(
                site_id=site_id,
                total_alerts=len(site_alerts),
                critical_alerts=crit,
                warning_alerts=warn,
                top_risk_type=top_risk,
                latest_alert_at=latest,
            ))

        return summaries
