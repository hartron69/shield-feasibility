"""
tests/test_locality_risk_profile.py

Tests for Sprint 1 — Locality Risk Engine.

Covers:
  A. Data model construction and serialisation
  B. Builder with standard locality (no cages)
  C. Builder with cage portfolio
  D. Builder without cage portfolio (clean fallback)
  E. Confidence / defaults surfaced explicitly
  F. Multi-locality build
  G. API contract (single + batch)
  H. KH portfolio known-value tests (Kornstad / Leite / Hogsnes)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from models.locality_risk_profile import (
    DOMAINS,
    LIVE_RISK_SCALE_FACTORS,
    DomainRiskScores,
    DomainRiskWeights,
    LocalityRiskProfile,
    RiskSourceSummary,
)
from backend.services.locality_risk_builder import (
    build_locality_risk_profile,
    build_locality_risk_profiles,
    _compute_domain_weights,
    _top_risk_drivers,
    _concentration_flags,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

KH_IDS = ["KH_S01", "KH_S02", "KH_S03"]


def _make_scores(bio=40.0, struct=20.0, env=15.0, ops=10.0) -> DomainRiskScores:
    return DomainRiskScores(biological=bio, structural=struct, environmental=env, operational=ops)


def _minimal_profile() -> LocalityRiskProfile:
    return LocalityRiskProfile(
        locality_id="KH_S01",
        locality_name="Kornstad",
        company_name="Kornstad Havbruk AS",
        region="Møre og Romsdal",
        drift_type="sjø",
        biomass_tonnes=3000.0,
        biomass_value_nok=195_000_000.0,
        exposure_factor=1.15,
        cage_count=0,
        cage_weighting_mode="none",
        total_risk_score=28.5,
        total_risk_score_source="live_risk",
        domain_scores=_make_scores(),
        domain_weights=DomainRiskWeights(biological=0.5, structural=0.2, environmental=0.2, operational=0.1),
        domain_multipliers={d: 1.0 for d in DOMAINS},
        scale_factors=dict(LIVE_RISK_SCALE_FACTORS),
        concentration_flags=[],
        top_risk_drivers=["biological", "structural", "environmental", "operational"],
        confidence_level="high",
        confidence_notes=[],
        source_summary=RiskSourceSummary(
            live_risk_available=True,
            cage_portfolio_available=False,
            advanced_weighting_available=False,
            bw_live=True,
            sources_used=["Live Risk", "BarentsWatch"],
        ),
        used_defaults=[],
        metadata={},
    )


# ── A. Data model ───────────────────────────────────────────────────────────────

class TestDomainRiskScores:
    def test_to_dict_has_all_domains(self):
        s = _make_scores()
        d = s.to_dict()
        assert set(d.keys()) == set(DOMAINS)

    def test_from_dict_roundtrip(self):
        s = _make_scores(bio=55.1, struct=12.3, env=8.9, ops=6.0)
        s2 = DomainRiskScores.from_dict(s.to_dict())
        assert s2.biological == pytest.approx(55.1)
        assert s2.structural == pytest.approx(12.3)
        assert s2.environmental == pytest.approx(8.9)
        assert s2.operational == pytest.approx(6.0)


class TestDomainRiskWeights:
    def test_from_dict_roundtrip(self):
        w = DomainRiskWeights(biological=0.5, structural=0.25, environmental=0.15, operational=0.10)
        w2 = DomainRiskWeights.from_dict(w.to_dict())
        assert w2.biological == pytest.approx(0.5)
        assert w2.operational == pytest.approx(0.10)


class TestRiskSourceSummary:
    def test_roundtrip(self):
        src = RiskSourceSummary(
            live_risk_available=True,
            cage_portfolio_available=True,
            advanced_weighting_available=True,
            bw_live=False,
            sources_used=["Live Risk", "Cage Portfolio"],
        )
        src2 = RiskSourceSummary.from_dict(src.to_dict())
        assert src2.cage_portfolio_available is True
        assert src2.bw_live is False
        assert "Cage Portfolio" in src2.sources_used


class TestLocalityRiskProfileSerialisation:
    def test_to_dict_contains_all_top_level_keys(self):
        p = _minimal_profile()
        d = p.to_dict()
        expected = {
            "locality_id", "locality_name", "company_name", "region", "drift_type",
            "biomass_tonnes", "biomass_value_nok", "exposure_factor",
            "cage_count", "cage_weighting_mode",
            "domain_scores", "domain_weights", "domain_multipliers", "scale_factors",
            "concentration_flags", "top_risk_drivers",
            "confidence_level", "confidence_notes",
            "source_summary", "used_defaults", "metadata",
        }
        assert expected.issubset(d.keys())

    def test_from_dict_roundtrip(self):
        p = _minimal_profile()
        p2 = LocalityRiskProfile.from_dict(p.to_dict())
        assert p2.locality_id == "KH_S01"
        assert p2.biomass_tonnes == pytest.approx(3000.0)
        assert p2.domain_scores.biological == pytest.approx(40.0)
        assert p2.source_summary.live_risk_available is True

    def test_drift_type_is_sjo(self):
        p = _minimal_profile()
        assert p.drift_type == "sjø"

    def test_total_risk_score_in_to_dict(self):
        p = _minimal_profile()
        assert "total_risk_score" in p.to_dict()

    def test_from_dict_preserves_total_risk_score(self):
        p = _minimal_profile()
        p2 = LocalityRiskProfile.from_dict(p.to_dict())
        assert p2.total_risk_score == pytest.approx(28.5)
        assert p2.total_risk_score_source == "live_risk"


# ── B. Helper functions ─────────────────────────────────────────────────────────

class TestComputeDomainWeights:
    def test_weights_sum_to_one(self):
        scores = {"biological": 50.0, "structural": 20.0, "environmental": 15.0, "operational": 10.0}
        w = _compute_domain_weights(scores)
        assert sum(w.values()) == pytest.approx(1.0, abs=1e-6)

    def test_all_zero_scores_gives_uniform(self):
        scores = {d: 0.0 for d in DOMAINS}
        w = _compute_domain_weights(scores)
        for v in w.values():
            assert v == pytest.approx(0.25, abs=1e-6)

    def test_high_bio_dominates(self):
        scores = {"biological": 100.0, "structural": 0.0, "environmental": 0.0, "operational": 0.0}
        w = _compute_domain_weights(scores)
        assert w["biological"] == pytest.approx(1.0, abs=1e-6)

    def test_scale_factors_are_applied(self):
        # bio=10 (sf=0.35) vs env=10 (sf=0.25) → bio weight > env weight
        scores = {"biological": 10.0, "structural": 0.0, "environmental": 10.0, "operational": 0.0}
        w = _compute_domain_weights(scores)
        assert w["biological"] > w["environmental"]


class TestTopRiskDrivers:
    def test_returns_all_four_domains(self):
        w = {"biological": 0.5, "structural": 0.25, "environmental": 0.15, "operational": 0.10}
        drivers = _top_risk_drivers(w)
        assert set(drivers) == set(DOMAINS)

    def test_sorted_descending(self):
        w = {"biological": 0.5, "structural": 0.25, "environmental": 0.15, "operational": 0.10}
        drivers = _top_risk_drivers(w)
        assert drivers[0] == "biological"
        assert drivers[-1] == "operational"


class TestConcentrationFlags:
    def test_high_bio_dominance_flag(self):
        w = {"biological": 0.55, "structural": 0.20, "environmental": 0.15, "operational": 0.10}
        flags = _concentration_flags(w, exposure_factor=1.0)
        assert "high_biological_dominance" in flags

    def test_high_exposure_flag(self):
        w = {d: 0.25 for d in DOMAINS}
        flags = _concentration_flags(w, exposure_factor=1.15)
        assert "high_exposure" in flags

    def test_no_flags_for_balanced_low_exposure(self):
        w = {d: 0.25 for d in DOMAINS}
        flags = _concentration_flags(w, exposure_factor=0.85)
        assert flags == []


# ── C / D. Builder ──────────────────────────────────────────────────────────────

class TestBuilderStandardLocality:
    @pytest.mark.parametrize("lid", KH_IDS)
    def test_profile_created(self, lid):
        p = build_locality_risk_profile(lid)
        assert isinstance(p, LocalityRiskProfile)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_locality_id_matches(self, lid):
        p = build_locality_risk_profile(lid)
        assert p.locality_id == lid

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_all_domain_scores_present(self, lid):
        p = build_locality_risk_profile(lid)
        d = p.domain_scores.to_dict()
        assert set(d.keys()) == set(DOMAINS)
        for v in d.values():
            assert 0.0 <= v <= 100.0

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_domain_weights_sum_to_one(self, lid):
        p = build_locality_risk_profile(lid)
        total = sum(p.domain_weights.to_dict().values())
        assert total == pytest.approx(1.0, abs=1e-4)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_scale_factors_match_live_risk_model(self, lid):
        p = build_locality_risk_profile(lid)
        assert p.scale_factors["biological"]    == pytest.approx(0.35)
        assert p.scale_factors["structural"]    == pytest.approx(0.25)
        assert p.scale_factors["environmental"] == pytest.approx(0.25)
        assert p.scale_factors["operational"]   == pytest.approx(0.15)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_top_risk_drivers_has_four_entries(self, lid):
        p = build_locality_risk_profile(lid)
        assert len(p.top_risk_drivers) == 4
        assert set(p.top_risk_drivers) == set(DOMAINS)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_confidence_level_is_valid(self, lid):
        p = build_locality_risk_profile(lid)
        assert p.confidence_level in ("high", "medium", "low")

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_drift_type_is_sjo(self, lid):
        p = build_locality_risk_profile(lid)
        assert p.drift_type == "sjø"

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_total_risk_score_source_is_live_risk(self, lid):
        p = build_locality_risk_profile(lid)
        assert p.total_risk_score_source == "live_risk"

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_total_risk_score_in_valid_range(self, lid):
        p = build_locality_risk_profile(lid)
        assert 0.0 <= p.total_risk_score <= 100.0

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_total_risk_score_consistent_with_domain_scores(self, lid):
        p = build_locality_risk_profile(lid)
        expected = (
            p.domain_scores.biological    * 0.35 +
            p.domain_scores.structural    * 0.25 +
            p.domain_scores.environmental * 0.25 +
            p.domain_scores.operational   * 0.15
        )
        assert p.total_risk_score == pytest.approx(expected, abs=0.2)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_biomass_value_derived_from_tonnes(self, lid):
        p = build_locality_risk_profile(lid)
        expected = p.biomass_tonnes * 65_000
        assert p.biomass_value_nok == pytest.approx(expected)


class TestBuilderNoCages:
    def test_weighting_mode_is_none(self):
        p = build_locality_risk_profile("KH_S01")
        assert p.cage_weighting_mode == "none"

    def test_cage_count_is_zero(self):
        p = build_locality_risk_profile("KH_S01")
        assert p.cage_count == 0

    def test_domain_multipliers_are_ones(self):
        p = build_locality_risk_profile("KH_S01")
        for v in p.domain_multipliers.values():
            assert v == pytest.approx(1.0)

    def test_cage_defaults_listed(self):
        p = build_locality_risk_profile("KH_S01")
        defaults_str = " ".join(p.used_defaults)
        assert "cage" in defaults_str.lower() or "domain_multipliers" in defaults_str.lower()

    def test_no_crash_for_all_kh_localities(self):
        for lid in KH_IDS:
            p = build_locality_risk_profile(lid)
            assert p is not None


class TestBuilderWithCages:
    """Tests that cage weighting is included when cages are supplied."""

    def _make_cage(self, cage_type: str = "open_net"):
        from models.cage_technology import CagePenConfig
        return CagePenConfig(
            cage_id=f"cage_{cage_type}",
            cage_type=cage_type,
            biomass_tonnes=500.0,
        )

    def test_cage_count_reflects_input(self):
        cages = [self._make_cage("open_net"), self._make_cage("semi_closed")]
        p = build_locality_risk_profile("KH_S01", cages=cages)
        assert p.cage_count == 2

    def test_cage_weighting_mode_not_none(self):
        cages = [self._make_cage("open_net")]
        p = build_locality_risk_profile("KH_S01", cages=cages)
        assert p.cage_weighting_mode in ("advanced", "biomass_only")

    def test_cage_portfolio_in_source_summary(self):
        cages = [self._make_cage()]
        p = build_locality_risk_profile("KH_S01", cages=cages)
        assert p.source_summary.cage_portfolio_available is True
        assert "Cage Portfolio" in p.source_summary.sources_used

    def test_domain_multipliers_present_for_all_domains(self):
        cages = [self._make_cage("fully_closed")]
        p = build_locality_risk_profile("KH_S01", cages=cages)
        assert set(p.domain_multipliers.keys()) == set(DOMAINS)

    def test_no_cage_defaults_in_used_defaults(self):
        cages = [self._make_cage()]
        p = build_locality_risk_profile("KH_S01", cages=cages)
        cage_defaults = [d for d in p.used_defaults if "cage" in d.lower()]
        assert cage_defaults == []


# ── E. Confidence and defaults ──────────────────────────────────────────────────

class TestConfidenceAndDefaults:
    def test_used_defaults_is_list(self):
        p = build_locality_risk_profile("KH_S01")
        assert isinstance(p.used_defaults, list)

    def test_confidence_notes_is_list(self):
        p = build_locality_risk_profile("KH_S01")
        assert isinstance(p.confidence_notes, list)

    def test_source_summary_fields(self):
        p = build_locality_risk_profile("KH_S01")
        src = p.source_summary
        assert isinstance(src.live_risk_available, bool)
        assert isinstance(src.bw_live, bool)
        assert isinstance(src.sources_used, list)
        assert len(src.sources_used) >= 1

    def test_kh_s02_confidence_notes_mention_missing_source(self):
        # KH_S02 has a degraded BW environmental source → should appear in notes
        p = build_locality_risk_profile("KH_S02")
        notes_str = " ".join(p.confidence_notes).lower()
        assert "bw" in notes_str or "miljø" in notes_str or "kilde" in notes_str or "missing" in notes_str

    def test_kh_s03_high_confidence(self):
        # KH_S03 has sync_delay=0.8h → fresh, should be high
        p = build_locality_risk_profile("KH_S03")
        assert p.confidence_level == "high"


# ── F. Multi-locality build ─────────────────────────────────────────────────────

class TestMultiLocalityBuild:
    def test_returns_all_profiles(self):
        profiles = build_locality_risk_profiles(KH_IDS)
        assert len(profiles) == 3

    def test_each_profile_has_unique_locality_id(self):
        profiles = build_locality_risk_profiles(KH_IDS)
        ids = [p.locality_id for p in profiles]
        assert len(set(ids)) == 3

    def test_subset_build(self):
        profiles = build_locality_risk_profiles(["KH_S01", "KH_S03"])
        assert len(profiles) == 2
        ids = {p.locality_id for p in profiles}
        assert ids == {"KH_S01", "KH_S03"}

    def test_empty_input(self):
        profiles = build_locality_risk_profiles([])
        assert profiles == []

    def test_profiles_are_independent(self):
        profiles = build_locality_risk_profiles(KH_IDS)
        ids = [p.locality_id for p in profiles]
        assert "KH_S01" in ids
        assert "KH_S02" in ids
        assert "KH_S03" in ids


# ── G. API contract ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from backend.main import app
    return TestClient(app)


class TestLocalityRiskProfileAPI:
    def test_single_profile_200(self, client):
        resp = client.get("/api/localities/KH_S01/risk-profile")
        assert resp.status_code == 200

    def test_single_profile_structure(self, client):
        resp = client.get("/api/localities/KH_S01/risk-profile")
        d = resp.json()
        assert d["locality_id"] == "KH_S01"
        assert "total_risk_score" in d
        assert "domain_scores" in d
        assert "domain_weights" in d
        assert "domain_multipliers" in d
        assert "scale_factors" in d
        assert "confidence_level" in d
        assert "top_risk_drivers" in d
        assert "source_summary" in d

    def test_unknown_locality_404(self, client):
        resp = client.get("/api/localities/UNKNOWN_X/risk-profile")
        assert resp.status_code == 404

    def test_batch_endpoint_all_kh(self, client):
        resp = client.post(
            "/api/localities/risk-profiles",
            json={"locality_ids": ["KH_S01", "KH_S02", "KH_S03"]},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 3

    def test_batch_endpoint_partial_unknown(self, client):
        resp = client.post(
            "/api/localities/risk-profiles",
            json={"locality_ids": ["KH_S01", "DOES_NOT_EXIST"]},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 2
        # One valid, one error entry
        ids_or_errors = [(r.get("locality_id"), r.get("error")) for r in results]
        assert any(lid == "KH_S01" for lid, _ in ids_or_errors)
        assert any(err is not None for _, err in ids_or_errors)

    def test_batch_empty_list(self, client):
        resp = client.post(
            "/api/localities/risk-profiles",
            json={"locality_ids": []},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_all_kh_localities_return_200(self, client, lid):
        resp = client.get(f"/api/localities/{lid}/risk-profile")
        assert resp.status_code == 200

    def test_domain_weights_sum_to_one_in_api_response(self, client):
        resp = client.get("/api/localities/KH_S01/risk-profile")
        dw = resp.json()["domain_weights"]
        total = sum(dw.values())
        assert total == pytest.approx(1.0, abs=1e-4)


# ── H. KH portfolio known-value tests ──────────────────────────────────────────

class TestKHPortfolioValues:
    def test_kornstad_company_name(self):
        p = build_locality_risk_profile("KH_S01")
        assert "Kornstad" in p.company_name

    def test_leite_company_name(self):
        p = build_locality_risk_profile("KH_S02")
        assert "Kornstad" in p.company_name

    def test_hogsnes_lowest_exposure(self):
        # KH_S03 has exposure=0.85 (sheltered) — lowest in portfolio
        profiles = {p.locality_id: p for p in build_locality_risk_profiles(KH_IDS)}
        assert profiles["KH_S03"].exposure_factor < profiles["KH_S01"].exposure_factor
        assert profiles["KH_S03"].exposure_factor < profiles["KH_S02"].exposure_factor

    def test_kornstad_biomass_3000t(self):
        p = build_locality_risk_profile("KH_S01")
        assert p.biomass_tonnes == pytest.approx(3000.0)

    def test_leite_biomass_2500t(self):
        p = build_locality_risk_profile("KH_S02")
        assert p.biomass_tonnes == pytest.approx(2500.0)

    def test_hogsnes_biomass_2800t(self):
        p = build_locality_risk_profile("KH_S03")
        assert p.biomass_tonnes == pytest.approx(2800.0)

    def test_all_regions_more_og_romsdal(self):
        for lid in KH_IDS:
            p = build_locality_risk_profile(lid)
            assert "Møre og Romsdal" in p.region or "romsdal" in p.region.lower()

    def test_metadata_has_lat_lon(self):
        p = build_locality_risk_profile("KH_S01")
        assert p.metadata.get("lat") is not None
        assert p.metadata.get("lon") is not None

    def test_metadata_has_locality_no(self):
        p = build_locality_risk_profile("KH_S01")
        assert p.metadata.get("locality_no") == 12855
