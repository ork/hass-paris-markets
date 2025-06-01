"""Test the Paris Markets coordinator."""

from datetime import time
from types import MappingProxyType
from unittest.mock import MagicMock, patch

import pytest
import pytz
import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.paris_markets.const import (
    CONF_ARRONDISSEMENTS,
    CONF_FILTER_MODE,
    CONF_PRODUCT_TYPES,
    CONF_RADIUS,
    DOMAIN,
    FilterMode,
)
from custom_components.paris_markets.coordinator import (
    ParisMarketsDataUpdateCoordinator,
)

pytestmark = pytest.mark.asyncio


def _paris_time(time_str: str) -> time:
    """Helper function to create timezone-aware time objects for Paris timezone."""
    if not time_str:
        return None

    paris_tz = pytz.timezone("Europe/Paris")
    hour, minute = time_str.split(":")
    return time(int(hour), int(minute), tzinfo=paris_tz)


@pytest.fixture
def coordinator(hass: HomeAssistant):
    """Create a coordinator for testing."""

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Paris Markets",
        data={
            CONF_FILTER_MODE: FilterMode.RADIUS.value,
            CONF_RADIUS: 5.0,
            CONF_PRODUCT_TYPES: ["Alimentaire"],
        },
        source="user",
        entry_id="test",
        unique_id=None,
        discovery_keys=MappingProxyType({}),
        options={},
        subentries_data=[],
    )
    return ParisMarketsDataUpdateCoordinator(hass, entry)


@pytest.fixture
def coordinator_arrondissement(hass: HomeAssistant):
    """Create a coordinator for arrondissement testing."""

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Paris Markets",
        data={
            CONF_FILTER_MODE: FilterMode.ARRONDISSEMENT.value,
            CONF_ARRONDISSEMENTS: ["75001", "75002"],
            CONF_PRODUCT_TYPES: ["Alimentaire"],
        },
        source="user",
        entry_id="test",
        unique_id=None,
        discovery_keys=MappingProxyType({}),
        options={},
        subentries_data=[],
    )
    return ParisMarketsDataUpdateCoordinator(hass, entry)


