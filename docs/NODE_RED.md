# Node-RED integration

`foxess_plant` exposes **Home Assistant services and events**. Use the standard **node-red-contrib-home-assistant-websocket** nodes — no custom Node-RED palette required.

## Rules

1. **Do not** call `foxess_modbus.update_charge_period` from Node-RED if `foxess_plant` control is active.
2. Use `foxess_plant.set_charge_periods` or `set_charge_period` instead.
3. Use `get_plant_state` in a function node when you need a full JSON snapshot.

## Example: cheap-rate window

**Trigger:** state node on `sensor.octopus_cheap_import` → `true`

**Action:** call service `foxess_plant.set_tariff_mode`

```json
{
  "mode": "cheap_import"
}
```

Configure the `cheap_import` profile in integration **Options → Tariff profile**, or use `set_tariff_profile` to define it from Node-RED.

**End trigger:** when cheap window ends → `foxess_plant.apply_baseline` or `disarm_storm_prep`.

## Example: read plant state

**Action:** call service `foxess_plant.get_plant_state` with **Return Response** enabled.

Response fields include:

- `mode`, `control_active`, `override_active`
- `desired_periods`, `actual_periods`, `drift`
- `analytics` (self-consumption, self-sufficiency, kWh splits)
- `active_storm_triggers`, `active_outage_triggers`, `forecast_armed`
- `plant_id`, `inverter`, `entity_map`, `tariff_modes`

## Example: listen for drift

**Events:** all → event type `foxess_plant_control_drift`

Payload includes `desired` and `actual` period arrays. Plant may auto-reapply if **on_drift** is `reapply` (default).

## Example: storm prep from weather binary

Configure trigger entities in integration **Options → Storm prep**, or call the service directly:

**Trigger:** `binary_sensor.met_office_warning` → on

**Action:** `foxess_plant.arm_storm_prep`

```json
{
  "reason": "heavy_rain_warning"
}
```

**Clear:** weather off → `foxess_plant.disarm_storm_prep` (or configure triggers in Options for automatic handling).

## Example: low solar forecast

Configure in **Options → Forecast prep** with your Solcast / Forecast.Solar entity, or monitor `binary_sensor.*_forecast_prep_active`.

When tomorrow's forecast drops below threshold, plant arms overnight charge automatically.

## Events reference

| Event | When |
|-------|------|
| `foxess_plant_period_applied` | Successful Modbus write |
| `foxess_plant_period_apply_failed` | Write failed |
| `foxess_plant_control_drift` | Actual ≠ desired |
| `foxess_plant_external_write_detected` | Same as drift (alias) |
| `foxess_plant_storm_armed` | Storm override armed |
| `foxess_plant_storm_disarmed` | Storm override cleared |
| `foxess_plant_outage_armed` | Outage override armed |
| `foxess_plant_outage_disarmed` | Outage override cleared |
| `foxess_plant_forecast_armed` | Low forecast prep armed |
| `foxess_plant_forecast_disarmed` | Forecast prep cleared |
| `foxess_plant_tariff_applied` | Tariff mode applied |
| `foxess_plant_baseline_restored` | Baseline reapplied |

## Maintenance mode

Call `foxess_plant.release_control` before manual testing in Developer Tools, then `take_control` when done.
