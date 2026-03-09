"""
Tests for Sprint 5 – StructuralRiskDomain (feasibility-grade structural prior model).

Covers:
* Sub-type names match domain_loss_breakdown.py DOMAIN_SUBTYPES
* EAL computation: probability × exposure_factor × loss_fraction × TIV
* Site exposure factor clamping and UserWarning
* model_type = "structural_prior", confidence = 0.15, data_quality = "PRIOR_ONLY"
* DomainRiskSummary fields populated correctly
* Zero TIV returns zero monetary values but correct probabilities
* Metadata fields present
"""

import warnings

import pytest

from risk_domains.structural import StructuralRiskDomain, STRUCTURAL_RISK_PROFILES
from risk_domains.base_domain import DomainRiskSummary
from models.domain_loss_breakdown import DOMAIN_SUBTYPES


# ── Constants / sub-type name alignment ───────────────────────────────────────

class TestSubTypeNames:
    def test_profiles_match_domain_loss_breakdown_subtypes(self):
        """Sub-type names in STRUCTURAL_RISK_PROFILES must match DOMAIN_SUBTYPES["structural"]."""
        expected = set(DOMAIN_SUBTYPES["structural"])
        actual = set(STRUCTURAL_RISK_PROFILES.keys())
        assert actual == expected, (
            f"Mismatch between risk profiles {actual} and domain subtypes {expected}"
        )

    def test_four_sub_types(self):
        assert len(STRUCTURAL_RISK_PROFILES) == 4

    def test_required_sub_types_present(self):
        for st in ("mooring_failure", "net_integrity", "cage_structural", "feed_system"):
            assert st in STRUCTURAL_RISK_PROFILES, f"{st} missing from STRUCTURAL_RISK_PROFILES"


# ── StructuralRiskDomain construction ────────────────────────────────────────

