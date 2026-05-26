/**
 * FoxESS Plant panel — HA sidebar app (phases 5a–5e).
 * hass / narrow / panel / route from Home Assistant.
 * @version 0.4.4
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

async function callService(hass, domain, service, data) {
  await hass.callService(domain, service, data, undefined, true, true);
}

const SOC_THUMBS = [
  { key: "min_soc", label: "Off-grid min", short: "Off-grid", color: "#e53935" },
  { key: "min_soc_on_grid", label: "System min", short: "On-grid", color: "#f9a825" },
  { key: "max_soc", label: "System max", short: "Max", color: "#2e7d32" },
];

/** Enforce min ≤ system min ≤ max; equal values allowed (e.g. both at 5%). */
function clampSocDraft(d) {
  let min = Math.round(Number(d.min_soc) || 0);
  let mid = Math.round(Number(d.min_soc_on_grid) || 0);
  let max = Math.round(Number(d.max_soc) || 100);
  min = Math.max(0, Math.min(100, min));
  mid = Math.max(0, Math.min(100, mid));
  max = Math.max(0, Math.min(100, max));
  if (mid < min) mid = min;
  if (max < mid) max = mid;
  d.min_soc = min;
  d.min_soc_on_grid = mid;
  d.max_soc = max;
  return d;
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
  border-bottom: 1px solid var(--divider-color);
  background: var(--app-header-background-color, var(--primary-background-color));
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
  margin-bottom: -1px;
  background: transparent;
  color: var(--secondary-text-color);
  font-size: 14px; font-weight: 500; font-family: inherit;
  cursor: pointer; white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
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
.field input[type="time"], .field select {
  width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; font-family: inherit;
}
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
    this._socDrag = null;
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
  }

  connectedCallback() {
    this._root.addEventListener("click", this._onClick);
    this._root.addEventListener("input", this._onInput);
    this._root.addEventListener("change", this._onInput);
    void this._refreshPlantState();
    this._timer = window.setInterval(() => void this._refreshPlantState(), 30000);
    this._render();
  }

  disconnectedCallback() {
    this._root.removeEventListener("click", this._onClick);
    this._root.removeEventListener("input", this._onInput);
    this._root.removeEventListener("change", this._onInput);
    this._endSocDrag();
    if (this._timer) window.clearInterval(this._timer);
    if (this._toastTimer) window.clearTimeout(this._toastTimer);
  }

  set hass(v) {
    this._hass = v;
    if (!this._socDrag) this._render();
  }
  get hass() {
    return this._hass;
  }
  set narrow(v) {
    this._narrow = Boolean(v);
    this._render();
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
      if (!this._socDrag) this._render();
    } catch {
      /* ws optional */
    }
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

  async _handleClick(e) {
    const btn = e.target.closest("[data-action]");
    if (!btn || this._busy) return;
    const action = btn.dataset.action;

    if (action === "nav") {
      this._view = btn.dataset.view;
      this._settingsView = "main";
      this._deviceSub = "main";
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
      this._render();
      return;
    }
    if (action === "settings-tab") {
      this._view = "settings";
      this._settingsView = btn.dataset.sub;
      if (btn.dataset.sub === "schedules") this._initChargeDraft();
      if (btn.dataset.sub === "quick") this._initSocDraft();
      if (btn.dataset.sub === "workmode") this._initWorkModeDraft();
      this._render();
      return;
    }
    if (action === "pick-work-mode") {
      this._workModeDraft = btn.dataset.mode;
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
    }
  }

  _handleInput(e) {
    const el = e.target;
    if (!el?.dataset?.field) return;
    const parts = el.dataset.field.split(":");
    const kind = parts[0];
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
    if ((kind === "soc" || kind === "soc-num") && this._socDraft) {
      const field = parts[1];
      this._socDraft[field] = parseFloat(el.value);
      clampSocDraft(this._socDraft);
      this._updateTripleSocDom();
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
    let pct = Math.round(((e.clientX - rect.left) / rect.width) * 100);
    pct = Math.max(0, Math.min(100, pct));
    const key = this._socDrag.thumb;
    const d = this._socDraft;
    if (key === "min_soc") {
      d.min_soc = Math.min(pct, d.min_soc_on_grid);
    } else if (key === "min_soc_on_grid") {
      d.min_soc_on_grid = Math.max(d.min_soc, Math.min(pct, d.max_soc));
    } else if (key === "max_soc") {
      d.max_soc = Math.max(d.min_soc_on_grid, pct);
    }
    clampSocDraft(d);
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
        `<div><label>${esc(t.label)}</label><input type="number" min="0" max="100" step="1" data-field="soc-num:${t.key}" value="${clamped[t.key]}"></div>`
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
<div class="triple-soc-scale"><span>0%</span><span>100%</span></div>
</div>
<div class="soc-legend">
<span><i style="background:#e53935"></i> Below off-grid min</span>
<span><i style="background:#f9a825"></i> Off-grid reserve</span>
<span><i style="background:#2e7d32"></i> Normal use</span>
<span><i style="background:var(--fp-accent)"></i> Charge headroom</span>
</div>
<div class="soc-numeric">${numericHtml}</div>
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
    const map = plant?.entity_map ?? {};
    if (!plant || !this._socDraft) return;
    const clamped = clampSocDraft({ ...this._socDraft });
    const { min_soc, min_soc_on_grid, max_soc } = clamped;
    this._socDraft = clamped;
    this._busy = true;
    this._render();
    try {
      const pairs = [
        ["min_soc", min_soc],
        ["min_soc_on_grid", min_soc_on_grid],
        ["max_soc", max_soc],
      ];
      for (const [key, value] of pairs) {
        const entity_id = map[key];
        if (entity_id) {
          await callService(this._hass, "number", "set_value", { entity_id, value });
        }
      }
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
</div>`;
  }

  _renderDevice(plant) {
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
<p class="placeholder" style="margin-top:14px;font-size:13px">Day / month / year charts — phase 5f (next).</p>`;
  }

  _renderPeriodCard(idx, period) {
    const p = period || DEFAULT_PERIODS[0];
    const actual = this._plantState?.actual_periods?.[idx];
    const drift =
      actual &&
      (Boolean(p.enable_force_charge) !== Boolean(actual.enable_force_charge) ||
        Boolean(p.enable_charge_from_grid) !== Boolean(actual.enable_charge_from_grid));
    return `<div class="period-card">
<h4>Period ${idx + 1} ${drift ? '<span style="color:var(--fp-amber);font-size:12px">≠ inverter</span>' : ""}</h4>
<div class="toggle-row"><span>Force charge</span><input type="checkbox" data-field="period:${idx}:enable_force_charge" ${p.enable_force_charge ? "checked" : ""}></div>
<div class="toggle-row"><span>Charge from grid</span><input type="checkbox" data-field="period:${idx}:enable_charge_from_grid" ${p.enable_charge_from_grid ? "checked" : ""}></div>
<div class="field"><label>Start</label><input type="time" data-field="period:${idx}:start" value="${esc(timeForInput(p.start))}"></div>
<div class="field"><label>End</label><input type="time" data-field="period:${idx}:end" value="${esc(timeForInput(p.end))}"></div>
</div>`;
  }

  _renderSettingsMain(plant) {
    const s = this._plantState?.settings ?? {};
    const storm = this._plantState?.storm_prep ?? {};
    const armed = Boolean(this._plantState?.active_storm_triggers?.length);
    return `<header class="header"><h1>Settings</h1><p>Quick controls for your plant</p></header>
${this._modeBanner()}
<button type="button" class="list-btn" data-action="settings-sub" data-sub="quick"><span>Quick Settings<span class="sub">Max ${s.max_soc ?? "—"}% · Min ${s.min_soc ?? "—"}% · Off-grid ${s.min_soc_on_grid ?? "—"}%</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="schedules"><span>Charge schedule<span class="sub">Two charge windows (baseline)</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="workmode"><span>Work mode<span class="sub">${esc(s.work_mode ?? "—")}</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="storm"><span>StormSafe<span class="sub">${storm.enabled ? (armed ? "Active now" : "Armed") : "Disabled in config"}</span></span><span class="chev">›</span></button>
<button type="button" class="list-btn" data-action="settings-sub" data-sub="control"><span>Plant control<span class="sub">${this._plantState?.control_active ? "Fox Plant manages periods" : "Released to manual"}</span></span><span class="chev">›</span></button>`;
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
    const storm = this._plantState?.storm_prep ?? {};
    const armed = Boolean(this._plantState?.active_storm_triggers?.length);
    const triggers = this._plantState?.active_storm_triggers ?? [];
    const configured = storm.trigger_entities ?? [];
    return `<header class="header"><h1>StormSafe</h1><p>${storm.enabled ? "Enabled in integration config" : "Enable under Integration → Configure"}</p></header>
${this._renderStormHero(armed)}
<div class="card">
<p class="card-title">Status</p>
<p style="margin:0 0 10px;font-size:14px">${armed ? "Storm prep is <strong>active</strong> — override schedule applied." : "No storm triggers active."}</p>
${triggers.length ? `<div>${triggers.map((t) => `<span class="trigger-chip">${esc(t)}</span>`).join("")}</div>` : ""}
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="arm-storm" ${this._busy ? "disabled" : ""}>Test arm storm prep</button>
<button type="button" class="btn btn-secondary" data-action="disarm-storm" ${this._busy ? "disabled" : ""}>Disarm override</button>
</div>
</div>
<div class="card"><p class="card-title">Configured triggers (${configured.length})</p>
${configured.length ? configured.map((t) => `<span class="trigger-chip">${esc(t)}</span>`).join("") : '<p style="margin:0;font-size:13px;color:var(--secondary-text-color)">Add weather or binary sensors in storm prep options.</p>'}
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
      this._root.innerHTML = `<div class="main"><p class="placeholder">Loading Fox Plant…</p></div>`;
      return;
    }
    const plant = this._getPlant();
    if (!plant) {
      this._root.innerHTML = `<div class="main"><p class="placeholder">Add FoxESS Plant and select your inverter device.</p></div>`;
      return;
    }
    const subTabs =
      this._view === "settings"
        ? this._renderTabBar(SETTINGS_NAV, this._settingsView, "settings-tab", "sub", true)
        : "";
    const pageHeader = `<header class="page-header">${this._renderTabBar(NAV, this._view, "nav", "view")}${subTabs}</header>`;

    this._root.innerHTML = `<div class="shell ${this._narrow ? "narrow" : ""}">
${pageHeader}
<main class="main">${this._renderView(plant)}</main>
</div>`;
    if (this._view === "settings" && this._settingsView === "quick") {
      this._bindTripleSoc();
    }
  }
}

customElements.define("foxess-plant-panel", FoxessPlantPanel);
