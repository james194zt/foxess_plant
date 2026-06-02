/**
 * FoxESS Plant panel — HA sidebar app (phases 5a–5e).
 * hass / narrow / panel / route from Home Assistant.
 * @version 0.8.112
 */

const NAV = [
  { id: "overview", label: "Overview" },
  { id: "device", label: "Device" },
  { id: "energy", label: "Energy" },
  { id: "settings", label: "Settings" },
];

const SETTINGS_NAV = [
  { id: "main", label: "All" },
  { id: "quick", label: "Quick" },
  { id: "schedules", label: "Schedule" },
  { id: "workmode", label: "Work mode" },
  { id: "storm", label: "StormSafe" },
  { id: "charts", label: "Charts" },
  { id: "control", label: "Control" },
];

/** Fox hub-and-spoke flow (viewBox 0 0 1024 1017). Anchors sync with tools/compose_flow_layers.py */
/** Hub on side/front wall corner — user-tuned v0.8.104 (was y=726). */
const FOX_FLOW_HUB = { x: 536, y: 766 };

const FOX_FLOW_PATHS = {
  "solar-aio": "M 388 422 L 388 696",
  "grid-hub": "M 228 848 L 536 848 L 536 766",
  "hub-grid": "M 536 766 L 536 848 L 228 848",
  "aio-hub": "M 404 724 L 536 766",
  "hub-aio": "M 536 766 L 404 724",
  "hub-home": "M 536 766 L 636 738",
};
const FOX_FLOW_HUB_SPOKES = new Set(["solar-aio", "aio-hub", "hub-aio", "hub-home", "grid-hub", "hub-grid"]);

const FLOW_PATHS_VER = "flow-solar-aio";
const PANEL_VERSION = "0.8.112";
const PANEL_BUILD_FALLBACK = PANEL_VERSION;

/** Manifest version from cached module filename (foxess-plant-panel.v0_8_109.{hash}.js). */
function panelVersionFromModuleUrl() {
  const re = /foxess-plant-panel\.v(\d+)_(\d+)_(\d+)\.[a-f0-9]+\.js/i;
  const urls = [];
  if (typeof import.meta !== "undefined" && import.meta.url) urls.push(import.meta.url);
  for (const script of document.getElementsByTagName("script")) {
    if (script.src) urls.push(script.src);
  }
  for (const src of urls) {
    const m = String(src).match(re);
    if (m) return `${m[1]}.${m[2]}.${m[3]}`;
  }
  return null;
}

function panelElementTag() {
  const ver = panelVersionFromModuleUrl() || PANEL_VERSION;
  return `foxess-plant-panel-${String(ver).replace(/\./g, "_")}`;
}

/** HA scoped registry: one tag, one class — reusing the constructor for multiple tags throws. */
function registerFoxessPlantPanel() {
  const tag = panelElementTag();
  if (customElements.get(tag)) return;
  try {
    customElements.define(tag, FoxessPlantPanel);
  } catch (err) {
    console.error(`FoxESS Plant: could not register <${tag}>`, err);
  }
}
const FLOW_STROKE = { base: 4, active: 7, hubR: 8 };
/** Inactive pipe track — Fox charcoal softened for 3D scene overlay (app uses darker on flat grey UI). */
const FLOW_PIPE_STROKE = "#A8AEB6";
/** Active flow colours (brighter than Material defaults for contrast on pipe tracks). */
const FLOW_ACTIVE_STROKE = {
  solar: "#F5BC00",
  grid: "#4A9AFF",
  export: "#B565FF",
  battery: "#4DDC72",
  home: "#4DDC72",
  hub: "#4C925B",
};
const FLOW_DASH = "18 22";
const FLOW_SCENE_PV_THRESHOLD_W = 40;
const FLOW_SCENE_ASSET_VER = 34;

const FLOW_SCENE_BG_THEMES = new Set([
  "day_light",
  "day_dark",
  "night_light",
  "night_dark",
]);

function flowPathMarkup({ d, cls, isBase = false, isActive = false, reverse = false }) {
  const sw = isActive && !isBase ? FLOW_STROKE.active : FLOW_STROKE.base;
  const dash = isActive && !isBase ? ` stroke-dasharray="${FLOW_DASH}"` : "";
  const cap = isActive && !isBase ? ' stroke-linecap="butt"' : ' stroke-linecap="round"';
  const activeCls = isActive && !isBase ? " active" : "";
  const rev = reverse ? " reverse" : "";
  const baseCls = isBase ? " flow-path-base" : "";
  return `<path class="flow-path${baseCls} ${cls}${activeCls}${rev}" d="${d}" stroke-width="${sw}"${dash}${cap}></path>`;
}

const DEFAULT_PERIODS = [
  { enable_force_charge: false, enable_charge_from_grid: false, start: "00:00", end: "00:00" },
  { enable_force_charge: false, enable_charge_from_grid: false, start: "00:00", end: "00:00" },
];

const WORK_MODE_HINTS = {
  "Self Use": "Prioritise powering your home from solar and battery.",
  "Feed-in Priority": "Export surplus solar to the grid first.",
  "Back Up": "Keep battery reserved for outages.",
  "Force Charge": "Active remote force-charge session.",
  "Force Discharge": "Active remote force-discharge session.",
};

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Sidebar-style row: title + subtitle stacked (not inline). */
function renderListButton(attrs, title, subtitle) {
  const parts = ['type="button"', 'class="list-btn"'];
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value != null && value !== "") parts.push(`data-${esc(key)}="${esc(String(value))}"`);
  }
  return `<button ${parts.join(" ")}>
<span class="list-btn-body"><span class="list-btn-title">${esc(title)}</span><span class="list-btn-sub">${esc(subtitle)}</span></span>
<span class="chev" aria-hidden="true">›</span></button>`;
}

function stateNumber(hass, entityId) {
  if (!entityId || !hass?.states) return 0;
  const st = hass.states[entityId];
  if (!st || st.state === "unavailable" || st.state === "unknown") return 0;
  const n = parseFloat(st.state);
  return Number.isFinite(n) ? n : 0;
}

/** Normalise HA power sensors to watts (foxess_modbus uses kW). */
function statePowerWatts(hass, entityId) {
  if (!entityId || !hass?.states) return 0;
  const st = hass.states[entityId];
  if (!st || st.state === "unavailable" || st.state === "unknown") return 0;
  const n = parseFloat(st.state);
  if (!Number.isFinite(n)) return 0;
  const unit = String(st.attributes?.unit_of_measurement ?? "")
    .trim()
    .toLowerCase();
  if (unit === "kw") return n * 1000;
  if (unit === "w") return n;
  // foxess_modbus power entities are kW; very large bare numbers are likely watts
  if (Math.abs(n) > 500) return n;
  return n * 1000;
}

function stateString(hass, entityId) {
  if (!entityId || !hass?.states) return "—";
  const st = hass.states[entityId];
  return st ? st.state : "—";
}

/** foxess_modbus inverter_state → Fox app wording (register logic unchanged). */
const FOX_INVERTER_STATE_LABELS = {
  "on grid": "Normal",
  standby: "Checking",
  "off grid": "Off Grid",
  fault: "Fault",
};

function foxInverterStateLabelFromRaw(raw) {
  if (raw == null || raw === "" || raw === "—") return "—";
  if (raw === "unavailable" || raw === "unknown") return raw;
  const mapped = FOX_INVERTER_STATE_LABELS[String(raw).trim().toLowerCase()];
  return mapped ?? raw;
}

function foxInverterStateLabel(hass, plant, plantState) {
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  const entityId = map.inverter_state;
  const raw = entityId ? stateString(hass, entityId) : plantState?.identity?.inverter_state;
  return foxInverterStateLabelFromRaw(raw);
}

function foxWorkModeLabel(hass, plant, plantState) {
  const raw = plantState?.settings?.work_mode;
  if (raw && raw !== "unavailable" && raw !== "unknown") return raw;
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  const entityId = map.work_mode;
  return entityId ? stateString(hass, entityId) : "—";
}

/** PCS model from Modbus register (pcs_model_name), else foxess_modbus device label. */
function plantModelSubtitle(hass, plant, plantState) {
  const fromIdentity = plantState?.identity?.pcs_model_name;
  if (fromIdentity && fromIdentity !== "unavailable" && fromIdentity !== "unknown") {
    return String(fromIdentity).trim();
  }
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  const entityId = map.pcs_model_name;
  if (entityId) {
    const raw = stateString(hass, entityId);
    if (raw && raw !== "—" && raw !== "unavailable" && raw !== "unknown") {
      return String(raw).trim();
    }
  }
  const fallback = plant?.inverter;
  return fallback && fallback !== "—" ? String(fallback).trim() : "—";
}

function foxStatusToneClass(label) {
  const s = String(label || "").toLowerCase();
  if (s === "normal") return "is-normal";
  if (s === "fault") return "is-fault";
  if (s === "checking") return "is-checking";
  if (s === "off grid") return "is-offgrid";
  return "";
}

function entityUnit(hass, entityId) {
  const u = hass?.states?.[entityId]?.attributes?.unit_of_measurement;
  return u ? ` ${u}` : "";
}

function formatKw(watts, decimals = 2) {
  const kw = Math.abs(watts) / 1000;
  return kw >= 10 ? `${kw.toFixed(1)} kW` : `${kw.toFixed(decimals)} kW`;
}

function formatPercent(value) {
  return `${Math.round(value)}%`;
}

/** PCS serial for device hero (identity first, then entity). */
function plantDeviceSerial(hass, plant, plantState) {
  const fromIdentity = plantState?.identity?.pcs_serial_number;
  if (fromIdentity && fromIdentity !== "unavailable" && fromIdentity !== "unknown") {
    return String(fromIdentity).trim();
  }
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  const entityId = map.pcs_serial_number;
  if (entityId) {
    const raw = stateString(hass, entityId);
    if (raw && raw !== "—" && raw !== "unavailable" && raw !== "unknown") {
      return String(raw).trim();
    }
  }
  return "—";
}

function formatDevicePowerKw(watts) {
  const kw = Math.abs(watts) / 1000;
  if (kw < 10) return `${kw.toFixed(3)} kW`;
  return `${kw.toFixed(2)} kW`;
}

function deviceBatteryToneClass(status) {
  const s = String(status || "").toLowerCase();
  if (s.includes("charg")) return "is-charging";
  if (s.includes("discharg")) return "is-discharging";
  return "is-idle";
}

/** 270° arc gauge (gap at bottom), Fox app PV style. */
function renderPvThreeQuarterGauge(pvKw, maxKw, valueText, labelText) {
  const r = 42;
  const cx = 50;
  const cy = 52;
  const circ = 2 * Math.PI * r;
  const arcLen = circ * 0.75;
  const gapLen = circ - arcLen;
  const rot = 135;
  const pct = maxKw > 0 ? Math.min(1, Math.max(0, pvKw / maxKw)) : 0;
  const fillLen = arcLen * pct;
  const track = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--divider-color)" stroke-width="9" stroke-linecap="round" stroke-dasharray="${arcLen} ${gapLen}" transform="rotate(${rot} ${cx} ${cy})"/>`;
  const fill =
    fillLen > 0.5
      ? `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--fp-accent)" stroke-width="9" stroke-linecap="round" stroke-dasharray="${fillLen} ${circ - fillLen}" transform="rotate(${rot} ${cx} ${cy})"/>`
      : "";
  return `<div class="device-pv-wrap" role="img" aria-label="${esc(labelText)} ${esc(valueText)}">
<div class="device-pv-gauge"><svg viewBox="0 0 100 104" aria-hidden="true">${track}${fill}</svg></div>
<div class="device-pv-readout"><div class="device-pv-value">${esc(valueText)}</div><div class="device-pv-label">${esc(labelText)}</div></div>
</div>`;
}

function renderDeviceBatteryIcon(socPct) {
  const pct = Math.min(100, Math.max(0, socPct));
  const fillW = Math.round((34 * pct) / 100);
  return `<svg class="device-battery-svg" viewBox="0 0 44 22" aria-hidden="true">
<rect class="device-battery-shell" x="1" y="4" width="36" height="14" rx="2"/>
<rect class="device-battery-cap" x="37" y="8" width="4" height="6" rx="1"/>
<rect class="device-battery-fill" x="3" y="6" width="${fillW}" height="10" rx="1"/>
</svg>`;
}

function renderDeviceBatteryCard(flows, tempDisplay) {
  const tone = deviceBatteryToneClass(flows.batteryStatus);
  const icon = renderDeviceBatteryIcon(flows.batterySoc);
  return `<div class="device-battery-card ${tone}">
<div class="device-battery-top">
<div class="device-battery-status-row">${icon}<span class="device-battery-status">${esc(flows.batteryStatus)}</span></div>
<div class="device-battery-pct">${esc(formatPercent(flows.batterySoc))}</div>
</div>
<div class="device-battery-metrics">
<div class="device-battery-metric device-battery-metric--power"><span class="device-battery-metric-label">Power</span><span class="device-battery-metric-value">${esc(formatDevicePowerKw(flows.batteryW))}</span></div>
<div class="device-battery-metric device-battery-metric--temp"><span class="device-battery-metric-label">Temp.</span><span class="device-battery-metric-value">${esc(tempDisplay)}</span></div>
</div>
</div>`;
}

/** Fox app Solar Analysis palette (matches dashboard plotly cards). */
const FOX_ENERGY = {
  pv: "#05989A",
  load: "#7F3DFF",
  muted: "#C3C8D1",
};

