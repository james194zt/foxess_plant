# FoxESS Plant

Central **plant controller** for FoxESS inverters running [foxess_modbus](https://github.com/nathanmarlor/foxess_modbus). Owns charge period policy, drift detection, analytics, and Node-RED/automation APIs — **does not** talk Modbus directly.

## Screenshots
### Overview Page
<img width="719" height="891" alt="image" src="https://github.com/user-attachments/assets/d3a6a079-bed1-46c9-b5b5-bcc2fe71042c" />
<img width="719" height="1039" alt="image" src="https://github.com/user-attachments/assets/27d9bbc7-11ec-4ae7-b8e8-4565882da870" />

### Device Page
<img width="880" height="706" alt="image" src="https://github.com/user-attachments/assets/a8afdcf5-d314-4990-804c-f96740e49335" />

### Analysis Page
<img width="861" height="1022" alt="image" src="https://github.com/user-attachments/assets/d51f5607-2c13-46db-8035-ebb6cb16ea7b" />
<img width="862" height="801" alt="image" src="https://github.com/user-attachments/assets/682f55c4-0480-490e-a0d0-b69df04282d6" />

### Settings Pages
<img width="888" height="744" alt="image" src="https://github.com/user-attachments/assets/7a9a74c3-a6ec-4bbf-b6b4-da2c0aa0f9c9" />
<img width="1100" height="601" alt="image" src="https://github.com/user-attachments/assets/09e68686-2acd-42ef-a413-dff75ab1605b" />
<img width="866" height="1011" alt="image" src="https://github.com/user-attachments/assets/b166ce1e-34b8-4f09-824d-31f440d4b1d9" />
<img width="818" height="907" alt="image" src="https://github.com/user-attachments/assets/16cd7b65-c29f-45b1-9dc6-1e648e748581" />
<img width="824" height="908" alt="image" src="https://github.com/user-attachments/assets/84703bfd-bbbf-455a-8fb2-bc24ceb0ccc8" />



## Requirements

- Home Assistant 2025.1+
- **FoxESS - Modbus** integration configured and working
- **[Google Weather](https://github.com/safepay/ha_google_weather)** (HACS) for StormSafe — see [docs/INSTALL.md](docs/INSTALL.md)

## Quick install

See **[docs/INSTALL.md](docs/INSTALL.md)** — Fox Plant + Google Weather in four steps, then **Turn on StormSafe** in the panel.

## Fox Plant panel

Open **Fox Plant** from the HA sidebar: live energy diagram, schedules, SOC, work mode, and **StormSafe** (Google Weather location + pre-charge lead time).

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

## License

MIT
