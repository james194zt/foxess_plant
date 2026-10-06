// Smoke test for the responsive chart renderers in foxess-plant-panel.js.
//
// Loads the panel bundle in a stubbed browser context (no DOM needed) and renders the
// statistics, battery SOC and energy charts at phone (390px) and desktop (1400px) panel
// widths, checking viewBox sizes, layout mode and that no NaN/undefined leaks into SVG.
//
// Usage (WSL / Linux, Node 18+):  node tools/test_panel_charts.mjs
// Exit code 0 = all checks passed.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const panelPath = path.resolve(here, "../custom_components/foxess_plant/www/foxess-plant-panel.js");
const src = fs.readFileSync(panelPath, "utf8");

// Strip the ES import and evaluate as a classic script in a stubbed browser-ish context.
const code =
  src
    .replace(/^import .*$/m, "const renderFoxAlarmDetailModal = () => '';")
    .replace(/import\.meta/g, "({ url: '' })") +
  `
;globalThis.__fp = { setChartPanelWidth, isNarrowChart, chartRenderWidth, statisticsChartLayout,
  batterySocChartLayout, renderStatisticsChartHtml, renderBatterySocChartHtml,
  renderMirroredEnergyBarChart, renderBarChartSvg, emptyEnergyBucket, FOX_SUPPLY_SERIES, FOX_USAGE_SERIES,
  renderPerformancePowerChartSvg, renderPerformancePhysicsChartSvg, renderPerformanceMicroclimateChartSvg };`;

class Stub { constructor() {} }
const el = () => ({ style: {}, classList: { toggle() {}, add() {}, remove() {} }, append() {}, appendChild() {},
  addEventListener() {}, removeEventListener() {}, setAttribute() {}, querySelector: () => null,
  querySelectorAll: () => [] });
const ctx = {
  console, Math, Date, JSON, Number, String, Array, Object, Set, Map, Promise, Intl, RegExp, Error,
  isFinite, parseFloat, parseInt, encodeURIComponent, decodeURIComponent, URL, URLSearchParams,
  setTimeout, clearTimeout, setInterval, clearInterval,
  HTMLElement: class extends Stub { attachShadow() { return el(); } },
  customElements: { define() {}, get: () => undefined },
  document: { createElement: el, documentElement: el(), head: el(), body: el(), querySelector: () => null,
    querySelectorAll: () => [], getElementsByTagName: () => [], addEventListener() {} },
  getComputedStyle: () => ({ getPropertyValue: () => "" }),
  requestAnimationFrame: (f) => 0,
  fetch: async () => ({ ok: false, json: async () => ({}) }),
  navigator: { userAgent: "node" },
  location: { href: "http://x/", origin: "http://x", pathname: "/" },
  localStorage: { getItem: () => null, setItem() {} },
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  innerWidth: 390,
};
ctx.window = ctx;
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(code, ctx, { filename: "foxess-plant-panel.js" });
const fp = ctx.__fp;

let failures = 0;
const check = (name, cond, detail = "") => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
  if (!cond) failures++;
};
const vb = (html, cls) => {
  const m = html.match(new RegExp(`class="${cls}"[^>]*viewBox="0 0 ([\\d.]+) ([\\d.]+)"[^>]*`));
  return m ? { w: +m[1], h: +m[2], tag: m[0] } : null;
};
const noNaN = (html) => !/NaN|undefined|Infinity/.test(html);

// Fake one day of data.
const day0 = new Date(); day0.setHours(0, 0, 0, 0);
const tMin = day0.getTime(), tMax = tMin + 86400000, nowMs = tMin + 15 * 3600000;
const range = { tMin, tMax, nowMs };
const pts = (f) => Array.from({ length: 180 }, (_, i) => ({ t: tMin + i * 300000, v: f(i) }));
const series = [
  { id: "pv", legendGroup: "pv", color: "#f90", fill: true, fillColor: "rgba(255,153,0,.2)", points: pts((i) => Math.max(0, Math.sin(i / 30)) * 4) },
  { id: "load", legendGroup: "load", color: "#0af", points: pts((i) => 0.5 + (i % 20) / 20) },
];
const socSeries = { id: "soc", color: "#3d8", points: pts((i) => 20 + (i % 80)) };

