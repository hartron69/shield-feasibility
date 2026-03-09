"""
C5AI+ v5.0 – Model Registry.

Loads, saves and versions probability and severity models per (operator, risk_type).
Handles shadow model registration and promotion.

Storage layout:
  {store_dir}/registry/{operator_id}/{risk_type}.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

from c5ai_plus.models.probability_model import (
    BaseProbabilityModel,
    BetaBinomialModel,
    probability_model_from_dict,
)
from c5ai_plus.models.severity_model import LogNormalSeverityModel
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS

# Default prior probabilities per risk type
_PRIOR_PROBS = {
    "hab": 0.12,
    "lice": 0.30,
    "jellyfish": 0.08,
    "pathogen": 0.10,
}


def _default_concentration() -> float:
    return C5AI_SETTINGS.learning_bayesian_concentration


class ModelRegistry:
    """
    Registry that persists probability and severity models to JSON files.

    Parameters
    ----------
    store_dir : str
        Root directory for all learning store data.
    """

    def __init__(self, store_dir: str = ""):
        self._store_dir = store_dir or C5AI_SETTINGS.learning_store_dir
        self._prob_models: Dict[str, Dict[str, BaseProbabilityModel]] = {}
        self._sev_models: Dict[str, Dict[str, LogNormalSeverityModel]] = {}
        self._shadow_prob: Dict[str, Dict[str, BaseProbabilityModel]] = {}

    # ── Probability models ─────────────────────────────────────────────────

    def get_probability_model(
        self, operator_id: str, risk_type: str
    ) -> BaseProbabilityModel:
        """Return the current production probability model, loading from disk if needed."""
        self._ensure_prob_loaded(operator_id, risk_type)
        return self._prob_models[operator_id][risk_type]

    def update_probability_model(
        self, operator_id: str, risk_type: str, event_occurred: bool
    ) -> str:
        """Incorporate one observation and persist. Returns new version string."""
        model = self.get_probability_model(operator_id, risk_type)
        model.update(event_occurred)
        self._save_prob(operator_id, risk_type)
        return model.version

    # ── Severity models ────────────────────────────────────────────────────

    def get_severity_model(
        self, operator_id: str, risk_type: str
    ) -> LogNormalSeverityModel:
        """Return the current production severity model, loading from disk if needed."""
        self._ensure_sev_loaded(operator_id, risk_type)
        return self._sev_models[operator_id][risk_type]

    def update_severity_model(
        self, operator_id: str, risk_type: str, loss_nok: float
    ) -> str:
        """Incorporate one loss observation and persist. Returns new version string."""
        model = self.get_severity_model(operator_id, risk_type)
        model.update(loss_nok)
        self._save_sev(operator_id, risk_type)
        return model.version

    # ── Shadow model management ────────────────────────────────────────────

    def register_shadow(
        self,
        operator_id: str,
        risk_type: str,
        candidate_model: BaseProbabilityModel,
    ) -> None:
        """Register a candidate model as shadow (does NOT auto-promote)."""
        self._shadow_prob.setdefault(operator_id, {})[risk_type] = candidate_model

    def get_shadow_model(
        self, operator_id: str, risk_type: str
    ) -> Optional[BaseProbabilityModel]:
        """Return the shadow model if one is registered."""
        return self._shadow_prob.get(operator_id, {}).get(risk_type)

    def promote_shadow(self, operator_id: str, risk_type: str) -> bool:
        """
        Promote the shadow model to production.

        Returns True if a shadow existed and was promoted; False otherwise.
        """
        shadow = self.get_shadow_model(operator_id, risk_type)
        if shadow is None:
            return False
        self._prob_models.setdefault(operator_id, {})[risk_type] = shadow
        del self._shadow_prob[operator_id][risk_type]
        self._save_prob(operator_id, risk_type)
        return True

    # ── Version queries ────────────────────────────────────────────────────

    def model_versions(self, operator_id: str) -> Dict[str, str]:
        """Return {risk_type: version_string} for all known risk types."""
        from c5ai_plus.data_models.forecast_schema import RISK_TYPES
        versions = {}
        for rt in RISK_TYPES:
            model = self._prob_models.get(operator_id, {}).get(rt)
            if model is None:
                # Try loading from disk quietly
                try:
                    self._ensure_prob_loaded(operator_id, rt)
                    model = self._prob_models.get(operator_id, {}).get(rt)
                except Exception:
                    pass
            if model is not None:
                versions[rt] = model.version
        return versions

    # ── Internal persistence ───────────────────────────────────────────────

    def _registry_path(self, operator_id: str, risk_type: str) -> Path:
        p = Path(self._store_dir) / "registry" / operator_id
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{risk_type}.json"

    def _ensure_prob_loaded(self, operator_id: str, risk_type: str) -> None:
        if self._prob_models.get(operator_id, {}).get(risk_type) is None:
            self._prob_models.setdefault(operator_id, {})[risk_type] = (
                self._load_prob(operator_id, risk_type)
            )

    def _ensure_sev_loaded(self, operator_id: str, risk_type: str) -> None:
        if self._sev_models.get(operator_id, {}).get(risk_type) is None:
            self._sev_models.setdefault(operator_id, {})[risk_type] = (
                self._load_sev(operator_id, risk_type)
            )

    def _load_prob(self, operator_id: str, risk_type: str) -> BaseProbabilityModel:
        path = self._registry_path(operator_id, risk_type)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                prob_data = data.get("probability_model")
                if prob_data:
                    return probability_model_from_dict(prob_data)
            except Exception:
                pass
        # Fresh prior
        prior_prob = _PRIOR_PROBS.get(risk_type, 0.12)
        return BetaBinomialModel(
            prior_prob=prior_prob,
            concentration=_default_concentration(),
        )

    def _load_sev(self, operator_id: str, risk_type: str) -> LogNormalSeverityModel:
        path = self._registry_path(operator_id, risk_type)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                sev_data = data.get("severity_model")
                if sev_data:
                    return LogNormalSeverityModel.from_dict(sev_data)
            except Exception:
                pass
        return LogNormalSeverityModel()

    def _save_prob(self, operator_id: str, risk_type: str) -> None:
        path = self._registry_path(operator_id, risk_type)
        # Load existing file to preserve other keys
        data: dict = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                data = {}
        model = self._prob_models.get(operator_id, {}).get(risk_type)
        if model:
            data["probability_model"] = model.to_dict()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _save_sev(self, operator_id: str, risk_type: str) -> None:
        path = self._registry_path(operator_id, risk_type)
        data: dict = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                data = {}
        model = self._sev_models.get(operator_id, {}).get(risk_type)
        if model:
            data["severity_model"] = model.to_dict()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
