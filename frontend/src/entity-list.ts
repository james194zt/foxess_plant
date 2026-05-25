import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { HomeAssistant } from "./types";
import { stateString } from "./types";

export interface EntityRow {
  entity_id: string;
  name: string;
}

@customElement("fox-entity-list")
export class FoxEntityList extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;
  @property({ type: Array }) rows: EntityRow[] = [];
  @property({ type: String }) title = "";

  static styles = css`
    :host { display: block; }
    h3 {
      margin: 0 0 12px;
      font-size: 16px;
      font-weight: 600;
    }
    .list {
      background: var(--card-background-color);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.12));
    }
    .row {
      display: flex;
      justify-content: space-between;
      padding: 14px 16px;
      border-bottom: 1px solid var(--divider-color, rgba(127,127,127,0.2));
      font-size: 14px;
      gap: 12px;
    }
    .row:last-child { border-bottom: none; }
    .name { color: var(--secondary-text-color); flex: 1; }
    .value { color: var(--primary-text-color); font-weight: 500; text-align: right; }
  `;

  render() {
    if (!this.hass) return html``;
    return html`
      ${this.title ? html`<h3>${this.title}</h3>` : ""}
      <div class="list">
        ${this.rows.map(
          (row) => html`
            <div class="row">
              <span class="name">${row.name}</span>
              <span class="value">${stateString(this.hass!, row.entity_id)}${this._unit(row.entity_id)}</span>
            </div>
          `
        )}
      </div>
    `;
  }

  private _unit(entityId: string): string {
    const attrs = this.hass?.states[entityId]?.attributes ?? {};
    const u = attrs.unit_of_measurement as string | undefined;
    return u ? ` ${u}` : "";
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "fox-entity-list": FoxEntityList;
  }
}
