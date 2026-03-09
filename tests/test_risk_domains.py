"""
Tests for the Risk Domain Architecture (AP2).
"""
import pytest
from risk_domains import DOMAIN_REGISTRY, get_domain
from risk_domains.base_domain import DomainRiskSummary, RiskDomain
from risk_domains.biological import BiologicalRiskDomain
from risk_domains.structural import StructuralRiskDomain
from risk_domains.environmental import EnvironmentalRiskDomain
from risk_domains.operational import OperationalRiskDomain


class TestDomainRegistry:
    def test_all_domains_registered(self):
        expected = {"biological", "structural", "environmental", "operational"}
        assert expected == set(DOMAIN_REGISTRY.keys())

    def test_get_domain_returns_correct_type(self):
        bio = get_domain("biological")
        assert isinstance(bio, BiologicalRiskDomain)

    def test_get_domain_unknown_raises(self):
        with pytest.raises(KeyError):
            get_domain("nonexistent_domain")

    def test_registry_values_are_risk_domains(self):
        for domain in DOMAIN_REGISTRY.values():
            assert isinstance(domain, RiskDomain)


class TestStructuralDomain:
    def test_returns_summaries(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        assert len(summaries) > 0

    def test_all_summaries_are_structural_prior(self):
        # Sprint 5: upgraded from "stub" to "structural_prior" model type
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.model_type == "structural_prior"
            assert s.domain == "structural"

    def test_summary_type(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=50_000_000)
        for s in summaries:
            assert isinstance(s, DomainRiskSummary)
            assert 0.0 <= s.event_probability <= 1.0
            assert s.expected_annual_loss_nok >= 0.0

    def test_zero_tiv_gives_zero_loss(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=0)
        for s in summaries:
            assert s.expected_annual_loss_nok == 0.0


class TestEnvironmentalDomain:
    def test_returns_summaries(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=80_000_000)
        assert len(summaries) > 0

    def test_domain_name(self):
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=10_000_000)
        for s in summaries:
            assert s.domain == "environmental"

    def test_all_summaries_are_environmental_prior(self):
        # Sprint 6: upgraded from "stub" to "environmental_prior" model type
        domain = EnvironmentalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.model_type == "environmental_prior"


class TestOperationalDomain:
    def test_returns_summaries(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=60_000_000)
        assert len(summaries) > 0

    def test_domain_name(self):
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=60_000_000)
        for s in summaries:
            assert s.domain == "operational"

    def test_all_summaries_are_operational_prior(self):
        # Sprint 6: upgraded from "stub" to "operational_prior" model type
        domain = OperationalRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        for s in summaries:
            assert s.model_type == "operational_prior"


class TestDomainRiskSummary:
    def test_total_expected_loss(self):
        domain = StructuralRiskDomain()
        summaries = domain.assess(site_tiv_nok=100_000_000)
        total = domain.total_expected_annual_loss(summaries)
        assert total == sum(s.expected_annual_loss_nok for s in summaries)
        assert total >= 0.0
