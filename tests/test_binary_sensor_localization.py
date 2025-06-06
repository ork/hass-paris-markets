"""Comprehensive tests for Paris Markets sensor localization and timezone handling."""

from datetime import datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.paris_markets.binary_sensor import MarketBinarySensor


def paris_time(hour: int, minute: int = 0) -> time:
    """Create a timezone-aware time object for Paris timezone."""
    return time(hour, minute, tzinfo=ZoneInfo("Europe/Paris"))


class TestMarketBinarySensorLocalization:
    """Test MarketBinarySensor localization and translation features."""

    def test_sensor_translation_key_and_placeholders(self, mock_coordinator) -> None:
        """Test that sensor has correct translation key and placeholders."""
        sensor = MarketBinarySensor(mock_coordinator, "market_1")

        # Check translation key
        assert sensor.entity_description.translation_key == "market"

        # Check translation placeholders
        assert sensor._attr_translation_placeholders == {"market_name": "Saint-Germain"}
        assert sensor._attr_has_entity_name is True

    def test_sensor_names_for_different_markets(self, mock_coordinator) -> None:
        """Test sensor names and placeholders for different markets."""
        # Saint-Germain market
        sensor1 = MarketBinarySensor(mock_coordinator, "market_1")
        assert sensor1.entity_description.name == "Marché Saint-Germain"
        assert sensor1._attr_translation_placeholders == {
            "market_name": "Saint-Germain"
        }

        # Enfants Rouges market
        sensor2 = MarketBinarySensor(mock_coordinator, "market_2")
        assert sensor2.entity_description.name == "Marché des Enfants Rouges"
        assert sensor2._attr_translation_placeholders == {
            "market_name": "Enfants Rouges"
        }

        # Bio market
        sensor3 = MarketBinarySensor(mock_coordinator, "market_bio")
        assert sensor3.entity_description.name == "Marché Bio Raspail"
        assert sensor3._attr_translation_placeholders == {"market_name": "Bio Raspail"}

    def test_sensor_fallback_names_for_missing_data(self, empty_coordinator) -> None:
        """Test sensor fallback names when market data is missing."""
        sensor = MarketBinarySensor(empty_coordinator, "unknown_market")

        assert sensor.entity_description.name == "Market unknown_market"
        assert sensor._attr_translation_placeholders == {
            "market_name": "unknown_market"
        }


class TestMarketBinarySensorTimezoneHandling:
    """Test MarketBinarySensor timezone handling and Paris time calculations."""

    @pytest.mark.parametrize(
        "utc_hour,expected_state",
        [
            # UTC to Paris time conversion tests
            # In summer (DST): UTC+2, in winter: UTC+1
            # Assuming summer time for these tests
            (6, True),  # 8 AM Paris (6 UTC + 2) - exactly opening time (market opens)
            (7, True),  # 9 AM Paris
            (10, True),  # 12 PM Paris
            (12, True),  # 2 PM Paris - exactly closing time (market still open)
            (13, False),  # 3 PM Paris - after closing
        ],
    )
    def test_timezone_conversion_summer(
        self, mock_coordinator, utc_hour: int, expected_state: str
    ) -> None:
        """Test timezone conversion during summer time (DST)."""
        sensor = MarketBinarySensor(mock_coordinator, "market_1")

        # Create UTC datetime for Tuesday at specified hour
        utc_datetime = datetime(
            2025, 7, 1, utc_hour, 0, 0, tzinfo=ZoneInfo("UTC")
        )  # July - summer time
        paris_datetime = utc_datetime.astimezone(ZoneInfo("Europe/Paris"))

        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = paris_datetime
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            assert sensor.is_on == expected_state

    @pytest.mark.parametrize(
        "utc_hour,expected_state",
        [
            # Winter time tests (UTC+1)
            (7, True),  # 8 AM Paris (7 UTC + 1) - exactly opening time (market opens)
            (8, True),  # 9 AM Paris
            (11, True),  # 12 PM Paris
            (13, True),  # 2 PM Paris - exactly closing time (market still open)
            (14, False),  # 3 PM Paris - after closing
        ],
    )
    def test_timezone_conversion_winter(
        self, mock_coordinator, utc_hour: int, expected_state: str
    ) -> None:
        """Test timezone conversion during winter time (no DST)."""
        sensor = MarketBinarySensor(mock_coordinator, "market_1")

        # Create UTC datetime for Tuesday in January (winter time)
        utc_datetime = datetime(
            2025, 1, 7, utc_hour, 0, 0, tzinfo=ZoneInfo("UTC")
        )  # January - winter time
        paris_datetime = utc_datetime.astimezone(ZoneInfo("Europe/Paris"))

        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = paris_datetime
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            assert sensor.is_on == expected_state

    def test_dst_transition_handling(self, mock_coordinator) -> None:
        """Test handling of daylight saving time transitions."""
        sensor = MarketBinarySensor(mock_coordinator, "market_1")

        # Test during DST transition period (last Sunday in March at 2 AM)
        # This is when clocks spring forward from 2 AM to 3 AM
        dst_transition = datetime(
            2025, 3, 30, 1, 30, 0, tzinfo=ZoneInfo("Europe/Paris")
        )

        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = dst_transition
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Should handle DST transition gracefully
            # Sunday should be closed for market_1 anyway
            assert not sensor.is_on

    def test_different_timezone_inputs(self, mock_coordinator) -> None:
        """Test sensor handles different timezone inputs correctly."""
        sensor = MarketBinarySensor(mock_coordinator, "market_1")

        # Test with different timezone representations
        test_times = [
            datetime(
                2025, 6, 3, 10, 0, 0, tzinfo=ZoneInfo("Europe/Paris")
            ),  # Direct Paris time
            datetime(2025, 6, 3, 8, 0, 0, tzinfo=ZoneInfo("UTC")).astimezone(
                ZoneInfo("Europe/Paris")
            ),  # UTC converted
        ]

        for test_time in test_times:
            with patch(
                "custom_components.paris_markets.binary_sensor.datetime"
            ) as mock_datetime:
                mock_datetime.now.return_value = test_time
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

                # Both should result in the same state (Tuesday 10 AM Paris = open)
                assert sensor.is_on


