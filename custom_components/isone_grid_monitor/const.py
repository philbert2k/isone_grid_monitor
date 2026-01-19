"""Constants for the ISO-NE Grid Monitor integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "isone_grid_monitor"

# Config flow
CONF_ZONE: Final = "zone"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_MONITOR_SYSTEMWIDE: Final = "monitor_systemwide"

# Default values
DEFAULT_UPDATE_INTERVAL: Final = 5  # minutes
DEFAULT_ZONE: Final = "NEW_HAMPSHIRE"

# ISO-NE Zones (gridstatus format)
ZONES: Final = {
    "MAINE": ".Z.MAINE",
    "NEW_HAMPSHIRE": ".Z.NEWHAMPSHIRE", 
    "VERMONT": ".Z.VERMONT",
    "CONNECTICUT": ".Z.CONNECTICUT",
    "RHODE_ISLAND": ".Z.RHODEISLAND",
    "SEMASS": ".Z.SEMASS",
    "WCMASS": ".Z.WCMASS",
    "NEMASSBOST": ".Z.NEMASSBOST",
}

ZONE_IDS: Final = {
    ".Z.MAINE": 4001,
    ".Z.NEWHAMPSHIRE": 4002,
    ".Z.VERMONT": 4003,
    ".Z.CONNECTICUT": 4004,
    ".Z.RHODEISLAND": 4005,
    ".Z.SEMASS": 4006,
    ".Z.WCMASS": 4007,
    ".Z.NEMASSBOST": 4008,
}

# System status levels
STATUS_NORMAL: Final = "Normal"
STATUS_MLCC2: Final = "M/LCC 2 Alert"
STATUS_OP4: Final = "OP-4"
STATUS_OP7: Final = "OP-7 Emergency"
STATUS_EEA1: Final = "EEA Level 1"
STATUS_EEA2: Final = "EEA Level 2"
STATUS_EEA3: Final = "EEA Level 3"

# OP-4 Actions
OP4_ACTIONS: Final = {
    1: "Power Caution - Resources Notified",
    2: "EEA Level 1 Declared",
    3: "Voluntary Load Curtailment Requested",
    4: "Power Watch - Conservation May Be Needed",
    5: "30-Minute Reserve Depletion",
    6: "Demand Response - 2hr Block A",
    7: "Demand Response - 2hr Block B",
    8: "5% Voltage Reduction / EEA Level 2",
    9: "Customer Generation & Industrial Curtailment",
    10: "Power Warning - Immediate Reduction Needed",
    11: "Governor Appeals / Load Shed Preparation",
}

# Alert severity levels (0-5)
SEVERITY_NORMAL: Final = 0
SEVERITY_MLCC2: Final = 1
SEVERITY_OP4_EARLY: Final = 2  # Actions 1-3
SEVERITY_POWER_WATCH: Final = 3  # Actions 4-5
SEVERITY_POWER_WARNING: Final = 4  # Actions 6-9
SEVERITY_EMERGENCY: Final = 5  # Actions 10-11, OP-7, EEA3

# Sensor attributes
ATTR_STATUS: Final = "status"
ATTR_SEVERITY: Final = "severity"
ATTR_DESCRIPTION: Final = "description"
ATTR_ACTION_NUMBER: Final = "action_number"
ATTR_AFFECTED_AREA: Final = "affected_area"
ATTR_TIMESTAMP: Final = "timestamp"
ATTR_LOAD_MW: Final = "load_mw"
ATTR_RESERVE_MW: Final = "reserve_mw"
ATTR_EEA_LEVEL: Final = "eea_level"

# Sensor types
SENSOR_SYSTEM_STATUS: Final = "system_status"
SENSOR_ALERT_LEVEL: Final = "alert_level"
SENSOR_OP4_ACTION: Final = "op4_action"
SENSOR_ZONE_LOAD: Final = "zone_load"
SENSOR_TOTAL_LOAD: Final = "total_load"
SENSOR_EMERGENCY: Final = "grid_emergency"

# Update intervals (minutes)
MIN_UPDATE_INTERVAL: Final = 1
MAX_UPDATE_INTERVAL: Final = 60
