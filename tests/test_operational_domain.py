"""
Tests for Sprint 6 – OperationalRiskDomain (feasibility-grade operational prior model).

Covers:
* Sub-type names match domain_loss_breakdown.py DOMAIN_SUBTYPES["operational"]
* EAL computation: min(1.0, base_prob × operational_risk_factor) × loss_fraction × TIV
* Operational risk factor clamping and UserWarning
* model_type = "operational_prior", confidence = 0.15, data_quality = "PRIOR_ONLY"
* DomainRiskSummary fields populated correctly
* Zero TIV returns zero monetary values but correct probabilities
* Metadata fields present
"""

import warnings

import pytest

from risk_domains.operational import OperationalRiskDomain, OPERATIONAL_RISK_PROFILES
from risk_domains.base_domain import DomainRiskSummary
from models.domain_loss_breakdown import DOMAIN_SUBTYPES


# ── Constants / sub-type name alignment ───────────────────────────────────────

class TestSubTypeNames:
    def test_profiles_match_domain_loss_breakdown_subtypes(self):
        """Sub-type names in OPERATIONAL_RISK_PROFILES must match DOMAIN_SUBTYPES["operational"]."""
        expected = set(DOMAIN_SUBTYPES["operational"])
        actual = set(OPERATIONAL_RISK_PROFILES.keys())
        assert actual == expected, (
            f"Mismatch between risk profiles {actual} and domain subtypes {expected}"
        )

    def test_four_sub_types(self):
        assert len(OPERATIONAL_RISK_PROFILES) == 4

    def test_human_error_present(self):
        assert "human_error" in OPERATIONAL_RISK_PROFILES

    def test_procedure_failure_present(self):
        assert "procedure_failure" in OPERATIONAL_RISK_PROFILES

    def test_equipment_present(self):
        assert "equipment" in OPERATIONAL_RISK_PROFILES

    def test_incident_present(self):
        assert "incident" in OPERATIONAL_RISK_PROFILES

    def test_no_legacy_equipment_malfunction(self):
        """Bug fix: old sub-type name 'equipment_malfunction' must not appear."""
        assert "equipment_malfunction" not in OPERATIONAL_RISK_PROFILES

    def test_no_legacy_incident_response_gap(self):
        """Bug fix: old sub-type name 'incident_response_gap' must not appear."""
        assert "incident_response_gap" not in OPERATIONAL_RISK_PROFILES


# ── OperationalRiskDomain construction ───────────────────────────────────────

