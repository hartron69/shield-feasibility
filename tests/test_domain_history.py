"""
Comprehensive tests for domain-linked historical loss analytics (Phases 1–7).

Sample dataset (from data/sample_input.json):
  mortality (biological):             2019:8.6M, 2020:25.2M, 2021:3.3M,
                                      2022:17.3M+10.3M, 2023:5.7M  → 6 events, 70.4M
  property (structural):              2019:2.0M, 2021:7.6M, 2023:3.0M → 3 events, 12.6M
  business_interruption (operational):2020:4.7M, 2023:4.0M            → 2 events, 8.7M
  Total: 11 events, 91.7M, 5 years (2019–2023)
"""
import pytest
from backend.schemas import (
    HISTORY_DOMAIN_MAP,
    HistoricalDomainSummary,
    HistoricalLossSummary,
    HistoryEventRow,
)
from backend.services.history_analytics import (
    build_historical_loss_summary,
    build_history_event_rows,
    compute_domain_calibration_params,
    compute_domain_summaries,
    compute_portfolio_calibration_params,
    map_event_to_domain,
    ORDERED_DOMAINS,
)
from backend.services.operator_builder import load_template_history

# ── Exact expected values from sample data ────────────────────────────────────
_BIOLOGICAL_GROSS = 70_400_000.0   # 8.6+25.2+3.3+17.3+10.3+5.7
_STRUCTURAL_GROSS  = 12_600_000.0   # 2.0+7.6+3.0
_OPERATIONAL_GROSS =  8_700_000.0   # 4.7+4.0
_TOTAL_GROSS       = 91_700_000.0
_N_RECORDS         = 11
_N_YEARS           = 5


# ── Phase 1: Domain mapping ───────────────────────────────────────────────────

class TestDomainMapping:
    def test_mortality_maps_to_biological(self):
        assert map_event_to_domain("mortality") == "biological"

    def test_property_maps_to_structural(self):
        assert map_event_to_domain("property") == "structural"

    def test_business_interruption_maps_to_operational(self):
        assert map_event_to_domain("business_interruption") == "operational"

    def test_unknown_event_type_maps_to_unknown(self):
        assert map_event_to_domain("flood") == "unknown"
        assert map_event_to_domain("") == "unknown"
        assert map_event_to_domain("MORTALITY") == "unknown"  # case-sensitive

    def test_history_domain_map_constant_has_correct_keys(self):
        assert "mortality" in HISTORY_DOMAIN_MAP
        assert "property" in HISTORY_DOMAIN_MAP
        assert "business_interruption" in HISTORY_DOMAIN_MAP

    def test_history_domain_map_values_are_valid_domains(self):
        valid = {"biological", "structural", "environmental", "operational"}
        for v in HISTORY_DOMAIN_MAP.values():
            assert v in valid


# ── Phase 1: build_history_event_rows ────────────────────────────────────────

class TestBuildHistoryEventRows:
    @pytest.fixture
    def raw_records(self):
        return load_template_history()

    @pytest.fixture
    def rows_and_warnings(self, raw_records):
        return build_history_event_rows(raw_records)

    def test_returns_correct_count(self, rows_and_warnings):
        rows, _ = rows_and_warnings
        assert len(rows) == _N_RECORDS

    def test_all_rows_are_history_event_row(self, rows_and_warnings):
        rows, _ = rows_and_warnings
        for r in rows:
            assert isinstance(r, HistoryEventRow)

    def test_domain_field_populated(self, rows_and_warnings):
        rows, _ = rows_and_warnings
        for r in rows:
            assert r.domain in {"biological", "structural", "operational", "environmental", "unknown"}

    def test_mortality_rows_are_biological(self, rows_and_warnings):
        rows, _ = rows_and_warnings
        mortality_rows = [r for r in rows if r.event_type == "mortality"]
        assert all(r.domain == "biological" for r in mortality_rows)

    def test_property_rows_are_structural(self, rows_and_warnings):
        rows, _ = rows_and_warnings
        property_rows = [r for r in rows if r.event_type == "property"]
        assert all(r.domain == "structural" for r in property_rows)

    def test_business_interruption_rows_are_operational(self, rows_and_warnings):
        rows, _ = rows_and_warnings
        bi_rows = [r for r in rows if r.event_type == "business_interruption"]
        assert all(r.domain == "operational" for r in bi_rows)

    def test_no_warnings_for_known_event_types(self, rows_and_warnings):
        _, warnings = rows_and_warnings
        assert warnings == []

    def test_unknown_event_type_generates_warning(self):
        raw = [{"year": 2020, "event_type": "flood", "gross_loss": 1e6,
                "insured_loss": 0.8e6, "retained_loss": 0.2e6}]
        rows, warnings = build_history_event_rows(raw)
        assert rows[0].domain == "unknown"
        assert len(warnings) == 1
        assert "flood" in warnings[0]
        assert "2020" in warnings[0]

    def test_explicit_domain_override_respected(self):
        """If raw record has a 'domain' field with a valid value, it is used."""
        raw = [{"year": 2021, "event_type": "mortality", "domain": "environmental",
                "gross_loss": 1e6, "insured_loss": 0.5e6, "retained_loss": 0.5e6}]
        rows, warnings = build_history_event_rows(raw)
        assert rows[0].domain == "environmental"
        assert warnings == []

    def test_invalid_explicit_domain_falls_back_to_mapping(self):
        """Unknown 'domain' override falls back to event_type mapping."""
        raw = [{"year": 2021, "event_type": "mortality", "domain": "weather",
                "gross_loss": 1e6, "insured_loss": 0.5e6, "retained_loss": 0.5e6}]
        rows, warnings = build_history_event_rows(raw)
        assert rows[0].domain == "biological"


