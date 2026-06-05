/**
 * FoxESS Plant panel — HA sidebar app (phases 5a–5e).
 * hass / narrow / panel / route from Home Assistant.
 * @version 0.9.53
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
  { id: "pv", label: "PV" },
  { id: "solcast", label: "Solcast" },
  { id: "storm", label: "StormSafe" },
  { id: "control", label: "Control" },
];

const DEFAULT_PV_STRING = {
  enabled: true,
  panel_count: 6,
  watts_per_panel: 450,
  efficiency_factor: 100,
  tilt: 25,
  azimuth: 180,
};

const DEFAULT_PV_CONFIG = {
  pv1: { ...DEFAULT_PV_STRING },
  pv2: {
    enabled: false,
    panel_count: 1,
    watts_per_panel: 450,
    efficiency_factor: 100,
    tilt: 25,
    azimuth: 180,
  },
};

const PV_EFFICIENCY_FACTOR_URL = "https://kb.solcast.com.au/what-is-the-efficiency-factor";
const SOLCAST_API_DOCS_URL = "https://docs.solcast.com.au/";
const SOLCAST_HOBBYIST_URL = "https://solcast.com/free-rooftop-solar-forecasting";
const SOLCAST_ACCOUNT_LOCATIONS_URL = "https://toolkit.solcast.com.au/account/locations";
const SOLCAST_COORD_DECIMALS = 4;

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

const FLOW_PATHS_VER = "flow-comet-v3";
const PANEL_VERSION = "0.9.39";
const PANEL_BUILD_FALLBACK = PANEL_VERSION;
const PANEL_SYNC_STORAGE_KEY = "foxess_plant_panel_sync_build";

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
const FLOW_STROKE = { base: 3, underlay: 4, active: 5, hubActive: 6, hubR: 6.5 };
/** Idle pipe track — darker on day (white walls), lighter on night (black scene). */
const FLOW_PIPE_STROKE = { day: "#5E6A78", night: "#9AA8B8" };
/** Pale underlay beneath animated hub spokes so dashes do not sit on dark gaps. */
const FLOW_PIPE_UNDERLAY = { day: "#EEF1F5", night: "#9AA4B0" };
/** Active flow colours — inline on SVG paths for reliable rendering in HA shadow DOM. */
const FLOW_ACTIVE_STROKE = {
  solar: "#FFC400",
  grid: "#3D9AFF",
  export: "#C06AFF",
  battery: "#00FF66",
  home: "#00FF66",
  hub: "#00FF66",
};
const FLOW_COMET = {
  pathLen: 100,
  pulse: 12,
  hubHeadSw: 3.5,
  headSw: 3,
  glowScale: 2.35,
  dur: 1.75,
  durSolar: 1.55,
};
const FLOW_SCENE_PV_THRESHOLD_W = 40;
const FLOW_SCENE_CANVAS_BG_DARK = "#000000";
const FLOW_SCENE_CANVAS_BG_LIGHT = "#ffffff";
const FLOW_SCENE_ASSET_VER = 48;

const FLOW_SCENE_BG_THEMES = new Set([
  "day_light",
  "day_dark",
  "night_light",
  "night_dark",
]);

function flowPipeStroke(isNight) {
  return isNight ? FLOW_PIPE_STROKE.night : FLOW_PIPE_STROKE.day;
}

function flowPipeUnderlay(isNight) {
  return isNight ? FLOW_PIPE_UNDERLAY.night : FLOW_PIPE_UNDERLAY.day;
}

function flowActiveStroke(cls) {
  if (cls === "flow-solar") return FLOW_ACTIVE_STROKE.solar;
  if (cls === "flow-grid") return FLOW_ACTIVE_STROKE.grid;
  if (cls === "flow-export") return FLOW_ACTIVE_STROKE.export;
  if (cls === "flow-home-line") return FLOW_ACTIVE_STROKE.home;
  return FLOW_ACTIVE_STROKE.battery;
}

/** Hub spokes share one flow class + one pipe colour so segments match (incl. hub-home). */
function flowHubSpokeCls(id, gridExporting) {
  if (id.startsWith("solar")) return "flow-solar";
  if (id.includes("grid")) return gridExporting && id === "hub-grid" ? "flow-export" : "flow-grid";
  return "flow-battery";
}

/** Single Fox-style comet pulse (one blob + soft glow, same phase — not two dashes). */
function flowCometPaths({ d, cls = "", headSw, stroke, reverse = false }) {
  const L = FLOW_COMET.pathLen;
  const pulse = FLOW_COMET.pulse;
  const gap = L - pulse;
  const rev = reverse ? " reverse" : "";
  const clsAttr = cls ? ` ${cls}` : "";
  const glowSw = (headSw * FLOW_COMET.glowScale).toFixed(2);
  const dash = `${pulse} ${gap}`;
  return (
    `<path class="flow-comet flow-comet-glow${clsAttr}${rev}" d="${d}" pathLength="${L}" stroke="${stroke}" stroke-width="${glowSw}" stroke-dasharray="${dash}" stroke-linecap="round"></path>` +
    `<path class="flow-comet flow-comet-pulse${clsAttr}${rev}" d="${d}" pathLength="${L}" stroke="${stroke}" stroke-width="${headSw}" stroke-dasharray="${dash}" stroke-linecap="round"></path>`
  );
}

function flowIdlePipeMarkup(d, isNight) {
  const stroke = flowPipeStroke(isNight);
  const sw = FLOW_STROKE.hubActive;
  const outline = isNight
    ? ""
    : `<path class="flow-path flow-path-idle-outline" d="${d}" stroke="rgba(28, 36, 48, 0.55)" stroke-width="${sw + 2}" stroke-linecap="round" stroke-linejoin="round"></path>`;
  return (
    outline +
    `<path class="flow-path flow-path-idle" d="${d}" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round"></path>`
  );
}

function renderFlowScenePaths({ lines, activeIds, gridExporting, isNight }) {
  const idleHtml = Object.entries(FOX_FLOW_PATHS)
    .map(([id, d]) => (FOX_FLOW_HUB_SPOKES.has(id) ? flowIdlePipeMarkup(d, isNight) : ""))
    .join("");
  const activeHtml = Object.entries(FOX_FLOW_PATHS)
    .map(([id, d]) => {
      const line = lines.find((l) => l.id === id);
      if (!line || !FOX_FLOW_HUB_SPOKES.has(id)) return "";
      const cls = flowHubSpokeCls(id, gridExporting);
      if (!activeIds.has(id)) return "";
      return flowPathMarkup({
        d,
        cls,
        role: "flow",
        isNight,
        reverse: !!line?.reverse,
      });
    })
    .join("");
  return idleHtml + activeHtml;
}

/** Stable key — only changes when which pipes are active or scene theme changes (not power W). */
function flowSceneStructureKey(lines, gridExporting, isNight, bgTheme, haUiDark) {
  const active = lines
    .map((l) => `${l.id}${l.reverse ? ":r" : ""}`)
    .sort()
    .join(",");
  return `${bgTheme}|${haUiDark ? "haD" : "haL"}|${isNight ? "n" : "d"}|${gridExporting ? "x" : "i"}|${active}`;
}

function renderFlowSceneSvgInner({ lines, activeIds, gridExporting, isNight }) {
  const pathsHtml = renderFlowScenePaths({ lines, activeIds, gridExporting, isNight });
  const hubActive = lines.some((l) => l.id.includes("hub"));
  const hubFill = hubActive ? FLOW_ACTIVE_STROKE.battery : flowPipeStroke(isNight);
  return `${pathsHtml}<circle class="flow-hub-dot ${hubActive ? "active" : ""}" cx="${FOX_FLOW_HUB.x}" cy="${FOX_FLOW_HUB.y}" r="${FLOW_STROKE.hubR}" fill="${hubFill}"/>`;
}

/** role: flow = comet pulse (idle pipes drawn separately via renderFlowScenePaths). */
function flowPathMarkup({ d, cls = "", role = "flow", isNight = false, reverse = false }) {
  const isHubFlow = cls === "flow-battery";
  const stroke = flowActiveStroke(cls);
  const headSw = isHubFlow ? FLOW_COMET.hubHeadSw : FLOW_COMET.headSw;
  return flowCometPaths({ d, cls, headSw, stroke, reverse });
}

const DEFAULT_PERIODS = [
  { enable_force_charge: false, enable_charge_from_grid: false, start: "00:00", end: "00:00" },
  { enable_force_charge: false, enable_charge_from_grid: false, start: "00:00", end: "00:00" },
];

/** Display title + hint per FoxESS work_mode select option (key = entity option string). */
const WORK_MODE_META = {
  "Self Use": {
    title: "Self Use",
    hint: "Optimised for self consumption, reduce reliance on grid electricity.",
  },
  "Feed-in First": {
    title: "Feed-in Priority",
    hint: "Prioritises electricity sales to generate income.",
  },
  "Feed-in Priority": {
    title: "Feed-in Priority",
    hint: "Prioritises electricity sales to generate income.",
  },
  "Back-up": {
    title: "Back-up",
    hint: "Tailored for areas with unstable power grids. Reserves SOC to prevent power outages.",
  },
  "Back Up": {
    title: "Back-up",
    hint: "Tailored for areas with unstable power grids. Reserves SOC to prevent power outages.",
  },
  "Peak Shaving": {
    title: "Peak Shaving",
    hint: "Implements energy management strategies by setting battery SOC and import limits according to production schedules, reducing overall energy consumption during peak periods.",
  },
  "Force Charge": {
    title: "Force Charge",
    hint: "Active remote force-charge session.",
  },
  "Force Discharge": {
    title: "Force Discharge",
    hint: "Active remote force-discharge session.",
  },
};

function workModeMeta(option) {
  const key = String(option ?? "").trim();
  return WORK_MODE_META[key] || { title: key, hint: "" };
}

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
  return "is-default";
}

function foxWorkModeToneClass(label) {
  const s = String(label || "").toLowerCase();
  if (s.includes("self")) return "work-self-use";
  if (s.includes("feed")) return "work-feed-in";
  if (s.includes("back")) return "work-back-up";
  if (s.includes("force charge")) return "work-force-charge";
  if (s.includes("force discharge")) return "work-force-discharge";
  return "work-default";
}

function foxWorkModeDisplay(label) {
  const s = String(label || "").trim();
  const meta = WORK_MODE_META[s];
  if (meta?.title) return meta.title;
  if (s.toLowerCase() === "self use") return "Self Use";
  return s;
}

function normalizePvString(raw, defaults) {
  const base = defaults || DEFAULT_PV_STRING;
  const src = raw && typeof raw === "object" ? raw : {};
  let panelCount = parseInt(src.panel_count, 10);
  if (!Number.isFinite(panelCount)) panelCount = base.panel_count;
  panelCount = Math.max(1, Math.min(12, panelCount));
  let watts = parseInt(src.watts_per_panel, 10);
  if (!Number.isFinite(watts)) watts = base.watts_per_panel;
  watts = Math.max(100, Math.min(1000, watts));
  let eff = parseFloat(src.efficiency_factor);
  if (!Number.isFinite(eff)) eff = base.efficiency_factor;
  eff = Math.max(1, Math.min(100, eff));
  let tilt = parseInt(src.tilt, 10);
  if (!Number.isFinite(tilt)) tilt = base.tilt ?? 25;
  tilt = Math.max(0, Math.min(90, tilt));
  let azimuth = parseInt(src.azimuth, 10);
  if (!Number.isFinite(azimuth)) azimuth = base.azimuth ?? 180;
  azimuth = Math.max(0, Math.min(359, azimuth));
  return {
    enabled: Boolean(src.enabled ?? base.enabled),
    panel_count: panelCount,
    watts_per_panel: watts,
    efficiency_factor: eff,
    tilt,
    azimuth,
  };
}

function normalizePvConfig(raw) {
  const src = raw && typeof raw === "object" ? raw : {};
  return {
    pv1: normalizePvString(src.pv1, DEFAULT_PV_CONFIG.pv1),
    pv2: normalizePvString(src.pv2, DEFAULT_PV_CONFIG.pv2),
  };
}

function pvStringSummary(cfg) {
  if (!cfg?.enabled) return "Off";
  const kw = (cfg.panel_count * cfg.watts_per_panel) / 1000;
  return `${cfg.panel_count} panels · ${cfg.watts_per_panel} W · ${kw.toFixed(2)} kW · ${cfg.tilt}°/${cfg.azimuth}°`;
}

/** Effective DC kW cap from PV configuration (panels × W × efficiency). */
function pvStringEffectiveMaxKw(cfg) {
  if (!cfg?.enabled) return 0;
  const dcW = cfg.panel_count * cfg.watts_per_panel * (cfg.efficiency_factor / 100);
  return Math.max(0.01, dcW / 1000);
}

function enabledPvStrings(pvConfig) {
  const cfg = normalizePvConfig(pvConfig);
  const out = [];
  if (cfg.pv1?.enabled) out.push({ key: "pv1", label: "PV1 Power", cfg: cfg.pv1 });
  if (cfg.pv2?.enabled) out.push({ key: "pv2", label: "PV2 Power", cfg: cfg.pv2 });
  return out;
}

function parseSolcastCoordinateInput(raw) {
  const v = parseFloat(String(raw ?? "").trim());
  return Number.isFinite(v) ? v : null;
}

function normalizeSolcastCoordinateInput(raw) {
  const v = parseSolcastCoordinateInput(raw);
  if (v == null) return null;
  const factor = 10 ** SOLCAST_COORD_DECIMALS;
  return Math.round(v * factor) / factor;
}

function normalizeSolcastInstallationDateInput(raw) {
  const v = String(raw ?? "").trim();
  if (!v) return null;
  const iso = v.length >= 10 ? v.slice(0, 10) : v;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
  const parts = iso.split("-").map((x) => parseInt(x, 10));
  if (parts.length !== 3 || parts.some((n) => !Number.isFinite(n))) return null;
  const probe = new Date(parts[0], parts[1] - 1, parts[2]);
  if (
    probe.getFullYear() !== parts[0] ||
    probe.getMonth() !== parts[1] - 1 ||
    probe.getDate() !== parts[2]
  ) {
    return null;
  }
  return iso;
}

function solcastInstallationDateMax() {
  return new Date().toISOString().slice(0, 10);
}

function validateSolcastDraft(draft) {
  if (!draft?.enabled) return null;
  const lat = normalizeSolcastCoordinateInput(draft.latitude);
  const lon = normalizeSolcastCoordinateInput(draft.longitude);
  if (lat == null || lon == null) {
    return "Latitude and longitude are required. Copy them exactly from one of your two registered Solcast hobbyist locations (not Home Assistant coordinates).";
  }
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    return "Latitude must be between -90 and 90; longitude between -180 and 180.";
  }
  const installRaw = String(draft.installation_date ?? "").trim();
  if (installRaw) {
    const install = normalizeSolcastInstallationDateInput(installRaw);
    if (!install) {
      return "Installation date must be YYYY-MM-DD (match your Solcast Home PV system listing).";
    }
    if (install > solcastInstallationDateMax()) {
      return "Installation date cannot be in the future.";
    }
  }
  return null;
}

function solcastEnabledFromLive(sc) {
  const v = sc?.enabled;
  return v === true || v === 1 || v === "1" || v === "true";
}

function formatSolcastTimestamp(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "medium" });
}

function formatSolcastNextFetch(sc) {
  const status = sc?.next_fetch_status;
  if (status === "disabled") return "Off";
  if (!sc?.next_fetch_at) {
    if (status === "outside_window") return "Outside poll window";
    return "—";
  }
  const when = formatSolcastTimestamp(sc.next_fetch_at);
  if (status === "due_now") return `${when} (due now)`;
  if (status === "quota_exhausted") return `${when} (quota resets)`;
  if (status === "before_sunrise") return `${when} (at sunrise)`;
  if (status === "after_sunset") return `${when} (next sunrise)`;
  return when;
}

function nativeSolcastPvForecastEnabled(plantState) {
  const sc = plantState?.solcast;
  return Boolean(
    solcastEnabledFromLive(sc) &&
    sc?.api_key_set &&
    sc?.coordinates_configured &&
    sc?.hobbyist_sites_resolved &&
    sc?.fetch_pv_forecast !== false
  );
}

/** Chart overlay: use persisted detailed_forecast even before hobbyist bindings re-resolve. */
function statisticsSolcastForecastEnabled(plantState, hass) {
  const sc = plantState?.solcast;
  if (!sc || sc?.fetch_pv_forecast === false) return false;
  const rows = resolveSolcastDetailedForecast(plantState, hass);
  if (rows.length >= 2) return true;
  if (sc.forecast_persisted && (sc.pv_forecast_periods ?? 0) >= 2) return true;
  if (sc.pv_forecast_available) return true;
  return nativeSolcastPvForecastEnabled(plantState);
}

function solcastDetailedForecastFromHass(hass, plantState) {
  const sc = plantState?.solcast;
  const rows = sc?.detailed_forecast;
  if (Array.isArray(rows) && rows.length >= 2) return rows;
  if (!hass?.states) return Array.isArray(rows) ? rows : [];
  for (const st of Object.values(hass.states)) {
    const attrs = st?.attributes;
    if (!attrs || attrs.source !== "foxess_plant_solcast") continue;
    const df = attrs.detailed_forecast ?? attrs.detailedForecast;
    if (Array.isArray(df) && df.length >= 2) return df;
  }
  return Array.isArray(rows) ? rows : [];
}

function resolveSolcastDetailedForecast(plantState, hass) {
  return solcastDetailedForecastFromHass(hass, plantState);
}

function mergeStatisticsForecastSeries(series, range, plantState, hass) {
  if (!Array.isArray(series) || !range) return series;
  const without = series.filter((s) => s.id !== "forecast");
  const fPoints = buildForecastSeriesPoints(plantState, range, hass);
  if (!fPoints.length) return series;
  return [
    ...without,
    { id: "forecast", ...FORECAST_CHART_STYLE, connectGaps: true, points: fPoints },
  ];
}

function parseSolcastPeriodMs(raw) {
  if (raw == null || raw === "") return NaN;
  if (typeof raw === "number") return raw > 1e12 ? raw : raw * 1000;
  const text = String(raw).trim();
  if (!text) return NaN;
  if (/^\d+(\.\d+)?$/.test(text)) {
    const n = Number(text);
    return n > 1e12 ? n : n * 1000;
  }
  let t = Date.parse(text);
  if (Number.isFinite(t)) return t;
  t = Date.parse(text.replace(" ", "T"));
  if (Number.isFinite(t)) return t;
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(text)) {
    t = Date.parse(`${text.replace(" ", "T")}Z`);
    if (Number.isFinite(t)) return t;
  }
  return NaN;
}

function detailedForecastToChartPoints(rows, range) {
  if (!Array.isArray(rows) || rows.length < 2) return [];
  const raw = rows
    .map((row) => {
      const t = parseSolcastPeriodMs(row.period_end ?? row.period_start ?? row.period);
      let v = Number(row.pv_estimate ?? row.pv_power_rooftop ?? row.power ?? row.pv_power);
      if (!Number.isFinite(t) || !Number.isFinite(v)) return null;
      if (Math.abs(v) > 50) v /= 1000;
      return { t, v };
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t);
  if (raw.length < 2) return [];

  const graceMs = 36e5;
  let relevant = raw.filter((p) => p.t >= range.tMin - graceMs && p.t <= range.tMax);
  if (relevant.length < 2) {
    relevant = raw.filter((p) => p.t >= range.nowMs - STATISTICS_PERIOD_MS * 2 && p.t <= range.tMax);
  }
  if (relevant.length < 2) return [];

  return interpolatePointsToPeriod(relevant, STATISTICS_PERIOD_MS, range.tMin, range.tMax, {
    allowBackfill: false,
  });
}

function solcastIntradayForecastPoints(plantState, range) {
  const rows = plantState?.solcast?.forecast_intraday_points;
  if (!Array.isArray(rows) || rows.length < 2) return [];
  return rows
    .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v) && p.t >= range.tMin && p.t <= range.tMax)
    .map((p) => ({ t: p.t, v: p.v }))
    .sort((a, b) => a.t - b.t);
}

function nativeSolcastForecastPoints(plantState, range, hass) {
  const intraday = solcastIntradayForecastPoints(plantState, range);
  if (intraday.length >= 2) return intraday;
  const rows = resolveSolcastDetailedForecast(plantState, hass);
  return detailedForecastToChartPoints(rows, range);
}

function pvConfigSummary(pv) {
  const cfg = normalizePvConfig(pv);
  return `PV1: ${pvStringSummary(cfg.pv1)} · PV2: ${pvStringSummary(cfg.pv2)}`;
}

function overviewWeatherIconSvg(iconKey) {
  const key = String(iconKey || "unknown");
  if (key === "cloudy") {
    return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18h11a4 4 0 0 0 .3-8 5.5 5.5 0 0 0-10.6-1.2A3.8 3.8 0 0 0 7 18z" fill="#b0b8c4"/></svg>`;
  }
  if (key === "partly-cloudy") {
    return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="8.5" cy="9" r="3.2" fill="#f5bc00"/><g stroke="#f5bc00" stroke-width="1.6" stroke-linecap="round"><path d="M8.5 4.5v2M8.5 11.5v2M4.5 9h2M11.5 9h2"/></g><path d="M7 18h11a4 4 0 0 0 .3-8 5.2 5.2 0 0 0-10.2-1.4A3.8 3.8 0 0 0 7 18z" fill="#b0b8c4"/></svg>`;
  }
  if (key === "rain") {
    return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 15h11a4 4 0 0 0 .3-8 5.5 5.5 0 0 0-10.6-1.2A3.8 3.8 0 0 0 7 15z" fill="#8ea0b4"/><g stroke="#5b9bd5" stroke-width="1.8" stroke-linecap="round"><path d="M9 17.5v3M12 17.5v3.5M15 17.5v3"/></g></svg>`;
  }
  if (key === "snow") {
    return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 15h11a4 4 0 0 0 .3-8 5.5 5.5 0 0 0-10.6-1.2A3.8 3.8 0 0 0 7 15z" fill="#b0b8c4"/><g stroke="#dbeafe" stroke-width="1.6" stroke-linecap="round"><path d="M9 17l1.5 2.5M12 16.5v4M15 17l-1.5 2.5"/></g></svg>`;
  }
  if (key === "storm") {
    return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 14h11a4 4 0 0 0 .3-8 5.5 5.5 0 0 0-10.6-1.2A3.8 3.8 0 0 0 7 14z" fill="#7a8798"/><path d="M13 15.5l-2.5 4h2l-1 3.5 4-5.5h-2.2l1.7-2z" fill="#f5bc00"/></svg>`;
  }
  if (key === "fog") {
    return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><g stroke="#a8b0bc" stroke-width="1.8" stroke-linecap="round"><path d="M5 10h14M4 14h16M6 18h12"/></g></svg>`;
  }
  if (key === "wind") {
    return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><g stroke="#8ea0b4" stroke-width="1.8" stroke-linecap="round" fill="none"><path d="M4 8h11a3 3 0 1 0-3-3M4 13h13a2.5 2.5 0 1 1 0 5H4M4 18h9"/></g></svg>`;
  }
  if (key === "sunny") {
    return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2" fill="#f5bc00"/><g stroke="#f5bc00" stroke-width="2" stroke-linecap="round"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></g></svg>`;
  }
  return `<svg class="overview-weather-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18h11a4 4 0 0 0 .3-8 5.5 5.5 0 0 0-10.6-1.2A3.8 3.8 0 0 0 7 18z" fill="#b0b8c4"/></svg>`;
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

/** 270° arc gauge (gap at bottom), Fox app PV style. Fill = live kW ÷ configured effective max kW. */
function renderPvThreeQuarterGauge(pvKw, maxKw, valueText, labelText, pctOfMax) {
  const r = 42;
  const cx = 50;
  const cy = 52;
  const circ = 2 * Math.PI * r;
  const arcLen = circ * 0.75;
  const gapLen = circ - arcLen;
  const rot = 135;
  const pct = maxKw > 0 ? Math.min(1, Math.max(0, pvKw / maxKw)) : 0;
  const fillLen = arcLen * pct;
  const pctLabel =
    pctOfMax != null && Number.isFinite(pctOfMax)
      ? `${Math.round(pctOfMax)}% of ${maxKw < 10 ? maxKw.toFixed(2) : maxKw.toFixed(1)} kW`
      : maxKw > 0
        ? `${Math.round(pct * 100)}% of ${maxKw < 10 ? maxKw.toFixed(2) : maxKw.toFixed(1)} kW`
        : "";
  const track = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--divider-color)" stroke-width="9" stroke-linecap="round" stroke-dasharray="${arcLen} ${gapLen}" transform="rotate(${rot} ${cx} ${cy})"/>`;
  const fill =
    fillLen > 0.5
      ? `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--fp-accent)" stroke-width="9" stroke-linecap="round" stroke-dasharray="${fillLen} ${circ - fillLen}" transform="rotate(${rot} ${cx} ${cy})"/>`
      : "";
  const cap = pctLabel ? `<div class="device-pv-cap">${esc(pctLabel)}</div>` : "";
  return `<div class="device-pv-wrap" role="img" aria-label="${esc(labelText)} ${esc(valueText)} ${esc(pctLabel)}">
<div class="device-pv-gauge"><svg viewBox="0 0 100 104" aria-hidden="true">${track}${fill}</svg>
<div class="device-pv-readout"><div class="device-pv-value">${esc(valueText)}</div><div class="device-pv-label">${esc(labelText)}</div></div>
</div>
${cap}
</div>`;
}

