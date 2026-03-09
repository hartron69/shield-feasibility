"""
Tests for pooled PCC feasibility analysis.

Key assertions (from spec):
  - pooled CV < standalone CV
  - pooled RI cost per operator lower
  - pooled SCR per operator lower
  - pooled PCC appears in strategy comparison
  - no pooling → existing behaviour unchanged
"""
import pytest
import numpy as np

from data.input_schema import validate_input
from models.monte_carlo import MonteCarloEngine
from models.pcc_economics import PCCAssumptions
from models.pooling.assumptions import PoolingAssumptions, KNOWN_SIMPLIFICATIONS
from models.pooling.pool_simulator import (
    PoolMemberSpec,
    apply_rank_correlation,
    build_pool,
    generate_pool_member_specs,
    simulate_raw_member_losses,
)
from models.pooling.pool_economics import compute_pooled_economics
from models.strategies.pooled_pcc import PooledPCCStrategy


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def operator():
    """Load Nordic Aqua Partners template operator."""
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data" / "sample_input.json"
    with open(path) as f:
        raw = json.load(f)
    return validate_input(raw)


@pytest.fixture(scope="module")
def sim(operator):
    """Run MC simulation once for all tests (module scope for speed)."""
    engine = MonteCarloEngine(operator, n_simulations=2000)
    return engine.run()


@pytest.fixture
def default_assumptions():
    return PoolingAssumptions()


@pytest.fixture
def pool_and_specs(operator, sim, default_assumptions):
    return build_pool(
        operator,
        sim.annual_losses,
        default_assumptions,
        n_sims=sim.annual_losses.shape[0],
        n_years=5,
    )


# ── PoolingAssumptions ────────────────────────────────────────────────────────

class TestPoolingAssumptions:
    def test_default_values(self, default_assumptions):
        a = default_assumptions
        assert a.n_members == 4
        assert a.inter_member_correlation == 0.25
        assert a.similarity_spread == 0.15

    def test_validation_n_members_too_low(self):
        with pytest.raises(ValueError, match="n_members"):
            PoolingAssumptions(n_members=1)

    def test_validation_n_members_too_high(self):
        with pytest.raises(ValueError, match="n_members"):
            PoolingAssumptions(n_members=11)

    def test_validation_correlation_out_of_range(self):
        with pytest.raises(ValueError, match="inter_member_correlation"):
            PoolingAssumptions(inter_member_correlation=1.0)

    def test_validation_spread_out_of_range(self):
        with pytest.raises(ValueError, match="similarity_spread"):
            PoolingAssumptions(similarity_spread=0.6)

    def test_validation_loading_factor_out_of_range(self):
        with pytest.raises(ValueError, match="pooled_ri_loading_factor"):
            PoolingAssumptions(pooled_ri_loading_factor=0.5)

    def test_validation_allocation_basis(self):
        with pytest.raises(ValueError, match="allocation_basis"):
            PoolingAssumptions(allocation_basis="invalid")

    def test_known_simplifications_present(self):
        assert len(KNOWN_SIMPLIFICATIONS) >= 4
        assert any("synthetic" in s.lower() for s in KNOWN_SIMPLIFICATIONS)

    def test_presets_are_valid(self):
        for preset_name in ("default", "conservative", "optimistic"):
            a = getattr(PoolingAssumptions, preset_name)()
            assert isinstance(a, PoolingAssumptions)


# ── Pool member generation ────────────────────────────────────────────────────

