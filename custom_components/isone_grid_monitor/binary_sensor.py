"""Binary sensor platform for ISO-NE Grid Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_SEVERITY,
    ATTR_DESCRIPTION,
    ATTR_STATUS,
    SEVERITY_POWER_WARNING,
)
from .coordinator import ISONEDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ISO-NE binary sensors from a config entry."""
    coordinator: ISONEDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    binary_sensors: list[BinarySensorEntity] = [
        ISONEGridEmergencyBinarySensor(coordinator, entry),
    ]
    
    async_add_entities(binary_sensors)


class ISONEGridEmergencyBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for ISO-NE grid emergency status."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Grid Emergency"
    _attr_has_entity_name = True
    _attr_icon = "mdi:alert"

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_grid_emergency"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "ISO-NE Grid Monitor",
            "manufacturer": "ISO New England",
            "model": "Grid Status Monitor",
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> bool:
        """Return true if grid emergency is active."""
        if not self.coordinator.data:
            return False
        
        parsed_status = self.coordinator.data.get("parsed_status", {})
        return parsed_status.get("is_emergency", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        parsed_status = self.coordinator.data.get("parsed_status", {})
        
        attrs = {
            ATTR_STATUS: parsed_status.get("status", "Unknown"),
            ATTR_SEVERITY: parsed_status.get("severity", 0),
            ATTR_DESCRIPTION: parsed_status.get("description", ""),
        }
        
        # Add OP-4 action if present
        if parsed_status.get("op4_action"):
            attrs["op4_action"] = parsed_status["op4_action"]
        
        # Add EEA level if present
        if parsed_status.get("eea_level"):
            attrs["eea_level"] = parsed_status["eea_level"]
        
        return attrs

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self.is_on:
            return "mdi:alert-circle"
        return "mdi:check-circle"