function resolvePvStringPowerEntity(hass, map, which) {
  const key = which === "pv2" ? "pv2_power" : "pv1_power";
  const suffix = which === "pv2" ? "pv2_power" : "pv1_power";
  if (map[key] && hass?.states?.[map[key]]) return map[key];
  if (!hass?.states) return map[key] || null;
  const ids = Object.keys(hass.states);
  const hit = ids.find((id) => entityIdMatchesSuffix(id, suffix));
  return hit || (which === "pv1" ? map.pv_power : null) || null;
}

function renderDevicePvGaugeInner(hass, map, { key, label, cfg }) {
  const entityId = resolvePvStringPowerEntity(hass, map, key);
  const watts = entityId ? statePowerWatts(hass, entityId) : 0;
  const liveKw = watts / 1000;
  const maxKw = pvStringEffectiveMaxKw(cfg);
  const pct = maxKw > 0 ? Math.min(100, (liveKw / maxKw) * 100) : 0;
  return renderPvThreeQuarterGauge(liveKw, maxKw, formatDevicePowerKw(watts), label, pct);
}

/** One PV card (left column): 1 centred gauge or 2 side-by-side; battery stays in the right column. */
function renderDevicePvCard(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const strings = enabledPvStrings(plantState?.pv_config);
  if (!strings.length) {
    const flows = readEnergyFlows(hass, plant, plantState);
    const cfg = normalizePvConfig(plantState?.pv_config).pv1;
    const maxKw = pvStringEffectiveMaxKw(cfg);
    const liveKw = flows.pvW / 1000;
    const pct = maxKw > 0 ? Math.min(100, (liveKw / maxKw) * 100) : 0;
    const gauge = renderPvThreeQuarterGauge(
      liveKw,
      maxKw,
      formatDevicePowerKw(flows.pvW),
      "PV1 Power",
      pct
    );
    return `<div class="device-card device-card--pv"><div class="device-pv-gauges device-pv-gauges--single">${gauge}</div></div>`;
  }
  const layoutClass = strings.length > 1 ? "device-pv-gauges--dual" : "device-pv-gauges--single";
  const gauges = strings.map((s) => renderDevicePvGaugeInner(hass, map, s)).join("");
  return `<div class="device-card device-card--pv"><div class="device-pv-gauges ${layoutClass}">${gauges}</div></div>`;
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
    splitSigned: "charge",
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
    splitSigned: "discharge",
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
    splitSigned: "import",
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
    splitSigned: "export",
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

const BATTERY_SOC_POWER_THRESHOLD_KW = 0.04;
const BATTERY_SOC_COLORS = {
  charging: { line: "#3DDC84", fill: "rgba(61,220,132,0.2)" },
  discharging: { line: "#5B9BD5", fill: "rgba(91,155,213,0.2)" },
  idle: { line: "#8DB6FF", fill: "rgba(141,182,255,0.1)" },
};
const BATTERY_SOC_CHART_LAYOUT = {
  width: 1000,
  height: 300,
  pad: { l: 44, r: 8, t: 8, b: 40 },
  xTickHours: 3,
  xTickCount: 8,
  yTicks: [0, 50, 100],
};

const ENERGY_CHART_BAR = {
  pv: { suffix: "solar_energy_today", label: "PV", color: FOX_ENERGY.pv },
  load: { suffix: "load_energy_today", label: "Load", color: FOX_ENERGY.load, computed: true },
  grid: { suffix: "grid_consumption_energy_today", label: "From grid", color: "#FF6FAF" },
};

const ENERGY_PERIOD_TABS = [
  { id: "day", label: "Day" },
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "year", label: "Year" },
  { id: "total", label: "Total" },
];

const FOX_SUPPLY_SERIES = [
  { key: "solar", label: "Solar", color: "#19D4DE" },
  { key: "batteryDischarge", label: "Battery Discharge", color: "#8DB6FF" },
  { key: "gridImport", label: "Grid Import", color: "#2F6BFF" },
];

const FOX_USAGE_SERIES = [
  { key: "load", label: "Load", color: "#8A4DFF" },
  { key: "batteryCharge", label: "Battery Charge", color: "#C4A3FF" },
  { key: "gridExport", label: "Grid Export", color: "#FF6FAF" },
];

const OVERVIEW_DAILY_DAYS = 7;
const OVERVIEW_DAILY_COLORS = {
  production: "#8A4DFF",
  consumption: "#19D4DE",
  barMuted: "#4a5058",
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
  pv1_power: ["pv1_power"],
  pv2_power: ["pv2_power"],
  pv_power: ["pv1_power", "pv_power", "pv_power_total", "pv_power_evo_10", "pv_power_now"],
  battery_soc: ["battery_soc_1", "battery_soc"],
  battery_charge: ["battery_charge_1", "battery_charge"],
  battery_discharge: ["battery_discharge_1", "battery_discharge"],
  grid_import: ["grid_consumption", "grid_import"],
  grid_export: ["feed_in", "grid_ct", "grid_export"],
  load_power: ["load_power", "load_power_total"],
  solar_energy_today: ["solar_energy_today"],
  feed_in_energy_today: ["feed_in_energy_today", "feed_in_energy"],
  load_energy_today: ["load_energy_today"],
  battery_discharge_today: ["battery_discharge_today"],
  battery_charge_today: ["battery_charge_today"],
  grid_consumption_energy_today: ["grid_consumption_energy_today"],
};

/** Device → Parameters page (Fox app sections). Merged into resolveEntityMap at runtime. */
const DEVICE_ENTITY_FALLBACKS = {
  pv1_voltage: ["pv1_voltage"],
  pv1_current: ["pv1_current"],
  pv1_power: ["pv1_power"],
  pv2_voltage: ["pv2_voltage"],
  pv2_current: ["pv2_current"],
  pv2_power: ["pv2_power"],
  pv3_voltage: ["pv3_voltage"],
  pv3_current: ["pv3_current"],
  pv3_power: ["pv3_power"],
  pv4_voltage: ["pv4_voltage"],
  pv4_current: ["pv4_current"],
  pv4_power: ["pv4_power"],
  pv_power: ["pv_power_now", "pv1_power", "pv_power", "pv_power_total", "pv_power_evo_10"],
  solar_energy_today: ["solar_energy_today"],
  solar_energy_total: ["solar_energy_total"],
  grid_voltage_R: ["grid_voltage_R"],
  inv_current_R: ["inv_current_R"],
  inv_power: ["inv_power"],
  rfreq: ["rfreq"],
  invtemp: ["invtemp"],
  eps_rvolt_R: ["eps_rvolt_R"],
  eps_rcurrent_R: ["eps_rcurrent_R"],
  eps_power_R: ["eps_power_R"],
  eps_frequency: ["eps_frequency"],
  load_power_R: ["load_power_R"],
  load_power_total: ["load_power_total"],
  grid_status: ["grid_status"],
  feed_in_energy_total: ["feed_in_energy_total"],
  grid_consumption_energy_total: ["grid_consumption_energy_total"],
  battery_soh: ["battery_soh"],
  battery_cycles: ["battery_cycles"],
  battery_kwh_remaining: ["battery_kwh_remaining"],
  bms_kwh_nominal: ["bms_kwh_remaining_1"],
  batvolt_1: ["batvolt_1", "invbatvolt_1"],
  bat_current_1: ["bat_current_1", "invbatcurrent_1"],
  battery_charge_total: ["battery_charge_total"],
  battery_discharge_total: ["battery_discharge_total"],
  bms_temp_high: ["bms_cell_temp_high_1", "bms_cell_temp_high"],
  bms_online: ["bms_online"],
  modbus_protocol_version: ["modbus_protocol_version"],
  master_version: ["master_version"],
  slave_version: ["slave_version"],
  manager_version: ["manager_version"],
};

const DEVICE_PV_STRINGS = [1, 2, 3, 4];

const DEVICE_PARAMETER_SECTIONS = [
  { id: "pv", title: "PV Information", kind: "pv-table" },
  {
    id: "ac",
    title: "AC Information",
    kind: "metric-table",
    keys: ["grid_voltage_R", "inv_current_R", "inv_power", "rfreq"],
    headers: ["Voltage (V)", "Current (A)", "Power (kW)", "Frequency (Hz)"],
  },
  {
    id: "eps",
    title: "EPS Information",
    kind: "metric-table",
    keys: ["eps_rvolt_R", "eps_rcurrent_R", "eps_power_R", "eps_frequency"],
    headers: ["Voltage (V)", "Current (A)", "Power (kW)", "Frequency (Hz)"],
  },
  {
    id: "load",
    title: "Load Information",
    kind: "rows",
    rows: [
      ["load_energy_today", "Daily load consumption"],
      ["load_power_total", "Total load consumption"],
      ["load_power", "Total load power"],
      ["load_power_R", "Grid load power"],
      ["eps_power_R", "EPS load power"],
    ],
  },
  {
    id: "grid",
    title: "Grid Information",
    kind: "rows",
    rows: [
      ["grid_status", "Grid status"],
      ["feed_in_energy_today", "Daily feed-in energy"],
      ["feed_in_energy_total", "Total feed-in energy"],
      ["grid_consumption_energy_today", "Daily purchased energy"],
      ["grid_consumption_energy_total", "Total purchased energy"],
      ["grid_export", "Feed-in power"],
      ["grid_import", "Purchased power"],
    ],
  },
  {
    id: "datalogger",
    title: "System Information",
    kind: "datalogger",
  },
  {
    id: "battery",
    title: "Battery Information",
    kind: "rows",
    rows: [
      ["bms_kwh_nominal", "Nominal energy"],
      ["battery_soc", "SOC"],
      ["battery_kwh_remaining", "Remaining energy"],
      ["battery_status", "Status"],
      ["battery_power", "Battery power"],
      ["bat_current_1", "Current"],
      ["batvolt_1", "Voltage"],
      ["bms_temp_low", "Min. battery temperature"],
      ["battery_discharge_today", "Daily discharged energy"],
      ["battery_discharge_total", "Total discharged energy"],
      ["battery_charge_today", "Daily charged energy"],
      ["battery_charge_total", "Total charged energy"],
      ["battery_soh", "SOH"],
      ["battery_cycles", "Battery cycles"],
    ],
  },
];

const ANALYTICS_STATE_KEYS = [
  "solar_energy_today",
  "feed_in_energy_today",
  "load_energy_today",
  "grid_consumption_energy_today",
  "battery_discharge_today",
  "battery_charge_today",
];

const ANALYTICS_SUFFIXES = {
  solar_energy_today: ["solar_energy_today"],
  feed_in_energy_today: ["feed_in_energy_today"],
  load_energy_today: ["load_energy_today"],
  grid_consumption_energy_today: ["grid_consumption_energy_today"],
  battery_discharge_today: ["battery_discharge_today"],
  battery_charge_today: ["battery_charge_today"],
};

function analyticsFloat(states, key) {
  const raw = states[key];
  if (raw == null || raw === "" || raw === "unknown" || raw === "unavailable") return 0;
  const n = parseFloat(raw);
  return Number.isFinite(n) ? n : 0;
}

function isValidAnalyticsEnergyState(st) {
  if (!st || st.state === "unknown" || st.state === "unavailable") return false;
  const dc = st.attributes?.device_class;
  if (dc === "power") return false;
  return Number.isFinite(parseFloat(st.state));
}

function scoreAnalyticsEntity(entityId, key, suffix, mappedId) {
  if (mappedId && entityId === mappedId) return 1000;
  if (entityId.endsWith(`_${key}`)) return 500;
  if (key.includes("_today") && (entityId.includes("_total") || entityId.endsWith("_total"))) {
    return -500;
  }
  if (entityId.endsWith(`_${suffix}`) || entityId.includes(`_${suffix}_`)) return 100;
  return 0;
}

function pickAnalyticsState(hass, map, key) {
  const suffixes = ANALYTICS_SUFFIXES[key] || [key];
  const mappedId = map[key];
  if (mappedId && isValidAnalyticsEnergyState(hass.states[mappedId])) {
    return hass.states[mappedId].state;
  }
  const ranked = [];
  for (const entityId of Object.keys(hass.states)) {
    for (const suffix of suffixes) {
      if (!entityIdMatchesSuffix(entityId, suffix)) continue;
      const st = hass.states[entityId];
      if (!isValidAnalyticsEnergyState(st)) continue;
      const score = scoreAnalyticsEntity(entityId, key, suffix, mappedId);
      if (score < 0) continue;
      ranked.push({ score, value: parseFloat(st.state), state: st.state });
      break;
    }
  }
  if (!ranked.length) return null;
  ranked.sort((a, b) => b.score - a.score || b.value - a.value);
  const bestScore = ranked[0].score;
  const tier = ranked.filter((r) => r.score === bestScore);
  return tier[0].state;
}

function applyPvTodayFallback(states, overviewDaily) {
  const out = { ...states };
  const pvHist = overviewDaily?.production?.at(-1);
  const pvLive = analyticsFloat(out, "solar_energy_today");
  if (pvHist > 0 && (pvLive <= 0 || pvLive < pvHist * 0.85)) {
    out.solar_energy_today = String(pvHist);
  }
  return out;
}

function computeAnalyticsFromStates(states) {
  let pv = analyticsFloat(states, "solar_energy_today");
  let toGrid = analyticsFloat(states, "feed_in_energy_today");
  if (pv > 0 && toGrid > pv) toGrid = pv;
  const toLoadBattery = Math.max(0, pv - toGrid);
  const baseLoad = analyticsFloat(states, "load_energy_today");
  const batteryDischarge = analyticsFloat(states, "battery_discharge_today");
  const batteryCharge = analyticsFloat(states, "battery_charge_today");
  const fromGrid = analyticsFloat(states, "grid_consumption_energy_today");
  const loadConsumption = baseLoad - batteryDischarge + batteryCharge + fromGrid;
  const fromPvBattery = Math.max(0, loadConsumption - fromGrid);
  const selfConsumption = pv > 0 ? Math.min(100, Math.max(0, (toLoadBattery / pv) * 100)) : 0;
  const selfSufficiency =
    loadConsumption > 0 ? Math.min(100, Math.max(0, (fromPvBattery / loadConsumption) * 100)) : 0;
  return {
    pv_production_kwh_today: Math.round(pv * 100) / 100,
    pv_to_load_battery_kwh_today: Math.round(toLoadBattery * 100) / 100,
    pv_to_grid_kwh_today: Math.round(toGrid * 100) / 100,
    load_consumption_kwh_today: Math.round(loadConsumption * 100) / 100,
    load_from_pv_battery_kwh_today: Math.round(fromPvBattery * 100) / 100,
    load_from_grid_kwh_today: Math.round(fromGrid * 100) / 100,
    self_consumption_percent_today: Math.round(selfConsumption * 10) / 10,
    self_sufficiency_percent_today: Math.round(selfSufficiency * 10) / 10,
    battery_charge_kwh_today: Math.round(batteryCharge * 100) / 100,
    battery_discharge_kwh_today: Math.round(batteryDischarge * 100) / 100,
  };
}

/** Prefer live hass.states (with suffix scan) — coordinator analytics can lag or miss mapped entities. */
function resolveAnalyticsEntityStates(hass, map) {
  const states = {};
  if (!hass?.states) return states;
  for (const key of ANALYTICS_STATE_KEYS) {
    const picked = pickAnalyticsState(hass, map, key);
    if (picked != null) states[key] = picked;
  }
  return states;
}

