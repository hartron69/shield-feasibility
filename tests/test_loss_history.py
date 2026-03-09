"""
Tests for loss history display (Step 1) and calibration toggle (Step 2).

Template has 11 historical loss records spanning 2019-2023 (5 distinct years).
"""
import pytest
from backend.schemas import OperatorProfileInput
from backend.services.operator_builder import (
    build_operator_input,
    load_template_history,
    _MIN_HISTORY_RECORDS,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def default_profile():
    return OperatorProfileInput()


# ── load_template_history ─────────────────────────────────────────────────────

class TestLoadTemplateHistory:
    def test_returns_list(self):
        records = load_template_history()
        assert isinstance(records, list)

    def test_has_expected_count(self):
        # Template has 11 records
        records = load_template_history()
        assert len(records) == 11

    def test_record_fields(self):
        records = load_template_history()
        for r in records:
            assert "year" in r
            assert "event_type" in r
            assert "gross_loss" in r
            assert "insured_loss" in r
            assert "retained_loss" in r

    def test_years_span(self):
        records = load_template_history()
        years = {r["year"] for r in records}
        assert years == {2019, 2020, 2021, 2022, 2023}

    def test_gross_loss_positive(self):
        records = load_template_history()
        for r in records:
            assert r["gross_loss"] > 0


# ── Step 1: display-only (calibration OFF) ────────────────────────────────────

class TestHistoryDisplayOnly:
    def test_calibration_off_by_default(self, default_profile):
        _, alloc = build_operator_input(default_profile, use_history_calibration=False)
        assert alloc.calibration_active is False

    def test_calibration_off_empty_params(self, default_profile):
        _, alloc = build_operator_input(default_profile, use_history_calibration=False)
        assert alloc.calibrated_parameters == {}

    def test_tiv_scaling_used_when_calibration_off(self, default_profile):
        _, alloc = build_operator_input(default_profile, use_history_calibration=False)
        # TIV ratio = user_exposure / template_exposure; default is 64800 NOK/t not 72000, so ≠ 1.0
        from backend.services.operator_builder import _TEMPLATE_SEVERITY, _TEMPLATE_EXPOSURE
        tiv_ratio = default_profile.total_biomass_tonnes * default_profile.biomass_value_per_tonne / _TEMPLATE_EXPOSURE
        assert alloc.risk_severity_scaled == round(_TEMPLATE_SEVERITY * tiv_ratio)

    def test_default_events_scaling(self, default_profile):
        """Default profile has n_sites=3 (= template), so events = _TEMPLATE_EVENTS."""
        _, alloc = build_operator_input(default_profile, use_history_calibration=False)
        from backend.services.operator_builder import _TEMPLATE_EVENTS
        assert alloc.risk_events_scaled == pytest.approx(_TEMPLATE_EVENTS, abs=0.001)


# ── Step 2: calibration ON ────────────────────────────────────────────────────

class TestHistoryCalibrationOn:
    def test_calibration_active_flag(self, default_profile):
        _, alloc = build_operator_input(default_profile, use_history_calibration=True)
        assert alloc.calibration_active is True

    def test_calibrated_parameters_keys(self, default_profile):
        _, alloc = build_operator_input(default_profile, use_history_calibration=True)
        assert "mean_loss_severity" in alloc.calibrated_parameters
        assert "expected_annual_events" in alloc.calibrated_parameters

    def test_calibrated_severity_equals_mean_gross_loss(self, default_profile):
        records = load_template_history()
        expected_severity = round(
            sum(r["gross_loss"] for r in records) / len(records)
        )
        _, alloc = build_operator_input(default_profile, use_history_calibration=True)
        assert alloc.risk_severity_scaled == expected_severity
        assert alloc.calibrated_parameters["mean_loss_severity"] == float(expected_severity)

    def test_calibrated_events_equals_records_per_year(self, default_profile):
        records = load_template_history()
        n_years = len({r["year"] for r in records})
        expected_events = round(len(records) / n_years, 4)
        _, alloc = build_operator_input(default_profile, use_history_calibration=True)
        assert alloc.risk_events_scaled == pytest.approx(expected_events, abs=0.001)
        assert alloc.calibrated_parameters["expected_annual_events"] == pytest.approx(
            expected_events, abs=0.001
        )

    def test_calibration_overrides_tiv_scaling(self, default_profile):
        """When calibration ON, severity should differ from TIV-scaled value."""
        _, alloc_cal = build_operator_input(default_profile, use_history_calibration=True)
        _, alloc_tiv = build_operator_input(default_profile, use_history_calibration=False)
        # Template has specific historical values that differ from TIV-scaled template constant
        # (11 events, mean ~8.3M vs template 7.1M)
        assert alloc_cal.risk_severity_scaled != alloc_tiv.risk_severity_scaled

    def test_calibration_does_not_affect_financials(self, default_profile):
        """Financial ratios are independent of calibration mode."""
        _, alloc_cal = build_operator_input(default_profile, use_history_calibration=True)
        _, alloc_tiv = build_operator_input(default_profile, use_history_calibration=False)
        assert alloc_cal.financial_ratios == alloc_tiv.financial_ratios

    def test_calibration_does_not_affect_site_allocation(self, default_profile):
        """Site biomass / equipment allocation is independent of calibration mode."""
        _, alloc_cal = build_operator_input(default_profile, use_history_calibration=True)
        _, alloc_tiv = build_operator_input(default_profile, use_history_calibration=False)
        assert len(alloc_cal.sites) == len(alloc_tiv.sites)
        for sc, st in zip(alloc_cal.sites, alloc_tiv.sites):
            assert sc.biomass_tonnes == st.biomass_tonnes
            assert sc.equipment_value_nok == st.equipment_value_nok

    def test_calibration_propagates_to_operator_input(self, default_profile):
        """The risk_params in the built OperatorInput reflect the calibrated values."""
        records = load_template_history()
        expected_severity = round(sum(r["gross_loss"] for r in records) / len(records))

        operator, _ = build_operator_input(default_profile, use_history_calibration=True)
        assert operator.risk_params.mean_loss_severity == expected_severity


# ── MIN_HISTORY_RECORDS guard ─────────────────────────────────────────────────

class TestMinHistoryGuard:
    def test_constant_is_three(self):
        assert _MIN_HISTORY_RECORDS == 3

    def test_template_has_enough_records(self):
        """Template must have at least _MIN_HISTORY_RECORDS to trigger calibration."""
        records = load_template_history()
        assert len(records) >= _MIN_HISTORY_RECORDS


# ── API-level integration ─────────────────────────────────────────────────────

class TestAPIIntegration:
    def test_history_calibration_field_in_model_settings(self):
        from backend.schemas import ModelSettingsInput
        m = ModelSettingsInput()
        assert hasattr(m, "use_history_calibration")
        assert m.use_history_calibration is False

    def test_history_calibration_can_be_enabled(self):
        from backend.schemas import ModelSettingsInput
        m = ModelSettingsInput(use_history_calibration=True)
        assert m.use_history_calibration is True

    def test_history_summary_fields(self):
        from backend.schemas import HistorySummary, HistoryEventRow
        hs = HistorySummary(
            history_loaded=True,
            history_source="template",
            record_count=11,
            years_covered=[2019, 2020, 2021, 2022, 2023],
            calibration_active=False,
            calibration_source="none",
            calibrated_parameters={},
            records=[
                HistoryEventRow(
                    year=2019, event_type="mortality", domain="biological",
                    gross_loss=8_600_000, insured_loss=7_000_000, retained_loss=1_600_000,
                )
            ],
        )
        assert hs.history_loaded is True
        assert hs.record_count == 11
        assert len(hs.records) == 1

    def test_feasibility_response_has_history_field(self):
        from backend.schemas import FeasibilityResponse, HistoricalLossSummary
        fields = FeasibilityResponse.model_fields
        assert "history" in fields
        # Verify the field accepts HistoricalLossSummary
        annotation = fields["history"].annotation
        args = getattr(annotation, "__args__", (annotation,))
        assert any(a is HistoricalLossSummary for a in args)