class TestStructuralRiskDomainInit:
    def test_default_exposure_factor(self):
        domain = StructuralRiskDomain()
        assert domain.site_exposure_factor == 1.0

    def test_custom_exposure_factor_in_range(self):
        domain = StructuralRiskDomain(site_exposure_factor=1.5)
        assert domain.site_exposure_factor == 1.5

    def test_exposure_factor_clipped_to_min(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = StructuralRiskDomain(site_exposure_factor=0.3)
        assert domain.site_exposure_factor == pytest.approx(0.60)
        assert any(issubclass(w.category, UserWarning) for w in caught)

    def test_exposure_factor_clipped_to_max(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = StructuralRiskDomain(site_exposure_factor=3.0)
        assert domain.site_exposure_factor == pytest.approx(2.0)
        assert any(issubclass(w.category, UserWarning) for w in caught)

    def test_boundary_min_no_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = StructuralRiskDomain(site_exposure_factor=0.6)
        assert domain.site_exposure_factor == pytest.approx(0.60)
        assert not any(issubclass(w.category, UserWarning) for w in caught)

    def test_boundary_max_no_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = StructuralRiskDomain(site_exposure_factor=2.0)
        assert domain.site_exposure_factor == pytest.approx(2.0)
        assert not any(issubclass(w.category, UserWarning) for w in caught)

    def test_domain_name(self):
        assert StructuralRiskDomain.domain_name == "structural"


# ── assess() return value ─────────────────────────────────────────────────────

class TestAssessReturn:
    def test_returns_list_of_domain_risk_summaries(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        assert isinstance(summaries, list)
        assert all(isinstance(s, DomainRiskSummary) for s in summaries)

    def test_returns_four_summaries(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        assert len(summaries) == 4

    def test_sub_type_names_in_output(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        returned_sub_types = {s.sub_type for s in summaries}
        expected = set(DOMAIN_SUBTYPES["structural"])
        assert returned_sub_types == expected

    def test_domain_field_is_structural(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.domain == "structural"


# ── model quality metadata ────────────────────────────────────────────────────

class TestModelQualityMetadata:
    def test_model_type_structural_prior(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.model_type == "structural_prior", (
                f"{s.sub_type}: expected 'structural_prior', got '{s.model_type}'"
            )

    def test_confidence_015(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert abs(s.confidence - 0.15) < 1e-9, (
                f"{s.sub_type}: expected confidence=0.15, got {s.confidence}"
            )

    def test_data_quality_prior_only(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.data_quality == "PRIOR_ONLY"

    def test_metadata_has_description(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "description" in s.metadata
            assert len(s.metadata["description"]) > 10

    def test_metadata_has_base_probability(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "base_probability" in s.metadata
            assert 0 < s.metadata["base_probability"] <= 1.0

    def test_metadata_has_site_exposure_factor(self):
        ef = 1.3
        domain = StructuralRiskDomain(site_exposure_factor=ef)
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.metadata["site_exposure_factor"] == pytest.approx(ef)

    def test_metadata_has_loss_fraction_of_tiv(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "loss_fraction_of_tiv" in s.metadata
            assert 0 < s.metadata["loss_fraction_of_tiv"] <= 1.0


# ── EAL computation ───────────────────────────────────────────────────────────

class TestEALComputation:
    def test_eal_formula_default_exposure(self):
        """EAL = base_prob × 1.0 × loss_fraction × TIV for default exposure."""
        domain = StructuralRiskDomain()
        tiv = 200_000_000
        summaries = domain.assess(site_tiv_nok=tiv)
        for s in summaries:
            profile = STRUCTURAL_RISK_PROFILES[s.sub_type]
            expected_eal = (
                profile["annual_probability"] * 1.0
                * profile["loss_fraction_of_tiv"] * tiv
            )
            assert abs(s.expected_annual_loss_nok - expected_eal) < 1.0, (
                f"{s.sub_type}: EAL={s.expected_annual_loss_nok:.2f} ≠ expected {expected_eal:.2f}"
            )

    def test_eal_scales_with_tiv(self):
        domain = StructuralRiskDomain()
        summaries_100m = domain.assess(site_tiv_nok=100_000_000)
        summaries_200m = domain.assess(site_tiv_nok=200_000_000)
        for s1, s2 in zip(summaries_100m, summaries_200m):
            ratio = s2.expected_annual_loss_nok / s1.expected_annual_loss_nok
            assert abs(ratio - 2.0) < 1e-6, (
                f"{s1.sub_type}: EAL ratio {ratio:.4f} ≠ 2.0"
            )

    def test_eal_scales_with_exposure_factor(self):
        tiv = 100_000_000
        domain_1x = StructuralRiskDomain(site_exposure_factor=1.0)
        domain_2x = StructuralRiskDomain(site_exposure_factor=2.0)
        s1 = domain_1x.assess(site_tiv_nok=tiv)
        s2 = domain_2x.assess(site_tiv_nok=tiv)
        for a, b in zip(s1, s2):
            ratio = b.expected_annual_loss_nok / a.expected_annual_loss_nok
            assert abs(ratio - 2.0) < 1e-6, (
                f"{a.sub_type}: exposure factor ratio {ratio:.4f} ≠ 2.0"
            )

    def test_zero_tiv_gives_zero_eal(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=0.0)
        for s in summaries:
            assert s.expected_annual_loss_nok == 0.0

    def test_zero_tiv_still_has_probabilities(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=0.0)
        for s in summaries:
            assert s.event_probability > 0.0

    def test_adjusted_probability_capped_at_one(self):
        """With max exposure factor, probabilities must stay ≤ 1.0."""
        domain = StructuralRiskDomain(site_exposure_factor=2.0)
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.event_probability <= 1.0 + 1e-9

    def test_mooring_failure_eal_formula(self):
        """Spot-check mooring_failure at known profile values."""
        tiv = 100_000_000
        domain = StructuralRiskDomain(site_exposure_factor=1.5)
        summaries = domain.assess(site_tiv_nok=tiv)
        mf = next(s for s in summaries if s.sub_type == "mooring_failure")
        # annual_probability=0.05, exposure=1.5 → adjusted=0.075
        # loss_fraction=0.12 → EAL = 0.075 × 0.12 × 100M = 900_000
        assert abs(mf.expected_annual_loss_nok - 900_000) < 1.0


# ── Probability ordering ──────────────────────────────────────────────────────

class TestProbabilityOrdering:
    def test_net_integrity_highest_probability(self):
        """net_integrity has the highest base probability (0.10)."""
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        probs = {s.sub_type: s.event_probability for s in summaries}
        assert probs["net_integrity"] == max(probs.values())

    def test_cage_structural_lowest_probability(self):
        """cage_structural has the lowest base probability (0.04)."""
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        probs = {s.sub_type: s.event_probability for s in summaries}
        assert probs["cage_structural"] == min(probs.values())
