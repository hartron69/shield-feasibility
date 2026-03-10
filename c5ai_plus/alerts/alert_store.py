"""
C5AI+ v5.0 – Alert Store.

JSON persistence for AlertRecord.
Path pattern: {store_dir}/alerts/{site_id}/{year}.json
Each file is a JSON array of alert dicts, appended on save.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from c5ai_plus.alerts.alert_models import AlertRecord


class AlertStore:
    """
    Persistent store for AlertRecord objects.

    Parameters
    ----------
    store_dir : str
        Root directory for the alert store.
        Default: 'c5ai_plus/learning/store'
    """

    def __init__(self, store_dir: str = 'c5ai_plus/learning/store') -> None:
        self._root = store_dir

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(self, alert: AlertRecord) -> None:
        """Append a single AlertRecord to its year-scoped JSON file."""
        path = self._path_for(alert.site_id, alert.generated_at)
        existing = self._read_file(path)
        existing.append(alert.to_dict())
        self._write_file(path, existing)

    # ── Read ──────────────────────────────────────────────────────────────────

    def load_all(self, site_id: str) -> List[AlertRecord]:
        """Load all alerts for a site across all years."""
        site_dir = os.path.join(self._root, 'alerts', site_id)
        if not os.path.isdir(site_dir):
            return []

        records: List[AlertRecord] = []
        for fname in sorted(os.listdir(site_dir)):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(site_dir, fname)
            for d in self._read_file(fpath):
                try:
                    records.append(AlertRecord.from_dict(d))
                except (TypeError, KeyError):
                    pass
        return records

    def load_recent(self, site_id: str, n: int = 20) -> List[AlertRecord]:
        """Return up to the n most recent alerts for a site."""
        all_records = self.load_all(site_id)
        # Sort descending by generated_at
        all_records.sort(key=lambda r: r.generated_at, reverse=True)
        return all_records[:n]

    # ── Filter helpers ────────────────────────────────────────────────────────

    @staticmethod
    def filter_by_level(alerts: List[AlertRecord], level: str) -> List[AlertRecord]:
        """Return only alerts matching the given alert_level."""
        return [a for a in alerts if a.alert_level == level]

    @staticmethod
    def filter_by_risk_type(alerts: List[AlertRecord], risk_type: str) -> List[AlertRecord]:
        """Return only alerts matching the given risk_type."""
        return [a for a in alerts if a.risk_type == risk_type]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _path_for(self, site_id: str, generated_at: str) -> str:
        """Derive the file path for a given site / timestamp."""
        try:
            year = datetime.fromisoformat(generated_at).year
        except (ValueError, TypeError):
            year = datetime.now(timezone.utc).year
        return os.path.join(self._root, 'alerts', site_id, f'{year}.json')

    @staticmethod
    def _read_file(path: str) -> list:
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def _write_file(path: str, data: list) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