function polarToCartesian(cx, cy, r, deg) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeDonutSlice(cx, cy, rOuter, rInner, startDeg, endDeg) {
  const sweep = endDeg - startDeg;
  if (sweep <= 0) return "";
  if (sweep >= 359.99) endDeg = startDeg + 359.99;
  const startOuter = polarToCartesian(cx, cy, rOuter, endDeg);
  const endOuter = polarToCartesian(cx, cy, rOuter, startDeg);
  const startInner = polarToCartesian(cx, cy, rInner, startDeg);
  const endInner = polarToCartesian(cx, cy, rInner, endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return [
    "M",
    startOuter.x,
    startOuter.y,
    "A",
    rOuter,
    rOuter,
    0,
    large,
    0,
    endOuter.x,
    endOuter.y,
    "L",
    startInner.x,
    startInner.y,
    "A",
    rInner,
    rInner,
    0,
    large,
    1,
    endInner.x,
    endInner.y,
    "Z",
  ].join(" ");
}

function renderEnergyDonut(segments, gapDeg = 3) {
  const active = segments.filter((s) => s.value > 0);
  const total = active.reduce((sum, s) => sum + s.value, 0);
  const cx = 50;
  const cy = 50;
  const rOuter = 44;
  const rInner = 34;
  const stroke = "var(--card-background-color, #17191d)";

  if (total <= 0) {
    return `<svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><circle cx="${cx}" cy="${cy}" r="${(rOuter + rInner) / 2}" fill="none" stroke="${FOX_ENERGY.muted}" stroke-width="${rOuter - rInner}" opacity="0.35"/></svg>`;
  }

  let angle = -90;
  const gap = active.length > 1 ? gapDeg : 0;
  const sweepTotal = 360 - gap * active.length;
  const paths = active.map((seg) => {
    const sweep = (seg.value / total) * sweepTotal;
    const start = angle;
    const end = angle + sweep;
    angle = end + gap;
    const d = describeDonutSlice(cx, cy, rOuter, rInner, start, end);
    return `<path d="${d}" fill="${seg.color}" stroke="${stroke}" stroke-width="2"/>`;
  });
  return `<svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" aria-hidden="true">${paths.join("")}</svg>`;
}

function renderEnergyBreakdownRow({ heading, totalKwh, metrics, segments, centerPct, centerLabel, accent }) {
  const donut = renderEnergyDonut(segments);
  const metricsHtml = metrics
    .map(
      (m) => `<div class="fox-energy-metric">
<div class="fox-energy-metric-label">${esc(m.label)}</div>
<div class="fox-energy-metric-value" style="color:${esc(m.color)}">${m.value.toFixed(2)}<span class="fox-energy-metric-unit"> kWh</span></div>
</div>`
    )
    .join("");
  return `<div class="fox-energy-row">
<div class="fox-energy-copy">
<div class="fox-energy-heading">${esc(heading)}</div>
<div class="fox-energy-total">${totalKwh.toFixed(2)}<span>kWh</span></div>
${metricsHtml}
</div>
<div class="fox-energy-chart" role="img" aria-label="${esc(heading)}">
${donut}
<div class="fox-energy-chart-center">
<div class="fox-energy-chart-pct" style="color:${esc(accent)}">${Math.round(centerPct)}%</div>
<div class="fox-energy-chart-label">${esc(centerLabel)}</div>
</div>
</div>
</div>`;
}

/** Matches dashboard Statistics plotly-graph series (dashboard.yaml). */
const STATISTICS_CHART_SERIES = [
  {
    key: "pv_power",
    label: "Solar",
    legendGroup: "solar",
    color: "#19D4DE",
    fillColor: "rgba(25,212,222,0.16)",
    toKw: true,
    fill: true,
    lineWidth: 1.4,
  },
  {
    key: "battery_charge",
    label: "Battery",
    tooltipLabel: "Battery charging",
    legendGroup: "battery",
    color: "#8DB6FF",
    fillColor: "rgba(141,182,255,0.14)",
    toKw: true,
    negate: true,
    fill: true,
    lineWidth: 1.2,
  },
  {
    key: "battery_discharge",
    label: "Battery",
    tooltipLabel: "Battery discharging",
    legendGroup: "battery",
    color: "#8DB6FF",
    fillColor: "rgba(141,182,255,0.14)",
    toKw: true,
    fill: true,
    hideLegend: true,
    lineWidth: 1.2,
  },
  {
    key: "grid_import",
    label: "Grid",
    tooltipLabel: "Grid import",
    legendGroup: "grid",
    color: "#FF6FAF",
    fillColor: "rgba(255,111,175,0.14)",
    toKw: true,
    abs: true,
    fill: true,
    lineWidth: 1.2,
  },
  {
    key: "grid_export",
    label: "Grid",
    tooltipLabel: "Grid export",
    legendGroup: "grid",
    color: "#FF6FAF",
    fillColor: "rgba(255,111,175,0.14)",
    toKw: true,
    abs: true,
    negate: true,
    fill: true,
    hideLegend: true,
    lineWidth: 1.2,
  },
  {
    key: "load_power",
    label: "Load",
    legendGroup: "load",
    color: "#8A4DFF",
    fillColor: "rgba(138,77,255,0.14)",
    toKw: true,
    negate: true,
    fill: true,
    lineWidth: 1.2,
  },
];

const FORECAST_CHART_STYLE = {
  label: "Forecast",
  tooltipLabel: "Forecast",
  legendGroup: "forecast",
  color: "#FFD700",
  fillColor: "rgba(255,215,0,0.14)",
  fill: true,
  lineWidth: 1.2,
};

/** Consolidated top legend (one button toggles whole group). */
const STATISTICS_LEGEND_ORDER = ["solar", "battery", "grid", "load", "forecast"];
const STATISTICS_LEGEND_LABEL = {
  solar: "Solar",
  battery: "Battery",
  grid: "Grid",
  load: "Load",
  forecast: "Forecast",
};
const STATISTICS_LEGEND_COLORS = {
  solar: "#19D4DE",
  battery: "#8DB6FF",
  grid: "#FF6FAF",
  load: "#8A4DFF",
  forecast: "#FFD700",
};

const STATISTICS_CHART_LAYOUT = {
  width: 1000,
  height: 440,
  pad: { l: 52, r: 4, t: 12, b: 40 },
  xTickHours: 3,
  xTickCount: 8,
  yTickStepKw: 0.5,
};

/** Matches dashboard plotly-graph defaults: statistic mean, period 5minute. */
const STATISTICS_PERIOD_MS = 5 * 60 * 1000;

const ENERGY_CHART_BAR = {
  pv: { suffix: "solar_energy_today", label: "PV", color: FOX_ENERGY.pv },
  load: { suffix: "load_energy_today", label: "Load", color: FOX_ENERGY.load, computed: true },
  grid: { suffix: "grid_consumption_energy_today", label: "From grid", color: "#FF6FAF" },
};

function startOfLocalDay(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function endOfLocalDay(d) {
  const x = new Date(d);
  x.setHours(23, 59, 59, 999);
  return x;
}

/** Merge plant config map with live WS state and hass.states fallbacks (matches Lovelace entity ids). */
const CHART_ENTITY_FALLBACKS = {
  pv_power: ["pv1_power", "pv_power", "pv_power_total", "pv_power_evo_10", "pv_power_now"],
  battery_charge: ["battery_charge_1", "battery_charge"],
  battery_discharge: ["battery_discharge_1", "battery_discharge"],
  grid_import: ["grid_consumption", "grid_import"],
  grid_export: ["feed_in", "grid_ct", "grid_export"],
  load_power: ["load_power", "load_power_total"],
  solar_energy_today: ["solar_energy_today"],
  load_energy_today: ["load_energy_today"],
  battery_discharge_today: ["battery_discharge_today"],
  battery_charge_today: ["battery_charge_today"],
  grid_consumption_energy_today: ["grid_consumption_energy_today"],
};

function entityIdMatchesSuffix(entityId, suffix) {
  return (
    entityId.endsWith(`_${suffix}`) ||
    entityId.includes(`_${suffix}_`) ||
    entityId.endsWith(suffix)
  );
}

function resolveEntityMap(hass, plant, plantState) {
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  if (!hass?.states) return map;
  const ids = Object.keys(hass.states);
  for (const [key, suffixes] of Object.entries(CHART_ENTITY_FALLBACKS)) {
    if (map[key] && hass.states[map[key]]) continue;
    for (const suffix of suffixes) {
      const hit = ids.find((id) => entityIdMatchesSuffix(id, suffix));
      if (hit) {
        map[key] = hit;
        break;
      }
    }
  }
  return map;
}

async function fetchStatisticsDuring(hass, entityIds, start, end) {
  const statistic_ids = entityIds.filter(Boolean);
  if (!statistic_ids.length) return null;
  try {
    const viaPlant = await hass.connection.sendMessagePromise({
      type: "foxess_plant/fetch_statistics",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      entity_ids: statistic_ids,
      period: "5minute",
      statistic: "mean",
    });
    if (viaPlant && typeof viaPlant === "object" && !Array.isArray(viaPlant)) {
      return viaPlant;
    }
  } catch {
    /* older integration without fetch_statistics */
  }
  try {
    const res = await hass.connection.sendMessagePromise({
      type: "recorder/statistics_during_period",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      statistic_ids,
      period: "5minute",
      types: ["mean"],
    });
    return res && typeof res === "object" ? res : null;
  } catch {
    return null;
  }
}

function recorderStatsToPoints(rows, range) {
  return (rows || [])
    .map((row) => {
      const rawStart = row.start ?? row.start_time;
      let t;
      if (typeof rawStart === "number") {
        t = rawStart > 1e12 ? rawStart : rawStart * 1000;
      } else {
        t = new Date(rawStart).getTime();
      }
      if (!Number.isFinite(t) || t < range.tMin || t > range.nowMs) return null;
      const v = row.mean;
      if (v == null || !Number.isFinite(Number(v))) return null;
      return { t, v: Number(v) };
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t);
}

async function fetchHistoryDuring(hass, entityIds, start, end) {
  const ids = entityIds.filter(Boolean);
  if (!ids.length) return {};
  try {
    const viaPlant = await hass.connection.sendMessagePromise({
      type: "foxess_plant/fetch_history",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      entity_ids: ids,
      significant_changes_only: false,
    });
    if (viaPlant && typeof viaPlant === "object" && !Array.isArray(viaPlant)) {
      return viaPlant;
    }
  } catch {
    /* older integration without fetch_history */
  }
  const raw = await hass.connection.sendMessagePromise({
    type: "history/history_during_period",
    start_time: start.toISOString(),
    end_time: end.toISOString(),
    entity_ids: ids,
    minimal_response: true,
    significant_changes_only: false,
    no_attributes: true,
    include_start_time_state: true,
  });
  if (!raw || typeof raw !== "object") return {};
  // HA returns { "sensor.foo": [...] }, not a positional array.
  if (Array.isArray(raw)) {
    const map = {};
    ids.forEach((id, i) => {
      map[id] = raw[i] || [];
    });
    return map;
  }
  return raw;
}

function historyRowsForEntity(histMap, entityId) {
  if (!histMap || !entityId) return [];
  return histMap[entityId] || [];
}

function historyRowTimeMs(row) {
  const raw = row.lu ?? row.last_updated ?? row.last_changed ?? row.lc;
  if (typeof raw === "number") {
    return raw > 1e12 ? raw : raw * 1000;
  }
  const ms = new Date(raw).getTime();
  return Number.isFinite(ms) ? ms : NaN;
}

function historyToPoints(rows) {
  if (!rows?.length) return [];
  const sorted = rows
    .map((row) => {
      if (typeof row.t === "number" && typeof row.v === "number") {
        const t = row.t > 1e12 ? row.t : row.t * 1000;
        return Number.isFinite(t) ? { t, v: row.v } : null;
      }
      const t = historyRowTimeMs(row);
      const v = parseFloat(row.s ?? row.state);
      if (!Number.isFinite(t) || !Number.isFinite(v)) return null;
      return { t, v };
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t);
  const out = [];
  for (const p of sorted) {
    const last = out[out.length - 1];
    if (last && last.t === p.t) out[out.length - 1] = p;
    else out.push(p);
  }
  return out;
}

function transformPowerPoint(v, spec) {
  let x = v;
  if (spec.abs) x = Math.abs(x);
  if (spec.negate) x = -x;
  if (spec.toKw) x /= 1000;
  return x;
}

function entityValueToKw(hass, entityId, value) {
  const unit = String(hass?.states?.[entityId]?.attributes?.unit_of_measurement || "")
    .toLowerCase()
    .replace(/\s/g, "");
  if (unit === "kw") return value;
  return value / 1000;
}

function transformHistoryPoint(hass, entityId, v, spec) {
  let x = v;
  if (spec.toKw) x = entityValueToKw(hass, entityId, x);
  if (spec.abs) x = Math.abs(x);
  if (spec.negate) x = -x;
  return x;
}

function getStatisticsDayRange(now = new Date()) {
  const start = startOfLocalDay(now);
  const tMin = start.getTime();
  return { tMin, tMax: tMin + 24 * 60 * 60 * 1000, nowMs: now.getTime() };
}

/** Bucket raw recorder points into fixed 5-minute intervals using mean (plotly-graph). */
function resamplePointsMean(points, periodMs, originMs, endMs) {
  if (!points.length) return [];
  const buckets = new Map();
  for (const p of points) {
    if (p.t < originMs || p.t > endMs) continue;
    const bucket = originMs + Math.floor((p.t - originMs) / periodMs) * periodMs;
    let entry = buckets.get(bucket);
    if (!entry) {
      entry = { sum: 0, count: 0 };
      buckets.set(bucket, entry);
    }
    entry.sum += p.v;
    entry.count += 1;
  }
  return Array.from(buckets.entries())
    .sort(([a], [b]) => a - b)
    .map(([t, { sum, count }]) => ({ t, v: sum / count }));
}

/** Split when a gap exceeds several buckets (plotly connectgaps: false). */
function splitStatisticsSegments(points, periodMs = STATISTICS_PERIOD_MS, maxGapPeriods = 4) {
  if (!points.length) return [];
  const maxGap = periodMs * maxGapPeriods;
  const segments = [];
  let current = [points[0]];
  for (let i = 1; i < points.length; i++) {
    if (points[i].t - points[i - 1].t > maxGap) {
      if (current.length) segments.push(current);
      current = [];
    }
    current.push(points[i]);
  }
  if (current.length) segments.push(current);
  return segments;
}

function isEvenlySpacedPoints(points, periodMs = STATISTICS_PERIOD_MS, toleranceMs = 90_000) {
  if (points.length < 3) return false;
  let ok = 0;
  for (let i = 1; i < points.length; i++) {
    const dt = points[i].t - points[i - 1].t;
    if (Math.abs(dt - periodMs) <= toleranceMs) ok++;
  }
  return ok / (points.length - 1) >= 0.85;
}

function smoothLinePath(pts) {
  if (!pts.length) return "";
  if (pts.length === 1) return "";
  if (pts.length === 2) {
    return `M${pts[0].x.toFixed(2)},${pts[0].y.toFixed(2)} L${pts[1].x.toFixed(2)},${pts[1].y.toFixed(2)}`;
  }
  let d = `M${pts[0].x.toFixed(2)},${pts[0].y.toFixed(2)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(i - 1, 0)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(i + 2, pts.length - 1)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C${cp1x.toFixed(2)},${cp1y.toFixed(2)} ${cp2x.toFixed(2)},${cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  }
  return d;
}

function statisticsLinePath(pixelPts, timePts) {
  if (pixelPts.length < 2) return "";
  return isEvenlySpacedPoints(timePts || pixelPts) ? smoothLinePath(pixelPts) : polylinePath(pixelPts);
}

function polylinePath(pts) {
  if (!pts.length) return "";
  let d = `M${pts[0].x.toFixed(2)},${pts[0].y.toFixed(2)}`;
  for (let i = 1; i < pts.length; i++) {
    d += ` L${pts[i].x.toFixed(2)},${pts[i].y.toFixed(2)}`;
  }
  return d;
}

function statisticsChartPoints(points, range) {
  return resamplePointsMean(points, STATISTICS_PERIOD_MS, range.tMin, range.nowMs);
}

function interpolateSeriesAt(points, t) {
  if (!points.length) return null;
  if (t <= points[0].t) return points[0].v;
  if (t >= points[points.length - 1].t) return points[points.length - 1].v;
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    if (t >= a.t && t <= b.t) {
      const f = b.t === a.t ? 0 : (t - a.t) / (b.t - a.t);
      return a.v + (b.v - a.v) * f;
    }
  }
  return null;
}

function formatStatisticsHoverTime(ms) {
  const d = new Date(ms);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${mo}-${day} ${h}:${m}`;
}

function formatStatisticsKw(v) {
  return Number.isFinite(v) ? `${v.toFixed(3)} kW` : "—";
}

function fillToZeroPath(pts, yZero, timePts) {
  if (!pts.length) return "";
  const line = statisticsLinePath(pts, timePts);
  if (!line) return "";
  const last = pts[pts.length - 1];
  const first = pts[0];
  return `${line} L${last.x.toFixed(2)},${yZero.toFixed(2)} L${first.x.toFixed(2)},${yZero.toFixed(2)} Z`;
}

function computeStatisticsYDomain(series, padRatio = 0.08) {
  let yMin = 0;
  let yMax = 0.25;
  for (const s of series) {
    for (const p of s.points || []) {
      if (!Number.isFinite(p.v)) continue;
      yMin = Math.min(yMin, p.v);
      yMax = Math.max(yMax, p.v);
    }
  }
  if (yMax <= yMin) yMax = yMin + 1;
  const pad = (yMax - yMin) * padRatio;
  return snapStatisticsYDomain(yMin - pad, yMax + pad);
}

/** Snap Y axis to 0.5 kW ticks (Fox-style scale). */
function snapStatisticsYDomain(yMin, yMax, step = STATISTICS_CHART_LAYOUT.yTickStepKw) {
  let lo = Math.floor(yMin / step) * step;
  let hi = Math.ceil(yMax / step) * step;
  if (hi - lo < step * 2) {
    lo -= step;
    hi += step;
  }
  return { yMin: lo, yMax: hi };
}

function statisticsYTicks(yMin, yMax, step = STATISTICS_CHART_LAYOUT.yTickStepKw) {
  const ticks = [];
  for (let v = yMin; v <= yMax + step * 0.001; v += step) {
    ticks.push(Math.round(v * 2) / 2);
  }
  return ticks;
}

function formatStatisticsYTick(v) {
  const r = Math.round(v * 2) / 2;
  return Number.isInteger(r) ? String(r) : r.toFixed(1);
}

/** Map screen coords to viewBox when SVG uses meet or slice scaling. */
function statisticsPointerScale(svg) {
  const rect = svg.getBoundingClientRect();
  const vb = svg.viewBox.baseVal;
  const par = svg.getAttribute("preserveAspectRatio") || "xMidYMid meet";
  const slice = par.includes("slice");
  const scale = slice
    ? Math.max(rect.width / vb.width, rect.height / vb.height)
    : Math.min(rect.width / vb.width, rect.height / vb.height);
  const renderedW = vb.width * scale;
  const renderedH = vb.height * scale;
  return {
    scale,
    offsetX: (rect.width - renderedW) / 2,
    offsetY: (rect.height - renderedH) / 2,
    vb,
  };
}

function statisticsClientToTime(svg, clientX, padL, plotW, tMin, daySpan) {
  const rect = svg.getBoundingClientRect();
  const { scale, offsetX } = statisticsPointerScale(svg);
  const relX = (clientX - rect.left - offsetX) / scale - padL;
  const frac = Math.max(0, Math.min(1, relX / plotW));
  return tMin + frac * daySpan;
}

const STATISTICS_TOOLTIP_LABEL_BY_ID = {
  battery_charge: "Battery charging",
  battery_discharge: "Battery discharging",
  grid_import: "Grid import",
  grid_export: "Grid export",
};

function statisticsSeriesTooltipLabel(s) {
  if (s.tooltipLabel) return s.tooltipLabel;
  if (s.id && STATISTICS_TOOLTIP_LABEL_BY_ID[s.id]) return STATISTICS_TOOLTIP_LABEL_BY_ID[s.id];
  return s.label;
}

/** Hover tooltip: every series (charging, discharging, import, export, …). */
function statisticsTooltipRowsHtml(seriesMeta, t, hiddenGroups) {
  return seriesMeta
    .map((s) => {
      const g = s.legendGroup;
      if (g && hiddenGroups.has(g)) return "";
      const v = interpolateSeriesAt(s.points, t);
      if (v == null) return "";
      const label = statisticsSeriesTooltipLabel(s);
      return `<div class="statistics-tooltip-row"><span class="statistics-tooltip-label"><i class="statistics-tooltip-swatch" style="background:${esc(s.color)}"></i>${esc(label)}</span><strong>${formatStatisticsKw(v)}</strong></div>`;
    })
    .filter(Boolean)
    .join("");
}

function dailyMaxInRange(points, dayStartMs, dayEndMs) {
  let max = 0;
  for (const p of points) {
    if (p.t >= dayStartMs && p.t <= dayEndMs) max = Math.max(max, p.v);
  }
  return max;
}

function buildStatisticsSeriesPoints(hass, entityId, spec, range, statsMap, hist) {
  const statRows = statsMap?.[entityId];
  let rawPoints;
  if (statRows?.length) {
    rawPoints = recorderStatsToPoints(statRows, range);
  } else {
    rawPoints = statisticsChartPoints(historyToPoints(historyRowsForEntity(hist, entityId)), range);
  }
  return rawPoints.map((p) => ({
    t: p.t,
    v: transformHistoryPoint(hass, entityId, p.v, spec),
  }));
}

function findSolcastTodayEntity(hass, forecastEntityId) {
  if (!hass?.states || !String(forecastEntityId || "").toLowerCase().includes("solcast")) return null;
  const preferred = "sensor.solcast_pv_forecast_forecast_today";
  if (hass.states[preferred]) return preferred;
  const matches = Object.keys(hass.states).filter((eid) => {
    const oid = eid.split(".")[1]?.toLowerCase() || "";
    return oid.includes("solcast") && oid.includes("forecast") && oid.includes("today");
  });
  return matches.sort()[0] || null;
}

function solcastDetailedForecastAttribute(attrs) {
  if (!attrs) return null;
  if (Array.isArray(attrs.detailedForecast) && attrs.detailedForecast.length) {
    return attrs.detailedForecast;
  }
  const siteKeys = Object.keys(attrs).filter((k) => k.startsWith("detailedForecast_"));
  if (!siteKeys.length) return null;
  if (siteKeys.length === 1 && Array.isArray(attrs[siteKeys[0]])) return attrs[siteKeys[0]];
  const byStart = new Map();
  for (const key of siteKeys) {
    const rows = attrs[key];
    if (!Array.isArray(rows)) continue;
    for (const row of rows) {
      const ps = row.period_start;
      const v = Number(row.pv_estimate);
      if (!ps || !Number.isFinite(v)) continue;
      byStart.set(ps, (byStart.get(ps) || 0) + v);
    }
  }
  if (!byStart.size) return null;
  return Array.from(byStart.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([period_start, pv_estimate]) => ({ period_start, pv_estimate }));
}

function interpolatePointsToPeriod(points, periodMs, originMs, endMs) {
  if (!points.length) return [];
  const sorted = [...points].sort((a, b) => a.t - b.t);
  const out = [];
  for (let t = originMs; t <= endMs; t += periodMs) {
    const v = interpolateSeriesAt(sorted, t);
    if (v != null) out.push({ t, v });
  }
  return out;
}

/** Carry last reading into empty 5-minute buckets (sparse forecast sensors). */
function forwardFillResamplePoints(points, periodMs, originMs, endMs) {
  if (!points.length) return [];
  const sorted = [...points].sort((a, b) => a.t - b.t);
  const out = [];
  let lastV = sorted[0].v;
  for (let t = originMs; t <= endMs; t += periodMs) {
    const bucketEnd = t + periodMs;
    let sum = 0;
    let count = 0;
    for (const p of sorted) {
      if (p.t >= t && p.t < bucketEnd) {
        sum += p.v;
        count++;
      }
    }
    if (count > 0) lastV = sum / count;
    else {
      const mid = t + periodMs / 2;
      for (let i = sorted.length - 1; i >= 0; i--) {
        if (sorted[i].t <= mid) {
          lastV = sorted[i].v;
          break;
        }
      }
    }
    out.push({ t, v: lastV });
  }
  return out;
}

function buildForecastSeriesPoints(hass, forecastEntityId, range, hist) {
  const todayId = findSolcastTodayEntity(hass, forecastEntityId);
  if (todayId) {
    const detailed = solcastDetailedForecastAttribute(hass.states[todayId]?.attributes);
    if (detailed?.length) {
      const raw = detailed
        .map((row) => {
          const t = new Date(row.period_start).getTime();
          let v = Number(row.pv_estimate);
          if (!Number.isFinite(t) || !Number.isFinite(v)) return null;
          if (v > 50) v /= 1000;
          return { t, v };
        })
        .filter(Boolean)
        .sort((a, b) => a.t - b.t);
      if (raw.length >= 2) {
        return interpolatePointsToPeriod(
          raw.filter((p) => p.t >= range.tMin && p.t <= range.nowMs),
          STATISTICS_PERIOD_MS,
          range.tMin,
          range.nowMs
        );
      }
    }
  }
  const raw = historyToPoints(historyRowsForEntity(hist, forecastEntityId)).map((p) => ({
    t: p.t,
    v: entityValueToKw(hass, forecastEntityId, p.v),
  }));
  if (!raw.length) return [];
  return forwardFillResamplePoints(raw, STATISTICS_PERIOD_MS, range.tMin, range.nowMs);
}

async function fetchStatisticsChartSeries(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const specs = STATISTICS_CHART_SERIES.map((s) => ({ ...s, entity_id: map[s.key] })).filter(
    (s) => s.entity_id
  );
  if (!specs.length) {
    return { empty: "Map power entities in FoxESS Modbus, then reload FoxESS Plant." };
  }
  const forecastId = plantState?.panel_display?.forecast_entity_id || null;
  const entityIds = specs.map((s) => s.entity_id);
  const now = new Date();
  const start = startOfLocalDay(now);
  const range = getStatisticsDayRange(now);
  const [statsMap, hist] = await Promise.all([
    fetchStatisticsDuring(hass, entityIds, start, now),
    fetchHistoryDuring(
      hass,
      forecastId ? [...entityIds, forecastId] : entityIds,
      start,
      now
    ),
  ]);
  const series = specs.map((spec) => ({
    id: spec.key,
    label: spec.label,
    tooltipLabel: spec.tooltipLabel,
    legendGroup: spec.legendGroup,
    color: spec.color,
    fill: spec.fill,
    fillColor: spec.fillColor,
    hideLegend: spec.hideLegend,
    lineWidth: spec.lineWidth,
    points: buildStatisticsSeriesPoints(hass, spec.entity_id, spec, range, statsMap, hist),
  }));
  if (forecastId) {
    const fPoints = buildForecastSeriesPoints(hass, forecastId, range, hist);
    if (fPoints.length) {
      series.push({
        id: "forecast",
        ...FORECAST_CHART_STYLE,
        connectGaps: true,
        points: fPoints,
      });
    }
  }
  if (!series.some((s) => s.points.length)) {
    const listed = specs.map((s) => s.entity_id).join(", ");
    return {
      empty: `No statistics for: ${listed}. Confirm the Recorder stores 5-minute means for these entities (same as your Lovelace plotly-graph card).`,
    };
  }
  return { series, range };
}

function buildDailyLabels(startDay, count) {
  const labels = [];
  for (let i = 0; i < count; i++) {
    const d = new Date(startDay);
    d.setDate(d.getDate() + i);
    labels.push(d);
  }
  return labels;
}

function formatChartDayLabel(d) {
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function formatChartMonthLabel(d) {
  return d.toLocaleDateString(undefined, { month: "short" });
}

function formatChartTimeLabel(ms) {
  return new Date(ms).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function renderStatisticsChartHtml(series, range) {
  const visible = series.filter((s) => s.points?.length);
  if (!visible.length) {
    return `<p class="placeholder chart-empty">No power history for today yet.</p>`;
  }
  const { width, height, pad, xTickHours, xTickCount } = STATISTICS_CHART_LAYOUT;
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const { tMin, tMax, nowMs } = range;
  const daySpan = tMax - tMin;
  const xScale = (t) => pad.l + ((t - tMin) / daySpan) * w;
  const { yMin, yMax } = computeStatisticsYDomain(visible);
  const ySpan = yMax - yMin || 1;
  const yScale = (v) => pad.t + h - ((v - yMin) / ySpan) * h;
  const yZero = yScale(0);
  const yTicks = statisticsYTicks(yMin, yMax);
  const yUnitX = 12;
  const yAxisX = pad.l;
  const yLabelX = yAxisX - 8;
  const xTicks = Array.from({ length: xTickCount }, (_, i) => tMin + i * xTickHours * 60 * 60 * 1000);

  const plotSeries = visible.map((s) => {
    const clipped = s.points.filter((p) => p.t >= tMin && p.t <= nowMs);
    const segmentPoints = s.connectGaps ? [clipped] : splitStatisticsSegments(clipped);
    const segments = segmentPoints.map((seg) => ({
      timePts: seg,
      pixelPts: seg.map((p) => ({ x: xScale(p.t), y: yScale(p.v), t: p.t, v: p.v })),
    }));
    return { ...s, segments };
  });

  const grid = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${pad.l + w}" y2="${y.toFixed(1)}" class="statistics-grid"/>`;
    })
    .join("");

  const yLabels = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<text x="${yLabelX}" y="${(y + 4).toFixed(1)}" text-anchor="end" class="statistics-axis-y">${esc(formatStatisticsYTick(yv))}</text>`;
    })
    .join("");

  const xLabels = xTicks
    .map((xt) => {
      const x = xScale(xt);
      return `<text x="${x.toFixed(1)}" y="${height - pad.b + 20}" text-anchor="middle" class="statistics-axis-x">${esc(formatChartTimeLabel(xt))}</text>`;
    })
    .join("");

  const fills = plotSeries
    .flatMap((s) =>
      (s.segments || [])
        .filter((seg) => s.fill && seg.pixelPts.length >= 2)
        .map(
          (seg) =>
            `<path class="statistics-fill" data-series-id="${esc(s.id)}" data-legend-group="${esc(s.legendGroup || "")}" d="${fillToZeroPath(seg.pixelPts, yZero, seg.timePts)}" fill="${s.fillColor}" stroke="none"/>`
        )
    )
    .join("");

  const lines = plotSeries
    .flatMap((s) =>
      (s.segments || [])
        .filter((seg) => seg.pixelPts.length >= 2)
        .map(
          (seg) =>
            `<path class="statistics-line" data-series-id="${esc(s.id)}" data-legend-group="${esc(s.legendGroup || "")}" d="${statisticsLinePath(seg.pixelPts, seg.timePts)}" fill="none" stroke="${s.color}" stroke-width="${s.lineWidth || 1.2}" stroke-linecap="round" stroke-linejoin="round"/>`
        )
    )
    .join("");

  const groupsPresent = new Set(visible.map((s) => s.legendGroup || s.id));
  const legendItems = STATISTICS_LEGEND_ORDER.filter((g) => groupsPresent.has(g))
    .map(
      (g) =>
        `<button type="button" class="statistics-legend-item" data-legend-group="${esc(g)}" aria-pressed="true"><i style="background:${esc(STATISTICS_LEGEND_COLORS[g] || "#888")}"></i><span>${esc(STATISTICS_LEGEND_LABEL[g] || g)}</span></button>`
    )
    .join("");

  return `<div class="statistics-chart-wrap" data-statistics-chart="1">
<div class="statistics-chart-legend">${legendItems}</div>
<div class="statistics-chart-plot" data-pad-l="${pad.l}" data-pad-t="${pad.t}" data-pad-b="${pad.b}" data-plot-w="${w}" data-plot-h="${h}" data-t-min="${tMin}" data-t-max="${tMax}" data-y-min="${yMin}" data-y-max="${yMax}" data-now-ms="${nowMs}">
<svg class="statistics-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Statistics power chart">
<text x="${yUnitX}" y="${(pad.t + h / 2).toFixed(1)}" class="statistics-y-label" transform="rotate(-90 ${yUnitX} ${(pad.t + h / 2).toFixed(1)})">kW</text>
${grid}
<line x1="${yAxisX}" y1="${pad.t}" x2="${yAxisX}" y2="${(pad.t + h).toFixed(1)}" class="statistics-y-axis"/>
<line x1="${yAxisX}" y1="${yZero.toFixed(1)}" x2="${(pad.l + w).toFixed(1)}" y2="${yZero.toFixed(1)}" class="statistics-zero-line"/>
${fills}
${lines}
${yLabels}
${xLabels}
<rect class="statistics-hit" x="${pad.l}" y="${pad.t}" width="${w}" height="${h}" fill="transparent"/>
</svg>
<div class="statistics-crosshair" hidden><div class="statistics-spike"></div></div>
<div class="statistics-tooltip" hidden role="tooltip"></div>
</div>
</div>`;
}

function bindStatisticsChart(root, seriesMeta) {
  const wrap = root?.querySelector?.("[data-statistics-chart]");
  if (!wrap || wrap.dataset.bound || !seriesMeta?.length) return;
  const plot = wrap.querySelector(".statistics-chart-plot");
  if (!plot) return;
  wrap.dataset.bound = "1";

  const padL = Number(plot.dataset.padL);
  const padT = Number(plot.dataset.padT);
  const padB = Number(plot.dataset.padB);
  const plotW = Number(plot.dataset.plotW);
  const plotH = Number(plot.dataset.plotH);
  const tMin = Number(plot.dataset.tMin);
  const tMax = Number(plot.dataset.tMax);
  const yMin = Number(plot.dataset.yMin);
  const yMax = Number(plot.dataset.yMax);
  const nowMs = Number(plot.dataset.nowMs);
  const daySpan = tMax - tMin;
  const ySpan = yMax - yMin || 1;
  const svg = plot.querySelector(".statistics-chart-svg");
  const hit = plot.querySelector(".statistics-hit");
  const crosshair = plot.querySelector(".statistics-crosshair");
  const spike = plot.querySelector(".statistics-spike");
  const tooltip = plot.querySelector(".statistics-tooltip");
  const hiddenGroups = new Set();

  const applyLegendVisibility = () => {
    wrap.querySelectorAll("[data-legend-group]").forEach((el) => {
      if (!(el instanceof SVGElement) && !el.classList.contains("statistics-legend-item")) return;
      const g = el.getAttribute("data-legend-group");
      if (!g) return;
      if (el.classList.contains("statistics-legend-item")) {
        el.setAttribute("aria-pressed", hiddenGroups.has(g) ? "false" : "true");
        el.classList.toggle("off", hiddenGroups.has(g));
        return;
      }
      el.style.display = hiddenGroups.has(g) ? "none" : "";
    });
  };

  wrap.querySelectorAll(".statistics-legend-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const g = btn.getAttribute("data-legend-group");
      if (!g) return;
      if (hiddenGroups.has(g)) hiddenGroups.delete(g);
      else hiddenGroups.add(g);
      applyLegendVisibility();
    });
  });

  const showHover = (clientX) => {
    const t = Math.min(statisticsClientToTime(svg, clientX, padL, plotW, tMin, daySpan), nowMs);
    const rect = svg.getBoundingClientRect();
    const { scale, offsetX, offsetY } = statisticsPointerScale(svg);
    const xPx = padL + ((t - tMin) / daySpan) * plotW;
    const screenX = offsetX + xPx * scale;
    crosshair.hidden = false;
    crosshair.style.left = `${screenX}px`;
    crosshair.style.top = `${offsetY + padT * scale}px`;
    crosshair.style.bottom = `${offsetY + padB * scale}px`;
    spike.style.height = "100%";

    const rows = statisticsTooltipRowsHtml(seriesMeta, t, hiddenGroups);
    tooltip.hidden = false;
    tooltip.innerHTML = `<div class="statistics-tooltip-time">${esc(formatStatisticsHoverTime(t))}</div>${rows}`;
    const plotRect = plot.getBoundingClientRect();
    let left = screenX + 12;
    if (left + 200 > plotRect.width) left = screenX - 212;
    tooltip.style.left = `${Math.max(8, left)}px`;
    tooltip.style.top = "12px";
  };

  const hideHover = () => {
    crosshair.hidden = true;
    tooltip.hidden = true;
  };

  hit?.addEventListener("mousemove", (ev) => showHover(ev.clientX));
  hit?.addEventListener("mouseleave", hideHover);
  plot.addEventListener("touchmove", (ev) => {
    if (ev.touches[0]) {
      ev.preventDefault();
      showHover(ev.touches[0].clientX);
    }
  }, { passive: false });
  plot.addEventListener("touchend", hideHover);
}

