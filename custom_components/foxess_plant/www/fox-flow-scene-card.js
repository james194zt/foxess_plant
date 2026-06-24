/**
 * Lovelace card: Fox ESS live energy flow house scene (Fox Plant overview).
 * Resource: /foxess_plant_panel/fox-flow-scene-card.js (type: module)
 *
 * Bootstrap (define + picker) runs first so the Add-card dialog never waits on
 * a 600-line module still parsing. Full scene logic attaches at file end.
 */
const FoxFlowScene = {
  ready: false,

  getStubConfig() {
    return { show_weather: true };
  },

  getConfigForm() {
    return {
      schema: [
        { name: "plant_id", selector: { text: {} } },
        { name: "weather_entity", selector: { entity: { domain: ["weather"] } } },
        { name: "show_weather", default: true, selector: { boolean: {} } },
      ],
      computeLabel: (schema) => {
        if (schema.name === "plant_id") return "FoxESS Plant entry ID (optional)";
        if (schema.name === "weather_entity") return "Weather entity (optional)";
        if (schema.name === "show_weather") return "Show weather on scene";
        return undefined;
      },
      computeHelper: (schema) => {
        if (schema.name === "plant_id") {
          return "Leave blank to auto-discover FoxESS entities from your installation.";
        }
        return undefined;
      },
    };
  },

  setConfig(el, config) {
    if (!config) throw new Error("Invalid configuration");
    el._config = config;
    el._plantState = null;
    el._plantMap = null;
    el._flowKey = null;
    if (FoxFlowScene.ready) FoxFlowScene.schedulePlantPoll(el);
    FoxFlowScene.render(el);
  },

  setHass(el, hass) {
    el._hass = hass;
    FoxFlowScene.render(el);
  },

  connectedCallback(el) {
    if (FoxFlowScene.ready) FoxFlowScene.schedulePlantPoll(el);
  },

  disconnectedCallback(el) {
    if (el._plantPollTimer) {
      clearInterval(el._plantPollTimer);
      el._plantPollTimer = null;
    }
  },

  render(el) {
    if (!el.shadowRoot) return;
    if (!FoxFlowScene.ready || !el._hass) {
      el.shadowRoot.innerHTML =
        '<style>:host{display:block}.p{padding:24px 16px;text-align:center;color:var(--secondary-text-color,#888);font-size:14px}</style><div class="p">Fox Flow Scene</div>';
      return;
    }
    FoxFlowScene.renderFull(el);
  },
};

class FoxFlowSceneCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._plantState = null;
    this._plantMap = null;
    this._flowKey = null;
    this._plantPollTimer = null;
  }

  static getStubConfig(hass, entities, entitiesFallback) {
    return FoxFlowScene.getStubConfig(hass, entities, entitiesFallback);
  }

  static getConfigForm() {
    return FoxFlowScene.getConfigForm();
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return {
      rows: 4,
      columns: 12,
      min_rows: 3,
      min_columns: 6,
    };
  }

  setConfig(config) {
    FoxFlowScene.setConfig(this, config);
  }

  set hass(hass) {
    FoxFlowScene.setHass(this, hass);
  }

  connectedCallback() {
    FoxFlowScene.connectedCallback(this);
  }

  disconnectedCallback() {
    FoxFlowScene.disconnectedCallback(this);
  }
}

if (!customElements.get("fox-flow-scene-card")) {
  customElements.define("fox-flow-scene-card", FoxFlowSceneCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "fox-flow-scene-card")) {
  window.customCards.push({
    type: "fox-flow-scene-card",
    name: "Fox Flow Scene",
    description: "Live Fox ESS house energy flow scene (Fox Plant overview)",
    preview: false,
    documentationURL: "https://github.com/james194zt/foxess_plant",
    getEntitySuggestion: (hass, entityId) => {
      const domain = entityId.split(".")[0];
      if (domain !== "weather") return null;
      return {
        config: {
          type: "custom:fox-flow-scene-card",
          weather_entity: entityId,
          show_weather: true,
        },
      };
    },
  });
}

