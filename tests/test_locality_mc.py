"""
tests/test_locality_mc.py

Tests for Sprint 2 — Locality Monte Carlo Integration.

Covers:
  A. Sigmoid helper functions
  B. LocalityMonteCarloInput builder (frequency/severity mapping)
  C. OperatorInput construction
  D. Domain multiplier application
  E. LocalityMCResult runner
  F. Domain breakdown (with and without cage portfolio)
  G. Batch runner
  H. API contract (single + batch)
  I. KH portfolio known-value assertions
  J. Monotonicity: higher risk score → higher EAL
"""
from __future__ import annotations

import math
import pytest
from fastapi.testclient import TestClient

from models.locality_mc_inputs import (
    LocalityMonteCarloInput,
    build_locality_mc_inputs,
    score_to_frequency_multiplier,
    score_to_severity_multiplier,
    _FREQ_DOMAIN_WEIGHTS,
    _SEV_DOMAIN_WEIGHTS,
)
from models.locality_risk_profile import DOMAINS
from backend.services.locality_mc_runner import (
    LocalityMCResult,
    run_locality_mc,
    run_locality_mc_batch,
)
from backend.services.locality_risk_builder import build_locality_risk_profile


KH_IDS = ["KH_S01", "KH_S02", "KH_S03"]
_N = 2_000   # small N for fast tests


# ── A. Sigmoid helpers ──────────────────────────────────────────────────────────

class TestSigmoidFunctions:
    def test_frequency_at_score_50_is_1(self):
        assert score_to_frequency_multiplier(50.0) == pytest.approx(1.0, abs=1e-6)

    def test_severity_at_score_50_is_1(self):
        assert score_to_severity_multiplier(50.0) == pytest.approx(1.0, abs=1e-6)

    def test_frequency_increases_with_score(self):
        assert score_to_frequency_multiplier(70) > score_to_frequency_multiplier(50)
        assert score_to_frequency_multiplier(50) > score_to_frequency_multiplier(30)

    def test_severity_increases_with_score(self):
        assert score_to_severity_multiplier(70) > score_to_severity_multiplier(50)
        assert score_to_severity_multiplier(50) > score_to_severity_multiplier(30)

    def test_frequency_range_is_bounded(self):
        low = score_to_frequency_multiplier(0)
        high = score_to_frequency_multiplier(100)
        assert low > 0.3
        assert high < 2.0

    def test_severity_range_is_milder_than_frequency(self):
        # Severity should have smaller range than frequency
        freq_range = score_to_frequency_multiplier(80) - score_to_frequency_multiplier(20)
        sev_range  = score_to_severity_multiplier(80)  - score_to_severity_multiplier(20)
        assert sev_range < freq_range

    def test_frequency_domain_weights_sum_to_one(self):
        assert sum(_FREQ_DOMAIN_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-9)

    def test_severity_domain_weights_sum_to_one(self):
        assert sum(_SEV_DOMAIN_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-9)


# ── B. LocalityMonteCarloInput builder ─────────────────────────────────────────

