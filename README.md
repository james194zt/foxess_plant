# FoxESS Plant

Central **plant controller** for FoxESS inverters running [foxess_modbus](https://github.com/nathanmarlor/foxess_modbus). Owns charge-period policy, work mode / SOC limits, drift detection, tariff-aware automation, and a full **Fox Plant** sidebar panel — **does not** talk Modbus itself.

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
| **E.ON Next** (browser sign-in token in Fox Plant) | Fixed / flexible / Economy 7 / Next Drive tariffs, export rates, standing charge |
| **Fuse Energy** (phone number + texted code in Fox Plant) | Import and/or export tariff, contract dates; real half-hourly meter readings (electricity and gas) into the Energy dashboard |
| **Glow / Hildebrand IHD** (MQTT and/or Bright API) | Live grid import for analysis; optional SmartCharge meter rate verify |
| **Fox Cloud Open API** | Battery Warmup changes (the inverter refuses warm-up writes over Modbus) |
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

### Languages

Every label in the panel, the alarm guide and the Fox Flow Scene card comes from a language file: `custom_components/foxess_plant/www/i18n/en.json` (flat keys such as `"smart_charge.save_smartcharge": "Save SmartCharge"`). The panel follows Home Assistant's language (Profile → Language).

To add a language:

1. Copy `en.json` to the language's code, e.g. `de.json` (or `de-at.json` for a regional variant — `de-at` falls back to `de`, then English).
2. Translate the values; keep the keys. You don't need every label: anything missing shows in English.
3. Keep `{placeholders}` (e.g. `{count}`, `{kwh}`) exactly as written — the panel fills them in. Keys ending `.one` / `.other` are the singular and plural forms.
4. Some labels contain HTML (`<strong>…</strong>`, links) — keep the tags.
5. Reload the panel (a full browser refresh). No restart is needed for label changes.

Product names (Solcast, Octopus, StormSafe, SmartCharge…) and the work-mode values the inverter uses (e.g. *Self Use* in schedules) stay as they are. Text sent by the integration itself — SmartCharge plan reasons, error messages from suppliers — is still English for now.

## Features

### Inverter control (via foxess_modbus)

**FoxESS EVO:** Fox Plant stores its plans **on the inverter's own Mode Scheduler** (through the foxess_modbus
fork's `set_evo_schedule`), so they keep running if Home Assistant stops:

- **Quick Settings → Mode scheduler**: up to 6 slots (work mode, min / max SOC, force charge) plus the
  remaining-time work mode. With no slots, the inverter's scheduler is switched off and it follows Work Mode.
- **SmartCharge** puts each planned grid charge (Force Charge) and planned export (Force Discharge, stopping
  at the plan's level and never below the export floor) on the inverter as a slot 30 minutes before it starts,
  and removes it afterwards.
- **StormSafe, Outage prep and Forecast prep** hold the battery with a rolling 3-hour Force Charge slot,
  extended while armed, so it stays protected if Home Assistant goes down during a storm.
- Fox Plant checks the inverter's schedule every few minutes and re-writes it if it was changed elsewhere
  (don't edit the schedule in the Fox app while Fox Plant is in control).
- Remote Control isn't used for planned actions any more; it stays available for "do it now" commands.
- How the EVO's registers behave, and why: the foxess_modbus fork's `docs/evo/`.

**Other models** use charge periods and Remote Control as before. They're assumed to behave like the EVO and
haven't been tested on hardware yet; reports welcome.

- **Quick Settings** for day-to-day SOC and work mode. On the EVO, System Max SOC can't be set below the
  current battery level (the inverter refuses it), and Fox Plant keeps Max SOC From Grid in step.
- Services for take/release control, apply baseline, StormSafe arm/disarm — see [docs/NODE_RED.md](docs/NODE_RED.md)

### SmartCharge

Cost-optimised grid charging and export using your **tariff**, the **Solcast** PV forecast and your **house-load history**.

- Builds a half-hourly timeline to the end of tomorrow: import/export price, forecast PV, and predicted house load. Load is the median of the last 14 days of the inverter's load energy history, split weekday/weekend when there's enough data.
- Simulates the battery through that timeline and picks charge and export half-hours by cost. It charges overnight only when tomorrow's solar won't cover the house. It never charges at 15p just to avoid importing at 14p. It charges on negative prices and exports at peaks when the energy can be refilled more cheaply.
- Works with Octopus Agile / Tracker / Go / Economy 7 / flat (API or HA rate entities) and with the manual tariff schedule. Prices Agile hasn't published yet are estimated and never scheduled.
- The plan is committed. It is rebuilt when rates, the Solcast forecast or battery SOC change materially, at the daily plan time (default 16:00), and at least hourly.
- Each planned charge stops at the plan's SOC for that window. On the EVO it runs as a Force Charge slot on the inverter (setting "Charge from the inverter's own schedule", on by default); on other models Fox Plant holds Remote Control on during the window.
- Operating modes: **Max safety** (pessimistic solar, larger reserve), **Max profit** (lowest cost), **Max green** (cost plus carbon weighting)
- Settings include max charge / discharge power (kW), minimum saving per kWh, load history days, outage reserve, and export floor
- Optional **Glow / smart-meter import rate check** before arming: compares the live meter rate with the API within a tolerance, and rechecks after a mismatch. Fixed-rate and time-of-use tariffs only: on **Agile and Tracker it's skipped automatically**, because the meter isn't sent the half-hourly prices, so the rate Glow or an IHD reads from it isn't the real price (Octopus disables the IHD's cost display on Agile for the same reason). The rate check below covers those tariffs instead.
- Optional **Stop Exporting At Negative Export Prices** (off by default): while the export price is below 0p, Fox Plant sets the inverter's **Export Power Limit** to 0 W. The inverter stays in Self Use, so solar still runs the house and charges the battery; it just doesn't feed the grid. The limit you had is saved first and written back when the price goes positive, and also after a restart, when the option is turned off, or on Release Control. It's checked every half-hour, never second by second, because the inverter probably keeps this setting in flash memory. A failed write is retried every 2 minutes, with a notification after 3 failures. Needs an inverter with a writable Export Power Limit (EVO with the fork's 0.1.0 or later; KH / H3 Smart in foxess_modbus).
- **Octopus rate evidence** (native Octopus API): for every half-hour the API shows as negative, and every half-hour SmartCharge charges from the grid in, Fox Plant keeps the exact rate row Octopus returned, with the request URL (your API key is never in it), when it was fetched and Octopus's own server time; every later fetch that confirms or changes it; what Fox Plant did (the Force Charge slot written to the inverter, SmartCharge's decision); and the grid import across the half-hour from your smart meter's own register (via Glow) and from the inverter. The meter's price isn't recorded, because on Agile it isn't the real price. It's kept in `.storage`, survives restarts, and is under **Reports → SmartCharge → Octopus Rate Evidence** with **Download CSV / JSON** to send to Octopus if a bill doesn't match.
- **Rate check while charging:** whenever SmartCharge charges from the grid (at any price, not just negative), Fox Plant asks Octopus about the current half-hour every 5 minutes. If the API's rate differs from the one the plan used by more than the meter-check tolerance (0.5p by default), or Octopus no longer lists the half-hour, Octopus's rate replaces the saved one and SmartCharge re-plans at once on the real price, which stops a charge that isn't worth it (e.g. planned at 6p, really 20p). Each check is recorded in the evidence. A request that fails is recorded and the charge carries on, on the rates from the last successful fetch: a failed request isn't evidence the price changed.
- Configure under **Device → SmartCharge**. StormSafe still overrides when severe weather is active.