const FLOW_SCENE_ASSET_VER = 48;
const STATIC_BASE = "/foxess_plant_panel";
const FLOW_PATHS_VER = "flow-comet-v3";
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
const FLOW_STROKE = { hubR: 6.5 };
const FLOW_PIPE_STROKE = { day: "#5E6A78", night: "#9AA8B8" };
const FLOW_ACTIVE_STROKE = {
  solar: "#FFC400",
  grid: "#3D9AFF",
  export: "#C06AFF",
  battery: "#00FF66",
  home: "#00FF66",
};
const FLOW_COMET = { pathLen: 100, pulse: 12, hubHeadSw: 3.5, headSw: 3, glowScale: 2.35 };
const FLOW_SCENE_PV_THRESHOLD_W = 40;
const FLOW_SCENE_CANVAS_BG_DARK = "#000000";
const FLOW_SCENE_CANVAS_BG_LIGHT = "#ffffff";
const FLOW_SCENE_BG_THEMES = new Set(["day_light", "day_dark", "night_light", "night_dark"]);

const ENTITY_FALLBACKS = {
  pv_power: ["pv_power_evo_10", "pv_power_now", "pv_power", "pv_power_total", "pv1_power"],
  battery_soc: ["battery_soc_1", "battery_soc"],
  battery_power: ["invbatpower_1", "invbatpower", "battery_power"],
  battery_status: ["battery_status_evo_10", "battery_status"],
  grid_import: ["grid_consumption", "grid_import"],
  grid_export: ["feed_in", "grid_export"],
  load_power: ["load_power", "load_power_total"],
};

function flowPipeStroke(isNight) {
  return isNight ? FLOW_PIPE_STROKE.night : FLOW_PIPE_STROKE.day;
}

function flowActiveStroke(cls) {
  if (cls === "flow-solar") return FLOW_ACTIVE_STROKE.solar;
  if (cls === "flow-grid") return FLOW_ACTIVE_STROKE.grid;
  if (cls === "flow-export") return FLOW_ACTIVE_STROKE.export;
  if (cls === "flow-home-line") return FLOW_ACTIVE_STROKE.home;
  return FLOW_ACTIVE_STROKE.battery;
}

function flowHubSpokeCls(id, gridExporting) {
  if (id.startsWith("solar")) return "flow-solar";
  if (id.includes("grid")) return gridExporting && id === "hub-grid" ? "flow-export" : "flow-grid";
  return "flow-battery";
}

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
  const sw = 6;
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
      if (!line || !FOX_FLOW_HUB_SPOKES.has(id) || !activeIds.has(id)) return "";
      const cls = flowHubSpokeCls(id, gridExporting);
      const stroke = flowActiveStroke(cls);
      const headSw = cls === "flow-battery" ? FLOW_COMET.hubHeadSw : FLOW_COMET.headSw;
      return flowCometPaths({ d, cls, headSw, stroke, reverse: !!line?.reverse });
    })
    .join("");
  return idleHtml + activeHtml;
}

function inferBatteryFlowDirection(flows, threshold = FLOW_SCENE_PV_THRESHOLD_W) {
  const st = String(flows.batteryStatus || "").toLowerCase();
  if (st.includes("discharg")) return { discharging: true, charging: false };
  if (st.includes("charg")) return { discharging: false, charging: true };
  const w = flows.batteryW;
  return { discharging: w > threshold, charging: w < -threshold };
}

function computeFlowLines(flows, threshold = FLOW_SCENE_PV_THRESHOLD_W) {
  const lines = [];
  const hasPv = flows.pvW > threshold;
  const hasGridIn = flows.gridImportW > threshold;
  const hasGridOut = flows.gridExportW > threshold;
  const { discharging, charging } = inferBatteryFlowDirection(flows, threshold);
  const hasLoad = flows.loadW > threshold;
  const aioToHub = hasPv || discharging || hasGridOut;
  if (hasPv) lines.push({ id: "solar-aio" });
  if (hasGridIn) lines.push({ id: "grid-hub" });
  if (hasGridOut) lines.push({ id: "hub-grid" });
  if (aioToHub) lines.push({ id: "aio-hub" });
  else if (charging) lines.push({ id: "hub-aio", reverse: true });
  if (hasLoad && (hasGridOut || hasGridIn || aioToHub || charging || hasPv)) {
    lines.push({ id: "hub-home" });
  }
  return lines;
}