function renderBarChartSvg(groups, labels, { height = 200 } = {}) {
  const n = labels.length;
  if (!n) return `<p class="placeholder chart-empty">No energy history in this period.</p>`;
  const width = 400;
  const pad = { l: 40, r: 12, t: 16, b: 36 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  let yMax = 0.5;
  for (const g of groups) {
    for (const v of g.values) yMax = Math.max(yMax, v);
  }
  yMax *= 1.15;
  const groupW = w / n;
  const barW = Math.min(14, (groupW / Math.max(groups.length, 1)) * 0.7);
  const rects = [];
  labels.forEach((_, i) => {
    const gx = pad.l + i * groupW + groupW / 2;
    groups.forEach((g, gi) => {
      const v = g.values[i] || 0;
      const bh = (v / yMax) * h;
      const x = gx - (groups.length * barW) / 2 + gi * barW;
      const y = pad.t + h - bh;
      rects.push(
        `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${g.color}" opacity="0.92"/>`
      );
    });
    if (n <= 16 || i % Math.ceil(n / 8) === 0 || i === n - 1) {
      const lx = gx;
      const ly = height - 10;
      const lbl = labels[i] instanceof Date ? formatChartDayLabel(labels[i]) : String(labels[i]);
      rects.push(`<text x="${lx.toFixed(1)}" y="${ly}" text-anchor="middle" class="chart-axis">${esc(lbl)}</text>`);
    }
  });
  const legend = groups
    .map((g) => `<span class="chart-legend-item"><i style="background:${g.color}"></i>${esc(g.label)}</span>`)
    .join("");
  return `<div class="chart-wrap"><svg class="energy-bar-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">${rects.join("")}</svg><div class="chart-legend">${legend}</div></div>`;
}

function formatFoxPower(w) {
  const abs = Math.abs(w);
  if (abs < 1000) return `${Math.round(abs)} W`;
  const kw = abs / 1000;
  return kw < 10 ? `${kw.toFixed(2)} kW` : `${kw.toFixed(1)} kW`;
}

function formatW(w) {
  const kw = Math.abs(w) / 1000;
  return kw < 10 ? `${kw.toFixed(2)} kW` : `${kw.toFixed(1)} kW`;
}

function timeForInput(value) {
  if (!value) return "00:00";
  const p = String(value).split(":");
  return `${p[0].padStart(2, "0")}:${(p[1] || "00").padStart(2, "0")}`;
}

function modeClass(mode) {
  const m = String(mode || "").toLowerCase();
  if (m.includes("storm")) return "mode-storm";
  if (m.includes("outage")) return "mode-outage";
  if (m.includes("override") || m.includes("tariff") || m.includes("forecast")) return "mode-override";
  if (m === "manual") return "mode-manual";
  return "mode-baseline";
}

function readEnergyFlows(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const pvW = statePowerWatts(hass, map.pv_power);
  const loadW = Math.abs(statePowerWatts(hass, map.load_power));
  const gridImportW = statePowerWatts(hass, map.grid_import);
  const gridExportW = statePowerWatts(hass, map.grid_export);
  const batteryW = statePowerWatts(hass, map.battery_power);
  let batteryStatus = "Idle";
  const statusEntity = map.battery_status;
  if (statusEntity && hass.states[statusEntity]) {
    batteryStatus = hass.states[statusEntity].state;
  } else if (batteryW > 50) batteryStatus = "Discharging";
  else if (batteryW < -50) batteryStatus = "Charging";
  return {
    pvW: Math.max(0, pvW),
    loadW,
    gridImportW: Math.max(0, gridImportW),
    gridExportW: Math.max(0, gridExportW),
    batteryW,
    batterySoc: stateNumber(hass, map.battery_soc),
    batteryStatus,
  };
}

function sunPrevNext(hass, key) {
  const raw = hass?.states?.["sun.sun"]?.attributes?.[`next_${key}`];
  if (!raw) return null;
  const nxt = new Date(raw);
  if (Number.isNaN(nxt.getTime())) return null;
  return { prev: new Date(nxt.getTime() - 86_400_000), nxt };
}

function sunLastEvent(hass, key, now) {
  const pair = sunPrevNext(hass, key);
  if (!pair) return null;
  return now >= pair.nxt ? pair.nxt : pair.prev;
}

function sunNextEvent(hass, key, now) {
  const pair = sunPrevNext(hass, key);
  if (!pair) return null;
  return now >= pair.nxt ? new Date(pair.nxt.getTime() + 86_400_000) : pair.nxt;
}

function resolveFlowSceneBgThemeFromSun(hass) {
  const sun = hass?.states?.["sun.sun"];
  if (!sun?.attributes) return null;
  const now = new Date();

  const lastDawn = sunLastEvent(hass, "dawn", now);
  const lastRising = sunLastEvent(hass, "rising", now);
  const lastSetting = sunLastEvent(hass, "setting", now);
  const lastDusk = sunLastEvent(hass, "dusk", now);
  const nextSetting = sunNextEvent(hass, "setting", now);
  if (!lastDawn || !lastRising || !lastSetting || !lastDusk || !nextSetting) return null;

  if (now >= lastDawn && now < lastRising) return "day_dark";
  if (now >= lastRising && now < nextSetting) return "day_light";
  if (now >= lastSetting && now < lastDusk) return "night_light";
  return "night_dark";
}

function resolveFlowSceneBgTheme(hass, plantState) {
  return resolveFlowSceneBgThemeFromSun(hass)
    || (plantState?.flow_scene_theme && FLOW_SCENE_BG_THEMES.has(plantState.flow_scene_theme)
      ? plantState.flow_scene_theme
      : null)
    || "day_light";
}

/** PV/AIO sprites only ship in day_light + night_dark variants. */
function flowSceneOverlayTheme(bgTheme) {
  return bgTheme.startsWith("day_") ? "day_light" : "night_dark";
}

function flowSceneLayerUrl(layer, bgTheme, overlayTheme = flowSceneOverlayTheme(bgTheme)) {
  const theme = layer === "bg" ? bgTheme : overlayTheme;
  if (layer === "bg") {
    return `/foxess_plant_panel/flow_home_bg_scene_${theme}.png?v=${FLOW_SCENE_ASSET_VER}`;
  }
  return `/foxess_plant_panel/flow_${layer}_scene_${theme}.png?v=${FLOW_SCENE_ASSET_VER}`;
}

function inferBatteryFlowDirection(flows, threshold = FLOW_SCENE_PV_THRESHOLD_W) {
  const st = String(flows.batteryStatus || "").toLowerCase();
  if (st.includes("discharg")) {
    return { discharging: true, charging: false };
  }
  if (st.includes("charg")) {
    return { discharging: false, charging: true };
  }
  const w = flows.batteryW;
  return {
    discharging: w > threshold,
    charging: w < -threshold,
  };
}

function computeFlowLines(flows, threshold = FLOW_SCENE_PV_THRESHOLD_W) {
  const lines = [];
  const hasPv = flows.pvW > threshold;
  const hasGridIn = flows.gridImportW > threshold;
  const hasGridOut = flows.gridExportW > threshold;
  const { discharging, charging } = inferBatteryFlowDirection(flows, threshold);
  const hasLoad = flows.loadW > threshold;

  const aioToHub = hasPv || discharging || hasGridOut;
  if (hasPv) {
    lines.push({ id: "solar-aio" });
  }
  if (hasGridIn) lines.push({ id: "grid-hub" });
  if (hasGridOut) lines.push({ id: "hub-grid" });
  if (aioToHub) lines.push({ id: "aio-hub" });
  else if (charging) lines.push({ id: "hub-aio", reverse: true });
  if (hasLoad && (hasGridOut || hasGridIn || aioToHub || charging || hasPv)) {
    lines.push({ id: "hub-home" });
  }
  return lines;
}

async function fetchPlantState(hass, plantId) {
  return hass.connection.sendMessagePromise({
    type: "foxess_plant/plant_state",
    plant_id: plantId,
  });
}

async function fetchTriggerCandidates(hass) {
  return hass.connection.sendMessagePromise({
    type: "foxess_plant/trigger_candidates",
  });
}

const DEFAULT_BRAND_DOMAIN = "foxess_plant";
const DEFAULT_MODBUS_BRAND_DOMAIN = "foxess_modbus";
const DEFAULT_BRAND_ICON_STATIC = "/foxess_plant_panel/icon.png";
const DEVICE_EVO_IMAGE_STATIC = "/foxess_plant_panel/evo10.png?v=14";
const STORM_HERO_IMAGE_STATIC = "/foxess_plant_panel/bg_storm_safe_charging.png?v=1";
const IMPACT_ICON_ASSET_VER = 1;
const IMPACT_ICON_PATHS = {
  co2: "/foxess_plant_panel/impact_environment_co2.png",
  tree: "/foxess_plant_panel/impact_environment_planted.png",
  oil: "/foxess_plant_panel/impact_environment_oil.png",
};

function impactIconUrl(icon) {
  const path = IMPACT_ICON_PATHS[icon];
  return path ? `${path}?v=${IMPACT_ICON_ASSET_VER}` : "";
}
const DEVICE_PV_GAUGE_MAX_KW = 5;

let _brandsAccessToken;

async function ensureBrandsAccessToken(hass) {
  if (_brandsAccessToken || !hass?.connection) return _brandsAccessToken;
  try {
    const res = await hass.connection.sendMessagePromise({ type: "brands/access_token" });
    _brandsAccessToken = res?.token;
  } catch {
    /* brands API optional on older HA */
  }
  return _brandsAccessToken;
}

function buildBrandIconUrl(domain) {
  const base = `/api/brands/integration/${domain}/icon.png`;
  const url = new URL(base, location.origin);
  if (_brandsAccessToken) url.searchParams.set("token", _brandsAccessToken);
  return url.toString();
}

async function callService(hass, domain, service, data) {
  await hass.callService(domain, service, data, undefined, { blocking: true });
}

const SOC_MIN_PCT = 10;

const SOC_THUMBS = [
  { key: "min_soc", label: "Off-grid min", short: "Off-grid", color: "#e53935" },
  { key: "min_soc_on_grid", label: "System min", short: "On-grid", color: "#f9a825" },
  { key: "max_soc", label: "System max", short: "Max", color: "#2e7d32" },
];

/** Enforce 10–100%, min ≤ system min ≤ max (inverter rejects below 10%). */
function clampSocDraft(d) {
  let min = Math.round(Number(d.min_soc) || SOC_MIN_PCT);
  let mid = Math.round(Number(d.min_soc_on_grid) || SOC_MIN_PCT);
  let max = Math.round(Number(d.max_soc) || 100);
  min = Math.max(SOC_MIN_PCT, Math.min(100, min));
  mid = Math.max(SOC_MIN_PCT, Math.min(100, mid));
  max = Math.max(SOC_MIN_PCT, Math.min(100, max));
  if (mid < min) mid = min;
  if (max < mid) max = mid;
  d.min_soc = min;
  d.min_soc_on_grid = mid;
  d.max_soc = max;
  return d;
}

/** Apply drag to the active thumb first, then push siblings (Fox-app style). */
function applySocDrag(d, thumb, pct) {
  const p = Math.max(SOC_MIN_PCT, Math.min(100, Math.round(pct)));
  if (thumb === "min_soc") {
    d.min_soc = p;
    if (d.min_soc_on_grid < p) d.min_soc_on_grid = p;
    if (d.max_soc < d.min_soc_on_grid) d.max_soc = d.min_soc_on_grid;
  } else if (thumb === "min_soc_on_grid") {
    d.min_soc_on_grid = p;
    if (d.min_soc > p) d.min_soc = p;
    if (d.max_soc < p) d.max_soc = p;
  } else if (thumb === "max_soc") {
    d.max_soc = p;
    if (d.min_soc_on_grid > p) d.min_soc_on_grid = p;
    if (d.min_soc > d.min_soc_on_grid) d.min_soc = d.min_soc_on_grid;
  }
  return clampSocDraft(d);
}

const STYLES = `
:host {
  display: block;
  height: 100%;
  font-family: var(--ha-font-family, Roboto, sans-serif);
  background: var(--primary-background-color);
  color: var(--primary-text-color);
  --fp-radius: 14px;
  --fp-accent: var(--primary-color, #03a9f4);
  --fp-green: #2e7d32;
  --fp-amber: #f9a825;
  --fp-red: #e53935;
  --fp-flow-pipe: ${FLOW_PIPE_STROKE};
  --fp-flow-active-solar: ${FLOW_ACTIVE_STROKE.solar};
  --fp-flow-active-grid: ${FLOW_ACTIVE_STROKE.grid};
  --fp-flow-active-export: ${FLOW_ACTIVE_STROKE.export};
  --fp-flow-active-battery: ${FLOW_ACTIVE_STROKE.battery};
  --fp-flow-active-home: ${FLOW_ACTIVE_STROKE.home};
  --fp-flow-active-hub: ${FLOW_ACTIVE_STROKE.hub};
}
.shell {
  display: flex; flex-direction: column; height: 100%;
  min-height: calc(100vh - 56px);
  background: var(--primary-background-color);
}
.page-header {
  flex-shrink: 0;
  position: relative; z-index: 2;
  border-bottom: 1px solid var(--divider-color);
  background: var(--app-header-background-color, var(--primary-background-color));
}
.panel-brand-row {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px 4px;
}
.panel-brand-icon {
  width: 40px; height: 40px; flex-shrink: 0;
  object-fit: contain; border-radius: 8px;
}
.panel-brand-title {
  font-size: 18px; font-weight: 600; line-height: 1.2;
  color: var(--primary-text-color);
}
.panel-brand-sub {
  font-size: 12px; color: var(--secondary-text-color); margin-top: 2px;
}
.plant-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 8px 0;
}
.plant-row label {
  font-size: 12px; color: var(--secondary-text-color);
  font-weight: 500;
  white-space: nowrap;
}
.plant-row select {
  font-family: inherit;
  font-size: 13px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--divider-color);
  background: var(--card-background-color);
  color: var(--primary-text-color);
  width: 180px;
}
.tab-bar {
  display: flex; align-items: stretch; gap: 0;
  padding: 0 8px; overflow-x: auto; -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.tab-bar::-webkit-scrollbar { display: none; }
.tab {
  flex-shrink: 0;
  padding: 14px 20px 12px;
  border: none; border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--secondary-text-color);
  font-size: 14px; font-weight: 500; font-family: inherit;
  cursor: pointer; white-space: nowrap;
  position: relative; z-index: 1;
}
.tab:hover { color: var(--primary-text-color); }
.tab.active {
  color: var(--primary-text-color);
  font-weight: 600;
  border-bottom-color: var(--primary-text-color);
}
.tab-bar.sub { padding: 0 16px; border-top: 1px solid var(--divider-color); background: var(--secondary-background-color, transparent); }
.tab-bar.sub .tab { padding: 10px 16px 8px; font-size: 13px; }
.main {
  flex: 1; overflow-y: auto;
  padding: 20px 24px 40px;
  max-width: 1100px; width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
  container-type: inline-size;
  container-name: fp-main;
}
.shell.narrow .main { padding: 16px; }
.shell.narrow .tab { padding: 12px 14px 10px; font-size: 13px; }
.header { margin-bottom: 20px; }
.header h1 { margin: 0; font-size: 26px; font-weight: 600; letter-spacing: -0.02em; }
.header p { margin: 6px 0 0; color: var(--secondary-text-color); font-size: 14px; }
.overview-header { margin-bottom: 16px; }
.overview-model { margin: 4px 0 0; font-size: 15px; font-weight: 500; color: var(--secondary-text-color); letter-spacing: 0.01em; }
.overview-status-block { margin-top: 12px; }
.overview-status-row {
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; line-height: 1.35;
}
.overview-fox-status {
  font-size: 17px; font-weight: 700; letter-spacing: -0.01em; color: var(--primary-text-color);
}
.overview-fox-status.is-normal { color: #4caf50; }
.overview-fox-status.is-fault { color: var(--fp-red, #e53935); }
.overview-fox-status.is-checking { color: var(--secondary-text-color); }
.overview-fox-status.is-offgrid { color: var(--fp-amber, #ffb300); }
.overview-work-mode {
  margin: 0; font-size: 15px; font-weight: 600; color: var(--primary-text-color);
}
.overview-status-row .mode-pill { flex-shrink: 0; }
.overview-control-hint { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
.mode-banner-row {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 14px;
}
.mode-banner-hint { font-size: 13px; color: var(--secondary-text-color); }
.back-btn { background: none; border: none; color: var(--fp-accent); cursor: pointer; font-size: 14px; padding: 0 0 14px; font-family: inherit; }
.card {
  background: var(--card-background-color); border-radius: var(--fp-radius);
  padding: 18px 20px; margin-bottom: 14px;
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.08));
  border: 1px solid var(--divider-color, transparent);
}
.card-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--secondary-text-color); margin: 0 0 14px; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); gap: 12px; }
.overview-hero-row { display: flex; flex-direction: column; gap: 14px; margin-bottom: 14px; }
.overview-hero-scene { width: 100%; max-width: 440px; margin: 0 auto; }
.overview-hero-scene .scene-card--fox-flow { margin-bottom: 0; }
.overview-hero-stats {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px;
}
.breakdown-card { margin-top: 14px; padding-bottom: 8px; }
.statistics-card { padding-bottom: 16px; }
.statistics-card .card-title { margin-bottom: 12px; }
.fox-energy-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  align-items: stretch;
}
.fox-energy-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 18px;
  align-items: center;
  padding: 4px 14px 6px 0;
  min-width: 0;
}
.fox-energy-row + .fox-energy-row {
  border-left: 1px solid var(--divider-color, rgba(127,127,127,0.25));
  padding-left: 14px;
  padding-right: 0;
}
.fox-energy-copy { min-width: 0; }
.fox-energy-heading { font-size: 14px; color: var(--secondary-text-color); margin: 0 0 4px; font-weight: 500; }
.fox-energy-total { font-size: 24px; font-weight: 700; margin: 0 0 12px; line-height: 1.05; letter-spacing: -0.02em; }
.fox-energy-total span { font-size: 14px; font-weight: 500; color: var(--secondary-text-color); margin-left: 4px; }
.fox-energy-metric { margin-bottom: 10px; }
.fox-energy-metric:last-child { margin-bottom: 0; }
.fox-energy-metric-label { font-size: 12px; color: var(--secondary-text-color); margin-bottom: 2px; line-height: 1.25; }
.fox-energy-metric-value { font-size: 20px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em; }
.fox-energy-metric-unit { font-size: 13px; font-weight: 500; color: var(--secondary-text-color); margin-left: 2px; }
.fox-energy-chart {
  position: relative; flex-shrink: 0; width: 116px; height: 116px;
  margin-left: auto; align-self: center;
}
.fox-energy-chart svg {
  width: 116px; height: 116px; max-width: 100%; max-height: 100%;
  display: block; aspect-ratio: 1;
}
.fox-energy-chart-center {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  width: 72px; display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; pointer-events: none; gap: 5px;
}
.fox-energy-chart-pct { font-size: 22px; font-weight: 700; line-height: 1.1; letter-spacing: -0.03em; }
.fox-energy-chart-label {
  font-size: 10px; font-weight: 500; color: var(--secondary-text-color);
  line-height: 1.3; margin: 0; max-width: 72px;
}
.energy-period-tabs { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.energy-period-tabs button {
  flex: 1; min-width: 72px; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--divider-color);
  background: var(--card-background-color); color: var(--secondary-text-color); font-family: inherit;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.energy-period-tabs button.active {
  border-color: var(--fp-accent); color: var(--fp-accent);
  background: color-mix(in srgb, var(--fp-accent) 12%, var(--card-background-color));
}
.energy-chart-card { margin-top: 14px; }
.energy-chart-card .card-title { margin-bottom: 10px; }
.chart-wrap { position: relative; width: 100%; }
.energy-bar-chart { width: 100%; height: 220px; display: block; }
.statistics-chart-wrap {
  position: relative; width: 100%; font-family: "Segoe UI", Arial, sans-serif;
}
.statistics-chart-legend {
  display: flex; flex-wrap: wrap; gap: 8px 12px; margin-bottom: 10px;
}
.statistics-legend-item {
  display: inline-flex; align-items: center; gap: 6px; padding: 0; border: none;
  background: transparent; color: var(--primary-text-color); font: inherit;
  font-size: 11px; cursor: pointer; opacity: 1;
}
.statistics-legend-item.off { opacity: 0.35; }
.statistics-legend-item i {
  width: 10px; height: 10px; border-radius: 2px; display: inline-block; flex-shrink: 0;
}
.statistics-chart-plot { position: relative; width: 100%; margin: 0; }
.statistics-chart-svg {
  width: 100%; height: 440px; display: block;
}
.statistics-y-label {
  fill: var(--secondary-text-color); font-size: 12px; font-weight: 600; text-anchor: middle;
}
.statistics-y-axis { stroke: rgba(127,127,127,0.35); stroke-width: 1; }
.statistics-axis-x, .statistics-axis-y {
  fill: var(--secondary-text-color); font-size: 12px;
  font-variant-numeric: tabular-nums; text-rendering: geometricPrecision;
}
.statistics-grid { stroke: rgba(127,127,127,0.12); stroke-width: 1; }
.statistics-zero-line { stroke: rgba(127,127,127,0.20); stroke-width: 1; }
.statistics-hit { cursor: crosshair; }
.statistics-crosshair {
  position: absolute; top: 0; bottom: 40px; width: 1px; pointer-events: none;
  transform: translateX(-0.5px);
}
.statistics-spike {
  width: 1px; height: 100%; background: rgba(127,127,127,0.35);
}
.statistics-tooltip {
  position: absolute; z-index: 4; min-width: 180px; max-width: 260px;
  padding: 10px 12px; border-radius: 8px; pointer-events: none;
  background: var(--card-background-color, #1c1c1c);
  border: 1px solid rgba(127,127,127,0.35);
  box-shadow: 0 4px 16px rgba(0,0,0,0.28);
  font-size: 13px; color: var(--primary-text-color);
}
.statistics-tooltip-time {
  font-size: 12px; color: var(--secondary-text-color); margin-bottom: 8px;
}
.statistics-tooltip-row {
  display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 6px;
}
.statistics-tooltip-row:last-child { margin-bottom: 0; }
.statistics-tooltip-label {
  display: inline-flex; align-items: center; gap: 8px; min-width: 0; flex: 1;
}
.statistics-tooltip-swatch {
  width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; display: inline-block;
}
.statistics-tooltip-row strong { font-weight: 600; white-space: nowrap; flex-shrink: 0; }
.charts-entity-select {
  width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px;
  border: 1px solid var(--divider-color); background: var(--card-background-color);
  color: inherit; font-family: inherit; font-size: 14px; margin-bottom: 10px;
}
.charts-entity-hint { font-size: 12px; color: var(--secondary-text-color); line-height: 1.45; margin: 0 0 12px; }
.chart-grid { stroke: rgba(127,127,127,0.15); stroke-width: 1; }
.chart-axis { fill: var(--secondary-text-color); font-size: 9px; font-family: inherit; }
.chart-legend {
  display: flex; flex-wrap: wrap; gap: 10px 14px; margin-top: 10px; font-size: 12px; color: var(--secondary-text-color);
}
.chart-legend-item { display: inline-flex; align-items: center; gap: 6px; }
.chart-legend-item i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.chart-empty { margin: 24px 0; text-align: center; }
.chart-loading { margin: 24px 0; text-align: center; color: var(--secondary-text-color); font-size: 13px; }
.impact-card .card-title { margin-bottom: 12px; }
.impact-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px;
}
.impact-metric {
  text-align: center; padding: 14px 8px 10px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--fp-accent, #19d4de) 6%, var(--card-background-color));
  border: 1px solid var(--divider-color, rgba(127,127,127,0.2));
}
.impact-icon {
  display: block; height: 36px; width: auto; max-width: 56px;
  margin: 0 auto 10px; object-fit: contain;
}
.impact-value {
  font-size: 22px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
  color: var(--primary-text-color);
}
.impact-unit {
  font-size: 13px; font-weight: 500; color: var(--secondary-text-color); margin-left: 3px;
}
.impact-label {
  margin-top: 6px; font-size: 11px; line-height: 1.3; color: var(--secondary-text-color);
}
.impact-basis {
  margin: 12px 0 0; font-size: 11px; color: var(--secondary-text-color); text-align: center;
}
.impact-placeholder { font-size: 13px; line-height: 1.45; margin: 0; }
.impact-placeholder code { font-size: 12px; }
@media (max-width: 560px) {
  .impact-grid { grid-template-columns: 1fr; }
  .fox-energy-panel { grid-template-columns: 1fr; }
  .fox-energy-row {
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 14px 0 6px;
  }
  .fox-energy-chart { width: 128px; height: 128px; }
  .fox-energy-chart svg { width: 128px; height: 128px; }
  .fox-energy-chart-center { width: 78px; }
  .fox-energy-chart-pct { font-size: 24px; }
  .fox-energy-chart-label { font-size: 11px; max-width: 78px; }
  .fox-energy-row + .fox-energy-row {
    border-left: none;
    border-top: 1px solid var(--divider-color, rgba(127,127,127,0.25));
    padding-left: 0;
    padding-top: 16px;
    margin-top: 4px;
  }
}
.stat { background: var(--card-background-color); border-radius: var(--fp-radius); padding: 16px; border: 1px solid var(--divider-color, transparent); box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06)); }
.stat label { font-size: 12px; color: var(--secondary-text-color); display: block; }
.stat strong { font-size: 22px; display: block; margin-top: 6px; font-weight: 600; }
.mode-pill {
  display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px;
  border-radius: 999px; font-size: 12px; font-weight: 600; text-transform: capitalize;
  background: color-mix(in srgb, var(--fp-green) 20%, transparent); color: var(--fp-green);
}
.mode-pill.mode-storm { background: color-mix(in srgb, var(--fp-amber) 22%, transparent); color: var(--fp-amber); }
.mode-pill.mode-override { background: color-mix(in srgb, #7e57c2 22%, transparent); color: #7e57c2; }
.mode-pill.mode-manual { background: var(--secondary-background-color); color: var(--secondary-text-color); }
.mode-pill.mode-outage { background: color-mix(in srgb, var(--fp-red) 18%, transparent); color: var(--fp-red); }
.banner { display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px; border-radius: var(--fp-radius); margin-bottom: 14px; font-size: 13px; line-height: 1.45; }
.banner.warn { background: color-mix(in srgb, var(--fp-amber) 14%, var(--card-background-color)); border: 1px solid color-mix(in srgb, var(--fp-amber) 40%, transparent); }
.banner.info { background: color-mix(in srgb, var(--fp-accent) 12%, var(--card-background-color)); border: 1px solid color-mix(in srgb, var(--fp-accent) 35%, transparent); }
.banner strong { display: block; margin-bottom: 2px; }
.btn-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
.btn {
  padding: 10px 18px; border-radius: 10px; border: none; font-size: 14px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--fp-accent); color: var(--text-primary-color, #fff); }
.btn-secondary { background: var(--secondary-background-color); color: var(--primary-text-color); }
.btn-danger { background: color-mix(in srgb, var(--fp-red) 85%, #000); color: #fff; }
.list-btn {
  display: flex; justify-content: space-between; align-items: center; width: 100%;
  padding: 16px 18px; border: none; border-radius: var(--fp-radius);
  background: var(--card-background-color); color: inherit;
  cursor: pointer; text-align: left; font-family: inherit; margin-bottom: 10px;
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06));
  border: 1px solid var(--divider-color, transparent); gap: 12px;
}
.list-btn:hover { background: var(--secondary-background-color); }
.list-btn-body { display: flex; flex-direction: column; align-items: flex-start; gap: 5px; flex: 1; min-width: 0; }
.list-btn-title { display: block; font-size: 15px; font-weight: 600; line-height: 1.3; color: var(--primary-text-color); }
.list-btn-sub { display: block; font-size: 13px; font-weight: 400; line-height: 1.35; color: var(--secondary-text-color); }
.list-btn .chev { opacity: 0.45; font-size: 20px; flex-shrink: 0; line-height: 1; }
.list-btn .sub { font-size: 13px; color: var(--secondary-text-color); }
.placeholder { padding: 28px; text-align: center; color: var(--secondary-text-color); background: var(--card-background-color); border-radius: var(--fp-radius); border: 1px dashed var(--divider-color); }
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  padding: 12px 20px; border-radius: 10px; font-size: 14px; font-weight: 500;
  z-index: 100; box-shadow: 0 4px 16px rgba(0,0,0,0.25); max-width: 90%;
}
.toast.ok { background: var(--fp-green); color: #fff; }
.toast.err { background: var(--fp-red); color: #fff; }
.scene-card { background: var(--card-background-color); border-radius: var(--fp-radius); padding: 16px 12px 12px; border: 1px solid var(--divider-color, transparent); margin-bottom: 14px; }
.scene-title { font-size: 12px; font-weight: 700; color: var(--secondary-text-color); margin: 0 0 8px 4px; text-transform: uppercase; letter-spacing: 0.04em; }
.scene-card--fox-flow {
  padding: 0; border: none; border-radius: 0; background: transparent;
  width: 100%; margin: 0 0 14px; overflow: hidden;
}
.fox-flow-scene {
  display: block; width: 100%; max-width: 440px; margin: 0 auto; background: transparent;
}
.fox-flow-stage {
  position: relative; width: 100%; max-width: 440px; margin: 0 auto;
  background: #000;
}
.fox-flow-stage::before {
  content: ""; display: block; width: 100%; padding-top: 99.31640625%;
}
.fox-flow-layer {
  position: absolute; pointer-events: none; user-select: none;
}
.fox-flow-layer-bg {
  inset: 0; width: 100%; height: 100%; z-index: 0;
  object-fit: contain; object-position: center bottom;
  image-rendering: auto;
}
.fox-flow-layer-pv,
.fox-flow-layer-aio {
  inset: 0; width: 100%; height: 100%;
  object-fit: contain; object-position: center bottom;
  z-index: 1;
}
.fox-flow-svg {
  position: absolute; inset: 0; width: 100%; height: 100%;
  z-index: 3; pointer-events: none;
}
.fox-flow-badge {
  position: absolute; z-index: 4;
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 0; background: transparent; backdrop-filter: none;
  pointer-events: none; text-align: center;
}
.fox-flow-badge-label {
  font-size: 10px; font-weight: 600; color: rgba(255, 255, 255, 0.62);
  text-transform: uppercase; letter-spacing: 0.06em; line-height: 1.2;
}
.fox-flow-badge-value {
  font-size: 12px; font-weight: 600; color: #fff; line-height: 1.25;
  letter-spacing: -0.01em;
}
.fox-flow-badge-solar { left: 50%; top: 1%; transform: translateX(-50%); }
.fox-flow-badge-grid { left: 4%; bottom: 6%; align-items: flex-start; }
.fox-flow-badge-battery { left: 50%; bottom: 6%; transform: translateX(-50%); }
.fox-flow-badge-home { right: 4%; bottom: 6%; align-items: flex-end; }
.flow-path { fill: none; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; stroke: var(--fp-flow-pipe); opacity: 0.92; }
.flow-path-base { pointer-events: none; }
.flow-path.active {
  stroke-width: 7; stroke-dasharray: 18 22; animation: flow 1.1s linear infinite; opacity: 1;
  stroke-linecap: butt; paint-order: stroke; filter: drop-shadow(0 0 3px rgba(255, 255, 255, 0.55));
}
.flow-path.reverse { animation-direction: reverse; }
.flow-solar.active { stroke: var(--fp-flow-active-solar); filter: drop-shadow(0 0 5px rgba(245, 188, 0, 0.75)); }
.flow-grid.active { stroke: var(--fp-flow-active-grid); filter: drop-shadow(0 0 5px rgba(74, 154, 255, 0.75)); }
.flow-export.active { stroke: var(--fp-flow-active-export); filter: drop-shadow(0 0 5px rgba(181, 101, 255, 0.75)); }
.flow-battery.active {
  stroke: var(--fp-flow-active-battery);
  filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.65)) drop-shadow(0 0 8px rgba(77, 220, 114, 0.9));
}
.flow-home-line.active {
  stroke: var(--fp-flow-active-home);
  filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.65)) drop-shadow(0 0 8px rgba(77, 220, 114, 0.9));
}
.flow-hub-dot { fill: var(--fp-flow-pipe); opacity: 0.92; }
.flow-hub-dot.active { fill: var(--fp-flow-active-hub); filter: drop-shadow(0 0 6px rgba(77, 220, 114, 0.95)); }
@keyframes flow { to { stroke-dashoffset: -80; } }
.device-header { margin-bottom: 8px; }
.device-header h1 { margin-bottom: 4px; }
.device-model { margin: 0; font-size: 14px; color: var(--secondary-text-color); }
.device-fox-pill {
  display: inline-block; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 999px;
  margin-bottom: 12px; background: rgba(76, 175, 80, 0.15); color: #4caf50;
}
.device-fox-pill.is-fault { background: rgba(229, 57, 53, 0.15); color: var(--fp-red, #e53935); }
.device-fox-pill.is-checking { background: var(--secondary-background-color); color: var(--secondary-text-color); }
.device-fox-pill.is-offgrid { background: rgba(255, 179, 0, 0.15); color: var(--fp-amber, #ffb300); }
.device-hero {
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  margin: 4px 0 24px; padding: 0 16px; width: 100%; box-sizing: border-box;
}
.device-hero-img {
  max-width: min(200px, 62vw); max-height: 260px; width: auto; height: auto;
  display: block; object-fit: contain;
}
.device-serial-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 8px 12px; border: none; background: transparent;
  color: var(--secondary-text-color); font: inherit; font-size: 13px;
  cursor: pointer; border-radius: 8px; width: 100%; max-width: 360px;
}
.device-serial-btn:hover { background: var(--secondary-background-color, rgba(127,127,127,0.12)); color: var(--primary-text-color); }
.device-serial { font-family: ui-monospace, monospace; letter-spacing: 0.03em; }
.device-serial-muted { margin: 0; font-size: 13px; color: var(--secondary-text-color); text-align: center; }
.device-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;
  margin-bottom: 16px; align-items: stretch;
}
.device-card {
  background: var(--card-background-color); border-radius: 14px; padding: 18px 16px 20px;
  border: 1px solid var(--divider-color, rgba(127,127,127,0.28));
  min-height: 0; display: flex; flex-direction: column; box-sizing: border-box;
}
.device-card--gauge { align-items: center; justify-content: flex-start; }
.device-card--battery { align-items: stretch; justify-content: flex-start; }
.device-pv-wrap { width: 100%; display: flex; flex-direction: column; align-items: center; gap: 10px; }
.device-pv-gauge { width: 100%; max-width: 140px; aspect-ratio: 100 / 104; flex-shrink: 0; }
.device-pv-gauge svg { width: 100%; height: 100%; display: block; }
.device-pv-readout { text-align: center; width: 100%; }
.device-pv-value { font-size: 22px; font-weight: 700; line-height: 1.25; letter-spacing: -0.02em; margin: 0; }
.device-pv-label { font-size: 13px; color: var(--secondary-text-color); font-weight: 500; line-height: 1.4; margin: 8px 0 0; }
.device-battery-card { width: 100%; box-sizing: border-box; display: flex; flex-direction: column; gap: 0; }
.device-battery-top {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center;
  column-gap: 12px; width: 100%; padding-bottom: 14px;
}
.device-battery-status-row { display: flex; align-items: center; gap: 10px; min-width: 0; }
.device-battery-svg { width: 44px; height: 22px; flex-shrink: 0; }
.device-battery-shell { fill: none; stroke: var(--secondary-text-color); stroke-width: 1.5; }
.device-battery-cap { fill: var(--secondary-text-color); }
.device-battery-fill { fill: #4caf50; }
.device-battery-card.is-discharging .device-battery-fill { fill: var(--fp-accent); }
.device-battery-card.is-charging .device-battery-fill { fill: #4caf50; }
.device-battery-status { font-size: 14px; font-weight: 600; line-height: 1.35; }
.device-battery-pct { font-size: 28px; font-weight: 700; line-height: 1.1; letter-spacing: -0.03em; text-align: right; }
.device-battery-metrics {
  display: flex; flex-direction: row; justify-content: space-between; align-items: flex-start;
  width: 100%; padding-top: 14px; border-top: 1px solid var(--divider-color, rgba(127,127,127,0.35));
}
.device-battery-metric { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 0 1 auto; }
.device-battery-metric--power { align-items: flex-start; text-align: left; }
.device-battery-metric--temp { align-items: flex-end; text-align: right; margin-left: auto; }
.device-battery-metric-label { font-size: 13px; color: var(--secondary-text-color); font-weight: 500; line-height: 1.3; margin: 0; }
.device-battery-metric-value { font-size: 17px; font-weight: 700; line-height: 1.25; letter-spacing: -0.02em; margin: 0; white-space: nowrap; }
.entity-list { border-radius: var(--fp-radius); overflow: hidden; border: 1px solid var(--divider-color, transparent); }
.entity-row { display: flex; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid var(--divider-color); font-size: 14px; }
.entity-row:last-child { border-bottom: none; }
.entity-name { color: var(--secondary-text-color); }
.entity-value { font-weight: 500; }
.period-card { border: 1px solid var(--divider-color); border-radius: var(--fp-radius); padding: 16px; margin-bottom: 12px; background: var(--secondary-background-color, rgba(127,127,127,0.06)); }
.period-card h4 { margin: 0 0 12px; font-size: 15px; }
.field { margin-bottom: 12px; }
.field label { display: block; font-size: 12px; color: var(--secondary-text-color); margin-bottom: 6px; }
.field input[type="time"] {
  width: 9rem; max-width: 100%; box-sizing: border-box;
  padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; font-family: inherit;
}
.field select {
  width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; font-family: inherit;
}
.period-times { display: flex; flex-wrap: wrap; gap: 20px 24px; margin-bottom: 4px; }
.period-times .field { margin-bottom: 0; }
.toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; font-size: 14px; }
.toggle-row input { width: 18px; height: 18px; accent-color: var(--fp-accent); }
.triple-soc { padding: 8px 4px 4px; user-select: none; touch-action: none; }
.triple-soc-head { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.triple-soc-battery {
  width: 52px; height: 88px; flex-shrink: 0; border-radius: 10px;
  border: 2px solid var(--divider-color); position: relative; overflow: hidden;
  background: var(--secondary-background-color);
}
.triple-soc-battery-fill {
  position: absolute; left: 4px; right: 4px; bottom: 4px; border-radius: 6px;
  background: linear-gradient(180deg, #66bb6a 0%, #2e7d32 100%);
  transition: height 0.35s ease;
}
.triple-soc-battery-cap {
  position: absolute; top: -8px; left: 50%; transform: translateX(-50%);
  width: 22px; height: 8px; border-radius: 4px 4px 0 0;
  background: var(--divider-color);
}
.triple-soc-battery-pct {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 700; z-index: 1; text-shadow: 0 1px 2px rgba(0,0,0,0.35);
}
.triple-soc-summary { flex: 1; font-size: 13px; color: var(--secondary-text-color); line-height: 1.5; }
.triple-soc-summary strong { color: var(--primary-text-color); font-weight: 600; }
.triple-soc-track-wrap { position: relative; padding: 16px 8px 8px; margin: 0 -4px; }
.triple-soc-track {
  position: relative; height: 14px; border-radius: 999px;
  background: var(--divider-color); overflow: visible;
}
.triple-soc-zones { position: absolute; inset: 0; border-radius: 999px; overflow: hidden; display: flex; }
.triple-soc-zone { height: 100%; }
.triple-soc-zone.critical { background: color-mix(in srgb, #e53935 55%, var(--divider-color)); }
.triple-soc-zone.reserve { background: color-mix(in srgb, #f9a825 50%, var(--divider-color)); }
.triple-soc-zone.usable { background: color-mix(in srgb, #2e7d32 55%, var(--divider-color)); }
.triple-soc-zone.headroom { background: color-mix(in srgb, var(--fp-accent) 35%, var(--divider-color)); }
.triple-soc-live {
  position: absolute; top: -6px; bottom: -6px; width: 3px; margin-left: -1px;
  background: var(--primary-text-color); border-radius: 2px; z-index: 2;
  box-shadow: 0 0 0 2px var(--card-background-color);
  pointer-events: none;
}
.triple-soc-live::after {
  content: "Now"; position: absolute; top: -20px; left: 50%; transform: translateX(-50%);
  font-size: 10px; font-weight: 600; white-space: nowrap; color: var(--primary-text-color);
}
.triple-soc-thumb {
  position: absolute; top: 50%; width: 26px; height: 26px; margin: -13px 0 0 -13px;
  border-radius: 50%; border: 3px solid #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.35);
  cursor: grab; padding: 0; transition: transform 0.1s;
}
.triple-soc-thumb[data-soc-thumb="min_soc"] { z-index: 3; }
.triple-soc-thumb[data-soc-thumb="min_soc_on_grid"] { z-index: 4; }
.triple-soc-thumb[data-soc-thumb="max_soc"] { z-index: 5; }
.triple-soc-thumb.is-dragging { z-index: 10; transform: scale(1.1); }
.triple-soc-thumb:active { cursor: grabbing; }
.triple-soc-scale { display: flex; justify-content: space-between; font-size: 11px; color: var(--secondary-text-color); margin-top: 10px; padding: 0 4px; }
.soc-legend { display: flex; flex-wrap: wrap; gap: 12px 16px; margin-top: 16px; font-size: 12px; color: var(--secondary-text-color); }
.soc-legend span { display: inline-flex; align-items: center; gap: 6px; }
.soc-legend i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.soc-numeric { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 18px; }
.soc-numeric label { font-size: 11px; color: var(--secondary-text-color); display: block; margin-bottom: 4px; }
.soc-numeric input {
  width: 100%; box-sizing: border-box; padding: 8px 10px; border-radius: 8px;
  border: 1px solid var(--divider-color); background: var(--card-background-color);
  color: var(--primary-text-color); font-size: 15px; font-weight: 600; text-align: center; font-family: inherit;
}
.soc-limit-note {
  margin-top: 14px; padding: 10px 12px; font-size: 12px; line-height: 1.45;
  color: var(--secondary-text-color);
  background: color-mix(in srgb, var(--fp-amber) 14%, var(--card-background-color));
  border-radius: 10px; border-left: 3px solid var(--fp-amber);
}
.soc-limit-note strong { color: var(--primary-text-color); font-weight: 600; }
.mode-grid { display: grid; gap: 8px; }
.mode-option {
  display: block; width: 100%; text-align: left; padding: 14px 16px;
  border-radius: 12px; border: 2px solid var(--divider-color); background: var(--card-background-color);
  cursor: pointer; font-family: inherit; color: inherit; transition: border-color 0.15s;
}
.mode-option.selected { border-color: var(--fp-accent); background: color-mix(in srgb, var(--fp-accent) 10%, var(--card-background-color)); }
.mode-option .name { font-weight: 600; font-size: 15px; }
.mode-option .hint { font-size: 12px; color: var(--secondary-text-color); margin-top: 4px; }
.hero { border-radius: var(--fp-radius); overflow: hidden; background: var(--card-background-color); margin-bottom: 14px; border: 1px solid var(--divider-color); }
.hero-caption { padding: 12px 16px; font-size: 13px; color: var(--secondary-text-color); line-height: 1.45; border-top: 1px solid var(--divider-color); }
.storm-hero {
  border: none; border-radius: 0; background: #0d1520;
  width: calc(100% + 48px); max-width: none;
  margin: -20px -24px 20px;
}
.shell.narrow .storm-hero { width: calc(100% + 32px); margin: -16px -16px 16px; }
.storm-hero-media {
  position: relative; width: 100%; overflow: hidden;
  aspect-ratio: 750 / 420; max-height: min(52vw, 280px); min-height: 140px;
  background: #0d1520;
}
.storm-hero-img {
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; object-position: center center; display: block;
}
.storm-hero-half {
  position: absolute; top: 0; bottom: 0; width: 50%;
  pointer-events: none; transition: background 0.35s ease;
}
.storm-hero-half--left { left: 0; }
.storm-hero-half--right { right: 0; }
.storm-hero:not(.armed) .storm-hero-half--left { background: rgba(0, 0, 0, 0.18); }
.storm-hero.armed .storm-hero-half--right { background: rgba(0, 0, 0, 0.42); }
.storm-hero.armed .storm-hero-half--left { background: rgba(76, 175, 80, 0.08); }
.storm-hero-title {
  position: absolute; left: 0; right: 0; top: 0; z-index: 2;
  margin: 0; padding: 18px 20px 0;
  text-align: center; box-sizing: border-box;
  font-size: clamp(20px, 5.5vw, 26px); font-weight: 700; line-height: 1.2;
  letter-spacing: -0.02em; color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85), 0 0 24px rgba(0, 0, 0, 0.55);
  pointer-events: none;
}
.shell.narrow .storm-hero-title { padding-top: 14px; font-size: 20px; }
.storm-settings-header { margin-top: 0; margin-bottom: 16px; }
.trigger-chip { display: inline-block; padding: 4px 10px; border-radius: 8px; font-size: 12px; background: var(--secondary-background-color); margin: 4px 4px 0 0; }
.trigger-chips-wrap { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 10px; min-height: 28px; }
.trigger-chip-selected { display: inline-flex; align-items: center; gap: 4px; padding-right: 8px; background: color-mix(in srgb, var(--fp-accent) 18%, var(--secondary-background-color)); }
.trigger-chip-selected button {
  border: none; background: transparent; color: var(--secondary-text-color);
  cursor: pointer; font-size: 16px; line-height: 1; padding: 0 4px; font-family: inherit;
}
.trigger-chip-selected button:hover { color: var(--fp-red); }
.trigger-filter { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: inherit; font-family: inherit; font-size: 14px; margin-bottom: 8px; }
.trigger-filter-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.trigger-filter-actions .btn { padding: 8px 12px; font-size: 13px; }
.trigger-list { max-height: 280px; overflow-y: auto; border: 1px solid var(--divider-color); border-radius: 10px; padding: 0 12px; background: var(--card-background-color); }
.trigger-row { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--divider-color); font-size: 13px; }
.trigger-row:last-child { border-bottom: none; }
.trigger-row.suggested { background: color-mix(in srgb, var(--fp-amber) 8%, transparent); margin: 0 -12px; padding-left: 12px; padding-right: 12px; }
.trigger-row label { flex: 1; cursor: pointer; line-height: 1.35; user-select: none; }
.trigger-row input[type="checkbox"] { margin-top: 3px; flex-shrink: 0; width: 18px; height: 18px; accent-color: var(--fp-accent); cursor: pointer; }
.trigger-row .entity-id { display: block; font-size: 11px; color: var(--secondary-text-color); margin-top: 2px; }
.trigger-row .entity-state { font-size: 11px; color: var(--fp-accent); margin-left: auto; white-space: nowrap; }
.trigger-section-title { font-size: 12px; font-weight: 600; color: var(--secondary-text-color); margin: 10px 0 6px; text-transform: uppercase; letter-spacing: 0.04em; }
.storm-hint { margin: 0 0 12px; font-size: 13px; line-height: 1.45; color: var(--secondary-text-color); }
.gw-card { border-left: 3px solid var(--fp-accent); }
.gw-card.gw-ready { border-left-color: var(--fp-green, #4caf50); }
.gw-card.gw-warn { border-left-color: var(--fp-amber); }
.gw-status { font-size: 13px; line-height: 1.45; margin: 0 0 10px; color: var(--secondary-text-color); }
.gw-status strong { color: inherit; }
.gw-select { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: inherit; font-family: inherit; font-size: 14px; margin-bottom: 10px; }
.gw-linked { font-size: 12px; color: var(--secondary-text-color); margin: 8px 0 0; line-height: 1.45; }
.gw-linked code { font-size: 11px; }
.storm-advanced summary { cursor: pointer; font-weight: 600; font-size: 13px; padding: 4px 0; color: var(--secondary-text-color); }
.storm-advanced[open] summary { margin-bottom: 10px; color: inherit; }
.storm-advanced { margin-top: 4px; }
.trigger-row.google-weather { background: color-mix(in srgb, var(--fp-accent) 10%, transparent); }
.trigger-role { display: inline-block; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; padding: 2px 6px; border-radius: 6px; margin-left: 6px; background: var(--secondary-background-color); color: var(--fp-accent); }
@container fp-main (min-width: 720px) {
  .overview-hero-row {
    flex-direction: row;
    align-items: flex-start;
    gap: 14px;
  }
  .overview-hero-scene {
    flex: 0 0 440px;
    width: 440px;
    max-width: 440px;
    margin: 0;
  }
  .overview-hero-stats {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    grid-template-columns: unset;
  }
}
@media (max-width: 720px) {
  .device-grid { grid-template-columns: 1fr; gap: 12px; }
  .device-card--gauge, .device-card--battery { padding: 20px 20px 22px; }
  .device-pv-gauge { max-width: 160px; }
  .device-pv-value { font-size: 24px; }
  .device-battery-pct { font-size: 32px; }
}
@media (max-width: 600px) {
  .fox-flow-badge-value { font-size: 13px; }
}
`;

class FoxessPlantPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._narrow = false;
    this._panel = undefined;
    this._route = undefined;
    this._view = "overview";
    this._settingsView = "main";
    this._deviceSub = "main";
    this._plantState = undefined;
    this._selectedPlantId = undefined;
    this._timer = undefined;
    this._busy = false;
    this._toastTimer = undefined;
    this._chargeDraft = null;
    this._socDraft = null;
    this._workModeDraft = null;
    this._stormDraft = null;
    this._triggerMeta = null;
    this._triggerCandidates = null;
    this._triggerFilter = "";
    this._triggerShowAll = false;
    this._triggerGoogleOnly = false;
    this._stormShowAdvanced = false;
    this._triggerFilterTimer = undefined;
    this._brandIconSrc = DEFAULT_BRAND_ICON_STATIC;
    this._brandIconFallback = DEFAULT_BRAND_ICON_STATIC;
    this._brandIconStatic = DEFAULT_BRAND_ICON_STATIC;
    this._socDrag = null;
    this._energyPeriod = "day";
    this._energyChart = null;
    this._energyChartLoading = false;
    this._energyChartPlantId = undefined;
    this._statisticsChart = null;
    this._statisticsChartLoading = false;
    this._statisticsChartPlantId = undefined;
    this._chartsDraft = null;
    this._forecastCandidates = null;
    this._headerHasSubTabs = undefined;
    this._renderRaf = 0;
    this._onSocMove = this._onSocMove.bind(this);
    this._onSocEnd = this._onSocEnd.bind(this);
    const root = document.createElement("div");
    root.className = "root";
    this.shadowRoot.append(
      Object.assign(document.createElement("style"), { textContent: STYLES }),
      root
    );
    this._root = root;
    this._onClick = this._handleClick.bind(this);
    this._onInput = this._handleInput.bind(this);
    this._onChange = this._handleChange.bind(this);
  }

  connectedCallback() {
    this._root.addEventListener("click", this._onClick);
    this._root.addEventListener("input", this._onInput);
    this._root.addEventListener("change", this._onChange);
    void this._initBrandIcons();
    void this._refreshPlantState();
    this._timer = window.setInterval(() => void this._refreshPlantState(), 30000);
    this._render();
  }

  disconnectedCallback() {
    this._root.removeEventListener("click", this._onClick);
    this._root.removeEventListener("input", this._onInput);
    this._root.removeEventListener("change", this._onChange);
    if (this._triggerFilterTimer) window.clearTimeout(this._triggerFilterTimer);
    this._endSocDrag();
    if (this._timer) window.clearInterval(this._timer);
    if (this._toastTimer) window.clearTimeout(this._toastTimer);
  }

  set hass(v) {
    this._hass = v;
    if (v) void this._initBrandIcons();
    if (!this._socDrag) this._scheduleRender();
  }
  get hass() {
    return this._hass;
  }
  set narrow(v) {
    this._narrow = Boolean(v);
    const shell = this._root.querySelector(".shell");
    if (shell) shell.classList.toggle("narrow", this._narrow);
  }
  get narrow() {
    return this._narrow;
  }
  set panel(v) {
    this._panel = v;
    const plants = v?.config?.plants ?? [];
    if (!this._selectedPlantId && plants.length) this._selectedPlantId = plants[0].entry_id;
    void this._refreshPlantState();
    this._render();
  }
  get panel() {
    return this._panel;
  }
  set route(v) {
    this._route = v;
  }
  get route() {
    return this._route;
  }

  _getPlant() {
    const plants = this._panel?.config?.plants ?? [];
    return plants.find((p) => p.entry_id === this._selectedPlantId) ?? plants[0];
  }

  _panelBuild() {
    return this._panel?.config?.panel_js_build || PANEL_BUILD_FALLBACK;
  }

  async _initBrandIcons() {
    const cfg = this._panel?.config ?? {};
    this._brandIconStatic = cfg.brand_icon_static || DEFAULT_BRAND_ICON_STATIC;
    const plantDomain = cfg.brand_domain || DEFAULT_BRAND_DOMAIN;
    const modbusDomain = cfg.modbus_brand_domain || DEFAULT_MODBUS_BRAND_DOMAIN;
    if (!this._hass) {
      this._brandIconSrc = this._brandIconStatic;
      this._brandIconFallback = this._brandIconStatic;
      return;
    }
    await ensureBrandsAccessToken(this._hass);
    this._brandIconSrc = buildBrandIconUrl(plantDomain);
    this._brandIconFallback = buildBrandIconUrl(modbusDomain);
    if (this.isConnected) this._scheduleRender();
  }

  _renderPanelBrand() {
    return `<div class="panel-brand-row">
<img class="panel-brand-icon" src="${esc(this._brandIconSrc)}" data-fallback="${esc(this._brandIconFallback)}" data-static="${esc(this._brandIconStatic)}" width="40" height="40" alt="FoxESS">
<div>
<div class="panel-brand-title">Fox Plant</div>
<div class="panel-brand-sub">FoxESS inverter control</div>
</div>
</div>`;
  }

  _bindPanelBrandIcon(headerEl) {
    const img = headerEl?.querySelector(".panel-brand-icon");
    if (!img || img.dataset.bound) return;
    img.dataset.bound = "1";
    img.addEventListener("error", () => {
      const fallback = img.dataset.fallback;
      const staticSrc = img.dataset.static;
      if (fallback && img.src !== fallback) {
        img.src = fallback;
      } else if (staticSrc) {
        img.src = staticSrc;
      }
    });
  }

  _showToast(msg, type = "ok") {
    const old = this.shadowRoot.querySelector(".toast");
    if (old) old.remove();
    if (this._toastTimer) window.clearTimeout(this._toastTimer);
    const el = document.createElement("div");
    el.className = `toast ${type === "err" ? "err" : "ok"}`;
    el.textContent = msg;
    this.shadowRoot.appendChild(el);
    this._toastTimer = window.setTimeout(() => el.remove(), 3500);
  }

  async _refreshPlantState() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    try {
      this._plantState = await fetchPlantState(this._hass, plant.entry_id);
      if (this._settingsView !== "schedules") this._chargeDraft = null;
      if (this._settingsView !== "quick") this._socDraft = null;
      if (this._settingsView !== "workmode") this._workModeDraft = null;
      if (this._settingsView !== "storm") this._stormDraft = null;
      if (!this._socDrag) this._scheduleRender();
    } catch {
      /* ws optional */
    }
  }

  _scheduleRender() {
    if (this._renderRaf) return;
    this._renderRaf = requestAnimationFrame(() => {
      this._renderRaf = 0;
      this._render();
    });
  }

  _syncTabActive(headerEl) {
    headerEl.querySelectorAll('[data-action="nav"]').forEach((btn) => {
      const on = btn.dataset.view === this._view;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
    headerEl.querySelectorAll('[data-action="settings-tab"]').forEach((btn) => {
      const on = btn.dataset.sub === this._settingsView;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
  }

  _renderPlantSelect() {
    const plants = this._panel?.config?.plants ?? [];
    if (plants.length <= 1) return "";
    const selectedId = this._selectedPlantId ?? plants[0]?.entry_id;
    return `<div class="plant-row"><label>Plant</label><select data-action="pick-plant" aria-label="Plant selector">${plants
      .map(
        (p) =>
          `<option value="${esc(p.entry_id)}" ${p.entry_id === selectedId ? "selected" : ""}>${esc(
            p.title
          )}</option>`
      )
      .join("")}</select></div>`;
  }

  _rebuildPageHeader(headerEl) {
    const showSubTabs = this._view === "settings";
    headerEl.innerHTML =
      this._renderPanelBrand() +
      this._renderPlantSelect() +
      this._renderTabBar(NAV, this._view, "nav", "view") +
      (showSubTabs
        ? this._renderTabBar(SETTINGS_NAV, this._settingsView, "settings-tab", "sub", true)
        : "");
    this._bindPanelBrandIcon(headerEl);
    this._headerHasSubTabs = showSubTabs;
  }

  _initChargeDraft() {
    const src =
      this._plantState?.baseline_periods ??
      this._plantState?.desired_periods ??
      DEFAULT_PERIODS;
    this._chargeDraft = JSON.parse(JSON.stringify(src)).slice(0, 2);
    while (this._chargeDraft.length < 2) {
      this._chargeDraft.push({ ...DEFAULT_PERIODS[0] });
    }
  }

  _initSocDraft() {
    const s = this._plantState?.settings ?? {};
    this._socDraft = clampSocDraft({
      min_soc: s.min_soc ?? 10,
      min_soc_on_grid: s.min_soc_on_grid ?? 20,
      max_soc: s.max_soc ?? 100,
    });
  }

  _initWorkModeDraft() {
    this._workModeDraft =
      this._plantState?.settings?.work_mode ??
      stateString(this._hass, this._getPlant()?.entity_map?.work_mode);
  }

  _initStormDraft() {
    const storm = this._plantState?.storm_prep ?? {};
    const periods = JSON.parse(JSON.stringify(storm.charge_periods ?? DEFAULT_PERIODS)).slice(0, 2);
    while (periods.length < 2) periods.push({ ...DEFAULT_PERIODS[0] });
    this._stormDraft = {
      enabled: Boolean(storm.enabled),
      alert_provider: storm.alert_provider || "google_weather",
      google_weather_entry_id: storm.google_weather_entry_id ?? null,
      use_weather_condition: storm.use_weather_condition !== false,
      use_forecast_lead: storm.use_forecast_lead !== false,
      forecast_lead_hours: storm.forecast_lead_hours ?? 4,
      condition_entity_id: storm.condition_entity_id ?? null,
      weather_entity_id: storm.weather_entity_id ?? null,
      trigger_entities: [...(storm.trigger_entities ?? [])],
      charge_periods: periods,
      target_max_soc: storm.target_max_soc ?? null,
    };
  }

  _getGoogleWeatherEntries() {
    return this._triggerMeta?.google_weather?.entries ?? [];
  }

  _getSelectedGoogleWeatherEntry() {
    const id = this._stormDraft?.google_weather_entry_id;
    if (!id) return null;
    return this._getGoogleWeatherEntries().find((e) => e.entry_id === id) ?? null;
  }

  _applyGoogleWeatherEntry(entryId) {
    if (!this._stormDraft) return;
    this._stormDraft.google_weather_entry_id = entryId || null;
    this._stormDraft.alert_provider = "google_weather";
    const entry = this._getGoogleWeatherEntries().find((e) => e.entry_id === entryId);
    if (!entryId || !entry) {
      this._stormDraft.trigger_entities = [];
      this._stormDraft.condition_entity_id = null;
      this._stormDraft.weather_entity_id = null;
      this._stormDraft.use_weather_condition = false;
      return;
    }
    this._stormDraft.condition_entity_id = entry.condition_entity_id ?? null;
    this._stormDraft.weather_entity_id = entry.weather_entity ?? null;
    this._stormDraft.use_weather_condition = Boolean(
      entry.condition_entity_id || entry.weather_entity
    );
    if (entry.alert_trigger_ids?.length) {
      this._stormDraft.trigger_entities = [...entry.alert_trigger_ids];
    } else {
      this._stormDraft.trigger_entities = [];
    }
  }

  _inferGoogleWeatherEntryId() {
    const entries = this._getGoogleWeatherEntries();
    const draft = this._stormDraft;
    if (!entries.length || !draft) return null;
    if (draft.condition_entity_id) {
      const match = entries.find((e) => e.condition_entity_id === draft.condition_entity_id);
      if (match) return match.entry_id;
    }
    if (draft.weather_entity_id) {
      const match = entries.find((e) => e.weather_entity === draft.weather_entity_id);
      if (match) return match.entry_id;
    }
    const triggers = draft.trigger_entities ?? [];
    if (triggers.length) {
      for (const entry of entries) {
        const ids = new Set(entry.alert_trigger_ids || []);
        if (triggers.every((t) => ids.has(t)) && ids.size) {
          return entry.entry_id;
        }
      }
    }
    if (entries.length === 1) return entries[0].entry_id;
    return draft.google_weather_entry_id ?? null;
  }

  _enterStormSettings() {
    this._initStormDraft();
    this._triggerFilter = "";
    this._triggerShowAll = false;
    this._triggerGoogleOnly = false;
    this._stormShowAdvanced = false;
    void this._loadTriggerCandidates();
  }

  _initChartsDraft() {
    const pd = this._plantState?.panel_display ?? {};
    this._chartsDraft = {
      forecast_entity_id: pd.forecast_entity_id ?? null,
    };
  }

  _enterChartsSettings() {
    this._initChartsDraft();
    void this._loadForecastCandidates();
  }

  async _loadForecastCandidates() {
    if (!this._hass) return;
    try {
      const res = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/forecast_entity_candidates",
      });
      this._forecastCandidates = res?.entities ?? [];
      if (this._settingsView === "charts" && this._chartsDraft && !this._chartsDraft.forecast_entity_id) {
        const suggested = this._forecastCandidates.find((e) => e.suggested);
        if (suggested) this._chartsDraft.forecast_entity_id = suggested.entity_id;
      }
      if (this._settingsView === "charts") this._scheduleRender();
    } catch {
      this._forecastCandidates = [];
    }
  }

  async _saveChartsSettings() {
    const plant = this._getPlant();
    if (!plant || !this._chartsDraft) return;
    this._busy = true;
    this._render();
    try {
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_panel_display",
        plant_id: plant.entry_id,
        forecast_entity_id: this._chartsDraft.forecast_entity_id || null,
      });
      if (state) this._plantState = state;
      this._statisticsChart = null;
      this._statisticsChartPlantId = undefined;
      this._energyChart = null;
      this._energyChartPlantId = undefined;
      await this._loadStatisticsChart();
      if (this._view === "energy" && this._energyPeriod === "day") await this._loadEnergyCharts();
      this._showToast("Chart settings saved");
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _loadTriggerCandidates() {
    if (!this._hass) return;
    try {
      this._triggerMeta = await fetchTriggerCandidates(this._hass);
      this._triggerCandidates = this._triggerMeta?.entities ?? [];
      if (this._settingsView === "storm" && this._stormDraft) {
        const inferred = this._inferGoogleWeatherEntryId();
        if (inferred && !this._stormDraft.google_weather_entry_id) {
          this._applyGoogleWeatherEntry(inferred);
        } else if (this._stormDraft.google_weather_entry_id) {
          this._applyGoogleWeatherEntry(this._stormDraft.google_weather_entry_id);
        }
        this._scheduleRender();
      }
    } catch {
      this._triggerMeta = null;
      this._triggerCandidates = [];
    }
  }

  async _saveStormPrep() {
    const plant = this._getPlant();
    if (!plant || !this._stormDraft) return;
    this._busy = true;
    this._render();
    try {
      const target = this._stormDraft.target_max_soc;
      const payload = {
        type: "foxess_plant/update_storm_prep",
        plant_id: plant.entry_id,
        enabled: this._stormDraft.enabled,
        trigger_entities: this._stormDraft.trigger_entities,
        charge_periods: this._stormDraft.charge_periods,
        target_max_soc: target == null || target === "" ? null : Number(target),
      };
      if (this._stormDraft.alert_provider) {
        payload.alert_provider = this._stormDraft.alert_provider;
      }
      if (this._stormDraft.google_weather_entry_id) {
        payload.google_weather_entry_id = this._stormDraft.google_weather_entry_id;
      }
      payload.use_forecast_lead = Boolean(this._stormDraft.use_forecast_lead);
      payload.forecast_lead_hours = Number(this._stormDraft.forecast_lead_hours) || 4;
      const state = await this._hass.connection.sendMessagePromise(payload);
      if (state) this._plantState = state;
      this._initStormDraft();
      this._showToast("StormSafe settings saved");
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _handleClick(e) {
    const btn = e.target.closest("[data-action]");
    if (!btn || this._busy) return;
    const action = btn.dataset.action;

    if (action === "nav") {
      this._view = btn.dataset.view;
      this._settingsView = "main";
      this._deviceSub = "main";
      if (this._view === "energy") this._loadEnergyCharts();
      if (this._view === "overview") this._loadStatisticsChart();
      this._render();
      return;
    }
    if (action === "energy-period") {
      const period = btn.dataset.period;
      if (!period || period === this._energyPeriod) return;
      this._energyPeriod = period;
      this._loadEnergyCharts();
      this._render();
      return;
    }
    if (action === "device-sub") {
      this._deviceSub = btn.dataset.sub;
      this._render();
      return;
    }
    if (action === "device-back") {
      this._deviceSub = "main";
      this._render();
      return;
    }
    if (action === "settings-sub") {
      this._view = "settings";
      this._settingsView = btn.dataset.sub;
      if (btn.dataset.sub === "schedules") this._initChargeDraft();
      if (btn.dataset.sub === "quick") this._initSocDraft();
      if (btn.dataset.sub === "workmode") this._initWorkModeDraft();
      if (btn.dataset.sub === "storm") this._enterStormSettings();
      if (btn.dataset.sub === "charts") this._enterChartsSettings();
      this._render();
      return;
    }
    if (action === "settings-tab") {
      this._view = "settings";
      this._settingsView = btn.dataset.sub;
      if (btn.dataset.sub === "schedules") this._initChargeDraft();
      if (btn.dataset.sub === "quick") this._initSocDraft();
      if (btn.dataset.sub === "workmode") this._initWorkModeDraft();
      if (btn.dataset.sub === "storm") this._enterStormSettings();
      if (btn.dataset.sub === "charts") this._enterChartsSettings();
      this._render();
      return;
    }
    if (action === "save-charts-settings") {
      await this._saveChartsSettings();
      return;
    }
    if (action === "pick-work-mode") {
      this._workModeDraft = btn.dataset.mode;
      this._render();
      return;
    }
    if (action === "copy-period") {
      if (!this._chargeDraft) return;
      const from = parseInt(btn.dataset.from, 10);
      const to = parseInt(btn.dataset.to, 10);
      if (Number.isNaN(from) || Number.isNaN(to)) return;
      this._chargeDraft[to] = { ...this._chargeDraft[from] };
      this._render();
      return;
    }
    if (action === "swap-periods") {
      if (!this._chargeDraft) return;
      const tmp = this._chargeDraft[0];
      this._chargeDraft[0] = this._chargeDraft[1];
      this._chargeDraft[1] = tmp;
      this._render();
      return;
    }
    if (action === "save-schedules") {
      await this._saveSchedules();
      return;
    }
    if (action === "save-soc") {
      await this._saveSoc();
      return;
    }
    if (action === "save-work-mode") {
      await this._saveWorkMode();
      return;
    }
    if (action === "apply-baseline") {
      await this._runPlantService("apply_baseline");
      return;
    }
    if (action === "take-control") {
      await this._runPlantService("take_control");
      return;
    }
    if (action === "release-control") {
      await this._runPlantService("release_control");
      return;
    }
    if (action === "arm-storm") {
      await this._runPlantService("arm_storm_prep", { reason: "panel_manual" });
      return;
    }
    if (action === "disarm-storm") {
      await this._runPlantService("disarm_storm_prep");
      return;
    }
    if (action === "save-storm-prep") {
      await this._saveStormPrep();
      return;
    }
    if (action === "remove-storm-trigger") {
      if (!this._stormDraft) return;
      const entityId = btn.dataset.entity;
      if (!entityId) return;
      this._stormDraft.trigger_entities = this._stormDraft.trigger_entities.filter((id) => id !== entityId);
      this._syncStormTriggerPicker();
      return;
    }
    if (action === "toggle-storm-advanced") {
      this._stormShowAdvanced = !this._stormShowAdvanced;
      this._scheduleRender();
      return;
    }
    if (action === "storm-google-quick-setup") {
      if (!this._stormDraft) this._initStormDraft();
      const entries = this._getGoogleWeatherEntries();
      if (!entries.length) {
        this._showToast("Install Google Weather first", "err");
        return;
      }
      const entry = entries.length === 1 ? entries[0] : entries.find((e) => e.entry_id === this._stormDraft.google_weather_entry_id);
      if (!entry) {
        this._showToast("Select a Google Weather location first", "err");
        return;
      }
      this._applyGoogleWeatherEntry(entry.entry_id);
      this._stormDraft.enabled = true;
      this._stormDraft.use_forecast_lead = true;
      if (!this._stormDraft.forecast_lead_hours) this._stormDraft.forecast_lead_hours = 4;
      await this._saveStormPrep();
      return;
    }
    if (action === "storm-show-google-only") {
      this._triggerGoogleOnly = true;
      this._triggerShowAll = false;
      this._triggerFilter = "";
      this._syncStormTriggerPicker();
      return;
    }
    if (action === "storm-show-suggested") {
      this._triggerGoogleOnly = false;
      this._triggerShowAll = false;
      this._syncStormTriggerPicker();
      return;
    }
    if (action === "storm-show-all") {
      this._triggerGoogleOnly = false;
      this._triggerShowAll = true;
      this._syncStormTriggerPicker();
    }
  }

  _handleChange(e) {
    const el = e.target;
    if (!el?.dataset?.action || this._busy) return;
    if (el.dataset.action === "toggle-storm-trigger") {
      if (!this._stormDraft) return;
      const entityId = el.dataset.entity;
      if (!entityId) return;
      const list = this._stormDraft.trigger_entities;
      if (el.checked) {
        if (!list.includes(entityId)) list.push(entityId);
      } else {
        this._stormDraft.trigger_entities = list.filter((id) => id !== entityId);
      }
      this._syncStormTriggerPicker();
      return;
    }
    if (el.dataset.action === "toggle-storm-enabled") {
      if (!this._stormDraft) this._initStormDraft();
      this._stormDraft.enabled = el.checked;
    }
  }

  _handleInput(e) {
    const el = e.target;
    if (el?.dataset?.action === "pick-forecast-entity") {
      if (!this._chartsDraft) return;
      this._chartsDraft.forecast_entity_id = el.value || null;
      this._scheduleRender();
      return;
    }
    if (el?.dataset?.action === "pick-google-weather-entry") {
      if (!this._stormDraft) return;
      this._applyGoogleWeatherEntry(el.value || null);
      this._scheduleRender();
      return;
    }
    if (el?.dataset?.action === "pick-plant") {
      const id = el.value;
      if (!id || id === this._selectedPlantId) return;
      this._selectedPlantId = id;
      this._plantState = undefined;
      this._energyChart = null;
      this._energyChartPlantId = undefined;
      this._statisticsChart = null;
      this._statisticsChartPlantId = undefined;
      this._settingsView = "main";
      this._deviceSub = "main";
      this._view = "overview";
      void this._refreshPlantState();
      this._render();
      return;
    }
    if (el?.dataset?.action === "storm-trigger-filter") {
      this._triggerFilter = el.value;
      if (this._triggerFilterTimer) window.clearTimeout(this._triggerFilterTimer);
      this._triggerFilterTimer = window.setTimeout(() => {
        this._triggerFilterTimer = undefined;
        this._syncStormTriggerPicker();
      }, 120);
      return;
    }
    if (!el?.dataset?.field) return;
    const parts = el.dataset.field.split(":");
    const kind = parts[0];
    if (kind === "storm-period" && this._stormDraft) {
      const i = parseInt(parts[1], 10);
      const field = parts[2];
      if (el.type === "checkbox") {
        this._stormDraft.charge_periods[i][field] = el.checked;
      } else {
        this._stormDraft.charge_periods[i][field] = el.value;
      }
      return;
    }
    if (kind === "storm-max-soc" && this._stormDraft) {
      const raw = String(el.value).trim();
      this._stormDraft.target_max_soc = raw === "" ? null : Math.max(10, Math.min(100, parseFloat(raw) || 100));
      return;
    }
    if (kind === "storm-lead-hours" && this._stormDraft) {
      const n = parseInt(String(el.value).trim(), 10);
      this._stormDraft.forecast_lead_hours = Math.max(1, Math.min(48, Number.isFinite(n) ? n : 4));
      return;
    }
    if (kind === "toggle-storm-forecast" && this._stormDraft) {
      this._stormDraft.use_forecast_lead = el.checked;
      this._scheduleRender();
      return;
    }
    if (kind === "period" && this._chargeDraft) {
      const i = parseInt(parts[1], 10);
      const field = parts[2];
      if (el.type === "checkbox") {
        this._chargeDraft[i][field] = el.checked;
      } else {
        this._chargeDraft[i][field] = el.value;
      }
      return;
    }
    if (kind === "soc-num" && this._socDraft) {
      const field = parts[1];
      const raw = String(el.value).trim();
      if (raw === "") return;
      const v = parseFloat(raw);
      if (Number.isNaN(v)) return;
      if (e.type === "change" || (v >= SOC_MIN_PCT && v <= 100)) {
        applySocDrag(this._socDraft, field, v);
        this._updateTripleSocDom();
      }
    }
  }

  _endSocDrag() {
    if (!this._socDrag) return;
    window.removeEventListener("pointermove", this._onSocMove);
    window.removeEventListener("pointerup", this._onSocEnd);
    window.removeEventListener("pointercancel", this._onSocEnd);
    this._socDrag = null;
  }

  _onSocMove(e) {
    if (!this._socDrag || !this._socDraft) return;
    const rect = this._socDrag.track.getBoundingClientRect();
    if (!rect.width) return;
    const t = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const pct = Math.round(SOC_MIN_PCT + t * (100 - SOC_MIN_PCT));
    applySocDrag(this._socDraft, this._socDrag.thumb, pct);
    this._updateTripleSocDom();
  }

  _onSocEnd() {
    const thumb = this._socDrag?.thumbEl;
    if (thumb) thumb.classList.remove("is-dragging");
    this._endSocDrag();
  }

  _bindTripleSoc() {
    const track = this._root.querySelector(".triple-soc-track");
    if (!track) return;
    track.querySelectorAll("[data-soc-thumb]").forEach((thumb) => {
      thumb.addEventListener("pointerdown", (e) => {
        if (this._busy) return;
        e.preventDefault();
        track.querySelectorAll(".triple-soc-thumb").forEach((t) => t.classList.remove("is-dragging"));
        thumb.classList.add("is-dragging");
        thumb.setPointerCapture(e.pointerId);
        this._socDrag = { thumb: thumb.dataset.socThumb, thumbEl: thumb, track };
        window.addEventListener("pointermove", this._onSocMove);
        window.addEventListener("pointerup", this._onSocEnd);
        window.addEventListener("pointercancel", this._onSocEnd);
      });
    });
  }

  _updateTripleSocDom() {
    const wrap = this._root.querySelector(".triple-soc");
    if (!wrap || !this._socDraft) return;
    const d = clampSocDraft(this._socDraft);
    const min = d.min_soc;
    const mid = d.min_soc_on_grid;
    const max = d.max_soc;
    const zones = wrap.querySelector(".triple-soc-zones");
    if (zones) {
      zones.innerHTML = `
<div class="triple-soc-zone critical" style="width:${min}%"></div>
<div class="triple-soc-zone reserve" style="width:${mid - min}%"></div>
<div class="triple-soc-zone usable" style="width:${max - mid}%"></div>
<div class="triple-soc-zone headroom" style="width:${100 - max}%"></div>`;
    }
    SOC_THUMBS.forEach((t) => {
      const thumb = wrap.querySelector(`[data-soc-thumb="${t.key}"]`);
      const val = d[t.key];
      if (thumb) {
        thumb.style.left = `${val}%`;
        thumb.style.background = t.color;
        thumb.title = `${t.label}: ${val}%`;
      }
      const num = wrap.querySelector(`[data-field="soc-num:${t.key}"]`);
      if (num && document.activeElement !== num) num.value = String(val);
    });
    const summary = wrap.querySelector(".triple-soc-summary");
    if (summary) {
      const live = wrap.querySelector(".triple-soc-battery-pct")?.textContent?.replace("%", "") ?? "0";
      summary.innerHTML =
        min === mid
          ? `<strong>Reserve from</strong> ${min}%<br><strong>Usable to</strong> ${max}% · <strong>Now</strong> ${live}%`
          : `<strong>Reserve band</strong> ${min}% – ${mid}%<br><strong>Usable to</strong> ${max}% · <strong>Now</strong> ${live}%`;
    }
  }

  _renderTripleSoc(plant, d, liveSoc) {
    const clamped = clampSocDraft({ ...d });
    const min = clamped.min_soc;
    const mid = clamped.min_soc_on_grid;
    const max = clamped.max_soc;
    const live = Math.max(0, Math.min(100, Math.round(liveSoc ?? 0)));
    const fillH = Math.max(4, live);

    const thumbsHtml = SOC_THUMBS.map(
      (t) =>
        `<button type="button" class="triple-soc-thumb" data-soc-thumb="${t.key}" style="left:${clamped[t.key]}%;background:${t.color}" title="${esc(t.label)}: ${clamped[t.key]}%" aria-label="${esc(t.label)} ${clamped[t.key]}%"></button>`
    ).join("");

    const numericHtml = SOC_THUMBS.map(
      (t) =>
        `<div><label>${esc(t.label)}</label><input type="number" min="${SOC_MIN_PCT}" max="100" step="1" data-field="soc-num:${t.key}" value="${clamped[t.key]}"></div>`
    ).join("");

    return `<div class="triple-soc">
<div class="triple-soc-head">
<div class="triple-soc-battery" aria-hidden="true">
<div class="triple-soc-battery-cap"></div>
<div class="triple-soc-battery-fill" style="height:${fillH}%"></div>
<div class="triple-soc-battery-pct">${live}%</div>
</div>
<div class="triple-soc-summary">
${
      min === mid
        ? `<strong>Reserve from</strong> ${min}%<br><strong>Usable to</strong> ${max}% · <strong>Now</strong> ${live}%`
        : `<strong>Reserve band</strong> ${min}% – ${mid}%<br><strong>Usable to</strong> ${max}% · <strong>Now</strong> ${live}%`
    }
</div>
</div>
<div class="triple-soc-track-wrap">
<div class="triple-soc-track">
<div class="triple-soc-zones">
<div class="triple-soc-zone critical" style="width:${min}%"></div>
<div class="triple-soc-zone reserve" style="width:${mid - min}%"></div>
<div class="triple-soc-zone usable" style="width:${max - mid}%"></div>
<div class="triple-soc-zone headroom" style="width:${100 - max}%"></div>
</div>
<div class="triple-soc-live" style="left:${live}%"></div>
${thumbsHtml}
</div>
<div class="triple-soc-scale"><span>${SOC_MIN_PCT}%</span><span>100%</span></div>
</div>
<div class="soc-legend">
<span><i style="background:#e53935"></i> Below off-grid min</span>
<span><i style="background:#f9a825"></i> Off-grid reserve</span>
<span><i style="background:#2e7d32"></i> Normal use</span>
<span><i style="background:var(--fp-accent)"></i> Charge headroom</span>
</div>
<div class="soc-numeric">${numericHtml}</div>
<p class="soc-limit-note">Minimum for all three limits is <strong>10%</strong>. The inverter rejects lower values over Modbus; the Fox app may allow 5% but behaviour is inconsistent.</p>
</div>`;
  }

  async _runPlantService(service, extra = {}) {
    const plant = this._getPlant();
    if (!plant) return;
    this._busy = true;
    this._render();
    try {
      await callService(this._hass, "foxess_plant", service, {
        plant_id: plant.entry_id,
        ...extra,
      });
      await this._refreshPlantState();
      this._showToast("Updated");
    } catch (err) {
      this._showToast(err?.message || "Action failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _saveSchedules() {
    const plant = this._getPlant();
    if (!plant || !this._chargeDraft) return;
    this._busy = true;
    this._render();
    try {
      await callService(this._hass, "foxess_plant", "set_charge_periods", {
        plant_id: plant.entry_id,
        charge_periods: this._chargeDraft,
        as_override: false,
      });
      await callService(this._hass, "foxess_plant", "apply_desired", {
        plant_id: plant.entry_id,
      });
      await this._refreshPlantState();
      this._showToast("Charge schedule saved & applied");
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _saveSoc() {
    const plant = this._getPlant();
    if (!plant || !this._socDraft) return;
    const clamped = clampSocDraft({ ...this._socDraft });
    const { min_soc, min_soc_on_grid, max_soc } = clamped;
    this._socDraft = clamped;
    this._busy = true;
    this._render();
    try {
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/set_soc_limits",
        plant_id: plant.entry_id,
        min_soc,
        min_soc_on_grid,
        max_soc,
      });
      if (state) this._plantState = state;
      await this._refreshPlantState();
      this._showToast("SOC limits saved");
    } catch (err) {
      this._showToast(err?.message || "SOC save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _saveWorkMode() {
    const plant = this._getPlant();
    const entity_id = plant?.entity_map?.work_mode;
    if (!entity_id || !this._workModeDraft) return;
    this._busy = true;
    this._render();
    try {
      await callService(this._hass, "select", "select_option", {
        entity_id,
        option: this._workModeDraft,
      });
      await this._refreshPlantState();
      this._showToast("Work mode updated");
    } catch (err) {
      this._showToast(err?.message || "Work mode failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _renderTabBar(items, activeId, actionName, dataAttr = "view", sub = false) {
    const barClass = sub ? "tab-bar sub" : "tab-bar";
    return `<nav class="${barClass}" role="tablist">${items
      .map(
        (item) =>
          `<button type="button" class="tab ${activeId === item.id ? "active" : ""}" role="tab" aria-selected="${activeId === item.id}" data-action="${actionName}" data-${dataAttr}="${item.id}">${esc(item.label)}</button>`
      )
      .join("")}</nav>`;
  }

  _modeBannerExtra() {
    const st = this._plantState;
    if (!st) return "";
    if (st.drift) {
      return `<div class="banner warn"><strong>Schedule drift</strong>Inverter charge windows differ from what Fox Plant expects. <div class="btn-row"><button type="button" class="btn btn-primary" data-action="apply-baseline" ${this._busy ? "disabled" : ""}>Re-apply schedule</button></div></div>`;
    }
    if (!st.control_active) {
      return `<div class="banner info"><strong>Manual control</strong>Fox Plant is not managing charge periods. Modbus or the Fox app may change settings freely.</div>`;
    }
    return "";
  }

  _modeBanner() {
    const st = this._plantState;
    if (!st) return "";
    const mode = st.mode ?? "baseline";
    return `<div class="mode-banner-row"><span class="mode-pill ${modeClass(mode)}">${esc(mode)}</span><span class="mode-banner-hint">${st.control_active ? "Plant control active" : "Plant control off"}</span></div>${this._modeBannerExtra()}`;
  }

  _renderOverviewStatusBlock(plant) {
    const st = this._plantState;
    if (!st) return "";
    const systemStatus = foxInverterStateLabel(this._hass, plant, this._plantState);
    const workMode = foxWorkModeLabel(this._hass, plant, this._plantState);
    const plantMode = st.mode ?? "baseline";
    const statusPart =
      systemStatus !== "—"
        ? `<span class="overview-fox-status ${foxStatusToneClass(systemStatus)}">${esc(systemStatus)}</span>`
        : "";
    const workPart = workMode !== "—" ? `<span class="overview-work-mode">${esc(workMode)}</span>` : "";
    return `<div class="overview-status-block">
<div class="overview-status-row">
${statusPart}
${workPart}
<span class="mode-pill ${modeClass(plantMode)}">${esc(plantMode)}</span>
<span class="overview-control-hint">${st.control_active ? "Plant control active" : "Plant control off"}</span>
</div>
${this._modeBannerExtra()}
</div>`;
  }

  _renderEnergyScene(plant) {
    const flows = readEnergyFlows(this._hass, plant, this._plantState);
    const lines = computeFlowLines(flows);
    const activeIds = new Set(lines.map((l) => l.id));
    const bgTheme = resolveFlowSceneBgTheme(this._hass, this._plantState);
    const overlayTheme = flowSceneOverlayTheme(bgTheme);
    const isNight = !bgTheme.startsWith("day_");
    const soc = Math.min(100, Math.max(0, flows.batterySoc));
    const gridExporting = flows.gridExportW > flows.gridImportW && flows.gridExportW > FLOW_SCENE_PV_THRESHOLD_W;
    const gridLabel = gridExporting ? "To Grid" : "On Grid";
    const gridPower = gridExporting ? flows.gridExportW : flows.gridImportW;
    const batteryStatus = String(flows.batteryStatus || "Idle").toUpperCase();
    const batteryPower = Math.abs(flows.batteryW);
    const pathsHtml = Object.entries(FOX_FLOW_PATHS)
      .map(([id, d]) => {
        const line = lines.find((l) => l.id === id);
        if (!line && !FOX_FLOW_HUB_SPOKES.has(id)) return "";
        const cls = id.startsWith("solar")
          ? "flow-solar"
          : id.includes("grid")
            ? gridExporting && id === "hub-grid"
              ? "flow-export"
              : "flow-grid"
            : id.includes("aio") || id.includes("hub-aio")
              ? "flow-battery"
              : "flow-home-line";
        const isActive = activeIds.has(id);
        if (FOX_FLOW_HUB_SPOKES.has(id)) {
          const base = flowPathMarkup({ d, cls, isBase: true });
          if (!isActive) return base;
          return `${base}${flowPathMarkup({ d, cls, isActive: true, reverse: !!line?.reverse })}`;
        }
        return flowPathMarkup({ d, cls, isActive });
      })
      .join("");
    const hubActive = lines.some((l) => l.id.includes("hub"));
    return `<div class="scene-card scene-card--fox-flow">
<div class="fox-flow-scene ${isNight ? "fox-flow-scene--night" : "fox-flow-scene--day"}" role="img" aria-label="Live energy flow" data-panel-build="${esc(this._panelBuild())}">
<div class="fox-flow-stage">
<img class="fox-flow-layer fox-flow-layer-bg" src="${esc(flowSceneLayerUrl("bg", bgTheme, overlayTheme))}" alt="" loading="eager" decoding="async" fetchpriority="high" />
<img class="fox-flow-layer fox-flow-layer-pv" src="${esc(flowSceneLayerUrl("pv", bgTheme, overlayTheme))}" alt="" loading="lazy" decoding="async" />
<img class="fox-flow-layer fox-flow-layer-aio" src="${esc(flowSceneLayerUrl("aio", bgTheme, overlayTheme))}" alt="" loading="lazy" decoding="async" />
<svg class="fox-flow-svg" viewBox="0 0 1024 1017" preserveAspectRatio="xMidYMid meet" aria-hidden="true" data-flow-paths-ver="${esc(this._panel?.config?.flow_paths_ver || FLOW_PATHS_VER)}" data-flow-stroke-base="${FLOW_STROKE.base}" data-flow-stroke-active="${FLOW_STROKE.active}" data-hub-r="${FLOW_STROKE.hubR}" data-hub-home="${esc(FOX_FLOW_PATHS["hub-home"])}" data-aio-hub="${esc(FOX_FLOW_PATHS["aio-hub"])}">
${pathsHtml}
<circle class="flow-hub-dot ${hubActive ? "active" : ""}" cx="${FOX_FLOW_HUB.x}" cy="${FOX_FLOW_HUB.y}" r="${FLOW_STROKE.hubR}"/>
</svg>
<div class="fox-flow-badge fox-flow-badge-solar">
<span class="fox-flow-badge-label">Solar</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(flows.pvW))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-grid">
<span class="fox-flow-badge-label">${esc(gridLabel)}</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(gridPower))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-battery">
<span class="fox-flow-badge-label">${esc(batteryStatus)}</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(batteryPower))} | ${esc(formatPercent(soc))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-home">
<span class="fox-flow-badge-label">Home</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(flows.loadW))}</span>
</div>
</div>
</div>
</div>`;
  }

  _renderStormHero(armed) {
    return `<div class="hero storm-hero ${armed ? "armed" : ""}">
<div class="storm-hero-media">
<img class="storm-hero-img" src="${esc(STORM_HERO_IMAGE_STATIC)}" alt="StormSafe charging: home with battery backup during a storm" loading="lazy" decoding="async" />
<span class="storm-hero-half storm-hero-half--left" aria-hidden="true"></span>
<span class="storm-hero-half storm-hero-half--right" aria-hidden="true"></span>
<h2 class="storm-hero-title">StormSafe Charging</h2>
</div>
</div>`;
  }

  _stat(label, value, suffix = "") {
    const has = value != null && value !== "—";
    return `<div class="stat"><label>${esc(label)}</label><strong>${has ? esc(String(value)) + esc(suffix) : "—"}</strong></div>`;
  }

  _renderImpactPanel() {
    const imp = this._plantState?.impact ?? {};
    if (imp.co2_kg == null && imp.trees_planted == null && imp.oil_litres == null) {
      return `<div class="card impact-card" style="margin-top:14px">
<p class="card-title">Impact</p>
<p class="placeholder impact-placeholder">Lifetime energy totals not available yet. Reload FoxESS Plant after foxess_modbus exposes <code>solar_energy_total</code> and <code>feed_in_energy_total</code>.</p>
</div>`;
    }
    const items = [
      {
        label: "CO₂ reduction",
        value: imp.co2_kg,
        unit: "kg",
        icon: "co2",
      },
      {
        label: "Trees planted",
        value: imp.trees_planted,
        unit: "",
        icon: "tree",
      },
      {
        label: "Oil saved",
        value: imp.oil_litres,
        unit: "L",
        icon: "oil",
      },
    ];
    const grid = items
      .map((item) => {
        const has = item.value != null;
        const display = has
          ? `${Number(item.value).toFixed(1)}${item.unit ? `<span class="impact-unit">${esc(item.unit)}</span>` : ""}`
          : "—";
        return `<div class="impact-metric">
<img class="impact-icon" src="${esc(impactIconUrl(item.icon))}" alt="" loading="lazy" decoding="async" />
<div class="impact-value">${display}</div>
<div class="impact-label">${esc(item.label)}</div>
</div>`;
      })
      .join("");
    const basis =
      imp.self_consumption_kwh_total != null
        ? `<p class="impact-basis">Based on ${Number(imp.self_consumption_kwh_total).toFixed(1)} kWh lifetime self-consumption (solar − export)</p>`
        : imp.solar_kwh_total != null
          ? `<p class="impact-basis">Based on ${Number(imp.solar_kwh_total).toFixed(1)} kWh lifetime solar generation</p>`
          : "";
    return `<div class="card impact-card" style="margin-top:14px">
<p class="card-title">Impact</p>
<div class="impact-grid">${grid}</div>
${basis}
</div>`;
  }

  _renderOverview(plant) {
    const a = this._plantState?.analytics ?? {};
    const modelLine = plantModelSubtitle(this._hass, plant, this._plantState);
    return `<header class="header overview-header"><h1>${esc(plant.title)}</h1>${modelLine !== "—" ? `<p class="overview-model">${esc(modelLine)}</p>` : ""}${this._renderOverviewStatusBlock(plant)}</header>
<div class="overview-hero-row">
<div class="overview-hero-scene">
${this._renderEnergyScene(plant)}
</div>
<div class="overview-hero-stats">
${this._stat("Self-consumption", a.self_consumption_percent_today, a.self_consumption_percent_today != null ? "%" : "")}
${this._stat("Self-sufficiency", a.self_sufficiency_percent_today, a.self_sufficiency_percent_today != null ? "%" : "")}
${this._stat("PV today", a.pv_production_kwh_today, a.pv_production_kwh_today != null ? " kWh" : "")}
</div>
</div>
${this._renderImpactPanel()}
<div class="card statistics-card" style="margin-top:14px">
<p class="card-title">Statistics</p>
${this._renderStatisticsChartBody()}
</div>`;
  }

  _identityRows(plant) {
    const id = this._plantState?.identity ?? {};
    const rows = [
      ["pcs_model_name", "PCS model"],
      ["pcs_serial_number", "PCS serial"],
      ["grid_status", "Grid status"],
      ["inverter_state", "System status"],
      ["modbus_protocol_version", "Modbus protocol"],
      ["master_version", "Master firmware"],
      ["slave_version", "Slave firmware"],
      ["manager_version", "Manager firmware"],
      ["bms_online", "BMS online"],
      ["bms_pack_serial_modbus", "BMS pack serial (Modbus)"],
      ["bms_pack_count", "BMS pack count"],
      ["bms_pack_1_version", "Pack 1 version"],
      ["bms_pack_2_version", "Pack 2 version"],
      ["bms_pack_3_version", "Pack 3 version"],
      ["bms_pack_4_version", "Pack 4 version"],
    ];
    return rows
      .map(([key, label]) => {
        let value = id[key];
        if (value == null || value === "" || value === "unavailable" || value === "unknown") return null;
        if (key === "inverter_state") {
          value = foxInverterStateLabel(this._hass, plant, this._plantState);
        }
        return { label, value };
      })
      .filter(Boolean);
  }

  _identityValueList(rows) {
    if (!rows.length) {
      return `<p class="placeholder">No identity entities discovered yet. Update foxess_modbus, reload Home Assistant, then reload this panel.</p>`;
    }
    return `<div class="entity-list">${rows
      .map(
        (r) =>
          `<div class="entity-row"><span class="entity-name">${esc(r.label)}</span><span class="entity-value">${esc(r.value)}</span></div>`
      )
      .join("")}</div>`;
  }

  _renderDevice(plant) {
    if (this._deviceSub === "system") {
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>System info</h1><p>From Modbus (matches Fox app where confirmed)</p></header>${this._identityValueList(this._identityRows(plant))}`;
    }
    if (this._deviceSub === "parameters") {
      const rows = [
        ["pv_power", "PV power"],
        ["load_power", "Load"],
        ["grid_import", "Grid import"],
        ["grid_export", "Grid export"],
        ["battery_power", "Battery"],
        ["battery_soc", "SOC"],
      ]
        .map(([k, n]) => (plant.entity_map?.[k] ? { entity_id: plant.entity_map[k], name: n } : null))
        .filter(Boolean);
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>Parameters</h1></header>${this._entityList(rows)}`;
    }
    if (this._deviceSub === "battery") {
      const rows = [
        ["battery_soc", "SOC"],
        ["battery_power", "Power"],
        ["battery_status", "Status"],
        ["bms_temp_low", "Min temp"],
      ]
        .map(([k, n]) => (plant.entity_map?.[k] ? { entity_id: plant.entity_map[k], name: n } : null))
        .filter(Boolean);
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>Battery</h1></header>${this._entityList(rows)}`;
    }
    const flows = readEnergyFlows(this._hass, plant, this._plantState);
    const pvKw = flows.pvW / 1000;
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    const tempRaw = stateString(this._hass, map.bms_temp_low);
    const tempDisplay = tempRaw !== "—" ? `${tempRaw}℃` : "—";
    const serial = plantDeviceSerial(this._hass, plant, this._plantState);
    const modelLine = plantModelSubtitle(this._hass, plant, this._plantState);
    const systemStatus = foxInverterStateLabel(this._hass, plant, this._plantState);
    const statusPill =
      systemStatus !== "—"
        ? `<div class="device-fox-pill ${foxStatusToneClass(systemStatus)}">${esc(systemStatus)}</div>`
        : "";
    const serialRow =
      serial !== "—"
        ? `<button type="button" class="device-serial-btn" data-action="device-sub" data-sub="system"><span class="device-serial">${esc(serial)}</span><span class="chev">›</span></button>`
        : `<p class="device-serial device-serial-muted">Serial unavailable</p>`;
    return `<header class="header device-header"><h1>${esc(plant.title)}</h1>${modelLine !== "—" ? `<p class="device-model">${esc(modelLine)}</p>` : ""}</header>
${statusPill}
<div class="device-hero"><img class="device-hero-img" src="${esc(DEVICE_EVO_IMAGE_STATIC)}" alt="${esc(modelLine !== "—" ? modelLine : "Inverter")}" loading="lazy" />${serialRow}</div>
<div class="device-grid">
<div class="device-card device-card--gauge">${renderPvThreeQuarterGauge(pvKw, DEVICE_PV_GAUGE_MAX_KW, formatDevicePowerKw(flows.pvW), "PV Power")}</div>
<div class="device-card device-card--battery">${renderDeviceBatteryCard(flows, tempDisplay)}</div>
</div>
${renderListButton({ action: "device-sub", sub: "parameters" }, "Detailed parameters", "Live Modbus values")}
${renderListButton({ action: "nav", view: "overview" }, "Analysis graph", "Today's statistics chart")}
${renderListButton({ action: "device-sub", sub: "system" }, "System info", "Firmware, BMS, grid status")}`;
  }

  _entityList(rows) {
    if (!rows.length) return `<p class="placeholder">No entities mapped.</p>`;
    return `<div class="entity-list">${rows
      .map(
        (r) =>
          `<div class="entity-row"><span class="entity-name">${esc(r.name)}</span><span class="entity-value">${esc(stateString(this._hass, r.entity_id))}${esc(entityUnit(this._hass, r.entity_id))}</span></div>`
      )
      .join("")}</div>`;
  }

  _energyHistoryEntities(plant) {
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    return {
      pv: map.solar_energy_today,
      load: map.load_energy_today,
      discharge: map.battery_discharge_today,
      charge: map.battery_charge_today,
      grid: map.grid_consumption_energy_today,
    };
  }

  async _loadEnergyCharts() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    if (this._energyPeriod === "day") {
      return this._loadStatisticsChart();
    }
    if (!this._plantState) await this._refreshPlantState();
    const plantId = plant.entry_id;
    this._energyChartLoading = true;
    this._energyChart = null;
    this._energyChartPlantId = plantId;
    this._scheduleRender();
    try {
      const bar = await this._fetchPeriodEnergyBarChart(plant, this._energyPeriod);
      this._energyChart = { kind: "bar", svg: bar.svg, title: bar.title };
    } catch (err) {
      this._energyChart = {
        error:
          err?.message ||
          "Could not load history. Enable the Home Assistant recorder and keep history for power sensors.",
      };
    } finally {
      this._energyChartLoading = false;
      if (this._getPlant()?.entry_id === plantId && this._view === "energy") this._scheduleRender();
    }
  }

  async _loadStatisticsChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const plantId = plant.entry_id;
    this._statisticsChartLoading = true;
    this._statisticsChart = null;
    this._statisticsChartPlantId = plantId;
    this._scheduleRender();
    try {
      if (!this._plantState) await this._refreshPlantState();
      const chart = await this._fetchStatisticsChartData(plant);
      this._statisticsChart = chart;
    } catch (err) {
      this._statisticsChart = {
        error:
          err?.message ||
          "Could not load history. Enable the Home Assistant recorder and keep history for power sensors.",
      };
    } finally {
      this._statisticsChartLoading = false;
      if (this._getPlant()?.entry_id === plantId) this._scheduleRender();
    }
  }

  async _fetchStatisticsChartData(plant) {
    return fetchStatisticsChartSeries(this._hass, plant, this._plantState);
  }

  _renderStatisticsChartBody() {
    if (this._statisticsChartLoading) {
      return `<p class="chart-loading">Loading statistics…</p>`;
    }
    if (this._statisticsChart?.error) {
      return `<p class="placeholder chart-empty">${esc(this._statisticsChart.error)}</p>`;
    }
    if (this._statisticsChart?.empty) {
      return `<p class="placeholder chart-empty">${esc(this._statisticsChart.empty)}</p>`;
    }
    if (this._statisticsChart?.series) {
      return renderStatisticsChartHtml(this._statisticsChart.series, this._statisticsChart.range);
    }
    return `<p class="placeholder chart-empty">Open Energy or wait for history to load.</p>`;
  }

  _bindStatisticsChart() {
    if (!this._statisticsChart?.series) return;
    bindStatisticsChart(this._root, this._statisticsChart.series);
  }

  async _fetchPeriodEnergyBarChart(plant, period) {
    const ent = this._energyHistoryEntities(plant);
    const ids = [ent.pv, ent.load, ent.discharge, ent.charge, ent.grid].filter(Boolean);
    if (!ids.length) {
      return {
        title: period === "month" ? "This month" : "This year",
        svg: `<p class="placeholder chart-empty">Daily energy sensors not found. Reload FoxESS Plant.</p>`,
      };
    }
    const now = new Date();
    let rangeStart;
    let labels;
    let title;
    if (period === "month") {
      rangeStart = new Date(now.getFullYear(), now.getMonth(), 1);
      const dayCount = now.getDate();
      labels = buildDailyLabels(rangeStart, dayCount);
      title = now.toLocaleDateString(undefined, { month: "long", year: "numeric" });
    } else {
      rangeStart = new Date(now.getFullYear(), 0, 1);
      labels = [];
      for (let m = 0; m <= now.getMonth(); m++) labels.push(new Date(now.getFullYear(), m, 1));
      title = String(now.getFullYear());
    }
    const hist = await fetchHistoryDuring(this._hass, ids, rangeStart, now);
    const points = {
      pv: historyToPoints(historyRowsForEntity(hist, ent.pv)),
      load: historyToPoints(historyRowsForEntity(hist, ent.load)),
      discharge: historyToPoints(historyRowsForEntity(hist, ent.discharge)),
      charge: historyToPoints(historyRowsForEntity(hist, ent.charge)),
      grid: historyToPoints(historyRowsForEntity(hist, ent.grid)),
    };

    const bucketDaily = (pSeries, lSeries, dSeries, cSeries, gSeries) => {
      const vals = [];
      for (const day of labels) {
        const ds = startOfLocalDay(day).getTime();
        const de = endOfLocalDay(day).getTime();
        const load =
          dailyMaxInRange(lSeries, ds, de) -
          dailyMaxInRange(dSeries, ds, de) +
          dailyMaxInRange(cSeries, ds, de) +
          dailyMaxInRange(gSeries, ds, de);
        vals.push(Math.max(0, Math.round(load * 100) / 100));
      }
      return vals;
    };

    if (period === "month") {
      const groups = [
        {
          label: ENERGY_CHART_BAR.pv.label,
          color: ENERGY_CHART_BAR.pv.color,
          values: labels.map((day) => {
            const ds = startOfLocalDay(day).getTime();
            const de = endOfLocalDay(day).getTime();
            return Math.round(dailyMaxInRange(points.pv, ds, de) * 100) / 100;
          }),
        },
        {
          label: ENERGY_CHART_BAR.load.label,
          color: ENERGY_CHART_BAR.load.color,
          values: bucketDaily(points.pv, points.load, points.discharge, points.charge, points.grid),
        },
        {
          label: ENERGY_CHART_BAR.grid.label,
          color: ENERGY_CHART_BAR.grid.color,
          values: labels.map((day) => {
            const ds = startOfLocalDay(day).getTime();
            const de = endOfLocalDay(day).getTime();
            return Math.round(dailyMaxInRange(points.grid, ds, de) * 100) / 100;
          }),
        },
      ];
      return { title, svg: renderBarChartSvg(groups, labels) };
    }

    const monthLabels = labels;
    const monthGroups = [
      { label: ENERGY_CHART_BAR.pv.label, color: ENERGY_CHART_BAR.pv.color, values: [] },
      { label: ENERGY_CHART_BAR.load.label, color: ENERGY_CHART_BAR.load.color, values: [] },
      { label: ENERGY_CHART_BAR.grid.label, color: ENERGY_CHART_BAR.grid.color, values: [] },
    ];
    for (const monthStart of monthLabels) {
      const monthEnd = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0);
      const end = monthStart.getMonth() === now.getMonth() ? now : endOfLocalDay(monthEnd);
      const days = buildDailyLabels(monthStart, end.getDate());
      let pvSum = 0;
      let loadSum = 0;
      let gridSum = 0;
      for (const day of days) {
        const ds = startOfLocalDay(day).getTime();
        const de = endOfLocalDay(day).getTime();
        pvSum += dailyMaxInRange(points.pv, ds, de);
        gridSum += dailyMaxInRange(points.grid, ds, de);
        const load =
          dailyMaxInRange(points.load, ds, de) -
          dailyMaxInRange(points.discharge, ds, de) +
          dailyMaxInRange(points.charge, ds, de) +
          dailyMaxInRange(points.grid, ds, de);
        loadSum += Math.max(0, load);
      }
      monthGroups[0].values.push(Math.round(pvSum * 100) / 100);
      monthGroups[1].values.push(Math.round(loadSum * 100) / 100);
      monthGroups[2].values.push(Math.round(gridSum * 100) / 100);
    }
    return { title, svg: renderBarChartSvg(monthGroups, monthLabels.map(formatChartMonthLabel)) };
  }

  _renderEnergyCharts() {
    const periods = [
      { id: "day", label: "Day" },
      { id: "month", label: "Month" },
      { id: "year", label: "Year" },
    ];
    const tabs = periods
      .map(
        (p) =>
          `<button type="button" data-action="energy-period" data-period="${p.id}" class="${p.id === this._energyPeriod ? "active" : ""}">${p.label}</button>`
      )
      .join("");
    let body;
    if (this._energyPeriod === "day") {
      body = this._renderStatisticsChartBody();
    } else if (this._energyChartLoading) {
      body = `<p class="chart-loading">Loading chart…</p>`;
    } else if (this._energyChart?.error) {
      body = `<p class="placeholder chart-empty">${esc(this._energyChart.error)}</p>`;
    } else if (this._energyChart?.svg) {
      body = this._energyChart.svg;
    } else {
      body = `<p class="chart-loading">Loading chart…</p>`;
    }
    const chartTitle =
      this._energyPeriod === "day"
        ? "Statistics"
        : this._energyChart?.title || (this._energyPeriod === "month" ? "This month" : "This year");
    return `<div class="card energy-chart-card">
<p class="card-title">${esc(chartTitle)}</p>
<div class="energy-period-tabs">${tabs}</div>
${body}
</div>`;
  }

  _renderEnergyTodayBreakdown(a) {
    const pvTotal = Number(a.pv_production_kwh_today ?? 0) || 0;
    const pvToLoadBattery = Number(a.pv_to_load_battery_kwh_today ?? 0) || 0;
    const pvToGrid = Number(a.pv_to_grid_kwh_today ?? 0) || 0;
    const loadTotal = Number(a.load_consumption_kwh_today ?? 0) || 0;
    const loadFromPvBattery = Number(a.load_from_pv_battery_kwh_today ?? 0) || 0;
    const loadFromGrid = Number(a.load_from_grid_kwh_today ?? 0) || 0;
    const selfConsumption = Number(a.self_consumption_percent_today ?? 0) || 0;
    const selfSufficiency = Number(a.self_sufficiency_percent_today ?? 0) || 0;
    const textMain = "var(--primary-text-color)";

    const pvRow = renderEnergyBreakdownRow({
      heading: "PV Production",
      totalKwh: pvTotal,
      metrics: [
        { label: "To Load & Battery", value: pvToLoadBattery, color: FOX_ENERGY.pv },
        { label: "To Grid", value: pvToGrid, color: textMain },
      ],
      segments: [
        { value: pvToLoadBattery, color: FOX_ENERGY.pv },
        { value: pvToGrid, color: FOX_ENERGY.muted },
      ],
      centerPct: selfConsumption,
      centerLabel: "Self-Consumption",
      accent: FOX_ENERGY.pv,
    });

    const loadRow = renderEnergyBreakdownRow({
      heading: "Load Consumption",
      totalKwh: loadTotal,
      metrics: [
        { label: "From PV & Battery", value: loadFromPvBattery, color: FOX_ENERGY.load },
        { label: "From Grid", value: loadFromGrid, color: textMain },
      ],
      segments: [
        { value: loadFromPvBattery, color: FOX_ENERGY.load },
        { value: loadFromGrid, color: FOX_ENERGY.muted },
      ],
      centerPct: selfSufficiency,
      centerLabel: "Self-Sufficiency",
      accent: FOX_ENERGY.load,
    });

    return `<div class="card breakdown-card">
<p class="card-title">Today energy breakdown</p>
<div class="fox-energy-panel">${pvRow}${loadRow}</div>
</div>`;
  }

  _renderEnergy() {
    const a = this._plantState?.analytics ?? {};
    const has = Object.keys(a).length > 0;
    return `<header class="header"><h1>Energy</h1><p>Daily production and consumption</p></header>
${
  has
    ? `<div class="stats-row">
${this._stat("Load", a.load_consumption_kwh_today, " kWh")}
${this._stat("From grid", a.load_from_grid_kwh_today, " kWh")}
${this._stat("PV → grid", a.pv_to_grid_kwh_today, " kWh")}
${this._stat("Self-use", a.self_consumption_percent_today, "%")}
</div>
<div class="card" style="margin-top:14px"><p class="card-title">Balance</p>
<div class="stats-row">
${this._stat("Battery charge", a.battery_charge_kwh_today, " kWh")}
${this._stat("Battery discharge", a.battery_discharge_kwh_today, " kWh")}
</div></div>`
    : `<p class="placeholder">Analytics appear after the coordinator refreshes.</p>`
}
${has ? this._renderEnergyTodayBreakdown(a) : ""}
${this._renderEnergyCharts()}`;
  }

  _renderPeriodCard(idx, period, fieldPrefix = "period", titlePrefix = "Period") {
    const p = period || DEFAULT_PERIODS[0];
    const actual = fieldPrefix === "period" ? this._plantState?.actual_periods?.[idx] : null;
    const drift =
      actual &&
      (Boolean(p.enable_force_charge) !== Boolean(actual.enable_force_charge) ||
        Boolean(p.enable_charge_from_grid) !== Boolean(actual.enable_charge_from_grid));
    return `<div class="period-card">
<h4>${titlePrefix} ${idx + 1} ${drift ? '<span style="color:var(--fp-amber);font-size:12px">≠ inverter</span>' : ""}</h4>
<div class="toggle-row"><span>Force charge</span><input type="checkbox" data-field="${fieldPrefix}:${idx}:enable_force_charge" ${p.enable_force_charge ? "checked" : ""}></div>
<div class="toggle-row"><span>Charge from grid</span><input type="checkbox" data-field="${fieldPrefix}:${idx}:enable_charge_from_grid" ${p.enable_charge_from_grid ? "checked" : ""}></div>
<div class="period-times">
<div class="field"><label>Start</label><input type="time" data-field="${fieldPrefix}:${idx}:start" value="${esc(timeForInput(p.start))}"></div>
<div class="field"><label>End</label><input type="time" data-field="${fieldPrefix}:${idx}:end" value="${esc(timeForInput(p.end))}"></div>
</div>
</div>`;
  }

  _triggerRowId(entityId) {
    return `tr-${String(entityId).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  }

  _getFilteredTriggerRows() {
    const all = this._triggerCandidates ?? [];
    const filter = (this._triggerFilter || "").trim().toLowerCase();
    let rows = all;
    if (filter) {
      rows = all.filter((row) => {
        const blob = `${row.entity_id} ${row.name}`.toLowerCase();
        return blob.includes(filter);
      });
    } else if (this._triggerGoogleOnly) {
      const gw = all.filter((row) => row.provider === "google_weather");
      rows = gw.length ? gw : all.filter((row) => row.suggested);
    } else if (!this._triggerShowAll) {
      const suggested = all.filter((row) => row.suggested);
      rows = suggested.length ? suggested : all;
    }
    return rows;
  }

  _googleRoleLabel(role) {
    if (role === "urgent") return "Urgent";
    if (role === "severe") return "Severe";
    if (role === "any") return "Alert";
    return "";
  }

  _renderGoogleWeatherSource() {
    const gw = this._triggerMeta?.google_weather;
    const draft = this._stormDraft;
    if (!gw || !draft) {
      return `<div class="card gw-card gw-warn"><p class="card-title">Weather source</p><p class="gw-status">Loading…</p></div>`;
    }
    const repo = gw.hacs_repo || "https://github.com/safepay/ha_google_weather";
    const entries = gw.entries ?? [];
    const selectedId = draft.google_weather_entry_id || "";
    const selected = this._getSelectedGoogleWeatherEntry();

    if (!gw.installed) {
      return `<div class="card gw-card gw-warn"><p class="card-title">Install Google Weather (2 minutes)</p>
<ol class="storm-hint" style="margin:0;padding-left:18px;line-height:1.6">
<li>HACS → Custom repositories → <a href="${esc(repo)}" target="_blank" rel="noopener">ha_google_weather</a></li>
<li>Install <strong>Google Weather</strong>, restart Home Assistant</li>
<li>Settings → Integrations → Add → Google Weather (API key + your home location)</li>
<li>Return here and press <strong>Turn on StormSafe</strong></li>
</ol></div>`;
    }

    if (!entries.length) {
      return `<div class="card gw-card gw-warn"><p class="card-title">Google Weather</p>
<p class="gw-status">No Google Weather config entries found. Add the integration under Settings → Devices &amp; services.</p></div>`;
    }

    const options = entries
      .map(
        (e) =>
          `<option value="${esc(e.entry_id)}" ${e.entry_id === selectedId ? "selected" : ""}>${esc(e.title)}</option>`
      )
      .join("");
    let cls = "gw-card";
    let detail = "";

    const cond = selected?.current_condition;
    const savedStorm = this._plantState?.storm_prep ?? {};
    const forecast = savedStorm.forecast_detail ?? {};
    const forecastActive = Boolean(savedStorm.forecast_active);

    if (selected?.alerts_supported) {
      cls += " gw-ready";
      const names = selected.alert_entities.map((a) => esc(a.name)).join(", ");
      detail = `<p class="gw-linked"><strong>Alert triggers:</strong> ${names} (when <em>on</em>).</p>`;
    }

    if (selected?.condition_supported || selected?.weather_entity) {
      cls += selected?.alerts_supported ? "" : " gw-ready";
      detail += `<p class="gw-linked"><strong>Native Google Weather</strong> — current conditions + hourly forecast. Pre-charges when a storm is due within your lead time (below).</p>`;
      if (cond) {
        const stormNow = cond.is_storm
          ? '<strong style="color:var(--fp-amber)">storm now</strong>'
          : "clear now";
        detail += `<p class="gw-linked">Now: <strong>${esc(cond.label || cond.text)}</strong> (<code>${esc(cond.type || "—")}</code>) — ${stormNow}.</p>`;
      } else if (selected.condition_entity_id) {
        detail += `<p class="gw-linked">Enable the <strong>Weather condition</strong> sensor in HA if hidden (eye icon).</p>`;
      }
      if (forecastActive && forecast.next_storm) {
        detail += `<p class="gw-linked">Forecast: storm in ~<strong>${esc(String(forecast.next_storm.hours_until))}</strong>h (<code>${esc(forecast.next_storm.condition)}</code>) — <strong style="color:var(--fp-amber)">pre-charge active</strong>.</p>`;
      } else if (draft.use_forecast_lead && selected.weather_entity) {
        detail += `<p class="gw-linked">Forecast: no storm in the next <strong>${esc(String(draft.forecast_lead_hours || 4))}</strong> hours.</p>`;
      }
    } else if (selected) {
      cls += " gw-warn";
      detail = `<p class="gw-linked">No weather condition sensor found for this integration entry. Update Google Weather or pick another source under Advanced.</p>`;
    } else {
      detail = `<p class="gw-linked">Choose your Google Weather location. StormSafe uses official alert binaries (if available) and/or the weather condition sensor.</p>`;
    }

    if (selected?.weather_entity) {
      detail += `<p class="gw-linked">Also watches: <code>${esc(selected.weather_entity)}</code></p>`;
    }

    const quickBtn =
      entries.length && selected
        ? `<div class="btn-row" style="margin-top:10px"><button type="button" class="btn btn-primary" data-action="storm-google-quick-setup" ${this._busy ? "disabled" : ""}>Turn on StormSafe</button></div>`
        : "";
    return `<div class="card ${cls}"><p class="card-title">Google Weather</p>
<label class="field"><span style="font-size:12px;color:var(--secondary-text-color)">Location</span>
<select class="gw-select" data-action="pick-google-weather-entry" ${this._busy ? "disabled" : ""}>
<option value="">— Select location —</option>
${options}
</select></label>
${detail}${quickBtn}</div>`;
  }

  _renderStormAdvancedTriggers() {
    const draft = this._stormDraft;
    if (!this._stormShowAdvanced) {
      return `<details class="storm-advanced"><summary data-action="toggle-storm-advanced">Advanced: pick individual trigger entities</summary></details>`;
    }
    return `<details class="storm-advanced" open>
<summary data-action="toggle-storm-advanced">Advanced: pick individual trigger entities</summary>
<p class="storm-hint">Only needed if you are not using Google Weather alerts, or you want extra sensors (MeteoAlarm, NWS, templates).</p>
<div data-storm-trigger-chips>${this._renderTriggerChips()}</div>
<input type="search" class="trigger-filter" data-action="storm-trigger-filter" placeholder="Search entities…" value="${esc(this._triggerFilter)}" aria-label="Filter trigger entities">
<div class="trigger-filter-actions">
<button type="button" class="btn btn-secondary" data-action="storm-show-suggested" ${!this._triggerShowAll && !this._triggerFilter ? "disabled" : ""}>Weather matches</button>
<button type="button" class="btn btn-secondary" data-action="storm-show-all" ${this._triggerShowAll ? "disabled" : ""}>All binary sensors</button>
</div>
<div data-storm-trigger-list>${this._renderTriggerPickerListHtml()}</div>
<p style="margin:10px 0 0;font-size:12px;color:var(--secondary-text-color)" data-storm-trigger-count>${draft.trigger_entities.length} selected</p>
</details>`;
  }

  _renderTriggerChips() {
    const selected = this._stormDraft?.trigger_entities ?? [];
    if (!selected.length) {
      return '<p class="storm-hint" style="margin:0">Selected triggers appear here. Tick entities below, or use the search box.</p>';
    }
    return `<div class="trigger-chips-wrap">${selected
      .map((entityId) => {
        const row = (this._triggerCandidates ?? []).find((r) => r.entity_id === entityId);
        const name = row?.name ?? entityId;
        return `<span class="trigger-chip trigger-chip-selected"><button type="button" data-action="remove-storm-trigger" data-entity="${esc(entityId)}" aria-label="Remove ${esc(name)}">×</button>${esc(name)}</span>`;
      })
      .join("")}</div>`;
  }

  _renderTriggerPickerListHtml() {
    const selected = new Set(this._stormDraft?.trigger_entities ?? []);
    const rows = this._getFilteredTriggerRows();
    const all = this._triggerCandidates ?? [];
    const suggestedCount = all.filter((r) => r.suggested).length;

    if (!all.length) {
      return `<p class="placeholder" style="margin:8px 0 0">Loading entities… If this stays empty, reload FoxESS Plant and ensure weather warning binary sensors exist in Home Assistant.</p>`;
    }
    if (!rows.length) {
      const hint = this._triggerGoogleOnly
        ? "No Google Weather alerts match. Install Google Weather with alerts enabled, or show all sensors."
        : `No matches for “${esc(this._triggerFilter)}”. Try “alert”, “warning”, or show all sensors.`;
      return `<p class="placeholder" style="margin:8px 0 0">${hint}</p>`;
    }

    const showGroupedHeader =
      !this._triggerFilter && !this._triggerGoogleOnly && this._triggerShowAll && suggestedCount > 0;
    const googleRows = showGroupedHeader ? rows.filter((r) => r.provider === "google_weather") : [];
    const suggestedRows = showGroupedHeader
      ? rows.filter((r) => r.suggested && r.provider !== "google_weather")
      : [];
    const otherRows = showGroupedHeader
      ? rows.filter((r) => !r.suggested && r.provider !== "google_weather")
      : rows;

    const renderRows = (list) =>
      list
        .map((row) => {
          const on = selected.has(row.entity_id);
          const cls = [
            "trigger-row",
            row.provider === "google_weather" ? "google-weather" : "",
            row.suggested ? "suggested" : "",
          ]
            .filter(Boolean)
            .join(" ");
          const id = this._triggerRowId(row.entity_id);
          const role = row.provider === "google_weather" ? this._googleRoleLabel(row.role) : "";
          const roleHtml = role ? `<span class="trigger-role">${esc(role)}</span>` : "";
          return `<div class="${cls}">
<input type="checkbox" id="${id}" data-action="toggle-storm-trigger" data-entity="${esc(row.entity_id)}" ${on ? "checked" : ""}>
<label for="${id}">${esc(row.name)}${roleHtml}<span class="entity-id">${esc(row.entity_id)}</span></label>
<span class="entity-state">${esc(row.state)}</span>
</div>`;
        })
        .join("");

    let body = "";
    if (showGroupedHeader && googleRows.length) {
      body += `<p class="trigger-section-title">Google Weather (${googleRows.length})</p>${renderRows(googleRows)}`;
      if (suggestedRows.length) {
        body += `<p class="trigger-section-title">Other weather &amp; warnings (${suggestedRows.length})</p>${renderRows(suggestedRows)}`;
      }
      if (otherRows.length) {
        body += `<p class="trigger-section-title">Other binary sensors (${otherRows.length})</p>${renderRows(otherRows)}`;
      }
    } else if (this._triggerGoogleOnly && rows.length) {
      body += `<p class="trigger-section-title">Google Weather alerts (${rows.length})</p>${renderRows(rows)}`;
    } else {
      body = renderRows(rows);
    }

    return `<div class="trigger-list">${body}</div>`;
  }

  _syncStormTriggerPicker() {
    if (this._settingsView !== "storm" || !this._stormDraft) return;
    const main = this._root.querySelector(".main");
    if (!main) return;

    const listHost = main.querySelector("[data-storm-trigger-list]");
    const chipsHost = main.querySelector("[data-storm-trigger-chips]");
    const countEl = main.querySelector("[data-storm-trigger-count]");
    const filterEl = main.querySelector('[data-action="storm-trigger-filter"]');
    if (!listHost) return;

    const scrollEl = listHost.querySelector(".trigger-list");
    const scrollTop = scrollEl?.scrollTop ?? 0;
    const filterHadFocus = document.activeElement === filterEl;
    const selStart = filterEl?.selectionStart ?? 0;
    const selEnd = filterEl?.selectionEnd ?? 0;

    if (chipsHost) chipsHost.innerHTML = this._renderTriggerChips();
    listHost.innerHTML = this._renderTriggerPickerListHtml();
    if (countEl) {
      countEl.textContent = `${this._stormDraft.trigger_entities.length} selected`;
    }

    const newScroll = listHost.querySelector(".trigger-list");
    if (newScroll) newScroll.scrollTop = scrollTop;

    if (filterHadFocus && filterEl) {
      filterEl.focus();
      try {
        filterEl.setSelectionRange(selStart, selEnd);
      } catch {
        /* some browsers reject on type=search */
      }
    }
  }

  _renderSettingsMain(plant) {
    const s = this._plantState?.settings ?? {};
    const storm = this._plantState?.storm_prep ?? {};
    const triggersArmed = Boolean(this._plantState?.active_storm_triggers?.length);
    const overrideArmed =
      Boolean(this._plantState?.override_active) && String(this._plantState?.mode ?? "") === "storm";
    const armed = triggersArmed || overrideArmed;
    const gwEntry = (this._getGoogleWeatherEntries() || []).find(
      (e) => e.entry_id === storm.google_weather_entry_id
    );
    const stormSub = storm.enabled
      ? gwEntry
        ? `${gwEntry.title}${armed ? " · active" : ""}`
        : `${(storm.trigger_entities ?? []).length} trigger(s)`
      : "Off";
    return `<header class="header"><h1>Settings</h1><p>Quick controls for your plant</p></header>
${this._modeBanner()}
${renderListButton({ action: "settings-sub", sub: "quick" }, "Quick Settings", `Max ${s.max_soc ?? "—"}% · Min ${s.min_soc ?? "—"}% · Off-grid ${s.min_soc_on_grid ?? "—"}%`)}
${renderListButton({ action: "settings-sub", sub: "schedules" }, "Charge schedule", "Two charge windows (baseline)")}
${renderListButton({ action: "settings-sub", sub: "workmode" }, "Work mode", String(s.work_mode ?? "—"))}
${renderListButton({ action: "settings-sub", sub: "storm" }, "StormSafe", stormSub)}
${renderListButton({ action: "settings-sub", sub: "charts" }, "Charts", this._forecastEntityLabel())}
${renderListButton({ action: "settings-sub", sub: "control" }, "Plant control", this._plantState?.control_active ? "Fox Plant manages periods" : "Released to manual")}`;
  }

  _forecastEntityLabel() {
    const id = this._plantState?.panel_display?.forecast_entity_id;
    if (!id) return "No forecast overlay";
    const st = this._hass?.states?.[id];
    const name = st?.attributes?.friendly_name || id.split(".")[1] || id;
    return name;
  }

  _renderSettingsQuick() {
    if (!this._socDraft) this._initSocDraft();
    const plant = this._getPlant();
    const liveSoc = plant ? stateNumber(this._hass, plant.entity_map?.battery_soc) : 0;
    return `<header class="header"><h1>Quick Settings</h1><p>Drag the three handles — off-grid min, system min, system max</p></header>
<div class="card">
<p class="card-title">SOC limits</p>
${this._renderTripleSoc(plant, this._socDraft, liveSoc)}
<div class="btn-row"><button type="button" class="btn btn-primary" data-action="save-soc" ${this._busy ? "disabled" : ""}>Save to inverter</button></div>
</div>`;
  }

  _renderSettingsSchedules() {
    if (!this._chargeDraft) this._initChargeDraft();
    return `<header class="header"><h1>Charge schedule</h1><p>Baseline periods — Fox Plant keeps the inverter in sync</p></header>
${this._renderPeriodCard(0, this._chargeDraft[0])}
${this._renderPeriodCard(1, this._chargeDraft[1])}
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="save-schedules" ${this._busy ? "disabled" : ""}>Save & apply</button>
<button type="button" class="btn btn-secondary" data-action="apply-baseline" ${this._busy ? "disabled" : ""}>Re-apply only</button>
<button type="button" class="btn btn-secondary" data-action="copy-period" data-from="0" data-to="1" ${this._busy ? "disabled" : ""}>Copy period 1 → 2</button>
<button type="button" class="btn btn-secondary" data-action="swap-periods" ${this._busy ? "disabled" : ""}>Swap 1 ↔ 2</button>
</div>`;
  }

  _renderSettingsWorkMode() {
    if (!this._workModeDraft) this._initWorkModeDraft();
    const options = this._plantState?.settings?.work_mode_options ?? [];
    if (!options.length) {
      return `<header class="header"><h1>Work mode</h1></header><p class="placeholder">Work mode entity not found. Reload the integration.</p>`;
    }
    return `<header class="header"><h1>Work mode</h1><p>Matches the FoxESS inverter modes</p></header>
<div class="mode-grid">${options
      .map((opt) => {
        const sel = opt === this._workModeDraft ? "selected" : "";
        const hint = WORK_MODE_HINTS[opt] || "";
        return `<button type="button" class="mode-option ${sel}" data-action="pick-work-mode" data-mode="${esc(opt)}">
<span class="name">${esc(opt)}</span>${hint ? `<span class="hint">${esc(hint)}</span>` : ""}</button>`;
      })
      .join("")}</div>
<div class="btn-row" style="margin-top:16px"><button type="button" class="btn btn-primary" data-action="save-work-mode" ${this._busy ? "disabled" : ""}>Apply work mode</button></div>`;
  }

  _renderSettingsStorm() {
    if (!this._stormDraft) this._initStormDraft();
    const draft = this._stormDraft;
    const triggersArmed = Boolean(this._plantState?.active_storm_triggers?.length);
    const overrideArmed =
      Boolean(this._plantState?.override_active) && String(this._plantState?.mode ?? "") === "storm";
    const armed = triggersArmed || overrideArmed;
    const activeTriggers = this._plantState?.active_storm_triggers ?? [];
    const maxSocVal = draft.target_max_soc == null ? "" : String(draft.target_max_soc);
    return `${this._renderStormHero(armed)}
<header class="header storm-settings-header"><h1>StormSafe</h1><p>Pre-charge before severe weather — configured here, no blueprints required</p></header>
<div class="card">
<p class="card-title">Status</p>
<p style="margin:0 0 10px;font-size:14px">${armed ? "Storm prep is <strong>active</strong> — storm charge schedule applied." : "No storm triggers active right now."}</p>
${activeTriggers.length ? `<div>${activeTriggers.map((t) => `<span class="trigger-chip">${esc(t)}</span>`).join("")}</div>` : ""}
<div class="btn-row" style="margin-top:12px">
<button type="button" class="btn btn-primary" data-action="arm-storm" ${this._busy ? "disabled" : ""}>Test arm</button>
<button type="button" class="btn btn-secondary" data-action="disarm-storm" ${this._busy ? "disabled" : ""}>Disarm override</button>
</div>
</div>
<div class="card">
<div class="toggle-row"><span><strong>Enable StormSafe</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Arms when Google Weather reports a storm-type condition (or alert binaries turn on)</span></span>
<input type="checkbox" data-action="toggle-storm-enabled" ${draft.enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
</div>
${this._renderGoogleWeatherSource()}
<div class="card">
<p class="card-title">Pre-charge timing</p>
<div class="toggle-row"><span><strong>Forecast pre-charge</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Start storm schedule when Google hourly forecast shows severe weather within the lead time</span></span>
<input type="checkbox" data-field="toggle-storm-forecast" ${draft.use_forecast_lead ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="field" style="margin-top:10px"><label>Lead time (hours before forecast storm)</label>
<input type="number" min="1" max="48" step="1" data-field="storm-lead-hours" value="${esc(String(draft.forecast_lead_hours ?? 4))}" ${!draft.use_forecast_lead || this._busy ? "disabled" : ""}></div>
</div>
${this._renderStormAdvancedTriggers()}
<div class="card">
<p class="card-title">Storm charge schedule</p>
<p class="storm-hint">Applied while a trigger is active (separate from your baseline schedule).</p>
${this._renderPeriodCard(0, draft.charge_periods[0], "storm-period", "Storm period")}
${this._renderPeriodCard(1, draft.charge_periods[1], "storm-period", "Storm period")}
</div>
<div class="card">
<p class="card-title">Optional max SoC during storm</p>
<div class="field"><label>Target max % (leave empty to keep current max)</label>
<input type="number" min="10" max="100" step="1" data-field="storm-max-soc" value="${esc(maxSocVal)}" placeholder="e.g. 100"></div>
</div>
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="save-storm-prep" ${this._busy ? "disabled" : ""}>Save StormSafe settings</button>
</div>`;
  }

  _renderSettingsCharts() {
    if (!this._chartsDraft) this._initChartsDraft();
    const selected = this._chartsDraft.forecast_entity_id || "";
    const candidates = this._forecastCandidates ?? [];
    const options = [
      `<option value="">— None —</option>`,
      ...candidates.map((e) => {
        const unit = e.unit ? ` (${e.unit})` : "";
        const mark = e.suggested ? " ★" : "";
        return `<option value="${esc(e.entity_id)}" ${e.entity_id === selected ? "selected" : ""}>${esc(e.name)}${esc(unit)}${mark}</option>`;
      }),
    ];
    const current = selected
      ? stateString(this._hass, selected) + entityUnit(this._hass, selected)
      : "—";
    return `<header class="header"><h1>Charts</h1><p>Statistics graph and Energy → Day overlay</p></header>
<div class="card">
<p class="card-title">PV forecast line</p>
<p class="charts-entity-hint">Choose a power forecast sensor (e.g. Solcast). Values in <strong>W</strong> are converted to kW automatically; sensors already in <strong>kW</strong> are used as-is.</p>
<label class="charts-entity-hint" for="fp-forecast-entity">Forecast entity</label>
<select id="fp-forecast-entity" class="charts-entity-select" data-action="pick-forecast-entity" aria-label="Forecast entity">${options.join("")}</select>
<p class="charts-entity-hint">Current reading: <strong>${esc(current)}</strong></p>
<div class="btn-row"><button type="button" class="btn btn-primary" data-action="save-charts-settings" ${this._busy ? "disabled" : ""}>Save</button></div>
</div>`;
  }

  _renderSettingsControl() {
    const active = this._plantState?.control_active;
    return `<header class="header"><h1>Plant control</h1></header>
<div class="card">
<p style="margin:0 0 12px;line-height:1.5;font-size:14px">When <strong>active</strong>, Fox Plant is the only writer for charge periods (via <code>foxess_modbus</code>). Release control if you need to edit schedules in the Fox app temporarily.</p>
<div class="btn-row">
${active
      ? `<button type="button" class="btn btn-danger" data-action="release-control" ${this._busy ? "disabled" : ""}>Release control</button>`
      : `<button type="button" class="btn btn-primary" data-action="take-control" ${this._busy ? "disabled" : ""}>Take control</button>`}
<button type="button" class="btn btn-secondary" data-action="apply-baseline" ${this._busy ? "disabled" : ""}>Apply baseline now</button>
</div></div>`;
  }

  _renderSettings(plant) {
    switch (this._settingsView) {
      case "quick":
        return this._renderSettingsQuick();
      case "schedules":
        return this._renderSettingsSchedules();
      case "workmode":
        return this._renderSettingsWorkMode();
      case "storm":
        return this._renderSettingsStorm();
      case "charts":
        return this._renderSettingsCharts();
      case "control":
        return this._renderSettingsControl();
      default:
        return this._renderSettingsMain(plant);
    }
  }

  _renderView(plant) {
    switch (this._view) {
      case "overview":
        return this._renderOverview(plant);
      case "device":
        return this._renderDevice(plant);
      case "energy":
        return this._renderEnergy();
      case "settings":
        return this._renderSettings(plant);
      default:
        return "";
    }
  }

  _render() {
    try {
      this._renderPanel();
    } catch (err) {
      console.error("FoxESS Plant panel render failed", err);
      this._root.innerHTML = `<div class="main"><p class="placeholder">Fox Plant panel error: ${esc(err?.message || String(err))}</p></div>`;
    }
  }

  _renderPanel() {
    if (!this._hass) {
      this._headerHasSubTabs = undefined;
      this._root.innerHTML = `<div class="main"><p class="placeholder">Loading Fox Plant…</p></div>`;
      return;
    }
    const plant = this._getPlant();
    if (!plant) {
      this._headerHasSubTabs = undefined;
      this._root.innerHTML = `<div class="main"><p class="placeholder">Add FoxESS Plant and select your inverter device.</p></div>`;
      return;
    }

    const showSubTabs = this._view === "settings";
    let shell = this._root.querySelector(".shell");
    if (!shell) {
      shell = document.createElement("div");
      shell.className = `shell${this._narrow ? " narrow" : ""}`;
      shell.append(
        Object.assign(document.createElement("header"), { className: "page-header" }),
        Object.assign(document.createElement("main"), { className: "main" })
      );
      this._root.replaceChildren(shell);
      this._headerHasSubTabs = undefined;
    } else {
      shell.classList.toggle("narrow", this._narrow);
    }

    const headerEl = shell.querySelector(".page-header");
    if (this._headerHasSubTabs !== showSubTabs) {
      this._rebuildPageHeader(headerEl);
    } else {
      this._syncTabActive(headerEl);
    }

    shell.querySelector(".main").innerHTML = this._renderView(plant);

    if (this._view === "settings" && this._settingsView === "quick") {
      this._bindTripleSoc();
    }
    if (this._view === "settings" && this._settingsView === "storm" && this._stormDraft) {
      this._syncStormTriggerPicker();
    }
    if (
      (this._view === "overview" || (this._view === "energy" && this._energyPeriod === "day")) &&
      this._statisticsChart?.series
    ) {
      this._bindStatisticsChart();
    }
    if (this._view === "energy") {
      const plant = this._getPlant();
      if (!plant) return;
      if (this._energyPeriod === "day") {
        if (
          !this._statisticsChartLoading &&
          (this._statisticsChartPlantId !== plant.entry_id || !this._statisticsChart)
        ) {
          this._loadStatisticsChart();
        }
      } else if (
        !this._energyChartLoading &&
        (this._energyChartPlantId !== plant.entry_id || !this._energyChart)
      ) {
        this._loadEnergyCharts();
      }
    }
    if (this._view === "overview") {
      const plant = this._getPlant();
      if (
        plant &&
        !this._statisticsChartLoading &&
        (this._statisticsChartPlantId !== plant.entry_id || !this._statisticsChart)
      ) {
        this._loadStatisticsChart();
      }
    }
  }
}

registerFoxessPlantPanel();
