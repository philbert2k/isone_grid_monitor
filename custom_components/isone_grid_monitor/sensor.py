"""Sensor platform for ISO-NE Grid Monitor."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_ZONE,
    CONF_MONITOR_SYSTEMWIDE,
    ZONES,
    OP4_ACTIONS,
    ATTR_STATUS,
    ATTR_SEVERITY,
    ATTR_DESCRIPTION,
    ATTR_ACTION_NUMBER,
    ATTR_AFFECTED_AREA,
    ATTR_TIMESTAMP,
    ATTR_LOAD_MW,
    ATTR_EEA_LEVEL,
    STATUS_NORMAL,
)
from .coordinator import ISONEDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ISO-NE sensors from a config entry."""
    coordinator: ISONEDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    zone = entry.data.get(CONF_ZONE)
    monitor_systemwide = entry.data.get(CONF_MONITOR_SYSTEMWIDE, True)
    
    sensors: list[SensorEntity] = [
        ISONESystemStatusSensor(coordinator, entry),
        ISONEAlertLevelSensor(coordinator, entry),
        ISONETotalLoadSensor(coordinator, entry),
        ISONEOP4ActionSensor(coordinator, entry),
        ISONESystemCapacitySensor(coordinator, entry),
        ISONECapacityMarginSensor(coordinator, entry),
        ISONEForecastAlertsSensor(coordinator, entry),
    ]
    
    # Add zone-specific load sensor if zone is selected
    if zone and zone != "SYSTEM_WIDE":
        sensors.append(ISONEZoneLoadSensor(coordinator, entry, zone))
    
    async_add_entities(sensors)


class ISONEBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for ISO-NE sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "ISO-NE Grid Monitor",
            "manufacturer": "ISO New England",
            "model": "Grid Status Monitor",
            "sw_version": "1.0.1",
        }


class ISONESystemStatusSensor(ISONEBaseSensor):
    """Sensor for ISO-NE system status."""

    _attr_name = "System Status"
    _attr_icon = "mdi:transmission-tower"

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_system_status"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return STATUS_NORMAL
        
        parsed_status = self.coordinator.data.get("parsed_status", {})
        return parsed_status.get("status", STATUS_NORMAL)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        parsed_status = self.coordinator.data.get("parsed_status", {})
        status_data = self.coordinator.data.get("status", {})
        
        attrs = {
            ATTR_SEVERITY: parsed_status.get("severity", 0),
            ATTR_DESCRIPTION: parsed_status.get("description", ""),
        }
        
        if parsed_status.get("op4_action"):
            attrs[ATTR_ACTION_NUMBER] = parsed_status["op4_action"]
            attrs["action_description"] = OP4_ACTIONS.get(parsed_status["op4_action"], "")
        
        if parsed_status.get("eea_level"):
            attrs[ATTR_EEA_LEVEL] = parsed_status["eea_level"]
        
        # Add timestamp if available
        load_data = self.coordinator.data.get("load", {})
        if load_data.get("timestamp"):
            attrs[ATTR_TIMESTAMP] = load_data["timestamp"]
        
        return attrs


class ISONEAlertLevelSensor(ISONEBaseSensor):
    """Sensor for ISO-NE alert level (0-5 scale)."""

    _attr_name = "Alert Level"
    _attr_icon = "mdi:alert-circle"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_alert_level"

    @property
    def native_value(self) -> int:
        """Return the alert level (0-5)."""
        if not self.coordinator.data:
            return 0
        
        parsed_status = self.coordinator.data.get("parsed_status", {})
        return parsed_status.get("severity", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        parsed_status = self.coordinator.data.get("parsed_status", {})
        
        severity = parsed_status.get("severity", 0)
        severity_names = {
            0: "Normal",
            1: "Advisory",
            2: "Warning",
            3: "Watch",
            4: "Alert",
            5: "Emergency",
        }
        
        return {
            "severity_name": severity_names.get(severity, "Unknown"),
            ATTR_DESCRIPTION: parsed_status.get("description", ""),
            "is_emergency": parsed_status.get("is_emergency", False),
        }


class ISONEOP4ActionSensor(ISONEBaseSensor):
    """Sensor for current OP-4 action number."""

    _attr_name = "OP-4 Action"
    _attr_icon = "mdi:clipboard-alert"

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_op4_action"

    @property
    def native_value(self) -> str:
        """Return the current OP-4 action status."""
        if not self.coordinator.data:
            return "None"
        
        parsed_status = self.coordinator.data.get("parsed_status", {})
        action_num = parsed_status.get("op4_action")
        
        if action_num:
            return f"Action {action_num}"
        return "None"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        parsed_status = self.coordinator.data.get("parsed_status", {})
        action_num = parsed_status.get("op4_action")
        
        attrs = {}
        if action_num:
            attrs["action_number"] = action_num
            attrs["action_description"] = OP4_ACTIONS.get(action_num, "Unknown action")
            attrs[ATTR_SEVERITY] = parsed_status.get("severity", 0)
        else:
            attrs["action_number"] = None
            attrs["action_description"] = "No OP-4 action in effect"
        
        return attrs


class ISONETotalLoadSensor(ISONEBaseSensor):
    """Sensor for ISO-NE total system load."""

    _attr_name = "Total System Load"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.MEGA_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_load"

    @property
    def native_value(self) -> float | None:
        """Return the total system load in MW."""
        if not self.coordinator.data:
            return None
        
        load_data = self.coordinator.data.get("load", {})
        return load_data.get("total_load")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        load_data = self.coordinator.data.get("load", {})
        
        attrs = {}
        if load_data.get("timestamp"):
            attrs[ATTR_TIMESTAMP] = load_data["timestamp"]
        
        return attrs


class ISONESystemCapacitySensor(ISONEBaseSensor):
    """Sensor for ISO-NE system capacity."""

    _attr_name = "System Capacity"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.MEGA_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:transmission-tower-export"

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_system_capacity"

    @property
    def native_value(self) -> float | None:
        """Return the system capacity in MW."""
        if not self.coordinator.data:
            return None
        
        return self.coordinator.data.get("capacity")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            "description": "Available generation capacity",
            "source": "ISO-NE 7-day forecast"
        }
        
        if self.coordinator.last_capacity_update:
            attrs["last_updated"] = self.coordinator.last_capacity_update.isoformat()
        
        return attrs


