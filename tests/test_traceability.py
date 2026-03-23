"""
Tests for the TraceabilityBlock in FeasibilityResponse.

Tests:
- build_traceability_block returns a TraceabilityBlock with correct fields
- source is "static_model" when c5ai_enriched is False
- source is "c5ai_plus" when c5ai_enriched is True
- site_ids populated from loss_analysis per_site
- domains_used populated from sim.domain_loss_breakdown
- risk_type_count matches risk_types_used length
- applied_mitigations matches input
- analysis_id is non-empty
- generated_at is non-empty ISO string
- TraceabilityBlock is present in FeasibilityResponse from /api/feasibility/example + run
- traceability site_ids match loss_analysis site_ids
- fallback is graceful when traceability is missing (None)
"""
import pytest
from unittest.mock import MagicMock
import numpy as np


def _make_sim(c5ai_enriched=False, c5ai_scale=None, mitigated=False):
    sim = MagicMock()
    sim.c5ai_enriched = c5ai_enriched
    sim.c5ai_scale_factor = c5ai_scale
    sim.mitigated = mitigated
    sim.mitigation_summary = None
    sim.site_loss_distribution = {
        "Site A": np.random.default_rng(1).random((100, 5)) * 1_000_000,
        "Site B": np.random.default_rng(2).random((100, 5)) * 500_000,
    }

    dld = MagicMock()
    bio_arr = np.ones((100, 5)) * 5_000_000
    str_arr = np.ones((100, 5)) * 2_000_000
    env_arr = np.ones((100, 5)) * 1_500_000
    ops_arr = np.ones((100, 5)) * 800_000
    dld.domain_totals.return_value = {
        "biological": bio_arr,
        "structural": str_arr,
        "environmental": env_arr,
        "operational": ops_arr,
    }
    dld.all_subtypes.return_value = {
        "hab": bio_arr * 0.4,
        "lice": bio_arr * 0.3,
        "jellyfish": bio_arr * 0.2,
        "pathogen": bio_arr * 0.1,
        "mooring_failure": str_arr * 0.5,
        "net_integrity": str_arr * 0.5,
        "oxygen_stress": env_arr * 0.6,
        "temperature_extreme": env_arr * 0.4,
        "human_error": ops_arr * 0.5,
        "equipment_failure": ops_arr * 0.5,
    }
    sim.domain_loss_breakdown = dld
    return sim


def _make_op():
    op = MagicMock()
    site_a = MagicMock()
    site_a.name = "Site A"
    site_b = MagicMock()
    site_b.name = "Site B"
    op.sites = [site_a, site_b]
    return op


def _make_la_block():
    """Mock LossAnalysisBlock with per_site."""
    block = MagicMock()
    s1 = MagicMock()
    s1.site_id = "Site A"
    s1.site_name = "Site A"
    s1.expected_annual_loss_nok = 4_800_000.0
    s1.scr_contribution_nok = 12_000_000.0
    s1.dominant_domain = "biological"
    s1.domain_breakdown = {"biological": 3_000_000, "structural": 1_000_000, "environmental": 500_000, "operational": 300_000}

    s2 = MagicMock()
    s2.site_id = "Site B"
    s2.site_name = "Site B"
    s2.expected_annual_loss_nok = 2_400_000.0
    s2.scr_contribution_nok = 6_000_000.0
    s2.dominant_domain = "structural"
    s2.domain_breakdown = {"biological": 1_200_000, "structural": 700_000, "environmental": 300_000, "operational": 200_000}

    block.per_site = [s1, s2]
    return block