### Octopus Energy tariffs

- Native Octopus API (or external HA rate sensors)
- Tariff types: **Agile**, **Tracker**, **Go**, **Economy 7**, flat / SVT
- Import MPAN plus **export / SEG / Outgoing** rates when present on the account
- Live half-hourly plugin sensors for Agile / Tracker; automatic daily schedule sync for fixed tariffs
- **Reports → Octopus Energy Analysis**: 48h import/export price charts, Greener Nights forecast, overnight alignment, HEMS audit trail
- Configure under **Settings → Tariff** (provider Octopus)

### E.ON Next tariffs

- Native E.ON Next tariff import (Kraken platform). E.ON Next issues no API keys and has moved sign-in to Auth0 with password sign-in blocked for integrations, so Fox Plant uses a one-off **sign-in token** copied from your browser (Settings → Tariff → E.ON Next has a copy-paste snippet). The token only lasts a few hours, so treat it as single-use: paste it and press **Save E.ON Next** to fetch. Accounts not yet moved can still use email and password
- Tariff types: fixed / flexible, **Economy 7**, and **Next Drive** time-of-use (treated like Go)
- Import and export rates, including an export meter held on a separate E.ON account on the same login
- A good fetch syncs the daily schedule and standing charge and is saved. For fixed and time-of-use tariffs Fox Plant then stops contacting E.ON until the agreement end date, rolling the saved daily rates forward (restarts included). Paste a fresh token and save again if your tariff changes; open-ended or ended agreements keep fetching hourly
- Octopus-only extras (Greener Nights, Octopus Energy Analysis) are not available
- Configure under **Settings → Tariff** (provider E.ON Next)