class TestOperationalRiskDomainInit:
    def test_default_risk_factor(self):
        domain = OperationalRiskDomain()
        assert domain.operational_risk_factor == 1.0

    def test_custom_risk_factor_in_range(self):
        domain = OperationalRiskDomain(operational_risk_factor=1.5)
        assert domain.operational_risk_factor == pytest.approx(1.5)

    def test_risk_factor_clipped_to_min(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = OperationalRiskDomain(operational_risk_factor=0.1)
        assert domain.operational_risk_factor == pytest.approx(0.50)
        assert any(issubclass(w.category, UserWarning) for w in caught)

    def test_risk_factor_clipped_to_max(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = OperationalRiskDomain(operational_risk_factor=3.0)
        assert domain.operational_risk_factor == pytest.approx(2.0)
        assert any(issubclass(w.category, UserWarning) for w in caught)

    def test_boundary_min_no_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = OperationalRiskDomain(operational_risk_factor=0.50)
        assert domain.operational_risk_factor == pytest.approx(0.50)
        assert not any(issubclass(w.category, UserWarning) for w in caught)

    def test_boundary_max_no_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            domain = OperationalRiskDomain(operational_risk_factor=2.0)
        assert domain.operational_risk_factor == pytest.approx(2.0)
        assert not any(issubclass(w.category, UserWarning) for w in caught)

    def test_domain_name(self):
        assert OperationalRiskDomain.domain_name == "operational"

    def test_no_args_callable(self):
        """Backward-compat: callable with no arguments."""
        domain = OperationalRiskDomain()
        assert domain is not None


# ── assess() return value ─────────────────────────────────────────────────────

class TestAssessReturn:
    def test_returns_list_of_domain_risk_summaries(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        assert isinstance(summaries, list)
        assert all(isinstance(s, DomainRiskSummary) for s in summaries)

    def test_returns_four_summaries(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        assert len(summaries) == 4

    def test_sub_type_names_in_output(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        returned_sub_types = {s.sub_type for s in summaries}
        expected = set(DOMAIN_SUBTYPES["operational"])
        assert returned_sub_types == expected

    def test_domain_field_is_operational(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.domain == "operational"


# ── model quality metadata ────────────────────────────────────────────────────

class TestModelQualityMetadata:
    def test_model_type_operational_prior(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.model_type == "operational_prior", (
                f"{s.sub_type}: expected 'operational_prior', got '{s.model_type}'"
            )

    def test_not_stub(self):
        """Explicit regression: must no longer return model_type='stub'."""
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.model_type != "stub"

    def test_confidence_015(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert abs(s.confidence - 0.15) < 1e-9, (
                f"{s.sub_type}: expected confidence=0.15, got {s.confidence}"
            )

    def test_data_quality_prior_only(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.data_quality == "PRIOR_ONLY"

    def test_metadata_has_description(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "description" in s.metadata
            assert len(s.metadata["description"]) > 10

    def test_metadata_has_base_probability(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "base_probability" in s.metadata
            assert 0 < s.metadata["base_probability"] <= 1.0

    def test_metadata_has_operational_risk_factor(self):
        rf = 1.3
        domain = OperationalRiskDomain(operational_risk_factor=rf)
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert s.metadata["operational_risk_factor"] == pytest.approx(rf)

    def test_metadata_has_loss_fraction_of_tiv(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert "loss_fraction_of_tiv" in s.metadata
            assert 0 < s.metadata["loss_fraction_of_tiv"] <= 1.0


# ── EAL computation ───────────────────────────────────────────────────────────

class TestEALComputation:
    def test_eal_formula_default_factor(self):
        """EAL = base_prob × 1.0 × loss_fraction × TIV for default factor."""
        domain = OperationalRiskDomain()
        tiv = 200_000_000
        summaries = domain.assess(site_tiv_nok=tiv)
        for s in summaries:
            profile = OPERATIONAL_RISK_PROFILES[s.sub_type]
            expected_eal = (
                profile["annual_probability"] * 1.0
                * profile["loss_fraction_of_tiv"] * tiv
            )
            assert abs(s.expected_annual_loss_nok - expected_eal) < 1.0, (
                f"{s.sub_type}: EAL={s.expected_annual_loss_nok:.2f} ≠ expected {expected_eal:.2f}"
            )

    def test_eal_scales_with_tiv(self):
        domain = OperationalRiskDomain()
        summaries_100m = domain.assess(site_tiv_nok=100_000_000)
        summaries_200m = domain.assess(site_tiv_nok=200_000_000)
        for s1, s2 in zip(summaries_100m, summaries_200m):
            ratio = s2.expected_annual_loss_nok / s1.expected_annual_loss_nok
            assert abs(ratio - 2.0) < 1e-6, (
                f"{s1.sub_type}: EAL ratio {ratio:.4f} ≠ 2.0"
            )

    def test_eal_scales_with_risk_factor(self):
        tiv = 100_000_000
        domain_1x = OperationalRiskDomain(operational_risk_factor=1.0)
        domain_2x = OperationalRiskDomain(operational_risk_factor=2.0)
        s1 = domain_1x.assess(site_tiv_nok=tiv)
        s2 = domain_2x.assess(site_tiv_nok=tiv)
        for a, b in zip(s1, s2):
            ratio = b.expected_annual_loss_nok / a.expected_annual_loss_nok
            assert abs(ratio - 2.0) < 1e-6, (
                f"{a.sub_type}: risk factor ratio {ratio:.4f} ≠ 2.0"
            )

    def test_lower_factor_reduces_eal(self):
        """Factor < 1.0 = better management = lower EAL."""
        tiv = 100_000_000
        domain_low = OperationalRiskDomain(operational_risk_factor=0.5)
        domain_high = OperationalRiskDomain(operational_risk_factor=1.5)
        s_low = domain_low.assess(site_tiv_nok=tiv)
        s_high = domain_high.assess(site_tiv_nok=tiv)
        for a, b in zip(s_low, s_high):
            assert a.expected_annual_loss_nok < b.expected_annual_loss_nok, (
                f"{a.sub_type}: low-risk factor should have lower EAL"
            )

    def test_zero_tiv_gives_zero_eal(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=0.0)
        for s in summaries:
            assert s.expected_annual_loss_nok == 0.0

    def test_zero_tiv_still_has_probabilities(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=0.0)
        for s in summaries:
            assert s.event_probability > 0.0

    def test_adjusted_probability_capped_at_one(self):
        """With max risk factor, probabilities must stay ≤ 1.0."""
        domain = OperationalRiskDomain(operational_risk_factor=2.0)
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.event_probability <= 1.0 + 1e-9

    def test_human_error_eal_spot_check(self):
        """Spot-check human_error at known profile values with default factor."""
        tiv = 100_000_000
        domain = OperationalRiskDomain(operational_risk_factor=1.0)
        summaries = domain.assess(site_tiv_nok=tiv)
        he = next(s for s in summaries if s.sub_type == "human_error")
        # annual_probability=0.12, factor=1.0 → adjusted=0.12
        # loss_fraction=0.03 → EAL = 0.12 × 0.03 × 100M = 360_000
        assert abs(he.expected_annual_loss_nok - 360_000) < 1.0

    def test_incident_eal_spot_check(self):
        """Spot-check incident at known profile values with factor=1.5."""
        tiv = 100_000_000
        domain = OperationalRiskDomain(operational_risk_factor=1.5)
        summaries = domain.assess(site_tiv_nok=tiv)
        inc = next(s for s in summaries if s.sub_type == "incident")
        # annual_probability=0.05, factor=1.5 → adjusted=0.075
        # loss_fraction=0.05 → EAL = 0.075 × 0.05 × 100M = 375_000
        assert abs(inc.expected_annual_loss_nok - 375_000) < 1.0