class TestBuildTraceabilityBlock:
    def test_static_model_source(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim(c5ai_enriched=False)
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert t.source == "static_model"
        assert t.data_mode == "static_model"
        assert t.c5ai_enriched is False
        assert t.c5ai_scale_factor is None

    def test_c5ai_enriched_source(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim(c5ai_enriched=True, c5ai_scale=1.23)
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert t.source == "c5ai_plus"
        assert t.data_mode == "c5ai_forecast"
        assert t.c5ai_enriched is True
        assert abs(t.c5ai_scale_factor - 1.23) < 1e-6

    def test_c5ai_mitigated_source(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim(c5ai_enriched=True, c5ai_scale=0.95, mitigated=True)
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert t.source == "c5ai_plus_mitigated"
        assert t.data_mode == "c5ai_forecast_mitigated"
        assert t.mitigated_forecast_used is True

    def test_site_ids_from_loss_analysis(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert "Site A" in t.site_ids
        assert "Site B" in t.site_ids
        assert t.site_count == 2

    def test_domains_used_populated(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert "biological" in t.domains_used
        assert "structural" in t.domains_used
        assert t.domain_count >= 2

    def test_risk_types_used_populated(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert "hab" in t.risk_types_used
        assert "lice" in t.risk_types_used
        assert t.risk_type_count == len(t.risk_types_used)

    def test_applied_mitigations(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), ["hab_monitoring", "lice_treatment"], _make_la_block())
        assert "hab_monitoring" in t.applied_mitigations
        assert "lice_treatment" in t.applied_mitigations

    def test_analysis_id_non_empty(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert len(t.analysis_id) > 0

    def test_generated_at_iso_string(self):
        from backend.services.traceability import build_traceability_block
        from datetime import datetime
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert len(t.generated_at) > 0
        # Should parse as ISO datetime
        datetime.fromisoformat(t.generated_at.replace('Z', '+00:00'))

    def test_site_trace_has_eal_and_scr(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), [], _make_la_block())
        assert len(t.site_trace) == 2
        for s in t.site_trace:
            assert s.eal_nok > 0
            assert s.scr_contribution_nok > 0
            assert len(s.top_domains) >= 1

    def test_site_trace_matches_loss_analysis_site_ids(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        la = _make_la_block()
        t = build_traceability_block(sim, _make_op(), [], la)
        trace_ids = {s.site_id for s in t.site_trace}
        la_ids = {s.site_id for s in la.per_site}
        assert trace_ids == la_ids

    def test_graceful_with_no_loss_analysis(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), [], None)
        assert t.site_count >= 0
        assert t.analysis_id != ""

    def test_mapping_note_non_empty(self):
        from backend.services.traceability import build_traceability_block
        sim = _make_sim()
        t = build_traceability_block(sim, _make_op(), [], None)
        assert len(t.mapping_note) > 50


class TestTraceabilitySchema:
    def test_traceability_block_validates(self):
        from backend.schemas import TraceabilityBlock, TraceabilitySiteTrace
        block = TraceabilityBlock(
            analysis_id="abc123",
            generated_at="2026-03-22T10:00:00+00:00",
            source="static_model",
            site_count=3,
            domain_count=4,
            risk_type_count=10,
            site_ids=["S1", "S2", "S3"],
            domains_used=["biological", "structural"],
            risk_types_used=["hab", "lice", "mooring_failure"],
            data_mode="static_model",
            mapping_note="Test note",
        )
        assert block.site_count == 3

    def test_feasibility_response_backward_compat_without_traceability(self):
        from backend.schemas import FeasibilityResponse, ScenarioBlock, KPISummary, ReportBlock, MetadataBlock
        kpi = KPISummary(expected_annual_loss=1e6, p95_loss=2e6, p99_loss=3e6, scr=5e6,
                         recommended_strategy="PCC", verdict="POTENTIALLY_SUITABLE",
                         composite_score=55.0, confidence_level="medium")
        bl = ScenarioBlock(summary=kpi)
        r = FeasibilityResponse(
            baseline=bl,
            report=ReportBlock(available=False),
            metadata=MetadataBlock(domain_correlation_active=True, mitigation_active=False, n_simulations=1000),
        )
        assert r.traceability is None

    def test_feasibility_response_accepts_traceability(self):
        from backend.schemas import FeasibilityResponse, ScenarioBlock, KPISummary, ReportBlock, MetadataBlock, TraceabilityBlock
        kpi = KPISummary(expected_annual_loss=1e6, p95_loss=2e6, p99_loss=3e6, scr=5e6,
                         recommended_strategy="PCC", verdict="POTENTIALLY_SUITABLE",
                         composite_score=55.0, confidence_level="medium")
        bl = ScenarioBlock(summary=kpi)
        tb = TraceabilityBlock(analysis_id="xyz", generated_at="2026-03-22T10:00:00", source="static_model",
                               site_count=2, domain_count=4, risk_type_count=8,
                               site_ids=["A", "B"], domains_used=["biological"], risk_types_used=["hab"],
                               data_mode="static_model", mapping_note="note")
        r = FeasibilityResponse(
            baseline=bl,
            report=ReportBlock(available=False),
            metadata=MetadataBlock(domain_correlation_active=True, mitigation_active=False, n_simulations=1000),
            traceability=tb,
        )
        assert r.traceability.analysis_id == "xyz"


class TestTraceabilityAPIEndToEnd:
    def test_feasibility_run_has_traceability_field(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        ex_resp = client.post("/api/feasibility/example")
        assert ex_resp.status_code == 200
        example_req = ex_resp.json()
        example_req["model_settings"]["n_simulations"] = 500
        example_req["model_settings"]["generate_pdf"] = False
        run_resp = client.post("/api/feasibility/run", json=example_req)
        assert run_resp.status_code == 200
        data = run_resp.json()
        assert "traceability" in data

    def test_traceability_has_required_fields(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        ex_resp = client.post("/api/feasibility/example")
        example_req = ex_resp.json()
        example_req["model_settings"]["n_simulations"] = 500
        example_req["model_settings"]["generate_pdf"] = False
        run_resp = client.post("/api/feasibility/run", json=example_req)
        t = run_resp.json().get("traceability") or {}
        assert "analysis_id" in t
        assert "generated_at" in t
        assert "source" in t
        assert "site_count" in t
        assert "domains_used" in t

    def test_traceability_site_ids_consistent_with_loss_analysis(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        ex_resp = client.post("/api/feasibility/example")
        example_req = ex_resp.json()
        example_req["model_settings"]["n_simulations"] = 500
        example_req["model_settings"]["generate_pdf"] = False
        run_resp = client.post("/api/feasibility/run", json=example_req)
        data = run_resp.json()
        t = data.get("traceability") or {}
        la = data.get("loss_analysis") or {}
        if la.get("per_site") and t.get("site_ids"):
            la_ids = {s["site_id"] for s in la["per_site"]}
            t_ids = set(t["site_ids"])
            assert la_ids == t_ids