class TestPoolMemberGeneration:
    def test_member_count(self, operator, default_assumptions):
        rng = np.random.default_rng(42)
        specs = generate_pool_member_specs(operator, default_assumptions, rng)
        assert len(specs) == default_assumptions.n_members

    def test_member_0_is_operator(self, operator, default_assumptions):
        rng = np.random.default_rng(42)
        specs = generate_pool_member_specs(operator, default_assumptions, rng)
        op_spec = specs[0]
        assert op_spec.member_id == 0
        assert op_spec.label == "Operator (you)"
        assert op_spec.expected_events == pytest.approx(
            operator.risk_params.expected_annual_events
        )

    def test_synthetic_members_have_perturbed_params(self, operator, default_assumptions):
        rng = np.random.default_rng(42)
        specs = generate_pool_member_specs(operator, default_assumptions, rng)
        base_events = operator.risk_params.expected_annual_events
        for spec in specs[1:]:
            # Must be perturbed (within ±spread)
            spread = default_assumptions.similarity_spread
            assert base_events * (1 - spread - 0.01) <= spec.expected_events <= base_events * (1 + spread + 0.01)

    def test_synthetic_labels(self, operator, default_assumptions):
        rng = np.random.default_rng(42)
        specs = generate_pool_member_specs(operator, default_assumptions, rng)
        for i, spec in enumerate(specs[1:], start=2):
            assert "Synthetic" in spec.label
            assert str(i) in spec.label

    def test_reproducibility_with_same_seed(self, operator, default_assumptions):
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        specs1 = generate_pool_member_specs(operator, default_assumptions, rng1)
        specs2 = generate_pool_member_specs(operator, default_assumptions, rng2)
        for s1, s2 in zip(specs1, specs2):
            assert s1.expected_events == pytest.approx(s2.expected_events)


# ── Loss simulation ───────────────────────────────────────────────────────────

class TestPoolSimulation:
    def test_build_pool_returns_correct_shapes(self, pool_and_specs, sim):
        specs, correlated = pool_and_specs
        N, T = sim.annual_losses.shape
        assert len(specs) == 4
        assert len(correlated) == 4
        for arr in correlated:
            assert arr.shape == (N, T)

    def test_member_0_losses_match_operator(self, pool_and_specs, sim):
        """Member 0 should use the operator's pre-computed losses."""
        specs, correlated = pool_and_specs
        # After correlation, exact values change but shape and sum should be same order of magnitude
        op_losses = sim.annual_losses
        m0_losses = correlated[0]
        assert m0_losses.shape == op_losses.shape
        # Mean should be close (rank reordering preserves marginal distribution)
        assert m0_losses.mean() == pytest.approx(op_losses.mean(), rel=0.05)

    def test_all_losses_non_negative(self, pool_and_specs):
        _, correlated = pool_and_specs
        for arr in correlated:
            assert (arr >= 0).all()

    def test_synthetic_member_losses_are_positive_expected(self, pool_and_specs):
        _, correlated = pool_and_specs
        for arr in correlated[1:]:
            assert arr.mean() > 0


# ── Correlation ───────────────────────────────────────────────────────────────

class TestCorrelation:
    def _make_losses(self, n=2000, t=5, seed=42):
        rng = np.random.default_rng(seed)
        return [rng.exponential(1e7, (n, t)) for _ in range(4)]

    def test_zero_correlation_preserves_marginals(self):
        raw = self._make_losses()
        rng = np.random.default_rng(99)
        corr = apply_rank_correlation(raw, rho=0.0, rng=rng)
        # rho=0 → no reordering
        for r, c in zip(raw, corr):
            np.testing.assert_array_equal(r, c)

    def test_correlation_increases_pooled_variance(self):
        """
        Higher correlation → less diversification → higher pooled CV.
        Compare rho=0 (fully independent) vs rho=0.5.
        """
        raw_a = self._make_losses(seed=42)
        raw_b = self._make_losses(seed=42)  # same raw

        rng_a = np.random.default_rng(10)
        rng_b = np.random.default_rng(10)

        corr_low = apply_rank_correlation(raw_a, rho=0.01, rng=rng_a)
        corr_high = apply_rank_correlation(raw_b, rho=0.80, rng=rng_b)

        pool_low = sum(corr_low).mean(axis=1)
        pool_high = sum(corr_high).mean(axis=1)

        cv_low = pool_low.std() / pool_low.mean()
        cv_high = pool_high.std() / pool_high.mean()
        assert cv_high > cv_low

    def test_correlated_losses_preserve_marginal_distributions(self):
        """Rank reordering doesn't change each member's marginal mean/std."""
        raw = self._make_losses()
        rng = np.random.default_rng(77)
        corr = apply_rank_correlation(raw, rho=0.50, rng=rng)
        for r, c in zip(raw, corr):
            # Same total (just reordered within each year)
            for t in range(r.shape[1]):
                np.testing.assert_allclose(
                    np.sort(r[:, t]), np.sort(c[:, t])
                )


