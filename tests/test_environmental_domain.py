"""
Tests for Sprint 6 – EnvironmentalRiskDomain (feasibility-grade environmental prior model).

Covers:
* Sub-type names match domain_loss_breakdown.py DOMAIN_SUBTYPES["environmental"]
* EAL computation: min(1.0, base_prob × site_exposure_factor) × loss_fraction × TIV
* Site exposure factor clamping and UserWarning
* model_type = "environmental_prior", confidence = 0.15, data_quality = "PRIOR_ONLY"
* DomainRiskSummary fields populated correctly
* Zero TIV returns zero monetary values but correct probabilities
* Metadata fields present
"""

import warnings

import pytest

from risk_domains.environmental import EnvironmentalRiskDomain, ENVIRONMENTAL_RISK_PROFILES
from risk_domains.base_domain import DomainRiskSummary
from models.domain_loss_breakdown import DOMAIN_SUBTYPES


# ── Constants / sub-type name alignment ───────────────────────────────────────

class TestSubTypeNames:
    def test_profiles_match_domain_loss_breakdown_subtypes(self):
        """Sub-type names in ENVIRONMENTAL_RISK_PROFILES must match DOMAIN_SUBTYPES["environmental"]."""
        expected = set(DOMAIN_SUBTYPES["environmental"])
        actual = set(ENVIRONMENTAL_RISK_PROFILES.keys())
        assert actual == expected, (
            f"Mismatch between risk profiles {actual} and domain subtypes {expected}"
        )

    def test_four_sub_types(self):
        assert len(ENVIRONMENTAL_RISK_PROFILES) == 4

    def test_oxygen_stress_present(self):
        assert "oxygen_stress" in ENVIRONMENTAL_RISK_PROFILES

    def test_temperature_extreme_present(self):
        assert "temperature_extreme" in ENVIRONMENTAL_RISK_PROFILES

    def test_current_storm_present(self):
        assert "current_storm" in ENVIRONMENTAL_RISK_PROFILES

    def test_ice_present(self):
        assert "ice" in ENVIRONMENTAL_RISK_PROFILES

    def test_no_legacy_strong_current_damage(self):
        """Bug fix: old sub-type name 'strong_current_damage' must not appear."""
        assert "strong_current_damage" not in ENVIRONMENTAL_RISK_PROFILES

    def test_no_legacy_storm_wave_damage(self):
        """Bug fix: old sub-type name 'storm_wave_damage' must not appear."""
        assert "storm_wave_damage" not in ENVIRONMENTAL_RISK_PROFILES


# ── EnvironmentalRiskDomain construction ──────────────────────────────────────

