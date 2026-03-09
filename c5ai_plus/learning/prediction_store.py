"""
C5AI+ v5.0 – Prediction Store.

Persists PredictionRecord objects to JSON files.

Storage layout:
  {store_dir}/predictions/{operator_id}/{risk_type}_{year}.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from c5ai_plus.data_models.learning_schema import PredictionRecord
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS


class PredictionStore:
    """Persists and retrieves PredictionRecord objects."""

    def __init__(self, store_dir: str = ""):
        self._store_dir = store_dir or C5AI_SETTINGS.learning_store_dir

    def _path(self, operator_id: str, risk_type: str, year: int) -> Path:
        p = Path(self._store_dir) / "predictions" / operator_id
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{risk_type}_{year}.json"

    def save(self, record: PredictionRecord) -> None:
        """Persist a PredictionRecord (overwrites existing for same key)."""
        path = self._path(record.operator_id, record.risk_type, record.forecast_year)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record.to_dict(), fh, indent=2)

    def load(
        self, operator_id: str, risk_type: str, year: int
    ) -> Optional[PredictionRecord]:
        """Load a single record; returns None if not found."""
        path = self._path(operator_id, risk_type, year)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return PredictionRecord.from_dict(json.load(fh))
        except Exception:
            return None

    def load_all(self, operator_id: str) -> List[PredictionRecord]:
        """Load all records for an operator."""
        base = Path(self._store_dir) / "predictions" / operator_id
        if not base.exists():
            return []
        records = []
        for path in sorted(base.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    records.append(PredictionRecord.from_dict(json.load(fh)))
            except Exception:
                pass
        return records

    def list_years(self, operator_id: str, risk_type: str) -> List[int]:
        """Return sorted list of years for which predictions exist."""
        base = Path(self._store_dir) / "predictions" / operator_id
        if not base.exists():
            return []
        years = []
        for path in base.glob(f"{risk_type}_*.json"):
            try:
                year = int(path.stem.split("_")[-1])
                years.append(year)
            except ValueError:
                pass
        return sorted(years)
