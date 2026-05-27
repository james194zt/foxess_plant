# Fox Plant panel

The **Fox Plant** panel is a Home Assistant sidebar app (like ESPHome / Z-Wave JS) for monitoring and configuring your inverter through `foxess_plant`.

## Open the panel

After adding the FoxESS Plant integration and restarting HA:

1. Look for **Fox Plant** in the left sidebar (the panel header uses the same FoxESS logo as **FoxESS - Modbus** in HACS and Settings → Integrations)
2. Or browse to `/foxess-plant`

The panel registers automatically when at least one plant config entry exists.

## Navigation (HA-style)

Top tabs (like **Energy → Summary / Electricity / Gas**):

| Tab | Content |
|-----|---------|
| **Overview** | Live energy-flow diagram + today’s analytics |
| **Device** | PV gauge, battery card, detailed parameters |
| **Energy** | Daily kWh stats, Fox-style breakdown donuts, **Day / Month / Year** history charts |
| **Settings** | Sub-tabs: Quick, Schedule, Work mode, StormSafe, Control |

## Live energy scene

The overview diagram reads power entities discovered from your inverter device:

- `pv_power`, `load_power`, `grid_import`, `grid_export`, `battery_power`, `battery_soc`

Animated dashed lines show direction and magnitude of power flow.

## Settings (interactive)

| Screen | What it does |
|--------|----------------|
| **Quick Settings** | Fox-style triple-handle SOC bar (off-grid min · system min · system max) + numeric inputs |
| **Charge schedule** | Edit both baseline periods → `foxess_plant.set_charge_periods` + apply |
| **Work mode** | Pick inverter mode → `select.select_option` on work_mode entity |
| **StormSafe** | Enable, pick warning binary sensors, storm charge periods, optional max SoC, test arm/disarm |
| **Plant control** | Take / release exclusive period control |

## StormSafe illustration

Settings → StormSafe shows the Fox-style split-scene hero (prepared vs unprepared house). It highlights when storm prep triggers are active.

**StormSafe** uses **Google Weather** only (install guide: [INSTALL.md](INSTALL.md)). Pick your location, set pre-charge **lead time**, press **Turn on StormSafe**. No entity lists unless you open Advanced. See [STORMSAFE_GOOGLE_WEATHER.md](STORMSAFE_GOOGLE_WEATHER.md).

## Building the frontend (optional)

Source lives in `frontend/` (Lit + TypeScript). The shipped bundle is committed at:

`custom_components/foxess_plant/www/foxess-plant-panel.js`

To rebuild when Node.js is available:

```bash
cd frontend
npm install
npm run build
```

## Troubleshooting

- **Panel missing from sidebar** — Confirm `custom_components/foxess_plant/www/foxess-plant-panel.js` exists and restart HA.
- **Blank panel page** — Update to the latest `foxess_plant` release and restart HA (fixes panel registration after reboot). Hard-refresh the browser (Ctrl+F5). Check browser devtools → Network for `/foxess_plant_panel/foxess-plant-panel.js` (should be 200).
- **Empty energy diagram** — Reload the integration so panel entities are re-discovered into `entity_map`.
- **Analytics show —** — Wait for coordinator refresh or check plant sensors exist.