for (const [label, panelW] of [["phone 390px", 390], ["desktop 1400px", 1400]]) {
  console.log(`\n== ${label} ==`);
  fp.setChartPanelWidth(panelW);
  const narrow = fp.isNarrowChart();
  check("narrow mode detection", narrow === panelW < 756, `narrow=${narrow}`);

  // Statistics
  for (const opts of [{}, { sideLegend: true, includeSoc: true, socSeries }]) {
    const html = fp.renderStatisticsChartHtml(series, range, opts);
    const v = vb(html, "statistics-chart-svg");
    check(`statistics ${JSON.stringify(Object.keys(opts))} renders`, !!v && noNaN(html), v ? `${v.w}x${v.h}` : "no svg");
    if (narrow) {
      check("  statistics width = real px", v.w === panelW - 56, `${v.w}`);
      check("  statistics fluid style", /aspect-ratio:/.test(v.tag));
      const xLabels = (html.match(/class="statistics-axis-x"/g) || []).length;
      check("  statistics 4 x-labels", xLabels === 4, `${xLabels}`);
    } else {
      check("  statistics desktop 1000x440 unchanged", v.w === 1000 && v.h === 440 && !/aspect-ratio/.test(v.tag));
    }
  }

  // Battery SOC
  const socChart = { range, socPts: socSeries.points, segments: [{ mode: "charging", pts: socSeries.points }], activityBars: [] };
  const socHtml = fp.renderBatterySocChartHtml(socChart, 55);
  const sv = vb(socHtml, "soc-chart-svg");
  check("battery SOC renders", !!sv && noNaN(socHtml), sv ? `${sv.w}x${sv.h}` : "no svg");
  check(narrow ? "  SOC uses meet (not cropped)" : "  SOC desktop keeps slice",
    narrow ? /xMidYMid meet/.test(sv.tag) : /xMidYMid slice/.test(sv.tag));

  // Mirrored energy (week + month)
  const bucket = () => {
    const b = fp.emptyEnergyBucket();
    for (const s of fp.FOX_SUPPLY_SERIES) b.supply[s.key] = 3;
    for (const s of fp.FOX_USAGE_SERIES) b.usage[s.key] = 2;
    return b;
  };
  const week = fp.renderMirroredEnergyBarChart(Array.from({ length: 7 }, bucket), ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], { labelMode: "weekday" });
  const wv = vb(week, "fox-energy-mirror-chart");
  check("energy week renders", !!wv && noNaN(week), wv ? `${wv.w}x${wv.h}` : "no svg");
  check("  energy plot carries chart width for hover", new RegExp(`data-chart-w="${wv.w}"`).test(week));
  const days = Array.from({ length: 31 }, (_, i) => new Date(2026, 9, i + 1));
  const month = fp.renderMirroredEnergyBarChart(days.map(bucket), days, { labelMode: "month-day" });
  const monthLabels = (month.match(/<text[^>]*class="fox-energy-axis">\d+<\/text>/g) || [])
    .filter((t) => /y="[\d.]+" text-anchor="middle"/.test(t)).length;
  check("energy month renders", noNaN(month), `${monthLabels} day labels`);
  if (narrow) check("  month labels thinned on phone", monthLabels <= 12, `${monthLabels}`);

  // Small bar chart
  const bar = fp.renderBarChartSvg([{ label: "PV", color: "#f90", values: [1, 2, 3, 4, 5, 6, 7] }], days.slice(0, 7), { height: 180 });
  check("energy bar chart renders", noNaN(bar) && /energy-bar-chart/.test(bar));
}

// Performance charts at 5-minute detail (2026-10-06: bead-string dots, dew point read off the km axis)
{
  console.log("\n== performance charts, dense 5-minute day ==");
  const dense = (f) => Array.from({ length: 78 }, (_, i) => ({ t: tMin + i * 300000, v: f(i) }));
  const perfChart = (series) => ({ series, ac_limit_kw: 3.68, chart_window: { start_ms: tMin, end_ms: tMax } });
  const power = fp.renderPerformancePowerChartSvg(
    perfChart({ pv_power_kw: dense(() => 0), net_grid_power_kw: dense((i) => -0.02 * (i % 5)) })
  );
  check("power chart renders", noNaN(power) && /fox-perf-chart-svg/.test(power));
  check("  no per-sample dots on a dense line", !/<circle/.test(power));
  check("  sample hint counts what's drawn", !/\d+ samples? so far/.test(power));
  const physics = fp.renderPerformancePhysicsChartSvg(
    perfChart({ virtual_panel_temp_c: dense((i) => 10 + i / 10), wind_speed_ms: dense((i) => (i % 9) / 10) })
  );
  check("panel cooling chart renders", noNaN(physics));
  check("  wind has its own right-hand axis", /fill="#52C41A"[^>]*>[\d.]+</.test(physics) || /text-anchor="start"[^>]*fill="#52C41A"/.test(physics));
  check("  old voltage-method hint gone", !/400 V baselines/.test(physics));
  const micro = fp.renderPerformanceMicroclimateChartSvg(
    perfChart({ visibility_km: dense(() => 11), dew_point_c: dense((i) => 5 + (i % 20) / 10) })
  );
  check("microclimate chart renders", noNaN(micro));
  check("  dew point has its own °C axis", /text-anchor="start"[^>]*fill="#597EF7"[^>]*>[\d.]+°</.test(micro));
}

console.log(failures ? `\n${failures} FAILURE(S)` : "\nALL CHECKS PASSED");
process.exit(failures ? 1 : 0);
