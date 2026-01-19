"""Config flow for ISO-NE Grid Monitor integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_ZONE,
    CONF_UPDATE_INTERVAL,
    CONF_MONITOR_SYSTEMWIDE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_ZONE,
    ZONES,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class ISONEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ISO-NE Grid Monitor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate update interval
            update_interval = user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            if not MIN_UPDATE_INTERVAL <= update_interval <= MAX_UPDATE_INTERVAL:
                errors[CONF_UPDATE_INTERVAL] = "invalid_update_interval"
            
            if not errors:
                # Create entry
                return self.async_create_entry(
                    title=f"ISO-NE Grid Monitor ({user_input.get(CONF_ZONE, 'System-wide')})",
                    data=user_input,
                )

        # Show form
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MONITOR_SYSTEMWIDE, 
                    default=True
                ): cv.boolean,
                vol.Optional(
                    CONF_ZONE, 
                    default=DEFAULT_ZONE
                ): vol.In(list(ZONES.keys())),
                vol.Optional(
                    CONF_UPDATE_INTERVAL, 
                    default=DEFAULT_UPDATE_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ISONEOptionsFlowHandler:
        """Get the options flow for this handler."""
        return ISONEOptionsFlowHandler(config_entry)


class ISONEOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for ISO-NE Grid Monitor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate update interval
            update_interval = user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            if not MIN_UPDATE_INTERVAL <= update_interval <= MAX_UPDATE_INTERVAL:
                errors[CONF_UPDATE_INTERVAL] = "invalid_update_interval"
            
            if not errors:
                # Update entry
                return self.async_create_entry(title="", data=user_input)

        # Get current values
        current_zone = self.config_entry.data.get(CONF_ZONE, DEFAULT_ZONE)
        current_interval = self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        current_systemwide = self.config_entry.data.get(CONF_MONITOR_SYSTEMWIDE, True)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MONITOR_SYSTEMWIDE,
                    default=current_systemwide
                ): cv.boolean,
                vol.Optional(
                    CONF_ZONE,
                    default=current_zone
                ): vol.In(list(ZONES.keys())),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=current_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
