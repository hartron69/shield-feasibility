"""
Tests for CaptiveStructure objects (AP4).
"""
import pytest
import numpy as np
from unittest.mock import MagicMock

from models.captive_structure import (
    CaptiveStructure,
    RetentionLayer,
    ReinsuranceLayer,
)
from models.loss_model import LossView, compute_loss_view


def _make_sim(losses=None):
    sim = MagicMock()
    if losses is None:
        rng = np.random.default_rng(42)
        losses = rng.exponential(10_000_000, size=(1000, 5))
    sim.annual_losses = losses
    return sim


class TestRetentionLayer:
    def test_default_values(self):
        rl = RetentionLayer(name="test")
        assert rl.per_occurrence_retention == 0.0
        assert rl.annual_aggregate_retention == float("inf")

    def test_custom_values(self):
        rl = RetentionLayer(
            name="deductible",
            per_occurrence_retention=1_000_000,
            annual_aggregate_retention=5_000_000,
        )
        assert rl.per_occurrence_retention == 1_000_000


class TestReinsuranceLayer:
    def test_recovery_below_attachment(self):
        layer = ReinsuranceLayer(
            name="L1", attachment_point=5_000_000, limit=20_000_000
        )
        losses = np.array([1_000_000, 3_000_000])
        recoveries = layer.recovery(losses)
        np.testing.assert_array_equal(recoveries, [0, 0])

    def test_recovery_above_attachment(self):
        layer = ReinsuranceLayer(
            name="L1", attachment_point=5_000_000, limit=20_000_000
        )
        losses = np.array([10_000_000, 30_000_000])
        recoveries = layer.recovery(losses)
        assert recoveries[0] == pytest.approx(5_000_000)    # 10M - 5M = 5M, < 20M limit
        assert recoveries[1] == pytest.approx(20_000_000)   # capped at limit

    def test_partial_participation(self):
        layer = ReinsuranceLayer(
            name="L1", attachment_point=0, limit=10_000_000,
            participation_pct=50.0
        )
        losses = np.array([10_000_000])
        recoveries = layer.recovery(losses)
        assert recoveries[0] == pytest.approx(5_000_000)


class TestCaptiveStructure:
    def _basic_structure(self, retention=1_000_000, captive_limit=20_000_000):
        return CaptiveStructure(
            operator_name="TestOp",
            retention=RetentionLayer(
                name="retention",
                per_occurrence_retention=retention,
            ),
            captive_layer=ReinsuranceLayer(
                name="captive",
                attachment_point=retention,
                limit=captive_limit,
            ),
        )

    def test_compute_net_loss_with_retention(self):
        structure = self._basic_structure(retention=2_000_000)
        losses = np.array([500_000, 5_000_000, 50_000_000])
        net = structure.compute_net_loss(losses)
        # Below retention: fully retained
        assert net[0] == pytest.approx(500_000)
        # Above retention: retained = retention amount + excess above captive
        # 5M loss: 2M retention, captive absorbs 3M (within limit) → net = 2M
        assert net[1] == pytest.approx(2_000_000)

    def test_compute_captive_loss(self):
        structure = self._basic_structure(retention=1_000_000, captive_limit=10_000_000)
        losses = np.array([500_000, 6_000_000])
        captive = structure.compute_captive_loss(losses)
        # Below retention: captive absorbs 0
        assert captive[0] == pytest.approx(0.0)
        # 6M loss: excess above 1M = 5M, within limit → captive = 5M
        assert captive[1] == pytest.approx(5_000_000)

    def test_compute_reinsured_loss_no_layers(self):
        structure = CaptiveStructure(
            operator_name="test",
            retention=RetentionLayer("r"),
        )
        losses = np.array([10_000_000])
        reinsured = structure.compute_reinsured_loss(losses)
        np.testing.assert_array_equal(reinsured, [0.0])

    def test_capital_requirement_positive(self):
        structure = self._basic_structure()
        sim = _make_sim()
        capital = structure.capital_requirement(sim)
        assert capital >= 0.0

    def test_annual_reinsurance_premium(self):
        structure = CaptiveStructure(
            operator_name="op",
            retention=RetentionLayer("r"),
            captive_layer=ReinsuranceLayer(
                name="captive", attachment_point=0, limit=10_000_000,
                estimated_premium=500_000,
            ),
            reinsurance_layers=[
                ReinsuranceLayer(
                    name="XL", attachment_point=10_000_000, limit=20_000_000,
                    estimated_premium=300_000,
                )
            ],
        )
        assert structure.annual_reinsurance_premium() == pytest.approx(800_000)


class TestLossModel:
    def test_compute_loss_view_no_structure(self):
        losses = np.ones((100, 5)) * 10_000_000
        view = compute_loss_view(losses)
        np.testing.assert_array_almost_equal(view.gross_loss, losses)
        np.testing.assert_array_almost_equal(view.reinsured_loss, losses)

    def test_loss_view_properties(self):
        rng = np.random.default_rng(1)
        losses = rng.exponential(5_000_000, size=(500, 5))
        view = compute_loss_view(losses, attachment_point=1_000_000)
        assert view.mean_gross > 0
        assert view.mean_reinsured >= 0
        assert view.gross_var_995 > 0

    def test_retention_layer_applied(self):
        losses = np.array([[5_000_000, 10_000_000]])
        view = compute_loss_view(losses, retention_layer=2_000_000)
        # Losses below retention stay with operator
        # Loss of 5M: 5M > 2M retention → excess 3M → reinsured
        assert view.reinsured_loss[0, 0] == pytest.approx(3_000_000)
