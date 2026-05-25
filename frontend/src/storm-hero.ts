import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("fox-storm-hero")
export class FoxStormHero extends LitElement {
  @property({ type: Boolean }) armed = false;
  @property({ type: Boolean }) charging = false;

  static styles = css`
    :host { display: block; }
    .hero {
      border-radius: 16px;
      overflow: hidden;
      background: linear-gradient(180deg, #1a2332 0%, var(--card-background-color, #1c1c1c) 100%);
      margin-bottom: 16px;
    }
    svg { width: 100%; height: auto; display: block; }
    .caption {
      padding: 12px 16px;
      font-size: 13px;
      color: var(--secondary-text-color, #aaa);
      line-height: 1.45;
      border-top: 1px solid var(--divider-color, #333);
    }
    .prepared { opacity: 1; transition: opacity 0.4s; }
    .unprepared { opacity: 0.35; transition: opacity 0.4s; }
    .hero.armed .unprepared { opacity: 0.2; }
    .hero.armed .prepared { opacity: 1; }
    .hero:not(.armed) .prepared { opacity: 0.45; }
    .lightning { animation: flash 2.5s ease-in-out infinite; }
    @keyframes flash {
      0%, 90%, 100% { opacity: 0.3; }
      92%, 96% { opacity: 1; }
    }
  `;

  render() {
    return html`
      <div class="hero ${this.armed ? "armed" : ""}">
        <svg viewBox="0 0 400 140" aria-hidden="true">
          <!-- Unprepared (right) -->
          <g class="unprepared" transform="translate(210, 20)">
            <rect x="30" y="40" width="70" height="50" rx="4" fill="#333"/>
            <polygon points="65,20 110,45 20,45" fill="#444"/>
            <rect x="52" y="55" width="26" height="35" fill="#111"/>
            <rect x="95" y="70" width="28" height="40" rx="4" fill="#333" stroke="#c62828" stroke-width="2"/>
            <text x="109" y="95" text-anchor="middle" fill="#c62828" font-size="10">!</text>
          </g>
          <!-- Prepared (left) -->
          <g class="prepared" transform="translate(20, 20)">
            <rect x="30" y="40" width="70" height="50" rx="4" fill="#455a64"/>
            <polygon points="65,20 110,45 20,45" fill="#546e7a"/>
            <rect x="45" y="50" width="12" height="10" fill="#ffeb3b" opacity="0.9"/>
            <rect x="62" y="50" width="12" height="10" fill="#ffeb3b" opacity="0.9"/>
            <rect x="52" y="55" width="26" height="35" fill="#263238"/>
            <rect x="5" y="70" width="28" height="40" rx="4" fill="#2e7d32" stroke="#66bb6a" stroke-width="2"/>
            <rect x="11" y="78" width="16" height="26" rx="2" fill="#1b5e20"/>
            ${this.charging
              ? html`<text x="19" y="98" text-anchor="middle" fill="#a5d6a7" font-size="9">⚡</text>`
              : html`<rect x="14" y="88" width="10" height="14" fill="#66bb6a"/>`}
          </g>
          <!-- Storm cloud -->
          <g class="lightning" transform="translate(155, 8)">
            <ellipse cx="45" cy="28" rx="50" ry="22" fill="#37474f"/>
            <path d="M 55 48 L 48 62 L 54 62 L 46 78 L 58 58 L 52 58 Z" fill="#ffeb3b"/>
          </g>
        </svg>
        <div class="caption">
          When StormSafe is enabled, the system pre-charges before extreme weather so your home
          stays powered during an outage — like the prepared house on the left.
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "fox-storm-hero": FoxStormHero;
  }
}
