"""
tests/test_cage_technology.py — Cage pen technology model tests.

Tests:
  TestCageDomainMultipliers       (6)  — CAGE_DOMAIN_MULTIPLIERS constants
  TestCagePenConfig               (10) — dataclass construction / validation
  TestComputeLocalityMultipliers  (12) — biomass-weighted aggregation
  TestApplyCageMultipliers        (8)  — apply_cage_multipliers_to_domain_fractions
  TestBuildDomainBreakdownCages   (10) — integration with build_domain_loss_breakdown
  TestMonteCarloEngineCages       (6)  — MonteCarloEngine.cage_multipliers param

Total: 52 tests
"""

from __future__ import annotations

import pytest
import numpy as np

from models.cage_technology import (
    CAGE_DOMAIN_MULTIPLIERS,
    DOMAINS,
    VALID_CAGE_TYPES,
    CagePenConfig,
    cage_type_summary,
    compute_locality_domain_multipliers,
)
from models.domain_loss_breakdown import (
    DEFAULT_DOMAIN_FRACTIONS,
    _NON_BIO_DOMAIN_FRACTIONS,
    apply_cage_multipliers_to_domain_fractions,
    build_domain_loss_breakdown,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def open_net_cage():
    return CagePenConfig(cage_id="C01", cage_type="open_net", biomass_tonnes=500.0)


@pytest.fixture
def semi_closed_cage():
    return CagePenConfig(cage_id="C02", cage_type="semi_closed", biomass_tonnes=300.0)


@pytest.fixture
def fully_closed_cage():
    return CagePenConfig(cage_id="C03", cage_type="fully_closed", biomass_tonnes=200.0)


@pytest.fixture
def submerged_cage():
    return CagePenConfig(cage_id="C04", cage_type="submerged", biomass_tonnes=400.0)


@pytest.fixture
def mixed_locality(open_net_cage, semi_closed_cage):
    return [open_net_cage, semi_closed_cage]


@pytest.fixture
def annual_losses():
    rng = np.random.default_rng(42)
    return rng.exponential(10_000_000, size=(100, 5))


# ─────────────────────────────────────────────────────────────────────────────
# TestCageDomainMultipliers
# ─────────────────────────────────────────────────────────────────────────────

class TestCageDomainMultipliers:
    def test_all_cage_types_present(self):
        assert set(CAGE_DOMAIN_MULTIPLIERS.keys()) == {"open_net", "semi_closed", "fully_closed", "submerged"}

    def test_each_type_has_all_domains(self):
        for cage_type, mults in CAGE_DOMAIN_MULTIPLIERS.items():
            assert set(mults.keys()) == {"biological", "structural", "environmental", "operational"}, \
                f"{cage_type} missing a domain"

    def test_open_net_all_ones(self):
        for val in CAGE_DOMAIN_MULTIPLIERS["open_net"].values():
            assert val == 1.0

    def test_semi_closed_reduces_bio(self):
        assert CAGE_DOMAIN_MULTIPLIERS["semi_closed"]["biological"] < 1.0

    def test_fully_closed_lowest_bio(self):
        assert CAGE_DOMAIN_MULTIPLIERS["fully_closed"]["biological"] < \
               CAGE_DOMAIN_MULTIPLIERS["semi_closed"]["biological"]

    def test_fully_closed_highest_ops(self):
        ops = {ct: CAGE_DOMAIN_MULTIPLIERS[ct]["operational"] for ct in CAGE_DOMAIN_MULTIPLIERS}
        assert max(ops, key=ops.__getitem__) == "fully_closed"


# ─────────────────────────────────────────────────────────────────────────────
# TestCagePenConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestCagePenConfig:
    def test_valid_construction(self, open_net_cage):
        assert open_net_cage.cage_id == "C01"
        assert open_net_cage.cage_type == "open_net"
        assert open_net_cage.biomass_tonnes == 500.0

    def test_optional_fields_none(self, open_net_cage):
        assert open_net_cage.volume_m3 is None
        assert open_net_cage.installation_year is None

    def test_optional_fields_set(self):
        c = CagePenConfig("X", "semi_closed", 100.0, volume_m3=2000.0, installation_year=2020)
        assert c.volume_m3 == 2000.0
        assert c.installation_year == 2020

    def test_invalid_cage_type(self):
        with pytest.raises(ValueError, match="Unknown cage_type"):
            CagePenConfig("X", "underwater_hamster_wheel", 100.0)

    def test_zero_biomass_raises(self):
        with pytest.raises(ValueError, match="biomass_tonnes must be > 0"):
            CagePenConfig("X", "open_net", 0.0)

    def test_negative_biomass_raises(self):
        with pytest.raises(ValueError, match="biomass_tonnes must be > 0"):
            CagePenConfig("X", "open_net", -10.0)

    def test_domain_multipliers_property(self, open_net_cage):
        mults = open_net_cage.domain_multipliers
        assert set(mults.keys()) == set(DOMAINS)

    def test_to_dict_round_trip(self, semi_closed_cage):
        d = semi_closed_cage.to_dict()
        c2 = CagePenConfig.from_dict(d)
        assert c2.cage_id == semi_closed_cage.cage_id
        assert c2.cage_type == semi_closed_cage.cage_type
        assert c2.biomass_tonnes == semi_closed_cage.biomass_tonnes

    def test_from_dict_optional_fields(self):
        d = {"cage_id": "X", "cage_type": "submerged", "biomass_tonnes": 300.0}
        c = CagePenConfig.from_dict(d)
        assert c.volume_m3 is None

    def test_all_valid_types_accepted(self):
        for ct in VALID_CAGE_TYPES:
            c = CagePenConfig(f"id_{ct}", ct, 100.0)
            assert c.cage_type == ct


# ─────────────────────────────────────────────────────────────────────────────
# TestComputeLocalityMultipliers
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeLocalityMultipliers:
    def test_empty_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            compute_locality_domain_multipliers([])

    def test_single_open_net_returns_ones(self, open_net_cage):
        result = compute_locality_domain_multipliers([open_net_cage])
        for domain in DOMAINS:
            assert result[domain] == pytest.approx(1.0)

    def test_single_fully_closed(self, fully_closed_cage):
        result = compute_locality_domain_multipliers([fully_closed_cage])
        for domain in DOMAINS:
            assert result[domain] == pytest.approx(CAGE_DOMAIN_MULTIPLIERS["fully_closed"][domain])

    def test_equal_biomass_is_arithmetic_mean(self):
        c1 = CagePenConfig("A", "open_net", 500.0)
        c2 = CagePenConfig("B", "semi_closed", 500.0)
        result = compute_locality_domain_multipliers([c1, c2])
        for domain in DOMAINS:
            expected = (CAGE_DOMAIN_MULTIPLIERS["open_net"][domain]
                        + CAGE_DOMAIN_MULTIPLIERS["semi_closed"][domain]) / 2
            assert result[domain] == pytest.approx(expected)

    def test_biomass_weighting(self):
        # 75% open_net, 25% fully_closed
        c1 = CagePenConfig("A", "open_net",     750.0)
        c2 = CagePenConfig("B", "fully_closed", 250.0)
        result = compute_locality_domain_multipliers([c1, c2])
        for domain in DOMAINS:
            expected = (0.75 * CAGE_DOMAIN_MULTIPLIERS["open_net"][domain]
                        + 0.25 * CAGE_DOMAIN_MULTIPLIERS["fully_closed"][domain])
            assert result[domain] == pytest.approx(expected)

    def test_returns_all_domains(self, mixed_locality):
        result = compute_locality_domain_multipliers(mixed_locality)
        assert set(result.keys()) == set(DOMAINS)

    def test_all_values_positive(self, mixed_locality):
        result = compute_locality_domain_multipliers(mixed_locality)
        for v in result.values():
            assert v > 0

    def test_mixed_four_types(self):
        cages = [
            CagePenConfig("A", "open_net",     200.0),
            CagePenConfig("B", "semi_closed",  300.0),
            CagePenConfig("C", "fully_closed", 150.0),
            CagePenConfig("D", "submerged",    350.0),
        ]
        total = sum(c.biomass_tonnes for c in cages)
        result = compute_locality_domain_multipliers(cages)
        for domain in DOMAINS:
            expected = sum(
                c.biomass_tonnes / total * CAGE_DOMAIN_MULTIPLIERS[c.cage_type][domain]
                for c in cages
            )
            assert result[domain] == pytest.approx(expected)

    def test_cage_type_summary_keys(self):
        cages = [
            CagePenConfig("A", "open_net",    500.0),
            CagePenConfig("B", "semi_closed", 200.0),
            CagePenConfig("C", "semi_closed", 300.0),
        ]
        summary = cage_type_summary(cages)
        assert summary["open_net"] == pytest.approx(500.0)
        assert summary["semi_closed"] == pytest.approx(500.0)

    def test_cage_type_summary_single(self, fully_closed_cage):
        summary = cage_type_summary([fully_closed_cage])
        assert "fully_closed" in summary
        assert summary["fully_closed"] == pytest.approx(200.0)

    def test_zero_total_biomass_raises(self):
        """Biomass of 0 should have been rejected at CagePenConfig init."""
        with pytest.raises(ValueError):
            CagePenConfig("X", "open_net", 0.0)

    def test_result_type_is_dict(self, mixed_locality):
        result = compute_locality_domain_multipliers(mixed_locality)
        assert isinstance(result, dict)


# ─────────────────────────────────────────────────────────────────────────────
# TestApplyCageMultipliers
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyCageMultipliers:
    def test_all_ones_leaves_fractions_unchanged(self):
        mults = {d: 1.0 for d in DOMAINS}
        result = apply_cage_multipliers_to_domain_fractions(DEFAULT_DOMAIN_FRACTIONS, mults)
        for d, v in DEFAULT_DOMAIN_FRACTIONS.items():
            assert result[d] == pytest.approx(v)

    def test_result_sums_to_one(self):
        mults = {"biological": 0.5, "structural": 1.2, "environmental": 0.8, "operational": 1.1}
        result = apply_cage_multipliers_to_domain_fractions(DEFAULT_DOMAIN_FRACTIONS, mults)
        assert sum(result.values()) == pytest.approx(1.0)

    def test_reduces_bio_fraction(self):
        mults = {"biological": 0.5, "structural": 1.0, "environmental": 1.0, "operational": 1.0}
        base_bio = DEFAULT_DOMAIN_FRACTIONS["biological"]
        result = apply_cage_multipliers_to_domain_fractions(DEFAULT_DOMAIN_FRACTIONS, mults)
        # After renormalisation, bio should be < its base proportion
        assert result["biological"] < base_bio

    def test_non_bio_fractions_renormalise(self):
        mults = {"biological": 0.45, "structural": 1.2, "environmental": 0.6, "operational": 1.25}
        result = apply_cage_multipliers_to_domain_fractions(_NON_BIO_DOMAIN_FRACTIONS, mults)
        assert sum(result.values()) == pytest.approx(1.0)

    def test_missing_multiplier_defaults_to_one(self):
        partial_mults = {"biological": 0.7}
        result = apply_cage_multipliers_to_domain_fractions(DEFAULT_DOMAIN_FRACTIONS, partial_mults)
        assert sum(result.values()) == pytest.approx(1.0)

    def test_all_zero_multipliers_returns_fallback(self):
        """All zero multipliers — total is 0 → fallback to original fractions."""
        mults = {d: 0.0 for d in DOMAINS}
        result = apply_cage_multipliers_to_domain_fractions(DEFAULT_DOMAIN_FRACTIONS, mults)
        for d, v in DEFAULT_DOMAIN_FRACTIONS.items():
            assert result[d] == pytest.approx(v)

    def test_all_domains_in_result(self):
        mults = {d: 1.0 for d in DOMAINS}
        result = apply_cage_multipliers_to_domain_fractions(DEFAULT_DOMAIN_FRACTIONS, mults)
        assert set(result.keys()) == set(DEFAULT_DOMAIN_FRACTIONS.keys())

    def test_proportional_scaling(self):
        """Multiplying bio by 2× (others unchanged) should roughly double bio fraction after renorm."""
        mults = {"biological": 2.0, "structural": 1.0, "environmental": 1.0, "operational": 1.0}
        base_bio = DEFAULT_DOMAIN_FRACTIONS["biological"]
        other_sum = 1.0 - base_bio
        expected_bio_scaled = base_bio * 2.0
        expected_total = expected_bio_scaled + other_sum
        expected_bio_normed = expected_bio_scaled / expected_total
        result = apply_cage_multipliers_to_domain_fractions(DEFAULT_DOMAIN_FRACTIONS, mults)
        assert result["biological"] == pytest.approx(expected_bio_normed, rel=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# TestBuildDomainBreakdownCages
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildDomainBreakdownCages:
    def _make_cage_multipliers(self, cage_type: str):
        return dict(CAGE_DOMAIN_MULTIPLIERS[cage_type])

    def test_no_cage_multipliers_prior_only(self, annual_losses):
        dbd = build_domain_loss_breakdown(annual_losses)
        assert dbd.bio_modelled is False

    def test_with_open_net_multipliers_equals_baseline(self, annual_losses):
        """open_net all-ones → same total as no cage_multipliers."""
        mults = self._make_cage_multipliers("open_net")
        dbd_cage = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults)
        dbd_base = build_domain_loss_breakdown(annual_losses)
        # Totals should match (same fractions after all-1.0 scaling + renorm)
        np.testing.assert_allclose(dbd_cage.total(), dbd_base.total(), rtol=1e-10)

    def test_fully_closed_reduces_bio_share(self, annual_losses):
        mults_fc = self._make_cage_multipliers("fully_closed")
        mults_on = self._make_cage_multipliers("open_net")
        dbd_fc = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults_fc)
        dbd_on = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults_on)
        bio_fc = dbd_fc.domain_totals()["biological"].mean()
        bio_on = dbd_on.domain_totals()["biological"].mean()
        assert bio_fc < bio_on

    def test_total_preserved_with_cage_multipliers(self, annual_losses):
        mults = self._make_cage_multipliers("semi_closed")
        dbd = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults)
        np.testing.assert_allclose(dbd.total(), annual_losses, rtol=1e-10)

    def test_prior_only_bio_modelled_false(self, annual_losses):
        mults = self._make_cage_multipliers("semi_closed")
        dbd = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults)
        assert dbd.bio_modelled is False

    def test_bio_breakdown_path_bio_modelled_true(self, annual_losses):
        bio = {"hab": annual_losses * 0.3, "lice": annual_losses * 0.2}
        mults = self._make_cage_multipliers("fully_closed")
        dbd = build_domain_loss_breakdown(annual_losses, bio_breakdown=bio, cage_multipliers=mults)
        assert dbd.bio_modelled is True

    def test_bio_breakdown_bio_unchanged_with_cages(self, annual_losses):
        bio = {"hab": annual_losses * 0.3, "lice": annual_losses * 0.2}
        mults = self._make_cage_multipliers("submerged")
        dbd = build_domain_loss_breakdown(annual_losses, bio_breakdown=bio, cage_multipliers=mults)
        np.testing.assert_allclose(dbd.biological["hab"], annual_losses * 0.3)

    def test_submerged_reduces_env_share(self, annual_losses):
        mults_sub = self._make_cage_multipliers("submerged")
        mults_on = self._make_cage_multipliers("open_net")
        dbd_sub = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults_sub)
        dbd_on = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults_on)
        env_sub = dbd_sub.domain_totals()["environmental"].mean()
        env_on = dbd_on.domain_totals()["environmental"].mean()
        assert env_sub < env_on

    def test_domain_totals_all_present(self, annual_losses):
        mults = self._make_cage_multipliers("semi_closed")
        dbd = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults)
        totals = dbd.domain_totals()
        assert set(totals.keys()) == {"biological", "structural", "environmental", "operational"}

    def test_subtypes_all_nonneg(self, annual_losses):
        mults = self._make_cage_multipliers("fully_closed")
        dbd = build_domain_loss_breakdown(annual_losses, cage_multipliers=mults)
        for arr in dbd._all_arrays():
            assert (arr >= 0).all()


