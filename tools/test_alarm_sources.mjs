// Battery (BMS) fault decoding and raised/cleared history for the Alerts page.
import { copyFileSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const www = new URL("../custom_components/foxess_plant/www/", import.meta.url);
const src = readFileSync(new URL("foxess-plant-panel.js", www), "utf8");

// The guide is an ES module with a .js name: import a .mjs copy of it
const tmp = mkdtempSync(join(tmpdir(), "fox-guide-"));
copyFileSync(new URL("fox-alarm-guide.js", www), join(tmp, "fox-alarm-guide.mjs"));
const { bmsFaultLabel } = await import(pathToFileURL(join(tmp, "fox-alarm-guide.mjs")).href);

const grab = (name) => {
  const start = src.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `function ${name} not found`);
  let depth = 0;
  let i = src.indexOf("{", start);
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) break;
  }
  return src.slice(start, i + 1);
};
const code = [
  "historyRowTimeMs",
  "historyToStateRows",
  "bmsFaultNames",
  "eventsFromNamedHistory",
  "mergeStoredAlertEvents",
]
  .map(grab)
  .join("\n");
const { bmsFaultNames, eventsFromNamedHistory, mergeStoredAlertEvents } = new Function(
  "bmsFaultLabel",
  `${code}; return { bmsFaultNames, eventsFromNamedHistory, mergeStoredAlertEvents };`
)(bmsFaultLabel);

// Named from the EVO manual's BS1-BS6 table; unnamed bits keep the raw bit
assert.deepEqual(bmsFaultNames(["0", "0", "0", "0", "0", "0"]), []);
assert.deepEqual(bmsFaultNames(["3"]), [
  "Battery BS1 E01: Communication fault with PCS (EXT COM)",
  "Battery BS1 E02: Internal communication fault (INT COM)",
]);
assert.deepEqual(bmsFaultNames(["0", "5", "unavailable"]), [
  "Battery BS2 E01: Cell imbalance alarm (CB)",
  "Battery BS2 bit 2 (0x0004)",
]);

// A fault raised for two days, a gap where the inverter couldn't be read, then cleared
const day = 86400000;
const rows = [
  { s: "0", lu: 0 },
  { s: "8", lu: 1 },
  { s: "unavailable", lu: 1 + day / 1000 },
  { s: "8", lu: 2 + day / 1000 },
  { s: "0", lu: (2 * day) / 1000 },
];
const uv = "Battery BS1 E08: Under voltage fault (UV)";
const events = eventsFromNamedHistory(rows, (s) => bmsFaultNames([s]));
assert.deepEqual(
  events.map((e) => [e.action, e.name]),
  [["raised", uv], ["cleared", uv]]
);

// Stored log + HA history: the same event once, older stored events kept
{
  const t0 = Date.parse("2026-09-10T08:00:00Z");
  const history = [{ action: "cleared", name: "Meter lost", t: t0 + 3 * day + 60000, source: "alarms" }];
  const stored = [
    { action: "raised", name: "Meter lost", t: "2026-09-10T08:00:00Z" },
    { action: "cleared", name: "Meter lost", t: "2026-09-13T08:00:00Z" },
  ];
  assert.deepEqual(mergeStoredAlertEvents(history, stored).map((e) => e.action), ["raised", "cleared"]);
}
console.log("alarm sources: all checks passed");
