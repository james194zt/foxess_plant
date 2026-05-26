# FoxESS Plant

Central **plant controller** for FoxESS inverters running [foxess_modbus](https://github.com/nathanmarlor/foxess_modbus). Owns charge period policy, drift detection, analytics, and Node-RED/automation APIs — **does not** talk Modbus directly.

## Why

- Single writer for charge periods (via `foxess_modbus.update_all_charge_periods`)
- No dependency on the community charge-period Lovelace card
- Local **StormSafe** using **[Google Weather](docs/STORMSAFE_GOOGLE_WEATHER.md)** (forecast + conditions)
- Outage prep and low-solar forecast prep
- Daily energy analytics from mapped inverter entities
- **Fox Plant** sidebar panel — configure everything without blueprints

## Requirements

- Home Assistant 2025.1+
- **FoxESS - Modbus** integration configured and working
- **[Google Weather](https://github.com/safepay/ha_google_weather)** (HACS) for StormSafe — see [docs/INSTALL.md](docs/INSTALL.md)

## Quick install

See **[docs/INSTALL.md](docs/INSTALL.md)** — Fox Plant + Google Weather in four steps, then **Turn on StormSafe** in the panel.

## Fox Plant panel

Open **Fox Plant** from the HA sidebar: live energy diagram, schedules, SOC, work mode, and **StormSafe** (Google Weather location + pre-charge lead time).

See [docs/PANEL.md](docs/PANEL.md).

## StormSafe (Google Weather)

| Trigger | When it arms |
|---------|----------------|
| **Forecast** | Hourly forecast shows storm within your **lead time** (default 4 h) |
| **Current condition** | Google weather condition type is severe now |
| **Alerts** | Official alert binaries on (if available in your region) |

Configure in **Fox Plant → Settings → StormSafe** only. Disable Fox cloud StormSafe when using this.

## Prep policies

| Policy | Trigger | Action |
|--------|---------|--------|
| **Storm prep** | Google Weather (above) | Force charge + optional max SoC |
| **Outage prep** | Grid-down / backup triggers | Force charge while active |
| **Forecast prep** | Solar forecast below threshold | Overnight pre-charge |
| **Tariff** | `set_tariff_mode` / automation | Named charge profile |

Priority: **outage → storm → forecast → baseline**.

## Manual install

Copy `custom_components/foxess_plant` to `config/custom_components/` and restart HA.

## Services & blueprints

- Services: [docs/NODE_RED.md](docs/NODE_RED.md)
- Blueprints under `blueprints/automation/foxess_plant/` are **optional** — not required for normal use

## License

MIT
