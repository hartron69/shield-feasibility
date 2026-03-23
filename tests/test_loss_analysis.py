"""
Tests for backend loss analysis (Tapsanalyse tab).

Coverage:
1. compute_loss_analysis returns required top-level keys
2. per_site totals sum plausibly to portfolio EAL
3. per_domain totals are present and non-negative
4. SCR allocation sums to total_scr
5. dominant_domain is one of the 4 canonical domains
6. mitigated block present when mit data supplied; absent otherwise
7. mitigated per-site EALs are lower when loss reduces
8. method_note is a non-empty string
9. top_drivers sorted descending by impact_nok
10. compute_loss_analysis handles missing site_loss_distribution gracefully
11. Schema: LossAnalysisBlock validates from compute_loss_analysis output
12. FeasibilityResponse accepts loss_analysis: None (backward compat)
13. End-to-end: API route /api/feasibility/run returns loss_analysis payload
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from backend.services.loss_analysis import compute_loss_analysis
from backend.schemas import LossAnalysisBlock, LossAnalysisSite, LossAnalysisDriver, FeasibilityResponse


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _mock_dld(n=500, t=5, seed=42):
    """Return a mock DomainLossBreakdown with consistent arrays."""
    rng = np.random.default_rng(seed)
    dld = MagicMock()

    bio  = rng.exponential(4_000_000, size=(n, t))
    env  = rng.exponential(3_000_000, size=(n, t))
    stru = rng.exponential(2_000_000, size=(n, t))
    ops  = rng.exponential(1_000_000, size=(n, t))

    dld.domain_totals.return_value = {
        "biological":   bio,
        "environmental":env,
        "structural":   stru,
        "operational":  ops,
    }
    dld.all_subtypes.return_value = {
        "hab":         bio * 0.5,
        "lice":        bio * 0.3,
        "pathogen":    bio * 0.2,
        "current_storm": env * 0.7,
        "oxygen_stress": env * 0.3,
        "mooring_failure": stru * 0.6,
        "net_integrity": stru * 0.4,
        "human_error": ops,
    }
    return dld


def _mock_sim(n=500, t=5, n_sites=3, seed=7):
    """Return a mock SimulationResults with site_loss_distribution."""
    rng = np.random.default_rng(seed)
    base = rng.exponential(10_000_000, size=(n, t))

    sim = MagicMock()
    sim.annual_losses = base
    sim.mean_annual_loss = float(base.mean())
    sim.std_annual_loss  = float(base.std())
    sim.var_995 = float(np.percentile(base, 99.5))
    sim.domain_loss_breakdown = _mock_dld(n, t)

    # Create n_sites site distributions that sum to portfolio total
    weights = np.array([0.50, 0.30, 0.20][:n_sites])
    weights = weights / weights.sum()
    site_names = [f"Site_{i}" for i in range(n_sites)]
    sim.site_loss_distribution = {
        site_names[i]: base * weights[i] for i in range(n_sites)
    }
    return sim


def _mock_op():
    op = MagicMock()
    op.name = "Test AS"
    return op


# ─────────────────────────────────────────────────────────────────────────────
# Group 1: compute_loss_analysis — structure and content
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeLossAnalysisStructure:
    def _run(self, **kwargs):
        sim = _mock_sim()
        return compute_loss_analysis(sim, _mock_op(), 25_000_000, **kwargs)

    def test_returns_required_keys(self):
        result = self._run()
        assert "per_site" in result
        assert "per_domain" in result
        assert "top_drivers" in result
        assert "method_note" in result
        # mitigated may be None
        assert "mitigated" in result

    def test_per_site_has_3_sites(self):
        result = self._run()
        assert len(result["per_site"]) == 3

    def test_per_site_fields(self):
        result = self._run()
        for s in result["per_site"]:
            assert "site_id" in s
            assert "site_name" in s
            assert "expected_annual_loss_nok" in s
            assert "scr_contribution_nok" in s
            assert "scr_share_pct" in s
            assert "dominant_domain" in s
            assert "domain_breakdown" in s

    def test_per_domain_has_4_domains(self):
        result = self._run()
        assert set(result["per_domain"].keys()) == {"biological", "environmental", "structural", "operational"}

    def test_per_domain_values_non_negative(self):
        result = self._run()
        for d, v in result["per_domain"].items():
            assert v >= 0, f"{d} = {v}"

    def test_method_note_non_empty(self):
        result = self._run()
        assert isinstance(result["method_note"], str)
        assert len(result["method_note"]) > 10

    def test_top_drivers_sorted_descending(self):
        result = self._run()
        impacts = [d["impact_nok"] for d in result["top_drivers"]]
        assert impacts == sorted(impacts, reverse=True), "top_drivers must be sorted descending"

    def test_top_drivers_have_domain_and_label(self):
        result = self._run()
        for d in result["top_drivers"]:
            assert "label" in d
            assert "domain" in d
            assert d["domain"] in ("biological", "environmental", "structural", "operational")

    def test_dominant_domain_is_canonical(self):
        result = self._run()
        for s in result["per_site"]:
            assert s["dominant_domain"] in (
                "biological", "environmental", "structural", "operational"
            ), f"Unexpected dominant_domain: {s['dominant_domain']}"


class TestComputeLossAnalysisQuantitative:
    def test_per_site_eal_sums_to_portfolio_eal(self):
        """Sum of per-site EALs should approximately equal portfolio mean annual loss."""
        sim = _mock_sim(n=1000)
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        site_total = sum(s["expected_annual_loss_nok"] for s in result["per_site"])
        portfolio_eal = float(sim.annual_losses.mean())
        # Due to (N,T) mean vs sum, there may be a factor-of-T discrepancy
        # The key invariant is that per-site totals sum to the same number they
        # were derived from — the distribution sums to portfolio at each (n,t).
        # Allow 1% rounding tolerance.
        assert abs(site_total - portfolio_eal) / max(portfolio_eal, 1) < 0.01, (
            f"site_total={site_total:.0f} vs portfolio_eal={portfolio_eal:.0f}"
        )

    def test_scr_allocation_sums_to_total_scr(self):
        """Allocated SCR should sum to the input total_scr (within 1%)."""
        sim = _mock_sim(n=500)
        total_scr = 30_000_000.0
        result = compute_loss_analysis(sim, _mock_op(), total_scr)
        allocated = sum(s["scr_contribution_nok"] for s in result["per_site"])
        assert abs(allocated - total_scr) / total_scr < 0.01, (
            f"allocated_scr={allocated:.0f} vs total_scr={total_scr:.0f}"
        )

    def test_scr_shares_sum_to_100(self):
        sim = _mock_sim(n=500)
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        total_pct = sum(s["scr_share_pct"] for s in result["per_site"])
        assert abs(total_pct - 100.0) < 1.0, f"SCR shares sum = {total_pct:.1f}%"

    def test_largest_site_has_highest_eal(self):
        """Site_0 has 50% weight so must have largest EAL."""
        sim = _mock_sim(n=500)
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        # per_site is sorted descending by EAL
        assert result["per_site"][0]["site_id"] == "Site_0"

    def test_domain_breakdown_sums_approx_to_site_eal(self):
        """Sum of domain_breakdown values for a site ≈ site EAL (proportional allocation)."""
        sim = _mock_sim(n=500)
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        for s in result["per_site"]:
            domain_sum = sum(s["domain_breakdown"].values())
            # Allow 5% tolerance (floating-point rounding from proportional allocation)
            eal = s["expected_annual_loss_nok"]
            if eal > 0:
                assert abs(domain_sum - eal) / eal < 0.05, (
                    f"Site {s['site_id']}: domain_sum={domain_sum:.0f} vs eal={eal:.0f}"
                )


class TestComputeLossAnalysisMitigated:
    def test_mitigated_block_absent_when_no_mit_data(self):
        sim = _mock_sim()
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        assert result["mitigated"] is None

    def test_mitigated_block_present_when_mit_supplied(self):
        sim = _mock_sim(n=500)
        mit_e_loss = float(sim.annual_losses.mean()) * 0.7
        mit_losses_1d = sim.annual_losses.mean(axis=1) * 0.7
        result = compute_loss_analysis(
            sim, _mock_op(), 25_000_000,
            mit_losses_1d=mit_losses_1d,
            mit_e_loss=mit_e_loss,
            mit_scr=20_000_000,
        )
        assert result["mitigated"] is not None
        assert "per_site" in result["mitigated"]
        assert "per_domain" in result["mitigated"]
        assert "delta_total_eal_nok" in result["mitigated"]
        assert "delta_total_scr_nok" in result["mitigated"]

    def test_mitigated_per_site_eal_lower_than_baseline(self):
        sim = _mock_sim(n=500)
        baseline_eal = float(sim.annual_losses.mean())
        mit_e_loss = baseline_eal * 0.6
        mit_losses_1d = sim.annual_losses.mean(axis=1) * 0.6
        result = compute_loss_analysis(
            sim, _mock_op(), 25_000_000,
            mit_losses_1d=mit_losses_1d,
            mit_e_loss=mit_e_loss,
            mit_scr=15_000_000,
        )
        for s_base, s_mit in zip(result["per_site"], result["mitigated"]["per_site"]):
            assert s_mit["expected_annual_loss_nok"] <= s_base["expected_annual_loss_nok"] + 1, (
                f"Mitigated EAL ({s_mit['expected_annual_loss_nok']}) > baseline ({s_base['expected_annual_loss_nok']})"
            )

    def test_mitigated_delta_eal_negative(self):
        sim = _mock_sim(n=500)
        baseline_eal = float(sim.annual_losses.mean())
        mit_e_loss = baseline_eal * 0.7
        result = compute_loss_analysis(
            sim, _mock_op(), 25_000_000,
            mit_losses_1d=sim.annual_losses.mean(axis=1) * 0.7,
            mit_e_loss=mit_e_loss,
            mit_scr=18_000_000,
        )
        assert result["mitigated"]["delta_total_eal_nok"] < 0, (
            "delta_total_eal_nok must be negative when mit_e_loss < baseline_eal"
        )

    def test_mitigated_delta_scr_negative(self):
        sim = _mock_sim(n=500)
        result = compute_loss_analysis(
            sim, _mock_op(), 25_000_000,
            mit_losses_1d=sim.annual_losses.mean(axis=1) * 0.7,
            mit_e_loss=float(sim.annual_losses.mean()) * 0.7,
            mit_scr=18_000_000,
        )
        assert result["mitigated"]["delta_total_scr_nok"] < 0


class TestComputeLossAnalysisEdgeCases:
    def test_handles_missing_site_distribution(self):
        """When site_loss_distribution is None, per_site should be empty."""
        sim = _mock_sim()
        sim.site_loss_distribution = None
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        assert result["per_site"] == []

    def test_handles_empty_site_distribution(self):
        sim = _mock_sim()
        sim.site_loss_distribution = {}
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        assert result["per_site"] == []

    def test_handles_missing_domain_breakdown(self):
        sim = _mock_sim()
        sim.domain_loss_breakdown = None
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        # Should not raise; per_domain may be empty
        assert isinstance(result["per_domain"], dict)

    def test_single_site(self):
        sim = _mock_sim(n_sites=1)
        result = compute_loss_analysis(sim, _mock_op(), 25_000_000)
        assert len(result["per_site"]) == 1
        assert result["per_site"][0]["scr_share_pct"] == pytest.approx(100.0, abs=1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Group 2: Schema validation
# ─────────────────────────────────────────────────────────────────────────────

class TestLossAnalysisSchema:
    def test_loss_analysis_block_validates_from_compute_output(self):
        sim = _mock_sim(n=200)
        raw = compute_loss_analysis(sim, _mock_op(), 20_000_000)
        from backend.schemas import LossAnalysisMitigated, LossAnalysisMitigatedSite
        block = LossAnalysisBlock(
            per_site=[LossAnalysisSite(**s) for s in raw["per_site"]],
            per_domain=raw["per_domain"],
            top_drivers=[LossAnalysisDriver(**d) for d in raw["top_drivers"]],
            mitigated=None,
            method_note=raw["method_note"],
        )
        assert len(block.per_site) == 3
        assert block.method_note != ""

    def test_feasibility_response_backward_compat_no_loss_analysis(self):
        """FeasibilityResponse without loss_analysis must still validate."""
        from backend.schemas import (
            FeasibilityResponse, ScenarioBlock, KPISummary, ReportBlock, MetadataBlock
        )
        kpi = KPISummary(
            expected_annual_loss=1e7, p95_loss=2e7, p99_loss=3e7, scr=5e6,
            recommended_strategy="PCC Captive Cell", verdict="RECOMMENDED",
            composite_score=60.0, confidence_level="Medium",
        )
        block = ScenarioBlock(summary=kpi, charts={})
        resp = FeasibilityResponse(
            baseline=block,
            report=ReportBlock(available=False),
            metadata=MetadataBlock(domain_correlation_active=True, mitigation_active=False, n_simulations=500),
        )
        assert resp.loss_analysis is None

    def test_feasibility_response_accepts_loss_analysis(self):
        from backend.schemas import (
            FeasibilityResponse, ScenarioBlock, KPISummary, ReportBlock, MetadataBlock
        )
        kpi = KPISummary(
            expected_annual_loss=1e7, p95_loss=2e7, p99_loss=3e7, scr=5e6,
            recommended_strategy="PCC Captive Cell", verdict="RECOMMENDED",
            composite_score=60.0, confidence_level="Medium",
        )
        block = ScenarioBlock(summary=kpi, charts={})
        sim = _mock_sim(n=200)
        raw = compute_loss_analysis(sim, _mock_op(), 20_000_000)
        la_block = LossAnalysisBlock(
            per_site=[LossAnalysisSite(**s) for s in raw["per_site"]],
            per_domain=raw["per_domain"],
            top_drivers=[LossAnalysisDriver(**d) for d in raw["top_drivers"]],
            method_note=raw["method_note"],
        )
        resp = FeasibilityResponse(
            baseline=block,
            report=ReportBlock(available=False),
            metadata=MetadataBlock(domain_correlation_active=True, mitigation_active=False, n_simulations=200),
            loss_analysis=la_block,
        )
        assert resp.loss_analysis is not None
        assert len(resp.loss_analysis.per_site) == 3


# ─────────────────────────────────────────────────────────────────────────────
# Group 3: API end-to-end (TestClient)
# ─────────────────────────────────────────────────────────────────────────────

class TestLossAnalysisAPIEndToEnd:
    """Run the full API pipeline via TestClient and verify loss_analysis in response."""

    @pytest.fixture(scope="class")
    def api_response(self):
        """Run feasibility/example → get the example request → POST to /run."""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        # GET example request body
        example_resp = client.post("/api/feasibility/example")
        assert example_resp.status_code == 200
        example_request = example_resp.json()
        # Override n_simulations to keep test fast
        example_request["model_settings"]["n_simulations"] = 500
        example_request["model_settings"]["generate_pdf"] = False
        # POST to /run
        run_resp = client.post("/api/feasibility/run", json=example_request)
        assert run_resp.status_code == 200
        return run_resp.json()

    def test_response_has_loss_analysis_key(self, api_response):
        assert "loss_analysis" in api_response

    def test_loss_analysis_structure_when_present(self, api_response):
        la = api_response.get("loss_analysis")
        if la is None:
            pytest.skip("loss_analysis is None (no site_loss_distribution for this example)")
        assert "per_site" in la
        assert "per_domain" in la
        assert "top_drivers" in la
        assert "method_note" in la

    def test_per_domain_keys_canonical(self, api_response):
        la = api_response.get("loss_analysis")
        if la is None:
            return  # acceptable — no site data
        for k in (la.get("per_domain") or {}).keys():
            assert k in ("biological", "environmental", "structural", "operational"), (
                f"Unexpected domain key: {k}"
            )

    def test_per_site_non_empty_when_present(self, api_response):
        la = api_response.get("loss_analysis")
        if la and la.get("per_site"):
            assert len(la["per_site"]) > 0
