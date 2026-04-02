"""
tests/ila/test_norshelf_adapter.py

Tester for NorShelf-adapteren.

Tester caching, DQI-logikk, fallback og dataparsing uten å treffe
BarentsWatch API (patching av _fetch_norshelf og _get_token).
"""
from __future__ import annotations

import math
import time
from unittest.mock import MagicMock, patch

import pytest

from backend.services import norshelf_adapter
from backend.services.norshelf_adapter import (
    NorShelfData,
    _cache_dqi,
    _fallback_data,
    _parse_hs,
    _parse_temperature,
    _parse_u_v,
    clear_cache,
    get_norshelf,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_cache():
    """Tøm cache mellom alle tester."""
    clear_cache()
    yield
    clear_cache()


def _make_live(u=0.10, v=0.05, t=7.2, hs=1.1, now=None) -> NorShelfData:
    return NorShelfData(u=u, v=v, t_water=t, hs=hs, dqi=1, fetched_at=now or time.time())


# ── NorShelfData ──────────────────────────────────────────────────────────────

class TestNorShelfData:
    def test_current_speed_pythagoras(self):
        d = NorShelfData(u=0.3, v=0.4, t_water=7.0, hs=1.0, dqi=1, fetched_at=0)
        assert abs(d.current_speed() - 0.5) < 1e-9

    def test_current_speed_zero(self):
        d = NorShelfData(u=0.0, v=0.0, t_water=6.0, hs=0.5, dqi=1, fetched_at=0)
        assert d.current_speed() == 0.0

    def test_to_dict_keys(self):
        d = _make_live()
        keys = set(d.to_dict().keys())
        assert {"u", "v", "t_water", "hs", "dqi", "current_speed"} == keys

    def test_to_dict_current_speed_rounded(self):
        d = NorShelfData(u=0.3, v=0.4, t_water=7.0, hs=1.0, dqi=1, fetched_at=0)
        assert d.to_dict()["current_speed"] == 0.5


# ── DQI cache-logikk ──────────────────────────────────────────────────────────

class TestCacheDqi:
    def test_dqi1_fresh(self):
        now = time.time()
        assert _cache_dqi(now - 100, now) == 1

    def test_dqi1_at_boundary(self):
        now = time.time()
        assert _cache_dqi(now - (55 * 60 - 1), now) == 1

    def test_dqi2_stale(self):
        now = time.time()
        assert _cache_dqi(now - (55 * 60 + 1), now) == 2

    def test_dqi2_within_6h(self):
        now = time.time()
        assert _cache_dqi(now - (3 * 3600), now) == 2

    def test_dqi3_older_than_6h(self):
        now = time.time()
        assert _cache_dqi(now - (6 * 3600 + 1), now) == 3


# ── Fallback ──────────────────────────────────────────────────────────────────

class TestFallback:
    def test_fallback_dqi3(self):
        fb = _fallback_data()
        assert fb.dqi == 3

    def test_fallback_values_reasonable(self):
        fb = _fallback_data()
        assert 5.0 <= fb.t_water <= 10.0
        assert 0.0 <= fb.hs <= 3.0
        assert fb.fetched_at == 0.0

    def test_fallback_custom_dqi(self):
        assert _fallback_data(dqi=2).dqi == 2


# ── Parsefunksjoner ───────────────────────────────────────────────────────────

class TestParsers:
    # u/v
    def test_parse_u_v_uv_keys(self):
        u, v = _parse_u_v({"u": 0.12, "v": -0.05})
        assert u == pytest.approx(0.12)
        assert v == pytest.approx(-0.05)

    def test_parse_u_v_eastward_northward(self):
        u, v = _parse_u_v({"eastward": 0.20, "northward": 0.10})
        assert u == pytest.approx(0.20)

    def test_parse_u_v_list_input(self):
        u, v = _parse_u_v([{"u": 0.08, "v": 0.04}])
        assert u == pytest.approx(0.08)

    def test_parse_u_v_none_payload(self):
        u, v = _parse_u_v(None)
        assert u is None and v is None

    def test_parse_u_v_empty_list(self):
        u, v = _parse_u_v([])
        assert u is None

    # temperature
    def test_parse_temperature_temperature_key(self):
        assert _parse_temperature({"temperature": 7.3}) == pytest.approx(7.3)

    def test_parse_temperature_value_key(self):
        assert _parse_temperature({"value": 6.9}) == pytest.approx(6.9)

    def test_parse_temperature_none(self):
        assert _parse_temperature(None) is None

    def test_parse_temperature_list(self):
        assert _parse_temperature([{"seaSurfaceTemperature": 8.0}]) == pytest.approx(8.0)

    # Hs
    def test_parse_hs_hs_key(self):
        assert _parse_hs({"hs": 1.4}) == pytest.approx(1.4)

    def test_parse_hs_significantWaveHeight(self):
        assert _parse_hs({"significantWaveHeight": 2.1}) == pytest.approx(2.1)

    def test_parse_hs_none(self):
        assert _parse_hs(None) is None

    def test_parse_hs_list(self):
        assert _parse_hs([{"Hs": 0.9}]) == pytest.approx(0.9)


# ── get_norshelf — ingen token ────────────────────────────────────────────────

class TestGetNorshelfNoToken:
    def test_returns_fallback_when_no_token(self):
        with patch("backend.services.norshelf_adapter._get_token", return_value=None):
            result = get_norshelf(63.0, 7.5)
        assert result.dqi == 3

    def test_fallback_has_sane_values(self):
        with patch("backend.services.norshelf_adapter._get_token", return_value=None):
            result = get_norshelf(63.0, 7.5)
        assert 5.0 <= result.t_water <= 10.0
        assert result.hs >= 0.0


# ── get_norshelf — live fetch ─────────────────────────────────────────────────

class TestGetNorshelfLiveFetch:
    def _mock_fetch(self, u=0.12, v=0.04, t=7.1, hs=0.9):
        """Returnerer NorShelfData med DQI=1 (simulerer vellykket BW-henting)."""
        now = time.time()
        return NorShelfData(u=u, v=v, t_water=t, hs=hs, dqi=1, fetched_at=now)

    def test_live_fetch_populates_cache(self):
        data = self._mock_fetch()
        with patch("backend.services.norshelf_adapter._fetch_norshelf", return_value=data):
            r1 = get_norshelf(63.0, 7.5)
            r2 = get_norshelf(63.0, 7.5)
        assert r1.dqi == 1
        assert r1.t_water == r2.t_water  # cache-treff

    def test_different_coords_separate_cache(self):
        d1 = self._mock_fetch(t=7.0)
        d2 = self._mock_fetch(t=8.5)

        call_count = 0

        def side_effect(lat, lon):
            nonlocal call_count
            call_count += 1
            return d1 if lat < 63.05 else d2

        with patch("backend.services.norshelf_adapter._fetch_norshelf", side_effect=side_effect):
            r1 = get_norshelf(63.0, 7.5)
            r2 = get_norshelf(63.1, 7.6)
        assert r1.t_water != r2.t_water
        assert call_count == 2

    def test_stale_cache_returns_dqi2_when_bw_unavailable(self):
        stale_time = time.time() - (60 * 60)  # 60 min gammel
        stale_data = NorShelfData(u=0.1, v=0.0, t_water=7.0, hs=0.8, dqi=1, fetched_at=stale_time)

        # Populer cache manuelt
        key = (round(63.0, 2), round(7.5, 2))
        norshelf_adapter._CACHE[key] = {"data": stale_data, "fetched_at": stale_time}

        with patch("backend.services.norshelf_adapter._fetch_norshelf", return_value=None):
            result = get_norshelf(63.0, 7.5)

        assert result.dqi == 2
        assert result.t_water == pytest.approx(7.0)

    def test_very_old_cache_returns_dqi3_when_bw_unavailable(self):
        old_time = time.time() - (7 * 3600)  # 7 timer gammel
        old_data = NorShelfData(u=0.1, v=0.0, t_water=7.0, hs=0.8, dqi=1, fetched_at=old_time)

        key = (round(63.0, 2), round(7.5, 2))
        norshelf_adapter._CACHE[key] = {"data": old_data, "fetched_at": old_time}

        with patch("backend.services.norshelf_adapter._fetch_norshelf", return_value=None):
            result = get_norshelf(63.0, 7.5)

        assert result.dqi == 3

    def test_stale_cache_refreshed_when_bw_available(self):
        stale_time = time.time() - (60 * 60)
        stale_data = NorShelfData(u=0.1, v=0.0, t_water=7.0, hs=0.8, dqi=1, fetched_at=stale_time)
        fresh_data = NorShelfData(u=0.2, v=0.1, t_water=8.5, hs=1.2, dqi=1, fetched_at=time.time())

        key = (round(63.0, 2), round(7.5, 2))
        norshelf_adapter._CACHE[key] = {"data": stale_data, "fetched_at": stale_time}

        with patch("backend.services.norshelf_adapter._fetch_norshelf", return_value=fresh_data):
            result = get_norshelf(63.0, 7.5)

        assert result.dqi == 1
        assert result.t_water == pytest.approx(8.5)


# ── Integrasjon mot input_builder ─────────────────────────────────────────────

class TestNorShelfInputBuilderIntegration:
    """Verifiserer at NorShelf-data påvirker stressnivå og i_fraksjon korrekt."""

    def test_bolge_stress_oker_stressniva(self):
        from c5ai_plus.biological.ila.input_builder import _compute_stressniva

        live_neutral = {
            "lice": [0.3] * 7,
            "temperature": [7.0] * 7,
            "oxygen": [9.0] * 7,
            "treatment": [0] * 7,
        }
        ns_stille   = NorShelfData(u=0.0, v=0.0, t_water=7.0, hs=0.2, dqi=1, fetched_at=time.time())
        ns_hoybylge = NorShelfData(u=0.0, v=0.0, t_water=7.0, hs=3.5, dqi=1, fetched_at=time.time())

        s_stille   = _compute_stressniva(live_neutral, norshelf=ns_stille)
        s_hoybylge = _compute_stressniva(live_neutral, norshelf=ns_hoybylge)
        assert s_hoybylge > s_stille

    def test_norshelf_temp_brukes_fremfor_mock_temp(self):
        from c5ai_plus.biological.ila.input_builder import _compute_stressniva

        live = {
            "lice": [0.3] * 7,
            "temperature": [6.0] * 7,  # mock temp: lav (ingen stress)
            "oxygen": [9.0] * 7,
            "treatment": [0] * 7,
        }
        ns_varm = NorShelfData(u=0.0, v=0.0, t_water=13.0, hs=0.2, dqi=1, fetched_at=time.time())
        ns_kald = NorShelfData(u=0.0, v=0.0, t_water=6.0,  hs=0.2, dqi=1, fetched_at=time.time())

        # Varm NorShelf skal gi høyere stress (temp_stress > 0)
        assert _compute_stressniva(live, norshelf=ns_varm) > _compute_stressniva(live, norshelf=ns_kald)

    def test_dqi3_norshelf_ignores_bolge(self):
        from c5ai_plus.biological.ila.input_builder import _compute_stressniva

        live = {
            "lice": [0.3] * 7,
            "temperature": [7.0] * 7,
            "oxygen": [9.0] * 7,
            "treatment": [0] * 7,
        }
        ns_dqi3 = NorShelfData(u=0.0, v=0.0, t_water=7.0, hs=4.0, dqi=3, fetched_at=0)
        s_with  = _compute_stressniva(live, norshelf=ns_dqi3)
        s_none  = _compute_stressniva(live, norshelf=None)
        # DQI=3 → bølge ignoreres; skal gi samme resultat som None
        assert abs(s_with - s_none) < 1e-6

    def test_hoy_strom_oker_i_fraksjon(self):
        from c5ai_plus.biological.ila.input_builder import _compute_nabo_smittepress

        ns_stille = NorShelfData(u=0.0, v=0.0, t_water=7.0, hs=0.5, dqi=1, fetched_at=time.time())
        ns_sterk  = NorShelfData(u=0.4, v=0.0, t_water=7.0, hs=0.5, dqi=1, fetched_at=time.time())

        _, i_stille = _compute_nabo_smittepress("KH_S01", norshelf=ns_stille)
        _, i_sterk  = _compute_nabo_smittepress("KH_S01", norshelf=ns_sterk)
        assert i_sterk >= i_stille

    def test_i_fraksjon_capped_at_1(self):
        from c5ai_plus.biological.ila.input_builder import _compute_nabo_smittepress

        ns_ekstrem = NorShelfData(u=5.0, v=5.0, t_water=7.0, hs=0.5, dqi=1, fetched_at=time.time())
        _, i_fraksjon = _compute_nabo_smittepress("KH_S01", norshelf=ns_ekstrem)
        assert i_fraksjon <= 1.0
