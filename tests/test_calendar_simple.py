"""Simple test to verify calendar module imports."""


def test_simple_import():
    """Test that we can import the calendar module."""
    from custom_components.paris_markets.calendar import (
        MarketCalendar,
        async_setup_entry,
    )

    assert MarketCalendar is not None
    assert async_setup_entry is not None
