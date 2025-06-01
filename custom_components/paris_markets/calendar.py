"""Calendar platform for Paris Markets."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, date

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityDescription,
    CalendarEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    DEFAULT_ICON,
    DOMAIN,
)
from .coordinator import ParisMarketsDataUpdateCoordinator
from .models import MarketData, WeekDay

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Paris Markets calendar entities."""
    coordinator: ParisMarketsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    if coordinator.data:
        for market_id in coordinator.data.keys():
            entities.append(MarketCalendar(coordinator, market_id))

    async_add_entities(entities, True)


class MarketCalendar(
    CoordinatorEntity[ParisMarketsDataUpdateCoordinator], CalendarEntity
):
    """Representation of a Paris Market calendar."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ParisMarketsDataUpdateCoordinator,
        market_id: str,
    ) -> None:
        """Initialise the calendar."""
        super().__init__(coordinator)
        self.market_id = market_id
        self._market_data = self._get_market_data()

        if not self._market_data:
            market_name = f"Market {self.market_id}"
        else:
            market_name = self._market_data.long_name

        self._attr_translation_placeholders = {
            "market_name": market_name,
        }
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{self.market_id}_calendar"
        )
        self.entity_description = CalendarEntityDescription(
            key=f"market_{self.market_id}_calendar",
            name=market_name,
            icon=DEFAULT_ICON,
            translation_key="market",
        )

    def _get_market_data(self) -> MarketData | None:
        """Get data for the current market."""
        return MarketData.from_coordinator(self.coordinator, self.market_id)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return None

    def _create_calendar_event(
        self, market_data: MarketData, current_date: date
    ) -> CalendarEvent | None:
        """Create a calendar event for a given date if market is open."""
        market_day_schedule = market_data.schedule[WeekDay.from_date(current_date)]

        if not market_day_schedule.is_open():
            return None

        local_schedule = market_day_schedule.as_local_datetimes(current_date)
        if local_schedule is None:
            raise ValueError(
                f"Market {market_data.long_name} has no valid schedule for {current_date}"
            )

        local_start, local_end = local_schedule

        description = "\n".join(
            [
                f"Location: {market_data.location}",
                f"Arrondissement: {market_data.arrondissement}",
                f"Type: {market_data.product_type}",
            ]
        )

        return CalendarEvent(
            start=local_start,
            end=local_end,
            summary=market_data.long_name,
            description=description,
            location=market_data.location,
            uid=f"{self.market_id}_{current_date.isoformat()}",
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        market_data = self._get_market_data()
        if not market_data:
            return []

        events = []
        current_date = start_date.date()
        final_date = end_date.date()

        while current_date <= final_date:
            if event := self._create_calendar_event(market_data, current_date):
                events.append(event)
            current_date += timedelta(days=1)

        return events

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._market_data = self._get_market_data()
        self.async_write_ha_state()
