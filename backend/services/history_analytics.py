"""
history_analytics.py – domain-linked analytics for historical loss records.

All functions are pure (no I/O side effects). They accept raw dicts (as
loaded from JSON) and return Pydantic schema objects.

Domain mapping
--------------
event_type → domain is driven by HISTORY_DOMAIN_MAP in backend.schemas.
Unknown event types receive the fallback domain "unknown" and generate a
mapping_warning entry in the returned summary.

Average-annual convention
--------------------------
Per-domain averages (events_per_year, average_annual_loss) always divide by the
*full* history window (n_years_observed = len(all years in dataset)), not just
the years in which that domain appears.  This makes cross-domain comparisons
meaningful and avoids inflating low-frequency domains.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from backend.schemas import (
    HISTORY_DOMAIN_MAP,
    HistoricalDomainSummary,
    HistoricalLossSummary,
    HistoryEventRow,
)

# Canonical ordering used for domain summary tables
ORDERED_DOMAINS = ("biological", "structural", "environmental", "operational")


# ── Domain mapping ────────────────────────────────────────────────────────────

def map_event_to_domain(event_type: str) -> str:
    """Return the risk domain for a given event_type string.

    Falls back to "unknown" for unmapped types; no exception is raised.
    """
    return HISTORY_DOMAIN_MAP.get(event_type, "unknown")


# ── Row construction ──────────────────────────────────────────────────────────

def build_history_event_rows(
    raw_records: List[dict],
) -> tuple[List[HistoryEventRow], List[str]]:
    """Convert raw JSON dicts into HistoryEventRow instances.

    The domain field is derived from event_type.  An explicit "domain" key in
    the raw record is respected if it is a recognised value; otherwise the
    mapping is applied.

    Returns
    -------
    (rows, mapping_warnings)
        rows            : HistoryEventRow list (same length as raw_records)
        mapping_warnings: human-readable warning strings for unknown event types
    """
    known_domains = set(HISTORY_DOMAIN_MAP.values()) | {"environmental"}
    rows: List[HistoryEventRow] = []
    warnings: List[str] = []

    for r in raw_records:
        # Allow explicit domain override in source data
        explicit = r.get("domain", "")
        if explicit and explicit in known_domains:
            domain = explicit
        else:
            event_type = r.get("event_type", "")
            domain = map_event_to_domain(event_type)
            if domain == "unknown":
                warnings.append(
                    f"Unknown event_type '{event_type}' (year {r.get('year')}) "
                    f"mapped to 'unknown' (default fallback)"
                )

        rows.append(
            HistoryEventRow(
                year=r["year"],
                event_type=r.get("event_type", ""),
                domain=domain,
                gross_loss=float(r["gross_loss"]),
                insured_loss=float(r["insured_loss"]),
                retained_loss=float(r["retained_loss"]),
            )
        )

    return rows, warnings


# ── Domain summaries ──────────────────────────────────────────────────────────

def compute_domain_summaries(
    rows: List[HistoryEventRow],
    n_years: int,
    portfolio_total_gross: float,
) -> List[HistoricalDomainSummary]:
    """Compute per-domain aggregated statistics.

    Domains are returned in ORDERED_DOMAINS order; "unknown" is appended last.
    Only domains with at least one record are included.
    """
    by_domain: Dict[str, List[HistoryEventRow]] = defaultdict(list)
    for row in rows:
        by_domain[row.domain].append(row)

    result: List[HistoricalDomainSummary] = []

    for domain in ORDERED_DOMAINS:
        drecs = by_domain.get(domain, [])
        if not drecs:
            continue
        result.append(_make_domain_summary(domain, drecs, n_years, portfolio_total_gross))

    # Unknown domain last
    unknown_recs = by_domain.get("unknown", [])
    if unknown_recs:
        result.append(_make_domain_summary("unknown", unknown_recs, n_years, portfolio_total_gross))

    return result


def _make_domain_summary(
    domain: str,
    drecs: List[HistoryEventRow],
    n_years: int,
    portfolio_total_gross: float,
) -> HistoricalDomainSummary:
    gross = sum(r.gross_loss for r in drecs)
    insured = sum(r.insured_loss for r in drecs)
    retained = sum(r.retained_loss for r in drecs)
    count = len(drecs)
    return HistoricalDomainSummary(
        domain=domain,
        event_count=count,
        total_gross_loss=gross,
        total_insured_loss=insured,
        total_retained_loss=retained,
        mean_severity=gross / count,
        events_per_year=count / n_years if n_years > 0 else 0.0,
        loss_share_pct=(gross / portfolio_total_gross * 100) if portfolio_total_gross > 0 else 0.0,
        years_with_events=sorted(set(r.year for r in drecs)),
    )


# ── Calibration parameter helpers ─────────────────────────────────────────────

def compute_portfolio_calibration_params(
    rows: List[HistoryEventRow],
    n_years: int,
) -> Dict[str, float]:
    """Portfolio-wide calibration: mean severity + events per year from all records."""
    if not rows or n_years == 0:
        return {}
    total_gross = sum(r.gross_loss for r in rows)
    return {
        "mean_loss_severity": float(round(total_gross / len(rows))),
        "expected_annual_events": round(len(rows) / n_years, 4),
    }


def compute_domain_calibration_params(
    rows: List[HistoryEventRow],
    n_years: int,
) -> Dict[str, float]:
    """Per-domain calibration parameters (Phase 6 scaffold).

    Keys follow the pattern ``{domain}_{param}``, e.g.:
        biological_mean_severity
        biological_events_per_year
        biological_annual_loss_mean

    These are stored in the summary payload for future use by a domain-aware
    Monte Carlo engine but do not yet modify the simulation.
    """
    if not rows or n_years == 0:
        return {}

    by_domain: Dict[str, List[HistoryEventRow]] = defaultdict(list)
    for row in rows:
        by_domain[row.domain].append(row)

    params: Dict[str, float] = {}
    for domain, drecs in by_domain.items():
        gross = sum(r.gross_loss for r in drecs)
        count = len(drecs)
        params[f"{domain}_mean_severity"] = float(round(gross / count))
        params[f"{domain}_events_per_year"] = round(count / n_years, 4)
        params[f"{domain}_annual_loss_mean"] = float(round(gross / n_years))

    return params


# ── Main factory ──────────────────────────────────────────────────────────────

def build_historical_loss_summary(
    raw_records: List[dict],
    calibration_active: bool,
    calibration_mode: str,
    alloc_calibrated_params: Dict[str, float],
    history_source: str = "template",
) -> HistoricalLossSummary:
    """Build a complete HistoricalLossSummary from raw template records.

    Parameters
    ----------
    raw_records:
        As returned by ``load_template_history()``.
    calibration_active:
        Forwarded from ``AllocationSummary.calibration_active``.
    calibration_mode:
        ``"none"`` | ``"portfolio"`` | ``"domain"``
    alloc_calibrated_params:
        Already-computed parameters from operator_builder (avoids re-computing).
    history_source:
        ``"template"`` or ``"user_provided"``.

    Returns
    -------
    HistoricalLossSummary
    """
    if not raw_records:
        return _empty_summary(calibration_active, calibration_mode, alloc_calibrated_params, history_source)

    rows, mapping_warnings = build_history_event_rows(raw_records)
    years = sorted(set(r.year for r in rows))
    n_years = len(years)

    portfolio_gross = sum(r.gross_loss for r in rows)
    portfolio_insured = sum(r.insured_loss for r in rows)
    portfolio_retained = sum(r.retained_loss for r in rows)
    n_records = len(rows)

    domain_summaries = compute_domain_summaries(rows, n_years, portfolio_gross)

    cal_source_map = {
        "none":      "none",
        "portfolio": "historical_loss_records",
        "domain":    "historical_domain_calibration",
    }

    return HistoricalLossSummary(
        history_loaded=True,
        history_source=history_source,
        record_count=n_records,
        years_covered=years,
        n_years_observed=n_years,
        portfolio_total_gross=portfolio_gross,
        portfolio_total_insured=portfolio_insured,
        portfolio_total_retained=portfolio_retained,
        portfolio_mean_severity=portfolio_gross / n_records,
        portfolio_events_per_year=n_records / n_years,
        domain_summaries=domain_summaries,
        mapping_warnings=mapping_warnings,
        calibration_active=calibration_active,
        calibration_source=cal_source_map.get(calibration_mode, "none"),
        calibration_mode=calibration_mode,
        calibrated_parameters=alloc_calibrated_params,
        records=rows,
    )


def _empty_summary(
    calibration_active: bool,
    calibration_mode: str,
    calibrated_params: Dict[str, float],
    history_source: str,
) -> HistoricalLossSummary:
    return HistoricalLossSummary(
        history_loaded=False,
        history_source=history_source,
        record_count=0,
        years_covered=[],
        n_years_observed=0,
        portfolio_total_gross=0.0,
        portfolio_total_insured=0.0,
        portfolio_total_retained=0.0,
        portfolio_mean_severity=0.0,
        portfolio_events_per_year=0.0,
        domain_summaries=[],
        mapping_warnings=[],
        calibration_active=calibration_active,
        calibration_source="none",
        calibration_mode=calibration_mode,
        calibrated_parameters=calibrated_params,
        records=[],
    )
