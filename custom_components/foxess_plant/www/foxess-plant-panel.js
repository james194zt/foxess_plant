/**
 * FoxESS Plant panel — HA sidebar app (phases 5a–5e).
 * hass / narrow / panel / route from Home Assistant.
 * @version 0.8.1
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

const FLOW_PATHS = {
  "solar-home": "M 118 88 C 160 88, 175 115, 200 130",
  "grid-home": "M 382 88 C 340 88, 320 115, 295 130",
  "home-grid": "M 295 130 C 320 115, 340 88, 382 88",
  "battery-home": "M 250 228 C 250 195, 250 175, 250 155",
  "home-battery": "M 250 155 C 250 175, 250 195, 250 228",
};

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

function stateNumber(hass, entityId) {
  if (!entityId || !hass?.states) return 0;
  const st = hass.states[entityId];
  if (!st || st.state === "unavailable" || st.state === "unknown") return 0;
  const n = parseFloat(st.state);
  return Number.isFinite(n) ? n : 0;
}

function stateString(hass, entityId) {
  if (!entityId || !hass?.states) return "—";
  const st = hass.states[entityId];
  return st ? st.state : "—";
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
    return `<svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="${cx}" cy="${cy}" r="${(rOuter + rInner) / 2}" fill="none" stroke="${FOX_ENERGY.muted}" stroke-width="${rOuter - rInner}" opacity="0.35"/></svg>`;
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
  return `<svg viewBox="0 0 100 100" aria-hidden="true">${paths.join("")}</svg>`;
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

/** Matches dashboard Statistics plotly-graph series. */
const STATISTICS_CHART_SERIES = [
  { key: "pv_power", label: "Solar", color: "#19D4DE", toKw: true, fill: true },
  { key: "battery_charge", label: "Battery charge", color: "#8DB6FF", toKw: true, negate: true, fill: true },
  {
    key: "battery_discharge",
    label: "Battery discharge",
    color: "#8DB6FF",
    toKw: true,
    fill: true,
    hideLegend: true,
  },
  { key: "grid_import", label: "Grid import", color: "#FF6FAF", toKw: true, abs: true, fill: true },
  {
    key: "grid_export",
    label: "Grid export",
    color: "#FF6FAF",
    toKw: true,
    abs: true,
    negate: true,
    dash: true,
    hideLegend: true,
  },
  { key: "load_power", label: "Load", color: "#8A4DFF", toKw: true, negate: true, fill: true },
];

const FORECAST_CHART_STYLE = { label: "Forecast", color: "#FFD700", fill: true };

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

async function fetchHistoryDuring(hass, entityIds, start, end) {
  const ids = entityIds.filter(Boolean);
  if (!ids.length) return [];
  return hass.connection.sendMessagePromise({
    type: "history/history_during_period",
    start_time: start.toISOString(),
    end_time: end.toISOString(),
    entity_ids: ids,
    minimal_response: true,
    significant_changes_only: false,
    no_attributes: true,
  });
}

