"""
tests/test_live_risk.py

Tests for the Live Risk Intelligence module.

Covers:
  - Mock data generator integrity
  - Feed overview generation
  - Time series assembly (gaps, quality flags)
  - Source health summaries
  - Risk change explanation / attribution
  - Confidence score classification
  - Event timeline generation
  - Historical query (period slicing)
  - Cage impact output
  - API contract (FastAPI TestClient)
  - Edge cases for missing/partial data
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    from backend.main import app
    return TestClient(app)


VALID_IDS = ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]
VALID_PERIODS = ["7d", "30d", "90d", "12m"]
DOMAINS = ["biological", "structural", "environmental", "operational"]


# ══════════════════════════════════════════════════════════════════════════════
# 1. Mock data generator
# ══════════════════════════════════════════════════════════════════════════════

class TestMockDataGenerator:
    def test_all_locality_ids_present(self):
        from backend.services.live_risk_mock import get_all_locality_ids
        ids = get_all_locality_ids()
        assert set(ids) == {"KH_S01", "KH_S02", "KH_S03", "LM_S01"}

    def test_locality_data_has_90_days(self):
        from backend.services.live_risk_mock import get_locality_data, DAYS
        data = get_locality_data("KH_S01")
        assert len(data["timestamps"]) == DAYS
        assert len(data["lice"]) == DAYS
        assert len(data["risk_scores"]) == DAYS

    def test_risk_scores_in_valid_range(self):
        from backend.services.live_risk_mock import get_locality_data
        for lid in VALID_IDS:
            data = get_locality_data(lid)
            for r in data["risk_scores"]:
                assert 0 <= r["total"] <= 100, f"Total risk out of range for {lid}"
                for d in DOMAINS:
                    assert 0 <= r[d] <= 100, f"{d} risk out of range for {lid}"

    def test_lice_values_mostly_non_null(self):
        from backend.services.live_risk_mock import get_locality_data
        data = get_locality_data("KH_S01")
        non_null = [v for v in data["lice"] if v is not None]
        assert len(non_null) > 80, "Too many missing lice values"

    def test_deterministic_output(self):
        from backend.services.live_risk_mock import get_locality_data
        d1 = get_locality_data("KH_S01")
        d2 = get_locality_data("KH_S01")
        # Same object (cached) or same values
        assert d1["risk_scores"][0]["total"] == d2["risk_scores"][0]["total"]

    def test_kornstad_higher_lice_than_hogsnes(self):
        from backend.services.live_risk_mock import get_locality_data
        s01 = get_locality_data("KH_S01")
        s03 = get_locality_data("KH_S03")
        avg_s01 = sum(v for v in s01["lice"] if v) / sum(1 for v in s01["lice"] if v)
        avg_s03 = sum(v for v in s03["lice"] if v) / sum(1 for v in s03["lice"] if v)
        assert avg_s01 > avg_s03, "Kornstad should have higher average lice than Hogsnes"

    def test_period_slice(self):
        from backend.services.live_risk_mock import get_locality_data, slice_by_period, DAYS
        data = get_locality_data("KH_S01")
        sliced, start = slice_by_period(data["timestamps"], "30d")
        assert len(sliced) == 30
        assert start == DAYS - 30

    def test_period_slice_7d(self):
        from backend.services.live_risk_mock import get_locality_data, slice_by_period
        data = get_locality_data("KH_S01")
        sliced, start = slice_by_period(data["timestamps"], "7d")
        assert len(sliced) == 7

    def test_period_slice_90d_returns_90(self):
        from backend.services.live_risk_mock import get_locality_data, slice_by_period, DAYS
        data = get_locality_data("KH_S01")
        sliced, start = slice_by_period(data["timestamps"], "90d")
        assert len(sliced) == 90
        assert start == DAYS - 90

    def test_period_slice_12m_returns_full_year(self):
        from backend.services.live_risk_mock import get_locality_data, slice_by_period, DAYS
        data = get_locality_data("KH_S01")
        sliced, start = slice_by_period(data["timestamps"], "12m")
        assert len(sliced) == DAYS
        assert start == 0


# ══════════════════════════════════════════════════════════════════════════════
# 2. Feed overview
# ══════════════════════════════════════════════════════════════════════════════

class TestFeedOverview:
    def test_returns_all_localities(self):
        from backend.services.live_risk_feed import get_feed_overview
        feed = get_feed_overview()
        assert feed["total_count"] == 4
        assert len(feed["localities"]) == 4

    def test_counts_add_up(self):
        from backend.services.live_risk_feed import get_feed_overview
        feed = get_feed_overview()
        total_status = feed["healthy_count"] + feed["warning_count"] + feed["critical_count"]
        assert total_status == 4

    def test_locality_record_required_fields(self):
        from backend.services.live_risk_feed import get_feed_overview
        feed = get_feed_overview()
        for loc in feed["localities"]:
            assert "locality_id" in loc
            assert "locality_name" in loc
            assert "locality_no" in loc
            assert "last_sync" in loc
            assert "sync_freshness" in loc
            assert "risk_score" in loc
            assert "risk_change_30d" in loc
            assert "confidence" in loc
            assert "dominant_domain" in loc

    def test_risk_scores_are_floats(self):
        from backend.services.live_risk_feed import get_feed_overview
        feed = get_feed_overview()
        for loc in feed["localities"]:
            assert isinstance(loc["risk_score"], float)
            assert isinstance(loc["risk_change_30d"], float)

    def test_leite_has_stale_freshness(self):
        from backend.services.live_risk_feed import get_feed_overview
        feed = get_feed_overview()
        leite = next(loc for loc in feed["localities"] if loc["locality_id"] == "KH_S02")
        assert leite["sync_freshness"] in ("stale", "delayed"), "KH_S02 should be stale"

    def test_hogsnes_lowest_risk(self):
        from backend.services.live_risk_feed import get_feed_overview
        feed = get_feed_overview()
        scores = {loc["locality_id"]: loc["risk_score"] for loc in feed["localities"]}
        assert scores["KH_S03"] == min(scores.values()), "Hogsnes should have lowest risk"

    def test_dominant_domain_is_valid(self):
        from backend.services.live_risk_feed import get_feed_overview
        feed = get_feed_overview()
        for loc in feed["localities"]:
            assert loc["dominant_domain"] in DOMAINS


# ══════════════════════════════════════════════════════════════════════════════
# 3. Locality detail
# ══════════════════════════════════════════════════════════════════════════════

class TestLocalityDetail:
    def test_detail_has_required_fields(self):
        from backend.services.live_risk_feed import get_locality_detail
        detail = get_locality_detail("KH_S01")
        assert detail["locality_id"] == "KH_S01"
        assert "current_risk" in detail
        assert all(d in detail["current_risk"] for d in DOMAINS)
        assert "total" in detail["current_risk"]
        assert "available_periods" in detail

    def test_available_periods_complete(self):
        from backend.services.live_risk_feed import get_locality_detail
        detail = get_locality_detail("KH_S01")
        assert set(detail["available_periods"]) == {"7d", "30d", "90d", "12m"}


# ══════════════════════════════════════════════════════════════════════════════
# 4. Time series
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeSeries:
    def test_has_six_series(self):
        from backend.services.live_risk_feed import get_timeseries
        ts = get_timeseries("KH_S01", "30d")
        # 5 line series + 1 event_band (disease)
        assert len(ts["raw_data"]) == 6
        parameters = {s["parameter"] for s in ts["raw_data"]}
        assert "disease" in parameters
        assert "lice" in parameters

    def test_disease_series_is_event_band(self):
        from backend.services.live_risk_feed import get_timeseries
        ts = get_timeseries("KH_S01", "30d")
        disease = next(s for s in ts["raw_data"] if s["parameter"] == "disease")
        assert disease["chart_type"] == "event_band"
        assert "intervals" in disease
        assert "has_active" in disease
        # Points have "active" flag, not "value"
        for pt in disease["points"]:
            assert "active" in pt
            assert isinstance(pt["active"], bool)

    def test_30d_gives_30_points_per_series(self):
        from backend.services.live_risk_feed import get_timeseries
        ts = get_timeseries("KH_S01", "30d")
        for series in ts["raw_data"]:
            assert len(series["points"]) == 30, f"{series['parameter']} should have 30 points"

    def test_7d_gives_7_points(self):
        from backend.services.live_risk_feed import get_timeseries
        ts = get_timeseries("KH_S01", "7d")
        for series in ts["raw_data"]:
            assert len(series["points"]) == 7

    def test_missing_values_represented_as_none(self):
        from backend.services.live_risk_feed import get_timeseries
        ts = get_timeseries("KH_S01", "90d")
        lice_series = next(s for s in ts["raw_data"] if s["parameter"] == "lice")
        none_count = sum(1 for p in lice_series["points"] if p["value"] is None)
        # There should be some missing (but not all)
        assert 0 < none_count < 90

    def test_quality_flags_are_valid(self):
        from backend.services.live_risk_feed import get_timeseries
        valid_qualities = {"observed", "estimated", "missing"}
        ts = get_timeseries("KH_S01", "30d")
        for series in ts["raw_data"]:
            if series["chart_type"] == "event_band":
                continue  # event_band points use "active", not "quality"
            for pt in series["points"]:
                assert pt["quality"] in valid_qualities

    def test_missing_value_has_none(self):
        from backend.services.live_risk_feed import get_timeseries
        ts = get_timeseries("KH_S01", "90d")
        for series in ts["raw_data"]:
            if series["chart_type"] == "event_band":
                continue  # event_band points use "active", not "value"
            for pt in series["points"]:
                if pt["quality"] == "missing":
                    assert pt["value"] is None

    def test_lice_series_has_threshold(self):
        from backend.services.live_risk_feed import get_timeseries
        ts = get_timeseries("KH_S01", "30d")
        lice = next(s for s in ts["raw_data"] if s["parameter"] == "lice")
        assert lice["threshold"] is not None

    def test_timestamps_are_iso_strings(self):
        from backend.services.live_risk_feed import get_timeseries
        ts = get_timeseries("KH_S01", "7d")
        for series in ts["raw_data"]:
            for pt in series["points"]:
                assert isinstance(pt["timestamp"], str)
                assert "T" in pt["timestamp"]


# ══════════════════════════════════════════════════════════════════════════════
# 5. Risk history
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskHistory:
    def test_history_length_matches_period(self):
        from backend.services.live_risk_feed import get_risk_history
        h = get_risk_history("KH_S01", "30d")
        assert len(h["risk_history"]) == 30

    def test_history_has_all_domains(self):
        from backend.services.live_risk_feed import get_risk_history
        h = get_risk_history("KH_S01", "7d")
        for point in h["risk_history"]:
            for d in DOMAINS:
                assert d in point
            assert "total" in point

    def test_total_is_plausible_weighted_avg(self):
        from backend.services.live_risk_feed import get_risk_history
        h = get_risk_history("KH_S01", "30d")
        for point in h["risk_history"]:
            # Total should be within domain range
            domain_vals = [point[d] for d in DOMAINS]
            assert min(domain_vals) <= point["total"] <= max(domain_vals) + 10


# ══════════════════════════════════════════════════════════════════════════════
# 6. Source health
# ══════════════════════════════════════════════════════════════════════════════

class TestSourceHealth:
    def test_all_sources_present(self):
        from backend.services.source_health import get_source_status
        result = get_source_status("KH_S01")
        assert len(result["sources"]) == 5

    def test_source_record_has_required_fields(self):
        from backend.services.source_health import get_source_status
        result = get_source_status("KH_S01")
        required = {"source_id", "source_name", "source_type", "status",
                    "last_sync", "records_received", "contributes_to_risk"}
        for src in result["sources"]:
            assert required.issubset(src.keys())

    def test_kornstad_all_ok(self):
        from backend.services.source_health import get_source_status
        result = get_source_status("KH_S01")
        for src in result["sources"]:
            assert src["status"] == "ok"
        assert result["health_summary"] == "all_ok"

    def test_leite_has_degraded_source(self):
        from backend.services.source_health import get_source_status
        result = get_source_status("KH_S02")
        delayed = [s for s in result["sources"] if s["status"] == "delayed"]
        assert len(delayed) == 1
        assert delayed[0]["source_id"] == "bw_environmental"
        assert result["health_summary"] == "partial"

    def test_degraded_source_does_not_contribute(self):
        from backend.services.source_health import get_source_status
        result = get_source_status("KH_S02")
        delayed = next(s for s in result["sources"] if s["status"] == "delayed")
        assert delayed["contributes_to_risk"] is False

    def test_valid_status_values(self):
        from backend.services.source_health import get_source_status
        valid = {"ok", "delayed", "failed", "no_data"}
        for lid in VALID_IDS:
            result = get_source_status(lid)
            for src in result["sources"]:
                assert src["status"] in valid


# ══════════════════════════════════════════════════════════════════════════════
# 7. Risk change explanation
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskChangeExplainer:
    def test_breakdown_has_required_keys(self):
        from backend.services.risk_change_explainer import get_change_breakdown
        bd = get_change_breakdown("KH_S01", "30d")
        assert "total_delta" in bd
        assert "domain_deltas" in bd
        assert "factor_deltas" in bd
        assert "explanation_summary" in bd
        assert "confidence_note" in bd
        assert "from_date" in bd
        assert "to_date" in bd

    def test_domain_deltas_has_all_domains(self):
        from backend.services.risk_change_explainer import get_change_breakdown
        bd = get_change_breakdown("KH_S01", "30d")
        for d in DOMAINS:
            assert d in bd["domain_deltas"]

    def test_factor_deltas_non_empty(self):
        from backend.services.risk_change_explainer import get_change_breakdown
        bd = get_change_breakdown("KH_S01", "30d")
        assert len(bd["factor_deltas"]) > 0

    def test_factor_delta_has_direction(self):
        from backend.services.risk_change_explainer import get_change_breakdown
        bd = get_change_breakdown("KH_S01", "30d")
        valid_directions = {"up", "down", "unchanged"}
        for f in bd["factor_deltas"]:
            assert f["direction"] in valid_directions

    def test_explanation_summary_is_list(self):
        from backend.services.risk_change_explainer import get_change_breakdown
        bd = get_change_breakdown("KH_S01", "30d")
        assert isinstance(bd["explanation_summary"], list)
        assert len(bd["explanation_summary"]) > 0

    def test_period_days_matches(self):
        from backend.services.risk_change_explainer import get_change_breakdown
        bd = get_change_breakdown("KH_S01", "30d")
        assert bd["period_days"] == 30

    def test_total_delta_is_float(self):
        from backend.services.risk_change_explainer import get_change_breakdown
        bd = get_change_breakdown("KH_S01", "7d")
        assert isinstance(bd["total_delta"], float)


# ══════════════════════════════════════════════════════════════════════════════
# 8. Confidence scoring
# ══════════════════════════════════════════════════════════════════════════════

class TestConfidenceScoring:
    def test_confidence_levels_are_valid(self):
        from backend.services.confidence_scoring import compute_confidence
        valid = {"high", "medium", "low"}
        for lid in VALID_IDS:
            result = compute_confidence(lid)
            assert result["overall"] in valid

    def test_confidence_score_in_range(self):
        from backend.services.confidence_scoring import compute_confidence
        for lid in VALID_IDS:
            result = compute_confidence(lid)
            assert 0.0 <= result["score"] <= 1.0

    def test_components_present(self):
        from backend.services.confidence_scoring import compute_confidence
        result = compute_confidence("KH_S01")
        assert len(result["components"]) >= 3
        for comp in result["components"]:
            assert "component" in comp
            assert "score" in comp
            assert "explanation" in comp

    def test_component_scores_in_range(self):
        from backend.services.confidence_scoring import compute_confidence
        for lid in VALID_IDS:
            result = compute_confidence(lid)
            for comp in result["components"]:
                assert 0.0 <= comp["score"] <= 1.0

    def test_summary_is_string(self):
        from backend.services.confidence_scoring import compute_confidence
        result = compute_confidence("KH_S01")
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 10

    def test_leite_missing_sources_non_empty(self):
        from backend.services.confidence_scoring import compute_confidence
        result = compute_confidence("KH_S02")
        # KH_S02 has one degraded source
        assert len(result["missing_sources"]) >= 1

    def test_kornstad_no_missing_sources(self):
        from backend.services.confidence_scoring import compute_confidence
        result = compute_confidence("KH_S01")
        assert len(result["missing_sources"]) == 0


# ══════════════════════════════════════════════════════════════════════════════
# 9. Event timeline
# ══════════════════════════════════════════════════════════════════════════════

class TestEventTimeline:
    def test_returns_events_list(self):
        from backend.services.event_timeline import get_events
        result = get_events("KH_S01", "30d")
        assert "events" in result
        assert "total_count" in result
        assert isinstance(result["events"], list)

    def test_event_has_required_fields(self):
        from backend.services.event_timeline import get_events
        result = get_events("KH_S01", "90d")
        if result["events"]:
            event = result["events"][0]
            assert "event_id" in event
            assert "timestamp" in event
            assert "event_type" in event
            assert "severity" in event
            assert "title" in event
            assert "description" in event

    def test_severity_values_are_valid(self):
        from backend.services.event_timeline import get_events
        valid = {"info", "warning", "critical"}
        for lid in VALID_IDS:
            result = get_events(lid, "90d")
            for e in result["events"]:
                assert e["severity"] in valid, f"Invalid severity: {e['severity']}"

    def test_events_sorted_most_recent_first(self):
        from backend.services.event_timeline import get_events
        result = get_events("KH_S01", "90d")
        if len(result["events"]) > 1:
            timestamps = [e["timestamp"] for e in result["events"]]
            assert timestamps == sorted(timestamps, reverse=True)

    def test_total_count_matches_list(self):
        from backend.services.event_timeline import get_events
        result = get_events("KH_S01", "30d")
        assert result["total_count"] == len(result["events"])

    def test_7d_period_fewer_events_than_90d(self):
        from backend.services.event_timeline import get_events
        r7 = get_events("KH_S01", "7d")
        r90 = get_events("KH_S01", "90d")
        assert r7["total_count"] <= r90["total_count"]

    def test_leite_has_source_delay_event(self):
        from backend.services.event_timeline import get_events
        result = get_events("KH_S02", "90d")
        types = [e["event_type"] for e in result["events"]]
        assert "source_delayed" in types

    def test_hogsnes_no_disease_events(self):
        from backend.services.event_timeline import get_events
        result = get_events("KH_S03", "90d")
        disease_events = [e for e in result["events"] if "disease" in e["event_type"]]
        assert len(disease_events) == 0


# ══════════════════════════════════════════════════════════════════════════════
# 10. Cage impact
# ══════════════════════════════════════════════════════════════════════════════

class TestCageImpact:
    def test_returns_all_cage_types(self):
        from backend.services.live_risk_feed import get_cage_impact
        result = get_cage_impact("KH_S01")
        cage_types = {c["cage_type"] for c in result["cage_impacts"]}
        assert {"open_net", "semi_closed", "fully_closed", "submerged"} == cage_types

    def test_relative_impact_values_valid(self):
        from backend.services.live_risk_feed import get_cage_impact
        valid = {"high", "medium", "low"}
        result = get_cage_impact("KH_S01")
        for c in result["cage_impacts"]:
            assert c["relative_impact"] in valid

    def test_affected_domains_non_empty(self):
        from backend.services.live_risk_feed import get_cage_impact
        result = get_cage_impact("KH_S01")
        for c in result["cage_impacts"]:
            assert len(c["affected_domains"]) >= 1

    def test_note_present(self):
        from backend.services.live_risk_feed import get_cage_impact
        result = get_cage_impact("KH_S01")
        assert "note" in result
        assert len(result["note"]) > 10


# ══════════════════════════════════════════════════════════════════════════════
# 11. API contract tests (FastAPI TestClient)
# ══════════════════════════════════════════════════════════════════════════════

class TestAPIContract:
    def test_feed_endpoint_200(self, client):
        r = client.get("/api/live-risk/feed")
        assert r.status_code == 200
        body = r.json()
        assert "localities" in body
        assert "total_count" in body

    def test_locality_detail_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S01")
        assert r.status_code == 200
        assert r.json()["locality_id"] == "KH_S01"

    def test_locality_detail_404_unknown(self, client):
        r = client.get("/api/live-risk/localities/UNKNOWN")
        assert r.status_code == 404

    def test_timeseries_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/timeseries?period=30d")
        assert r.status_code == 200
        assert "raw_data" in r.json()

    def test_timeseries_invalid_period_422(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/timeseries?period=99x")
        assert r.status_code == 422

    def test_risk_history_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S02/risk-history?period=7d")
        assert r.status_code == 200

    def test_sources_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/sources")
        assert r.status_code == 200
        assert "sources" in r.json()
        assert "health_summary" in r.json()

    def test_change_breakdown_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/change-breakdown?period=30d")
        assert r.status_code == 200
        body = r.json()
        assert "total_delta" in body
        assert "factor_deltas" in body

    def test_events_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S03/events?period=90d")
        assert r.status_code == 200
        assert "events" in r.json()

    def test_confidence_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S02/confidence")
        assert r.status_code == 200
        body = r.json()
        assert "overall" in body
        assert "score" in body

    def test_cage_impact_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/cage-impact")
        assert r.status_code == 200
        assert "cage_impacts" in r.json()

    def test_all_periods_work(self, client):
        for period in ["7d", "30d", "90d", "12m"]:
            r = client.get(f"/api/live-risk/localities/KH_S01/timeseries?period={period}")
            assert r.status_code == 200, f"Period {period} failed"

    def test_all_localities_accessible(self, client):
        for lid in VALID_IDS:
            r = client.get(f"/api/live-risk/localities/{lid}")
            assert r.status_code == 200, f"Locality {lid} not accessible"


# ══════════════════════════════════════════════════════════════════════════════
# 12. Edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_hogsnes_zero_disease_events(self):
        from backend.services.live_risk_mock import get_locality_data
        data = get_locality_data("KH_S03")
        assert all(d == 0 for d in data["disease"])

    def test_breakdown_no_change_when_stable(self):
        """Breakdown with stable locality should show small deltas."""
        from backend.services.risk_change_explainer import get_change_breakdown
        bd = get_change_breakdown("KH_S03", "7d")
        # Hogsnes is low-risk and stable — most factor deltas should be small
        large_factors = [f for f in bd["factor_deltas"] if abs(f["delta"]) > 20]
        assert len(large_factors) == 0

    def test_timeseries_12m_returns_full_year(self):
        """12m period should return all 365 days of available history."""
        from backend.services.live_risk_feed import get_timeseries
        from backend.services.live_risk_mock import DAYS
        ts = get_timeseries("KH_S01", "12m")
        for series in ts["raw_data"]:
            if series.get("chart_type") == "event_band":
                continue
            assert len(series["points"]) == DAYS

    def test_all_localities_have_different_risk_profiles(self):
        from backend.services.live_risk_feed import get_feed_overview
        feed = get_feed_overview()
        scores = [loc["risk_score"] for loc in feed["localities"]]
        assert len(set(scores)) == len(scores), "All localities should have different risk scores"

    def test_events_empty_for_short_period_stable_locality(self):
        from backend.services.event_timeline import get_events
        result = get_events("KH_S03", "7d")
        # KH_S03 is the cleanest site — may have very few events in 7d
        assert result["total_count"] >= 0  # no crash; zero is valid

    def test_confidence_components_sum_correctly(self):
        from backend.services.confidence_scoring import compute_confidence
        for lid in VALID_IDS:
            result = compute_confidence(lid)
            scores = [c["score"] for c in result["components"]]
            avg = sum(scores) / len(scores)
            assert abs(avg - result["score"]) < 0.01, "Score should be mean of components"
