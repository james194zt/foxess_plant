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

## Optional: Solcast (rooftop PV forecast only)

Fox Plant uses **Google Weather** for overview conditions and **StormSafe**. Solcast is used only for **rooftop PV power forecasts** (chart overlay and diagnostic sensors), so your 10/day hobbyist quota is not spent on weather.

1. Register a free Solcast **Home PV System** account (10 API requests/day).
2. Fox Plant → **Settings** → **Solcast** → enable, paste API key, enter **latitude and longitude** copied from one of your **two registered sites** on the [Solcast Locations](https://toolkit.solcast.com.au/account/locations) page (not Home Assistant home coordinates), **installation date** (optional; stored to match your Solcast site listing, not sent to the API yet), turn on **Fetch PV forecast**, save.
3. **Settings** → **PV Configuration** — panel count, wattage, **efficiency** (loss factor), **tilt**, and **azimuth** for each enabled PV string (one API call per unique tilt/azimuth group). Tilt/azimuth are also editable under **Solcast**.
4. Power charts use the native PV forecast automatically; you can remove a third-party Solcast HA integration and clear **Charts** → forecast entity if you no longer need a fallback.
5. Diagnostic sensors (e.g. *Solcast PV forecast remaining today*) expose `detailed_forecast` in attributes for automations.

**API budget (typical):** 1–2 calls per refresh (PV1/PV2 with different orientation = 2). In **daylight** mode, Fox Plant reads HA sunrise/sunset, stops polling **1 hour before sunset**, and spaces refreshes evenly across that window (e.g. 10 hours of sun and limit 10 → about one refresh per hour if each refresh uses one API call).
