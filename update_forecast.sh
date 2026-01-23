#!/bin/bash
# Quick update script for adding forecast alerts sensor

cd /mnt/e/Data/Claude/isone_grid_monitor/custom_components/isone_grid_monitor

echo "Creating backup..."
cp sensor.py sensor.py.backup

echo "Adding forecast sensor import to setup..."
# This adds ISONEForecastAlertsSensor to the sensors list around line 56
sed -i '56 a\        ISONEForecastAlertsSensor(coordinator, entry),' sensor.py

echo "Adding forecast sensor class at end of file..."
cat >> sensor.py << 'ENDCLASS'


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
ENDCLASS

echo "Updating version in manifest.json..."
sed -i 's/"version": "1.0.2"/"version": "1.0.3"/' manifest.json

echo "Done! Files updated:"
echo "  - coordinator.py (already updated)"
echo "  - sensor.py (forecast sensor added)"
echo "  - manifest.json (version 1.0.3)"
echo ""
echo "Backup saved as sensor.py.backup"