async def test_coordinator_successful_update(hass: HomeAssistant, coordinator):
    """Test successful data update."""
    mock_response_data = {
        "results": [
            {
                "id_marche": "1",
                "nom_long": "Test Market",
                "nom_court": "test",
                "ardt": "75001",
                "localisation": "Test Location",
                "produit": "Alimentaire",
                "h_deb_sem_1": "08:00",
                "h_fin_sem_1": "14:00",
                "h_deb_sam": "08:00",
                "h_fin_sam": "15:00",
                "h_deb_dim": "",
                "h_fin_dim": "",
                "lundi": 0,
                "mardi": 1,
                "mercredi": 0,
                "jeudi": 1,
                "vendredi": 0,
                "samedi": 1,
                "dimanche": 0,
                "geo_point_2d": {"lat": 48.8566, "lon": 2.3522},
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    async def mock_executor_job(func, *args, **kwargs):
        """Mock the async_add_executor_job to call function directly."""
        return func(*args, **kwargs)

    with (
        patch.object(hass, "async_add_executor_job", side_effect=mock_executor_job),
        patch(
            "custom_components.paris_markets.coordinator.requests.get",
            return_value=mock_response,
        ),
    ):
        result = await coordinator._async_update_data()

        assert len(result) == 1
        assert "1" in result
        assert result["1"]["long_name"] == "Test Market"


async def test_coordinator_api_error(hass: HomeAssistant, coordinator):
    """Test API error handling."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "API Error"
    )

    with patch(
        "custom_components.paris_markets.coordinator.requests.get",
        return_value=mock_response,
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_coordinator_network_error(hass: HomeAssistant, coordinator):
    """Test network error handling."""
    with patch("custom_components.paris_markets.coordinator.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_coordinator_no_location_configured(hass: HomeAssistant):
    """Test coordinator when Home Assistant location is not configured."""

    hass.config.latitude = None
    hass.config.longitude = None

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Paris Markets",
        data={
            CONF_FILTER_MODE: FilterMode.RADIUS.value,
            CONF_RADIUS: 5.0,
            CONF_PRODUCT_TYPES: ["Alimentaire"],
        },
        source="user",
        entry_id="test",
        unique_id=None,
        discovery_keys=MappingProxyType({}),
        options={},
        subentries_data=[],
    )

    coordinator = ParisMarketsDataUpdateCoordinator(hass, entry)

    with pytest.raises(UpdateFailed, match="Home Assistant location not configured"):
        await coordinator._async_update_data()


async def test_coordinator_arrondissement_filtering(
    hass: HomeAssistant, coordinator_arrondissement
):
    """Test successful data update with arrondissement filtering."""
    mock_response_data = {
        "results": [
            {
                "id_marche": "1",
                "nom_long": "Test Market",
                "nom_court": "test",
                "ardt": 1,  # Integer arrondissement number
                "localisation": "Test Location",
                "produit": "Alimentaire",
                "h_deb_sem_1": "08:00",
                "h_fin_sem_1": "14:00",
                "h_deb_sam": "08:00",
                "h_fin_sam": "15:00",
                "h_deb_dim": "",
                "h_fin_dim": "",
                "lundi": 0,
                "mardi": 1,
                "mercredi": 0,
                "jeudi": 1,
                "vendredi": 0,
                "samedi": 1,
                "dimanche": 0,
                "geo_point_2d": {"lat": 48.8566, "lon": 2.3522},
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    async def mock_executor_job(func, *args, **kwargs):
        """Mock the async_add_executor_job to call function directly."""
        return func(*args, **kwargs)

    with (
        patch.object(hass, "async_add_executor_job", side_effect=mock_executor_job),
        patch(
            "custom_components.paris_markets.coordinator.requests.get",
            return_value=mock_response,
        ),
    ):
        result = await coordinator_arrondissement._async_update_data()

        assert len(result) == 1
        assert "1" in result
        assert result["1"]["long_name"] == "Test Market"


async def test_coordinator_data_normalisation(hass: HomeAssistant, coordinator):
    """Test that data normalisation correctly converts field names and day values."""
    # Test raw market data with French field names
    raw_market_data = {
        "id_marche": "123",
        "nom_long": "Marché Saint-Germain",
        "nom_court": "Saint-Germain",
        "localisation": "Place Saint-Germain",
        "ardt": "6",
        "produit": "Alimentaire",
        "jours_tenue": "Mardi, Samedi",
        "gestionnaire": "Ville de Paris",
        "secteur": "Test Sector",
        "lineaire": "150",
        "h_deb_sem_1": "08:00",
        "h_fin_sem_1": "14:00",
        "h_deb_sam": "08:00",
        "h_fin_sam": "13:00",
        "h_deb_dim": None,
        "h_fin_dim": None,
        "lundi": 0,  # Monday - closed
        "mardi": 1,  # Tuesday - open
        "mercredi": 0,  # Wednesday - closed
        "jeudi": 0,  # Thursday - closed
        "vendredi": 0,  # Friday - closed
        "samedi": 1,  # Saturday - open
        "dimanche": 0,  # Sunday - closed
        "geo_point_2d": {"lat": 48.8566, "lon": 2.3522},
    }

    normalised = coordinator._normalise_market_data(raw_market_data)

    # Check that field names are converted to English snake_case
    assert normalised["market_id"] == "123"
    assert normalised["long_name"] == "Marché Saint-Germain"
    assert normalised["short_name"] == "Saint-Germain"
    assert normalised["location"] == "Place Saint-Germain"
    assert normalised["arrondissement"] == "6"
    assert normalised["product_type"] == "Alimentaire"

    # Check that time fields are converted to structured schedule
    paris_tz = pytz.timezone("Europe/Paris")
    expected_schedule = {
        1: None,  # Monday - closed (lundi: 0)
        2: {
            "start_time": time(8, 0, tzinfo=paris_tz),
            "end_time": time(14, 0, tzinfo=paris_tz),
        },  # Tuesday - open (mardi: 1)
        3: None,  # Wednesday - closed (mercredi: 0)
        4: None,  # Thursday - closed (jeudi: 0)
        5: None,  # Friday - closed (vendredi: 0)
        6: {
            "start_time": time(8, 0, tzinfo=paris_tz),
            "end_time": time(13, 0, tzinfo=paris_tz),
        },  # Saturday - open (samedi: 1)
        7: None,  # Sunday - closed (dimanche: 0)
    }
    assert normalised["schedule"] == expected_schedule

    # Check that old time field names are not present
    assert "weekday_start_time" not in normalised
    assert "h_deb_sem_1" not in normalised

    # Check that day fields are not included (they're now part of the schedule structure)
    assert "day_1" not in normalised
    assert "day_2" not in normalised
    assert "day_3" not in normalised
    assert "day_4" not in normalised
    assert "day_5" not in normalised
    assert "day_6" not in normalised
    assert "day_7" not in normalised

    # Check that coordinates field is renamed
    assert normalised["coordinates"] == {"lat": 48.8566, "lon": 2.3522}

    # Check that old French field names are not present
    assert "nom_long" not in normalised
    assert "lundi" not in normalised
    assert "geo_point_2d" not in normalised


async def test_coordinator_schedule_structure(hass: HomeAssistant, coordinator):
    """Test that the schedule structure correctly maps day IDs to start/end times."""
    # Test raw market data with all possible schedule configurations
    raw_market_data = {
        "id_marche": "456",
        "nom_long": "Test Market",
        "h_deb_sem_1": "09:00",  # Weekday start
        "h_fin_sem_1": "15:00",  # Weekday end
        "h_deb_sam": "08:30",  # Saturday start
        "h_fin_sam": "12:30",  # Saturday end
        "h_deb_dim": "10:00",  # Sunday start
        "h_fin_dim": "13:00",  # Sunday end
        "lundi": 1,
        "mardi": 1,
        "mercredi": 0,
        "jeudi": 1,
        "vendredi": 1,
        "samedi": 1,
        "dimanche": 1,
    }

    normalised = coordinator._normalise_market_data(raw_market_data)

    # Check that schedule hash contains correct mappings
    schedule = normalised["schedule"]

    # Open weekdays (Monday, Tuesday, Thursday, Friday) should have weekday times
    paris_tz = pytz.timezone("Europe/Paris")
    expected_weekday_schedule = {
        "start_time": time(9, 0, tzinfo=paris_tz),
        "end_time": time(15, 0, tzinfo=paris_tz),
    }
    assert schedule[1] == expected_weekday_schedule  # Monday (open)
    assert schedule[2] == expected_weekday_schedule  # Tuesday (open)
    assert schedule[4] == expected_weekday_schedule  # Thursday (open)
    assert schedule[5] == expected_weekday_schedule  # Friday (open)

    # Closed weekday (Wednesday) should be None
    assert schedule[3] is None  # Wednesday (closed)

    # Saturday should use Saturday times (open)
    assert schedule[6] == {
        "start_time": time(8, 30, tzinfo=paris_tz),
        "end_time": time(12, 30, tzinfo=paris_tz),
    }

    # Sunday should use Sunday times (open)
    assert schedule[7] == {
        "start_time": time(10, 0, tzinfo=paris_tz),
        "end_time": time(13, 0, tzinfo=paris_tz),
    }

    # Verify structure allows easy access by day ID
    assert schedule[1]["start_time"] == time(9, 0, tzinfo=paris_tz)  # Monday start
    assert schedule[1]["end_time"] == time(15, 0, tzinfo=paris_tz)  # Monday end
    assert schedule[6]["start_time"] == time(8, 30, tzinfo=paris_tz)  # Saturday start
    assert schedule[7]["end_time"] == time(13, 0, tzinfo=paris_tz)  # Sunday end


async def test_coordinator_partial_schedule(hass: HomeAssistant, coordinator):
    """Test schedule structure with missing time data."""
    raw_market_data = {
        "id_marche": "789",
        "nom_long": "Partial Schedule Market",
        "h_deb_sem_1": "08:00",  # Only weekday times
        "h_fin_sem_1": "14:00",
        # No Saturday or Sunday times
        "lundi": 1,  # Monday - open
        "mardi": 1,  # Tuesday - open
        "mercredi": 0,  # Wednesday - closed
        "jeudi": 0,  # Thursday - closed
        "vendredi": 0,  # Friday - closed
        "samedi": 0,  # Closed on Saturday
        "dimanche": 0,  # Closed on Sunday
    }

    normalised = coordinator._normalise_market_data(raw_market_data)
    schedule = normalised["schedule"]

    # All days should be present in schedule
    for day_id in range(1, 8):
        assert day_id in schedule

    # Open weekdays should have times
    paris_tz = pytz.timezone("Europe/Paris")
    assert schedule[1] == {
        "start_time": time(8, 0, tzinfo=paris_tz),
        "end_time": time(14, 0, tzinfo=paris_tz),
    }  # Monday - open
    assert schedule[2] == {
        "start_time": time(8, 0, tzinfo=paris_tz),
        "end_time": time(14, 0, tzinfo=paris_tz),
    }  # Tuesday - open

    # Closed weekdays should be None
    assert schedule[3] is None  # Wednesday - closed
    assert schedule[4] is None  # Thursday - closed
    assert schedule[5] is None  # Friday - closed

    # Closed Saturday and Sunday should be None
    assert schedule[6] is None  # Saturday - closed
    assert schedule[7] is None  # Sunday - closed
