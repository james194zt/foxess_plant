# FoxESS Plant

Central **plant controller** for FoxESS inverters running [foxess_modbus](https://github.com/nathanmarlor/foxess_modbus). Owns charge-period policy, work mode / SOC limits, drift detection, tariff-aware automation, and a full **Fox Plant** sidebar panel — **does not** talk Modbus itself.

Current release: **v0.9.467**

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
- **[FoxESS - Modbus](https://github.com/nathanmarlor/foxess_modbus)** configured and working for your inverter

### Optional integrations

| Integration | Used for |
|-------------|----------|
| **[Google Weather](https://github.com/safepay/ha_google_weather)** (HACS) | StormSafe forecast / current condition / alerts — see [docs/STORMSAFE_GOOGLE_WEATHER.md](docs/STORMSAFE_GOOGLE_WEATHER.md) |
| **Solcast** (hobbyist API key in Fox Plant) | PV forecast charts, SmartCharge solar budget, optional StormSafe PV pre-check |
| **Octopus Energy** (API key in Fox Plant) | Agile / Tracker / Go / Economy 7 / flat tariffs, export/SEG rates, Greener Nights |
| **Glow / Hildebrand IHD** (MQTT and/or Bright API) | Live grid import for analysis; optional SmartCharge meter rate verify |
| **Fox Cloud Open API** | Battery Warmup and cloud scheduler helpers (disable cloud mode scheduler when HA owns control) |
| Local weather / PWS (e.g. Ecowitt) | Performance wind, rain, dew point, and related charts |

## Quick install

See **[docs/INSTALL.md](docs/INSTALL.md)** — HACS or manual copy, add the integration, pick your inverter, then open **Fox Plant** in the sidebar.

Manual install: copy `custom_components/foxess_plant` to `config/custom_components/` and restart Home Assistant.

## Fox Plant panel

| Nav | What you get |
|-----|----------------|
| **Overview** | Live hub-and-spoke energy diagram, weather, daily production / consumption, StormSafe & SmartCharge status |
| **Device** | Analysis, Realtime curves, Alerts, PV Configuration, Quick Settings, **StormSafe**, **SmartCharge**, **Warmup** |
| **Energy Analysis** | Supply / usage balance, costs, and forecast accuracy |
| **Reports** | Energy Report; Octopus Energy Analysis; Performance (if enabled); SmartCharge Analysis (if SmartCharge is on) |
| **Settings** | Fox API, Solcast, Glow meter, Tariff, Weather, Performance |

## Features

### Inverter control (via foxess_modbus)

- Exclusive ownership of charge periods, work mode, and SOC limits when plant control is active
- **Quick Settings** for day-to-day SOC / work mode (locked while SmartCharge is managing the inverter)
- Baseline charge schedule, drift detection vs actual Modbus periods
- Multi-segment Home Assistant scheduler (up to 95 segments)
- Services for take/release control, apply baseline, save schedule — see [docs/NODE_RED.md](docs/NODE_RED.md)

### SmartCharge

Tariff-aware grid charging using **Solcast** PV forecast and **Octopus** (or schedule) rates.

- Operating modes: **Max safety**, **Max profit**, **Max green**
- Daily plan (default 16:00 UK local) with rest-of-today vs full horizon once tomorrow’s Agile rates publish
- Agile polling, negative-import interrupt, price-drop replan
- Spread optimizer, winter / solar-gap fill, export thresholds per mode
- Force-charge only while the planned local HH:MM window is active (does not charge “now” for a future cheap slot)
- Optional **Glow / smart-meter import rate check** before arming — compares live meter vs API within a tolerance and rechecks after a mismatch
- Configure under **Device → SmartCharge**; StormSafe still overrides when severe weather is active

### Octopus Energy tariffs

- Native Octopus API (or external HA rate sensors)
- Tariff types: **Agile**, **Tracker**, **Go**, **Economy 7**, flat / SVT
- Import MPAN plus **export / SEG / Outgoing** rates when present on the account
- Live half-hourly plugin sensors for Agile / Tracker; automatic daily schedule sync for fixed tariffs
- **Reports → Octopus Energy Analysis**: 48h import/export price charts, Greener Nights forecast, overnight alignment, HEMS audit trail
- Configure under **Settings → Tariff** (provider Octopus)

### Solcast PV forecast

- Hobbyist rooftop forecast API (quota-aware polling)
- **Device → PV Configuration** for PV1/PV2 panels (watts, tilt, azimuth, efficiency, degradation)
- Feeds Overview / Energy charts, SmartCharge, and optional StormSafe Solcast pre-check
- Configure under **Settings → Solcast**

### StormSafe (Google Weather)

Pre-charge before severe weather. Configure under **Device → StormSafe** (not Settings).

| Trigger | When it arms |
|---------|----------------|
| **Forecast** | Hourly forecast shows storm within your **lead time** (default 4 h) |
| **Current condition** | Google weather condition type is severe now |
| **Alerts** | Official alert binaries on (if available in your region) |

Optional Solcast pre-check can prefer PV top-up over grid import when forecast solar covers the gap. Disable Fox cloud StormSafe when using this. Detail: [docs/STORMSAFE_GOOGLE_WEATHER.md](docs/STORMSAFE_GOOGLE_WEATHER.md).

### Glow smart meter

- MQTT (`glow/{MAC}/SENSOR/electricitymeter`) and/or Bright API
- Live grid import for Energy Analysis
- Optional SmartCharge live import-rate double-check
- Configure under **Settings → Glow meter**

### Fox Cloud & Battery Warmup

- **Settings → Fox API** — Cloud Open API key + device SN; option to disable the cloud mode scheduler so it does not fight HA
- **Device → Warmup** — Fox-app-style battery heating (start/stop temperatures, low-price slots) via Cloud API

### Performance reporting

- Daily SQLite ledger: PV, import/export, savings, clipping, payback
- Weather / PWS mapping (wind, rain, dew point, radiation, outdoor temp, etc.)
- Virtual panel temperature from string voltage / power history
- **Reports → Performance** (Day / Week / Month) when enabled
- Configure under **Settings → Performance** and **Settings → Weather**

### Tariff schedule (non-Octopus or band editor)

- 24-hour band schedule (Band A–D) with import / export / standing charges
- Entity-backed rates or plugin sensors
- Optional apply of band inverter control
- Named tariff modes via services / automation (`set_tariff_mode`)

## Prep policy priority

When multiple automations want control:

**Outage prep → StormSafe → Forecast prep → SmartCharge / baseline**

Outage and Forecast prep remain available via the integration options / backend (grid-down and low-forecast triggers). Day-to-day panel focus is **StormSafe** and **SmartCharge**.

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/INSTALL.md](docs/INSTALL.md) | Install and first-run |
| [docs/STORMSAFE_GOOGLE_WEATHER.md](docs/STORMSAFE_GOOGLE_WEATHER.md) | StormSafe + Google Weather |
| [docs/NODE_RED.md](docs/NODE_RED.md) | Services, plant state, Node-RED |
| [docs/PANEL.md](docs/PANEL.md) | Panel notes (may lag the live UI — prefer this README + the sidebar) |

## License

MIT
