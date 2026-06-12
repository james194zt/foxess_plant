#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
panel = ROOT / "custom_components/foxess_plant/www/foxess-plant-panel.js"
const_line = (ROOT / "tools/fox_work_mode_icons.const.js").read_text(encoding="utf-8").strip()

helpers = """
function workModeIconKey(option) {
  const k = String(option ?? "").trim();
  const map = {
    "Self Use": "selfUse",
    "Feed-in First": "feedInPriority",
    "Feed-in Priority": "feedInPriority",
    "Back-up": "backUp",
    "Back Up": "backUp",
    "Peak Shaving": "peakShaving",
    "Force Charge": "forceCharge",
    "Force Discharge": "forceDischarge",
  };
  if (map[k]) return map[k];
  const lower = k.toLowerCase();
  if (lower.includes("self")) return "selfUse";
  if (lower.includes("feed")) return "feedInPriority";
  if (lower.includes("back")) return "backUp";
  if (lower.includes("peak")) return "peakShaving";
  if (lower.includes("force") && lower.includes("charge")) return "forceCharge";
  if (lower.includes("force") && lower.includes("discharge")) return "forceDischarge";
  return null;
}

function renderWorkModeIconHtml(option) {
  const key = workModeIconKey(option);
  const svg = key ? FOX_WORK_MODE_ICONS[key] : "";
  return svg ? `<span class="mode-option-icon" aria-hidden="true">${svg}</span>` : "";
}
"""

text = panel.read_text(encoding="utf-8")
marker = "/** Display title + hint per FoxESS work_mode select option (key = entity option string). */"
if "FOX_WORK_MODE_ICONS" not in text:
    insert_at = text.find("function workModeMeta(option)")
    text = text[:insert_at] + const_line + "\n\n" + helpers + "\n" + text[insert_at:]

old_render = """        return `<button type="button" class="mode-option ${sel}" data-action="pick-work-mode" data-mode="${esc(opt)}">
<span class="mode-option-body"><span class="name">${esc(meta.title)}</span>${meta.hint ? `<span class="hint">${esc(meta.hint)}</span>` : ""}</span></button>`;"""

new_render = """        return `<button type="button" class="mode-option ${sel}" data-action="pick-work-mode" data-mode="${esc(opt)}">
${renderWorkModeIconHtml(opt)}<span class="mode-option-body"><span class="name">${esc(meta.title)}</span>${meta.hint ? `<span class="hint">${esc(meta.hint)}</span>` : ""}</span></button>`;"""

text = text.replace(old_render, new_render)

old_css = """.mode-grid { display: grid; gap: 8px; }
.mode-option {
  display: block; width: 100%; text-align: left; padding: 14px 16px;
  border-radius: 12px; border: 2px solid var(--divider-color); background: var(--card-background-color);
  cursor: pointer; font-family: inherit; color: inherit; transition: border-color 0.15s;
}
.mode-option.selected { border-color: var(--fp-accent); background: color-mix(in srgb, var(--fp-accent) 10%, var(--card-background-color)); }
.mode-option-body { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; width: 100%; }"""

new_css = """.mode-grid { display: grid; gap: 8px; }
.mode-option {
  display: flex; align-items: flex-start; gap: 12px; width: 100%; text-align: left; padding: 14px 16px;
  border-radius: 12px; border: 2px solid var(--divider-color); background: var(--card-background-color);
  cursor: pointer; font-family: inherit; color: inherit; transition: border-color 0.15s;
}
.mode-option.selected { border-color: var(--fp-accent); background: color-mix(in srgb, var(--fp-accent) 10%, var(--card-background-color)); }
.mode-option-icon {
  flex: 0 0 40px; width: 40px; height: 40px; border-radius: 8px; overflow: hidden;
}
.mode-option-icon svg { display: block; width: 100%; height: 100%; }
.mode-option-body { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; flex: 1; min-width: 0; }"""

text = text.replace(old_css, new_css)

text = text.replace("@version 0.9.91", "@version 0.9.92")
panel.write_text(text, encoding="utf-8")
print("patched panel")

manifest = ROOT / "custom_components/foxess_plant/manifest.json"
manifest.write_text(manifest.read_text(encoding="utf-8").replace('"0.9.91"', '"0.9.92"'), encoding="utf-8")
print("bumped manifest")