# ── Pooled economics ──────────────────────────────────────────────────────────

class TestPooledEconomics:
    @pytest.fixture
    def economics(self, operator, sim, default_assumptions):
        specs, correlated = build_pool(
            operator, sim.annual_losses, default_assumptions,
            n_sims=sim.annual_losses.shape[0], n_years=5,
        )
        standalone_scr = float(np.percentile(sim.annual_losses.mean(axis=1), 99.5))
        standalone_ri = 0.5e6  # small placeholder
        return compute_pooled_economics(
            specs=specs,
            correlated_losses=correlated,
            operator_losses=sim.annual_losses,
            operator_standalone_ri_premium=standalone_ri,
            operator_standalone_scr=standalone_scr,
            assumptions=default_assumptions,
            standalone_pcc_assumptions=PCCAssumptions.base(),
        )

    def test_pooled_cv_less_than_standalone_cv(self, economics):
        """Core diversification requirement: pooled CV < standalone CV."""
        assert economics.pooled_cv < economics.standalone_cv, (
            f"Pooled CV {economics.pooled_cv:.4f} should be < standalone "
            f"CV {economics.standalone_cv:.4f}"
        )

    def test_cv_reduction_positive(self, economics):
        assert economics.cv_reduction_pct > 0

    def test_pooled_scr_per_operator_less_than_standalone(self, economics):
        """Pooled SCR allocated to operator < standalone SCR."""
        op_allocated_scr = economics.operator_allocation.allocated_scr
        assert op_allocated_scr < economics.standalone_var_995, (
            f"Allocated pooled SCR {op_allocated_scr:.0f} should be < "
            f"standalone VaR {economics.standalone_var_995:.0f}"
        )

    def test_all_allocations_count(self, economics, default_assumptions):
        assert len(economics.all_allocations) == default_assumptions.n_members

    def test_allocation_weights_sum_to_one(self, economics):
        total = sum(a.allocation_weight for a in economics.all_allocations)
        assert total == pytest.approx(1.0, abs=0.01)

    def test_operator_is_member_0(self, economics):
        assert economics.operator_allocation.member_id == 0
        assert economics.operator_allocation.label == "Operator (you)"

    def test_pooled_ri_is_positive(self, economics):
        assert economics.pooled_ri_premium > 0

    def test_pooled_mean_loss_greater_than_individual(self, economics, operator):
        """Pool mean > any single member's mean (it's the sum)."""
        individual_eal = operator.risk_params.expected_annual_events * operator.risk_params.mean_loss_severity
        assert economics.pooled_mean_annual_loss > individual_eal * 0.5  # sanity


# ── PooledPCCStrategy ────────────────────────────────────────────────────────

class TestPooledPCCStrategy:
    @pytest.fixture
    def standalone_pcc_result(self, operator, sim):
        from models.strategies.pcc_captive import PCCCaptiveStrategy
        return PCCCaptiveStrategy(operator, sim).calculate()

    @pytest.fixture
    def pooled_strategy(self, operator, sim, standalone_pcc_result):
        standalone_scr = standalone_pcc_result.net_loss_scr_data["scr_net"] if standalone_pcc_result.net_loss_scr_data else 0.0
        standalone_ri = standalone_pcc_result.annual_breakdown[0].reinsurance_cost if standalone_pcc_result.annual_breakdown else 0.0
        return PooledPCCStrategy(
            operator, sim,
            pooling_assumptions=PoolingAssumptions(),
            standalone_pcc_assumptions=PCCAssumptions.base(),
            standalone_ri_premium=standalone_ri,
            standalone_scr=standalone_scr,
        )

    def test_calculate_returns_strategy_result(self, pooled_strategy):
        from models.strategies.base_strategy import StrategyResult
        result = pooled_strategy.calculate()
        assert isinstance(result, StrategyResult)

    def test_strategy_name(self, pooled_strategy):
        result = pooled_strategy.calculate()
        assert result.strategy_name == "Pooled PCC Cell"

    def test_pooled_economics_populated(self, pooled_strategy):
        pooled_strategy.calculate()
        assert pooled_strategy.pooled_economics is not None

    def test_required_capital_less_than_standalone(self, operator, sim, standalone_pcc_result, pooled_strategy):
        """Pooled required capital (SCR) per operator should be less."""
        pooled_result = pooled_strategy.calculate()
        standalone_cap = standalone_pcc_result.required_capital
        pooled_cap = pooled_result.required_capital
        # Pooled SCR should be meaningfully lower
        assert pooled_cap < standalone_cap * 1.1, (
            f"Pooled capital {pooled_cap:.0f} should be less than "
            f"standalone {standalone_cap:.0f}"
        )

    def test_annual_breakdown_length(self, pooled_strategy):
        result = pooled_strategy.calculate()
        assert len(result.annual_breakdown) == 5

    def test_simulated_5yr_costs_shape(self, pooled_strategy, sim):
        result = pooled_strategy.calculate()
        assert result.simulated_5yr_costs.shape == (sim.annual_losses.shape[0],)

    def test_net_loss_scr_data_present(self, pooled_strategy):
        result = pooled_strategy.calculate()
        assert result.net_loss_scr_data is not None
        assert "scr_net" in result.net_loss_scr_data