function readLiveAnalytics(hass, plant, plantState, overviewDaily) {
  const map = resolveEntityMap(hass, plant, plantState);
  let states = resolveAnalyticsEntityStates(hass, map);
  states = applyPvTodayFallback(states, overviewDaily);
  let analytics = computeAnalyticsFromStates(states);
  const cached = plantState?.analytics ?? {};

  const loadFromHistory = overviewDaily?.consumption?.at(-1);
  if (loadFromHistory > 0 && analytics.load_consumption_kwh_today < loadFromHistory) {
    const patched = { ...states, load_energy_today: String(loadFromHistory) };
    if (analyticsFloat(states, "grid_consumption_energy_today") === 0) {
      patched.grid_consumption_energy_today = "0";
    }
    analytics = computeAnalyticsFromStates(patched);
  }

  if (!Object.keys(states).length && cached.pv_production_kwh_today != null) {
    return cached;
  }
  return { ...cached, ...analytics };
}

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
  const allFallbacks = { ...CHART_ENTITY_FALLBACKS, ...DEVICE_ENTITY_FALLBACKS };
  for (const [key, suffixes] of Object.entries(allFallbacks)) {
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

function entityDisplayValue(hass, entityId) {
  if (!entityId || !hass?.states?.[entityId]) return "—";
  const st = stateString(hass, entityId);
  if (st === "—") return "—";
  return `${st}${entityUnit(hass, entityId)}`;
}

function entityMapRows(hass, plant, plantState, pairs) {
  const map = resolveEntityMap(hass, plant, plantState);
  return pairs
    .map(([key, name]) => (map[key] ? { entity_id: map[key], name, key } : null))
    .filter(Boolean);
}

function deviceParamEntityIds(map, sections) {
  const ids = new Set();
  for (const section of sections) {
    if (section.kind === "pv-table") {
      for (const n of DEVICE_PV_STRINGS) {
        for (const suffix of ["voltage", "current", "power"]) {
          const id = map[`pv${n}_${suffix}`];
          if (id) ids.add(id);
        }
      }
      if (map.pv_power) ids.add(map.pv_power);
    } else if (section.kind === "metric-table") {
      for (const key of section.keys) {
        if (map[key]) ids.add(map[key]);
      }
    } else if (section.kind === "rows") {
      for (const [key] of section.rows) {
        if (map[key]) ids.add(map[key]);
      }
    } else if (section.kind === "datalogger") {
      for (const key of ["bms_online", "manager_version", "master_version", "modbus_protocol_version"]) {
        if (map[key]) ids.add(map[key]);
      }
    }
  }
  return ids;
}

function deviceParamLastUpdated(hass, entityIds) {
  let latest = 0;
  for (const entityId of entityIds) {
    const ts = hass?.states?.[entityId]?.last_updated;
    if (!ts) continue;
    const ms = Date.parse(ts);
    if (Number.isFinite(ms) && ms > latest) latest = ms;
  }
  if (!latest) return "";
  try {
    return new Date(latest).toLocaleString(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return new Date(latest).toISOString();
  }
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

const STATISTICS_SIGNED_EPS_KW = 0.05;
/** Drop isolated 5-minute spikes not seen in neighbours (recorder glitches). */
const STATISTICS_SPIKE_MAX_DELTA_KW = 8;

function transformHistoryPoint(hass, entityId, v, spec) {
  let x = v;
  if (spec.toKw) x = entityValueToKw(hass, entityId, x);
  if (spec.splitSigned === "import") return x > STATISTICS_SIGNED_EPS_KW ? x : 0;
  if (spec.splitSigned === "export") return x < -STATISTICS_SIGNED_EPS_KW ? x : 0;
  if (spec.splitSigned === "charge") return x > STATISTICS_SIGNED_EPS_KW ? -Math.abs(x) : 0;
  if (spec.splitSigned === "discharge") return x > STATISTICS_SIGNED_EPS_KW ? Math.abs(x) : 0;
  if (spec.abs) x = Math.abs(x);
  if (spec.negate) x = -x;
  return x;
}

function filterStatisticsSpikes(points) {
  if (points.length < 3) return points;
  const out = [];
  for (let i = 0; i < points.length; i++) {
    const prev = points[i - 1]?.v ?? points[i].v;
    const next = points[i + 1]?.v ?? points[i].v;
    const v = points[i].v;
    const neighbour = (Math.abs(prev) + Math.abs(next)) / 2;
    const delta = Math.abs(v - prev);
    if (delta > STATISTICS_SPIKE_MAX_DELTA_KW && Math.abs(v) > neighbour * 2.5 && Math.abs(v) > 1) {
      continue;
    }
    out.push(points[i]);
  }
  return out;
}

function getStatisticsDayRange(now = new Date()) {
  const start = startOfLocalDay(now);
  const tMin = start.getTime();
  return { tMin, tMax: tMin + 24 * 60 * 60 * 1000, nowMs: now.getTime() };
}

function getStatisticsDayRangeForDate(dayDate, { asOf = new Date() } = {}) {
  const start = startOfLocalDay(dayDate);
  const tMin = start.getTime();
  const tMax = tMin + 24 * 60 * 60 * 1000;
  const endCap = endOfLocalDay(dayDate).getTime();
  const nowMs = Math.min(asOf.getTime(), endCap, tMax);
  return { tMin, tMax, nowMs: Math.max(tMin, nowMs) };
}

function startOfWeekMonday(d) {
  const x = startOfLocalDay(d);
  const day = x.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  x.setDate(x.getDate() + diff);
  return x;
}

function roundEnergyKwh(v) {
  return Math.round(v * 100) / 100;
}

function roundEnergyPct(v) {
  return Math.round(v * 10) / 10;
}

function formatEnergyDateLabel(d) {
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${mo}-${day}`;
}

function formatEnergyRangeLabel(start, end) {
  return `${formatEnergyDateLabel(start)} ~ ${formatEnergyDateLabel(end)}`;
}

function energyPeriodBounds(period, offset = 0, now = new Date()) {
  const o = Math.max(0, Number(offset) || 0);
  if (period === "day") {
    const d = startOfLocalDay(now);
    d.setDate(d.getDate() - o);
    return { start: startOfLocalDay(d), end: endOfLocalDay(d), canNext: o > 0, canPrev: true };
  }
  if (period === "week") {
    const start = startOfWeekMonday(now);
    start.setDate(start.getDate() - o * 7);
    const weekEnd = new Date(start);
    weekEnd.setDate(weekEnd.getDate() + 6);
    weekEnd.setHours(23, 59, 59, 999);
    const end = o === 0 ? now : weekEnd;
    return { start, end, canNext: o > 0, canPrev: true };
  }
  if (period === "month") {
    const start = new Date(now.getFullYear(), now.getMonth() - o, 1);
    const monthEnd = new Date(start.getFullYear(), start.getMonth() + 1, 0, 23, 59, 59, 999);
    const end = o === 0 ? now : monthEnd;
    return { start, end, canNext: o > 0, canPrev: true };
  }
  if (period === "year") {
    const start = new Date(now.getFullYear() - o, 0, 1);
    const yearEnd = new Date(start.getFullYear(), 11, 31, 23, 59, 59, 999);
    const end = o === 0 ? now : yearEnd;
    return { start, end, canNext: o > 0, canPrev: true };
  }
  return { start: new Date(2000, 0, 1), end: now, canNext: false, canPrev: false };
}

function energyPeriodNavLabel(period, offset = 0, now = new Date()) {
  const { start, end } = energyPeriodBounds(period, offset, now);
  if (period === "day") return formatEnergyDateLabel(start);
  if (period === "week") return formatEnergyRangeLabel(start, end);
  if (period === "month") {
    return start.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  }
  if (period === "year") return String(start.getFullYear());
  return "Total";
}

function energyBreakdownTitle(period, offset = 0, now = new Date()) {
  if (period === "day" && offset === 0) return "Today energy breakdown";
  return `Energy breakdown · ${energyPeriodNavLabel(period, offset, now)}`;
}

function dailyLoadKwhFromPoints(points, dayStartMs, dayEndMs) {
  const load =
    dailyMaxInRange(points.load, dayStartMs, dayEndMs) -
    dailyMaxInRange(points.discharge, dayStartMs, dayEndMs) +
    dailyMaxInRange(points.charge, dayStartMs, dayEndMs) +
    dailyMaxInRange(points.grid, dayStartMs, dayEndMs);
  return Math.max(0, load);
}

function computeEnergyBreakdown(points, dayLabels) {
  let pvTotal = 0;
  let pvToGrid = 0;
  let loadTotal = 0;
  let loadFromGrid = 0;
  for (const day of dayLabels) {
    const ds = startOfLocalDay(day).getTime();
    const de = endOfLocalDay(day).getTime();
    pvTotal += dailyMaxInRange(points.pv, ds, de);
    pvToGrid += dailyMaxInRange(points.feedIn, ds, de);
    loadTotal += dailyLoadKwhFromPoints(points, ds, de);
    loadFromGrid += dailyMaxInRange(points.grid, ds, de);
  }
  const pvToLoadBattery = Math.max(0, pvTotal - pvToGrid);
  const loadFromPvBattery = Math.max(0, loadTotal - loadFromGrid);
  const selfConsumption = pvTotal > 0 ? Math.min(100, (pvToLoadBattery / pvTotal) * 100) : 0;
  const selfSufficiency = loadTotal > 0 ? Math.min(100, (loadFromPvBattery / loadTotal) * 100) : 0;
  return {
    pv_production_kwh: roundEnergyKwh(pvTotal),
    pv_to_load_battery_kwh: roundEnergyKwh(pvToLoadBattery),
    pv_to_grid_kwh: roundEnergyKwh(pvToGrid),
    load_consumption_kwh: roundEnergyKwh(loadTotal),
    load_from_pv_battery_kwh: roundEnergyKwh(loadFromPvBattery),
    load_from_grid_kwh: roundEnergyKwh(loadFromGrid),
    self_consumption_percent: roundEnergyPct(selfConsumption),
    self_sufficiency_percent: roundEnergyPct(selfSufficiency),
  };
}

function analyticsFromBreakdown(b) {
  return {
    pv_production_kwh_today: b.pv_production_kwh,
    pv_to_load_battery_kwh_today: b.pv_to_load_battery_kwh,
    pv_to_grid_kwh_today: b.pv_to_grid_kwh,
    load_consumption_kwh_today: b.load_consumption_kwh,
    load_from_pv_battery_kwh_today: b.load_from_pv_battery_kwh,
    load_from_grid_kwh_today: b.load_from_grid_kwh,
    self_consumption_percent_today: b.self_consumption_percent,
    self_sufficiency_percent_today: b.self_sufficiency_percent,
  };
}

function energyBucketForDay(points, day) {
  const ds = startOfLocalDay(day).getTime();
  const de = endOfLocalDay(day).getTime();
  return {
    supply: {
      solar: roundEnergyKwh(dailyMaxInRange(points.pv, ds, de)),
      batteryDischarge: roundEnergyKwh(dailyMaxInRange(points.discharge, ds, de)),
      gridImport: roundEnergyKwh(dailyMaxInRange(points.grid, ds, de)),
    },
    usage: {
      load: roundEnergyKwh(dailyLoadKwhFromPoints(points, ds, de)),
      batteryCharge: roundEnergyKwh(dailyMaxInRange(points.charge, ds, de)),
      gridExport: roundEnergyKwh(dailyMaxInRange(points.feedIn, ds, de)),
    },
  };
}

function energyBucketSum(points, days) {
  const out = {
    supply: { solar: 0, batteryDischarge: 0, gridImport: 0 },
    usage: { load: 0, batteryCharge: 0, gridExport: 0 },
  };
  for (const day of days) {
    const b = energyBucketForDay(points, day);
    for (const k of Object.keys(out.supply)) out.supply[k] += b.supply[k];
    for (const k of Object.keys(out.usage)) out.usage[k] += b.usage[k];
  }
  for (const k of Object.keys(out.supply)) out.supply[k] = roundEnergyKwh(out.supply[k]);
  for (const k of Object.keys(out.usage)) out.usage[k] = roundEnergyKwh(out.usage[k]);
  return out;
}

function buildDaysInRange(start, end) {
  const days = [];
  const cursor = startOfLocalDay(start);
  const last = startOfLocalDay(end);
  while (cursor <= last) {
    days.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

function formatWeekdayLabel(d) {
  return d.toLocaleDateString(undefined, { weekday: "short" });
}

function formatMonthShortLabel(d) {
  return d.toLocaleDateString(undefined, { month: "short" });
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
  return polylinePath(pixelPts);
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

function interpolateSeriesAt(points, t, { allowBackfill = true } = {}) {
  if (!points.length) return null;
  if (t <= points[0].t) return allowBackfill ? points[0].v : null;
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
      if (v == null || Math.abs(v) < 0.001) return "";
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
  return filterStatisticsSpikes(
    rawPoints.map((p) => ({
      t: p.t,
      v: transformHistoryPoint(hass, entityId, p.v, spec),
    }))
  );
}

function interpolatePointsToPeriod(points, periodMs, originMs, endMs, { allowBackfill = true } = {}) {
  if (!points.length) return [];
  const sorted = [...points].sort((a, b) => a.t - b.t);
  const out = [];
  for (let t = originMs; t <= endMs; t += periodMs) {
    const v = interpolateSeriesAt(sorted, t, { allowBackfill });
    if (v != null) out.push({ t, v });
  }
  return out;
}

/** PV forecast overlay from Fox Plant native Solcast state only (no third-party HA integration). */
function buildForecastSeriesPoints(plantState, range, hass) {
  if (!statisticsSolcastForecastEnabled(plantState, hass)) return [];
  return nativeSolcastForecastPoints(plantState, range, hass);
}

function clampSocPercent(v) {
  if (!Number.isFinite(v)) return null;
  return Math.min(100, Math.max(0, Number(v)));
}

function buildSocHistoryPoints(hass, entityId, range, statsMap, hist) {
  const statRows = statsMap?.[entityId];
  let rawPoints;
  if (statRows?.length) {
    rawPoints = recorderStatsToPoints(statRows, range);
  } else {
    rawPoints = statisticsChartPoints(historyToPoints(historyRowsForEntity(hist, entityId)), range);
  }
  return rawPoints
    .map((p) => ({ t: p.t, v: clampSocPercent(p.v) }))
    .filter((p) => p.v != null);
}

function buildSocPowerPoints(hass, entityId, range, statsMap, hist) {
  const spec = { toKw: true };
  const statRows = statsMap?.[entityId];
  let rawPoints;
  if (statRows?.length) {
    rawPoints = recorderStatsToPoints(statRows, range).map((p) => ({
      t: p.t,
      v: transformHistoryPoint(hass, entityId, p.v, spec),
    }));
  } else {
    rawPoints = statisticsChartPoints(historyToPoints(historyRowsForEntity(hist, entityId)), range).map(
      (p) => ({ t: p.t, v: transformHistoryPoint(hass, entityId, p.v, spec) })
    );
  }
  return rawPoints
    .map((p) => ({ t: p.t, v: Math.abs(p.v) }))
    .filter((p) => Number.isFinite(p.v));
}

function batteryFlowModeAt(t, chargePts, dischargePts) {
  const ch = Math.abs(interpolateSeriesAt(chargePts, t) ?? 0);
  const dis = Math.abs(interpolateSeriesAt(dischargePts, t) ?? 0);
  if (ch > BATTERY_SOC_POWER_THRESHOLD_KW) return "charging";
  if (dis > BATTERY_SOC_POWER_THRESHOLD_KW) return "discharging";
  return "idle";
}

function splitSocSegmentsByMode(socPts, chargePts, dischargePts) {
  if (socPts.length < 2) return socPts.length ? [{ mode: "idle", pts: socPts }] : [];
  const segments = [];
  let mode = batteryFlowModeAt(socPts[0].t, chargePts, dischargePts);
  let pts = [socPts[0]];
  for (let i = 1; i < socPts.length; i++) {
    const p = socPts[i];
    const nextMode = batteryFlowModeAt(p.t, chargePts, dischargePts);
    if (nextMode !== mode) {
      if (pts.length >= 2) segments.push({ mode, pts });
      mode = nextMode;
      pts = [socPts[i - 1], p];
    } else {
      pts.push(p);
    }
  }
  if (pts.length >= 2) segments.push({ mode, pts });
  return segments;
}

function buildSocActivityBars(chargePts, dischargePts, range) {
  const bars = [];
  for (let t = range.tMin; t <= range.nowMs; t += STATISTICS_PERIOD_MS) {
    const ch = interpolateSeriesAt(chargePts, t) ?? 0;
    const dis = interpolateSeriesAt(dischargePts, t) ?? 0;
    if (ch > BATTERY_SOC_POWER_THRESHOLD_KW) {
      bars.push({ t, mode: "charging", intensity: Math.min(1, ch / 4) });
    } else if (dis > BATTERY_SOC_POWER_THRESHOLD_KW) {
      bars.push({ t, mode: "discharging", intensity: Math.min(1, dis / 4) });
    }
  }
  return bars;
}

function formatSocPercent(v) {
  return Number.isFinite(v) ? `${Math.round(v)}%` : "—";
}

function readLiveBatterySoc(hass, plant, plantState) {
  const entityId = resolveEntityMap(hass, plant, plantState).battery_soc;
  if (!entityId || !hass?.states?.[entityId]) return null;
  const st = hass.states[entityId];
  if (st.state === "unavailable" || st.state === "unknown" || st.state === "") return null;
  const n = parseFloat(st.state);
  if (!Number.isFinite(n)) return null;
  return clampSocPercent(n);
}

function resolveBatterySocDisplay(hass, plant, plantState, chart) {
  const live = readLiveBatterySoc(hass, plant, plantState);
  if (live != null) return live;
  const { socPts, range } = chart || {};
  if (!socPts?.length) return null;
  const atNow = clampSocPercent(interpolateSeriesAt(socPts, range?.nowMs ?? Date.now()));
  if (atNow != null) return atNow;
  return clampSocPercent(socPts[socPts.length - 1]?.v);
}

function fillSocAreaPath(pts, yBase) {
  if (pts.length < 2) return "";
  const line = statisticsLinePath(pts, pts.map((p) => ({ t: p.t })));
  if (!line) return "";
  const last = pts[pts.length - 1];
  const first = pts[0];
  return `${line} L${last.x.toFixed(2)},${yBase.toFixed(2)} L${first.x.toFixed(2)},${yBase.toFixed(2)} Z`;
}

async function fetchBatterySocChartSeries(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const socId = map.battery_soc;
  const chargeId = map.battery_charge;
  const dischargeId = map.battery_discharge;
  if (!socId) {
    return { empty: "Map battery SOC in FoxESS Modbus, then reload FoxESS Plant." };
  }
  const now = new Date();
  const start = startOfLocalDay(now);
  const range = getStatisticsDayRange(now);
  const entityIds = [socId, chargeId, dischargeId].filter(Boolean);
  const [statsMap, hist] = await Promise.all([
    fetchStatisticsDuring(hass, entityIds, start, now),
    fetchHistoryDuring(hass, entityIds, start, now),
  ]);
  const socPts = buildSocHistoryPoints(hass, socId, range, statsMap, hist);
  if (!socPts.length) {
    return {
      empty: `No SOC history for ${socId}. Enable the Recorder for battery_soc (5-minute statistics or state history).`,
    };
  }
  const chargePts = chargeId ? buildSocPowerPoints(hass, chargeId, range, statsMap, hist) : [];
  const dischargePts = dischargeId ? buildSocPowerPoints(hass, dischargeId, range, statsMap, hist) : [];
  return {
    range,
    socPts,
    chargePts,
    dischargePts,
    segments: splitSocSegmentsByMode(socPts, chargePts, dischargePts),
    activityBars: buildSocActivityBars(chargePts, dischargePts, range),
  };
}

function renderBatterySocChartHtml(chart, liveSocPct) {
  const { socPts, segments, activityBars, range } = chart;
  if (!socPts?.length) {
    return `<p class="placeholder chart-empty">No battery SOC history for today yet.</p>`;
  }
  const { width, height, pad, xTickHours, xTickCount, yTicks } = BATTERY_SOC_CHART_LAYOUT;
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const { tMin, tMax, nowMs } = range;
  const daySpan = tMax - tMin;
  const xScale = (t) => pad.l + ((t - tMin) / daySpan) * w;
  const yScale = (v) => pad.t + h - (v / 100) * h;
  const yBase = yScale(0);
  const displaySoc =
    liveSocPct != null ? liveSocPct : clampSocPercent(socPts[socPts.length - 1]?.v);
  const slotW = (w / (Math.ceil((range.nowMs - range.tMin) / STATISTICS_PERIOD_MS) || 1)) * 0.85;

  const grid = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${pad.l + w}" y2="${y.toFixed(1)}" class="soc-chart-grid"/>`;
    })
    .join("");

  const yLabels = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<text x="${(pad.l - 8).toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="end" class="soc-chart-axis-y">${yv}%</text>`;
    })
    .join("");

  const xTickSet = new Set(
    Array.from({ length: xTickCount }, (_, i) => tMin + i * xTickHours * 60 * 60 * 1000)
  );
  const xLabels = [];
  for (const xt of xTickSet) {
    const x = xScale(xt);
    xLabels.push(
      `<text x="${x.toFixed(1)}" y="${height - pad.b + 18}" text-anchor="middle" class="soc-chart-axis-x">${esc(formatChartTimeLabel(xt))}</text>`
    );
  }
  const nowX = xScale(nowMs);
  if (![...xTickSet].some((xt) => Math.abs(xt - nowMs) < 20 * 60 * 1000)) {
    xLabels.push(
      `<text x="${nowX.toFixed(1)}" y="${height - pad.b + 18}" text-anchor="middle" class="soc-chart-axis-x soc-chart-now-label">Now</text>`
    );
  }
  xLabels.push(
    `<line x1="${nowX.toFixed(1)}" y1="${pad.t}" x2="${nowX.toFixed(1)}" y2="${pad.t + h}" class="soc-chart-now-line"/>`
  );

  const activityRects = (activityBars || [])
    .map((bar) => {
      const cx = xScale(bar.t + STATISTICS_PERIOD_MS / 2);
      const barH = 8 + bar.intensity * 22;
      const fill =
        bar.mode === "charging"
          ? "rgba(61,220,132,0.12)"
          : "rgba(91,155,213,0.12)";
      return `<rect x="${(cx - slotW / 2).toFixed(2)}" y="${(yBase - barH).toFixed(2)}" width="${slotW.toFixed(2)}" height="${barH.toFixed(2)}" fill="${fill}" rx="1"/>`;
    })
    .join("");

  const fills = (segments || [])
    .map((seg) => {
      const colors = BATTERY_SOC_COLORS[seg.mode] || BATTERY_SOC_COLORS.idle;
      const pixelPts = seg.pts.map((p) => ({
        x: xScale(p.t),
        y: yScale(p.v),
        t: p.t,
        v: p.v,
      }));
      if (pixelPts.length < 2) return "";
      return `<path class="soc-chart-fill" d="${fillSocAreaPath(pixelPts, yBase)}" fill="${colors.fill}" stroke="none"/>`;
    })
    .join("");

  const lines = (segments || [])
    .map((seg) => {
      const colors = BATTERY_SOC_COLORS[seg.mode] || BATTERY_SOC_COLORS.idle;
      const pixelPts = seg.pts.map((p) => ({
        x: xScale(p.t),
        y: yScale(p.v),
        t: p.t,
        v: p.v,
      }));
      if (pixelPts.length < 2) return "";
      return `<path class="soc-chart-line" d="${statisticsLinePath(pixelPts, seg.pts)}" fill="none" stroke="${colors.line}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>`;
    })
    .join("");

  return `<div class="soc-chart-wrap" data-soc-chart="1">
<div class="soc-chart-head">
<div class="soc-chart-value">${esc(formatSocPercent(displaySoc))}</div>
<div class="soc-chart-legend" aria-hidden="true">
<span class="soc-chart-legend-item"><i style="background:${BATTERY_SOC_COLORS.charging.line}"></i>Charging</span>
<span class="soc-chart-legend-item"><i style="background:${BATTERY_SOC_COLORS.discharging.line}"></i>Discharging</span>
</div>
</div>
<div class="soc-chart-plot" data-pad-l="${pad.l}" data-pad-t="${pad.t}" data-pad-b="${pad.b}" data-plot-w="${w}" data-plot-h="${h}" data-t-min="${tMin}" data-t-max="${tMax}" data-now-ms="${nowMs}">
<svg class="soc-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Battery state of charge chart">
${grid}
${yLabels}
${activityRects}
${fills}
${lines}
${xLabels.join("")}
</svg>
<div class="soc-chart-hit" aria-hidden="true"></div>
<div class="soc-chart-crosshair" hidden><div class="soc-chart-spike"></div></div>
<div class="soc-chart-tooltip" hidden role="tooltip"></div>
</div>
</div>`;
}

function bindBatterySocChart(root, chart) {
  const wrap = root?.querySelector?.("[data-soc-chart]");
  if (!wrap || wrap.dataset.bound || !chart?.socPts?.length) return;
  const plot = wrap.querySelector(".soc-chart-plot");
  if (!plot) return;
  wrap.dataset.bound = "1";

  const padL = Number(plot.dataset.padL);
  const padT = Number(plot.dataset.padT);
  const padB = Number(plot.dataset.padB);
  const plotW = Number(plot.dataset.plotW);
  const tMin = Number(plot.dataset.tMin);
  const tMax = Number(plot.dataset.tMax);
  const daySpan = tMax - tMin;
  const svg = plot.querySelector(".soc-chart-svg");
  const hit = plot.querySelector(".soc-chart-hit");
  const crosshair = plot.querySelector(".soc-chart-crosshair");
  const tooltip = plot.querySelector(".soc-chart-tooltip");

  const showHover = (clientX) => {
    const t = Math.min(statisticsClientToTime(svg, clientX, padL, plotW, tMin, daySpan), tMax);
    const { scale, offsetX, offsetY } = statisticsPointerScale(svg);
    const xPx = padL + ((t - tMin) / daySpan) * plotW;
    const screenX = offsetX + xPx * scale;
    crosshair.hidden = false;
    crosshair.style.left = `${screenX}px`;
    crosshair.style.top = `${offsetY + padT * scale}px`;
    crosshair.style.bottom = `${offsetY + padB * scale}px`;

    const soc = clampSocPercent(interpolateSeriesAt(chart.socPts, t));
    const mode = batteryFlowModeAt(t, chart.chargePts, chart.dischargePts);
    const modeLabel =
      mode === "charging" ? "Charging" : mode === "discharging" ? "Discharging" : "Idle";
    const modeColor = (BATTERY_SOC_COLORS[mode] || BATTERY_SOC_COLORS.idle).line;
    tooltip.hidden = false;
    tooltip.innerHTML = `<div class="soc-chart-tooltip-time">${esc(formatStatisticsHoverTime(t))}</div>
<div class="soc-chart-tooltip-row"><span class="soc-chart-tooltip-label"><i class="soc-chart-tooltip-swatch" style="background:${modeColor}"></i>${esc(modeLabel)}</span><strong>${esc(formatSocPercent(soc))}</strong></div>`;
    const plotRect = plot.getBoundingClientRect();
    let left = screenX + 12;
    if (left + 180 > plotRect.width) left = screenX - 192;
    tooltip.style.left = `${Math.max(8, left)}px`;
    tooltip.style.top = "8px";
  };

  const hideHover = () => {
    crosshair.hidden = true;
    tooltip.hidden = true;
  };

  hit?.addEventListener("mousemove", (ev) => showHover(ev.clientX));
  hit?.addEventListener("mouseleave", hideHover);
  plot.addEventListener(
    "touchmove",
    (ev) => {
      if (ev.touches[0]) {
        ev.preventDefault();
        showHover(ev.touches[0].clientX);
      }
    },
    { passive: false }
  );
  plot.addEventListener("touchend", hideHover);
}

