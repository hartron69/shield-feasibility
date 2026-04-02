"""
tests/ila/test_patogen_kobling.py

ILA → C5AI+ patogen-prior kobling.
"""
import pytest
from c5ai_plus.biological.ila.patogen_kobling import juster_patogen_prior


class TestJusterPatogenPrior:
    def test_ingen_ila_returnerer_statisk_prior(self):
        assert juster_patogen_prior(0.10, None) == 0.10

    def test_blanding_med_vekt_0_6(self):
        # 0.60 * 0.30 + 0.40 * 0.10 = 0.18 + 0.04 = 0.22
        result = juster_patogen_prior(0.10, 0.30, vekt=0.60)
        assert abs(result - 0.22) < 0.0001

    def test_cap_ved_0_70(self):
        result = juster_patogen_prior(0.50, 1.0, vekt=0.90)
        assert result <= 0.70

    def test_ila_null_gir_statisk_prior(self):
        result = juster_patogen_prior(0.15, 0.0, vekt=0.60)
        # 0.60 * 0.0 + 0.40 * 0.15 = 0.06
        assert abs(result - 0.06) < 0.0001

    def test_ila_ekvivalent_gir_statisk(self):
        # Hvis ILA P_total == statisk prior, resultat = statisk prior
        result = juster_patogen_prior(0.10, 0.10, vekt=0.60)
        assert abs(result - 0.10) < 0.0001

    def test_output_avrundet_til_4_desimaler(self):
        result = juster_patogen_prior(0.123456, 0.654321)
        # Kontroller at resultatet er rundet
        assert result == round(result, 4)

    def test_vekt_0_returnerer_statisk_prior(self):
        result = juster_patogen_prior(0.10, 0.80, vekt=0.0)
        assert abs(result - 0.10) < 0.0001

    def test_vekt_1_returnerer_ila_p_total_capped(self):
        result = juster_patogen_prior(0.10, 0.50, vekt=1.0)
        assert abs(result - 0.50) < 0.0001
