# Node-RED integration

`foxess_plant` exposes **Home Assistant services and events**. Use the standard **node-red-contrib-home-assistant-websocket** nodes — no custom Node-RED palette required.

## Rules

1. **Do not** call `foxess_modbus.update_charge_period` from Node-RED if `foxess_plant` control is active.
2. Use `foxess_plant.set_charge_periods` or `set_charge_period` instead.
3. Use `get_plant_state` in a function node when you need a full JSON snapshot.

## Example: cheap-rate window

**Trigger:** state node on `sensor.octopus_cheap_import` → `true`

**Action:** call service `foxess_plant.set_charge_periods`

```json
{
  "charge_periods": [
    {
      "enable_force_charge": true,
      "enable_charge_from_grid": true,
      "start": "00:30",
      "end": "05:00"
    },
    {
      "enable_force_charge": false,
      "enable_charge_from_grid": false,
      "start": "00:00",
      "end": "00:00"
    }
  ],
  "as_override": true,
  "mode": "tariff",
  "reason": "cheap_import"
}
```

**End trigger:** when cheap window ends → `foxess_plant.disarm_storm_prep` (restores baseline).

## Example: read plant state

**Action:** call service `foxess_plant.get_plant_state` with **Return Response** enabled.

Response fields include:

- `mode`, `control_active`, `override_active`
- `desired_periods`, `actual_periods`, `drift`
- `plant_id`, `inverter`, `entity_map`

## Example: listen for drift

**Events:** all → event type `foxess_plant_control_drift`

Payload includes `desired` and `actual` period arrays. Plant may auto-reapply if **on_drift** is `reapply` (default).

## Example: storm prep from weather binary

**Trigger:** `binary_sensor.met_office_warning` → on

**Action:** `foxess_plant.arm_storm_prep`

```json
{
  "charge_periods": [
    {
      "enable_force_charge": true,
      "enable_charge_from_grid": true,
      "start": "00:00",
      "end": "23:59"
    },
    {
      "enable_force_charge": false,
      "enable_charge_from_grid": false,
      "start": "00:00",
      "end": "00:00"
    }
  ],
  "reason": "heavy_rain_warning"
}
```

**Clear:** weather off → `foxess_plant.disarm_storm_prep`

## Events reference

| Event | When |
|-------|------|
| `foxess_plant_period_applied` | Successful Modbus write |
| `foxess_plant_period_apply_failed` | Write failed |
| `foxess_plant_control_drift` | Actual ≠ desired |
| `foxess_plant_external_write_detected` | Same as drift (alias) |
| `foxess_plant_storm_armed` | Storm/tariff override armed |
| `foxess_plant_storm_disarmed` | Storm override cleared |
| `foxess_plant_baseline_restored` | Baseline reapplied |

## Maintenance mode

Call `foxess_plant.release_control` before manual testing in Developer Tools, then `take_control` when done.
