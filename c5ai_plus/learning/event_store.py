"""
C5AI+ v5.0 – Event Store.

Persists ObservedEvent objects to JSON files and provides matched-pair joins.

Storage layout:
  {store_dir}/events/{operator_id}/{year}.json   ← list of events for that year
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

from c5ai_plus.data_models.learning_schema import ObservedEvent, PredictionRecord
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS


class EventStore:
    """Persists and retrieves ObservedEvent objects."""

    def __init__(self, store_dir: str = ""):
        self._store_dir = store_dir or C5AI_SETTINGS.learning_store_dir

    def _path(self, operator_id: str, year: int) -> Path:
        p = Path(self._store_dir) / "events" / operator_id
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{year}.json"

    def save(self, events: List[ObservedEvent]) -> None:
        """
        Persist a list of events for the same (operator_id, year).

        Merges with any previously stored events for that year.
        """
        if not events:
            return
        operator_id = events[0].operator_id
        year = events[0].event_year
        existing = self.load(operator_id, year) or []
        # Build a map keyed by (site_id, risk_type) to avoid duplicates
        merged: dict = {(e.site_id, e.risk_type): e for e in existing}
        for e in events:
            merged[(e.site_id, e.risk_type)] = e
        path = self._path(operator_id, year)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([e.to_dict() for e in merged.values()], fh, indent=2)

    def load(
        self, operator_id: str, year: int
    ) -> Optional[List[ObservedEvent]]:
        """Load all events for (operator_id, year); returns None if file missing."""
        path = self._path(operator_id, year)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            return [ObservedEvent.from_dict(d) for d in raw]
        except Exception:
            return None

    def load_all(self, operator_id: str) -> List[ObservedEvent]:
        """Load all events across all years for an operator."""
        base = Path(self._store_dir) / "events" / operator_id
        if not base.exists():
            return []
        all_events: List[ObservedEvent] = []
        for path in sorted(base.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                all_events.extend(ObservedEvent.from_dict(d) for d in raw)
            except Exception:
                pass
        return all_events

    def matched_pairs(
        self,
        operator_id: str,
        risk_type: str,
        predictions: List[PredictionRecord],
    ) -> List[Tuple[PredictionRecord, ObservedEvent]]:
        """
        Join predictions with observed events on (operator_id, risk_type, year).

        Returns only pairs where both a prediction and an observation exist.
        """
        # Build prediction lookup by year
        pred_map = {p.forecast_year: p for p in predictions
                    if p.risk_type == risk_type}

        pairs: List[Tuple[PredictionRecord, ObservedEvent]] = []
        all_events = self.load_all(operator_id)
        for event in all_events:
            if event.risk_type != risk_type:
                continue
            pred = pred_map.get(event.event_year)
            if pred is not None:
                pairs.append((pred, event))
        return pairs
