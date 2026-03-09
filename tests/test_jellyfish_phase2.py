"""
Tests for JellyfishForecaster Phase 2 (temperature-sensitive prior).
"""
import pytest
from c5ai_plus.data_models.biological_input import (
    JellyfishObservation,
    SiteMetadata,
    EnvironmentalObservation,
)
from c5ai_plus.forecasting.jellyfish_forecaster import JellyfishForecaster
from c5ai_plus.ingestion.data_loader import SiteData
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS


def _make_site(summer_temp: float = 14.0, months=(7, 8, 9)):
    meta = SiteMetadata(
        site_id="test_site",
        site_name="Test Site",
        latitude=60.0,
        longitude=5.0,
        species="Atlantic Salmon",
        biomass_tonnes=1000.0,
        biomass_value_nok=50_000_000,
    )
    env_obs = [
        EnvironmentalObservation(
            site_id="test_site",
            year=2023,
            month=m,
            sea_temp_celsius=summer_temp,
        )
        for m in months
    ]
    return SiteData(metadata=meta, env_obs=env_obs, lice_obs=[], hab_alerts=[])


class TestJellyfishObservationValidation:
    def test_valid_month(self):
        obs = JellyfishObservation(site_id="s1", year=2023, month=7, density_index=1.5)
        assert obs.month == 7

    def test_invalid_month_raises(self):
        with pytest.raises(ValueError):
            JellyfishObservation(site_id="s1", year=2023, month=0)

    def test_invalid_month_13_raises(self):
        with pytest.raises(ValueError):
            JellyfishObservation(site_id="s1", year=2023, month=13)

    def test_valid_month_boundary(self):
        obs = JellyfishObservation(site_id="s1", year=2023, month=12)
        assert obs.month == 12


class TestJellyfishForecaster:
    def test_no_temp_data_uses_prior(self):
        meta = SiteMetadata(
            site_id="s0", site_name="No Data",
            latitude=60.0, longitude=5.0,
            species="Salmon", biomass_tonnes=500,
            biomass_value_nok=25_000_000,
        )
        site = SiteData(metadata=meta, env_obs=[], lice_obs=[], hab_alerts=[])
        forecaster = JellyfishForecaster()
        forecasts = forecaster.forecast(site, 3)
        assert len(forecasts) == 3
        # With no data, should use base prior probability
        expected_prob = C5AI_SETTINGS.jellyfish_prior_event_probability
        assert abs(forecasts[0].event_probability - expected_prob) < 1e-4
        assert forecasts[0].model_used == "prior"

    def test_warm_summer_increases_probability(self):
        # Site with cold summer (<12°C) vs warm (>16°C)
        site_cold = _make_site(summer_temp=10.0)
        site_warm = _make_site(summer_temp=18.0)
        forecaster = JellyfishForecaster()
        fc_cold = forecaster.forecast(site_cold, 1)
        fc_warm = forecaster.forecast(site_warm, 1)
        assert fc_warm[0].event_probability > fc_cold[0].event_probability

    def test_warm_summer_model_used(self):
        site = _make_site(summer_temp=18.0)
        forecaster = JellyfishForecaster()
        forecasts = forecaster.forecast(site, 2)
        assert forecasts[0].model_used == "temp_adjusted_prior"

    def test_cold_summer_no_uplift(self):
        site = _make_site(summer_temp=8.0)
        forecaster = JellyfishForecaster()
        forecasts = forecaster.forecast(site, 1)
        base = C5AI_SETTINGS.jellyfish_prior_event_probability
        assert abs(forecasts[0].event_probability - base) < 1e-4

    def test_probability_capped_at_1(self):
        # Extreme temperature should not push probability above 1.0
        site = _make_site(summer_temp=40.0)
        forecaster = JellyfishForecaster()
        forecasts = forecaster.forecast(site, 1)
        assert forecasts[0].event_probability <= 1.0

    def test_jellyfish_obs_increases_probability(self):
        site = _make_site(summer_temp=14.0)
        # Add jellyfish observations with high density
        site.jellyfish_obs = [
            JellyfishObservation(site_id="test_site", year=2023, month=8, density_index=2.5)
        ]
        forecaster = JellyfishForecaster()
        # Compare with same site but no jellyfish obs
        site_no_obs = _make_site(summer_temp=14.0)
        fc_with_obs = forecaster.forecast(site, 1)
        fc_no_obs = forecaster.forecast(site_no_obs, 1)
        assert fc_with_obs[0].event_probability >= fc_no_obs[0].event_probability

    def test_observation_adjusted_model_used(self):
        site = _make_site(summer_temp=14.0)
        site.jellyfish_obs = [
            JellyfishObservation(site_id="test_site", year=2023, month=7, density_index=1.0)
        ]
        forecaster = JellyfishForecaster()
        forecasts = forecaster.forecast(site, 1)
        assert forecasts[0].model_used == "observation_adjusted_prior"

    def test_forecast_returns_correct_years(self):
        site = _make_site(14.0)
        forecaster = JellyfishForecaster()
        forecasts = forecaster.forecast(site, 5)
        assert len(forecasts) == 5
        assert all(fc.risk_type == "jellyfish" for fc in forecasts)

    def test_expected_loss_positive(self):
        site = _make_site(14.0)
        forecaster = JellyfishForecaster()
        forecasts = forecaster.forecast(site, 1)
        assert forecasts[0].expected_loss_mean >= 0.0
