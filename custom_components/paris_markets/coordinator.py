"""DataUpdateCoordinator for Paris Markets."""

import logging
from datetime import datetime, time, timedelta
from functools import partial
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_ENDPOINT,
    CONF_ARRONDISSEMENTS,
    CONF_FILTER_MODE,
    CONF_PRODUCT_TYPES,
    CONF_RADIUS,
    DEFAULT_PRODUCT_TYPES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SCAN_INTERVAL,
)
from .models import FilterMode

_LOGGER = logging.getLogger(__name__)


class ParisMarketsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Paris Markets data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise."""
        self.entry = entry

        scan_interval_seconds = entry.options.get(
            SCAN_INTERVAL, timedelta(days=DEFAULT_SCAN_INTERVAL).total_seconds()
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval_seconds),
        )

    def _normalise_market_data(self, raw_market: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise raw API market data to snake_case English field names.

        Converts French field names to English snake_case equivalents and
        replaces French day names with integers (1=Monday, 7=Sunday).
        Creates a structured schedule hash mapping day IDs to start/end times.

        Args:
            raw_market: Raw market data from the API

        Returns:
            Normalized market data dictionary with English field names
        """
        return {
            **self._normalise_basic_fields(raw_market),
            "schedule": self._create_schedule(raw_market),
        }

    def _normalise_basic_fields(self, raw_market: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalise basic market fields."""
        field_mapping = {
            "id_marche": "market_id",
            "nom_long": "long_name",
            "nom_court": "short_name",
            "localisation": "location",
            "ardt": "arrondissement",
            "produit": "product_type",
            "geo_point_2d": "coordinates",
        }

        return {
            field_mapping[french_key]: value
            for french_key, value in raw_market.items()
            if french_key in field_mapping
        }

    def _parse_paris_time(self, time_boundary: Optional[str]) -> Optional[time]:
        if not time_boundary:
            return None
        return (
            datetime.strptime(time_boundary, "%H:%M")
            .replace(tzinfo=ZoneInfo("Europe/Paris"))
            .timetz()
        )

    def _create_schedule(
        self, raw_market: Dict[str, Any]
    ) -> Dict[int, Optional[Dict[str, Any]]]:
        """Create a structured schedule from raw market data."""
        # Configuration for each day type
        schedule_config = (
            (range(1, 6), "h_deb_sem_1", "h_fin_sem_1"),
            ([6], "h_deb_sam", "h_fin_sam"),
            ([7], "h_deb_dim", "h_fin_dim"),
        )

        day_names = {
            1: "lundi",
            2: "mardi",
            3: "mercredi",
            4: "jeudi",
            5: "vendredi",
            6: "samedi",
            7: "dimanche",
        }

        schedule: Dict[int, Optional[Dict[str, Any]]] = {}

        for config in schedule_config:
            schedule_entry = {
                "start_time": self._parse_paris_time(raw_market.get(config[1])),
                "end_time": self._parse_paris_time(raw_market.get(config[2])),
            }

            for day_id in config[0]:
                day_name = day_names[day_id]
                is_open = bool(raw_market.get(day_name, False))
                schedule[day_id] = schedule_entry if is_open else None

        return schedule

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            filter_mode = self.entry.data.get(CONF_FILTER_MODE, FilterMode.RADIUS.value)
            product_types = self.entry.data.get(
                CONF_PRODUCT_TYPES, DEFAULT_PRODUCT_TYPES
            )

            where_clauses = []

            if filter_mode == FilterMode.RADIUS.value:
                user_lat = self.hass.config.latitude
                user_lon = self.hass.config.longitude

                if user_lat is None or user_lon is None:
                    raise UpdateFailed(
                        "Home Assistant location not configured. Please set your location in Settings > System > General."
                    )

                radius_km = self.entry.data[CONF_RADIUS]

                distance_clause = f"within_distance(geo_point_2d, GEOM'POINT({user_lon} {user_lat})', {radius_km}km)"
                where_clauses.append(distance_clause)

            elif filter_mode == FilterMode.ARRONDISSEMENT.value:
                arrondissements = self.entry.data.get(CONF_ARRONDISSEMENTS)

                if arrondissements:
                    # API expects simple integers for 'ardt' (e.g., 1, 17)
                    arrondissement_list = ", ".join(
                        [str(arr) for arr in arrondissements]
                    )
                    arrondissement_clause = f"ardt IN ({arrondissement_list})"
                    where_clauses.append(arrondissement_clause)

            # Add product type filter
            if product_types:
                product_list = ", ".join([f'"{ptype}"' for ptype in product_types])
                product_clause = f"produit IN ({product_list})"
                where_clauses.append(product_clause)

            # Combine clauses with AND
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            params = {
                "limit": 100,  # Adjust limit or implement pagination if necessary
                "where": where_clause,
            }

            _LOGGER.debug(f"Requesting Paris Markets API with params: {params}")

            response = await self.hass.async_add_executor_job(
                partial(requests.get, API_ENDPOINT, params=params, timeout=10)
            )
            response.raise_for_status()
            data = response.json()

            if "results" not in data:
                _LOGGER.warning("No 'results' in API response from Paris Markets")
                return {}

            # Normalise each market's data before processing
            normalised_markets = []
            for market in data["results"]:
                try:
                    normalised_market = self._normalise_market_data(market)
                    normalised_markets.append(normalised_market)
                except Exception as err:
                    _LOGGER.warning(
                        f"Failed to normalise market data for market {market.get('id_marche', 'unknown')}: {err}"
                    )
                    normalised_markets.append(market)

            processed_data = {
                market.get("market_id", market.get("id_marche", "unknown")): market
                for market in normalised_markets
            }
            _LOGGER.debug(
                f"Successfully fetched and processed {len(processed_data)} markets using {filter_mode} filtering. "
                f"Normalised {len(normalised_markets)} market records."
            )
            return processed_data

        except requests.exceptions.RequestException as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except KeyError as err:
            _LOGGER.error(f"Configuration data missing: {err}")
            raise UpdateFailed(f"Configuration data missing: {err}") from err
        except Exception as err:
            _LOGGER.exception(f"Unexpected error fetching Paris Markets data: {err}")
            raise UpdateFailed(f"Unexpected error fetching data: {err}") from err
