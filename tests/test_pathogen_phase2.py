"""
Tests for PathogenForecaster Phase 2 (network contagion model).
"""
import pytest
from c5ai_plus.data_models.biological_input import (
    PathogenObservation,
    SiteMetadata,
    LiceObservation,
)
from c5ai_plus.forecasting.pathogen_forecaster import PathogenForecaster
from c5ai_plus.ingestion.data_loader import SiteData
from c5ai_plus.network.site_network import SiteRiskNetwork
from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS


def _make_site(site_id="s1", lat=60.0, lon=5.0, lice_obs=None):
    meta = SiteMetadata(
        site_id=site_id,
        site_name=f"Site {site_id}",
        latitude=lat,
        longitude=lon,
        species="Atlantic Salmon",
        biomass_tonnes=1000.0,
        biomass_value_nok=50_000_000,
    )
    return SiteData(
        metadata=meta,
        env_obs=[],
        lice_obs=lice_obs or [],
        hab_alerts=[],
    )


class TestPathogenObservationValidation:
    def test_valid_week(self):
        obs = PathogenObservation(
            site_id="s1", year=2023, week=25,
            pathogen_type="ILA", confirmed=True
        )
        assert obs.week == 25

    def test_invalid_week_zero(self):
        with pytest.raises(ValueError):
            PathogenObservation(
                site_id="s1", year=2023, week=0, pathogen_type="ILA"
            )

    def test_invalid_week_54(self):
        with pytest.raises(ValueError):
            PathogenObservation(
                site_id="s1", year=2023, week=54, pathogen_type="ILA"
            )

    def test_valid_boundary_weeks(self):
        obs1 = PathogenObservation(site_id="s1", year=2023, week=1, pathogen_type="PD")
        obs2 = PathogenObservation(site_id="s1", year=2023, week=53, pathogen_type="PD")
        assert obs1.week == 1
        assert obs2.week == 53


class TestPathogenForecaster:
    def test_no_data_uses_prior(self):
        site = _make_site()
        forecaster = PathogenForecaster()
        forecasts = forecaster.forecast(site, 1)
        expected_prob = C5AI_SETTINGS.pathogen_prior_event_probability
        assert abs(forecasts[0].event_probability - expected_prob) < 1e-4
        assert forecasts[0].model_used == "prior"

    def test_high_lice_increases_probability(self):
        # Many lice exceedance weeks should raise pathogen probability
        high_lice = [
            LiceObservation(site_id="s1", year=2023, week=w, avg_lice_per_fish=1.2)
            for w in range(1, 30)
        ]
        site_high = _make_site(lice_obs=high_lice)
        site_base = _make_site()
        forecaster = PathogenForecaster()
        fc_high = forecaster.forecast(site_high, 1)
        fc_base = forecaster.forecast(site_base, 1)
        assert fc_high[0].event_probability > fc_base[0].event_probability

    def test_treatment_adjusted_model_label(self):
        # Many treated but still exceeding weeks
        treated_lice = [
            LiceObservation(
                site_id="s1", year=2023, week=w,
                avg_lice_per_fish=0.8, treatment_applied=True
            )
            for w in range(1, 15)
        ]
        site = _make_site(lice_obs=treated_lice)
        forecaster = PathogenForecaster()
        forecasts = forecaster.forecast(site, 1)
        assert forecasts[0].model_used in (
            "treatment_adjusted_prior", "network_prior", "prior"
        )

    def test_network_multiplier_increases_probability(self):
        # Two nearby sites: site s1 at (60.0, 5.0) and s2 at (60.01, 5.01) – very close
        nx = pytest.importorskip("networkx", reason="networkx not installed")
        sites = [
            SiteMetadata(
                site_id="s1", site_name="S1",
                latitude=60.0, longitude=5.0,
                species="Salmon", biomass_tonnes=1000,
                biomass_value_nok=50_000_000,
            ),
            SiteMetadata(
                site_id="s2", site_name="S2",
                latitude=60.01, longitude=5.01,
                species="Salmon", biomass_tonnes=1000,
                biomass_value_nok=50_000_000,
            ),
        ]
        network = SiteRiskNetwork(sites, max_distance_km=100)
        site = _make_site(site_id="s1")
        forecaster_with_network = PathogenForecaster(network=network)
        forecaster_no_network = PathogenForecaster()
        fc_net = forecaster_with_network.forecast(site, 1)
        fc_no_net = forecaster_no_network.forecast(site, 1)
        # With nearby neighbour, probability should be >= without network
        assert fc_net[0].event_probability >= fc_no_net[0].event_probability

    def test_network_model_used(self):
        pytest.importorskip("networkx", reason="networkx not installed")
        sites = [
            SiteMetadata(
                site_id="s1", site_name="S1",
                latitude=60.0, longitude=5.0,
                species="Salmon", biomass_tonnes=1000,
                biomass_value_nok=50_000_000,
            ),
            SiteMetadata(
                site_id="s2", site_name="S2",
                latitude=60.01, longitude=5.01,
                species="Salmon", biomass_tonnes=1000,
                biomass_value_nok=50_000_000,
            ),
        ]
        network = SiteRiskNetwork(sites, max_distance_km=100)
        site = _make_site(site_id="s1")
        forecaster = PathogenForecaster(network=network)
        forecasts = forecaster.forecast(site, 1)
        # Should be network_prior when connected neighbours exist
        assert forecasts[0].model_used == "network_prior"

    def test_observation_based_model(self):
        site = _make_site()
        site.pathogen_obs = [
            PathogenObservation(
                site_id="s1", year=2022, week=10,
                pathogen_type="ILA", confirmed=True, mortality_rate=0.15
            ),
            PathogenObservation(
                site_id="s1", year=2021, week=20,
                pathogen_type="ILA", confirmed=True, mortality_rate=0.10
            ),
        ]
        forecaster = PathogenForecaster()
        forecasts = forecaster.forecast(site, 1)
        assert forecasts[0].model_used == "observation_based"

    def test_probability_bounded(self):
        high_lice = [
            LiceObservation(site_id="s1", year=2023, week=w, avg_lice_per_fish=5.0)
            for w in range(1, 53)
        ]
        site = _make_site(lice_obs=high_lice)
        forecaster = PathogenForecaster()
        forecasts = forecaster.forecast(site, 1)
        assert 0.0 <= forecasts[0].event_probability <= 1.0

    def test_forecast_length(self):
        site = _make_site()
        forecaster = PathogenForecaster()
        forecasts = forecaster.forecast(site, 5)
        assert len(forecasts) == 5
