# Fox Plant panel

The **Fox Plant** panel is a Home Assistant sidebar app (like ESPHome / Z-Wave JS) for monitoring and configuring your inverter through `foxess_plant`.

## Open the panel

After adding the FoxESS Plant integration and restarting HA:

1. Look for **Fox Plant** in the left sidebar (`mdi:solar-power-variant`)
2. Or browse to `/foxess-plant`

The panel registers automatically when at least one plant config entry exists.

## Navigation (HA-style)

| Section | Content |
|---------|---------|
| **Overview** | Live energy-flow diagram (solar → home ← grid ↔ battery) + today’s analytics |
| **Device** | PV gauge, battery card, detailed parameters, battery list |
| **Energy** | Daily kWh / self-consumption stats |
| **Settings** | SOC & work mode (read-only for now), StormSafe hero + config link |

No bottom tab bar — left sidebar on desktop, horizontal section picker on mobile.

## Live energy scene

The overview diagram reads power entities discovered from your inverter device:

- `pv_power`, `load_power`, `grid_import`, `grid_export`, `battery_power`, `battery_soc`

Animated dashed lines show direction and magnitude of power flow.

## StormSafe illustration

Settings → StormSafe shows the Fox-style split-scene hero (prepared vs unprepared house). It highlights when storm prep triggers are active.

Configure triggers under **Integration → Configure → Storm prep**.

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
