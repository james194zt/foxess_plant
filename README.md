# FoxESS Plant

Central **plant controller** for FoxESS inverters running [foxess_modbus](https://github.com/nathanmarlor/foxess_modbus). Owns charge period policy, drift detection, and Node-RED/automation APIs — **does not** talk Modbus directly.

## Why

- Single writer for charge periods (via `foxess_modbus.update_all_charge_periods`)
- No dependency on the community charge-period Lovelace card
- Configurable entity map (auto-discovered from your inverter device)
- Events and services for Node-RED and automations
- Drift detection when something else changes inverter periods

## Requirements

- Home Assistant 2025.1+
- **FoxESS - Modbus** integration configured and working

## Install

### HACS custom repository

1. HACS → Custom repositories → `https://github.com/james194zt/foxess_plant`
2. Install **FoxESS Plant**, restart HA
3. Settings → Devices & services → Add integration → **FoxESS Plant**
4. Select your `foxess_modbus` inverter device

### Manual

Copy `custom_components/foxess_plant` to your HA `config/custom_components/` and restart.

## Setup

1. Add integration and pick inverter device (entities auto-discovered).
2. Configure **baseline charge periods** in integration **Options**.
3. Disable Fox cloud schedules / StormSafe if using local storm prep.
4. Use **`foxess_plant.*` services** in automations and Node-RED — avoid calling `foxess_modbus.update_charge_period` directly.

## Entities

| Entity | Purpose |
|--------|---------|
| `sensor.*_plant_mode` | `baseline` / `storm` / `tariff` / `manual` |
| `binary_sensor.*_control_active` | Plant is allowed to write |
| `binary_sensor.*_period_override` | Temporary override active |
| `binary_sensor.*_control_drift` | Inverter ≠ desired periods |
| `button.*_apply_baseline` | Restore baseline |
| `button.*_disarm_override` | Clear override |

## Services (Node-RED / automations)

See [docs/NODE_RED.md](docs/NODE_RED.md).

Key services:

- `foxess_plant.set_charge_period` / `set_charge_periods`
- `foxess_plant.apply_baseline` / `apply_desired`
- `foxess_plant.arm_storm_prep` / `disarm_storm_prep`
- `foxess_plant.take_control` / `release_control`
- `foxess_plant.get_plant_state` (returns JSON)

## Events

Listen on HA event bus, e.g. `foxess_plant_period_applied`, `foxess_plant_control_drift`, `foxess_plant_storm_armed`.

## License

MIT