### Fuse Energy

- Fuse has no API keys, so Fox Plant signs in the way the Fuse website does: **Settings → Tariff**, choose **Fuse** as the Import and/or Export provider, enter your mobile number in international format (e.g. `+447700900123`), press **Send Code**, type in the code Fuse texts you and press **Sign In**. Then **Save Fuse** (import) or **Save Export**. One sign-in serves import and export, and survives restarts
- Reads the current tariff: unit rate(s), the hours each rate applies, standing charge, contract dates and the next price change. Re-read weekly, daily after a contract ends, and on **Fetch Rates Now**; rates are rebuilt from the saved tariff in between, so SmartCharge never runs short of prices
- **Meter readings**: Fuse's real half-hourly smart-meter readings (estimates are never used) go into Home Assistant long-term statistics as **Fuse Grid Import**, **Fuse Grid Export** and **Fuse Gas**, every 6 hours, with 3 months back-filled. Pick them in **Settings → Dashboards → Energy**. They're statistics, not entities: see them in Developer Tools → Statistics. The diagnostic sensor *Fuse meter data up to* shows how far the readings reach
- If Fuse ends the session, Home Assistant shows a notification; the saved rates stay in use until you sign in again
- Not yet seen on a real account: multi-rate (Day/Night) rate hours and the gas readings' unit. Reports welcome
- Developers: what we learned about Fuse's web app is in [docs/FUSE_ENERGY_API.md](docs/FUSE_ENERGY_API.md)

### Mixed suppliers

Import and export each have their own provider on **Settings → Tariff**: the same supplier for both, or e.g. E.ON Next import with Octopus Outgoing or Fuse export, a Home Assistant sensor, or rates you type into the daily schedule (Manual Rates, e.g. a fixed SEG). With export priced elsewhere, the schedule's Export column shows that provider's prices read-only.

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

On the EVO, an armed StormSafe charges to its target and holds the battery there from the inverter's own scheduler (a rolling 3-hour slot, extended while armed), so the battery stays protected even if Home Assistant goes down.

Optional Solcast pre-check can prefer PV top-up over grid import when forecast solar covers the gap. Disable Fox cloud StormSafe when using this. Detail: [docs/STORMSAFE_GOOGLE_WEATHER.md](docs/STORMSAFE_GOOGLE_WEATHER.md).

### Glow smart meter

- MQTT (`glow/{MAC}/SENSOR/electricitymeter`) and/or Bright API
- Live grid import for Energy Analysis
- Optional SmartCharge live import-rate double-check
- **Grid Power Source**: switch **Use Glow for Grid Import** and/or **Use Glow for Grid Export** to take live grid power (flow scene, flow card, performance net grid) from the meter instead of the inverter CT. Inverter CTs can read wrongly at a few hundred watts: on one EVO the CT counted 0.6 kWh of "export" in a morning, including at night with no PV, while the meter recorded 3 Wh. Home is corrected by the same amount so the flows still add up. Each direction goes back to the CT if the meter hasn't reported for 2 minutes.
- Configure under **Settings → Glow meter**

### Fox Cloud & Battery Warmup

- **Settings → Fox API** — Cloud Open API key + device SN (used only for battery warm-up)
- **Device → Warmup** — Fox-app-style battery heating (start/stop temperatures, heating periods) via the Cloud API. On the EVO the current settings can also be read over Modbus (foxess_modbus fork Battery Warm-up entities), but changes have to go through the cloud.

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
| [docs/FUSE_ENERGY_API.md](docs/FUSE_ENERGY_API.md) | Unofficial notes on Fuse Energy's web app: sign-in, tariffs, half-hourly meter readings (for other integrations) |

## License

MIT
