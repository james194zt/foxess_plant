#!/usr/bin/env node
/** Extract Fox Cloud device page SVG icons from New Devices.har */
const fs = require("fs");
const path = require("path");

const HAR = process.argv[2] || path.resolve(__dirname, "../../Fox APp Screenshots/New Devices.har");
const OUT = path.resolve(__dirname, "../custom_components/foxess_plant/www/fox-device-icons.json");

function extractSymbol(text, iconId) {
  const re = new RegExp(`id:"${iconId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"[^}]*content:'([^']+)'`);
  const m = text.match(re);
  if (!m) return null;
  let raw = m[1].replace(/\\n/g, "\n");
  raw = raw.replace(/<symbol([^>]*)>/, "<svg$1>");
  raw = raw.replace("</symbol>", "</svg>");
  raw = raw.replace(/\s+xmlns="http:\/\/www.w3.org\/2000\/svg"/, "");
  if (!raw.includes('xmlns="http://www.w3.org/2000/svg"')) {
    raw = raw.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1);
  }
  return raw;
}

const har = JSON.parse(fs.readFileSync(HAR, "utf8"));
const jsTexts = [];
for (const e of har.log.entries || []) {
  const url = e.request?.url || "";
  const t = e.response?.content?.text;
  if (!t || typeof t !== "string") continue;
  if (/\.js(\?|$)/.test(url)) jsTexts.push(t);
}
const app = jsTexts.join("\n");
const iconIds = [...new Set([...app.matchAll(/id:"(icon-[^"]+)"/g)].map((m) => m[1]))].sort();
console.log(`Found ${iconIds.length} icon ids in HAR JS`);

const WANT = {
  pv_power: ["icon-icon-phot", "icon-pv", "icon-icon-pv"],
  battery_soc: ["icon-icon-battery", "icon-battery", "icon-soc"],
  discharging: ["icon-icon-discharge", "icon-discharge"],
  temperature: ["icon-icon-temp", "icon-temperature", "icon-temp"],
};

const icons = {};
const missing = [];
for (const [key, candidates] of Object.entries(WANT)) {
  let svg = null;
  let used = null;
  for (const id of candidates) {
    svg = extractSymbol(app, id);
    if (svg) {
      used = id;
      break;
    }
  }
  if (!svg) {
    for (const id of iconIds) {
      if (
        (key === "pv_power" && /phot|pv/i.test(id)) ||
        (key === "battery_soc" && /battery/i.test(id) && !/discharg/i.test(id)) ||
        (key === "discharging" && /discharg/i.test(id)) ||
        (key === "temperature" && /temp/i.test(id))
      ) {
        svg = extractSymbol(app, id);
        if (svg) {
          used = id;
          break;
        }
      }
    }
  }
  if (svg) {
    icons[key] = svg;
    console.log(`  ${key}: ${used}`);
  } else {
    missing.push(key);
    console.log(`  ${key}: MISSING`);
  }
}

// Also dump all matching ids for manual review
const review = iconIds.filter((id) => /phot|pv|battery|discharg|temp|soc|power|device|real|curve|load|grid|eps|ac/i.test(id));
fs.writeFileSync(OUT, JSON.stringify({ icons, missing, reviewIds: review }, null, 2));
console.log(`Wrote ${OUT}`);
