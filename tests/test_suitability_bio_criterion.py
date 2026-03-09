"""
Tests for the new Criterion 6 – Biological Operational Readiness.
"""

import pytest

from analysis.suitability_engine import SuitabilityEngine
from tests.test_monte_carlo_integration import SAMPLE_OPERATOR, _make_engine
from data.input_schema import validate_input
from analysis.cost_analyzer import CostAnalyzer
from models.strategies.full_insurance import FullInsuranceStrategy
from models.strategies.pcc_captive import PCCCaptiveStrategy


def _make_full_assessment(extra_operator: dict = None):
    """Run a minimal full pipeline and return the SuitabilityEngine."""
    raw = {**SAMPLE_OPERATOR, **(extra_operator or {})}
    operator = validate_input(raw)
    engine = _make_engine(extra=extra_operator, n=500)
    sim = engine.run()

    strategy_results = {
        "Full Insurance": FullInsuranceStrategy(operator, sim).calculate(),
        "PCC Captive Cell": PCCCaptiveStrategy(operator, sim).calculate(),
    }
    cost_analysis = CostAnalyzer(operator, strategy_results).analyze()

    return SuitabilityEngine(operator, sim, strategy_results, cost_analysis)


class TestBioReadinessCriterion:
    def test_criterion_present_in_assessment(self):
        engine = _make_full_assessment()
        rec = engine.assess()
        names = [c.name for c in rec.criterion_scores]
        assert "Biologisk Operasjonell Beredskap" in names

    def test_criterion_weight_is_10_percent(self):
        engine = _make_full_assessment()
        rec = engine.assess()
        bio = next(c for c in rec.criterion_scores if "Biologisk" in c.name)
        assert bio.weight == pytest.approx(0.10, abs=0.001)

    def test_all_weights_sum_to_one(self):
        engine = _make_full_assessment()
        rec = engine.assess()
        total_weight = sum(c.weight for c in rec.criterion_scores)
        assert total_weight == pytest.approx(1.0, abs=0.01)

    def test_explicit_bio_score_high_raises_raw_score(self):
        low = _make_full_assessment({"bio_readiness_score": 20})
        high = _make_full_assessment({"bio_readiness_score": 90})

        low_rec = low.assess()
        high_rec = high.assess()

        low_bio = next(c for c in low_rec.criterion_scores if "Biologisk" in c.name)
        high_bio = next(c for c in high_rec.criterion_scores if "Biologisk" in c.name)

        assert high_bio.raw_score > low_bio.raw_score

    def test_composite_score_has_six_criteria(self):
        engine = _make_full_assessment()
        rec = engine.assess()
        assert len(rec.criterion_scores) == 6

    def test_weighted_scores_sum_to_composite(self):
        engine = _make_full_assessment()
        rec = engine.assess()
        total = sum(c.weighted_score for c in rec.criterion_scores)
        assert total == pytest.approx(rec.composite_score, abs=0.001)

    def test_no_risk_manager_lowers_bio_score(self):
        with_rm = _make_full_assessment({"has_risk_manager": True})
        without_rm = _make_full_assessment({"has_risk_manager": False})

        with_rm_rec = with_rm.assess()
        without_rm_rec = without_rm.assess()

        with_bio = next(c for c in with_rm_rec.criterion_scores if "Biologisk" in c.name)
        without_bio = next(c for c in without_rm_rec.criterion_scores if "Biologisk" in c.name)

        assert with_bio.raw_score >= without_bio.raw_score
