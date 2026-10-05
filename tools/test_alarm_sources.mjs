// Battery (BMS) fault decoding and raised/cleared history for the Alerts page.
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const src = readFileSync(new URL("../custom_components/foxess_plant/www/foxess-plant-panel.js", import.meta.url), "utf8");
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
  `${code}; return { bmsFaultNames, eventsFromNamedHistory, mergeStoredAlertEvents };`
)();

// Stored log + HA history: the same event once, older stored events kept
{
  const t0 = Date.parse("2026-09-10T08:00:00Z");
  const history = [{ action: "cleared", name: "Meter lost", t: t0 + 3 * 86400000 + 60000, source: "alarms" }];
  const stored = [
    { action: "raised", name: "Meter lost", t: "2026-09-10T08:00:00Z" },
    { action: "cleared", name: "Meter lost", t: "2026-09-13T08:00:00Z" },
  ];
  const merged = mergeStoredAlertEvents(history, stored);
  assert.deepEqual(merged.map((e) => e.action), ["raised", "cleared"]);
}

assert.deepEqual(bmsFaultNames(["0", "0", "0", "0", "0", "0"]), []);
assert.deepEqual(bmsFaultNames(["0", "9", "unavailable"]), [
  "Battery fault 2 bit 0 (0x0001)",
  "Battery fault 2 bit 3 (0x0008)",
]);

// A fault raised for two days, a gap where the inverter couldn't be read, then cleared
const day = 86400000;
const rows = [
  { s: "0", lu: 0 },
  { s: "8", lu: 1 },
  { s: "unavailable", lu: 1 + day / 1000 },
  { s: "8", lu: 2 + day / 1000 },
  { s: "0", lu: 2 * day / 1000 },
];
const events = eventsFromNamedHistory(rows, (s) => bmsFaultNames([s]));
assert.deepEqual(
  events.map((e) => [e.action, e.name]),
  [["raised", "Battery fault 1 bit 3 (0x0008)"], ["cleared", "Battery fault 1 bit 3 (0x0008)"]]
);
console.log("alarm sources: all checks passed");
