// Analysis card money: each step of a daily kWh counter is priced at the rate in force at the time.
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
const { priceDailyCounter, syncSparkSeriesToTotal } = new Function(
  `${grab("priceDailyCounter")}\n${grab("syncSparkSeriesToTotal")}; return { priceDailyCounter, syncSparkSeriesToTotal };`
)();

const H = 3600 * 1000;
const day = Date.UTC(2026, 9, 5);
const near = (a, b, msg) => assert.ok(Math.abs(a - b) < 1e-9, `${msg}: ${a} vs ${b}`);
// The user's bands (£/kWh): 0.1805 02:00-05:00, 0.4525 16:00-19:00, 0.2465 otherwise
const rate = (t) => {
  const h = new Date(t).getUTCHours();
  return h >= 2 && h < 5 ? 0.1805 : h >= 16 && h < 19 ? 0.4525 : 0.2465;
};

// Yesterday's 2.3 kWh still showing at midnight, reset just after, then 1 kWh at 03:00 and 0.5 kWh at 17:00
const pts = [
  { t: day, v: 2.3 },
  { t: day + 60 * 1000, v: 0 },
  { t: day + 3 * H, v: 1.0 },
  { t: day + 17 * H, v: 1.5 },
];
const r = priceDailyCounter(pts, day, day + 20 * H, 10 * 60 * 1000, rate);
near(r.kwh, 1.5, "kWh ignores yesterday's total");
near(r.cost, 1.0 * 0.1805 + 0.5 * 0.4525, "each step at its own band");
assert.equal(r.cumulative[0], 0);
// Running cost never goes down when the rate changes
for (let i = 1; i < r.cumulative.length; i++) assert.ok(r.cumulative[i] >= r.cumulative[i - 1] - 1e-12);

// A better meter's total keeps the timing but sets the kWh
const g = priceDailyCounter(pts, day, day + 20 * H, 10 * 60 * 1000, rate, 3.0);
near(g.kwh, 3.0, "scaled kWh");
near(g.cost, 2 * (1.0 * 0.1805 + 0.5 * 0.4525), "scaled cost");

// No energy: no cost; no target applied to nothing
const z = priceDailyCounter([{ t: day, v: 0 }], day, day + 2 * H, 10 * 60 * 1000, rate, 1.0);
near(z.cost, 0, "nothing imported");

// Sparkline scaled to the total rather than a jump at the end
assert.deepEqual(syncSparkSeriesToTotal([0, 5, 10], 11), [0, 5.5, 11]);
assert.deepEqual(syncSparkSeriesToTotal([0, 0], 2), [0, 2]);
console.log("tariff pricing: all checks passed");
