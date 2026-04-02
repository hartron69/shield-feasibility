"""
tests/ila/test_mre1.py

MRE-1 øyeblikks-snapshot for ILA-risiko.
"""
import math
import pytest
from c5ai_plus.biological.ila.mre1 import (
    ILAMre1Input, ILAMre1Resultat, kjor_mre1, beregn_varselniva
)


# ── Terskel-mapping ──────────────────────────────────────────────────────────

class TestVarselniva:
    def test_gronn(self):
        assert beregn_varselniva(0.00) == "GRØNN"
        assert beregn_varselniva(0.04) == "GRØNN"

    def test_ila01_grense(self):
        assert beregn_varselniva(0.05) == "ILA01"
        assert beregn_varselniva(0.19) == "ILA01"

    def test_ila02_grense(self):
        assert beregn_varselniva(0.20) == "ILA02"
        assert beregn_varselniva(0.49) == "ILA02"

    def test_ila03_grense(self):
        assert beregn_varselniva(0.50) == "ILA03"
        assert beregn_varselniva(0.79) == "ILA03"

    def test_ila04_grense(self):
        assert beregn_varselniva(0.80) == "ILA04"
        assert beregn_varselniva(1.00) == "ILA04"


# ── Matematiske invarianter ──────────────────────────────────────────────────

class TestMRE1Invarianter:
    def test_p_total_mellom_0_og_1(self):
        res = kjor_mre1(ILAMre1Input())
        assert 0 <= res.p_total <= 1

    def test_p_total_capped_ved_0_999(self):
        # Maksimal eksponering skal ikke returnere nøyaktig 1.0
        inp = ILAMre1Input(
            hpr0_tetthet=1.0,
            i_fraksjon_naboer=1.0,
            bronnbat_besok_per_ar=100,
            bronnbat_desinfeksjon_rate=0.0,
            antall_nabo_med_ila=10,
        )
        res = kjor_mre1(inp)
        assert res.p_total <= 0.999

    def test_kilde_attribusjon_summerer_til_1(self):
        res = kjor_mre1(ILAMre1Input())
        total = (res.attrib_hydro + res.attrib_wb + res.attrib_ops
                 + res.attrib_smolt + res.attrib_wild + res.attrib_mutate)
        assert abs(total - 1.0) < 0.01

    def test_alle_p_verdier_ikke_negative(self):
        res = kjor_mre1(ILAMre1Input())
        for attr in ["p_hydro", "p_wb", "p_ops", "p_smolt", "p_wild", "p_mutate", "p_bird"]:
            assert getattr(res, attr) >= 0

    def test_p_total_stoerre_enn_max_enkelt_kilde(self):
        # P_total ≥ max enkelt P_k  (fra 1 − ∏(1−P_k))
        inp = ILAMre1Input(hpr0_tetthet=0.5, bronnbat_besok_per_ar=20)
        res = kjor_mre1(inp)
        max_p = max(res.p_hydro, res.p_wb, res.p_ops, res.p_smolt,
                    res.p_wild, res.p_mutate, res.p_bird)
        assert res.p_total >= max_p


# ── Retningsriktige effekter ─────────────────────────────────────────────────

class TestMRE1Sensitivitet:
    def test_hpr0_oker_p_total(self):
        lavt  = kjor_mre1(ILAMre1Input(hpr0_tetthet=0.10))
        hoyt  = kjor_mre1(ILAMre1Input(hpr0_tetthet=0.80))
        assert hoyt.p_total > lavt.p_total

    def test_bronnbat_frekvens_oker_p_total(self):
        lavt  = kjor_mre1(ILAMre1Input(bronnbat_besok_per_ar=4))
        hoyt  = kjor_mre1(ILAMre1Input(bronnbat_besok_per_ar=36))
        assert hoyt.p_total > lavt.p_total

    def test_god_desinfeksjon_senker_p_total(self):
        god   = kjor_mre1(ILAMre1Input(bronnbat_desinfeksjon_rate=0.99))
        darlig = kjor_mre1(ILAMre1Input(bronnbat_desinfeksjon_rate=0.10))
        assert god.p_total < darlig.p_total

    def test_fuglesesong_oker_p_bird(self):
        ute    = kjor_mre1(ILAMre1Input(fugl_sesong_aktiv=False))
        inne   = kjor_mre1(ILAMre1Input(fugl_sesong_aktiv=True))
        assert inne.p_bird > ute.p_bird

    def test_fersk_smolt_har_hoy_p_smolt(self):
        fersk  = kjor_mre1(ILAMre1Input(smolt_uker_siden_utsett=0))
        gammel = kjor_mre1(ILAMre1Input(smolt_uker_siden_utsett=40))
        assert fersk.p_smolt > gammel.p_smolt

    def test_nabo_med_ila_oker_p_wb(self):
        ingen  = kjor_mre1(ILAMre1Input(antall_nabo_med_ila=0))
        tre    = kjor_mre1(ILAMre1Input(antall_nabo_med_ila=3))
        assert tre.p_wb > ingen.p_wb


