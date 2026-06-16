#!/usr/bin/env node
/** Insert FOX_ALARM_ICONS from fox_alarm_icons.const.js into foxess-plant-panel.js */
const fs = require("fs");
const path = require("path");

const PANEL = path.resolve(__dirname, "../custom_components/foxess_plant/www/foxess-plant-panel.js");
const CONST = path.resolve(__dirname, "fox_alarm_icons.const.js");
const MARKER = "function mergeAlarmHistoryEvents";

let panel = fs.readFileSync(PANEL, "utf8");
const iconsBlock = fs.readFileSync(CONST, "utf8").trim() + "\n\n";

if (panel.includes("const FOX_ALARM_ICONS =")) {
  panel = panel.replace(/const FOX_ALARM_ICONS = \{[\s\S]*?\};\n\n/, iconsBlock);
  console.log("Replaced existing FOX_ALARM_ICONS");
} else if (panel.includes(MARKER)) {
  panel = panel.replace(MARKER, iconsBlock + MARKER);
  console.log("Inserted FOX_ALARM_ICONS before mergeAlarmHistoryEvents");
} else {
  console.error("Could not find insertion point");
  process.exit(1);
}

fs.writeFileSync(PANEL, panel);
console.log("Patched", PANEL);
