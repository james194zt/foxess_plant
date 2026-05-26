# StormSafe with Google Weather

Fox Plant **StormSafe** pre-charges your battery when severe weather is detected. With **Google Weather** (HACS), that usually means:

1. **Weather condition** sensor (`sensor.{location}_weather_condition`) — primary for UK/EU when alert binaries are missing
2. **Alert binaries** (`*_weather_alert`, etc.) — when Google publishes them for your region

## Weather condition (recommended)

The integration creates `sensor.home_weather_condition` (name varies by location).

| Field | Meaning |
|-------|---------|
| **State** | Localized text, e.g. “Partly cloudy”, “Heavy rain” — do not use for automations |
| **Attribute `type`** | Google API code, e.g. `PARTLY_CLOUDY`, `THUNDERSTORM`, `HEAVY_RAIN` — **StormSafe uses this** |
| **Attribute `is_daytime`** | Day vs night |

StormSafe arms when `type` is one of the storm codes below (same mapping as [ha_google_weather](https://github.com/safepay/ha_google_weather) uses for the `weather.*` entity).

### Storm condition types (Google `type`)

| Google `type` | Typical meaning |
|---------------|-----------------|
| `WINDY`, `WIND_AND_RAIN` | High wind / wind and rain |
| `HEAVY_RAIN`, `HEAVY_RAIN_SHOWERS`, `MODERATE_TO_HEAVY_RAIN`, `RAIN_PERIODICALLY_HEAVY` | Heavy rain |
| `HAIL`, `HAIL_SHOWERS` | Hail |
| `THUNDERSTORM`, `THUNDERSHOWER`, `LIGHT_THUNDERSTORM_RAIN`, `SCATTERED_THUNDERSTORMS`, `HEAVY_THUNDERSTORM`, `SEVERE_THUNDERSTORM` | Thunder |
| `TORNADO`, `HURRICANE`, `TROPICAL_STORM` | Extreme |
| `SNOWSTORM`, `HEAVY_SNOW_STORM`, `BLIZZARD`, `BLOWING_SNOW`, `HEAVY_SNOW`, … | Heavy snow / blizzard |

**Not armed** for benign types such as `CLEAR`, `MOSTLY_CLEAR`, `PARTLY_CLOUDY`, `LIGHT_RAIN`, `DRIZZLE`, `FOG`, etc.

### Inspect in Home Assistant

Developer tools → States → `sensor.home_weather_condition`:

```yaml
state: Partly cloudy
attributes:
  type: PARTLY_CLOUDY
  is_daytime: true
```

When a storm approaches, `type` may change to e.g. `THUNDERSTORM` or `HEAVY_RAIN` and StormSafe will arm (if enabled).

The `weather.home_weather` entity state (`rainy`, `lightning`, `pouring`, …) is used as a fallback if the condition sensor is unavailable.

### Other sensors (thunderstorm probability, etc.)

`sensor.home_thunderstorm_probability` and similar are **numeric forecasts**, not on/off triggers. They are useful for dashboards and future threshold rules, but StormSafe uses **condition `type`**, **hourly forecast lead time**, and alert binaries.

## Configure in Fox Plant

See [INSTALL.md](INSTALL.md). Select your Google Weather location, set **lead time**, press **Turn on StormSafe**.

## Forecast pre-charge (lead time)

Fox Plant reads Google **hourly forecast** (via `weather.get_forecasts`). If a storm-type hour falls within the next **N** hours (default **4**), StormSafe arms early. The panel shows e.g. “storm in ~3h — pre-charge active”.

## Alert binaries (optional)

Where Google supports official alerts, binaries such as `binary_sensor.home_weather_alert` also arm StormSafe when **on**.

## Test

- **Test arm** — applies the storm schedule immediately
- Watch the condition sensor `type` in Developer tools during real weather

Disable Fox cloud **StormSafe** if you rely on local StormSafe.