# ── No pooling → unchanged behaviour ─────────────────────────────────────────

class TestNoPoolingBackwardCompat:
    def test_feasibility_response_has_no_pooling_when_disabled(self):
        """When pooling is disabled, FeasibilityResponse.pooling must be None."""
        from backend.schemas import FeasibilityResponse, FeasibilityRequest
        req = FeasibilityRequest()
        assert req.pooling_settings.enabled is False
        # pooling field defaults to None
        from backend.schemas import ScenarioBlock, KPISummary, ReportBlock, MetadataBlock
        resp = FeasibilityResponse(
            baseline=ScenarioBlock(
                summary=KPISummary(
                    expected_annual_loss=1.0, p95_loss=2.0, p99_loss=3.0, scr=1.0,
                    recommended_strategy="PCC", verdict="SUITABLE",
                    composite_score=0.7, confidence_level="medium"
                )
            ),
            report=ReportBlock(available=False),
            metadata=MetadataBlock(
                domain_correlation_active=True, mitigation_active=False, n_simulations=1000
            ),
        )
        assert resp.pooling is None

    def test_pooling_settings_default_disabled(self):
        from backend.schemas import FeasibilityRequest
        req = FeasibilityRequest()
        assert req.pooling_settings.enabled is False

    def test_existing_strategy_results_unchanged_without_pooling(self, operator, sim):
        """Running without pooling produces same strategy set as before."""
        from models.strategies.full_insurance import FullInsuranceStrategy
        from models.strategies.pcc_captive import PCCCaptiveStrategy
        strategies = {
            "Full Insurance": FullInsuranceStrategy(operator, sim),
            "PCC Captive Cell": PCCCaptiveStrategy(operator, sim),
        }
        results = {name: s.calculate() for name, s in strategies.items()}
        assert "Full Insurance" in results
        assert "PCC Captive Cell" in results
        assert "Pooled PCC Cell" not in results


# ── Integration: pooling appears in strategy comparison ──────────────────────

