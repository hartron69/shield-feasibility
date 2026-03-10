"""C5AI+ v5.0 – Structural domain alert rules.

Re-exports STRUCTURAL_RULES from the central alert_rules module so callers
can import from either location.
"""

from c5ai_plus.alerts.alert_rules import STRUCTURAL_RULES

__all__ = ['STRUCTURAL_RULES']
