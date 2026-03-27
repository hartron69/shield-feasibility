"""
tests/test_live_risk_economics.py

Tests for Live Risk Economics — config validation, service contracts,
EL/SCR/premium arithmetic, cage attribution, and API endpoint.
"""
import pytest
from fastapi.testclient import TestClient

# ══════════════════════════════════════════════════════════════════════════════
# 1. Config validation
# ══════════════════════════════════════════════════════════════════════════════

class TestEconomicsConfig:
    def test_el_elasticity_positive(self):
        from config.live_risk_economics import EL_ELASTICITY_PER_POINT
        assert EL_ELASTICITY_PER_POINT > 0

    def test_el_elasticity_matches_base_and_ref(self):
        from config.live_risk_economics import (
            EL_ELASTICITY_PER_POINT, BASE_EL_RATE_AT_REF, REFERENCE_RISK_SCORE,
        )
        assert abs(EL_ELASTICITY_PER_POINT - BASE_EL_RATE_AT_REF / REFERENCE_RISK_SCORE) < 1e-10

    def test_scr_loading_in_range(self):
        from config.live_risk_economics import SCR_LOADING
        assert 2.0 <= SCR_LOADING <= 6.0, "SCR loading outside plausible aquaculture range"

    def test_premium_loading_in_range(self):
        from config.live_risk_economics import PREMIUM_LOADING
        assert 1.2 <= PREMIUM_LOADING <= 4.0

    def test_domain_weights_sum_to_one(self):
        from config.live_risk_economics import DOMAIN_WEIGHTS
        total = sum(DOMAIN_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Domain weights sum to {total}, expected 1.0"

    def test_domain_weights_cover_all_domains(self):
        from config.live_risk_economics import DOMAIN_WEIGHTS
        assert set(DOMAIN_WEIGHTS) == {"biological", "structural", "environmental", "operational"}

    def test_all_localities_have_financial_profiles(self):
        from config.live_risk_economics import LOCALITY_FINANCIALS
        from backend.services.live_risk_mock import get_all_locality_ids
        for lid in get_all_locality_ids():
            assert lid in LOCALITY_FINANCIALS, f"No financial profile for {lid}"

    def test_tiv_positive_for_all_localities(self):
        from config.live_risk_economics import LOCALITY_FINANCIALS
        for lid, fin in LOCALITY_FINANCIALS.items():
            tiv = fin["biomass_tonnes"] * fin["value_per_tonne_nok"]
            assert tiv > 0, f"Non-positive TIV for {lid}"

    def test_n_cages_positive(self):
        from config.live_risk_economics import LOCALITY_FINANCIALS
        for lid, fin in LOCALITY_FINANCIALS.items():
            assert fin.get("n_cages", 0) > 0, f"n_cages missing or zero for {lid}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. Service contract
# ══════════════════════════════════════════════════════════════════════════════

REQUIRED_KEYS = {
    "locality_id", "period", "tiv_nok", "biomass_tonnes", "value_per_tonne_nok",
    "current_risk_score", "domain_risk_current", "risk_delta",
    "current_annual_el_nok", "domain_el_delta_nok", "total_el_delta_nok",
    "current_scr_nok", "scr_delta_nok",
    "current_annual_premium_nok", "premium_delta_nok",
    "cage_attribution", "methodology",
}

class TestEconomicsService:
    def test_has_required_keys(self):
        from backend.services.live_risk_economics import get_economics
        result = get_economics("KH_S01", "30d")
        missing = REQUIRED_KEYS - set(result)
        assert not missing, f"Missing keys: {missing}"

    def test_tiv_correct(self):
        from backend.services.live_risk_economics import get_economics
        from config.live_risk_economics import LOCALITY_FINANCIALS
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            fin = LOCALITY_FINANCIALS[lid]
            expected_tiv = fin["biomass_tonnes"] * fin["value_per_tonne_nok"]
            result = get_economics(lid, "30d")
            assert result["tiv_nok"] == expected_tiv

    def test_current_annual_el_positive(self):
        from backend.services.live_risk_economics import get_economics
        result = get_economics("KH_S01", "30d")
        assert result["current_annual_el_nok"] > 0

    def test_el_delta_direction_matches_risk_delta(self):
        """EL delta sign must agree with total risk delta sign."""
        from backend.services.live_risk_economics import get_economics
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            for period in ["30d", "90d"]:
                r = get_economics(lid, period)
                risk_d = r["risk_delta"]["total"]
                el_d   = r["total_el_delta_nok"]
                if abs(risk_d) > 0.05:   # only assert when change is non-trivial
                    assert (el_d >= 0) == (risk_d >= 0), (
                        f"{lid}/{period}: risk_delta={risk_d} but el_delta={el_d}"
                    )

    def test_domain_el_sum_approximately_equals_total_el(self):
        """Sum of domain EL deltas should equal total EL delta (modulo rounding)."""
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        domain_sum = sum(r["domain_el_delta_nok"].values())
        assert abs(domain_sum - r["total_el_delta_nok"]) <= 10  # ±10 NOK rounding

    def test_scr_equals_el_times_loading(self):
        from backend.services.live_risk_economics import get_economics
        from config.live_risk_economics import SCR_LOADING
        r = get_economics("KH_S01", "30d")
        assert r["current_scr_nok"] == round(r["current_annual_el_nok"] * SCR_LOADING)
        assert r["scr_delta_nok"]   == round(r["total_el_delta_nok"] * SCR_LOADING)

    def test_premium_equals_el_times_loading(self):
        from backend.services.live_risk_economics import get_economics
        from config.live_risk_economics import PREMIUM_LOADING
        r = get_economics("KH_S01", "30d")
        assert r["current_annual_premium_nok"] == round(r["current_annual_el_nok"] * PREMIUM_LOADING)
        assert r["premium_delta_nok"]           == round(r["total_el_delta_nok"] * PREMIUM_LOADING)

    def test_domain_risk_current_all_positive(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        for d, v in r["domain_risk_current"].items():
            assert v >= 0, f"domain_risk_current[{d}] = {v}"

    def test_risk_delta_has_all_domains(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        for d in ["biological", "structural", "environmental", "operational", "total"]:
            assert d in r["risk_delta"], f"risk_delta missing '{d}'"

    def test_domain_el_delta_has_all_domains(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        for d in ["biological", "structural", "environmental", "operational"]:
            assert d in r["domain_el_delta_nok"]

    def test_methodology_has_required_fields(self):
        from backend.services.live_risk_economics import get_economics
        m = get_economics("KH_S01", "30d")["methodology"]
        for key in ["el_elasticity_per_point", "scr_loading", "premium_loading",
                    "base_el_rate_at_ref", "reference_risk_score", "domain_weights", "note"]:
            assert key in m

    def test_all_periods_work(self):
        from backend.services.live_risk_economics import get_economics
        for period in ["7d", "30d", "90d", "12m"]:
            r = get_economics("KH_S01", period)
            assert r["period"] == period

    def test_all_localities_return_results(self):
        from backend.services.live_risk_economics import get_economics
        from backend.services.live_risk_mock import get_all_locality_ids
        for lid in get_all_locality_ids():
            r = get_economics(lid, "30d")
            assert r["locality_id"] == lid


# ══════════════════════════════════════════════════════════════════════════════
# 3. Cage attribution
# ══════════════════════════════════════════════════════════════════════════════

class TestCageAttribution:
    def test_cage_attribution_is_list(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        assert isinstance(r["cage_attribution"], list)

    def test_cage_count_matches_config(self):
        from backend.services.live_risk_economics import get_economics
        from config.live_risk_economics import LOCALITY_FINANCIALS
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            r = get_economics(lid, "30d")
            expected = LOCALITY_FINANCIALS[lid]["n_cages"]
            assert len(r["cage_attribution"]) == expected

    def test_cage_shares_sum_to_100(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        total_share = sum(c["biomass_share"] for c in r["cage_attribution"])
        assert abs(total_share - 100.0) < 0.5  # floating point tolerance

    def test_cage_el_sum_approximately_equals_locality_el(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        cage_sum = sum(c["el_delta_nok"] for c in r["cage_attribution"])
        assert abs(cage_sum - r["total_el_delta_nok"]) <= len(r["cage_attribution"])

    def test_cage_has_required_fields(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        for cage in r["cage_attribution"]:
            for key in ["cage_id", "biomass_share", "el_delta_nok", "domain_el_delta_nok"]:
                assert key in cage

    def test_cage_ids_are_unique(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        ids = [c["cage_id"] for c in r["cage_attribution"]]
        assert len(ids) == len(set(ids))

    def test_cage_domain_el_covers_all_domains(self):
        from backend.services.live_risk_economics import get_economics
        r = get_economics("KH_S01", "30d")
        for cage in r["cage_attribution"]:
            for d in ["biological", "structural", "environmental", "operational"]:
                assert d in cage["domain_el_delta_nok"]


# ══════════════════════════════════════════════════════════════════════════════
# 4. Financial sanity checks
# ══════════════════════════════════════════════════════════════════════════════

class TestEconomicsSanity:
    def test_hogsnes_lower_el_than_kornstad(self):
        """KH_S03 (sheltered, lower risk) should have lower current annual EL."""
        from backend.services.live_risk_economics import get_economics
        kh01 = get_economics("KH_S01", "30d")
        kh03 = get_economics("KH_S03", "30d")
        # KH_S01 has higher biomass AND higher risk → higher EL
        assert kh01["current_annual_el_nok"] > kh03["current_annual_el_nok"]

    def test_scr_exceeds_annual_el(self):
        """SCR (VaR tail) should always exceed annual EL."""
        from backend.services.live_risk_economics import get_economics
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            r = get_economics(lid, "30d")
            assert r["current_scr_nok"] > r["current_annual_el_nok"]

    def test_premium_exceeds_annual_el(self):
        """Market premium loading > 1 means premium > EL."""
        from backend.services.live_risk_economics import get_economics
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            r = get_economics(lid, "30d")
            assert r["current_annual_premium_nok"] > r["current_annual_el_nok"]

    def test_tiv_in_plausible_nok_range(self):
        """TIV should be between 50 M and 200 M NOK for these locality sizes."""
        from backend.services.live_risk_economics import get_economics
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            r = get_economics(lid, "30d")
            assert 50_000_000 <= r["tiv_nok"] <= 200_000_000

    def test_el_rate_below_20_pct_of_tiv(self):
        """Annual EL should not exceed 20 % of TIV — sanity cap."""
        from backend.services.live_risk_economics import get_economics
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            r = get_economics(lid, "30d")
            assert r["current_annual_el_nok"] < 0.20 * r["tiv_nok"]


# ══════════════════════════════════════════════════════════════════════════════
# 5. API contract
# ══════════════════════════════════════════════════════════════════════════════

class TestEconomicsAPI:
    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)

    def test_economics_200(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/economics")
        assert r.status_code == 200

    def test_economics_has_tiv(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/economics")
        assert "tiv_nok" in r.json()

    def test_economics_404_unknown_locality(self, client):
        r = client.get("/api/live-risk/localities/UNKNOWN/economics")
        assert r.status_code == 404

    def test_economics_422_invalid_period(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/economics?period=5y")
        assert r.status_code == 422

    def test_economics_all_periods(self, client):
        for period in ["7d", "30d", "90d", "12m"]:
            r = client.get(f"/api/live-risk/localities/KH_S01/economics?period={period}")
            assert r.status_code == 200, f"Failed for period={period}"

    def test_economics_all_localities(self, client):
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            r = client.get(f"/api/live-risk/localities/{lid}/economics")
            assert r.status_code == 200, f"Failed for locality={lid}"

    def test_cage_attribution_in_response(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/economics")
        data = r.json()
        assert "cage_attribution" in data
        assert len(data["cage_attribution"]) == 8  # KH_S01 has 8 cages

    def test_methodology_in_response(self, client):
        r = client.get("/api/live-risk/localities/KH_S01/economics")
        assert "methodology" in r.json()
