"""Sensor platform for Paris Markets."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DEFAULT_ICON, DOMAIN
from .coordinator import ParisMarketsDataUpdateCoordinator
from .models import MarketData, WeekDay

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Paris Markets sensors."""
    coordinator: ParisMarketsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    if coordinator.data:
        for market_id in coordinator.data.keys():
            entities.append(MarketSensor(coordinator, market_id))

    async_add_entities(entities, True)


class MarketSensor(CoordinatorEntity[ParisMarketsDataUpdateCoordinator], SensorEntity):
    """Representation of a Paris Market sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ParisMarketsDataUpdateCoordinator,
        market_id: str,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.market_id = market_id
        self._market_data = self._get_market_data()

        if not self._market_data:
            market_name = f"Market {self.market_id}"
            short_name = self.market_id
        else:
            market_name = self._market_data.long_name
            short_name = self._market_data.short_name

        self._attr_translation_placeholders = {"market_name": short_name}
        self.entity_description = SensorEntityDescription(
            key=f"market_{self.market_id}",
            name=market_name,
            icon=DEFAULT_ICON,
            translation_key="market",
        )
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.market_id}"

    def _get_market_data(self) -> MarketData | None:
        """Get data for the current market."""
        return MarketData.from_coordinator(self.coordinator, self.market_id)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        market_data = self._get_market_data()
        if not market_data:
            return None

        paris_now = datetime.now(tz=ZoneInfo("Europe/Paris"))
        paris_time = paris_now.time()
        current_weekday = WeekDay.from_date(paris_now.date())

        market_day_schedule = market_data.schedule[current_weekday]

        if not market_day_schedule.is_open():
            return "closed"

        start_time = market_day_schedule.start_time
        end_time = market_day_schedule.end_time

        if not start_time or not end_time:
            return "closed"

        is_open_now = (
            start_time.replace(tzinfo=None)
            <= paris_time
            <= end_time.replace(tzinfo=None)
        )

        return "open" if is_open_now else "closed"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return other details about the market."""
        market_data = self._get_market_data()
        if not market_data:
            return None

        return {
            "long_name": market_data.long_name,
            "short_name": market_data.short_name,
            "arrondissement": market_data.arrondissement,
            "location": market_data.location,
            "product_type": market_data.product_type,
            "coordinates": market_data.coordinates,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._market_data = self._get_market_data()
        self.async_write_ha_state()
