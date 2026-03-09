"""
Tests for the biomass valuation suggestion and override logic in operator_builder.

Covers:
1. suggested value calculated correctly from formula
2. applied value == suggested value (via biomass_value_per_tonne) when no override
3. applied value == override when biomass_value_per_tonne_override is provided
4. override flag is correct in both cases
5. defaults are applied when inputs are omitted
6. invalid valuation inputs are rejected by Pydantic
7. override value flows through to MC (changes expected loss)
"""

import pytest

from backend.schemas import OperatorProfileInput
from backend.services.operator_builder import build_operator_input


# ── Helpers ───────────────────────────────────────────────────────────────────

def _profile(**kwargs) -> OperatorProfileInput:
    defaults = dict(
        name="Test AS",
        country="Norge",
        n_sites=3,
        total_biomass_tonnes=9_200.0,
        biomass_value_per_tonne=64_800.0,   # matches default suggested (ref=80, real=0.9, hc=0.1)
        annual_revenue_nok=897_000_000.0,
        annual_premium_nok=19_500_000.0,
    )
    defaults.update(kwargs)
    return OperatorProfileInput(**defaults)


# ── TestSuggestedFormula ──────────────────────────────────────────────────────

class TestSuggestedFormula:
    def test_standard_example_from_spec(self):
        """80 × 1000 × 0.90 × (1 - 0.10) = 64,800 NOK/t"""
        _, alloc = build_operator_input(_profile(
            reference_price_per_kg=80.0,
            realisation_factor=0.90,
            prudence_haircut=0.10,
        ))
        assert alloc.biomass_valuation.suggested_biomass_value_per_tonne == pytest.approx(64_800.0, rel=1e-4)

    def test_zero_haircut_gives_no_prudence_reduction(self):
        """80 × 1000 × 0.90 × 1.0 = 72,000 NOK/t"""
        _, alloc = build_operator_input(_profile(
            reference_price_per_kg=80.0,
            realisation_factor=0.90,
            prudence_haircut=0.0,
        ))
        assert alloc.biomass_valuation.suggested_biomass_value_per_tonne == pytest.approx(72_000.0, rel=1e-4)

    def test_higher_reference_price_gives_higher_suggestion(self):
        _, alloc_low = build_operator_input(_profile(reference_price_per_kg=60.0))
        _, alloc_high = build_operator_input(_profile(reference_price_per_kg=100.0))
        assert (
            alloc_high.biomass_valuation.suggested_biomass_value_per_tonne
            > alloc_low.biomass_valuation.suggested_biomass_value_per_tonne
        )

    def test_higher_haircut_gives_lower_suggestion(self):
        _, alloc_low = build_operator_input(_profile(prudence_haircut=0.05))
        _, alloc_high = build_operator_input(_profile(prudence_haircut=0.25))
        assert (
            alloc_high.biomass_valuation.suggested_biomass_value_per_tonne
            < alloc_low.biomass_valuation.suggested_biomass_value_per_tonne
        )

    def test_summary_records_all_formula_inputs(self):
        _, alloc = build_operator_input(_profile(
            reference_price_per_kg=75.0,
            realisation_factor=0.85,
            prudence_haircut=0.12,
        ))
        bv = alloc.biomass_valuation
        assert bv.reference_price_per_kg == 75.0
        assert bv.realisation_factor == 0.85
        assert bv.prudence_haircut == 0.12


# ── TestAppliedValue ──────────────────────────────────────────────────────────

class TestAppliedValue:
    def test_applied_equals_biomass_field_when_no_override(self):
        """Backward-compat path: applied = biomass_value_per_tonne (not suggested)."""
        _, alloc = build_operator_input(_profile(
            biomass_value_per_tonne=72_000.0,
            biomass_value_per_tonne_override=None,
        ))
        assert alloc.biomass_valuation.applied_biomass_value_per_tonne == pytest.approx(72_000.0)

    def test_user_overridden_false_when_no_override(self):
        _, alloc = build_operator_input(_profile(biomass_value_per_tonne_override=None))
        assert alloc.biomass_valuation.user_overridden is False

    def test_applied_equals_override_when_provided(self):
        _, alloc = build_operator_input(_profile(
            biomass_value_per_tonne=64_800.0,
            biomass_value_per_tonne_override=85_000.0,
        ))
        assert alloc.biomass_valuation.applied_biomass_value_per_tonne == pytest.approx(85_000.0)

    def test_user_overridden_true_when_override_provided(self):
        _, alloc = build_operator_input(_profile(biomass_value_per_tonne_override=85_000.0))
        assert alloc.biomass_valuation.user_overridden is True

    def test_override_takes_priority_over_biomass_field(self):
        """If both fields are present, override wins."""
        _, alloc = build_operator_input(_profile(
            biomass_value_per_tonne=72_000.0,
            biomass_value_per_tonne_override=90_000.0,
        ))
        assert alloc.biomass_valuation.applied_biomass_value_per_tonne == pytest.approx(90_000.0)


