"""
tests/ila/test_mre2.py

MRE-2 ukentlig SEIR hazard-modell for ILA-risiko.
"""
import pytest
from c5ai_plus.biological.ila.mre2 import kjor_mre2, SEIRUke, SIGMA, RHO


# ── Strukturelle invarianter ─────────────────────────────────────────────────

class TestSEIRInvarianter:
    def test_52_uker_returneres(self):
        uker = kjor_mre2(sesong_uker=52)
        assert len(uker) == 52

    def test_seir_summer_til_1_etter_hvert_steg(self):
        uker = kjor_mre2()
        for u in uker:
            total = u.s + u.e + u.i + u.r
            assert abs(total - 1.0) < 1e-5, f"Uke {u.uke_nr}: S+E+I+R = {total:.8f}"

    def test_alle_seir_fraksjonar_ikke_negative(self):
        uker = kjor_mre2()
        for u in uker:
            assert u.s >= 0
            assert u.e >= 0
            assert u.i >= 0
            assert u.r >= 0

    def test_p_kumulativ_monotont_stigende(self):
        uker = kjor_mre2()
        for i in range(1, len(uker)):
            assert uker[i].p_kumulativ >= uker[i-1].p_kumulativ - 1e-9, \
                f"Uke {uker[i].uke_nr}: p_kum={uker[i].p_kumulativ} < uke {uker[i-1].uke_nr}: {uker[i-1].p_kumulativ}"

    def test_p_kumulativ_start_stoerre_enn_0(self):
        uker = kjor_mre2()
        assert uker[0].p_kumulativ > 0

    def test_p_kumulativ_slutt_lavere_enn_1_korte_sesonger(self):
        # Med svært lav HPR0 og bare 4 uker er p_kum fortsatt < 1
        uker = kjor_mre2(sesong_uker=4, hpr0_tetthet=0.05, intro_rate_base=0.001)
        assert uker[-1].p_kumulativ < 1.0

    def test_uke_nr_starter_paa_1(self):
        uker = kjor_mre2()
        assert uker[0].uke_nr == 1
        assert uker[-1].uke_nr == 52

    def test_p_uke_mellom_0_og_1(self):
        uker = kjor_mre2(hpr0_tetthet=1.0)
        for u in uker:
            assert 0 <= u.p_uke <= 1


# ── SEIR-modellens dynamikk ──────────────────────────────────────────────────

class TestSEIRDynamikk:
    def test_s_synker_over_tid(self):
        uker = kjor_mre2(hpr0_tetthet=0.50)
        # S-fraksjonen bør generelt synke
        assert uker[-1].s <= uker[0].s

    def test_r_vokser_over_tid(self):
        uker = kjor_mre2(hpr0_tetthet=0.50)
        assert uker[-1].r >= uker[0].r

    def test_hoy_hpr0_gir_raskere_progressjon(self):
        # Sammenlign tidlig i sesongen der ingen har nådd tak
        uker_lav  = kjor_mre2(hpr0_tetthet=0.05, sesong_uker=10)
        uker_hoy  = kjor_mre2(hpr0_tetthet=0.80, sesong_uker=10)
        assert uker_hoy[-1].p_kumulativ > uker_lav[-1].p_kumulativ

    def test_ila01_terskel_krysses_ved_hoy_hpr0(self):
        # Med høy HPR0 skal minst ett varselnivå utover GRØNN nås i sesongen
        uker = kjor_mre2(hpr0_tetthet=0.50, intro_rate_base=0.01)
        assert any(u.varselniva != "GRØNN" for u in uker)

    def test_sesong_lengde_variabel(self):
        for n in [4, 13, 26, 52]:
            uker = kjor_mre2(sesong_uker=n)
            assert len(uker) == n

    def test_e0_setter_startbetingelse(self):
        normal = kjor_mre2(e0=0.0)
        med_e0 = kjor_mre2(e0=0.05)
        # Med initial E0 skal I-fraksjonen vokse raskere tidlig
        assert med_e0[5].i >= normal[5].i


# ── Varselnivå-mapping ───────────────────────────────────────────────────────

class TestMRE2Varselniva:
    def test_varselniva_konsistent_med_p_kumulativ(self):
        uker = kjor_mre2(hpr0_tetthet=0.50, intro_rate_base=0.01)
        for u in uker:
            if u.p_kumulativ >= 0.80:
                assert u.varselniva == "ILA04"
            elif u.p_kumulativ >= 0.50:
                assert u.varselniva == "ILA03"
            elif u.p_kumulativ >= 0.20:
                assert u.varselniva == "ILA02"
            elif u.p_kumulativ >= 0.05:
                assert u.varselniva == "ILA01"
            else:
                assert u.varselniva == "GRØNN"


# ── SEIR-konstanter ──────────────────────────────────────────────────────────

class TestSEIRKonstanter:
    def test_sigma_verdi(self):
        assert abs(SIGMA - 1/3) < 1e-10

    def test_rho_verdi(self):
        assert abs(RHO - 1/10) < 1e-10


# ── Serialisering ────────────────────────────────────────────────────────────

class TestMRE2Serialisering:
    def test_to_dict_har_alle_felt(self):
        uker = kjor_mre2()
        d    = uker[0].to_dict()
        expected = {"uke_nr", "s", "e", "i", "r",
                    "lambda_intro", "lambda_amp", "lambda_hydro",
                    "p_uke", "p_kumulativ", "varselniva"}
        assert expected == set(d.keys())

    def test_alle_numeriske_felt_er_float_eller_int(self):
        d = kjor_mre2()[0].to_dict()
        for k, v in d.items():
            if k != "varselniva":
                assert isinstance(v, (int, float)), f"{k}: {type(v)}"
