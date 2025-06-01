"""Config flow for Paris Markets."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ARRONDISSEMENTS,
    CONF_FILTER_MODE,
    CONF_PRODUCT_TYPES,
    CONF_RADIUS,
    DEFAULT_FILTER_MODE,
    DEFAULT_PRODUCT_TYPES,
    DEFAULT_RADIUS_KM,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MINIMUM_SCAN_INTERVAL,
    SCAN_INTERVAL,
)
from .models import Arrondissement, FilterMode, ProductType

_LOGGER = logging.getLogger(__name__)


class ParisMarketsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Paris Markets."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return ParisMarketsOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step to configure filter mode and options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                filter_mode = user_input[CONF_FILTER_MODE]
                product_types = user_input.get(
                    CONF_PRODUCT_TYPES, DEFAULT_PRODUCT_TYPES
                )

                # Validate based on filter mode
                if filter_mode == FilterMode.RADIUS.value:
                    radius = float(user_input[CONF_RADIUS])
                    if radius <= 0:
                        errors["base"] = "invalid_radius"
                    elif (
                        self.hass.config.latitude is None
                        or self.hass.config.longitude is None
                    ):
                        errors["base"] = "no_home_location"
                elif filter_mode == FilterMode.ARRONDISSEMENT.value:
                    arrondissements = user_input.get(CONF_ARRONDISSEMENTS)
                    if not arrondissements:
                        errors["base"] = "no_arrondissements"

                if not product_types:
                    errors["base"] = "no_product_types"

                if not errors:
                    # Clean up the data to only include relevant fields
                    clean_data = {
                        CONF_FILTER_MODE: filter_mode,
                        CONF_PRODUCT_TYPES: product_types,
                    }

                    if filter_mode == FilterMode.RADIUS.value:
                        clean_data[CONF_RADIUS] = float(user_input[CONF_RADIUS])
                    elif filter_mode == FilterMode.ARRONDISSEMENT.value:
                        clean_data[CONF_ARRONDISSEMENTS] = user_input[
                            CONF_ARRONDISSEMENTS
                        ]

                    if filter_mode == FilterMode.RADIUS.value:
                        lat = self.hass.config.latitude
                        lon = self.hass.config.longitude
                        radius = float(user_input[CONF_RADIUS])
                        unique_id = (
                            f"pm_radius_{lat}_{lon}_{radius}_{len(product_types)}"
                        )
                        title = f"Paris Markets ({radius}km radius)"
                    else:  # ARRONDISSEMENT mode
                        selected_arrondissements = user_input[CONF_ARRONDISSEMENTS]
                        arrondissements_str = "_".join(
                            map(str, sorted(selected_arrondissements))
                        )
                        unique_id = f"pm_arrondissements_{arrondissements_str}_{len(product_types)}"
                        title = f"Paris Markets ({len(selected_arrondissements)} arrondissement{'s' if len(selected_arrondissements) > 1 else ''})"

                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(title=title, data=clean_data)

            except ValueError:
                errors["base"] = "invalid_input_type"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        filter_mode = (
            user_input.get(CONF_FILTER_MODE, DEFAULT_FILTER_MODE)
            if user_input
            else DEFAULT_FILTER_MODE
        )

        schema_dict = {
            vol.Required(
                CONF_FILTER_MODE, default=filter_mode
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=FilterMode.RADIUS.value, label="Distance from home"
                        ),
                        selector.SelectOptionDict(
                            value=FilterMode.ARRONDISSEMENT.value,
                            label="Specific arrondissements",
                        ),
                    ],
                    translation_key="filter_mode",
                )
            )
        }

        # Always include radius field (optional when not in radius mode)
        if filter_mode == FilterMode.RADIUS.value:
            schema_dict[vol.Required(CONF_RADIUS, default=DEFAULT_RADIUS_KM)] = (
                vol.Coerce(float)
            )
        else:
            schema_dict[vol.Optional(CONF_RADIUS)] = vol.Coerce(float)

        # Always include arrondissements field (optional when not in arrondissement mode)
        current_arrondissements = (
            user_input.get(CONF_ARRONDISSEMENTS, []) if user_input else []
        )
        if filter_mode == FilterMode.ARRONDISSEMENT.value:
            schema_dict[
                vol.Required(CONF_ARRONDISSEMENTS, default=current_arrondissements)
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=str(arr.value),
                            label=str(arr.value),
                        )
                        for arr in Arrondissement
                    ],
                    multiple=True,
                    translation_key="arrondissements",
                )
            )
        else:
            schema_dict[vol.Optional(CONF_ARRONDISSEMENTS)] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=str(arr.value),
                            label=str(arr.value),
                        )
                        for arr in Arrondissement
                    ],
                    multiple=True,
                    translation_key="arrondissements",
                )
            )

        schema_dict[vol.Required(CONF_PRODUCT_TYPES, default=DEFAULT_PRODUCT_TYPES)] = (
            selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=product.value, label=product.value
                        )
                        for product in ProductType
                    ],
                    multiple=True,
                    translation_key="product_types",
                )
            )
        )

        data_schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                CONF_RADIUS: str(DEFAULT_RADIUS_KM),
                CONF_FILTER_MODE: filter_mode,
            },
        )


class ParisMarketsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Paris Markets.
    Allows users to update scan_interval (and potentially radius/location later).
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                scan_interval_days = int(
                    user_input.get("scan_interval_days", DEFAULT_SCAN_INTERVAL)
                )

                if scan_interval_days < MINIMUM_SCAN_INTERVAL:
                    errors["base"] = "invalid_scan_interval"
                else:
                    scan_interval_seconds = scan_interval_days * 24 * 60 * 60

                    options = {
                        **self.config_entry.options,
                        SCAN_INTERVAL: scan_interval_seconds,
                    }
                    return self.async_create_entry(title="", data=options)
            except ValueError:
                errors["base"] = "invalid_input_type"
            except Exception:
                _LOGGER.exception("Unexpected error in options flow")
                errors["base"] = "unknown"

        # Convert current scan_interval from seconds to days for display
        current_scan_interval_seconds = self.config_entry.options.get(
            SCAN_INTERVAL, int(timedelta(days=DEFAULT_SCAN_INTERVAL).total_seconds())
        )
        current_scan_interval_days = int(current_scan_interval_seconds / (24 * 60 * 60))

        options_schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval_days",
                    default=current_scan_interval_days,
                ): vol.Coerce(int),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