# ── Phase 2: compute_domain_summaries ────────────────────────────────────────

class TestComputeDomainSummaries:
    @pytest.fixture
    def rows(self):
        raw = load_template_history()
        rows, _ = build_history_event_rows(raw)
        return rows

    @pytest.fixture
    def summaries(self, rows):
        return compute_domain_summaries(rows, _N_YEARS, _TOTAL_GROSS)

    def test_returns_three_domains(self, summaries):
        assert len(summaries) == 3

    def test_domain_order_follows_ordered_domains(self, summaries):
        """biological < structural < operational in ORDERED_DOMAINS."""
        names = [s.domain for s in summaries]
        assert names == ["biological", "structural", "operational"]

    def test_biological_event_count(self, summaries):
        bio = next(s for s in summaries if s.domain == "biological")
        assert bio.event_count == 6

    def test_biological_total_gross(self, summaries):
        bio = next(s for s in summaries if s.domain == "biological")
        assert bio.total_gross_loss == pytest.approx(_BIOLOGICAL_GROSS)

    def test_structural_event_count(self, summaries):
        struct = next(s for s in summaries if s.domain == "structural")
        assert struct.event_count == 3

    def test_structural_total_gross(self, summaries):
        struct = next(s for s in summaries if s.domain == "structural")
        assert struct.total_gross_loss == pytest.approx(_STRUCTURAL_GROSS)

    def test_operational_event_count(self, summaries):
        ops = next(s for s in summaries if s.domain == "operational")
        assert ops.event_count == 2

    def test_operational_total_gross(self, summaries):
        ops = next(s for s in summaries if s.domain == "operational")
        assert ops.total_gross_loss == pytest.approx(_OPERATIONAL_GROSS)

    def test_loss_share_sums_to_100(self, summaries):
        total_share = sum(s.loss_share_pct for s in summaries)
        assert total_share == pytest.approx(100.0, abs=0.01)

    def test_biological_mean_severity(self, summaries):
        bio = next(s for s in summaries if s.domain == "biological")
        expected = _BIOLOGICAL_GROSS / 6
        assert bio.mean_severity == pytest.approx(expected)

    def test_average_annual_loss_uses_full_window(self, summaries):
        """events_per_year should divide by n_years=5, not by years-with-events."""
        # Structural appears in 3 years but n_years is 5
        struct = next(s for s in summaries if s.domain == "structural")
        assert struct.events_per_year == pytest.approx(3 / 5)

    def test_operational_events_per_year(self, summaries):
        ops = next(s for s in summaries if s.domain == "operational")
        assert ops.events_per_year == pytest.approx(2 / 5)

    def test_structural_years_with_events(self, summaries):
        struct = next(s for s in summaries if s.domain == "structural")
        assert set(struct.years_with_events) == {2019, 2021, 2023}

    def test_unknown_domain_appended_last(self):
        raw = [
            {"year": 2020, "event_type": "mortality", "gross_loss": 1e6, "insured_loss": 0.8e6, "retained_loss": 0.2e6},
            {"year": 2020, "event_type": "flood",     "gross_loss": 2e6, "insured_loss": 1.5e6, "retained_loss": 0.5e6},
        ]
        rows, _ = build_history_event_rows(raw)
        summaries = compute_domain_summaries(rows, 1, 3e6)
        assert summaries[-1].domain == "unknown"


# ── Phase 3: portfolio calibration ───────────────────────────────────────────

