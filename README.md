# ISO-NE Grid Monitor for Home Assistant

Monitor the New England power grid in real-time! Get alerts for grid emergencies, capacity deficiencies, and power warnings from ISO New England.

## Quick Start

1. **Install via HACS** or copy to `/config/custom_components/`
2. **Restart Home Assistant**
3. **Add Integration**: Settings → Devices & Services → Add Integration → "ISO-NE Grid Monitor"
4. **Configure**: Select zone (NEW_HAMPSHIRE), update interval (5 min)

## What It Monitors

- **OP-4 Actions** (1-11): Capacity deficiency procedures
- **OP-7**: Emergency load shedding
- **EEA Levels** (1-3): Energy Emergency Alerts
- **System Load**: Real-time MW readings
- **Alert Severity**: 0-5 scale

## Entities Created

- `sensor.isone_grid_monitor_system_status` - Current status
- `sensor.isone_grid_monitor_alert_level` - Severity (0-5)
- `sensor.isone_grid_monitor_op_4_action` - OP-4 action number
- `sensor.isone_grid_monitor_total_system_load` - Load in MW
- `binary_sensor.isone_grid_monitor_grid_emergency` - Emergency flag

## Example Automation

```yaml
automation:
  - alias: "Grid Emergency Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.isone_grid_monitor_grid_emergency
        to: 'on'
    action:
      - service: notify.mobile_app_phone
        data:
          title: "⚡ Grid Emergency"
          message: "{{ states('sensor.isone_grid_monitor_system_status') }}"
```

## Alert Levels

| Level | Status | Meaning |
|-------|--------|---------|
| 0 | Normal | Grid operating normally |
| 1 | Advisory | M/LCC 2 abnormal conditions |
| 2 | Warning | OP-4 Actions 1-3 |
| 3 | Watch | OP-4 Actions 4-5 (Power Watch) |
| 4 | Alert | OP-4 Actions 6-9 (Power Warning) |
| 5 | Emergency | OP-4 10-11, OP-7, or EEA Level 3 |

## Requirements

- Home Assistant 2024.1.0+
- gridstatus Python library (auto-installed)

## Documentation

See INSTALLATION.md for detailed setup instructions.
See QUICKSTART.md for 5-minute deployment guide.
See examples/automations.yaml for more automation examples.

## Support

- GitHub Issues: Report bugs and request features
- Home Assistant Logs: Settings → System → Logs

## License

MIT License - See LICENSE file
