"""
C5AI+ v5.0 – Probability Shift Detector.

Generic (risk-type agnostic) detector for absolute/relative changes
in event probability and threshold crossings.
"""

from __future__ import annotations

from c5ai_plus.alerts.alert_models import ProbabilityShiftSignal


class ProbabilityShiftDetector:
    """
    Detect meaningful shifts in forecast probability between two time points.

    Parameters
    ----------
    abs_threshold : float
        Absolute change in probability that triggers the detector (default 0.10).
    rel_threshold : float
        Relative change (|delta| / previous) that triggers the detector (default 0.50).
    cross_low : float
        Lower threshold-crossing boundary (default 0.10).
    cross_high : float
        Upper threshold-crossing boundary (default 0.20).
    """

    def __init__(
        self,
        abs_threshold: float = 0.10,
        rel_threshold: float = 0.50,
        cross_low: float = 0.10,
        cross_high: float = 0.20,
    ) -> None:
        self._abs_threshold = abs_threshold
        self._rel_threshold = rel_threshold
        self._cross_low = cross_low
        self._cross_high = cross_high

    def detect(
        self,
        site_id: str,
        risk_type: str,
        previous_probability: float,
        current_probability: float,
    ) -> ProbabilityShiftSignal:
        """
        Analyse probability shift between two snapshots.

        Returns
        -------
        ProbabilityShiftSignal with triggered=True when any condition is met.
        """
        absolute_change = current_probability - previous_probability
        previous_safe = max(previous_probability, 1e-9)
        relative_change = absolute_change / previous_safe

        abs_triggered = abs(absolute_change) >= self._abs_threshold
        rel_triggered = abs(relative_change) >= self._rel_threshold
        threshold_crossed = self._crosses_threshold(previous_probability, current_probability)

        triggered = abs_triggered or rel_triggered or threshold_crossed

        return ProbabilityShiftSignal(
            site_id=site_id,
            risk_type=risk_type,
            previous_probability=previous_probability,
            current_probability=current_probability,
            absolute_change=absolute_change,
            relative_change=relative_change,
            threshold_crossed=threshold_crossed,
            triggered=triggered,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _crosses_threshold(self, previous: float, current: float) -> bool:
        """Return True if probability crossed either watch threshold."""
        for boundary in (self._cross_low, self._cross_high):
            if (previous < boundary <= current) or (current < boundary <= previous):
                return True
        return False