async function fetchStatisticsChartSeries(hass, plant, plantState, { dayOffset = 0 } = {}) {
  const map = resolveEntityMap(hass, plant, plantState);
  const specs = STATISTICS_CHART_SERIES.map((s) => ({ ...s, entity_id: map[s.key] })).filter(
    (s) => s.entity_id
  );
  if (!specs.length) {
    return { empty: "Map power entities in FoxESS Modbus, then reload FoxESS Plant." };
  }
  let forecastState = plantState;
  if (dayOffset === 0) {
    try {
      const fresh = await fetchPlantState(hass, plant.entry_id);
      if (fresh) forecastState = fresh;
    } catch {
      /* plant_state optional */
    }
  }
  const now = new Date();
  const day = startOfLocalDay(now);
  day.setDate(day.getDate() - Math.max(0, dayOffset));
  const range = getStatisticsDayRangeForDate(day, { asOf: dayOffset === 0 ? now : endOfLocalDay(day) });
  const fetchEnd = new Date(range.nowMs);
  const start = new Date(range.tMin);
  const entityIds = specs.map((s) => s.entity_id);
  const [statsMap, hist] = await Promise.all([
    fetchStatisticsDuring(hass, entityIds, start, fetchEnd),
    fetchHistoryDuring(hass, entityIds, start, fetchEnd),
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
  if (dayOffset === 0) {
    const fPoints = buildForecastSeriesPoints(forecastState, range, hass);
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
  return { series, range, forecastState, dayOffset };
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

function buildLastNDays(count = OVERVIEW_DAILY_DAYS) {
  const labels = [];
  const anchor = startOfLocalDay(new Date());
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(anchor);
    d.setDate(d.getDate() - i);
    labels.push(d);
  }
  return labels;
}

function formatDailyKwh(value) {
  if (value == null || !Number.isFinite(Number(value))) return "— kWh";
  return `${Number(value).toFixed(2)} kWh`;
}

function dailyProductionKwh(points, dayStartMs, dayEndMs) {
  return Math.round(dailyMaxInRange(points.pv, dayStartMs, dayEndMs) * 100) / 100;
}

function dailyConsumptionKwh(points, dayStartMs, dayEndMs) {
  const load =
    dailyMaxInRange(points.load, dayStartMs, dayEndMs) -
    dailyMaxInRange(points.discharge, dayStartMs, dayEndMs) +
    dailyMaxInRange(points.charge, dayStartMs, dayEndMs) +
    dailyMaxInRange(points.grid, dayStartMs, dayEndMs);
  return Math.round(Math.max(0, load) * 100) / 100;
}

function renderOverviewDailySparklineSvg(values, labels, accentColor) {
  const n = Math.min(values.length, labels.length);
  if (!n) return "";
  const width = 156;
  const height = 54;
  const pad = { l: 6, r: 6, t: 14, b: 12 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const dayFont = 6;
  const todayFont = 5.5;
  let yMax = 0.1;
  for (let i = 0; i < n; i++) yMax = Math.max(yMax, values[i] || 0);
  yMax *= 1.1;
  const slotW = w / n;
  const barW = Math.min(11, slotW * 0.52);
  const todayIdx = n - 1;
  const parts = [];
  const hits = [];
  for (let i = 0; i < n; i++) {
    const v = values[i] || 0;
    const cx = pad.l + i * slotW + slotW / 2;
    const bh = Math.max(2, (v / yMax) * h);
    const x = cx - barW / 2;
    const y = pad.t + h - bh;
    const fill = i === todayIdx ? accentColor : OVERVIEW_DAILY_COLORS.barMuted;
    const tip = formatDailyKwh(v);
    parts.push(
      `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${fill}"/>`
    );
    if (i === todayIdx) {
      parts.push(
        `<text x="${cx.toFixed(1)}" y="8" text-anchor="middle" class="overview-daily-today-mark" font-size="${todayFont}">Today</text>`
      );
      parts.push(
        `<line x1="${cx.toFixed(1)}" y1="9.5" x2="${cx.toFixed(1)}" y2="${(y - 1).toFixed(1)}" class="overview-daily-today-line"/>`
      );
    }
    parts.push(
      `<text x="${cx.toFixed(1)}" y="${(height - 4).toFixed(1)}" text-anchor="middle" class="overview-daily-day" font-size="${dayFont}">${esc(String(labels[i].getDate()))}</text>`
    );
    hits.push(
      `<rect class="overview-daily-bar-hit" x="${(pad.l + i * slotW).toFixed(1)}" y="${pad.t}" width="${slotW.toFixed(1)}" height="${(h + pad.b).toFixed(1)}" fill="transparent" data-value="${v}" aria-label="${esc(tip)}"/>`
    );
  }
  return `<div class="overview-daily-chart-wrap"><svg class="overview-daily-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><rect class="overview-daily-hover-col" visibility="hidden" fill="rgba(127,127,127,0.14)" pointer-events="none"/>${parts.join("")}${hits.join("")}</svg><div class="overview-daily-tooltip" hidden role="tooltip"></div></div>`;
}

function bindOverviewDailyCharts(root) {
  root?.querySelectorAll(".overview-daily-chart-wrap").forEach((wrap) => {
    if (wrap.dataset.bound === "1") return;
    wrap.dataset.bound = "1";
    const tooltip = wrap.querySelector(".overview-daily-tooltip");
    const svg = wrap.querySelector(".overview-daily-chart");
    const highlight = svg?.querySelector(".overview-daily-hover-col");
    if (!tooltip || !svg || !highlight) return;
    const hide = () => {
      tooltip.hidden = true;
      highlight.setAttribute("visibility", "hidden");
    };
    const show = (hit, clientX) => {
      const rect = wrap.getBoundingClientRect();
      const val = Number(hit.dataset.value);
      tooltip.textContent = formatDailyKwh(val);
      tooltip.hidden = false;
      tooltip.style.left = `${Math.max(8, Math.min(rect.width - 8, clientX - rect.left))}px`;
      tooltip.style.top = "0px";
      highlight.setAttribute("x", hit.getAttribute("x"));
      highlight.setAttribute("y", hit.getAttribute("y"));
      highlight.setAttribute("width", hit.getAttribute("width"));
      highlight.setAttribute("height", hit.getAttribute("height"));
      highlight.setAttribute("visibility", "visible");
    };
    wrap.addEventListener("mousemove", (ev) => {
      const hit = ev.target.closest?.(".overview-daily-bar-hit");
      if (hit && wrap.contains(hit)) show(hit, ev.clientX);
      else hide();
    });
    wrap.addEventListener("mouseleave", hide);
    wrap.addEventListener("click", (ev) => {
      if (ev.target.closest?.(".overview-daily-bar-hit")) ev.stopPropagation();
    });
  });
}

async function fetchFoxMirroredBarChart(hass, plant, plantState, period, offset = 0) {
  const now = new Date();
  const bounds = energyPeriodBounds(period, offset, now);
  const { start, end } = bounds;
  const { points, error } = await fetchEnergyHistoryPoints(hass, plant, plantState, start, end);
  if (!points) return { title: energyPeriodNavLabel(period, offset, now), svg: `<p class="placeholder chart-empty">${esc(error)}</p>` };

  if (period === "week") {
    const days = buildDaysInRange(start, end);
    const buckets = days.map((day) => energyBucketForDay(points, day));
    const labels = days.map(formatWeekdayLabel);
    return {
      title: energyPeriodNavLabel(period, offset, now),
      breakdown: computeEnergyBreakdown(points, days),
      svg: renderMirroredEnergyBarChart(buckets, labels),
    };
  }

  if (period === "month") {
    const days = buildDaysInRange(start, end);
    const buckets = days.map((day) => energyBucketForDay(points, day));
    const labels = days;
    return {
      title: energyPeriodNavLabel(period, offset, now),
      breakdown: computeEnergyBreakdown(points, days),
      svg: renderMirroredEnergyBarChart(buckets, labels),
    };
  }

  if (period === "year") {
    const labels = [];
    const buckets = [];
    for (let m = 0; m < 12; m++) {
      const monthStart = new Date(start.getFullYear(), m, 1);
      if (monthStart > end) break;
      const monthEnd = new Date(start.getFullYear(), m + 1, 0, 23, 59, 59, 999);
      const effectiveEnd = monthEnd > end ? end : monthEnd;
      const days = buildDaysInRange(monthStart, effectiveEnd);
      if (!days.length) continue;
      labels.push(formatMonthShortLabel(monthStart));
      buckets.push(energyBucketSum(points, days));
    }
    const allDays = buildDaysInRange(start, end);
    return {
      title: energyPeriodNavLabel(period, offset, now),
      breakdown: computeEnergyBreakdown(points, allDays),
      svg: renderMirroredEnergyBarChart(buckets, labels),
    };
  }

  const years = new Set();
  for (const key of ["pv", "feedIn", "load", "discharge", "charge", "grid"]) {
    for (const p of points[key] || []) years.add(new Date(p.t).getFullYear());
  }
  const yearList = Array.from(years).filter((y) => y >= 2000 && y <= now.getFullYear()).sort((a, b) => a - b);
  if (!yearList.length) yearList.push(now.getFullYear());
  const labels = yearList.map(String);
  const buckets = yearList.map((year) => {
    const yStart = new Date(year, 0, 1);
    const yEnd = year === now.getFullYear() ? end : new Date(year, 11, 31, 23, 59, 59, 999);
    return energyBucketSum(points, buildDaysInRange(yStart, yEnd));
  });
  const allDays = buildDaysInRange(start, end);
  return {
    title: "Total",
    breakdown: computeEnergyBreakdown(points, allDays),
    svg: renderMirroredEnergyBarChart(buckets, labels),
  };
}

async function fetchOverviewDailyEnergy(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const ent = {
    pv: map.solar_energy_today,
    load: map.load_energy_today,
    discharge: map.battery_discharge_today,
    charge: map.battery_charge_today,
    grid: map.grid_consumption_energy_today,
  };
  const ids = [ent.pv, ent.load, ent.discharge, ent.charge, ent.grid].filter(Boolean);
  const labels = buildLastNDays(OVERVIEW_DAILY_DAYS);
  if (!ids.length) {
    return { error: "Daily energy sensors not found. Reload FoxESS Plant after foxess_modbus is configured." };
  }
  const rangeStart = labels[0];
  const now = new Date();
  const hist = await fetchHistoryDuring(hass, ids, rangeStart, now);
  const points = {
    pv: historyToPoints(historyRowsForEntity(hist, ent.pv)),
    load: historyToPoints(historyRowsForEntity(hist, ent.load)),
    discharge: historyToPoints(historyRowsForEntity(hist, ent.discharge)),
    charge: historyToPoints(historyRowsForEntity(hist, ent.charge)),
    grid: historyToPoints(historyRowsForEntity(hist, ent.grid)),
  };
  const production = labels.map((day) => {
    const ds = startOfLocalDay(day).getTime();
    const de = endOfLocalDay(day).getTime();
    return dailyProductionKwh(points, ds, de);
  });
  const consumption = labels.map((day) => {
    const ds = startOfLocalDay(day).getTime();
    const de = endOfLocalDay(day).getTime();
    return dailyConsumptionKwh(points, ds, de);
  });
  return { labels, production, consumption };
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
    const isForecast = s.id === "forecast" || s.legendGroup === "forecast";
    const clipEnd = isForecast ? tMax : nowMs;
    const clipped = s.points.filter((p) => p.t >= tMin && p.t <= clipEnd);
    let segmentGroups;
    if (isForecast && clipped.length >= 2) {
      const past = clipped.filter((p) => p.t <= nowMs);
      const future = clipped.filter((p) => p.t >= nowMs);
      segmentGroups = [];
      if (past.length >= 2) segmentGroups.push({ pts: past, dash: "" });
      if (future.length >= 2) {
        const futurePts =
          past.length && past[past.length - 1].t < nowMs
            ? [past[past.length - 1], ...future.filter((p) => p.t > past[past.length - 1].t)]
            : future;
        if (futurePts.length >= 2) segmentGroups.push({ pts: futurePts, dash: "5 4" });
      }
      if (!segmentGroups.length) segmentGroups.push({ pts: clipped, dash: "" });
    } else {
      const segmentPoints = s.connectGaps ? [clipped] : splitStatisticsSegments(clipped);
      segmentGroups = segmentPoints.map((pts) => ({ pts, dash: "" }));
    }
    const segments = segmentGroups.map(({ pts, dash }) => ({
      timePts: pts,
      pixelPts: pts.map((p) => ({ x: xScale(p.t), y: yScale(p.v), t: p.t, v: p.v })),
      dash,
    }));
    return { ...s, segments, isForecast };
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
            `<path class="statistics-line${seg.dash ? " statistics-line-forecast-future" : ""}" data-series-id="${esc(s.id)}" data-legend-group="${esc(s.legendGroup || "")}" d="${statisticsLinePath(seg.pixelPts, seg.timePts)}" fill="none" stroke="${s.color}" stroke-width="${s.lineWidth || 1.2}" stroke-linecap="round" stroke-linejoin="round"${seg.dash ? ` stroke-dasharray="${seg.dash}"` : ""}/>`
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
    const t = Math.min(statisticsClientToTime(svg, clientX, padL, plotW, tMin, daySpan), tMax);
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

function renderMirroredEnergyBarChart(buckets, labels, { height = 300 } = {}) {
  const n = buckets.length;
  if (!n) return `<p class="placeholder chart-empty">No energy history in this period.</p>`;
  const width = 1000;
  const pad = { l: 44, r: 12, t: 24, b: 42 };
  const plotH = height - pad.t - pad.b;
  const midY = pad.t + plotH / 2;
  const halfH = plotH / 2 - 6;
  const w = width - pad.l - pad.r;
  let maxVal = 0.5;
  for (const b of buckets) {
    const supply = FOX_SUPPLY_SERIES.reduce((s, spec) => s + (b.supply?.[spec.key] || 0), 0);
    const usage = FOX_USAGE_SERIES.reduce((s, spec) => s + (b.usage?.[spec.key] || 0), 0);
    maxVal = Math.max(maxVal, supply, usage);
  }
  maxVal *= 1.12;
  const yScale = (v) => (v / maxVal) * halfH;
  const groupW = w / n;
  const barW = Math.min(28, groupW * 0.62);
  const parts = [];
  for (const yv of [maxVal, maxVal / 2]) {
    const up = midY - yScale(yv);
    const down = midY + yScale(yv);
    parts.push(`<line x1="${pad.l}" y1="${up.toFixed(1)}" x2="${pad.l + w}" y2="${up.toFixed(1)}" class="fox-energy-grid"/>`);
    parts.push(`<line x1="${pad.l}" y1="${down.toFixed(1)}" x2="${pad.l + w}" y2="${down.toFixed(1)}" class="fox-energy-grid"/>`);
    parts.push(
      `<text x="${pad.l - 8}" y="${(up + 4).toFixed(1)}" text-anchor="end" class="fox-energy-axis">${esc(String(Math.round(yv)))}</text>`
    );
    parts.push(
      `<text x="${pad.l - 8}" y="${(down + 4).toFixed(1)}" text-anchor="end" class="fox-energy-axis">${esc(String(Math.round(yv)))}</text>`
    );
  }
  parts.push(`<text x="14" y="${(pad.t + plotH / 2).toFixed(1)}" class="fox-energy-y-label" transform="rotate(-90 14 ${(pad.t + plotH / 2).toFixed(1)})">kWh</text>`);
  parts.push(`<line x1="${pad.l}" y1="${midY.toFixed(1)}" x2="${pad.l + w}" y2="${midY.toFixed(1)}" class="fox-energy-zero"/>`);

  buckets.forEach((bucket, i) => {
    const cx = pad.l + i * groupW + groupW / 2;
    let y = midY;
    for (const spec of FOX_SUPPLY_SERIES) {
      const v = bucket.supply?.[spec.key] || 0;
      if (v <= 0) continue;
      const bh = yScale(v);
      y -= bh;
      parts.push(
        `<rect x="${(cx - barW / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${spec.color}" opacity="0.95"/>`
      );
    }
    y = midY;
    for (const spec of FOX_USAGE_SERIES) {
      const v = bucket.usage?.[spec.key] || 0;
      if (v <= 0) continue;
      const bh = yScale(v);
      parts.push(
        `<rect x="${(cx - barW / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${spec.color}" opacity="0.95"/>`
      );
      y += bh;
    }
    if (n <= 16 || i % Math.ceil(n / 10) === 0 || i === n - 1) {
      const lbl = labels[i] instanceof Date ? formatChartDayLabel(labels[i]) : String(labels[i]);
      parts.push(`<text x="${cx.toFixed(1)}" y="${height - 12}" text-anchor="middle" class="fox-energy-axis">${esc(lbl)}</text>`);
    }
  });

  const supplyLegend = FOX_SUPPLY_SERIES.map(
    (s) => `<span class="fox-energy-legend-item"><i style="background:${s.color}"></i>${esc(s.label)}</span>`
  ).join("");
  const usageLegend = FOX_USAGE_SERIES.map(
    (s) => `<span class="fox-energy-legend-item"><i style="background:${s.color}"></i>${esc(s.label)}</span>`
  ).join("");

  return `<div class="fox-energy-chart-wrap" data-fox-energy-chart="1">
<div class="fox-energy-legend">
<div class="fox-energy-legend-row"><span class="fox-energy-legend-heading">SUPPLY</span>${supplyLegend}</div>
<div class="fox-energy-legend-row"><span class="fox-energy-legend-heading">USAGE</span>${usageLegend}</div>
</div>
<svg class="fox-energy-mirror-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Energy supply and usage chart">${parts.join("")}</svg>
</div>`;
}

function resolveEnergyHistoryEntities(map) {
  return {
    pv: map.solar_energy_today,
    feedIn: map.feed_in_energy_today,
    load: map.load_energy_today,
    discharge: map.battery_discharge_today,
    charge: map.battery_charge_today,
    grid: map.grid_consumption_energy_today,
  };
}

async function fetchEnergyHistoryPoints(hass, plant, plantState, rangeStart, rangeEnd) {
  const map = resolveEntityMap(hass, plant, plantState);
  const ent = resolveEnergyHistoryEntities(map);
  const ids = [ent.pv, ent.feedIn, ent.load, ent.discharge, ent.charge, ent.grid].filter(Boolean);
  if (!ids.length) return { ent, points: null, error: "Daily energy sensors not found. Reload FoxESS Plant." };
  const hist = await fetchHistoryDuring(hass, ids, rangeStart, rangeEnd);
  const points = {
    pv: historyToPoints(historyRowsForEntity(hist, ent.pv)),
    feedIn: historyToPoints(historyRowsForEntity(hist, ent.feedIn)),
    load: historyToPoints(historyRowsForEntity(hist, ent.load)),
    discharge: historyToPoints(historyRowsForEntity(hist, ent.discharge)),
    charge: historyToPoints(historyRowsForEntity(hist, ent.charge)),
    grid: historyToPoints(historyRowsForEntity(hist, ent.grid)),
  };
  return { ent, points };
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

function resolveFlowScenePeriodFromSun(hass) {
  const sun = hass?.states?.["sun.sun"];
  if (!sun?.state || sun.state === "unknown" || sun.state === "unavailable") return null;
  return sun.state === "above_horizon" ? "day" : "night";
}

/** Parse CSS color to relative luminance (0–1); higher = lighter background. */
function cssColorLuminance(color) {
  const raw = String(color || "").trim();
  if (!raw) return null;
  let r = 0;
  let g = 0;
  let b = 0;
  const hex = raw.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const h = hex[1].length === 3
      ? hex[1].split("").map((c) => c + c).join("")
      : hex[1];
    r = parseInt(h.slice(0, 2), 16);
    g = parseInt(h.slice(2, 4), 16);
    b = parseInt(h.slice(4, 6), 16);
  } else {
    const rgb = raw.match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i);
    if (!rgb) return null;
    r = Number(rgb[1]);
    g = Number(rgb[2]);
    b = Number(rgb[3]);
  }
  const lin = (c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** True when Home Assistant UI is in dark mode (Fox _dark art + black stage). */
function resolveHaUiDark(hass) {
  if (typeof hass?.themes?.darkMode === "boolean") {
    return hass.themes.darkMode;
  }
  try {
    const root = document.documentElement;
    const bg = getComputedStyle(root).getPropertyValue("--primary-background-color").trim();
    const lum = cssColorLuminance(bg);
    if (lum != null) return lum < 0.45;
  } catch (_) {
    /* panel may run before theme vars are ready */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function normalizeFlowSceneTheme(theme) {
  if (!theme || typeof theme !== "string") return null;
  if (FLOW_SCENE_BG_THEMES.has(theme)) return theme;
  if (theme.startsWith("day_")) return "day_dark";
  if (theme.startsWith("night_")) return "night_dark";
  return null;
}

function resolveFlowSceneBgTheme(hass, plantState) {
  const period = resolveFlowScenePeriodFromSun(hass)
    || (() => {
      const t = normalizeFlowSceneTheme(plantState?.flow_scene_theme);
      if (!t) return null;
      return t.startsWith("day_") ? "day" : "night";
    })()
    || "day";
  const suffix = resolveHaUiDark(hass) ? "dark" : "light";
  return `${period}_${suffix}`;
}

/** Backdrop and overlays share the same Fox UI-theme + sun variant. */
function flowSceneOverlayTheme(bgTheme) {
  return bgTheme;
}

/** Baked sky+house at 1024×1017 — PV/AIO scene layers unchanged (tuned paths). */
function flowSceneLayerUrl(layer, bgTheme, overlayTheme = flowSceneOverlayTheme(bgTheme)) {
  if (layer === "backdrop") {
    return `/foxess_plant_panel/flow_home_bg_scene_${bgTheme}.png?v=${FLOW_SCENE_ASSET_VER}`;
  }
  const theme = overlayTheme;
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
const DEVICE_EVO_IMAGE_STATIC = "/foxess_plant_panel/evo10.png?v=15";
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

function tripleSocBatteryFillMarkup(liveSoc) {
  const live = Math.max(0, Math.min(100, Math.round(liveSoc ?? 0)));
  if (live >= 99) {
    return `<div class="triple-soc-battery-fill is-full"></div>`;
  }
  const h = Math.max(4, live);
  return `<div class="triple-soc-battery-fill" style="height:max(4px,calc((100% - 8px) * ${h} / 100))"></div>`;
}

function validateSocLimits(draft, liveSoc) {
  const errors = [];
  const warnings = [];
  if (!draft) return { errors: ["SOC limits unavailable."], warnings: [] };
  const min = Math.round(Number(draft.min_soc));
  const mid = Math.round(Number(draft.min_soc_on_grid));
  const max = Math.round(Number(draft.max_soc));
  if (![min, mid, max].every((v) => Number.isFinite(v))) {
    return { errors: ["Enter a whole-number percentage for each SOC limit."], warnings: [] };
  }
  if (min < SOC_MIN_PCT || mid < SOC_MIN_PCT || max < SOC_MIN_PCT) {
    errors.push(`All SOC limits must be at least ${SOC_MIN_PCT}%.`);
  }
  if (min > 100 || mid > 100 || max > 100) {
    errors.push("SOC limits cannot exceed 100%.");
  }
  if (min > mid) {
    errors.push(`Off-grid min (${min}%) must be ≤ system min (${mid}%).`);
  }
  if (mid > max) {
    errors.push(`System min (${mid}%) must be ≤ system max (${max}%).`);
  }
  const live = Math.ceil(Number(liveSoc));
  if (Number.isFinite(live) && live > 0 && max < live) {
    warnings.push(
      `System max (${max}%) is below the current battery level (${live}%). The inverter may reject this — Save will show the error if it does.`
    );
  }
  return { errors, warnings };
}

function renderSocFeedbackHtml(validation, saveError) {
  const parts = [];
  if (validation?.errors?.length) {
    parts.push(
      `<div class="soc-validation" role="alert">${validation.errors.map((msg) => `<p>${esc(msg)}</p>`).join("")}</div>`
    );
  }
  if (validation?.warnings?.length) {
    parts.push(
      `<div class="soc-validation warn" role="status">${validation.warnings.map((msg) => `<p>${esc(msg)}</p>`).join("")}</div>`
    );
  }
  if (saveError) {
    parts.push(`<div class="soc-validation" role="alert"><p>${esc(saveError)}</p></div>`);
  }
  return parts.join("");
}

/** Map pointer X on the track to an SOC % (track left/right = 0/100 visually). */
function socPctFromTrackPointer(clientX, trackRect, grabOffset = 0) {
  if (!trackRect?.width) return SOC_MIN_PCT;
  const pointerPct = ((clientX - trackRect.left) / trackRect.width) * 100;
  return Math.round(Math.max(SOC_MIN_PCT, Math.min(100, pointerPct + grabOffset)));
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
  position: relative;
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
.panel-build-footer {
  position: absolute; right: 12px; bottom: 8px; z-index: 1;
  margin: 0; padding: 0;
  font-size: 9px; line-height: 1.3;
  color: var(--secondary-text-color); opacity: 0.42;
  letter-spacing: 0.02em; white-space: nowrap;
  pointer-events: none;
}
.panel-stale-banner { margin-bottom: 14px; }
.overview-status-block { margin-top: 12px; }
.overview-status-row {
  display: flex; align-items: center; flex-wrap: wrap; gap: 6px 8px; line-height: 1.35;
}
.fox-pill {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 5px 14px; border-radius: 999px;
  font-size: 13px; font-weight: 700; line-height: 1.2;
  letter-spacing: -0.01em; white-space: nowrap;
}
.overview-fox-status.fox-pill.is-normal { background: #569e5c; color: #fff; }
.overview-fox-status.fox-pill.is-fault { background: #c62828; color: #fff; }
.overview-fox-status.fox-pill.is-checking { background: #5c6370; color: #fff; }
.overview-fox-status.fox-pill.is-offgrid { background: #e6a817; color: #1a1a1a; }
.overview-fox-status.fox-pill.is-default { background: var(--secondary-background-color); color: var(--primary-text-color); }
.overview-work-mode.fox-pill.work-self-use { background: #f4d05d; color: #1a1a1a; }
.overview-work-mode.fox-pill.work-feed-in { background: #7eb8ff; color: #12253d; }
.overview-work-mode.fox-pill.work-back-up { background: #90a4ae; color: #fff; }
.overview-work-mode.fox-pill.work-force-charge { background: #7e57c2; color: #fff; }
.overview-work-mode.fox-pill.work-force-discharge { background: #ef6c57; color: #fff; }
.overview-work-mode.fox-pill.work-default { background: #f4d05d; color: #1a1a1a; }
.overview-status-row .mode-pill { flex-shrink: 0; }
.overview-control-hint { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
.overview-weather {
  display: flex; align-items: center; gap: 6px; margin-top: 8px;
  font-size: 14px; font-weight: 600; color: var(--primary-text-color); line-height: 1.2;
}
.overview-weather-icon { width: 18px; height: 18px; flex-shrink: 0; display: block; }
.overview-weather-temp { letter-spacing: -0.01em; }
.overview-weather-label { font-size: 13px; font-weight: 500; color: var(--secondary-text-color); }
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
.overview-hero-scene { width: 100%; max-width: none; margin: 0; min-width: 0; }
.overview-hero-scene .scene-card--fox-flow { margin-bottom: 0; width: 100%; }
.overview-hero-daily {
  display: flex; flex-direction: column; gap: 12px;
  min-width: 0;
}
.overview-stats-row {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px;
  margin-bottom: 14px; min-width: 0;
}
.overview-daily-card {
  background: var(--card-background-color); border-radius: var(--fp-radius);
  border: 1px solid var(--divider-color, transparent);
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06));
  padding: 14px 14px 10px; min-width: 0; text-align: left;
  cursor: pointer; font-family: inherit; color: inherit;
}
.overview-daily-card:hover { background: var(--secondary-background-color); }
.overview-daily-card:has(.overview-daily-chart-wrap:hover) { background: var(--card-background-color); }
.overview-daily-hover-col { pointer-events: none; }
.overview-daily-head {
  display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px;
}
.overview-daily-title {
  font-size: 12px; font-weight: 600; color: var(--secondary-text-color); letter-spacing: 0.01em;
}
.overview-daily-chev { font-size: 16px; line-height: 1; color: var(--secondary-text-color); opacity: 0.55; }
.overview-daily-value {
  font-size: 22px; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 8px; line-height: 1.15;
}
.overview-daily-chart-wrap { position: relative; width: 100%; }
.overview-daily-chart { width: 100%; height: auto; display: block; }
.overview-daily-bar-hit { cursor: default; pointer-events: all; }
.overview-daily-tooltip {
  position: absolute; z-index: 2; pointer-events: none;
  transform: translate(-50%, calc(-100% - 4px));
  padding: 5px 9px; border-radius: 8px; font-size: 11px; font-weight: 600; line-height: 1.2;
  white-space: nowrap; color: var(--primary-text-color);
  background: var(--card-background-color);
  border: 1px solid var(--divider-color, rgba(127,127,127,0.35));
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
}
.overview-daily-tooltip[hidden] { display: none !important; }
.overview-daily-today-mark {
  font-weight: 600; fill: var(--secondary-text-color);
}
.overview-daily-today-line { stroke: rgba(127,127,127,0.35); stroke-width: 0.75; }
.overview-daily-day { fill: var(--secondary-text-color); opacity: 0.85; }
.overview-daily-loading {
  font-size: 13px; color: var(--secondary-text-color); padding: 24px 14px; text-align: center;
}
.overview-daily-empty {
  font-size: 12px; color: var(--secondary-text-color); line-height: 1.45; padding: 8px 0 0;
}
.breakdown-card { margin-top: 14px; padding-bottom: 8px; }
.statistics-card { padding-bottom: 16px; }
.statistics-card .card-title { margin-bottom: 12px; }
.soc-chart-card { padding-bottom: 16px; }
.soc-chart-card .card-title { margin-bottom: 8px; }
.soc-chart-wrap {
  position: relative; width: 100%; font-family: "Segoe UI", Arial, sans-serif;
}
.soc-chart-head {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  margin-bottom: 10px; flex-wrap: wrap;
}
.soc-chart-value {
  font-size: 22px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
}
.soc-chart-legend {
  display: flex; flex-wrap: wrap; gap: 10px 14px; align-items: center;
  font-size: 11px; color: var(--secondary-text-color); margin-top: 6px;
}
.soc-chart-legend-item {
  display: inline-flex; align-items: center; gap: 6px;
}
.soc-chart-legend-item i {
  width: 14px; height: 3px; border-radius: 1px; display: inline-block;
}
.soc-chart-plot { position: relative; width: 100%; }
.soc-chart-svg { width: 100%; height: 300px; display: block; }
.soc-chart-grid { stroke: rgba(127,127,127,0.12); stroke-width: 1; }
.soc-chart-axis-x, .soc-chart-axis-y {
  fill: var(--secondary-text-color); font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.soc-chart-now-label { font-weight: 600; fill: var(--primary-text-color); }
.soc-chart-now-line { stroke: rgba(127,127,127,0.28); stroke-width: 1; stroke-dasharray: 3 3; }
.soc-chart-hit { position: absolute; inset: 0; cursor: crosshair; }
.soc-chart-crosshair {
  position: absolute; top: 0; bottom: 40px; width: 1px; pointer-events: none;
  transform: translateX(-0.5px);
}
.soc-chart-spike {
  width: 1px; height: 100%; background: rgba(127,127,127,0.35);
}
.soc-chart-tooltip {
  position: absolute; z-index: 4; min-width: 160px; padding: 8px 10px; border-radius: 8px;
  pointer-events: none; background: var(--card-background-color, #1c1c1c);
  border: 1px solid rgba(127,127,127,0.35);
  box-shadow: 0 4px 16px rgba(0,0,0,0.28);
  font-size: 12px; color: var(--primary-text-color);
}
.soc-chart-tooltip-time {
  font-size: 11px; color: var(--secondary-text-color); margin-bottom: 6px;
}
.soc-chart-tooltip-row {
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
}
.soc-chart-tooltip-label {
  display: inline-flex; align-items: center; gap: 6px;
}
.soc-chart-tooltip-swatch {
  width: 10px; height: 10px; border-radius: 2px; display: inline-block;
}
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
.energy-period-tabs {
  display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: nowrap;
  padding: 4px; border-radius: 12px;
  background: var(--secondary-background-color, rgba(127,127,127,0.12));
  border: 1px solid var(--divider-color, transparent);
}
.energy-period-tabs button {
  flex: 1; min-width: 0; padding: 10px 8px; border-radius: 10px; border: none;
  background: transparent; color: var(--secondary-text-color); font-family: inherit;
  font-size: 13px; font-weight: 600; cursor: pointer;
}
.energy-period-tabs button.active {
  color: var(--primary-text-color);
  background: var(--card-background-color);
  box-shadow: 0 1px 3px rgba(0,0,0,0.18);
}
.energy-date-nav {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  margin: 0 0 14px; min-height: 40px;
}
.energy-date-nav button {
  width: 36px; height: 36px; border-radius: 10px; border: 1px solid var(--divider-color);
  background: var(--card-background-color); color: var(--primary-text-color);
  font-size: 20px; line-height: 1; cursor: pointer; font-family: inherit;
}
.energy-date-nav button:disabled { opacity: 0.35; cursor: default; }
.energy-date-label { font-size: 15px; font-weight: 600; text-align: center; min-width: 180px; }
.energy-analysis-card { margin-top: 0; padding: 14px 16px 10px; }
.breakdown-card { margin-top: 14px; }
.energy-chart-card { margin-top: 14px; }
.fox-energy-chart-wrap { width: 100%; }
.fox-energy-mirror-chart { width: 100%; height: 300px; display: block; }
.fox-energy-legend { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.fox-energy-legend-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; font-size: 11px; }
.fox-energy-legend-heading { font-weight: 700; font-size: 10px; letter-spacing: 0.04em; color: var(--secondary-text-color); margin-right: 4px; }
.fox-energy-legend-item { display: inline-flex; align-items: center; gap: 5px; color: var(--primary-text-color); }
.fox-energy-legend-item i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.fox-energy-grid { stroke: rgba(127,127,127,0.12); stroke-width: 1; stroke-dasharray: 3 4; }
.fox-energy-zero { stroke: rgba(127,127,127,0.28); stroke-width: 1; }
.fox-energy-axis { fill: var(--secondary-text-color); font-size: 11px; }
.fox-energy-y-label { fill: var(--secondary-text-color); font-size: 12px; font-weight: 600; text-anchor: middle; }
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
  display: block; width: 100%;
}
.fox-flow-scene--ha-dark {
  background: ${FLOW_SCENE_CANVAS_BG_DARK};
}
.fox-flow-scene--ha-light {
  background: ${FLOW_SCENE_CANVAS_BG_LIGHT};
}
.fox-flow-stage {
  position: relative; width: 100%;
}
.fox-flow-scene--ha-dark .fox-flow-stage {
  background: ${FLOW_SCENE_CANVAS_BG_DARK};
}
.fox-flow-scene--ha-light .fox-flow-stage {
  background: ${FLOW_SCENE_CANVAS_BG_LIGHT};
}
.fox-flow-stage::before {
  content: ""; display: block; width: 100%; padding-top: 99.31640625%;
}
.overview-hero-row .overview-hero-scene .fox-flow-scene,
.overview-hero-row .overview-hero-scene .fox-flow-stage {
  width: 100%; max-width: none; margin: 0; box-sizing: border-box;
}
.fox-flow-layer {
  position: absolute; pointer-events: none; user-select: none;
}
.fox-flow-layer-backdrop,
.fox-flow-layer-pv,
.fox-flow-layer-aio {
  inset: 0; width: 100%; height: 100%;
  object-fit: contain; object-position: center bottom;
  image-rendering: auto;
}
.fox-flow-layer-backdrop { z-index: 0; }
.fox-flow-layer-pv,
.fox-flow-layer-aio { z-index: 2; }
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
/* Day sky is light — solar label sits on the backdrop, not the dark house stage */
.fox-flow-scene--day .fox-flow-badge-solar .fox-flow-badge-label {
  color: rgba(30, 30, 30, 0.72);
}
.fox-flow-scene--day .fox-flow-badge-solar .fox-flow-badge-value {
  color: #1a1a1a;
}
.fox-flow-scene--night .fox-flow-badge-solar .fox-flow-badge-label {
  color: rgba(255, 255, 255, 0.62);
}
.fox-flow-scene--night .fox-flow-badge-solar .fox-flow-badge-value {
  color: #fff;
}
.fox-flow-badge-grid { left: 4%; bottom: 6%; align-items: flex-start; }
.fox-flow-badge-battery { left: 50%; bottom: 6%; transform: translateX(-50%); }
.fox-flow-badge-home { right: 4%; bottom: 6%; align-items: flex-end; }
.flow-path { fill: none; stroke-linecap: round; stroke-linejoin: round; }
.flow-path-idle { opacity: 1; }
.flow-path-idle-outline { opacity: 1; pointer-events: none; }
.flow-comet { fill: none; stroke-linejoin: round; pointer-events: none; }
.flow-comet-glow { opacity: 0.48; }
.flow-comet-pulse { opacity: 1; }
.flow-comet-pulse.flow-solar { filter: drop-shadow(0 0 5px rgba(255, 196, 0, 0.95)); }
.flow-comet-pulse.flow-grid { filter: drop-shadow(0 0 5px rgba(61, 154, 255, 0.95)); }
.flow-comet-pulse.flow-export { filter: drop-shadow(0 0 5px rgba(192, 106, 255, 0.95)); }
.flow-comet-pulse.flow-battery { filter: drop-shadow(0 0 6px rgba(0, 255, 102, 0.95)); }
.flow-comet-pulse { animation: flow-comet-pulse-fwd 1.75s linear infinite; }
.flow-comet-glow { animation: flow-comet-pulse-fwd 1.75s linear infinite; }
.flow-comet-pulse.flow-solar,
.flow-comet-glow.flow-solar { animation-duration: 1.55s; }
.flow-comet-pulse.reverse,
.flow-comet-glow.reverse { animation-name: flow-comet-pulse-rev; }
.flow-hub-dot.active { filter: drop-shadow(0 0 10px rgba(0, 255, 102, 0.95)); }
@keyframes flow-comet-pulse-fwd {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: -100; }
}
@keyframes flow-comet-pulse-rev {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: 100; }
}
.device-header { margin-bottom: 8px; }
.device-header h1 { margin-bottom: 4px; }
.device-model { margin: 0; font-size: 14px; color: var(--secondary-text-color); }
.device-fox-pill {
  display: inline-flex; align-items: center; padding: 5px 14px; border-radius: 999px;
  margin-bottom: 12px; font-size: 13px; font-weight: 700;
}
.device-fox-pill.is-normal { background: #569e5c; color: #fff; }
.device-fox-pill.is-fault { background: #c62828; color: #fff; }
.device-fox-pill.is-checking { background: #5c6370; color: #fff; }
.device-fox-pill.is-offgrid { background: #e6a817; color: #1a1a1a; }
.device-fox-pill.is-default { background: var(--secondary-background-color); color: var(--primary-text-color); }
.device-hero {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  margin: 4px 0 18px; padding: 0 16px; width: 100%; box-sizing: border-box;
}
.device-hero-img {
  max-width: min(200px, 62vw); max-height: 220px; width: auto; height: auto;
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
.device-card--pv { align-items: stretch; justify-content: center; min-height: 100%; }
.device-card--battery { align-items: stretch; justify-content: flex-start; }
.device-pv-gauges {
  width: 100%; display: flex; flex-wrap: nowrap; align-items: flex-start;
  box-sizing: border-box;
}
.device-pv-gauges--single { justify-content: center; }
.device-pv-gauges--single .device-pv-wrap { flex: 0 1 auto; width: 100%; max-width: 160px; }
.device-pv-gauges--dual {
  justify-content: center; gap: 4px 8px; padding: 0 2px;
}
.device-pv-gauges--dual .device-pv-wrap {
  flex: 1 1 0; min-width: 0; max-width: 50%;
}
.device-pv-gauges--dual .device-pv-gauge { max-width: 108px; }
.device-pv-gauges--dual .device-pv-value { font-size: 15px; }
.device-pv-gauges--dual .device-pv-label { font-size: 11px; margin-top: 2px; }
.device-pv-wrap { width: 100%; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.device-pv-gauge {
  position: relative; width: 100%; max-width: 140px; aspect-ratio: 100 / 104; flex-shrink: 0;
}
.device-pv-gauge svg { width: 100%; height: 100%; display: block; }
.device-pv-readout {
  position: absolute; left: 0; right: 0; top: 40%; transform: translateY(-50%);
  text-align: center; min-width: 0; padding: 0 10px; box-sizing: border-box; pointer-events: none;
}
.device-pv-value { font-size: 17px; font-weight: 700; line-height: 1.2; letter-spacing: -0.02em; margin: 0; }
.device-pv-label { font-size: 12px; color: var(--secondary-text-color); font-weight: 500; line-height: 1.3; margin: 3px 0 0; }
.device-pv-cap {
  font-size: 10px; color: var(--secondary-text-color); line-height: 1.25; margin: 0;
  text-align: center; width: 100%; opacity: 0.9;
}
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
.device-param-sections { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.device-param-section {
  border-radius: var(--fp-radius);
  border: 1px solid var(--divider-color, transparent);
  background: var(--card-background-color, rgba(127,127,127,0.06));
  overflow: hidden;
}
.device-param-summary {
  width: 100%; border: none; background: transparent; cursor: pointer;
  padding: 14px 18px; font-weight: 600; font-size: 15px; text-align: left;
  display: flex; justify-content: space-between; align-items: center;
  color: inherit; font-family: inherit;
}
.device-param-section.is-open > .device-param-summary { border-bottom: 1px solid var(--divider-color); }
.device-param-summary::after { content: "›"; transform: rotate(90deg); opacity: 0.45; font-size: 18px; transition: transform 0.15s; }
.device-param-section.is-open > .device-param-summary::after { transform: rotate(-90deg); }
.device-param-section .entity-list { border: none; border-radius: 0; }
.device-param-table-wrap { overflow-x: auto; }
.device-param-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.device-param-table th, .device-param-table td { padding: 10px 14px; text-align: right; border-bottom: 1px solid var(--divider-color); white-space: nowrap; }
.device-param-table th:first-child, .device-param-table td:first-child { text-align: left; }
.device-param-table tr:last-child td { border-bottom: none; }
.device-param-table th { color: var(--secondary-text-color); font-weight: 500; font-size: 12px; }
.device-param-empty { padding: 14px 18px; font-size: 13px; color: var(--secondary-text-color); margin: 0; }
.device-param-updated { text-align: center; font-size: 12px; color: var(--secondary-text-color); margin-top: 16px; }
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
.field-hint { font-size: 12px; color: var(--secondary-text-color); margin: 0 0 8px; line-height: 1.45; }
.field-link { color: var(--fp-accent); text-decoration: none; }
.field-link:hover { text-decoration: underline; }
.pv-range-row { display: flex; align-items: center; gap: 12px; }
.pv-range-row input[type="range"] { flex: 1; min-width: 0; accent-color: var(--fp-accent); }
.pv-range-value { min-width: 56px; font-size: 14px; font-variant-numeric: tabular-nums; text-align: right; color: var(--primary-text-color); }
.pv-string-card.pv-string-disabled .pv-config-fields { opacity: 0.55; pointer-events: none; }
.pv-geometry-block { margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(127,127,127,0.2); }
.pv-geometry-block:first-of-type { margin-top: 0; padding-top: 0; border-top: none; }
.pv-geometry-label { margin: 0 0 8px; font-size: 13px; color: var(--secondary-text-color); }
.field input[type="number"].pv-eff-input { width: 100%; max-width: 120px; box-sizing: border-box; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); background: var(--card-background-color, #1c1c1e); color: var(--primary-text-color); }
.triple-soc { padding: 8px 4px 4px; user-select: none; touch-action: none; }
.triple-soc-head { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.triple-soc-battery {
  width: 52px; height: 88px; flex-shrink: 0; border-radius: 10px;
  border: 2px solid var(--divider-color); position: relative; overflow: hidden;
  background: var(--secondary-background-color);
}
.triple-soc-battery-fill {
  position: absolute; left: 4px; right: 4px; bottom: 4px; border-radius: 0 0 6px 6px;
  background: linear-gradient(180deg, #66bb6a 0%, #2e7d32 100%);
  transition: height 0.35s ease, top 0.35s ease, border-radius 0.2s ease;
  min-height: 4px;
}
.triple-soc-battery-fill.is-full {
  top: 4px;
  height: auto;
  border-radius: 6px;
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
.triple-soc-thumb.is-dragging { z-index: 10; transform: scale(1.1); transition: transform 0.1s; }
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
.soc-validation {
  margin-top: 14px; padding: 10px 12px; border-radius: 8px;
  background: color-mix(in srgb, #e53935 18%, var(--card-background-color));
  border: 1px solid color-mix(in srgb, #e53935 45%, transparent);
  color: var(--primary-text-color); font-size: 13px; line-height: 1.45;
}
.soc-validation p { margin: 0; }
.soc-validation p + p { margin-top: 6px; }
.soc-validation.warn {
  background: color-mix(in srgb, var(--fp-amber) 18%, var(--card-background-color));
  border-color: color-mix(in srgb, var(--fp-amber) 45%, transparent);
}
.mode-grid { display: grid; gap: 8px; }
.mode-option {
  display: block; width: 100%; text-align: left; padding: 14px 16px;
  border-radius: 12px; border: 2px solid var(--divider-color); background: var(--card-background-color);
  cursor: pointer; font-family: inherit; color: inherit; transition: border-color 0.15s;
}
.mode-option.selected { border-color: var(--fp-accent); background: color-mix(in srgb, var(--fp-accent) 10%, var(--card-background-color)); }
.mode-option-body { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; width: 100%; }
.mode-option .name { display: block; font-weight: 600; font-size: 15px; line-height: 1.3; }
.mode-option .hint { display: block; font-size: 12px; line-height: 1.4; color: var(--secondary-text-color); }
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
@container fp-main (min-width: 560px) {
  .overview-hero-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: start;
    gap: 14px;
  }
  .overview-hero-scene {
    width: 100%;
    max-width: none;
    margin: 0;
    min-width: 0;
  }
  .overview-hero-daily {
    flex: none;
    min-width: 0;
  }
}
@media (max-width: 720px) {
  .device-grid { grid-template-columns: 1fr; gap: 12px; }
  .device-card--pv, .device-card--battery { padding: 20px 20px 22px; }
  .device-pv-gauges--dual .device-pv-gauge { max-width: 120px; }
  .device-pv-gauges--dual .device-pv-value { font-size: 14px; }
  .device-pv-gauges--dual .device-pv-readout { padding: 0 6px; }
  .device-pv-gauge { max-width: 160px; }
  .device-pv-value { font-size: 18px; }
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
    this._deviceParamOpen = new Set();
    this._plantState = undefined;
    this._selectedPlantId = undefined;
    this._timer = undefined;
    this._busy = false;
    this._toastTimer = undefined;
    this._chargeDraft = null;
    this._socDraft = null;
    this._socSaveError = null;
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
    this._rangeDrag = false;
    this._settingsFieldFocused = false;
    this._renderPending = false;
    this._energyPeriod = "day";
    this._energyPeriodOffset = 0;
    this._energyBreakdown = null;
    this._energyChart = null;
    this._energyChartLoading = false;
    this._energyChartPlantId = undefined;
    this._statisticsChart = null;
    this._statisticsChartLoading = false;
    this._statisticsChartPlantId = undefined;
    this._batterySocChart = null;
    this._batterySocChartLoading = false;
    this._batterySocChartPlantId = undefined;
    this._overviewDaily = null;
    this._overviewDailyLoading = false;
    this._overviewDailyPlantId = undefined;
    this._overviewDailySlotCache = undefined;
    this._panelSyncBusy = false;
    this._panelStale = false;
    this._flowSceneKey = undefined;
    this._flowScenePlantId = undefined;
    this._flowSceneKeyPending = undefined;
    this._flowSceneKeyPendingN = 0;
    this._pvDraft = null;
    this._solcastDraft = null;
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
    this._onPointerDown = this._onPointerDown.bind(this);
    this._onPointerUp = this._onPointerUp.bind(this);
    this._onFocusIn = this._onFocusIn.bind(this);
    this._onFocusOut = this._onFocusOut.bind(this);
    this._onPaste = this._onPaste.bind(this);
  }

  connectedCallback() {
    this._root.addEventListener("click", this._onClick);
    this._root.addEventListener("input", this._onInput);
    this._root.addEventListener("change", this._onChange);
    this._root.addEventListener("pointerdown", this._onPointerDown);
    this._root.addEventListener("pointerup", this._onPointerUp);
    this._root.addEventListener("pointercancel", this._onPointerUp);
    this._root.addEventListener("focusin", this._onFocusIn, true);
    this._root.addEventListener("focusout", this._onFocusOut, true);
    this._root.addEventListener("paste", this._onPaste, true);
    void this._initBrandIcons();
    void this._refreshPlantState();
    this._timer = window.setInterval(() => void this._refreshPlantState(), 30000);
    this._render();
  }

  disconnectedCallback() {
    this._root.removeEventListener("click", this._onClick);
    this._root.removeEventListener("input", this._onInput);
    this._root.removeEventListener("change", this._onChange);
    this._root.removeEventListener("pointerdown", this._onPointerDown);
    this._root.removeEventListener("pointerup", this._onPointerUp);
    this._root.removeEventListener("pointercancel", this._onPointerUp);
    this._root.removeEventListener("focusin", this._onFocusIn, true);
    this._root.removeEventListener("focusout", this._onFocusOut, true);
    this._root.removeEventListener("paste", this._onPaste, true);
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
    this._scheduleRender();
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
    const jsVer = panelVersionFromModuleUrl() || PANEL_VERSION;
    const regBuild = this._panel?.config?.panel_js_build || "—";
    const regVer = String(regBuild).split("-")[0] || "—";
    const diskVer = this._plantState?.panel_runtime?.manifest_version || "—";
    return `js ${jsVer} · registered ${regVer} · disk ${diskVer}`;
  }

  _syncPanelBuildFooter(shell) {
    if (!shell) return;
    let el = shell.querySelector(".panel-build-footer");
    if (!el) {
      el = document.createElement("p");
      el.className = "panel-build-footer";
      el.setAttribute("aria-hidden", "true");
      shell.appendChild(el);
    }
    el.textContent = `Panel build ${this._panelBuild()}`;
  }

  _panelIsStale() {
    const runtime = this._plantState?.panel_runtime;
    if (!runtime?.js_build) return false;
    const jsVer = panelVersionFromModuleUrl() || PANEL_VERSION;
    const regBuild = this._panel?.config?.panel_js_build;
    const diskVer = runtime.manifest_version;
    const staleReg = Boolean(regBuild && runtime.js_build && regBuild !== runtime.js_build);
    const staleJs = Boolean(diskVer && jsVer && diskVer !== jsVer);
    return staleReg || staleJs;
  }

  _renderPanelStaleBanner() {
    if (!this._panelStale) return "";
    const runtime = this._plantState?.panel_runtime ?? {};
    const jsVer = panelVersionFromModuleUrl() || PANEL_VERSION;
    const regVer = String(this._panel?.config?.panel_js_build || "—").split("-")[0];
    return `<div class="banner warn panel-stale-banner" role="status">
<strong>Panel update pending</strong>
Browser ${esc(jsVer)} · HA registered ${esc(regVer)} · files on disk ${esc(runtime.manifest_version || "—")}.
Reloading panel registration…
</div>`;
  }

  async _syncPanelIfStale() {
    if (this._panelSyncBusy || !this._hass) return;
    const runtime = this._plantState?.panel_runtime;
    if (!runtime?.js_build) return;
    this._panelStale = this._panelIsStale();
    if (!this._panelStale) return;
    const attempted = sessionStorage.getItem(PANEL_SYNC_STORAGE_KEY);
    if (attempted === runtime.js_build) return;
    this._panelSyncBusy = true;
    sessionStorage.setItem(PANEL_SYNC_STORAGE_KEY, runtime.js_build);
    this._scheduleRender();
    try {
      await this._hass.callService("foxess_plant", "reload_panel", {}, undefined, true, true);
    } catch (err) {
      console.warn("FoxESS Plant: reload_panel failed (restart HA if panel stays stale)", err);
    }
    window.setTimeout(() => window.location.reload(), 400);
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
      if (
        this._settingsView === "solcast" &&
        this._solcastDraft &&
        !this._settingsFieldFocused &&
        !this._rangeDrag
      ) {
        const sc = this._plantState?.solcast ?? {};
        this._solcastDraft.enabled = solcastEnabledFromLive(sc);
        this._solcastDraft.fetch_pv_forecast = sc.fetch_pv_forecast !== false;
        this._solcastDraft.api_key_set = Boolean(sc.api_key_set);
      }
      this._panelStale = this._panelIsStale();
      if (!this._socDrag) this._scheduleRender();
      void this._syncPanelIfStale();
    } catch {
      /* ws optional */
    }
  }

  _settingsFieldBlocksRender() {
    if (this._view !== "settings") return false;
    if (this._settingsFieldFocused) return true;
    const el = this.shadowRoot?.activeElement || document.activeElement;
    if (!el || !this._root.contains(el)) return false;
    const tag = el.tagName;
    if (tag === "SELECT" || tag === "TEXTAREA") return true;
    if (tag !== "INPUT") return false;
    const type = (el.type || "text").toLowerCase();
    return ["range", "date", "number", "text", "password"].includes(type);
  }

  _onFocusIn(e) {
    if (this._view !== "settings" || !this._root.contains(e.target)) return;
    if (e.target.matches?.("input, select, textarea")) this._settingsFieldFocused = true;
  }

  _onFocusOut() {
    if (this._view !== "settings") return;
    window.requestAnimationFrame(() => {
      const active = this.shadowRoot?.activeElement || document.activeElement;
      if (active && this._root.contains(active) && active.matches?.("input, select, textarea")) return;
      this._settingsFieldFocused = false;
      if (this._renderPending) {
        this._renderPending = false;
        this._scheduleRender();
      }
    });
  }

  _onPaste(e) {
    const el = e.target;
    if (!el?.dataset?.field || this._busy) return;
    const parts = el.dataset.field.split(":");
    if (parts[0] !== "solcast" || parts[1] !== "api_key" || !this._solcastDraft) return;
    const text = e.clipboardData?.getData("text/plain") ?? "";
    if (text) this._solcastDraft.api_key = text;
  }

  _onPointerDown(e) {
    const t = e.target;
    if (t?.matches?.('input[type="range"][data-field^="pv:"]')) this._rangeDrag = true;
  }

  _onPointerUp() {
    this._rangeDrag = false;
  }

  _updatePvRangeLabel(el) {
    const row = el?.closest?.(".pv-range-row");
    if (!row) return;
    const label = row.querySelector(".pv-range-value");
    if (!label) return;
    const field = el.dataset?.field || "";
    if (field.endsWith(":tilt")) label.textContent = `${el.value}°`;
    else if (field.endsWith(":azimuth")) label.textContent = `${el.value}°`;
    else if (field.endsWith(":panel_count")) label.textContent = String(el.value);
    else if (field.endsWith(":watts_per_panel")) label.textContent = `${el.value} W`;
  }

  _statisticsChartVisible() {
    return (
      this._view === "overview" ||
      (this._view === "energy" && this._energyPeriod === "day")
    );
  }

  _pickStatisticsForecastState() {
    const live = this._plantState;
    const cached = this._statisticsChart?.forecastState;
    const liveIntraday = live?.solcast?.forecast_intraday_points;
    if (Array.isArray(liveIntraday) && liveIntraday.length >= 2) return live;
    const cachedIntraday = cached?.solcast?.forecast_intraday_points;
    if (Array.isArray(cachedIntraday) && cachedIntraday.length >= 2) return cached;
    const liveRows = resolveSolcastDetailedForecast(live, this._hass);
    if (liveRows.length >= 2) return live;
    const cachedRows = resolveSolcastDetailedForecast(cached, this._hass);
    if (cachedRows.length >= 2) return cached;
    return live ?? cached;
  }

  _statisticsSeriesForDisplay() {
    if (!this._statisticsChart?.series || !this._statisticsChart?.range) return null;
    const state = this._pickStatisticsForecastState();
    return mergeStatisticsForecastSeries(
      this._statisticsChart.series,
      this._statisticsChart.range,
      state,
      this._hass
    );
  }

  _reloadStatisticsChartWhenVisible() {
    if (!this._statisticsChartVisible()) return;
    this._statisticsChart = null;
    this._statisticsChartPlantId = undefined;
    if (this._view === "overview") void this._loadOverviewStatisticsChart();
    else void this._loadStatisticsChart();
  }

  _scheduleRender(force = false) {
    if (!force && (this._socDrag || this._rangeDrag || this._settingsFieldBlocksRender())) {
      this._renderPending = true;
      return;
    }
    this._renderPending = false;
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

  _initPvDraft() {
    this._pvDraft = normalizePvConfig(this._plantState?.pv_config);
  }

  _enterPvSettings() {
    this._initPvDraft();
  }

  _initSolcastDraft() {
    const sc = this._plantState?.solcast ?? {};
    this._solcastDraft = {
      enabled: solcastEnabledFromLive(sc),
      api_key: "",
      api_key_set: Boolean(sc.api_key_set),
      api_limit: sc.api_limit ?? 10,
      auto_update: sc.auto_update === "all_day" ? "all_day" : "daylight",
      fetch_pv_forecast: sc.fetch_pv_forecast !== false,
      latitude: sc.latitude ?? sc.coordinates?.latitude ?? "",
      longitude: sc.longitude ?? sc.coordinates?.longitude ?? "",
      installation_date: sc.installation_date ?? "",
      period: sc.period ?? "PT30M",
    };
  }

  _enterSolcastSettings() {
    this._solcastDraft = null;
    this._initSolcastDraft();
    this._initPvDraft();
  }

  _syncSolcastDraftFromDom() {
    if (!this._solcastDraft) return;
    const root = this._root;
    const enabledEl = root.querySelector('[data-field="solcast:enabled"]');
    if (enabledEl) this._solcastDraft.enabled = enabledEl.checked;
    const fetchEl = root.querySelector('[data-field="solcast:fetch_pv_forecast"]');
    if (fetchEl) this._solcastDraft.fetch_pv_forecast = fetchEl.checked;
  }

  _solcastSettingsSubtitle() {
    const sc = this._plantState?.solcast;
    if (!solcastEnabledFromLive(sc)) return "Off — enable for native PV forecast on charts";
    if (!sc.api_key_set) return "API key required";
    if (!sc.coordinates_configured) return "Solcast site latitude/longitude required";
    if (!sc.hobbyist_sites_resolved) return "Linking to Solcast Home PV site(s)… save settings";
    const rem = sc.api_remaining ?? "—";
    return `PV forecast · ${sc.api_used_today ?? 0}/${sc.api_limit ?? 10} API calls today · ${rem} left`;
  }

  async _saveSolcastSettings() {
    const plant = this._getPlant();
    if (!plant || !this._solcastDraft) return;
    this._syncSolcastDraftFromDom();
    this._busy = true;
    this._render();
    try {
      const draft = this._solcastDraft;
      const validationErr = validateSolcastDraft(draft);
      if (validationErr) {
        this._showToast(validationErr, "err");
        return;
      }
      const lat = normalizeSolcastCoordinateInput(draft.latitude);
      const lon = normalizeSolcastCoordinateInput(draft.longitude);
      const payload = {
        enabled: Boolean(draft.enabled),
        api_limit: Math.max(1, Math.min(50, parseInt(draft.api_limit, 10) || 10)),
        auto_update: draft.auto_update === "all_day" ? "all_day" : "daylight",
        fetch_pv_forecast: Boolean(draft.fetch_pv_forecast),
        period: draft.period || "PT30M",
        latitude: lat,
        longitude: lon,
        installation_date: normalizeSolcastInstallationDateInput(draft.installation_date),
      };
      const key = String(draft.api_key || "").trim();
      if (key) payload.api_key = key;
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_solcast",
        plant_id: plant.entry_id,
        solcast: payload,
      });
      if (state) this._plantState = state;
      if (this._pvDraft && draft.fetch_pv_forecast) {
        const pvState = await this._hass.connection.sendMessagePromise({
          type: "foxess_plant/update_pv_config",
          plant_id: plant.entry_id,
          pv_config: normalizePvConfig(this._pvDraft),
        });
        if (pvState) this._plantState = pvState;
        this._initPvDraft();
      }
      this._initSolcastDraft();
      this._showToast("Solcast settings saved");
      this._reloadStatisticsChartWhenVisible();
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _testSolcastConnection() {
    const plant = this._getPlant();
    if (!plant || !this._solcastDraft) return;
    this._syncSolcastDraftFromDom();
    this._busy = true;
    this._render();
    try {
      const draft = this._solcastDraft;
      const key = String(draft.api_key || "").trim();
      if (key || !draft.api_key_set) {
        const payload = {
          enabled: Boolean(draft.enabled),
          api_limit: Math.max(1, Math.min(50, parseInt(draft.api_limit, 10) || 10)),
          auto_update: draft.auto_update === "all_day" ? "all_day" : "daylight",
          fetch_pv_forecast: Boolean(draft.fetch_pv_forecast),
          period: draft.period || "PT30M",
          latitude: draft.latitude === "" ? null : parseFloat(draft.latitude),
          longitude: draft.longitude === "" ? null : parseFloat(draft.longitude),
          fetch_now: false,
        };
        if (key) payload.api_key = key;
        const state = await this._hass.connection.sendMessagePromise({
          type: "foxess_plant/update_solcast",
          plant_id: plant.entry_id,
          solcast: payload,
        });
        if (state) this._plantState = state;
      }
      const res = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/test_solcast",
        plant_id: plant.entry_id,
      });
      if (res?.plant_state) this._plantState = res.plant_state;
      this._initSolcastDraft();
      this._reloadStatisticsChartWhenVisible();
      const sc = res?.solcast ?? {};
      const summary = sc.live_summary;
      const match = sc.test_match_note || summary?.match_note;
      const msg = match
        ? `Solcast hobbyist OK — ${match}`
        : summary?.condition_label
          ? `Solcast hobbyist OK — ${summary.condition_label}`
          : "Solcast hobbyist API OK (listed Home PV sites)";
      this._showToast(msg);
    } catch (err) {
      this._showToast(err?.message || "Solcast test failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _savePvConfig() {
    const plant = this._getPlant();
    if (!plant || !this._pvDraft) return;
    this._busy = true;
    this._render();
    try {
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_pv_config",
        plant_id: plant.entry_id,
        pv_config: normalizePvConfig(this._pvDraft),
      });
      if (state) this._plantState = state;
      this._initPvDraft();
      this._showToast("PV configuration saved");
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
      const nextView = btn.dataset.view;
      if (this._view === "energy" && nextView !== "energy") {
        this._energyPeriodOffset = 0;
        this._energyBreakdown = null;
        this._statisticsChart = null;
        this._statisticsChartPlantId = undefined;
      }
      this._view = nextView;
      this._settingsView = "main";
      this._solcastDraft = null;
      this._deviceSub = "main";
      if (this._view === "energy") this._loadEnergyCharts();
      if (this._view === "overview") this._loadOverviewStatisticsChart();
      this._render();
      return;
    }
    if (action === "energy-period") {
      const period = btn.dataset.period;
      if (!period || period === this._energyPeriod) return;
      this._energyPeriod = period;
      this._energyPeriodOffset = 0;
      this._energyBreakdown = null;
      this._energyChart = null;
      this._energyChartPlantId = undefined;
      this._statisticsChart = null;
      this._statisticsChartPlantId = undefined;
      this._loadEnergyCharts();
      this._render();
      return;
    }
    if (action === "energy-nav") {
      const dir = btn.dataset.dir;
      const bounds = energyPeriodBounds(this._energyPeriod, this._energyPeriodOffset);
      if (dir === "prev") {
        this._energyPeriodOffset += 1;
      } else if (dir === "next" && bounds.canNext) {
        this._energyPeriodOffset = Math.max(0, this._energyPeriodOffset - 1);
      } else {
        return;
      }
      this._energyBreakdown = null;
      this._energyChart = null;
      this._energyChartPlantId = undefined;
      this._statisticsChart = null;
      this._statisticsChartPlantId = undefined;
      this._loadEnergyCharts();
      this._scheduleRender();
      return;
    }
    if (action === "device-sub") {
      this._deviceSub = btn.dataset.sub;
      if (btn.dataset.sub === "parameters") this._deviceParamOpen = new Set();
      if (btn.dataset.sub === "pv-config") this._enterPvSettings();
      this._render();
      return;
    }
    if (action === "device-param-toggle") {
      const sectionId = btn.dataset.section;
      if (!sectionId) return;
      if (this._deviceParamOpen.has(sectionId)) this._deviceParamOpen.delete(sectionId);
      else this._deviceParamOpen.add(sectionId);
      this._scheduleRender();
      return;
    }
    if (action === "device-back") {
      this._deviceSub = "main";
      this._deviceParamOpen = new Set();
      this._render();
      return;
    }
    if (action === "settings-sub") {
      this._view = "settings";
      if (btn.dataset.sub !== "solcast") this._solcastDraft = null;
      this._settingsView = btn.dataset.sub;
      if (btn.dataset.sub === "schedules") this._initChargeDraft();
      if (btn.dataset.sub === "quick") this._initSocDraft();
      if (btn.dataset.sub === "workmode") this._initWorkModeDraft();
      if (btn.dataset.sub === "storm") this._enterStormSettings();
      if (btn.dataset.sub === "pv") this._enterPvSettings();
      if (btn.dataset.sub === "solcast") this._enterSolcastSettings();
      this._render();
      return;
    }
    if (action === "settings-tab") {
      this._view = "settings";
      if (btn.dataset.sub !== "solcast") this._solcastDraft = null;
      this._settingsView = btn.dataset.sub;
      if (btn.dataset.sub === "schedules") this._initChargeDraft();
      if (btn.dataset.sub === "quick") this._initSocDraft();
      if (btn.dataset.sub === "workmode") this._initWorkModeDraft();
      if (btn.dataset.sub === "storm") this._enterStormSettings();
      if (btn.dataset.sub === "pv") this._enterPvSettings();
      if (btn.dataset.sub === "solcast") this._enterSolcastSettings();
      this._render();
      return;
    }
    if (action === "save-pv-config") {
      await this._savePvConfig();
      return;
    }
    if (action === "save-solcast-settings") {
      await this._saveSolcastSettings();
      return;
    }
    if (action === "test-solcast") {
      await this._testSolcastConnection();
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
    if (action === "sync-schedule") {
      await this._syncScheduleFromInverter();
      return;
    }
    if (action === "reapply-schedule") {
      await this._runPlantService("reapply_schedule", {}, "Schedule re-applied to inverter");
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
    if (this._busy) return;
    if (el?.dataset?.field) {
      const parts = el.dataset.field.split(":");
      if (parts[0] === "solcast" && this._solcastDraft) {
        if (parts[1] === "enabled") {
          this._solcastDraft.enabled = el.checked;
          this._scheduleRender();
          return;
        }
        if (parts[1] === "fetch_pv_forecast") {
          this._solcastDraft.fetch_pv_forecast = el.checked;
          this._scheduleRender();
          return;
        }
      }
      if (parts[0] === "pv" && ["tilt", "azimuth", "panel_count", "watts_per_panel"].includes(parts[2])) {
        this._rangeDrag = false;
        this._scheduleRender(true);
        return;
      }
    }
    if (!el?.dataset?.action) return;
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
      this._energyPeriodOffset = 0;
      this._energyBreakdown = null;
      this._batterySocChart = null;
      this._batterySocChartPlantId = undefined;
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
    if (kind === "solcast" && this._solcastDraft) {
      const field = parts[1];
      if (!field) return;
      if (field === "enabled") {
        this._solcastDraft.enabled = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "fetch_pv_forecast") {
        this._solcastDraft.fetch_pv_forecast = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "auto_update") {
        this._solcastDraft.auto_update = el.value === "all_day" ? "all_day" : "daylight";
        return;
      }
      if (field === "api_limit") {
        const n = parseInt(String(el.value).trim(), 10);
        this._solcastDraft.api_limit = Math.max(1, Math.min(50, Number.isFinite(n) ? n : 10));
        return;
      }
      if (field === "api_key") {
        this._solcastDraft.api_key = el.value;
        return;
      }
      if (field === "latitude" || field === "longitude") {
        this._solcastDraft[field] = el.value;
        return;
      }
      if (field === "installation_date") {
        this._solcastDraft.installation_date = el.value;
        return;
      }
      return;
    }
    if (kind === "pv" && this._pvDraft) {
      const which = parts[1];
      const field = parts[2];
      const cfg = this._pvDraft[which];
      if (!cfg || !field) return;
      if (el.type === "checkbox") {
        cfg.enabled = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "panel_count") {
        cfg.panel_count = Math.max(1, Math.min(12, parseInt(el.value, 10) || 1));
      } else if (field === "watts_per_panel") {
        cfg.watts_per_panel = Math.max(100, Math.min(1000, parseInt(el.value, 10) || 450));
      } else if (field === "efficiency_factor") {
        const raw = String(el.value).trim();
        if (raw === "") return;
        const v = parseFloat(raw);
        if (!Number.isFinite(v)) return;
        cfg.efficiency_factor = Math.max(1, Math.min(100, v));
        if (e.type === "change") this._scheduleRender();
        return;
      } else if (field === "tilt") {
        cfg.tilt = Math.max(0, Math.min(90, parseInt(el.value, 10) || 25));
      } else if (field === "azimuth") {
        cfg.azimuth = Math.max(0, Math.min(359, parseInt(el.value, 10) || 180));
      } else {
        return;
      }
      this._updatePvRangeLabel(el);
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
        this._socSaveError = null;
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
    this._socSaveError = null;
    const rect = this._socDrag.track.getBoundingClientRect();
    const pct = socPctFromTrackPointer(e.clientX, rect, this._socDrag.grabOffset ?? 0);
    applySocDrag(this._socDraft, this._socDrag.thumb, pct);
    this._updateTripleSocDom();
  }

  _onSocEnd() {
    const thumb = this._socDrag?.thumbEl;
    if (thumb) thumb.classList.remove("is-dragging");
    this._endSocDrag();
  }

  _liveBatterySoc(plant) {
    if (!plant || !this._hass) return null;
    const v = stateNumber(this._hass, plant.entity_map?.battery_soc);
    return Number.isFinite(v) ? v : null;
  }

  _socValidationIssues() {
    return validateSocLimits(this._socDraft, this._liveBatterySoc(this._getPlant()));
  }

  _syncSocValidationUi() {
    const validation = this._socValidationIssues();
    const wrap = this._root.querySelector(".triple-soc");
    if (!wrap) return;
    const html = renderSocFeedbackHtml(validation, this._socSaveError);
    wrap.querySelectorAll(".soc-validation").forEach((el) => el.remove());
    if (html) wrap.querySelector(".soc-numeric")?.insertAdjacentHTML("afterend", html);
    const saveBtn = this._root.querySelector('[data-action="save-soc"]');
    if (saveBtn) saveBtn.disabled = Boolean(this._busy || validation.errors.length);
  }

  _bindTripleSoc() {
    const track = this._root.querySelector(".triple-soc-track");
    if (!track) return;
    track.querySelectorAll("[data-soc-thumb]").forEach((thumb) => {
      thumb.addEventListener("pointerdown", (e) => {
        if (this._busy) return;
        e.preventDefault();
        this._socSaveError = null;
        track.querySelectorAll(".triple-soc-thumb").forEach((t) => t.classList.remove("is-dragging"));
        thumb.classList.add("is-dragging");
        thumb.setPointerCapture(e.pointerId);
        const rect = track.getBoundingClientRect();
        const thumbKey = thumb.dataset.socThumb;
        const currentVal = clampSocDraft(this._socDraft)[thumbKey];
        const pointerPct = rect.width ? ((e.clientX - rect.left) / rect.width) * 100 : currentVal;
        this._socDrag = {
          thumb: thumbKey,
          thumbEl: thumb,
          track,
          grabOffset: currentVal - pointerPct,
        };
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
    this._syncSocValidationUi();
  }

  _renderTripleSoc(plant, d, liveSoc) {
    const clamped = clampSocDraft({ ...d });
    const min = clamped.min_soc;
    const mid = clamped.min_soc_on_grid;
    const max = clamped.max_soc;
    const live = Math.max(0, Math.min(100, Math.round(liveSoc ?? 0)));
    const fillMarkup = tripleSocBatteryFillMarkup(live);

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
${fillMarkup}
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
${renderSocFeedbackHtml(validateSocLimits(clamped, live), this._socSaveError)}
<p class="soc-limit-note">Minimum for all three limits is <strong>10%</strong>. Keep <strong>off-grid min ≤ system min ≤ system max</strong>. The inverter may reject limits that conflict with the current battery level — Save will show the error if it does.</p>
</div>`;
  }

  async _runPlantService(service, extra = {}, toastMsg = "Updated") {
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
      this._showToast(toastMsg);
    } catch (err) {
      this._showToast(err?.message || "Action failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _syncScheduleFromInverter() {
    const plant = this._getPlant();
    if (!plant) return;
    this._busy = true;
    this._render();
    try {
      await callService(this._hass, "foxess_plant", "sync_schedule_from_inverter", {
        plant_id: plant.entry_id,
      });
      await this._refreshPlantState();
      this._initChargeDraft();
      this._showToast("Synced schedule from inverter");
    } catch (err) {
      this._showToast(err?.message || "Sync failed", "err");
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
    const validation = validateSocLimits(clamped, this._liveBatterySoc(plant));
    if (validation.errors.length) {
      this._showToast(validation.errors[0], "err");
      return;
    }
    const { min_soc, min_soc_on_grid, max_soc } = clamped;
    this._socDraft = clamped;
    this._socSaveError = null;
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
      this._socSaveError = null;
      this._showToast("SOC limits saved");
    } catch (err) {
      this._socSaveError = err?.message || "SOC save failed";
      this._render();
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

  _scheduleSyncButtons() {
    const dis = this._busy ? "disabled" : "";
    return `<div class="btn-row schedule-sync-row">
<button type="button" class="btn btn-secondary" data-action="sync-schedule" ${dis}>Sync from inverter</button>
<button type="button" class="btn btn-primary" data-action="reapply-schedule" ${dis}>Re-apply to inverter</button>
</div>`;
  }

  _modeBannerExtra() {
    const st = this._plantState;
    if (!st) return "";
    if (st.drift) {
      return `<div class="banner warn"><strong>Schedule drift</strong>Inverter charge windows differ from what Fox Plant expects. Sync copies the inverter into your app settings; re-apply pushes your app schedule to the inverter and enables plant control.${this._scheduleSyncButtons()}</div>`;
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

  _renderOverviewWeather() {
    const wx = this._plantState?.overview_weather;
    if (!wx || (!wx.temperature_display && !wx.condition_label)) return "";
    const icon = overviewWeatherIconSvg(wx.icon_key);
    const temp = wx.temperature_display
      ? `<span class="overview-weather-temp">${esc(wx.temperature_display)}</span>`
      : "";
    const label = wx.condition_label
      ? `<span class="overview-weather-label">${esc(wx.condition_label)}</span>`
      : "";
    const aria = [wx.temperature_display, wx.condition_label].filter(Boolean).join(", ");
    return `<div class="overview-weather" role="img" aria-label="${esc(aria || "Weather")}">${icon}${temp}${label}</div>`;
  }

  _renderOverviewStatusBlock(plant) {
    const st = this._plantState;
    if (!st) return "";
    const systemStatus = foxInverterStateLabel(this._hass, plant, this._plantState);
    const workMode = foxWorkModeLabel(this._hass, plant, this._plantState);
    const plantMode = st.mode ?? "baseline";
    const statusPart =
      systemStatus !== "—"
        ? `<span class="fox-pill overview-fox-status ${foxStatusToneClass(systemStatus)}">${esc(systemStatus)}</span>`
        : "";
    const workPart =
      workMode !== "—"
        ? `<span class="fox-pill overview-work-mode ${foxWorkModeToneClass(workMode)}">${esc(foxWorkModeDisplay(workMode))}</span>`
        : "";
    return `<div class="overview-status-block">
<div class="overview-status-row">
${statusPart}
${workPart}
<span class="mode-pill ${modeClass(plantMode)}">${esc(plantMode)}</span>
<span class="overview-control-hint">${st.control_active ? "Plant control active" : "Plant control off"}</span>
</div>
${this._renderOverviewWeather()}
${this._modeBannerExtra()}
</div>`;
  }

  _renderFlowBackdropMarkup(ctx) {
    return `<img class="fox-flow-layer fox-flow-layer-backdrop" src="${esc(flowSceneLayerUrl("backdrop", ctx.bgTheme, ctx.overlayTheme))}" alt="" loading="eager" decoding="async" fetchpriority="high" />`;
  }

  _renderEnergyScene(plant) {
    const ctx = this._flowSceneContext(plant);
    const pathsHtml = renderFlowScenePaths({
      lines: ctx.lines,
      activeIds: ctx.activeIds,
      gridExporting: ctx.gridExporting,
      isNight: ctx.isNight,
    });
    const haClass = ctx.haUiDark ? "fox-flow-scene--ha-dark" : "fox-flow-scene--ha-light";
    const skyClass = ctx.bgTheme === "day_light" ? " fox-flow-scene--light-sky" : "";
    return `<div class="scene-card scene-card--fox-flow">
<div class="fox-flow-scene ${ctx.isNight ? "fox-flow-scene--night" : "fox-flow-scene--day"} ${haClass}${skyClass}" role="img" aria-label="Live energy flow" data-panel-build="${esc(this._panelBuild())}">
<div class="fox-flow-stage">
${this._renderFlowBackdropMarkup(ctx)}
<img class="fox-flow-layer fox-flow-layer-pv" src="${esc(flowSceneLayerUrl("pv", ctx.bgTheme, ctx.overlayTheme))}" alt="" loading="lazy" decoding="async" />
<img class="fox-flow-layer fox-flow-layer-aio" src="${esc(flowSceneLayerUrl("aio", ctx.bgTheme, ctx.overlayTheme))}" alt="" loading="lazy" decoding="async" />
<svg class="fox-flow-svg" viewBox="0 0 1024 1017" preserveAspectRatio="xMidYMid meet" aria-hidden="true" data-flow-paths-ver="${esc(this._panel?.config?.flow_paths_ver || FLOW_PATHS_VER)}" data-flow-pipe-day="${FLOW_PIPE_STROKE.day}" data-flow-stroke-base="${FLOW_STROKE.base}" data-flow-stroke-active="${FLOW_STROKE.hubActive}" data-hub-r="${FLOW_STROKE.hubR}" data-hub-home="${esc(FOX_FLOW_PATHS["hub-home"])}" data-aio-hub="${esc(FOX_FLOW_PATHS["aio-hub"])}">
${pathsHtml}
<circle class="flow-hub-dot ${ctx.hubActive ? "active" : ""}" cx="${FOX_FLOW_HUB.x}" cy="${FOX_FLOW_HUB.y}" r="${FLOW_STROKE.hubR}" fill="${ctx.hubActive ? FLOW_ACTIVE_STROKE.battery : flowPipeStroke(ctx.isNight)}"/>
</svg>
<div class="fox-flow-badge fox-flow-badge-solar">
<span class="fox-flow-badge-label">Solar</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(ctx.flows.pvW))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-grid">
<span class="fox-flow-badge-label">${esc(ctx.gridLabel)}</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(ctx.gridPower))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-battery">
<span class="fox-flow-badge-label">${esc(ctx.batteryStatus)}</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(ctx.batteryPower))} | ${esc(formatPercent(ctx.soc))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-home">
<span class="fox-flow-badge-label">Home</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(ctx.flows.loadW))}</span>
</div>
</div>
</div>
</div>`;
  }

  _flowSceneContext(plant) {
    const flows = readEnergyFlows(this._hass, plant, this._plantState);
    const lines = computeFlowLines(flows);
    const activeIds = new Set(lines.map((l) => l.id));
    const bgTheme = resolveFlowSceneBgTheme(this._hass, this._plantState);
    const overlayTheme = flowSceneOverlayTheme(bgTheme);
    const haUiDark = resolveHaUiDark(this._hass);
    const isNight = !bgTheme.startsWith("day_");
    const soc = Math.min(100, Math.max(0, flows.batterySoc));
    const gridExporting =
      flows.gridExportW > flows.gridImportW && flows.gridExportW > FLOW_SCENE_PV_THRESHOLD_W;
    return {
      flows,
      lines,
      activeIds,
      bgTheme,
      overlayTheme,
      haUiDark,
      isNight,
      soc,
      gridExporting,
      gridLabel: gridExporting ? "To Grid" : "On Grid",
      gridPower: gridExporting ? flows.gridExportW : flows.gridImportW,
      batteryStatus: String(flows.batteryStatus || "Idle").toUpperCase(),
      batteryPower: Math.abs(flows.batteryW),
      hubActive: lines.some((l) => l.id.includes("hub")),
      key: flowSceneStructureKey(lines, gridExporting, isNight, bgTheme, haUiDark),
    };
  }

  /** Require two matching updates before rebuilding flow pipes (avoids threshold flicker). */
  _stableFlowSceneKey(nextKey) {
    if (this._flowSceneKey == null) {
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      return nextKey;
    }
    if (nextKey === this._flowSceneKey) {
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      return this._flowSceneKey;
    }
    if (nextKey === this._flowSceneKeyPending) {
      this._flowSceneKeyPendingN += 1;
    } else {
      this._flowSceneKeyPending = nextKey;
      this._flowSceneKeyPendingN = 1;
    }
    if (this._flowSceneKeyPendingN >= 2) {
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      return nextKey;
    }
    return this._flowSceneKey;
  }

  _patchFlowBadges(stage, ctx) {
    const set = (sel, text) => {
      const el = stage.querySelector(sel);
      if (el) el.textContent = text;
    };
    set(".fox-flow-badge-solar .fox-flow-badge-value", formatFoxPower(ctx.flows.pvW));
    set(".fox-flow-badge-grid .fox-flow-badge-label", ctx.gridLabel);
    set(".fox-flow-badge-grid .fox-flow-badge-value", formatFoxPower(ctx.gridPower));
    set(".fox-flow-badge-battery .fox-flow-badge-label", ctx.batteryStatus);
    set(
      ".fox-flow-badge-battery .fox-flow-badge-value",
      `${formatFoxPower(ctx.batteryPower)} | ${formatPercent(ctx.soc)}`
    );
    set(".fox-flow-badge-home .fox-flow-badge-value", formatFoxPower(ctx.flows.loadW));
  }

  _renderOverviewHeader(plant) {
    const modelLine = plantModelSubtitle(this._hass, plant, this._plantState);
    return `<header class="header overview-header"><h1>${esc(plant.title)}</h1>${modelLine !== "—" ? `<p class="overview-model">${esc(modelLine)}</p>` : ""}${this._renderOverviewStatusBlock(plant)}</header>`;
  }

  _renderOverviewAfterHero(plant) {
    const a = readLiveAnalytics(this._hass, plant, this._plantState, this._overviewDaily);
    return `<div class="overview-stats-row">
${this._stat("Self-consumption", a.self_consumption_percent_today, a.self_consumption_percent_today != null ? "%" : "")}
${this._stat("Self-sufficiency", a.self_sufficiency_percent_today, a.self_sufficiency_percent_today != null ? "%" : "")}
${this._stat("PV today", a.pv_production_kwh_today, a.pv_production_kwh_today != null ? " kWh" : "")}
</div>
<div class="card statistics-card" style="margin-top:14px">
<p class="card-title">Statistics</p>
${this._renderStatisticsChartBody()}
</div>
<div class="card soc-chart-card" style="margin-top:14px">
<p class="card-title">Battery SOC</p>
${this._renderBatterySocChartBody(plant)}
</div>
${this._renderImpactPanel()}`;
  }

  /** Refresh overview without disconnecting the flow scene (CSS animations keep running). */
  _renderOverviewMain(mainEl, plant) {
    const ctx = this._flowSceneContext(plant);
    if (this._flowScenePlantId !== plant.entry_id) {
      this._flowSceneKey = undefined;
      this._flowScenePlantId = plant.entry_id;
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      this._overviewDailySlotCache = undefined;
    }
    const stableKey = this._stableFlowSceneKey(ctx.key);
    const rebuildFlow = stableKey !== this._flowSceneKey;

    if (!mainEl.querySelector(".overview-root")) {
      mainEl.innerHTML = `<div class="overview-root">
<div class="overview-chrome"></div>
<div class="overview-hero-row">
<div class="overview-hero-scene"></div>
<div class="overview-hero-daily-slot"></div>
</div>
<div class="overview-after-hero"></div>
</div>`;
    }

    mainEl.querySelector(".overview-chrome").innerHTML =
      this._renderOverviewHeader(plant) + this._renderPanelStaleBanner();
    const dailyKey = this._overviewDailySlotKey();
    const dailySlot = mainEl.querySelector(".overview-hero-daily-slot");
    if (dailyKey !== this._overviewDailySlotCache) {
      dailySlot.innerHTML = this._renderOverviewDailyCards();
      this._overviewDailySlotCache = dailyKey;
    }
    mainEl.querySelector(".overview-after-hero").innerHTML = this._renderOverviewAfterHero(plant);

    const sceneSlot = mainEl.querySelector(".overview-hero-scene");
    if (rebuildFlow || !sceneSlot.querySelector(".fox-flow-stage")) {
      sceneSlot.innerHTML = this._renderEnergyScene(plant);
      this._flowSceneKey = stableKey;
    } else {
      const stage = sceneSlot.querySelector(".fox-flow-stage");
      if (stage) this._patchFlowBadges(stage, ctx);
    }
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
    const has = value != null && value !== "—" && !(typeof value === "number" && !Number.isFinite(value));
    const show = has ? esc(String(value)) + esc(suffix) : "—";
    return `<div class="stat"><label>${esc(label)}</label><strong>${show}</strong></div>`;
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

  _renderOverviewDailyCard(title, values, labels, accentColor, analyticsFallback) {
    const todayVal = values?.[values.length - 1];
    const display =
      todayVal != null && Number.isFinite(todayVal) && todayVal > 0
        ? todayVal
        : analyticsFallback != null && Number.isFinite(Number(analyticsFallback))
          ? Number(analyticsFallback)
          : todayVal;
    const chart =
      values?.length && labels?.length
        ? renderOverviewDailySparklineSvg(values, labels, accentColor)
        : "";
    return `<button type="button" class="overview-daily-card" data-action="nav" data-view="energy" aria-label="${esc(title)}">
<div class="overview-daily-head"><span class="overview-daily-title">${esc(title)}</span><span class="overview-daily-chev" aria-hidden="true">›</span></div>
<div class="overview-daily-value">${esc(formatDailyKwh(display))}</div>
${chart}
</button>`;
  }

  _overviewDailySlotKey() {
    if (this._overviewDailyLoading) return "loading";
    const data = this._overviewDaily;
    if (data?.error) return `err:${data.error}`;
    if (!data?.labels?.length) return "empty";
    const a = this._plantState?.analytics ?? {};
    const dates = data.labels.map((d) => d.getTime()).join(",");
    const prod = (data.production || []).join(",");
    const cons = (data.consumption || []).join(",");
    return `${dates}|${prod}|${cons}|${a.pv_production_kwh_today ?? ""}|${a.load_consumption_kwh_today ?? ""}`;
  }

  _renderOverviewDailyCards() {
    if (this._overviewDailyLoading) {
      return `<div class="overview-hero-daily"><div class="overview-daily-loading">Loading daily energy…</div></div>`;
    }
    const data = this._overviewDaily;
    if (data?.error) {
      return `<div class="overview-hero-daily"><div class="overview-daily-card"><p class="overview-daily-empty">${esc(data.error)}</p></div></div>`;
    }
    if (!data?.labels?.length) {
      return "";
    }
    const a = this._plantState?.analytics ?? {};
    return `<div class="overview-hero-daily">
${this._renderOverviewDailyCard(
  "Daily Production",
  data.production,
  data.labels,
  OVERVIEW_DAILY_COLORS.production,
  a.pv_production_kwh_today
)}
${this._renderOverviewDailyCard(
  "Daily Consumption",
  data.consumption,
  data.labels,
  OVERVIEW_DAILY_COLORS.consumption,
  a.load_consumption_kwh_today
)}
</div>`;
  }

  async _loadOverviewDailyCards() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const plantId = plant.entry_id;
    this._overviewDailyLoading = true;
    this._overviewDaily = null;
    this._overviewDailyPlantId = plantId;
    this._scheduleRender();
    try {
      if (!this._plantState) await this._refreshPlantState();
      this._overviewDaily = await fetchOverviewDailyEnergy(this._hass, plant, this._plantState);
    } catch (err) {
      this._overviewDaily = {
        error:
          err?.message ||
          "Could not load daily energy history. Enable the Home Assistant recorder for your daily kWh sensors.",
      };
    } finally {
      this._overviewDailyLoading = false;
      if (this._getPlant()?.entry_id === plantId && this._view === "overview") this._scheduleRender();
    }
  }

  _renderOverview(plant) {
    return `${this._renderOverviewHeader(plant)}
${this._renderPanelStaleBanner()}
<div class="overview-hero-row">
<div class="overview-hero-scene">
${this._renderEnergyScene(plant)}
</div>
${this._renderOverviewDailyCards()}
</div>
${this._renderOverviewAfterHero(plant)}`;
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
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>Parameters</h1><p>Live Modbus values (Fox app layout)</p></header>${this._renderDeviceParameters(plant)}`;
    }
    if (this._deviceSub === "battery") {
      const map = resolveEntityMap(this._hass, plant, this._plantState);
      const section = DEVICE_PARAMETER_SECTIONS.find((s) => s.id === "battery");
      const rows = section ? entityMapRows(this._hass, plant, this._plantState, section.rows) : [];
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>Battery</h1></header>${this._entityList(rows)}`;
    }
    if (this._deviceSub === "pv-config") {
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button>${this._renderPvConfiguration({
        title: "System PV Configuration",
        subtitle: "General solar panel settings for PV1 and PV2",
      })}`;
    }
    const flows = readEnergyFlows(this._hass, plant, this._plantState);
    const pvCard = renderDevicePvCard(this._hass, plant, this._plantState);
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
${pvCard}
<div class="device-card device-card--battery">${renderDeviceBatteryCard(flows, tempDisplay)}</div>
</div>
${renderListButton({ action: "device-sub", sub: "parameters" }, "Detailed parameters", "PV, AC, battery, grid — like Fox app")}
${renderListButton({ action: "device-sub", sub: "system" }, "System info", "Firmware, BMS, grid status")}
${renderListButton({ action: "device-sub", sub: "pv-config" }, "System PV Configuration", pvConfigSummary(this._plantState?.pv_config))}`;
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

  _entityMapRows(pairs) {
    return entityMapRows(this._hass, this._getPlant(), this._plantState, pairs);
  }

  _renderDevicePvTable(map) {
    const rows = DEVICE_PV_STRINGS.map((n) => {
      const v = map[`pv${n}_voltage`];
      const c = map[`pv${n}_current`];
      const p = map[`pv${n}_power`];
      if (!v && !c && !p) return null;
      return `<tr><td>PV${n}</td><td>${esc(entityDisplayValue(this._hass, v))}</td><td>${esc(entityDisplayValue(this._hass, c))}</td><td>${esc(entityDisplayValue(this._hass, p))}</td></tr>`;
    }).filter(Boolean);
    if (!rows.length) return `<p class="device-param-empty">No PV string sensors discovered.</p>`;
    const total =
      map.pv_power && this._hass?.states?.[map.pv_power]
        ? `<tr><td>PV</td><td>—</td><td>—</td><td>${esc(entityDisplayValue(this._hass, map.pv_power))}</td></tr>`
        : "";
    return `<div class="device-param-table-wrap"><table class="device-param-table"><thead><tr><th>PV</th><th>Voltage (V)</th><th>Current (A)</th><th>Power (kW)</th></tr></thead><tbody>${total}${rows.join("")}</tbody></table></div>`;
  }

  _renderDeviceMetricTable(map, keys, headers) {
    const values = keys.map((key) => entityDisplayValue(this._hass, map[key]));
    if (values.every((v) => v === "—")) {
      return `<p class="device-param-empty">No sensors discovered for this section.</p>`;
    }
    return `<div class="device-param-table-wrap"><table class="device-param-table"><thead><tr>${headers
      .map((h) => `<th>${esc(h)}</th>`)
      .join("")}</tr></thead><tbody><tr>${values.map((v) => `<td>${esc(v)}</td>`).join("")}</tr></tbody></table></div>`;
  }

  _renderDeviceDataloggerRows(plant, map) {
    const id = this._plantState?.identity ?? {};
    const rows = [];
    const bmsId = map.bms_online;
    if (bmsId && this._hass?.states?.[bmsId]) {
      const on = this._hass.states[bmsId].state === "on";
      rows.push({ name: "Status", value: on ? "Online" : "Offline" });
    } else if (id.bms_online != null && id.bms_online !== "") {
      rows.push({ name: "Status", value: id.bms_online === true || id.bms_online === "on" ? "Online" : "Offline" });
    }
    const firmware =
      entityDisplayValue(this._hass, map.manager_version) !== "—"
        ? entityDisplayValue(this._hass, map.manager_version)
        : entityDisplayValue(this._hass, map.master_version);
    if (firmware !== "—") rows.push({ name: "Software version", value: firmware });
    const proto = id.modbus_protocol_version || entityDisplayValue(this._hass, map.modbus_protocol_version);
    if (proto && proto !== "—") rows.push({ name: "Modbus protocol", value: proto });
    const master = id.master_version || entityDisplayValue(this._hass, map.master_version);
    if (master && master !== "—") rows.push({ name: "Master firmware", value: master });
    const slave = id.slave_version || entityDisplayValue(this._hass, map.slave_version);
    if (slave && slave !== "—") rows.push({ name: "Slave firmware", value: slave });
    if (!rows.length) {
      return `<p class="device-param-empty">No datalogger sensors discovered yet.</p>`;
    }
    return `<div class="entity-list">${rows
      .map(
        (r) =>
          `<div class="entity-row"><span class="entity-name">${esc(r.name)}</span><span class="entity-value">${esc(r.value)}</span></div>`
      )
      .join("")}</div>`;
  }

  _deviceParamSectionHasContent(section, map) {
    if (section.kind === "pv-table") {
      return DEVICE_PV_STRINGS.some((n) => map[`pv${n}_voltage`] || map[`pv${n}_current`] || map[`pv${n}_power`]) || map.pv_power;
    }
    if (section.kind === "metric-table") {
      return section.keys.some((key) => map[key]);
    }
    if (section.kind === "datalogger") {
      return Boolean(
        map.bms_online ||
          map.manager_version ||
          map.master_version ||
          map.modbus_protocol_version ||
          this._plantState?.identity?.modbus_protocol_version
      );
    }
    if (section.kind === "rows") {
      return section.rows.some(([key]) => map[key]);
    }
    return false;
  }

  _renderDeviceParamSectionBody(section, plant, map) {
    if (section.kind === "pv-table") return this._renderDevicePvTable(map);
    if (section.kind === "metric-table") {
      return this._renderDeviceMetricTable(map, section.keys, section.headers);
    }
    if (section.kind === "datalogger") return this._renderDeviceDataloggerRows(plant, map);
    const rows = entityMapRows(this._hass, plant, this._plantState, section.rows);
    return this._entityList(rows);
  }

  _renderDeviceParameters(plant) {
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    const sections = DEVICE_PARAMETER_SECTIONS.filter((section) => this._deviceParamSectionHasContent(section, map));
    if (!sections.length) {
      return `<p class="placeholder">No Modbus sensors discovered. Reload foxess_modbus and this panel, or reconfigure the plant device link.</p>`;
    }
    const entityIds = deviceParamEntityIds(map, sections);
    const updated = deviceParamLastUpdated(this._hass, entityIds);
    const body = sections
      .map((section) => {
        const isOpen = this._deviceParamOpen.has(section.id);
        const sectionBody = isOpen ? this._renderDeviceParamSectionBody(section, plant, map) : "";
        return `<div class="device-param-section${isOpen ? " is-open" : ""}"><button type="button" class="device-param-summary" data-action="device-param-toggle" data-section="${esc(section.id)}" aria-expanded="${isOpen}">${esc(section.title)}</button>${isOpen ? `<div class="device-param-body">${sectionBody}</div>` : ""}</div>`;
      })
      .join("");
    const stamp = updated ? `<p class="device-param-updated">${esc(updated)}</p>` : "";
    return `<div class="device-param-sections">${body}</div>${stamp}`;
  }

  _energyHistoryEntities(plant) {
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    return resolveEnergyHistoryEntities(map);
  }

  _energyChartCacheKey(plant) {
    return `${plant.entry_id}:${this._energyPeriod}:${this._energyPeriodOffset}`;
  }

  async _loadEnergyCharts() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const cacheKey = this._energyChartCacheKey(plant);
    if (this._energyPeriod === "day") {
      if (this._statisticsChartPlantId === cacheKey && this._statisticsChart) return;
      return this._loadStatisticsChart();
    }
    if (this._energyChartPlantId === cacheKey && this._energyChart) return;
    if (!this._plantState) await this._refreshPlantState();
    this._energyChartLoading = true;
    this._energyChart = null;
    this._energyChartPlantId = cacheKey;
    this._scheduleRender();
    try {
      const bar = await fetchFoxMirroredBarChart(
        this._hass,
        plant,
        this._plantState,
        this._energyPeriod,
        this._energyPeriodOffset
      );
      this._energyChart = { kind: "mirror", svg: bar.svg, title: bar.title };
      if (bar.breakdown) this._energyBreakdown = bar.breakdown;
    } catch (err) {
      this._energyChart = {
        error:
          err?.message ||
          "Could not load history. Enable the Home Assistant recorder and keep history for power sensors.",
      };
    } finally {
      this._energyChartLoading = false;
      if (this._energyChartCacheKey(this._getPlant()) === cacheKey && this._view === "energy") {
        this._scheduleRender();
      }
    }
  }

  async _loadOverviewStatisticsChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const cacheKey = `${plant.entry_id}:overview`;
    if (this._statisticsChartPlantId === cacheKey && this._statisticsChart) return;
    this._statisticsChartLoading = true;
    this._statisticsChart = null;
    this._statisticsChartPlantId = cacheKey;
    this._scheduleRender();
    try {
      if (resolveSolcastDetailedForecast(this._plantState, this._hass).length < 2) {
        await this._refreshPlantState();
      }
      this._statisticsChart = await fetchStatisticsChartSeries(this._hass, plant, this._plantState, {
        dayOffset: 0,
      });
    } catch (err) {
      this._statisticsChart = {
        error:
          err?.message ||
          "Could not load history. Enable the Home Assistant recorder and keep history for power sensors.",
      };
    } finally {
      this._statisticsChartLoading = false;
      if (this._getPlant()?.entry_id === plant.entry_id && this._view === "overview") this._scheduleRender();
    }
  }

  async _loadStatisticsChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const cacheKey = this._energyChartCacheKey(plant);
    if (this._statisticsChartPlantId === cacheKey && this._statisticsChart) return;
    this._statisticsChartLoading = true;
    this._statisticsChart = null;
    this._statisticsChartPlantId = cacheKey;
    this._scheduleRender();
    try {
      if (
        this._energyPeriodOffset === 0 &&
        resolveSolcastDetailedForecast(this._plantState, this._hass).length < 2
      ) {
        await this._refreshPlantState();
      }
      const chart = await this._fetchStatisticsChartData(plant);
      this._statisticsChart = chart;
      if (this._energyPeriod === "day" && this._energyPeriodOffset > 0) {
        const bounds = energyPeriodBounds("day", this._energyPeriodOffset);
        const { points } = await fetchEnergyHistoryPoints(
          this._hass,
          plant,
          this._plantState,
          bounds.start,
          bounds.end
        );
        if (points) {
          this._energyBreakdown = computeEnergyBreakdown(points, buildDaysInRange(bounds.start, bounds.end));
        }
      } else if (this._energyPeriod === "day" && this._energyPeriodOffset === 0) {
        this._energyBreakdown = null;
      }
    } catch (err) {
      this._statisticsChart = {
        error:
          err?.message ||
          "Could not load history. Enable the Home Assistant recorder and keep history for power sensors.",
      };
    } finally {
      this._statisticsChartLoading = false;
      if (this._energyChartCacheKey(this._getPlant()) === cacheKey) this._scheduleRender();
    }
  }

  async _fetchStatisticsChartData(plant) {
    return fetchStatisticsChartSeries(this._hass, plant, this._plantState, {
      dayOffset: this._energyPeriodOffset,
    });
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
    const series = this._statisticsSeriesForDisplay();
    if (series?.length) {
      return renderStatisticsChartHtml(series, this._statisticsChart.range);
    }
    return `<p class="placeholder chart-empty">Open Energy or wait for history to load.</p>`;
  }

  _bindStatisticsChart() {
    const series = this._statisticsSeriesForDisplay();
    if (!series?.length) return;
    bindStatisticsChart(this._root, series);
  }

  async _loadBatterySocChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const plantId = plant.entry_id;
    this._batterySocChartLoading = true;
    this._batterySocChart = null;
    this._batterySocChartPlantId = plantId;
    this._scheduleRender();
    try {
      await this._refreshPlantState();
      this._batterySocChart = await fetchBatterySocChartSeries(this._hass, plant, this._plantState);
    } catch (err) {
      this._batterySocChart = {
        error:
          err?.message ||
          "Could not load battery SOC history. Enable the Home Assistant recorder for battery_soc.",
      };
    } finally {
      this._batterySocChartLoading = false;
      if (this._getPlant()?.entry_id === plantId) this._scheduleRender();
    }
  }

  _renderBatterySocChartBody(plant) {
    if (this._batterySocChartLoading) {
      return `<p class="chart-loading">Loading battery SOC…</p>`;
    }
    if (this._batterySocChart?.error) {
      return `<p class="placeholder chart-empty">${esc(this._batterySocChart.error)}</p>`;
    }
    if (this._batterySocChart?.empty) {
      return `<p class="placeholder chart-empty">${esc(this._batterySocChart.empty)}</p>`;
    }
    if (this._batterySocChart?.socPts?.length) {
      const displaySoc = resolveBatterySocDisplay(
        this._hass,
        plant,
        this._plantState,
        this._batterySocChart
      );
      return renderBatterySocChartHtml(this._batterySocChart, displaySoc);
    }
    return `<p class="placeholder chart-empty">Waiting for battery SOC history…</p>`;
  }

  _bindBatterySocChart() {
    if (!this._batterySocChart?.socPts?.length) return;
    bindBatterySocChart(this._root, this._batterySocChart);
  }

  _renderEnergyPeriodTabs() {
    const tabs = ENERGY_PERIOD_TABS.map(
      (p) =>
        `<button type="button" data-action="energy-period" data-period="${p.id}" class="${p.id === this._energyPeriod ? "active" : ""}">${p.label}</button>`
    ).join("");
    return `<div class="energy-period-tabs">${tabs}</div>`;
  }

  _renderEnergyDateNav() {
    if (this._energyPeriod === "total") return "";
    const bounds = energyPeriodBounds(this._energyPeriod, this._energyPeriodOffset);
    const label = energyPeriodNavLabel(this._energyPeriod, this._energyPeriodOffset);
    return `<div class="energy-date-nav">
<button type="button" data-action="energy-nav" data-dir="prev" aria-label="Previous period">‹</button>
<span class="energy-date-label">${esc(label)}</span>
<button type="button" data-action="energy-nav" data-dir="next" aria-label="Next period"${bounds.canNext ? "" : " disabled"}>›</button>
</div>`;
  }

  _energyAnalyticsForView(plant) {
    if (this._energyBreakdown) return analyticsFromBreakdown(this._energyBreakdown);
    return readLiveAnalytics(this._hass, plant, this._plantState, this._overviewDaily);
  }

  _renderEnergyBreakdownCard(plant) {
    const a = this._energyAnalyticsForView(plant);
    const has =
      Number(a.pv_production_kwh_today ?? 0) > 0 ||
      Number(a.load_consumption_kwh_today ?? 0) > 0 ||
      this._energyPeriod !== "day" ||
      this._energyPeriodOffset > 0;
    if (!has && (this._energyChartLoading || this._statisticsChartLoading)) {
      return `<div class="card breakdown-card"><p class="chart-loading">Loading breakdown…</p></div>`;
    }
    if (!has) return "";
    const title = energyBreakdownTitle(this._energyPeriod, this._energyPeriodOffset);
    return this._renderEnergyBreakdownRows(a, title);
  }

  _renderEnergyBreakdownRows(a, title) {
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
<p class="card-title">${esc(title)}</p>
<div class="fox-energy-panel">${pvRow}${loadRow}</div>
</div>`;
  }

  _renderEnergyCharts() {
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
    return `<div class="card energy-chart-card">
<p class="card-title">Statistics</p>
${body}
</div>`;
  }

  _renderEnergy(plant) {
    return `<header class="header"><h1>Energy</h1><p>Production and consumption analysis</p></header>
<div class="card energy-analysis-card">
${this._renderEnergyPeriodTabs()}
${this._renderEnergyDateNav()}
</div>
${this._renderEnergyBreakdownCard(plant)}
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
${renderListButton({ action: "settings-sub", sub: "pv" }, "PV Configuration", pvConfigSummary(this._plantState?.pv_config))}
${renderListButton({ action: "settings-sub", sub: "solcast" }, "Solcast", this._solcastSettingsSubtitle())}
${renderListButton({ action: "settings-sub", sub: "storm" }, "StormSafe", stormSub)}
${renderListButton({ action: "settings-sub", sub: "control" }, "Plant control", this._plantState?.control_active ? "Fox Plant manages periods" : "Released to manual")}`;
  }

  _renderSettingsQuick() {
    if (!this._socDraft) this._initSocDraft();
    const plant = this._getPlant();
    const liveSoc = this._liveBatterySoc(plant) ?? 0;
    const validation = validateSocLimits(this._socDraft, liveSoc);
    return `<header class="header"><h1>Quick Settings</h1><p>Drag the three handles — off-grid min, system min, system max</p></header>
<div class="card">
<p class="card-title">SOC limits</p>
${this._renderTripleSoc(plant, this._socDraft, liveSoc)}
<div class="btn-row"><button type="button" class="btn btn-primary" data-action="save-soc" ${this._busy || validation.errors.length ? "disabled" : ""}>Save to inverter</button></div>
</div>`;
  }

  _renderSettingsSchedules() {
    if (!this._chargeDraft) this._initChargeDraft();
    const driftHint = this._plantState?.drift
      ? `<div class="banner warn" style="margin-bottom:12px"><strong>Schedule drift</strong> Inverter and app schedules differ.${this._scheduleSyncButtons()}</div>`
      : "";
    return `<header class="header"><h1>Charge schedule</h1><p>Baseline periods — Fox Plant keeps the inverter in sync</p></header>
${driftHint}
${this._renderPeriodCard(0, this._chargeDraft[0])}
${this._renderPeriodCard(1, this._chargeDraft[1])}
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="save-schedules" ${this._busy ? "disabled" : ""}>Save & apply</button>
<button type="button" class="btn btn-secondary" data-action="sync-schedule" ${this._busy ? "disabled" : ""}>Sync from inverter</button>
<button type="button" class="btn btn-secondary" data-action="reapply-schedule" ${this._busy ? "disabled" : ""}>Re-apply to inverter</button>
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
        const meta = workModeMeta(opt);
        return `<button type="button" class="mode-option ${sel}" data-action="pick-work-mode" data-mode="${esc(opt)}">
<span class="mode-option-body"><span class="name">${esc(meta.title)}</span>${meta.hint ? `<span class="hint">${esc(meta.hint)}</span>` : ""}</span></button>`;
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
<header class="header storm-settings-header"><h1>StormSafe</h1><p>Pre-charge before severe weather — uses <strong>Google Weather</strong> for conditions and hourly forecast lead time</p></header>
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

  _renderPvTiltAzimuthFields(which, { allowWhenDisabled = false } = {}) {
    if (!this._pvDraft) this._initPvDraft();
    const cfg = this._pvDraft[which];
    const stringLabel = which === "pv2" ? "PV2" : "PV1";
    const disabled = this._busy || (!allowWhenDisabled && !cfg.enabled);
    const offHint = !cfg.enabled && !allowWhenDisabled ? " (string off — enable under PV Configuration)" : "";
    return `<div class="pv-geometry-block" data-pv-string="${esc(which)}">
<p class="pv-geometry-label"><strong>${esc(stringLabel)}</strong>${esc(offHint)}</p>
<div class="field">
<label>Tilt (°)</label>
<p class="field-hint">Panel angle from horizontal (default 25° if unset)</p>
<div class="pv-range-row">
<input type="range" min="0" max="90" step="1" data-field="pv:${which}:tilt" value="${esc(String(cfg.tilt))}" ${disabled ? "disabled" : ""}>
<span class="pv-range-value">${esc(String(cfg.tilt))}°</span>
</div>
</div>
<div class="field">
<label>Azimuth (°)</label>
<p class="field-hint">0° = north, 90° = east, 180° = south (default 180° if unset)</p>
<div class="pv-range-row">
<input type="range" min="0" max="359" step="1" data-field="pv:${which}:azimuth" value="${esc(String(cfg.azimuth))}" ${disabled ? "disabled" : ""}>
<span class="pv-range-value">${esc(String(cfg.azimuth))}°</span>
</div>
</div>
</div>`;
  }

  _renderPvStringBlock(which) {
    if (!this._pvDraft) this._initPvDraft();
    const cfg = this._pvDraft[which];
    const sectionTitle = which === "pv2" ? "PV2 configuration" : "PV1 configuration";
    const enabledLabel = which === "pv2" ? "PV2 Enabled" : "PV1 Enabled";
    const arrayHintTarget = which === "pv2" ? "PV2" : "PV1";
    const disabled = this._busy || !cfg.enabled;
    const disabledClass = cfg.enabled ? "" : " pv-string-disabled";
    const nameplateKw = ((cfg.panel_count * cfg.watts_per_panel) / 1000).toFixed(2);
    const effectiveKw = (
      (cfg.panel_count * cfg.watts_per_panel * cfg.efficiency_factor) /
      100000
    ).toFixed(2);
    return `<div class="card pv-string-card${disabledClass}">
<p class="card-title">${esc(sectionTitle)}</p>
<div class="toggle-row"><span><strong>${esc(enabledLabel)}</strong></span>
<input type="checkbox" data-field="pv:${which}:enabled" ${cfg.enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="pv-config-fields">
<div class="field">
<label>PV Array size</label>
<p class="field-hint">Total number of panels on ${esc(arrayHintTarget)}</p>
<div class="pv-range-row">
<input type="range" min="1" max="12" step="1" data-field="pv:${which}:panel_count" value="${esc(String(cfg.panel_count))}" ${disabled ? "disabled" : ""}>
<span class="pv-range-value">${esc(String(cfg.panel_count))}</span>
</div>
</div>
<div class="field">
<label>Wattage per panel</label>
<div class="pv-range-row">
<input type="range" min="100" max="1000" step="10" data-field="pv:${which}:watts_per_panel" value="${esc(String(cfg.watts_per_panel))}" ${disabled ? "disabled" : ""}>
<span class="pv-range-value">${esc(String(cfg.watts_per_panel))} W</span>
</div>
</div>
<div class="field">
<label>Efficiency Factor</label>
<p class="field-hint"><a class="field-link" href="${esc(PV_EFFICIENCY_FACTOR_URL)}" target="_blank" rel="noopener noreferrer">What is the efficiency factor?</a></p>
<input type="number" class="pv-eff-input" min="1" max="100" step="1" data-field="pv:${which}:efficiency_factor" value="${esc(String(cfg.efficiency_factor))}" ${disabled ? "disabled" : ""} aria-label="Efficiency factor percent"> <span style="font-size:14px">%</span>
</div>
${this._renderPvTiltAzimuthFields(which)}
<p class="field-hint" style="margin-top:4px">Nameplate ${esc(nameplateKw)} kW DC · Effective ${esc(effectiveKw)} kW (after efficiency)</p>
</div>
</div>`;
  }

  _renderPvConfiguration({ title, subtitle }) {
    if (!this._pvDraft) this._initPvDraft();
    return `<header class="header"><h1>${esc(title)}</h1>${subtitle ? `<p>${esc(subtitle)}</p>` : ""}</header>
<section class="card" style="margin-bottom:12px"><p class="card-title">PV Configuration</p>
<p class="field-hint" style="margin:0">Panel count, wattage, efficiency, tilt, and azimuth drive the native Solcast rooftop PV forecast on Overview and Energy charts.</p>
</section>
${this._renderPvStringBlock("pv1")}
${this._renderPvStringBlock("pv2")}
<div class="btn-row"><button type="button" class="btn btn-primary" data-action="save-pv-config" ${this._busy ? "disabled" : ""}>Save PV configuration</button></div>`;
  }

  _renderSettingsPv() {
    return this._renderPvConfiguration({
      title: "PV Configuration",
      subtitle: "Configure PV1 and PV2 arrays for analysis",
    });
  }

  _renderSettingsSolcast() {
    if (!this._solcastDraft) this._initSolcastDraft();
    const draft = this._solcastDraft;
    const live = this._plantState?.solcast ?? {};
    const keyPlaceholder = draft.api_key_set ? "••••••••  (leave blank to keep)" : "Paste Solcast API key";
    const coordConfigured = Boolean(live.coordinates_configured);
    const coordDisplay =
      live.coordinates?.latitude != null && live.coordinates?.longitude != null
        ? `${Number(live.coordinates.latitude).toFixed(SOLCAST_COORD_DECIMALS)}, ${Number(live.coordinates.longitude).toFixed(SOLCAST_COORD_DECIMALS)}`
        : "Not set";
    const installDisplay = live.installation_date
      ? esc(String(live.installation_date))
      : "Not set";
    const installMax = solcastInstallationDateMax();
    const lastFetch = esc(formatSolcastTimestamp(live.cache_updated_at || live.last_fetch_at));
    const nextFetch = esc(formatSolcastNextFetch(live));
    const lastErr = live.last_error ? esc(String(live.last_error)) : "None";
    const pvReqs = live.pv_requests ?? [];
    const pvReqLines = pvReqs.length
      ? pvReqs
          .map(
            (r) =>
              `${esc(r.label)}: ${esc(String(r.capacity_kw))} kW · ${esc(String(r.tilt))}° tilt · ${esc(String(r.azimuth))}° az · loss ${esc(String(r.loss_factor))}`
          )
          .join("<br>")
      : "Enable PV strings in PV Configuration to request rooftop forecasts.";
    const solcastLiveOn = solcastEnabledFromLive(live) && live.fetch_pv_forecast !== false;
    const pvStatus = live.pv_forecast_available
      ? `${live.pv_forecast_periods ?? 0} forecast periods · ${live.pv_power_now_kw != null ? `${Number(live.pv_power_now_kw).toFixed(2)} kW now` : "power pending"}${live.forecast_persisted ? " · cached" : ""}`
      : live.forecast_persisted
        ? `${live.pv_forecast_periods ?? 0} cached periods — awaiting chart reload`
        : solcastLiveOn
          ? "Awaiting PV forecast fetch"
          : "PV forecast off";
    const sched = live.poll_schedule;
    let scheduleHint = "";
    if (sched && draft.auto_update === "daylight") {
      const interval = sched.interval_minutes ?? "—";
      const hours = sched.window_hours ?? "—";
      const until = sched.poll_until ? new Date(sched.poll_until).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";
      const inWin = sched.in_window ? "active now" : "outside window (before sunrise or within 1h of sunset)";
      scheduleHint = `<p class="field-hint">Daylight schedule: <strong>${esc(String(hours))}</strong> h between sunrise and 1 h before sunset · about <strong>${esc(String(interval))}</strong> min between refreshes (spread across your ${esc(String(draft.api_limit))}/day API limit) · polls until <strong>${esc(until)}</strong> · ${esc(inWin)}</p>`;
    } else if (sched && draft.auto_update === "all_day") {
      scheduleHint = `<p class="field-hint">24 h mode: about <strong>${esc(String(sched.interval_minutes ?? "—"))}</strong> min between refreshes.</p>`;
    }
    return `<header class="header"><h1>Solcast</h1><p><a class="field-link" href="${esc(SOLCAST_API_DOCS_URL)}" target="_blank" rel="noopener noreferrer">Solcast hobbyist API</a> for <strong>rooftop PV forecast</strong> only — overview weather and StormSafe stay on Google Weather.</p></header>
<div class="card">
<p class="card-title">Account</p>
<p class="field-hint">Register a free <a class="field-link" href="${esc(SOLCAST_HOBBYIST_URL)}" target="_blank" rel="noopener noreferrer">Home PV System</a> account (10 API requests/day). All quota goes to PV forecasts — no weather calls.</p>
<div class="toggle-row"><span><strong>Enable Solcast PV forecast</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Replaces a third-party Solcast integration for chart PV lines</span></span>
<input type="checkbox" data-field="solcast:enabled" ${draft.enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>API key</label>
<input type="password" autocomplete="off" data-field="solcast:api_key" value="${esc(String(draft.api_key || ""))}" placeholder="${esc(keyPlaceholder)}" ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>API limit (requests per day)</label>
<p class="field-hint">Hobbyist plans are typically 10/day — used to spread automatic polling.</p>
<input type="number" min="1" max="50" step="1" data-field="solcast:api_limit" value="${esc(String(draft.api_limit))}" ${this._busy ? "disabled" : ""}></div>
</div>
<div class="card">
<p class="card-title">Auto update</p>
<div class="field"><label>Schedule</label>
<select data-field="solcast:auto_update" ${this._busy ? "disabled" : ""}>
<option value="daylight" ${draft.auto_update === "daylight" ? "selected" : ""}>Automatic update of forecasts from sunrise to sunset</option>
<option value="all_day" ${draft.auto_update === "all_day" ? "selected" : ""}>Automatic update over 24 hours</option>
</select></div>
${scheduleHint}
<p class="field-hint">Each refresh uses <strong>1 request per unique tilt/azimuth group</strong>. In daylight mode, your ${esc(String(draft.api_limit))} daily calls are spread from <strong>sunrise</strong> until <strong>1 hour before sunset</strong> (from Home Assistant <code>sun.sun</code>).</p>
<div class="toggle-row" style="margin-top:12px"><span><strong>Fetch PV forecast</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Uses hobbyist <code>rooftop_sites/{resource_id}/forecasts</code> (matched to your toolkit Home PV sites)</span></span>
<input type="checkbox" data-field="solcast:fetch_pv_forecast" ${draft.fetch_pv_forecast ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
</div>
<div class="card">
<p class="card-title">Rooftop tilt &amp; azimuth</p>
<p class="field-hint" style="margin:0">Used for each enabled PV string on the Solcast API. Panel count, wattage, and efficiency are under <strong>Settings → PV Configuration</strong>. Saved together when you press <strong>Save</strong> below.</p>
${this._renderPvTiltAzimuthFields("pv1", { allowWhenDisabled: true })}
${this._renderPvTiltAzimuthFields("pv2", { allowWhenDisabled: true })}
</div>
<div class="card">
<p class="card-title">Solcast site location</p>
<p class="field-hint">Hobbyist accounts may register <strong>two</strong> rooftop sites on <a class="field-link" href="${esc(SOLCAST_ACCOUNT_LOCATIONS_URL)}" target="_blank" rel="noopener noreferrer">Solcast → Locations</a>. Enter the <strong>latitude and longitude exactly as shown there</strong> for the site you use. Do <strong>not</strong> copy Home Assistant home coordinates — extra decimal places will not match Solcast and API calls can fail or return the wrong site.</p>
<div class="field"><label>Latitude <span class="field-required">*</span></label>
<input type="number" step="0.0001" inputmode="decimal" data-field="solcast:latitude" value="${esc(String(draft.latitude))}" placeholder="e.g. -33.8568" ${this._busy ? "disabled" : ""} required></div>
<div class="field"><label>Longitude <span class="field-required">*</span></label>
<input type="number" step="0.0001" inputmode="decimal" data-field="solcast:longitude" value="${esc(String(draft.longitude))}" placeholder="e.g. 151.2153" ${this._busy ? "disabled" : ""} required></div>
<p class="field-hint">Saved as ${SOLCAST_COORD_DECIMALS} decimal places to match typical Solcast listings. Saved site: <strong>${esc(coordDisplay)}</strong>${coordConfigured ? "" : " — required when Solcast is enabled"}</p>
<div class="field"><label>Installation date</label>
<p class="field-hint">Same field as Solcast <strong>Add Home PV System</strong> (used for age derating on their site). Optional here — not sent to the rooftop API yet. Use your best estimate if unsure.</p>
<input type="date" data-field="solcast:installation_date" value="${esc(String(draft.installation_date || ""))}" max="${esc(installMax)}" ${this._busy ? "disabled" : ""}></div>
<p class="field-hint">Saved: <strong>${installDisplay}</strong></p>
<div class="field"><label>Data period</label>
<p class="field-hint">PT30M = 30-minute resolution (recommended for hobbyist quota).</p>
<input type="text" data-field="solcast:period" value="${esc(String(draft.period))}" readonly></div>
</div>
<div class="card">
<p class="card-title">Status</p>
<div class="entity-list">
<div class="entity-row"><span class="entity-name">API used today</span><span class="entity-value">${esc(String(live.api_used_today ?? 0))} / ${esc(String(live.api_limit ?? draft.api_limit))}</span></div>
<div class="entity-row"><span class="entity-name">Remaining today</span><span class="entity-value">${esc(String(live.api_remaining ?? "—"))}</span></div>
<div class="entity-row"><span class="entity-name">Last fetch</span><span class="entity-value">${lastFetch}</span></div>
<div class="entity-row"><span class="entity-name">Next fetch</span><span class="entity-value">${nextFetch}</span></div>
<div class="entity-row"><span class="entity-name">Last error</span><span class="entity-value">${lastErr}</span></div>
<div class="entity-row"><span class="entity-name">PV forecast</span><span class="entity-value">${esc(pvStatus)}</span></div>
<div class="entity-row"><span class="entity-name">Installation date</span><span class="entity-value">${installDisplay}</span></div>
<div class="entity-row"><span class="entity-name">Toolkit sites</span><span class="entity-value">${esc(
      live.hobbyist_sites_resolved
        ? (live.rooftop_sites_meta ?? [])
            .map((s) => `${s.label}: ${s.name || s.resource_id}`)
            .join(" · ") || "Linked"
        : "Not linked — press Save"
    )}</span></div>
</div>
<p class="field-hint" style="margin-top:8px"><strong>API groups</strong> (from PV config):<br>${pvReqLines}</p>
<p class="field-hint">Diagnostic sensors expose <code>detailed_forecast</code> for automations — charts use plant state directly.</p>
</div>
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="save-solcast-settings" ${this._busy ? "disabled" : ""}>Save</button>
<button type="button" class="btn btn-secondary" data-action="test-solcast" ${this._busy ? "disabled" : ""}>Test connection</button>
<p class="field-hint" style="margin-top:10px">Test lists your <strong>Home PV systems</strong> from the Solcast toolkit (does not use your daily forecast quota).</p>
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
      case "pv":
        return this._renderSettingsPv();
      case "solcast":
        return this._renderSettingsSolcast();
      case "storm":
        return this._renderSettingsStorm();
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
        return this._renderEnergy(plant);
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
    this._syncPanelBuildFooter(shell);

    const headerEl = shell.querySelector(".page-header");
    if (this._headerHasSubTabs !== showSubTabs) {
      this._rebuildPageHeader(headerEl);
    } else {
      this._syncTabActive(headerEl);
    }

    const mainEl = shell.querySelector(".main");
    if (this._view === "overview") {
      this._renderOverviewMain(mainEl, plant);
    } else {
      this._flowSceneKey = undefined;
      this._flowScenePlantId = undefined;
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      mainEl.innerHTML = this._renderView(plant);
    }

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
    if (this._view === "overview") {
      bindOverviewDailyCharts(this._root);
      if (this._batterySocChart?.socPts?.length) {
        this._bindBatterySocChart();
      }
    }
    if (this._view === "energy") {
      const plant = this._getPlant();
      if (!plant) return;
      const cacheKey = this._energyChartCacheKey(plant);
      if (this._energyPeriod === "day") {
        if (!this._statisticsChartLoading && (this._statisticsChartPlantId !== cacheKey || !this._statisticsChart)) {
          this._loadStatisticsChart();
        }
      } else if (!this._energyChartLoading && (this._energyChartPlantId !== cacheKey || !this._energyChart)) {
        this._loadEnergyCharts();
      }
    }
    if (this._view === "overview") {
      const plant = this._getPlant();
      if (
        plant &&
        !this._statisticsChartLoading &&
        (this._statisticsChartPlantId !== `${plant.entry_id}:overview` || !this._statisticsChart)
      ) {
        this._loadOverviewStatisticsChart();
      }
      if (
        plant &&
        !this._batterySocChartLoading &&
        (this._batterySocChartPlantId !== plant.entry_id || !this._batterySocChart)
      ) {
        this._loadBatterySocChart();
      }
      if (
        plant &&
        !this._overviewDailyLoading &&
        (this._overviewDailyPlantId !== plant.entry_id || !this._overviewDaily)
      ) {
        this._loadOverviewDailyCards();
      }
    }
  }
}

registerFoxessPlantPanel();
