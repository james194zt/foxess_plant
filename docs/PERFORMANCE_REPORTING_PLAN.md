# FoxESS Performance, Solar Analysis & Cost Reporting

Phased plan for recorder-backed time series, SQLite financial rollups, solar physics diagnostics, and panel charting.

**Storage policy:** HA Recorder for all continuous metrics (5-minute statistics). SQLite (`performance.db`) for daily ledger, payback ROI, and HEMS audit events. No JSON bucket files.

---

## Architecture

| Layer | Technology | Contents |
|-------|------------|----------|
| Live sensors | HA Recorder | PV kW, net grid kW, virtual panel temp, wind, clipping kW, Solcast forecast kW |
| Daily rollup | SQLite | `daily_ledger`, `payback_config`, `hems_events` |
| Charts | `statistics_during_period` | Panel websocket reuses `foxess_plant/fetch_statistics` |
| Rates | Existing tariff sensors | Import/export £/kWh (convert to p/kWh in charts) |

---

## Phase 0 — Foundation (MVP) ✅ in progress

- [x] `PerformanceConfig` + defaults
- [x] `performance/` package: virtual temp, clipping, financial math, sample collector, SQLite store
- [x] Diagnostic sensors (recorder-backed, 5-min updates)
- [x] Coordinator 5-minute tick + midnight ledger commit
- [ ] Panel Performance tab (Phase 5)

### Recorder sensors

| Entity suffix | Unit | Source |
|---------------|------|--------|
| `performance_pv_power_kw` | kW | Modbus PV |
| `performance_net_grid_power_kw` | kW | Export − import (+ = export) |
| `performance_virtual_panel_temp_c` | °C | String voltage → temp (doc 4) |
| `performance_wind_speed_ms` | m/s | Google Weather entity |
| `performance_clipping_loss_kw` | kW | Inverter AC limit saturation |
| `performance_solcast_forecast_kw` | kW | Solcast detailed forecast |

### SQLite schema

See `performance/store.py` — tables `daily_ledger`, `payback_config`, `hems_events`.

---

## Phase 1 — Solar performance reporting

- Forecast accuracy % (actual / Solcast)
- Peak vs rated % (cloud-mirror detection)
- Day classification tags (under / on-target / over forecast)
- Seasonal temperature-adjusted index using virtual panel temp
- Post-rain soiling recovery signal

---

## Phase 2 — Physics & microclimate

### Virtual panel temperature (Ideas doc 4)

```
voltage_delta_pct = (live_v - baseline_v_25c) / baseline_v_25c
temp_delta_c = voltage_delta_pct / temp_coefficient  # e.g. -0.003
virtual_temp_c = 25.0 + temp_delta_c
```

Only when PV > 0.1 kW. Clamp −10…85 °C.

### Charts

- **Wind effect:** virtual temp °C vs wind m/s (dual Y)
- **Cloud flush:** virtual temp low → PV spike above AC limit
- Visibility, dew point, precipitation correlation insights

---

## Phase 3 — Clipping loss

- Detect when PV ≥ 98% of `inverter_ac_limit_kw`
- Estimate unclipped power from recent ramp
- `clipping_loss_kwh_today` + valuation at export rate
- Hatched overlay on day chart

---

## Phase 4 — Cost & financial reporting

Per 5-minute bucket:

| Line | Formula |
|------|---------|
| Export earnings | export_kwh × export_p |
| Import spend | import_kwh × import_p |
| Avoided cost | self_consumed_kwh × import_p |
| Net | export + avoided − import |

Midnight → `daily_ledger` row. Lifetime ROI from `SUM(net_daily_savings_gbp)`.

---

## Phase 5 — Dashboard UI

### Dual-axis day chart (recorder)

Left: PV, net grid, clipping. Right: Agile import rate (p/kWh).

### Summary cards

1. Solar yield (kWh + % of Solcast)
2. Grid trade (export £ | import £)
3. True savings today (net daily savings)
4. Lifetime payback (% + break-even date)

### Physics sub-chart

Virtual panel temp vs wind speed.

---

## Phase 6 — SmartCharge audit (read-only)

Log to `hems_events`: daily plan, plunge override, export armed, spread pairs.

---

## Implementation order

1. **Phase 0** — sensors, store, tick (current)
2. **Phase 1 + 4** — solar rollup + financial ledger
3. **Phase 5** — panel charts + cards
4. **Phase 3 + 2** — clipping + physics charts
5. **Phase 6** — audit trail

---

## Query examples

```sql
SELECT SUM(net_daily_savings_gbp) FROM daily_ledger;
SELECT date, forecast_accuracy_pct FROM daily_ledger WHERE forecast_accuracy_pct > 110;
```

Recorder charts: pass performance sensor entity IDs to `foxess_plant/fetch_statistics` with `period: "5minute"`.