class TestPortfolioCalibration:
    @pytest.fixture
    def rows(self):
        raw = load_template_history()
        rows, _ = build_history_event_rows(raw)
        return rows

    def test_mean_loss_severity(self, rows):
        params = compute_portfolio_calibration_params(rows, _N_YEARS)
        expected = round(_TOTAL_GROSS / _N_RECORDS)
        assert params["mean_loss_severity"] == expected

    def test_expected_annual_events(self, rows):
        params = compute_portfolio_calibration_params(rows, _N_YEARS)
        assert params["expected_annual_events"] == pytest.approx(_N_RECORDS / _N_YEARS, abs=0.001)

    def test_empty_records_returns_empty(self):
        params = compute_portfolio_calibration_params([], 5)
        assert params == {}

    def test_zero_years_returns_empty(self, rows):
        params = compute_portfolio_calibration_params(rows, 0)
        assert params == {}


# ── Phase 6: domain calibration scaffold ─────────────────────────────────────

class TestDomainCalibrationScaffold:
    @pytest.fixture
    def rows(self):
        raw = load_template_history()
        rows, _ = build_history_event_rows(raw)
        return rows

    def test_returns_per_domain_keys(self, rows):
        params = compute_domain_calibration_params(rows, _N_YEARS)
        for domain in ("biological", "structural", "operational"):
            assert f"{domain}_mean_severity" in params
            assert f"{domain}_events_per_year" in params
            assert f"{domain}_annual_loss_mean" in params

    def test_biological_events_per_year(self, rows):
        params = compute_domain_calibration_params(rows, _N_YEARS)
        assert params["biological_events_per_year"] == pytest.approx(6 / 5)

    def test_structural_mean_severity(self, rows):
        params = compute_domain_calibration_params(rows, _N_YEARS)
        expected = round(_STRUCTURAL_GROSS / 3)
        assert params["structural_mean_severity"] == expected

    def test_operational_annual_loss_mean(self, rows):
        params = compute_domain_calibration_params(rows, _N_YEARS)
        expected = round(_OPERATIONAL_GROSS / _N_YEARS)
        assert params["operational_annual_loss_mean"] == expected

    def test_empty_returns_empty(self):
        assert compute_domain_calibration_params([], 5) == {}


# ── Phase 3: build_historical_loss_summary ────────────────────────────────────

class TestBuildHistoricalLossSummary:
    @pytest.fixture
    def raw_records(self):
        return load_template_history()

    @pytest.fixture
    def summary(self, raw_records):
        return build_historical_loss_summary(
            raw_records=raw_records,
            calibration_active=False,
            calibration_mode="none",
            alloc_calibrated_params={},
        )

    def test_returns_historical_loss_summary(self, summary):
        assert isinstance(summary, HistoricalLossSummary)

    def test_history_loaded(self, summary):
        assert summary.history_loaded is True

    def test_record_count(self, summary):
        assert summary.record_count == _N_RECORDS

    def test_years_covered(self, summary):
        assert summary.years_covered == [2019, 2020, 2021, 2022, 2023]

    def test_n_years_observed(self, summary):
        assert summary.n_years_observed == _N_YEARS

    def test_portfolio_total_gross(self, summary):
        assert summary.portfolio_total_gross == pytest.approx(_TOTAL_GROSS)

    def test_portfolio_mean_severity(self, summary):
        assert summary.portfolio_mean_severity == pytest.approx(_TOTAL_GROSS / _N_RECORDS)

    def test_portfolio_events_per_year(self, summary):
        assert summary.portfolio_events_per_year == pytest.approx(_N_RECORDS / _N_YEARS)

    def test_has_three_domain_summaries(self, summary):
        assert len(summary.domain_summaries) == 3

    def test_no_mapping_warnings_for_sample_data(self, summary):
        assert summary.mapping_warnings == []

    def test_records_have_domain_field(self, summary):
        for r in summary.records:
            assert r.domain in {"biological", "structural", "operational"}

    def test_calibration_mode_none(self, summary):
        assert summary.calibration_mode == "none"
        assert summary.calibration_source == "none"
        assert summary.calibration_active is False

    def test_calibration_mode_portfolio(self, raw_records):
        params = {"mean_loss_severity": 8_336_364.0, "expected_annual_events": 2.2}
        s = build_historical_loss_summary(
            raw_records=raw_records,
            calibration_active=True,
            calibration_mode="portfolio",
            alloc_calibrated_params=params,
        )
        assert s.calibration_mode == "portfolio"
        assert s.calibration_source == "historical_loss_records"
        assert s.calibration_active is True
        assert s.calibrated_parameters == params

    def test_empty_records_returns_not_loaded(self):
        s = build_historical_loss_summary(
            raw_records=[],
            calibration_active=False,
            calibration_mode="none",
            alloc_calibrated_params={},
        )
        assert s.history_loaded is False
        assert s.record_count == 0
        assert s.domain_summaries == []


# ── Schema compatibility ──────────────────────────────────────────────────────