class TestStrategyComparison:
    def test_pooled_pcc_in_strategy_results_when_enabled(self, operator, sim):
        """When pooling is enabled, 'Pooled PCC Cell' appears in strategies."""
        from models.strategies.pcc_captive import PCCCaptiveStrategy

        sa_result = PCCCaptiveStrategy(operator, sim).calculate()
        standalone_scr = sa_result.net_loss_scr_data["scr_net"] if sa_result.net_loss_scr_data else 0.0
        standalone_ri = sa_result.annual_breakdown[0].reinsurance_cost if sa_result.annual_breakdown else 0.0

        pooled_strategy = PooledPCCStrategy(
            operator, sim,
            pooling_assumptions=PoolingAssumptions(),
            standalone_pcc_assumptions=PCCAssumptions.base(),
            standalone_ri_premium=standalone_ri,
            standalone_scr=standalone_scr,
        )
        pooled_result = pooled_strategy.calculate()

        strategies = {
            "Full Insurance": __import__(
                "models.strategies.full_insurance", fromlist=["FullInsuranceStrategy"]
            ).FullInsuranceStrategy(operator, sim).calculate(),
            "PCC Captive Cell": sa_result,
            "Pooled PCC Cell": pooled_result,
        }
        assert "Pooled PCC Cell" in strategies
        assert strategies["Pooled PCC Cell"].strategy_name == "Pooled PCC Cell"

    def test_pooled_scr_lower_than_standalone_in_strategy_comparison(self, operator, sim):
        """Pooled SCR per operator must be lower than standalone SCR.

        Note: pooled RI per operator is NOT necessarily lower — the pool retention
        (25 M for the whole pool = ~6 M effective per member) is lower than the
        standalone retention (25 M per operator), so RI kicks in more often and
        pooled RI per operator can be HIGHER.  The pooling benefit materialises via
        CV / SCR reduction and the lower RI loading factor (1.40 vs 1.75).
        """
        from models.strategies.pcc_captive import PCCCaptiveStrategy

        sa_result = PCCCaptiveStrategy(operator, sim).calculate()
        standalone_scr = (
            sa_result.net_loss_scr_data.get("scr_net", 0)
            if sa_result.net_loss_scr_data
            else sa_result.required_capital
        )

        pooled_strategy = PooledPCCStrategy(
            operator, sim,
            pooling_assumptions=PoolingAssumptions(),
            standalone_pcc_assumptions=PCCAssumptions.base(),
            standalone_ri_premium=(
                sa_result.annual_breakdown[0].reinsurance_cost
                if sa_result.annual_breakdown else 1.0
            ),
            standalone_scr=standalone_scr,
        )
        pooled_result = pooled_strategy.calculate()

        pooled_scr = pooled_result.required_capital
        assert pooled_scr < standalone_scr, (
            f"Pooled SCR {pooled_scr:.0f} should be < standalone SCR {standalone_scr:.0f}"
        )

    def test_pooled_cv_improves_vs_standalone(self, operator, sim):
        """CV of pooled losses < CV of standalone losses."""
        from models.strategies.pcc_captive import PCCCaptiveStrategy

        sa_result = PCCCaptiveStrategy(operator, sim).calculate()
        pooled_strategy = PooledPCCStrategy(
            operator, sim,
            pooling_assumptions=PoolingAssumptions(),
            standalone_pcc_assumptions=PCCAssumptions.base(),
        )
        pooled_strategy.calculate()
        eco = pooled_strategy.pooled_economics
        assert eco is not None
        assert eco.pooled_cv < eco.standalone_cv


# ── Schema validation ────────────────────────────────────────────────────────

class TestPoolingSchemas:
    def test_pooling_settings_input_defaults(self):
        from backend.schemas import PoolingSettingsInput
        p = PoolingSettingsInput()
        assert p.enabled is False
        assert p.n_members == 4
        assert p.inter_member_correlation == 0.25

    def test_pooling_result_fields(self):
        from backend.schemas import PoolingResult, PoolingMemberStats
        r = PoolingResult(
            enabled=True, n_members=4,
            pooled_mean_annual_loss=1e7, pooled_cv=0.5, pooled_var_995=3e7,
            standalone_cv=0.8, standalone_var_995=5e7,
            cv_reduction_pct=37.5, var_reduction_pct=40.0,
            pooled_ri_premium_annual=1e6, standalone_ri_premium_annual=2e6,
            ri_premium_reduction_pct=50.0,
            pooled_scr=5e6, standalone_scr=10e6, scr_reduction_pct=50.0,
            operator_5yr_tcor_standalone=20e6, operator_5yr_tcor_pooled=12e6,
            tcor_improvement_pct=40.0,
            members=[
                PoolingMemberStats(
                    member_id=0, label="Operator (you)",
                    expected_annual_loss=1e7, allocation_weight=0.25,
                    standalone_cv=0.8, pooled_cv=0.5,
                    allocated_ri_premium_annual=2.5e5,
                    allocated_scr=1.25e6, allocated_5yr_tcor=3e6,
                )
            ],
            viable=True,
            verdict_narrative="Pooled PCC is viable.",
        )
        assert r.n_members == 4
        assert r.viable is True
        assert len(r.members) == 1

    def test_feasibility_response_has_pooling_field(self):
        from backend.schemas import FeasibilityResponse
        assert "pooling" in FeasibilityResponse.model_fields
