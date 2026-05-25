/**
 * FoxESS Plant panel — pure Web Components (no external deps).
 * HA panel contract: hass, narrow, panel (panel.config.plants[]).
 */

const NAV = [
  { id: "overview", label: "Overview", icon: "mdi:home-lightning-bolt" },
  { id: "device", label: "Device", icon: "mdi:solar-power-variant" },
  { id: "energy", label: "Energy", icon: "mdi:chart-line" },
  { id: "settings", label: "Settings", icon: "mdi:cog" },
];

const FLOW_PATHS = {
  "solar-home": "M 118 88 C 160 88, 175 115, 200 130",
  "grid-home": "M 382 88 C 340 88, 320 115, 295 130",
  "home-grid": "M 295 130 C 320 115, 340 88, 382 88",
  "battery-home": "M 250 228 C 250 195, 250 175, 250 155",
  "home-battery": "M 250 155 C 250 175, 250 195, 250 228",
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
  } else if (batteryW > 50) {
    batteryStatus = "Discharging";
  } else if (batteryW < -50) {
    batteryStatus = "Charging";
  }
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

const STYLES = `
:host { display: block; height: 100%; background: var(--primary-background-color, #111); color: var(--primary-text-color, #fff); --sidebar-width: 240px; }
.shell { display: flex; height: 100%; min-height: calc(100vh - 56px); }
.shell.narrow { flex-direction: column; }
.sidebar { width: var(--sidebar-width); flex-shrink: 0; border-right: 1px solid var(--divider-color, rgba(127,127,127,0.25)); padding: 16px 8px; background: var(--sidebar-background-color, var(--card-background-color)); }
.shell.narrow .sidebar { width: 100%; display: flex; overflow-x: auto; border-right: none; border-bottom: 1px solid var(--divider-color, rgba(127,127,127,0.25)); padding: 8px; }
.nav-btn { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 14px; margin-bottom: 4px; border: none; border-radius: 10px; background: transparent; color: var(--primary-text-color); font-size: 14px; cursor: pointer; text-align: left; font-family: inherit; }
.shell.narrow .nav-btn { flex: 1; justify-content: center; min-width: 72px; margin-bottom: 0; }
.nav-btn:hover { background: var(--secondary-background-color, rgba(127,127,127,0.15)); }
.nav-btn.active { background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.15); color: var(--primary-color, #03a9f4); font-weight: 600; }
.nav-btn ha-icon { --mdc-icon-size: 22px; color: inherit; }
.main { flex: 1; overflow-y: auto; padding: 20px 24px 32px; max-width: 960px; }
.shell.narrow .main { padding: 16px; max-width: none; }
.header { margin-bottom: 20px; }
.header h1 { margin: 0; font-size: 24px; font-weight: 600; }
.header p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: 14px; }
.back-btn { background: none; border: none; color: var(--primary-color); cursor: pointer; font-size: 14px; padding: 0 0 12px; font-family: inherit; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 16px; }
.stat { background: var(--card-background-color); border-radius: 12px; padding: 14px; box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12)); }
.stat label { font-size: 12px; color: var(--secondary-text-color); display: block; }
.stat strong { font-size: 20px; display: block; margin-top: 4px; }
.settings-list { display: flex; flex-direction: column; gap: 8px; }
.settings-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; border-radius: 12px; background: var(--card-background-color); border: none; width: 100%; text-align: left; color: inherit; font-size: 15px; cursor: pointer; box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12)); font-family: inherit; }
.settings-item:disabled { cursor: default; opacity: 1; }
.settings-item::after { content: "›"; opacity: 0.45; margin-left: 8px; }
.settings-item:disabled::after { content: ""; }
.placeholder { padding: 32px; text-align: center; color: var(--secondary-text-color); background: var(--card-background-color); border-radius: 12px; }
.scene-card { background: var(--card-background-color, #1c1c1c); border-radius: 16px; padding: 16px 12px 12px; box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.2)); overflow: hidden; }
.scene-title { font-size: 14px; font-weight: 600; color: var(--secondary-text-color, #888); margin: 0 0 8px 4px; text-transform: uppercase; letter-spacing: 0.04em; }
.scene-card svg { width: 100%; height: auto; display: block; max-height: 280px; }
.node-label { font-size: 11px; fill: var(--secondary-text-color, #999); font-family: var(--ha-font-family, Roboto, sans-serif); }
.node-value { font-size: 13px; font-weight: 600; fill: var(--primary-text-color, #fff); font-family: var(--ha-font-family, Roboto, sans-serif); }
.flow-path { fill: none; stroke-width: 3; stroke-linecap: round; opacity: 0.2; }
.flow-path.active { opacity: 1; stroke-dasharray: 8 10; animation: flow 1.2s linear infinite; }
.flow-path.reverse { animation-direction: reverse; }
.flow-solar.active { stroke: #f4b400; }
.flow-grid.active { stroke: #4285f4; }
.flow-export.active { stroke: #9c27b0; }
.flow-battery.active { stroke: #0f9d58; }
.flow-label { font-size: 10px; fill: var(--primary-text-color, #eee); font-family: var(--ha-font-family, Roboto, sans-serif); }
@keyframes flow { to { stroke-dashoffset: -36; } }
.house-body { fill: var(--divider-color, #333); stroke: var(--primary-color, #03a9f4); stroke-width: 2; }
.house-roof { fill: var(--primary-color, #03a9f4); opacity: 0.85; }
.soc-ring-bg { fill: none; stroke: var(--divider-color, #444); stroke-width: 6; }
.soc-ring { fill: none; stroke: #0f9d58; stroke-width: 6; stroke-linecap: round; transform: rotate(-90deg); transform-origin: 250px 248px; transition: stroke-dasharray 0.6s ease; }
.device-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.device-card { background: var(--card-background-color, #1c1c1c); border-radius: 16px; padding: 16px; box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.15)); min-height: 140px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.badge { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; background: rgba(15, 157, 88, 0.2); color: #0f9d58; margin-bottom: 12px; align-self: flex-start; }
.gauge { width: 100px; height: 100px; position: relative; }
.gauge svg { width: 100%; height: 100%; }
.gauge-value { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; color: var(--primary-text-color); }
.gauge-label { font-size: 11px; color: var(--secondary-text-color); }
.battery-header { width: 100%; display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 13px; color: var(--secondary-text-color); }
.battery-pct { font-size: 36px; font-weight: 700; color: var(--primary-text-color); line-height: 1; }
.metrics { display: flex; width: 100%; justify-content: space-around; margin-top: 12px; font-size: 12px; color: var(--secondary-text-color); }
.metrics strong { display: block; color: var(--primary-text-color); font-size: 14px; }
.nav-row { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
button.link { width: 100%; text-align: left; padding: 14px 16px; border: none; border-radius: 12px; background: var(--card-background-color); color: var(--primary-text-color); font-size: 15px; cursor: pointer; box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12)); font-family: inherit; }
button.link:hover { background: var(--secondary-background-color, #2a2a2a); }
button.link::after { content: "›"; float: right; opacity: 0.5; }
.entity-list { background: var(--card-background-color); border-radius: 12px; overflow: hidden; box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12)); }
.entity-row { display: flex; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--divider-color, rgba(127,127,127,0.2)); font-size: 14px; gap: 12px; }
.entity-row:last-child { border-bottom: none; }
.entity-name { color: var(--secondary-text-color); flex: 1; }
.entity-value { color: var(--primary-text-color); font-weight: 500; text-align: right; }
.hero { border-radius: 16px; overflow: hidden; background: linear-gradient(180deg, #1a2332 0%, var(--card-background-color, #1c1c1c) 100%); margin-bottom: 16px; }
.hero svg { width: 100%; height: auto; display: block; }
.hero-caption { padding: 12px 16px; font-size: 13px; color: var(--secondary-text-color, #aaa); line-height: 1.45; border-top: 1px solid var(--divider-color, #333); }
.prepared { opacity: 1; transition: opacity 0.4s; }
.unprepared { opacity: 0.35; transition: opacity 0.4s; }
.hero.armed .unprepared { opacity: 0.2; }
.hero.armed .prepared { opacity: 1; }
.hero:not(.armed) .prepared { opacity: 0.45; }
.lightning { animation: flash 2.5s ease-in-out infinite; }
@keyframes flash { 0%, 90%, 100% { opacity: 0.3; } 92%, 96% { opacity: 1; } }
@media (max-width: 600px) { .device-grid { grid-template-columns: 1fr; } .scene-card svg { max-height: 220px; } }
`;

class FoxessPlantPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._narrow = false;
    this._panel = undefined;
    this._view = "overview";
    this._settingsView = "main";
    this._deviceSub = "main";
    this._plantState = undefined;
    this._selectedPlantId = undefined;
    this._timer = undefined;
    const root = document.createElement("div");
    root.className = "root";
    this.shadowRoot.append(
      Object.assign(document.createElement("style"), { textContent: STYLES }),
      root
    );
    this._root = root;
    this._onClick = this._handleClick.bind(this);
  }

  connectedCallback() {
    this._root.addEventListener("click", this._onClick);
    void this._refreshPlantState();
    this._timer = window.setInterval(() => void this._refreshPlantState(), 30000);
    this._render();
  }

  disconnectedCallback() {
    this._root.removeEventListener("click", this._onClick);
    if (this._timer) window.clearInterval(this._timer);
  }

  set hass(v) {
    this._hass = v;
    this._render();
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

  _getPlant() {
    const plants = this._panel?.config?.plants ?? [];
    return plants.find((p) => p.entry_id === this._selectedPlantId) ?? plants[0];
  }

  async _refreshPlantState() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    try {
      this._plantState = await fetchPlantState(this._hass, plant.entry_id);
      this._render();
    } catch {
      /* panel works without ws state */
    }
  }

  _handleClick(e) {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;
    if (action === "nav") {
      this._view = btn.dataset.view;
      this._settingsView = "main";
      this._deviceSub = "main";
      this._render();
    } else if (action === "device-sub") {
      this._deviceSub = btn.dataset.sub;
      this._render();
    } else if (action === "device-back") {
      this._deviceSub = "main";
      this._render();
    } else if (action === "settings-storm") {
      this._settingsView = "storm";
      this._render();
    } else if (action === "settings-back") {
      this._settingsView = "main";
      this._render();
    }
  }

  _rowsFromMap(plant, pairs) {
    return pairs
      .map(([key, name]) => {
        const entity_id = plant.entity_map?.[key];
        return entity_id ? { entity_id, name } : null;
      })
      .filter(Boolean);
  }

  _renderEntityList(title, rows) {
    if (!rows.length) return `<p class="placeholder">No entities mapped.</p>`;
    const rowsHtml = rows
      .map(
        (r) =>
          `<div class="entity-row"><span class="entity-name">${esc(r.name)}</span><span class="entity-value">${esc(stateString(this._hass, r.entity_id))}${esc(entityUnit(this._hass, r.entity_id))}</span></div>`
      )
      .join("");
    return `${title ? `<h3 style="margin:0 0 12px;font-size:16px;font-weight:600">${esc(title)}</h3>` : ""}<div class="entity-list">${rowsHtml}</div>`;
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
        const active = activeIds.has(id) ? "active" : "";
        const rev = line?.reverse ? "reverse" : "";
        const labelY = id.includes("battery") ? 200 : 108;
        const label = line?.label
          ? `<text class="flow-label" x="250" y="${labelY}" text-anchor="middle">${esc(line.label)}</text>`
          : "";
        return `<path class="flow-path ${cls} ${active} ${rev}" d="${d}"></path>${label}`;
      })
      .join("");

    return `<div class="scene-card"><div class="scene-title">Live energy flow</div>
<svg viewBox="0 0 500 290" role="img" aria-label="Energy flow diagram">
${pathsHtml}
<g transform="translate(70, 48)">
<rect x="0" y="18" width="48" height="32" rx="4" fill="#f4b400" opacity="0.25" stroke="#f4b400" stroke-width="1.5"/>
<line x1="8" y1="26" x2="40" y2="26" stroke="#f4b400" stroke-width="1"/><line x1="8" y1="34" x2="40" y2="34" stroke="#f4b400" stroke-width="1"/>
<line x1="8" y1="42" x2="40" y2="42" stroke="#f4b400" stroke-width="1"/><line x1="24" y1="18" x2="24" y2="50" stroke="#f4b400" stroke-width="1"/>
<text class="node-label" x="24" y="12" text-anchor="middle">Solar</text>
<text class="node-value" x="24" y="68" text-anchor="middle">${esc(formatKw(flows.pvW, 2))}</text>
</g>
<g transform="translate(382, 48)">
<path d="M0 50 L0 20 L12 20 L12 8 L24 8 L24 20 L36 20 L36 50 Z" fill="#4285f4" opacity="0.3" stroke="#4285f4"/>
<text class="node-label" x="18" y="0" text-anchor="middle">Grid</text>
<text class="node-value" x="18" y="68" text-anchor="middle">${esc(gridVal)}</text>
</g>
<g transform="translate(200, 108)">
<polygon class="house-roof" points="50,0 100,35 0,35"/>
<rect class="house-body" x="8" y="35" width="84" height="55" rx="4"/>
<rect x="38" y="55" width="24" height="35" rx="2" fill="var(--card-background-color,#222)"/>
<text class="node-label" x="50" y="-8" text-anchor="middle">Home</text>
<text class="node-value" x="50" y="108" text-anchor="middle">${esc(formatKw(flows.loadW, 2))}</text>
</g>
<g transform="translate(222, 220)">
<circle class="soc-ring-bg" cx="28" cy="28" r="28"/>
<circle class="soc-ring" cx="28" cy="28" r="28" stroke-dasharray="${circumference}" stroke-dashoffset="${socOffset}"/>
<rect x="18" y="14" width="20" height="28" rx="3" fill="var(--card-background-color,#222)" stroke="#0f9d58" stroke-width="2"/>
<rect x="24" y="10" width="8" height="4" rx="1" fill="#0f9d58"/>
<text class="node-value" x="28" y="34" text-anchor="middle" font-size="11">${esc(formatPercent(soc))}</text>
<text class="node-label" x="28" y="-4" text-anchor="middle">Battery</text>
<text class="node-value" x="28" y="72" text-anchor="middle" font-size="11">${esc(flows.batteryStatus)}</text>
</g>
</svg></div>`;
  }

  _renderStormHero(armed, charging) {
    const chargeIcon = charging
      ? `<text x="19" y="98" text-anchor="middle" fill="#a5d6a7" font-size="9">⚡</text>`
      : `<rect x="14" y="88" width="10" height="14" fill="#66bb6a"/>`;
    return `<div class="hero ${armed ? "armed" : ""}">
<svg viewBox="0 0 400 140" aria-hidden="true">
<g class="unprepared" transform="translate(210, 20)">
<rect x="30" y="40" width="70" height="50" rx="4" fill="#333"/>
<polygon points="65,20 110,45 20,45" fill="#444"/>
<rect x="52" y="55" width="26" height="35" fill="#111"/>
<rect x="95" y="70" width="28" height="40" rx="4" fill="#333" stroke="#c62828" stroke-width="2"/>
<text x="109" y="95" text-anchor="middle" fill="#c62828" font-size="10">!</text>
</g>
<g class="prepared" transform="translate(20, 20)">
<rect x="30" y="40" width="70" height="50" rx="4" fill="#455a64"/>
<polygon points="65,20 110,45 20,45" fill="#546e7a"/>
<rect x="45" y="50" width="12" height="10" fill="#ffeb3b" opacity="0.9"/>
<rect x="62" y="50" width="12" height="10" fill="#ffeb3b" opacity="0.9"/>
<rect x="52" y="55" width="26" height="35" fill="#263238"/>
<rect x="5" y="70" width="28" height="40" rx="4" fill="#2e7d32" stroke="#66bb6a" stroke-width="2"/>
<rect x="11" y="78" width="16" height="26" rx="2" fill="#1b5e20"/>${chargeIcon}
</g>
<g class="lightning" transform="translate(155, 8)">
<ellipse cx="45" cy="28" rx="50" ry="22" fill="#37474f"/>
<path d="M 55 48 L 48 62 L 54 62 L 46 78 L 58 58 L 52 58 Z" fill="#ffeb3b"/>
</g>
</svg>
<div class="hero-caption">When StormSafe is enabled, the system pre-charges before extreme weather so your home stays powered during an outage — like the prepared house on the left.</div>
</div>`;
  }

  _stat(label, value, suffix = "") {
    const has = value != null && value !== "—";
    return `<div class="stat"><label>${esc(label)}</label><strong>${has ? esc(value) + esc(suffix) : "—"}</strong></div>`;
  }

  _renderOverview(plant) {
    const a = this._plantState?.analytics ?? {};
    const mode = this._plantState?.mode ?? "—";
    return `<header class="header"><h1>${esc(plant.title)}</h1><p>Mode: ${esc(mode)} · Inverter ${esc(plant.inverter)}</p></header>
${this._renderEnergyScene(plant)}
<div class="stats-row">
${this._stat("Self-consumption today", a.self_consumption_percent_today, a.self_consumption_percent_today != null ? "%" : "")}
${this._stat("Self-sufficiency today", a.self_sufficiency_percent_today, a.self_sufficiency_percent_today != null ? "%" : "")}
${this._stat("PV today", a.pv_production_kwh_today, a.pv_production_kwh_today != null ? " kWh" : "")}
</div>`;
  }

  _renderDeviceOverview(plant) {
    const flows = readEnergyFlows(this._hass, plant);
    const mode = this._plantState?.mode ?? "—";
    const control = this._plantState?.control_active ? "on" : "off";
    const pvKw = flows.pvW / 1000;
    const gaugePct = Math.min(100, (pvKw / 5) * 100);
    const circumference = 2 * Math.PI * 40;
    const offset = circumference * (1 - gaugePct / 100);
    const temp = stateString(this._hass, plant.entity_map?.bms_temp_low);
    const tempStr = temp !== "—" ? `${temp}°C` : "—";
    return `<span class="badge">${esc(mode)} · control ${control}</span>
<div class="device-grid">
<div class="device-card"><div class="gauge"><svg viewBox="0 0 100 100">
<circle cx="50" cy="50" r="40" fill="none" stroke="var(--divider-color,#444)" stroke-width="8"/>
<circle cx="50" cy="50" r="40" fill="none" stroke="#03a9f4" stroke-width="8" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" transform="rotate(-90 50 50)" stroke-linecap="round"/>
</svg><div class="gauge-value"><span>${pvKw.toFixed(2)}</span><span class="gauge-label">PV Power</span></div></div></div>
<div class="device-card"><div class="battery-header">🔋 ${esc(flows.batteryStatus)}</div>
<div class="battery-pct">${esc(formatPercent(flows.batterySoc))}</div>
<div class="metrics"><div><span>Power</span><strong>${esc(formatKw(Math.abs(flows.batteryW), 2))}</strong></div>
<div><span>Temp.</span><strong>${esc(tempStr)}</strong></div></div></div></div>
<div class="nav-row">
<button type="button" class="link" data-action="device-sub" data-sub="parameters">Detailed Parameters</button>
<button type="button" class="link" data-action="device-sub" data-sub="battery">Battery Information</button>
</div>`;
  }

  _renderDevice(plant) {
    if (this._deviceSub === "parameters") {
      const rows = this._rowsFromMap(plant, [
        ["pv_power", "PV power"],
        ["load_power", "Load power"],
        ["grid_import", "Grid import"],
        ["grid_export", "Grid export"],
        ["battery_power", "Battery power"],
        ["battery_soc", "Battery SOC"],
      ]);
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button>
<header class="header"><h1>Detailed Parameters</h1></header>
${this._renderEntityList("Live values", rows)}`;
    }
    if (this._deviceSub === "battery") {
      const rows = this._rowsFromMap(plant, [
        ["battery_soc", "SOC"],
        ["battery_power", "Battery power"],
        ["battery_status", "Status"],
        ["bms_temp_low", "Min. battery temperature"],
      ]);
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button>
<header class="header"><h1>Battery</h1></header>
${this._renderEntityList("", rows)}`;
    }
    return `<header class="header"><h1>Device</h1><p>${esc(plant.title)}</p></header>${this._renderDeviceOverview(plant)}`;
  }

  _renderEnergy() {
    const a = this._plantState?.analytics ?? {};
    const hasAnalytics = Object.keys(a).length > 0;
    const stats = hasAnalytics
      ? `<div class="stats-row">
${this._stat("Load consumption", a.load_consumption_kwh_today ?? "—", " kWh")}
${this._stat("From grid", a.load_from_grid_kwh_today ?? "—", " kWh")}
${this._stat("PV to grid", a.pv_to_grid_kwh_today ?? "—", " kWh")}
<div class="stat"><label>Self-consumption</label><strong>${a.self_consumption_percent_today != null ? esc(formatPercent(a.self_consumption_percent_today)) : "—"}</strong></div>
</div>`
      : `<div class="placeholder">Energy analytics will appear here once plant state is available from the integration.</div>`;
    return `<header class="header"><h1>Energy</h1><p>Daily analytics from your plant</p></header>
${stats}
<p class="placeholder" style="margin-top:16px">Analysis graph (Day / Month / Year) — coming in next update.</p>`;
  }

  _renderSettings(plant) {
    if (this._settingsView === "storm") {
      const triggers = this._plantState?.active_storm_triggers;
      const armed = Boolean(triggers?.length);
      return `<button type="button" class="back-btn" data-action="settings-back">← Settings</button>
<header class="header"><h1>StormSafe Charging</h1></header>
${this._renderStormHero(armed, armed)}
<p class="placeholder">Configure storm triggers in Integration → Configure → Storm prep, or call <code>foxess_plant.arm_storm_prep</code> from automations.</p>`;
    }
    const map = plant.entity_map || {};
    return `<header class="header"><h1>Settings</h1></header>
<div class="settings-list">
<button type="button" class="settings-item" disabled><span>System Max SOC</span><span>${esc(stateString(this._hass, map.max_soc))}</span></button>
<button type="button" class="settings-item" disabled><span>System Min SOC</span><span>${esc(stateString(this._hass, map.min_soc))}</span></button>
<button type="button" class="settings-item" disabled><span>Off-grid Min SOC</span><span>${esc(stateString(this._hass, map.min_soc_on_grid))}</span></button>
<button type="button" class="settings-item" disabled><span>Work mode</span><span>${esc(stateString(this._hass, map.work_mode))}</span></button>
<button type="button" class="settings-item" data-action="settings-storm"><span>StormSafe Charging</span></button>
</div>
<p class="placeholder" style="margin-top:16px;font-size:13px">Interactive SOC sliders and charge period editor — next update.</p>`;
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
    const plant = this._getPlant();
    if (!plant) {
      this._root.innerHTML = `<div class="main"><div class="placeholder">Add FoxESS Plant integration and select your inverter to use this panel.</div></div>`;
      return;
    }

    const navHtml = NAV.map(
      (item) =>
        `<button type="button" class="nav-btn ${this._view === item.id ? "active" : ""}" data-action="nav" data-view="${item.id}">
<ha-icon icon="${item.icon}"></ha-icon>${this._narrow ? "" : esc(item.label)}
</button>`
    ).join("");

    this._root.innerHTML = `<div class="shell ${this._narrow ? "narrow" : ""}">
<nav class="sidebar">${navHtml}</nav>
<main class="main">${this._renderView(plant)}</main>
</div>`;
  }
}

customElements.define("foxess-plant-panel", FoxessPlantPanel);
