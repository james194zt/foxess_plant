#!/usr/bin/env node
/** Extract Fox Cloud alarm page SVG icons from the public app.js bundle. */
const fs = require("fs");
const path = require("path");
const https = require("https");

const APP_URL = process.argv[2] || "https://www.foxesscloud.com/v2/assets/js/app.4cb4e12a.js";
const OUT_JSON = path.resolve(__dirname, "../custom_components/foxess_plant/www/fox-alarm-icons.json");
const OUT_CONST = path.resolve(__dirname, "fox_alarm_icons.const.js");

const ICON_IDS = {
  alarm: "icon-alarm",
  alert: "icon-alert",
  warning: "icon-warning",
  no_alarm: "icon-noAlarm",
  big_empty: "icon-bigEmpty",
  empty: "icon-empty",
  fault: "icon-fault",
  fault_red: "icon-fault-red",
  faults: "icon-faults",
  tips_warn: "icon-tipsWarn",
};

function fetchText(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
      })
      .on("error", reject);
  });
}

function extractSymbol(text, iconId) {
  const re = new RegExp(
    `id:"${iconId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"[^}]*content:'([^']+)'`
  );
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

async function main() {
  const app = await fetchText(APP_URL);
  const icons = {};
  const missing = [];
  for (const [key, id] of Object.entries(ICON_IDS)) {
    const svg = extractSymbol(app, id);
    if (svg) icons[key] = { id, svg };
    else missing.push(id);
  }

  const cogPath = path.resolve(__dirname, "../custom_components/foxess_plant/www/fox-alarm-active-cog.svg");
  let activeCog = null;
  if (fs.existsSync(cogPath)) {
    activeCog = fs.readFileSync(cogPath, "utf8").trim();
  }

  const payload = { icons, missing, active_cog: activeCog ? "fox-alarm-active-cog.svg" : null };
  fs.writeFileSync(OUT_JSON, JSON.stringify(payload, null, 2));

  const flat = {};
  for (const [key, val] of Object.entries(icons)) flat[key] = val.svg;
  if (activeCog) flat.active_cog = activeCog;
  fs.writeFileSync(OUT_CONST, `const FOX_ALARM_ICONS = ${JSON.stringify(flat)};\n`);
  console.log(`wrote ${OUT_JSON} (${Object.keys(icons).length} icons, missing=${missing})`);
  console.log(`wrote ${OUT_CONST}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
