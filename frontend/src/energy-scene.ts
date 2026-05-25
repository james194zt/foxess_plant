import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { HomeAssistant, PlantConfig } from "./types";
import { formatKw, formatPercent } from "./types";
import { computeFlowLines, readEnergyFlows } from "./power";

const FLOW_PATHS: Record<string, string> = {
  "solar-home": "M 118 88 C 160 88, 175 115, 200 130",
  "grid-home": "M 382 88 C 340 88, 320 115, 295 130",
  "home-grid": "M 295 130 C 320 115, 340 88, 382 88",
  "battery-home": "M 250 228 C 250 195, 250 175, 250 155",
  "home-battery": "M 250 155 C 250 175, 250 195, 250 228",
};

@customElement("fox-energy-scene")
export class FoxEnergyScene extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;
  @property({ attribute: false }) plant?: PlantConfig;

  static styles = css`
    :host {
      display: block;
    }
    .scene-card {
      background: var(--card-background-color, #1c1c1c);
      border-radius: 16px;
      padding: 16px 12px 12px;
      box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0, 0, 0, 0.2));
      overflow: hidden;
    }
    .scene-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--secondary-text-color, #888);
      margin: 0 0 8px 4px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    svg {
      width: 100%;
      height: auto;
      display: block;
      max-height: 280px;
    }
    .node-label {
      font-size: 11px;
      fill: var(--secondary-text-color, #999);
      font-family: var(--ha-font-family, Roboto, sans-serif);
    }
    .node-value {
      font-size: 13px;
      font-weight: 600;
      fill: var(--primary-text-color, #fff);
      font-family: var(--ha-font-family, Roboto, sans-serif);
    }
    .flow-path {
      fill: none;
      stroke-width: 3;
      stroke-linecap: round;
      opacity: 0.2;
    }
    .flow-path.active {
      opacity: 1;
      stroke-dasharray: 8 10;
      animation: flow 1.2s linear infinite;
    }
    .flow-path.reverse {
      animation-direction: reverse;
    }
    .flow-solar.active { stroke: #f4b400; }
    .flow-grid.active { stroke: #4285f4; }
    .flow-export.active { stroke: #9c27b0; }
    .flow-battery.active { stroke: #0f9d58; }
    .flow-label {
      font-size: 10px;
      fill: var(--primary-text-color, #eee);
      font-family: var(--ha-font-family, Roboto, sans-serif);
    }
    @keyframes flow {
      to { stroke-dashoffset: -36; }
    }
    .house-body { fill: var(--divider-color, #333); stroke: var(--primary-color, #03a9f4); stroke-width: 2; }
    .house-roof { fill: var(--primary-color, #03a9f4); opacity: 0.85; }
    .soc-ring-bg { fill: none; stroke: var(--divider-color, #444); stroke-width: 6; }
    .soc-ring { fill: none; stroke: #0f9d58; stroke-width: 6; stroke-linecap: round; transform: rotate(-90deg); transform-origin: 250px 248px; transition: stroke-dasharray 0.6s ease; }
    @media (max-width: 600px) {
      svg { max-height: 220px; }
    }
  `;

  render() {
    if (!this.hass || !this.plant) {
      return html`<div class="scene-card">No plant configured</div>`;
    }
    const flows = readEnergyFlows(this.hass, this.plant);
    const lines = computeFlowLines(flows);
    const activeIds = new Set(lines.map((l) => l.id));
    const soc = Math.min(100, Math.max(0, flows.batterySoc));
    const circumference = 2 * Math.PI * 28;
    const socOffset = circumference * (1 - soc / 100);

    return html`
      <div class="scene-card">
        <div class="scene-title">Live energy flow</div>
        <svg viewBox="0 0 500 290" role="img" aria-label="Energy flow diagram">
          ${Object.entries(FLOW_PATHS).map(([id, d]) => {
            const line = lines.find((l) => l.id === id);
            const cls = id.includes("solar")
              ? "flow-solar"
              : id.includes("grid") && !id.includes("home-grid")
                ? "flow-grid"
                : id === "home-grid"
                  ? "flow-export"
                  : "flow-battery";
            return html`
              <path
                class="flow-path ${cls} ${activeIds.has(id) ? "active" : ""} ${line?.reverse ? "reverse" : ""}"
                d="${d}"
              ></path>
              ${line?.label
                ? html`<text class="flow-label" x="250" y="${id.includes('battery') ? 200 : 108}" text-anchor="middle">${line.label}</text>`
                : ""}
            `;
          })}

          <!-- Solar -->
          <g transform="translate(70, 48)">
            <rect x="0" y="18" width="48" height="32" rx="4" fill="#f4b400" opacity="0.25" stroke="#f4b400" stroke-width="1.5"/>
            <line x1="8" y1="26" x2="40" y2="26" stroke="#f4b400" stroke-width="1"/>
            <line x1="8" y1="34" x2="40" y2="34" stroke="#f4b400" stroke-width="1"/>
            <line x1="8" y1="42" x2="40" y2="42" stroke="#f4b400" stroke-width="1"/>
            <line x1="24" y1="18" x2="24" y2="50" stroke="#f4b400" stroke-width="1"/>
            <text class="node-label" x="24" y="12" text-anchor="middle">Solar</text>
            <text class="node-value" x="24" y="68" text-anchor="middle">${formatKw(flows.pvW, 2)}</text>
          </g>

          <!-- Grid -->
          <g transform="translate(382, 48)">
            <path d="M0 50 L0 20 L12 20 L12 8 L24 8 L24 20 L36 20 L36 50 Z" fill="#4285f4" opacity="0.3" stroke="#4285f4"/>
            <text class="node-label" x="18" y="0" text-anchor="middle">Grid</text>
            <text class="node-value" x="18" y="68" text-anchor="middle">${flows.gridExportW > flows.gridImportW ? formatKw(flows.gridExportW, 2) : formatKw(flows.gridImportW, 2)}</text>
          </g>

          <!-- House / inverter -->
          <g transform="translate(200, 108)">
            <polygon class="house-roof" points="50,0 100,35 0,35"/>
            <rect class="house-body" x="8" y="35" width="84" height="55" rx="4"/>
            <rect x="38" y="55" width="24" height="35" rx="2" fill="var(--card-background-color,#222)"/>
            <text class="node-label" x="50" y="-8" text-anchor="middle">Home</text>
            <text class="node-value" x="50" y="108" text-anchor="middle">${formatKw(flows.loadW, 2)}</text>
          </g>

          <!-- Battery -->
          <g transform="translate(222, 220)">
            <circle class="soc-ring-bg" cx="28" cy="28" r="28"/>
            <circle
              class="soc-ring"
              cx="28"
              cy="28"
              r="28"
              stroke-dasharray="${circumference}"
              stroke-dashoffset="${socOffset}"
            />
            <rect x="18" y="14" width="20" height="28" rx="3" fill="var(--card-background-color,#222)" stroke="#0f9d58" stroke-width="2"/>
            <rect x="24" y="10" width="8" height="4" rx="1" fill="#0f9d58"/>
            <text class="node-value" x="28" y="34" text-anchor="middle" font-size="11">${formatPercent(soc)}</text>
            <text class="node-label" x="28" y="-4" text-anchor="middle">Battery</text>
            <text class="node-value" x="28" y="72" text-anchor="middle" font-size="11">${flows.batteryStatus}</text>
          </g>
        </svg>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "fox-energy-scene": FoxEnergyScene;
  }
}
