"""Comprehensive tests for the Paris Markets sensor platform."""

from datetime import datetime, time
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant

from custom_components.paris_markets.const import DEFAULT_ICON, DOMAIN
from custom_components.paris_markets.sensor import MarketSensor, async_setup_entry


def paris_time(hour: int, minute: int = 0) -> time:
    """Create a timezone-aware time object for Paris timezone."""
    return time(hour, minute, tzinfo=ZoneInfo("Europe/Paris"))


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_with_coordinator_data(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test setting up sensors when coordinator has data."""
        entry = MagicMock()
        entry.entry_id = "test_integration"
        hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

        entities = []
        async_add_entities = MagicMock(
            side_effect=lambda ents, update: entities.extend(ents)
        )

        await async_setup_entry(hass, entry, async_add_entities)

        # Should create one sensor per market
        assert len(entities) == 3
        assert all(isinstance(entity, MarketSensor) for entity in entities)

        market_ids = {entity.market_id for entity in entities}
        expected_ids = {"market_1", "market_2", "market_bio"}
        assert market_ids == expected_ids

    @pytest.mark.asyncio
    async def test_setup_with_empty_coordinator(
        self, hass: HomeAssistant, empty_coordinator
    ) -> None:
        """Test setting up sensors when coordinator has no data."""
        entry = MagicMock()
        entry.entry_id = "test_integration"
        hass.data[DOMAIN] = {entry.entry_id: empty_coordinator}

        entities = []
        async_add_entities = MagicMock(
            side_effect=lambda ents, update: entities.extend(ents)
        )

        await async_setup_entry(hass, entry, async_add_entities)

        # Should create no sensors
        assert len(entities) == 0

    @pytest.mark.asyncio
    async def test_setup_with_failed_coordinator(
        self, hass: HomeAssistant, failed_coordinator
    ) -> None:
        """Test setting up sensors when coordinator has failed."""
        entry = MagicMock()
        entry.entry_id = "test_integration"
        hass.data[DOMAIN] = {entry.entry_id: failed_coordinator}

        entities = []
        async_add_entities = MagicMock(
            side_effect=lambda ents, update: entities.extend(ents)
        )

        await async_setup_entry(hass, entry, async_add_entities)

        # Should create no sensors when data is None
        assert len(entities) == 0


class TestMarketSensorInitialization:
    """Test MarketSensor initialization and basic properties."""

    def test_sensor_initialization_with_valid_data(self, mock_coordinator) -> None:
        """Test sensor initialization with valid market data."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        assert sensor.market_id == "market_1"
        assert sensor.unique_id == "test_integration_market_1"
        assert sensor.entity_description.key == "market_market_1"
        assert sensor.entity_description.name == "Marché Saint-Germain"
        assert sensor.entity_description.icon == DEFAULT_ICON
        assert sensor.entity_description.translation_key == "market"
        assert sensor._attr_translation_placeholders == {"market_name": "Saint-Germain"}
        assert sensor._attr_has_entity_name is True

    def test_sensor_initialization_with_missing_data(self, empty_coordinator) -> None:
        """Test sensor initialization when market data is missing."""
        sensor = MarketSensor(empty_coordinator, "nonexistent_market")

        assert sensor.market_id == "nonexistent_market"
        assert sensor.unique_id == "test_integration_nonexistent_market"
        assert sensor.entity_description.name == "Market nonexistent_market"
        assert sensor._attr_translation_placeholders == {
            "market_name": "nonexistent_market"
        }

    def test_sensor_availability(self, mock_coordinator) -> None:
        """Test sensor availability based on coordinator state."""
        sensor = MarketSensor(mock_coordinator, "market_1")
        assert sensor.available is True

        # Test when coordinator update fails
        mock_coordinator.last_update_success = False
        assert sensor.available is False

    def test_sensor_should_poll(self, mock_coordinator) -> None:
        """Test that sensor should not poll (coordinator-based)."""
        sensor = MarketSensor(mock_coordinator, "market_1")
        assert sensor.should_poll is False


class TestMarketSensorStateLogic:
    """Test the core state logic of MarketSensor."""

    @pytest.mark.parametrize(
        "market_id,day,hour,minute,expected_state",
        [
            # Market 1 (Saint-Germain): Tue 8-14, Thu 8-14:30, Sat 8-13, Sun 9-13:30
            ("market_1", 2, 10, 0, "open"),  # Tuesday 10:00 - open
            ("market_1", 2, 7, 30, "closed"),  # Tuesday 7:30 - before opening
            ("market_1", 2, 14, 30, "closed"),  # Tuesday 14:30 - after closing
            ("market_1", 4, 14, 15, "open"),  # Thursday 14:15 - still open
            ("market_1", 4, 14, 45, "closed"),  # Thursday 14:45 - after closing
            ("market_1", 6, 12, 30, "open"),  # Saturday 12:30 - open
            ("market_1", 7, 13, 0, "open"),  # Sunday 13:00 - open
            ("market_1", 1, 10, 0, "closed"),  # Monday - closed
            ("market_1", 3, 10, 0, "closed"),  # Wednesday - closed
            ("market_1", 5, 10, 0, "closed"),  # Friday - closed
            # Market 2 (Enfants Rouges): Tue-Fri 8:30-13, Sat 8:30-17, Sun 9-14
            ("market_2", 2, 9, 0, "open"),  # Tuesday 9:00 - open
            ("market_2", 3, 12, 30, "open"),  # Wednesday 12:30 - open
            ("market_2", 6, 16, 0, "open"),  # Saturday 16:00 - open
            ("market_2", 7, 13, 30, "open"),  # Sunday 13:30 - open
            ("market_2", 1, 10, 0, "closed"),  # Monday - closed
            # Market Bio (Raspail): Sunday only 9-15
            ("market_bio", 7, 12, 0, "open"),  # Sunday 12:00 - open
            ("market_bio", 7, 8, 30, "closed"),  # Sunday 8:30 - before opening
            ("market_bio", 7, 15, 30, "closed"),  # Sunday 15:30 - after closing
            ("market_bio", 2, 10, 0, "closed"),  # Tuesday - closed
        ],
    )
    def test_market_states_comprehensive(
        self,
        mock_coordinator,
        market_id: str,
        day: int,
        hour: int,
        minute: int,
        expected_state: str,
    ) -> None:
        """Test market states comprehensively across different schedules."""
        sensor = MarketSensor(mock_coordinator, market_id)

        # Create a datetime for 2025 (current year) with the specified day
        # Day 1=Monday, 2=Tuesday, etc.
        # Start with Monday 2025-06-02 and add days
        base_date = datetime(2025, 6, 2)  # Monday
        test_date = base_date.replace(day=base_date.day + (day - 1))
        test_datetime = test_date.replace(hour=hour, minute=minute)
        paris_datetime = test_datetime.replace(tzinfo=ZoneInfo("Europe/Paris"))

        with patch("custom_components.paris_markets.sensor.datetime") as mock_datetime:
            mock_datetime.now.return_value = paris_datetime
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            assert sensor.native_value == expected_state

    def test_sensor_state_with_no_market_data(self, empty_coordinator) -> None:
        """Test sensor state when market data is unavailable."""
        sensor = MarketSensor(empty_coordinator, "nonexistent_market")
        assert sensor.native_value is None

    def test_sensor_state_edge_cases(self, mock_coordinator) -> None:
        """Test edge cases for sensor state calculation."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        # Test exactly at opening time
        tuesday_8am = datetime(2025, 6, 3, 8, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch("custom_components.paris_markets.sensor.datetime") as mock_datetime:
            mock_datetime.now.return_value = tuesday_8am
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert sensor.native_value == "open"

        # Test exactly at closing time
        tuesday_2pm = datetime(2025, 6, 3, 14, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch("custom_components.paris_markets.sensor.datetime") as mock_datetime:
            mock_datetime.now.return_value = tuesday_2pm
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert sensor.native_value == "open"

        # Test one minute after closing
        tuesday_2_01pm = datetime(2025, 6, 3, 14, 1, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch("custom_components.paris_markets.sensor.datetime") as mock_datetime:
            mock_datetime.now.return_value = tuesday_2_01pm
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert sensor.native_value == "closed"


class TestMarketSensorAttributes:
    """Test MarketSensor attributes and metadata."""

    def test_extra_state_attributes_with_valid_data(self, mock_coordinator) -> None:
        """Test extra state attributes when market data is available."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        attrs = sensor.extra_state_attributes

        assert attrs is not None
        expected_attrs = {
            "long_name": "Marché Saint-Germain",
            "short_name": "Saint-Germain",
            "arrondissement": 6,
            "location": "4-6 Rue Lobineau",
            "product_type": "Alimentaire",
            "coordinates": {"lat": 48.8566, "lon": 2.3522},
        }

        assert attrs == expected_attrs

    def test_extra_state_attributes_with_missing_data(self, empty_coordinator) -> None:
        """Test extra state attributes when market data is missing."""
        sensor = MarketSensor(empty_coordinator, "nonexistent_market")

        attrs = sensor.extra_state_attributes
        assert attrs is None

    def test_market_data_caching(self, mock_coordinator) -> None:
        """Test that market data is properly retrieved."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        # Access market data multiple times
        data1 = sensor._get_market_data()
        data2 = sensor._get_market_data()

        assert data1 is not None
        assert data2 is not None
        assert data1.market_id == "market_1"
        assert data1.long_name == "Marché Saint-Germain"

    def test_different_market_attributes(self, mock_coordinator) -> None:
        """Test attributes for different markets."""
        # Test bio market
        bio_sensor = MarketSensor(mock_coordinator, "market_bio")
        bio_attrs = bio_sensor.extra_state_attributes

        assert bio_attrs["product_type"] == "Alimentaire bio"
        assert bio_attrs["arrondissement"] == 6
        assert bio_attrs["short_name"] == "Bio Raspail"

        # Test regular market
        regular_sensor = MarketSensor(mock_coordinator, "market_2")
        regular_attrs = regular_sensor.extra_state_attributes

        assert regular_attrs["product_type"] == "Alimentaire"
        assert regular_attrs["arrondissement"] == 3
        assert regular_attrs["short_name"] == "Enfants Rouges"


class TestMarketSensorUpdates:
    """Test MarketSensor update handling."""

    def test_coordinator_update_callback(self, mock_coordinator) -> None:
        """Test that sensor responds to coordinator updates."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        # Mock the async_write_ha_state method
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        # Verify state was written
        sensor.async_write_ha_state.assert_called_once()

    def test_coordinator_listener_registration(self, mock_coordinator) -> None:
        """Test that sensor registers as coordinator listener."""
        # MarketSensor inherits from CoordinatorEntity which automatically registers listeners
        sensor = MarketSensor(mock_coordinator, "market_1")

        # The listener registration happens in CoordinatorEntity.__init__
        # We can verify the sensor is properly set up to receive updates
        assert hasattr(sensor, "_handle_coordinator_update")
        assert callable(sensor._handle_coordinator_update)

    def test_sensor_device_info(self, mock_coordinator) -> None:
        """Test sensor device information."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        # Market sensors shouldn't have device info (they're standalone entities)
        assert sensor.device_info is None

    def test_sensor_entity_category(self, mock_coordinator) -> None:
        """Test that sensor has no entity category (primary entity)."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        # Market sensors should be primary entities, not diagnostic/config
        assert sensor.entity_category is None


class TestMarketSensorErrorConditions:
    """Test MarketSensor error handling and edge cases."""

    def test_coordinator_data_becomes_none(self, mock_coordinator) -> None:
        """Test behavior when coordinator data becomes None after initialization."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        # Initially should work
        assert sensor.native_value is not None

        # Simulate coordinator losing data
        mock_coordinator.data = None

        # Should handle gracefully
        assert sensor.native_value is None
        assert sensor.extra_state_attributes is None

    def test_market_removed_from_coordinator(self, mock_coordinator) -> None:
        """Test behavior when specific market is removed from coordinator data."""
        sensor = MarketSensor(mock_coordinator, "market_1")

        # Initially should work
        assert sensor.native_value is not None

        # Remove the specific market
        del mock_coordinator.data["market_1"]

        # Should handle gracefully
        assert sensor.native_value is None
        assert sensor.extra_state_attributes is None

    def test_malformed_schedule_data(self, mock_coordinator) -> None:
        """Test behavior with malformed schedule data."""
        # Create a copy of the market data with malformed schedule
        import copy

        bad_data = copy.deepcopy(mock_coordinator.data["market_1"])
        # Use a schedule that passes validation but represents unusual data
        bad_data["schedule"] = {
            2: None,  # None schedule for Tuesday (this is valid)
            3: {
                "start_time": paris_time(23, 59),  # Very late start time
                "end_time": paris_time(23, 59),  # Same as start time (edge case)
            },
        }
        mock_coordinator.data = {"market_1": bad_data}

        sensor = MarketSensor(mock_coordinator, "market_1")

        # Should handle edge case data gracefully
        tuesday_10am = datetime(2025, 6, 3, 10, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch("custom_components.paris_markets.sensor.datetime") as mock_datetime:
            mock_datetime.now.return_value = tuesday_10am
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            # Should return closed due to no schedule on Tuesday
            assert sensor.native_value == "closed"

        # Test the edge case schedule on Wednesday
        wednesday_11pm = datetime(
            2025, 6, 4, 23, 59, 0, tzinfo=ZoneInfo("Europe/Paris")
        )
        with patch("custom_components.paris_markets.sensor.datetime") as mock_datetime:
            mock_datetime.now.return_value = wednesday_11pm
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            # Should be open exactly at the edge time
            assert sensor.native_value == "open"
