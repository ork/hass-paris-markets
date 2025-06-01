"""Test the Paris Markets config flow."""

from types import MappingProxyType
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.paris_markets.const import (
    CONF_ARRONDISSEMENTS,
    CONF_FILTER_MODE,
    CONF_PRODUCT_TYPES,
    CONF_RADIUS,
    DOMAIN,
)
from custom_components.paris_markets.models import FilterMode

pytestmark = pytest.mark.asyncio


async def test_form_user(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "custom_components.paris_markets.coordinator.ParisMarketsDataUpdateCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ),
        patch(
            "custom_components.paris_markets.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_FILTER_MODE: FilterMode.RADIUS.value,
                CONF_RADIUS: 5.0,
                CONF_PRODUCT_TYPES: ["Alimentaire", "Alimentaire bio"],
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Paris Markets (5.0km radius)"
    assert result2["data"] == {
        CONF_FILTER_MODE: FilterMode.RADIUS.value,
        CONF_RADIUS: 5.0,
        CONF_PRODUCT_TYPES: ["Alimentaire", "Alimentaire bio"],
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_user_arrondissement_mode(hass: HomeAssistant) -> None:
    """Test we get the form with arrondissement mode."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "custom_components.paris_markets.coordinator.ParisMarketsDataUpdateCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ),
        patch(
            "custom_components.paris_markets.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_FILTER_MODE: FilterMode.ARRONDISSEMENT.value,
                CONF_ARRONDISSEMENTS: ["1", "2"],
                CONF_PRODUCT_TYPES: ["Alimentaire", "Alimentaire bio"],
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Paris Markets (2 arrondissements)"
    assert result2["data"] == {
        CONF_FILTER_MODE: FilterMode.ARRONDISSEMENT.value,
        CONF_ARRONDISSEMENTS: ["1", "2"],
        CONF_PRODUCT_TYPES: ["Alimentaire", "Alimentaire bio"],
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_radius(hass: HomeAssistant) -> None:
    """Test we handle invalid radius."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_FILTER_MODE: FilterMode.RADIUS.value,
            CONF_RADIUS: 0.0,  # Invalid radius
            CONF_PRODUCT_TYPES: ["Alimentaire"],
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_radius"}


async def test_form_no_arrondissements(hass: HomeAssistant) -> None:
    """Test we handle no arrondissements selected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_FILTER_MODE: FilterMode.ARRONDISSEMENT.value,
            CONF_ARRONDISSEMENTS: [],  # No arrondissements selected
            CONF_PRODUCT_TYPES: ["Alimentaire"],
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "no_arrondissements"}


async def test_form_no_location_configured(hass: HomeAssistant) -> None:
    """Test we handle no Home Assistant location configured."""
    hass.config.latitude = None
    hass.config.longitude = None

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_FILTER_MODE: FilterMode.RADIUS.value,
            CONF_RADIUS: 5.0,
            CONF_PRODUCT_TYPES: ["Alimentaire"],
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "no_home_location"}


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Paris Markets",
        data={
            "radius_km": 5.0,
            "product_types": ["alimentaire"],
        },
        source=config_entries.SOURCE_USER,
        entry_id="test",
        unique_id=None,
        discovery_keys=MappingProxyType({}),
        options={},
        subentries_data=[],
    )

    hass.config_entries._entries[entry.entry_id] = entry

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"scan_interval_days": 1},  # 1 day (minimum allowed)
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == {"scan_interval": 86400}


async def test_options_flow_invalid_scan_interval(hass: HomeAssistant) -> None:
    """Test options flow with invalid scan interval (below 1 day minimum)."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Paris Markets",
        data={
            "radius_km": 5.0,
            "product_types": ["alimentaire"],
        },
        source=config_entries.SOURCE_USER,
        entry_id="test",
        unique_id=None,
        discovery_keys=MappingProxyType({}),
        options={},
        subentries_data=[],
    )

    hass.config_entries._entries[entry.entry_id] = entry

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"scan_interval_days": 0},  # 0 days (below minimum of 1 day)
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_scan_interval"}
