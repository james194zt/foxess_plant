# FoxESS Plant

Central **plant controller** for FoxESS inverters running [foxess_modbus](https://github.com/nathanmarlor/foxess_modbus). Owns charge period policy, drift detection, analytics, and Node-RED/automation APIs — **does not** talk Modbus directly.

## Why

- Single writer for charge periods (via `foxess_modbus.update_all_charge_periods`)
- No dependency on the community charge-period Lovelace card
- Local replacements for Fox cloud StormSafe, outage prep, and low-solar forecast prep
- Daily energy analytics (self-consumption / self-sufficiency) from mapped inverter entities
- Configurable entity map (auto-discovered from your inverter device)
- Events and services for Node-RED and automations
- Drift detection when something else changes inverter periods

## Requirements

- Home Assistant 2025.1+
- **FoxESS - Modbus** integration configured and working

## Fox Plant panel

Open **Fox Plant** from the HA sidebar for a full GUI: live energy-flow diagram, device overview, analytics, and settings (including StormSafe illustration).

See [docs/PANEL.md](docs/PANEL.md).

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
2. Open integration **Configure** → choose **Baseline schedule**, **Storm prep**, etc.
3. Disable Fox cloud schedules / StormSafe if using local storm prep.
4. Use **`foxess_plant.*` services** in automations and Node-RED — avoid calling `foxess_modbus.update_charge_period` directly.

## Prep policies (local Fox cloud replacements)

| Policy | Trigger | Action |
|--------|---------|--------|
| **Storm prep** | Weather / warning binary sensors | Force charge + optional max SoC |
| **Outage prep** | Grid-down / backup triggers | Force charge while trigger active |
| **Forecast prep** | Solar forecast entity below threshold | Overnight pre-charge |
| **Tariff** | `set_tariff_mode` service / automation | Apply named charge profile |

Priority when multiple triggers are active: **outage → storm → forecast → baseline**.

## Entities

| Entity | Purpose |
|--------|---------|
| `sensor.*_plant_mode` | `baseline` / `storm` / `outage` / `forecast` / `tariff` / `manual` |
| `sensor.*_self_consumption_percent_today` | PV self-consumption % |
| `sensor.*_self_sufficiency_percent_today` | Load self-sufficiency % |
| `binary_sensor.*_control_active` | Plant is allowed to write |
| `binary_sensor.*_period_override` | Temporary override active |
| `binary_sensor.*_control_drift` | Inverter ≠ desired periods |
| `binary_sensor.*_storm_prep_active` | Storm trigger(s) active |
| `binary_sensor.*_outage_prep_active` | Outage trigger(s) active |
| `binary_sensor.*_forecast_prep_active` | Low forecast prep armed |
| `button.*_apply_baseline` | Restore baseline |
| `button.*_disarm_override` | Clear override |

## Services (Node-RED / automations)

See [docs/NODE_RED.md](docs/NODE_RED.md).

Key services:

- `foxess_plant.set_charge_period` / `set_charge_periods`
- `foxess_plant.apply_baseline` / `apply_desired`
- `foxess_plant.arm_storm_prep` / `disarm_storm_prep`
- `foxess_plant.set_tariff_mode` / `set_tariff_profile`
- `foxess_plant.take_control` / `release_control`
- `foxess_plant.get_plant_state` (returns JSON)

## Blueprints

Import from `blueprints/automation/foxess_plant/storm_prep.yaml` for weather-triggered storm prep.

## Events

Listen on HA event bus, e.g. `foxess_plant_period_applied`, `foxess_plant_control_drift`, `foxess_plant_storm_armed`, `foxess_plant_forecast_armed`.

## License

MIT
