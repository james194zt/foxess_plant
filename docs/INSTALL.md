# Install Fox Plant + Google Weather (simple path)

## 1. FoxESS Modbus

You need a working **FoxESS - Modbus** inverter in Home Assistant first.

## 2. FoxESS Plant

1. HACS → Custom repositories → `https://github.com/james194zt/foxess_plant`
2. Install **FoxESS Plant**, restart Home Assistant
3. Settings → Devices & services → **Add integration** → **FoxESS Plant**
4. Select your inverter device → Confirm

If Google Weather is already installed with **one** location, StormSafe is **pre-linked** automatically (not enabled until you turn it on in the panel).

## 3. Google Weather (native StormSafe weather)

1. HACS → Custom repositories → `https://github.com/safepay/ha_google_weather`
2. Install **Google Weather**, restart Home Assistant
3. Settings → Integrations → **Add** → **Google Weather**
   - Google Maps API key with **Weather API** enabled
   - Location name (e.g. `home`) — same name you will see in Fox Plant
   - Enable **hourly forecast** (recommended)
4. On the Google Weather device page, show **Weather condition** if it is hidden (eye icon)

## 4. Turn on StormSafe

1. Open **Fox Plant** in the sidebar
2. **Settings** → **StormSafe**
3. Select your **Google Weather** location
4. Press **Turn on StormSafe** (or enable + **Save StormSafe settings**)
5. Set **lead time** (default 4 hours) — pre-charge starts when a storm is forecast within that window
6. Disable Fox cloud **StormSafe** to avoid conflicts

## Done

Fox Plant will:

- Pre-charge from **hourly forecast** (storm due within lead time)
- Arm when **current** weather is already severe
- Use **alert binaries** too if Google provides them in your region

See [STORMSAFE_GOOGLE_WEATHER.md](STORMSAFE_GOOGLE_WEATHER.md) for technical detail.