# ─────────────────────────────────────────────────────────────────────────────
# TestMonteCarloEngineCages
# ─────────────────────────────────────────────────────────────────────────────

class TestMonteCarloEngineCages:
    """Integration test: MonteCarloEngine.cage_multipliers flows through to domain breakdown."""

    def _make_engine(self, cage_multipliers=None):
        from models.monte_carlo import MonteCarloEngine
        from data.input_schema import validate_input
        import json
        from pathlib import Path
        raw = json.loads((Path(__file__).resolve().parents[1] / "data" / "sample_input.json").read_text())
        op = validate_input(raw)
        return MonteCarloEngine(op, n_simulations=500, seed=0, cage_multipliers=cage_multipliers)

    def test_no_cage_multipliers_no_domain_breakdown(self):
        engine = self._make_engine()
        sim = engine.run()
        # Without cage_multipliers AND without domain_correlation, no breakdown
        assert sim.domain_loss_breakdown is None

    def test_with_cage_multipliers_produces_domain_breakdown(self):
        mults = {d: 1.0 for d in DOMAINS}
        engine = self._make_engine(cage_multipliers=mults)
        sim = engine.run()
        assert sim.domain_loss_breakdown is not None

    def test_cage_multipliers_stored(self):
        mults = dict(CAGE_DOMAIN_MULTIPLIERS["semi_closed"])
        engine = self._make_engine(cage_multipliers=mults)
        assert engine.cage_multipliers == mults

    def test_fully_closed_bio_loss_lower(self):
        mults_fc = dict(CAGE_DOMAIN_MULTIPLIERS["fully_closed"])
        mults_on = dict(CAGE_DOMAIN_MULTIPLIERS["open_net"])
        sim_fc = self._make_engine(cage_multipliers=mults_fc).run()
        sim_on = self._make_engine(cage_multipliers=mults_on).run()
        bio_fc = sim_fc.domain_loss_breakdown.domain_totals()["biological"].mean()
        bio_on = sim_on.domain_loss_breakdown.domain_totals()["biological"].mean()
        assert bio_fc < bio_on

    def test_domain_breakdown_total_matches_sim(self):
        mults = dict(CAGE_DOMAIN_MULTIPLIERS["semi_closed"])
        sim = self._make_engine(cage_multipliers=mults).run()
        dbd_total = sim.domain_loss_breakdown.total()
        np.testing.assert_allclose(dbd_total, sim.annual_losses, rtol=1e-10)

    def test_none_cage_multipliers_no_effect(self):
        engine = self._make_engine(cage_multipliers=None)
        assert engine.cage_multipliers is None
