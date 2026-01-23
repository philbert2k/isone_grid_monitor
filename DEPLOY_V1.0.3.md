# 🚀 Deploy Forecast Alerts - v1.0.3

## Files Ready:
- ✅ coordinator.py - Updated with forecast alert parsing
- ✅ manifest.json - Version 1.0.3
- ⏳ sensor.py - Needs forecast sensor added (easy!)

## Quick Deployment:

```bash
cd /mnt/e/Data/Claude/isone_grid_monitor

# Run the Python script to update sensor.py
python3 add_forecast_sensor.py

# Verify it worked
grep -n "ISONEForecastAlertsSensor" custom_components/isone_grid_monitor/sensor.py

# Should see 2 lines:
# Line ~57: In the sensors list
# Line ~400+: The class definition

# Check what changed
git status
git diff custom_components/isone_grid_monitor/

# Commit everything
git add custom_components/isone_grid_monitor/coordinator.py
git add custom_components/isone_grid_monitor/sensor.py
git add custom_components/isone_grid_monitor/manifest.json

git commit -m "Add 7-day forecast alert monitoring

- New sensor: Forecast Alerts (updates every 30 min)
- Parses ISO-NE 7-day capacity forecast CSV
- Detects upcoming: load relief actions, OP-4 warnings, low reserves
- Shows nearest alert with days ahead countdown
- Full alert details available in sensor attributes
- Version bump to 1.0.3"

# Push to GitHub
git push

# Create release
gh release create v1.0.3 \
  --title "v1.0.3 - Forecast Alert Monitoring" \
  --notes "**New Feature: 7-Day Forecast Alerts** 🔮

Proactive monitoring of upcoming grid issues!

**New Sensor:**
- \`sensor.isone_grid_monitor_forecast_alerts\`
- Monitors ISO-NE's 7-day capacity forecast
- Updates every 30 minutes

**Detects:**
- Load relief actions expected
- Forecasted OP-4 procedures
- Low reserve margin warnings  
- Upcoming capacity deficiencies

**Shows:**
- Nearest upcoming alert
- Days ahead countdown
- Full details in attributes
- Alert type and messages

Get advance warning before grid issues happen!"
```

## What You'll Get:

**New Sensor:** `sensor.isone_grid_monitor_forecast_alerts`

**States:**
- "No Alerts" - All clear for next 7 days
- "Alert Today (2 total)" - Issues forecasted today
- "Alert Tomorrow (1 total)" - Issues tomorrow
- "Alert in 3 days (1 total)" - Issues in 3 days

**Attributes:**
- `has_alerts`: true/false
- `total_alerts`: count
- `forecast_checked`: timestamp
- `day_0`, `day_1`, etc.: Full alert details per day

## Example Automation:

```yaml
automation:
  - alias: "ISO-NE: Forecast Alert Notification"
    trigger:
      - platform: state
        entity_id: sensor.isone_grid_monitor_forecast_alerts
        to: "Alert Tomorrow"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "⚠️ Grid Alert Forecasted Tomorrow"
          message: "ISO-NE expects grid issues tomorrow. Plan accordingly."
```

## After Deployment:

1. Update via HACS (will see v1.0.3)
2. Restart Home Assistant
3. Check Developer Tools → States
4. Look for `sensor.isone_grid_monitor_forecast_alerts`
5. Should show "No Alerts" or forecast data

Done! 🎉
