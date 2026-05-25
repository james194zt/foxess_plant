import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { HomeAssistant, PlantConfig } from "./types";
import { formatKw, formatPercent, stateNumber, stateString } from "./types";
import { readEnergyFlows } from "./power";

@customElement("fox-device-overview")
export class FoxDeviceOverview extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;
  @property({ attribute: false }) plant?: PlantConfig;
  @property({ attribute: false }) plantState?: Record<string, unknown>;

  static styles = css`
    :host { display: block; }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .card {
      background: var(--card-background-color, #1c1c1c);
      border-radius: 16px;
      padding: 16px;
      box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.15));
      min-height: 140px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      background: rgba(15, 157, 88, 0.2);
      color: #0f9d58;
      margin-bottom: 12px;
      align-self: flex-start;
    }
    .gauge {
      width: 100px;
      height: 100px;
      position: relative;
    }
    .gauge svg { width: 100%; height: 100%; }
    .gauge-value {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 18px;
      color: var(--primary-text-color);
    }
    .gauge-label {
      font-size: 11px;
      color: var(--secondary-text-color);
    }
    .battery-header {
      width: 100%;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    .battery-pct {
      font-size: 36px;
      font-weight: 700;
      color: var(--primary-text-color);
      line-height: 1;
    }
    .metrics {
      display: flex;
      width: 100%;
      justify-content: space-around;
      margin-top: 12px;
      font-size: 12px;
      color: var(--secondary-text-color);
    }
    .metrics strong {
      display: block;
      color: var(--primary-text-color);
      font-size: 14px;
    }
    .nav-row {
      margin-top: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    button.link {
      width: 100%;
      text-align: left;
      padding: 14px 16px;
      border: none;
      border-radius: 12px;
      background: var(--card-background-color);
      color: var(--primary-text-color);
      font-size: 15px;
      cursor: pointer;
      box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12));
    }
    button.link:hover { background: var(--secondary-background-color, #2a2a2a); }
    button.link::after { content: "›"; float: right; opacity: 0.5; }
  `;

  render() {
    if (!this.hass || !this.plant) return html``;
    const flows = readEnergyFlows(this.hass, this.plant);
    const mode = (this.plantState?.mode as string) ?? "—";
    const pvKw = flows.pvW / 1000;
    const gaugePct = Math.min(100, (pvKw / 5) * 100);
    const circumference = 2 * Math.PI * 40;
    const offset = circumference * (1 - gaugePct / 100);
    const temp = stateString(this.hass, this.plant.entity_map.bms_temp_low);

    return html`
      <span class="badge">${mode} · control ${this.plantState?.control_active ? "on" : "off"}</span>
      <div class="grid">
        <div class="card">
          <div class="gauge">
            <svg viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" fill="none" stroke="var(--divider-color,#444)" stroke-width="8"/>
              <circle cx="50" cy="50" r="40" fill="none" stroke="#03a9f4" stroke-width="8"
                stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
                transform="rotate(-90 50 50)" stroke-linecap="round"/>
            </svg>
            <div class="gauge-value">
              <span>${(pvKw).toFixed(2)}</span>
              <span class="gauge-label">PV Power</span>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="battery-header">🔋 ${flows.batteryStatus}</div>
          <div class="battery-pct">${formatPercent(flows.batterySoc)}</div>
          <div class="metrics">
            <div><span>Power</span><strong>${formatKw(Math.abs(flows.batteryW), 2)}</strong></div>
            <div><span>Temp.</span><strong>${temp !== "—" ? `${temp}°C` : "—"}</strong></div>
          </div>
        </div>
      </div>
      <div class="nav-row">
        <button class="link" @click=${() => this.dispatchEvent(new CustomEvent("navigate", { detail: { sub: "parameters" }, bubbles: true }))}>
          Detailed Parameters
        </button>
        <button class="link" @click=${() => this.dispatchEvent(new CustomEvent("navigate", { detail: { sub: "battery" }, bubbles: true }))}>
          Battery Information
        </button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "fox-device-overview": FoxDeviceOverview;
  }
}