function historyToPoints(rows) {
  if (!rows?.length) return [];
  return rows
    .map((row) => {
      const t = new Date(row.lu || row.last_changed);
      const v = parseFloat(row.s);
      if (!Number.isFinite(v)) return null;
      return { t: t.getTime(), v };
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t);
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
  return Math.max(0, x);
}

function dailyMaxInRange(points, dayStartMs, dayEndMs) {
  let max = 0;
  for (const p of points) {
    if (p.t >= dayStartMs && p.t <= dayEndMs) max = Math.max(max, p.v);
  }
  return max;
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

function renderLineChartSvg(series, { height = 220, yLabel = "kW", title = "Statistics" } = {}) {
  const visible = series.filter((s) => s.points?.length);
  const all = visible.flatMap((s) => s.points);
  if (!all.length) return `<p class="placeholder chart-empty">No power history for today yet.</p>`;
  const width = 400;
  const pad = { l: 44, r: 14, t: 28, b: 32 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const tMin = all[0].t;
  const tMax = all[all.length - 1].t;
  const tSpan = Math.max(tMax - tMin, 60000);
  let yMax = 0.25;
  for (const p of all) yMax = Math.max(yMax, Math.max(0, p.v));
  yMax *= 1.12;
  const yTicks = [0, yMax * 0.5, yMax];
  const xTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => tMin + tSpan * f);

  const xy = (p) => ({
    x: pad.l + ((p.t - tMin) / tSpan) * w,
    y: pad.t + h - (Math.max(0, p.v) / yMax) * h,
  });

  const fills = visible
    .filter((s) => s.fill)
    .map((s) => {
      if (!s.points.length) return "";
      const pts = s.points.map((p) => xy(p));
      const d =
        `M${pts[0].x.toFixed(1)},${(pad.t + h).toFixed(1)} ` +
        pts.map((p) => `L${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ") +
        ` L${pts[pts.length - 1].x.toFixed(1)},${(pad.t + h).toFixed(1)} Z`;
      const fillColor = s.color === "#19D4DE" ? "rgba(25,212,222,0.16)" : s.color === "#8A4DFF" ? "rgba(138,77,255,0.14)" : s.color === "#FF6FAF" ? "rgba(255,111,175,0.14)" : s.color === "#8DB6FF" ? "rgba(141,182,255,0.14)" : s.color === "#FFD700" ? "rgba(255,215,0,0.14)" : "rgba(127,127,127,0.12)";
      return `<path d="${d}" fill="${fillColor}" stroke="none"/>`;
    })
    .join("");

  const paths = visible
    .map((s) => {
      const d = s.points
        .map((p, i) => {
          const { x, y } = xy(p);
          return `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
      return `<path class="energy-line" d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.dash ? "1.2" : "1.4"}" stroke-dasharray="${s.dash ? "5 3" : "none"}" opacity="${s.dash ? 0.9 : 1}"/>`;
    })
    .join("");

  const grid = yTicks
    .map((yv) => {
      const y = pad.t + h - (yv / yMax) * h;
      return `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${pad.l + w}" y2="${y.toFixed(1)}" class="chart-grid"/>`;
    })
    .join("");
  const yLabels = yTicks
    .map((yv) => {
      const y = pad.t + h - (yv / yMax) * h;
      return `<text x="${pad.l - 6}" y="${(y + 4).toFixed(1)}" text-anchor="end" class="chart-axis">${yv.toFixed(1)}</text>`;
    })
    .join("");
  const xLabels = xTicks
    .map((xt) => {
      const x = pad.l + ((xt - tMin) / tSpan) * w;
      return `<text x="${x.toFixed(1)}" y="${height - 8}" text-anchor="middle" class="chart-axis">${esc(formatChartTimeLabel(xt))}</text>`;
    })
    .join("");
  const legend = visible
    .filter((s) => !s.hideLegend)
    .map(
      (s) =>
        `<span class="chart-legend-item"><i style="background:${s.color}"></i>${esc(s.label)}</span>`
    )
    .join("");
  return `<div class="chart-wrap statistics-chart-wrap"><div class="chart-heading">${esc(title)}</div><svg class="energy-line-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><text x="${pad.l}" y="16" class="chart-axis chart-title-inline">${esc(title)}</text>${grid}${fills}${paths}${yLabels}${xLabels}</svg><div class="chart-legend">${legend}</div><div class="chart-y-title">${esc(yLabel)}</div></div>`;
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

function readEnergyFlows(hass, plant) {
  const map = plant.entity_map || {};
  const pvW = stateNumber(hass, map.pv_power);
  const loadW = Math.abs(stateNumber(hass, map.load_power));
  const gridImportW = stateNumber(hass, map.grid_import);
  const gridExportW = stateNumber(hass, map.grid_export);
  const batteryW = stateNumber(hass, map.battery_power);
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

function computeFlowLines(flows, threshold = 40) {
  const lines = [];
  if (flows.pvW > threshold) lines.push({ id: "solar-home", label: formatW(flows.pvW) });
  if (flows.gridImportW > threshold) lines.push({ id: "grid-home", label: formatW(flows.gridImportW) });
  if (flows.gridExportW > threshold) lines.push({ id: "home-grid", reverse: true, label: formatW(flows.gridExportW) });
  if (flows.batteryW > threshold) lines.push({ id: "battery-home", label: formatW(flows.batteryW) });
  else if (flows.batteryW < -threshold) lines.push({ id: "home-battery", label: formatW(Math.abs(flows.batteryW)) });
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
}
.shell.narrow .main { padding: 16px; }
.shell.narrow .tab { padding: 12px 14px 10px; font-size: 13px; }
.header { margin-bottom: 20px; }
.header h1 { margin: 0; font-size: 26px; font-weight: 600; letter-spacing: -0.02em; }
.header p { margin: 6px 0 0; color: var(--secondary-text-color); font-size: 14px; }
.back-btn { background: none; border: none; color: var(--fp-accent); cursor: pointer; font-size: 14px; padding: 0 0 14px; font-family: inherit; }
.card {
  background: var(--card-background-color); border-radius: var(--fp-radius);
  padding: 18px 20px; margin-bottom: 14px;
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.08));
  border: 1px solid var(--divider-color, transparent);
}
.card-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--secondary-text-color); margin: 0 0 14px; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); gap: 12px; }
.breakdown-card { margin-top: 14px; padding-bottom: 8px; }
.fox-energy-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  align-items: stretch;
}
.fox-energy-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) min(46%, 118px);
  gap: 6px 10px;
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
.fox-energy-chart { position: relative; width: 100%; aspect-ratio: 1; max-width: 118px; margin-left: auto; }
.fox-energy-chart svg { width: 100%; height: 100%; display: block; }
.fox-energy-chart-center {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; text-align: center; pointer-events: none; padding: 6px;
}
.fox-energy-chart-pct { font-size: 24px; font-weight: 700; line-height: 1; letter-spacing: -0.03em; }
.fox-energy-chart-label { font-size: 10px; color: var(--secondary-text-color); margin-top: 4px; line-height: 1.2; max-width: 80px; }
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
.energy-line-chart, .energy-bar-chart { width: 100%; height: 220px; display: block; }
.statistics-chart-wrap .energy-line-chart { height: 260px; }
.chart-heading { font-size: 15px; font-weight: 600; margin-bottom: 8px; color: var(--primary-text-color); }
.chart-title-inline { font-size: 11px; font-weight: 600; fill: var(--secondary-text-color); }
.charts-entity-select {
  width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px;
  border: 1px solid var(--divider-color); background: var(--card-background-color);
  color: inherit; font-family: inherit; font-size: 14px; margin-bottom: 10px;
}
.charts-entity-hint { font-size: 12px; color: var(--secondary-text-color); line-height: 1.45; margin: 0 0 12px; }
.chart-grid { stroke: rgba(127,127,127,0.15); stroke-width: 1; }
.chart-axis { fill: var(--secondary-text-color); font-size: 9px; font-family: inherit; }
.chart-y-title {
  position: absolute; left: 0; top: 50%; transform: translateY(-50%) rotate(-90deg);
  font-size: 10px; color: var(--secondary-text-color); letter-spacing: 0.04em;
}
.chart-legend {
  display: flex; flex-wrap: wrap; gap: 10px 14px; margin-top: 10px; font-size: 12px; color: var(--secondary-text-color);
}
.chart-legend-item { display: inline-flex; align-items: center; gap: 6px; }
.chart-legend-item i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.chart-empty { margin: 24px 0; text-align: center; }
.chart-loading { margin: 24px 0; text-align: center; color: var(--secondary-text-color); font-size: 13px; }
@media (max-width: 560px) {
  .fox-energy-panel { grid-template-columns: 1fr; }
  .fox-energy-row {
    grid-template-columns: minmax(0, 1fr) min(40vw, 132px);
    padding: 14px 0 6px;
  }
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
  background: var(--card-background-color); color: inherit; font-size: 15px;
  cursor: pointer; text-align: left; font-family: inherit; margin-bottom: 8px;
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06));
  border: 1px solid var(--divider-color, transparent);
}
.list-btn:hover { background: var(--secondary-background-color); }
.list-btn .chev { opacity: 0.4; font-size: 18px; }
.list-btn .sub { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }
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
.scene-card svg { width: 100%; height: auto; display: block; max-height: 280px; }
.node-label { font-size: 11px; fill: var(--secondary-text-color); font-family: inherit; }
.node-value { font-size: 13px; font-weight: 600; fill: var(--primary-text-color); font-family: inherit; }
.flow-path { fill: none; stroke-width: 3; stroke-linecap: round; opacity: 0.2; }
.flow-path.active { opacity: 1; stroke-dasharray: 8 10; animation: flow 1.2s linear infinite; }
.flow-path.reverse { animation-direction: reverse; }
.flow-solar.active { stroke: #f4b400; } .flow-grid.active { stroke: #4285f4; }
.flow-export.active { stroke: #9c27b0; } .flow-battery.active { stroke: #0f9d58; }
.flow-label { font-size: 10px; fill: var(--primary-text-color); font-family: inherit; }
@keyframes flow { to { stroke-dashoffset: -36; } }
.house-body { fill: var(--divider-color); stroke: var(--fp-accent); stroke-width: 2; }
.house-roof { fill: var(--fp-accent); opacity: 0.85; }
.soc-ring-bg { fill: none; stroke: var(--divider-color); stroke-width: 6; }
.soc-ring { fill: none; stroke: #0f9d58; stroke-width: 6; stroke-linecap: round; transform: rotate(-90deg); transform-origin: 250px 248px; }
.device-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.device-card { background: var(--card-background-color); border-radius: var(--fp-radius); padding: 18px; border: 1px solid var(--divider-color, transparent); min-height: 150px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.gauge { width: 108px; height: 108px; position: relative; }
.gauge svg { width: 100%; height: 100%; }
.gauge-value { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; font-weight: 700; font-size: 20px; }
.gauge-label { font-size: 11px; color: var(--secondary-text-color); font-weight: 400; }
.battery-pct { font-size: 40px; font-weight: 700; line-height: 1; }
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
.hero { border-radius: var(--fp-radius); overflow: hidden; background: linear-gradient(180deg, #1a2332 0%, var(--card-background-color) 100%); margin-bottom: 14px; border: 1px solid var(--divider-color); }
.hero svg { width: 100%; height: auto; display: block; }
.hero-caption { padding: 12px 16px; font-size: 13px; color: var(--secondary-text-color); line-height: 1.45; border-top: 1px solid var(--divider-color); }
.prepared { opacity: 1; } .unprepared { opacity: 0.35; }
.hero.armed .unprepared { opacity: 0.2; } .hero:not(.armed) .prepared { opacity: 0.45; }
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
@media (max-width: 600px) { .device-grid { grid-template-columns: 1fr; } .scene-card svg { max-height: 220px; } }
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

  _modeBanner() {
    const st = this._plantState;
    if (!st) return "";
    const mode = st.mode ?? "baseline";
    const pills = `<span class="mode-pill ${modeClass(mode)}">${esc(mode)}</span>`;
    let extra = "";
    if (st.drift) {
      extra = `<div class="banner warn"><strong>Schedule drift</strong>Inverter charge windows differ from what Fox Plant expects. <div class="btn-row"><button type="button" class="btn btn-primary" data-action="apply-baseline" ${this._busy ? "disabled" : ""}>Re-apply schedule</button></div></div>`;
    } else if (!st.control_active) {
      extra = `<div class="banner info"><strong>Manual control</strong>Fox Plant is not managing charge periods. Modbus or the Fox app may change settings freely.</div>`;
    }
    return `<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap">${pills}<span style="font-size:13px;color:var(--secondary-text-color)">${st.control_active ? "Plant control active" : "Plant control off"}</span></div>${extra}`;
  }

  _renderEnergyScene(plant) {
    const flows = readEnergyFlows(this._hass, plant);
    const lines = computeFlowLines(flows);
    const activeIds = new Set(lines.map((l) => l.id));
    const soc = Math.min(100, Math.max(0, flows.batterySoc));
    const circumference = 2 * Math.PI * 28;
    const socOffset = circumference * (1 - soc / 100);
    const gridVal =
      flows.gridExportW > flows.gridImportW
        ? formatKw(flows.gridExportW, 2)
        : formatKw(flows.gridImportW, 2);
    const pathsHtml = Object.entries(FLOW_PATHS)
      .map(([id, d]) => {
        const line = lines.find((l) => l.id === id);
        const cls = id.includes("solar")
          ? "flow-solar"
          : id.includes("grid") && id !== "home-grid"
            ? "flow-grid"
            : id === "home-grid"
              ? "flow-export"
              : "flow-battery";
        const labelY = id.includes("battery") ? 200 : 108;
        const label = line?.label
          ? `<text class="flow-label" x="250" y="${labelY}" text-anchor="middle">${esc(line.label)}</text>`
          : "";
        return `<path class="flow-path ${cls} ${activeIds.has(id) ? "active" : ""} ${line?.reverse ? "reverse" : ""}" d="${d}"></path>${label}`;
      })
      .join("");
    return `<div class="scene-card"><div class="scene-title">Live energy flow</div>
<svg viewBox="0 0 500 290" role="img" aria-label="Energy flow">
${pathsHtml}
<g transform="translate(70,48)"><rect x="0" y="18" width="48" height="32" rx="4" fill="#f4b400" opacity="0.25" stroke="#f4b400"/><text class="node-label" x="24" y="12" text-anchor="middle">Solar</text><text class="node-value" x="24" y="68" text-anchor="middle">${esc(formatKw(flows.pvW, 2))}</text></g>
<g transform="translate(382,48)"><path d="M0 50 L0 20 L12 20 L12 8 L24 8 L24 20 L36 20 L36 50 Z" fill="#4285f4" opacity="0.3" stroke="#4285f4"/><text class="node-label" x="18" y="0" text-anchor="middle">Grid</text><text class="node-value" x="18" y="68" text-anchor="middle">${esc(gridVal)}</text></g>
<g transform="translate(200,108)"><polygon class="house-roof" points="50,0 100,35 0,35"/><rect class="house-body" x="8" y="35" width="84" height="55" rx="4"/><text class="node-label" x="50" y="-8" text-anchor="middle">Home</text><text class="node-value" x="50" y="108" text-anchor="middle">${esc(formatKw(flows.loadW, 2))}</text></g>
<g transform="translate(222,220)"><circle class="soc-ring-bg" cx="28" cy="28" r="28"/><circle class="soc-ring" cx="28" cy="28" r="28" stroke-dasharray="${circumference}" stroke-dashoffset="${socOffset}"/><text class="node-value" x="28" y="34" text-anchor="middle" font-size="11">${esc(formatPercent(soc))}</text><text class="node-label" x="28" y="-4" text-anchor="middle">Battery</text><text class="node-value" x="28" y="72" text-anchor="middle" font-size="11">${esc(flows.batteryStatus)}</text></g>
</svg></div>`;
  }

  _renderStormHero(armed) {
    return `<div class="hero ${armed ? "armed" : ""}"><svg viewBox="0 0 400 140" aria-hidden="true">
<g class="unprepared" transform="translate(210,20)"><rect x="30" y="40" width="70" height="50" rx="4" fill="#333"/><polygon points="65,20 110,45 20,45" fill="#444"/><rect x="95" y="70" width="28" height="40" rx="4" fill="#333" stroke="#c62828" stroke-width="2"/></g>
<g class="prepared" transform="translate(20,20)"><rect x="30" y="40" width="70" height="50" rx="4" fill="#455a64"/><polygon points="65,20 110,45 20,45" fill="#546e7a"/><rect x="5" y="70" width="28" height="40" rx="4" fill="#2e7d32" stroke="#66bb6a" stroke-width="2"/></g>
<g transform="translate(155,8)"><ellipse cx="45" cy="28" rx="50" ry="22" fill="#37474f"/><path d="M55 48 L48 62 L54 62 L46 78 L58 58 L52 58 Z" fill="#ffeb3b"/></g>
</svg><div class="hero-caption">Pre-charges the battery before severe weather using your storm prep schedule.</div></div>`;
  }

  _stat(label, value, suffix = "") {
    const has = value != null && value !== "—";
    return `<div class="stat"><label>${esc(label)}</label><strong>${has ? esc(String(value)) + esc(suffix) : "—"}</strong></div>`;
  }

  _renderOverview(plant) {
    const a = this._plantState?.analytics ?? {};
    return `<header class="header"><h1>${esc(plant.title)}</h1><p>${esc(plant.inverter)}</p></header>
${this._modeBanner()}
${this._renderEnergyScene(plant)}
<div class="stats-row" style="margin-top:14px">
${this._stat("Self-consumption", a.self_consumption_percent_today, a.self_consumption_percent_today != null ? "%" : "")}
${this._stat("Self-sufficiency", a.self_sufficiency_percent_today, a.self_sufficiency_percent_today != null ? "%" : "")}
${this._stat("PV today", a.pv_production_kwh_today, a.pv_production_kwh_today != null ? " kWh" : "")}
</div>
<div class="card statistics-card" style="margin-top:14px">
<p class="card-title">Statistics</p>
${this._renderStatisticsChartBody()}
</div>`;
  }

  _identityRows() {
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
        const value = id[key];
        if (value == null || value === "" || value === "unavailable" || value === "unknown") return null;
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
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>System info</h1><p>From Modbus (matches Fox app where confirmed)</p></header>${this._identityValueList(this._identityRows())}`;
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
    const flows = readEnergyFlows(this._hass, plant);
    const pvKw = flows.pvW / 1000;
    const circ = 2 * Math.PI * 40;
    const off = circ * (1 - Math.min(100, (pvKw / 5) * 100) / 100);
    const temp = stateString(this._hass, plant.entity_map?.bms_temp_low);
    return `<header class="header"><h1>Device</h1></header>${this._modeBanner()}
<div class="device-grid">
<div class="device-card"><div class="gauge"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="var(--divider-color)" stroke-width="8"/><circle cx="50" cy="50" r="40" fill="none" stroke="var(--fp-accent)" stroke-width="8" stroke-dasharray="${circ}" stroke-dashoffset="${off}" transform="rotate(-90 50 50)" stroke-linecap="round"/></svg><div class="gauge-value"><span>${pvKw.toFixed(2)}</span><span class="gauge-label">kW PV</span></div></div></div>
<div class="device-card"><div class="battery-pct">${esc(formatPercent(flows.batterySoc))}</div><div style="font-size:13px;color:var(--secondary-text-color);margin-top:8px">${esc(flows.batteryStatus)} · ${esc(formatKw(Math.abs(flows.batteryW), 2))}</div><div style="font-size:12px;margin-top:6px;color:var(--secondary-text-color)">Min temp ${esc(temp !== "—" ? temp + "°C" : "—")}</div></div>
</div>
<button type="button" class="list-btn" data-action="device-sub" data-sub="system"><span>System info<span class="sub">PCS model/serial, firmware, BMS</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="device-sub" data-sub="parameters"><span>Detailed parameters<span class="sub">Live Modbus values</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="device-sub" data-sub="battery"><span>Battery<span class="sub">SOC, power, temperature</span></span><span class="chev">›</span></button>`;
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
    const map = plant.entity_map || {};
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
      const svg = await this._fetchStatisticsChartSvg(plant);
      this._statisticsChart = { svg };
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

  async _fetchStatisticsChartSvg(plant) {
    const map = plant.entity_map || {};
    const specs = STATISTICS_CHART_SERIES.map((s) => ({ ...s, entity_id: map[s.key] })).filter(
      (s) => s.entity_id
    );
    if (!specs.length) {
      return `<p class="placeholder chart-empty">Map power entities in FoxESS Modbus, then reload FoxESS Plant.</p>`;
    }
    const forecastId = this._plantState?.panel_display?.forecast_entity_id || null;
    const entityIds = specs.map((s) => s.entity_id);
    if (forecastId) entityIds.push(forecastId);
    const now = new Date();
    const start = startOfLocalDay(now);
    const hist = await fetchHistoryDuring(this._hass, entityIds, start, now);
    const series = specs.map((spec, idx) => ({
      label: spec.label,
      color: spec.color,
      dash: spec.dash,
      fill: spec.fill,
      hideLegend: spec.hideLegend,
      points: historyToPoints(hist[idx]).map((p) => ({
        t: p.t,
        v: transformHistoryPoint(this._hass, spec.entity_id, p.v, spec),
      })),
    }));
    if (forecastId) {
      const fIdx = entityIds.indexOf(forecastId);
      const fPoints = historyToPoints(hist[fIdx]).map((p) => ({
        t: p.t,
        v: transformHistoryPoint(this._hass, forecastId, p.v, { toKw: true }),
      }));
      if (fPoints.length) {
        series.push({
          ...FORECAST_CHART_STYLE,
          points: fPoints,
        });
      }
    }
    return renderLineChartSvg(series, { height: 260, title: "Statistics" });
  }

  _renderStatisticsChartBody() {
    if (this._statisticsChartLoading) {
      return `<p class="chart-loading">Loading statistics…</p>`;
    }
    if (this._statisticsChart?.error) {
      return `<p class="placeholder chart-empty">${esc(this._statisticsChart.error)}</p>`;
    }
    if (this._statisticsChart?.svg) return this._statisticsChart.svg;
    return `<p class="placeholder chart-empty">Open Energy or wait for history to load.</p>`;
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
    const idx = {
      pv: ids.indexOf(ent.pv),
      load: ids.indexOf(ent.load),
      discharge: ids.indexOf(ent.discharge),
      charge: ids.indexOf(ent.charge),
      grid: ids.indexOf(ent.grid),
    };
    const points = {
      pv: historyToPoints(hist[idx.pv]),
      load: historyToPoints(hist[idx.load]),
      discharge: historyToPoints(hist[idx.discharge]),
      charge: historyToPoints(hist[idx.charge]),
      grid: historyToPoints(hist[idx.grid]),
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
<button type="button" class="list-btn" data-action="settings-sub" data-sub="quick"><span>Quick Settings<span class="sub">Max ${s.max_soc ?? "—"}% · Min ${s.min_soc ?? "—"}% · Off-grid ${s.min_soc_on_grid ?? "—"}%</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="schedules"><span>Charge schedule<span class="sub">Two charge windows (baseline)</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="workmode"><span>Work mode<span class="sub">${esc(s.work_mode ?? "—")}</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="storm"><span>StormSafe<span class="sub">${stormSub}</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="charts"><span>Charts<span class="sub">${esc(this._forecastEntityLabel())}</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="control"><span>Plant control<span class="sub">${this._plantState?.control_active ? "Fox Plant manages periods" : "Released to manual"}</span></span><span class="chev">›</span></button>`;
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
    return `<header class="header"><h1>StormSafe</h1><p>Pre-charge before severe weather — configured here, no blueprints required</p></header>
${this._renderStormHero(armed)}
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

customElements.define("foxess-plant-panel", FoxessPlantPanel);