class TestSchemaCompat:
    def test_feasibility_response_history_field_type(self):
        """FeasibilityResponse.history must accept HistoricalLossSummary."""
        from backend.schemas import FeasibilityResponse
        import inspect
        annotation = FeasibilityResponse.model_fields["history"].annotation
        # Optional[HistoricalLossSummary] — check the inner type
        args = getattr(annotation, "__args__", (annotation,))
        assert any(a is HistoricalLossSummary for a in args)

    def test_history_event_row_has_domain_field(self):
        row = HistoryEventRow(
            year=2020, event_type="mortality", domain="biological",
            gross_loss=1e6, insured_loss=0.8e6, retained_loss=0.2e6,
        )
        assert row.domain == "biological"

    def test_historical_domain_summary_fields(self):
        ds = HistoricalDomainSummary(
            domain="biological", event_count=6,
            total_gross_loss=70_400_000.0, total_insured_loss=60_000_000.0,
            total_retained_loss=10_400_000.0, mean_severity=11_733_333.0,
            events_per_year=1.2, loss_share_pct=76.8,
            years_with_events=[2019, 2020, 2021, 2022, 2023],
        )
        assert ds.domain == "biological"
        assert ds.event_count == 6

    def test_allocation_summary_has_calibration_mode(self):
        from backend.schemas import AllocationSummary, SiteAllocationRow
        a = AllocationSummary(
            template_exposure_nok=1.0, user_exposure_nok=1.0, tiv_ratio=1.0,
            risk_severity_scaled=1.0, risk_events_scaled=1.0, financial_ratios={}, sites=[],
        )
        assert hasattr(a, "calibration_mode")
        assert a.calibration_mode == "none"

    def test_history_domain_map_is_exported(self):
        from backend.schemas import HISTORY_DOMAIN_MAP
        assert isinstance(HISTORY_DOMAIN_MAP, dict)
        assert len(HISTORY_DOMAIN_MAP) >= 3


# ── Operator builder integration ──────────────────────────────────────────────

class TestOperatorBuilderIntegration:
    @pytest.fixture
    def default_profile(self):
        from backend.schemas import OperatorProfileInput
        return OperatorProfileInput()

    def test_calibration_mode_none_when_off(self, default_profile):
        from backend.services.operator_builder import build_operator_input
        _, alloc = build_operator_input(default_profile, use_history_calibration=False)
        assert alloc.calibration_mode == "none"

    def test_calibration_mode_portfolio_when_on(self, default_profile):
        from backend.services.operator_builder import build_operator_input
        _, alloc = build_operator_input(default_profile, use_history_calibration=True)
        assert alloc.calibration_mode == "portfolio"
        assert alloc.calibration_active is True

    def test_calibration_mode_propagates_to_history_summary(self, default_profile):
        from backend.services.operator_builder import build_operator_input, load_template_history
        _, alloc = build_operator_input(default_profile, use_history_calibration=True)
        raw = load_template_history()
        s = build_historical_loss_summary(
            raw_records=raw,
            calibration_active=alloc.calibration_active,
            calibration_mode=alloc.calibration_mode,
            alloc_calibrated_params=alloc.calibrated_parameters,
        )
        assert s.calibration_mode == "portfolio"
        assert s.calibration_active is True


# ── End-to-end numerical correctness ─────────────────────────────────────────

class TestNumericalCorrectness:
    """Verify exact values from sample_input.json domain split."""

    @pytest.fixture
    def summary(self):
        raw = load_template_history()
        return build_historical_loss_summary(
            raw_records=raw,
            calibration_active=False,
            calibration_mode="none",
            alloc_calibrated_params={},
        )

    def test_biological_gross_exact(self, summary):
        bio = next(s for s in summary.domain_summaries if s.domain == "biological")
        assert bio.total_gross_loss == 70_400_000.0

    def test_structural_gross_exact(self, summary):
        struct = next(s for s in summary.domain_summaries if s.domain == "structural")
        assert struct.total_gross_loss == 12_600_000.0

    def test_operational_gross_exact(self, summary):
        ops = next(s for s in summary.domain_summaries if s.domain == "operational")
        assert ops.total_gross_loss == 8_700_000.0

    def test_biological_loss_share(self, summary):
        bio = next(s for s in summary.domain_summaries if s.domain == "biological")
        expected_pct = 70_400_000 / 91_700_000 * 100
        assert bio.loss_share_pct == pytest.approx(expected_pct, abs=0.01)

    def test_structural_events_per_year(self, summary):
        struct = next(s for s in summary.domain_summaries if s.domain == "structural")
        assert struct.events_per_year == pytest.approx(0.6, abs=0.001)

    def test_portfolio_mean_severity(self, summary):
        expected = 91_700_000 / 11
        assert summary.portfolio_mean_severity == pytest.approx(expected, abs=1)

    def test_portfolio_events_per_year(self, summary):
        assert summary.portfolio_events_per_year == pytest.approx(2.2, abs=0.001)
