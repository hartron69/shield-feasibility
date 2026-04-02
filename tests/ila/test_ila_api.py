"""
tests/ila/test_ila_api.py

API-endepunkt-tester for ILA-modulen.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestILAMre1API:
    def test_mre1_kjente_lokaliteter(self, client):
        for lid in ["KH_S01", "KH_S02", "KH_S03"]:
            r = client.get(f"/api/ila/{lid}/mre1")
            assert r.status_code == 200, f"{lid}: {r.text}"
            d = r.json()
            assert "p_total" in d
            assert "varselniva" in d
            assert "dominerende_kilde" in d

    def test_mre1_p_total_mellom_0_og_1(self, client):
        r = client.get("/api/ila/KH_S01/mre1")
        assert r.status_code == 200
        assert 0 <= r.json()["p_total"] <= 1

    def test_mre1_ukjent_id_gir_404(self, client):
        r = client.get("/api/ila/UKJENT_ID/mre1")
        assert r.status_code == 404

    def test_mre1_har_kilde_felter(self, client):
        r = client.get("/api/ila/KH_S01/mre1")
        d = r.json()
        for felt in ["p_hydro", "p_wb", "p_ops", "p_smolt", "p_wild", "p_mutate", "p_bird"]:
            assert felt in d, f"Mangler felt: {felt}"

    def test_mre1_varselniva_er_gyldig(self, client):
        r = client.get("/api/ila/KH_S01/mre1")
        assert r.json()["varselniva"] in {"GRØNN", "ILA01", "ILA02", "ILA03", "ILA04"}

    def test_mre1_inneholder_ila_sone(self, client):
        r = client.get("/api/ila/KH_S01/mre1")
        assert "ila_sone" in r.json()


class TestILAMre2API:
    def test_mre2_returnerer_52_uker(self, client):
        r = client.get("/api/ila/KH_S01/mre2")
        assert r.status_code == 200
        d = r.json()
        assert d["antall"] == 52
        assert len(d["uker"]) == 52

    def test_mre2_ukentlig_struktur(self, client):
        r = client.get("/api/ila/KH_S01/mre2")
        uke = r.json()["uker"][0]
        for felt in ["uke_nr", "s", "e", "i", "r", "p_uke", "p_kumulativ", "varselniva"]:
            assert felt in uke, f"Mangler felt: {felt}"

    def test_mre2_sesong_uker_parameter(self, client):
        r = client.get("/api/ila/KH_S01/mre2?sesong_uker=13")
        assert r.status_code == 200
        assert r.json()["antall"] == 13

    def test_mre2_ugyldig_sesong_uker_gir_422(self, client):
        r = client.get("/api/ila/KH_S01/mre2?sesong_uker=200")
        assert r.status_code == 422

    def test_mre2_ukjent_id_gir_404(self, client):
        r = client.get("/api/ila/UKJENT/mre2")
        assert r.status_code == 404

    def test_mre2_seir_summer_til_1(self, client):
        uker = client.get("/api/ila/KH_S01/mre2").json()["uker"]
        for uke in uker:
            total = uke["s"] + uke["e"] + uke["i"] + uke["r"]
            assert abs(total - 1.0) < 1e-4, f"Uke {uke['uke_nr']}: SEIR sum = {total}"


class TestILAPortfolioAPI:
    def test_portfolio_returnerer_data(self, client):
        r = client.get("/api/ila/portfolio")
        assert r.status_code == 200
        d = r.json()
        assert "lokaliteter" in d
        assert "antall" in d

    def test_portfolio_sortert_etter_p_total(self, client):
        loks = client.get("/api/ila/portfolio").json()["lokaliteter"]
        if len(loks) >= 2:
            for i in range(len(loks) - 1):
                assert loks[i]["p_total"] >= loks[i+1]["p_total"]

    def test_portfolio_alle_kjente_profiler(self, client):
        loks = client.get("/api/ila/portfolio").json()["lokaliteter"]
        ids = {l["locality_id"] for l in loks}
        # Alle 4 profiler skal være med
        for lid in ["KH_S01", "KH_S02", "KH_S03", "LM_S01"]:
            assert lid in ids
