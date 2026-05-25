import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import "./energy-scene";
import "./storm-hero";
import "./device-overview";
import "./entity-list";
import type {
  HomeAssistant,
  PanelInfo,
  PanelView,
  PlantConfig,
  SettingsView,
} from "./types";
import { fetchPlantState, formatPercent, stateString } from "./types";

const NAV: { id: PanelView; label: string; icon: string }[] = [
  { id: "overview", label: "Overview", icon: "mdi:home-lightning-bolt" },
  { id: "device", label: "Device", icon: "mdi:solar-power-variant" },
  { id: "energy", label: "Energy", icon: "mdi:chart-line" },
  { id: "settings", label: "Settings", icon: "mdi:cog" },
];

@customElement("foxess-plant-panel")
export class FoxessPlantPanel extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ type: Boolean }) public narrow = false;
  @property({ attribute: false }) public panel!: PanelInfo;

  @state() private _view: PanelView = "overview";
  @state() private _settingsView: SettingsView = "main";
  @state() private _deviceSub: "main" | "parameters" | "battery" = "main";
  @state() private _plantState?: Record<string, unknown>;
  @state() private _selectedPlantId?: string;

  static styles = css`
    :host {
      display: block;
      height: 100%;
      background: var(--primary-background-color, #111);
      color: var(--primary-text-color, #fff);
      --sidebar-width: 240px;
    }
    .shell {
      display: flex;
      height: 100%;
      min-height: calc(100vh - 56px);
    }
    .sidebar {
      width: var(--sidebar-width);
      flex-shrink: 0;
      border-right: 1px solid var(--divider-color, rgba(127,127,127,0.25));
      padding: 16px 8px;
      background: var(--sidebar-background-color, var(--card-background-color));
    }
    .sidebar.narrow-hidden { display: none; }
    .nav-btn {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
      padding: 12px 14px;
      margin-bottom: 4px;
      border: none;
      border-radius: 10px;
      background: transparent;
      color: var(--primary-text-color);
      font-size: 14px;
      cursor: pointer;
      text-align: left;
    }
    .nav-btn:hover { background: var(--secondary-background-color, rgba(127,127,127,0.15)); }
    .nav-btn.active {
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.15);
      color: var(--primary-color, #03a9f4);
      font-weight: 600;
    }
    .nav-btn ha-icon { --mdc-icon-size: 22px; color: inherit; }
    .main {
      flex: 1;
      overflow-y: auto;
      padding: 20px 24px 32px;
      max-width: 960px;
    }
    .header {
      margin-bottom: 20px;
    }
    .header h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
    }
    .header p {
      margin: 4px 0 0;
      color: var(--secondary-text-color);
      font-size: 14px;
    }
  .back-btn {
      background: none;
      border: none;
      color: var(--primary-color);
      cursor: pointer;
      font-size: 14px;
      padding: 0 0 12px;
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }
    .stat {
      background: var(--card-background-color);
      border-radius: 12px;
      padding: 14px;
      box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12));
    }
    .stat label { font-size: 12px; color: var(--secondary-text-color); display: block; }
    .stat strong { font-size: 20px; display: block; margin-top: 4px; }
    .settings-list { display: flex; flex-direction: column; gap: 8px; }
    .settings-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      border-radius: 12px;
      background: var(--card-background-color);
      border: none;
      width: 100%;
      text-align: left;
      color: inherit;
      font-size: 15px;
      cursor: pointer;
      box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12));
    }
    .settings-item::after { content: "›"; opacity: 0.45; margin-left: 8px; }
    .placeholder {
      padding: 32px;
      text-align: center;
      color: var(--secondary-text-color);
      background: var(--card-background-color);
      border-radius: 12px;
    }
    @media (max-width: 768px) {
      .shell { flex-direction: column; }
      .sidebar {
        width: 100%;
        display: flex;
        overflow-x: auto;
        border-right: none;
        border-bottom: 1px solid var(--divider-color, rgba(127,127,127,0.25));
        padding: 8px;
      }
      .nav-btn { flex: 1; justify-content: center; min-width: 100px; }
      .main { padding: 16px; }
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    void this._refreshPlantState();
    this._timer = window.setInterval(() => void this._refreshPlantState(), 30000);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._timer) window.clearInterval(this._timer);
  }

  private _timer?: number;

  updated(changed: Map<string, unknown>): void {
    if (changed.has("panel") || changed.has("hass")) {
      const plants = this.panel?.config?.plants ?? [];
      if (!this._selectedPlantId && plants.length) {
        this._selectedPlantId = plants[0].entry_id;
      }
    }
  }

  private get _plant(): PlantConfig | undefined {
    const plants = this.panel?.config?.plants ?? [];
    return plants.find((p) => p.entry_id === this._selectedPlantId) ?? plants[0];
  }

  private async _refreshPlantState(): Promise<void> {
    const plant = this._plant;
    if (!plant || !this.hass) return;
    try {
      this._plantState = await fetchPlantState(this.hass, plant.entry_id);
    } catch {
      /* panel works without ws state */
    }
  }

  render() {
    const plant = this._plant;
    if (!plant) {
      return html`
        <div class="main">
          <div class="placeholder">
            Add FoxESS Plant integration and select your inverter to use this panel.
          </div>
        </div>
      `;
    }

    return html`
      <div class="shell">
        <nav class="sidebar ${this.narrow ? "narrow-hidden" : ""}">
          ${NAV.map(
            (item) => html`
              <button
                class="nav-btn ${this._view === item.id ? "active" : ""}"
                @click=${() => {
                  this._view = item.id;
                  this._settingsView = "main";
                  this._deviceSub = "main";
                }}
              >
                <ha-icon icon="${item.icon}"></ha-icon>
                ${this.narrow ? nothing : item.label}
              </button>
            `
          )}
        </nav>
        <main class="main">${this._renderView(plant)}</main>
      </div>
    `;
  }

  private _renderView(plant: PlantConfig) {
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
        return nothing;
    }
  }

  private _renderOverview(plant: PlantConfig) {
    const analytics = (this._plantState?.analytics ?? {}) as Record<string, number>;
    return html`
      <header class="header">
        <h1>${plant.title}</h1>
        <p>Mode: ${(this._plantState?.mode as string) ?? "—"} · Inverter ${plant.inverter}</p>
      </header>
      <fox-energy-scene .hass=${this.hass} .plant=${plant}></fox-energy-scene>
      <div class="stats-row">
        <div class="stat">
          <label>Self-consumption today</label>
          <strong>${analytics.self_consumption_percent_today ?? "—"}${analytics.self_consumption_percent_today != null ? "%" : ""}</strong>
        </div>
        <div class="stat">
          <label>Self-sufficiency today</label>
          <strong>${analytics.self_sufficiency_percent_today ?? "—"}${analytics.self_sufficiency_percent_today != null ? "%" : ""}</strong>
        </div>
        <div class="stat">
          <label>PV today</label>
          <strong>${analytics.pv_production_kwh_today ?? "—"}${analytics.pv_production_kwh_today != null ? " kWh" : ""}</strong>
        </div>
      </div>
    `;
  }

  private _renderDevice(plant: PlantConfig) {
    if (this._deviceSub === "parameters") {
      return html`
        <button class="back-btn" @click=${() => (this._deviceSub = "main")}>← Device</button>
        <header class="header"><h1>Detailed Parameters</h1></header>
        <fox-entity-list
          .hass=${this.hass}
          title="Live values"
          .rows=${this._rowsFromMap(plant, [
            ["pv_power", "PV power"],
            ["load_power", "Load power"],
            ["grid_import", "Grid import"],
            ["grid_export", "Grid export"],
            ["battery_power", "Battery power"],
            ["battery_soc", "Battery SOC"],
          ])}
        ></fox-entity-list>
      `;
    }
    if (this._deviceSub === "battery") {
      return html`
        <button class="back-btn" @click=${() => (this._deviceSub = "main")}>← Device</button>
        <header class="header"><h1>Battery</h1></header>
        <fox-entity-list
          .hass=${this.hass}
          .rows=${this._rowsFromMap(plant, [
            ["battery_soc", "SOC"],
            ["battery_power", "Battery power"],
            ["battery_status", "Status"],
            ["bms_temp_low", "Min. battery temperature"],
          ])}
        ></fox-entity-list>
      `;
    }
    return html`
      <header class="header"><h1>Device</h1><p>${plant.title}</p></header>
      <fox-device-overview
        .hass=${this.hass}
        .plant=${plant}
        .plantState=${this._plantState}
        @navigate=${(e: CustomEvent) => {
          this._deviceSub = e.detail.sub;
        }}
      ></fox-device-overview>
    `;
  }

  private _renderEnergy(plant: PlantConfig) {
    const analytics = (this._plantState?.analytics ?? {}) as Record<string, number>;
    return html`
      <header class="header">
        <h1>Energy</h1>
        <p>Daily analytics from your plant</p>
      </header>
      <div class="stats-row">
        <div class="stat"><label>Load consumption</label><strong>${analytics.load_consumption_kwh_today ?? "—"} kWh</strong></div>
        <div class="stat"><label>From grid</label><strong>${analytics.load_from_grid_kwh_today ?? "—"} kWh</strong></div>
        <div class="stat"><label>PV to grid</label><strong>${analytics.pv_to_grid_kwh_today ?? "—"} kWh</strong></div>
        <div class="stat"><label>Self-consumption</label><strong>${formatPercent(analytics.self_consumption_percent_today ?? 0)}</strong></div>
      </div>
      <p class="placeholder" style="margin-top:16px">Analysis graph (Day / Month / Year) — coming in next update.</p>
    `;
  }

  private _renderSettings(plant: PlantConfig) {
    if (this._settingsView === "storm") {
      const triggers = this._plantState?.active_storm_triggers as string[] | undefined;
      const armed = Boolean(triggers?.length);
      return html`
        <button class="back-btn" @click=${() => (this._settingsView = "main")}>← Settings</button>
        <header class="header"><h1>StormSafe Charging</h1></header>
        <fox-storm-hero .armed=${armed} .charging=${armed}></fox-storm-hero>
        <p class="placeholder">
          Configure storm triggers in Integration → Configure → Storm prep, or call
          <code>foxess_plant.arm_storm_prep</code> from automations.
        </p>
      `;
    }
    const map = plant.entity_map;
    return html`
      <header class="header"><h1>Settings</h1></header>
      <div class="settings-list">
        <button class="settings-item" disabled>
          <span>System Max SOC</span>
          <span>${stateString(this.hass, map.max_soc)}</span>
        </button>
        <button class="settings-item" disabled>
          <span>System Min SOC</span>
          <span>${stateString(this.hass, map.min_soc)}</span>
        </button>
        <button class="settings-item" disabled>
          <span>Off-grid Min SOC</span>
          <span>${stateString(this.hass, map.min_soc_on_grid)}</span>
        </button>
        <button class="settings-item" disabled>
          <span>Work mode</span>
          <span>${stateString(this.hass, map.work_mode)}</span>
        </button>
        <button class="settings-item" @click=${() => (this._settingsView = "storm")}>
          <span>StormSafe Charging</span>
        </button>
      </div>
      <p class="placeholder" style="margin-top:16px;font-size:13px">
        Interactive SOC sliders and charge period editor — next update.
      </p>
    `;
  }

  private _rowsFromMap(
    plant: PlantConfig,
    pairs: [string, string][]
  ): { entity_id: string; name: string }[] {
    return pairs
      .map(([key, name]) => {
        const entity_id = plant.entity_map[key];
        return entity_id ? { entity_id, name } : null;
      })
      .filter(Boolean) as { entity_id: string; name: string }[];
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "foxess-plant-panel": FoxessPlantPanel;
  }
}
