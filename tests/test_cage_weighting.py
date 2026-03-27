"""
tests/test_cage_weighting.py — Advanced cage weighting engine tests.

Tests:
  TestConfigIntegrity                 (4)  — DOMAIN_COMPONENT_WEIGHTS sums
  TestCageHasAdvancedData             (8)  — trigger detection logic
  TestRawComponentDerivation          (10) — _derive_raw_components
  TestMaxNormalise                    (5)  — normalisation helper
  TestBackwardCompatibility           (6)  — biomass-only path is exact
  TestAdvancedWeightingFormula        (10) — formula correctness
  TestScenarioA_ValueWeighting        (5)  — higher value → more consequence weight
  TestScenarioB_SPOFandClosed         (5)  — SPOF closed cage → structural/ops weight
  TestScenarioC_SubmergedCriticality  (5)  — submerged criticality drives struct/ops
  TestScenarioD_BackwardCompat        (4)  — old inputs → unchanged results
  TestValidation                      (8)  — CagePenConfig validation for new fields
  TestDomainWeightNormalization       (6)  — per-domain weights sum to 1.0
  TestEdgeCases                       (6)  — single cage, all same type, SPOF+value

Total: 82 tests
"""

from __future__ import annotations

import pytest
import numpy as np

from models.cage_technology import (
    CAGE_DOMAIN_MULTIPLIERS,
    DOMAINS,
    CagePenConfig,
    compute_locality_domain_multipliers,
)
from models.cage_weighting import (
    AdvancedWeightingResult,
    CageWeightDetail,
    _cage_has_advanced_data,
    _derive_raw_components,
    _locality_has_advanced_data,
    _max_normalise,
    compute_locality_domain_multipliers_advanced,
)
from config.cage_weighting import (
    CAGE_TYPE_DEFAULT_SCORES,
    DOMAIN_COMPONENT_WEIGHTS,
    FAILURE_MODE_CONSEQUENCE_MULTIPLIER,
    REDUNDANCY_CRITICALITY_SCALE,
    SPOF_CRITICALITY_MULTIPLIER,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def open_net():
    return CagePenConfig("ON1", "open_net", 500.0)


@pytest.fixture
def open_net_b():
    return CagePenConfig("ON2", "open_net", 300.0)


@pytest.fixture
def semi_closed():
    return CagePenConfig("SC1", "semi_closed", 400.0)


@pytest.fixture
def fully_closed():
    return CagePenConfig("FC1", "fully_closed", 200.0)


@pytest.fixture
def submerged():
    return CagePenConfig("SB1", "submerged", 350.0)


@pytest.fixture
def cage_with_value():
    return CagePenConfig("V1", "open_net", 500.0, biomass_value_nok=40_000_000)


@pytest.fixture
def cage_spof():
    return CagePenConfig(
        "SP1", "fully_closed", 200.0,
        biomass_value_nok=20_000_000,
        single_point_of_failure=True,
        structural_criticality_score=0.80,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TestConfigIntegrity
# ─────────────────────────────────────────────────────────────────────────────

class TestConfigIntegrity:
    def test_all_domains_present(self):
        assert set(DOMAIN_COMPONENT_WEIGHTS.keys()) == set(DOMAINS)

    def test_each_domain_has_five_components(self):
        for domain, weights in DOMAIN_COMPONENT_WEIGHTS.items():
            assert set(weights.keys()) == {"biomass", "value", "consequence", "complexity", "criticality"}, \
                f"{domain} missing a component"

    def test_each_domain_sums_to_one(self):
        for domain, weights in DOMAIN_COMPONENT_WEIGHTS.items():
            assert sum(weights.values()) == pytest.approx(1.0, abs=1e-9), \
                f"{domain} weights sum to {sum(weights.values())}"

    def test_cage_type_defaults_present(self):
        for ct in CAGE_DOMAIN_MULTIPLIERS:
            assert ct in CAGE_TYPE_DEFAULT_SCORES, f"{ct} not in CAGE_TYPE_DEFAULT_SCORES"


# ─────────────────────────────────────────────────────────────────────────────
# TestCageHasAdvancedData
# ─────────────────────────────────────────────────────────────────────────────

class TestCageHasAdvancedData:
    def test_bare_cage_has_no_advanced_data(self, open_net):
        assert _cage_has_advanced_data(open_net) is False

    def test_biomass_value_triggers(self, open_net):
        c = CagePenConfig("X", "open_net", 100.0, biomass_value_nok=5_000_000)
        assert _cage_has_advanced_data(c) is True

    def test_consequence_factor_triggers_if_nondefault(self):
        c = CagePenConfig("X", "open_net", 100.0, consequence_factor=1.5)
        assert _cage_has_advanced_data(c) is True

    def test_consequence_factor_one_not_triggered(self):
        c = CagePenConfig("X", "open_net", 100.0, consequence_factor=1.0)
        assert _cage_has_advanced_data(c) is False

    def test_spof_triggers(self):
        c = CagePenConfig("X", "open_net", 100.0, single_point_of_failure=True)
        assert _cage_has_advanced_data(c) is True

    def test_redundancy_triggers(self):
        c = CagePenConfig("X", "open_net", 100.0, redundancy_level=1)
        assert _cage_has_advanced_data(c) is True

    def test_failure_mode_threshold_triggers(self):
        c = CagePenConfig("X", "open_net", 100.0, failure_mode_class="threshold")
        assert _cage_has_advanced_data(c) is True

    def test_locality_triggers_if_any_cage_advanced(self, open_net):
        adv = CagePenConfig("X", "semi_closed", 300.0, biomass_value_nok=10_000_000)
        assert _locality_has_advanced_data([open_net, adv]) is True
        assert _locality_has_advanced_data([open_net]) is False


# ─────────────────────────────────────────────────────────────────────────────
# TestRawComponentDerivation
# ─────────────────────────────────────────────────────────────────────────────

class TestRawComponentDerivation:
    def test_biomass_equals_cage_biomass(self, open_net):
        bio, *_ = _derive_raw_components(open_net)
        assert bio == pytest.approx(500.0)

    def test_value_zero_when_not_provided(self, open_net):
        _, val, *_ = _derive_raw_components(open_net)
        assert val == pytest.approx(0.0)

    def test_value_uses_biomass_value_nok(self, cage_with_value):
        _, val, *_ = _derive_raw_components(cage_with_value)
        assert val == pytest.approx(40_000_000)

    def test_consequence_zero_without_value(self, open_net):
        _, _, cons, *_ = _derive_raw_components(open_net)
        assert cons == pytest.approx(0.0)

    def test_consequence_scales_with_fm_multiplier(self):
        c_prop = CagePenConfig("X", "open_net", 100.0, biomass_value_nok=10_000_000, failure_mode_class="proportional")
        c_thresh = CagePenConfig("Y", "open_net", 100.0, biomass_value_nok=10_000_000, failure_mode_class="threshold")
        _, _, cons_p, *_ = _derive_raw_components(c_prop)
        _, _, cons_t, *_ = _derive_raw_components(c_thresh)
        assert cons_t == pytest.approx(cons_p * FAILURE_MODE_CONSEQUENCE_MULTIPLIER["threshold"])

    def test_complexity_defaults_from_cage_type(self, open_net):
        _, _, _, compl, _, _, def_used = _derive_raw_components(open_net)
        assert compl == pytest.approx(CAGE_TYPE_DEFAULT_SCORES["open_net"]["complexity"])
        assert def_used is True

    def test_complexity_uses_explicit_score(self):
        c = CagePenConfig("X", "open_net", 100.0, operational_complexity_score=0.90)
        _, _, _, compl, _, _, _ = _derive_raw_components(c)
        assert compl == pytest.approx(0.90)

    def test_spof_doubles_criticality(self):
        c_no  = CagePenConfig("A", "open_net", 100.0, structural_criticality_score=0.5)
        c_yes = CagePenConfig("B", "open_net", 100.0, structural_criticality_score=0.5, single_point_of_failure=True)
        _, _, _, _, crit_no,  *_ = _derive_raw_components(c_no)
        _, _, _, _, crit_yes, *_ = _derive_raw_components(c_yes)
        assert crit_yes == pytest.approx(crit_no * SPOF_CRITICALITY_MULTIPLIER)

    def test_redundancy_level_1_increases_criticality(self):
        c_std  = CagePenConfig("A", "open_net", 100.0, structural_criticality_score=0.5, redundancy_level=3)
        c_none = CagePenConfig("B", "open_net", 100.0, structural_criticality_score=0.5, redundancy_level=1)
        _, _, _, _, crit_std,  *_ = _derive_raw_components(c_std)
        _, _, _, _, crit_none, *_ = _derive_raw_components(c_none)
        assert crit_none > crit_std

    def test_defaults_not_used_when_all_explicit(self):
        c = CagePenConfig(
            "X", "open_net", 100.0,
            operational_complexity_score=0.5,
            structural_criticality_score=0.4,
            redundancy_level=3,
            failure_mode_class="proportional",
        )
        _, _, _, _, _, _, def_used = _derive_raw_components(c)
        assert def_used is False


# ─────────────────────────────────────────────────────────────────────────────
# TestMaxNormalise
# ─────────────────────────────────────────────────────────────────────────────

class TestMaxNormalise:
    def test_max_is_one(self):
        result = _max_normalise([100.0, 50.0, 25.0])
        assert max(result) == pytest.approx(1.0)

    def test_proportional_values(self):
        result = _max_normalise([100.0, 50.0])
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(0.5)

    def test_all_zero_returns_zeros(self):
        result = _max_normalise([0.0, 0.0, 0.0])
        assert all(v == 0.0 for v in result)

    def test_equal_values_all_one(self):
        result = _max_normalise([7.0, 7.0, 7.0])
        assert all(v == pytest.approx(1.0) for v in result)

    def test_single_value_is_one(self):
        result = _max_normalise([42.0])
        assert result[0] == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# TestBackwardCompatibility
# ─────────────────────────────────────────────────────────────────────────────

class TestBackwardCompatibility:
    def _biomass_result(self, cages):
        return compute_locality_domain_multipliers(cages)

    def _adv_result(self, cages):
        return compute_locality_domain_multipliers_advanced(cages)

    def test_mode_is_biomass_only(self, open_net, semi_closed):
        r = self._adv_result([open_net, semi_closed])
        assert r.weighting_mode == "biomass_only"

    def test_two_open_net_cages_exact_match(self, open_net, open_net_b):
        expected = self._biomass_result([open_net, open_net_b])
        r = self._adv_result([open_net, open_net_b])
        for d in DOMAINS:
            assert r.domain_multipliers[d] == pytest.approx(expected[d], rel=1e-12)

    def test_mixed_types_exact_match(self, open_net, semi_closed, fully_closed):
        cages = [open_net, semi_closed, fully_closed]
        expected = self._biomass_result(cages)
        r = self._adv_result(cages)
        for d in DOMAINS:
            assert r.domain_multipliers[d] == pytest.approx(expected[d], rel=1e-12)

    def test_single_cage_exact_match(self, submerged):
        expected = self._biomass_result([submerged])
        r = self._adv_result([submerged])
        for d in DOMAINS:
            assert r.domain_multipliers[d] == pytest.approx(expected[d], rel=1e-12)

    def test_details_defaults_used_in_biomass_mode(self, open_net, semi_closed):
        r = self._adv_result([open_net, semi_closed])
        for detail in r.cage_weight_details:
            assert detail.defaults_used is True

    def test_empty_domain_weights_in_biomass_mode(self, open_net):
        r = self._adv_result([open_net])
        for detail in r.cage_weight_details:
            assert detail.domain_weights == {}


# ─────────────────────────────────────────────────────────────────────────────
# TestAdvancedWeightingFormula
# ─────────────────────────────────────────────────────────────────────────────

class TestAdvancedWeightingFormula:
    def test_mode_is_advanced_when_value_set(self, open_net, cage_with_value):
        r = compute_locality_domain_multipliers_advanced([open_net, cage_with_value])
        assert r.weighting_mode == "advanced"

    def test_result_has_all_domains(self, open_net, cage_spof):
        r = compute_locality_domain_multipliers_advanced([open_net, cage_spof])
        assert set(r.domain_multipliers.keys()) == set(DOMAINS)

    def test_single_cage_advanced_returns_cage_type_multipliers(self):
        c = CagePenConfig("X", "semi_closed", 500.0, biomass_value_nok=10_000_000)
        r = compute_locality_domain_multipliers_advanced([c])
        for d in DOMAINS:
            assert r.domain_multipliers[d] == pytest.approx(
                CAGE_DOMAIN_MULTIPLIERS["semi_closed"][d], rel=1e-9
            )

    def test_domain_multipliers_are_positive(self, open_net, cage_spof):
        r = compute_locality_domain_multipliers_advanced([open_net, cage_spof])
        for v in r.domain_multipliers.values():
            assert v > 0

    def test_details_list_has_one_per_cage(self, open_net, semi_closed, cage_spof):
        cages = [open_net, semi_closed, cage_spof]
        r = compute_locality_domain_multipliers_advanced(cages)
        assert len(r.cage_weight_details) == len(cages)

    def test_weight_mode_and_details_consistent(self, open_net, cage_with_value):
        r = compute_locality_domain_multipliers_advanced([open_net, cage_with_value])
        for d in r.cage_weight_details:
            assert len(d.domain_weights) == len(DOMAINS)

    def test_fully_closed_spof_elevated_operational(self):
        """Fully closed cage with SPOF should increase operational weight relative to open_net."""
        c_open   = CagePenConfig("A", "open_net", 500.0, biomass_value_nok=30_000_000)
        c_closed = CagePenConfig("B", "fully_closed", 500.0, biomass_value_nok=30_000_000,
                                 single_point_of_failure=True)
        r = compute_locality_domain_multipliers_advanced([c_open, c_closed])
        # closed cage should have higher ops weight than open_net
        ops_weights = {d.cage_id: d.domain_weights.get("operational", 0) for d in r.cage_weight_details}
        assert ops_weights["B"] > ops_weights["A"]

    def test_warnings_emitted_when_consequence_factor_without_value(self):
        c = CagePenConfig("X", "open_net", 100.0, consequence_factor=2.0)
        c2 = CagePenConfig("Y", "open_net", 200.0, biomass_value_nok=5_000_000)
        r = compute_locality_domain_multipliers_advanced([c, c2])
        assert any("consequence_factor" in w for w in r.warnings)

    def test_warnings_empty_for_clean_input(self, open_net, cage_with_value):
        r = compute_locality_domain_multipliers_advanced([open_net, cage_with_value])
        assert r.warnings == []

    def test_empty_cages_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            compute_locality_domain_multipliers_advanced([])


# ─────────────────────────────────────────────────────────────────────────────
# TestScenarioA_ValueWeighting
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioA_ValueWeighting:
    """
    Scenario A: Two cages with same biomass but different value.
    Higher-value cage should receive more consequence-driven weight,
    especially for domains where consequence coefficient is high (structural).
    """

    def setup_method(self):
        self.c_high = CagePenConfig("HIGH", "open_net", 500.0, biomass_value_nok=50_000_000)
        self.c_low  = CagePenConfig("LOW",  "open_net", 500.0, biomass_value_nok=10_000_000)
        self.result = compute_locality_domain_multipliers_advanced([self.c_high, self.c_low])

    def test_mode_is_advanced(self):
        assert self.result.weighting_mode == "advanced"

    def test_high_value_cage_has_more_structural_weight(self):
        weights = {d.cage_id: d.domain_weights.get("structural", 0) for d in self.result.cage_weight_details}
        assert weights["HIGH"] > weights["LOW"]

    def test_high_value_cage_has_more_biological_weight(self):
        weights = {d.cage_id: d.domain_weights.get("biological", 0) for d in self.result.cage_weight_details}
        assert weights["HIGH"] > weights["LOW"]

    def test_domain_weights_sum_to_one_per_domain(self):
        for domain in DOMAINS:
            total = sum(d.domain_weights.get(domain, 0) for d in self.result.cage_weight_details)
            assert total == pytest.approx(1.0, abs=1e-5)

    def test_domain_multipliers_all_equal(self):
        """Both cages are open_net — multipliers = 1.0 regardless of weights."""
        for v in self.result.domain_multipliers.values():
            assert v == pytest.approx(1.0, rel=1e-9)


# ─────────────────────────────────────────────────────────────────────────────
# TestScenarioB_SPOFandClosed
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioB_SPOFandClosed:
    """
    Scenario B: open_net vs. fully_closed with SPOF, same biomass and value.
    Closed cage with SPOF should contribute more to operational/structural.
    """

    def setup_method(self):
        self.c_open   = CagePenConfig("OPEN",   "open_net",    500.0, biomass_value_nok=30_000_000)
        self.c_closed = CagePenConfig("CLOSED", "fully_closed", 500.0, biomass_value_nok=30_000_000,
                                      single_point_of_failure=True)
        self.result = compute_locality_domain_multipliers_advanced([self.c_open, self.c_closed])

    def test_mode_is_advanced(self):
        assert self.result.weighting_mode == "advanced"

    def test_closed_has_higher_operational_weight(self):
        wt = {d.cage_id: d.domain_weights.get("operational", 0) for d in self.result.cage_weight_details}
        assert wt["CLOSED"] > wt["OPEN"]

    def test_closed_has_higher_structural_weight(self):
        wt = {d.cage_id: d.domain_weights.get("structural", 0) for d in self.result.cage_weight_details}
        assert wt["CLOSED"] > wt["OPEN"]

    def test_locality_ops_multiplier_higher_than_open_net_only(self):
        """If only open_net, ops mult = 1.0. With closed SPOF cage, should be > 1.0."""
        ops_mult = self.result.domain_multipliers["operational"]
        assert ops_mult > 1.0

    def test_domain_weights_sum_per_domain(self):
        for domain in DOMAINS:
            total = sum(d.domain_weights.get(domain, 0) for d in self.result.cage_weight_details)
            assert total == pytest.approx(1.0, abs=1e-5)


# ─────────────────────────────────────────────────────────────────────────────
# TestScenarioC_SubmergedCriticality
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioC_SubmergedCriticality:
    """
    Scenario C: submerged cage with modest biomass but explicit high criticality.
    Should receive elevated structural/operational contribution.
    """

    def setup_method(self):
        # large open_net cage, smaller submerged with high criticality
        self.c_open = CagePenConfig("BIG",  "open_net",  800.0, biomass_value_nok=50_000_000)
        self.c_sub  = CagePenConfig("CRIT", "submerged", 200.0, biomass_value_nok=15_000_000,
                                    structural_criticality_score=0.95, redundancy_level=1)
        self.result = compute_locality_domain_multipliers_advanced([self.c_open, self.c_sub])

    def test_mode_is_advanced(self):
        assert self.result.weighting_mode == "advanced"

    def test_submerged_structural_weight_not_dominated_by_biomass(self):
        """
        Despite having 1/5 the biomass, submerged's structural weight should be
        elevated well above its biomass share (0.2) due to high criticality.
        """
        weights = {d.cage_id: d.domain_weights.get("structural", 0) for d in self.result.cage_weight_details}
        pure_biomass_share = 200.0 / (200.0 + 800.0)   # 0.20
        assert weights["CRIT"] > pure_biomass_share

    def test_submerged_operational_weight_elevated(self):
        weights = {d.cage_id: d.domain_weights.get("operational", 0) for d in self.result.cage_weight_details}
        pure_biomass_share = 200.0 / (200.0 + 800.0)
        assert weights["CRIT"] > pure_biomass_share

    def test_derived_criticality_elevated(self):
        sub_detail = next(d for d in self.result.cage_weight_details if d.cage_id == "CRIT")
        # criticality = 0.95 * spof_mult(1.0) * redundancy(2.0) = 1.90
        assert sub_detail.derived_criticality == pytest.approx(
            0.95 * 1.0 * REDUNDANCY_CRITICALITY_SCALE[1], rel=1e-6
        )

    def test_domain_weights_sum_to_one(self):
        for domain in DOMAINS:
            total = sum(d.domain_weights.get(domain, 0) for d in self.result.cage_weight_details)
            assert total == pytest.approx(1.0, abs=1e-5)


# ─────────────────────────────────────────────────────────────────────────────
# TestScenarioD_BackwardCompat
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioD_BackwardCompat:
    """Scenario D: old inputs with biomass only → results remain backward compatible."""

    def test_two_cages_biomass_only_mode(self):
        c1 = CagePenConfig("A", "open_net",    500.0)
        c2 = CagePenConfig("B", "semi_closed", 300.0)
        r  = compute_locality_domain_multipliers_advanced([c1, c2])
        assert r.weighting_mode == "biomass_only"

    def test_multipliers_match_biomass_function(self):
        c1 = CagePenConfig("A", "open_net",     500.0)
        c2 = CagePenConfig("B", "semi_closed",  300.0)
        c3 = CagePenConfig("C", "fully_closed", 100.0)
        expected = compute_locality_domain_multipliers([c1, c2, c3])
        r = compute_locality_domain_multipliers_advanced([c1, c2, c3])
        for d in DOMAINS:
            assert r.domain_multipliers[d] == pytest.approx(expected[d], rel=1e-12)

    def test_no_warnings_for_biomass_only_input(self):
        c1 = CagePenConfig("A", "open_net",  500.0)
        c2 = CagePenConfig("B", "submerged", 300.0)
        r  = compute_locality_domain_multipliers_advanced([c1, c2])
        assert r.warnings == []

    def test_single_open_net_biomass_mode_equals_one(self):
        c = CagePenConfig("A", "open_net", 1000.0)
        r = compute_locality_domain_multipliers_advanced([c])
        for d in DOMAINS:
            assert r.domain_multipliers[d] == pytest.approx(1.0, rel=1e-12)


# ─────────────────────────────────────────────────────────────────────────────
# TestValidation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def test_invalid_failure_mode_class(self):
        with pytest.raises(ValueError, match="Unknown failure_mode_class"):
            CagePenConfig("X", "open_net", 100.0, failure_mode_class="explodes")

    def test_valid_failure_mode_classes(self):
        for fmc in ["proportional", "threshold", "binary_high_consequence"]:
            c = CagePenConfig("X", "open_net", 100.0, failure_mode_class=fmc)
            assert c.failure_mode_class == fmc

    def test_invalid_redundancy_level(self):
        with pytest.raises(ValueError, match="redundancy_level"):
            CagePenConfig("X", "open_net", 100.0, redundancy_level=0)

    def test_valid_redundancy_levels(self):
        for lvl in [1, 2, 3, 4, 5]:
            c = CagePenConfig("X", "open_net", 100.0, redundancy_level=lvl)
            assert c.redundancy_level == lvl

    def test_negative_biomass_value_nok(self):
        with pytest.raises(ValueError, match="biomass_value_nok must be >= 0"):
            CagePenConfig("X", "open_net", 100.0, biomass_value_nok=-1.0)

    def test_complexity_out_of_range(self):
        with pytest.raises(ValueError, match="operational_complexity_score"):
            CagePenConfig("X", "open_net", 100.0, operational_complexity_score=1.5)

    def test_criticality_out_of_range(self):
        with pytest.raises(ValueError, match="structural_criticality_score"):
            CagePenConfig("X", "open_net", 100.0, structural_criticality_score=-0.1)

    def test_maturity_out_of_range(self):
        with pytest.raises(ValueError, match="technology_maturity_score"):
            CagePenConfig("X", "open_net", 100.0, technology_maturity_score=2.0)


# ─────────────────────────────────────────────────────────────────────────────
# TestDomainWeightNormalization
# ─────────────────────────────────────────────────────────────────────────────

class TestDomainWeightNormalization:
    def _run(self, cages):
        return compute_locality_domain_multipliers_advanced(cages)

    def test_two_advanced_cages_each_domain_sums_one(self, open_net, cage_spof):
        r = self._run([open_net, cage_spof])
        for domain in DOMAINS:
            total = sum(d.domain_weights.get(domain, 0) for d in r.cage_weight_details)
            assert total == pytest.approx(1.0, abs=1e-5)

    def test_three_cages_each_domain_sums_one(self):
        cages = [
            CagePenConfig("A", "open_net",    500.0, biomass_value_nok=30_000_000),
            CagePenConfig("B", "semi_closed", 300.0, biomass_value_nok=20_000_000),
            CagePenConfig("C", "submerged",   200.0, biomass_value_nok=15_000_000),
        ]
        r = self._run(cages)
        for domain in DOMAINS:
            total = sum(d.domain_weights.get(domain, 0) for d in r.cage_weight_details)
            assert total == pytest.approx(1.0, abs=1e-5)

    def test_all_weights_nonnegative(self):
        cages = [
            CagePenConfig("A", "open_net",    500.0, biomass_value_nok=30_000_000),
            CagePenConfig("B", "fully_closed", 200.0, single_point_of_failure=True),
        ]
        r = self._run(cages)
        for detail in r.cage_weight_details:
            for v in detail.domain_weights.values():
                assert v >= 0.0

    def test_single_cage_all_domain_weights_are_one(self):
        c = CagePenConfig("X", "semi_closed", 300.0, biomass_value_nok=20_000_000)
        r = self._run([c])
        for domain in DOMAINS:
            assert r.cage_weight_details[0].domain_weights[domain] == pytest.approx(1.0, rel=1e-9)

    def test_same_type_same_advanced_fields_equal_weights(self):
        """Two identical cages should have equal weight per domain (0.5 each)."""
        c1 = CagePenConfig("A", "semi_closed", 500.0, biomass_value_nok=30_000_000,
                            operational_complexity_score=0.6)
        c2 = CagePenConfig("B", "semi_closed", 500.0, biomass_value_nok=30_000_000,
                            operational_complexity_score=0.6)
        r = self._run([c1, c2])
        for domain in DOMAINS:
            w1 = r.cage_weight_details[0].domain_weights[domain]
            w2 = r.cage_weight_details[1].domain_weights[domain]
            assert w1 == pytest.approx(0.5, rel=1e-9)
            assert w2 == pytest.approx(0.5, rel=1e-9)

    def test_locality_multiplier_between_cage_type_extremes(self):
        """Mixed locality: multiplier must lie between the two cage type extremes."""
        c1 = CagePenConfig("A", "open_net",    500.0, biomass_value_nok=20_000_000)
        c2 = CagePenConfig("B", "fully_closed", 500.0, biomass_value_nok=20_000_000)
        r = self._run([c1, c2])
        for domain in DOMAINS:
            lo = min(CAGE_DOMAIN_MULTIPLIERS["open_net"][domain],
                     CAGE_DOMAIN_MULTIPLIERS["fully_closed"][domain])
            hi = max(CAGE_DOMAIN_MULTIPLIERS["open_net"][domain],
                     CAGE_DOMAIN_MULTIPLIERS["fully_closed"][domain])
            mult = r.domain_multipliers[domain]
            assert lo <= mult <= hi + 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# TestEdgeCases
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_all_same_type_open_net_advanced_mult_is_one(self):
        """All open_net (multipliers = 1.0) → locality multipliers always = 1.0."""
        cages = [
            CagePenConfig("A", "open_net", 500.0, biomass_value_nok=30_000_000),
            CagePenConfig("B", "open_net", 200.0, biomass_value_nok=5_000_000),
        ]
        r = compute_locality_domain_multipliers_advanced(cages)
        for d in DOMAINS:
            assert r.domain_multipliers[d] == pytest.approx(1.0, rel=1e-9)

    def test_binary_high_consequence_mode_large_consequence(self):
        c1 = CagePenConfig("A", "open_net",    500.0, biomass_value_nok=10_000_000)
        c2 = CagePenConfig("B", "semi_closed", 500.0, biomass_value_nok=10_000_000,
                            failure_mode_class="binary_high_consequence")
        r = compute_locality_domain_multipliers_advanced([c1, c2])
        # c2 consequence = 10M * 1.0 * 2.5 = 25M; c1 = 10M * 1.0 * 1.0 = 10M
        # c2 should dominate consequence component → higher structural/biological weight
        wt = {d.cage_id: d.domain_weights.get("structural", 0) for d in r.cage_weight_details}
        assert wt["B"] > wt["A"]

    def test_fully_closed_spof_and_value_warning_for_consequence_without_value(self):
        c_no_val = CagePenConfig("A", "open_net", 100.0, consequence_factor=3.0)
        c_with_val = CagePenConfig("B", "open_net", 200.0, biomass_value_nok=10_000_000)
        r = compute_locality_domain_multipliers_advanced([c_no_val, c_with_val])
        assert any("consequence_factor" in w for w in r.warnings)

    def test_spof_warning_for_low_criticality(self):
        c = CagePenConfig("X", "open_net", 100.0, single_point_of_failure=True)
        c2 = CagePenConfig("Y", "open_net", 200.0)
        r = compute_locality_domain_multipliers_advanced([c, c2])
        assert any("single_point_of_failure" in w for w in r.warnings)

    def test_to_dict_from_dict_round_trip_with_advanced_fields(self):
        c = CagePenConfig(
            "TEST", "semi_closed", 300.0,
            biomass_value_nok=20_000_000,
            consequence_factor=1.2,
            operational_complexity_score=0.7,
            structural_criticality_score=0.5,
            single_point_of_failure=True,
            redundancy_level=2,
            technology_maturity_score=0.8,
            failure_mode_class="threshold",
        )
        d = c.to_dict()
        c2 = CagePenConfig.from_dict(d)
        assert c2.biomass_value_nok == pytest.approx(20_000_000)
        assert c2.single_point_of_failure is True
        assert c2.redundancy_level == 2
        assert c2.failure_mode_class == "threshold"

    def test_partial_advanced_data_triggers_full_advanced_path(self):
        """Even one cage with advanced data → entire locality uses advanced path."""
        c_bare = CagePenConfig("A", "open_net", 500.0)
        c_adv  = CagePenConfig("B", "semi_closed", 100.0, biomass_value_nok=5_000_000)
        r = compute_locality_domain_multipliers_advanced([c_bare, c_adv])
        assert r.weighting_mode == "advanced"
