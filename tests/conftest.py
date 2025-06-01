"""Test configuration for pytest-homeassistant-custom-component."""

from datetime import time
from typing import Any, Dict
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from custom_components.paris_markets.coordinator import (
    ParisMarketsDataUpdateCoordinator,
)


def paris_time(hour: int, minute: int = 0) -> time:
    """Create a timezone-aware time object for Paris timezone."""
    return time(hour, minute, tzinfo=ZoneInfo("Europe/Paris"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def expected_lingering_tasks() -> bool:
    """Return True if lingering tasks are expected."""
    return True


@pytest.fixture
def expected_lingering_timers() -> bool:
    """Return True if lingering timers are expected."""
    return True


# Comprehensive mock market data for testing
MOCK_MARKET_DATA = {
    "market_1": {
        "market_id": "market_1",
        "long_name": "Marché Saint-Germain",
        "short_name": "Saint-Germain",
        "arrondissement": "6",
        "location": "4-6 Rue Lobineau",
        "product_type": "Alimentaire",
        "coordinates": {"lat": 48.8566, "lon": 2.3522},
        "schedule": {
            1: None,  # Monday - closed
            2: {  # Tuesday
                "start_time": paris_time(8, 0),
                "end_time": paris_time(14, 0),
            },
            3: None,  # Wednesday - closed
            4: {  # Thursday
                "start_time": paris_time(8, 0),
                "end_time": paris_time(14, 30),
            },
            5: None,  # Friday - closed
            6: {  # Saturday
                "start_time": paris_time(8, 0),
                "end_time": paris_time(13, 0),
            },
            7: {  # Sunday
                "start_time": paris_time(9, 0),
                "end_time": paris_time(13, 30),
            },
        },
    },
    "market_2": {
        "market_id": "market_2",
        "long_name": "Marché des Enfants Rouges",
        "short_name": "Enfants Rouges",
        "arrondissement": "3",
        "location": "39 Rue de Bretagne",
        "product_type": "Alimentaire",
        "coordinates": {"lat": 48.8628, "lon": 2.3639},
        "schedule": {
            1: None,  # Monday - closed
            2: {  # Tuesday
                "start_time": paris_time(8, 30),
                "end_time": paris_time(13, 0),
            },
            3: {  # Wednesday
                "start_time": paris_time(8, 30),
                "end_time": paris_time(13, 0),
            },
            4: {  # Thursday
                "start_time": paris_time(8, 30),
                "end_time": paris_time(13, 0),
            },
            5: {  # Friday
                "start_time": paris_time(8, 30),
                "end_time": paris_time(13, 0),
            },
            6: {  # Saturday
                "start_time": paris_time(8, 30),
                "end_time": paris_time(17, 0),
            },
            7: {  # Sunday
                "start_time": paris_time(9, 0),
                "end_time": paris_time(14, 0),
            },
        },
    },
    "market_bio": {
        "market_id": "market_bio",
        "long_name": "Marché Bio Raspail",
        "short_name": "Bio Raspail",
        "arrondissement": "6",
        "location": "Boulevard Raspail",
        "product_type": "Alimentaire bio",
        "coordinates": {"lat": 48.8467, "lon": 2.3261},
        "schedule": {
            1: None,  # Monday - closed
            2: None,  # Tuesday - closed
            3: None,  # Wednesday - closed
            4: None,  # Thursday - closed
            5: None,  # Friday - closed
            6: None,  # Saturday - closed
            7: {  # Sunday only
                "start_time": paris_time(9, 0),
                "end_time": paris_time(15, 0),
            },
        },
    },
}


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator with comprehensive test data."""
    import copy

    coordinator = MagicMock(spec=ParisMarketsDataUpdateCoordinator)
    coordinator.data = copy.deepcopy(
        MOCK_MARKET_DATA
    )  # Create a fresh copy for each test
    coordinator.async_add_listener = MagicMock()
    coordinator.last_update_success = True
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_integration"
    return coordinator


@pytest.fixture
def empty_coordinator() -> MagicMock:
    """Create a mock coordinator with no data."""
    coordinator = MagicMock(spec=ParisMarketsDataUpdateCoordinator)
    coordinator.data = {}
    coordinator.async_add_listener = MagicMock()
    coordinator.last_update_success = True
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_integration"
    return coordinator


@pytest.fixture
def failed_coordinator() -> MagicMock:
    """Create a mock coordinator that has failed to update."""
    coordinator = MagicMock(spec=ParisMarketsDataUpdateCoordinator)
    coordinator.data = None
    coordinator.async_add_listener = MagicMock()
    coordinator.last_update_success = False
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_integration"
    return coordinator


@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Provide a single market's data for testing."""
    return MOCK_MARKET_DATA["market_1"]