class TestMarketBinarySensorStateTransitions:
    """Test state transitions and edge cases in time calculations."""

    def test_exact_opening_and_closing_times(self, mock_coordinator) -> None:
        """Test sensor state at exact opening and closing times."""
        sensor = MarketBinarySensor(mock_coordinator, "market_1")

        # Test exactly at opening time (8:00 AM Tuesday)
        opening_time = datetime(2025, 6, 3, 8, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = opening_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert sensor.is_on

        # Test exactly at closing time (2:00 PM Tuesday)
        closing_time = datetime(2025, 6, 3, 14, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = closing_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert sensor.is_on

        # Test one second before opening
        before_opening = datetime(
            2025, 6, 3, 7, 59, 59, tzinfo=ZoneInfo("Europe/Paris")
        )
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = before_opening
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert not sensor.is_on

        # Test one second after closing
        after_closing = datetime(2025, 6, 3, 14, 0, 1, tzinfo=ZoneInfo("Europe/Paris"))
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = after_closing
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert not sensor.is_on

    def test_different_market_schedules(self, mock_coordinator) -> None:
        """Test state calculations for markets with different schedules."""
        # Test market with extended Saturday hours (market_2: until 17:00)
        sensor2 = MarketBinarySensor(mock_coordinator, "market_2")

        # Saturday 4 PM should be open for market_2
        saturday_4pm = datetime(2025, 6, 7, 16, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = saturday_4pm
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert sensor2.is_on

        # Test bio market (Sunday only)
        bio_sensor = MarketBinarySensor(mock_coordinator, "market_bio")

        # Sunday 12 PM should be open for bio market
        sunday_12pm = datetime(2025, 6, 8, 12, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = sunday_12pm
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert bio_sensor.is_on

        # Monday should be closed for bio market
        monday_12pm = datetime(2025, 6, 9, 12, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = monday_12pm
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            assert not bio_sensor.is_on

    def test_malformed_time_data_handling(self, mock_coordinator) -> None:
        """Test handling of edge case schedule data."""
        # Create a sensor with edge case schedule data
        import copy

        bad_data = copy.deepcopy(mock_coordinator.data["market_1"])
        # Test with an edge case: schedule where start_time and end_time are the same
        bad_data["schedule"] = {
            2: {
                "start_time": paris_time(12, 0),  # Same as end time (edge case)
                "end_time": paris_time(12, 0),  # Same as start time (edge case)
            }
        }
        mock_coordinator.data = {"market_1": bad_data}

        sensor = MarketBinarySensor(mock_coordinator, "market_1")

        # Should handle edge case data gracefully
        tuesday_10am = datetime(2025, 6, 3, 10, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = tuesday_10am
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            # Should return closed since 10am is before the 12:00-12:00 "window"
            assert not sensor.is_on

        # Test exactly at the edge case time
        tuesday_noon = datetime(2025, 6, 3, 12, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch(
            "custom_components.paris_markets.binary_sensor.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = tuesday_noon
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            # Should return open at exactly 12:00 (inclusive)
            assert sensor.is_on
