"""Data coordinator for ISO-NE Grid Monitor."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any
import aiohttp
import pandas as pd
import io

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
    ZONES,
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
        self.zone_code = ZONES.get(self.zone) if self.zone else None
        self.monitor_systemwide = entry.data.get(CONF_MONITOR_SYSTEMWIDE, True)
        
        # Track last update times for CSV data
        self.last_zone_update = None
        self.last_capacity_update = None
        self.last_forecast_update = None
        
        # Cached CSV data
        self.cached_zone_load = None
        self.cached_capacity = None
        self.cached_forecast_alerts = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from ISO-NE via gridstatus and CSV."""
        try:
            data = {}
            now = datetime.now()
            
            # Get system status (every update - 5 min)
            _LOGGER.debug("Fetching ISO-NE system status")
            status_data = await self.hass.async_add_executor_job(
                self._get_status
            )
            data["status"] = status_data
            
            # Get total load (every update - 5 min)
            _LOGGER.debug("Fetching ISO-NE total load")
            load_data = await self.hass.async_add_executor_job(
                self._get_load
            )
            data["load"] = load_data
            
            # Get zone load from CSV (every 10 min)
            if self.zone and self.zone_code:
                if (self.last_zone_update is None or 
                    (now - self.last_zone_update).total_seconds() >= 600):
                    _LOGGER.debug("Fetching zone load from CSV")
                    zone_load = await self._get_zone_load_csv()
                    self.cached_zone_load = zone_load
                    self.last_zone_update = now
                data["load"]["zone_load"] = self.cached_zone_load
            
            # Get capacity from CSV (every 30 min)
            if (self.last_capacity_update is None or 
                (now - self.last_capacity_update).total_seconds() >= 1800):
                _LOGGER.debug("Fetching capacity from CSV")
                capacity = await self._get_capacity_csv()
                self.cached_capacity = capacity
                self.last_capacity_update = now
            data["capacity"] = self.cached_capacity
            
            # Calculate capacity margin
            if data.get("capacity") and data["load"].get("total_load"):
                margin = ((data["capacity"] - data["load"]["total_load"]) / 
                         data["capacity"] * 100)
                data["capacity_margin"] = round(margin, 1)
            else:
                data["capacity_margin"] = None
            
            # Get forecast alerts from CSV (every 30 min)
            if (self.last_forecast_update is None or 
                (now - self.last_forecast_update).total_seconds() >= 1800):
                _LOGGER.debug("Fetching forecast alerts from CSV")
                forecast_alerts = await self._get_forecast_alerts_csv()
                self.cached_forecast_alerts = forecast_alerts
                self.last_forecast_update = now
            data["forecast_alerts"] = self.cached_forecast_alerts
            
            # Parse status for alerts
            data["parsed_status"] = self._parse_status(status_data)
            
            _LOGGER.debug("Successfully updated ISO-NE data")
            return data
            
        except Exception as err:
            _LOGGER.error("Error fetching ISO-NE data: %s", err)
            raise UpdateFailed(f"Error communicating with ISO-NE API: {err}") from err

    def _get_status(self) -> dict[str, Any]:
        """Get current system status (runs in executor)."""
        try:
            status = self.isone.get_status("latest")
            if status is None or (hasattr(status, "empty") and status.empty) or len(status) == 0:
                _LOGGER.warning("No status data returned from ISO-NE")
                return {"status": STATUS_NORMAL, "raw": None}
            
            # Convert DataFrame to dict for easier handling
            status_dict = status.to_dict('records')[0] if not status.empty else {}
            return {"status": status_dict.get("Status", STATUS_NORMAL), "raw": status_dict}
            
        except Exception as err:
            _LOGGER.error("Error fetching status: %s", err)
            return {"status": STATUS_NORMAL, "raw": None, "error": str(err)}

    def _get_load(self) -> dict[str, Any]:
        """Get current total load data (runs in executor)."""
        try:
            # Get today's load data
            load = self.isone.get_load("today")
            if load is None or (hasattr(load, "empty") and load.empty) or len(load) == 0:
                _LOGGER.warning("No load data returned from ISO-NE")
                return {"total_load": None, "zone_load": None}
            
            # Get the most recent load reading
            latest_load = load.iloc[-1]
            
            return {
                "total_load": latest_load.get("Load"),
                "timestamp": latest_load.get("Time"),
                "zone_load": None,  # Will be filled by CSV data
            }
            
        except Exception as err:
            _LOGGER.error("Error fetching load: %s", err)
            return {"total_load": None, "zone_load": None, "error": str(err)}

    async def _get_zone_load_csv(self) -> float | None:
        """Fetch zone load from ISO-NE CSV."""
        try:
            # Format: WW_RT_ACTUAL_LOADS_YYYYMMDD.csv
            date_str = datetime.now().strftime("%Y%m%d")
            url = f"https://www.iso-ne.com/static-transform/csv/histRpts/rt-load/WW_RT_ACTUAL_LOADS_{date_str}.csv"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        _LOGGER.warning(f"Failed to fetch zone load CSV: HTTP {response.status}")
                        return None
                    
                    csv_text = await response.text()
                    
            # Parse CSV
            df = pd.read_csv(io.StringIO(csv_text))
            
            # Find the column for our zone (e.g., ".H.NEWHAMPSHIRE")
            zone_column = None
            for col in df.columns:
                if self.zone.upper() in col.upper():
                    zone_column = col
                    break
            
            if not zone_column:
                _LOGGER.warning(f"Zone column not found for {self.zone}")
                return None
            
            # Get most recent value
            latest_value = df[zone_column].iloc[-1]
            return float(latest_value) if pd.notna(latest_value) else None
            
        except Exception as err:
            _LOGGER.error(f"Error fetching zone load CSV: {err}")
            return None

    async def _get_capacity_csv(self) -> float | None:
        """Fetch system capacity from ISO-NE CSV."""
        try:
            url = f"https://www.iso-ne.com/transform/csv/sdf?start={datetime.now().strftime('%Y%m%d')}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        _LOGGER.warning(f"Failed to fetch capacity CSV: HTTP {response.status}")
                        # Return static fallback
                        return 31500.0
                    
                    csv_text = await response.text()
            
            # Parse CSV
            df = pd.read_csv(io.StringIO(csv_text))
            
            # Get today's capacity (first row is usually today)
            # Look for "Operable Capacity" or similar column
            capacity_col = None
            for col in df.columns:
                if "capacity" in col.lower() or "available" in col.lower():
                    capacity_col = col
                    break
            
            if capacity_col:
                capacity = df[capacity_col].iloc[0]
                return float(capacity) if pd.notna(capacity) else 31500.0
            else:
                # Fallback to static value
                return 31500.0
                
        except Exception as err:
            _LOGGER.error(f"Error fetching capacity CSV: {err}")
            # Return static fallback capacity for New England
            return 31500.0

    async def _get_forecast_alerts_csv(self) -> dict[str, Any]:
        """Fetch 7-day capacity forecast and parse for alerts."""
        try:
            # Use the correct ISO-NE forecast URL with today's date
            date_str = datetime.now().strftime("%Y%m%d")
            url = f"https://www.iso-ne.com/transform/csv/sdf?start={date_str}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        _LOGGER.warning(f"Failed to fetch forecast CSV: HTTP {response.status}")
                        return {
                            "alerts": [], 
                            "has_alerts": False, 
                            "forecast_checked": datetime.now().isoformat()
                        }
                    
                    csv_text = await response.text()
            
            # Parse the CSV data
            lines = csv_text.split('\n')
            data = {}
            days = []
            
            for line in lines:
                if not line.strip():
                    continue
                
                # Parse CSV line (handle quoted values)
                import re as regex
                parts = [p.strip('"') for p in regex.split(',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)]
                
                if not parts:
                    continue
                
                line_type = parts[0]
                
                if line_type == "H" and len(parts) > 2:
                    # Header row with day labels
                    days = parts[2:]
                
                elif line_type == "D" and len(parts) > 1:
                    # Data row
                    label = parts[1]
                    values = parts[2:] if len(parts) > 2 else []
                    if label and values:
                        data[label] = values
            
            # Analyze for capacity issues
            alerts = []
            
            # Check capacity margins
            if "Total Capacity Supply Obligation (CSO)" in data and "Total Available Generation and Imports" in data:
                cso = data["Total Capacity Supply Obligation (CSO)"]
                available = data["Total Available Generation and Imports"]
                
                for i, day in enumerate(days):
                    if i < len(cso) and i < len(available):
                        try:
                            cso_val = float(cso[i].replace(',', ''))
                            avail_val = float(available[i].replace(',', ''))
                            margin = ((avail_val - cso_val) / cso_val * 100)
                            
                            if margin < 5:
                                alerts.append({
                                    "date": day,
                                    "days_ahead": i,
                                    "alerts": [{
                                        "type": "Critical Reserve Margin" if margin < 0 else "Low Reserve Margin",
                                        "message": f"Reserve margin: {margin:.1f}% (Available: {avail_val:,.0f} MW, Required: {cso_val:,.0f} MW)",
                                        "keyword": "capacity"
                                    }],
                                    "alert_count": 1
                                })
                        except (ValueError, IndexError):
                            pass
            
            # Check for high cold weather outages
            if "Anticipated Cold Weather Outages" in data:
                outages = data["Anticipated Cold Weather Outages"]
                for i, day in enumerate(days):
                    if i < len(outages):
                        try:
                            outage_val = float(outages[i].replace(',', ''))
                            if outage_val > 3000:
                                # Find existing alert for this day or create new
                                day_alert = next((a for a in alerts if a["days_ahead"] == i), None)
                                if day_alert:
                                    day_alert["alerts"].append({
                                        "type": "High Cold Weather Outages",
                                        "message": f"{outage_val:,.0f} MW offline due to cold weather",
                                        "keyword": "outage"
                                    })
                                    day_alert["alert_count"] += 1
                                else:
                                    alerts.append({
                                        "date": day,
                                        "days_ahead": i,
                                        "alerts": [{
                                            "type": "High Cold Weather Outages",
                                            "message": f"{outage_val:,.0f} MW offline due to cold weather",
                                            "keyword": "outage"
                                        }],
                                        "alert_count": 1
                                    })
                        except (ValueError, IndexError):
                            pass
            
            return {
                "alerts": alerts,
                "has_alerts": len(alerts) > 0,
                "total_alerts": sum(a["alert_count"] for a in alerts),
                "forecast_checked": datetime.now().isoformat()
            }
            
        except Exception as err:
            _LOGGER.error(f"Error fetching forecast alerts: {err}")
            return {
                "alerts": [], 
                "has_alerts": False, 
                "error": str(err), 
                "forecast_checked": datetime.now().isoformat()
            }

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