class ISONECapacityMarginSensor(ISONEBaseSensor):
    """Sensor for ISO-NE capacity margin percentage."""

    _attr_name = "Capacity Margin"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:gauge"

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_capacity_margin"

    @property
    def native_value(self) -> float | None:
        """Return the capacity margin percentage."""
        if not self.coordinator.data:
            return None
        
        return self.coordinator.data.get("capacity_margin")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        capacity = self.coordinator.data.get("capacity")
        load = self.coordinator.data.get("load", {}).get("total_load")
        
        attrs = {
            "description": "Available capacity headroom"
        }
        
        if capacity and load:
            attrs["available_mw"] = round(capacity - load, 1)
            attrs["capacity_mw"] = round(capacity, 1)
            attrs["load_mw"] = round(load, 1)
        
        return attrs


class ISONEZoneLoadSensor(ISONEBaseSensor):
    """Sensor for ISO-NE zone-specific load."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.MEGA_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:map-marker-radius"

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
        zone: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._zone = zone
        self._zone_code = ZONES.get(zone, "")
        self._attr_name = f"{zone.replace('_', ' ').title()} Load"
        self._attr_unique_id = f"{entry.entry_id}_zone_load_{zone.lower()}"

    @property
    def native_value(self) -> float | None:
        """Return the zone load in MW."""
        if not self.coordinator.data:
            return None
        
        load_data = self.coordinator.data.get("load", {})
        return load_data.get("zone_load")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            "zone": self._zone,
            "zone_code": self._zone_code,
        }
        
        if not self.coordinator.data:
            return attrs
        
        load_data = self.coordinator.data.get("load", {})
        if load_data.get("timestamp"):
            attrs[ATTR_TIMESTAMP] = load_data["timestamp"]
        
        return attrs


class ISONEForecastAlertsSensor(ISONEBaseSensor):
    """Sensor for ISO-NE 7-day forecast alerts."""

    _attr_name = "Forecast Alerts"
    _attr_icon = "mdi:calendar-alert"

    def __init__(
        self,
        coordinator: ISONEDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_forecast_alerts"

    @property
    def native_value(self) -> str:
        """Return the forecast alert status."""
        if not self.coordinator.data:
            return "No Data"
        
        forecast_data = self.coordinator.data.get("forecast_alerts", {})
        
        if not forecast_data or not forecast_data.get("has_alerts"):
            return "No Alerts"
        
        total_alerts = forecast_data.get("total_alerts", 0)
        alerts = forecast_data.get("alerts", [])
        
        if alerts:
            # Show the nearest upcoming alert
            nearest = alerts[0]
            days = nearest.get("days_ahead", 0)
            if days == 0:
                return f"Alert Today ({total_alerts} total)"
            elif days == 1:
                return f"Alert Tomorrow ({total_alerts} total)"
            else:
                return f"Alert in {days} days ({total_alerts} total)"
        
        return "No Alerts"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        forecast_data = self.coordinator.data.get("forecast_alerts", {})
        
        attrs = {
            "has_alerts": forecast_data.get("has_alerts", False),
            "total_alerts": forecast_data.get("total_alerts", 0),
            "forecast_checked": forecast_data.get("forecast_checked"),
        }
        
        # Add details for each day with alerts
        alerts = forecast_data.get("alerts", [])
        if alerts:
            for idx, day in enumerate(alerts):
                day_key = f"day_{idx}"
                attrs[day_key] = {
                    "date": day.get("date"),
                    "days_ahead": day.get("days_ahead"),
                    "alert_count": day.get("alert_count"),
                    "alerts": [
                        {
                            "type": alert.get("type"),
                            "message": alert.get("message")
                        }
                        for alert in day.get("alerts", [])
                    ]
                }
        
        return attrs
