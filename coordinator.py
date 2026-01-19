"""Data coordinator for ISO-NE Grid Monitor."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import gridstatus
from gridstatus import ISONE

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_ZONE,
    CONF_MONITOR_SYSTEMWIDE,
    DEFAULT_UPDATE_INTERVAL,
    STATUS_NORMAL,
    STATUS_MLCC2,
    STATUS_OP4,
    STATUS_OP7,
    STATUS_EEA1,
    STATUS_EEA2,
    STATUS_EEA3,
    SEVERITY_NORMAL,
    SEVERITY_MLCC2,
    SEVERITY_OP4_EARLY,
    SEVERITY_POWER_WATCH,
    SEVERITY_POWER_WARNING,
    SEVERITY_EMERGENCY,
)

_LOGGER = logging.getLogger(__name__)


class ISONEDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ISO-NE data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.isone = ISONE()
        
        # Get config values
        update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        self.zone = entry.data.get(CONF_ZONE)
        self.monitor_systemwide = entry.data.get(CONF_MONITOR_SYSTEMWIDE, True)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from ISO-NE via gridstatus."""
        try:
            data = {}
            
            # Get system status
            _LOGGER.debug("Fetching ISO-NE system status")
            status_data = await self.hass.async_add_executor_job(
                self._get_status
            )
            data["status"] = status_data
            
            # Get load data
            _LOGGER.debug("Fetching ISO-NE load data")
            load_data = await self.hass.async_add_executor_job(
                self._get_load
            )
            data["load"] = load_data
            
            # Parse status for alerts
            data["parsed_status"] = self._parse_status(status_data)
            
            _LOGGER.debug("Successfully updated ISO-NE data: %s", data)
            return data
            
        except Exception as err:
            _LOGGER.error("Error fetching ISO-NE data: %s", err)
            raise UpdateFailed(f"Error communicating with ISO-NE API: {err}") from err

    def _get_status(self) -> dict[str, Any]:
        """Get current system status (runs in executor)."""
        try:
            status = self.isone.get_status("latest")
            if status is None or status.empty:
                _LOGGER.warning("No status data returned from ISO-NE")
                return {"status": STATUS_NORMAL, "raw": None}
            
            # Convert DataFrame to dict for easier handling
            status_dict = status.to_dict('records')[0] if not status.empty else {}
            return {"status": status_dict.get("Status", STATUS_NORMAL), "raw": status_dict}
            
        except Exception as err:
            _LOGGER.error("Error fetching status: %s", err)
            return {"status": STATUS_NORMAL, "raw": None, "error": str(err)}

    def _get_load(self) -> dict[str, Any]:
        """Get current load data (runs in executor)."""
        try:
            # Get today's load data
            load = self.isone.get_load("today")
            if load is None or load.empty:
                _LOGGER.warning("No load data returned from ISO-NE")
                return {"total_load": None, "zone_load": None}
            
            # Get the most recent load reading
            latest_load = load.iloc[-1]
            
            return {
                "total_load": latest_load.get("Load"),
                "timestamp": latest_load.get("Time"),
                "zone_load": None,  # Zone-specific load requires different API call
            }
            
        except Exception as err:
            _LOGGER.error("Error fetching load: %s", err)
            return {"total_load": None, "zone_load": None, "error": str(err)}

    def _parse_status(self, status_data: dict[str, Any]) -> dict[str, Any]:
        """Parse status data to extract meaningful alerts."""
        status_text = status_data.get("status", STATUS_NORMAL)
        raw_data = status_data.get("raw", {})
        
        parsed = {
            "status": status_text,
            "severity": SEVERITY_NORMAL,
            "op4_action": None,
            "eea_level": None,
            "description": "Grid operating normally",
            "is_emergency": False,
        }
        
        # Normalize status text for parsing
        status_lower = status_text.lower()
        
        # Check for OP-7 Emergency
        if "op-7" in status_lower or "op7" in status_lower or "load shed" in status_lower:
            parsed["status"] = STATUS_OP7
            parsed["severity"] = SEVERITY_EMERGENCY
            parsed["description"] = "Emergency - Load shedding may occur"
            parsed["is_emergency"] = True
            
        # Check for EEA levels
        elif "eea" in status_lower or "energy emergency alert" in status_lower:
            if "eea 3" in status_lower or "eea level 3" in status_lower:
                parsed["status"] = STATUS_EEA3
                parsed["eea_level"] = 3
                parsed["severity"] = SEVERITY_EMERGENCY
                parsed["description"] = "Energy Emergency Alert Level 3"
                parsed["is_emergency"] = True
            elif "eea 2" in status_lower or "eea level 2" in status_lower:
                parsed["status"] = STATUS_EEA2
                parsed["eea_level"] = 2
                parsed["severity"] = SEVERITY_POWER_WARNING
                parsed["description"] = "Energy Emergency Alert Level 2"
                parsed["is_emergency"] = True
            elif "eea 1" in status_lower or "eea level 1" in status_lower:
                parsed["status"] = STATUS_EEA1
                parsed["eea_level"] = 1
                parsed["severity"] = SEVERITY_OP4_EARLY
                parsed["description"] = "Energy Emergency Alert Level 1"
                parsed["is_emergency"] = False
                
        # Check for OP-4 actions
        elif "op-4" in status_lower or "op4" in status_lower:
            # Try to extract action number
            action_num = self._extract_op4_action(status_text)
            parsed["status"] = STATUS_OP4
            parsed["op4_action"] = action_num
            
            if action_num:
                if action_num >= 10:
                    parsed["severity"] = SEVERITY_EMERGENCY
                    parsed["is_emergency"] = True
                    parsed["description"] = f"OP-4 Action {action_num} - Critical"
                elif action_num >= 6:
                    parsed["severity"] = SEVERITY_POWER_WARNING
                    parsed["is_emergency"] = True
                    parsed["description"] = f"OP-4 Action {action_num} - Power Warning"
                elif action_num >= 4:
                    parsed["severity"] = SEVERITY_POWER_WATCH
                    parsed["is_emergency"] = False
                    parsed["description"] = f"OP-4 Action {action_num} - Power Watch"
                else:
                    parsed["severity"] = SEVERITY_OP4_EARLY
                    parsed["is_emergency"] = False
                    parsed["description"] = f"OP-4 Action {action_num} - Early Warning"
            else:
                parsed["severity"] = SEVERITY_OP4_EARLY
                parsed["description"] = "OP-4 Capacity Deficiency Procedure Active"
                
        # Check for M/LCC 2 Alert
        elif "m/lcc" in status_lower or "mlcc" in status_lower or "abnormal" in status_lower:
            parsed["status"] = STATUS_MLCC2
            parsed["severity"] = SEVERITY_MLCC2
            parsed["description"] = "Abnormal conditions alert"
            
        # Check for Power Watch/Warning/Caution
        elif "power warning" in status_lower:
            parsed["severity"] = SEVERITY_POWER_WARNING
            parsed["is_emergency"] = True
            parsed["description"] = "Power Warning - Immediate reduction needed"
        elif "power watch" in status_lower:
            parsed["severity"] = SEVERITY_POWER_WATCH
            parsed["description"] = "Power Watch - Conservation may be needed"
        elif "power caution" in status_lower:
            parsed["severity"] = SEVERITY_OP4_EARLY
            parsed["description"] = "Power Caution - Resources on alert"
            
        return parsed

    def _extract_op4_action(self, status_text: str) -> int | None:
        """Extract OP-4 action number from status text."""
        import re
        
        # Look for patterns like "Action 5", "OP-4 Action 10", etc.
        patterns = [
            r"action\s+(\d+)",
            r"op-?4\s+action\s+(\d+)",
            r"op-?4\s+(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, status_text.lower())
            if match:
                action_num = int(match.group(1))
                if 1 <= action_num <= 11:
                    return action_num
        
        return None
