// Extract the warm-up tariff helpers from the panel and check them against real and edge-case maps.
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const src = readFileSync(new URL("../custom_components/foxess_plant/www/foxess-plant-panel.js", import.meta.url), "utf8");
const grab = (name) => {
  const start = src.indexOf(`function ${name}(`);
  let depth = 0, i = src.indexOf("{", start);
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) break;
  }
  return src.slice(start, i + 1);
};
const code = ["tariffHourlyImport", "warmupWindowsFromTariff", "warmupCoversHour"].map(grab).join("\n");
const { tariffHourlyImport, warmupWindowsFromTariff, warmupCoversHour } = new Function(
  `${code}; return { tariffHourlyImport, warmupWindowsFromTariff, warmupCoversHour };`
)();

const bands = (...p) => p.map((x) => ({ import_p_per_kwh: x }));
// The user's map (2026-10-05): 18.05p 02-05, 45.25p 16-19, 24.65p otherwise
const user = { hours: [0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0], bands: bands(24.65, 18.05, 45.25, 0) };
assert.deepEqual(warmupWindowsFromTariff(user), { price: 18.05, windows: [{ start: "02:00", end: "05:00" }] });

// Economy 7 style crossing midnight: cheap 23:00-06:00 stays one window
const e7 = { hours: Array.from({ length: 24 }, (_, h) => (h >= 23 || h < 6 ? 1 : 0)), bands: bands(30, 12, 0, 0) };
assert.deepEqual(warmupWindowsFromTariff(e7).windows, [{ start: "23:00", end: "06:00" }]);

// Four cheap runs: keep the three longest, in time order
const four = { hours: [1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0], bands: bands(30, 10, 0, 0) };
assert.deepEqual(warmupWindowsFromTariff(four).windows, [
  { start: "00:00", end: "02:00" }, { start: "06:00", end: "09:00" }, { start: "12:00", end: "16:00" },
]);

// Flat price or no prices: nothing to pick
assert.equal(warmupWindowsFromTariff({ hours: Array(24).fill(0), bands: bands(24, 0, 0, 0) }), null);
assert.equal(warmupWindowsFromTariff({ hours: Array(24).fill(0), bands: bands(0, 0, 0, 0) }), null);
assert.equal(tariffHourlyImport({ hours: Array(24).fill(0), bands: bands(0, 0, 0, 0) }), null);

// Coverage marks, including a period crossing midnight and disabled periods
const slots = [{ enabled: true, start: "23:00", end: "02:00" }, { enabled: false, start: "10:00", end: "12:00" }];
assert.deepEqual([22, 23, 0, 1, 2, 10].map((h) => warmupCoversHour(slots, h)), [false, true, true, true, false, false]);
console.log("warm-up tariff helpers: all checks passed");
