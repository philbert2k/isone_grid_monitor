#!/usr/bin/env python3
"""
Quick script to add forecast alert sensor to sensor.py
Run this in WSL: python3 add_forecast_sensor.py
"""

sensor_file = "/mnt/e/Data/Claude/isone_grid_monitor/custom_components/isone_grid_monitor/sensor.py"

# Read current file
with open(sensor_file, 'r') as f:
    lines = f.readlines()

# Find the line with ISONECapacityMarginSensor and add ISONEForecastAlertsSensor after it
updated_lines = []
for i, line in enumerate(lines):
    updated_lines.append(line)
    if 'ISONECapacityMarginSensor(coordinator, entry),' in line:
        # Add the forecast sensor on the next line with same indentation
        updated_lines.append('        ISONEForecastAlertsSensor(coordinator, entry),\n')

# Add the new sensor class at the end
forecast_sensor_class = '''

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
'''

updated_lines.append(forecast_sensor_class)

# Write updated file
with open(sensor_file, 'w') as f:
    f.writelines(updated_lines)

print("✅ sensor.py updated successfully!")
print("✅ Forecast alert sensor added")