# ── TestDefaults ──────────────────────────────────────────────────────────────

class TestDefaults:
    def test_default_reference_price_is_80(self):
        p = OperatorProfileInput()
        assert p.reference_price_per_kg == 80.0

    def test_default_realisation_factor_is_0_90(self):
        p = OperatorProfileInput()
        assert p.realisation_factor == pytest.approx(0.90)

    def test_default_prudence_haircut_is_0_10(self):
        p = OperatorProfileInput()
        assert p.prudence_haircut == pytest.approx(0.10)

    def test_default_override_is_none(self):
        p = OperatorProfileInput()
        assert p.biomass_value_per_tonne_override is None

    def test_default_biomass_value_matches_suggested(self):
        """Default biomass_value_per_tonne = 64,800 = 80×1000×0.9×0.9"""
        p = OperatorProfileInput()
        assert p.biomass_value_per_tonne == pytest.approx(64_800.0)

    def test_default_request_produces_valuation_summary(self):
        _, alloc = build_operator_input(OperatorProfileInput())
        assert alloc.biomass_valuation is not None


# ── TestMCFlowthrough ─────────────────────────────────────────────────────────

class TestMCFlowthrough:
    """Applied value must reach the MC engine (TIV-scaling chain)."""

    def test_override_changes_expected_loss(self):
        """Higher applied value → higher TIV → higher mean_loss_severity → higher E[loss]."""
        from models.monte_carlo import MonteCarloEngine

        op_low, _ = build_operator_input(_profile(biomass_value_per_tonne_override=40_000.0))
        op_high, _ = build_operator_input(_profile(biomass_value_per_tonne_override=120_000.0))

        sim_low = MonteCarloEngine(op_low, n_simulations=300).run()
        sim_high = MonteCarloEngine(op_high, n_simulations=300).run()
        assert sim_high.mean_annual_loss > sim_low.mean_annual_loss * 1.5

    def test_applied_value_used_in_site_biomass_value(self):
        """Site.biomass_value_per_tonne == applied_value."""
        op, alloc = build_operator_input(_profile(biomass_value_per_tonne_override=55_000.0))
        for site in op.sites:
            assert site.biomass_value_per_tonne == pytest.approx(55_000.0)
        assert alloc.biomass_valuation.applied_biomass_value_per_tonne == pytest.approx(55_000.0)


# ── TestSchemaValidation ──────────────────────────────────────────────────────

class TestSchemaValidation:
    def test_realisation_factor_above_max_rejected(self):
        with pytest.raises(Exception):
            _profile(realisation_factor=1.5)   # > 1.2

    def test_realisation_factor_below_min_rejected(self):
        with pytest.raises(Exception):
            _profile(realisation_factor=0.3)   # < 0.5

    def test_prudence_haircut_above_max_rejected(self):
        with pytest.raises(Exception):
            _profile(prudence_haircut=0.6)     # > 0.5

    def test_negative_reference_price_rejected(self):
        with pytest.raises(Exception):
            _profile(reference_price_per_kg=-10.0)

    def test_valid_override_is_accepted(self):
        p = _profile(biomass_value_per_tonne_override=50_000.0)
        assert p.biomass_value_per_tonne_override == 50_000.0

    def test_none_override_is_accepted(self):
        p = _profile(biomass_value_per_tonne_override=None)
        assert p.biomass_value_per_tonne_override is None

    def test_negative_override_raises_in_builder(self):
        with pytest.raises((ValueError, Exception)):
            build_operator_input(_profile(biomass_value_per_tonne_override=-1.0))