class TestEnvironmentalRiskDomainInit:
    def test_default_exposure_factor(self):
        domain = EnvironmentalRiskDomain()
        assert domain.site_exposure_factor == 1.0

    def test_custom_exposure_factor_in_range(self):
        domain = EnvironmentalRiskDomain(site_exposure_factor=1.5)
        assert domain.site_exposure_factor == pytest.approx(1.5)

    def test_exposure_factor_clipped_to_min(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = EnvironmentalRiskDomain(site_exposure_factor=0.1)
        assert domain.site_exposure_factor == pytest.approx(0.50)
        assert any(issubclass(w.category, UserWarning) for w in caught)

    def test_exposure_factor_clipped_to_max(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = EnvironmentalRiskDomain(site_exposure_factor=3.0)
        assert domain.site_exposure_factor == pytest.approx(2.0)
        assert any(issubclass(w.category, UserWarning) for w in caught)

    def test_boundary_min_no_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = EnvironmentalRiskDomain(site_exposure_factor=0.50)
        assert domain.site_exposure_factor == pytest.approx(0.50)
        assert not any(issubclass(w.category, UserWarning) for w in caught)

    def test_boundary_max_no_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = EnvironmentalRiskDomain(site_exposure_factor=2.0)
        assert domain.site_exposure_factor == pytest.approx(2.0)
        assert not any(issubclass(w.category, UserWarning) for w in caught)

    def test_domain_name(self):
        assert EnvironmentalRiskDomain.domain_name == "environmental"

    def test_no_args_callable(self):
        """Backward-compat: callable with no arguments."""
        domain = EnvironmentalRiskDomain()
        assert domain is not None


# ── assess() return value ─────────────────────────────────────────────────────

class TestAssessReturn:
    def test_returns_list_of_domain_risk_summaries(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        assert isinstance(summaries, list)
        assert all(isinstance(s, DomainRiskSummary) for s in summaries)

    def test_returns_four_summaries(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        assert len(summaries) == 4

    def test_sub_type_names_in_output(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        returned_sub_types = {s.sub_type for s in summaries}
        expected = set(DOMAIN_SUBTYPES["environmental"])
        assert returned_sub_types == expected

    def test_domain_field_is_environmental(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.domain == "environmental"


# ── model quality metadata ────────────────────────────────────────────────────

class TestModelQualityMetadata:
    def test_model_type_environmental_prior(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.model_type == "environmental_prior", (
                f"{s.sub_type}: expected 'environmental_prior', got '{s.model_type}'"
            )

    def test_not_stub(self):
        """Explicit regression: must no longer return model_type='stub'."""
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.model_type != "stub"

    def test_confidence_015(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert abs(s.confidence - 0.15) < 1e-9, (
                f"{s.sub_type}: expected confidence=0.15, got {s.confidence}"
            )

    def test_data_quality_prior_only(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.data_quality == "PRIOR_ONLY"

    def test_metadata_has_description(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "description" in s.metadata
            assert len(s.metadata["description"]) > 10

    def test_metadata_has_base_probability(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "base_probability" in s.metadata
            assert 0 < s.metadata["base_probability"] <= 1.0

    def test_metadata_has_site_exposure_factor(self):
        ef = 1.4
        domain = EnvironmentalRiskDomain(site_exposure_factor=ef)
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.metadata["site_exposure_factor"] == pytest.approx(ef)

    def test_metadata_has_loss_fraction_of_tiv(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "loss_fraction_of_tiv" in s.metadata
            assert 0 < s.metadata["loss_fraction_of_tiv"] <= 1.0


# ── EAL computation ───────────────────────────────────────────────────────────

class TestEALComputation:
    def test_eal_formula_default_exposure(self):
        """EAL = base_prob × 1.0 × loss_fraction × TIV for default exposure."""
        domain = EnvironmentalRiskDomain()
        tiv = 200_000_000
        summaries = domain.assess(site_tiv_nok=tiv)
        for s in summaries:
            profile = ENVIRONMENTAL_RISK_PROFILES[s.sub_type]
            expected_eal = (
                profile["annual_probability"] * 1.0
                * profile["loss_fraction_of_tiv"] * tiv
            )
            assert abs(s.expected_annual_loss_nok - expected_eal) < 1.0, (
                f"{s.sub_type}: EAL={s.expected_annual_loss_nok:.2f} ≠ expected {expected_eal:.2f}"
            )

    def test_eal_scales_with_tiv(self):
        domain = EnvironmentalRiskDomain()
        summaries_100m = domain.assess(site_tiv_nok=100_000_000)
        summaries_200m = domain.assess(site_tiv_nok=200_000_000)
        for s1, s2 in zip(summaries_100m, summaries_200m):
            ratio = s2.expected_annual_loss_nok / s1.expected_annual_loss_nok
            assert abs(ratio - 2.0) < 1e-6, (
                f"{s1.sub_type}: EAL ratio {ratio:.4f} ≠ 2.0"
            )

    def test_eal_scales_with_exposure_factor(self):
        tiv = 100_000_000
        domain_1x = EnvironmentalRiskDomain(site_exposure_factor=1.0)
        domain_2x = EnvironmentalRiskDomain(site_exposure_factor=2.0)
        s1 = domain_1x.assess(site_tiv_nok=tiv)
        s2 = domain_2x.assess(site_tiv_nok=tiv)
        for a, b in zip(s1, s2):
            ratio = b.expected_annual_loss_nok / a.expected_annual_loss_nok
            assert abs(ratio - 2.0) < 1e-6, (
                f"{a.sub_type}: exposure factor ratio {ratio:.4f} ≠ 2.0"
            )

    def test_zero_tiv_gives_zero_eal(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=0.0)
        for s in summaries:
            assert s.expected_annual_loss_nok == 0.0

    def test_zero_tiv_still_has_probabilities(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=0.0)
        for s in summaries:
            assert s.event_probability > 0.0

    def test_adjusted_probability_capped_at_one(self):
        """With max exposure factor, probabilities must stay ≤ 1.0."""
        domain = EnvironmentalRiskDomain(site_exposure_factor=2.0)
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.event_probability <= 1.0 + 1e-9

    def test_oxygen_stress_eal_spot_check(self):
        """Spot-check oxygen_stress at known profile values with default exposure."""
        tiv = 100_000_000
        domain = EnvironmentalRiskDomain(site_exposure_factor=1.0)
        summaries = domain.assess(site_tiv_nok=tiv)
        os_ = next(s for s in summaries if s.sub_type == "oxygen_stress")
        # annual_probability=0.10, exposure=1.0 → adjusted=0.10
        # loss_fraction=0.05 → EAL = 0.10 × 0.05 × 100M = 500_000
        assert abs(os_.expected_annual_loss_nok - 500_000) < 1.0

    def test_current_storm_eal_spot_check(self):
        """Spot-check current_storm at known profile values with exposure=1.5."""
        tiv = 100_000_000
        domain = EnvironmentalRiskDomain(site_exposure_factor=1.5)
        summaries = domain.assess(site_tiv_nok=tiv)
        cs = next(s for s in summaries if s.sub_type == "current_storm")
        # annual_probability=0.06, exposure=1.5 → adjusted=0.09
        # loss_fraction=0.07 → EAL = 0.09 × 0.07 × 100M = 630_000
        assert abs(cs.expected_annual_loss_nok - 630_000) < 1.0