class TestBuildLocalityMCInputs:
    @pytest.mark.parametrize("lid", KH_IDS)
    def test_returns_mc_input(self, lid):
        profile = build_locality_risk_profile(lid)
        mc = build_locality_mc_inputs(profile)
        assert isinstance(mc, LocalityMonteCarloInput)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_locality_id_matches(self, lid):
        profile = build_locality_risk_profile(lid)
        mc = build_locality_mc_inputs(profile)
        assert mc.locality_id == lid

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_base_events_positive(self, lid):
        profile = build_locality_risk_profile(lid)
        mc = build_locality_mc_inputs(profile)
        assert mc.base_expected_events > 0

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_effective_events_positive(self, lid):
        profile = build_locality_risk_profile(lid)
        mc = build_locality_mc_inputs(profile)
        assert mc.effective_expected_events > 0

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_effective_severity_positive(self, lid):
        profile = build_locality_risk_profile(lid)
        mc = build_locality_mc_inputs(profile)
        assert mc.effective_mean_severity_nok > 0

    def test_base_freq_derived_from_site_profile(self):
        # KH_S03 (exposure=0.85, sheltered) should have lower base_freq than KH_S01 (open_coast)
        p1 = build_locality_risk_profile("KH_S01")
        p3 = build_locality_risk_profile("KH_S03")
        mc1 = build_locality_mc_inputs(p1)
        mc3 = build_locality_mc_inputs(p3)
        assert mc3.base_expected_events < mc1.base_expected_events

    def test_base_severity_is_18_pct_of_biomass(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        expected_sev = p.biomass_tonnes * 65_000 * 0.18
        assert mc.base_mean_severity_nok == pytest.approx(expected_sev, rel=0.01)

    def test_frequency_multiplier_matches_sigmoid(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        expected = score_to_frequency_multiplier(p.total_risk_score)
        assert mc.frequency_multiplier == pytest.approx(expected, rel=1e-6)

    def test_severity_multiplier_matches_sigmoid(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        expected = score_to_severity_multiplier(p.total_risk_score)
        assert mc.severity_multiplier == pytest.approx(expected, rel=1e-6)

    def test_non_bio_fracs_sum_to_one(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert sum(mc.non_bio_domain_fracs.values()) == pytest.approx(1.0, abs=1e-6)

    def test_non_bio_fracs_has_struct_env_ops_keys(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert set(mc.non_bio_domain_fracs.keys()) == {"structural", "environmental", "operational"}

    def test_cage_multipliers_has_all_four_domains(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert set(mc.cage_multipliers.keys()) == set(DOMAINS)


# ── C. OperatorInput construction ───────────────────────────────────────────────

class TestOperatorInput:
    def test_operator_input_has_one_site(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert len(mc.operator_input.sites) == 1

    def test_risk_params_events_match_effective(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert mc.operator_input.risk_params.expected_annual_events == pytest.approx(
            mc.effective_expected_events, rel=1e-6
        )

    def test_risk_params_severity_match_effective(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert mc.operator_input.risk_params.mean_loss_severity == pytest.approx(
            mc.effective_mean_severity_nok, rel=1e-6
        )

    def test_facility_type_is_sea_based(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert mc.operator_input.facility_type == "sea_based"

    def test_country_is_norway(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert mc.operator_input.country == "Norway"

    def test_site_biomass_matches_profile(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert mc.operator_input.sites[0].biomass_tonnes == pytest.approx(p.biomass_tonnes)


# ── D. Domain multiplier application ────────────────────────────────────────────

class TestDomainMultiplierApplication:
    def test_default_multipliers_give_neutral_domain_freq_factor(self):
        # All multipliers = 1.0 → domain_freq_factor = sum(weights × 1.0) = 1.0
        p = build_locality_risk_profile("KH_S01")
        # Profile without cages has all multipliers = 1.0
        mc = build_locality_mc_inputs(p)
        assert mc.domain_freq_factor == pytest.approx(1.0, abs=1e-6)

    def test_default_multipliers_give_neutral_domain_sev_factor(self):
        p = build_locality_risk_profile("KH_S01")
        mc = build_locality_mc_inputs(p)
        assert mc.domain_sev_factor == pytest.approx(1.0, abs=1e-6)

    def test_high_bio_multiplier_increases_frequency(self):
        from models.locality_risk_profile import (
            DomainRiskScores, DomainRiskWeights, LocalityRiskProfile, RiskSourceSummary
        )
        from models.locality_risk_profile import DOMAINS as _D  # noqa: F401

        p_base = build_locality_risk_profile("KH_S01")
        # Manually set a high bio multiplier
        import dataclasses
        p_high_bio = dataclasses.replace(
            p_base,
            domain_multipliers={**p_base.domain_multipliers, "biological": 1.5},
        )
        mc_base = build_locality_mc_inputs(p_base)
        mc_high = build_locality_mc_inputs(p_high_bio)
        assert mc_high.domain_freq_factor > mc_base.domain_freq_factor

    def test_high_struct_multiplier_increases_severity(self):
        import dataclasses
        p_base = build_locality_risk_profile("KH_S01")
        p_high_struct = dataclasses.replace(
            p_base,
            domain_multipliers={**p_base.domain_multipliers, "structural": 1.5},
        )
        mc_base  = build_locality_mc_inputs(p_base)
        mc_high  = build_locality_mc_inputs(p_high_struct)
        assert mc_high.domain_sev_factor > mc_base.domain_sev_factor


# ── E. LocalityMCResult runner ───────────────────────────────────────────────────

class TestRunLocalityMC:
    @pytest.mark.parametrize("lid", KH_IDS)
    def test_result_created(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        assert isinstance(r, LocalityMCResult)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_eal_positive(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        assert r.eal_nok > 0

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_scr_greater_than_eal(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        assert r.scr_nok > r.eal_nok

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_var_ordering(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        assert r.var_95_nok <= r.var_99_nok <= r.scr_nok

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_domain_eal_sum_approx_total_eal(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        domain_sum = sum(r.domain_eal_nok.values())
        assert domain_sum == pytest.approx(r.eal_nok, rel=0.01)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_domain_fractions_sum_to_one(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        assert sum(r.domain_fractions.values()) == pytest.approx(1.0, abs=1e-4)

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_all_domain_fractions_positive(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        for d, v in r.domain_fractions.items():
            assert v >= 0, f"{d} fraction negative"

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_domain_correlation_applied(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        assert r.domain_correlation_applied is True

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_n_simulations_stored(self, lid):
        r = run_locality_mc(lid, n_simulations=_N)
        assert r.n_simulations == _N

    def test_seed_gives_reproducible_results(self):
        r1 = run_locality_mc("KH_S01", n_simulations=_N, seed=7)
        r2 = run_locality_mc("KH_S01", n_simulations=_N, seed=7)
        assert r1.eal_nok == r2.eal_nok
        assert r1.scr_nok == r2.scr_nok

    def test_different_seeds_give_different_results(self):
        r1 = run_locality_mc("KH_S01", n_simulations=_N, seed=1)
        r2 = run_locality_mc("KH_S01", n_simulations=_N, seed=99)
        # Very unlikely to be identical
        assert r1.eal_nok != r2.eal_nok or r1.scr_nok != r2.scr_nok


# ── F. Domain breakdown with cage portfolio ─────────────────────────────────────

class TestDomainBreakdownWithCages:
    def _make_cage(self, cage_type="open_net"):
        from models.cage_technology import CagePenConfig
        return CagePenConfig(cage_id=f"c_{cage_type}", cage_type=cage_type, biomass_tonnes=500.0)

    def test_cage_portfolio_accepted(self):
        cages = [self._make_cage("semi_closed"), self._make_cage("open_net")]
        r = run_locality_mc("KH_S01", cages=cages, n_simulations=_N)
        assert isinstance(r, LocalityMCResult)
        assert r.eal_nok > 0

    def test_cage_portfolio_changes_domain_fractions(self):
        r_no_cage = run_locality_mc("KH_S01", n_simulations=_N, seed=42)
        cages = [self._make_cage("fully_closed")]
        r_with_cage = run_locality_mc("KH_S01", cages=cages, n_simulations=_N, seed=42)
        # Fully closed cage has reduced bio multiplier → bio fraction should differ
        assert r_no_cage.domain_fractions != r_with_cage.domain_fractions


# ── G. Batch runner ─────────────────────────────────────────────────────────────

class TestBatchRunner:
    def test_returns_all_three_kh(self):
        results = run_locality_mc_batch(KH_IDS, n_simulations=_N)
        assert len(results) == 3

    def test_no_errors_for_known_ids(self):
        results = run_locality_mc_batch(KH_IDS, n_simulations=_N)
        for r in results:
            assert "error" not in r

    def test_error_entry_for_unknown_id(self):
        results = run_locality_mc_batch(["KH_S01", "UNKNOWN_X"], n_simulations=_N)
        assert len(results) == 2
        errors = [r for r in results if "error" in r]
        assert len(errors) == 1
        assert errors[0]["locality_id"] == "UNKNOWN_X"

    def test_each_locality_uses_different_seed(self):
        # Run batch and individual with same base seed — batch should give same EAL
        batch = run_locality_mc_batch(["KH_S01"], n_simulations=_N, seed=42)
        single = run_locality_mc("KH_S01", n_simulations=_N, seed=42)
        assert batch[0]["eal_nok"] == single.eal_nok

    def test_empty_batch_returns_empty(self):
        assert run_locality_mc_batch([], n_simulations=_N) == []


# ── H. API contract ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from backend.main import app
    return TestClient(app)


class TestLocalityMCAPI:
    def test_single_locality_200(self, client):
        r = client.get(f"/api/localities/KH_S01/mc?n_simulations={_N}")
        assert r.status_code == 200

    def test_single_locality_structure(self, client):
        r = client.get(f"/api/localities/KH_S01/mc?n_simulations={_N}")
        d = r.json()
        required = {
            "locality_id", "locality_name", "eal_nok", "scr_nok",
            "var_99_nok", "var_95_nok", "std_nok", "tvar_95_nok",
            "mean_event_count", "domain_eal_nok", "domain_fractions",
            "effective_expected_events", "effective_mean_severity_nok",
            "frequency_multiplier", "severity_multiplier",
            "total_risk_score", "n_simulations", "domain_correlation_applied",
        }
        assert required.issubset(d.keys())

    def test_unknown_locality_404(self, client):
        r = client.get("/api/localities/FAKE_ID/mc")
        assert r.status_code == 404

    def test_n_simulations_too_small_422(self, client):
        r = client.get("/api/localities/KH_S01/mc?n_simulations=100")
        assert r.status_code == 422

    @pytest.mark.parametrize("lid", KH_IDS)
    def test_all_kh_return_200(self, client, lid):
        r = client.get(f"/api/localities/{lid}/mc?n_simulations={_N}")
        assert r.status_code == 200

    def test_batch_endpoint_200(self, client):
        r = client.post(
            "/api/localities/mc-batch",
            json={"locality_ids": KH_IDS, "n_simulations": _N},
        )
        assert r.status_code == 200

    def test_batch_returns_three_entries(self, client):
        r = client.post(
            "/api/localities/mc-batch",
            json={"locality_ids": KH_IDS, "n_simulations": _N},
        )
        assert len(r.json()) == 3

    def test_batch_partial_unknown(self, client):
        r = client.post(
            "/api/localities/mc-batch",
            json={"locality_ids": ["KH_S01", "NO_SUCH"], "n_simulations": _N},
        )
        assert r.status_code == 200
        results = r.json()
        assert len(results) == 2
        errors = [x for x in results if "error" in x]
        assert len(errors) == 1

    def test_domain_fractions_sum_to_one_api(self, client):
        r = client.get(f"/api/localities/KH_S01/mc?n_simulations={_N}")
        fracs = r.json()["domain_fractions"]
        assert sum(fracs.values()) == pytest.approx(1.0, abs=1e-4)

    def test_scr_greater_than_eal_api(self, client):
        r = client.get(f"/api/localities/KH_S01/mc?n_simulations={_N}")
        d = r.json()
        assert d["scr_nok"] > d["eal_nok"]


# ── I. KH portfolio known-value assertions ───────────────────────────────────────

class TestKHKnownValues:
    def test_kornstad_eal_in_plausible_range(self):
        # KH_S01: 3000t × 65k = 195 MNOK biomass; portfolio EAL ~22.6M / 3 ≈ 7.5M per site
        r = run_locality_mc("KH_S01", n_simulations=_N)
        assert 1_000_000 < r.eal_nok < 25_000_000

    def test_leite_eal_in_plausible_range(self):
        r = run_locality_mc("KH_S02", n_simulations=_N)
        assert 1_000_000 < r.eal_nok < 25_000_000

    def test_hogsnes_eal_in_plausible_range(self):
        r = run_locality_mc("KH_S03", n_simulations=_N)
        assert 500_000 < r.eal_nok < 20_000_000

    def test_hogsnes_lower_base_freq_than_kornstad(self):
        # Sheltered (0.85) vs open_coast (1.15)
        p1 = build_locality_risk_profile("KH_S01")
        p3 = build_locality_risk_profile("KH_S03")
        mc1 = build_locality_mc_inputs(p1)
        mc3 = build_locality_mc_inputs(p3)
        assert mc3.base_expected_events < mc1.base_expected_events

    def test_all_domain_keys_present(self):
        r = run_locality_mc("KH_S01", n_simulations=_N)
        assert set(r.domain_eal_nok.keys())   == set(DOMAINS)
        assert set(r.domain_fractions.keys()) == set(DOMAINS)

    def test_locality_name_stored_correctly(self):
        r = run_locality_mc("KH_S01", n_simulations=_N)
        assert r.locality_name == "Kornstad"

    def test_to_dict_roundtrip(self):
        r = run_locality_mc("KH_S01", n_simulations=_N)
        r2 = LocalityMCResult.from_dict(r.to_dict())
        assert r2.locality_id   == r.locality_id
        assert r2.eal_nok       == r.eal_nok
        assert r2.scr_nok       == r.scr_nok
        assert r2.domain_fractions == r.domain_fractions


# ── J. Monotonicity: higher risk score → higher EAL ────────────────────────────

class TestMonotonicity:
    def test_higher_score_gives_higher_eal(self):
        """Manually patch total_risk_score on the profile to check monotonicity."""
        import dataclasses
        p = build_locality_risk_profile("KH_S01")

        # Score 30 (below neutral)
        p_low = dataclasses.replace(p, total_risk_score=30.0)
        mc_low = build_locality_mc_inputs(p_low)

        # Score 70 (above neutral)
        p_high = dataclasses.replace(p, total_risk_score=70.0)
        mc_high = build_locality_mc_inputs(p_high)

        # Higher score → higher effective_events AND severity
        assert mc_high.effective_expected_events > mc_low.effective_expected_events
        assert mc_high.effective_mean_severity_nok > mc_low.effective_mean_severity_nok

    def test_higher_score_gives_higher_eal_end_to_end(self):
        """End-to-end with two different profiles."""
        import dataclasses
        p = build_locality_risk_profile("KH_S01")

        # Force score 20 vs 80 to get a meaningful difference
        p_low  = dataclasses.replace(p, total_risk_score=20.0)
        p_high = dataclasses.replace(p, total_risk_score=80.0)

        from models.monte_carlo import MonteCarloEngine
        from models.domain_correlation import DomainCorrelationMatrix

        def _run(profile):
            mc = build_locality_mc_inputs(profile)
            return MonteCarloEngine(
                mc.operator_input,
                n_simulations=_N,
                seed=42,
                domain_correlation=DomainCorrelationMatrix.expert_default(),
                cage_multipliers=mc.cage_multipliers,
                non_bio_domain_fracs=mc.non_bio_domain_fracs,
            ).run()

        sim_low  = _run(p_low)
        sim_high = _run(p_high)
        assert sim_high.mean_annual_loss > sim_low.mean_annual_loss