# ── Spesifikke scenario ──────────────────────────────────────────────────────

class TestMRE1Scenarioer:
    def test_gronn_ved_lav_eksponering(self):
        # Minimal eksponering: lav HPR0, ingen nabosmitte, null delte ops,
        # gammel smolt, god desinfeksjon, lav tetthet
        inp = ILAMre1Input(
            hpr0_tetthet=0.02,
            bronnbat_besok_per_ar=2,
            bronnbat_desinfeksjon_rate=0.99,
            i_fraksjon_naboer=0.0,
            delte_ops_per_ar=0,
            stressniva_norm=0.0,
            biomasse_tetthet_norm=0.1,
            smolt_uker_siden_utsett=52,
            villfisk_tetthet_norm=0.01,
            mutasjonsrate_prior=0.0001,
            fugl_sesong_aktiv=False,
        )
        res = kjor_mre1(inp)
        assert res.varselniva == "GRØNN"

    def test_ila01_ved_moderat_eksponering(self):
        inp = ILAMre1Input(
            hpr0_tetthet=0.60,
            bronnbat_besok_per_ar=24,
            bronnbat_desinfeksjon_rate=0.50,
        )
        res = kjor_mre1(inp)
        assert res.varselniva in ["ILA01", "ILA02", "ILA03", "ILA04"]

    def test_e_tap_mnok_beregnes_korrekt(self):
        inp = ILAMre1Input()
        res = kjor_mre1(inp, biomasse_verdi_mnok=20.0)
        assert res.e_tap_mnok is not None
        assert abs(res.e_tap_mnok - res.p_total * 20.0) < 0.001

    def test_e_tap_none_ved_null_biomasse(self):
        # biomasse_verdi_mnok=0 er falsy → e_tap returneres som None
        res = kjor_mre1(ILAMre1Input(), biomasse_verdi_mnok=0.0)
        assert res.e_tap_mnok is None

    def test_dominerende_kilde_er_gyldig_kode(self):
        res = kjor_mre1(ILAMre1Input())
        assert res.dominerende_kilde in {"HYDRO", "WB", "OPS", "SMOLT", "WILD", "MUTATE", "BIRD"}


# ── to_dict / from_dict ──────────────────────────────────────────────────────

class TestMRE1Serialisering:
    def test_to_dict_har_alle_felt(self):
        res = kjor_mre1(ILAMre1Input())
        d = res.to_dict()
        expected_keys = {
            "p_total", "varselniva", "dominerende_kilde", "e_tap_mnok",
            "p_hydro", "p_wb", "p_ops", "p_smolt", "p_wild", "p_mutate", "p_bird",
            "attrib_hydro", "attrib_wb", "attrib_ops", "attrib_smolt",
            "attrib_wild", "attrib_mutate",
        }
        assert expected_keys == set(d.keys())

    def test_to_dict_verdier_er_floats(self):
        res = kjor_mre1(ILAMre1Input())
        d = res.to_dict()
        for k, v in d.items():
            if k not in ("varselniva", "dominerende_kilde", "e_tap_mnok"):
                assert isinstance(v, float), f"{k} should be float, got {type(v)}"


# ── KH kjente verdier ────────────────────────────────────────────────────────

class TestMRE1KHVerdier:
    """End-to-end test med kjente KH-lokalitetsprofiler via input_builder."""

    def test_kh_s01_p_total_i_forventet_range(self):
        from c5ai_plus.biological.ila.input_builder import bygg_mre1_input, hent_ila_profil
        inp    = bygg_mre1_input("KH_S01")
        profil = hent_ila_profil("KH_S01")
        assert inp is not None
        res = kjor_mre1(inp, biomasse_verdi_mnok=profil["biomasse_verdi_mnok"])
        # KH_S01: moderat profil — P_total bør ligge mellom 5% og 60%
        assert 0.05 <= res.p_total <= 0.60

    def test_kh_s03_har_lavere_p_total_enn_kh_s02(self):
        from c5ai_plus.biological.ila.input_builder import bygg_mre1_input
        s03 = kjor_mre1(bygg_mre1_input("KH_S03"))
        s02 = kjor_mre1(bygg_mre1_input("KH_S02"))
        # KH_S03 er renest/lavest risiko
        assert s03.p_total < s02.p_total

    def test_alle_kh_lokaliteter_returnerer_resultat(self):
        from c5ai_plus.biological.ila.input_builder import bygg_mre1_input, hent_ila_profil
        for lid in ["KH_S01", "KH_S02", "KH_S03"]:
            inp = bygg_mre1_input(lid)
            assert inp is not None
            profil = hent_ila_profil(lid)
            res = kjor_mre1(inp, biomasse_verdi_mnok=profil["biomasse_verdi_mnok"])
            assert 0 <= res.p_total <= 1
