"""
C5AI+ v5.0 – Pattern Detector.

Computes a weighted precursor_score in [0, 1] per site/risk_type and
returns a list of triggered PatternSignals.

When env_data is absent the detector falls back to a probability-level
proxy so callers never need to guard for missing data.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from c5ai_plus.alerts.alert_models import PatternSignal
from c5ai_plus.alerts.alert_rules import ALL_RULES, AlertRule
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS


class PatternDetector:
    """
    Rule-based precursor detector for four biological risk types.

    Parameters
    ----------
    trigger_z_score : float
        Z-score threshold above which a signal is considered triggered.
    """

    def __init__(self, trigger_z_score: float = 1.5) -> None:
        self._trigger_z = trigger_z_score

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(
        self,
        site_id: str,
        risk_type: str,
        current_probability: float,
        env_data: Optional[Dict] = None,
    ) -> Tuple[float, List[PatternSignal]]:
        """
        Compute precursor score and triggered signals.

        Parameters
        ----------
        site_id : str
        risk_type : str   ('hab' | 'lice' | 'jellyfish' | 'pathogen')
        current_probability : float
        env_data : dict | None
            Optional environmental context. Recognised keys vary by risk type.

        Returns
        -------
        precursor_score : float   in [0, 1]
        signals : List[PatternSignal]
        """
        rules = ALL_RULES.get(risk_type, [])
        if not rules:
            return 0.0, []

        env = env_data or {}
        signals: List[PatternSignal] = []
        total_weight = sum(r.weight for r in rules)

        for rule in rules:
            current_val, baseline_val, direction = self._evaluate_rule(
                rule, current_probability, env
            )
            z_score = self._z_score(current_val, baseline_val)
            triggered = abs(z_score) >= self._trigger_z

            signals.append(PatternSignal(
                site_id=site_id,
                risk_type=risk_type,
                signal_name=rule.rule_id,
                current_value=current_val,
                baseline_value=baseline_val,
                z_score=z_score,
                threshold=self._trigger_z,
                direction=direction,
                triggered=triggered,
            ))

        # Weighted precursor score: sum(weight * triggered) / sum(weight)
        score = sum(
            rule.weight * (1.0 if sig.triggered else 0.0)
            for rule, sig in zip(rules, signals)
        ) / (total_weight or 1.0)

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))
        return score, signals

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _z_score(current: float, baseline: float, sigma: float = 1.0) -> float:
        """Simple z-score assuming unit standard deviation."""
        return (current - baseline) / sigma

    def _evaluate_rule(
        self,
        rule: AlertRule,
        current_probability: float,
        env: Dict,
    ) -> Tuple[float, float, str]:
        """
        Map a rule to (current_value, baseline_value, direction).

        Falls back to probability-based proxy when no specific env key found.
        Returns floats on a normalised scale suitable for z-score computation.
        """
        rid = rule.rule_id

        # ── HAB rules ────────────────────────────────────────────────────────
        if rid == 'hab_warm_surface':
            thresh = C5AI_SETTINGS.hab_temp_threshold_high  # 20°C
            current = env.get('surface_temp_c', self._prob_to_temp_proxy(current_probability, 15.0, 22.0))
            baseline = 14.0
            return current, baseline, 'increasing'

        if rid == 'hab_low_oxygen':
            current = env.get('dissolved_oxygen_mg_l', 8.0 - current_probability * 4.0)
            baseline = 8.0
            # Low oxygen → direction is decreasing, invert for z-score
            return baseline - current, 0.0, 'decreasing'

        if rid == 'hab_high_nitrate':
            current = env.get('nitrate_umol_l', 5.0 + current_probability * 20.0)
            baseline = 5.0
            return current, baseline, 'increasing'

        if rid == 'hab_high_prior':
            baseline_prob = C5AI_SETTINGS.hab_prior_event_probability  # 0.12
            return current_probability, baseline_prob, 'increasing'

        # ── Lice rules ────────────────────────────────────────────────────────
        if rid == 'lice_warm_water':
            thresh = C5AI_SETTINGS.lice_temp_threshold  # 10°C
            current = env.get('water_temp_c', self._prob_to_temp_proxy(current_probability, 8.0, 14.0))
            baseline = thresh
            return current, baseline, 'increasing'

        if rid == 'lice_elevated_counts':
            current = env.get('lice_count_per_fish', current_probability * 10.0)
            baseline = 1.0  # treatment trigger threshold
            return current, baseline, 'increasing'

        if rid == 'lice_treatment_fatigue':
            current = env.get('treatments_last_12m', int(current_probability * 5))
            baseline = 1.0
            return float(current), baseline, 'increasing'

        if rid == 'lice_open_exposure':
            # 1 = open coast, 0 = sheltered; proxy from env or default low
            current = env.get('open_coast_flag', 0.5 + 0.5 * current_probability)
            baseline = 0.3
            return current, baseline, 'increasing'

        # ── Jellyfish rules ───────────────────────────────────────────────────
        if rid == 'jellyfish_warm_seasonal':
            month = env.get('month', 7)  # default July (peak season)
            bloom_factor = 1.0 if 5 <= month <= 9 else 0.0
            current = bloom_factor + current_probability
            baseline = C5AI_SETTINGS.jellyfish_prior_event_probability  # 0.08
            return current, baseline, 'increasing'

        if rid == 'jellyfish_current_pattern':
            current = env.get('onshore_current_score', current_probability * 1.5)
            baseline = 0.2
            return current, baseline, 'increasing'

        if rid == 'jellyfish_prior_sightings':
            current = env.get('nearby_sightings_count', int(current_probability * 8))
            baseline = 0.5
            return float(current), baseline, 'increasing'

        # ── Pathogen rules ────────────────────────────────────────────────────
        if rid == 'pathogen_neighbor_outbreak':
            current = env.get('neighbor_outbreak_flag', current_probability * 2.0)
            baseline = 0.1
            return current, baseline, 'increasing'

        if rid == 'pathogen_high_biomass':
            current = env.get('biomass_density_kg_m3', 15.0 + current_probability * 20.0)
            baseline = 15.0
            return current, baseline, 'increasing'

        if rid == 'pathogen_operational_stress':
            current = env.get('handling_events_last_30d', current_probability * 4.0)
            baseline = 0.5
            return current, baseline, 'increasing'

        if rid == 'pathogen_high_prior':
            baseline_prob = C5AI_SETTINGS.pathogen_prior_event_probability  # 0.10
            return current_probability, baseline_prob, 'increasing'

        # ── Structural rules ──────────────────────────────────────────────────
        if rid == 'mooring_overload':
            current = env.get('mooring_inspection_score', 0.8 - current_probability * 0.4)
            # Low score is bad, so invert for z-score (baseline - current)
            return 0.6 - current, 0.0, 'decreasing'

        if rid == 'net_degradation':
            current = env.get('net_strength_residual_pct', 90.0 - current_probability * 30.0)
            return 70.0 - current, 0.0, 'decreasing'

        if rid == 'cage_deformation':
            current = env.get('deformation_load_index', 0.2 + current_probability * 0.6)
            baseline = 0.5
            return current, baseline, 'increasing'

        if rid == 'anchor_deterioration':
            current = env.get('anchor_line_condition', 0.9 - current_probability * 0.5)
            return 0.5 - current, 0.0, 'decreasing'

        if rid == 'inspection_overdue':
            current = env.get('last_inspection_days_ago', 90 + int(current_probability * 200))
            baseline = 180.0
            return float(current), baseline, 'increasing'

        # ── Environmental rules ───────────────────────────────────────────────
        if rid == 'low_oxygen_env':
            current = env.get('dissolved_oxygen_mg_l', 8.5 - current_probability * 3.0)
            return 7.0 - current, 0.0, 'decreasing'

        if rid == 'temp_anomaly':
            temp = env.get('surface_temp_c', 10.0 + current_probability * 8.0)
            return abs(temp - 10.0), 3.0, 'increasing'

        if rid == 'high_current_wave':
            current = env.get('current_speed_ms', 0.3 + current_probability * 0.6)
            baseline = 0.6
            return current, baseline, 'increasing'

        if rid == 'ice_formation':
            current = env.get('ice_risk_score', current_probability * 0.5)
            baseline = 0.05
            return current, baseline, 'increasing'

        if rid == 'exposure_event':
            current = env.get('combined_exposure_score', 0.2 + current_probability * 0.8)
            baseline = 0.5
            return current, baseline, 'increasing'

        # ── Operational rules ─────────────────────────────────────────────────
        if rid == 'staffing_gap':
            current = env.get('staffing_score', 0.9 - current_probability * 0.4)
            return 0.6 - current, 0.0, 'decreasing'

        if rid == 'training_deficit':
            current = env.get('training_compliance_pct', 90 - current_probability * 30)
            return 80.0 - current, 0.0, 'decreasing'

        if rid == 'equipment_readiness_low':
            current = env.get('equipment_readiness_score', 0.9 - current_probability * 0.4)
            return 0.7 - current, 0.0, 'decreasing'

        if rid == 'high_incident_rate':
            current = env.get('incident_rate_12m', current_probability * 2.0)
            baseline = 1.0
            return float(current), baseline, 'increasing'

        if rid == 'maintenance_overdue':
            current = env.get('maintenance_backlog_score', current_probability * 0.6)
            baseline = 0.3
            return current, baseline, 'increasing'

        # Fallback: generic probability proxy
        return current_probability, 0.15, 'increasing'

    @staticmethod
    def _prob_to_temp_proxy(prob: float, low: float, high: float) -> float:
        """Map probability [0,1] linearly to temperature range [low, high]."""
        return low + prob * (high - low)