function flowSceneStructureKey(lines, gridExporting, isNight, bgTheme, haUiDark) {
  const active = lines
    .map((l) => `${l.id}${l.reverse ? ":r" : ""}`)
    .sort()
    .join(",");
  return `${bgTheme}|${haUiDark ? "haD" : "haL"}|${isNight ? "n" : "d"}|${gridExporting ? "x" : "i"}|${active}`;
}

function entityIdMatchesSuffix(entityId, suffix) {
  const id = String(entityId || "");
  if (id.endsWith(`_${suffix}`)) return true;
  const dot = id.lastIndexOf(".");
  return (dot >= 0 ? id.slice(dot + 1) : id) === suffix;
}

function resolveEntityMap(hass, configEntities = {}, plantStateMap = {}) {
  const map = { ...plantStateMap, ...(configEntities || {}) };
  if (!hass?.states) return map;
  const ids = Object.keys(hass.states);
  for (const [key, suffixes] of Object.entries(ENTITY_FALLBACKS)) {
    if (map[key]) continue;
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

function stateNumber(hass, entityId) {
  if (!entityId || !hass?.states) return 0;
  const st = hass.states[entityId];
  if (!st || st.state === "unavailable" || st.state === "unknown") return 0;
  const n = parseFloat(st.state);
  return Number.isFinite(n) ? n : 0;
}

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
  if (Math.abs(n) > 500) return n;
  return n * 1000;
}

function readEnergyFlows(hass, entityMap) {
  const pvW = statePowerWatts(hass, entityMap.pv_power);
  const loadW = Math.abs(statePowerWatts(hass, entityMap.load_power));
  const gridImportW = statePowerWatts(hass, entityMap.grid_import);
  const gridExportW = statePowerWatts(hass, entityMap.grid_export);
  const batteryW = statePowerWatts(hass, entityMap.battery_power);
  let batteryStatus = "Idle";
  const statusEntity = entityMap.battery_status;
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
    batterySoc: stateNumber(hass, entityMap.battery_soc),
    batteryStatus,
  };
}

function formatFoxPower(w) {
  const abs = Math.abs(w);
  if (abs < 1000) return `${Math.round(abs)} W`;
  const kw = abs / 1000;
  return kw < 10 ? `${kw.toFixed(2)} kW` : `${kw.toFixed(1)} kW`;
}

function formatPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${Math.round(Math.min(100, Math.max(0, n)))}%`;
}

function cssColorLuminance(color) {
  const raw = String(color || "").trim();
  if (!raw) return null;
  let r = 0;
  let g = 0;
  let b = 0;
  const hex = raw.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const h = hex[1].length === 3 ? hex[1].split("").map((c) => c + c).join("") : hex[1];
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

function resolveHaUiDark(hass) {
  if (typeof hass?.themes?.darkMode === "boolean") return hass.themes.darkMode;
  try {
    const bg = getComputedStyle(document.documentElement).getPropertyValue("--primary-background-color").trim();
    const lum = cssColorLuminance(bg);
    if (lum != null) return lum < 0.45;
  } catch (_) {
    /* ignore */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function resolveFlowScenePeriodFromSun(hass) {
  const sun = hass?.states?.["sun.sun"];
  if (!sun?.state || sun.state === "unknown" || sun.state === "unavailable") return null;
  return sun.state === "above_horizon" ? "day" : "night";
}

function normalizeFlowSceneTheme(theme) {
  if (!theme || typeof theme !== "string") return null;
  if (FLOW_SCENE_BG_THEMES.has(theme)) return theme;
  if (theme.startsWith("day_")) return "day_dark";
  if (theme.startsWith("night_")) return "night_dark";
  return null;
}

function resolveFlowSceneBgTheme(hass, plantState) {
  const period =
    resolveFlowScenePeriodFromSun(hass) ||
    (() => {
      const t = normalizeFlowSceneTheme(plantState?.flow_scene_theme);
      if (!t) return null;
      return t.startsWith("day_") ? "day" : "night";
    })() ||
    "day";
  const suffix = resolveHaUiDark(hass) ? "dark" : "light";
  return `${period}_${suffix}`;
}

function flowSceneLayerUrl(layer, bgTheme) {
  if (layer === "backdrop") {
    return `${STATIC_BASE}/flow_home_bg_scene_${bgTheme}.png?v=${FLOW_SCENE_ASSET_VER}`;
  }
  return `${STATIC_BASE}/flow_${layer}_scene_${bgTheme}.png?v=${FLOW_SCENE_ASSET_VER}`;
}

function weatherOverlayHtml(hass, plantState, weatherEntity) {
  const wx = plantState?.overview_weather;
  let temp = wx?.temperature_display || "";
  let label = wx?.condition_label || "";
  if ((!temp && !label) && weatherEntity && hass?.states?.[weatherEntity]) {
    const st = hass.states[weatherEntity];
    temp = st.attributes?.temperature != null ? `${st.attributes.temperature}°` : "";
    label = st.state ? String(st.state).replace(/-/g, " ") : "";
  }
  if (!temp && !label) return "";
  const aria = [temp, label].filter(Boolean).join(", ");
  return `<div class="weather" role="img" aria-label="${aria}"><span class="weather-temp">${temp}</span><span class="weather-label">${label}</span></div>`;
}

const CARD_STYLES = `
:host { display: block; }
.card {
  overflow: hidden;
  border-radius: var(--ha-card-border-radius, 12px);
  background: var(--card-background-color, #1c1c1c);
  box-shadow: var(--ha-card-box-shadow, none);
}
.scene-card--fox-flow {
  padding: 0; border: none; border-radius: 0; background: transparent;
  width: 100%; margin: 0; overflow: hidden;
}
.fox-flow-scene { display: block; width: 100%; }
.fox-flow-scene--ha-dark { background: ${FLOW_SCENE_CANVAS_BG_DARK}; }
.fox-flow-scene--ha-light { background: ${FLOW_SCENE_CANVAS_BG_LIGHT}; }
.fox-flow-stage { position: relative; width: 100%; }
.fox-flow-scene--ha-dark .fox-flow-stage { background: ${FLOW_SCENE_CANVAS_BG_DARK}; }
.fox-flow-scene--ha-light .fox-flow-stage { background: ${FLOW_SCENE_CANVAS_BG_LIGHT}; }
.fox-flow-stage::before { content: ""; display: block; width: 100%; padding-top: 99.31640625%; }
.fox-flow-layer {
  position: absolute; pointer-events: none; user-select: none;
  inset: 0; width: 100%; height: 100%;
  object-fit: contain; object-position: center bottom;
}
.fox-flow-layer-backdrop { z-index: 0; }
.fox-flow-layer-pv, .fox-flow-layer-aio { z-index: 2; }
.fox-flow-svg {
  position: absolute; inset: 0; width: 100%; height: 100%;
  z-index: 3; pointer-events: none;
}
.weather {
  position: absolute; z-index: 5; top: 3%; left: 4%;
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.85);
  pointer-events: none;
}
.fox-flow-scene--day .weather { color: rgba(30,30,30,0.85); }
.weather-temp { letter-spacing: -0.01em; }
.weather-label { color: rgba(255,255,255,0.62); text-transform: capitalize; }
.fox-flow-scene--day .weather-label { color: rgba(30,30,30,0.62); }
.fox-flow-badge {
  position: absolute; z-index: 4;
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  pointer-events: none; text-align: center;
}
.fox-flow-badge-label {
  font-size: 10px; font-weight: 600; color: rgba(255,255,255,0.62);
  text-transform: uppercase; letter-spacing: 0.06em; line-height: 1.2;
}
.fox-flow-badge-value {
  font-size: 12px; font-weight: 600; color: #fff; line-height: 1.25;
}
.fox-flow-badge-solar { left: 50%; top: 1%; transform: translateX(-50%); }
.fox-flow-scene--day .fox-flow-badge-solar .fox-flow-badge-label { color: rgba(30,30,30,0.72); }
.fox-flow-scene--day .fox-flow-badge-solar .fox-flow-badge-value { color: #1a1a1a; }
.fox-flow-badge-grid { left: 4%; bottom: 6%; align-items: flex-start; }
.fox-flow-badge-battery { left: 50%; bottom: 6%; transform: translateX(-50%); }
.fox-flow-badge-home { right: 4%; bottom: 6%; align-items: flex-end; }
.fox-flow-scene--ha-light .fox-flow-badge-grid .fox-flow-badge-label,
.fox-flow-scene--ha-light .fox-flow-badge-battery .fox-flow-badge-label,
.fox-flow-scene--ha-light .fox-flow-badge-home .fox-flow-badge-label {
  color: var(--secondary-text-color, rgba(30,30,30,0.72));
}
.fox-flow-scene--ha-light .fox-flow-badge-grid .fox-flow-badge-value,
.fox-flow-scene--ha-light .fox-flow-badge-battery .fox-flow-badge-value,
.fox-flow-scene--ha-light .fox-flow-badge-home .fox-flow-badge-value {
  color: var(--primary-text-color, #1a1a1a);
}
.flow-path { fill: none; stroke-linecap: round; stroke-linejoin: round; }
.flow-comet { fill: none; stroke-linejoin: round; pointer-events: none; }
.flow-comet-glow { opacity: 0.48; }
.flow-comet-pulse { opacity: 1; animation: flow-comet-pulse-fwd 1.75s linear infinite; }
.flow-comet-glow { animation: flow-comet-pulse-fwd 1.75s linear infinite; }
.flow-comet-pulse.flow-solar, .flow-comet-glow.flow-solar { animation-duration: 1.55s; }
.flow-comet-pulse.reverse, .flow-comet-glow.reverse { animation-name: flow-comet-pulse-rev; }
.flow-hub-dot.active { filter: drop-shadow(0 0 10px rgba(0, 255, 102, 0.95)); }
@keyframes flow-comet-pulse-fwd {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: -100; }
}
@keyframes flow-comet-pulse-rev {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: 100; }
}
.placeholder {
  padding: 24px 16px; text-align: center; color: var(--secondary-text-color, #888);
  font-size: 14px;
}
`;

FoxFlowScene.schedulePlantPoll = function schedulePlantPoll(el) {
  if (el._plantPollTimer) {
    clearInterval(el._plantPollTimer);
    el._plantPollTimer = null;
  }
  if (!el._config?.plant_id) return;
  void FoxFlowScene.refreshPlantState(el);
  el._plantPollTimer = setInterval(() => void FoxFlowScene.refreshPlantState(el), 60000);
};

FoxFlowScene.refreshPlantState = async function refreshPlantState(el) {
  if (!el._hass?.connection || !el._config?.plant_id) return;
  try {
    const state = await el._hass.connection.sendMessagePromise({
      type: "foxess_plant/plant_state",
      plant_id: el._config.plant_id,
    });
    el._plantState = state;
    el._plantMap = state?.entity_map || null;
    FoxFlowScene.renderFull(el);
  } catch (err) {
    console.warn("Fox flow scene card: plant_state failed", err);
  }
};

FoxFlowScene.flowContext = function flowContext(el) {
  const hass = el._hass;
  const entityMap = resolveEntityMap(hass, el._config.entities, el._plantMap || {});
  const flows = readEnergyFlows(hass, entityMap);
  const lines = computeFlowLines(flows);
  const activeIds = new Set(lines.map((l) => l.id));
  const bgTheme = resolveFlowSceneBgTheme(hass, el._plantState);
  const haUiDark = resolveHaUiDark(hass);
  const isNight = !bgTheme.startsWith("day_");
  const soc = Math.min(100, Math.max(0, flows.batterySoc));
  const gridExporting =
    flows.gridExportW > flows.gridImportW && flows.gridExportW > FLOW_SCENE_PV_THRESHOLD_W;
  return {
    flows,
    lines,
    activeIds,
    bgTheme,
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
};

FoxFlowScene.patchBadges = function patchBadges(stage, ctx) {
  const set = (sel, text) => {
    const badge = stage.querySelector(sel);
    if (badge) badge.textContent = text;
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
};

FoxFlowScene.renderSceneHtml = function renderSceneHtml(el, ctx) {
  const pathsHtml = renderFlowScenePaths({
    lines: ctx.lines,
    activeIds: ctx.activeIds,
    gridExporting: ctx.gridExporting,
    isNight: ctx.isNight,
  });
  const haClass = ctx.haUiDark ? "fox-flow-scene--ha-dark" : "fox-flow-scene--ha-light";
  const weather =
    el._config.show_weather === false
      ? ""
      : weatherOverlayHtml(el._hass, el._plantState, el._config.weather_entity);
  const hubFill = ctx.hubActive ? FLOW_ACTIVE_STROKE.battery : flowPipeStroke(ctx.isNight);
  return `
<div class="scene-card--fox-flow">
<div class="fox-flow-scene ${ctx.isNight ? "fox-flow-scene--night" : "fox-flow-scene--day"} ${haClass}">
<div class="fox-flow-stage">
<img class="fox-flow-layer fox-flow-layer-backdrop" src="${flowSceneLayerUrl("backdrop", ctx.bgTheme)}" alt="" loading="eager" decoding="async" />
<img class="fox-flow-layer fox-flow-layer-pv" src="${flowSceneLayerUrl("pv", ctx.bgTheme)}" alt="" loading="lazy" decoding="async" />
<img class="fox-flow-layer fox-flow-layer-aio" src="${flowSceneLayerUrl("aio", ctx.bgTheme)}" alt="" loading="lazy" decoding="async" />
<svg class="fox-flow-svg" viewBox="0 0 1024 1017" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
${pathsHtml}
<circle class="flow-hub-dot ${ctx.hubActive ? "active" : ""}" cx="${FOX_FLOW_HUB.x}" cy="${FOX_FLOW_HUB.y}" r="${FLOW_STROKE.hubR}" fill="${hubFill}"/>
</svg>
${weather}
<div class="fox-flow-badge fox-flow-badge-solar">
<span class="fox-flow-badge-label">Solar</span>
<span class="fox-flow-badge-value">${formatFoxPower(ctx.flows.pvW)}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-grid">
<span class="fox-flow-badge-label">${ctx.gridLabel}</span>
<span class="fox-flow-badge-value">${formatFoxPower(ctx.gridPower)}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-battery">
<span class="fox-flow-badge-label">${ctx.batteryStatus}</span>
<span class="fox-flow-badge-value">${formatFoxPower(ctx.batteryPower)} | ${formatPercent(ctx.soc)}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-home">
<span class="fox-flow-badge-label">Home</span>
<span class="fox-flow-badge-value">${formatFoxPower(ctx.flows.loadW)}</span>
</div>
</div>
</div>
</div>`;
};

FoxFlowScene.renderFull = function renderFull(el) {
  if (!el.shadowRoot) return;
  if (!el._hass) {
    el.shadowRoot.innerHTML = `<style>${CARD_STYLES}</style><div class="card"><p class="placeholder">Loading…</p></div>`;
    return;
  }
  const ctx = FoxFlowScene.flowContext(el);
  const stage = el.shadowRoot.querySelector(".fox-flow-stage");
  const canPatch =
    stage &&
    el._flowKey === ctx.key &&
    stage.querySelector(".fox-flow-layer-backdrop")?.src?.includes(ctx.bgTheme);
  if (canPatch) {
    FoxFlowScene.patchBadges(stage, ctx);
    const svg = stage.querySelector(".fox-flow-svg");
    if (svg) {
      const hub = svg.querySelector(".flow-hub-dot");
      if (hub) {
        hub.classList.toggle("active", ctx.hubActive);
        hub.setAttribute("fill", ctx.hubActive ? FLOW_ACTIVE_STROKE.battery : flowPipeStroke(ctx.isNight));
      }
    }
    return;
  }
  el._flowKey = ctx.key;
  el.shadowRoot.innerHTML = `<style>${CARD_STYLES}</style><div class="card">${FoxFlowScene.renderSceneHtml(el, ctx)}</div>`;
};

FoxFlowScene.getStubConfig = function getStubConfig(hass) {
  const weatherEntity =
    hass && hass.states
      ? Object.keys(hass.states).find((id) => id.startsWith("weather."))
      : undefined;
  return {
    show_weather: true,
    ...(weatherEntity ? { weather_entity: weatherEntity } : {}),
  };
};

FoxFlowScene.ready = true;
