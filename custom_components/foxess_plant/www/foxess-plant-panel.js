/**
 * FoxESS Plant panel — HA sidebar app (phases 5a–5e).
 * hass / narrow / panel / route from Home Assistant.
 * @version 0.9.267
 */

import { renderFoxAlarmDetailModal } from "./fox-alarm-guide.js";

/** @deprecated Legacy device UI — not in nav (replaced by device_new). */
const PANEL_VIEW_DEVICE_LEGACY = "device_legacy";

const NAV = [
  { id: "overview", label: "Overview" },
  { id: "device_new", label: "Device" },
  { id: "energy_analysis", label: "Energy Analysis" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const DEVICE_NEW_NAV = [
  { id: "analysis", label: "Analysis" },
  { id: "realtime", label: "Realtime" },
  { id: "alarms", label: "Alerts" },
  { id: "pv-config", label: "PV Configuration" },
];

/** Fox Cloud device Analysis real-time curve series. */
// FOX_DEVICE_SUMMARY_ICONS_START
const FOX_DEVICE_SUMMARY_ICONS = {"battery_soc": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 40 40\" fill=\"none\" id=\"icon-d-battery1\">\n<g id=\"icon-d-battery1_Frame 1739332876\">\n<circle id=\"icon-d-battery1_Ellipse 3833\" cx=\"19.9967\" cy=\"19.9967\" r=\"16.6667\" fill=\"#894BFC\" fill-opacity=\"0.1\" />\n<g id=\"icon-d-battery1_Rectangle 34625968\">\n<mask id=\"icon-d-battery1_path-2-inside-1_278_10283\" fill=\"white\">\n<rect x=\"15.1123\" y=\"13.1847\" width=\"9.76953\" height=\"14.5304\" rx=\"1\" />\n</mask>\n<rect x=\"15.1123\" y=\"13.1847\" width=\"9.76953\" height=\"14.5304\" rx=\"1\" stroke=\"#894BFC\" stroke-width=\"2.2\" mask=\"url(#icon-d-battery1_path-2-inside-1_278_10283)\" />\n</g>\n<path id=\"icon-d-battery1_Rectangle 34625969\" d=\"M18.1475 12.6784C18.1475 12.4575 18.3265 12.2784 18.5475 12.2784H21.4486C21.6695 12.2784 21.8486 12.4575 21.8486 12.6784V13.3163H18.1475V12.6784Z\" fill=\"#894BFC\" />\n<rect id=\"icon-d-battery1_Rectangle 34625973\" x=\"16.9961\" y=\"23.9239\" width=\"6\" height=\"1.76709\" rx=\"0.2\" fill=\"#894BFC\" />\n<rect id=\"icon-d-battery1_Rectangle 34625974\" x=\"16.9961\" y=\"21.3531\" width=\"6\" height=\"1.76709\" rx=\"0.2\" fill=\"#894BFC\" />\n</g>\n</svg>", "discharging": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 40 40\" fill=\"none\" id=\"icon-d-battery2\">\n<g id=\"icon-d-battery2_Frame 1739332877\">\n<circle id=\"icon-d-battery2_Ellipse 3833\" cx=\"19.9997\" cy=\"19.9987\" r=\"16.6667\" fill=\"#D9F7BE\" />\n<path id=\"icon-d-battery2_Vector 1662\" d=\"M14.0558 20.3907L21.9124 12.165C22.0395 12.032 22.2627 12.1393 22.2381 12.3217L21.3216 19.1138C21.3062 19.2278 21.3948 19.3292 21.5099 19.3292L25.7831 19.3292C25.9537 19.3292 26.0379 19.5367 25.9154 19.6555L17.4973 27.828C17.3629 27.9584 17.1407 27.8363 17.1789 27.6529L18.5773 20.9407C18.6019 20.8227 18.5119 20.7119 18.3913 20.7119H14.1932C14.0261 20.7119 13.9404 20.5116 14.0558 20.3907Z\" stroke=\"#52C41A\" stroke-width=\"1.045\" />\n<path id=\"icon-d-battery2_Vector 1663\" d=\"M19.7575 16.8945L17.9814 18.9603\" stroke=\"#52C41A\" stroke-width=\"0.76\" stroke-linecap=\"round\" />\n</g>\n</svg>", "temperature": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 41 40\" fill=\"none\" id=\"icon-d-battery3\">\n<circle cx=\"20.4997\" cy=\"19.9987\" r=\"16.6667\" fill=\"#D9F7BE\" />\n<path d=\"M18.5741 15.2578H19.7591C20.1542 15.2578 20.3518 15.4554 20.3518 15.8505C20.3518 16.2456 20.1542 16.4431 19.7591 16.4431H18.5741C18.179 16.4431 17.9814 16.2456 17.9814 15.8505C17.9814 15.4554 18.179 15.2578 18.5741 15.2578Z\" fill=\"#52C41A\" />\n<path d=\"M18.5741 17.9258H19.7591C20.1542 17.9258 20.3518 18.1233 20.3518 18.5184C20.3518 18.9136 20.1542 19.1111 19.7591 19.1111H18.5741C18.179 19.1111 17.9814 18.9136 17.9814 18.5184C17.9814 18.1233 18.179 17.9258 18.5741 17.9258Z\" fill=\"#52C41A\" />\n<path d=\"M20.413 11.3334C19.6621 11.3559 18.9496 11.67 18.4264 12.2091C17.9033 12.7482 17.6107 13.4698 17.6107 14.221V20.3334L17.527 20.401C16.9967 20.8386 16.5698 21.3881 16.2769 22.0101C15.9841 22.6321 15.8325 23.3112 15.833 23.9987C15.833 26.576 17.9223 28.6654 20.4997 28.6654C23.077 28.6654 25.1663 26.576 25.1663 23.9987L25.1647 23.8777C25.1479 23.2108 24.9882 22.5553 24.6962 21.9555C24.4042 21.3557 23.9869 20.8256 23.4723 20.401L23.3883 20.3334V14.221C23.3883 13.4549 23.084 12.7201 22.5423 12.1783C22.0006 11.6365 21.2658 11.3321 20.4997 11.332L20.413 11.3334ZM20.4997 12.6654C20.704 12.6654 20.9063 12.7056 21.095 12.7838C21.2837 12.862 21.4552 12.9766 21.5997 13.121C21.7442 13.2655 21.8587 13.437 21.9369 13.6257C22.0151 13.8144 22.0553 14.0167 22.0553 14.221V20.672C22.0553 20.7816 22.0823 20.8894 22.1339 20.986C22.1854 21.0826 22.26 21.1651 22.351 21.226C22.8073 21.5303 23.1814 21.9427 23.4399 22.4264C23.6985 22.9101 23.8335 23.4502 23.833 23.9987C23.833 25.8397 22.3407 27.332 20.4997 27.332C18.6587 27.332 17.1663 25.8397 17.1663 23.9987C17.1663 22.872 17.729 21.842 18.6483 21.2264C18.7393 21.1654 18.8139 21.083 18.8655 20.9864C18.9171 20.8897 18.944 20.7819 18.944 20.6724V14.221C18.944 14.0167 18.9842 13.8144 19.0624 13.6257C19.1406 13.437 19.2552 13.2655 19.3997 13.121C19.5441 12.9766 19.7156 12.862 19.9043 12.7838C20.0931 12.7056 20.2954 12.6654 20.4997 12.6654Z\" fill=\"#52C41A\" />\n<path d=\"M18.8337 23C18.9216 23 19.0087 23.0174 19.0899 23.0512C19.1712 23.085 19.2449 23.1346 19.3068 23.197C19.3688 23.2595 19.4178 23.3335 19.451 23.415C19.4842 23.4965 19.501 23.5837 19.5003 23.6717L19.502 23.7317C19.5187 24.054 19.6584 24.3576 19.8925 24.5798C20.1265 24.8021 20.4369 24.926 20.7597 24.926V26.2593L20.6773 26.258C20.0043 26.2366 19.366 25.9542 18.8975 25.4706C18.429 24.987 18.167 24.34 18.167 23.6667L18.1687 23.6167C18.1813 23.4489 18.2568 23.2922 18.3801 23.1778C18.5035 23.0635 18.6655 22.9999 18.8337 23Z\" fill=\"#52C41A\" />\n</svg>", "pv_power": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 40 40\" fill=\"none\" id=\"icon-d-battery4\">\n<g id=\"icon-d-battery4_Frame 1321317006\">\n<circle id=\"icon-d-battery4_Ellipse 3833\" cx=\"19.9967\" cy=\"19.9948\" r=\"16.6667\" fill=\"#699BFF\" fill-opacity=\"0.1\" />\n<rect id=\"icon-d-battery4_Rectangle 34625970\" x=\"23.4297\" y=\"22.2656\" width=\"5.96902\" height=\"1.1\" rx=\"0.55\" fill=\"#699BFF\" />\n<rect id=\"icon-d-battery4_Rectangle 34625971\" x=\"22.0918\" y=\"24.4102\" width=\"7.30739\" height=\"1.1\" rx=\"0.55\" fill=\"#699BFF\" />\n<rect id=\"icon-d-battery4_Rectangle 34625972\" x=\"20.2891\" y=\"26.8477\" width=\"9.10883\" height=\"1.1\" rx=\"0.55\" fill=\"#699BFF\" />\n<path id=\"icon-d-battery4_Vector\" d=\"M22.3981 19.087H20.816C20.6734 19.087 20.5645 18.9583 20.5877 18.8181L21.151 15.3676C21.1881 15.1416 20.9087 15.0048 20.7523 15.1717L16.7698 19.4335C16.6318 19.5819 16.7361 19.8241 16.939 19.8241H18.5211C18.6636 19.8241 18.7726 19.9528 18.7494 20.093L18.1861 23.5435C18.149 23.7696 18.4284 23.9063 18.5848 23.7394L22.5673 19.4776C22.7064 19.3292 22.6009 19.087 22.3981 19.087Z\" fill=\"#699BFF\" />\n<path id=\"icon-d-battery4_Ellipse 3837\" d=\"M28.7434 19.9967C28.7434 14.9848 24.6805 10.9219 19.6686 10.9219C14.6567 10.9219 10.5938 14.9848 10.5938 19.9967C10.5938 25.0086 14.6567 29.0715 19.6686 29.0715\" stroke=\"#699BFF\" stroke-width=\"1.1\" stroke-linecap=\"round\" />\n</g>\n</svg>"};
// FOX_DEVICE_SUMMARY_ICONS_END

/** Fox Cloud device summary card accents (chart palette + icon fills). */
const DEVICE_SUMMARY_CARD_THEMES = {
  pv: {
    accent: "#08979C",
    accentHi: "#19D4DE",
    bg: "linear-gradient(180deg, rgba(8,151,156,0.20) 0%, rgba(25,212,222,0.06) 38%, rgba(8,151,156,0.02) 100%)",
    top: "linear-gradient(90deg, #19D4DE 0%, #08979C 100%)",
  },
  soc: {
    accent: "#894BFC",
    accentHi: "#B69CFF",
    bg: "linear-gradient(180deg, rgba(137,75,252,0.18) 0%, rgba(137,75,252,0.05) 40%, rgba(137,75,252,0.02) 100%)",
    top: "linear-gradient(90deg, #B69CFF 0%, #894BFC 100%)",
  },
  discharge: {
    accent: "#52C41A",
    accentHi: "#03BD9A",
    bg: "linear-gradient(180deg, rgba(82,196,26,0.16) 0%, rgba(3,189,154,0.06) 40%, rgba(82,196,26,0.02) 100%)",
    top: "linear-gradient(90deg, #03BD9A 0%, #52C41A 100%)",
  },
  temp: {
    accent: "#52C41A",
    accentHi: "#03BD9A",
    bg: "linear-gradient(180deg, rgba(82,196,26,0.16) 0%, rgba(3,189,154,0.06) 40%, rgba(82,196,26,0.02) 100%)",
  },
};

const DEVICE_REALTIME_CHART_SERIES = [
  {
    key: "pv_power",
    label: "PV Power",
    legendGroup: "pv",
    color: "#19D4DE",
    toKw: true,
    fill: false,
    lineWidth: 1.6,
  },
  {
    key: "eps_power_R",
    label: "EPS Power",
    legendGroup: "eps",
    color: "#FF6FAF",
    toKw: true,
    fill: false,
    lineWidth: 1.4,
    densify: true,
    showZeroInTooltip: true,
  },
  {
    key: "inv_power",
    label: "Output AC Power",
    legendGroup: "ac",
    color: "#2F6BFF",
    toKw: true,
    fill: false,
    lineWidth: 1.4,
  },
  {
    key: "battery_power",
    label: "Battery Power",
    legendGroup: "battery",
    color: "#F5C542",
    toKw: true,
    fill: false,
    lineWidth: 1.4,
  },
];

function normalizePanelView(view) {
  if (view === "energy") return "energy_analysis";
  if (view === "device") return "device_new";
  return view;
}

const SETTINGS_NAV = [
  { id: "main", label: "All" },
  { id: "quick", label: "Quick" },
  { id: "schedules", label: "Schedule" },
  { id: "workmode", label: "Work mode" },
  { id: "pv", label: "PV" },
  { id: "solcast", label: "Solcast" },
  { id: "glow", label: "Glow meter" },
  { id: "tariff", label: "Tariff" },
  { id: "smart", label: "SmartCharge" },
  { id: "storm", label: "StormSafe" },
  { id: "control", label: "Control" },
];

const DEFAULT_PV_STRING = {
  enabled: true,
  panel_count: 6,
  watts_per_panel: 450,
  efficiency_factor: 100,
  tilt: 25,
  azimuth: 180,
  installation_cost_minor: 0,
};

const DEFAULT_PV_CONFIG = {
  annual_degradation_pct: 2,
  pv1: { ...DEFAULT_PV_STRING },
  pv2: {
    enabled: false,
    panel_count: 1,
    watts_per_panel: 450,
    efficiency_factor: 100,
    tilt: 25,
    azimuth: 180,
  },
};

const DEFAULT_TARIFF = {
  kind: "static",
  currency: "GBP",
  import_source: "schedule",
  import_entity: "",
  import_p_per_kwh: 0,
  export_source: "schedule",
  export_entity: "",
  export_p_per_kwh: 0,
  standing_source: "plugin",
  standing_entity: "",
  standing_charge_p_per_day: 0,
  schedule: {
    hours: Array(24).fill(0),
    bands: [
      { import_p_per_kwh: 0, export_p_per_kwh: 0 },
      { import_p_per_kwh: 0, export_p_per_kwh: 0 },
      { import_p_per_kwh: 0, export_p_per_kwh: 0 },
      { import_p_per_kwh: 0, export_p_per_kwh: 0 },
    ],
  },
  dynamic: {
    enabled: false,
    provider: "",
    source: "native",
    account_number: "",
    import_mpan: "",
    export_mpan: "",
    import_entity: "",
    export_entity: "",
  },
};

/** Four schedule band colours (00:00–24:00 editor). */
const TARIFF_BAND_COLORS = ["#43A047", "#1E88E5", "#FB8C00", "#E53935"];
const TARIFF_BAND_LABELS = ["Band A", "Band B", "Band C", "Band D"];

/** ISO 4217 codes for tariff settings (must match const.py TARIFF_CURRENCIES). */
const TARIFF_CURRENCIES = {
  AUD: { name: "Australian dollar", decimals: 2 },
  BGN: { name: "Bulgarian lev", decimals: 2 },
  BRL: { name: "Brazilian real", decimals: 2 },
  CAD: { name: "Canadian dollar", decimals: 2 },
  CHF: { name: "Swiss franc", decimals: 2 },
  CNY: { name: "Chinese yuan", decimals: 2 },
  CZK: { name: "Czech koruna", decimals: 2 },
  DKK: { name: "Danish krone", decimals: 2 },
  EUR: { name: "Euro", decimals: 2 },
  GBP: { name: "British pound", decimals: 2 },
  HKD: { name: "Hong Kong dollar", decimals: 2 },
  HUF: { name: "Hungarian forint", decimals: 2 },
  ILS: { name: "Israeli new shekel", decimals: 2 },
  INR: { name: "Indian rupee", decimals: 2 },
  JPY: { name: "Japanese yen", decimals: 0 },
  KRW: { name: "South Korean won", decimals: 0 },
  MXN: { name: "Mexican peso", decimals: 2 },
  NOK: { name: "Norwegian krone", decimals: 2 },
  NZD: { name: "New Zealand dollar", decimals: 2 },
  PLN: { name: "Polish zloty", decimals: 2 },
  RON: { name: "Romanian leu", decimals: 2 },
  SEK: { name: "Swedish krona", decimals: 2 },
  SGD: { name: "Singapore dollar", decimals: 2 },
  TRY: { name: "Turkish lira", decimals: 2 },
  USD: { name: "US dollar", decimals: 2 },
  ZAR: { name: "South African rand", decimals: 2 },
};

function normalizeTariffCurrency(code) {
  const raw = String(code || "GBP").toUpperCase().trim().slice(0, 3);
  return TARIFF_CURRENCIES[raw] ? raw : "GBP";
}

function tariffCurrencyMeta(code) {
  return TARIFF_CURRENCIES[normalizeTariffCurrency(code)] || TARIFF_CURRENCIES.GBP;
}

function tariffMinorFactor(code) {
  const decimals = tariffCurrencyMeta(code).decimals;
  return decimals > 0 ? 10 ** decimals : 1;
}

function minorToMajor(minor, code) {
  const factor = tariffMinorFactor(code);
  const decimals = tariffCurrencyMeta(code).decimals;
  return Math.round((parseTariffRate(minor) / factor) * 10 ** Math.max(decimals, 4)) / 10 ** Math.max(decimals, 4);
}

function majorToMinor(major, code) {
  return Math.round(parseTariffRate(major) * tariffMinorFactor(code) * 10000) / 10000;
}

function tariffRateInputStep(code) {
  const d = tariffCurrencyMeta(code).decimals;
  if (d === 0) return "1";
  if (d === 2) return "0.01";
  return "0.0001";
}

const PV_EFFICIENCY_FACTOR_URL = "https://kb.solcast.com.au/what-is-the-efficiency-factor";
const SOLCAST_API_DOCS_URL = "https://docs.solcast.com.au/";
const SOLCAST_HOBBYIST_URL = "https://solcast.com/free-rooftop-solar-forecasting";
const GLOW_DOCS_URL = "https://docs.glowmarkt.com/GlowmarktAPIDataRetrievalDocumentationIndividualUserForBright.pdf";
const GLOW_MQTT_INTEGRATION_URL = "https://github.com/megakid/ha_hildebrand_glow_ihd_mqtt";
const SOLCAST_ACCOUNT_LOCATIONS_URL = "https://toolkit.solcast.com.au/account/locations";
const OCTOPUS_API_DOCS_URL = "https://octopus.energy/dashboard/new/accounts/personal-access-token/";
const SOLCAST_COORD_DECIMALS = 4;

/** Fox hub-and-spoke flow (viewBox 0 0 1024 1017). Anchors sync with tools/compose_flow_layers.py */
/** Hub on side/front wall corner — user-tuned v0.8.104 (was y=726). */
const FOX_FLOW_HUB = { x: 536, y: 766 };

const FOX_FLOW_PATHS = {
  "solar-aio": "M 388 422 L 388 696",
  "grid-hub": "M 228 848 L 536 848 L 536 766",
  "hub-grid": "M 536 766 L 536 848 L 228 848",
  "aio-hub": "M 404 724 L 536 766",
  "hub-aio": "M 536 766 L 404 724",
  "hub-home": "M 536 766 L 636 738",
};
const FOX_FLOW_HUB_SPOKES = new Set(["solar-aio", "aio-hub", "hub-aio", "hub-home", "grid-hub", "hub-grid"]);

const FLOW_PATHS_VER = "flow-comet-v3";
const PANEL_VERSION = "0.9.248";
/** Bump when Device Analysis DOM/CSS layout changes (forces full re-render). */
const DEVICE_NEW_ANALYSIS_LAYOUT_VER = "11";
/** Extra .main max-width on Device view ≈ sidebar column (280px) + layout gap (16px). */
const DEVICE_NEW_MAIN_WIDTH_EXTRA_PX = 296;
/** Max wait for recorder/history websocket round-trips (prevents infinite loading spinners). */
const HA_WS_TIMEOUT_MS = 90000;
const PANEL_BUILD_FALLBACK = PANEL_VERSION;
const PANEL_SYNC_STORAGE_KEY = "foxess_plant_panel_sync_build";

/** MDI menu — opens Home Assistant sidebar via hass-toggle-menu. */
const HA_MENU_ICON_SVG =
  '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M3 6h18v2H3V6m0 5h18v2H3v-2m0 5h18v2H3v-2z"/></svg>';

/** Manifest version from cached module filename (foxess-plant-panel.v0_8_109.{hash}.js). */
function panelVersionFromModuleUrl() {
  const re = /foxess-plant-panel\.v(\d+)_(\d+)_(\d+)\.[a-f0-9]+\.js/i;
  const urls = [];
  if (typeof import.meta !== "undefined" && import.meta.url) urls.push(import.meta.url);
  for (const script of document.getElementsByTagName("script")) {
    if (script.src) urls.push(script.src);
  }
  for (const src of urls) {
    const m = String(src).match(re);
    if (m) return `${m[1]}.${m[2]}.${m[3]}`;
  }
  return null;
}

function panelElementTag() {
  const ver = panelVersionFromModuleUrl() || PANEL_VERSION;
  return `foxess-plant-panel-${String(ver).replace(/\./g, "_")}`;
}

/** HA scoped registry: one tag, one class — reusing the constructor for multiple tags throws. */
function registerFoxessPlantPanel() {
  const tag = panelElementTag();
  if (customElements.get(tag)) return;
  try {
    customElements.define(tag, FoxessPlantPanel);
  } catch (err) {
    console.error(`FoxESS Plant: could not register <${tag}>`, err);
  }
}
const FLOW_STROKE = { base: 3, underlay: 4, active: 5, hubActive: 6, hubR: 6.5 };
/** Idle pipe track — darker on day (white walls), lighter on night (black scene). */
const FLOW_PIPE_STROKE = { day: "#5E6A78", night: "#9AA8B8" };
/** Pale underlay beneath animated hub spokes so dashes do not sit on dark gaps. */
const FLOW_PIPE_UNDERLAY = { day: "#EEF1F5", night: "#9AA4B0" };
/** Active flow colours — inline on SVG paths for reliable rendering in HA shadow DOM. */
const FLOW_ACTIVE_STROKE = {
  solar: "#FFC400",
  grid: "#3D9AFF",
  export: "#C06AFF",
  battery: "#00FF66",
  home: "#00FF66",
  hub: "#00FF66",
};
const FLOW_COMET = {
  pathLen: 100,
  pulse: 12,
  hubHeadSw: 3.5,
  headSw: 3,
  glowScale: 2.35,
  dur: 1.75,
  durSolar: 1.55,
};
const FLOW_SCENE_PV_THRESHOLD_W = 40;
const FLOW_SCENE_CANVAS_BG_DARK = "#000000";
const FLOW_SCENE_CANVAS_BG_LIGHT = "#ffffff";
const FLOW_SCENE_ASSET_VER = 48;

const FLOW_SCENE_BG_THEMES = new Set([
  "day_light",
  "day_dark",
  "night_light",
  "night_dark",
]);

function flowPipeStroke(isNight) {
  return isNight ? FLOW_PIPE_STROKE.night : FLOW_PIPE_STROKE.day;
}

function flowPipeUnderlay(isNight) {
  return isNight ? FLOW_PIPE_UNDERLAY.night : FLOW_PIPE_UNDERLAY.day;
}

function flowActiveStroke(cls) {
  if (cls === "flow-solar") return FLOW_ACTIVE_STROKE.solar;
  if (cls === "flow-grid") return FLOW_ACTIVE_STROKE.grid;
  if (cls === "flow-export") return FLOW_ACTIVE_STROKE.export;
  if (cls === "flow-home-line") return FLOW_ACTIVE_STROKE.home;
  return FLOW_ACTIVE_STROKE.battery;
}

/** Hub spokes share one flow class + one pipe colour so segments match (incl. hub-home). */
function flowHubSpokeCls(id, gridExporting) {
  if (id.startsWith("solar")) return "flow-solar";
  if (id.includes("grid")) return gridExporting && id === "hub-grid" ? "flow-export" : "flow-grid";
  return "flow-battery";
}

/** Single Fox-style comet pulse (one blob + soft glow, same phase — not two dashes). */
function flowCometPaths({ d, cls = "", headSw, stroke, reverse = false }) {
  const L = FLOW_COMET.pathLen;
  const pulse = FLOW_COMET.pulse;
  const gap = L - pulse;
  const rev = reverse ? " reverse" : "";
  const clsAttr = cls ? ` ${cls}` : "";
  const glowSw = (headSw * FLOW_COMET.glowScale).toFixed(2);
  const dash = `${pulse} ${gap}`;
  return (
    `<path class="flow-comet flow-comet-glow${clsAttr}${rev}" d="${d}" pathLength="${L}" stroke="${stroke}" stroke-width="${glowSw}" stroke-dasharray="${dash}" stroke-linecap="round"></path>` +
    `<path class="flow-comet flow-comet-pulse${clsAttr}${rev}" d="${d}" pathLength="${L}" stroke="${stroke}" stroke-width="${headSw}" stroke-dasharray="${dash}" stroke-linecap="round"></path>`
  );
}

function flowIdlePipeMarkup(d, isNight) {
  const stroke = flowPipeStroke(isNight);
  const sw = FLOW_STROKE.hubActive;
  const outline = isNight
    ? ""
    : `<path class="flow-path flow-path-idle-outline" d="${d}" stroke="rgba(28, 36, 48, 0.55)" stroke-width="${sw + 2}" stroke-linecap="round" stroke-linejoin="round"></path>`;
  return (
    outline +
    `<path class="flow-path flow-path-idle" d="${d}" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round"></path>`
  );
}

function renderFlowScenePaths({ lines, activeIds, gridExporting, isNight }) {
  const idleHtml = Object.entries(FOX_FLOW_PATHS)
    .map(([id, d]) => (FOX_FLOW_HUB_SPOKES.has(id) ? flowIdlePipeMarkup(d, isNight) : ""))
    .join("");
  const activeHtml = Object.entries(FOX_FLOW_PATHS)
    .map(([id, d]) => {
      const line = lines.find((l) => l.id === id);
      if (!line || !FOX_FLOW_HUB_SPOKES.has(id)) return "";
      const cls = flowHubSpokeCls(id, gridExporting);
      if (!activeIds.has(id)) return "";
      return flowPathMarkup({
        d,
        cls,
        role: "flow",
        isNight,
        reverse: !!line?.reverse,
      });
    })
    .join("");
  return idleHtml + activeHtml;
}

/** Stable key — only changes when which pipes are active or scene theme changes (not power W). */
function flowSceneStructureKey(lines, gridExporting, isNight, bgTheme, haUiDark) {
  const active = lines
    .map((l) => `${l.id}${l.reverse ? ":r" : ""}`)
    .sort()
    .join(",");
  return `${bgTheme}|${haUiDark ? "haD" : "haL"}|${isNight ? "n" : "d"}|${gridExporting ? "x" : "i"}|${active}`;
}

function renderFlowSceneSvgInner({ lines, activeIds, gridExporting, isNight }) {
  const pathsHtml = renderFlowScenePaths({ lines, activeIds, gridExporting, isNight });
  const hubActive = lines.some((l) => l.id.includes("hub"));
  const hubFill = hubActive ? FLOW_ACTIVE_STROKE.battery : flowPipeStroke(isNight);
  return `${pathsHtml}<circle class="flow-hub-dot ${hubActive ? "active" : ""}" cx="${FOX_FLOW_HUB.x}" cy="${FOX_FLOW_HUB.y}" r="${FLOW_STROKE.hubR}" fill="${hubFill}"/>`;
}

/** role: flow = comet pulse (idle pipes drawn separately via renderFlowScenePaths). */
function flowPathMarkup({ d, cls = "", role = "flow", isNight = false, reverse = false }) {
  const isHubFlow = cls === "flow-battery";
  const stroke = flowActiveStroke(cls);
  const headSw = isHubFlow ? FLOW_COMET.hubHeadSw : FLOW_COMET.headSw;
  return flowCometPaths({ d, cls, headSw, stroke, reverse });
}

const DEFAULT_PERIODS = [
  { enable_force_charge: false, enable_charge_from_grid: false, start: "00:00", end: "00:00" },
  { enable_force_charge: false, enable_charge_from_grid: false, start: "00:00", end: "00:00" },
];

/** Display title + hint per FoxESS work_mode select option (key = entity option string). */
const WORK_MODE_META = {
  "Self Use": {
    title: "Self Use",
    hint: "Optimised for self consumption, reduce reliance on grid electricity.",
  },
  "Feed-in First": {
    title: "Feed-in Priority",
    hint: "Prioritises electricity sales to generate income.",
  },
  "Feed-in Priority": {
    title: "Feed-in Priority",
    hint: "Prioritises electricity sales to generate income.",
  },
  "Back-up": {
    title: "Back-up",
    hint: "Tailored for areas with unstable power grids. Reserves SOC to prevent power outages.",
  },
  "Back Up": {
    title: "Back-up",
    hint: "Tailored for areas with unstable power grids. Reserves SOC to prevent power outages.",
  },
  "Peak Shaving": {
    title: "Peak Shaving",
    hint: "Implements energy management strategies by setting battery SOC and import limits according to production schedules, reducing overall energy consumption during peak periods.",
  },
  "Force Charge": {
    title: "Force Charge",
    hint: "Active remote force-charge session.",
  },
  "Force Discharge": {
    title: "Force Discharge",
    hint: "Active remote force-discharge session.",
  },
};

const FOX_WORK_MODE_ICONS = {"selfUse": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 48 48\" fill=\"none\"><rect width=\"48\" height=\"48\" rx=\"10\" fill=\"#FA8C16\" /><path d=\"M24.9987 24.2216H27.9987L22.9987 31.9989V26.4442H19.9987L24.9987 18.6656V24.2216Z\" fill=\"white\" /><path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M23.1016 10.1474C23.61 9.68526 24.3874 9.68526 24.8958 10.1474L38.6654 22.6656H34.6654V34.6656C34.6654 35.402 34.0684 35.9989 33.332 35.9989H14.6654C13.929 35.9989 13.332 35.402 13.332 34.6656V22.6656H9.33203L23.1016 10.1474ZM15.9987 20.2099V33.3322H31.9987V20.2099L23.9987 12.9364L15.9987 20.2099Z\" fill=\"white\" /></svg>", "feedInPriority": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 48 48\" fill=\"none\"><rect width=\"48\" height=\"48\" rx=\"10\" fill=\"#894BFC\" /><path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M27.2427 10.0007C26.6165 10.6391 26.1184 11.4025 25.7883 12.2507H20.8534L19.7974 16.0007H25.468C25.6131 16.7158 25.8742 17.3886 26.2284 18.0007H19.2349L17.8286 23.0007H30.1737L29.576 20.877C30.3276 21.1707 31.1449 21.3339 32.0005 21.334C32.0138 21.334 32.0276 21.3328 32.0409 21.3327L32.5109 23.0007H35.5005C35.7766 23.0007 36.0005 23.2245 36.0005 23.5007V24.5007C36.0005 24.7768 35.7766 25.0006 35.5005 25.0007H33.0747L36.6476 37.7012C36.7072 37.9142 36.4811 38.0939 36.287 37.9876L24.0005 31.2598L11.714 37.9876C11.5201 38.0933 11.2941 37.9139 11.3534 37.7012L14.9276 25.0007H12.5005C12.2246 25.0004 12.0005 24.7766 12.0005 24.5007V23.5007C12.0005 23.2247 12.2246 23.0009 12.5005 23.0007H15.4901L16.8976 18.0007H15.5005C15.2246 18.0004 15.0005 17.7766 15.0005 17.5007V16.5007C15.0005 16.2247 15.2246 16.0009 15.5005 16.0007H17.4601L18.9953 10.5475C19.0863 10.2242 19.3808 10.0008 19.7167 10.0007H27.2427ZM14.8091 33.7285L21.6581 29.9772L16.6385 27.2285L14.8091 33.7285ZM26.343 29.9772L33.1932 33.7285L31.3638 27.2285L26.343 29.9772ZM17.2635 25.0059L24.0005 28.6947L30.7388 25.0059L30.7375 25.0007H17.2648L17.2635 25.0059Z\" fill=\"white\" /><path d=\"M32.0005 13.334H37.3338V16.0007H32.0005V20.0007L26.6672 14.6673L32.0005 9.33398V13.334Z\" fill=\"white\" /></svg>", "backUp": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 48 48\" fill=\"none\"><rect width=\"48\" height=\"48\" rx=\"10\" fill=\"#08979C\" /><path d=\"M25.3346 23.9993H29.3346L22.668 33.3327V26.666H18.668L25.3346 17.3327V23.9993ZM22.668 15.9993H17.3346V34.666H30.668V15.9993H25.3346V13.3327H22.668V15.9993ZM20.0013 13.3327V11.9993C20.0013 11.263 20.5983 10.666 21.3346 10.666H26.668C27.4044 10.666 28.0013 11.263 28.0013 11.9993V13.3327H32.0013C32.7377 13.3327 33.3346 13.9296 33.3346 14.666V35.9993C33.3346 36.7357 32.7377 37.3327 32.0013 37.3327H16.0013C15.2649 37.3327 14.668 36.7357 14.668 35.9993V14.666C14.668 13.9296 15.2649 13.3327 16.0013 13.3327H20.0013Z\" fill=\"white\" /></svg>", "peakShaving": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 48 48\" fill=\"none\"><g id=\"Frame 1321316676\"><rect id=\"Rectangle 34625412\" width=\"48\" height=\"48\" rx=\"4\" fill=\"#FC355D\" /><g id=\"Frame 1321316322\"><g id=\"Group 1000004358\"><path id=\"Vector 480\" d=\"M12.6494 22.5198C12.899 22.5198 13.473 22.2442 13.7724 21.1419C14.1468 19.7639 15.2698 16.0893 16.3929 21.6012C16.4417 21.821 17.3211 25.1092 18.5159 22.1977C19.7106 19.2862 19.8921 18.9575 21.1913 22.3093C22.2306 24.9907 22.7792 22.718 22.9236 21.2465C22.9997 20.087 23.1033 18.8083 23.2314 17.5844M35.2209 22.5198C34.8662 22.7079 34.3616 22.6402 33.9039 22.4954C33.3174 22.3099 32.9696 21.7466 32.8761 21.1386C32.2139 16.8336 30.7403 11.14 29.1478 16.9445C27.0039 24.7587 26.4404 21.7384 26.2566 20.9341C26.1296 19.6614 26.0048 18.5496 25.8824 17.5844\" stroke=\"white\" stroke-width=\"1.5\" stroke-linecap=\"round\" /><path id=\"Vector 479\" d=\"M23.3679 15.9402C23.6839 13.4146 24.634 9.44125 25.8455 15.8182\" stroke=\"white\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-dasharray=\"3 3\" /><path id=\"Vector 481\" d=\"M12.3613 17.8438H33.6387C34.7432 17.8438 35.6387 18.7392 35.6387 19.8437V29.4103C35.6387 30.5149 34.7432 31.4103 33.6387 31.4103H23.0051\" stroke=\"#FFB8C6\" stroke-width=\"1.5\" stroke-linecap=\"round\" /><rect id=\"Rectangle 24027\" x=\"18.895\" y=\"26.5547\" width=\"9.31278\" height=\"9.06249\" rx=\"1\" fill=\"white\" /><g id=\"Rectangle 24028\"><mask id=\"path-6-inside-1_2095_75746\" fill=\"white\"><rect x=\"20.7388\" y=\"28.9844\" width=\"1.53526\" height=\"4.7414\" rx=\"0.1\" /></mask><rect x=\"20.7388\" y=\"28.9844\" width=\"1.53526\" height=\"4.7414\" rx=\"0.1\" stroke=\"#FC355D\" stroke-width=\"0.4\" mask=\"url(#path-6-inside-1_2095_75746)\" /></g><rect id=\"Rectangle 24029\" x=\"21.1538\" y=\"28.4453\" width=\"0.705239\" height=\"0.363547\" rx=\"0.1\" fill=\"#FC355D\" /><rect id=\"Rectangle 24030\" x=\"20.8098\" y=\"31.25\" width=\"1.39725\" height=\"2.32806\" fill=\"#FC355D\" /><g id=\"Rectangle 24028_2\"><mask id=\"path-9-inside-2_2095_75746\" fill=\"white\"><rect x=\"22.822\" y=\"28.9844\" width=\"1.53526\" height=\"4.7414\" rx=\"0.1\" /></mask><rect x=\"22.822\" y=\"28.9844\" width=\"1.53526\" height=\"4.7414\" rx=\"0.1\" stroke=\"#FC355D\" stroke-width=\"0.4\" mask=\"url(#path-9-inside-2_2095_75746)\" /></g><rect id=\"Rectangle 24029_2\" x=\"23.2334\" y=\"28.4453\" width=\"0.705239\" height=\"0.363547\" rx=\"0.1\" fill=\"#FC355D\" /><rect id=\"Rectangle 24030_2\" x=\"22.8855\" y=\"29.8047\" width=\"1.39725\" height=\"3.77386\" fill=\"#FC355D\" /><g id=\"Rectangle 24028_3\"><mask id=\"path-12-inside-3_2095_75746\" fill=\"white\"><rect x=\"24.8977\" y=\"28.9844\" width=\"1.53526\" height=\"4.7414\" rx=\"0.1\" /></mask><rect x=\"24.8977\" y=\"28.9844\" width=\"1.53526\" height=\"4.7414\" rx=\"0.1\" stroke=\"#FC355D\" stroke-width=\"0.4\" mask=\"url(#path-12-inside-3_2095_75746)\" /></g><rect id=\"Rectangle 24029_3\" x=\"25.3127\" y=\"28.4453\" width=\"0.705239\" height=\"0.363547\" rx=\"0.1\" fill=\"#FC355D\" /><rect id=\"Rectangle 24030_3\" x=\"24.9648\" y=\"32.2656\" width=\"1.39725\" height=\"1.31359\" fill=\"#FC355D\" /></g></g></g></svg>", "forceCharge": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 20 20\" fill=\"none\"><g id=\"Frame 272\"><path d=\"M0 2C0 0.895431 0.895431 0 2 0H18C19.1046 0 20 0.895431 20 2V18C20 19.1046 19.1046 20 18 20H2C0.895431 20 0 19.1046 0 18V2Z\" fill=\"#1677FF\" /><g id=\"Icon/ChargeOutline\"><path id=\"vector\" fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M12.5 3.25C12.5 3.11193 12.3881 3 12.25 3H7.82812C7.69005 3 7.57812 3.11193 7.57812 3.25V4H4.25C4.11193 4 4 4.11193 4 4.25V4.875C4 5.01307 4.11193 5.125 4.25 5.125H5V14.9375H4.25C4.11193 14.9375 4 15.0494 4 15.1875V15.8125C4 15.9506 4.11193 16.0625 4.25 16.0625H15.75C15.8881 16.0625 16 15.9506 16 15.8125V15.1875C16 15.0494 15.8881 14.9375 15.75 14.9375H15V5.125H15.75C15.8881 5.125 16 5.01307 16 4.875V4.25C16 4.11193 15.8881 4 15.75 4H12.5V3.25ZM9.5 10.7H7.5L10.5 6.5V9.3H12.5L9.5 13.5V10.7Z\" fill=\"white\" /></g></g></svg>", "forceDischarge": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 20 20\" fill=\"none\"><g id=\"Frame 272\"><path d=\"M0 2C0 0.895431 0.895431 0 2 0H18C19.1046 0 20 0.895431 20 2V18C20 19.1046 19.1046 20 18 20H2C0.895431 20 0 19.1046 0 18V2Z\" fill=\"#894BFC\" /><g id=\"Icon/ChargeOutline\"><path id=\"vector\" fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M12.5 3.25C12.5 3.11193 12.3881 3 12.25 3H7.82812C7.69005 3 7.57812 3.11193 7.57812 3.25V4H4.25C4.11193 4 4 4.11193 4 4.25V4.875C4 5.01307 4.11193 5.125 4.25 5.125H5V14.9375H4.25C4.11193 14.9375 4 15.0494 4 15.1875V15.8125C4 15.9506 4.11193 16.0625 4.25 16.0625H15.75C15.8881 16.0625 16 15.9506 16 15.8125V15.1875C16 15.0494 15.8881 14.9375 15.75 14.9375H15V5.125H15.75C15.8881 5.125 16 5.01307 16 4.875V4.25C16 4.11193 15.8881 4 15.75 4H12.5V3.25ZM9.5 10.7H7.5L10.5 6.5V9.3H12.5L9.5 13.5V10.7Z\" fill=\"white\" /></g></g></svg>"};


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

function workModeMeta(option) {
  const key = String(option ?? "").trim();
  return WORK_MODE_META[key] || { title: key, hint: "" };
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Sidebar-style row: title + subtitle stacked (not inline). */
function renderListButton(attrs, title, subtitle) {
  const parts = ['type="button"', 'class="list-btn"'];
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value != null && value !== "") parts.push(`data-${esc(key)}="${esc(String(value))}"`);
  }
  return `<button ${parts.join(" ")}>
<span class="list-btn-body"><span class="list-btn-title">${esc(title)}</span><span class="list-btn-sub">${esc(subtitle)}</span></span>
<span class="chev" aria-hidden="true">›</span></button>`;
}

function stateNumber(hass, entityId) {
  if (!entityId || !hass?.states) return 0;
  const st = hass.states[entityId];
  if (!st || st.state === "unavailable" || st.state === "unknown") return 0;
  const n = parseFloat(st.state);
  return Number.isFinite(n) ? n : 0;
}

/** Normalise HA power sensors to watts (foxess_modbus uses kW). */
function statePowerWatts(hass, entityId) {
  if (!entityId || !hass?.states) return 0;
  const st = hass.states[entityId];
  if (!st || st.state === "unavailable" || st.state === "unknown") return 0;
  const n = parseFloat(st.state);
  if (!Number.isFinite(n)) return 0;
  const unit = String(st.attributes?.unit_of_measurement ?? "")
    .trim()
    .toLowerCase();
  if (unit === "kw") return n * 1000;
  if (unit === "w") return n;
  // foxess_modbus power entities are kW; very large bare numbers are likely watts
  if (Math.abs(n) > 500) return n;
  return n * 1000;
}

function stateString(hass, entityId) {
  if (!entityId || !hass?.states) return "—";
  const st = hass.states[entityId];
  return st ? st.state : "—";
}

/** Fox app uses single-character ℃ (not ° + C). */
const FOX_UNIT_CELSIUS = "\u2103";
const FOX_UNIT_KW = "kW";
const FOX_UNIT_PERCENT = "%";

function batteryTempMetricParts(hass, entityId) {
  const raw = stateString(hass, entityId);
  if (raw === "—") return { num: "—", unit: "" };
  const n = parseFloat(raw);
  const num = Number.isFinite(n) ? String(n) : raw;
  return { num, unit: FOX_UNIT_CELSIUS };
}

function devicePowerKwMetricParts(watts) {
  const kw = Math.abs(watts) / 1000;
  const num = kw < 10 ? kw.toFixed(3) : kw.toFixed(2);
  return { num, unit: FOX_UNIT_KW };
}

function percentMetricParts(value) {
  return { num: String(Math.round(value)), unit: FOX_UNIT_PERCENT };
}

function renderFoxSummaryMetricValue(num, unit, { valueClass = "fox-device-new-summary-value" } = {}) {
  if (num === "—" || num == null || num === "") {
    return `<strong class="${valueClass}">${esc("—")}</strong>`;
  }
  const unitHtml = unit
    ? `<span class="fox-summary-metric-unit">${esc(unit)}</span>`
    : "";
  return `<strong class="${valueClass}"><span class="fox-summary-metric-num">${esc(String(num))}</span>${unitHtml}</strong>`;
}

/** foxess_modbus inverter_state → Fox app wording (register logic unchanged). */
const FOX_INVERTER_STATE_LABELS = {
  "on grid": "Normal",
  standby: "Checking",
  "off grid": "Off Grid",
  fault: "Fault",
};

function foxInverterStateLabelFromRaw(raw) {
  if (raw == null || raw === "" || raw === "—") return "—";
  if (raw === "unavailable" || raw === "unknown") return raw;
  const mapped = FOX_INVERTER_STATE_LABELS[String(raw).trim().toLowerCase()];
  return mapped ?? raw;
}

function foxInverterStateLabel(hass, plant, plantState) {
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  const entityId = map.inverter_state;
  const raw = entityId ? stateString(hass, entityId) : plantState?.identity?.inverter_state;
  return foxInverterStateLabelFromRaw(raw);
}

function foxWorkModeLabel(hass, plant, plantState) {
  const raw = plantState?.settings?.work_mode;
  if (raw && raw !== "unavailable" && raw !== "unknown") return raw;
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  const entityId = map.work_mode;
  return entityId ? stateString(hass, entityId) : "—";
}

/** PCS model from Modbus register (pcs_model_name), else foxess_modbus device label. */
function plantModelSubtitle(hass, plant, plantState) {
  const fromIdentity = plantState?.identity?.pcs_model_name;
  if (fromIdentity && fromIdentity !== "unavailable" && fromIdentity !== "unknown") {
    return String(fromIdentity).trim();
  }
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  const entityId = map.pcs_model_name;
  if (entityId) {
    const raw = stateString(hass, entityId);
    if (raw && raw !== "—" && raw !== "unavailable" && raw !== "unknown") {
      return String(raw).trim();
    }
  }
  const fallback = plant?.inverter;
  return fallback && fallback !== "—" ? String(fallback).trim() : "—";
}

function foxStatusToneClass(label) {
  const s = String(label || "").toLowerCase();
  if (s === "normal") return "is-normal";
  if (s === "fault") return "is-fault";
  if (s === "checking") return "is-checking";
  if (s === "off grid") return "is-offgrid";
  return "is-default";
}

function foxWorkModeToneClass(label) {
  const s = String(label || "").toLowerCase();
  if (s.includes("self")) return "work-self-use";
  if (s.includes("feed")) return "work-feed-in";
  if (s.includes("back")) return "work-back-up";
  if (s.includes("force charge")) return "work-force-charge";
  if (s.includes("force discharge")) return "work-force-discharge";
  return "work-default";
}

function foxWorkModeDisplay(label) {
  const s = String(label || "").trim();
  const meta = WORK_MODE_META[s];
  if (meta?.title) return meta.title;
  if (s.toLowerCase() === "self use") return "Self Use";
  return s;
}

function normalizePvString(raw, defaults) {
  const base = defaults || DEFAULT_PV_STRING;
  const src = raw && typeof raw === "object" ? raw : {};
  let panelCount = parseInt(src.panel_count, 10);
  if (!Number.isFinite(panelCount)) panelCount = base.panel_count;
  panelCount = Math.max(1, Math.min(12, panelCount));
  let watts = parseInt(src.watts_per_panel, 10);
  if (!Number.isFinite(watts)) watts = base.watts_per_panel;
  watts = Math.max(100, Math.min(1000, watts));
  let eff = parseFloat(src.efficiency_factor);
  if (!Number.isFinite(eff)) eff = base.efficiency_factor;
  eff = Math.max(1, Math.min(100, eff));
  let tilt = parseInt(src.tilt, 10);
  if (!Number.isFinite(tilt)) tilt = base.tilt ?? 25;
  tilt = Math.max(0, Math.min(90, tilt));
  let azimuth = parseInt(src.azimuth, 10);
  if (!Number.isFinite(azimuth)) azimuth = base.azimuth ?? 180;
  azimuth = Math.max(0, Math.min(359, azimuth));
  let installationCostMinor = parseFloat(src.installation_cost_minor);
  if (!Number.isFinite(installationCostMinor)) installationCostMinor = base.installation_cost_minor ?? 0;
  installationCostMinor = Math.max(0, Math.min(99_999_999, installationCostMinor));
  return {
    enabled: Boolean(src.enabled ?? base.enabled),
    panel_count: panelCount,
    watts_per_panel: watts,
    efficiency_factor: eff,
    tilt,
    azimuth,
    installation_cost_minor: installationCostMinor,
  };
}

function pvConfigCurrency(plantState, tariffDraft) {
  if (tariffDraft?.currency) return normalizeTariffCurrency(tariffDraft.currency);
  return tariffCurrencyFromTariff(plantState?.tariff);
}

function normalizePvConfig(raw) {
  const src = raw && typeof raw === "object" ? raw : {};
  let annualDegradation = parseFloat(src.annual_degradation_pct);
  if (!Number.isFinite(annualDegradation)) annualDegradation = DEFAULT_PV_CONFIG.annual_degradation_pct;
  annualDegradation = Math.max(0, Math.min(10, annualDegradation));
  return {
    annual_degradation_pct: annualDegradation,
    pv1: normalizePvString(src.pv1, DEFAULT_PV_CONFIG.pv1),
    pv2: normalizePvString(src.pv2, DEFAULT_PV_CONFIG.pv2),
  };
}

function pvInstallationDate(plantState, solcastDraft) {
  const raw = String(
    solcastDraft?.installation_date ?? plantState?.solcast?.installation_date ?? ""
  ).trim();
  return normalizeSolcastInstallationDateInput(raw) || "";
}

function monthsSincePvInstallation(installDateStr, refDate = new Date()) {
  const normalized = normalizeSolcastInstallationDateInput(installDateStr);
  if (!normalized) return null;
  const parts = normalized.split("-").map((x) => parseInt(x, 10));
  const install = new Date(parts[0], parts[1] - 1, parts[2]);
  if (Number.isNaN(install.getTime()) || install > refDate) return 0;
  let months =
    (refDate.getFullYear() - install.getFullYear()) * 12 +
    (refDate.getMonth() - install.getMonth());
  if (refDate.getDate() < install.getDate()) months -= 1;
  return Math.max(0, months);
}

/** Solcast-style age derating: start at 100% and subtract annual loss pro-rated by month. */
function computePvEfficiencyFromInstall(installDateStr, annualDegradationPct = 2) {
  const months = monthsSincePvInstallation(installDateStr);
  if (months == null) return null;
  const rate = Math.max(0, Math.min(10, Number(annualDegradationPct) || 0));
  const lossPct = rate * (months / 12);
  const efficiency = Math.round(100 - lossPct);
  return Math.max(1, Math.min(100, efficiency));
}

function syncPvDraftEfficiencyFromInstall(pvDraft, plantState, solcastDraft) {
  const installDate = pvInstallationDate(plantState, solcastDraft);
  if (!installDate || !pvDraft) return false;
  const efficiency = computePvEfficiencyFromInstall(
    installDate,
    pvDraft.annual_degradation_pct ?? DEFAULT_PV_CONFIG.annual_degradation_pct
  );
  if (efficiency == null) return false;
  if (pvDraft.pv1) pvDraft.pv1.efficiency_factor = efficiency;
  if (pvDraft.pv2) pvDraft.pv2.efficiency_factor = efficiency;
  return true;
}

function formatPvEfficiencyAgeHint(installDateStr, annualDegradationPct) {
  const months = monthsSincePvInstallation(installDateStr);
  if (months == null) return "";
  const years = Math.floor(months / 12);
  const remMonths = months % 12;
  const ageParts = [];
  if (years) ageParts.push(`${years} year${years === 1 ? "" : "s"}`);
  if (remMonths) ageParts.push(`${remMonths} month${remMonths === 1 ? "" : "s"}`);
  const ageLabel = ageParts.length ? ageParts.join(" ") : "0 months";
  const rate = Number(annualDegradationPct) || 0;
  return `Auto-calculated from installation date ${installDateStr} (${ageLabel} · ${months} months) at ${rate}% loss per year.`;
}

function pvStringSummary(cfg) {
  if (!cfg?.enabled) return "Off";
  const kw = (cfg.panel_count * cfg.watts_per_panel) / 1000;
  return `${cfg.panel_count} panels · ${cfg.watts_per_panel} W · ${kw.toFixed(2)} kW · ${cfg.tilt}°/${cfg.azimuth}°`;
}

/** Effective DC kW cap from PV configuration (panels × W × efficiency). */
function pvStringEffectiveMaxKw(cfg) {
  if (!cfg?.enabled) return 0;
  const dcW = cfg.panel_count * cfg.watts_per_panel * (cfg.efficiency_factor / 100);
  return Math.max(0.01, dcW / 1000);
}

function enabledPvStrings(pvConfig) {
  const cfg = normalizePvConfig(pvConfig);
  const out = [];
  if (cfg.pv1?.enabled) out.push({ key: "pv1", label: "PV1 Power", cfg: cfg.pv1 });
  if (cfg.pv2?.enabled) out.push({ key: "pv2", label: "PV2 Power", cfg: cfg.pv2 });
  return out;
}

function parseSolcastCoordinateInput(raw) {
  const v = parseFloat(String(raw ?? "").trim());
  return Number.isFinite(v) ? v : null;
}

function normalizeSolcastCoordinateInput(raw) {
  const v = parseSolcastCoordinateInput(raw);
  if (v == null) return null;
  const factor = 10 ** SOLCAST_COORD_DECIMALS;
  return Math.round(v * factor) / factor;
}

function normalizeSolcastInstallationDateInput(raw) {
  const v = String(raw ?? "").trim();
  if (!v) return null;
  const iso = v.length >= 10 ? v.slice(0, 10) : v;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
  const parts = iso.split("-").map((x) => parseInt(x, 10));
  if (parts.length !== 3 || parts.some((n) => !Number.isFinite(n))) return null;
  const probe = new Date(parts[0], parts[1] - 1, parts[2]);
  if (
    probe.getFullYear() !== parts[0] ||
    probe.getMonth() !== parts[1] - 1 ||
    probe.getDate() !== parts[2]
  ) {
    return null;
  }
  return iso;
}

function solcastInstallationDateMax() {
  return new Date().toISOString().slice(0, 10);
}

function validateSolcastDraft(draft) {
  if (!draft?.enabled) return null;
  const lat = normalizeSolcastCoordinateInput(draft.latitude);
  const lon = normalizeSolcastCoordinateInput(draft.longitude);
  if (lat == null || lon == null) {
    return "Latitude and longitude are required. Copy them exactly from one of your two registered Solcast hobbyist locations (not Home Assistant coordinates).";
  }
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    return "Latitude must be between -90 and 90; longitude between -180 and 180.";
  }
  const installRaw = String(draft.installation_date ?? "").trim();
  if (installRaw) {
    const install = normalizeSolcastInstallationDateInput(installRaw);
    if (!install) {
      return "Installation date must be YYYY-MM-DD (match your Solcast Home PV system listing).";
    }
    if (install > solcastInstallationDateMax()) {
      return "Installation date cannot be in the future.";
    }
  }
  return null;
}

function solcastEnabledFromLive(sc) {
  const v = sc?.enabled;
  return v === true || v === 1 || v === "1" || v === "true";
}

function formatSolcastTimestamp(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "medium" });
}

function formatSolcastTimeOnly(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function formatSolcastNextFetch(sc) {
  const status = sc?.next_fetch_status;
  if (status === "disabled") return "Off";
  if (!sc?.next_fetch_at) {
    if (status === "outside_window") return "Outside poll window";
    return "—";
  }
  const when = formatSolcastTimestamp(sc.next_fetch_at);
  if (status === "due_now") return `${when} (due now)`;
  if (status === "quota_exhausted") {
    const resetWhen = formatSolcastTimestamp(sc.next_fetch_reset_at || sc.next_fetch_at);
    const pollAt = sc.next_fetch_poll_at;
    const schedule = sc.poll_schedule;
    const sunriseIso = pollAt || schedule?.sunrise;
    if (schedule?.mode === "all_day" || !sunriseIso) {
      return `Quota resets ${resetWhen}`;
    }
    const sunriseWhen = formatSolcastTimeOnly(sunriseIso);
    return `Quota resets ${resetWhen} · next poll at sunrise (${sunriseWhen})`;
  }
  if (status === "before_sunrise") return `${when} (at sunrise)`;
  if (status === "after_sunset") return `${when} (next sunrise)`;
  return when;
}

function nativeSolcastPvForecastEnabled(plantState) {
  const sc = plantState?.solcast;
  return Boolean(
    solcastEnabledFromLive(sc) &&
    sc?.api_key_set &&
    sc?.coordinates_configured &&
    sc?.hobbyist_sites_resolved &&
    sc?.fetch_pv_forecast !== false
  );
}

/** Chart overlay: use persisted detailed_forecast even before hobbyist bindings re-resolve. */
function statisticsSolcastForecastEnabled(plantState, hass) {
  const sc = plantState?.solcast;
  if (!sc || sc?.fetch_pv_forecast === false) return false;
  if ((sc.forecast_intraday_points?.length ?? 0) >= 2) return true;
  const rows = resolveSolcastDetailedForecast(plantState, hass);
  if (rows.length >= 2) return true;
  if (sc.forecast_persisted && (sc.pv_forecast_periods ?? 0) >= 2) return true;
  if (sc.pv_forecast_available) return true;
  return nativeSolcastPvForecastEnabled(plantState);
}

function solcastDetailedForecastFromHass(hass, plantState) {
  const sc = plantState?.solcast;
  const rows = sc?.detailed_forecast;
  if (Array.isArray(rows) && rows.length >= 2) return rows;
  if (!hass?.states) return Array.isArray(rows) ? rows : [];
  for (const st of Object.values(hass.states)) {
    const attrs = st?.attributes;
    if (!attrs || attrs.source !== "foxess_plant_solcast") continue;
    const df = attrs.detailed_forecast ?? attrs.detailedForecast;
    if (Array.isArray(df) && df.length >= 2) return df;
  }
  return Array.isArray(rows) ? rows : [];
}

function resolveSolcastDetailedForecast(plantState, hass) {
  return solcastDetailedForecastFromHass(hass, plantState);
}

function resolveBestSolcastDetailedRows(primaryState, extraState, hass) {
  const candidates = [
    resolveSolcastDetailedForecast(primaryState, hass),
    extraState ? resolveSolcastDetailedForecast(extraState, hass) : [],
  ];
  return candidates.reduce((best, cur) => (cur.length > best.length ? cur : best), []);
}

function statisticsRangeForDisplay(range, dayOffset = 0) {
  if (!range || dayOffset > 0) return range ?? null;
  const nowMs = Math.min(Date.now(), range.tMax);
  return { ...range, nowMs: Math.max(range.tMin, nowMs) };
}

function forecastHasFuturePoints(points, nowMs) {
  return (
    Array.isArray(points) &&
    points.filter((p) => Number.isFinite(p?.t) && p.t > nowMs + STATISTICS_PERIOD_MS * 0.5).length >= 2
  );
}

/** Solcast 30-min (or API) intervals from detailed_forecast rows. */
function buildSolcastIntervalSeries(rows) {
  if (!Array.isArray(rows) || !rows.length) return [];
  const parsed = rows
    .map((row) => {
      const start = parseSolcastPeriodMs(row.period_start ?? row.period);
      let v = Number(row.pv_estimate ?? row.pv_power_rooftop ?? row.power ?? row.pv_power);
      if (!Number.isFinite(start) || !Number.isFinite(v)) return null;
      if (Math.abs(v) > 50) v /= 1000;
      return { start, v, row };
    })
    .filter(Boolean)
    .sort((a, b) => a.start - b.start);
  const intervals = [];
  for (let i = 0; i < parsed.length; i += 1) {
    const start = parsed[i].start;
    let end = parseSolcastPeriodMs(parsed[i].row?.period_end);
    if (!Number.isFinite(end) || end <= start) {
      end = i + 1 < parsed.length ? parsed[i + 1].start : start + 30 * 60 * 1000;
    }
    if (end > start) intervals.push({ start, end, v: parsed[i].v });
  }
  return intervals;
}

/** kW for the Solcast interval containing *tMs*. */
function solcastKwAtTime(rows, tMs) {
  if (!Number.isFinite(tMs)) return null;
  const intervals = buildSolcastIntervalSeries(rows);
  for (const iv of intervals) {
    if (tMs >= iv.start && tMs < iv.end) return iv.v;
  }
  const last = intervals[intervals.length - 1];
  return last && tMs >= last.start ? last.v : null;
}

/** Insert a forecast point at *nowMs* when revision history and future slots do not meet. */
function bridgeForecastGapAtNow(points, nowMs, preferKw, detailedRows) {
  if (!Array.isArray(points) || points.length < 2 || !Number.isFinite(nowMs)) return points || [];
  const sorted = [...points].sort((a, b) => a.t - b.t);
  if (sorted.some((p) => Math.abs(p.t - nowMs) <= STATISTICS_PERIOD_MS * 0.6)) return sorted;

  const lastBefore = [...sorted].filter((p) => p.t <= nowMs).pop();
  const firstAfter = sorted.find((p) => p.t > nowMs);
  if (!firstAfter) return sorted;

  const gap = firstAfter.t - (lastBefore?.t ?? nowMs);
  if (gap <= STATISTICS_PERIOD_MS * 1.5) return sorted;

  let v = Number.isFinite(preferKw) ? preferKw : null;
  if (v == null && detailedRows?.length) v = solcastKwAtTime(detailedRows, nowMs);
  if (v == null) v = interpolateSeriesAt(sorted, nowMs, { allowBackfill: true });
  if (v == null && lastBefore) v = lastBefore.v;
  if (v == null) v = firstAfter.v;
  if (!Number.isFinite(v)) return sorted;

  const out = sorted.filter((p) => Math.abs(p.t - nowMs) > 500);
  out.push({ t: nowMs, v });
  return out.sort((a, b) => a.t - b.t);
}

function mergeForecastPointsWithFuture(intradayPts, detailedPts, nowMs) {
  if (!Array.isArray(intradayPts) || intradayPts.length < 2) {
    return Array.isArray(detailedPts) && detailedPts.length >= 2 ? detailedPts : intradayPts || [];
  }
  if (forecastHasFuturePoints(intradayPts, nowMs)) return intradayPts;
  if (!Array.isArray(detailedPts) || detailedPts.length < 2) return intradayPts;
  const future = detailedPts.filter((p) => p.t >= nowMs - STATISTICS_PERIOD_MS);
  if (!future.length) return intradayPts;
  const merged = intradayPts.filter((p) => p.t <= nowMs);
  const lastPast = merged[merged.length - 1];
  for (const p of future) {
    if (!lastPast || p.t > lastPast.t) merged.push(p);
  }
  return merged.length >= 2 ? merged : intradayPts;
}

function filterStatisticsForecastServerPoints(serverPoints, range) {
  if (!Array.isArray(serverPoints) || !range) return [];
  return serverPoints
    .filter(
      (p) =>
        Number.isFinite(p?.t) &&
        Number.isFinite(p?.v) &&
        p.t >= range.tMin &&
        p.t <= range.tMax
    )
    .map((p) => ({ t: p.t, v: p.v }))
    .sort((a, b) => a.t - b.t);
}

function forecastRevisionPastPoints(plantState, forecastState, range, nowMs, fallbackPoints) {
  let intraday = solcastIntradayForecastPoints(plantState, range);
  if (forecastState) {
    const extra = solcastIntradayForecastPoints(forecastState, range);
    if (extra.length > intraday.length) intraday = extra;
  }
  let past = intraday.filter((p) => Number.isFinite(p.t) && p.t <= nowMs);
  if (past.length < 2 && Array.isArray(fallbackPoints) && fallbackPoints.length >= 2) {
    const fb = fallbackPoints.filter((p) => Number.isFinite(p.t) && p.t <= nowMs);
    if (fb.length >= 2) past = fb;
  }
  return past;
}

/** Keep revision past (solid) and future tail from a full client/server series. */
function stitchForecastPastWithFutureTail(pastPts, tailPts, nowMs) {
  const past = (pastPts || [])
    .filter((p) => Number.isFinite(p.t) && p.t <= nowMs)
    .sort((a, b) => a.t - b.t);
  if (past.length < 2) return tailPts?.length >= 2 ? tailPts : past;
  const futureGrace = nowMs + STATISTICS_PERIOD_MS * 0.5;
  const futureTail = (tailPts || []).filter((p) => Number.isFinite(p.t) && p.t > futureGrace);
  const tail = (tailPts || []).filter((p) => Number.isFinite(p.t) && p.t >= nowMs - STATISTICS_PERIOD_MS);
  if (!tail.length && futureTail.length < 2) return past;
  const merged = [...past];
  const lastPast = merged[merged.length - 1];
  const append = futureTail.length >= 2 ? futureTail : tail;
  for (const p of append) {
    if (!lastPast || p.t > lastPast.t) merged.push(p);
  }
  return merged.length >= 2 ? merged : past;
}

function statisticsForecastPastBase(fPoints, revisionPast, nowMs) {
  const past = (fPoints || []).filter((p) => Number.isFinite(p.t) && p.t <= nowMs);
  if (past.length >= 2) return past;
  return revisionPast.length >= 2 ? revisionPast : past;
}

function buildStatisticsForecastPoints(
  range,
  plantState,
  forecastState,
  hass,
  serverPoints,
  { fallbackPoints = null } = {}
) {
  const nowMs = range?.nowMs ?? Date.now();
  const detailedRows = resolveBestSolcastDetailedRows(plantState, forecastState, hass);
  const server = filterStatisticsForecastServerPoints(serverPoints, range);
  const detailed = detailedForecastToChartPoints(detailedRows, range, { extendFuture: true });
  const revisionPast = forecastRevisionPastPoints(
    plantState,
    forecastState,
    range,
    nowMs,
    fallbackPoints
  );

  // Client series carries the future tail (intraday include_future + detailed rows).
  let fPoints = buildForecastSeriesPoints(plantState, range, hass, forecastState);
  if (fPoints.length < 2 && Array.isArray(fallbackPoints) && fallbackPoints.length >= 2) {
    fPoints = fallbackPoints;
  }
  if (fPoints.length >= 2) {
    fPoints = mergeForecastPointsWithFuture(fPoints, detailed, nowMs);
  } else if (detailed.length >= 2) {
    fPoints = detailed;
  } else if (revisionPast.length >= 2) {
    fPoints = revisionPast;
  }

  // Overlay revision history for the solid segment without discarding the future tail.
  if (revisionPast.length >= 2) {
    fPoints = stitchForecastPastWithFutureTail(revisionPast, fPoints, nowMs);
  }

  const forecastPastCount = (pts) =>
    (pts || []).filter((p) => Number.isFinite(p.t) && p.t <= nowMs).length;

  // Server overlay may be future-only when poll history is unavailable.
  if (server.length >= 2) {
    if (!forecastHasFuturePoints(fPoints, nowMs)) {
      fPoints = mergeForecastPointsWithFuture(
        statisticsForecastPastBase(fPoints, revisionPast, nowMs),
        server,
        nowMs
      );
    } else if (forecastPastCount(fPoints) < 2) {
      const basePast = statisticsForecastPastBase(fPoints, revisionPast, nowMs);
      if (basePast.length >= 2) {
        fPoints = stitchForecastPastWithFutureTail(basePast, fPoints, nowMs);
      }
    }
  }

  if (!forecastHasFuturePoints(fPoints, nowMs) && detailed.length >= 2) {
    fPoints = mergeForecastPointsWithFuture(
      statisticsForecastPastBase(fPoints, revisionPast, nowMs),
      detailed,
      nowMs
    );
  }

  const nowKw =
    plantState?.solcast?.pv_power_now_kw ?? forecastState?.solcast?.pv_power_now_kw;
  return bridgeForecastGapAtNow(
    fPoints,
    nowMs,
    nowKw != null ? Number(nowKw) : null,
    detailedRows
  );
}

function mergeStatisticsForecastSeries(
  series,
  range,
  plantState,
  hass,
  { dayOffset = 0, fallbackPoints = null, forecastState = null, serverForecastPoints = null } = {}
) {
  if (!Array.isArray(series) || !range) return series;
  const without = series.filter((s) => s.id !== "forecast");
  if (dayOffset > 0) {
    const existing = series.find((s) => s.id === "forecast");
    return existing?.points?.length >= 2 ? series : without;
  }
  const fPoints = buildStatisticsForecastPoints(range, plantState, forecastState, hass, serverForecastPoints, {
    fallbackPoints,
  });
  if (fPoints.length < 2) {
    const existing = series.find((s) => s.id === "forecast");
    if (existing?.points?.length >= 2) return series;
    const serverOnly = filterStatisticsForecastServerPoints(serverForecastPoints, range);
    if (serverOnly.length >= 2) {
      return [
        ...without,
        { id: "forecast", ...FORECAST_CHART_STYLE, connectGaps: true, points: serverOnly },
      ];
    }
    return without;
  }
  return [
    ...without,
    { id: "forecast", ...FORECAST_CHART_STYLE, connectGaps: true, points: fPoints },
  ];
}

function formatLocalDayKey(dayDate) {
  const y = dayDate.getFullYear();
  const m = String(dayDate.getMonth() + 1).padStart(2, "0");
  const d = String(dayDate.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

async function fetchSolcastStatisticsForecastPoints(hass, plant) {
  if (!hass?.connection || !plant?.entry_id) return [];
  try {
    const res = await hass.connection.sendMessagePromise({
      type: "foxess_plant/solcast_statistics_forecast",
      plant_id: plant.entry_id,
    });
    if (!Array.isArray(res?.points) || res.points.length < 2) return [];
    return res.points
      .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v))
      .map((p) => ({ t: p.t, v: p.v }))
      .sort((a, b) => a.t - b.t);
  } catch {
    return [];
  }
}

async function fetchHistoricalSolcastForecastPoints(hass, plant, dayOffset) {
  if (!hass?.connection || !plant?.entry_id || dayOffset <= 0) return [];
  const day = startOfLocalDay(new Date());
  day.setDate(day.getDate() - dayOffset);
  try {
    const res = await hass.connection.sendMessagePromise({
      type: "foxess_plant/solcast_forecast_intraday",
      plant_id: plant.entry_id,
      day: formatLocalDayKey(day),
    });
    if (!Array.isArray(res?.points) || res.points.length < 2) return [];
    return res.points
      .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v))
      .map((p) => ({ t: p.t, v: p.v }))
      .sort((a, b) => a.t - b.t);
  } catch {
    return [];
  }
}


const FORECAST_ACCURACY_COLORS = {
  actual: "#19D4DE",
  predicted: "#FFD700",
  firstRevision: "rgba(255,215,0,0.42)",
  latestRevision: "#FFD700",
  cloud: "rgba(168,178,198,0.85)",
  cloudFill: "rgba(168,178,198,0.24)",
};

async function fetchPlantList(hass) {
  if (!hass?.connection) return [];
  try {
    const res = await hass.connection.sendMessagePromise({ type: "foxess_plant/plant_list" });
    return Array.isArray(res?.plants) ? res.plants : [];
  } catch {
    return [];
  }
}

async function fetchForecastAccuracyReport(hass, plant, dayOffset = 0) {
  if (!hass?.connection || !plant?.entry_id) return null;
  const day = startOfLocalDay(new Date());
  day.setDate(day.getDate() - dayOffset);
  try {
    return await hass.connection.sendMessagePromise({
      type: "foxess_plant/solcast_forecast_accuracy",
      plant_id: plant.entry_id,
      day: formatLocalDayKey(day),
    });
  } catch (err) {
    const bits = [
      err?.message,
      err?.code,
      err?.error?.message,
      err?.error?.code,
      err?.body?.message,
      typeof err === "string" ? err : "",
    ].filter((b) => b && b !== "Unknown error");
    const msg = bits[0] || "Failed to load forecast accuracy";
    return { error: msg, solcast_enabled: true };
  }
}

function forecastAccuracyRangeFromReport(report, intraday) {
  const day = report?.day ? new Date(`${report.day}T12:00:00`) : new Date();
  const dayStart = startOfLocalDay(day).getTime();
  const win = report?.chart_window;
  const asOf = report?.as_of ? Date.parse(report.as_of) : Date.now();
  let tMin = Number(win?.t_min_ms);
  let tMax = Number(win?.t_max_ms);
  if (!Number.isFinite(tMin)) tMin = dayStart + 6 * 3600000;
  if (!Number.isFinite(tMax)) tMax = dayStart + 20 * 3600000;
  let nowMs = report?.is_today
    ? Math.min(Date.now(), tMax)
    : Math.min(Number.isFinite(asOf) ? asOf : Date.now(), tMax);
  if (report?.is_today) {
    let dataEnd = tMin;
    for (const key of ["actual_power_kw", "predicted_power_kw", "latest_revision_power_kw"]) {
      for (const p of intraday?.[key] || []) {
        if (Number.isFinite(p?.t) && p.t > dataEnd) dataEnd = p.t;
      }
    }
    const endRef = Math.max(dataEnd, nowMs, tMin + 3600000);
    const endCeil = ceilToLocalHourMs(endRef + 3600000);
    tMax = Math.min(tMax, Math.max(endCeil, tMin + 2 * 3600000));
    nowMs = Math.min(Math.max(nowMs, dataEnd), tMax);
  }
  return { tMin, tMax, nowMs, dayStart };
}

function ceilToLocalHourMs(ms) {
  const d = new Date(ms);
  d.setMinutes(0, 0, 0);
  if (ms > d.getTime()) d.setHours(d.getHours() + 1);
  return d.getTime();
}

function buildForecastAccuracySeriesMeta(intraday, { compact = false } = {}) {
  if (!intraday) return [];
  const meta = [];
  const add = (id, label, color, points, yAxis = "kw") => {
    if (!Array.isArray(points) || points.length < 2) return;
    meta.push({
      id,
      label,
      color,
      yAxis,
      points: [...points].sort((a, b) => a.t - b.t),
    });
  };
  add("pv_actual", "PV generation", FORECAST_ACCURACY_COLORS.actual, intraday.actual_power_kw);
  add("pv_forecast", "Forecast PV", FORECAST_ACCURACY_COLORS.predicted, intraday.predicted_power_kw);
  if (!compact) {
    add(
      "pv_latest",
      "Latest forecast PV",
      FORECAST_ACCURACY_COLORS.latestRevision,
      intraday.latest_revision_power_kw
    );
  }
  add("cloud", "Cloud cover", FORECAST_ACCURACY_COLORS.cloud, intraday.cloud_coverage_pct, "pct");
  return meta;
}

function forecastAccuracyTooltipRowsHtml(seriesMeta, t) {
  return seriesMeta
    .map((s) => {
      const v = interpolateSeriesAt(s.points, t);
      if (v == null) return "";
      const value =
        s.yAxis === "pct"
          ? `${Math.round(Math.min(100, Math.max(0, v)))}%`
          : formatStatisticsKw(v);
      return `<div class="statistics-tooltip-row"><span class="statistics-tooltip-label"><i class="statistics-tooltip-swatch" style="background:${esc(s.color)}"></i>${esc(s.label)}</span><strong>${esc(value)}</strong></div>`;
    })
    .filter(Boolean)
    .join("");
}

function bindForecastAccuracyChart(scope, seriesMeta) {
  const plot = scope?.querySelector?.("[data-forecast-accuracy-chart]:not([data-bound])");
  if (!plot || plot.dataset.bound || !seriesMeta?.length) return;
  plot.dataset.bound = "1";

  const padL = Number(plot.dataset.padL);
  const padT = Number(plot.dataset.padT);
  const padB = Number(plot.dataset.padB);
  const plotW = Number(plot.dataset.plotW);
  const tMin = Number(plot.dataset.tMin);
  const tMax = Number(plot.dataset.tMax);
  const daySpan = tMax - tMin;
  const svg = plot.querySelector(".forecast-accuracy-chart-svg");
  const hit = plot.querySelector(".forecast-accuracy-hit");
  const crosshair = plot.querySelector(".statistics-crosshair");
  const tooltip = plot.querySelector(".statistics-tooltip");
  if (!svg || !hit || !crosshair || !tooltip) return;

  const showHover = (clientX) => {
    const t = Math.min(statisticsClientToTime(svg, clientX, padL, plotW, tMin, daySpan), tMax);
    const { scale, offsetX, offsetY } = statisticsPointerScale(svg);
    const xPx = padL + ((t - tMin) / daySpan) * plotW;
    const screenX = offsetX + xPx * scale;
    crosshair.hidden = false;
    crosshair.style.left = `${screenX}px`;
    crosshair.style.top = `${offsetY + padT * scale}px`;
    crosshair.style.bottom = `${offsetY + padB * scale}px`;

    const rows = forecastAccuracyTooltipRowsHtml(seriesMeta, t);
    tooltip.hidden = false;
    tooltip.innerHTML = `<div class="statistics-tooltip-time">${esc(formatStatisticsHoverTime(t))}</div>${rows}`;
    const plotRect = plot.getBoundingClientRect();
    let left = screenX + 12;
    if (left + 200 > plotRect.width) left = screenX - 212;
    tooltip.style.left = `${Math.max(8, left)}px`;
    tooltip.style.top = "12px";
  };

  const hideHover = () => {
    crosshair.hidden = true;
    tooltip.hidden = true;
  };

  hit.addEventListener("mousemove", (ev) => showHover(ev.clientX));
  hit.addEventListener("mouseleave", hideHover);
  bindTouchChartScrub(hit, showHover, hideHover);
}

function forecastAccuracyYDomain(values, { minZero = true, padRatio = 0.04 } = {}) {
  const data = (values || []).filter((v) => Number.isFinite(Number(v))).map((v) => Number(v));
  if (!data.length) return { yMin: 0, yMax: 1 };
  let yMin = Math.min(...data);
  let yMax = Math.max(...data);
  if (yMax <= yMin) {
    const bump = Math.max(Math.abs(yMax) * 0.08, 0.12);
    yMin = minZero ? 0 : yMin - bump;
    yMax = yMax + bump;
  } else {
    const span = yMax - yMin;
    const pad = Math.max(span * padRatio, 0.05);
    yMin = minZero ? Math.max(0, yMin - pad * 0.2) : yMin - pad;
    yMax = yMax + pad;
  }
  return { yMin, yMax };
}

function forecastAccuracyYTicks(yMin, yMax) {
  const span = Math.max(yMax - yMin, 0.1);
  let step = 0.5;
  if (span > 16) step = 4;
  else if (span > 8) step = 2;
  else if (span > 4) step = 1;
  else if (span <= 1.2) step = 0.2;
  const start = Math.floor(yMin / step) * step;
  const ticks = [];
  for (let v = start; v <= yMax + step * 0.01; v += step) {
    if (v >= yMin - step * 0.01) ticks.push(Math.round(v * 100) / 100);
  }
  if (!ticks.length) ticks.push(yMin, yMax);
  return ticks;
}

function forecastAccuracyXTicks(tMin, tMax, { maxTicks = 7 } = {}) {
  const spanH = Math.max((tMax - tMin) / 3600000, 1);
  let stepH = 1;
  if (spanH / stepH > maxTicks) stepH = 2;
  if (spanH / stepH > maxTicks) stepH = 3;
  if (spanH / stepH > maxTicks) stepH = Math.ceil(spanH / maxTicks);
  const ticks = [];
  const start = new Date(tMin);
  start.setMinutes(0, 0, 0);
  let t = start.getTime();
  if (t < tMin) t += stepH * 3600000;
  while (t <= tMax + 1) {
    if (t >= tMin - 1 && t <= tMax + 1) ticks.push(t);
    t += stepH * 3600000;
  }
  return ticks;
}

function forecastAccuracyClipPoints(points, range) {
  const { tMin, nowMs } = range;
  return (points || []).filter(
    (p) => Number.isFinite(p.t) && Number.isFinite(p.v) && p.t >= tMin && p.t <= nowMs
  );
}

function forecastAccuracyClipCloudPoints(points, range) {
  const { tMin, tMax } = range;
  return (points || []).filter(
    (p) => Number.isFinite(p.t) && Number.isFinite(p.v) && p.t >= tMin && p.t <= tMax
  );
}

function forecastAccuracyPlotSvg(series, range, options = {}) {
  const {
    height = 160,
    width = 1000,
    pad = { l: 46, r: 8, t: 8, b: 28 },
    yUnit = "kWh",
    yMinZero = true,
    ariaLabel = "Forecast chart",
    showLegend = true,
    secondarySeries = null,
  } = options;
  const visible = (series || []).filter((s) => Array.isArray(s.points) && s.points.length >= 2);
  const cloudPts = forecastAccuracyClipCloudPoints(secondarySeries?.points, range);
  const hasCloud = cloudPts.length >= 2;
  if (!visible.length && !hasCloud) return "";
  const plotPad = { ...pad };
  if (hasCloud) plotPad.r = Math.max(plotPad.r, 34);
  const w = width - plotPad.l - plotPad.r;
  const h = height - plotPad.t - plotPad.b;
  const { tMin, tMax, nowMs } = range;
  const daySpan = Math.max(tMax - tMin, 1);
  const xScale = (t) => plotPad.l + ((t - tMin) / daySpan) * w;
  const allValues = [];
  for (const s of visible) {
    for (const p of forecastAccuracyClipPoints(s.points, range)) {
      allValues.push(p.v);
    }
  }
  const { yMin, yMax } = forecastAccuracyYDomain(allValues, { minZero: yMinZero });
  const ySpan = Math.max(yMax - yMin, 0.01);
  const yScale = (v) => plotPad.t + h - ((v - yMin) / ySpan) * h;
  const yCloudScale = (v) => {
    const inset = hasCloud ? (showLegend ? 10 : 8) : 0;
    const plotH = Math.max(h - inset, 1);
    return plotPad.t + inset + plotH - (Math.min(100, Math.max(0, Number(v))) / 100) * plotH;
  };
  const yTicks = forecastAccuracyYTicks(yMin, yMax);
  const xTicks = forecastAccuracyXTicks(tMin, tMax);
  const grid = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<line x1="${plotPad.l}" y1="${y.toFixed(1)}" x2="${plotPad.l + w}" y2="${y.toFixed(1)}" class="statistics-grid"/>`;
    })
    .join("");
  const plotBottom = plotPad.t + h;
  const axisLabelY = (y, yv, ticks, isCloud = false) => {
    const isBottom = Math.abs(y - plotBottom) < 1.5;
    if (isBottom && !isCloud && yMinZero && yv <= yMin + 0.001 && ticks.length > 2) return null;
    return isBottom ? y - 5 : y + 4;
  };
  const yLabels = yTicks
    .map((yv) => {
      const y = yScale(yv);
      const labelY = axisLabelY(y, yv, yTicks);
      if (labelY == null) return "";
      const label = yUnit === "kW" ? formatStatisticsYTick(yv) : yv.toFixed(yv % 1 ? 1 : 0);
      return `<text x="${plotPad.l - 8}" y="${labelY.toFixed(1)}" text-anchor="end" class="statistics-axis-y">${esc(label)}</text>`;
    })
    .join("");
  const cloudLabelX = width - 8;
  const yCloudLabels = hasCloud
    ? [0, 50, 100]
        .map((yv) => {
          const y = yCloudScale(yv);
          const labelY = axisLabelY(y, yv, [0, 50, 100], true);
          if (labelY == null) return "";
          return `<text x="${cloudLabelX.toFixed(1)}" y="${labelY.toFixed(1)}" text-anchor="end" class="statistics-axis-y forecast-accuracy-axis-y--cloud">${yv}%</text>`;
        })
        .join("")
    : "";
  const xLabelY = plotBottom + Math.max(12, Math.round(plotPad.b * 0.55));
  const xLabels = xTicks
    .map((xt) => {
      const x = xScale(xt);
      return `<text x="${x.toFixed(1)}" y="${xLabelY.toFixed(1)}" text-anchor="middle" class="statistics-axis-x">${esc(formatChartTimeLabel(xt))}</text>`;
    })
    .join("");
  let cloudFill = "";
  let cloudLine = "";
  if (hasCloud) {
    const pixelPts = cloudPts.map((p) => ({ x: xScale(p.t), y: yCloudScale(p.v), t: p.t, v: p.v }));
    const baseline = plotPad.t + h;
    cloudFill = `<path class="forecast-accuracy-cloud-fill" d="${fillToZeroPath(pixelPts, baseline, cloudPts)}" fill="${secondarySeries.fillColor || FORECAST_ACCURACY_COLORS.cloudFill}" stroke="none"/>`;
    cloudLine = `<path class="statistics-line forecast-accuracy-cloud-line" d="${polylinePath(pixelPts)}" fill="none" stroke="${secondarySeries.color || FORECAST_ACCURACY_COLORS.cloud}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>`;
  }
  const lines = visible
    .map((s) => {
      const pts = forecastAccuracyClipPoints(s.points, range);
      if (pts.length < 2) return "";
      const pixelPts = pts.map((p) => ({ x: xScale(p.t), y: yScale(p.v) }));
      return `<path class="statistics-line" d="${polylinePath(pixelPts)}" fill="none" stroke="${s.color}" stroke-width="${s.lineWidth || 1.8}" stroke-linecap="round" stroke-linejoin="round"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""}/>`;
    })
    .join("");
  const legendItems = [...visible];
  if (hasCloud) {
    legendItems.push({
      label: secondarySeries.label || "Cloud cover",
      color: secondarySeries.color || FORECAST_ACCURACY_COLORS.cloud,
    });
  }
  const legend = showLegend
    ? legendItems
        .map(
          (s) =>
            `<span class="forecast-accuracy-legend-item"><i style="background:${s.color}"></i>${esc(s.label)}</span>`
        )
        .join("")
    : "";
  const head = showLegend
    ? `<div class="forecast-accuracy-plot-head forecast-accuracy-plot-head--stacked">
<span class="forecast-accuracy-plot-label">${esc(yUnit)}</span>
<div class="forecast-accuracy-legend forecast-accuracy-legend--inline">${legend}</div>
</div>`
    : `<div class="forecast-accuracy-plot-head forecast-accuracy-plot-head--axis-only"><span class="forecast-accuracy-plot-label">${esc(yUnit)}</span></div>`;
  const plotAttrs = `data-pad-l="${plotPad.l}" data-pad-t="${plotPad.t}" data-pad-b="${plotPad.b}" data-plot-w="${w}" data-plot-h="${h}" data-t-min="${tMin}" data-t-max="${tMax}"`;
  return `<div class="forecast-accuracy-plot${hasCloud ? " forecast-accuracy-plot--cloud" : ""}">
${head}
<div class="forecast-accuracy-chart-plot" data-forecast-accuracy-chart="1" ${plotAttrs}>
<svg class="forecast-accuracy-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMinYMin meet" role="img" aria-label="${esc(ariaLabel)}">
${grid}${cloudFill}${yLabels}${yCloudLabels}${xLabels}${lines}${cloudLine}
<rect class="forecast-accuracy-hit statistics-hit" x="${plotPad.l}" y="${plotPad.t}" width="${w}" height="${h}" fill="transparent"/>
</svg>
<div class="statistics-crosshair" hidden><div class="statistics-spike"></div></div>
<div class="statistics-tooltip" hidden role="tooltip"></div>
</div>
</div>`;
}

function renderForecastAccuracyChartHtml(intraday, range, { compact = false } = {}) {
  const powerSeries = [
    {
      id: "pv_actual",
      label: "PV generation",
      color: FORECAST_ACCURACY_COLORS.actual,
      points: intraday?.actual_power_kw,
    },
    {
      id: "pv_forecast",
      label: "Forecast PV",
      color: FORECAST_ACCURACY_COLORS.predicted,
      points: intraday?.predicted_power_kw,
    },
  ];
  if (!compact && intraday?.latest_revision_power_kw?.length >= 2) {
    powerSeries.push({
      id: "pv_latest",
      label: "Latest forecast PV",
      color: FORECAST_ACCURACY_COLORS.latestRevision,
      dash: "5 4",
      lineWidth: 1.6,
      points: intraday.latest_revision_power_kw,
    });
  }
  const hasPower = powerSeries.some((s) => s.points?.length >= 2);
  if (!hasPower) {
    return `<p class="placeholder chart-empty">No intraday forecast comparison yet.</p>`;
  }
  const pad = compact
    ? { l: 44, r: 6, t: 4, b: 20 }
    : { l: 50, r: 10, t: 4, b: 22 };
  const cloudPoints = intraday?.cloud_coverage_pct;
  const secondarySeries =
    cloudPoints?.length >= 2
      ? {
          points: cloudPoints,
          label: "Cloud cover",
          color: FORECAST_ACCURACY_COLORS.cloud,
          fillColor: FORECAST_ACCURACY_COLORS.cloudFill,
        }
      : null;
  if (secondarySeries) {
    pad.t = compact ? 12 : 14;
    pad.r = compact ? 32 : 36;
    pad.b = compact ? 24 : 26;
  }
  const chartHeight = compact ? 168 : 180;
  const height = secondarySeries ? chartHeight + (compact ? 10 : 8) : chartHeight;
  return `<div class="forecast-accuracy-chart-wrap${secondarySeries ? " forecast-accuracy-chart-wrap--cloud" : ""}">${forecastAccuracyPlotSvg(powerSeries, range, {
    height,
    pad,
    yUnit: "kW",
    yMinZero: true,
    showLegend: true,
    secondarySeries,
    ariaLabel: "PV generation vs forecast power and cloud cover",
  })}</div>`;
}

function formatRevisionClock(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "—";
  }
}

function formatForecastSignedKwh(value) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)} kWh`;
}

function renderForecastAccuracyRevisionsTable(revisions) {
  const rows = (revisions || []).slice().reverse();
  if (!rows.length) return "";
  const body = rows
    .map((r) => {
      const delta = r.delta_kwh;
      const deltaCls =
        delta == null ? "" : delta > 0 ? "forecast-accuracy-delta--up" : delta < 0 ? "forecast-accuracy-delta--down" : "";
      const deltaText = delta == null ? "—" : formatForecastSignedKwh(delta);
      return `<tr>
<td>${esc(formatRevisionClock(r.fetched_at))}</td>
<td>${esc(formatDailyKwh(r.forecast_today_kwh))}</td>
<td class="${deltaCls}">${esc(deltaText)}</td>
<td>${esc(formatDailyKwh(r.forecast_remaining_kwh))}</td>
</tr>`;
    })
    .join("");
  return `<div class="forecast-accuracy-revisions-wrap">
<table class="forecast-accuracy-revisions">
<thead><tr><th>Updated</th><th>Day total</th><th>Change</th><th>Remaining</th></tr></thead>
<tbody>${body}</tbody>
</table>
</div>`;
}

function renderForecastAccuracyCard(report, { compact = false, loading = false, period = "day" } = {}) {
  if (period !== "day") return "";
  const title = compact ? "Forecast vs production" : "Solar Forecast Accuracy";
  const titleHtml = compact
    ? `<p class="card-title">${esc(title)}</p>`
    : `<h3 class="fox-analysis-summary-title fox-analysis-chart-title">${esc(title)}</h3>`;
  const margin = compact ? "margin-top:14px" : "";
  if (loading || !report) {
    return `<div class="card forecast-accuracy-card${compact ? " forecast-accuracy-card--compact" : ""}" style="${margin}">
${titleHtml}
<p class="forecast-accuracy-empty chart-loading forecast-accuracy-loading">Loading forecast data…</p>
</div>`;
  }
  if (report.error) {
    const errText = report.error;
    return `<div class="card forecast-accuracy-card${compact ? " forecast-accuracy-card--compact" : ""}" style="${margin}">
${titleHtml}
<p class="forecast-accuracy-empty">${esc(errText)}</p>
<p class="forecast-accuracy-hint">Check FoxESS Plant is loaded, then refresh the page.</p>
</div>`;
  }
  if (!report.intraday?.actual_power_kw?.length && !report.intraday?.predicted_power_kw?.length) {
    return `<div class="card forecast-accuracy-card${compact ? " forecast-accuracy-card--compact" : ""}" style="${margin}">
${titleHtml}
<p class="forecast-accuracy-empty">No forecast comparison data for this day yet.</p>
</div>`;
  }
  const actual = formatDailyKwh(report.actual_kwh);
  const predicted = formatDailyKwh(report.predicted_kwh);
  const errKwh = report.error_kwh;
  const errPct =
    report.error_pct == null || !Number.isFinite(Number(report.error_pct))
      ? ""
      : ` (${report.error_pct >= 0 ? "+" : ""}${Number(report.error_pct).toFixed(1)}%)`;
  const errText = errKwh == null ? "—" : `${formatForecastSignedKwh(errKwh)}${errPct}`;
  const errCls =
    errKwh == null ? "" : errKwh >= 0 ? "forecast-accuracy-stat--high" : "forecast-accuracy-stat--low";
  const revisionHint =
    compact && report.revision_count
      ? `<p class="forecast-accuracy-hint">${report.revision_count} forecast update${report.revision_count === 1 ? "" : "s"} · latest ${esc(formatRevisionClock(report.revisions?.[report.revisions.length - 1]?.fetched_at))}</p>`
      : "";
  const revisionShift =
    !compact &&
    report.first_predicted_kwh != null &&
    report.latest_predicted_kwh != null &&
    Math.abs(report.latest_predicted_kwh - report.first_predicted_kwh) >= 0.05
      ? `<p class="forecast-accuracy-hint">Day total revised from ${esc(formatDailyKwh(report.first_predicted_kwh))} to ${esc(formatDailyKwh(report.latest_predicted_kwh))}</p>`
      : "";
  const range = forecastAccuracyRangeFromReport(report, report.intraday);
  const chart = renderForecastAccuracyChartHtml(report.intraday, range, { compact });
  const revisions = compact ? "" : renderForecastAccuracyRevisionsTable(report.revisions);
  return `<div class="card forecast-accuracy-card${compact ? " forecast-accuracy-card--compact" : ""}" style="${margin}" data-forecast-accuracy="1">
${titleHtml}
<p class="forecast-accuracy-sub">${compact ? "Solcast revisions compared with measured solar output" : "Measured production vs Solcast predictions and intraday revisions"}</p>
<div class="forecast-accuracy-stats">
<div class="forecast-accuracy-stat"><label>Actual</label><strong>${esc(actual)}</strong></div>
<div class="forecast-accuracy-stat"><label>Forecast</label><strong>${esc(predicted)}</strong></div>
<div class="forecast-accuracy-stat ${errCls}"><label>Variance</label><strong>${esc(errText)}</strong></div>
</div>
${revisionShift}${revisionHint}
${chart}
${revisions}
</div>`;
}

function octopusTariffEnabled(plantState) {
  const dynamic = plantState?.tariff?.dynamic;
  return Boolean(dynamic?.enabled && String(dynamic?.provider || "").toLowerCase() === "octopus");
}

function smartChargeEnabled(plantState) {
  return Boolean(plantState?.smart_charge?.enabled);
}

function reportsNavForState(plantState) {
  const items = [...REPORTS_NAV];
  if (smartChargeEnabled(plantState)) {
    items.push({ id: "smart_charge", label: "SmartCharge Analysis" });
  }
  return items;
}

function octopusGreenerPayload(plantState) {
  const raw = plantState?.tariff?.octopus_greener;
  return raw && typeof raw === "object" ? raw : null;
}

function formatOctopusTimeMs(ms) {
  if (!Number.isFinite(ms)) return "—";
  return new Date(ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatOctopusPeriodRange(startMs, endMs) {
  return `${formatOctopusTimeMs(startMs)} - ${formatOctopusTimeMs(endMs)}`;
}

function formatOctopusMoneyPence(pence) {
  if (pence == null || !Number.isFinite(Number(pence))) return "—";
  return `£${(Number(pence) / 100).toFixed(2)}`;
}

function formatOctopusPointsValue(points, apiAmount) {
  if (apiAmount != null && Number.isFinite(Number(apiAmount))) {
    return `≈ £${Number(apiAmount).toFixed(2)} value`;
  }
  if (points != null && Number.isFinite(Number(points))) {
    return `≈ £${(Number(points) / 800).toFixed(2)} value`;
  }
  return "";
}

function formatOctopusRate(pPerKwh) {
  if (pPerKwh == null || !Number.isFinite(Number(pPerKwh))) return "—";
  return `${Number(pPerKwh).toFixed(2)}p/kWh`;
}

function formatOctopusChartTimeMs(ms) {
  if (!Number.isFinite(ms)) return "—";
  return new Date(ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
}

function formatOctopusTooltipHour(ms) {
  if (!Number.isFinite(ms)) return "—";
  const d = new Date(ms);
  const h = d.getHours() % 12 || 12;
  const suffix = d.getHours() < 12 ? "AM" : "PM";
  return `${h}${suffix}`;
}

function formatOctopusTooltipSlotRange(startMs, endMs) {
  if (!Number.isFinite(startMs)) return "—";
  const timeOpts = { hour: "numeric", minute: "2-digit", hour12: true };
  const start = new Date(startMs).toLocaleTimeString([], timeOpts);
  if (!Number.isFinite(endMs)) return start;
  const end = new Date(endMs).toLocaleTimeString([], timeOpts);
  return `${start} – ${end}`;
}

function octopusChartTooltipHtml(chartMode, bar) {
  const time = bar.label || formatOctopusTooltipSlotRange(bar.start_ms, bar.end_ms);
  const timeRow = `<div class="octopus-greener-tooltip-time">${esc(time)}</div>`;
  if (chartMode === "import-rate") {
    const rate = bar.p_per_kwh ?? bar.value;
    return `${timeRow}<div class="octopus-greener-tooltip-score">Import price: <strong>${esc(formatOctopusRate(rate))}</strong></div>`;
  }
  if (chartMode === "export-rate") {
    const rate = bar.p_per_kwh ?? bar.value;
    return `${timeRow}<div class="octopus-greener-tooltip-score">Export price: <strong>${esc(formatOctopusRate(rate))}</strong></div>`;
  }
  if (chartMode === "consumption") {
    const kwh = bar.kwh ?? bar.value;
    const kwhText = kwh != null && Number.isFinite(Number(kwh)) ? `${Number(kwh).toFixed(1)} kWh` : "—";
    return `${timeRow}<div class="octopus-greener-tooltip-score">Smart-meter import: <strong>${esc(kwhText)}</strong></div>`;
  }
  if (chartMode === "dual") {
    const scoreText = bar.low_carbon_score != null ? `${bar.low_carbon_score}/10` : "—";
    const carbonLabel = octopusCarbonPeriodIsGreen(bar) ? "Low carbon" : "Higher carbon";
    const importPrice = bar.p_per_kwh != null ? formatOctopusRate(bar.p_per_kwh) : "—";
    const exportPrice = bar.export_p_per_kwh != null ? formatOctopusRate(bar.export_p_per_kwh) : "—";
    const gco2Text = bar.gco2 != null ? `${bar.gco2} gCO₂/kWh` : "";
    return `${timeRow}
<div class="octopus-greener-tooltip-score">${esc(carbonLabel)} score: <strong>${esc(scoreText)}</strong></div>
<div class="octopus-greener-tooltip-gco2">Import price: <strong>${esc(importPrice)}</strong> · Export price: <strong>${esc(exportPrice)}</strong>${gco2Text ? ` · ${esc(gco2Text)}` : ""}</div>`;
  }
  return `${timeRow}<div class="octopus-greener-tooltip-gco2">${esc(String(bar.value ?? "—"))}</div>`;
}

function octopusCarbonPeriodsForChart(periods, now = Date.now()) {
  const rows = (Array.isArray(periods) ? periods : [])
    .filter((p) => Number.isFinite(p?.start_ms))
    .sort((a, b) => a.start_ms - b.start_ms);
  if (!rows.length) return [];
  const currentIdx = rows.findIndex((p) => p.start_ms <= now && p.end_ms > now);
  const anchor = currentIdx >= 0 ? currentIdx : rows.findIndex((p) => p.start_ms >= now);
  if (anchor < 0) {
    return rows.slice(Math.max(0, rows.length - 48));
  }
  const startIdx = Math.max(0, anchor - 1);
  return rows.slice(startIdx, startIdx + 48);
}

function octopusLowCarbonScoreFromGco2(gco2) {
  if (gco2 == null || !Number.isFinite(Number(gco2))) return null;
  return Math.max(1, Math.min(10, Math.round(10 - (Number(gco2) - 60) / 25)));
}

function octopusBarScore(period) {
  if (period?.low_carbon_score != null && Number.isFinite(Number(period.low_carbon_score))) {
    return Number(period.low_carbon_score);
  }
  return octopusLowCarbonScoreFromGco2(period?.gco2_per_kwh) ?? 1;
}

function octopusLowCarbonScoreGreenMin(threshold = 99) {
  return octopusLowCarbonScoreFromGco2(threshold) ?? 8;
}

function octopusCarbonPeriodIsGreen(period, threshold = 99) {
  return octopusBarScore(period) >= octopusLowCarbonScoreGreenMin(threshold);
}

function octopusGreenerNightByDate(greenerNights) {
  const map = new Map();
  for (const row of Array.isArray(greenerNights) ? greenerNights : []) {
    if (row?.date) map.set(String(row.date), row);
  }
  return map;
}

function octopusGreenerWeekRows(greenerNights, periodOffset = 0, now = new Date()) {
  const { start } = energyPeriodBounds("week", periodOffset, now);
  const days = buildFullWeekDays(start);
  const byDate = octopusGreenerNightByDate(greenerNights);
  return days.map((d) => {
    const dateKey = formatEnergyDateLabel(d);
    const row = byDate.get(dateKey);
    let score = null;
    if (row?.greenness_score != null && Number.isFinite(Number(row.greenness_score))) {
      score = Number(row.greenness_score);
    }
    return {
      date: dateKey,
      dayMs: startOfLocalDay(d).getTime(),
      label: d.toLocaleDateString(undefined, { weekday: "short" }),
      shortDate: d.toLocaleDateString(undefined, { day: "numeric", month: "short" }),
      greenness_score: score,
      greenness_index: row?.greenness_index ?? null,
      is_greener_night: Boolean(row?.is_greener_night),
      hasData: Boolean(row),
    };
  });
}

function octopusGreenerWeekHeadline(rows) {
  const withData = rows.filter((r) => r.hasData);
  if (!withData.length) return "Greener nights forecast";
  const greener = withData.filter((r) => r.is_greener_night);
  if (!greener.length) return "No greener nights forecast this week";
  if (greener.length === 1) return "1 greener night this week";
  return `${greener.length} greener nights this week`;
}

function startOfWeekSunday(d) {
  const x = startOfLocalDay(d);
  x.setDate(x.getDate() - x.getDay());
  return x;
}

function formatOctopusTileDate(d) {
  const day = String(d.getDate()).padStart(2, "0");
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  return `${day}/${mo}`;
}

const OCTOPUS_GREENER_SAPLING_VER = 3;
const OCTOPUS_GREENER_SAPLING_LOW_URL = `/foxess_plant_panel/octopus_greener_sapling.png?v=${OCTOPUS_GREENER_SAPLING_VER}`;
const OCTOPUS_GREENER_SAPLING_GREEN_URL = `/foxess_plant_panel/octopus_greener_sapling_green.png?v=${OCTOPUS_GREENER_SAPLING_VER}`;

function octopusGreenerPlantSvg(isGreenerNight) {
  const isGreen = Boolean(isGreenerNight);
  const cls = isGreen
    ? "octopus-upcoming-week-plant octopus-upcoming-week-plant--green"
    : "octopus-upcoming-week-plant octopus-upcoming-week-plant--low";
  const url = isGreen ? OCTOPUS_GREENER_SAPLING_GREEN_URL : OCTOPUS_GREENER_SAPLING_LOW_URL;
  return `<div class="octopus-upcoming-week-plant-wrap"><img class="${cls}" src="${esc(url)}" alt="" loading="lazy" decoding="async"></div>`;
}

function octopusUpcomingWeekRows(greenerNights, now = new Date()) {
  const start = startOfWeekSunday(now);
  const byDate = octopusGreenerNightByDate(greenerNights);
  const todayKey = formatEnergyDateLabel(now);
  const rows = [];
  for (let i = 0; i < 7; i += 1) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    const dateKey = formatEnergyDateLabel(d);
    const row = byDate.get(dateKey);
    let score = null;
    if (row?.greenness_score != null && Number.isFinite(Number(row.greenness_score))) {
      score = Number(row.greenness_score);
    }
    rows.push({
      date: dateKey,
      label: d.toLocaleDateString(undefined, { weekday: "short" }),
      tileDate: formatOctopusTileDate(d),
      greenness_score: score,
      is_greener_night: Boolean(row?.is_greener_night),
      hasData: Boolean(row),
      isPast: dateKey < todayKey,
      isToday: dateKey === todayKey,
    });
  }
  let featuredDate = null;
  for (const row of rows) {
    if (row.date >= todayKey && row.is_greener_night) {
      featuredDate = row.date;
      break;
    }
  }
  return rows.map((row) => ({ ...row, featured: row.date === featuredDate }));
}

function octopusAnalysisCardTitle(title, { compact = false } = {}) {
  if (compact) return `<p class="card-title">${esc(title)}</p>`;
  return `<h3 class="fox-analysis-summary-title fox-analysis-chart-title">${esc(title)}</h3>`;
}

function renderOctopusGreenerDailyIntroHtml() {
  return `<p class="octopus-greener-intro octopus-greener-intro--daily">${esc(OCTOPUS_GREENER_DAILY_INTRO)}<span class="octopus-greener-help-wrap"><button type="button" class="octopus-greener-help-btn fox-analysis-help-btn" aria-describedby="octopus-greener-help-tip" aria-label="Low carbon score information"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="8" y="11.5" text-anchor="middle" font-size="10" font-weight="600" fill="currentColor">?</text></svg></button><span id="octopus-greener-help-tip" class="octopus-greener-help-bubble" role="tooltip">${esc(OCTOPUS_GREENER_DAILY_HELP)}</span></span></p>`;
}

function renderOctopusUpcomingWeekCard(payload) {
  if (!payload) {
    return `<div class="card octopus-upcoming-week-card" data-octopus-upcoming-week-card="1">
${octopusAnalysisCardTitle(OCTOPUS_UPCOMING_WEEK_CARD_TITLE)}
<p class="octopus-greener-empty chart-loading">Loading upcoming week…</p>
</div>`;
  }
  const rows = octopusUpcomingWeekRows(payload.greener_nights);
  const err = payload.errors?.greener_nights;
  const errHtml = err ? `<p class="octopus-upcoming-week-error">${esc(String(err))}</p>` : "";
  const tiles = rows
    .map((row) => {
      const active = row.is_greener_night;
      const classes = [
        "octopus-upcoming-week-day",
        row.featured ? "octopus-upcoming-week-day--featured" : "",
        active ? "octopus-upcoming-week-day--green" : "",
        row.isToday ? "octopus-upcoming-week-day--today" : "",
        row.isPast && !row.hasData ? "octopus-upcoming-week-day--past" : "",
      ]
        .filter(Boolean)
        .join(" ");
      const badge = row.featured ? `<span class="octopus-upcoming-week-badge">Green</span>` : "";
      return `<div class="${classes}" title="${esc(row.label)} ${esc(row.tileDate)}${active ? " · Greener night" : ""}${row.greenness_score != null ? ` · Score ${row.greenness_score}/100` : ""}">
${badge}
<span class="octopus-upcoming-week-dayname">${esc(row.label)}</span>
<span class="octopus-upcoming-week-date">${esc(row.tileDate)}</span>
${octopusGreenerPlantSvg(active)}
</div>`;
    })
    .join("");
  return `<div class="card octopus-upcoming-week-card" data-octopus-upcoming-week-card="1">
${octopusAnalysisCardTitle(OCTOPUS_UPCOMING_WEEK_CARD_TITLE)}
<p class="octopus-greener-headline">Greener Nights start at 11PM and end at 6AM the following morning.</p>
<p class="octopus-upcoming-week-note">Spot an upcoming Greener Night that&apos;s now disappeared? Don&apos;t worry, this will still count even if it&apos;s no longer showing.</p>
${errHtml}
<div class="octopus-upcoming-week-grid" role="list" aria-label="Greener nights upcoming week">${tiles}</div>
</div>`;
}

function renderOctopusGreenerWeekChartSvg(greenerNights, periodOffset = 0) {
  const W = 680;
  const H = 190;
  const padL = 54;
  const padR = 12;
  const padT = 16;
  const padB = 30;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const scoreMax = 100;
  const rows = octopusGreenerWeekRows(greenerNights, periodOffset);
  if (!rows.some((r) => r.hasData)) {
    return `<p class="octopus-greener-empty">Greener nights forecast unavailable for this week. Octopus publishes the next seven overnight windows only.</p>`;
  }
  const slotW = chartW / rows.length;
  const barW = Math.max(10, Math.min(36, slotW * 0.72));
  const barsMeta = rows.map((r) => ({
    date: r.date,
    label: r.label,
    shortDate: r.shortDate,
    greenness_score: r.greenness_score,
    greenness_index: r.greenness_index,
    is_greener_night: r.is_greener_night,
    hasData: r.hasData,
  }));
  const bars = rows
    .map((r, i) => {
      const x = padL + i * slotW + (slotW - barW) / 2;
      if (!r.hasData || r.greenness_score == null) {
        return `<rect class="octopus-greener-bar octopus-greener-bar--nodata" data-bar-index="${i}" x="${x.toFixed(1)}" y="${(padT + chartH - 2).toFixed(1)}" width="${barW.toFixed(1)}" height="2" fill="var(--secondary-text-color)" opacity="0.35" rx="1" />`;
      }
      const h = Math.max(4, (r.greenness_score / scoreMax) * chartH);
      const y = padT + chartH - h;
      const color = r.is_greener_night
        ? "var(--octopus-green-bar, #22c55e)"
        : "var(--octopus-purple-bar, #8b5cf6)";
      const rx = Math.min(barW / 2, h / 2, 6);
      return `<rect class="octopus-greener-bar" data-bar-index="${i}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" fill="${color}" rx="${rx.toFixed(1)}" />`;
    })
    .join("");
  const xLabels = rows
    .map((r, i) => {
      const x = padL + i * slotW + slotW / 2;
      return `<text x="${x.toFixed(1)}" y="${H - 8}" text-anchor="middle" class="octopus-greener-axis">${esc(r.label)}</text>`;
    })
    .join("");
  const yMid = padT + chartH / 2;
  const yArrowTip = padT + 2;
  const yArrowBase = padT + 12;
  const barsJson = encodeURIComponent(JSON.stringify(barsMeta));
  const hitLeftPct = ((padL / W) * 100).toFixed(3);
  return `<div class="octopus-greener-chart-wrap">
<div class="octopus-greener-chart-plot" data-octopus-greener-plot="1" data-chart-mode="week" data-chart-w="${W}" data-pad-l="${padL}" data-pad-t="${padT}" data-pad-b="${padB}" data-chart-inner-w="${chartW}" data-slot-w="${slotW}" data-bars="${barsJson}" style="--octopus-hit-left:${hitLeftPct}%">
<svg class="octopus-greener-chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Greener nights weekly forecast chart">
<polygon points="24,${yArrowTip} 20,${yArrowBase} 28,${yArrowBase}" class="octopus-greener-y-arrow-head" />
<line x1="24" y1="${yArrowBase}" x2="24" y2="${(padT + chartH).toFixed(1)}" class="octopus-greener-y-arrow" />
<text x="14" y="${yMid.toFixed(1)}" transform="rotate(-90 14 ${yMid.toFixed(1)})" text-anchor="middle" class="octopus-greener-y-label">Greenness score</text>
${bars}
${xLabels}
</svg>
<div class="octopus-greener-hit" aria-hidden="true"></div>
<div class="octopus-greener-tooltip" hidden role="tooltip"></div>
</div>
<div class="octopus-greener-legend">
<span><i class="octopus-greener-swatch octopus-greener-swatch--green"></i>Greener night</span>
<span><i class="octopus-greener-swatch octopus-greener-swatch--purple"></i>Not a greener night</span>
</div>
</div>`;
}

function renderOctopusGreenerWeekTable(greenerNights, periodOffset = 0) {
  const rows = octopusGreenerWeekRows(greenerNights, periodOffset);
  if (!rows.some((r) => r.hasData)) {
    return `<p class="octopus-greener-empty">Greener nights forecast unavailable for this week. Octopus publishes the next seven overnight windows only.</p>`;
  }
  const body = rows
    .map((r) => {
      const score = r.greenness_score != null ? `${r.greenness_score}/100` : "—";
      const night = !r.hasData ? "—" : r.is_greener_night ? "Yes" : "No";
      const index = r.greenness_index ? String(r.greenness_index) : "—";
      return `<tr><td>${esc(r.shortDate)}</td><td>${esc(r.label)}</td><td>${esc(score)}</td><td>${esc(index)}</td><td>${esc(night)}</td></tr>`;
    })
    .join("");
  return `<div class="octopus-greener-table-wrap"><table class="octopus-greener-table">
<thead><tr><th>Date</th><th>Day</th><th>Greenness score</th><th>Index</th><th>Greener night</th></tr></thead>
<tbody>${body}</tbody>
</table></div>`;
}

function renderOctopusGreenerWeekTimeline(rows) {
  const upcoming = rows.filter((r) => r.hasData && r.is_greener_night);
  if (!upcoming.length) {
    const any = rows.some((r) => r.hasData);
    if (!any) return "";
    return `<ul class="octopus-greener-timeline">${renderOctopusGreenerTimelineItem({
      tone: "warn",
      title: "No greener nights flagged in this week\u2019s forecast",
      detail: "Shift EV charging to nights with higher greenness scores if you can.",
    })}</ul>`;
  }
  const items = upcoming
    .map((r) => {
      const score = r.greenness_score != null ? `${r.greenness_score}/100` : "—";
      return renderOctopusGreenerTimelineItem({
        tone: "good",
        title: `${r.label} ${r.shortDate}: greener night (${score})`,
        detail: "Good window for overnight EV charging (23:00–06:00).",
      });
    })
    .join("");
  return `<ul class="octopus-greener-timeline">${items}</ul>`;
}

function renderOctopusGreenerCarbonLegend(threshold) {
  return `<div class="octopus-greener-legend octopus-greener-legend--top">
<span><i class="octopus-greener-swatch octopus-greener-swatch--green"></i>≤${Math.round(threshold)}gCO₂/kWh Green</span>
<span><i class="octopus-greener-swatch octopus-greener-swatch--purple"></i>&gt;${Math.round(threshold)}gCO₂/kWh Not-so-green</span>
<span><i class="octopus-greener-swatch-line" aria-hidden="true"></i>National green line</span>
</div>`;
}

const OCTOPUS_TIMELINE_LEAF_SVG = `<svg class="octopus-greener-timeline-icon-svg octopus-greener-timeline-icon-svg--leaf" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 26" aria-hidden="true"><path fill="#18f0b8" d="M15.938 3.718c-4.606 0-8.502 2.988-9.827 7.108a14.56 14.56 0 0 1 6.545-1.537h5.156c.516 0 .938.417.938.928 0 .51-.422.928-.938.928H12.656c-.972 0-1.916.11-2.824.314-1.518.342-2.93.951-4.184 1.781C2.244 15.486 0 19.321 0 23.68v.928C0 25.38.627 26 1.406 26c.78 0 1.407-.62 1.407-1.393v-.928a9.675 9.675 0 0 1 3.152-7.149c1.16 4.381 5.185 7.613 9.973 7.613h.058C23.736 24.103 30 16.548 30 7.234c0-2.471-.44-4.822-1.236-6.94-.153-.4-.744-.382-.95-.005a6.56 6.56 0 0 1-5.783 3.429h-6.093Z"/></svg>`;

const OCTOPUS_TIMELINE_UNPLUGGED_SVG = `<svg class="octopus-greener-timeline-icon-svg octopus-greener-timeline-icon-svg--unplugged" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 15 21" aria-hidden="true"><path fill="#8b5cf6" d="M13.8887 6.5244c.1206.0086.2399.034.3535.0772a1.2471 1.2471 0 0 1 .8037 1.165c0 .1677-.0339.334-.0996.4883a1.2474 1.2474 0 0 1-1.1963.7568v1.2451c0 3.012-2.148 5.4906-5 6.1006v2.6094a1.2502 1.2502 0 0 1-2.1338.8838 1.2502 1.2502 0 0 1-.3662-.8838v-2.6094a6.4213 6.4213 0 0 1-1.6133-.581l9.252-9.252Zm-12.041 6.3848c-.383-.8028-.5977-1.7009-.5977-2.6524v-1.245C.56 9.0117 0 8.4555 0 7.7665c.0002-.6888.5601-1.2441 1.25-1.2441h6.9854l-6.3877 6.3867Z"/><path fill="#8b5cf6" d="M3.832 0c.677 0 1.2225.5839 1.2227 1.3037v5.2188H2.6094V1.3037C2.6105.5838 3.157 0 3.832 0ZM11.17 0c.6769 0 1.2225.5838 1.2227 1.3037l-.001 1.0928a2.0151 2.0151 0 0 0-.2197.1894L9.9463 4.8115V1.3037C9.9464.584 10.493 0 11.1699 0Z"/><path fill="#8b5cf6" d="M12.8787 3.2929c.3905-.3905 1.0237-.3905 1.4142 0 .3905.3905.3905 1.0237 0 1.4142L2.7071 16.293c-.3905.3905-1.0237.3905-1.4142 0-.3905-.3905-.3905-1.0237 0-1.4142L12.8787 3.2929Z"/></svg>`;

function octopusGreenerTimelineIconHtml(tone) {
  if (tone === "good") return OCTOPUS_TIMELINE_LEAF_SVG;
  return OCTOPUS_TIMELINE_UNPLUGGED_SVG;
}

function splitOctopusTimelineText(text) {
  const raw = String(text || "").trim();
  if (!raw) return { title: "", detail: "" };
  const colonIdx = raw.indexOf(":");
  if (colonIdx === -1) return { title: raw, detail: "" };
  const afterColon = raw.slice(colonIdx + 1).trim();
  const splitAt = afterColon.search(/\.\s+/);
  if (splitAt === -1) {
    return { title: `${raw.slice(0, colonIdx + 1)} ${afterColon}`.trim(), detail: "" };
  }
  const title = `${raw.slice(0, colonIdx + 1)} ${afterColon.slice(0, splitAt).trim()}`.trim();
  const detail = afterColon.slice(splitAt + 1).trim();
  return { title, detail };
}

function octopusGreenerTimelineCopy(row) {
  if (row?.title) {
    return { title: String(row.title), detail: row.detail != null ? String(row.detail) : "" };
  }
  return splitOctopusTimelineText(row?.text);
}

function renderOctopusGreenerTimelineCopyHtml(row) {
  const { title, detail } = octopusGreenerTimelineCopy(row);
  const detailHtml = detail
    ? `<span class="octopus-greener-timeline-detail">${esc(detail)}</span>`
    : "";
  return `<div class="octopus-greener-timeline-copy"><strong class="octopus-greener-timeline-title">${esc(title)}</strong>${detailHtml}</div>`;
}

function renderOctopusGreenerTimelineItem(row) {
  const tone = row.tone === "good" ? "good" : row.tone === "warn" ? "warn" : "neutral";
  return `<li class="octopus-greener-timeline-item octopus-greener-timeline-item--${tone}"><span class="octopus-greener-timeline-icon">${octopusGreenerTimelineIconHtml(tone)}</span>${renderOctopusGreenerTimelineCopyHtml(row)}</li>`;
}

function renderOctopusGreenerChartSvg(periods, threshold) {
  const W = 680;
  const H = 190;
  const padL = 54;
  const padR = 12;
  const padT = 16;
  const padB = 30;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const scoreMax = 10;
  const now = Date.now();
  const rows = octopusCarbonPeriodsForChart(periods, now);
  if (!rows.length) {
    return `<p class="octopus-greener-empty">Half-hourly carbon forecast unavailable. Save a valid Octopus API key and account number with a UK postcode on your account.</p>`;
  }
  const greenScoreLine = octopusLowCarbonScoreGreenMin(threshold);
  const greenY = padT + chartH - (greenScoreLine / scoreMax) * chartH;
  const slotW = chartW / rows.length;
  const barW = Math.max(2, Math.min(8, slotW * 0.75));
  const barsMeta = rows.map((p) => ({
    start_ms: p.start_ms,
    end_ms: p.end_ms,
    score: octopusBarScore(p),
    gco2: p.gco2_per_kwh != null ? Math.round(Number(p.gco2_per_kwh)) : null,
    green: octopusCarbonPeriodIsGreen(p, threshold),
  }));
  const bars = rows
    .map((p, i) => {
      const score = octopusBarScore(p);
      const h = Math.max(2, (score / scoreMax) * chartH);
      const x = padL + i * slotW + (slotW - barW) / 2;
      const y = padT + chartH - h;
      const green = octopusCarbonPeriodIsGreen(p, threshold);
      const color = green ? "var(--octopus-green-bar, #22c55e)" : "var(--octopus-purple-bar, #8b5cf6)";
      const rx = Math.min(barW / 2, h / 2, 4);
      return `<rect class="octopus-greener-bar" data-bar-index="${i}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" fill="${color}" rx="${rx.toFixed(1)}" />`;
    })
    .join("");
  const tickCount = Math.min(7, rows.length);
  const xLabels = [];
  for (let i = 0; i < tickCount; i += 1) {
    const idx = tickCount === 1 ? 0 : Math.round((i / (tickCount - 1)) * (rows.length - 1));
    const row = rows[idx];
    const x = padL + idx * slotW + slotW / 2;
    const label =
      row.start_ms <= now && row.end_ms > now
        ? "Now"
        : formatOctopusChartTimeMs(row.start_ms);
    xLabels.push(
      `<text x="${x.toFixed(1)}" y="${H - 8}" text-anchor="middle" class="octopus-greener-axis">${esc(label)}</text>`
    );
  }
  const yMid = padT + chartH / 2;
  const yArrowTip = padT + 2;
  const yArrowBase = padT + 12;
  const barsJson = encodeURIComponent(JSON.stringify(barsMeta));
  const hitLeftPct = ((padL / W) * 100).toFixed(3);
  return `<div class="octopus-greener-chart-wrap">
${renderOctopusGreenerCarbonLegend(threshold)}
<div class="octopus-greener-chart-plot" data-octopus-greener-plot="1" data-chart-mode="carbon-day" data-chart-w="${W}" data-pad-l="${padL}" data-pad-t="${padT}" data-pad-b="${padB}" data-chart-inner-w="${chartW}" data-slot-w="${slotW}" data-bars="${barsJson}" style="--octopus-hit-left:${hitLeftPct}%">
<svg class="octopus-greener-chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Carbon intensity forecast chart">
<polygon points="24,${yArrowTip} 20,${yArrowBase} 28,${yArrowBase}" class="octopus-greener-y-arrow-head" />
<line x1="24" y1="${yArrowBase}" x2="24" y2="${(padT + chartH).toFixed(1)}" class="octopus-greener-y-arrow" />
<text x="14" y="${yMid.toFixed(1)}" transform="rotate(-90 14 ${yMid.toFixed(1)})" text-anchor="middle" class="octopus-greener-y-label">Low carbon score</text>
<line x1="${padL}" y1="${greenY.toFixed(1)}" x2="${W - padR}" y2="${greenY.toFixed(1)}" class="octopus-greener-green-line" stroke-dasharray="4 4" />
${bars}
${xLabels.join("")}
</svg>
<div class="octopus-greener-hit" aria-hidden="true"></div>
<div class="octopus-greener-tooltip" hidden role="tooltip"></div>
</div>
<p class="octopus-analysis-chart-hint">Hover bars for time, carbon score, and intensity</p>
</div>`;
}

function octopusCarbonDayTooltipHtml(bar) {
  const time = formatOctopusTooltipSlotRange(bar.start_ms, bar.end_ms);
  const scoreText = bar.score != null ? `${bar.score}/10` : "—";
  const gco2Text = bar.gco2 != null ? `${bar.gco2} gCO₂/kWh` : "—";
  const bandText = bar.green ? "Green" : "Not-so-green";
  return `<div class="octopus-greener-tooltip-time">${esc(time)}</div>
<div class="octopus-greener-tooltip-score">${esc(bandText)} · Low carbon score: <strong>${esc(scoreText)}</strong></div>
<div class="octopus-greener-tooltip-gco2">${esc(gco2Text)}</div>`;
}

function octopusGreenerChartBars(plot) {
  try {
    return JSON.parse(decodeURIComponent(plot?.dataset?.bars || "%5B%5D"));
  } catch {
    return [];
  }
}

function hideOctopusGreenerChartHover(plot) {
  if (!plot) return;
  const tooltip = plot.querySelector(".octopus-greener-tooltip");
  if (tooltip) tooltip.hidden = true;
  plot.querySelectorAll(".octopus-greener-bar").forEach((el) => {
    el.classList.remove("octopus-greener-bar--hover");
  });
}

function updateOctopusGreenerChartHover(plot, clientX) {
  const svg = plot.querySelector(".octopus-greener-chart-svg");
  const tooltip = plot.querySelector(".octopus-greener-tooltip");
  if (!svg || !tooltip) return false;
  const bars = octopusGreenerChartBars(plot);
  if (!bars.length) return false;
  const chartW = Number(plot.dataset.chartW) || 680;
  const padL = Number(plot.dataset.padL) || 54;
  const padT = Number(plot.dataset.padT) || 16;
  const chartInnerW = Number(plot.dataset.chartInnerW) || chartW - padL - 12;
  const slotW = Number(plot.dataset.slotW) || chartInnerW / bars.length;
  const rect = svg.getBoundingClientRect();
  if (!rect.width) return false;
  const scale = rect.width / chartW;
  const x = (clientX - rect.left) / scale;
  if (x < padL || x > padL + chartInnerW) {
    hideOctopusGreenerChartHover(plot);
    return false;
  }
  const idx = Math.min(bars.length - 1, Math.max(0, Math.floor((x - padL) / slotW)));
  const bar = bars[idx];
  if (!bar) {
    hideOctopusGreenerChartHover(plot);
    return false;
  }
  const chartMode = plot.dataset.chartMode || "day";
  tooltip.hidden = false;
  if (chartMode === "week") {
    const scoreText = bar.greenness_score != null ? `${bar.greenness_score}/100` : "—";
    const nightText = !bar.hasData ? "No forecast" : bar.is_greener_night ? "Greener night" : "Not a greener night";
    const indexText = bar.greenness_index ? String(bar.greenness_index) : "—";
    tooltip.innerHTML = `<div class="octopus-greener-tooltip-time">${esc(bar.shortDate || bar.label || bar.date || "—")}</div>
<div class="octopus-greener-tooltip-score">Greenness score: <strong>${esc(scoreText)}</strong></div>
<div class="octopus-greener-tooltip-gco2">${esc(nightText)}${bar.hasData && bar.greenness_index ? ` · ${esc(indexText)}` : ""}</div>`;
  } else if (
    chartMode === "import-rate" ||
    chartMode === "export-rate" ||
    chartMode === "consumption" ||
    chartMode === "dual"
  ) {
    tooltip.innerHTML = octopusChartTooltipHtml(chartMode, bar);
  } else {
    tooltip.innerHTML = octopusCarbonDayTooltipHtml(bar);
  }
  plot.querySelectorAll(".octopus-greener-bar").forEach((el, i) => {
    el.classList.toggle("octopus-greener-bar--hover", i === idx);
  });
  const cx = (padL + idx * slotW + slotW / 2) * scale;
  const plotRect = plot.getBoundingClientRect();
  let left = cx;
  const tipW = 168;
  if (left + tipW / 2 > plotRect.width - 8) left = plotRect.width - tipW / 2 - 8;
  if (left - tipW / 2 < 8) left = tipW / 2 + 8;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${Math.max(8, padT * scale - 6)}px`;
  return true;
}

function bindOctopusGreenerCharts(root) {
  root?.querySelectorAll("[data-octopus-greener-plot]:not([data-greener-bound])").forEach((plot) => {
    plot.dataset.greenerBound = "1";
    const hit = plot.querySelector(".octopus-greener-hit");
    if (!hit) return;
    const show = (clientX) => {
      updateOctopusGreenerChartHover(plot, clientX);
    };
    const hide = () => hideOctopusGreenerChartHover(plot);
    hit.addEventListener("mousemove", (ev) => show(ev.clientX));
    hit.addEventListener("mouseleave", hide);
    bindTouchChartScrub(hit, show, hide);
  });
}

/** Touch scrub on charts without blocking vertical page scroll on mobile. */
function bindTouchChartScrub(el, onScrub, onEnd) {
  if (!el) return;
  let startX = 0;
  let startY = 0;
  let scrubbing = false;
  el.addEventListener(
    "touchstart",
    (ev) => {
      const t = ev.touches[0];
      if (!t) return;
      startX = t.clientX;
      startY = t.clientY;
      scrubbing = false;
    },
    { passive: true }
  );
  el.addEventListener(
    "touchmove",
    (ev) => {
      const t = ev.touches[0];
      if (!t) return;
      const dx = t.clientX - startX;
      const dy = t.clientY - startY;
      if (!scrubbing) {
        if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 10) return;
        if (Math.abs(dx) > 10 || Math.abs(dy) > 10) scrubbing = true;
      }
      if (!scrubbing) return;
      ev.preventDefault();
      onScrub(t.clientX);
    },
    { passive: false }
  );
  const end = () => {
    scrubbing = false;
    onEnd?.();
  };
  el.addEventListener("touchend", end);
  el.addEventListener("touchcancel", end);
}

function renderOctopusGreenerTable(periods) {
  const rows = octopusCarbonPeriodsForChart(periods);
  if (!rows.length) {
    return `<p class="octopus-greener-empty">Half-hourly carbon forecast unavailable. Save a valid Octopus API key and account number with a UK postcode on your account.</p>`;
  }
  const body = rows
    .map((p) => {
      const score = p.low_carbon_score != null ? `${p.low_carbon_score}/10` : "—";
      const gco2 = p.gco2_per_kwh != null ? Math.round(Number(p.gco2_per_kwh)) : "—";
      return `<tr><td>${esc(formatOctopusPeriodRange(p.start_ms, p.end_ms))}</td><td>${esc(score)}</td><td>${esc(String(gco2))}</td></tr>`;
    })
    .join("");
  return `<div class="octopus-greener-table-wrap"><table class="octopus-greener-table">
<thead><tr><th>Time</th><th>Low carbon score</th><th>Carbon intensity (gCO₂/kWh)</th></tr></thead>
<tbody>${body}</tbody>
</table></div>`;
}

function renderOctopusGreenerTimeline(timeline) {
  const rows = Array.isArray(timeline) ? timeline : [];
  if (!rows.length) return "";
  const items = rows.map((row) => renderOctopusGreenerTimelineItem(row)).join("");
  return `<ul class="octopus-greener-timeline">${items}</ul>`;
}

function renderOctopusGreenerNightsCard(
  payload,
  { compact = false, view = "standard", energyPeriod = "day", energyPeriodOffset = 0 } = {}
) {
  if (!payload) {
    return `<div class="card octopus-greener-card${compact ? " octopus-greener-card--compact" : ""}" style="margin-top:14px">
${octopusAnalysisCardTitle(OCTOPUS_GREENER_CARD_TITLE, { compact })}
<p class="octopus-greener-empty chart-loading">Loading greener forecast…</p>
</div>`;
  }
  const isWeek = energyPeriod === "week";
  const threshold = Number(payload.green_threshold_gco2 ?? 99);
  const standardActive = view !== "detailed";
  let headline;
  let body;
  let introHtml;
  let nightsHint;
  if (isWeek) {
    const weekRows = octopusGreenerWeekRows(payload.greener_nights, energyPeriodOffset);
    headline = octopusGreenerWeekHeadline(weekRows);
    body = standardActive
      ? `${renderOctopusGreenerWeekChartSvg(payload.greener_nights, energyPeriodOffset)}${renderOctopusGreenerWeekTimeline(weekRows)}`
      : renderOctopusGreenerWeekTable(payload.greener_nights, energyPeriodOffset);
    const weekIntro = standardActive
      ? "Weekly greener nights forecast (23:00–06:00). Taller bars mean cleaner overnight energy."
      : "Daily greenness scores for the selected week from Octopus.";
    introHtml = `<p class="octopus-greener-intro">${esc(weekIntro)}</p>`;
    const weekLabel = energyPeriodNavLabel("week", energyPeriodOffset);
    nightsHint = `<p class="octopus-greener-hint">${esc(weekLabel)} · Octopus publishes up to seven nights ahead</p>`;
  } else {
    headline = payload.title || "Clean energy forecast";
    body = standardActive
      ? `${renderOctopusGreenerChartSvg(payload.carbon_periods, threshold)}${renderOctopusGreenerTimeline(payload.timeline)}`
      : renderOctopusGreenerTable(payload.carbon_periods);
    introHtml = standardActive
      ? renderOctopusGreenerDailyIntroHtml()
      : `<p class="octopus-greener-intro">Half-hourly low carbon score and regional carbon intensity from Octopus.</p>`;
    nightsHint =
      Array.isArray(payload.greener_nights) && payload.greener_nights.length
        ? `<p class="octopus-greener-hint">${payload.greener_nights.filter((n) => n.is_greener_night).length} greener night(s) in the next ${payload.greener_nights.length} days · ${payload.history_count || 0} snapshots stored</p>`
        : "";
  }
  const err = payload.errors?.greener_nights || payload.errors?.carbon || payload.errors?.account;
  const errHtml = err ? `<p class="octopus-greener-error">${esc(String(err))}</p>` : "";
  return `<div class="card octopus-greener-card${compact ? " octopus-greener-card--compact" : ""}" style="margin-top:14px" data-octopus-greener-card="1">
<div class="octopus-greener-head">
${octopusAnalysisCardTitle(OCTOPUS_GREENER_CARD_TITLE, { compact })}
<div class="octopus-greener-view-toggle" role="group" aria-label="Greener forecast view">
<button type="button" class="octopus-greener-view-btn${standardActive ? " active" : ""}" data-action="octopus-greener-view" data-view="standard" aria-pressed="${standardActive}">Graph</button>
<button type="button" class="octopus-greener-view-btn${!standardActive ? " active" : ""}" data-action="octopus-greener-view" data-view="detailed" aria-pressed="${!standardActive}">List</button>
</div>
</div>
<p class="octopus-greener-headline">${esc(headline)}</p>
${introHtml}
${nightsHint}${errHtml}
${body}
</div>`;
}

function renderOctopusRewardsCard(payload, { compact = false } = {}) {
  const rewards = payload?.rewards;
  if (!rewards) return "";
  const points = rewards.loyalty_points;
  const money = rewards.loyalty_monetary_amount;
  const balance = rewards.account_balance_pence;
  const rate = rewards.current_import_p_per_kwh;
  const hasPoints = points != null && Number.isFinite(Number(points));
  const hasCost = rate != null || balance != null;
  if (!hasPoints && !hasCost) return "";
  const pointsVal = hasPoints ? `${Number(points).toLocaleString()} Octopoints` : "—";
  const moneyVal = formatOctopusPointsValue(points, money);
  return `<div class="card octopus-rewards-card${compact ? " octopus-rewards-card--compact" : ""}" style="margin-top:14px" data-octopus-rewards-card="1">
<p class="card-title">Octopus account</p>
<div class="octopus-rewards-split">
<div class="octopus-rewards-pane">
<label>Octopoints</label>
<strong>${esc(pointsVal)}</strong>
${moneyVal ? `<span class="octopus-rewards-sub">${esc(moneyVal)}</span>` : ""}
</div>
<div class="octopus-rewards-pane">
<label>Current energy cost</label>
<strong>${esc(formatOctopusRate(rate))}</strong>
<span class="octopus-rewards-sub">Account balance ${esc(formatOctopusMoneyPence(balance))}</span>
</div>
</div>
</div>`;
}

function octopusAnalysisPayload(plantState) {
  const raw = plantState?.tariff?.octopus_analysis;
  return raw && typeof raw === "object" ? raw : null;
}

function formatSmartChargeMode(mode) {
  const m = String(mode || "").toLowerCase();
  if (m === "max_safety") return "Max Safety";
  if (m === "max_profit") return "Max Profit";
  if (m === "max_green") return "Max Green";
  return mode ? String(mode) : "—";
}

function formatSmartChargeKwh(v) {
  if (v == null || !Number.isFinite(Number(v))) return "—";
  return `${Number(v).toFixed(2)} kWh`;
}

function formatSmartChargeDuration(min) {
  if (min == null || !Number.isFinite(Number(min))) return "—";
  const m = Math.max(0, Math.round(Number(min)));
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h}h ${r}m` : `${h}h`;
}

function formatSmartChargeDateTimeMs(ms) {
  if (!Number.isFinite(ms)) return "—";
  return new Date(ms).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderSmartChargeSummaryCards(summary) {
  const s = summary || {};
  const cards = [
    {
      label: "Grid import (actual)",
      value: formatSmartChargeKwh(s.grid_import_kwh_actual),
      sub: s.grid_import_kwh_planned != null ? `Planned ${formatSmartChargeKwh(s.grid_import_kwh_planned)}` : "",
      tone: "import",
    },
    {
      label: "Grid export (actual)",
      value: formatSmartChargeKwh(s.grid_export_kwh_actual),
      sub: s.grid_export_kwh_planned != null ? `Planned ${formatSmartChargeKwh(s.grid_export_kwh_planned)}` : "",
      tone: "export",
    },
    {
      label: "Armed sessions",
      value: String(s.armed_sessions ?? 0),
      sub: `${s.import_sessions ?? 0} import · ${s.export_sessions ?? 0} export`,
      tone: "sessions",
    },
    {
      label: "Spread profit (theoretical)",
      value: s.theoretical_spread_profit_p != null ? `${Number(s.theoretical_spread_profit_p).toFixed(2)}p` : "—",
      sub: formatSmartChargeMode(s.operating_mode),
      tone: "profit",
    },
  ];
  return `<div class="fox-sc-analysis-summary">${cards
    .map(
      (c) => `<div class="fox-sc-analysis-card fox-sc-analysis-card--${esc(c.tone)}">
<div class="fox-sc-analysis-card-label">${esc(c.label)}</div>
<div class="fox-sc-analysis-card-value">${esc(c.value)}</div>
${c.sub ? `<div class="fox-sc-analysis-card-sub">${esc(c.sub)}</div>` : ""}
</div>`
    )
    .join("")}</div>`;
}

function renderSmartChargeDailyChartSvg(dailyChart) {
  const rows = (Array.isArray(dailyChart) ? dailyChart : []).filter((r) => r?.date);
  if (!rows.length) {
    return `<p class="octopus-greener-empty">No daily SmartCharge activity for this period.</p>`;
  }
  const mapped = rows.map((row) => {
    const d = new Date(`${row.date}T12:00:00`);
    return {
      start_ms: d.getTime(),
      label: d.toLocaleDateString(undefined, { day: "numeric", month: "short" }),
      import_actual: Number(row.import_actual_kwh) || 0,
      export_actual: Number(row.export_actual_kwh) || 0,
      import_planned: Number(row.import_planned_kwh) || 0,
      export_planned: Number(row.export_planned_kwh) || 0,
    };
  });
  const maxVal = Math.max(
    ...mapped.flatMap((r) => [r.import_actual, r.export_actual, r.import_planned, r.export_planned]),
    0.1
  );
  const W = 640;
  const H = 168;
  const padL = 28;
  const padR = 12;
  const padT = 12;
  const padB = 28;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const slotW = chartW / mapped.length;
  const barW = Math.max(2, slotW * 0.18);
  const bars = mapped
    .map((row, i) => {
      const x0 = padL + i * slotW + slotW * 0.08;
      const specs = [
        { key: "import_actual", color: "#2F6BFF" },
        { key: "import_planned", color: "#8DB6FF" },
        { key: "export_actual", color: "#FF6FAF" },
        { key: "export_planned", color: "#ffc2dd" },
      ];
      return specs
        .map((spec, j) => {
          const v = row[spec.key];
          const h = Math.max(1, (v / maxVal) * chartH);
          const x = x0 + j * (barW + 1);
          const y = padT + chartH - h;
          return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" fill="${spec.color}" rx="1" />`;
        })
        .join("");
    })
    .join("");
  const legend = `<div class="fox-sc-analysis-chart-legend">
<span><i style="background:#2F6BFF"></i> Import actual</span>
<span><i style="background:#8DB6FF"></i> Import planned</span>
<span><i style="background:#FF6FAF"></i> Export actual</span>
<span><i style="background:#ffc2dd"></i> Export planned</span>
</div>`;
  return `${legend}<svg class="fox-sc-analysis-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="SmartCharge daily import and export"><rect x="${padL}" y="${padT}" width="${chartW}" height="${chartH}" fill="none" stroke="var(--divider-color,#333)" stroke-opacity="0.25"/>${bars}</svg>`;
}

function renderSmartChargeSessionsTable(sessions) {
  const rows = Array.isArray(sessions) ? sessions : [];
  if (!rows.length) {
    return `<p class="placeholder">No armed SmartCharge sessions recorded in this period.</p>`;
  }
  const body = rows
    .slice()
    .sort((a, b) => (b.start_ms || 0) - (a.start_ms || 0))
    .map((row) => {
      const dir = row.direction === "export" ? "Export" : "Import";
      const actual =
        row.direction === "export"
          ? formatSmartChargeKwh(row.actual_export_kwh)
          : formatSmartChargeKwh(row.actual_import_kwh);
      const planned =
        row.direction === "export"
          ? formatSmartChargeKwh(row.planned_export_kwh)
          : formatSmartChargeKwh(row.planned_import_kwh);
      return `<tr>
<td>${esc(formatSmartChargeDateTimeMs(row.start_ms))}</td>
<td>${esc(dir)}</td>
<td>${esc(String(row.action || "—"))}</td>
<td>${esc(formatSmartChargeDuration(row.duration_min))}</td>
<td>${esc(actual)}</td>
<td>${esc(planned)}</td>
</tr>`;
    })
    .join("");
  return `<div class="table-wrap"><table class="data-table fox-sc-analysis-table">
<thead><tr><th>Started</th><th>Direction</th><th>Action</th><th>Duration</th><th>Actual</th><th>Planned</th></tr></thead>
<tbody>${body}</tbody>
</table></div>`;
}

function renderSmartChargePlannedTable(slots) {
  const rows = Array.isArray(slots) ? slots : [];
  if (!rows.length) {
    return `<p class="placeholder">No daily plan slots in recorder history for this period.</p>`;
  }
  const body = rows
    .map((row) => {
      const isExport = String(row.action || "").includes("export");
      const planned = isExport
        ? formatSmartChargeKwh(row.planned_export_kwh)
        : formatSmartChargeKwh(row.planned_import_kwh);
      return `<tr>
<td>${esc(formatSmartChargeDateTimeMs(row.start_ms))}</td>
<td>${esc(formatSmartChargeDateTimeMs(row.end_ms))}</td>
<td>${esc(String(row.action || "—"))}</td>
<td>${esc(String(row.reason || "—"))}</td>
<td>${esc(planned)}</td>
</tr>`;
    })
    .join("");
  return `<div class="table-wrap"><table class="data-table fox-sc-analysis-table">
<thead><tr><th>Start</th><th>End</th><th>Action</th><th>Reason</th><th>Planned kWh</th></tr></thead>
<tbody>${body}</tbody>
</table></div>`;
}

function renderSmartChargeAnalysisPage(report, { loading = false } = {}) {
  if (loading && !report) {
    return `<div data-smart-charge-analysis-main="1"><header class="header"><h1>SmartCharge Analysis</h1></header><p class="chart-loading">Loading SmartCharge analysis…</p></div>`;
  }
  if (!report || report.enabled === false) {
    return `<div data-smart-charge-analysis-main="1"><header class="header"><h1>SmartCharge Analysis</h1></header><p class="placeholder">Enable SmartCharge in Settings → SmartCharge to use this report.</p></div>`;
  }
  if (report.error) {
    return `<div data-smart-charge-analysis-main="1"><header class="header"><h1>SmartCharge Analysis</h1><p class="placeholder">${esc(report.error)}</p></div>`;
  }
  const hint = report.hint ? `<p class="field-hint">${esc(report.hint)}</p>` : "";
  return `<div data-smart-charge-analysis-main="1">
<header class="header"><h1>SmartCharge Analysis</h1><p>${esc(report.period_label || "")}</p></header>
${hint}
${renderSmartChargeSummaryCards(report.summary)}
<div class="card fox-report-chart-card fox-analysis-chart-card">
<h3 class="fox-analysis-summary-title fox-analysis-chart-title">Daily import &amp; export</h3>
${renderSmartChargeDailyChartSvg(report.daily_chart)}
</div>
<div class="card fox-report-details">
<h3 class="fox-report-details-title">Armed sessions</h3>
${renderSmartChargeSessionsTable(report.sessions)}
</div>
<div class="card fox-report-details">
<h3 class="fox-report-details-title">Planned slots (from daily plan history)</h3>
${renderSmartChargePlannedTable(report.planned_slots)}
</div>
</div>`;
}

function octopusConsumptionDailyTotals(consumption, days = 14) {
  const map = new Map();
  for (const row of Array.isArray(consumption) ? consumption : []) {
    if (!Number.isFinite(row?.start_ms)) continue;
    const d = new Date(row.start_ms);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    map.set(key, (map.get(key) || 0) + Number(row.kwh || 0));
  }
  return [...map.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-days)
    .map(([date, kwh]) => ({ date, kwh: Math.round(kwh * 100) / 100 }));
}

function renderOctopusGenericBarChartSvg(rows, {
  valueKey,
  maxValue = null,
  colorFn = () => "#22c55e",
  emptyHint = "No data available.",
  ariaLabel = "Chart",
  chartMode = "generic",
  overlaySvg = "",
  barsMetaFn = null,
} = {}) {
  const data = (Array.isArray(rows) ? rows : []).filter((r) => r?.start_ms != null);
  if (!data.length) return `<p class="octopus-greener-empty">${esc(emptyHint)}</p>`;
  const W = 640;
  const H = 168;
  const padL = 28;
  const padR = 12;
  const padT = 12;
  const padB = 28;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const slotW = chartW / data.length;
  const barW = Math.max(2, slotW * 0.72);
  const values = data.map((r) => {
    const v = r[valueKey];
    return v != null && Number.isFinite(Number(v)) ? Number(v) : 0;
  });
  const peak =
    maxValue != null && Number.isFinite(Number(maxValue)) ? Number(maxValue) : Math.max(...values, 0.01);
  const barsMeta = data.map((row, i) => {
    const base = {
      start_ms: row.start_ms,
      end_ms: row.end_ms,
      label: row.label,
      value: values[i],
      [valueKey]: row[valueKey],
    };
    const extra = barsMetaFn ? barsMetaFn(row, values[i]) : row;
    return { ...base, ...extra };
  });
  const bars = data
    .map((row, i) => {
      const v = values[i];
      const h = Math.max(2, (v / peak) * chartH);
      const x = padL + i * slotW + (slotW - barW) / 2;
      const y = padT + chartH - h;
      const color = colorFn(row, v);
      return `<rect class="octopus-greener-bar" data-bar-index="${i}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" fill="${color}" rx="2" />`;
    })
    .join("");
  const tickCount = Math.min(7, data.length);
  const labels = [];
  for (let i = 0; i < tickCount; i += 1) {
    const idx = tickCount === 1 ? 0 : Math.round((i / (tickCount - 1)) * (data.length - 1));
    const row = data[idx];
    const x = padL + idx * slotW + slotW / 2;
    const label = row.label || formatOctopusChartTimeMs(row.start_ms);
    labels.push(
      `<text x="${x.toFixed(1)}" y="${H - 8}" text-anchor="middle" class="octopus-greener-axis">${esc(label)}</text>`
    );
  }
  const barsJson = encodeURIComponent(JSON.stringify(barsMeta));
  const hitLeftPct = ((padL / W) * 100).toFixed(3);
  return `<div class="octopus-greener-chart-plot" data-octopus-greener-plot="1" data-chart-mode="${esc(chartMode)}" data-chart-w="${W}" data-pad-l="${padL}" data-pad-t="${padT}" data-pad-b="${padB}" data-chart-inner-w="${chartW}" data-slot-w="${slotW}" data-bars="${barsJson}" style="--octopus-hit-left:${hitLeftPct}%">
<svg class="octopus-greener-chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(ariaLabel)}">${bars}${overlaySvg}${labels.join("")}</svg>
<div class="octopus-greener-hit" aria-hidden="true"></div>
<div class="octopus-greener-tooltip" hidden role="tooltip"></div>
</div>`;
}

function renderOctopusRateChartSvg(slots, { kind = "import" } = {}) {
  const rows = (Array.isArray(slots) ? slots : []).filter((s) => s?.start_ms != null);
  const color = kind === "export" ? "#f59e0b" : "#03a9f4";
  const chartMode = kind === "export" ? "export-rate" : "import-rate";
  const chart = renderOctopusGenericBarChartSvg(rows, {
    valueKey: "p_per_kwh",
    colorFn: () => color,
    emptyHint:
      kind === "export"
        ? "Export unit rates unavailable. Connect Octopus with an export meter."
        : "Import unit rates unavailable. Connect Octopus native tariff or refresh rates.",
    ariaLabel: `${kind} unit rate chart`,
    chartMode,
    barsMetaFn: (row) => ({ p_per_kwh: row.p_per_kwh }),
  });
  if (!chart.includes("octopus-greener-chart-plot")) return chart;
  const legendLabel = kind === "export" ? "Export unit rate" : "Import unit rate";
  return `${chart}<p class="octopus-analysis-chart-hint"><i class="octopus-analysis-swatch" style="background:${color}"></i> ${esc(legendLabel)} — hover bars for time and price</p>`;
}

function octopusDualPriceLinePoints(rows, rateKey, maxRate, padL, padT, chartH, slotW) {
  return rows
    .map((row, i) => {
      const rate = row[rateKey];
      if (rate == null || !Number.isFinite(Number(rate))) return null;
      const x = padL + i * slotW + slotW / 2;
      const y = padT + chartH - (Number(rate) / Math.max(0.01, maxRate)) * chartH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .filter(Boolean)
    .join(" ");
}

function renderOctopusDualChartSvg(dualPeriods) {
  const rows = (Array.isArray(dualPeriods) ? dualPeriods : []).filter((p) => p?.start_ms != null);
  if (!rows.length) {
    return `<p class="octopus-greener-empty">Price and carbon overlay unavailable. Save Octopus API credentials and postcode.</p>`;
  }
  const rates = rows
    .flatMap((r) => [r.p_per_kwh, r.export_p_per_kwh])
    .map((v) => (v != null ? Number(v) : null))
    .filter((v) => v != null && Number.isFinite(v));
  const maxRate = rates.length ? Math.max(...rates) : 1;
  const W = 640;
  const H = 168;
  const padL = 28;
  const padR = 12;
  const padT = 12;
  const padB = 28;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const slotW = chartW / rows.length;
  const importPoints = octopusDualPriceLinePoints(rows, "p_per_kwh", maxRate, padL, padT, chartH, slotW);
  const exportPoints = octopusDualPriceLinePoints(
    rows,
    "export_p_per_kwh",
    maxRate,
    padL,
    padT,
    chartH,
    slotW
  );
  const importLine = importPoints
    ? `<polyline points="${importPoints}" fill="none" stroke="#03a9f4" stroke-width="2" stroke-linejoin="round" opacity="0.9" />`
    : "";
  const exportLine = exportPoints
    ? `<polyline points="${exportPoints}" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linejoin="round" opacity="0.9" />`
    : "";
  const chart = renderOctopusGenericBarChartSvg(rows, {
    valueKey: "low_carbon_score",
    maxValue: 10,
    colorFn: (row) => (octopusCarbonPeriodIsGreen(row) ? "#22c55e" : "#8b5cf6"),
    emptyHint: "No carbon periods.",
    ariaLabel: "Price and carbon overlay chart",
    chartMode: "dual",
    overlaySvg: `${importLine}${exportLine}`,
    barsMetaFn: (row) => ({
      low_carbon_score: row.low_carbon_score,
      p_per_kwh: row.p_per_kwh,
      export_p_per_kwh: row.export_p_per_kwh,
      is_green: octopusCarbonPeriodIsGreen(row),
      gco2: row.gco2_per_kwh != null ? Math.round(Number(row.gco2_per_kwh)) : null,
    }),
  });
  return `<div class="octopus-analysis-dual-wrap">
<div class="octopus-analysis-dual-legend">
<span><i class="octopus-analysis-swatch octopus-analysis-swatch--green"></i> Low carbon</span>
<span><i class="octopus-analysis-swatch octopus-analysis-swatch--purple"></i> Higher carbon</span>
<span><i class="octopus-analysis-swatch-line octopus-analysis-swatch-line--import"></i> Import price</span>
<span><i class="octopus-analysis-swatch-line octopus-analysis-swatch-line--export"></i> Export price</span>
</div>
${chart}
<p class="octopus-analysis-chart-hint">Hover bars for carbon score, import/export prices, and time</p>
</div>`;
}

function renderOctopusConsumptionChartSvg(consumption) {
  const daily = octopusConsumptionDailyTotals(consumption, 14);
  if (!daily.length) {
    return `<p class="octopus-greener-empty">Smart-meter import unavailable. Consumption is polled every 30 minutes when Octopus is connected — check back after the next poll.</p>`;
  }
  const rows = daily.map((d) => ({
    start_ms: Date.parse(`${d.date}T12:00:00`),
    label: d.date.slice(5),
    kwh: d.kwh,
  }));
  const chart = renderOctopusGenericBarChartSvg(rows, {
    valueKey: "kwh",
    colorFn: () => "#699BFF",
    emptyHint: "No consumption data.",
    ariaLabel: "Daily import consumption",
    chartMode: "consumption",
    barsMetaFn: (row) => ({ kwh: row.kwh }),
  });
  if (!chart.includes("octopus-greener-chart-plot")) return chart;
  return `${chart}<p class="octopus-analysis-chart-hint"><i class="octopus-analysis-swatch" style="background:#699BFF"></i> Daily import — hover bars for kWh</p>`;
}

function renderOctopusComplianceCard(compliance) {
  if (!compliance) {
    return `<div class="card octopus-analysis-card"><h3 class="fox-analysis-summary-title fox-analysis-chart-title">Greener Nights alignment</h3><p class="octopus-greener-empty">Overnight alignment is calculated from polled smart-meter import (every 30 minutes).</p></div>`;
  }
  const pct = compliance.alignment_pct;
  const pctText = pct != null ? `${pct}%` : "—";
  const tierHint =
    compliance.projected_octopoints
      ? `On track for ~${compliance.projected_octopoints.toLocaleString()} Octopoints this month (IOG rewards use EV charging data from Octopus).`
      : compliance.next_tier
        ? `Reach ${compliance.next_tier.label} overnight alignment for ~${compliance.next_tier.points.toLocaleString()} Octopoints.`
        : "Charge or import more during greener nights (11pm–6am) to improve alignment.";
  return `<div class="card octopus-analysis-card" data-octopus-compliance-card="1">
<h3 class="fox-analysis-summary-title fox-analysis-chart-title">Greener Nights alignment</h3>
<p class="octopus-greener-intro">Overnight import on greener nights this month (${esc(compliance.month || "")}).</p>
<div class="octopus-analysis-metrics">
<div class="octopus-analysis-metric"><label>Alignment</label><strong>${esc(pctText)}</strong></div>
<div class="octopus-analysis-metric"><label>Overnight import</label><strong>${esc(String(compliance.overnight_kwh ?? "—"))} kWh</strong></div>
<div class="octopus-analysis-metric"><label>On greener nights</label><strong>${esc(String(compliance.greener_overnight_kwh ?? "—"))} kWh</strong></div>
</div>
<p class="octopus-greener-hint">${esc(tierHint)}</p>
<p class="octopus-greener-hint">${esc(compliance.note || "")}</p>
</div>`;
}

function renderOctopusCarbonInsightsCard(extremes) {
  if (!extremes?.best_start_ms && !extremes?.worst_start_ms) return "";
  const best = extremes.best_start_ms ? formatOctopusChartTimeMs(extremes.best_start_ms) : "—";
  const worst = extremes.worst_start_ms ? formatOctopusChartTimeMs(extremes.worst_start_ms) : "—";
  const bestG = extremes.best_gco2 != null ? `${Math.round(extremes.best_gco2)}g` : "—";
  const worstG = extremes.worst_gco2 != null ? `${Math.round(extremes.worst_gco2)}g` : "—";
  return `<div class="card octopus-analysis-card">
<h3 class="fox-analysis-summary-title fox-analysis-chart-title">Carbon insights (next 24h)</h3>
<div class="octopus-analysis-metrics">
<div class="octopus-analysis-metric"><label>Cleanest period</label><strong>${esc(best)}</strong><span class="octopus-greener-hint">${esc(bestG)} CO₂/kWh</span></div>
<div class="octopus-analysis-metric"><label>Highest carbon</label><strong>${esc(worst)}</strong><span class="octopus-greener-hint">${esc(worstG)} CO₂/kWh</span></div>
</div>
</div>`;
}

function renderOctopusForecastHistoryCard(history, greenerNights) {
  const flips = Array.isArray(history?.forecast_flips) ? history.forecast_flips : [];
  const nights = Array.isArray(greenerNights) ? greenerNights : [];
  const changed = nights.filter((n) => n.forecast_changed);
  if (!flips.length && !changed.length && !(history?.snapshot_count > 1)) {
    return `<div class="card octopus-analysis-card"><h3 class="fox-analysis-summary-title fox-analysis-chart-title">Forecast history</h3><p class="octopus-greener-hint">Daily greener-night snapshots will build here (${esc(String(history?.snapshot_count || 0))} stored).</p></div>`;
  }
  const flipRows = flips
    .slice(0, 6)
    .map(
      (f) =>
        `<li><strong>${esc(f.date)}</strong> — changed from ${esc(f.from)} to ${esc(f.to)} (${esc(String(f.recorded_at || "").slice(0, 16))})</li>`
    )
    .join("");
  const changedRows = changed
    .slice(0, 4)
    .map((n) => {
      const was = n.was_greener_night ? "was greener" : "was not greener";
      const now = n.is_greener_night ? "now greener" : "no longer greener";
      return `<li><strong>${esc(n.date)}</strong> — ${was}, ${now}${n.greenness_index ? ` (${esc(String(n.greenness_index))})` : ""}</li>`;
    })
    .join("");
  return `<div class="card octopus-analysis-card">
<h3 class="fox-analysis-summary-title fox-analysis-chart-title">Forecast history</h3>
<p class="octopus-greener-intro">${esc(String(history?.snapshot_count || 0))} daily snapshots stored. Dates ever flagged greener stay recorded even if Octopus later changes the forecast.</p>
${flipRows ? `<ul class="octopus-analysis-list">${flipRows}</ul>` : ""}
${changedRows ? `<ul class="octopus-analysis-list">${changedRows}</ul>` : ""}
</div>`;
}

function renderOctopusEnergyAnalysisPage(payload, { loading = false, greenerView = "standard" } = {}) {
  if (loading) {
    return `<div data-octopus-analysis-main="1"><header class="header"><h1>Octopus Energy Analysis</h1><p class="chart-loading">Loading Octopus data…</p></header></div>`;
  }
  if (!payload) {
    return `<div data-octopus-analysis-main="1"><header class="header"><h1>Octopus Energy Analysis</h1></header><p class="placeholder">Enable Octopus as your dynamic tariff provider in Settings → Tariff to use this report.</p></div>`;
  }
  const err = payload.errors?.auth || payload.errors?.consumption || payload.errors?.carbon;
  const errHtml = err ? `<p class="octopus-greener-error">${esc(String(err))}</p>` : "";
  const rewardsHtml = renderOctopusRewardsCard(payload, { compact: false });
  const greenerCard = renderOctopusGreenerNightsCard(
    {
      ...payload,
      greener_nights: payload.greener_nights,
      carbon_periods: payload.carbon_periods,
      timeline: payload.timeline,
      title: payload.greener_title,
    },
    { compact: false, view: greenerView, energyPeriod: "day", energyPeriodOffset: 0 }
  );
  const weekCard = renderOctopusUpcomingWeekCard(payload);
  const tariffLabel = payload.import_tariff_code
    ? `${payload.tariff_type || "tariff"} · ${payload.import_tariff_code}`
    : "Octopus tariff not linked — use native Octopus connection for live rates";
  return `<div data-octopus-analysis-main="1">
<header class="header"><h1>Octopus Energy Analysis</h1><p>${esc(tariffLabel)}${payload.fetched_at ? ` · updated ${esc(String(payload.fetched_at).slice(0, 16).replace("T", " "))}` : ""}</p></header>
${errHtml}
${rewardsHtml}
<div class="octopus-analysis-grid">
<div class="card octopus-analysis-card"><h3 class="fox-analysis-summary-title fox-analysis-chart-title">Import price (48h)</h3>${renderOctopusRateChartSvg(payload.import_rate_slots, { kind: "import" })}</div>
<div class="card octopus-analysis-card"><h3 class="fox-analysis-summary-title fox-analysis-chart-title">Export price (48h)</h3>${renderOctopusRateChartSvg(payload.export_rate_slots, { kind: "export" })}</div>
</div>
<div class="card octopus-analysis-card"><h3 class="fox-analysis-summary-title fox-analysis-chart-title">Price and carbon overlay</h3><p class="octopus-greener-intro">Bars show low carbon score; blue line is import price and amber is export price — look for cheap, green periods to run loads or charge the battery.</p>${renderOctopusDualChartSvg(payload.dual_periods)}</div>
${renderOctopusCarbonInsightsCard(payload.carbon_extremes)}
${renderOctopusComplianceCard(payload.compliance)}
<div class="card octopus-analysis-card"><h3 class="fox-analysis-summary-title fox-analysis-chart-title">Smart-meter import (14 days)</h3>${renderOctopusConsumptionChartSvg(payload.consumption)}</div>
${renderOctopusForecastHistoryCard(payload.history, payload.greener_nights)}
${greenerCard}
${weekCard}
</div>`;
}

function parseSolcastPeriodMs(raw) {
  if (raw == null || raw === "") return NaN;
  if (typeof raw === "number") return raw > 1e12 ? raw : raw * 1000;
  const text = String(raw).trim();
  if (!text) return NaN;
  if (/^\d+(\.\d+)?$/.test(text)) {
    const n = Number(text);
    return n > 1e12 ? n : n * 1000;
  }
  let t = Date.parse(text);
  if (Number.isFinite(t)) return t;
  t = Date.parse(text.replace(" ", "T"));
  if (Number.isFinite(t)) return t;
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(text)) {
    t = Date.parse(`${text.replace(" ", "T")}Z`);
    if (Number.isFinite(t)) return t;
  }
  return NaN;
}

function detailedForecastToChartPoints(rows, range, { extendFuture = false } = {}) {
  if (!Array.isArray(rows) || rows.length < 2) return [];
  const raw = rows
    .map((row) => {
      const t = parseSolcastPeriodMs(row.period_start ?? row.period_end ?? row.period);
      let v = Number(row.pv_estimate ?? row.pv_power_rooftop ?? row.power ?? row.pv_power);
      if (!Number.isFinite(t) || !Number.isFinite(v)) return null;
      if (Math.abs(v) > 50) v /= 1000;
      return { t, v };
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t);
  if (raw.length < 2) return [];

  const graceMs = 36e5;
  let relevant = raw.filter((p) => p.t >= range.tMin - graceMs && p.t <= range.tMax);
  if (relevant.length < 2) {
    relevant = raw.filter((p) => p.t >= range.nowMs - STATISTICS_PERIOD_MS * 2 && p.t <= range.tMax);
  }
  if (relevant.length < 2) return [];

  let out = interpolatePointsToPeriod(relevant, STATISTICS_PERIOD_MS, range.tMin, range.tMax, {
    allowBackfill: false,
  });
  const nowMs = range?.nowMs ?? Date.now();
  if (
    extendFuture &&
    out.length >= 2 &&
    range.tMax > nowMs + STATISTICS_PERIOD_MS &&
    !forecastHasFuturePoints(out, nowMs)
  ) {
    const intervals = buildSolcastIntervalSeries(rows);
    const extra = [];
    for (let t = Math.max(out[out.length - 1].t + STATISTICS_PERIOD_MS, nowMs); t <= range.tMax; t += STATISTICS_PERIOD_MS) {
      let v = solcastKwAtTime(rows, t);
      if (v == null && intervals.length) v = intervals[intervals.length - 1].v;
      if (v != null) extra.push({ t, v });
    }
    if (extra.length) out = [...out, ...extra];
  }
  return out;
}

function solcastIntradayForecastPoints(plantState, range) {
  const rows = plantState?.solcast?.forecast_intraday_points;
  if (!Array.isArray(rows) || rows.length < 2) return [];
  return rows
    .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v) && p.t >= range.tMin && p.t <= range.tMax)
    .map((p) => ({ t: p.t, v: p.v }))
    .sort((a, b) => a.t - b.t);
}

function nativeSolcastForecastPoints(plantState, range, hass, extraState) {
  let intraday = solcastIntradayForecastPoints(plantState, range);
  if (extraState) {
    const extra = solcastIntradayForecastPoints(extraState, range);
    if (extra.length > intraday.length) intraday = extra;
  }
  const detailed = detailedForecastToChartPoints(
    resolveBestSolcastDetailedRows(plantState, extraState, hass),
    range
  );
  const nowMs = range?.nowMs ?? Date.now();
  return mergeForecastPointsWithFuture(intraday, detailed, nowMs);
}

function buildForecastSeriesPoints(plantState, range, hass, extraState) {
  if (!statisticsSolcastForecastEnabled(plantState, hass)) return [];
  return nativeSolcastForecastPoints(plantState, range, hass, extraState);
}

function pvConfigSummary(pv) {
  const cfg = normalizePvConfig(pv);
  return `PV1: ${pvStringSummary(cfg.pv1)} · PV2: ${pvStringSummary(cfg.pv2)}`;
}

function parseTariffRate(raw) {
  if (raw == null || raw === "") return 0;
  const v = parseFloat(String(raw).trim());
  return Number.isFinite(v) ? Math.max(0, v) : 0;
}

function normalizeTariffSchedule(raw) {
  const base = DEFAULT_TARIFF.schedule;
  const src = raw && typeof raw === "object" ? raw : {};
  const hoursRaw = Array.isArray(src.hours) ? src.hours : base.hours;
  const hours = [];
  for (let i = 0; i < 24; i += 1) {
    const v = parseInt(String(hoursRaw[i] ?? 0), 10);
    hours.push(Number.isFinite(v) ? Math.max(0, Math.min(3, v)) : 0);
  }
  const bandsRaw = Array.isArray(src.bands) ? src.bands : base.bands;
  const bands = [];
  for (let i = 0; i < 4; i += 1) {
    const b = bandsRaw[i] && typeof bandsRaw[i] === "object" ? bandsRaw[i] : {};
    bands.push({
      import_p_per_kwh: parseTariffRate(b.import_p_per_kwh),
      export_p_per_kwh: parseTariffRate(b.export_p_per_kwh),
    });
  }
  return { hours, bands };
}

function normalizeTariffImportSource(v) {
  const s = String(v || "schedule");
  if (s === "entity") return "entity";
  if (s === "manual") return "schedule";
  return "schedule";
}

function normalizeTariffExportSource(v) {
  return normalizeTariffImportSource(v);
}

function normalizeTariffStandingSource(v) {
  const s = String(v || "plugin");
  if (s === "entity") return "entity";
  if (s === "manual") return "plugin";
  return "plugin";
}

/** True when native Octopus API owns the daily schedule (not Agile/Tracker). */
function octopusNativeManagesSchedule(tariff, octopusDraft) {
  const draft = octopusDraft && typeof octopusDraft === "object" ? octopusDraft : {};
  const dyn = tariff?.dynamic ?? {};
  const live = tariff?.octopus ?? {};
  const enabled = draft.enabled !== undefined ? draft.enabled : dyn.enabled;
  const source = draft.source !== undefined ? draft.source : dyn.source;
  if (!enabled || source === "entity") return false;
  if (!live.connected) return false;
  const tariffType = live.tariff_type ? String(live.tariff_type) : "";
  if (tariffType === "agile" || tariffType === "tracker") return false;
  return true;
}

/** True when a native tariff API (e.g. Octopus fixed tariff) owns the plugin standing charge. */
function tariffApiLocksStandingCharge(tariff, octopusDraft) {
  if (normalizeTariffStandingSource(tariff?.standing_source) !== "plugin") return false;
  return octopusNativeManagesSchedule(tariff, octopusDraft);
}

function normalizeOctopusDraft(raw, octopusLive) {
  const base = DEFAULT_TARIFF.dynamic;
  const t = raw && typeof raw === "object" ? raw : {};
  const live = octopusLive && typeof octopusLive === "object" ? octopusLive : {};
  const entity = (v) => {
    const s = v ? String(v).trim() : "";
    return s || "";
  };
  return {
    enabled: Boolean(t.enabled),
    provider: t.provider ? String(t.provider) : "octopus",
    source: t.source === "entity" ? "entity" : "native",
    api_key: "",
    api_key_set: Boolean(t.api_key_set ?? live.api_key_set),
    account_number: entity(t.account_number ?? live.account_number),
    import_mpan: entity(t.import_mpan ?? live.import_mpan),
    export_mpan: entity(t.export_mpan ?? live.export_mpan),
    import_entity: entity(t.import_entity),
    export_entity: entity(t.export_entity),
  };
}

function normalizeTariffDraft(raw) {
  const t = { ...DEFAULT_TARIFF, ...(raw && typeof raw === "object" ? raw : {}) };
  const entity = (v) => {
    const s = v ? String(v).trim() : "";
    return s || null;
  };
  const schedule = normalizeTariffSchedule(t.schedule);
  if (parseTariffRate(t.import_p_per_kwh) > 0 && schedule.bands[0].import_p_per_kwh <= 0) {
    schedule.bands[0].import_p_per_kwh = parseTariffRate(t.import_p_per_kwh);
  }
  if (parseTariffRate(t.export_p_per_kwh) > 0 && schedule.bands[0].export_p_per_kwh <= 0) {
    schedule.bands[0].export_p_per_kwh = parseTariffRate(t.export_p_per_kwh);
  }
  return {
    kind: t.kind === "dynamic" ? "dynamic" : "static",
    currency: normalizeTariffCurrency(t.currency),
    import_source: normalizeTariffImportSource(t.import_source),
    import_entity: entity(t.import_entity),
    import_p_per_kwh: parseTariffRate(t.import_p_per_kwh),
    export_source: normalizeTariffExportSource(t.export_source),
    export_entity: entity(t.export_entity),
    export_p_per_kwh: parseTariffRate(t.export_p_per_kwh),
    standing_source: normalizeTariffStandingSource(t.standing_source),
    standing_entity: entity(t.standing_entity),
    standing_charge_p_per_day: parseTariffRate(t.standing_charge_p_per_day),
    schedule,
    dynamic: normalizeOctopusDraft(t.dynamic, null),
  };
}

function tariffScheduleBandIndex(tariff, tMs) {
  const schedule = normalizeTariffSchedule(tariff?.schedule);
  const hour = new Date(tMs).getHours();
  return schedule.hours[hour] ?? 0;
}

function buildTariffSavePayload(draft) {
  const normalized = normalizeTariffDraft(draft);
  const schedule = normalizeTariffSchedule(normalized.schedule);
  if (normalized.import_source === "schedule") {
    normalized.import_p_per_kwh = schedule.bands[0]?.import_p_per_kwh ?? 0;
  }
  if (normalized.export_source === "schedule") {
    normalized.export_p_per_kwh = schedule.bands[0]?.export_p_per_kwh ?? 0;
  }
  return {
    kind: normalized.kind,
    currency: normalized.currency,
    import_source: normalized.import_source,
    import_entity: normalized.import_entity,
    import_p_per_kwh: normalized.import_p_per_kwh,
    export_source: normalized.export_source,
    export_entity: normalized.export_entity,
    export_p_per_kwh: normalized.export_p_per_kwh,
    standing_source: normalized.standing_source,
    standing_entity: normalized.standing_entity,
    standing_charge_p_per_day: normalized.standing_charge_p_per_day,
    schedule,
    dynamic: {
      enabled: Boolean(normalized.dynamic?.enabled),
      provider: normalized.dynamic?.provider || "",
      source: normalized.dynamic?.source === "entity" ? "entity" : "native",
      account_number: normalized.dynamic?.account_number || null,
      import_mpan: normalized.dynamic?.import_mpan || null,
      export_mpan: normalized.dynamic?.export_mpan || null,
      import_entity: normalized.dynamic?.import_entity || null,
      export_entity: normalized.dynamic?.export_entity || null,
    },
  };
}

function tariffSaveErrorMessage(err) {
  if (!err) return "Save failed";
  const bits = [err.message, err.code, err.error?.message, err.error?.code].filter(Boolean);
  const msg = bits.find((b) => b && b !== "Unknown error") || bits[0];
  return msg || "Save failed";
}

function tariffRatesAtTime(tariff, tMs) {
  const t = tariff && typeof tariff === "object" ? tariff : {};
  const schedule = normalizeTariffSchedule(t.schedule);
  const bandIdx = tariffScheduleBandIndex(t, tMs);
  const band = schedule.bands[bandIdx] ?? schedule.bands[0];
  const eff = tariffEffectiveRates(t);
  return {
    import_p_per_kwh:
      normalizeTariffImportSource(t.import_source) === "schedule"
        ? parseTariffRate(band?.import_p_per_kwh)
        : eff.import_p_per_kwh,
    export_p_per_kwh:
      normalizeTariffExportSource(t.export_source) === "schedule"
        ? parseTariffRate(band?.export_p_per_kwh)
        : eff.export_p_per_kwh,
    standing_charge_p_per_day: eff.standing_charge_p_per_day,
  };
}

function tariffEffectiveRates(tariff) {
  const t = tariff && typeof tariff === "object" ? tariff : {};
  const eff = t.effective ?? {};
  return {
    import_p_per_kwh: parseTariffRate(eff.import_p_per_kwh ?? t.import_p_per_kwh),
    export_p_per_kwh: parseTariffRate(eff.export_p_per_kwh ?? t.export_p_per_kwh),
    standing_charge_p_per_day: parseTariffRate(
      eff.standing_charge_p_per_day ?? t.standing_charge_p_per_day
    ),
  };
}

async function fetchTariffEntityCandidates(hass) {
  const res = await hass.connection.sendMessagePromise({ type: "foxess_plant/tariff_entity_candidates" });
  return res?.entities ?? [];
}

const TARIFF_IMPORT_HINTS = ["import", "consumption", "buy", "unit_rate", "electricity", "glow", "octopus", "agile", "tariff", "rate"];
const TARIFF_EXPORT_HINTS = ["export", "feed_in", "feed-in", "feedin", "seg", "sell", "tariff", "rate"];
const TARIFF_STANDING_HINTS = ["standing", "daily_charge", "daily_standing", "standing_charge", "fixed", "daily"];

function tariffSensorEntityFilter(state) {
  if (!state?.entity_id?.startsWith("sensor.")) return false;
  if (state.state == null || state.state === "" || state.state === "unknown" || state.state === "unavailable") {
    return false;
  }
  const v = parseFloat(String(state.state));
  return Number.isFinite(v);
}

function suggestedTariffEntitiesForKind(hass, kind, limit = 5) {
  if (!hass?.states) return [];
  const hints =
    kind === "export" ? TARIFF_EXPORT_HINTS : kind === "standing" ? TARIFF_STANDING_HINTS : TARIFF_IMPORT_HINTS;
  const rows = [];
  for (const entityId of Object.keys(hass.states)) {
    const state = hass.states[entityId];
    if (!tariffSensorEntityFilter(state)) continue;
    const blob = `${entityId} ${state.attributes?.friendly_name || ""}`.toLowerCase();
    const matched = hints.some((hint) => blob.includes(hint));
    if (!matched) continue;
    if (kind === "import" && (blob.includes("export") || blob.includes("feed"))) continue;
    if (kind === "export" && (blob.includes("import") || blob.includes("consumption"))) continue;
    rows.push({
      entity_id: entityId,
      name: state.attributes?.friendly_name || entityId,
      state: state.state,
      unit: state.attributes?.unit_of_measurement || "",
    });
  }
  rows.sort((a, b) => a.name.localeCompare(b.name));
  return rows.slice(0, limit);
}

function tariffSuggestedEntitiesHint(hass, kind) {
  const rows = suggestedTariffEntitiesForKind(hass, kind);
  if (!rows.length) return "Search by sensor name or entity id (e.g. sensor.octopus_energy_electricity_meter_rate).";
  const bits = rows.map((row) => {
    const unit = row.unit ? ` ${row.unit}` : "";
    return `${row.name} (${row.entity_id}${unit ? ` · ${String(row.state).trim()}${unit}` : ""})`;
  });
  return `Suggested: ${bits.join(" · ")}`;
}

let _haEntityPickerLoadPromise = null;

async function ensureHaEntityPickerLoaded() {
  if (customElements.get("ha-entity-picker")) return;
  if (typeof window.loadCardHelpers !== "function") {
    throw new Error("Home Assistant entity picker is not available");
  }
  if (!_haEntityPickerLoadPromise) {
    _haEntityPickerLoadPromise = (async () => {
      const helpers = await window.loadCardHelpers();
      const card = await helpers.createCardElement({ type: "entities", entities: [] });
      const configEl = card.constructor.getConfigElement?.();
      if (configEl && typeof configEl.then === "function") await configEl;
      await customElements.whenDefined("ha-entity-picker");
    })();
  }
  await _haEntityPickerLoadPromise;
}

function tariffCurrencyFromTariff(tariff) {
  const t = tariff && typeof tariff === "object" ? tariff : {};
  return normalizeTariffCurrency(t.currency ?? t.effective?.currency);
}

function formatTariffMoney(minor, currency) {
  const v = parseTariffRate(minor);
  if (!Number.isFinite(v)) return "—";
  const code = normalizeTariffCurrency(currency);
  const major = minorToMajor(v, code);
  const decimals = tariffCurrencyMeta(code).decimals;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      minimumFractionDigits: Math.min(decimals, 4),
      maximumFractionDigits: Math.max(decimals, 4),
    }).format(major);
  } catch {
    return `${major.toFixed(Math.min(decimals, 4))} ${code}`;
  }
}

function formatTariffMoneyDisplay(majorAmount, currency) {
  if (majorAmount == null || !Number.isFinite(Number(majorAmount))) return { value: "—", unit: "" };
  const code = normalizeTariffCurrency(currency);
  const n = Number(majorAmount);
  const sign = n < 0 ? "-" : "";
  try {
    const parts = new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).formatToParts(Math.abs(n));
    const symbol = parts.find((p) => p.type === "currency")?.value ?? code;
    const num = parts
      .filter((p) => ["integer", "group", "decimal", "fraction"].includes(p.type))
      .map((p) => p.value)
      .join("");
    return { value: `${sign}${num}`, unit: ` ${symbol}` };
  } catch {
    return { value: `${sign}${Math.abs(n).toFixed(2)}`, unit: ` ${code}` };
  }
}

function tariffSettingsSummary(tariff) {
  const rates = tariffEffectiveRates(tariff);
  const currency = tariffCurrencyFromTariff(tariff);
  const entityBits = [];
  if (normalizeTariffImportSource(tariff?.import_source) === "entity" && tariff?.import_entity) {
    entityBits.push("Import sensor");
  }
  if (normalizeTariffExportSource(tariff?.export_source) === "entity" && tariff?.export_entity) {
    entityBits.push("Export sensor");
  }
  if (normalizeTariffStandingSource(tariff?.standing_source) === "entity" && tariff?.standing_entity) {
    entityBits.push("Standing sensor");
  }
  const scheduleBits = [];
  if (normalizeTariffImportSource(tariff?.import_source) === "schedule") scheduleBits.push("Import schedule");
  if (normalizeTariffExportSource(tariff?.export_source) === "schedule") scheduleBits.push("Export schedule");
  if (normalizeTariffStandingSource(tariff?.standing_source) === "plugin") scheduleBits.push("Standing sensor");
  if (!rates.import_p_per_kwh && !rates.export_p_per_kwh && !rates.standing_charge_p_per_day) {
    if (entityBits.length) return `${entityBits.join(" · ")} — awaiting live values`;
    if (scheduleBits.length) return `${scheduleBits.join(" · ")} — set band rates`;
    return "Not configured — add rates for cost analysis";
  }
  const parts = [];
  if (rates.import_p_per_kwh) parts.push(`Import ${formatTariffMoney(rates.import_p_per_kwh, currency)}/kWh`);
  if (rates.export_p_per_kwh) parts.push(`Export ${formatTariffMoney(rates.export_p_per_kwh, currency)}/kWh`);
  if (rates.standing_charge_p_per_day) {
    parts.push(`Standing ${formatTariffMoney(rates.standing_charge_p_per_day, currency)}/day`);
  }
  const status = scheduleBits.length ? ` · ${scheduleBits.join(", ")}` : "";
  return parts.join(" · ") + status;
}

/** Google Weather API icons — https://gitlab.com/bignutty/google-weather-icons (icons/weather/v1) */
const GOOGLE_WEATHER_ICON_VER = 3;
const GOOGLE_WEATHER_ICON_BASE = "/foxess_plant_panel/weather/v1";

function googleWeatherIconTheme(hass) {
  return resolveHaUiDark(hass) ? "dark" : "light";
}

function googleWeatherIconAssetUrl(theme, iconFile) {
  return `${GOOGLE_WEATHER_ICON_BASE}/${theme}/${iconFile}?v=${GOOGLE_WEATHER_ICON_VER}`;
}

function normalizeGoogleConditionToken(raw) {
  if (raw == null || raw === "") return "";
  return String(raw).trim().toUpperCase().replace(/-/g, "_");
}

function isWeatherNightAt(atMs, isDaytime) {
  if (typeof isDaytime === "boolean") return !isDaytime;
  const d = new Date(atMs ?? Date.now());
  if (Number.isNaN(d.getTime())) return false;
  const hour = d.getHours();
  return hour < 6 || hour >= 21;
}

function googleWeatherDayNightIcon(dayFile, nightFile, isNight) {
  return isNight ? nightFile : dayFile;
}

function googleWeatherIconFileFromGoogleType(type, isNight) {
  const token = normalizeGoogleConditionToken(type);
  if (!token || token === "TYPE_UNSPECIFIED") return null;
  const dn = (day, night) => googleWeatherDayNightIcon(day, night, isNight);
  if (token === "CLEAR" || token === "FAIR") return dn("clear_day.svg", "clear_night.svg");
  if (token === "MOSTLY_CLEAR") return dn("clear_day.svg", "mostly_clear_night.svg");
  if (token === "PARTLY_CLOUDY") return dn("partly_cloudy_day.svg", "partly_cloudy_night.svg");
  if (token === "MOSTLY_CLOUDY" || token === "OVERCAST") {
    return dn("mostly_cloudy_day.svg", "mostly_cloudy_night.svg");
  }
  if (token === "CLOUDY") return "cloudy.svg";
  if (token === "WINDY" || token === "WIND" || token === "GALE" || token === "BREEZY") return "windy.svg";
  if (token === "WIND_AND_RAIN") return "rain_showers.svg";
  if (
    token === "LIGHT_RAIN_SHOWERS" ||
    token === "CHANCE_OF_SHOWERS" ||
    token === "SCATTERED_SHOWERS"
  ) {
    return dn("scattered_rain_showers_day.svg", "scattered_rain_showers_night.svg");
  }
  if (token === "RAIN_SHOWERS") return "rain_showers.svg";
  if (
    token === "HEAVY_RAIN_SHOWERS" ||
    token === "HEAVY_RAIN" ||
    token === "MODERATE_TO_HEAVY_RAIN" ||
    token === "RAIN_PERIODICALLY_HEAVY"
  ) {
    return "heavy_rain.svg";
  }
  if (
    token === "LIGHT_TO_MODERATE_RAIN" ||
    token === "RAIN" ||
    token === "LIGHT_RAIN" ||
    token === "DRIZZLE"
  ) {
    return "drizzle.svg";
  }
  if (
    token === "LIGHT_SNOW_SHOWERS" ||
    token === "CHANCE_OF_SNOW_SHOWERS" ||
    token === "SCATTERED_SNOW_SHOWERS"
  ) {
    return dn("scattered_snow_showers_day.svg", "scattered_snow_showers_night.svg");
  }
  if (token === "SNOW_SHOWERS") return "snow_showers.svg";
  if (
    token === "HEAVY_SNOW_SHOWERS" ||
    token === "HEAVY_SNOW" ||
    token === "MODERATE_TO_HEAVY_SNOW" ||
    token === "SNOW_PERIODICALLY_HEAVY" ||
    token === "SNOWSTORM" ||
    token === "HEAVY_SNOW_STORM" ||
    token === "BLIZZARD"
  ) {
    return "heavy_snow.svg";
  }
  if (
    token === "LIGHT_TO_MODERATE_SNOW" ||
    token === "SNOW" ||
    token === "LIGHT_SNOW" ||
    token === "FLURRIES"
  ) {
    return "flurries.svg";
  }
  if (token === "BLOWING_SNOW") return "blowing_snow.svg";
  if (
    token === "RAIN_AND_SNOW" ||
    token === "SLEET" ||
    token === "WINTRY_MIX" ||
    token === "GLAZE" ||
    token === "FREEZING_RAIN" ||
    token === "ICE_STORM" ||
    token === "WINTER_STORM"
  ) {
    return "wintry_mix.svg";
  }
  if (token === "MIXED_RAIN_HAIL_SLEET") return "mixed_rain_hail_sleet.svg";
  if (token === "HAIL" || token === "HAIL_SHOWERS") return "sleet_hail.svg";
  if (token === "ICY") return "icy.svg";
  if (
    token === "FOG" ||
    token === "HAZE" ||
    token === "MIST" ||
    token === "SMOG" ||
    token === "DUST" ||
    token === "DUST_STORM" ||
    token === "SAND" ||
    token === "SANDSTORM"
  ) {
    return "haze_fog_dust_smoke.svg";
  }
  if (token === "FOG" || token === "HAZE" || token === "MIST" || token === "SMOG") {
    return "haze_fog.svg";
  }
  if (token === "ISOLATED_THUNDERSTORMS") return "isolated_tstorms.svg";
  if (
    token === "THUNDERSTORM" ||
    token === "THUNDERSHOWER" ||
    token === "LIGHT_THUNDERSTORM_RAIN"
  ) {
    return dn("thunderstorms_day.svg", "thunderstorms_night.svg");
  }
  if (token === "SCATTERED_THUNDERSTORMS") {
    return dn("isolated_scattered_tstorms_day.svg", "isolated_scattered_tstorms_night.svg");
  }
  if (
    token === "HEAVY_THUNDERSTORM" ||
    token === "SEVERE_THUNDERSTORM" ||
    token === "STRONG_THUNDERSTORMS"
  ) {
    return "strong_thunderstorms.svg";
  }
  if (token === "TORNADO") return "tornado.svg";
  if (
    token === "HURRICANE" ||
    token === "TROPICAL_STORM" ||
    token === "TYPHOON" ||
    token === "CYCLONE" ||
    token === "TROPICAL_CYCLONE" ||
    token === "EXTRATROPICAL_CYCLONE"
  ) {
    return "hurricane.svg";
  }
  if (token === "HEAT" || token === "HOT") return "hot.svg";
  if (token === "COLD" || token === "WIND_CHILL" || token === "VERY_COLD") return "cold.svg";
  if (token === "WILDFIRE" || token === "FIRE" || token === "BUSHFIRE" || token === "FIRE_WEATHER") {
    return "haze_fog.svg";
  }
  if (token.includes("_WITH_") || token.includes("_THEN_")) {
    return `${token.toLowerCase()}.svg`;
  }
  return null;
}

function googleWeatherIconFileFromHaCondition(condition, isNight) {
  const token = String(condition || "").toLowerCase();
  if (!token) return null;
  const dn = (day, night) => googleWeatherDayNightIcon(day, night, isNight);
  if (token === "clear-night") return "clear_night.svg";
  if (token === "sunny" || token === "clear") return dn("clear_day.svg", "clear_night.svg");
  if (token === "partlycloudy" || token === "partly-cloudy") {
    return dn("partly_cloudy_day.svg", "partly_cloudy_night.svg");
  }
  if (token === "cloudy") return "cloudy.svg";
  if (token === "pouring") return "heavy_rain.svg";
  if (token === "rainy") return "rain_showers.svg";
  if (token === "snowy") return "heavy_snow.svg";
  if (token === "snowy-rainy") return "wintry_mix.svg";
  if (token === "fog") return "haze_fog.svg";
  if (token === "hail") return "sleet_hail.svg";
  if (token === "windy" || token === "windy-variant") return "windy.svg";
  if (token === "lightning") return dn("thunderstorms_day.svg", "thunderstorms_night.svg");
  if (token === "lightning-rainy") return "strong_thunderstorms.svg";
  if (token === "exceptional" || token === "hurricane") return "hurricane.svg";
  return null;
}

function googleWeatherIconFileFromIconKey(iconKey, isNight) {
  const key = String(iconKey || "");
  const dn = (day, night) => googleWeatherDayNightIcon(day, night, isNight);
  if (key === "sunny") return dn("clear_day.svg", "clear_night.svg");
  if (key === "partly-cloudy") return dn("partly_cloudy_day.svg", "partly_cloudy_night.svg");
  if (key === "cloudy") return "cloudy.svg";
  if (key === "rain") return "heavy_rain.svg";
  if (key === "snow") return "heavy_snow.svg";
  if (key === "storm") return "strong_thunderstorms.svg";
  if (key === "fog") return "haze_fog.svg";
  if (key === "wind") return "windy.svg";
  return null;
}

function resolveGoogleWeatherIconFile({ conditionType, haCondition, iconKey, isNight, isDaytime, atMs }) {
  const night =
    typeof isDaytime === "boolean" ? !isDaytime : isWeatherNightAt(atMs, isDaytime);
  return (
    googleWeatherIconFileFromGoogleType(conditionType, night) ||
    googleWeatherIconFileFromHaCondition(haCondition || conditionType, night) ||
    googleWeatherIconFileFromIconKey(iconKey, night) ||
    "not_available.svg"
  );
}

function googleWeatherIconHtml(hass, opts = {}, className = "overview-weather-icon") {
  const theme = googleWeatherIconTheme(hass);
  const iconFile = resolveGoogleWeatherIconFile(opts);
  const url = googleWeatherIconAssetUrl(theme, iconFile);
  const cls = esc(className);
  const size = className.includes("hourly") ? 28 : 18;
  return `<img class="${cls}" src="${esc(url)}" alt="" width="${size}" height="${size}" loading="lazy" decoding="async">`;
}

function overviewWeatherIconSvg(hass, opts, className = "overview-weather-icon") {
  if (opts && typeof opts === "object") {
    return googleWeatherIconHtml(hass, opts, className);
  }
  return googleWeatherIconHtml(
    null,
    { iconKey: opts, atMs: Date.now() },
    className
  );
}

function haConditionToIconKey(condition) {
  if (!condition) return "unknown";
  const token = String(condition).toLowerCase();
  if (["lightning", "lightning-rainy", "exceptional", "hurricane"].includes(token)) return "storm";
  if (["rainy", "pouring"].includes(token)) return "rain";
  if (["snowy", "snowy-rainy"].includes(token)) return "snow";
  if (token === "fog") return "fog";
  if (["windy", "windy-variant", "hail"].includes(token)) return "wind";
  if (["partlycloudy", "partly-cloudy"].includes(token)) return "partly-cloudy";
  if (token === "cloudy") return "cloudy";
  if (["sunny", "clear", "clear-night"].includes(token)) return "sunny";
  return "unknown";
}

function formatHourlyWeatherTemp(temp, unit) {
  if (!Number.isFinite(temp)) return "—";
  const value = Math.round(temp);
  return `${value}°`;
}

function formatHourlyWeatherTime(t, isNow) {
  if (isNow) return "Now";
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return "—";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function parseHourlyWeatherSlots(forecast, overviewWx, maxHours = 24) {
  const now = Date.now();
  const unit = overviewWx?.temperature_unit;
  const slots = [];
  for (const row of forecast || []) {
    if (!row || slots.length >= maxHours) break;
    const t = new Date(row.datetime).getTime();
    if (Number.isNaN(t) || t < now - 60 * 60 * 1000) continue;
    const precipRaw = row.precipitation_probability ?? row.precipitation ?? null;
    let precipPct = null;
    if (Number.isFinite(precipRaw)) precipPct = Math.round(precipRaw);
    else if (precipRaw != null && precipRaw !== "") {
      const parsed = parseFloat(precipRaw);
      if (Number.isFinite(parsed)) precipPct = Math.round(parsed);
    }
    const nativeType =
      row.native_condition ||
      row.condition_type ||
      row.type ||
      row.weather_condition ||
      null;
    let isDaytime = null;
    if (typeof row.is_daytime === "boolean") isDaytime = row.is_daytime;
    else if (typeof row.isDaytime === "boolean") isDaytime = row.isDaytime;
    slots.push({
      t,
      tempDisplay: formatHourlyWeatherTemp(row.temperature, unit ?? row.temperature_unit),
      precipPct,
      haCondition: row.condition,
      conditionType: nativeType,
      isDaytime,
      iconKey: haConditionToIconKey(row.condition),
      isNow: false,
    });
  }
  if (slots.length) {
    const first = new Date(slots[0].t);
    const nowDate = new Date(now);
    slots[0].isNow =
      first.getHours() === nowDate.getHours() && first.toDateString() === nowDate.toDateString();
  }
  return slots;
}

async function fetchHourlyWeatherOverview(hass, weatherEntityId, overviewWx) {
  if (!weatherEntityId) {
    return { empty: "Add Google Weather to show an hourly forecast." };
  }
  try {
    const response = await callServiceWithResponse(
      hass,
      "weather",
      "get_forecasts",
      { type: "hourly" },
      { entity_id: weatherEntityId }
    );
    const block = response?.[weatherEntityId] ?? Object.values(response || {})[0];
    const forecast = block?.forecast;
    if (!Array.isArray(forecast) || !forecast.length) {
      return { empty: "No hourly forecast available yet." };
    }
    const slots = parseHourlyWeatherSlots(forecast, overviewWx);
    if (!slots.length) {
      return { empty: "No hourly forecast available yet." };
    }
    if (slots[0].isNow && Number.isFinite(overviewWx?.temperature)) {
      slots[0].tempDisplay = formatHourlyWeatherTemp(
        overviewWx.temperature,
        overviewWx.temperature_unit
      );
      if (overviewWx.condition_type) slots[0].conditionType = overviewWx.condition_type;
      if (overviewWx.ha_condition) slots[0].haCondition = overviewWx.ha_condition;
      if (typeof overviewWx.is_daytime === "boolean") slots[0].isDaytime = overviewWx.is_daytime;
      else if (overviewWx.icon_key) slots[0].iconKey = overviewWx.icon_key;
    }
    return { slots, weatherEntityId };
  } catch (err) {
    return { error: err?.message || "Could not load hourly forecast." };
  }
}

function renderHourlyWeatherOverviewHtml(hass, data) {
  if (data?.error) {
    return `<p class="placeholder hourly-weather-empty">${esc(data.error)}</p>`;
  }
  if (data?.empty) {
    return `<p class="placeholder hourly-weather-empty">${esc(data.empty)}</p>`;
  }
  const slots = data?.slots || [];
  if (!slots.length) {
    return `<p class="placeholder hourly-weather-empty">No hourly forecast available yet.</p>`;
  }
  const cols = slots
    .map(
      (slot) => `<div class="hourly-weather-col">
<div class="hourly-weather-temp">${esc(slot.tempDisplay)}</div>
<div class="hourly-weather-icon-wrap">${googleWeatherIconHtml(hass, {
        conditionType: slot.conditionType,
        haCondition: slot.haCondition,
        iconKey: slot.iconKey,
        isDaytime: slot.isDaytime,
        atMs: slot.t,
      }, "hourly-weather-icon")}</div>
<div class="hourly-weather-precip">${slot.precipPct != null ? `${esc(String(slot.precipPct))}%` : "—"}</div>
<div class="hourly-weather-time${slot.isNow ? " hourly-weather-time--now" : ""}">${esc(formatHourlyWeatherTime(slot.t, slot.isNow))}</div>
</div>`
    )
    .join("");
  return `<div class="hourly-weather-card-inner" data-hourly-weather="1">
<div class="hourly-weather-head">
<h3 class="hourly-weather-title"><svg class="hourly-weather-title-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 7v5.2l3.2 1.8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>Hourly overview</h3>
<div class="hourly-weather-nav">
<button type="button" class="hourly-weather-nav-btn" data-hourly-scroll="-1" aria-label="Scroll hourly forecast left">‹</button>
<button type="button" class="hourly-weather-nav-btn" data-hourly-scroll="1" aria-label="Scroll hourly forecast right">›</button>
</div>
</div>
<div class="hourly-weather-scroll-wrap">
<div class="hourly-weather-scroll">${cols}</div>
</div>
</div>`;
}

function bindHourlyWeatherOverview(root) {
  const card = root?.querySelector?.("[data-hourly-weather]");
  if (!card || card.dataset.bound) return;
  card.dataset.bound = "1";
  const scroller = card.querySelector(".hourly-weather-scroll");
  if (!scroller) return;
  card.querySelectorAll("[data-hourly-scroll]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dir = Number(btn.getAttribute("data-hourly-scroll")) || 0;
      scroller.scrollBy({ left: dir * 220, behavior: "smooth" });
    });
  });
  scroller.addEventListener(
    "scroll",
    () => {
      card.dataset.scrollLeft = String(Math.round(scroller.scrollLeft));
    },
    { passive: true }
  );
}

function entityUnit(hass, entityId) {
  const u = hass?.states?.[entityId]?.attributes?.unit_of_measurement;
  return u ? ` ${u}` : "";
}

function formatKw(watts, decimals = 2) {
  const kw = Math.abs(watts) / 1000;
  return kw >= 10 ? `${kw.toFixed(1)} kW` : `${kw.toFixed(decimals)} kW`;
}

function formatPercent(value) {
  return `${Math.round(value)}%`;
}

/** PCS serial for device hero (identity first, then entity). */
function plantDeviceSerial(hass, plant, plantState) {
  const fromIdentity = plantState?.identity?.pcs_serial_number;
  if (fromIdentity && fromIdentity !== "unavailable" && fromIdentity !== "unknown") {
    return String(fromIdentity).trim();
  }
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  const entityId = map.pcs_serial_number;
  if (entityId) {
    const raw = stateString(hass, entityId);
    if (raw && raw !== "—" && raw !== "unavailable" && raw !== "unknown") {
      return String(raw).trim();
    }
  }
  return "—";
}

function formatDevicePowerKw(watts) {
  const kw = Math.abs(watts) / 1000;
  if (kw < 10) return `${kw.toFixed(3)} kW`;
  return `${kw.toFixed(2)} kW`;
}

function deviceBatteryToneClass(status) {
  const s = String(status || "").toLowerCase();
  if (s.includes("charg")) return "is-charging";
  if (s.includes("discharg")) return "is-discharging";
  return "is-idle";
}

/** 270° arc gauge (gap at bottom), Fox app PV style. Fill = live kW ÷ configured effective max kW. */
function renderPvThreeQuarterGauge(pvKw, maxKw, valueText, labelText, pctOfMax) {
  const r = 42;
  const cx = 50;
  const cy = 52;
  const circ = 2 * Math.PI * r;
  const arcLen = circ * 0.75;
  const gapLen = circ - arcLen;
  const rot = 135;
  const pct = maxKw > 0 ? Math.min(1, Math.max(0, pvKw / maxKw)) : 0;
  const fillLen = arcLen * pct;
  const pctLabel =
    pctOfMax != null && Number.isFinite(pctOfMax)
      ? `${Math.round(pctOfMax)}% of ${maxKw < 10 ? maxKw.toFixed(2) : maxKw.toFixed(1)} kW`
      : maxKw > 0
        ? `${Math.round(pct * 100)}% of ${maxKw < 10 ? maxKw.toFixed(2) : maxKw.toFixed(1)} kW`
        : "";
  const track = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--divider-color)" stroke-width="9" stroke-linecap="round" stroke-dasharray="${arcLen} ${gapLen}" transform="rotate(${rot} ${cx} ${cy})"/>`;
  const fill =
    fillLen > 0.5
      ? `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--fp-accent)" stroke-width="9" stroke-linecap="round" stroke-dasharray="${fillLen} ${circ - fillLen}" transform="rotate(${rot} ${cx} ${cy})"/>`
      : "";
  const cap = pctLabel ? `<div class="device-pv-cap">${esc(pctLabel)}</div>` : "";
  return `<div class="device-pv-wrap" role="img" aria-label="${esc(labelText)} ${esc(valueText)} ${esc(pctLabel)}">
<div class="device-pv-gauge"><svg viewBox="0 0 100 104" aria-hidden="true">${track}${fill}</svg>
<div class="device-pv-readout"><div class="device-pv-value">${esc(valueText)}</div><div class="device-pv-label">${esc(labelText)}</div></div>
</div>
${cap}
</div>`;
}

function resolvePvStringPowerEntity(hass, map, which) {
  const key = which === "pv2" ? "pv2_power" : "pv1_power";
  const suffix = which === "pv2" ? "pv2_power" : "pv1_power";
  if (map[key] && hass?.states?.[map[key]]) return map[key];
  if (!hass?.states) return map[key] || null;
  const ids = Object.keys(hass.states);
  const hit = ids.find((id) => entityIdMatchesSuffix(id, suffix));
  return hit || (which === "pv1" ? map.pv_power : null) || null;
}

function renderDevicePvGaugeInner(hass, map, { key, label, cfg }) {
  const entityId = resolvePvStringPowerEntity(hass, map, key);
  const watts = entityId ? statePowerWatts(hass, entityId) : 0;
  const liveKw = watts / 1000;
  const maxKw = pvStringEffectiveMaxKw(cfg);
  const pct = maxKw > 0 ? Math.min(100, (liveKw / maxKw) * 100) : 0;
  return renderPvThreeQuarterGauge(liveKw, maxKw, formatDevicePowerKw(watts), label, pct);
}

/** One PV card (left column): 1 centred gauge or 2 side-by-side; battery stays in the right column. */
function renderDevicePvCard(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const strings = enabledPvStrings(plantState?.pv_config);
  if (!strings.length) {
    const flows = readEnergyFlows(hass, plant, plantState);
    const cfg = normalizePvConfig(plantState?.pv_config).pv1;
    const maxKw = pvStringEffectiveMaxKw(cfg);
    const liveKw = flows.pvW / 1000;
    const pct = maxKw > 0 ? Math.min(100, (liveKw / maxKw) * 100) : 0;
    const gauge = renderPvThreeQuarterGauge(
      liveKw,
      maxKw,
      formatDevicePowerKw(flows.pvW),
      "PV1 Power",
      pct
    );
    return `<div class="device-card device-card--pv"><div class="device-pv-gauges device-pv-gauges--single">${gauge}</div></div>`;
  }
  const layoutClass = strings.length > 1 ? "device-pv-gauges--dual" : "device-pv-gauges--single";
  const gauges = strings.map((s) => renderDevicePvGaugeInner(hass, map, s)).join("");
  return `<div class="device-card device-card--pv"><div class="device-pv-gauges ${layoutClass}">${gauges}</div></div>`;
}

function renderDeviceBatteryIcon(socPct) {
  const pct = Math.min(100, Math.max(0, socPct));
  const fillW = Math.round((34 * pct) / 100);
  return `<svg class="device-battery-svg" viewBox="0 0 44 22" aria-hidden="true">
<rect class="device-battery-shell" x="1" y="4" width="36" height="14" rx="2"/>
<rect class="device-battery-cap" x="37" y="8" width="4" height="6" rx="1"/>
<rect class="device-battery-fill" x="3" y="6" width="${fillW}" height="10" rx="1"/>
</svg>`;
}

function renderDeviceBatteryCard(flows, tempDisplay) {
  const tone = deviceBatteryToneClass(flows.batteryStatus);
  const icon = renderDeviceBatteryIcon(flows.batterySoc);
  return `<div class="device-battery-card ${tone}">
<div class="device-battery-top">
<div class="device-battery-status-row">${icon}<span class="device-battery-status">${esc(flows.batteryStatus)}</span></div>
<div class="device-battery-pct">${esc(formatPercent(flows.batterySoc))}</div>
</div>
<div class="device-battery-metrics">
<div class="device-battery-metric device-battery-metric--power"><span class="device-battery-metric-label">Power</span><span class="device-battery-metric-value">${esc(formatDevicePowerKw(flows.batteryW))}</span></div>
<div class="device-battery-metric device-battery-metric--temp"><span class="device-battery-metric-label">Temp.</span><span class="device-battery-metric-value">${esc(tempDisplay)}</span></div>
</div>
</div>`;
}

function deviceNewDischargeKw(flows) {
  const w = Number(flows?.batteryW) || 0;
  if (w > 50) return w / 1000;
  const status = String(flows?.batteryStatus || "").toLowerCase();
  if (status.includes("discharg")) return Math.abs(w) / 1000;
  return 0;
}

function renderDeviceBatteryTempSummaryCard(hass, map) {
  const theme = DEVICE_SUMMARY_CARD_THEMES.temp || {};
  const icon = foxDeviceSummaryIcon("temperature");
  const style = theme.accent
    ? ` style="--fox-summary-accent:${theme.accent};--fox-summary-accent-hi:${theme.accentHi || theme.accent};--fox-summary-bg:${theme.bg};"`
    : "";
  const minParts = batteryTempMetricParts(hass, map.bms_temp_low);
  const maxParts = batteryTempMetricParts(hass, map.bms_temp_high);
  return `<div class="fox-device-new-summary-card fox-device-new-summary-card--temp fox-device-new-summary-card--temps"${style}>
<div class="fox-device-new-summary-head">
<span class="fox-device-new-summary-label">Battery Temperature</span>
${icon ? `<span class="fox-device-new-summary-icon" aria-hidden="true">${icon}</span>` : ""}
</div>
<div class="fox-device-new-summary-body">
<div class="fox-device-new-summary-temp-labels">
<span class="fox-device-new-summary-temp-label">Min.</span>
<span class="fox-device-new-summary-temp-label">Max.</span>
</div>
<div class="fox-device-new-summary-temp-values">
${renderFoxSummaryMetricValue(minParts.num, minParts.unit, {
    valueClass: "fox-device-new-summary-value fox-device-new-summary-temp-value",
  })}
${renderFoxSummaryMetricValue(maxParts.num, maxParts.unit, {
    valueClass: "fox-device-new-summary-value fox-device-new-summary-temp-value",
  })}
</div>
</div>
</div>`;
}

function renderDeviceNewSummaryCardItems(hass, plant, plantState) {
  const flows = readEnergyFlows(hass, plant, plantState);
  const map = resolveEntityMap(hass, plant, plantState);
  const iconKeys = { pv: "pv_power", soc: "battery_soc", discharge: "discharging" };
  const cards = [
    { label: "PV Power", metric: devicePowerKwMetricParts(flows.pvW), tone: "pv" },
    { label: "Battery SOC", metric: percentMetricParts(flows.batterySoc), tone: "soc" },
    {
      label: "Discharging power",
      metric: { num: deviceNewDischargeKw(flows).toFixed(3), unit: FOX_UNIT_KW },
      tone: "discharge",
    },
  ];
  const standard = cards
    .map((c) => {
      const icon = foxDeviceSummaryIcon(iconKeys[c.tone]);
      const theme = DEVICE_SUMMARY_CARD_THEMES[c.tone] || {};
      const style = theme.accent
        ? ` style="--fox-summary-accent:${theme.accent};--fox-summary-accent-hi:${theme.accentHi || theme.accent};--fox-summary-bg:${theme.bg};"`
        : "";
      return `<div class="fox-device-new-summary-card fox-device-new-summary-card--${c.tone}"${style}>
<div class="fox-device-new-summary-head">
<span class="fox-device-new-summary-label">${esc(c.label)}</span>
${icon ? `<span class="fox-device-new-summary-icon" aria-hidden="true">${icon}</span>` : ""}
</div>
<div class="fox-device-new-summary-body">${renderFoxSummaryMetricValue(c.metric.num, c.metric.unit)}</div>
</div>`;
    })
    .join("");
  return `${standard}${renderDeviceBatteryTempSummaryCard(hass, map)}`;
}

function renderDeviceNewSummaryCards(hass, plant, plantState) {
  return `<div class="fox-device-new-summary" data-device-new-summary="1">${renderDeviceNewSummaryCardItems(
    hass,
    plant,
    plantState
  )}</div>`;
}

function repairDeviceNewSummaryElement(summary) {
  if (!summary) return null;
  const nested = summary.querySelector(":scope > .fox-device-new-summary");
  if (nested) summary.innerHTML = nested.innerHTML;
  return summary;
}

function renderDeviceNewMetricGrid(hass, rows) {
  if (!rows.length) {
    return `<p class="device-param-empty">No sensors discovered for this section.</p>`;
  }
  return `<div class="fox-device-new-metric-grid">${rows
    .map((r) => {
      const label = r.name || r.label;
      let valueHtml;
      if (r.html) {
        valueHtml = r.html;
      } else {
        const value = r.entity_id
          ? entityDisplayValue(hass, r.entity_id)
          : r.value != null && r.value !== ""
            ? String(r.value)
            : "—";
        valueHtml = esc(value);
      }
      return `<div class="fox-device-new-metric-item"><span class="fox-device-new-metric-label-wrap"><span class="fox-device-new-metric-label">${esc(label)}</span><span class="fox-device-new-metric-colon"> :</span></span><span class="fox-device-new-metric-value">${valueHtml}</span></div>`;
    })
    .join("")}</div>`;
}

function entityMapRowsFox(hass, plant, plantState, pairs) {
  const map = resolveEntityMap(hass, plant, plantState);
  return pairs.map(([key, name]) => ({
    key: key || null,
    name,
    entity_id: key && map[key] ? map[key] : null,
  }));
}

function formatDeviceNewGridStatusHtml(hass, entityId) {
  const st = entityId ? stateString(hass, entityId) : "—";
  if (st === "—") return "—";
  const lower = st.toLowerCase();
  const tone =
    lower.includes("export") || lower.includes("feed")
      ? "export"
      : lower.includes("import") || lower.includes("purchase")
        ? "import"
        : "idle";
  return `<span class="fox-device-new-grid-status fox-device-new-grid-status--${tone}"><span class="fox-device-new-grid-status-dot" aria-hidden="true"></span><span>${esc(st)}</span></span>`;
}

function foxDeviceCheckPillIcon() {
  return `<svg class="fox-device-new-check-pill-icon" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="6.25" fill="currentColor" opacity="0.2"/><path d="M4.2 7.1l1.85 1.9 3.75-3.95" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

function formatFoxTonePill(text, toneClass, { showCheckIcon = false } = {}) {
  const label = String(text || "—");
  if (label === "—") return esc(label);
  const icon = showCheckIcon ? foxDeviceCheckPillIcon() : "";
  return `<span class="fox-device-new-check-pill ${toneClass}">${icon}<span class="fox-device-new-check-pill-text">${esc(label)}</span></span>`;
}

function isFoxFaultInverterState(label) {
  return String(label || "").trim().toLowerCase() === "fault";
}

/** Link Fault state pills to the Device → Alerts tab. */
function wrapFoxInverterStatePillLink(label, pillHtml, { fromOverview = false } = {}) {
  if (!pillHtml || !isFoxFaultInverterState(label)) return pillHtml;
  const attrs = fromOverview
    ? `data-action="nav" data-view="device_new" data-device-sub="alarms"`
    : `data-action="device-new-tab" data-sub="alarms"`;
  return `<button type="button" class="fox-inverter-state-pill-link" ${attrs} title="View alerts">${pillHtml}</button>`;
}

/** Fox device card status pill (Normal / Online with tick). */
function formatFoxDeviceCheckPill(value) {
  const text = String(value || "—");
  if (text === "—") return esc(text);
  const lower = text.trim().toLowerCase();
  const positive = /^(normal|online|on)$/.test(lower);
  const cls = positive
    ? "fox-device-new-check-pill--ok"
    : lower === "fault"
      ? "fox-device-new-check-pill--fault"
      : "fox-device-new-check-pill--off";
  return formatFoxTonePill(text, cls, { showCheckIcon: positive });
}

function formatFoxOverviewStatusPill(value) {
  const text = String(value || "—");
  if (text === "—") return esc(text);
  const lower = text.trim().toLowerCase();
  if (/^(normal|online|on)$/.test(lower)) return formatFoxDeviceCheckPill(value);
  if (lower === "fault") return formatFoxDeviceCheckPill(value);
  if (lower === "checking") return formatFoxTonePill(text, "fox-overview-pill--checking");
  if (lower === "off grid") return formatFoxTonePill(text, "fox-overview-pill--offgrid");
  return formatFoxTonePill(text, "fox-device-new-check-pill--off");
}

function formatFoxOverviewWorkModePill(label) {
  const text = foxWorkModeDisplay(label);
  if (text === "—") return esc(text);
  return formatFoxTonePill(text, `fox-overview-pill--${foxWorkModeToneClass(label)}`);
}

function formatFoxOverviewPlantModePill(mode) {
  const raw = String(mode || "baseline").trim();
  const display = raw ? raw.charAt(0).toUpperCase() + raw.slice(1) : "Baseline";
  const tone = modeClass(mode).replace(/^mode-/, "plant-");
  return formatFoxTonePill(display, `fox-overview-pill--${tone}`);
}

function formatDeviceNewOnlineBadge(value) {
  return formatFoxDeviceCheckPill(value);
}

/** Fox datalogger software version (Modbus protocol major.minor, e.g. V2.09). */
function formatFoxDataloggerSoftwareVersion(hass, plantState, map) {
  const proto = plantState?.identity?.modbus_protocol_version || entityDisplayValue(hass, map.modbus_protocol_version);
  if (proto && proto !== "—") {
    const parts = String(proto)
      .replace(/^V/i, "")
      .split(".")
      .map((p) => p.trim())
      .filter(Boolean);
    if (parts.length >= 2) {
      const major = Number(parts[0]);
      const minor = Number(parts[1]);
      if (Number.isFinite(major) && Number.isFinite(minor)) {
        return `V${major}.${String(minor).padStart(2, "0")}`;
      }
    }
    return String(proto);
  }
  const slave = entityDisplayValue(hass, map.slave_version);
  return slave !== "—" ? slave : "—";
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      /* fall through to execCommand */
    }
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  document.body.appendChild(ta);
  ta.select();
  try {
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  } catch (_) {
    ta.remove();
    return false;
  }
}

function deviceSerialCopyIconSvg() {
  return `<svg class="fox-device-new-sidebar-copy-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>`;
}

function renderDeviceNewFoxDatalogger(hass, plant, plantState, map) {
  const id = plantState?.identity ?? {};
  const rows = [];
  const bmsId = map.bms_online;
  let status = "—";
  if (bmsId && hass?.states?.[bmsId]) {
    status = hass.states[bmsId].state === "on" ? "Online" : "Offline";
  } else if (id.bms_online != null && id.bms_online !== "") {
    status = id.bms_online === true || id.bms_online === "on" ? "Online" : "Offline";
  }
  rows.push({ name: "Status", html: formatDeviceNewOnlineBadge(status) });
  rows.push({ name: "Software Version", value: formatFoxDataloggerSoftwareVersion(hass, plantState, map) });
  const signal = entityDisplayValue(hass, map.datalogger_signal);
  rows.push({ name: "Signal strength", value: signal !== "—" ? signal : "—" });
  return renderDeviceNewMetricGrid(hass, rows);
}

function renderDeviceNewMetricRows(hass, plant, plantState, pairs) {
  const rows = entityMapRowsFox(hass, plant, plantState, pairs).map((row) => {
    if (row.key === "grid_status") {
      return { ...row, html: formatDeviceNewGridStatusHtml(hass, row.entity_id) };
    }
    return row;
  });
  return renderDeviceNewMetricGrid(hass, rows);
}

function renderDeviceNewPvTable(hass, map) {
  const cell = (entityId) => {
    if (!entityId || !hass?.states?.[entityId]) return "—";
    return entityDisplayValue(hass, entityId);
  };
  const totalRow = `<tr><td>PV</td><td>—</td><td>—</td><td>${esc(cell(map.pv_power))}</td></tr>`;
  const stringRows = DEVICE_PV_STRINGS.map(
    (n) =>
      `<tr><td>PV${n}</td><td>${esc(cell(map[`pv${n}_voltage`]))}</td><td>${esc(cell(map[`pv${n}_current`]))}</td><td>${esc(cell(map[`pv${n}_power`]))}</td></tr>`
  ).join("");
  return `<div class="device-param-table-wrap fox-device-new-table-wrap"><table class="device-param-table fox-device-new-table"><thead><tr><th>PV</th><th>Voltage (V)</th><th>Current (A)</th><th>Power (kW)</th></tr></thead><tbody>${totalRow}${stringRows}</tbody></table></div>`;
}

function renderDeviceNewMetricTable(hass, map, keys, headers) {
  const values = keys.map((key) => (map[key] ? entityDisplayValue(hass, map[key]) : "—"));
  return `<div class="device-param-table-wrap fox-device-new-table-wrap"><table class="device-param-table fox-device-new-table"><thead><tr>${headers
    .map((h) => `<th>${esc(h)}</th>`)
    .join("")}</tr></thead><tbody><tr>${values.map((v) => `<td>${esc(v)}</td>`).join("")}</tr></tbody></table></div>`;
}

function renderDeviceNewSubsections(hass, plant, plantState, section) {
  return (section.subsections || [])
    .map((sub) => {
      const body = renderDeviceNewMetricRows(hass, plant, plantState, sub.rows || []);
      return `<div class="fox-device-new-subsection"><h4 class="fox-device-new-subsection-title">${esc(sub.title)}</h4>${body}</div>`;
    })
    .join("");
}

function deviceNewSidebarRowValue(value) {
  if (value == null || value === "" || value === "—") return null;
  return String(value);
}

function renderDeviceNewSidebarRow(row) {
  const dd = row.html ?? esc(String(row.value));
  return `<div class="fox-device-new-sidebar-row"><dt>${esc(row.label)}</dt><dd>${dd}</dd></div>`;
}

function renderDeviceNewSidebar(hass, plant, plantState) {
  const id = plantState?.identity ?? {};
  const map = resolveEntityMap(hass, plant, plantState);
  const serialRaw = plantDeviceSerial(hass, plant, plantState);
  const pcsSn = deviceNewSidebarRowValue(serialRaw !== "—" ? serialRaw : id.pcs_serial_number);
  const batterySn = deviceNewSidebarRowValue(
    id.bms_pack_serial_modbus || entityDisplayValue(hass, map.bms_pack_serial_modbus)
  );
  const model = deviceNewSidebarRowValue(
    (() => {
      const m = plantModelSubtitle(hass, plant, plantState);
      return m !== "—" ? m : id.pcs_model_name;
    })()
  );
  const status = foxInverterStateLabel(hass, plant, plantState);
  const meterOnline =
    id.bms_online === true ||
    id.bms_online === "on" ||
    (map.bms_online && hass?.states?.[map.bms_online]?.state === "on");
  const meterLabel =
    meterOnline ? "Online" : id.bms_online === false || id.bms_online === "off" ? "Offline" : null;
  const plantTitle = deviceNewSidebarRowValue(plant?.title);
  const serialHero = pcsSn
    ? `<div class="fox-device-new-sidebar-serial-row">
<button type="button" class="fox-device-new-sidebar-serial-btn device-serial-btn" data-action="device-new-sub" data-sub="system">
<span class="fox-device-new-sidebar-serial-prefix">SN:</span>
<span class="device-serial fox-device-new-sidebar-serial">${esc(pcsSn)}</span>
<span class="fox-device-new-sidebar-chevron chev" aria-hidden="true">›</span>
</button>
<button type="button" class="fox-device-new-sidebar-copy-btn" data-action="copy-device-serial" data-serial="${esc(pcsSn)}" aria-label="Copy serial number">${deviceSerialCopyIconSvg()}</button>
</div>`
    : `<p class="device-serial device-serial-muted fox-device-new-sidebar-serial-muted">Serial unavailable</p>`;
  const rows = [
    status !== "—"
      ? {
          label: "State",
          html: wrapFoxInverterStatePillLink(status, formatFoxDeviceCheckPill(status)),
        }
      : null,
    pcsSn ? { label: "PSC SN", value: pcsSn } : null,
    batterySn ? { label: "Battery SN", value: batterySn } : null,
    plantTitle
      ? {
          label: "Plant",
          html: `<span class="fox-device-new-sidebar-plant">${esc(plantTitle)}<span class="fox-device-new-sidebar-chevron" aria-hidden="true">›</span></span>`,
        }
      : null,
    model ? { label: "Model", value: model } : null,
    meterLabel ? { label: "Meter", html: formatFoxDeviceCheckPill(meterLabel) } : null,
    deviceNewSidebarRowValue(id.master_version || entityDisplayValue(hass, map.master_version))
      ? { label: "Version_Master", value: id.master_version || entityDisplayValue(hass, map.master_version) }
      : null,
    deviceNewSidebarRowValue(id.slave_version || entityDisplayValue(hass, map.slave_version))
      ? { label: "Version_Slave", value: id.slave_version || entityDisplayValue(hass, map.slave_version) }
      : null,
    deviceNewSidebarRowValue(id.manager_version || entityDisplayValue(hass, map.manager_version))
      ? { label: "Version_Manager", value: id.manager_version || entityDisplayValue(hass, map.manager_version) }
      : null,
  ].filter(Boolean);
  const body = rows.length
    ? `<dl class="fox-device-new-sidebar-list">${rows.map(renderDeviceNewSidebarRow).join("")}</dl>`
    : `<p class="placeholder">No device identity available yet.</p>`;
  return `<div class="fox-device-new-sidebar-col"><aside class="fox-device-new-sidebar">
<div class="fox-device-new-sidebar-hero">
<img class="fox-device-new-sidebar-img" src="${esc(DEVICE_EVO_IMAGE_STATIC)}" alt="" loading="lazy" />
${serialHero}
</div>
<div class="fox-device-new-sidebar-divider" aria-hidden="true"></div>
<h3 class="fox-device-new-sidebar-section-title">Device Information</h3>
${body}
</aside></div>`;
}

async function fetchDeviceRealtimeChartSeries(hass, plant, plantState, { dayOffset = 0 } = {}) {
  const map = resolveEntityMap(hass, plant, plantState);
  const specs = DEVICE_REALTIME_CHART_SERIES.map((s) => {
    const candidates = chartEntityCandidates(hass, map, s.key);
    return { ...s, entity_id: candidates[0] || null };
  }).filter((s) => s.entity_id);
  if (!specs.length) {
    return { empty: "Map inverter power entities in FoxESS Modbus, then reload FoxESS Plant." };
  }
  const now = new Date();
  const day = startOfLocalDay(now);
  day.setDate(day.getDate() - Math.max(0, dayOffset));
  const range = getStatisticsDayRangeForDate(day, { asOf: dayOffset === 0 ? now : endOfLocalDay(day) });
  const fetchEnd = new Date(range.nowMs);
  const start = new Date(range.tMin);
  const socId = map.battery_soc;
  const entityIds = [
    ...new Set(
      [...specs.flatMap((s) => chartEntityCandidates(hass, map, s.key)), socId].filter(Boolean)
    ),
  ];
  const [statsMap, hist] = await Promise.all([
    fetchStatisticsDuring(hass, entityIds, start, fetchEnd),
    fetchHistoryDuring(hass, entityIds, start, fetchEnd),
  ]);
  const series = finalizeDeviceRealtimeChartSeries(
    specs.map((spec) => {
      const built = buildChartSeriesPointsWithFallback(hass, map, spec.key, spec, range, statsMap, hist);
      return {
        id: spec.key,
        label: spec.label,
        tooltipLabel: spec.label,
        legendGroup: spec.legendGroup,
        color: spec.color,
        fill: spec.fill,
        lineWidth: spec.lineWidth,
        densify: spec.densify,
        showZeroInTooltip: spec.showZeroInTooltip,
        entity_id: built.entityId,
        points: built.points,
      };
    }),
    range
  );
  let socSeries = null;
  if (socId) {
    const socPoints = buildSocHistoryPoints(hass, socId, range, statsMap, hist);
    if (socPoints.length) {
      socSeries = {
        id: "battery_soc",
        label: "Battery SOC",
        tooltipLabel: "Battery SOC",
        legendGroup: "soc",
        yAxis: "soc",
        color: STATISTICS_SOC_COLOR,
        connectGaps: true,
        lineWidth: 1.6,
        points: socPoints,
      };
    }
  }
  if (!series.some((s) => s.points.length) && !socSeries?.points?.length) {
    return { empty: "No power history for this day yet." };
  }
  return { series, socSeries, range, dayOffset };
}

/** Fox app Solar Analysis palette (matches dashboard plotly cards). */
const FOX_ENERGY = {
  pv: "#05989A",
  load: "#7F3DFF",
  muted: "#C3C8D1",
};

function polarToCartesian(cx, cy, r, deg) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeDonutSlice(cx, cy, rOuter, rInner, startDeg, endDeg) {
  const sweep = endDeg - startDeg;
  if (sweep <= 0) return "";
  if (sweep >= 359.99) endDeg = startDeg + 359.99;
  const startOuter = polarToCartesian(cx, cy, rOuter, endDeg);
  const endOuter = polarToCartesian(cx, cy, rOuter, startDeg);
  const startInner = polarToCartesian(cx, cy, rInner, startDeg);
  const endInner = polarToCartesian(cx, cy, rInner, endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return [
    "M",
    startOuter.x,
    startOuter.y,
    "A",
    rOuter,
    rOuter,
    0,
    large,
    0,
    endOuter.x,
    endOuter.y,
    "L",
    startInner.x,
    startInner.y,
    "A",
    rInner,
    rInner,
    0,
    large,
    1,
    endInner.x,
    endInner.y,
    "Z",
  ].join(" ");
}

function renderEnergyDonut(segments, gapDeg = 3) {
  const active = segments.filter((s) => s.value > 0);
  const total = active.reduce((sum, s) => sum + s.value, 0);
  const cx = 50;
  const cy = 50;
  const rOuter = 44;
  const rInner = 34;
  const stroke = "var(--card-background-color, #17191d)";

  if (total <= 0) {
    return `<svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><circle cx="${cx}" cy="${cy}" r="${(rOuter + rInner) / 2}" fill="none" stroke="${FOX_ENERGY.muted}" stroke-width="${rOuter - rInner}" opacity="0.35"/></svg>`;
  }

  let angle = -90;
  const gap = active.length > 1 ? gapDeg : 0;
  const sweepTotal = 360 - gap * active.length;
  const paths = active.map((seg) => {
    const sweep = (seg.value / total) * sweepTotal;
    const start = angle;
    const end = angle + sweep;
    angle = end + gap;
    const d = describeDonutSlice(cx, cy, rOuter, rInner, start, end);
    return `<path d="${d}" fill="${seg.color}" stroke="${stroke}" stroke-width="2"/>`;
  });
  return `<svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" aria-hidden="true">${paths.join("")}</svg>`;
}

function renderEnergyBreakdownRow({ heading, totalKwh, metrics, segments, centerPct, centerLabel, accent }) {
  const donut = renderEnergyDonut(segments);
  const metricsHtml = metrics
    .map(
      (m) => `<div class="fox-energy-metric">
<div class="fox-energy-metric-label">${esc(m.label)}</div>
<div class="fox-energy-metric-value" style="color:${esc(m.color)}">${m.value.toFixed(2)}<span class="fox-energy-metric-unit"> kWh</span></div>
</div>`
    )
    .join("");
  return `<div class="fox-energy-row">
<div class="fox-energy-copy">
<div class="fox-energy-heading">${esc(heading)}</div>
<div class="fox-energy-total">${totalKwh.toFixed(2)}<span>kWh</span></div>
${metricsHtml}
</div>
<div class="fox-energy-chart" role="img" aria-label="${esc(heading)}">
${donut}
<div class="fox-energy-chart-center">
<div class="fox-energy-chart-pct" style="color:${esc(accent)}">${Math.round(centerPct)}%</div>
<div class="fox-energy-chart-label">${esc(centerLabel)}</div>
</div>
</div>
</div>`;
}

const FOX_ANALYSIS_SPLIT_COLORS = {
  selfConsumption: "#894BFC",
  export: "#eb6d48",
  selfSufficiency: "#eb6d48",
  gridPurchase: "#03BD9A",
};

function renderEnergyBalanceHelpIcon() {
  return `<button type="button" class="fox-analysis-help-btn" data-action="energy-balance-help-open" aria-label="Energy Balance help">
<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="8" y="11.5" text-anchor="middle" font-size="10" font-weight="600" fill="currentColor">?</text></svg>
</button>`;
}

function renderEnergyBalanceHelpModal() {
  return `<div class="fox-help-modal-backdrop" data-energy-balance-help-modal="1" data-action="energy-balance-help-backdrop">
<div class="fox-help-modal" data-action="energy-balance-help-dialog" role="dialog" aria-modal="true" aria-labelledby="fox-energy-balance-help-title">
<button type="button" class="fox-help-modal-close" data-action="energy-balance-help-close" aria-label="Close">×</button>
<h2 id="fox-energy-balance-help-title" class="fox-help-modal-title">Energy Balance</h2>
<div class="fox-help-modal-body">
<p>The energy balance refers to the proportion between the production and consumption.</p>
<p>A positive energy balance means that you have produced more energy than you consumed.</p>
<p>A negative energy balance means that you have produced less energy than you consumed.</p>
</div>
<div class="fox-help-modal-footer">
<button type="button" class="fox-help-modal-ok" data-action="energy-balance-help-close">Ok</button>
</div>
</div>
</div>`;
}

function renderFoxAnalysisProporBar(segments, total, attrs = "") {
  const sum = segments.reduce((s, seg) => s + Math.max(0, seg.value), 0);
  const t = total > 0 ? total : sum;
  if (t <= 0) {
    return `<div class="fox-analysis-propor fox-analysis-propor--empty"${attrs} aria-hidden="true"></div>`;
  }
  const bars = segments
    .filter((seg) => seg.value > 0)
    .map((seg) => {
      const pct = (seg.value / t) * 100;
      const label = pct >= 10 ? `<span>${Math.round(pct)}%</span>` : "";
      return `<div class="fox-analysis-propor-seg" style="width:${pct.toFixed(2)}%;background:${seg.color}" title="${esc(seg.label)}">${label}</div>`;
    })
    .join("");
  return `<div class="fox-analysis-propor"${attrs} role="img" aria-hidden="true">${bars}</div>`;
}

function renderFoxAnalysisInfoRowInner({ label, value, pct, color }) {
  const v = Number(value ?? 0) || 0;
  const p = Number(pct ?? 0) || 0;
  return `<div class="fox-analysis-info-na">${esc(label)}</div>
<div class="fox-analysis-info-nu">
<div class="fox-analysis-info-l">${v.toFixed(2)}<span>kWh</span></div>
<div class="fox-analysis-info-r" style="color:${color}">${Math.round(p)}%</div>
</div>
<div class="fox-analysis-info-pr" style="background:${color}"></div>`;
}

function renderFoxAnalysisInfoRow(row) {
  return `<div class="fox-analysis-info-row">${renderFoxAnalysisInfoRowInner(row)}</div>`;
}

function renderFoxAnalysisEnergySplitCard({ cardId, title, total, segments, rows }) {
  const t = Number(total ?? 0) || 0;
  const rowHtml = rows
    .map(
      (row, i) =>
        `<div class="fox-analysis-info-row" data-energy-split-row="${i}">${renderFoxAnalysisInfoRowInner(row)}</div>`
    )
    .join("");
  return `<div class="fox-analysis-top-card fox-analysis-enerbf" data-energy-split-card="${esc(cardId)}">
<div class="fox-analysis-prc">
<div class="fox-analysis-num" data-energy-split-total>${t.toFixed(2)}<span class="fox-analysis-unit">kWh</span></div>
<div class="fox-analysis-name">${esc(title)}</div>
</div>
${renderFoxAnalysisProporBar(segments, t, ' data-energy-split-bar="1"')}
<div class="fox-analysis-info">${rowHtml}</div>
</div>`;
}

function foxAnalysisTopCardsData(a) {
  const pvTotal = Number(a.pv_production_kwh_today ?? 0) || 0;
  const pvToLoadBattery = Number(a.pv_to_load_battery_kwh_today ?? 0) || 0;
  const pvToGrid = Number(a.pv_to_grid_kwh_today ?? 0) || 0;
  const loadTotal = Number(a.load_consumption_kwh_today ?? 0) || 0;
  const loadFromPvBattery = Number(a.load_from_pv_battery_kwh_today ?? 0) || 0;
  const loadFromGrid = Number(a.load_from_grid_kwh_today ?? 0) || 0;
  const selfConsumption = Number(a.self_consumption_percent_today ?? 0) || 0;
  const selfSufficiency = Number(a.self_sufficiency_percent_today ?? 0) || 0;
  return {
    balance: Math.max(0, pvTotal - loadTotal),
    production: {
      total: pvTotal,
      segments: [
        { value: pvToLoadBattery, color: FOX_ANALYSIS_SPLIT_COLORS.selfConsumption, label: "Self-Consumption" },
        { value: pvToGrid, color: FOX_ANALYSIS_SPLIT_COLORS.export, label: "Export" },
      ],
      rows: [
        { label: "Self-Consumption", value: pvToLoadBattery, pct: selfConsumption, color: FOX_ANALYSIS_SPLIT_COLORS.selfConsumption },
        { label: "Export", value: pvToGrid, pct: Math.max(0, 100 - selfConsumption), color: FOX_ANALYSIS_SPLIT_COLORS.export },
      ],
    },
    consumption: {
      total: loadTotal,
      segments: [
        { value: loadFromPvBattery, color: FOX_ANALYSIS_SPLIT_COLORS.selfSufficiency, label: "Self-Sufficiency" },
        { value: loadFromGrid, color: FOX_ANALYSIS_SPLIT_COLORS.gridPurchase, label: "Grid Purchase" },
      ],
      rows: [
        { label: "Self-Sufficiency", value: loadFromPvBattery, pct: selfSufficiency, color: FOX_ANALYSIS_SPLIT_COLORS.selfSufficiency },
        { label: "Grid Purchase", value: loadFromGrid, pct: Math.max(0, 100 - selfSufficiency), color: FOX_ANALYSIS_SPLIT_COLORS.gridPurchase },
      ],
    },
  };
}

function patchFoxAnalysisInfoRowEl(rowEl, { value, pct, color }) {
  if (!rowEl) return;
  const v = Number(value ?? 0) || 0;
  const p = Number(pct ?? 0) || 0;
  const l = rowEl.querySelector(".fox-analysis-info-l");
  const r = rowEl.querySelector(".fox-analysis-info-r");
  const pr = rowEl.querySelector(".fox-analysis-info-pr");
  if (l) l.innerHTML = `${v.toFixed(2)}<span>kWh</span>`;
  if (r) {
    r.textContent = `${Math.round(p)}%`;
    r.style.color = color;
  }
  if (pr) pr.style.background = color;
}

function patchFoxAnalysisProporBarEl(barEl, segments, total) {
  if (!barEl) return;
  const sum = segments.reduce((s, seg) => s + Math.max(0, seg.value), 0);
  const t = total > 0 ? total : sum;
  const active = segments.filter((seg) => seg.value > 0);
  const existing = barEl.querySelectorAll(".fox-analysis-propor-seg");
  if (!active.length) {
    barEl.className = "fox-analysis-propor fox-analysis-propor--empty";
    barEl.innerHTML = "";
    return;
  }
  barEl.className = "fox-analysis-propor";
  if (existing.length !== active.length) {
    barEl.innerHTML = active
      .map((seg) => {
        const pct = (seg.value / t) * 100;
        const label = pct >= 10 ? `<span>${Math.round(pct)}%</span>` : "";
        return `<div class="fox-analysis-propor-seg" style="width:${pct.toFixed(2)}%;background:${seg.color}" title="${esc(seg.label)}">${label}</div>`;
      })
      .join("");
    return;
  }
  active.forEach((seg, i) => {
    const el = existing[i];
    const pct = (seg.value / t) * 100;
    el.style.width = `${pct.toFixed(2)}%`;
    el.style.background = seg.color;
    el.title = seg.label;
    el.innerHTML = pct >= 10 ? `<span>${Math.round(pct)}%</span>` : "";
  });
}

function patchFoxAnalysisSplitCardEl(root, cardId, { total, segments, rows }) {
  const card = root.querySelector(`[data-energy-split-card="${cardId}"]`);
  if (!card) return false;
  const num = card.querySelector("[data-energy-split-total]");
  if (num) num.innerHTML = `${Number(total ?? 0).toFixed(2)}<span class="fox-analysis-unit">kWh</span>`;
  patchFoxAnalysisProporBarEl(card.querySelector("[data-energy-split-bar]"), segments, total);
  card.querySelectorAll("[data-energy-split-row]").forEach((rowEl, i) => {
    patchFoxAnalysisInfoRowEl(rowEl, rows[i] || {});
  });
  return true;
}

function patchFoxAnalysisTopCardsEl(topEl, a) {
  const data = foxAnalysisTopCardsData(a);
  const balanceEl = topEl.querySelector("[data-energy-balance-value]");
  if (balanceEl) balanceEl.innerHTML = `${data.balance.toFixed(2)}<span>kWh</span>`;
  patchFoxAnalysisSplitCardEl(topEl, "production", data.production);
  patchFoxAnalysisSplitCardEl(topEl, "consumption", data.consumption);
}

function foxAnalysisIconHtml(key, { muted = false } = {}) {
  let svg = FOX_ANALYSIS_ICONS[key] || "";
  if (!svg) return "";
  if (muted) svg = svg.replace(/fill="#[^"]+"/g, 'fill="currentColor"');
  return `<span class="fox-analysis-stat-icon${muted ? " fox-analysis-stat-icon--muted" : ""}" aria-hidden="true">${svg}</span>`;
}

function renderFoxAnalysisStatCol(label, value, iconKey, options = {}) {
  const v = Number(value ?? 0) || 0;
  return `<div class="fox-analysis-stat-col">
${foxAnalysisIconHtml(iconKey, options)}
<div class="fox-analysis-stat-col-nu">${v.toFixed(2)}<span>kWh</span></div>
<div class="fox-analysis-stat-col-na">${esc(label)}</div>
</div>`;
}

function renderFoxAnalysisFlowBridge() {
  return `<div class="fox-analysis-stat-bridge" aria-hidden="true">
<div class="fox-analysis-stat-flow flow-l"><span class="fox-analysis-stat-flow-glow"></span></div>
<div class="fox-analysis-stat-flow flow-r"><span class="fox-analysis-stat-flow-glow"></span></div>
</div>`;
}

function buildEnergyBreakdownPvRow(a) {
  const pvTotal = Number(a.pv_production_kwh_today ?? 0) || 0;
  const pvToLoadBattery = Number(a.pv_to_load_battery_kwh_today ?? 0) || 0;
  const pvToGrid = Number(a.pv_to_grid_kwh_today ?? 0) || 0;
  const selfConsumption = Number(a.self_consumption_percent_today ?? 0) || 0;
  return renderEnergyBreakdownRow({
    heading: "PV Production",
    totalKwh: pvTotal,
    metrics: [
      { label: "To Load & Battery", value: pvToLoadBattery, color: FOX_ENERGY.pv },
      { label: "To Grid", value: pvToGrid, color: "var(--primary-text-color)" },
    ],
    segments: [
      { value: pvToLoadBattery, color: FOX_ENERGY.pv },
      { value: pvToGrid, color: FOX_ENERGY.muted },
    ],
    centerPct: selfConsumption,
    centerLabel: "Self-Consumption",
    accent: FOX_ENERGY.pv,
  });
}

function buildEnergyBreakdownLoadRow(a) {
  const loadTotal = Number(a.load_consumption_kwh_today ?? 0) || 0;
  const loadFromPvBattery = Number(a.load_from_pv_battery_kwh_today ?? 0) || 0;
  const loadFromGrid = Number(a.load_from_grid_kwh_today ?? 0) || 0;
  const selfSufficiency = Number(a.self_sufficiency_percent_today ?? 0) || 0;
  return renderEnergyBreakdownRow({
    heading: "Load Consumption",
    totalKwh: loadTotal,
    metrics: [
      { label: "From PV & Battery", value: loadFromPvBattery, color: FOX_ENERGY.load },
      { label: "From Grid", value: loadFromGrid, color: "var(--primary-text-color)" },
    ],
    segments: [
      { value: loadFromPvBattery, color: FOX_ENERGY.load },
      { value: loadFromGrid, color: FOX_ENERGY.muted },
    ],
    centerPct: selfSufficiency,
    centerLabel: "Self-Sufficiency",
    accent: FOX_ENERGY.load,
  });
}

function renderEnergyReportBalanceCard(a) {
  const data = foxAnalysisTopCardsData(a);
  return `<div class="card fox-report-balance-card">
<div class="fox-analysis-balance-icon" aria-hidden="true">
<svg viewBox="0 0 48 48"><circle cx="19" cy="24" r="13" fill="${FOX_ANALYSIS_SPLIT_COLORS.selfConsumption}" opacity="0.88"/><circle cx="29" cy="24" r="13" fill="${FOX_ANALYSIS_SPLIT_COLORS.export}" opacity="0.88"/></svg>
</div>
<div class="fox-analysis-top-value">${data.balance.toFixed(2)}<span>kWh</span></div>
<div class="fox-analysis-top-heading-row">
<div class="fox-analysis-top-heading">Energy Balance</div>
${renderEnergyBalanceHelpIcon()}
</div>
</div>`;
}

function renderEnergyReportPvDonutCard(a) {
  return `<div class="card fox-report-donut-card"><div class="fox-energy-panel fox-energy-panel--single">${buildEnergyBreakdownPvRow(a)}</div></div>`;
}

function renderEnergyReportLoadDonutCard(a) {
  return `<div class="card fox-report-donut-card"><div class="fox-energy-panel fox-energy-panel--single">${buildEnergyBreakdownLoadRow(a)}</div></div>`;
}

function formatEnergyReportDetailDate(d) {
  const date = d.toLocaleDateString(undefined, { day: "2-digit", month: "2-digit", year: "numeric" });
  const wd = d.toLocaleDateString(undefined, { weekday: "short" });
  return `${date} (${wd})`;
}

function emptyEnergyReportDetailMetrics() {
  return {
    pvExport: 0,
    pvSelf: 0,
    pvTotal: 0,
    loadGrid: 0,
    loadSelf: 0,
    loadTotal: 0,
  };
}

function energyReportDetailMetricsFromBreakdown(b) {
  return {
    pvExport: b.pv_to_grid_kwh,
    pvSelf: b.pv_to_load_battery_kwh,
    pvTotal: b.pv_production_kwh,
    loadGrid: b.load_from_grid_kwh,
    loadSelf: b.load_from_pv_battery_kwh,
    loadTotal: b.load_consumption_kwh,
  };
}

function buildEnergyReportDetailRows(points, period, offset = 0, now = new Date()) {
  const { start, end } = energyPeriodBounds(period, offset, now);
  const todayMs = startOfLocalDay(now).getTime();
  const rows = [];

  const pushRow = (label, days) => {
    if (!days.length) {
      rows.push({ label, ...emptyEnergyReportDetailMetrics() });
      return;
    }
    const b = computeEnergyBreakdown(points, days);
    rows.push({ label, ...energyReportDetailMetricsFromBreakdown(b) });
  };

  if (period === "day") {
    pushRow(formatEnergyReportDetailDate(start), [start]);
    return rows;
  }
  if (period === "week") {
    for (const day of buildFullWeekDays(start)) {
      if (startOfLocalDay(day).getTime() > todayMs) {
        rows.push({ label: formatEnergyReportDetailDate(day), ...emptyEnergyReportDetailMetrics() });
        continue;
      }
      pushRow(formatEnergyReportDetailDate(day), [day]);
    }
    return rows;
  }
  if (period === "month") {
    for (const day of buildFullMonthDays(start)) {
      if (startOfLocalDay(day).getTime() > todayMs) {
        rows.push({ label: formatEnergyReportDetailDate(day), ...emptyEnergyReportDetailMetrics() });
        continue;
      }
      pushRow(formatEnergyReportDetailDate(day), [day]);
    }
    return rows;
  }
  if (period === "year") {
    const year = start.getFullYear();
    for (let m = 0; m < 12; m += 1) {
      const monthStart = new Date(year, m, 1);
      const monthEnd = new Date(year, m + 1, 0, 23, 59, 59, 999);
      const label = monthStart.toLocaleDateString(undefined, { month: "short", year: "numeric" });
      if (offset === 0 && monthStart.getTime() > todayMs) {
        rows.push({ label, ...emptyEnergyReportDetailMetrics() });
        continue;
      }
      const effectiveEnd = offset === 0 && monthEnd > now ? now : monthEnd;
      const days = buildDaysInRange(monthStart, effectiveEnd);
      pushRow(label, days);
    }
    return rows;
  }

  const years = new Set();
  for (const key of ["pv", "feedIn", "load", "discharge", "charge", "grid"]) {
    for (const p of points[key] || []) years.add(new Date(p.t).getFullYear());
  }
  const yearList = Array.from(years)
    .filter((y) => y >= 2000 && y <= now.getFullYear())
    .sort((a, b) => a - b);
  if (!yearList.length) yearList.push(now.getFullYear());
  for (const year of yearList) {
    const yStart = new Date(year, 0, 1);
    const yEnd = year === now.getFullYear() ? end : new Date(year, 11, 31, 23, 59, 59, 999);
    pushRow(String(year), buildDaysInRange(yStart, yEnd));
  }
  return rows;
}

function formatEnergyReportKwh(v) {
  return (Number(v) || 0).toFixed(2);
}

function renderEnergyReportDetailsTable(rows) {
  if (!rows?.length) {
    return `<p class="placeholder chart-empty">No detail rows for this period.</p>`;
  }
  const body = rows
    .map(
      (row) => `<tr>
<td>${esc(row.label)}</td>
<td>${formatEnergyReportKwh(row.pvExport)}</td>
<td>${formatEnergyReportKwh(row.pvSelf)}</td>
<td>${formatEnergyReportKwh(row.pvTotal)}</td>
<td>${formatEnergyReportKwh(row.loadGrid)}</td>
<td>${formatEnergyReportKwh(row.loadSelf)}</td>
<td>${formatEnergyReportKwh(row.loadTotal)}</td>
</tr>`
    )
    .join("");
  return `<div class="fox-report-details-table-wrap">
<table class="fox-report-details-table">
<thead>
<tr>
<th rowspan="2">Date</th>
<th colspan="3" class="fox-report-th-group">PV Production (kWh)</th>
<th colspan="3" class="fox-report-th-group">Load Consumption (kWh)</th>
</tr>
<tr>
<th>Export to Grid</th>
<th>To Load &amp; Battery (Self-Consumption)</th>
<th>Total</th>
<th>From Grid</th>
<th>From PV and Battery (Self-Sufficiency)</th>
<th>Total</th>
</tr>
</thead>
<tbody>${body}</tbody>
</table>
</div>`;
}

async function fetchEnergyReportData(hass, plant, plantState, period, offset = 0) {
  const now = new Date();
  const title = energyPeriodNavLabel(period, offset, now);
  const bar = await fetchFoxMirroredBarChart(hass, plant, plantState, period, offset);
  const bounds = energyPeriodBounds(period, offset, now);
  const fetchEnd = bounds.end > now ? now : bounds.end;
  const { points, error } = await fetchEnergyHistoryPoints(hass, plant, plantState, bounds.start, fetchEnd);
  if (!points) {
    return {
      title,
      error: error || "Daily energy sensors not found. Reload FoxESS Plant.",
      analytics: null,
      chartSvg: bar?.svg || "",
      detailRows: [],
    };
  }
  const detailRows = buildEnergyReportDetailRows(points, period, offset, now);
  const analytics = bar.breakdown
    ? analyticsFromBreakdown(bar.breakdown)
    : readLiveAnalytics(hass, plant, plantState, null);
  return {
    title,
    error: null,
    analytics,
    breakdown: bar.breakdown,
    chartSvg: bar.svg,
    detailRows,
  };
}

function renderFoxAnalysisTopCards(a) {
  const data = foxAnalysisTopCardsData(a);
  return `<div class="fox-analysis-top">
<div class="fox-analysis-top-card fox-analysis-top-card--balance">
<div class="fox-analysis-balance-icon" aria-hidden="true">
<svg viewBox="0 0 48 48"><circle cx="19" cy="24" r="13" fill="${FOX_ANALYSIS_SPLIT_COLORS.selfConsumption}" opacity="0.88"/><circle cx="29" cy="24" r="13" fill="${FOX_ANALYSIS_SPLIT_COLORS.export}" opacity="0.88"/></svg>
</div>
<div class="fox-analysis-top-value" data-energy-balance-value>${data.balance.toFixed(2)}<span>kWh</span></div>
<div class="fox-analysis-top-heading-row">
<div class="fox-analysis-top-heading">Energy Balance</div>
${renderEnergyBalanceHelpIcon()}
</div>
</div>
${renderFoxAnalysisEnergySplitCard({
  cardId: "production",
  title: "Production",
  ...data.production,
})}
${renderFoxAnalysisEnergySplitCard({
  cardId: "consumption",
  title: "Consumption",
  ...data.consumption,
})}
</div>`;
}

function renderFoxAnalysisLineSparkline(values, color, { placeholder = false } = {}) {
  const width = 132;
  const height = 40;
  const pad = { l: 0, r: 0, t: 6, b: 6 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  if (placeholder) {
    const y0 = pad.t + h * 0.62;
    const y1 = pad.t + h * 0.38;
    const path = `M${pad.l},${y0.toFixed(1)} L${(pad.l + w * 0.35).toFixed(1)},${(y0 - h * 0.08).toFixed(1)} L${(pad.l + w * 0.72).toFixed(1)},${(y1 + h * 0.05).toFixed(1)} L${(pad.l + w).toFixed(1)},${y1.toFixed(1)}`;
    return `<svg class="fox-analysis-sparkline fox-analysis-sparkline--placeholder" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><path d="${path}" fill="none" stroke="${color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" opacity="0.38" stroke-dasharray="4 3"/></svg>`;
  }
  const data = (values || []).map((v) => Number(v) || 0);
  if (data.length < 2) {
    return `<svg class="fox-analysis-sparkline fox-analysis-sparkline--empty" viewBox="0 0 ${width} ${height}" aria-hidden="true"></svg>`;
  }
  let yMax = 0.1;
  let yMin = 0;
  for (const v of data) {
    yMax = Math.max(yMax, v);
    yMin = Math.min(yMin, v);
  }
  if (yMax - yMin < yMax * 0.08 && yMin > 0) {
    yMin = Math.max(0, yMin - (yMax - yMin) * 0.35);
  }
  const span = Math.max(yMax - yMin, yMax * 0.06, 0.1) * 1.08;
  const base = yMin;
  const pts = data.map((v, i) => ({
    x: pad.l + (i / (data.length - 1)) * w,
    y: pad.t + h - ((v - base) / span) * h,
  }));
  const path = smoothLinePath(pts);
  if (!path) {
    return `<svg class="fox-analysis-sparkline fox-analysis-sparkline--empty" viewBox="0 0 ${width} ${height}" aria-hidden="true"></svg>`;
  }
  return `<svg class="fox-analysis-sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

function buildTariffIntradaySeries(importPts, exportPts, rates, range, currency, tariff) {
  const useSchedule =
    tariff &&
    (normalizeTariffImportSource(tariff.import_source) === "schedule" ||
      normalizeTariffExportSource(tariff.export_source) === "schedule");
  const standingDailyMajor = minorToMajor(rates.standing_charge_p_per_day, currency);
  const importKwh = interpolatePointsToPeriod(importPts, ANALYSIS_SPARK_SAMPLE_MS, range.tMin, range.nowMs).map(
    (p) => Math.max(0, p.v)
  );
  const exportKwh = interpolatePointsToPeriod(exportPts, ANALYSIS_SPARK_SAMPLE_MS, range.tMin, range.nowMs).map(
    (p) => Math.max(0, p.v)
  );
  const slots = Math.max(importKwh.length, exportKwh.length, 1);
  const daySpan = range.tMax - range.tMin;
  const importCost = [];
  const exportRevenue = [];
  const totalCost = [];
  for (let i = 0; i < slots; i += 1) {
    const ik = importKwh[i] ?? importKwh[importKwh.length - 1] ?? 0;
    const ek = exportKwh[i] ?? exportKwh[exportKwh.length - 1] ?? 0;
    const t = range.tMin + i * ANALYSIS_SPARK_SAMPLE_MS;
    const slotRates = useSchedule ? tariffRatesAtTime(tariff, t) : rates;
    const importRateMajor = minorToMajor(slotRates.import_p_per_kwh, currency);
    const exportRateMajor = minorToMajor(slotRates.export_p_per_kwh, currency);
    const standing = standingDailyMajor * Math.min(1, Math.max(0, (t - range.tMin) / daySpan));
    const ic = ik * importRateMajor;
    const er = ek * exportRateMajor;
    importCost.push(ic);
    exportRevenue.push(er);
    totalCost.push(standing + ic - er);
  }
  return {
    importCost: downsampleSparkSeries(importCost),
    exportRevenue: downsampleSparkSeries(exportRevenue),
    totalCost: downsampleSparkSeries(totalCost),
  };
}

async function fetchAnalysisTariffIntraday(hass, plant, plantState, overviewDaily, { start, end } = {}) {
  const tariff = plantState?.tariff;
  if (!tariff?.configured) {
    return { configured: false };
  }
  const currency = tariffCurrencyFromTariff(tariff);
  const rates = tariffEffectiveRates(tariff);
  const map = resolveEntityMap(hass, plant, plantState);
  const importId = map.grid_consumption_energy_today;
  const exportId = map.feed_in_energy_today;
  const now = new Date();
  const range =
    start && end
      ? {
          tMin: start.getTime(),
          nowMs: Math.min(end.getTime(), now.getTime()),
          tMax: end.getTime(),
        }
      : getStatisticsDayRange(now);
  const ids = [importId, exportId].filter(Boolean);
  let importPts = [];
  let exportPts = [];
  if (ids.length) {
    const hist = await fetchHistoryDuring(hass, ids, new Date(range.tMin), new Date(range.nowMs));
    importPts = importId ? historyToPoints(historyRowsForEntity(hist, importId)) : [];
    exportPts = exportId ? historyToPoints(historyRowsForEntity(hist, exportId)) : [];
  }
  const series = buildTariffIntradaySeries(importPts, exportPts, rates, range, currency, tariff);
  const analytics = readLiveAnalytics(hass, plant, plantState, overviewDaily);
  const importKwh = Number(analytics.load_from_grid_kwh_today ?? 0) || 0;
  const exportKwh = Number(analytics.pv_to_grid_kwh_today ?? 0) || 0;
  const importCost = importKwh * minorToMajor(rates.import_p_per_kwh, currency);
  const exportRevenue = exportKwh * minorToMajor(rates.export_p_per_kwh, currency);
  const standing = minorToMajor(rates.standing_charge_p_per_day, currency);
  const totalCost = standing + importCost - exportRevenue;
  return {
    configured: true,
    currency,
    rates,
    totals: { importCost, exportRevenue, standing, totalCost, importKwh, exportKwh },
    series,
  };
}

function renderFoxAnalysisSummaryRow(label, displayValue, unit, sparklineHtml, { muted = false, valueKey = "", labelKey = "" } = {}) {
  const unitHtml = unit ? `<span>${esc(unit)}</span>` : "";
  const valueAttr = valueKey ? ` data-summary-value="${esc(valueKey)}"` : "";
  const labelAttr = labelKey ? ` data-summary-label="${esc(labelKey)}"` : "";
  return `<div class="fox-analysis-summary-row${muted ? " fox-analysis-summary-row--muted" : ""}">
<div class="fox-analysis-summary-row-main">
<span class="fox-analysis-summary-label"${labelAttr}>${esc(label)}</span>
<strong class="fox-analysis-summary-value"${valueAttr}>${esc(displayValue)}${unitHtml}</strong>
</div>
<div class="fox-analysis-summary-spark">${sparklineHtml}</div>
</div>`;
}

function renderFoxAnalysisSummaryCard(a, sparkData, analysisTariff, { loading = false, period = "day" } = {}) {
  const periodLabel = energyPeriodSummaryLabel(period);
  const pvVal = Number(a.pv_production_kwh_today ?? 0) || 0;
  const loadVal = Number(a.load_consumption_kwh_today ?? 0) || 0;
  let prodSpark = "";
  let consSpark = "";
  const sparkLoading = loading || sparkData?.loading;
  let prodSeries = sparkData?.production;
  let consSeries = sparkData?.consumption;
  if (period === "day" && !sparkLoading && !sparkData?.error) {
    prodSeries = syncSparkSeriesToTotal(prodSeries, pvVal);
    consSeries = syncSparkSeriesToTotal(consSeries, loadVal);
  }
  prodSeries = ensureSparkSeries(prodSeries);
  consSeries = ensureSparkSeries(consSeries);
  if (sparkLoading) {
    prodSpark = `<span class="fox-analysis-sparkline-loading" aria-hidden="true"></span>`;
    consSpark = prodSpark;
  } else if (prodSeries.length >= 2) {
    prodSpark = renderFoxAnalysisLineSparkline(prodSeries, FOX_ANALYSIS_SPARK_COLORS.production);
    consSpark = renderFoxAnalysisLineSparkline(consSeries, FOX_ANALYSIS_SPARK_COLORS.consumption);
  } else {
    prodSpark = renderFoxAnalysisLineSparkline([], FOX_ANALYSIS_SPARK_COLORS.production);
    consSpark = renderFoxAnalysisLineSparkline([], FOX_ANALYSIS_SPARK_COLORS.consumption);
  }

  const tariffReady = analysisTariff?.configured;
  const tariffLoading = loading && !tariffReady;
  const placeholderSpark = (color) =>
    renderFoxAnalysisLineSparkline(null, color, { placeholder: true });
  let exportSpark = placeholderSpark(FOX_ANALYSIS_SPARK_COLORS.exportRevenue);
  let importSpark = placeholderSpark(FOX_ANALYSIS_SPARK_COLORS.importCost);
  let totalSpark = placeholderSpark(FOX_ANALYSIS_SPARK_COLORS.totalCost);
  let exportDisplay = "—";
  let exportUnit = "";
  let importDisplay = "—";
  let importUnit = "";
  let totalDisplay = "—";
  let totalUnit = "";
  let totalMuted = true;

  if (tariffLoading) {
    exportSpark = `<span class="fox-analysis-sparkline-loading" aria-hidden="true"></span>`;
    importSpark = exportSpark;
    totalSpark = exportSpark;
  } else if (tariffReady) {
    const totals = analysisTariff.totals ?? {};
    const series = analysisTariff.series ?? {};
    if (series.exportRevenue?.length >= 2) {
      exportSpark = renderFoxAnalysisLineSparkline(series.exportRevenue, FOX_ANALYSIS_SPARK_COLORS.exportRevenue);
    }
    if (series.importCost?.length >= 2) {
      importSpark = renderFoxAnalysisLineSparkline(series.importCost, FOX_ANALYSIS_SPARK_COLORS.importCost);
    }
    if (series.totalCost?.length >= 2) {
      totalSpark = renderFoxAnalysisLineSparkline(series.totalCost, FOX_ANALYSIS_SPARK_COLORS.totalCost);
    }
    const currency = analysisTariff.currency ?? "GBP";
    const exportMoney = formatTariffMoneyDisplay(totals.exportRevenue, currency);
    const importMoney = formatTariffMoneyDisplay(totals.importCost, currency);
    const totalMoney = formatTariffMoneyDisplay(totals.totalCost, currency);
    exportDisplay = exportMoney.value;
    exportUnit = exportMoney.unit;
    importDisplay = importMoney.value;
    importUnit = importMoney.unit;
    totalDisplay = totalMoney.value;
    totalUnit = totalMoney.unit;
    totalMuted = false;
  }

  const rows = [
    renderFoxAnalysisSummaryRow(`${periodLabel} Production`, pvVal.toFixed(2), "kWh", prodSpark, {
      valueKey: "production",
      labelKey: "production",
    }),
    renderFoxAnalysisSummaryRow(`${periodLabel} Consumption`, loadVal.toFixed(2), "kWh", consSpark, {
      valueKey: "consumption",
      labelKey: "consumption",
    }),
    renderFoxAnalysisSummaryRow("Exported Energy Revenue", exportDisplay, exportUnit, exportSpark, {
      valueKey: "export_revenue",
      muted: !tariffReady,
    }),
    renderFoxAnalysisSummaryRow("Imported Energy Cost", importDisplay, importUnit, importSpark, {
      valueKey: "import_cost",
      muted: !tariffReady,
    }),
    renderFoxAnalysisSummaryRow("Total Revenue", totalDisplay, totalUnit, totalSpark, {
      valueKey: "total_cost",
      muted: totalMuted,
    }),
  ].join("");
  return `<div class="fox-analysis-summary-card-inner">
<div class="fox-analysis-summary-head">
<h3 class="fox-analysis-summary-title">Analysis</h3>
<button type="button" class="fox-analysis-summary-details" data-action="nav" data-view="energy_analysis">Details ›</button>
</div>
<div class="fox-analysis-summary-rows">${rows}</div>
</div>`;
}

function renderFoxSupplyUsagePanel(a) {
  const gridHint =
    a.grid_data_source === "glow" && a.grid_import_kw_live != null
      ? `<p class="field-hint" style="margin:-4px 0 8px;text-align:center">Live meter ${Number(a.grid_import_kw_live).toFixed(2)} kW · grid from Glow smart meter</p>`
      : a.grid_data_source === "glow"
        ? `<p class="field-hint" style="margin:-4px 0 8px;text-align:center">Grid import from Glow smart meter</p>`
        : "";
  return `<div class="fox-analysis-stat-r">
<div class="fox-analysis-stat-na">Supply</div>
${gridHint}
<div class="fox-analysis-stat-row">
${renderFoxAnalysisStatCol("Imported", a.load_from_grid_kwh_today, "imported", { muted: true })}
${renderFoxAnalysisStatCol("PV Produced", a.pv_production_kwh_today, "pv_produced")}
${renderFoxAnalysisStatCol("Discharged", a.battery_discharge_kwh_today, "discharged")}
</div>
${renderFoxAnalysisFlowBridge()}
<div class="fox-analysis-stat-usage-wrap">
<div class="fox-analysis-stat-na fox-analysis-stat-na--overlay">Usage</div>
<div class="fox-analysis-stat-row">
${renderFoxAnalysisStatCol("Exported", a.pv_to_grid_kwh_today, "exported", { muted: true })}
${renderFoxAnalysisStatCol("Consumed", a.load_consumption_kwh_today, "consumed")}
${renderFoxAnalysisStatCol("Charged", a.battery_charge_kwh_today, "charged")}
</div>
</div>
</div>`;
}

function renderDeviceRealtimeLegend(visible, { socSeries = null } = {}) {
  const seen = new Set();
  const items = [];
  for (const s of visible) {
    const group = s.legendGroup || s.id;
    if (seen.has(group)) continue;
    seen.add(group);
    items.push({ group, label: s.label || group, color: s.color || "#888" });
  }
  if (socSeries?.points?.length) {
    items.push({
      group: "soc",
      label: socSeries.label || "Battery SOC",
      color: socSeries.color || STATISTICS_SOC_COLOR,
    });
  }
  return items
    .map(
      (it) =>
        `<button type="button" class="statistics-legend-item" data-legend-group="${esc(it.group)}" aria-pressed="true"><i style="background:${esc(it.color)}"></i><span>${esc(it.label)}</span></button>`
    )
    .join("");
}

function foxDeviceSummaryIcon(key) {
  return FOX_DEVICE_SUMMARY_ICONS[key] || "";
}

function renderStatisticsSideLegend(visible, { socVisible = false } = {}) {
  const groupsPresent = new Set(visible.map((s) => s.legendGroup || s.id));
  if (socVisible) groupsPresent.add("soc");
  const section = (heading, items) => {
    const rows = items
      .filter((it) => groupsPresent.has(it.group))
      .map(
        (it) =>
          `<button type="button" class="statistics-legend-item statistics-legend-item--side" data-legend-group="${esc(it.group)}" aria-pressed="true"><i style="background:${esc(it.color)}"></i><span>${esc(it.label)}</span></button>`
      )
      .join("");
    if (!rows) return "";
    const head = heading ? `<div class="statistics-legend-heading">${esc(heading)}</div>` : "";
    return `<div class="statistics-legend-section">${head}${rows}</div>`;
  };
  return (
    section("", STATISTICS_SIDE_LEGEND.soc) +
    section("SUPPLY", STATISTICS_SIDE_LEGEND.supply) +
    section("USAGE", STATISTICS_SIDE_LEGEND.usage) +
    section("", STATISTICS_SIDE_LEGEND.forecast)
  );
}

/** Matches dashboard Statistics plotly-graph series (dashboard.yaml). */
const STATISTICS_CHART_SERIES = [
  {
    key: "pv_power",
    label: "Solar",
    legendGroup: "solar",
    color: "#19D4DE",
    fillColor: "rgba(25,212,222,0.16)",
    toKw: true,
    fill: true,
    lineWidth: 1.4,
    statisticsOnly: true,
  },
  {
    key: "battery_charge",
    label: "Battery",
    tooltipLabel: "Battery charging",
    legendGroup: "battery",
    color: "#8DB6FF",
    fillColor: "rgba(141,182,255,0.14)",
    toKw: true,
    clampMin: 0,
    negate: true,
    fill: true,
    lineWidth: 1.2,
    statisticsOnly: true,
  },
  {
    key: "battery_discharge",
    label: "Battery",
    tooltipLabel: "Battery discharging",
    legendGroup: "battery",
    color: "#8DB6FF",
    fillColor: "rgba(141,182,255,0.14)",
    toKw: true,
    clampMin: 0,
    fill: true,
    hideLegend: true,
    lineWidth: 1.2,
    statisticsOnly: true,
  },
  {
    key: "grid_import",
    label: "Grid",
    tooltipLabel: "Grid import",
    legendGroup: "grid",
    color: "#FF6FAF",
    fillColor: "rgba(255,111,175,0.14)",
    toKw: true,
    abs: true,
    statisticsOnly: true,
    fill: true,
    lineWidth: 1.2,
  },
  {
    key: "grid_export",
    label: "Grid",
    tooltipLabel: "Grid export",
    legendGroup: "grid",
    color: "#FF6FAF",
    fillColor: "rgba(255,111,175,0.14)",
    toKw: true,
    abs: true,
    negate: true,
    statisticsOnly: true,
    fill: true,
    hideLegend: true,
    lineWidth: 1.2,
  },
  {
    key: "load_power",
    label: "Load",
    legendGroup: "load",
    color: "#8A4DFF",
    fillColor: "rgba(138,77,255,0.14)",
    toKw: true,
    negate: true,
    fill: true,
    lineWidth: 1.2,
    statisticsOnly: true,
  },
];

const FORECAST_CHART_STYLE = {
  label: "Forecast",
  tooltipLabel: "Forecast",
  legendGroup: "forecast",
  color: "#FFD700",
  fillColor: "rgba(255,215,0,0.14)",
  fill: true,
  lineWidth: 1.2,
};

/** Consolidated top legend (one button toggles whole group). */
const STATISTICS_LEGEND_ORDER = ["solar", "battery", "grid", "load", "forecast"];
const STATISTICS_LEGEND_LABEL = {
  solar: "Solar",
  battery: "Battery",
  grid: "Grid",
  load: "Load",
  forecast: "Forecast",
};
const STATISTICS_LEGEND_COLORS = {
  solar: "#19D4DE",
  battery: "#8DB6FF",
  grid: "#FF6FAF",
  load: "#8A4DFF",
  forecast: "#FFD700",
};

/** Side legend groups (FoxCloud Energy Analysis layout). */
const STATISTICS_SOC_COLOR = "#7FD47C";
const STATISTICS_SOC_Y_TICKS = [0, 50, 100];
const STATISTICS_SIDE_LEGEND = {
  soc: [{ group: "soc", label: "SoC", color: STATISTICS_SOC_COLOR }],
  supply: [
    { group: "solar", label: "Solar", color: "#19D4DE" },
    { group: "battery", label: "Battery Discharge", color: "#8DB6FF" },
    { group: "grid", label: "Grid Import", color: "#2F6BFF" },
  ],
  usage: [
    { group: "grid", label: "Grid Export", color: "#FF6FAF" },
    { group: "battery", label: "Battery Charge", color: "#C4A3FF" },
    { group: "load", label: "Total Load", color: "#8A4DFF" },
  ],
  forecast: [{ group: "forecast", label: "Forecast", color: "#FFD700" }],
};

const STATISTICS_CHART_LAYOUT = {
  width: 1000,
  height: 440,
  pad: { l: 58, r: 8, t: 22, b: 40 },
  xTickHours: 3,
  xTickCount: 8,
  yTickStepKw: 0.5,
};

function statisticsChartLayout({ sideLegend = false, hasSoc = false } = {}) {
  const r = hasSoc ? 44 : sideLegend ? 16 : 8;
  return {
    ...STATISTICS_CHART_LAYOUT,
    pad: {
      l: sideLegend ? 58 : 52,
      r,
      t: sideLegend ? 22 : 12,
      b: 40,
    },
  };
}

/** Matches dashboard plotly-graph defaults: statistic mean, period 5minute. */
const STATISTICS_PERIOD_MS = 5 * 60 * 1000;
/** Analysis summary sparklines: 10-minute buckets for intraday trend shape. */
const ANALYSIS_SPARK_SAMPLE_MS = 10 * 60 * 1000;
const ANALYSIS_SPARK_MAX_POINTS = 72;

const BATTERY_SOC_POWER_THRESHOLD_KW = 0.04;
const BATTERY_SOC_POWER_SMOOTH_MS = STATISTICS_PERIOD_MS * 3;
const BATTERY_SOC_SLOPE_WINDOW_MS = STATISTICS_PERIOD_MS * 6;
const BATTERY_SOC_SLOPE_DELTA_PCT = 0.12;
const BATTERY_SOC_FULL_PCT = 99.5;
const BATTERY_SOC_COLORS = {
  charging: { line: "#3DDC84", fill: "rgba(61,220,132,0.2)" },
  discharging: { line: "#5B9BD5", fill: "rgba(91,155,213,0.2)" },
  idle: { line: "#8A9199", fill: "rgba(138,145,153,0.14)" },
};
const BATTERY_SOC_CHART_LAYOUT = {
  width: 1000,
  height: 300,
  pad: { l: 44, r: 8, t: 8, b: 40 },
  xTickHours: 3,
  xTickCount: 8,
  yTicks: [0, 50, 100],
};

const ENERGY_CHART_BAR = {
  pv: { suffix: "solar_energy_today", label: "PV", color: FOX_ENERGY.pv },
  load: { suffix: "load_energy_today", label: "Load", color: FOX_ENERGY.load, computed: true },
  grid: { suffix: "grid_consumption_energy_today", label: "From grid", color: "#FF6FAF" },
};

const ENERGY_PERIOD_TABS = [
  { id: "day", label: "Day" },
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "year", label: "Year" },
  { id: "total", label: "Total" },
];

/** Fox Energy Report: week / month / year only. */
const REPORTS_PERIOD_TABS = [
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "year", label: "Year" },
];

const REPORTS_NAV = [
  { id: "energy_report", label: "Energy Report" },
  { id: "octopus", label: "Octopus Energy Analysis" },
];

/** Device → Analysis energy chart (no day — real-time curve has its own day nav). */
const DEVICE_NEW_ENERGY_PERIOD_TABS = [
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "year", label: "Year" },
  { id: "total", label: "Total" },
];

function normalizeReportsPeriod(period) {
  return REPORTS_PERIOD_TABS.some((t) => t.id === period) ? period : "week";
}

const FOX_SUPPLY_SERIES = [
  { key: "solar", label: "Solar", color: "#19D4DE" },
  { key: "batteryDischarge", label: "Battery Discharge", color: "#8DB6FF" },
  { key: "gridImport", label: "Grid Import", color: "#2F6BFF" },
];

const FOX_USAGE_SERIES = [
  { key: "load", label: "Load", color: "#8A4DFF" },
  { key: "batteryCharge", label: "Battery Charge", color: "#C4A3FF" },
  { key: "gridExport", label: "Grid Export", color: "#FF6FAF" },
];

const OVERVIEW_DAILY_DAYS = 7;
const OVERVIEW_DAILY_COLORS = {
  production: "#8A4DFF",
  consumption: "#19D4DE",
  barMuted: "#4a5058",
};

const OVERVIEW_BALANCE_SPARK_COLORS = {
  charge: "#C4A3FF",
  discharge: "#8DB6FF",
};

function renderOverviewBalanceMetric(label, valueKwh, sparkHtml) {
  const has = valueKwh != null && Number.isFinite(Number(valueKwh));
  const display = has ? Number(valueKwh).toFixed(1) : "—";
  return `<div class="overview-balance-row">
<div class="overview-balance-copy">
<div class="overview-balance-heading">${esc(label)}</div>
<div class="overview-balance-total">${esc(display)}<span>kWh</span></div>
</div>
<div class="overview-balance-spark">${sparkHtml}</div>
</div>`;
}

function renderOverviewBalanceSpark(series, color, totalKwh, loading = false) {
  if (loading) {
    return `<span class="fox-analysis-sparkline-loading" aria-hidden="true"></span>`;
  }
  const synced = syncSparkSeriesToTotal(series, totalKwh);
  const data = ensureSparkSeries(synced);
  return renderFoxAnalysisLineSparkline(data, color);
}

const FOX_ANALYSIS_ICONS = {"imported": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 14 15\" fill=\"none\" id=\"icon-e_grid_import\">\n<path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M8.62038 1.00002C8.30727 1.31924 8.05824 1.70094 7.89316 2.12502H5.42571L4.89772 4.00002H7.733C7.80559 4.3576 7.93611 4.69398 8.11321 5.00001H4.61647L3.91335 7.50001H10.0859L9.78703 6.43817C10.1628 6.58504 10.5715 6.66665 10.9993 6.66669C11.0059 6.66668 11.0128 6.66607 11.0195 6.66603L11.2545 7.50001H12.7493C12.8873 7.50003 12.9993 7.61195 12.9993 7.75001V8.25001C12.9993 8.38808 12.8873 8.5 12.7493 8.50001H11.5364L13.3228 14.8503C13.3526 14.9568 13.2396 15.0466 13.1425 14.9935L6.99928 11.6296L0.85605 14.9935C0.759073 15.0463 0.646091 14.9566 0.675706 14.8503L2.46282 8.50001H1.24928C1.11133 8.49988 0.999284 8.388 0.999284 8.25001V7.75001C0.999285 7.61203 1.11133 7.50015 1.24928 7.50001H2.74407L3.44785 5.00001H2.74928C2.61133 4.99988 2.49928 4.888 2.49928 4.75001V4.25002C2.49928 4.11203 2.61133 4.00015 2.74928 4.00002H3.7291L4.49668 1.27345C4.54217 1.11182 4.68944 1.00009 4.85735 1.00002H8.62038ZM2.40358 12.864L5.82805 10.9883L3.31828 9.61395L2.40358 12.864ZM8.1705 10.9883L11.5956 12.864L10.6809 9.61395L8.1705 10.9883ZM3.63078 8.50262L6.99928 10.347L10.3684 8.50262L10.3678 8.50001H3.63144L3.63078 8.50262Z\" fill=\"#52C41A\" />\n<path d=\"M13.6659 3.33336L10.9993 6.00001V4.00002H8.33261V2.66669H10.9993V0.666687L13.6659 3.33336Z\" fill=\"#52C41A\" />\n</svg>", "pv_produced": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 36 36\" fill=\"none\" id=\"icon-icon-phot\">\n<g id=\"icon-icon-phot_icon-&#229;&#133;&#137;&#228;&#188;&#143;&#229;&#143;&#145;&#231;&#148;&#181;\">\n<path id=\"icon-icon-phot_Rectangle 34625637\" d=\"M4.5 7.5C4.5 5.84315 5.84315 4.5 7.5 4.5H28.5C30.1569 4.5 31.5 5.84315 31.5 7.5V28.5C31.5 30.1569 30.1569 31.5 28.5 31.5H7.5C5.84315 31.5 4.5 30.1569 4.5 28.5V7.5Z\" fill=\"#894BFC\" />\n<g id=\"icon-icon-phot_Frame\">\n<path id=\"icon-icon-phot_Vector\" d=\"M13.9738 18.0725C13.9738 19.4913 14.7413 20.8024 15.9873 21.5118C16.6011 21.8605 17.2949 22.0438 18.0008 22.0438C18.7067 22.0438 19.4005 21.8605 20.0143 21.5118C21.2602 20.8024 22.0277 19.4913 22.0277 18.0725C22.0277 16.6537 21.2602 15.3428 20.0143 14.6334C19.4005 14.2847 18.7067 14.1014 18.0008 14.1014C17.2949 14.1014 16.6011 14.2847 15.9873 14.6334C14.7413 15.3426 13.9738 16.6537 13.9738 18.0725ZM17.9947 10.4385C18.2567 10.4346 18.4861 10.6648 18.4922 10.9252L18.5003 12.5193C18.5044 12.7776 18.271 13.0039 18.0069 13.01C17.7448 13.014 17.5155 12.7836 17.5094 12.5233L17.5013 10.9292C17.5195 10.6308 17.7328 10.4427 17.9947 10.4385ZM25.9107 18.0444C25.9066 18.3029 25.7158 18.5131 25.413 18.5311L23.7966 18.5232C23.5347 18.5191 23.2991 18.2928 23.303 18.0325C23.3072 17.7742 23.5367 17.5419 23.8007 17.5458L25.4171 17.5539C25.679 17.5599 25.9147 17.7861 25.9107 18.0444ZM12.6985 18.0444C12.6944 18.3029 12.5034 18.5131 12.2008 18.5311L10.5844 18.5232C10.3225 18.5191 10.0869 18.2928 10.0909 18.0325C10.095 17.7742 10.3245 17.5419 10.5886 17.5458L12.205 17.5539C12.4669 17.5599 12.7025 17.7861 12.6985 18.0444ZM18.0067 25.7304C17.7448 25.7346 17.5153 25.5043 17.5094 25.2439L17.5013 23.6498C17.4971 23.3915 17.7306 23.1652 17.9947 23.1591C18.2567 23.1552 18.4861 23.3856 18.4922 23.6458L18.5003 25.2399C18.4821 25.5384 18.2688 25.7265 18.0069 25.7306L18.0067 25.7304ZM23.4676 12.6835C23.6566 12.8637 23.6524 13.1862 23.4697 13.3743L22.3325 14.5058C22.1496 14.6921 21.8227 14.6881 21.6317 14.508C21.4429 14.3276 21.4471 14.0052 21.6298 13.8169L22.767 12.6855C22.9924 12.4873 23.2768 12.5033 23.4676 12.6837V12.6835ZM23.6098 23.5818C23.4208 23.7619 23.1365 23.778 22.9092 23.5798L21.772 22.4483C21.5891 22.262 21.5851 21.9376 21.7739 21.7573C21.9629 21.5773 22.2918 21.5731 22.4745 21.7594L23.6117 22.8909C23.7946 23.077 23.7986 23.4016 23.6098 23.5818ZM14.2661 14.3676C14.0773 14.5479 13.7931 14.5639 13.5656 14.3658L12.4283 13.2343C12.2456 13.048 12.2415 12.7236 12.4303 12.5433C12.6193 12.3631 12.9482 12.3591 13.1311 12.5452L14.2683 13.6767C14.451 13.865 14.4571 14.1874 14.2661 14.3677V14.3676ZM12.5095 23.5036C12.3207 23.3235 12.3248 23.0009 12.5077 22.8128L13.6448 21.6813C13.8275 21.495 14.1545 21.499 14.3453 21.6793C14.5343 21.8593 14.5302 22.1819 14.3475 22.3702L13.2103 23.5017C12.9847 23.6998 12.6985 23.6838 12.5095 23.5036Z\" fill=\"white\" />\n</g>\n</g>\n</svg>", "discharged": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 20 20\" fill=\"none\" id=\"icon-icon-discharge\">\n<g id=\"icon-icon-discharge_Frame 272\">\n<path d=\"M0 2C0 0.895431 0.895431 0 2 0H18C19.1046 0 20 0.895431 20 2V18C20 19.1046 19.1046 20 18 20H2C0.895431 20 0 19.1046 0 18V2Z\" fill=\"#894BFC\" />\n<g id=\"icon-icon-discharge_Icon/ChargeOutline\">\n<path id=\"icon-icon-discharge_vector\" fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M12.5 3.25C12.5 3.11193 12.3881 3 12.25 3H7.82812C7.69005 3 7.57812 3.11193 7.57812 3.25V4H4.25C4.11193 4 4 4.11193 4 4.25V4.875C4 5.01307 4.11193 5.125 4.25 5.125H5V14.9375H4.25C4.11193 14.9375 4 15.0494 4 15.1875V15.8125C4 15.9506 4.11193 16.0625 4.25 16.0625H15.75C15.8881 16.0625 16 15.9506 16 15.8125V15.1875C16 15.0494 15.8881 14.9375 15.75 14.9375H15V5.125H15.75C15.8881 5.125 16 5.01307 16 4.875V4.25C16 4.11193 15.8881 4 15.75 4H12.5V3.25ZM9.5 10.7H7.5L10.5 6.5V9.3H12.5L9.5 13.5V10.7Z\" fill=\"white\" />\n</g>\n</g>\n</svg>", "exported": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 16 16\" fill=\"none\" id=\"icon-e_grid_export\">\n<path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M9.62037 1.00002C9.30726 1.31924 9.05824 1.70094 8.89316 2.12502H6.42571L5.89771 4.00002H8.733C8.80559 4.35761 8.93611 4.69399 9.11321 5.00002H5.61646L4.91334 7.50002H11.0859L10.787 6.43817C11.1628 6.58504 11.5715 6.66665 11.9993 6.66669C12.0059 6.66669 12.0128 6.66607 12.0195 6.66604L12.2545 7.50002H13.7493C13.8873 7.50003 13.9993 7.61196 13.9993 7.75002V8.25002C13.9993 8.38808 13.8873 8.50001 13.7493 8.50002H12.5364L14.3228 14.8503C14.3526 14.9568 14.2396 15.0466 14.1425 14.9935L7.99928 11.6296L1.85605 14.9935C1.75907 15.0463 1.64609 14.9566 1.67571 14.8503L3.46282 8.50002H2.24928C2.11132 8.49989 1.99928 8.38801 1.99928 8.25002V7.75002C1.99928 7.61203 2.11132 7.50016 2.24928 7.50002H3.74407L4.44784 5.00002H3.74928C3.61132 4.99989 3.49928 4.88801 3.49928 4.75002V4.25002C3.49928 4.11203 3.61132 4.00016 3.74928 4.00002H4.72909L5.49667 1.27346C5.54217 1.11182 5.68944 1.00009 5.85735 1.00002H9.62037ZM3.40357 12.864L6.82805 10.9883L4.31829 9.61395L3.40357 12.864ZM9.1705 10.9883L12.5956 12.864L11.6809 9.61395L9.1705 10.9883ZM4.63079 8.50262L7.99928 10.347L11.3684 8.50262L11.3678 8.50002H4.63144L4.63079 8.50262Z\" fill=\"#1677FF\" />\n<path d=\"M11.9993 2.66669H14.6659V4.00002H11.9993V6.00002L9.33261 3.33335L11.9993 0.666687V2.66669Z\" fill=\"#1677FF\" />\n</svg>", "consumed": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 36 36\" fill=\"none\" id=\"icon-icon-load\">\n<g id=\"icon-icon-load_icon-&#232;&#180;&#159;&#232;&#189;&#189;&#229;&#174;&#182;&#231;&#148;&#168;\">\n<path id=\"icon-icon-load_Rectangle 34625637\" d=\"M4.5 7.5C4.5 5.84315 5.84315 4.5 7.5 4.5H28.5C30.1569 4.5 31.5 5.84315 31.5 7.5V28.5C31.5 30.1569 30.1569 31.5 28.5 31.5H7.5C5.84315 31.5 4.5 30.1569 4.5 28.5V7.5Z\" fill=\"#EB6D48\" />\n<g id=\"icon-icon-load_Frame\">\n<path id=\"icon-icon-load_Vector\" d=\"M12.9365 19.1735V24.7738H16.3115V21.0408H19.6865V24.7738H23.0615V19.1735L17.999 14.9738L12.9365 19.1735Z\" fill=\"white\" />\n<path id=\"icon-icon-load_Vector_2\" d=\"M17.9961 11.2274L11.2461 17.0236V19.3854L17.9961 13.5909L24.7461 19.3854V17.0236L17.9961 11.2274Z\" fill=\"white\" />\n</g>\n</g>\n</svg>", "charged": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 36 36\" fill=\"none\" id=\"icon-icon-battery\">\n<g id=\"icon-icon-battery_icon-&#231;&#148;&#181;&#230;&#177;&#160;\">\n<path id=\"icon-icon-battery_Rectangle 34625637\" d=\"M4.5 7.5C4.5 5.84315 5.84315 4.5 7.5 4.5H28.5C30.1569 4.5 31.5 5.84315 31.5 7.5V28.5C31.5 30.1569 30.1569 31.5 28.5 31.5H7.5C5.84315 31.5 4.5 30.1569 4.5 28.5V7.5Z\" fill=\"#03BD9A\" />\n<g id=\"icon-icon-battery_Frame\" clip-path=\"url(#icon-icon-battery_clip0_36_2961)\">\n<path id=\"icon-icon-battery_Vector\" d=\"M21.0349 23.7746L21.0349 14.2157L14.9656 14.2157L14.9656 23.7746L21.0349 23.7746ZM16.4829 11.5776L14.9656 11.5776C14.131 11.5776 13.4482 12.1554 13.4482 12.8615L13.4482 23.7746C13.4482 24.4807 14.131 25.0585 14.9656 25.0585L21.0349 25.0585C21.8694 25.0585 22.5522 24.4807 22.5522 23.7746L22.5522 12.8615C22.5522 12.1554 21.8694 11.5776 21.0349 11.5776L19.5175 11.5776C19.5175 11.2246 19.1761 10.9357 18.7589 10.9357L17.2415 10.9357C16.8243 10.9357 16.4829 11.2246 16.4829 11.5776ZM17.2415 12.2196L21.0349 12.2196C21.4521 12.2196 21.7935 12.5084 21.7935 12.8615L21.7935 23.7746C21.7935 24.1277 21.4521 24.4165 21.0349 24.4165L14.9656 24.4165C14.5483 24.4165 14.2069 24.1277 14.2069 23.7746L14.2069 12.8615C14.2069 12.5084 14.5483 12.2196 14.9656 12.2196L17.2415 12.2196Z\" fill=\"white\" />\n</g>\n</g>\n<defs>\n<clipPath id=\"icon-icon-battery_clip0_36_2961\">\n<rect width=\"14.1429\" height=\"16.7143\" fill=\"white\" transform=\"translate(9.64258 25.0714) rotate(-90)\" />\n</clipPath>\n</defs>\n</svg>"};

const FOX_ANALYSIS_SPARK_COLORS = {
  production: "#17A589",
  consumption: "#2F6BFF",
  exportRevenue: "#17A589",
  importCost: "#EB6D48",
  totalCost: "#8A4DFF",
  revenue: "#8A4DFF",
};

function startOfLocalDay(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function endOfLocalDay(d) {
  const x = new Date(d);
  x.setHours(23, 59, 59, 999);
  return x;
}

/** Merge plant config map with live WS state and hass.states fallbacks (matches Lovelace entity ids). */
const CHART_ENTITY_FALLBACKS = {
  pv1_power: ["pv1_power"],
  pv2_power: ["pv2_power"],
  pv_power: ["pv_power_evo_10", "pv_power_now", "pv_power", "pv_power_total", "pv1_power"],
  battery_soc: ["battery_soc_1", "battery_soc"],
  battery_charge: ["battery_charge_1", "battery_charge"],
  battery_discharge: ["battery_discharge_1", "battery_discharge"],
  grid_import: ["grid_consumption", "grid_import"],
  grid_export: ["feed_in", "grid_export"],
  load_power: ["load_power", "load_power_total"],
  solar_energy_today: ["solar_energy_today"],
  feed_in_energy_today: ["feed_in_energy_today", "feed_in_energy"],
  load_energy_today: ["load_energy_today"],
  battery_discharge_today: ["battery_discharge_today"],
  battery_charge_today: ["battery_charge_today"],
  grid_consumption_energy_today: ["grid_consumption_energy_today"],
};

/** Device → Parameters page (Fox app sections). Merged into resolveEntityMap at runtime. */
const DEVICE_ENTITY_FALLBACKS = {
  pv1_voltage: ["pv1_voltage"],
  pv1_current: ["pv1_current"],
  pv1_power: ["pv1_power"],
  pv2_voltage: ["pv2_voltage"],
  pv2_current: ["pv2_current"],
  pv2_power: ["pv2_power"],
  pv3_voltage: ["pv3_voltage"],
  pv3_current: ["pv3_current"],
  pv3_power: ["pv3_power"],
  pv4_voltage: ["pv4_voltage"],
  pv4_current: ["pv4_current"],
  pv4_power: ["pv4_power"],
  pv_power: ["pv_power_evo_10", "pv_power_now", "pv_power", "pv_power_total", "pv1_power"],
  battery_power: ["invbatpower_1", "invbatpower", "battery_power"],
  solar_energy_today: ["solar_energy_today"],
  solar_energy_total: ["solar_energy_total"],
  grid_voltage_R: ["grid_voltage_R"],
  inv_current_R: ["inv_current_R"],
  inv_power: ["inv_power"],
  rfreq: ["rfreq"],
  invtemp: ["invtemp"],
  eps_rvolt_R: ["eps_rvolt_R"],
  eps_rcurrent_R: ["eps_rcurrent_R"],
  eps_power_R: ["eps_power_R"],
  eps_frequency: ["eps_frequency"],
  load_power_R: ["load_power_R"],
  load_power_total: ["load_power_total"],
  load_energy_total: ["load_energy_total", "load_power_total", "load_consumption_total"],
  grid_status: ["grid_status"],
  feed_in_energy_total: ["feed_in_energy_total"],
  grid_consumption_energy_total: ["grid_consumption_energy_total"],
  battery_soh: ["battery_soh"],
  battery_cycles: ["battery_cycles"],
  battery_kwh_remaining: ["battery_kwh_remaining"],
  bms_kwh_nominal: ["bms_kwh_nominal", "bms_kwh_remaining_1", "bms_capacity", "battery_capacity"],
  bms_kwh_remaining_1: ["bms_kwh_remaining_1"],
  bms_design_energy_wh: ["bms_design_energy_wh", "bms_kwh_nominal", "bms_kwh_remaining_1"],
  bms_ah_fcc: ["bms_ah_fcc"],
  bms_ah_nominal: ["bms_ah_nominal"],
  battery_ah_remaining: ["battery_ah_remaining", "bms_ah_remaining", "battery_remaining_capacity"],
  bms_self_discharge_rate: ["bms_self_discharge_rate"],
  bms_remaining_power_capacity: ["bms_remaining_power_capacity"],
  bms_round_trip_efficiency_remaining: ["bms_round_trip_efficiency_remaining"],
  bms_ohmic_resistance: ["bms_ohmic_resistance"],
  bms_deep_discharge_event_count: ["bms_deep_discharge_event_count"],
  bms_extreme_temp_hours: ["bms_extreme_temp_hours"],
  bms_extreme_temp_charge_hours: ["bms_extreme_temp_charge_hours"],
  bms_charge_capacity_throughput_ah: ["bms_charge_capacity_throughput_ah"],
  bms_discharge_capacity_throughput_ah: ["bms_discharge_capacity_throughput_ah"],
  datalogger_signal: ["signal_strength", "wifi_signal", "bms_signal_strength"],
  batvolt_1: ["batvolt_1", "invbatvolt_1"],
  bat_current_1: ["bat_current_1", "invbatcurrent_1"],
  battery_charge_total: ["battery_charge_total"],
  battery_discharge_total: ["battery_discharge_total"],
  bms_temp_high: ["bms_cell_temp_high_1", "bms_cell_temp_high"],
  bms_online: ["bms_online"],
  bms_pack_serial_modbus: ["bms_pack_serial_modbus"],
  modbus_protocol_version: ["modbus_protocol_version"],
  master_version: ["master_version"],
  slave_version: ["slave_version"],
  manager_version: ["manager_version"],
  inverter_alarms: ["inverter_alarms"],
  inverter_alarm_last: ["inverter_alarm_last"],
  inverter_fault_code: ["inverter_fault_code"],
  bms_fault_1_raw: ["bms_fault_1_raw"],
  bms_fault_2_raw: ["bms_fault_2_raw"],
  bms_fault_3_raw: ["bms_fault_3_raw"],
  bms_fault_4_raw: ["bms_fault_4_raw"],
  bms_fault_5_raw: ["bms_fault_5_raw"],
  bms_fault_6_raw: ["bms_fault_6_raw"],
};

const DEVICE_PV_STRINGS = [1, 2, 3, 4];

const DEVICE_PARAMETER_SECTIONS = [
  { id: "pv", title: "PV Information", kind: "pv-table" },
  {
    id: "ac",
    title: "AC Information",
    kind: "metric-table",
    keys: ["grid_voltage_R", "inv_current_R", "inv_power", "rfreq"],
    headers: ["Voltage (V)", "Current (A)", "Power (kW)", "Frequency (Hz)"],
  },
  {
    id: "eps",
    title: "EPS Information",
    kind: "metric-table",
    keys: ["eps_rvolt_R", "eps_rcurrent_R", "eps_power_R", "eps_frequency"],
    headers: ["Voltage (V)", "Current (A)", "Power (kW)", "Frequency (Hz)"],
  },
  {
    id: "load",
    title: "Load Information",
    kind: "rows",
    rows: [
      ["load_energy_today", "Daily load consumption"],
      ["load_power_total", "Total load consumption"],
      ["load_power", "Total load power"],
      ["load_power_R", "Grid load power"],
      ["eps_power_R", "EPS load power"],
    ],
  },
  {
    id: "grid",
    title: "Grid Information",
    kind: "rows",
    rows: [
      ["grid_status", "Grid Status"],
      ["feed_in_energy_today", "Daily feed-in energy"],
      ["feed_in_energy_total", "Total feed-in energy"],
      ["grid_consumption_energy_today", "Daily purchased energy"],
      ["grid_consumption_energy_total", "Total purchased energy"],
      ["grid_export", "Feed-in Power"],
      ["grid_import", "Purchased Power"],
    ],
  },
  {
    id: "battery",
    title: "Battery Information",
    kind: "rows",
    rows: [
      ["bms_kwh_nominal", "Nominal energy"],
      ["battery_soc", "SOC"],
      ["battery_kwh_remaining", "Remaining energy"],
      ["battery_status", "Status"],
      ["battery_power", "Battery power"],
      ["bat_current_1", "Current"],
      ["batvolt_1", "Voltage"],
      ["bms_temp_low", "Min. battery temperature"],
      ["battery_soh", "SOH"],
      ["battery_charge_today", "Daily charged energy"],
      ["battery_charge_total", "Total charged energy"],
      ["battery_discharge_today", "Daily discharged energy"],
      ["battery_discharge_total", "Total discharged energy"],
      ["battery_cycles", "Battery cycles"],
    ],
  },
  { id: "datalogger", title: "Datalogger Information", kind: "datalogger" },
];

/** Fox Cloud Devices → Real-time tab (full page: PV/AC/EPS tables + metric sections). */
const DEVICE_NEW_REALTIME_SECTIONS = [
  { id: "pv", title: "PV Information", kind: "pv-table" },
  {
    id: "ac",
    title: "AC Information",
    kind: "metric-table",
    keys: ["grid_voltage_R", "inv_current_R", "inv_power", "rfreq"],
    headers: ["Voltage (V)", "Current (A)", "Power (kW)", "Frequency (Hz)"],
  },
  {
    id: "eps",
    title: "EPS Information",
    kind: "metric-table",
    keys: ["eps_rvolt_R", "eps_rcurrent_R", "eps_power_R", "eps_frequency"],
    headers: ["Voltage (V)", "Current (A)", "Power (kW)", "Frequency (Hz)"],
  },
  {
    id: "load",
    title: "Load Information",
    kind: "rows",
    rows: [
      ["load_energy_today", "Daily load consumption"],
      ["load_energy_total", "Total load consumption"],
      ["load_power", "Total load power"],
      ["load_power_R", "Grid load power"],
      ["eps_power_R", "EPS load power"],
    ],
  },
  { id: "datalogger", title: "Datalogger Information", kind: "fox-datalogger" },
  {
    id: "grid",
    title: "Grid Information",
    kind: "rows",
    rows: [
      ["grid_status", "Grid Status"],
      ["feed_in_energy_today", "Daily feed-in energy"],
      ["feed_in_energy_total", "Total feed-in energy"],
      ["grid_consumption_energy_today", "Daily purchased energy"],
      ["grid_consumption_energy_total", "Total purchased energy"],
      ["grid_export", "Feed-in Power"],
      ["grid_import", "Purchased Power"],
    ],
  },
  {
    id: "battery",
    title: "Battery Information",
    kind: "subsections",
    subsections: [
      {
        title: "General",
        rows: [
          ["battery_soc", "SOC"],
          ["bms_design_energy_wh", "Capacity"],
          ["bat_current_1", "Current"],
          ["batvolt_1", "Voltage"],
          ["battery_discharge_today", "Daily discharged energy"],
          ["battery_discharge_total", "Total discharged energy"],
          ["battery_charge_today", "Daily charged energy"],
          ["battery_charge_total", "Total charged energy"],
        ],
      },
      {
        title: "Health",
        rows: [
          ["battery_soh", "SOH"],
          ["battery_ah_remaining", "Remaining Capacity"],
          ["bms_self_discharge_rate", "Evolution of self-discharging rates"],
          ["bms_remaining_power_capacity", "Remaining Power Capacity"],
          ["bms_round_trip_efficiency_remaining", "Remaining Round trip efficiency"],
          ["bms_ohmic_resistance", "Ohmic resistance"],
        ],
      },
      {
        title: "General",
        rows: [
          ["battery_charge_total", "Charge Energy throughput"],
          ["battery_discharge_total", "Discharge Energy throughput"],
          ["bms_charge_capacity_throughput_ah", "Charge Capacity throughput"],
          ["bms_discharge_capacity_throughput_ah", "Discharge Capacity throughput"],
          ["battery_cycles", "Number of full equivalent charge-discharge cycles"],
        ],
      },
      {
        title: "Tracking of harmful events",
        rows: [
          ["bms_deep_discharge_event_count", "Number of deep discharge event"],
          ["bms_extreme_temp_hours", "Time spent in extreme temp"],
          ["bms_extreme_temp_charge_hours", "Time spent charging in extreme temp"],
        ],
      },
    ],
  },
];

const ANALYTICS_STATE_KEYS = [
  "solar_energy_today",
  "feed_in_energy_today",
  "load_energy_today",
  "grid_consumption_energy_today",
  "battery_discharge_today",
  "battery_charge_today",
];

const ANALYTICS_SUFFIXES = {
  solar_energy_today: ["solar_energy_today"],
  feed_in_energy_today: ["feed_in_energy_today"],
  load_energy_today: ["load_energy_today"],
  grid_consumption_energy_today: ["grid_consumption_energy_today"],
  battery_discharge_today: ["battery_discharge_today"],
  battery_charge_today: ["battery_charge_today"],
};

function analyticsFloat(states, key) {
  const raw = states[key];
  if (raw == null || raw === "" || raw === "unknown" || raw === "unavailable") return 0;
  const n = parseFloat(raw);
  return Number.isFinite(n) ? n : 0;
}

function isValidAnalyticsEnergyState(st) {
  if (!st || st.state === "unknown" || st.state === "unavailable") return false;
  const dc = st.attributes?.device_class;
  if (dc === "power") return false;
  return Number.isFinite(parseFloat(st.state));
}

function scoreAnalyticsEntity(entityId, key, suffix, mappedId) {
  if (mappedId && entityId === mappedId) return 1000;
  if (entityId.endsWith(`_${key}`)) return 500;
  if (key.includes("_today") && (entityId.includes("_total") || entityId.endsWith("_total"))) {
    return -500;
  }
  if (entityId.endsWith(`_${suffix}`) || entityId.includes(`_${suffix}_`)) return 100;
  return 0;
}

function pickAnalyticsState(hass, map, key) {
  const suffixes = ANALYTICS_SUFFIXES[key] || [key];
  const mappedId = map[key];
  if (mappedId && isValidAnalyticsEnergyState(hass.states[mappedId])) {
    return hass.states[mappedId].state;
  }
  const ranked = [];
  for (const entityId of Object.keys(hass.states)) {
    for (const suffix of suffixes) {
      if (!entityIdMatchesSuffix(entityId, suffix)) continue;
      const st = hass.states[entityId];
      if (!isValidAnalyticsEnergyState(st)) continue;
      const score = scoreAnalyticsEntity(entityId, key, suffix, mappedId);
      if (score < 0) continue;
      ranked.push({ score, value: parseFloat(st.state), state: st.state });
      break;
    }
  }
  if (!ranked.length) return null;
  ranked.sort((a, b) => b.score - a.score || b.value - a.value);
  const bestScore = ranked[0].score;
  const tier = ranked.filter((r) => r.score === bestScore);
  return tier[0].state;
}

function applyPvTodayFallback(states, overviewDaily) {
  const out = { ...states };
  const pvHist = overviewDaily?.production?.at(-1);
  const pvLive = analyticsFloat(out, "solar_energy_today");
  if (pvHist > 0 && (pvLive <= 0 || pvLive < pvHist * 0.85)) {
    out.solar_energy_today = String(pvHist);
  }
  return out;
}

function computeAnalyticsFromStates(states) {
  let pv = analyticsFloat(states, "solar_energy_today");
  let toGrid = analyticsFloat(states, "feed_in_energy_today");
  if (pv > 0 && toGrid > pv) toGrid = pv;
  const toLoadBattery = Math.max(0, pv - toGrid);
  const baseLoad = analyticsFloat(states, "load_energy_today");
  const batteryDischarge = analyticsFloat(states, "battery_discharge_today");
  const batteryCharge = analyticsFloat(states, "battery_charge_today");
  const fromGrid = analyticsFloat(states, "grid_consumption_energy_today");
  const loadConsumption = baseLoad - batteryDischarge + batteryCharge + fromGrid;
  const fromPvBattery = Math.max(0, loadConsumption - fromGrid);
  const selfConsumption = pv > 0 ? Math.min(100, Math.max(0, (toLoadBattery / pv) * 100)) : 0;
  const selfSufficiency =
    loadConsumption > 0 ? Math.min(100, Math.max(0, (fromPvBattery / loadConsumption) * 100)) : 0;
  return {
    pv_production_kwh_today: Math.round(pv * 100) / 100,
    pv_to_load_battery_kwh_today: Math.round(toLoadBattery * 100) / 100,
    pv_to_grid_kwh_today: Math.round(toGrid * 100) / 100,
    load_consumption_kwh_today: Math.round(loadConsumption * 100) / 100,
    load_from_pv_battery_kwh_today: Math.round(fromPvBattery * 100) / 100,
    load_from_grid_kwh_today: Math.round(fromGrid * 100) / 100,
    self_consumption_percent_today: Math.round(selfConsumption * 10) / 10,
    self_sufficiency_percent_today: Math.round(selfSufficiency * 10) / 10,
    battery_charge_kwh_today: Math.round(batteryCharge * 100) / 100,
    battery_discharge_kwh_today: Math.round(batteryDischarge * 100) / 100,
  };
}

/** Prefer live hass.states (with suffix scan) — coordinator analytics can lag or miss mapped entities. */
function resolveAnalyticsEntityStates(hass, map) {
  const states = {};
  if (!hass?.states) return states;
  for (const key of ANALYTICS_STATE_KEYS) {
    const picked = pickAnalyticsState(hass, map, key);
    if (picked != null) states[key] = picked;
  }
  return states;
}

function readLiveAnalytics(hass, plant, plantState, overviewDaily) {
  const map = resolveEntityMap(hass, plant, plantState);
  let states = resolveAnalyticsEntityStates(hass, map);
  states = applyPvTodayFallback(states, overviewDaily);
  let analytics = computeAnalyticsFromStates(states);
  const cached = plantState?.analytics ?? {};

  const loadFromHistory = overviewDaily?.consumption?.at(-1);
  if (loadFromHistory > 0 && analytics.load_consumption_kwh_today < loadFromHistory) {
    const patched = { ...states, load_energy_today: String(loadFromHistory) };
    if (analyticsFloat(states, "grid_consumption_energy_today") === 0) {
      patched.grid_consumption_energy_today = "0";
    }
    analytics = computeAnalyticsFromStates(patched);
  }

  if (!Object.keys(states).length && cached.pv_production_kwh_today != null) {
    return cached;
  }
  return { ...cached, ...analytics };
}

function entityIdMatchesSuffix(entityId, suffix) {
  if (!entityId || !suffix) return false;
  const id = String(entityId);
  if (id.endsWith(`_${suffix}`)) return true;
  const dot = id.lastIndexOf(".");
  const local = dot >= 0 ? id.slice(dot + 1) : id;
  return local === suffix;
}

function resolveEntityMap(hass, plant, plantState) {
  const map = { ...(plant?.entity_map || {}), ...(plantState?.entity_map || {}) };
  if (!hass?.states) return map;
  const ids = Object.keys(hass.states);
  const allFallbacks = { ...CHART_ENTITY_FALLBACKS, ...DEVICE_ENTITY_FALLBACKS };
  for (const [key, suffixes] of Object.entries(allFallbacks)) {
    for (const suffix of suffixes) {
      const hit = ids.find((id) => entityIdMatchesSuffix(id, suffix));
      if (hit) {
        map[key] = hit;
        break;
      }
    }
  }
  return map;
}

function entityDisplayValue(hass, entityId) {
  if (!entityId || !hass?.states?.[entityId]) return "—";
  const st = stateString(hass, entityId);
  if (st === "—") return "—";
  return `${st}${entityUnit(hass, entityId)}`;
}

function entityMapRows(hass, plant, plantState, pairs) {
  const map = resolveEntityMap(hass, plant, plantState);
  return pairs
    .map(([key, name]) => (map[key] ? { entity_id: map[key], name, key } : null))
    .filter(Boolean);
}

function deviceParamEntityIds(map, sections) {
  const ids = new Set();
  for (const section of sections) {
    if (section.kind === "pv-table") {
      for (const n of DEVICE_PV_STRINGS) {
        for (const suffix of ["voltage", "current", "power"]) {
          const id = map[`pv${n}_${suffix}`];
          if (id) ids.add(id);
        }
      }
      if (map.pv_power) ids.add(map.pv_power);
    } else if (section.kind === "metric-table") {
      for (const key of section.keys) {
        if (map[key]) ids.add(map[key]);
      }
    } else if (section.kind === "rows") {
      for (const [key] of section.rows) {
        if (map[key]) ids.add(map[key]);
      }
    } else if (section.kind === "datalogger") {
      for (const key of ["bms_online", "manager_version", "master_version", "modbus_protocol_version"]) {
        if (map[key]) ids.add(map[key]);
      }
    }
  }
  return ids;
}

function deviceParamLastUpdated(hass, entityIds) {
  let latest = 0;
  for (const entityId of entityIds) {
    const ts = hass?.states?.[entityId]?.last_updated;
    if (!ts) continue;
    const ms = Date.parse(ts);
    if (Number.isFinite(ms) && ms > latest) latest = ms;
  }
  if (!latest) return "";
  try {
    return new Date(latest).toLocaleString(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return new Date(latest).toISOString();
  }
}

async function hassMessageWithTimeout(hass, message, timeoutMs = HA_WS_TIMEOUT_MS) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`Home Assistant request timed out after ${Math.round(timeoutMs / 1000)}s`)),
      timeoutMs
    );
  });
  try {
    return await Promise.race([hass.connection.sendMessagePromise(message), timeout]);
  } finally {
    clearTimeout(timer);
  }
}

function recorderEntityRows(map, entityId) {
  const raw = map?.[entityId];
  if (Array.isArray(raw)) return raw;
  if (raw && typeof raw === "object" && Array.isArray(raw.mean)) return raw.mean;
  return [];
}

/** Prefer native recorder statistics (same API as plotly-graph), fall back to plant websocket. */
function mergeRecorderEntityMaps(plantMap, nativeMap, entityIds) {
  const out = {};
  for (const id of entityIds) {
    const plantRows = recorderEntityRows(plantMap, id);
    const nativeRows = recorderEntityRows(nativeMap, id);
    out[id] = nativeRows.length ? nativeRows : plantRows;
  }
  return out;
}

async function fetchStatisticsDuring(hass, entityIds, start, end) {
  const statistic_ids = entityIds.filter(Boolean);
  if (!statistic_ids.length) return null;
  let plantMap = null;
  try {
    const viaPlant = await hassMessageWithTimeout(hass, {
      type: "foxess_plant/fetch_statistics",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      entity_ids: statistic_ids,
      period: "5minute",
      statistic: "mean",
    });
    if (viaPlant && typeof viaPlant === "object" && !Array.isArray(viaPlant)) {
      plantMap = viaPlant;
    }
  } catch {
    /* older integration without fetch_statistics, or timeout */
  }
  let nativeMap = null;
  try {
    const res = await hassMessageWithTimeout(hass, {
      type: "recorder/statistics_during_period",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      statistic_ids,
      period: "5minute",
      types: ["mean"],
    });
    if (res && typeof res === "object" && !Array.isArray(res)) {
      nativeMap = res;
    }
  } catch {
    /* recorder unavailable or timeout */
  }
  if (!plantMap && !nativeMap) return null;
  return mergeRecorderEntityMaps(plantMap, nativeMap, statistic_ids);
}

function recorderStatsToPoints(rows, range) {
  return (rows || [])
    .map((row) => {
      const rawStart = row.start ?? row.start_time;
      let t;
      if (typeof rawStart === "number") {
        t = rawStart > 1e12 ? rawStart : rawStart * 1000;
      } else {
        t = new Date(rawStart).getTime();
      }
      if (!Number.isFinite(t) || t < range.tMin || t > range.nowMs) return null;
      const v = row.mean;
      if (v == null || !Number.isFinite(Number(v))) return null;
      return { t, v: Number(v) };
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t);
}

function normalizeHistoryDuringResponse(raw, ids) {
  if (!raw || typeof raw !== "object") return {};
  if (Array.isArray(raw)) {
    const map = {};
    ids.forEach((id, i) => {
      map[id] = raw[i] || [];
    });
    return map;
  }
  return raw;
}

async function fetchHistoryDuring(hass, entityIds, start, end, { significantChangesOnly = false } = {}) {
  const ids = entityIds.filter(Boolean);
  if (!ids.length) return {};
  let plantMap = null;
  try {
    const viaPlant = await hassMessageWithTimeout(hass, {
      type: "foxess_plant/fetch_history",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      entity_ids: ids,
      significant_changes_only: significantChangesOnly,
    });
    if (viaPlant && typeof viaPlant === "object" && !Array.isArray(viaPlant)) {
      plantMap = viaPlant;
    }
  } catch {
    /* older integration without fetch_history, or timeout */
  }
  let nativeMap = null;
  try {
    const raw = await hassMessageWithTimeout(hass, {
      type: "history/history_during_period",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      entity_ids: ids,
      minimal_response: true,
      significant_changes_only: significantChangesOnly,
      no_attributes: true,
      include_start_time_state: true,
    });
    nativeMap = normalizeHistoryDuringResponse(raw, ids);
  } catch {
    /* history unavailable or timeout */
  }
  if (!plantMap && !nativeMap) return {};
  return mergeRecorderEntityMaps(plantMap, nativeMap, ids);
}

function historyRowsForEntity(histMap, entityId) {
  if (!histMap || !entityId) return [];
  return histMap[entityId] || [];
}

function historyRowTimeMs(row) {
  const raw = row.lu ?? row.last_updated ?? row.last_changed ?? row.lc;
  if (typeof raw === "number") {
    return raw > 1e12 ? raw : raw * 1000;
  }
  const ms = new Date(raw).getTime();
  return Number.isFinite(ms) ? ms : NaN;
}

function historyToPoints(rows) {
  if (!rows?.length) return [];
  const sorted = rows
    .map((row) => {
      if (typeof row.t === "number" && typeof row.v === "number") {
        const t = row.t > 1e12 ? row.t : row.t * 1000;
        return Number.isFinite(t) ? { t, v: row.v } : null;
      }
      const t = historyRowTimeMs(row);
      const v = parseFloat(row.s ?? row.state);
      if (!Number.isFinite(t) || !Number.isFinite(v)) return null;
      return { t, v };
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t);
  const out = [];
  for (const p of sorted) {
    const last = out[out.length - 1];
    if (last && last.t === p.t) out[out.length - 1] = p;
    else out.push(p);
  }
  return out;
}

const FOX_ALARM_HISTORY_DAYS = 30;

const FOX_ALARM_META = {
  "PV Over-voltage": { category: "PV", severity: "warning" },
  "DC arc fault": { category: "PV", severity: "critical" },
  "String reverse connection": { category: "PV", severity: "warning" },
  "Grid power outage": { category: "Grid", severity: "critical" },
  "Abnormal grid voltage": { category: "Grid", severity: "warning" },
  "Abnormal grid frequency": { category: "Grid", severity: "warning" },
  "Output overcurrent": { category: "Output", severity: "warning" },
  "Output DC component too large": { category: "Output", severity: "warning" },
  "Residual current": { category: "Safety", severity: "critical" },
  "Grounding fault": { category: "Safety", severity: "critical" },
  "Low insulation resistance": { category: "Safety", severity: "critical" },
  "Inverter overtemperature": { category: "Thermal", severity: "warning" },
  "Energy storage equipment abnormal": { category: "Storage", severity: "warning" },
  "Islanding": { category: "Safety", severity: "critical" },
  "Off-grid output overload": { category: "Output", severity: "warning" },
  "External fan fault": { category: "Other", severity: "warning" },
  "Energy storage reverse connection": { category: "Storage", severity: "critical" },
  "Meter lost": { category: "Communication", severity: "warning" },
  "BMS lost": { category: "Communication", severity: "warning" },
  // Legacy fault-code names (inverter_fault_code fallback)
  "Grid Lost Fault": { category: "Grid", severity: "critical" },
  "Grid Voltage Fault": { category: "Grid", severity: "warning" },
  "Grid Frequency Fault": { category: "Grid", severity: "warning" },
  "Output Over-current Fault": { category: "Output", severity: "warning" },
  "Output DC Over-current Fault": { category: "Output", severity: "warning" },
  "Residual Current Consistency Fault": { category: "Safety", severity: "critical" },
  "Ground Connection Fault": { category: "Safety", severity: "critical" },
  "Low Insulation Resistante Fault": { category: "Safety", severity: "critical" },
  "Inverter Over-temperature Fault": { category: "Thermal", severity: "warning" },
  "Energy Storage Equipment Abnormal Fault": { category: "Storage", severity: "warning" },
  "Isolated Island Fault": { category: "Safety", severity: "critical" },
  "Off-grid Output Overload Fault": { category: "Output", severity: "warning" },
  "External Fan Fault": { category: "Other", severity: "warning" },
  "Energy Storage Reverse Connection Fault": { category: "Storage", severity: "critical" },
  "Meter Lost Fault": { category: "Communication", severity: "warning" },
  "BMS Lost Fault": { category: "Communication", severity: "warning" },
};

const FOX_ALARM_CATEGORY_COLORS = {
  PV: "#19D4DE",
  Grid: "#7F3DFF",
  Output: "#08979C",
  Safety: "#EB6D48",
  Thermal: "#FAAD14",
  Storage: "#52C41A",
  Communication: "#699BFF",
  Other: "#8c8c8c",
};

const FOX_ALARM_SEVERITY_COLORS = {
  critical: "#ff4d4f",
  warning: "#faad14",
  info: "#1890ff",
};

function foxAlarmMeta(name) {
  return FOX_ALARM_META[name] || { category: "Other", severity: "warning" };
}

/** Modbus alarm bit index → Fox-style code (register word + bit). */
const FOX_ALARM_CODE_MAP = (() => {
  const words = [
    [
      "PV Over-voltage",
      "DC arc fault",
      "String reverse connection",
      null,
      null,
      null,
      null,
      "Grid power outage",
      "Abnormal grid voltage",
      null,
      null,
      "Abnormal grid frequency",
      null,
      null,
      "Output overcurrent",
      "Output DC component too large",
    ],
    [
      "Residual current",
      "Grounding fault",
      "Low insulation resistance",
      "Inverter overtemperature",
      null,
      null,
      null,
      null,
      null,
      "Energy storage equipment abnormal",
      "Islanding",
      null,
      null,
      null,
      "Off-grid output overload",
      null,
    ],
    [
      null,
      null,
      null,
      "External fan fault",
      "Energy storage reverse connection",
      null,
      null,
      null,
      null,
      "Meter lost",
      "BMS lost",
      null,
      null,
      null,
      null,
      null,
    ],
  ];
  const map = {};
  words.forEach((word, wi) => {
    word.forEach((name, bi) => {
      if (name) map[name] = `${39067 + wi}-${bi}`;
    });
  });
  return map;
})();

function foxAlarmCode(name) {
  return FOX_ALARM_CODE_MAP[name] || "—";
}

function toDateInputValue(ms) {
  if (!Number.isFinite(ms)) return "";
  const d = new Date(ms);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function parseDateInputStartMs(s) {
  if (!s) return NaN;
  const parts = String(s).split("-").map((x) => parseInt(x, 10));
  if (parts.length !== 3 || parts.some((n) => !Number.isFinite(n))) return NaN;
  return new Date(parts[0], parts[1] - 1, parts[2], 0, 0, 0, 0).getTime();
}

function parseDateInputEndMs(s) {
  if (!s) return NaN;
  const parts = String(s).split("-").map((x) => parseInt(x, 10));
  if (parts.length !== 3 || parts.some((n) => !Number.isFinite(n))) return NaN;
  return new Date(parts[0], parts[1] - 1, parts[2], 23, 59, 59, 999).getTime();
}

function defaultAlarmCustomRangeValues() {
  const end = Date.now();
  const start = end - 7 * 86400000;
  return { start: toDateInputValue(start), end: toDateInputValue(end) };
}

function makeHistoricalAlarmRecord(name, occurrenceMs, recoveryMs, deviceName) {
  const meta = foxAlarmMeta(name);
  return {
    name,
    message: name,
    device: deviceName,
    category: meta.category,
    severity: meta.severity,
    code: foxAlarmCode(name),
    occurrenceMs,
    recoveryMs,
  };
}

/** Pair raised/cleared recorder events into Fox historical rows. */
function pairAlarmHistoryRecords(events, activeNames, deviceName) {
  const open = new Map();
  const records = [];
  const sorted = [...events].sort((a, b) => a.t - b.t);
  for (const ev of sorted) {
    if (ev.action === "raised") {
      if (!open.has(ev.name)) open.set(ev.name, ev.t);
    } else if (ev.action === "cleared") {
      const occ = open.get(ev.name);
      if (occ != null) {
        records.push(makeHistoricalAlarmRecord(ev.name, occ, ev.t, deviceName));
        open.delete(ev.name);
      } else {
        records.push(makeHistoricalAlarmRecord(ev.name, ev.t, ev.t, deviceName));
      }
    }
  }
  for (const [name, occ] of open) {
    records.push(makeHistoricalAlarmRecord(name, occ, null, deviceName));
  }
  const activeSet = new Set(activeNames || []);
  for (const name of activeSet) {
    if (records.some((r) => r.name === name && r.recoveryMs == null)) continue;
    let since = null;
    for (let i = events.length - 1; i >= 0; i -= 1) {
      if (events[i].name === name && events[i].action === "raised") {
        since = events[i].t;
        break;
      }
    }
    records.push(makeHistoricalAlarmRecord(name, since || Date.now(), null, deviceName));
  }
  return records.sort((a, b) => (b.occurrenceMs || 0) - (a.occurrenceMs || 0));
}

function filterHistoricalAlarmRecords(records, { category, severity, device }, timeRange) {
  let startMs;
  let endMs;
  if (timeRange?.mode === "custom") {
    startMs = parseDateInputStartMs(timeRange.start);
    endMs = parseDateInputEndMs(timeRange.end);
    if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) {
      const def = defaultAlarmCustomRangeValues();
      startMs = parseDateInputStartMs(def.start);
      endMs = parseDateInputEndMs(def.end);
    }
  } else {
    endMs = Date.now();
    startMs = endMs - 86400000;
  }
  return records.filter((row) => {
    if (!Number.isFinite(row.occurrenceMs)) return false;
    if (row.occurrenceMs < startMs || row.occurrenceMs > endMs) return false;
    if (category && row.category !== category) return false;
    if (severity && row.severity !== severity) return false;
    if (device && row.device !== device) return false;
    return true;
  });
}

function countOverviewFaultsLast24h(alarmData) {
  if (!alarmData || alarmData.error) return null;
  const rows = filterHistoricalAlarmRecords(alarmData.historicalRecords || [], {}, { mode: "24h" });
  const seen = new Set(rows.map((r) => r.name));
  let extra = 0;
  for (const a of alarmData.active || []) {
    if (!seen.has(a.name)) {
      extra += 1;
      seen.add(a.name);
    }
  }
  return rows.length + extra;
}

function formatOverviewFaultDetectedText(count) {
  const n = Math.max(0, Number(count) || 0);
  return n === 1 ? "1 fault detected" : `${n} faults detected`;
}

function overviewSystemStatusOkIcon() {
  return `<svg class="overview-system-status-glyph overview-system-status-glyph--ok" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="8" fill="#52c41a"/><path d="M4.5 8.2l2.1 2.1 5-5.2" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

function overviewSystemStatusFaultIcon() {
  return `<svg class="overview-system-status-glyph overview-system-status-glyph--fault" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="8" fill="#ff4d4f"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>`;
}

function renderOverviewSystemStatusCard({ loading = false, faultCount = null, error = null } = {}) {
  const detailsBtn = `<button type="button" class="overview-system-status-details" data-action="nav" data-view="device_new" data-device-sub="alarms">Details <span aria-hidden="true">›</span></button>`;
  let body;
  if (loading) {
    body = `<div class="overview-system-status-body overview-system-status-body--loading"><span>Checking system status…</span></div>`;
  } else if (faultCount == null && error) {
    body = `<div class="overview-system-status-body"><span class="overview-system-status-text">${esc(error)}</span></div>`;
  } else if ((faultCount ?? 0) > 0) {
    body = `<div class="overview-system-status-body">${overviewSystemStatusFaultIcon()}<span class="overview-system-status-text overview-system-status-text--fault">${esc(formatOverviewFaultDetectedText(faultCount))}</span></div>`;
  } else {
    body = `<div class="overview-system-status-body">${overviewSystemStatusOkIcon()}<span class="overview-system-status-text">System working normally.</span></div>`;
  }
  return `<div class="overview-system-status-card">
<div class="overview-system-status-head"><span class="overview-system-status-title">System Status</span>${detailsBtn}</div>
${body}
</div>`;
}

function overviewAutomationStatusPillClass(tone) {
  if (tone === "armed") return "overview-automation-status-pill overview-automation-status-pill--armed";
  if (tone === "watch") return "overview-automation-status-pill overview-automation-status-pill--watch";
  if (tone === "idle") return "overview-automation-status-pill overview-automation-status-pill--idle";
  return "overview-automation-status-pill overview-automation-status-pill--off";
}

function overviewStormStatusSummary(plantState) {
  const storm = plantState?.storm_prep ?? {};
  if (!storm.enabled) return { label: "Off", tone: "off", detail: "Disabled in settings" };
  const triggersArmed = Boolean(plantState?.active_storm_triggers?.length);
  const overrideArmed =
    Boolean(plantState?.override_active) && String(plantState?.mode ?? "") === "storm";
  const forecastArmed = Boolean(plantState?.forecast_armed);
  const armed = triggersArmed || overrideArmed || forecastArmed;
  if (armed) {
    const precheck = storm.solcast_precheck ?? {};
    let detail = "Storm charge schedule applied";
    if (precheck.action === "pv_only") detail = "PV top-up only — no grid import";
    else if (forecastArmed && !triggersArmed && !overrideArmed) detail = "Forecast pre-charge armed";
    return { label: "Active", tone: "armed", detail };
  }
  if (storm.condition_active) {
    const label = storm.current_condition?.label;
    return { label: "Monitoring", tone: "watch", detail: label || "Storm conditions detected" };
  }
  if (storm.forecast_active) {
    return { label: "Monitoring", tone: "watch", detail: "Severe weather in forecast" };
  }
  return { label: "Ready", tone: "idle", detail: "Watching Google Weather" };
}

function overviewSmartChargeStatusSummary(plantState) {
  const sc = plantState?.smart_charge ?? {};
  if (!sc.enabled) return { label: "Off", tone: "off", detail: "Disabled in settings" };
  if (sc.discharge_armed) {
    const reason = sc.decision?.reason;
    return { label: "Exporting", tone: "armed", detail: reason || "Force Discharge active" };
  }
  if (sc.armed) {
    const reason = sc.decision?.reason;
    return { label: "Armed", tone: "armed", detail: reason || "Grid charge in progress" };
  }
  const reason = sc.decision?.reason;
  return { label: "Ready", tone: "idle", detail: reason || "Watching tariffs and solar" };
}

const SMART_CHARGE_MODE_META = {
  max_safety: {
    title: "Max safety",
    hint: "Higher reserve, minimal export — backup first",
    accent: "var(--fp-accent)",
  },
  max_profit: {
    title: "Max profit",
    hint: "Aggressive Agile arbitrage — charge low, export high",
    accent: "var(--fp-amber, #f9a825)",
  },
  max_green: {
    title: "Max green",
    hint: "Renewable-first — greener nights and low carbon",
    accent: "var(--fp-green, #4caf50)",
  },
};

function smartChargeModeIconHtml(mode) {
  const src = SMART_CHARGE_MODE_ICONS[mode] || SMART_CHARGE_MODE_ICONS.max_safety;
  return `<img src="${esc(src)}" width="40" height="40" alt="" decoding="async" />`;
}

function smartChargePlanActionTone(action) {
  if (action === "export" || action === "spread_export") return "export";
  if (action === "charge" || action === "spread_charge" || action === "winter_fill") return "charge";
  if (action === "charge_candidate" || action === "arbitrage") return "candidate";
  return "idle";
}

function renderSmartChargePlanTimeline(dailyPlan, currentSlot) {
  const slots = (dailyPlan || []).filter((s) => s.start && s.end && s.reason !== "no_slots").slice(0, 24);
  if (!slots.length) {
    return `<p class="sc-empty-hint">Plan appears after the daily Octopus refresh (default 16:00 UK).</p>`;
  }
  const nowKey =
    currentSlot?.start && currentSlot?.end ? `${currentSlot.start}-${currentSlot.end}` : null;
  const segments = slots
    .map((s) => {
      const tone = smartChargePlanActionTone(s.action);
      const isNow = nowKey === `${s.start}-${s.end}`;
      const imp = Number(s.import_p_per_kwh ?? 0).toFixed(1);
      const exp = s.export_p_per_kwh != null ? Number(s.export_p_per_kwh).toFixed(1) : null;
      const title = `${s.start}–${s.end} ${s.action}${exp != null ? ` · ${exp}p exp` : ` · ${imp}p imp`}`;
      return `<div class="sc-timeline-seg sc-timeline-seg--${tone}${isNow ? " sc-timeline-seg--now" : ""}" title="${esc(title)}" aria-label="${esc(title)}"></div>`;
    })
    .join("");
  return `<div class="sc-timeline-wrap">
<div class="sc-timeline" role="img" aria-label="Daily charge and export plan">${segments}</div>
<div class="sc-timeline-legend">
<span><i class="sc-legend-dot sc-legend-dot--charge"></i>Charge</span>
<span><i class="sc-legend-dot sc-legend-dot--export"></i>Export</span>
<span><i class="sc-legend-dot sc-legend-dot--candidate"></i>Candidate</span>
<span><i class="sc-legend-dot sc-legend-dot--idle"></i>Hold</span>
</div>
</div>`;
}

function renderSmartChargeStatTiles(decision) {
  const tiles = [];
  if (decision.target_soc_effective != null) {
    const pct = Math.max(0, Math.min(100, Number(decision.target_soc_effective)));
    tiles.push({
      label: "Target SOC",
      value: `${pct.toFixed(0)}%`,
      gauge: pct,
    });
  }
  if (decision.reserve_kwh != null) {
    tiles.push({ label: "Reserve floor", value: `${Number(decision.reserve_kwh).toFixed(1)} kWh` });
  }
  if (decision.grid_gap_kwh != null) {
    tiles.push({ label: "Grid gap", value: `${Number(decision.grid_gap_kwh).toFixed(1)} kWh` });
  }
  if (decision.forecast_kwh != null) {
    tiles.push({ label: "Solar forecast", value: `${Number(decision.forecast_kwh).toFixed(1)} kWh` });
  }
  if (!tiles.length) return "";
  return `<div class="sc-stat-grid">${tiles
    .map((t) => {
      const gauge =
        t.gauge != null
          ? `<div class="sc-gauge-track" aria-hidden="true"><div class="sc-gauge-fill" style="width:${t.gauge}%"></div></div>`
          : "";
      return `<div class="sc-stat-tile"><span class="sc-stat-label">${esc(t.label)}</span><strong class="sc-stat-value">${esc(t.value)}</strong>${gauge}</div>`;
    })
    .join("")}</div>`;
}

function renderOverviewAutomationHalf({ sub, title, summary }) {
  const pillClass = overviewAutomationStatusPillClass(summary.tone);
  return `<button type="button" class="overview-automation-half" data-action="settings-sub" data-sub="${esc(sub)}" aria-label="${esc(title)}: ${esc(summary.label)}">
<div class="overview-automation-half-head">
<span class="overview-automation-half-title">${esc(title)}</span>
<span class="${pillClass}">${esc(summary.label)}</span>
</div>
<span class="overview-automation-half-detail">${esc(summary.detail)}</span>
</button>`;
}

function renderOverviewAutomationStatusCard(plantState) {
  const storm = overviewStormStatusSummary(plantState);
  const smart = overviewSmartChargeStatusSummary(plantState);
  return `<div class="overview-automation-status-card">
${renderOverviewAutomationHalf({ sub: "storm", title: "StormSafe", summary: storm })}
${renderOverviewAutomationHalf({ sub: "smart", title: "SmartCharge", summary: smart })}
</div>`;
}

function parseAlarmStateList(state) {
  if (!state || state === "unknown" || state === "unavailable" || state === "None") return [];
  return String(state)
    .split(";")
    .map((s) => s.trim())
    .filter(Boolean);
}

function historyToStateRows(rows) {
  if (!rows?.length) return [];
  const sorted = rows
    .map((row) => {
      const t = historyRowTimeMs(row);
      const s = row.s ?? row.state;
      if (!Number.isFinite(t) || s == null) return null;
      return { t, s: String(s) };
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t);
  const out = [];
  for (const p of sorted) {
    const last = out[out.length - 1];
    if (last && last.t === p.t && last.s === p.s) continue;
    if (last && last.t === p.t) out[out.length - 1] = p;
    else out.push(p);
  }
  return out;
}

function parseAlarmLastStateEvents(state) {
  if (!state || state === "unknown" || state === "unavailable" || state === "None") return [];
  const events = [];
  for (const part of String(state)
    .split(";")
    .map((s) => s.trim())
    .filter(Boolean)) {
    const m = part.match(/^(Raised|Cleared):\s*(.+)$/i);
    if (!m) continue;
    const action = m[1].toLowerCase();
    for (const name of m[2]
      .split(";")
      .map((s) => s.trim())
      .filter(Boolean)) {
      events.push({ action, name });
    }
  }
  return events;
}

function eventsFromAlarmsHistory(rows) {
  const events = [];
  let prev = new Set();
  for (const row of historyToStateRows(rows)) {
    const active = new Set(parseAlarmStateList(row.s));
    for (const name of active) {
      if (!prev.has(name)) events.push({ action: "raised", name, t: row.t });
    }
    for (const name of prev) {
      if (!active.has(name)) events.push({ action: "cleared", name, t: row.t });
    }
    prev = active;
  }
  return events;
}

const FOX_ALARM_ICONS = {"alarm":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 14 14\" id=\"icon-alarm\">\n  <path d=\"M3.0625 7C3.0625 4.82538 4.82538 3.0625 7 3.0625C9.17462 3.0625 10.9375 4.82538 10.9375 7V12.8516H3.0625V7Z\" fill-opacity=\"0.06\" />\n  <path d=\"M6.99993 5.08594C8.07969 5.08594 8.95501 5.96126 8.95501 7.04102V8.29199H7.75189V7.04102C7.75189 6.62572 7.41523 6.28906 6.99993 6.28906V5.08594Z\" fill-opacity=\"0.88\" />\n  <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M6.99993 3.0625C9.17455 3.0625 10.9374 4.82538 10.9374 7V11.6484H12.0312C12.152 11.6484 12.2499 11.7464 12.2499 11.8672V12.6328C12.2499 12.7536 12.152 12.8516 12.0312 12.8516H1.96868C1.84787 12.8516 1.74993 12.7536 1.74993 12.6328V11.8672C1.74993 11.7464 1.84787 11.6484 1.96868 11.6484H3.06243V7C3.06243 4.82538 4.82531 3.0625 6.99993 3.0625ZM6.99993 4.26562C5.48978 4.26562 4.26556 5.48985 4.26556 7V11.6484H9.73431V7C9.73431 5.48985 8.51009 4.26562 6.99993 4.26562Z\" fill-opacity=\"0.88\" />\n  <path d=\"M2.45018 6.39837C2.57099 6.39837 2.66893 6.49631 2.66893 6.61712V7.38275C2.66893 7.50356 2.57099 7.6015 2.45018 7.6015H1.09375C0.972938 7.6015 0.875 7.50356 0.875 7.38275V6.61712C0.875 6.49631 0.972938 6.39837 1.09375 6.39837H2.45018Z\" fill-opacity=\"0.88\" />\n  <path d=\"M12.9062 6.39837C13.0271 6.39837 13.125 6.49631 13.125 6.61712V7.38275C13.125 7.50356 13.0271 7.6015 12.9062 7.6015H11.5801C11.4593 7.6015 11.3613 7.50356 11.3613 7.38275V6.61712C11.3613 6.49631 11.4593 6.39837 11.5801 6.39837H12.9062Z\" fill-opacity=\"0.88\" />\n  <path d=\"M2.93961 2.39833C3.02504 2.31291 3.16354 2.31291 3.24897 2.39833L4.18672 3.33608C4.27214 3.42151 4.27214 3.56001 4.18672 3.64544L3.64533 4.18681C3.5599 4.27223 3.4214 4.27224 3.33598 4.18681L2.39824 3.24906C2.31282 3.16363 2.31282 3.02513 2.39824 2.93971L2.93961 2.39833Z\" fill-opacity=\"0.88\" />\n  <path d=\"M10.7509 2.39823C10.8364 2.3128 10.9749 2.3128 11.0603 2.39823L11.6017 2.93961C11.6871 3.02504 11.6871 3.16354 11.6017 3.24897L10.6639 4.18672C10.5785 4.27214 10.44 4.27214 10.3546 4.18672L9.81319 3.64533C9.72777 3.5599 9.72777 3.4214 9.81319 3.33598L10.7509 2.39823Z\" fill-opacity=\"0.88\" />\n  <path d=\"M7.38275 0.875C7.50356 0.875 7.6015 0.972938 7.6015 1.09375V2.41992C7.6015 2.54073 7.50356 2.63867 7.38275 2.63867H6.61712C6.49631 2.63867 6.39837 2.54073 6.39837 2.41992V1.09375C6.39837 0.972938 6.49631 0.875 6.61712 0.875H7.38275Z\" fill-opacity=\"0.88\" />\n</svg>","alert":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 13 13\" fill=\"none\" id=\"icon-alert\">\n<path d=\"M12 0C11.9406 0 11.8797 0.0109375 11.8187 0.0359375L2.8125 3.65469H0.25C0.1125 3.65469 0 3.77031 0 3.91406V8.58594C0 8.72969 0.1125 8.84531 0.25 8.84531H1.8375C1.77969 9.02656 1.75 9.21875 1.75 9.41406C1.75 10.4437 2.59062 11.2812 3.625 11.2812C4.49062 11.2812 5.22031 10.6937 5.43594 9.9L11.8203 12.4656C11.8812 12.4891 11.9422 12.5016 12.0016 12.5016C12.2656 12.5016 12.5016 12.2797 12.5016 11.9828V0.51875C12.5 0.221875 12.2656 0 12 0ZM3.625 10.1609C3.21094 10.1609 2.875 9.82656 2.875 9.41406C2.875 9.23906 2.93594 9.07187 3.04687 8.93906L4.37344 9.47187C4.34219 9.85625 4.01875 10.1609 3.625 10.1609Z\" fill=\"#FAAD14\" />\n</svg>","warning":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 15 14\" fill=\"none\" id=\"icon-warning\">\n<g id=\"icon-warning_alert-line\">\n<path id=\"icon-warning_Vector\" d=\"M7.83885 1.75008L13.3959 11.3751C13.557 11.6541 13.4614 12.0109 13.1824 12.1719C13.0937 12.2231 12.9931 12.2501 12.8907 12.2501H1.77669C1.45453 12.2501 1.19336 11.9889 1.19336 11.6668C1.19336 11.5643 1.22032 11.4638 1.27151 11.3751L6.82852 1.75008C6.98957 1.47107 7.34634 1.37548 7.62535 1.53656C7.71402 1.58776 7.78769 1.6614 7.83885 1.75008ZM2.78706 11.0834H11.8803L7.33368 3.20841L2.78706 11.0834ZM6.75035 9.33343H7.91702V10.5001H6.75035V9.33343ZM6.75035 5.25008H7.91702V8.16676H6.75035V5.25008Z\" fill=\"white\" />\n</g>\n</svg>","no_alarm":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 41 41\" fill=\"none\" id=\"icon-noAlarm\">\n<g id=\"icon-noAlarm_Icon / CheckCircleFilled\">\n<path id=\"icon-noAlarm_Vector\" d=\"M20.5 3C10.8359 3 3 10.8359 3 20.5C3 30.1641 10.8359 38 20.5 38C30.1641 38 38 30.1641 38 20.5C38 10.8359 30.1641 3 20.5 3ZM28.0586 14.7852L19.832 26.1914C19.7171 26.3519 19.5655 26.4827 19.3899 26.5729C19.2143 26.6631 19.0197 26.7101 18.8223 26.7101C18.6248 26.7101 18.4303 26.6631 18.2547 26.5729C18.0791 26.4827 17.9275 26.3519 17.8125 26.1914L12.9414 19.4414C12.793 19.2344 12.9414 18.9453 13.1953 18.9453H15.0273C15.4258 18.9453 15.8047 19.1367 16.0391 19.4648L18.8203 23.3242L24.9609 14.8086C25.1953 14.4844 25.5703 14.2891 25.9727 14.2891H27.8047C28.0586 14.2891 28.207 14.5781 28.0586 14.7852Z\" fill=\"#49AA19\" />\n</g>\n</svg>","big_empty":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 65 41\" fill=\"none\" id=\"icon-bigEmpty\">\n<g id=\"icon-bigEmpty_Group\">\n<path id=\"icon-bigEmpty_Subtract\" d=\"M9.5 28.5215C3.92848 29.7718 0.5 31.4751 0.5 33.3522C0.5 37.1895 14.8269 40.3003 32.5 40.3003C50.1731 40.3003 64.5 37.1895 64.5 33.3522C64.5 31.4751 61.0715 29.7718 55.5 28.5215V31.5504C55.5 33.6576 54.18 35.3847 52.55 35.3847H12.45C10.82 35.3847 9.5 33.6566 9.5 31.5504V28.5215Z\" fill=\"white\" fill-opacity=\"0.12\" />\n<g id=\"icon-bigEmpty_Group_2\">\n<path id=\"icon-bigEmpty_Vector\" d=\"M42.113 16.4581C42.113 14.865 43.107 13.5498 44.34 13.5488H55.5V31.5512C55.5 33.6584 54.18 35.3855 52.55 35.3855H12.45C10.82 35.3855 9.5 33.6574 9.5 31.5512V13.5488H20.66C21.893 13.5488 22.887 14.862 22.887 16.4551V16.4769C22.887 18.07 23.892 19.3564 25.124 19.3564H39.876C41.108 19.3564 42.113 18.0581 42.113 16.465V16.4581Z\" fill=\"white\" fill-opacity=\"0.08\" stroke=\"#424242\" />\n<path id=\"icon-bigEmpty_Vector_2\" d=\"M55.5 13.6575L45.354 2.24085C44.867 1.46267 44.156 0.992188 43.407 0.992188H21.593C20.844 0.992188 20.133 1.46267 19.646 2.23986L9.5 13.6585\" stroke=\"#424242\" />\n</g>\n</g>\n</svg>","empty":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 64 41\" id=\"icon-empty\"><g transform=\"translate(0 1)\" fill=\"none\" fill-rule=\"evenodd\"><ellipse fill=\"#f5f5f5\" cx=\"32\" cy=\"33\" rx=\"32\" ry=\"7\" /><g fill-rule=\"nonzero\" stroke=\"#d9d9d9\"><path d=\"M55 12.76L44.854 1.258C44.367.474 43.656 0 42.907 0H21.093c-.749 0-1.46.474-1.947 1.257L9 12.761V22h46v-9.24z\" /><path d=\"M41.613 15.931c0-1.605.994-2.93 2.227-2.931H55v18.137C55 33.26 53.68 35 52.05 35h-40.1C10.32 35 9 33.259 9 31.137V13h11.16c1.233 0 2.227 1.323 2.227 2.928v.022c0 1.605 1.005 2.901 2.237 2.901h14.752c1.232 0 2.237-1.308 2.237-2.913v-.007z\" fill=\"#fafafa\" /></g></g></svg>","fault":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 16 16\" fill=\"none\" id=\"icon-fault\">\n<g id=\"icon-fault_Frame\" clip-path=\"url(#icon-fault_clip0_955_19678)\">\n<path id=\"icon-fault_Vector\" d=\"M14.9331 8.00365C14.9331 11.833 11.8291 14.937 7.99974 14.937C4.17041 14.937 1.06641 11.833 1.06641 8.00365C1.06641 4.17431 4.17041 1.07031 7.99974 1.07031C11.8291 1.07031 14.9331 4.17431 14.9331 8.00365Z\" fill=\"#F6453F\" />\n<path id=\"icon-fault_Vector_2\" d=\"M7.99987 1.59792C4.46547 1.59792 1.59987 4.46352 1.59987 7.99792C1.59987 11.5323 4.46547 14.3979 7.99987 14.3979C11.5343 14.3979 14.3999 11.5323 14.3999 7.99792C14.3999 4.46352 11.5343 1.59792 7.99987 1.59792ZM0.533203 7.99792C0.533203 3.87418 3.87614 0.53125 7.99987 0.53125C12.1236 0.53125 15.4665 3.87418 15.4665 7.99792C15.4665 12.1216 12.1236 15.4646 7.99987 15.4646C3.87614 15.4646 0.533203 12.1216 0.533203 7.99792Z\" fill=\"#F6453F\" />\n<path id=\"icon-fault_Vector_3\" d=\"M8.82 3H7.00013L7.1985 10.2294H8.62163L8.82 3ZM8.55187 11.5847C8.46844 11.5064 8.36852 11.4445 8.2582 11.4028C8.14787 11.361 8.02943 11.3402 7.91007 11.3417C7.66135 11.3417 7.44661 11.4229 7.26826 11.5847C7.18159 11.661 7.11304 11.7529 7.0669 11.8546C7.02076 11.9563 6.99803 12.0657 7.00013 12.1758C7.00013 12.4122 7.08931 12.6102 7.26826 12.7703C7.44661 12.9299 7.66074 13.01 7.91007 13.01C8.15878 13.01 8.37353 12.9299 8.55187 12.7703C8.73083 12.6102 8.82 12.4122 8.82 12.1758C8.82 11.9439 8.73083 11.7465 8.55187 11.5847Z\" fill=\"white\" />\n</g>\n<defs>\n<clipPath id=\"icon-fault_clip0_955_19678\">\n<rect width=\"16\" height=\"16\" fill=\"white\" />\n</clipPath>\n</defs>\n</svg>","fault_red":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 16 16\" fill=\"none\" id=\"icon-fault-red\">\n<g id=\"icon-fault-red_Icon / ExclamationCircleOutlined\">\n<g id=\"icon-fault-red_Vector\">\n<path d=\"M8 1C4.13438 1 1 4.13438 1 8C1 11.8656 4.13438 15 8 15C11.8656 15 15 11.8656 15 8C15 4.13438 11.8656 1 8 1ZM8 13.8125C4.79063 13.8125 2.1875 11.2094 2.1875 8C2.1875 4.79063 4.79063 2.1875 8 2.1875C11.2094 2.1875 13.8125 4.79063 13.8125 8C13.8125 11.2094 11.2094 13.8125 8 13.8125Z\" fill=\"#F5222D\" />\n<path d=\"M7.25 10.75C7.25 10.9489 7.32902 11.1397 7.46967 11.2803C7.61032 11.421 7.80109 11.5 8 11.5C8.19891 11.5 8.38968 11.421 8.53033 11.2803C8.67098 11.1397 8.75 10.9489 8.75 10.75C8.75 10.5511 8.67098 10.3603 8.53033 10.2197C8.38968 10.079 8.19891 10 8 10C7.80109 10 7.61032 10.079 7.46967 10.2197C7.32902 10.3603 7.25 10.5511 7.25 10.75ZM7.625 9H8.375C8.44375 9 8.5 8.94375 8.5 8.875V4.625C8.5 4.55625 8.44375 4.5 8.375 4.5H7.625C7.55625 4.5 7.5 4.55625 7.5 4.625V8.875C7.5 8.94375 7.55625 9 7.625 9Z\" fill=\"#F5222D\" />\n</g>\n</g>\n</svg>","faults":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 48 48\" fill=\"none\" id=\"icon-faults\">\n<g id=\"icon-faults_Group 1000006122\">\n<rect id=\"icon-faults_Rectangle 71\" width=\"48\" height=\"48\" rx=\"4\" fill=\"#FC355D\" />\n<g id=\"icon-faults_Frame\">\n<path id=\"icon-faults_Vector\" d=\"M36.0278 32.5028L25.4524 13.7769C25.3062 13.5148 25.0949 13.297 24.8398 13.1454C24.5847 12.9939 24.295 12.9141 24 12.9141C23.705 12.9141 23.4153 12.9939 23.1602 13.1454C22.9051 13.297 22.6938 13.5148 22.5476 13.7769L11.9721 32.5028C11.8258 32.7645 11.7492 33.0609 11.75 33.3624C11.7508 33.6639 11.8289 33.9599 11.9765 34.2208C12.1241 34.4818 12.3361 34.6985 12.5913 34.8494C12.8465 35.0003 13.1359 35.0801 13.4306 35.0807H34.5755C34.8697 35.079 35.1583 34.9984 35.4127 34.8471C35.667 34.6958 35.8781 34.4789 36.025 34.2182C36.1719 33.9574 36.2495 33.6618 36.25 33.3609C36.2505 33.0599 36.1739 32.7641 36.0278 32.5028ZM22.8039 20.4683C22.8039 20.1372 22.9325 19.8197 23.1614 19.5856C23.3903 19.3514 23.7007 19.2199 24.0244 19.2199C24.3428 19.2281 24.6454 19.3632 24.8678 19.5964C25.0901 19.8297 25.2145 20.1425 25.2144 20.4683V26.8975C25.1583 27.1797 25.0087 27.4334 24.7907 27.6157C24.5727 27.7979 24.2998 27.8975 24.0183 27.8975C23.7368 27.8975 23.4639 27.7979 23.2459 27.6157C23.0279 27.4334 22.8783 27.1797 22.8222 26.8975L22.8039 20.4683ZM25.2144 33.2518H22.7734V30.7551H25.2144V33.2518Z\" fill=\"white\" />\n</g>\n</g>\n</svg>","tips_warn":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 16 16\" fill=\"none\" id=\"icon-tipsWarn\">\n<g id=\"icon-tipsWarn_warning-filled\">\n<path id=\"icon-tipsWarn_vector\" d=\"M8 1C9.97933 1.052 11.6278 1.73683 12.9455 3.0545C14.2632 4.37217 14.948 6.02067 15 8C14.948 9.97933 14.2632 11.6278 12.9455 12.9455C11.6278 14.2632 9.97933 14.948 8 15C6.02067 14.948 4.37217 14.2632 3.0545 12.9455C1.73683 11.6278 1.052 9.97933 1 8C1.052 6.02067 1.73683 4.37217 3.0545 3.0545C4.37217 1.73683 6.02067 1.052 8 1ZM8 4C7.729 4 7.505 4.099 7.328 4.297C7.151 4.495 7.07283 4.72933 7.0935 5L7.453 9C7.474 9.146 7.53383 9.26317 7.6325 9.3515C7.73117 9.43983 7.8535 9.48417 7.9995 9.4845C8.1455 9.48483 8.26783 9.4405 8.3665 9.3515C8.46517 9.2625 8.525 9.14533 8.546 9L8.9055 5C8.9265 4.729 8.84833 4.49467 8.671 4.297C8.49367 4.09933 8.26967 4.00033 7.999 4H8ZM8 12C8.22933 11.9897 8.4195 11.9115 8.5705 11.7655C8.7215 11.6195 8.797 11.432 8.797 11.203C8.797 10.974 8.7215 10.7838 8.5705 10.6325C8.4195 10.4812 8.22933 10.4057 8 10.406C7.77067 10.4063 7.5805 10.4818 7.4295 10.6325C7.2785 10.7832 7.203 10.9733 7.203 11.203C7.203 11.4327 7.2785 11.6202 7.4295 11.7655C7.5805 11.9108 7.77067 11.989 8 12Z\" fill=\"#FA7D08\" />\n</g>\n</svg>","active_cog":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1618 1618\" class=\"fox-alarm-cog-svg\" aria-hidden=\"true\">\n  <g class=\"fox-alarm-cog-gear fox-alarm-cog-gear--gray\">\n    <g transform=\"matrix(0.8079075813293457,0.5893091559410095,-0.5893091559410095,0.8079075813293457,512,512)\">\n      <path fill=\"#f5f5f5\" d=\"M193.4239959716797,0.6759999990463257 C193.4239959716797,-105.7750015258789 107.12799835205078,-192.0709991455078 0.6769999861717224,-192.0709991455078 C-105.7750015258789,-192.0709991455078 -192.07000732421875,-105.7750015258789 -192.07000732421875,0.6759999990463257 C-192.07000732421875,107.12799835205078 -105.7750015258789,193.42300415039062 0.6769999861717224,193.42300415039062 C107.12799835205078,193.42300415039062 193.4239959716797,107.12799835205078 193.4239959716797,0.6759999990463257z M387.0889892578125,225.6790008544922 C383.3429870605469,232.09100341796875 375.57000732421875,234.8489990234375 368.5350036621094,232.47000122070312 C368.5350036621094,232.47000122070312 292.6510009765625,206.80499267578125 292.6510009765625,206.80499267578125 C269.49700927734375,239.63600158691406 240.656005859375,268.8160095214844 206.8159942626953,292.6820068359375 C206.8159942626953,292.6820068359375 232.47000122070312,368.5350036621094 232.47000122070312,368.5350036621094 C234.8489990234375,375.5690002441406 232.09100341796875,383.3429870605469 225.67999267578125,387.0889892578125 C191.17599487304688,407.24798583984375 153.73399353027344,422.927001953125 114.15299987792969,433.32598876953125 C106.97000122070312,435.2130126953125 99.52200317382812,431.6659851074219 96.2300033569336,425.010009765625 C96.2300033569336,425.010009765625 60.715999603271484,353.197998046875 60.715999603271484,353.197998046875 C19.913000106811523,360.2510070800781 -21.114999771118164,360.010986328125 -60.70199966430664,353.16900634765625 C-60.70199966430664,353.16900634765625 -96.2300033569336,425.010009765625 -96.2300033569336,425.010009765625 C-99.52200317382812,431.6659851074219 -106.97100067138672,435.2130126953125 -114.15299987792969,433.32598876953125 C-153.73500061035156,422.927001953125 -191.17599487304688,407.24798583984375 -225.67999267578125,387.0889892578125 C-232.09100341796875,383.3420104980469 -234.85000610351562,375.5690002441406 -232.4709930419922,368.5350036621094 C-232.4709930419922,368.5350036621094 -206.80599975585938,292.6499938964844 -206.80599975585938,292.6499938964844 C-239.63699340820312,269.49700927734375 -268.8169860839844,240.65499877929688 -292.6820068359375,206.8159942626953 C-292.6820068359375,206.8159942626953 -368.5350036621094,232.47000122070312 -368.5350036621094,232.47000122070312 C-375.5690002441406,234.8489990234375 -383.3429870605469,232.09100341796875 -387.0889892578125,225.6790008544922 C-407.2489929199219,191.17599487304688 -422.927001953125,153.73399353027344 -433.32598876953125,114.15299987792969 C-435.2130126953125,106.97000122070312 -431.6669921875,99.52100372314453 -425.010009765625,96.22899627685547 C-425.010009765625,96.22899627685547 -353.1990051269531,60.715999603271484 -353.1990051269531,60.715999603271484 C-360.2510070800781,19.913000106811523 -360.0119934082031,-21.114999771118164 -353.16900634765625,-60.70199966430664 C-353.16900634765625,-60.70199966430664 -425.010009765625,-96.2300033569336 -425.010009765625,-96.2300033569336 C-431.6669921875,-99.52200317382812 -435.2130126953125,-106.97100067138672 -433.32598876953125,-114.15299987792969 C-422.927001953125,-153.73500061035156 -407.2489929199219,-191.177001953125 -387.0889892578125,-225.67999267578125 C-383.3429870605469,-232.0919952392578 -375.5690002441406,-234.85000610351562 -368.5350036621094,-232.4709930419922 C-368.5350036621094,-232.4709930419922 -292.6510009765625,-206.80599975585938 -292.6510009765625,-206.80599975585938 C-269.49700927734375,-239.63699340820312 -240.656005859375,-268.8169860839844 -206.8159942626953,-292.6820068359375 C-206.8159942626953,-292.6820068359375 -232.47000122070312,-368.5360107421875 -232.47000122070312,-368.5360107421875 C-234.8489990234375,-375.57000732421875 -232.09100341796875,-383.3429870605469 -225.67999267578125,-387.0889892578125 C-191.17599487304688,-407.2489929199219 -153.73399353027344,-422.927001953125 -114.15299987792969,-433.32598876953125 C-106.97000122070312,-435.2130126953125 -99.52200317382812,-431.6669921875 -96.2300033569336,-425.010009765625 C-96.2300033569336,-425.010009765625 -60.715999603271484,-353.1990051269531 -60.715999603271484,-353.1990051269531 C-19.913000106811523,-360.25201416015625 21.114999771118164,-360.0119934082031 60.70100021362305,-353.1700134277344 C60.70100021362305,-353.1700134277344 96.22899627685547,-425.010009765625 96.22899627685547,-425.010009765625 C99.52100372314453,-431.6669921875 106.97000122070312,-435.2130126953125 114.15299987792969,-433.32598876953125 C153.73399353027344,-422.927001953125 191.17599487304688,-407.2489929199219 225.6790008544922,-387.0899963378906 C232.09100341796875,-383.3429870605469 234.8489990234375,-375.57000732421875 232.47000122070312,-368.5360107421875 C232.47000122070312,-368.5360107421875 206.80499267578125,-292.6520080566406 206.80499267578125,-292.6520080566406 C239.63600158691406,-269.49798583984375 268.8169860839844,-240.656005859375 292.6820068359375,-206.81700134277344 C292.6820068359375,-206.81700134277344 368.5350036621094,-232.4709930419922 368.5350036621094,-232.4709930419922 C375.57000732421875,-234.85000610351562 383.3429870605469,-232.0919952392578 387.0889892578125,-225.67999267578125 C407.2489929199219,-191.17599487304688 422.927001953125,-153.73500061035156 433.32598876953125,-114.15299987792969 C435.2130126953125,-106.97100067138672 431.6669921875,-99.52200317382812 425.010009765625,-96.2300033569336 C425.010009765625,-96.2300033569336 353.1990051269531,-60.71699905395508 353.1990051269531,-60.71699905395508 C360.25201416015625,-19.913000106811523 360.0119934082031,21.11400032043457 353.16900634765625,60.70100021362305 C353.16900634765625,60.70100021362305 425.010009765625,96.22899627685547 425.010009765625,96.22899627685547 C431.6669921875,99.52100372314453 435.2130126953125,106.97000122070312 433.32598876953125,114.1520004272461 C422.927001953125,153.73399353027344 407.2489929199219,191.17599487304688 387.0889892578125,225.6790008544922z\"/>\n      <path fill=\"#d8d8d8\" d=\"M0.6769999861717224,193.42300415039062 C-105.7750015258789,193.42300415039062 -192.07000732421875,107.12799835205078 -192.07000732421875,0.6759999990463257 C-192.07000732421875,-105.7750015258789 -105.7750015258789,-192.0709991455078 0.6769999861717224,-192.0709991455078 C107.12799835205078,-192.0709991455078 193.4239959716797,-105.7750015258789 193.4239959716797,0.6759999990463257 C193.4239959716797,107.12799835205078 107.12799835205078,193.42300415039062 0.6769999861717224,193.42300415039062z M203.4239959716797,0.6759999990463257 C203.4239959716797,-111.2979965209961 112.6510009765625,-202.0709991455078 0.6769999861717224,-202.0709991455078 C-111.2969970703125,-202.0709991455078 -202.07000732421875,-111.2979965209961 -202.07000732421875,0.6759999990463257 C-202.07000732421875,112.6500015258789 -111.2969970703125,203.42300415039062 0.6769999861717224,203.42300415039062 C112.6510009765625,203.42300415039062 203.4239959716797,112.6500015258789 203.4239959716797,0.6759999990463257z M206.8159942626953,292.6820068359375 C240.656005859375,268.8160095214844 269.49700927734375,239.63600158691406 292.6510009765625,206.80499267578125 C292.6510009765625,206.80499267578125 368.5350036621094,232.47000122070312 368.5350036621094,232.47000122070312 C375.57000732421875,234.8489990234375 383.3429870605469,232.09100341796875 387.0889892578125,225.6790008544922 C407.2489929199219,191.17599487304688 422.927001953125,153.73399353027344 433.32598876953125,114.1520004272461 C435.2130126953125,106.97000122070312 431.6669921875,99.52100372314453 425.010009765625,96.22899627685547 C425.010009765625,96.22899627685547 353.16900634765625,60.70100021362305 353.16900634765625,60.70100021362305 C360.0119934082031,21.11400032043457 360.25201416015625,-19.913000106811523 353.1990051269531,-60.71699905395508 C353.1990051269531,-60.71699905395508 425.010009765625,-96.2300033569336 425.010009765625,-96.2300033569336 C431.6669921875,-99.52200317382812 435.2130126953125,-106.97100067138672 433.32598876953125,-114.15299987792969 C422.927001953125,-153.73500061035156 407.2489929199219,-191.17599487304688 387.0889892578125,-225.67999267578125 C383.3429870605469,-232.0919952392578 375.57000732421875,-234.85000610351562 368.5350036621094,-232.4709930419922 C368.5350036621094,-232.4709930419922 292.6820068359375,-206.81700134277344 292.6820068359375,-206.81700134277344 C268.8169860839844,-240.656005859375 239.63600158691406,-269.49798583984375 206.80499267578125,-292.6520080566406 C206.80499267578125,-292.6520080566406 232.47000122070312,-368.5360107421875 232.47000122070312,-368.5360107421875 C234.8489990234375,-375.57000732421875 232.09100341796875,-383.3429870605469 225.6790008544922,-387.0899963378906 C191.17599487304688,-407.2489929199219 153.73399353027344,-422.927001953125 114.15299987792969,-433.32598876953125 C106.97000122070312,-435.2130126953125 99.52100372314453,-431.6669921875 96.22899627685547,-425.010009765625 C96.22899627685547,-425.010009765625 60.70100021362305,-353.1700134277344 60.70100021362305,-353.1700134277344 C21.114999771118164,-360.0119934082031 -19.913000106811523,-360.25201416015625 -60.715999603271484,-353.1990051269531 C-60.715999603271484,-353.1990051269531 -96.2300033569336,-425.010009765625 -96.2300033569336,-425.010009765625 C-99.52200317382812,-431.6669921875 -106.97000122070312,-435.2130126953125 -114.15299987792969,-433.32598876953125 C-153.73399353027344,-422.927001953125 -191.17599487304688,-407.2489929199219 -225.67999267578125,-387.0889892578125 C-232.09100341796875,-383.3429870605469 -234.8489990234375,-375.57000732421875 -232.47000122070312,-368.5360107421875 C-232.47000122070312,-368.5360107421875 -206.8159942626953,-292.6820068359375 -206.8159942626953,-292.6820068359375 C-240.656005859375,-268.8169860839844 -269.49700927734375,-239.63699340820312 -292.6510009765625,-206.80599975585938 C-292.6510009765625,-206.80599975585938 -368.5350036621094,-232.4709930419922 -368.5350036621094,-232.4709930419922 C-375.5690002441406,-234.85000610351562 -383.3429870605469,-232.0919952392578 -387.0889892578125,-225.67999267578125 C-407.2489929199219,-191.177001953125 -422.927001953125,-153.73500061035156 -433.32598876953125,-114.15299987792969 C-435.2130126953125,-106.97100067138672 -431.6669921875,-99.52200317382812 -425.010009765625,-96.2300033569336 C-425.010009765625,-96.2300033569336 -353.16900634765625,-60.70199966430664 -353.16900634765625,-60.70199966430664 C-360.0119934082031,-21.114999771118164 -360.2510070800781,19.913000106811523 -353.1990051269531,60.715999603271484 C-353.1990051269531,60.715999603271484 -425.010009765625,96.22899627685547 -425.010009765625,96.22899627685547 C-431.6669921875,99.52100372314453 -435.2130126953125,106.97000122070312 -433.32598876953125,114.15299987792969 C-422.927001953125,153.73399353027344 -407.2489929199219,191.17599487304688 -387.0889892578125,225.6790008544922 C-383.3429870605469,232.09100341796875 -375.5690002441406,234.8489990234375 -368.5350036621094,232.47000122070312 C-368.5350036621094,232.47000122070312 -292.6820068359375,206.8159942626953 -292.6820068359375,206.8159942626953 C-268.8169860839844,240.65499877929688 -239.63699340820312,269.49700927734375 -206.80599975585938,292.6499938964844 C-206.80599975585938,292.6499938964844 -232.4709930419922,368.5350036621094 -232.4709930419922,368.5350036621094 C-234.85000610351562,375.5690002441406 -232.09100341796875,383.3420104980469 -225.67999267578125,387.0889892578125 C-191.17599487304688,407.24798583984375 -153.73500061035156,422.927001953125 -114.15299987792969,433.32598876953125 C-106.97100067138672,435.2130126953125 -99.52200317382812,431.6659851074219 -96.2300033569336,425.010009765625 C-96.2300033569336,425.010009765625 -60.70199966430664,353.16900634765625 -60.70199966430664,353.16900634765625 C-21.114999771118164,360.010986328125 19.913000106811523,360.2510070800781 60.715999603271484,353.197998046875 C60.715999603271484,353.197998046875 96.2300033569336,425.010009765625 96.2300033569336,425.010009765625 C99.52200317382812,431.6659851074219 106.97000122070312,435.2130126953125 114.15299987792969,433.32598876953125 C153.73399353027344,422.927001953125 191.17599487304688,407.24798583984375 225.67999267578125,387.0889892578125 C232.09100341796875,383.3429870605469 234.8489990234375,375.5690002441406 232.47000122070312,368.5350036621094 C232.47000122070312,368.5350036621094 206.8159942626953,292.6820068359375 206.8159942626953,292.6820068359375z M288.7820129394531,194.94000244140625 C288.7820129394531,194.94000244140625 284.47900390625,201.04200744628906 284.47900390625,201.04200744628906 C261.97100830078125,232.95599365234375 233.93899536132812,261.3160095214844 201.05299377441406,284.510009765625 C201.05299377441406,284.510009765625 194.9510040283203,288.81298828125 194.9510040283203,288.81298828125 C194.9510040283203,288.81298828125 222.9969940185547,371.739013671875 222.9969940185547,371.739013671875 C223.91099548339844,374.44000244140625 222.8000030517578,377.19000244140625 220.63499450683594,378.4549865722656 C186.9029998779297,398.16400146484375 150.302001953125,413.489013671875 111.61199951171875,423.65399169921875 C109.18800354003906,424.2909851074219 106.45800018310547,423.13299560546875 105.19400024414062,420.5769958496094 C105.19400024414062,420.5769958496094 66.37000274658203,342.072998046875 66.37000274658203,342.072998046875 C66.37000274658203,342.072998046875 59.01300048828125,343.343994140625 59.01300048828125,343.343994140625 C19.358999252319336,350.1990051269531 -20.517000198364258,349.9670104980469 -58.999000549316406,343.31500244140625 C-58.999000549316406,343.31500244140625 -66.35600280761719,342.0429992675781 -66.35600280761719,342.0429992675781 C-66.35600280761719,342.0429992675781 -105.19400024414062,420.5769958496094 -105.19400024414062,420.5769958496094 C-106.45800018310547,423.13299560546875 -109.18800354003906,424.2909851074219 -111.61199951171875,423.65399169921875 C-150.302001953125,413.489013671875 -186.9029998779297,398.1629943847656 -220.63499450683594,378.4540100097656 C-222.8000030517578,377.1889953613281 -223.91099548339844,374.44000244140625 -222.9980010986328,371.739013671875 C-222.9980010986328,371.739013671875 -194.9409942626953,288.781005859375 -194.9409942626953,288.781005859375 C-194.9409942626953,288.781005859375 -201.04299926757812,284.4779968261719 -201.04299926757812,284.4779968261719 C-232.95700073242188,261.97100830078125 -261.3169860839844,233.93899536132812 -284.510009765625,201.052001953125 C-284.510009765625,201.052001953125 -288.81298828125,194.9510040283203 -288.81298828125,194.9510040283203 C-288.81298828125,194.9510040283203 -371.739013671875,222.9969940185547 -371.739013671875,222.9969940185547 C-374.4410095214844,223.91099548339844 -377.19000244140625,222.8000030517578 -378.4549865722656,220.63499450683594 C-398.16400146484375,186.90199279785156 -413.489013671875,150.30099487304688 -423.65399169921875,111.61199951171875 C-424.2909851074219,109.18800354003906 -423.13299560546875,106.45700073242188 -420.5769958496094,105.19300079345703 C-420.5769958496094,105.19300079345703 -342.072998046875,66.37000274658203 -342.072998046875,66.37000274658203 C-342.072998046875,66.37000274658203 -343.3450012207031,59.01300048828125 -343.3450012207031,59.01300048828125 C-350.1990051269531,19.357999801635742 -349.9670104980469,-20.517000198364258 -343.31500244140625,-58.999000549316406 C-343.31500244140625,-58.999000549316406 -342.0429992675781,-66.35600280761719 -342.0429992675781,-66.35600280761719 C-342.0429992675781,-66.35600280761719 -420.5769958496094,-105.19400024414062 -420.5769958496094,-105.19400024414062 C-423.13299560546875,-106.45800018310547 -424.2909851074219,-109.18800354003906 -423.65399169921875,-111.61199951171875 C-413.489013671875,-150.302001953125 -398.16400146484375,-186.9029998779297 -378.4549865722656,-220.63499450683594 C-377.19000244140625,-222.80099487304688 -374.44000244140625,-223.91200256347656 -371.739013671875,-222.9980010986328 C-371.739013671875,-222.9980010986328 -288.7820129394531,-194.9409942626953 -288.7820129394531,-194.9409942626953 C-288.7820129394531,-194.9409942626953 -284.47900390625,-201.04299926757812 -284.47900390625,-201.04299926757812 C-261.97100830078125,-232.95700073242188 -233.93899536132812,-261.3169860839844 -201.05299377441406,-284.510009765625 C-201.05299377441406,-284.510009765625 -194.9510040283203,-288.81298828125 -194.9510040283203,-288.81298828125 C-194.9510040283203,-288.81298828125 -222.9969940185547,-371.739013671875 -222.9969940185547,-371.739013671875 C-223.91099548339844,-374.4410095214844 -222.8000030517578,-377.19000244140625 -220.63499450683594,-378.4549865722656 C-186.90199279785156,-398.16400146484375 -150.302001953125,-413.489013671875 -111.61199951171875,-423.65399169921875 C-109.18800354003906,-424.2909851074219 -106.45800018310547,-423.1340026855469 -105.19400024414062,-420.5769958496094 C-105.19400024414062,-420.5769958496094 -66.37000274658203,-342.072998046875 -66.37000274658203,-342.072998046875 C-66.37000274658203,-342.072998046875 -59.01300048828125,-343.3450012207031 -59.01300048828125,-343.3450012207031 C-19.358999252319336,-350.1990051269531 20.516000747680664,-349.9670104980469 58.99800109863281,-343.3160095214844 C58.99800109863281,-343.3160095214844 66.3550033569336,-342.04400634765625 66.3550033569336,-342.04400634765625 C66.3550033569336,-342.04400634765625 105.19300079345703,-420.5769958496094 105.19300079345703,-420.5769958496094 C106.45700073242188,-423.13299560546875 109.18800354003906,-424.2919921875 111.61199951171875,-423.6549987792969 C150.302001953125,-413.489990234375 186.90199279785156,-398.16400146484375 220.63499450683594,-378.4549865722656 C222.8000030517578,-377.19000244140625 223.91099548339844,-374.4410095214844 222.9969940185547,-371.739990234375 C222.9969940185547,-371.739990234375 194.94000244140625,-288.7829895019531 194.94000244140625,-288.7829895019531 C194.94000244140625,-288.7829895019531 201.04200744628906,-284.47900390625 201.04200744628906,-284.47900390625 C232.95700073242188,-261.97198486328125 261.3169860839844,-233.94000244140625 284.510009765625,-201.05299377441406 C284.510009765625,-201.05299377441406 288.81298828125,-194.95199584960938 288.81298828125,-194.95199584960938 C288.81298828125,-194.95199584960938 371.739013671875,-222.9980010986328 371.739013671875,-222.9980010986328 C374.4410095214844,-223.91099548339844 377.19000244140625,-222.8000030517578 378.4549865722656,-220.63499450683594 C398.16400146484375,-186.9029998779297 413.489990234375,-150.302001953125 423.65399169921875,-111.61199951171875 C424.2909851074219,-109.18800354003906 423.1340026855469,-106.45800018310547 420.5769958496094,-105.19400024414062 C420.5769958496094,-105.19400024414062 342.072998046875,-66.37100219726562 342.072998046875,-66.37100219726562 C342.072998046875,-66.37100219726562 343.3450012207031,-59.01300048828125 343.3450012207031,-59.01300048828125 C350.1990051269531,-19.358999252319336 349.9670104980469,20.516000747680664 343.31500244140625,58.99800109863281 C343.31500244140625,58.99800109863281 342.04400634765625,66.3550033569336 342.04400634765625,66.3550033569336 C342.04400634765625,66.3550033569336 420.5769958496094,105.19300079345703 420.5769958496094,105.19300079345703 C423.1340026855469,106.45700073242188 424.2909851074219,109.18699645996094 423.65399169921875,111.61100006103516 C413.489990234375,150.30099487304688 398.16400146484375,186.90199279785156 378.4549865722656,220.63400268554688 C377.19000244140625,222.7989959716797 374.4410095214844,223.91099548339844 371.739013671875,222.9969940185547 C371.739013671875,222.9969940185547 288.7820129394531,194.94000244140625 288.7820129394531,194.94000244140625z\"/>\n    </g>\n  </g>\n  <g class=\"fox-alarm-cog-gear fox-alarm-cog-gear--green\">\n    <g transform=\"matrix(0.8079075813293457,-0.5893091559410095,0.5893091559410095,0.8079075813293457,1106.001953125,1106.001953125)\">\n      <path fill=\"#f5ffed\" d=\"M178.95799255371094,-73.39199829101562 C138.21800231933594,-171.7449951171875 25.468000411987305,-218.447998046875 -72.88200378417969,-177.7100067138672 C-171.2270050048828,-136.97300720214844 -217.9290008544922,-24.222000122070312 -177.19200134277344,74.12799835205078 C-136.4550018310547,172.47799682617188 -23.70199966430664,219.17799377441406 74.64800262451172,178.43800354003906 C172.98800659179688,137.697998046875 219.697998046875,24.947999954223633 178.95799255371094,-73.39199829101562z M443.9880065917969,60.36800003051758 C442.9779968261719,67.72799682617188 436.8479919433594,73.24800109863281 429.447998046875,73.73799896240234 C429.447998046875,73.73799896240234 349.51800537109375,79.06800079345703 349.51800537109375,79.06800079345703 C340.68798828125,118.25800323486328 325.2070007324219,156.25799560546875 303.0769958496094,191.25799560546875 C303.0769958496094,191.25799560546875 355.8080139160156,251.51800537109375 355.8080139160156,251.51800537109375 C360.697998046875,257.1080017089844 361.1180114746094,265.3479919433594 356.62799072265625,271.25799560546875 C332.4679870605469,303.0880126953125 303.87799072265625,331.89801025390625 271.2879943847656,356.6579895019531 C265.37799072265625,361.14801025390625 257.13800048828125,360.7179870605469 251.54800415039062,355.8280029296875 C251.54800415039062,355.8280029296875 191.25799560546875,303.0769958496094 191.25799560546875,303.0769958496094 C156.25799560546875,325.2070007324219 118.25800323486328,340.68798828125 79.06800079345703,349.51800537109375 C79.06800079345703,349.51800537109375 73.73799896240234,429.4779968261719 73.73799896240234,429.4779968261719 C73.24800109863281,436.88800048828125 67.71800231933594,443.01800537109375 60.358001708984375,444.02801513671875 C19.81800079345703,449.5679931640625 -20.781999588012695,449.4079895019531 -60.37200164794922,443.9880065917969 C-67.72200012207031,442.9779968261719 -73.25199890136719,436.8479919433594 -73.74199676513672,429.447998046875 C-73.74199676513672,429.447998046875 -79.0719985961914,349.51800537109375 -79.0719985961914,349.51800537109375 C-118.26499938964844,340.68798828125 -156.26100158691406,325.2070007324219 -191.25900268554688,303.0769958496094 C-191.25900268554688,303.0769958496094 -251.52099609375,355.8080139160156 -251.52099609375,355.8080139160156 C-257.1090087890625,360.697998046875 -265.34698486328125,361.1180114746094 -271.260986328125,356.62799072265625 C-303.0899963378906,332.4679870605469 -331.90399169921875,303.87799072265625 -356.6579895019531,271.2879943847656 C-361.1499938964844,265.37799072265625 -360.7239990234375,257.13800048828125 -355.8340148925781,251.54800415039062 C-355.8340148925781,251.54800415039062 -303.0790100097656,191.25799560546875 -303.0790100097656,191.25799560546875 C-325.2099914550781,156.25799560546875 -340.6889953613281,118.25800323486328 -349.5169982910156,79.06800079345703 C-349.5169982910156,79.06800079345703 -429.4849853515625,73.73799896240234 -429.4849853515625,73.73799896240234 C-436.8949890136719,73.24800109863281 -443.0220031738281,67.71800231933594 -444.0270080566406,60.358001708984375 C-449.5669860839844,19.81800079345703 -449.4100036621094,-20.781999588012695 -443.989013671875,-60.37200164794922 C-442.98199462890625,-67.73200225830078 -436.8550109863281,-73.25199890136719 -429.4460144042969,-73.74199676513672 C-429.4460144042969,-73.74199676513672 -349.5169982910156,-79.0719985961914 -349.5169982910156,-79.0719985961914 C-340.6889953613281,-118.26499938964844 -325.2099914550781,-156.26100158691406 -303.0790100097656,-191.25900268554688 C-303.0790100097656,-191.25900268554688 -355.8080139160156,-251.52099609375 -355.8080139160156,-251.52099609375 C-360.697998046875,-257.1099853515625 -361.125,-265.34698486328125 -356.635009765625,-271.260986328125 C-332.47198486328125,-303.09100341796875 -303.8810119628906,-331.90399169921875 -271.2919921875,-356.6579895019531 C-265.37799072265625,-361.1499938964844 -257.1390075683594,-360.7239990234375 -251.5500030517578,-355.8340148925781 C-251.5500030517578,-355.8340148925781 -191.25900268554688,-303.0790100097656 -191.25900268554688,-303.0790100097656 C-156.26100158691406,-325.2099914550781 -118.26499938964844,-340.6889953613281 -79.0719985961914,-349.5169982910156 C-79.0719985961914,-349.5169982910156 -73.74199676513672,-429.4849853515625 -73.74199676513672,-429.4849853515625 C-73.25199890136719,-436.8949890136719 -67.72200012207031,-443.0220031738281 -60.36199951171875,-444.0270080566406 C-19.812000274658203,-449.5669860839844 20.777999877929688,-449.4100036621094 60.36800003051758,-443.989013671875 C67.72799682617188,-442.98199462890625 73.24800109863281,-436.8559875488281 73.73799896240234,-429.4460144042969 C73.73799896240234,-429.4460144042969 79.06800079345703,-349.5169982910156 79.06800079345703,-349.5169982910156 C118.25800323486328,-340.69000244140625 156.25799560546875,-325.2099914550781 191.25799560546875,-303.0790100097656 C191.25799560546875,-303.0790100097656 251.51800537109375,-355.8080139160156 251.51800537109375,-355.8080139160156 C257.1080017089844,-360.697998046875 265.3479919433594,-361.125 271.25799560546875,-356.635009765625 C303.0880126953125,-332.4729919433594 331.89801025390625,-303.8810119628906 356.6579895019531,-271.2919921875 C361.14801025390625,-265.37799072265625 360.7179870605469,-257.1390075683594 355.8280029296875,-251.55099487304688 C355.8280029296875,-251.55099487304688 303.0769958496094,-191.25900268554688 303.0769958496094,-191.25900268554688 C325.2070007324219,-156.26100158691406 340.68798828125,-118.26499938964844 349.51800537109375,-79.0719985961914 C349.51800537109375,-79.0719985961914 429.4779968261719,-73.74199676513672 429.4779968261719,-73.74199676513672 C436.88800048828125,-73.25199890136719 443.01800537109375,-67.72200012207031 444.02801513671875,-60.36199951171875 C449.5679931640625,-19.812000274658203 449.4079895019531,20.777999877929688 443.9880065917969,60.36800003051758z\"/>\n      <path fill=\"#b8eb8f\" d=\"M74.64800262451172,178.43800354003906 C172.98800659179688,137.697998046875 219.697998046875,24.947999954223633 178.95799255371094,-73.39199829101562 C138.21800231933594,-171.7449951171875 25.468000411987305,-218.447998046875 -72.88200378417969,-177.7100067138672 C-171.2270050048828,-136.97300720214844 -217.9290008544922,-24.222000122070312 -177.19200134277344,74.12799835205078 C-136.4550018310547,172.47799682617188 -23.70199966430664,219.17799377441406 74.64800262451172,178.43800354003906z M188.197998046875,-77.22200012207031 C231.04800415039062,26.22800064086914 181.91799926757812,144.8280029296875 78.46800231933594,187.67799377441406 C-24.98200035095215,230.5279998779297 -143.58099365234375,181.4080047607422 -186.43099975585938,77.947998046875 C-229.28199768066406,-25.50200080871582 -180.156005859375,-144.0989990234375 -76.7020034790039,-186.94900512695312 C26.74799919128418,-229.8000030517578 145.34800720214844,-180.6739959716797 188.197998046875,-77.22200012207031z M303.0769958496094,191.25799560546875 C325.2070007324219,156.25799560546875 340.68798828125,118.25800323486328 349.51800537109375,79.06800079345703 C349.51800537109375,79.06800079345703 429.447998046875,73.73799896240234 429.447998046875,73.73799896240234 C436.8479919433594,73.24800109863281 442.9779968261719,67.72799682617188 443.9880065917969,60.36800003051758 C449.4079895019531,20.777999877929688 449.5679931640625,-19.812000274658203 444.02801513671875,-60.36199951171875 C443.01800537109375,-67.72200012207031 436.88800048828125,-73.25199890136719 429.4779968261719,-73.74199676513672 C429.4779968261719,-73.74199676513672 349.51800537109375,-79.0719985961914 349.51800537109375,-79.0719985961914 C340.68798828125,-118.26499938964844 325.2070007324219,-156.26100158691406 303.0769958496094,-191.25900268554688 C303.0769958496094,-191.25900268554688 355.8280029296875,-251.55099487304688 355.8280029296875,-251.55099487304688 C360.7179870605469,-257.1390075683594 361.14801025390625,-265.37799072265625 356.6579895019531,-271.2919921875 C331.89801025390625,-303.8810119628906 303.0880126953125,-332.4729919433594 271.25799560546875,-356.635009765625 C265.3479919433594,-361.125 257.1080017089844,-360.697998046875 251.51800537109375,-355.8080139160156 C251.51800537109375,-355.8080139160156 191.25799560546875,-303.0790100097656 191.25799560546875,-303.0790100097656 C156.25799560546875,-325.2099914550781 118.25800323486328,-340.69000244140625 79.06800079345703,-349.5169982910156 C79.06800079345703,-349.5169982910156 73.73799896240234,-429.4460144042969 73.73799896240234,-429.4460144042969 C73.24800109863281,-436.8559875488281 67.72799682617188,-442.98199462890625 60.36800003051758,-443.989013671875 C20.777999877929688,-449.4100036621094 -19.812000274658203,-449.5669860839844 -60.36199951171875,-444.0270080566406 C-67.72200012207031,-443.0220031738281 -73.25199890136719,-436.8949890136719 -73.74199676513672,-429.4849853515625 C-73.74199676513672,-429.4849853515625 -79.0719985961914,-349.5169982910156 -79.0719985961914,-349.5169982910156 C-118.26499938964844,-340.6889953613281 -156.26100158691406,-325.2099914550781 -191.25900268554688,-303.0790100097656 C-191.25900268554688,-303.0790100097656 -251.5500030517578,-355.8340148925781 -251.5500030517578,-355.8340148925781 C-257.1390075683594,-360.7239990234375 -265.37799072265625,-361.1499938964844 -271.2919921875,-356.6579895019531 C-303.8810119628906,-331.90399169921875 -332.47198486328125,-303.09100341796875 -356.635009765625,-271.260986328125 C-361.125,-265.34698486328125 -360.697998046875,-257.1099853515625 -355.8080139160156,-251.52099609375 C-355.8080139160156,-251.52099609375 -303.0790100097656,-191.25900268554688 -303.0790100097656,-191.25900268554688 C-325.2099914550781,-156.26100158691406 -340.6889953613281,-118.26499938964844 -349.5169982910156,-79.0719985961914 C-349.5169982910156,-79.0719985961914 -429.4460144042969,-73.74199676513672 -429.4460144042969,-73.74199676513672 C-436.8550109863281,-73.25199890136719 -442.98199462890625,-67.73200225830078 -443.989013671875,-60.37200164794922 C-449.4100036621094,-20.781999588012695 -449.5669860839844,19.81800079345703 -444.0270080566406,60.358001708984375 C-443.0220031738281,67.71800231933594 -436.8949890136719,73.24800109863281 -429.4849853515625,73.73799896240234 C-429.4849853515625,73.73799896240234 -349.5169982910156,79.06800079345703 -349.5169982910156,79.06800079345703 C-340.6889953613281,118.25800323486328 -325.2099914550781,156.25799560546875 -303.0790100097656,191.25799560546875 C-303.0790100097656,191.25799560546875 -355.8340148925781,251.54800415039062 -355.8340148925781,251.54800415039062 C-360.7239990234375,257.13800048828125 -361.1499938964844,265.37799072265625 -356.6579895019531,271.2879943847656 C-331.90399169921875,303.87799072265625 -303.0899963378906,332.4679870605469 -271.260986328125,356.62799072265625 C-265.34698486328125,361.1180114746094 -257.1090087890625,360.697998046875 -251.52099609375,355.8080139160156 C-251.52099609375,355.8080139160156 -191.25900268554688,303.0769958496094 -191.25900268554688,303.0769958496094 C-156.26100158691406,325.2070007324219 -118.26499938964844,340.68798828125 -79.0719985961914,349.51800537109375 C-79.0719985961914,349.51800537109375 -73.74199676513672,429.447998046875 -73.74199676513672,429.447998046875 C-73.25199890136719,436.8479919433594 -67.72200012207031,442.9779968261719 -60.37200164794922,443.9880065917969 C-20.781999588012695,449.4079895019531 19.81800079345703,449.5679931640625 60.358001708984375,444.02801513671875 C67.71800231933594,443.01800537109375 73.24800109863281,436.88800048828125 73.73799896240234,429.4779968261719 C73.73799896240234,429.4779968261719 79.06800079345703,349.51800537109375 79.06800079345703,349.51800537109375 C118.25800323486328,340.68798828125 156.25799560546875,325.2070007324219 191.25799560546875,303.0769958496094 C191.25799560546875,303.0769958496094 251.54800415039062,355.8280029296875 251.54800415039062,355.8280029296875 C257.13800048828125,360.7179870605469 265.37799072265625,361.14801025390625 271.2879943847656,356.6579895019531 C303.87799072265625,331.89801025390625 332.4679870605469,303.0880126953125 356.62799072265625,271.25799560546875 C361.1180114746094,265.3479919433594 360.697998046875,257.1080017089844 355.8080139160156,251.51800537109375 C355.8080139160156,251.51800537109375 303.0769958496094,191.25799560546875 303.0769958496094,191.25799560546875z M341.39801025390625,69.58799743652344 C341.39801025390625,69.58799743652344 339.75799560546875,76.86799621582031 339.75799560546875,76.86799621582031 C331.1780090332031,114.96800231933594 316.12799072265625,151.8979949951172 294.62799072265625,185.9080047607422 C294.62799072265625,185.9080047607422 290.63800048828125,192.21800231933594 290.63800048828125,192.21800231933594 C290.63800048828125,192.21800231933594 348.27801513671875,258.1080017089844 348.27801513671875,258.1080017089844 C350.1579895019531,260.24798583984375 350.18798828125,263.2179870605469 348.6679992675781,265.2080078125 C325.0480041503906,296.3280029296875 297.0979919433594,324.49798583984375 265.2380065917969,348.68798828125 C263.24798583984375,350.2080078125 260.27801513671875,350.18798828125 258.12799072265625,348.3080139160156 C258.12799072265625,348.3080139160156 192.21800231933594,290.63800048828125 192.21800231933594,290.63800048828125 C192.21800231933594,290.63800048828125 185.9080047607422,294.62799072265625 185.9080047607422,294.62799072265625 C151.8979949951172,316.12799072265625 114.96800231933594,331.1780090332031 76.86799621582031,339.75799560546875 C76.86799621582031,339.75799560546875 69.58799743652344,341.39801025390625 69.58799743652344,341.39801025390625 C69.58799743652344,341.39801025390625 63.757999420166016,428.8179931640625 63.757999420166016,428.8179931640625 C63.56800079345703,431.6579895019531 61.487998962402344,433.77801513671875 59.007999420166016,434.1180114746094 C19.378000259399414,439.52801513671875 -20.302000045776367,439.37701416015625 -59.012001037597656,434.0769958496094 C-61.50199890136719,433.73699951171875 -63.571998596191406,431.62799072265625 -63.762001037597656,428.77801513671875 C-63.762001037597656,428.77801513671875 -69.59200286865234,341.39801025390625 -69.59200286865234,341.39801025390625 C-69.59200286865234,341.39801025390625 -76.87200164794922,339.75799560546875 -76.87200164794922,339.75799560546875 C-114.9729995727539,331.1780090332031 -151.90199279785156,316.12799072265625 -185.9149932861328,294.62799072265625 C-185.9149932861328,294.62799072265625 -192.22500610351562,290.63800048828125 -192.22500610351562,290.63800048828125 C-192.22500610351562,290.63800048828125 -258.1059875488281,348.27801513671875 -258.1059875488281,348.27801513671875 C-260.25201416015625,350.1579895019531 -263.2179870605469,350.18798828125 -265.2149963378906,348.6679992675781 C-296.3320007324219,325.0480041503906 -324.49798583984375,297.0979919433594 -348.69500732421875,265.2380065917969 C-350.21099853515625,263.24798583984375 -350.1860046386719,260.27801513671875 -348.3080139160156,258.12799072265625 C-348.3080139160156,258.12799072265625 -290.6369934082031,192.21800231933594 -290.6369934082031,192.21800231933594 C-290.6369934082031,192.21800231933594 -294.62701416015625,185.9080047607422 -294.62701416015625,185.9080047607422 C-316.135009765625,151.8979949951172 -331.17999267578125,114.96800231933594 -339.760986328125,76.86799621582031 C-339.760986328125,76.86799621582031 -341.4020080566406,69.58799743652344 -341.4020080566406,69.58799743652344 C-341.4020080566406,69.58799743652344 -428.82000732421875,63.757999420166016 -428.82000732421875,63.757999420166016 C-431.6650085449219,63.56800079345703 -433.7799987792969,61.487998962402344 -434.1189880371094,59.007999420166016 C-439.53399658203125,19.378000259399414 -439.3810119628906,-20.302000045776367 -434.08099365234375,-59.012001037597656 C-433.7409973144531,-61.50199890136719 -431.6260070800781,-63.571998596191406 -428.781005859375,-63.762001037597656 C-428.781005859375,-63.762001037597656 -341.4020080566406,-69.59200286865234 -341.4020080566406,-69.59200286865234 C-341.4020080566406,-69.59200286865234 -339.760986328125,-76.87200164794922 -339.760986328125,-76.87200164794922 C-331.17999267578125,-114.9739990234375 -316.135009765625,-151.90199279785156 -294.62701416015625,-185.9149932861328 C-294.62701416015625,-185.9149932861328 -290.6369934082031,-192.2259979248047 -290.6369934082031,-192.2259979248047 C-290.6369934082031,-192.2259979248047 -348.2820129394531,-258.1059875488281 -348.2820129394531,-258.1059875488281 C-350.1600036621094,-260.25299072265625 -350.1860046386719,-263.2179870605469 -348.6700134277344,-265.2149963378906 C-325.0480041503906,-296.3330078125 -297.0979919433594,-324.49798583984375 -265.2430114746094,-348.69500732421875 C-263.24700927734375,-350.21099853515625 -260.2820129394531,-350.1860046386719 -258.135009765625,-348.3080139160156 C-258.135009765625,-348.3080139160156 -192.22500610351562,-290.6369934082031 -192.22500610351562,-290.6369934082031 C-192.22500610351562,-290.6369934082031 -185.9149932861328,-294.62701416015625 -185.9149932861328,-294.62701416015625 C-151.90199279785156,-316.135009765625 -114.9729995727539,-331.17999267578125 -76.87200164794922,-339.760986328125 C-76.87200164794922,-339.760986328125 -69.59200286865234,-341.4020080566406 -69.59200286865234,-341.4020080566406 C-69.59200286865234,-341.4020080566406 -63.762001037597656,-428.82000732421875 -63.762001037597656,-428.82000732421875 C-63.571998596191406,-431.6659851074219 -61.492000579833984,-433.7799987792969 -59.012001037597656,-434.1189880371094 C-19.371999740600586,-439.53399658203125 20.29800033569336,-439.3819885253906 59.007999420166016,-434.0820007324219 C61.49800109863281,-433.7409973144531 63.56800079345703,-431.62701416015625 63.757999420166016,-428.781005859375 C63.757999420166016,-428.781005859375 69.58799743652344,-341.4020080566406 69.58799743652344,-341.4020080566406 C69.58799743652344,-341.4020080566406 76.86799621582031,-339.760986328125 76.86799621582031,-339.760986328125 C114.96800231933594,-331.17999267578125 151.8979949951172,-316.135009765625 185.9080047607422,-294.62701416015625 C185.9080047607422,-294.62701416015625 192.21800231933594,-290.6369934082031 192.21800231933594,-290.6369934082031 C192.21800231933594,-290.6369934082031 258.1080017089844,-348.2829895019531 258.1080017089844,-348.2829895019531 C260.24798583984375,-350.1610107421875 263.2179870605469,-350.1860046386719 265.2080078125,-348.6700134277344 C296.3280029296875,-325.0480041503906 324.49798583984375,-297.0979919433594 348.68798828125,-265.2430114746094 C350.2080078125,-263.24700927734375 350.18798828125,-260.2820129394531 348.3080139160156,-258.135986328125 C348.3080139160156,-258.135986328125 290.63800048828125,-192.22500610351562 290.63800048828125,-192.22500610351562 C290.63800048828125,-192.22500610351562 294.62799072265625,-185.9149932861328 294.62799072265625,-185.9149932861328 C316.12799072265625,-151.90199279785156 331.1780090332031,-114.9739990234375 339.75799560546875,-76.87200164794922 C339.75799560546875,-76.87200164794922 341.39801025390625,-69.59200286865234 341.39801025390625,-69.59200286865234 C341.39801025390625,-69.59200286865234 428.8179931640625,-63.762001037597656 428.8179931640625,-63.762001037597656 C431.6579895019531,-63.571998596191406 433.77801513671875,-61.492000579833984 434.1180114746094,-59.012001037597656 C439.52801513671875,-19.371999740600586 439.37701416015625,20.308000564575195 434.0769958496094,59.007999420166016 C433.73699951171875,61.49800109863281 431.62799072265625,63.56800079345703 428.77801513671875,63.757999420166016 C428.77801513671875,63.757999420166016 341.39801025390625,69.58799743652344 341.39801025390625,69.58799743652344z\"/>\n    </g>\n  </g>\n</svg>"};

function mergeAlarmHistoryEvents(lastRows, alarmsRows) {
  const events = [];
  for (const row of historyToStateRows(lastRows)) {
    for (const ev of parseAlarmLastStateEvents(row.s)) {
      events.push({ ...ev, t: row.t, source: "last" });
    }
  }
  if (!events.length) {
    for (const ev of eventsFromAlarmsHistory(alarmsRows)) {
      events.push({ ...ev, source: "alarms" });
    }
  }
  events.sort((a, b) => a.t - b.t);
  return events;
}

function formatFoxAlarmDateTime(ms) {
  if (!Number.isFinite(ms)) return "—";
  return new Date(ms).toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatFoxTimeAgo(ms, now = Date.now()) {
  if (!Number.isFinite(ms)) return "";
  const sec = Math.max(0, Math.floor((now - ms) / 1000));
  if (sec < 60) return "Updated just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `Updated ${min} minute${min === 1 ? "" : "s"} ago`;
  const hr = Math.floor(min / 60);
  if (hr < 48) return `Updated ${hr} hour${hr === 1 ? "" : "s"} ago`;
  const day = Math.floor(hr / 24);
  return `Updated ${day} day${day === 1 ? "" : "s"} ago`;
}

function buildFoxAlarmDashboard(activeNames, historyEvents, { fetchedAt = Date.now(), deviceName = "Device" } = {}) {
  const active = activeNames.map((name) => {
    const meta = foxAlarmMeta(name);
    let since = null;
    for (let i = historyEvents.length - 1; i >= 0; i -= 1) {
      const ev = historyEvents[i];
      if (ev.name === name && ev.action === "raised") {
        since = ev.t;
        break;
      }
    }
    return { name, ...meta, since, status: "active" };
  });

  const historicalRecords = pairAlarmHistoryRecords(historyEvents, activeNames, deviceName);

  const categoryCounts = {};
  const severityCounts = { critical: 0, warning: 0, info: 0 };
  for (const ev of historyEvents) {
    if (ev.action !== "raised") continue;
    const meta = foxAlarmMeta(ev.name);
    categoryCounts[meta.category] = (categoryCounts[meta.category] || 0) + 1;
    severityCounts[meta.severity] = (severityCounts[meta.severity] || 0) + 1;
  }
  for (const row of active) {
    const meta = foxAlarmMeta(row.name);
    categoryCounts[meta.category] = (categoryCounts[meta.category] || 0) + 1;
    severityCounts[meta.severity] = (severityCounts[meta.severity] || 0) + 1;
  }

  const dayMs = 86400000;
  const startDay = startOfLocalDay(new Date(fetchedAt - (FOX_ALARM_HISTORY_DAYS - 1) * dayMs));
  const labels = [];
  const categorySeries = {};
  for (let i = 0; i < FOX_ALARM_HISTORY_DAYS; i += 1) {
    labels.push(new Date(startDay.getTime() + i * dayMs));
  }
  for (const cat of Object.keys(FOX_ALARM_CATEGORY_COLORS)) {
    categorySeries[cat] = new Array(FOX_ALARM_HISTORY_DAYS).fill(0);
  }
  for (const ev of historyEvents) {
    if (ev.action !== "raised" || !Number.isFinite(ev.t)) continue;
    const idx = Math.floor((startOfLocalDay(new Date(ev.t)).getTime() - startDay.getTime()) / dayMs);
    if (idx < 0 || idx >= FOX_ALARM_HISTORY_DAYS) continue;
    const cat = foxAlarmMeta(ev.name).category;
    categorySeries[cat][idx] += 1;
  }

  const trendGroups = Object.entries(FOX_ALARM_CATEGORY_COLORS)
    .filter(([cat]) => categorySeries[cat]?.some((v) => v > 0))
    .map(([cat, color]) => ({ label: cat, color, values: categorySeries[cat] }));

  return {
    fetchedAt,
    deviceName,
    active,
    historicalRecords,
    historyEvents,
    categorySegments: Object.entries(categoryCounts).map(([label, value]) => ({
      label,
      value,
      color: FOX_ALARM_CATEGORY_COLORS[label] || FOX_ALARM_CATEGORY_COLORS.Other,
    })),
    severitySegments: Object.entries(severityCounts)
      .filter(([, value]) => value > 0)
      .map(([label, value]) => ({
        label: label.charAt(0).toUpperCase() + label.slice(1),
        value,
        color: FOX_ALARM_SEVERITY_COLORS[label] || FOX_ALARM_SEVERITY_COLORS.warning,
      })),
    trendGroups,
    trendLabels: labels,
  };
}

async function fetchDeviceAlarmDashboard(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const alarmsId = map.inverter_alarms || map.inverter_fault_code;
  const lastId = map.inverter_alarm_last;
  if (!alarmsId && !lastId) {
    return {
      error:
        "Alarm sensors not found. Update foxess_modbus, reload the integration, then reload this panel.",
      missingEntities: true,
    };
  }

  const now = new Date();
  const start = startOfLocalDay(new Date(now.getTime() - (FOX_ALARM_HISTORY_DAYS - 1) * 86400000));
  const end = now;
  const ids = [alarmsId, lastId].filter(Boolean);
  const hist = await fetchHistoryDuring(hass, ids, start, end, { significantChangesOnly: true });
  const activeNames = alarmsId ? parseAlarmStateList(stateString(hass, alarmsId)) : [];
  const historyEvents = mergeAlarmHistoryEvents(
    lastId ? historyRowsForEntity(hist, lastId) : [],
    alarmsId ? historyRowsForEntity(hist, alarmsId) : []
  );
  return buildFoxAlarmDashboard(activeNames, historyEvents, {
    fetchedAt: Date.now(),
    deviceName: plant.title || "Device",
  });
}

function renderFoxAlarmEmptyIcon() {
  const cog = FOX_ALARM_ICONS.active_cog || "";
  if (!cog) {
    return `<svg class="fox-alarm-empty-icon" viewBox="0 0 120 100" aria-hidden="true">
<circle cx="42" cy="50" r="22" fill="none" stroke="#d9d9d9" stroke-width="6"/>
<circle cx="78" cy="50" r="22" fill="none" stroke="#b7eb8f" stroke-width="6" opacity="0.85"/>
</svg>`;
  }
  return `<div class="fox-alarm-cog-wrap" aria-hidden="true">${cog}</div>`;
}

/** Fox Cloud `#icon-empty` — Category / Severity / Trend no-data illustration. */
function renderFoxAlarmNoDataIcon() {
  let svg = FOX_ALARM_ICONS.empty || "";
  if (!svg) return "";
  if (!svg.includes("fox-alarm-icon-empty")) {
    svg = svg.replace("<svg ", '<svg class="fox-alarm-icon-empty" ');
  }
  return `<span class="fox-alarm-no-data-svg">${svg}</span>`;
}

function renderFoxAlarmMiniCard(title, bodyHtml, { wide = false } = {}) {
  return `<div class="card fox-alarm-mini-card${wide ? " fox-alarm-mini-card--wide" : ""}">
<div class="fox-alarm-mini-head"><h4 class="fox-alarm-mini-title">${esc(title)}</h4></div>
<div class="fox-alarm-mini-body">${bodyHtml}</div>
</div>`;
}

function renderFoxAlarmDonutCard(title, segments) {
  const total = segments.reduce((sum, s) => sum + (s.value || 0), 0);
  const body =
    total > 0
      ? `<div class="fox-alarm-donut-wrap">${renderEnergyDonut(segments)}</div><ul class="fox-alarm-legend">${segments
          .filter((s) => s.value > 0)
          .map(
            (s) =>
              `<li><span class="fox-alarm-legend-dot" style="background:${s.color}"></span><span>${esc(s.label)}</span><strong>${esc(String(s.value))}</strong></li>`
          )
          .join("")}</ul>`
      : `<div class="fox-alarm-no-data">${renderFoxAlarmNoDataIcon()}<span>No data</span></div>`;
  return renderFoxAlarmMiniCard(title, body);
}

function renderFoxAlarmTrendCard(groups, labels) {
  const hasData = groups.some((g) => g.values.some((v) => v > 0));
  const body = hasData
    ? renderBarChartSvg(groups, labels, { height: 180 })
    : `<div class="fox-alarm-no-data">${renderFoxAlarmNoDataIcon()}<span>No data</span></div>`;
  return renderFoxAlarmMiniCard("Trend by Category", body, { wide: true });
}

function renderFoxAlarmSeverityPill(severity) {
  const tone = FOX_ALARM_SEVERITY_COLORS[severity] ? severity : "warning";
  return `<span class="fox-alarm-severity fox-alarm-severity--${tone}">${esc(tone)}</span>`;
}

function renderFoxAlarmActiveTableRows(rows) {
  if (!rows.length) {
    return `<div class="fox-alarm-empty-list">${renderFoxAlarmEmptyIcon()}<p>No Alerts</p></div>`;
  }
  return `<div class="fox-alarm-table-wrap"><table class="fox-alarm-table"><thead><tr>
<th>Time</th><th>Alarm</th><th>Category</th><th>Severity</th><th>Status</th>
</tr></thead><tbody>${rows
    .map((row) => {
      const time = row.since ? formatFoxAlarmDateTime(row.since) : "—";
      return `<tr class="fox-alarm-row fox-alarm-row--clickable" data-action="device-alarm-detail-open" data-alarm="${esc(row.name)}" title="View troubleshooting guide">
<td>${esc(time)}</td>
<td class="fox-alarm-name-cell">${esc(row.name)}<span class="fox-alarm-row-chev" aria-hidden="true">›</span></td>
<td>${esc(row.category)}</td>
<td>${renderFoxAlarmSeverityPill(row.severity)}</td>
<td><span class="fox-alarm-status fox-alarm-status--warn">Active</span></td>
</tr>`;
    })
    .join("")}</tbody></table></div>`;
}

function renderFoxAlarmHistoricalEmpty() {
  return `<div class="fox-alarm-table-empty">${renderFoxAlarmNoDataIcon()}<span>No data</span></div>`;
}

function renderFoxAlarmHistoricalToolbar(data, { filters, timeRange }) {
  const categories = [
    ...new Set((data.historicalRecords || []).map((r) => r.category).filter(Boolean)),
  ].sort();
  const severities = ["critical", "warning", "info"];
  const devices = [...new Set((data.historicalRecords || []).map((r) => r.device).filter(Boolean))].sort();
  const mode = timeRange?.mode === "custom" ? "custom" : "24h";
  const custom = defaultAlarmCustomRangeValues();
  const startVal = timeRange?.start || custom.start;
  const endVal = timeRange?.end || custom.end;
  const catOpts = `<option value="">Category</option>${categories
    .map((c) => `<option value="${esc(c)}"${filters?.category === c ? " selected" : ""}>${esc(c)}</option>`)
    .join("")}`;
  const sevOpts = `<option value="">Severity</option>${severities
    .map(
      (s) =>
        `<option value="${esc(s)}"${filters?.severity === s ? " selected" : ""}>${esc(s.charAt(0).toUpperCase() + s.slice(1))}</option>`
    )
    .join("")}`;
  const devOpts = `<option value="">Device</option>${devices
    .map((d) => `<option value="${esc(d)}"${filters?.device === d ? " selected" : ""}>${esc(d)}</option>`)
    .join("")}`;
  return `<div class="fox-alarm-hist-toolbar">
<div class="fox-alarm-hist-filters">
<label class="fox-alarm-hist-select-wrap"><select class="fox-alarm-hist-select" data-field="device-alarm:category" aria-label="Category">${catOpts}</select></label>
<label class="fox-alarm-hist-select-wrap"><select class="fox-alarm-hist-select" data-field="device-alarm:severity" aria-label="Severity">${sevOpts}</select></label>
<label class="fox-alarm-hist-select-wrap"><select class="fox-alarm-hist-select" data-field="device-alarm:device" aria-label="Device">${devOpts}</select></label>
<button type="button" class="fox-alarm-hist-clear" data-action="device-alarm-filter-clear">Clear</button>
</div>
<div class="fox-alarm-hist-range">
<div class="fox-alarm-hist-dates${mode === "custom" ? "" : " fox-alarm-hist-dates--hidden"}">
<input type="date" class="fox-alarm-hist-date" data-field="device-alarm:range-start" value="${esc(startVal)}" aria-label="Start date"${mode === "custom" ? "" : " disabled"}>
<span class="fox-alarm-hist-date-sep" aria-hidden="true">→</span>
<input type="date" class="fox-alarm-hist-date" data-field="device-alarm:range-end" value="${esc(endVal)}" aria-label="End date"${mode === "custom" ? "" : " disabled"}>
</div>
<button type="button" class="fox-alarm-hist-range-btn${mode === "custom" ? " active" : ""}" data-action="device-alarm-range" data-range="custom">Custom</button>
<button type="button" class="fox-alarm-hist-range-btn${mode === "24h" ? " active" : ""}" data-action="device-alarm-range" data-range="24h">Last 24H</button>
</div>
</div>`;
}

function renderFoxAlarmHistoricalTableRows(rows) {
  if (!rows.length) return renderFoxAlarmHistoricalEmpty();
  return `<div class="fox-alarm-table-wrap fox-alarm-table-wrap--historical"><table class="fox-alarm-table fox-alarm-table--historical"><thead><tr>
<th>Device</th><th>Severity</th><th>Code</th><th>Message</th><th>Category</th><th>Occurrence time</th><th>Recovery time</th>
</tr></thead><tbody>${rows
    .map((row) => {
      const recovery =
        row.recoveryMs == null ? "—" : formatFoxAlarmDateTime(row.recoveryMs);
      return `<tr class="fox-alarm-row fox-alarm-row--clickable" data-action="device-alarm-detail-open" data-alarm="${esc(row.name)}" title="View troubleshooting guide">
<td>${esc(row.device)}</td>
<td>${renderFoxAlarmSeverityPill(row.severity)}</td>
<td>${esc(row.code)}</td>
<td class="fox-alarm-name-cell">${esc(row.message)}<span class="fox-alarm-row-chev" aria-hidden="true">›</span></td>
<td>${esc(row.category)}</td>
<td>${esc(formatFoxAlarmDateTime(row.occurrenceMs))}</td>
<td>${esc(recovery)}</td>
</tr>`;
    })
    .join("")}</tbody></table></div>`;
}

function renderFoxAlarmHistListContent(data, { tab, filters, timeRange }) {
  if (tab === "active") {
    return renderFoxAlarmActiveTableRows(data.active || []);
  }
  const toolbar = renderFoxAlarmHistoricalToolbar(data, { filters, timeRange });
  const body = renderFoxAlarmHistoricalTableRows(
    filterHistoricalAlarmRecords(data.historicalRecords || [], filters, timeRange)
  );
  return `${toolbar}<div data-fox-alarm-hist-body>${body}</div>`;
}

function renderFoxAlarmListSection(data, { tab, filters, timeRange }) {
  const listBody = renderFoxAlarmHistListContent(data, { tab, filters, timeRange });
  return `<div class="card fox-alarm-list-card" data-fox-alarm-list-card="1">
<div class="fox-alarm-tabs" role="tablist">
<button type="button" class="fox-alarm-tab${tab === "active" ? " active" : ""}" data-action="device-alarm-tab" data-tab="active" role="tab">Active Warning</button>
<button type="button" class="fox-alarm-tab${tab === "historical" ? " active" : ""}" data-action="device-alarm-tab" data-tab="historical" role="tab">Historical Warning</button>
</div>
<div data-fox-alarm-list-dynamic>${listBody}</div>
</div>`;
}

function renderFoxAlarmPage(data, { tab = "active", loading = false, filters = {}, timeRange = { mode: "24h" } } = {}) {
  if (loading) {
    return `<div class="fox-alarm-page"><div class="fox-alarm-head"><h2 class="fox-alarm-title">Alerts</h2></div><p class="chart-loading">Loading alarm history…</p></div>`;
  }
  if (data?.error) {
    return `<div class="fox-alarm-page"><div class="fox-alarm-head"><h2 class="fox-alarm-title">Alerts</h2></div><p class="placeholder chart-empty">${esc(data.error)}</p></div>`;
  }
  const updated = formatFoxTimeAgo(data.fetchedAt);
  return `<div class="fox-alarm-page">
<div class="fox-alarm-head">
<h2 class="fox-alarm-title">Alerts</h2>
<span class="fox-alarm-updated">${esc(updated)}</span>
</div>
<div class="fox-alarm-summary-grid">
${renderFoxAlarmDonutCard("Category", data.categorySegments)}
${renderFoxAlarmDonutCard("Severity", data.severitySegments)}
${renderFoxAlarmTrendCard(data.trendGroups, data.trendLabels)}
</div>
${renderFoxAlarmListSection(data, { tab, filters, timeRange })}
</div>`;
}

function transformPowerPoint(v, spec) {
  let x = v;
  if (spec.abs) x = Math.abs(x);
  if (spec.negate) x = -x;
  if (spec.toKw) x /= 1000;
  return x;
}

function entityValueToKw(hass, entityId, value) {
  if (!Number.isFinite(value)) return value;
  const st = hass?.states?.[entityId];
  const unit = String(st?.attributes?.unit_of_measurement || "")
    .toLowerCase()
    .replace(/\s/g, "");
  if (unit === "kw") return value;
  if (unit === "w") return value / 1000;
  if (Math.abs(value) > 500) return value / 1000;
  return value;
}

const STATISTICS_SIGNED_EPS_KW = 0.05;
/** Drop isolated 5-minute spikes not seen in neighbours (recorder glitches). */
const STATISTICS_SPIKE_MAX_DELTA_KW = 8;
const STATISTICS_Y_MAX_TICKS = 8;

function transformHistoryPoint(hass, entityId, v, spec) {
  let x = v;
  if (spec.toKw) x = entityValueToKw(hass, entityId, x);
  if (spec.splitSigned === "import") return x > STATISTICS_SIGNED_EPS_KW ? x : 0;
  if (spec.splitSigned === "export") return x < -STATISTICS_SIGNED_EPS_KW ? x : 0;
  if (spec.splitSigned === "charge") return x > STATISTICS_SIGNED_EPS_KW ? -Math.abs(x) : 0;
  if (spec.splitSigned === "discharge") return x > STATISTICS_SIGNED_EPS_KW ? Math.abs(x) : 0;
  if (spec.clampMin === 0) x = Math.max(0, x);
  if (spec.abs) x = Math.abs(x);
  if (spec.negate) x = -x;
  return x;
}

function filterStatisticsSpikes(points) {
  if (points.length < 3) return points;
  const out = [];
  for (let i = 0; i < points.length; i++) {
    const prev = points[i - 1]?.v ?? points[i].v;
    const next = points[i + 1]?.v ?? points[i].v;
    const v = points[i].v;
    const neighbour = (Math.abs(prev) + Math.abs(next)) / 2;
    const delta = Math.abs(v - prev);
    if (delta > STATISTICS_SPIKE_MAX_DELTA_KW && Math.abs(v) > neighbour * 2.5 && Math.abs(v) > 1) {
      continue;
    }
    out.push(points[i]);
  }
  return out;
}

function statisticsPointsPeakAbs(points) {
  let peak = 0;
  for (const p of points || []) {
    if (Number.isFinite(p.v)) peak = Math.max(peak, Math.abs(p.v));
  }
  return peak;
}

function getStatisticsDayRange(now = new Date()) {
  const start = startOfLocalDay(now);
  const tMin = start.getTime();
  return { tMin, tMax: tMin + 24 * 60 * 60 * 1000, nowMs: now.getTime() };
}

function getStatisticsDayRangeForDate(dayDate, { asOf = new Date() } = {}) {
  const start = startOfLocalDay(dayDate);
  const tMin = start.getTime();
  const tMax = tMin + 24 * 60 * 60 * 1000;
  const endCap = endOfLocalDay(dayDate).getTime();
  const nowMs = Math.min(asOf.getTime(), endCap, tMax);
  return { tMin, tMax, nowMs: Math.max(tMin, nowMs) };
}

function startOfWeekMonday(d) {
  const x = startOfLocalDay(d);
  const day = x.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  x.setDate(x.getDate() + diff);
  return x;
}

function roundEnergyKwh(v) {
  return Math.round(v * 100) / 100;
}

function roundEnergyPct(v) {
  return Math.round(v * 10) / 10;
}

function formatEnergyDateLabel(d) {
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${mo}-${day}`;
}

function formatEnergyRangeLabel(start, end) {
  return `${formatEnergyDateLabel(start)} ~ ${formatEnergyDateLabel(end)}`;
}

function energyPeriodBounds(period, offset = 0, now = new Date()) {
  const o = Math.max(0, Number(offset) || 0);
  if (period === "day") {
    const d = startOfLocalDay(now);
    d.setDate(d.getDate() - o);
    return { start: startOfLocalDay(d), end: endOfLocalDay(d), canNext: o > 0, canPrev: true };
  }
  if (period === "week") {
    const start = startOfWeekMonday(now);
    start.setDate(start.getDate() - o * 7);
    const end = endOfWeekSunday(start);
    return { start, end, canNext: o > 0, canPrev: true };
  }
  if (period === "month") {
    const start = new Date(now.getFullYear(), now.getMonth() - o, 1);
    const end = new Date(start.getFullYear(), start.getMonth() + 1, 0, 23, 59, 59, 999);
    return { start, end, canNext: o > 0, canPrev: true };
  }
  if (period === "year") {
    const start = new Date(now.getFullYear() - o, 0, 1);
    const end = new Date(start.getFullYear(), 11, 31, 23, 59, 59, 999);
    return { start, end, canNext: o > 0, canPrev: true };
  }
  return { start: new Date(2000, 0, 1), end: now, canNext: false, canPrev: false };
}

function energyPeriodNavLabel(period, offset = 0, now = new Date()) {
  const { start, end } = energyPeriodBounds(period, offset, now);
  if (period === "day") return formatEnergyDateLabel(start);
  if (period === "week") return formatEnergyRangeLabel(start, end);
  if (period === "month") {
    return start.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  }
  if (period === "year") return String(start.getFullYear());
  return "Total";
}

function formatDeviceCurveDateLabel(d) {
  const day = String(d.getDate()).padStart(2, "0");
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const y = d.getFullYear();
  return `${day}/${mo}/${y}`;
}

function formatDeviceShortDayMonth(d) {
  const day = String(d.getDate()).padStart(2, "0");
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  return `${day}/${mo}`;
}

function deviceNewEnergyPeriodNavLabel(period, offset = 0, now = new Date()) {
  const { start, end } = energyPeriodBounds(period, offset, now);
  if (period === "week") {
    return `${formatDeviceShortDayMonth(start)} - ${formatDeviceShortDayMonth(end)}`;
  }
  if (period === "month") {
    return start.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  }
  if (period === "year") return String(start.getFullYear());
  return "Total";
}

function energyBreakdownTitle(period, offset = 0, now = new Date()) {
  if (period === "day" && offset === 0) return "Today energy breakdown";
  return `Energy breakdown · ${energyPeriodNavLabel(period, offset, now)}`;
}

function dailyLoadKwhFromPoints(points, dayStartMs, dayEndMs) {
  const load =
    dailyMaxInRange(points.load, dayStartMs, dayEndMs) -
    dailyMaxInRange(points.discharge, dayStartMs, dayEndMs) +
    dailyMaxInRange(points.charge, dayStartMs, dayEndMs) +
    dailyMaxInRange(points.grid, dayStartMs, dayEndMs);
  return Math.max(0, load);
}

function computeEnergyBreakdown(points, dayLabels) {
  let pvTotal = 0;
  let pvToGrid = 0;
  let loadTotal = 0;
  let loadFromGrid = 0;
  let batteryCharge = 0;
  let batteryDischarge = 0;
  for (const day of dayLabels) {
    const ds = startOfLocalDay(day).getTime();
    const de = endOfLocalDay(day).getTime();
    pvTotal += dailyMaxInRange(points.pv, ds, de);
    pvToGrid += dailyMaxInRange(points.feedIn, ds, de);
    loadTotal += dailyLoadKwhFromPoints(points, ds, de);
    loadFromGrid += dailyMaxInRange(points.grid, ds, de);
    batteryCharge += dailyMaxInRange(points.charge, ds, de);
    batteryDischarge += dailyMaxInRange(points.discharge, ds, de);
  }
  const pvToLoadBattery = Math.max(0, pvTotal - pvToGrid);
  const loadFromPvBattery = Math.max(0, loadTotal - loadFromGrid);
  const selfConsumption = pvTotal > 0 ? Math.min(100, (pvToLoadBattery / pvTotal) * 100) : 0;
  const selfSufficiency = loadTotal > 0 ? Math.min(100, (loadFromPvBattery / loadTotal) * 100) : 0;
  return {
    pv_production_kwh: roundEnergyKwh(pvTotal),
    pv_to_load_battery_kwh: roundEnergyKwh(pvToLoadBattery),
    pv_to_grid_kwh: roundEnergyKwh(pvToGrid),
    load_consumption_kwh: roundEnergyKwh(loadTotal),
    load_from_pv_battery_kwh: roundEnergyKwh(loadFromPvBattery),
    load_from_grid_kwh: roundEnergyKwh(loadFromGrid),
    battery_charge_kwh: roundEnergyKwh(batteryCharge),
    battery_discharge_kwh: roundEnergyKwh(batteryDischarge),
    self_consumption_percent: roundEnergyPct(selfConsumption),
    self_sufficiency_percent: roundEnergyPct(selfSufficiency),
  };
}

function analyticsFromBreakdown(b) {
  return {
    pv_production_kwh_today: b.pv_production_kwh,
    pv_to_load_battery_kwh_today: b.pv_to_load_battery_kwh,
    pv_to_grid_kwh_today: b.pv_to_grid_kwh,
    load_consumption_kwh_today: b.load_consumption_kwh,
    load_from_pv_battery_kwh_today: b.load_from_pv_battery_kwh,
    load_from_grid_kwh_today: b.load_from_grid_kwh,
    battery_charge_kwh_today: b.battery_charge_kwh,
    battery_discharge_kwh_today: b.battery_discharge_kwh,
    self_consumption_percent_today: b.self_consumption_percent,
    self_sufficiency_percent_today: b.self_sufficiency_percent,
  };
}

function emptyEnergyBucket() {
  return {
    supply: { solar: 0, batteryDischarge: 0, gridImport: 0 },
    usage: { load: 0, batteryCharge: 0, gridExport: 0 },
  };
}

function endOfWeekSunday(mondayStart) {
  const d = new Date(mondayStart);
  d.setDate(d.getDate() + 6);
  return endOfLocalDay(d);
}

function buildFullWeekDays(weekMonday) {
  return buildDaysInRange(weekMonday, endOfWeekSunday(weekMonday));
}

function buildFullMonthDays(monthStart) {
  const last = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0);
  return buildDaysInRange(monthStart, last);
}

function daysUpToToday(days, now = new Date()) {
  const cap = startOfLocalDay(now).getTime();
  return days.filter((d) => startOfLocalDay(d).getTime() <= cap);
}

function energyBucketForDay(points, day, now = new Date()) {
  if (startOfLocalDay(day).getTime() > startOfLocalDay(now).getTime()) return emptyEnergyBucket();
  const ds = startOfLocalDay(day).getTime();
  const de = endOfLocalDay(day).getTime();
  return {
    supply: {
      solar: roundEnergyKwh(dailyMaxInRange(points.pv, ds, de)),
      batteryDischarge: roundEnergyKwh(dailyMaxInRange(points.discharge, ds, de)),
      gridImport: roundEnergyKwh(dailyMaxInRange(points.grid, ds, de)),
    },
    usage: {
      load: roundEnergyKwh(dailyLoadKwhFromPoints(points, ds, de)),
      batteryCharge: roundEnergyKwh(dailyMaxInRange(points.charge, ds, de)),
      gridExport: roundEnergyKwh(dailyMaxInRange(points.feedIn, ds, de)),
    },
  };
}

function energyBucketSum(points, days) {
  const out = {
    supply: { solar: 0, batteryDischarge: 0, gridImport: 0 },
    usage: { load: 0, batteryCharge: 0, gridExport: 0 },
  };
  for (const day of days) {
    const b = energyBucketForDay(points, day);
    for (const k of Object.keys(out.supply)) out.supply[k] += b.supply[k];
    for (const k of Object.keys(out.usage)) out.usage[k] += b.usage[k];
  }
  for (const k of Object.keys(out.supply)) out.supply[k] = roundEnergyKwh(out.supply[k]);
  for (const k of Object.keys(out.usage)) out.usage[k] = roundEnergyKwh(out.usage[k]);
  return out;
}

function buildDaysInRange(start, end) {
  const days = [];
  const cursor = startOfLocalDay(start);
  const last = startOfLocalDay(end);
  while (cursor <= last) {
    days.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

function formatWeekdayLabel(d) {
  return d.toLocaleDateString(undefined, { weekday: "short" });
}

function formatMonthShortLabel(d) {
  return d.toLocaleDateString(undefined, { month: "short" });
}

/** Bucket raw recorder points into fixed 5-minute intervals using mean (plotly-graph). */
function resamplePointsMean(points, periodMs, originMs, endMs) {
  if (!points.length) return [];
  const buckets = new Map();
  for (const p of points) {
    if (p.t < originMs || p.t > endMs) continue;
    const bucket = originMs + Math.floor((p.t - originMs) / periodMs) * periodMs;
    let entry = buckets.get(bucket);
    if (!entry) {
      entry = { sum: 0, count: 0 };
      buckets.set(bucket, entry);
    }
    entry.sum += p.v;
    entry.count += 1;
  }
  return Array.from(buckets.entries())
    .sort(([a], [b]) => a - b)
    .map(([t, { sum, count }]) => ({ t, v: sum / count }));
}

/** Split when a gap exceeds several buckets (plotly connectgaps: false). */
function splitStatisticsSegments(points, periodMs = STATISTICS_PERIOD_MS, maxGapPeriods = 4) {
  if (!points.length) return [];
  const maxGap = periodMs * maxGapPeriods;
  const segments = [];
  let current = [points[0]];
  for (let i = 1; i < points.length; i++) {
    if (points[i].t - points[i - 1].t > maxGap) {
      if (current.length) segments.push(current);
      current = [];
    }
    current.push(points[i]);
  }
  if (current.length) segments.push(current);
  return segments;
}

function isEvenlySpacedPoints(points, periodMs = STATISTICS_PERIOD_MS, toleranceMs = 90_000) {
  if (points.length < 3) return false;
  let ok = 0;
  for (let i = 1; i < points.length; i++) {
    const dt = points[i].t - points[i - 1].t;
    if (Math.abs(dt - periodMs) <= toleranceMs) ok++;
  }
  return ok / (points.length - 1) >= 0.85;
}

function smoothLinePath(pts) {
  if (!pts.length) return "";
  if (pts.length === 1) return "";
  if (pts.length === 2) {
    return `M${pts[0].x.toFixed(2)},${pts[0].y.toFixed(2)} L${pts[1].x.toFixed(2)},${pts[1].y.toFixed(2)}`;
  }
  let d = `M${pts[0].x.toFixed(2)},${pts[0].y.toFixed(2)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(i - 1, 0)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(i + 2, pts.length - 1)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C${cp1x.toFixed(2)},${cp1y.toFixed(2)} ${cp2x.toFixed(2)},${cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  }
  return d;
}

function statisticsLinePath(pixelPts, timePts) {
  if (pixelPts.length < 2) return "";
  return polylinePath(pixelPts);
}

function polylinePath(pts) {
  if (!pts.length) return "";
  let d = `M${pts[0].x.toFixed(2)},${pts[0].y.toFixed(2)}`;
  for (let i = 1; i < pts.length; i++) {
    d += ` L${pts[i].x.toFixed(2)},${pts[i].y.toFixed(2)}`;
  }
  return d;
}

function statisticsChartPoints(points, range) {
  return resamplePointsMean(points, STATISTICS_PERIOD_MS, range.tMin, range.nowMs);
}

function interpolateSeriesAt(points, t, { allowBackfill = true } = {}) {
  if (!points.length) return null;
  if (t <= points[0].t) return allowBackfill ? points[0].v : null;
  if (t >= points[points.length - 1].t) return points[points.length - 1].v;
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    if (t >= a.t && t <= b.t) {
      const f = b.t === a.t ? 0 : (t - a.t) / (b.t - a.t);
      return a.v + (b.v - a.v) * f;
    }
  }
  return null;
}

function formatStatisticsHoverTime(ms) {
  const d = new Date(ms);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${mo}-${day} ${h}:${m}`;
}

function formatStatisticsKw(v) {
  return Number.isFinite(v) ? `${v.toFixed(3)} kW` : "—";
}

function fillToZeroPath(pts, yZero, timePts) {
  if (!pts.length) return "";
  const line = statisticsLinePath(pts, timePts);
  if (!line) return "";
  const last = pts[pts.length - 1];
  const first = pts[0];
  return `${line} L${last.x.toFixed(2)},${yZero.toFixed(2)} L${first.x.toFixed(2)},${yZero.toFixed(2)} Z`;
}

function statisticsPercentile(sorted, p) {
  if (!sorted.length) return 0;
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

function statisticsYTickStep(span, maxTicks = STATISTICS_Y_MAX_TICKS) {
  const rough = Math.max(span / maxTicks, 0.1);
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const norm = rough / magnitude;
  let nice;
  if (norm <= 1) nice = 1;
  else if (norm <= 2) nice = 2;
  else if (norm <= 5) nice = 5;
  else nice = 10;
  return nice * magnitude;
}

function computeStatisticsYDomain(series, padRatio = 0.08) {
  const raw = [];
  for (const s of series) {
    for (const p of s.points || []) {
      if (Number.isFinite(p.v)) raw.push(p.v);
    }
  }
  if (!raw.length) return snapStatisticsYDomain(0, 0.25);

  const plausible = raw.filter((v) => Math.abs(v) <= 25);
  const forScale =
    plausible.length >= Math.max(3, Math.floor(raw.length * 0.1)) ? plausible : raw;
  let yMin = Math.min(...forScale);
  let yMax = Math.max(...forScale);
  if (yMin < 0 && yMax > 0) {
    /* signed power chart — keep zero visible */
  } else if (yMin >= 0) {
    yMin = 0;
  }
  if (yMax <= yMin) yMax = yMin + Math.max(Math.abs(yMin) * 0.15, 0.5);
  const pad = Math.max((yMax - yMin) * padRatio, 0.05);
  return snapStatisticsYDomain(yMin - pad, yMax + pad);
}

/** Snap Y axis to 0.5 kW ticks; widen step when range is large (Overview statistics). */
function snapStatisticsYDomain(yMin, yMax) {
  const span = Math.max(yMax - yMin, 0.25);
  let step = STATISTICS_CHART_LAYOUT.yTickStepKw;
  if (span / step > STATISTICS_Y_MAX_TICKS) {
    step = statisticsYTickStep(span, STATISTICS_Y_MAX_TICKS);
  }
  let lo = Math.floor(yMin / step) * step;
  let hi = Math.ceil(yMax / step) * step;
  if (hi - lo < step * 2) {
    lo -= step;
    hi += step;
  }
  return { yMin: lo, yMax: hi, step };
}

function statisticsYTicks(yMin, yMax, step) {
  const tickStep =
    step ||
    (() => {
      const span = Math.max(yMax - yMin, 0.25);
      let s = STATISTICS_CHART_LAYOUT.yTickStepKw;
      if (span / s > STATISTICS_Y_MAX_TICKS) s = statisticsYTickStep(span, STATISTICS_Y_MAX_TICKS);
      return s;
    })();
  const ticks = [];
  const start = Math.floor(yMin / tickStep) * tickStep;
  for (let v = start; v <= yMax + tickStep * 0.001; v += tickStep) {
    if (v >= yMin - tickStep * 0.001) {
      const rounded = Math.round(v / tickStep) * tickStep;
      ticks.push(Math.abs(tickStep - 0.5) < 0.001 ? Math.round(rounded * 2) / 2 : rounded);
    }
  }
  return ticks;
}

function formatStatisticsYTick(v) {
  const r = Math.round(v * 2) / 2;
  return Number.isInteger(r) ? String(r) : r.toFixed(1);
}

/** Map screen coords to viewBox when SVG uses meet or slice scaling. */
function statisticsPointerScale(svg) {
  const rect = svg.getBoundingClientRect();
  const vb = svg.viewBox.baseVal;
  const par = svg.getAttribute("preserveAspectRatio") || "xMidYMid meet";
  const slice = par.includes("slice");
  const scale = slice
    ? Math.max(rect.width / vb.width, rect.height / vb.height)
    : Math.min(rect.width / vb.width, rect.height / vb.height);
  const renderedW = vb.width * scale;
  const renderedH = vb.height * scale;
  return {
    scale,
    offsetX: (rect.width - renderedW) / 2,
    offsetY: (rect.height - renderedH) / 2,
    vb,
  };
}

function syncStatisticsSideLegendOffset(wrap) {
  if (!wrap?.classList?.contains("statistics-chart-wrap--soc")) return;
  const plot = wrap.querySelector(".statistics-chart-plot");
  const legend = wrap.querySelector(".statistics-chart-legend-side");
  const svg = plot?.querySelector(".statistics-chart-svg");
  if (!plot || !legend || !svg) return;
  const sideBySide = getComputedStyle(wrap).gridTemplateColumns.includes(" ");
  if (!sideBySide) {
    legend.style.paddingTop = "";
    return;
  }
  const padT = Number(plot.dataset.padT);
  if (!Number.isFinite(padT)) return;
  const { scale, offsetY } = statisticsPointerScale(svg);
  const tickY = offsetY + (padT + 4) * scale;
  const firstRow = legend.querySelector(".statistics-legend-item--side");
  const rowH = firstRow?.getBoundingClientRect().height || 16;
  legend.style.paddingTop = `${Math.max(0, Math.round(tickY - rowH / 2))}px`;
}

function statisticsClientToTime(svg, clientX, padL, plotW, tMin, daySpan) {
  const rect = svg.getBoundingClientRect();
  const { scale, offsetX } = statisticsPointerScale(svg);
  const relX = (clientX - rect.left - offsetX) / scale - padL;
  const frac = Math.max(0, Math.min(1, relX / plotW));
  return tMin + frac * daySpan;
}

const STATISTICS_TOOLTIP_LABEL_BY_ID = {
  battery_charge: "Battery charging",
  battery_discharge: "Battery discharging",
  grid_import: "Grid import",
  grid_export: "Grid export",
};

function statisticsSeriesTooltipLabel(s) {
  if (s.tooltipLabel) return s.tooltipLabel;
  if (s.id && STATISTICS_TOOLTIP_LABEL_BY_ID[s.id]) return STATISTICS_TOOLTIP_LABEL_BY_ID[s.id];
  return s.label;
}

/** Hover tooltip: every series (charging, discharging, import, export, …). */
function statisticsTooltipRowsHtml(seriesMeta, t, hiddenGroups) {
  return seriesMeta
    .map((s) => {
      const g = s.legendGroup;
      if (g && hiddenGroups.has(g)) return "";
      const v = interpolateSeriesAt(s.points, t);
      if (v == null) return "";
      const label = statisticsSeriesTooltipLabel(s);
      if (s.yAxis === "soc") {
        return `<div class="statistics-tooltip-row"><span class="statistics-tooltip-label"><i class="statistics-tooltip-swatch" style="background:${esc(s.color)}"></i>${esc(label)}</span><strong>${esc(formatSocPercent(v))}</strong></div>`;
      }
      if (Math.abs(v) < 0.001 && !s.showZeroInTooltip) return "";
      return `<div class="statistics-tooltip-row"><span class="statistics-tooltip-label"><i class="statistics-tooltip-swatch" style="background:${esc(s.color)}"></i>${esc(label)}</span><strong>${formatStatisticsKw(v)}</strong></div>`;
    })
    .filter(Boolean)
    .join("");
}

function dailyMaxInRange(points, dayStartMs, dayEndMs) {
  let max = 0;
  for (const p of points) {
    if (p.t >= dayStartMs && p.t <= dayEndMs) max = Math.max(max, p.v);
  }
  return max;
}

function statisticsPointsHaveSignal(points) {
  return (points || []).some((p) => Math.abs(p.v) > STATISTICS_SIGNED_EPS_KW);
}

function chartEntityCandidates(hass, map, key) {
  const suffixes = CHART_ENTITY_FALLBACKS[key] || DEVICE_ENTITY_FALLBACKS[key] || [];
  const seen = new Set();
  const out = [];
  const primary = map?.[key];
  if (primary && entityIdMatchesChartSuffixes(primary, suffixes)) {
    seen.add(primary);
    out.push(primary);
  }
  if (!hass?.states) return out;
  for (const suffix of suffixes) {
    for (const id of Object.keys(hass.states)) {
      if (!seen.has(id) && entityIdMatchesSuffix(id, suffix)) {
        seen.add(id);
        out.push(id);
      }
    }
  }
  return out;
}

function entityIdMatchesChartSuffixes(entityId, suffixes) {
  return (suffixes || []).some((suffix) => entityIdMatchesSuffix(entityId, suffix));
}

function buildChartSeriesPointsWithFallback(hass, map, key, spec, range, statsMap, hist) {
  const candidates = chartEntityCandidates(hass, map, key);
  let best = [];
  let bestId = candidates[0] || null;
  for (const entityId of candidates) {
    const pts = buildStatisticsSeriesPoints(hass, entityId, spec, range, statsMap, hist);
    if (statisticsPointsHaveSignal(pts)) {
      return { entityId, points: pts };
    }
    if (pts.length > best.length) {
      best = pts;
      bestId = entityId;
    }
  }
  return { entityId: bestId, points: best };
}

/** Fill every 5-minute bucket so idle series draw a flat zero line, not isolated blobs. */
function densifyStatisticsPoints(points, range) {
  const period = STATISTICS_PERIOD_MS;
  const byTime = new Map();
  for (const p of points || []) {
    if (!Number.isFinite(p.t)) continue;
    const bucket = range.tMin + Math.floor((p.t - range.tMin) / period) * period;
    byTime.set(bucket, p.v);
  }
  const out = [];
  for (let t = range.tMin; t <= range.nowMs; t += period) {
    out.push({ t, v: byTime.has(t) ? byTime.get(t) : 0 });
  }
  return out.length ? out : [...(points || [])];
}

function finalizeStatisticsChartSeries(series, range) {
  return series.map((s) => ({
    ...s,
    connectGaps: true,
    points: densifyStatisticsPoints(s.points, range),
  }));
}

/** Device real-time curve: densify idle series so EPS/grid-style lines sit on zero, not blobs. */
function finalizeDeviceRealtimeChartSeries(series, range) {
  return series.map((s) => {
    const densify = s.densify === true || seriesHasLargeGaps(s.points);
    return {
      ...s,
      connectGaps: true,
      points: densify ? densifyStatisticsPoints(s.points, range) : s.points,
    };
  });
}

function seriesHasLargeGaps(points, periodMs = STATISTICS_PERIOD_MS, maxGapPeriods = 4) {
  if (!points?.length) return true;
  if (points.length < 2) return true;
  const maxGap = periodMs * maxGapPeriods;
  for (let i = 1; i < points.length; i++) {
    if (points[i].t - points[i - 1].t > maxGap) return true;
  }
  return false;
}

function statisticsRawPointsForEntity(hass, entityId, range, statsMap, hist, options = {}) {
  const statRows = statsMap?.[entityId];
  let statPoints = [];
  if (statRows?.length) {
    statPoints = recorderStatsToPoints(statRows, range);
  }
  if (options.statisticsOnly) {
    if (statPoints.length >= 2) return statPoints;
    const histPts = historyToPoints(historyRowsForEntity(hist, entityId));
    if (histPts.length) {
      return statisticsChartPoints(histPts, range);
    }
    return statPoints;
  }
  const histPoints = statisticsChartPoints(
    historyToPoints(historyRowsForEntity(hist, entityId)),
    range
  );
  const scaledStatPeak = statisticsPointsPeakAbs(
    statPoints.map((p) => ({ v: entityValueToKw(hass, entityId, p.v) }))
  );
  const scaledHistPeak = statisticsPointsPeakAbs(
    histPoints.map((p) => ({ v: entityValueToKw(hass, entityId, p.v) }))
  );
  const liveKw = Math.abs(entityValueToKw(hass, entityId, stateNumber(hass, entityId)));
  if (options.preferHistory && histPoints.length) {
    if (scaledStatPeak > Math.max(liveKw * 15 + 0.25, 5) && scaledHistPeak <= scaledStatPeak) {
      return histPoints;
    }
    if (!statPoints.length || scaledHistPeak <= scaledStatPeak) {
      return histPoints;
    }
  }
  if (statPoints.length && histPoints.length) {
    if (scaledHistPeak > 0 && scaledStatPeak > Math.max(scaledHistPeak * 4, 5)) {
      return histPoints;
    }
    if (scaledStatPeak > Math.max(liveKw * 15 + 0.25, 5)) {
      return histPoints;
    }
  }
  if (statPoints.length && (statisticsPointsHaveSignal(statPoints) || !histPoints.length)) {
    return statPoints;
  }
  return histPoints.length ? histPoints : statPoints;
}

function buildStatisticsSeriesPoints(hass, entityId, spec, range, statsMap, hist) {
  const rawPoints = statisticsRawPointsForEntity(hass, entityId, range, statsMap, hist, {
    preferHistory: spec.preferHistory === true,
    statisticsOnly: spec.statisticsOnly === true,
  });
  const transformed = rawPoints.map((p) => ({
    t: p.t,
    v: transformHistoryPoint(hass, entityId, p.v, spec),
  }));
  return spec.statisticsOnly ? transformed : filterStatisticsSpikes(transformed);
}

function interpolatePointsToPeriod(points, periodMs, originMs, endMs, { allowBackfill = true } = {}) {
  if (!points.length) return [];
  const sorted = [...points].sort((a, b) => a.t - b.t);
  const out = [];
  for (let t = originMs; t <= endMs; t += periodMs) {
    const v = interpolateSeriesAt(sorted, t, { allowBackfill });
    if (v != null) out.push({ t, v });
  }
  return out;
}

function clampSocPercent(v) {
  if (!Number.isFinite(v)) return null;
  return Math.min(100, Math.max(0, Number(v)));
}

function buildSocHistoryPoints(hass, entityId, range, statsMap, hist) {
  const rawPoints = statisticsRawPointsForEntity(hass, entityId, range, statsMap, hist);
  return rawPoints
    .map((p) => ({ t: p.t, v: clampSocPercent(p.v) }))
    .filter((p) => p.v != null);
}

function buildSocPowerPoints(hass, entityId, range, statsMap, hist) {
  const spec = { toKw: true };
  const rawPoints = statisticsRawPointsForEntity(hass, entityId, range, statsMap, hist).map((p) => ({
    t: p.t,
    v: transformHistoryPoint(hass, entityId, p.v, spec),
  }));
  return rawPoints
    .map((p) => ({ t: p.t, v: Math.abs(p.v) }))
    .filter((p) => Number.isFinite(p.v));
}

function peakBatteryPowerAt(t, pts, radiusMs = BATTERY_SOC_POWER_SMOOTH_MS) {
  if (!pts?.length) return 0;
  let peak = 0;
  for (let dt = -radiusMs; dt <= radiusMs; dt += STATISTICS_PERIOD_MS) {
    peak = Math.max(peak, Math.abs(interpolateSeriesAt(pts, t + dt) ?? 0));
  }
  return peak;
}

function socDeltaOverWindow(t, socPts, halfWindowMs = BATTERY_SOC_SLOPE_WINDOW_MS / 2) {
  if (!socPts?.length) return null;
  const v0 = interpolateSeriesAt(socPts, t - halfWindowMs);
  const v1 = interpolateSeriesAt(socPts, t + halfWindowMs);
  if (v0 == null || v1 == null) return null;
  return v1 - v0;
}

function batteryFlowModeAt(t, chargePts, dischargePts, socPts) {
  const ch = peakBatteryPowerAt(t, chargePts);
  const dis = peakBatteryPowerAt(t, dischargePts);
  if (ch > BATTERY_SOC_POWER_THRESHOLD_KW) return "charging";
  if (dis > BATTERY_SOC_POWER_THRESHOLD_KW) {
    const soc = interpolateSeriesAt(socPts, t);
    const delta = socDeltaOverWindow(t, socPts);
    if (
      soc != null &&
      soc >= BATTERY_SOC_FULL_PCT &&
      delta != null &&
      Math.abs(delta) < BATTERY_SOC_SLOPE_DELTA_PCT
    ) {
      return "idle";
    }
    return "discharging";
  }
  const delta = socDeltaOverWindow(t, socPts);
  if (delta != null && Math.abs(delta) >= BATTERY_SOC_SLOPE_DELTA_PCT) {
    return delta > 0 ? "charging" : "discharging";
  }
  return "idle";
}

function splitSocSegmentsByMode(socPts, chargePts, dischargePts) {
  if (socPts.length < 2) return socPts.length ? [{ mode: "idle", pts: socPts }] : [];
  const segments = [];
  let mode = batteryFlowModeAt(socPts[0].t, chargePts, dischargePts, socPts);
  let pts = [socPts[0]];
  for (let i = 1; i < socPts.length; i++) {
    const p = socPts[i];
    const nextMode = batteryFlowModeAt(p.t, chargePts, dischargePts, socPts);
    if (nextMode !== mode) {
      if (pts.length >= 2) segments.push({ mode, pts });
      mode = nextMode;
      pts = [socPts[i - 1], p];
    } else {
      pts.push(p);
    }
  }
  if (pts.length >= 2) segments.push({ mode, pts });
  return segments;
}

function buildSocActivityBars(chargePts, dischargePts, range) {
  const bars = [];
  for (let t = range.tMin; t <= range.nowMs; t += STATISTICS_PERIOD_MS) {
    const ch = peakBatteryPowerAt(t, chargePts);
    const dis = peakBatteryPowerAt(t, dischargePts);
    if (ch > BATTERY_SOC_POWER_THRESHOLD_KW) {
      bars.push({ t, mode: "charging", intensity: Math.min(1, ch / 4) });
    } else if (dis > BATTERY_SOC_POWER_THRESHOLD_KW) {
      bars.push({ t, mode: "discharging", intensity: Math.min(1, dis / 4) });
    }
  }
  return bars;
}

function formatSocPercent(v) {
  return Number.isFinite(v) ? `${Math.round(v)}%` : "—";
}

function readLiveBatterySoc(hass, plant, plantState) {
  const entityId = resolveEntityMap(hass, plant, plantState).battery_soc;
  if (!entityId || !hass?.states?.[entityId]) return null;
  const st = hass.states[entityId];
  if (st.state === "unavailable" || st.state === "unknown" || st.state === "") return null;
  const n = parseFloat(st.state);
  if (!Number.isFinite(n)) return null;
  return clampSocPercent(n);
}

function resolveBatterySocDisplay(hass, plant, plantState, chart) {
  const live = readLiveBatterySoc(hass, plant, plantState);
  if (live != null) return live;
  const { socPts, range } = chart || {};
  if (!socPts?.length) return null;
  const atNow = clampSocPercent(interpolateSeriesAt(socPts, range?.nowMs ?? Date.now()));
  if (atNow != null) return atNow;
  return clampSocPercent(socPts[socPts.length - 1]?.v);
}

function fillSocAreaPath(pts, yBase) {
  if (pts.length < 2) return "";
  const line = statisticsLinePath(pts, pts.map((p) => ({ t: p.t })));
  if (!line) return "";
  const last = pts[pts.length - 1];
  const first = pts[0];
  return `${line} L${last.x.toFixed(2)},${yBase.toFixed(2)} L${first.x.toFixed(2)},${yBase.toFixed(2)} Z`;
}

async function fetchBatterySocChartSeries(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const socId = map.battery_soc;
  const chargeId = map.battery_charge;
  const dischargeId = map.battery_discharge;
  if (!socId) {
    return { empty: "Map battery SOC in FoxESS Modbus, then reload FoxESS Plant." };
  }
  const now = new Date();
  const start = startOfLocalDay(now);
  const range = getStatisticsDayRange(now);
  const entityIds = [socId, chargeId, dischargeId].filter(Boolean);
  const [statsMap, hist] = await Promise.all([
    fetchStatisticsDuring(hass, entityIds, start, now),
    fetchHistoryDuring(hass, entityIds, start, now),
  ]);
  const socPts = buildSocHistoryPoints(hass, socId, range, statsMap, hist);
  if (!socPts.length) {
    return {
      empty: `No SOC history for ${socId}. Enable the Recorder for battery_soc (5-minute statistics or state history).`,
    };
  }
  const chargePts = chargeId ? buildSocPowerPoints(hass, chargeId, range, statsMap, hist) : [];
  const dischargePts = dischargeId ? buildSocPowerPoints(hass, dischargeId, range, statsMap, hist) : [];
  return {
    range,
    socPts,
    chargePts,
    dischargePts,
    segments: splitSocSegmentsByMode(socPts, chargePts, dischargePts),
    activityBars: buildSocActivityBars(chargePts, dischargePts, range),
  };
}

function renderBatterySocChartHtml(chart, liveSocPct) {
  if (!chart?.range || !chart?.socPts?.length) {
    return `<p class="placeholder chart-empty">No battery SOC history for today yet.</p>`;
  }
  const { socPts, segments, activityBars, range } = chart;
  const { width, height, pad, xTickHours, xTickCount, yTicks } = BATTERY_SOC_CHART_LAYOUT;
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const { tMin, tMax, nowMs } = range;
  const daySpan = tMax - tMin;
  const xScale = (t) => pad.l + ((t - tMin) / daySpan) * w;
  const yScale = (v) => pad.t + h - (v / 100) * h;
  const yBase = yScale(0);
  const displaySoc =
    liveSocPct != null ? liveSocPct : clampSocPercent(socPts[socPts.length - 1]?.v);
  const slotW = (w / (Math.ceil((range.nowMs - range.tMin) / STATISTICS_PERIOD_MS) || 1)) * 0.85;

  const grid = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${pad.l + w}" y2="${y.toFixed(1)}" class="soc-chart-grid"/>`;
    })
    .join("");

  const yLabels = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<text x="${(pad.l - 8).toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="end" class="soc-chart-axis-y">${yv}%</text>`;
    })
    .join("");

  const xTickSet = new Set(
    Array.from({ length: xTickCount }, (_, i) => tMin + i * xTickHours * 60 * 60 * 1000)
  );
  const xLabels = [];
  for (const xt of xTickSet) {
    const x = xScale(xt);
    xLabels.push(
      `<text x="${x.toFixed(1)}" y="${height - pad.b + 18}" text-anchor="middle" class="soc-chart-axis-x">${esc(formatChartTimeLabel(xt))}</text>`
    );
  }
  const nowX = xScale(nowMs);
  xLabels.push(
    `<line x1="${nowX.toFixed(1)}" y1="${pad.t}" x2="${nowX.toFixed(1)}" y2="${pad.t + h}" class="soc-chart-now-line"/>`
  );

  const activityRects = (activityBars || [])
    .map((bar) => {
      const cx = xScale(bar.t + STATISTICS_PERIOD_MS / 2);
      const barH = 8 + bar.intensity * 22;
      const fill =
        bar.mode === "charging"
          ? "rgba(61,220,132,0.12)"
          : "rgba(91,155,213,0.12)";
      return `<rect x="${(cx - slotW / 2).toFixed(2)}" y="${(yBase - barH).toFixed(2)}" width="${slotW.toFixed(2)}" height="${barH.toFixed(2)}" fill="${fill}" rx="1"/>`;
    })
    .join("");

  const fills = (segments || [])
    .map((seg) => {
      const colors = BATTERY_SOC_COLORS[seg.mode] || BATTERY_SOC_COLORS.idle;
      const pixelPts = seg.pts.map((p) => ({
        x: xScale(p.t),
        y: yScale(p.v),
        t: p.t,
        v: p.v,
      }));
      if (pixelPts.length < 2) return "";
      return `<path class="soc-chart-fill" d="${fillSocAreaPath(pixelPts, yBase)}" fill="${colors.fill}" stroke="none"/>`;
    })
    .join("");

  const lines = (segments || [])
    .map((seg) => {
      const colors = BATTERY_SOC_COLORS[seg.mode] || BATTERY_SOC_COLORS.idle;
      const pixelPts = seg.pts.map((p) => ({
        x: xScale(p.t),
        y: yScale(p.v),
        t: p.t,
        v: p.v,
      }));
      if (pixelPts.length < 2) return "";
      return `<path class="soc-chart-line" d="${statisticsLinePath(pixelPts, seg.pts)}" fill="none" stroke="${colors.line}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>`;
    })
    .join("");

  return `<div class="soc-chart-wrap" data-soc-chart="1">
<div class="soc-chart-head">
<div class="soc-chart-value">${esc(formatSocPercent(displaySoc))}</div>
<div class="soc-chart-legend" aria-hidden="true">
<span class="soc-chart-legend-item"><i style="background:${BATTERY_SOC_COLORS.charging.line}"></i>Charging</span>
<span class="soc-chart-legend-item"><i style="background:${BATTERY_SOC_COLORS.discharging.line}"></i>Discharging</span>
</div>
</div>
<div class="soc-chart-plot" data-pad-l="${pad.l}" data-pad-t="${pad.t}" data-pad-b="${pad.b}" data-plot-w="${w}" data-plot-h="${h}" data-t-min="${tMin}" data-t-max="${tMax}" data-now-ms="${nowMs}">
<svg class="soc-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Battery state of charge chart">
${grid}
${yLabels}
${activityRects}
${fills}
${lines}
${xLabels.join("")}
</svg>
<div class="soc-chart-hit" aria-hidden="true"></div>
<div class="soc-chart-crosshair" hidden><div class="soc-chart-spike"></div></div>
<div class="soc-chart-tooltip" hidden role="tooltip"></div>
</div>
</div>`;
}

function bindBatterySocChart(root, chart) {
  const wrap = root?.querySelector?.("[data-soc-chart]");
  if (!wrap || wrap.dataset.bound || !chart?.socPts?.length) return;
  const plot = wrap.querySelector(".soc-chart-plot");
  if (!plot) return;
  wrap.dataset.bound = "1";

  const padL = Number(plot.dataset.padL);
  const padT = Number(plot.dataset.padT);
  const padB = Number(plot.dataset.padB);
  const plotW = Number(plot.dataset.plotW);
  const tMin = Number(plot.dataset.tMin);
  const tMax = Number(plot.dataset.tMax);
  const daySpan = tMax - tMin;
  const svg = plot.querySelector(".soc-chart-svg");
  const hit = plot.querySelector(".soc-chart-hit");
  const crosshair = plot.querySelector(".soc-chart-crosshair");
  const tooltip = plot.querySelector(".soc-chart-tooltip");

  const showHover = (clientX) => {
    const t = Math.min(statisticsClientToTime(svg, clientX, padL, plotW, tMin, daySpan), tMax);
    const { scale, offsetX, offsetY } = statisticsPointerScale(svg);
    const xPx = padL + ((t - tMin) / daySpan) * plotW;
    const screenX = offsetX + xPx * scale;
    crosshair.hidden = false;
    crosshair.style.left = `${screenX}px`;
    crosshair.style.top = `${offsetY + padT * scale}px`;
    crosshair.style.bottom = `${offsetY + padB * scale}px`;

    const soc = clampSocPercent(interpolateSeriesAt(chart.socPts, t));
    const mode = batteryFlowModeAt(t, chart.chargePts, chart.dischargePts, chart.socPts);
    const modeLabel =
      mode === "charging" ? "Charging" : mode === "discharging" ? "Discharging" : "Idle";
    const modeColor = (BATTERY_SOC_COLORS[mode] || BATTERY_SOC_COLORS.idle).line;
    tooltip.hidden = false;
    tooltip.innerHTML = `<div class="soc-chart-tooltip-time">${esc(formatStatisticsHoverTime(t))}</div>
<div class="soc-chart-tooltip-row"><span class="soc-chart-tooltip-label"><i class="soc-chart-tooltip-swatch" style="background:${modeColor}"></i>${esc(modeLabel)}</span><strong>${esc(formatSocPercent(soc))}</strong></div>`;
    const plotRect = plot.getBoundingClientRect();
    let left = screenX + 12;
    if (left + 180 > plotRect.width) left = screenX - 192;
    tooltip.style.left = `${Math.max(8, left)}px`;
    tooltip.style.top = "8px";
  };

  const hideHover = () => {
    crosshair.hidden = true;
    tooltip.hidden = true;
  };

  hit?.addEventListener("mousemove", (ev) => showHover(ev.clientX));
  hit?.addEventListener("mouseleave", hideHover);
  bindTouchChartScrub(hit, showHover, hideHover);
}

async function fetchStatisticsChartSeries(hass, plant, plantState, { dayOffset = 0 } = {}) {
  const map = resolveEntityMap(hass, plant, plantState);
  const specs = STATISTICS_CHART_SERIES.map((s) => {
    const candidates = chartEntityCandidates(hass, map, s.key);
    return { ...s, entity_id: candidates[0] || null };
  }).filter((s) => s.entity_id);
  if (!specs.length) {
    return { empty: "Map power entities in FoxESS Modbus, then reload FoxESS Plant." };
  }
  let forecastState = plantState;
  if (dayOffset === 0) {
    try {
      const fresh = await fetchPlantState(hass, plant.entry_id);
      if (fresh) forecastState = fresh;
    } catch {
      /* plant_state optional */
    }
  }
  const now = new Date();
  const day = startOfLocalDay(now);
  day.setDate(day.getDate() - Math.max(0, dayOffset));
  const range = getStatisticsDayRangeForDate(day, { asOf: dayOffset === 0 ? now : endOfLocalDay(day) });
  const fetchEnd = new Date(range.nowMs);
  const start = new Date(range.tMin);
  const socId = map.battery_soc;
  const entityIds = [
    ...new Set(
      [...specs.flatMap((s) => chartEntityCandidates(hass, map, s.key)), socId].filter(Boolean)
    ),
  ];
  const [statsMap, hist] = await Promise.all([
    fetchStatisticsDuring(hass, entityIds, start, fetchEnd),
    fetchHistoryDuring(hass, entityIds, start, fetchEnd),
  ]);
  let series = finalizeStatisticsChartSeries(
    specs.map((spec) => {
      const built = buildChartSeriesPointsWithFallback(hass, map, spec.key, spec, range, statsMap, hist);
      return {
        id: spec.key,
        label: spec.label,
        tooltipLabel: spec.tooltipLabel,
        legendGroup: spec.legendGroup,
        color: spec.color,
        fill: spec.fill,
        fillColor: spec.fillColor,
        hideLegend: spec.hideLegend,
        lineWidth: spec.lineWidth,
        showZeroInTooltip: spec.showZeroInTooltip,
        entity_id: built.entityId,
        points: built.points,
      };
    }),
    range
  );
  let socSeries = null;
  if (socId) {
    const socPoints = buildSocHistoryPoints(hass, socId, range, statsMap, hist);
    if (socPoints.length) {
      socSeries = {
        id: "battery_soc",
        label: "SoC",
        tooltipLabel: "SoC",
        legendGroup: "soc",
        yAxis: "soc",
        color: STATISTICS_SOC_COLOR,
        connectGaps: true,
        lineWidth: 1.6,
        points: socPoints,
      };
    }
  }
  if (dayOffset === 0) {
    let serverForecastPoints = [];
    try {
      serverForecastPoints = await fetchSolcastStatisticsForecastPoints(hass, plant);
    } catch {
      serverForecastPoints = [];
    }
    const fPoints = buildStatisticsForecastPoints(
      range,
      forecastState,
      forecastState,
      hass,
      serverForecastPoints
    );
    if (fPoints.length >= 2) {
      series.push({
        id: "forecast",
        ...FORECAST_CHART_STYLE,
        connectGaps: true,
        points: fPoints,
      });
    }
    return { series, socSeries, range, forecastState, dayOffset, serverForecastPoints };
  } else {
    const fPoints = await fetchHistoricalSolcastForecastPoints(hass, plant, dayOffset);
    const inRange = fPoints.filter((p) => p.t >= range.tMin && p.t <= range.tMax);
    if (inRange.length >= 2) {
      series.push({
        id: "forecast",
        ...FORECAST_CHART_STYLE,
        connectGaps: true,
        points: inRange,
      });
    }
  }
  if (!series.some((s) => s.points.length)) {
    const listed = specs.map((s) => s.entity_id).join(", ");
    return {
      empty: `No statistics for: ${listed}. Confirm the Recorder stores 5-minute means for these entities (same as your Lovelace plotly-graph card).`,
      dayOffset,
    };
  }
  return { series, socSeries, range, forecastState, dayOffset, serverForecastPoints: null };
}

function buildDailyLabels(startDay, count) {
  const labels = [];
  for (let i = 0; i < count; i++) {
    const d = new Date(startDay);
    d.setDate(d.getDate() + i);
    labels.push(d);
  }
  return labels;
}

function buildLastNDays(count = OVERVIEW_DAILY_DAYS) {
  const labels = [];
  const anchor = startOfLocalDay(new Date());
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(anchor);
    d.setDate(d.getDate() - i);
    labels.push(d);
  }
  return labels;
}

function formatDailyKwh(value) {
  if (value == null || !Number.isFinite(Number(value))) return "— kWh";
  return `${Number(value).toFixed(2)} kWh`;
}

function dailyProductionKwh(points, dayStartMs, dayEndMs) {
  return Math.round(dailyMaxInRange(points.pv, dayStartMs, dayEndMs) * 100) / 100;
}

function dailyConsumptionKwh(points, dayStartMs, dayEndMs) {
  const load =
    dailyMaxInRange(points.load, dayStartMs, dayEndMs) -
    dailyMaxInRange(points.discharge, dayStartMs, dayEndMs) +
    dailyMaxInRange(points.charge, dayStartMs, dayEndMs) +
    dailyMaxInRange(points.grid, dayStartMs, dayEndMs);
  return Math.round(Math.max(0, load) * 100) / 100;
}

function renderOverviewDailySparklineSvg(values, labels, accentColor) {
  const n = Math.min(values.length, labels.length);
  if (!n) return "";
  const width = 156;
  const height = 54;
  const pad = { l: 6, r: 6, t: 14, b: 12 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const dayFont = 6;
  const todayFont = 5.5;
  let yMax = 0.1;
  for (let i = 0; i < n; i++) yMax = Math.max(yMax, values[i] || 0);
  yMax *= 1.1;
  const slotW = w / n;
  const barW = Math.min(11, slotW * 0.52);
  const todayIdx = n - 1;
  const parts = [];
  const hits = [];
  for (let i = 0; i < n; i++) {
    const v = values[i] || 0;
    const cx = pad.l + i * slotW + slotW / 2;
    const bh = Math.max(2, (v / yMax) * h);
    const x = cx - barW / 2;
    const y = pad.t + h - bh;
    const fill = i === todayIdx ? accentColor : OVERVIEW_DAILY_COLORS.barMuted;
    const tip = formatDailyKwh(v);
    parts.push(
      `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${fill}"/>`
    );
    if (i === todayIdx) {
      parts.push(
        `<text x="${cx.toFixed(1)}" y="8" text-anchor="middle" class="overview-daily-today-mark" font-size="${todayFont}">Today</text>`
      );
      parts.push(
        `<line x1="${cx.toFixed(1)}" y1="9.5" x2="${cx.toFixed(1)}" y2="${(y - 1).toFixed(1)}" class="overview-daily-today-line"/>`
      );
    }
    parts.push(
      `<text x="${cx.toFixed(1)}" y="${(height - 4).toFixed(1)}" text-anchor="middle" class="overview-daily-day" font-size="${dayFont}">${esc(String(labels[i].getDate()))}</text>`
    );
    hits.push(
      `<rect class="overview-daily-bar-hit" x="${(pad.l + i * slotW).toFixed(1)}" y="${pad.t}" width="${slotW.toFixed(1)}" height="${(h + pad.b).toFixed(1)}" fill="transparent" data-value="${v}" aria-label="${esc(tip)}"/>`
    );
  }
  return `<div class="overview-daily-chart-wrap"><svg class="overview-daily-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><rect class="overview-daily-hover-col" visibility="hidden" fill="rgba(127,127,127,0.14)" pointer-events="none"/>${parts.join("")}${hits.join("")}</svg><div class="overview-daily-tooltip" hidden role="tooltip"></div></div>`;
}

function bindOverviewDailyCharts(root) {
  root?.querySelectorAll(".overview-daily-chart-wrap").forEach((wrap) => {
    if (wrap.dataset.bound === "1") return;
    wrap.dataset.bound = "1";
    const tooltip = wrap.querySelector(".overview-daily-tooltip");
    const svg = wrap.querySelector(".overview-daily-chart");
    const highlight = svg?.querySelector(".overview-daily-hover-col");
    if (!tooltip || !svg || !highlight) return;
    const hide = () => {
      tooltip.hidden = true;
      highlight.setAttribute("visibility", "hidden");
    };
    const show = (hit, clientX) => {
      const rect = wrap.getBoundingClientRect();
      const val = Number(hit.dataset.value);
      tooltip.textContent = formatDailyKwh(val);
      tooltip.hidden = false;
      tooltip.style.left = `${Math.max(8, Math.min(rect.width - 8, clientX - rect.left))}px`;
      tooltip.style.top = "0px";
      highlight.setAttribute("x", hit.getAttribute("x"));
      highlight.setAttribute("y", hit.getAttribute("y"));
      highlight.setAttribute("width", hit.getAttribute("width"));
      highlight.setAttribute("height", hit.getAttribute("height"));
      highlight.setAttribute("visibility", "visible");
    };
    wrap.addEventListener("mousemove", (ev) => {
      const hit = ev.target.closest?.(".overview-daily-bar-hit");
      if (hit && wrap.contains(hit)) show(hit, ev.clientX);
      else hide();
    });
    wrap.addEventListener("mouseleave", hide);
    wrap.addEventListener("click", (ev) => {
      if (ev.target.closest?.(".overview-daily-bar-hit")) ev.stopPropagation();
    });
  });
}

async function fetchFoxMirroredBarChart(hass, plant, plantState, period, offset = 0) {
  const now = new Date();
  const bounds = energyPeriodBounds(period, offset, now);
  const { start, end } = bounds;
  const fetchEnd = end > now ? now : end;
  const { points, error } = await fetchEnergyHistoryPoints(hass, plant, plantState, start, fetchEnd);
  if (!points) return { title: energyPeriodNavLabel(period, offset, now), svg: `<p class="placeholder chart-empty">${esc(error)}</p>` };

  if (period === "day") {
    const bucket = energyBucketForDay(points, start, now);
    return {
      title: energyPeriodNavLabel(period, offset, now),
      breakdown: computeEnergyBreakdown(points, [start]),
      svg: renderMirroredEnergyBarChart([bucket], [formatEnergyDateLabel(start)], { labelMode: "weekday" }),
    };
  }

  if (period === "week") {
    const days = buildFullWeekDays(start);
    const buckets = days.map((day) => energyBucketForDay(points, day, now));
    const labels = days.map(formatWeekdayLabel);
    const breakdownDays = daysUpToToday(days, now);
    return {
      title: energyPeriodNavLabel(period, offset, now),
      breakdown: computeEnergyBreakdown(points, breakdownDays),
      svg: renderMirroredEnergyBarChart(buckets, labels, { labelMode: "weekday" }),
    };
  }

  if (period === "month") {
    const days = buildFullMonthDays(start);
    const buckets = days.map((day) => energyBucketForDay(points, day, now));
    const breakdownDays = daysUpToToday(days, now);
    return {
      title: energyPeriodNavLabel(period, offset, now),
      breakdown: computeEnergyBreakdown(points, breakdownDays),
      svg: renderMirroredEnergyBarChart(buckets, days, { labelMode: "month-day" }),
    };
  }

  if (period === "year") {
    const year = start.getFullYear();
    const labels = [];
    const buckets = [];
    const today = startOfLocalDay(now);
    for (let m = 0; m < 12; m++) {
      const monthStart = new Date(year, m, 1);
      const monthEnd = new Date(year, m + 1, 0, 23, 59, 59, 999);
      labels.push(formatMonthShortLabel(monthStart));
      if (offset === 0 && monthStart > today) {
        buckets.push(emptyEnergyBucket());
        continue;
      }
      const effectiveEnd = offset === 0 && monthEnd > now ? now : monthEnd;
      const days = buildDaysInRange(monthStart, effectiveEnd);
      buckets.push(days.length ? energyBucketSum(points, days) : emptyEnergyBucket());
    }
    const breakdownDays = daysUpToToday(buildDaysInRange(start, fetchEnd), now);
    return {
      title: energyPeriodNavLabel(period, offset, now),
      breakdown: computeEnergyBreakdown(points, breakdownDays),
      svg: renderMirroredEnergyBarChart(buckets, labels, { labelMode: "month-short" }),
    };
  }

  const years = new Set();
  for (const key of ["pv", "feedIn", "load", "discharge", "charge", "grid"]) {
    for (const p of points[key] || []) years.add(new Date(p.t).getFullYear());
  }
  const yearList = Array.from(years).filter((y) => y >= 2000 && y <= now.getFullYear()).sort((a, b) => a - b);
  if (!yearList.length) yearList.push(now.getFullYear());
  const labels = yearList.map(String);
  const buckets = yearList.map((year) => {
    const yStart = new Date(year, 0, 1);
    const yEnd = year === now.getFullYear() ? end : new Date(year, 11, 31, 23, 59, 59, 999);
    return energyBucketSum(points, buildDaysInRange(yStart, yEnd));
  });
  const allDays = buildDaysInRange(start, end);
  return {
    title: "Total",
    breakdown: computeEnergyBreakdown(points, allDays),
    svg: renderMirroredEnergyBarChart(buckets, labels),
  };
}

async function fetchOverviewDailyEnergy(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const ent = {
    pv: map.solar_energy_today,
    load: map.load_energy_today,
    discharge: map.battery_discharge_today,
    charge: map.battery_charge_today,
    grid: map.grid_consumption_energy_today,
  };
  const ids = [ent.pv, ent.load, ent.discharge, ent.charge, ent.grid].filter(Boolean);
  const labels = buildLastNDays(OVERVIEW_DAILY_DAYS);
  if (!ids.length) {
    return { error: "Daily energy sensors not found. Reload FoxESS Plant after foxess_modbus is configured." };
  }
  const rangeStart = labels[0];
  const now = new Date();
  const hist = await fetchHistoryDuring(hass, ids, rangeStart, now);
  const points = {
    pv: historyToPoints(historyRowsForEntity(hist, ent.pv)),
    load: historyToPoints(historyRowsForEntity(hist, ent.load)),
    discharge: historyToPoints(historyRowsForEntity(hist, ent.discharge)),
    charge: historyToPoints(historyRowsForEntity(hist, ent.charge)),
    grid: historyToPoints(historyRowsForEntity(hist, ent.grid)),
  };
  const production = labels.map((day) => {
    const ds = startOfLocalDay(day).getTime();
    const de = endOfLocalDay(day).getTime();
    return dailyProductionKwh(points, ds, de);
  });
  const consumption = labels.map((day) => {
    const ds = startOfLocalDay(day).getTime();
    const de = endOfLocalDay(day).getTime();
    return dailyConsumptionKwh(points, ds, de);
  });
  const todayStart = startOfLocalDay(now).getTime();
  const todayEnd = now.getTime();
  return {
    labels,
    production,
    consumption,
    batteryChargeSpark: cumulativeHistorySparkValues(points.charge, todayStart, todayEnd),
    batteryDischargeSpark: cumulativeHistorySparkValues(points.discharge, todayStart, todayEnd),
  };
}

function energyPeriodSummaryLabel(period) {
  if (period === "week") return "Weekly";
  if (period === "month") return "Monthly";
  if (period === "year") return "Yearly";
  if (period === "total") return "Total";
  return "Daily";
}

function downsampleSparkSeries(values, maxPoints = ANALYSIS_SPARK_MAX_POINTS) {
  const data = (values || []).map((v) => Number(v) || 0);
  if (data.length <= maxPoints) return data;
  const out = [];
  const step = (data.length - 1) / (maxPoints - 1);
  for (let i = 0; i < maxPoints; i++) {
    out.push(data[Math.round(i * step)]);
  }
  return out;
}

function sortCumulativeHistoryPts(pts, endMs) {
  return (pts || [])
    .map((p) => ({ t: p.t, v: Math.max(0, Number(p.v) || 0) }))
    .filter((p) => p.t <= endMs)
    .sort((a, b) => a.t - b.t);
}

function cumulativeValueAt(sortedPts, t) {
  if (!sortedPts?.length) return 0;
  return Math.max(0, interpolateSeriesAt(sortedPts, t, { allowBackfill: true }) ?? 0);
}

function resampleCumulativeSparkValues(pts, startMs, endMs) {
  const sorted = sortCumulativeHistoryPts(pts, endMs);
  if (!sorted.length) return [];
  const out = [];
  for (let t = startMs; t <= endMs; t += ANALYSIS_SPARK_SAMPLE_MS) {
    out.push(roundEnergyKwh(cumulativeValueAt(sorted, t)));
  }
  const data = downsampleSparkSeries(out);
  return data.length >= 2 ? data : [];
}

function cumulativeHistorySparkValues(pts, startMs, endMs) {
  return resampleCumulativeSparkValues(pts, startMs, endMs);
}

function buildIntradayProductionSpark(points, startMs, endMs) {
  return resampleCumulativeSparkValues(points.pv, startMs, endMs);
}

function buildIntradayConsumptionSpark(points, startMs, endMs) {
  const sorted = {
    load: sortCumulativeHistoryPts(points.load, endMs),
    discharge: sortCumulativeHistoryPts(points.discharge, endMs),
    charge: sortCumulativeHistoryPts(points.charge, endMs),
    grid: sortCumulativeHistoryPts(points.grid, endMs),
  };
  const out = [];
  for (let t = startMs; t <= endMs; t += ANALYSIS_SPARK_SAMPLE_MS) {
    let v;
    if (sorted.load.length) {
      v = cumulativeValueAt(sorted.load, t);
    } else {
      v =
        -cumulativeValueAt(sorted.discharge, t) +
        cumulativeValueAt(sorted.charge, t) +
        cumulativeValueAt(sorted.grid, t);
    }
    out.push(roundEnergyKwh(Math.max(0, v)));
  }
  const data = downsampleSparkSeries(out);
  return data.length >= 2 ? data : [];
}

function buildSparkPowerPoints(hass, entityId, spec, range, statsMap, hist) {
  if (!entityId) return [];
  let rawPoints = statisticsRawPointsForEntity(hass, entityId, range, statsMap, hist).map((p) => ({
    t: p.t,
    v: transformHistoryPoint(hass, entityId, p.v, spec),
  }));
  if (!rawPoints.length) {
    const histPts = historyToPoints(historyRowsForEntity(hist, entityId)).map((p) => ({
      t: p.t,
      v: transformHistoryPoint(hass, entityId, p.v, spec),
    }));
    rawPoints = resamplePointsMean(histPts, STATISTICS_PERIOD_MS, range.tMin, range.nowMs);
  }
  return rawPoints
    .map((p) => ({ t: p.t, v: Math.max(0, Number(p.v) || 0) }))
    .filter((p) => Number.isFinite(p.v));
}

function integratePowerSparkSeries(powerPts, startMs, endMs) {
  if (!powerPts?.length) return [];
  const hours = ANALYSIS_SPARK_SAMPLE_MS / 3600000;
  let cum = 0;
  const out = [];
  for (let t = startMs; t <= endMs; t += ANALYSIS_SPARK_SAMPLE_MS) {
    const kw = interpolateSeriesAt(powerPts, t) ?? 0;
    cum += Math.max(0, kw) * hours;
    out.push(roundEnergyKwh(cum));
  }
  const data = downsampleSparkSeries(out);
  return data.length >= 2 ? data : [];
}

async function fetchDaySparkFromPowerStats(hass, plant, plantState, startMs, endMs) {
  const map = resolveEntityMap(hass, plant, plantState);
  const pvId = map.pv_power;
  const loadId = map.load_power;
  const ids = [pvId, loadId].filter(Boolean);
  if (!ids.length) return null;
  const start = new Date(startMs);
  const end = new Date(endMs);
  const [statsMap, hist] = await Promise.all([
    fetchStatisticsDuring(hass, ids, start, end),
    fetchHistoryDuring(hass, ids, start, end),
  ]);
  const range = { tMin: startMs, nowMs: endMs, tMax: endMs };
  const pvSpec = { toKw: true };
  const loadSpec = { toKw: true };
  const pvPower = buildSparkPowerPoints(hass, pvId, pvSpec, range, statsMap, hist);
  const loadPower = loadId ? buildSparkPowerPoints(hass, loadId, loadSpec, range, statsMap, hist) : [];
  if (!pvPower.length && !loadPower.length) return null;
  const production = integratePowerSparkSeries(pvPower, startMs, endMs);
  const consumption = integratePowerSparkSeries(loadPower, startMs, endMs);
  if (production.length < 2 && consumption.length < 2) return null;
  return { production, consumption };
}

function resamplePeriodSparkBuckets(values, maxPoints = ANALYSIS_SPARK_MAX_POINTS) {
  const data = (values || []).map((v) => Number(v) || 0);
  if (data.length <= 1) return data.length === 1 ? [0, data[0]] : [];
  return downsampleSparkSeries(data, Math.min(maxPoints, Math.max(data.length, 2)));
}

function buildDailySparkBuckets(points, days) {
  return days.map((day) => {
    const ds = startOfLocalDay(day).getTime();
    const de = endOfLocalDay(day).getTime();
    return {
      production: dailyProductionKwh(points, ds, de),
      consumption: dailyConsumptionKwh(points, ds, de),
    };
  });
}

function syncSparkSeriesToTotal(series, total) {
  const data = (series || []).map((v) => Number(v) || 0);
  const target = Number(total) || 0;
  if (!data.length) return target > 0 ? [0, target] : [];
  if (data.length === 1) return [0, target];
  data[data.length - 1] = target;
  return data;
}

function ensureSparkSeries(values) {
  const data = (values || []).map((v) => Number(v) || 0);
  if (data.length >= 2) return data;
  if (data.length === 1) return [0, data[0]];
  return [];
}

async function fetchAnalysisSummarySparkData(hass, plant, plantState, period, offset = 0) {
  const now = new Date();
  const bounds = energyPeriodBounds(period, offset, now);
  const fetchEnd = bounds.end > now ? now : bounds.end;
  const { points, error } = await fetchEnergyHistoryPoints(hass, plant, plantState, bounds.start, fetchEnd);
  if (!points) return { error, production: [], consumption: [] };

  if (period === "day") {
    const startMs = bounds.start.getTime();
    const endMs = fetchEnd.getTime();
    const fromPower = await fetchDaySparkFromPowerStats(hass, plant, plantState, startMs, endMs);
    if (fromPower?.production?.length >= 2 || fromPower?.consumption?.length >= 2) {
      return {
        production:
          fromPower.production?.length >= 2
            ? fromPower.production
            : buildIntradayProductionSpark(points, startMs, endMs),
        consumption:
          fromPower.consumption?.length >= 2
            ? fromPower.consumption
            : buildIntradayConsumptionSpark(points, startMs, endMs),
      };
    }
    return {
      production: buildIntradayProductionSpark(points, startMs, endMs),
      consumption: buildIntradayConsumptionSpark(points, startMs, endMs),
    };
  }

  if (period === "week") {
    const days = daysUpToToday(buildFullWeekDays(bounds.start), now);
    const buckets = buildDailySparkBuckets(points, days);
    return {
      production: resamplePeriodSparkBuckets(buckets.map((b) => b.production), 7),
      consumption: resamplePeriodSparkBuckets(buckets.map((b) => b.consumption), 7),
    };
  }

  if (period === "month") {
    const days = daysUpToToday(buildFullMonthDays(bounds.start), now);
    const buckets = buildDailySparkBuckets(points, days);
    return {
      production: resamplePeriodSparkBuckets(buckets.map((b) => b.production), 31),
      consumption: resamplePeriodSparkBuckets(buckets.map((b) => b.consumption), 31),
    };
  }

  if (period === "year") {
    const year = bounds.start.getFullYear();
    const production = [];
    const consumption = [];
    const today = startOfLocalDay(now);
    for (let m = 0; m < 12; m++) {
      const monthStart = new Date(year, m, 1);
      if (offset === 0 && monthStart > today) {
        production.push(0);
        consumption.push(0);
        continue;
      }
      const monthEnd = new Date(year, m + 1, 0, 23, 59, 59, 999);
      const effectiveEnd = offset === 0 && monthEnd > now ? now : monthEnd;
      const days = buildDaysInRange(monthStart, effectiveEnd);
      let pv = 0;
      let load = 0;
      for (const day of days) {
        const ds = startOfLocalDay(day).getTime();
        const de = endOfLocalDay(day).getTime();
        pv += dailyProductionKwh(points, ds, de);
        load += dailyConsumptionKwh(points, ds, de);
      }
      production.push(roundEnergyKwh(pv));
      consumption.push(roundEnergyKwh(load));
    }
    return {
      production: resamplePeriodSparkBuckets(production, 12),
      consumption: resamplePeriodSparkBuckets(consumption, 12),
    };
  }

  const years = new Set();
  for (const key of ["pv", "feedIn", "load", "discharge", "charge", "grid"]) {
    for (const p of points[key] || []) years.add(new Date(p.t).getFullYear());
  }
  const yearList = Array.from(years).filter((y) => y >= 2000 && y <= now.getFullYear()).sort((a, b) => a - b);
  if (!yearList.length) yearList.push(now.getFullYear());
  const production = yearList.map((year) => {
    const yStart = new Date(year, 0, 1);
    const yEnd = year === now.getFullYear() ? fetchEnd : new Date(year, 11, 31, 23, 59, 59, 999);
    const days = buildDaysInRange(yStart, yEnd);
    let pv = 0;
    for (const day of days) {
      const ds = startOfLocalDay(day).getTime();
      const de = endOfLocalDay(day).getTime();
      pv += dailyProductionKwh(points, ds, de);
    }
    return roundEnergyKwh(pv);
  });
  const consumption = yearList.map((year) => {
    const yStart = new Date(year, 0, 1);
    const yEnd = year === now.getFullYear() ? fetchEnd : new Date(year, 11, 31, 23, 59, 59, 999);
    const days = buildDaysInRange(yStart, yEnd);
    let load = 0;
    for (const day of days) {
      const ds = startOfLocalDay(day).getTime();
      const de = endOfLocalDay(day).getTime();
      load += dailyConsumptionKwh(points, ds, de);
    }
    return roundEnergyKwh(load);
  });
  return {
    production: resamplePeriodSparkBuckets(production, 24),
    consumption: resamplePeriodSparkBuckets(consumption, 24),
  };
}

function formatChartDayLabel(d) {
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function formatChartMonthLabel(d) {
  return d.toLocaleDateString(undefined, { month: "short" });
}

function formatChartTimeLabel(ms) {
  return new Date(ms).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function renderStatisticsChartHtml(series, range, options = {}) {
  const sideLegend = options.sideLegend === true;
  const includeSoc = options.includeSoc === true;
  const socSeries = includeSoc ? options.socSeries : null;
  const hasSoc = !!socSeries?.points?.length;
  const visible = series.filter((s) => s.points?.length);
  if (!visible.length && !hasSoc) {
    return `<p class="placeholder chart-empty">No power history for today yet.</p>`;
  }
  const layout = statisticsChartLayout({ sideLegend, hasSoc });
  const { width, height, pad, xTickHours, xTickCount } = layout;
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const { tMin, tMax, nowMs } = range;
  const daySpan = tMax - tMin;
  const xScale = (t) => pad.l + ((t - tMin) / daySpan) * w;
  const { yMin, yMax, step: yTickStep } = computeStatisticsYDomain(visible);
  const ySpan = yMax - yMin || 1;
  const yScale = (v) => pad.t + h - ((v - yMin) / ySpan) * h;
  const ySocScale = (v) => pad.t + h - (Math.min(100, Math.max(0, v)) / 100) * h;
  const yZero = yScale(0);
  const yTicks = statisticsYTicks(yMin, yMax, yTickStep);
  const yAxisX = pad.l;
  const yLabelX = yAxisX - 10;
  const yAxisRightX = pad.l + w;
  const yLabelRightX = yAxisRightX + 8;
  const xTicks = Array.from({ length: xTickCount }, (_, i) => tMin + i * xTickHours * 60 * 60 * 1000);

  const plotSeries = visible.map((s) => {
    const isForecast = s.id === "forecast" || s.legendGroup === "forecast";
    const clipEnd = isForecast ? tMax : nowMs;
    const clipped = s.points.filter((p) => p.t >= tMin && p.t <= clipEnd);
    let segmentGroups;
    if (isForecast && clipped.length >= 2) {
      if (options.forecastFullDaySolid) {
        segmentGroups = [{ pts: clipped, dash: "" }];
      } else {
        const past = clipped.filter((p) => p.t <= nowMs);
        const future = clipped.filter((p) => p.t > nowMs + STATISTICS_PERIOD_MS * 0.5);
        segmentGroups = [];
        if (past.length >= 2) segmentGroups.push({ pts: past, dash: "" });
        const futurePts =
          past.length && past[past.length - 1].t < nowMs
            ? [past[past.length - 1], ...future.filter((p) => p.t > past[past.length - 1].t)]
            : future;
        if (futurePts.length >= 2) segmentGroups.push({ pts: futurePts, dash: "5 4" });
        else if (!past.length && future.length >= 2) segmentGroups.push({ pts: future, dash: "5 4" });
        if (!segmentGroups.length) segmentGroups.push({ pts: clipped, dash: "" });
      }
    } else {
      const segmentPoints = s.connectGaps ? [clipped] : splitStatisticsSegments(clipped);
      segmentGroups = segmentPoints.map((pts) => ({ pts, dash: "" }));
    }
    const segments = segmentGroups.map(({ pts, dash }) => ({
      timePts: pts,
      pixelPts: pts.map((p) => ({ x: xScale(p.t), y: yScale(p.v), t: p.t, v: p.v })),
      dash,
    }));
    return { ...s, segments, isForecast };
  });

  let socPlotSeries = null;
  if (hasSoc) {
    const clipped = socSeries.points.filter((p) => p.t >= tMin && p.t <= nowMs);
    const segmentGroups = socSeries.connectGaps ? [clipped] : splitStatisticsSegments(clipped);
    const segments = segmentGroups
      .filter((pts) => pts.length >= 2)
      .map((pts) => ({
        timePts: pts,
        pixelPts: pts.map((p) => ({ x: xScale(p.t), y: ySocScale(p.v), t: p.t, v: p.v })),
        dash: "",
      }));
    socPlotSeries = { ...socSeries, segments };
  }

  const grid = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${pad.l + w}" y2="${y.toFixed(1)}" class="statistics-grid"/>`;
    })
    .join("");

  const yLabels = yTicks
    .map((yv) => {
      const y = yScale(yv);
      return `<text x="${yLabelX}" y="${(y + 4).toFixed(1)}" text-anchor="end" class="statistics-axis-y">${esc(formatStatisticsYTick(yv))}</text>`;
    })
    .join("");

  const ySocLabels = hasSoc
    ? STATISTICS_SOC_Y_TICKS.map((yv) => {
        const y = ySocScale(yv);
        return `<text x="${yLabelRightX}" y="${(y + 4).toFixed(1)}" text-anchor="start" class="statistics-axis-y statistics-axis-y--soc">${yv}%</text>`;
      }).join("")
    : "";

  const xLabels = xTicks
    .map((xt) => {
      const x = xScale(xt);
      return `<text x="${x.toFixed(1)}" y="${height - pad.b + 20}" text-anchor="middle" class="statistics-axis-x">${esc(formatChartTimeLabel(xt))}</text>`;
    })
    .join("");

  const fills = plotSeries
    .flatMap((s) =>
      (s.segments || [])
        .filter((seg) => s.fill && seg.pixelPts.length >= 2)
        .map(
          (seg) =>
            `<path class="statistics-fill" data-series-id="${esc(s.id)}" data-legend-group="${esc(s.legendGroup || "")}" d="${fillToZeroPath(seg.pixelPts, yZero, seg.timePts)}" fill="${s.fillColor}" stroke="none"/>`
        )
    )
    .join("");

  const lines = plotSeries
    .flatMap((s) =>
      (s.segments || [])
        .filter((seg) => seg.pixelPts.length >= 2)
        .map(
          (seg) =>
            `<path class="statistics-line${seg.dash ? " statistics-line-forecast-future" : ""}" data-series-id="${esc(s.id)}" data-legend-group="${esc(s.legendGroup || "")}" d="${statisticsLinePath(seg.pixelPts, seg.timePts)}" fill="none" stroke="${s.color}" stroke-width="${s.lineWidth || 1.2}" stroke-linecap="round" stroke-linejoin="round"${seg.dash ? ` stroke-dasharray="${seg.dash}"` : ""}/>`
        )
    )
    .join("");

  const socLines = socPlotSeries
    ? (socPlotSeries.segments || [])
        .filter((seg) => seg.pixelPts.length >= 2)
        .map(
          (seg) =>
            `<path class="statistics-line statistics-line-soc" data-series-id="${esc(socPlotSeries.id)}" data-legend-group="soc" d="${statisticsLinePath(seg.pixelPts, seg.timePts)}" fill="none" stroke="${socPlotSeries.color}" stroke-width="${socPlotSeries.lineWidth || 1.6}" stroke-linecap="round" stroke-linejoin="round"/>`
        )
        .join("")
    : "";

  const legendItems = sideLegend
    ? renderStatisticsSideLegend(visible, { socVisible: hasSoc })
    : options.legendFromSeries
      ? renderDeviceRealtimeLegend(visible, { socSeries: hasSoc ? socSeries : null })
      : STATISTICS_LEGEND_ORDER.filter((g) => new Set(visible.map((s) => s.legendGroup || s.id)).has(g))
          .map(
            (g) =>
              `<button type="button" class="statistics-legend-item" data-legend-group="${esc(g)}" aria-pressed="true"><i style="background:${esc(STATISTICS_LEGEND_COLORS[g] || "#888")}"></i><span>${esc(STATISTICS_LEGEND_LABEL[g] || g)}</span></button>`
          )
          .join("");

  const powerAxisLabel = sideLegend || hasSoc ? "Power (kW)" : "kW";
  const leftAxisTitle = `<text x="${yLabelX}" y="${(pad.t - 6).toFixed(1)}" text-anchor="start" class="statistics-y-label statistics-y-label--left">${esc(powerAxisLabel)}</text>`;
  const rightAxisTitle = hasSoc
    ? `<text x="${yAxisRightX}" y="${(pad.t - 6).toFixed(1)}" text-anchor="end" class="statistics-y-label statistics-y-label--right">SOC</text>`
    : "";

  const plotHtml = `<div class="statistics-chart-plot" data-pad-l="${pad.l}" data-pad-t="${pad.t}" data-pad-b="${pad.b}" data-plot-w="${w}" data-plot-h="${h}" data-t-min="${tMin}" data-t-max="${tMax}" data-y-min="${yMin}" data-y-max="${yMax}" data-now-ms="${nowMs}">
<svg class="statistics-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Statistics power chart">
${leftAxisTitle}
${rightAxisTitle}
${grid}
<line x1="${yAxisX}" y1="${pad.t}" x2="${yAxisX}" y2="${(pad.t + h).toFixed(1)}" class="statistics-y-axis"/>
${hasSoc ? `<line x1="${yAxisRightX}" y1="${pad.t}" x2="${yAxisRightX}" y2="${(pad.t + h).toFixed(1)}" class="statistics-y-axis statistics-y-axis--right"/>` : ""}
<line x1="${yAxisX}" y1="${yZero.toFixed(1)}" x2="${(pad.l + w).toFixed(1)}" y2="${yZero.toFixed(1)}" class="statistics-zero-line"/>
${fills}
${lines}
${socLines}
${yLabels}
${ySocLabels}
${xLabels}
<rect class="statistics-hit" x="${pad.l}" y="${pad.t}" width="${w}" height="${h}" fill="transparent"/>
</svg>
<div class="statistics-crosshair" hidden><div class="statistics-spike"></div></div>
<div class="statistics-tooltip" hidden role="tooltip"></div>
</div>`;

  if (sideLegend) {
    return `<div class="statistics-chart-wrap statistics-chart-wrap--side${hasSoc ? " statistics-chart-wrap--soc" : ""}" data-statistics-chart="1">
<div class="statistics-chart-main">${plotHtml}</div>
<aside class="statistics-chart-legend-side">${legendItems}</aside>
</div>`;
  }

  return `<div class="statistics-chart-wrap" data-statistics-chart="1">
<div class="statistics-chart-legend">${legendItems}</div>
${plotHtml}
</div>`;
}

function bindStatisticsChart(root, seriesMeta) {
  const wrap = root?.querySelector?.("[data-statistics-chart]");
  if (!wrap || wrap.dataset.bound || !seriesMeta?.length) return;
  const plot = wrap.querySelector(".statistics-chart-plot");
  if (!plot) return;
  wrap.dataset.bound = "1";

  const padL = Number(plot.dataset.padL);
  const padT = Number(plot.dataset.padT);
  const padB = Number(plot.dataset.padB);
  const plotW = Number(plot.dataset.plotW);
  const plotH = Number(plot.dataset.plotH);
  const tMin = Number(plot.dataset.tMin);
  const tMax = Number(plot.dataset.tMax);
  const yMin = Number(plot.dataset.yMin);
  const yMax = Number(plot.dataset.yMax);
  const nowMs = Number(plot.dataset.nowMs);
  const daySpan = tMax - tMin;
  const ySpan = yMax - yMin || 1;
  const svg = plot.querySelector(".statistics-chart-svg");
  const hit = plot.querySelector(".statistics-hit");
  const crosshair = plot.querySelector(".statistics-crosshair");
  const spike = plot.querySelector(".statistics-spike");
  const tooltip = plot.querySelector(".statistics-tooltip");
  const hiddenGroups = new Set();

  const applyLegendVisibility = () => {
    wrap.querySelectorAll("[data-legend-group]").forEach((el) => {
      if (!(el instanceof SVGElement) && !el.classList.contains("statistics-legend-item")) return;
      const g = el.getAttribute("data-legend-group");
      if (!g) return;
      if (el.classList.contains("statistics-legend-item")) {
        el.setAttribute("aria-pressed", hiddenGroups.has(g) ? "false" : "true");
        el.classList.toggle("off", hiddenGroups.has(g));
        return;
      }
      el.style.display = hiddenGroups.has(g) ? "none" : "";
    });
  };

  wrap.querySelectorAll(".statistics-legend-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const g = btn.getAttribute("data-legend-group");
      if (!g) return;
      if (hiddenGroups.has(g)) hiddenGroups.delete(g);
      else hiddenGroups.add(g);
      applyLegendVisibility();
    });
  });

  const showHover = (clientX) => {
    const t = Math.min(statisticsClientToTime(svg, clientX, padL, plotW, tMin, daySpan), tMax);
    const rect = svg.getBoundingClientRect();
    const { scale, offsetX, offsetY } = statisticsPointerScale(svg);
    const xPx = padL + ((t - tMin) / daySpan) * plotW;
    const screenX = offsetX + xPx * scale;
    crosshair.hidden = false;
    crosshair.style.left = `${screenX}px`;
    crosshair.style.top = `${offsetY + padT * scale}px`;
    crosshair.style.bottom = `${offsetY + padB * scale}px`;
    spike.style.height = "100%";

    const rows = statisticsTooltipRowsHtml(seriesMeta, t, hiddenGroups);
    tooltip.hidden = false;
    tooltip.innerHTML = `<div class="statistics-tooltip-time">${esc(formatStatisticsHoverTime(t))}</div>${rows}`;
    const plotRect = plot.getBoundingClientRect();
    let left = screenX + 12;
    if (left + 200 > plotRect.width) left = screenX - 212;
    tooltip.style.left = `${Math.max(8, left)}px`;
    tooltip.style.top = "12px";
  };

  const hideHover = () => {
    crosshair.hidden = true;
    tooltip.hidden = true;
  };

  hit?.addEventListener("mousemove", (ev) => showHover(ev.clientX));
  hit?.addEventListener("mouseleave", hideHover);
  bindTouchChartScrub(hit, showHover, hideHover);

  syncStatisticsSideLegendOffset(wrap);
  if (typeof ResizeObserver !== "undefined") {
    wrap._statLegendRo?.disconnect?.();
    wrap._statLegendRo = new ResizeObserver(() => syncStatisticsSideLegendOffset(wrap));
    wrap._statLegendRo.observe(svg);
  }
}

function renderBarChartSvg(groups, labels, { height = 200 } = {}) {
  const n = labels.length;
  if (!n) return `<p class="placeholder chart-empty">No energy history in this period.</p>`;
  const width = 400;
  const pad = { l: 40, r: 12, t: 16, b: 36 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  let yMax = 0.5;
  for (const g of groups) {
    for (const v of g.values) yMax = Math.max(yMax, v);
  }
  yMax *= 1.15;
  const groupW = w / n;
  const barW = Math.min(14, (groupW / Math.max(groups.length, 1)) * 0.7);
  const rects = [];
  labels.forEach((_, i) => {
    const gx = pad.l + i * groupW + groupW / 2;
    groups.forEach((g, gi) => {
      const v = g.values[i] || 0;
      const bh = (v / yMax) * h;
      const x = gx - (groups.length * barW) / 2 + gi * barW;
      const y = pad.t + h - bh;
      rects.push(
        `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${g.color}" opacity="0.92"/>`
      );
    });
    if (n <= 16 || i % Math.ceil(n / 8) === 0 || i === n - 1) {
      const lx = gx;
      const ly = height - 10;
      const lbl = labels[i] instanceof Date ? formatChartDayLabel(labels[i]) : String(labels[i]);
      rects.push(`<text x="${lx.toFixed(1)}" y="${ly}" text-anchor="middle" class="chart-axis">${esc(lbl)}</text>`);
    }
  });
  const legend = groups
    .map((g) => `<span class="chart-legend-item"><i style="background:${g.color}"></i>${esc(g.label)}</span>`)
    .join("");
  return `<div class="chart-wrap"><svg class="energy-bar-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">${rects.join("")}</svg><div class="chart-legend">${legend}</div></div>`;
}

function mirrorChartAxisLabel(label, i, n, labelMode) {
  if (labelMode === "month-day" && label instanceof Date) {
    const day = label.getDate();
    if (day % 2 === 1 || i === n - 1) return String(day);
    return null;
  }
  if (labelMode === "weekday" || labelMode === "month-short") return String(label);
  if (label instanceof Date) return formatChartDayLabel(label);
  return String(label);
}

function mirroredEnergyColumnLabels(labels, labelMode) {
  const n = labels.length;
  return labels.map((label, i) => {
    const axis = mirrorChartAxisLabel(label, i, n, labelMode);
    if (axis) return axis;
    if (label instanceof Date) return formatEnergyDateLabel(label);
    return String(label);
  });
}

function sumMirroredEnergyBuckets(buckets) {
  const out = emptyEnergyBucket();
  for (const bucket of buckets) {
    for (const spec of FOX_SUPPLY_SERIES) {
      out.supply[spec.key] += bucket.supply?.[spec.key] || 0;
    }
    for (const spec of FOX_USAGE_SERIES) {
      out.usage[spec.key] += bucket.usage?.[spec.key] || 0;
    }
  }
  for (const spec of FOX_SUPPLY_SERIES) out.supply[spec.key] = roundEnergyKwh(out.supply[spec.key]);
  for (const spec of FOX_USAGE_SERIES) out.usage[spec.key] = roundEnergyKwh(out.usage[spec.key]);
  return out;
}

function renderMirroredEnergyLegendItem(spec, valueKwh) {
  const val = Number(valueKwh) || 0;
  return `<span class="statistics-legend-item fox-energy-mirror-legend-item"><i style="background:${spec.color}"></i><span>${esc(spec.label)}</span><span class="fox-energy-mirror-legend-value">${val.toFixed(2)} kWh</span></span>`;
}

function mirroredEnergyTooltipRowsHtml(bucket) {
  const row = (spec, v) => {
    if (v <= 0) return "";
    return `<div class="statistics-tooltip-row"><span class="statistics-tooltip-label"><i class="statistics-tooltip-swatch" style="background:${esc(spec.color)}"></i>${esc(spec.label)}</span><strong>${v.toFixed(2)} kWh</strong></div>`;
  };
  const rows = [
    ...FOX_SUPPLY_SERIES.map((s) => row(s, bucket.supply?.[s.key] || 0)),
    ...FOX_USAGE_SERIES.map((s) => row(s, bucket.usage?.[s.key] || 0)),
  ].filter(Boolean);
  return rows.length
    ? rows.join("")
    : `<div class="statistics-tooltip-row"><span class="statistics-tooltip-label">No data</span></div>`;
}

function bindMirroredEnergyChart(root) {
  const wrap =
    root?.querySelector?.("[data-fox-energy-chart]") ||
    (root?.matches?.("[data-fox-energy-chart]") ? root : null);
  if (!wrap) return;
  const plot = wrap.querySelector(".fox-energy-mirror-plot");
  const svg = plot?.querySelector("svg");
  const tooltip = plot?.querySelector(".statistics-tooltip");
  if (!plot || !svg || !tooltip) return;
  delete wrap.dataset.bound;
  let buckets = [];
  let labels = [];
  try {
    buckets = JSON.parse(wrap.dataset.energyBuckets || "[]");
    labels = JSON.parse(wrap.dataset.energyLabels || "[]");
  } catch {
    return;
  }
  if (!buckets.length) return;
  wrap.dataset.bound = "1";

  const padL = 44;
  const plotW = 1000 - padL - 12;
  const n = buckets.length;
  const groupW = plotW / n;

  const hideHover = () => {
    tooltip.hidden = true;
  };

  const showColumn = (clientX) => {
    const rect = svg.getBoundingClientRect();
    if (!rect.width) return;
    const x = ((clientX - rect.left) / rect.width) * 1000;
    const rel = x - padL;
    if (rel < 0 || rel > plotW) {
      hideHover();
      return;
    }
    const i = Math.min(n - 1, Math.max(0, Math.floor(rel / groupW)));
    const label = labels[i] ?? "";
    tooltip.hidden = false;
    tooltip.innerHTML = `<div class="statistics-tooltip-time">${esc(String(label))}</div>${mirroredEnergyTooltipRowsHtml(buckets[i])}`;
    const plotRect = plot.getBoundingClientRect();
    const colCenter = ((padL + i * groupW + groupW / 2) / 1000) * rect.width;
    let left = colCenter + 12;
    if (left + 200 > plotRect.width) left = colCenter - 212;
    tooltip.style.left = `${Math.max(8, left)}px`;
    tooltip.style.top = "8px";
  };

  svg.addEventListener("mousemove", (ev) => showColumn(ev.clientX));
  svg.addEventListener("mouseleave", hideHover);
  bindTouchChartScrub(svg, showColumn, hideHover);
}

function renderMirroredEnergyBarChart(buckets, labels, { height = 300, labelMode = "auto" } = {}) {
  const n = buckets.length;
  if (!n) return `<p class="placeholder chart-empty">No energy history in this period.</p>`;
  const width = 1000;
  const pad = { l: 44, r: 12, t: 24, b: 42 };
  const plotH = height - pad.t - pad.b;
  const midY = pad.t + plotH / 2;
  const halfH = plotH / 2 - 6;
  const w = width - pad.l - pad.r;
  let maxVal = 0.5;
  for (const b of buckets) {
    const supply = FOX_SUPPLY_SERIES.reduce((s, spec) => s + (b.supply?.[spec.key] || 0), 0);
    const usage = FOX_USAGE_SERIES.reduce((s, spec) => s + (b.usage?.[spec.key] || 0), 0);
    maxVal = Math.max(maxVal, supply, usage);
  }
  maxVal *= 1.12;
  const yScale = (v) => (v / maxVal) * halfH;
  const groupW = w / n;
  const barW = Math.min(28, groupW * 0.62);
  const parts = [];
  for (const yv of [maxVal, maxVal / 2]) {
    const up = midY - yScale(yv);
    const down = midY + yScale(yv);
    parts.push(`<line x1="${pad.l}" y1="${up.toFixed(1)}" x2="${pad.l + w}" y2="${up.toFixed(1)}" class="fox-energy-grid"/>`);
    parts.push(`<line x1="${pad.l}" y1="${down.toFixed(1)}" x2="${pad.l + w}" y2="${down.toFixed(1)}" class="fox-energy-grid"/>`);
    parts.push(
      `<text x="${pad.l - 8}" y="${(up + 4).toFixed(1)}" text-anchor="end" class="fox-energy-axis">${esc(String(Math.round(yv)))}</text>`
    );
    parts.push(
      `<text x="${pad.l - 8}" y="${(down + 4).toFixed(1)}" text-anchor="end" class="fox-energy-axis">${esc(String(Math.round(yv)))}</text>`
    );
  }
  parts.push(`<text x="14" y="${(pad.t + plotH / 2).toFixed(1)}" class="fox-energy-y-label" transform="rotate(-90 14 ${(pad.t + plotH / 2).toFixed(1)})">kWh</text>`);
  parts.push(`<line x1="${pad.l}" y1="${midY.toFixed(1)}" x2="${pad.l + w}" y2="${midY.toFixed(1)}" class="fox-energy-zero"/>`);

  buckets.forEach((bucket, i) => {
    const cx = pad.l + i * groupW + groupW / 2;
    let y = midY;
    for (const spec of FOX_SUPPLY_SERIES) {
      const v = bucket.supply?.[spec.key] || 0;
      if (v <= 0) continue;
      const bh = yScale(v);
      y -= bh;
      parts.push(
        `<rect x="${(cx - barW / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${spec.color}" opacity="0.95"/>`
      );
    }
    y = midY;
    for (const spec of FOX_USAGE_SERIES) {
      const v = bucket.usage?.[spec.key] || 0;
      if (v <= 0) continue;
      const bh = yScale(v);
      parts.push(
        `<rect x="${(cx - barW / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${spec.color}" opacity="0.95"/>`
      );
      y += bh;
    }
    if (n <= 16 || i % Math.ceil(n / 10) === 0 || i === n - 1 || labelMode === "month-day") {
      const lbl = mirrorChartAxisLabel(labels[i], i, n, labelMode);
      if (lbl) {
        parts.push(`<text x="${cx.toFixed(1)}" y="${height - 12}" text-anchor="middle" class="fox-energy-axis">${esc(lbl)}</text>`);
      }
    }
  });

  const totals = sumMirroredEnergyBuckets(buckets);
  const supplyLegend = FOX_SUPPLY_SERIES.map((s) =>
    renderMirroredEnergyLegendItem(s, totals.supply[s.key])
  ).join("");
  const usageLegend = FOX_USAGE_SERIES.map((s) =>
    renderMirroredEnergyLegendItem(s, totals.usage[s.key])
  ).join("");
  const displayLabels = mirroredEnergyColumnLabels(labels, labelMode);

  return `<div class="fox-energy-chart-wrap" data-fox-energy-chart="1" data-energy-buckets="${esc(JSON.stringify(buckets))}" data-energy-labels="${esc(JSON.stringify(displayLabels))}">
<div class="statistics-chart-legend fox-energy-mirror-legend">
<div class="fox-energy-legend-row"><span class="fox-energy-legend-heading">SUPPLY</span>${supplyLegend}</div>
<div class="fox-energy-legend-row"><span class="fox-energy-legend-heading">USAGE</span>${usageLegend}</div>
</div>
<div class="fox-energy-mirror-plot">
<svg class="fox-energy-mirror-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Energy supply and usage chart">${parts.join("")}</svg>
<div class="statistics-tooltip" hidden role="tooltip"></div>
</div>
</div>`;
}

function resolveEnergyHistoryEntities(map) {
  return {
    pv: map.solar_energy_today,
    feedIn: map.feed_in_energy_today,
    load: map.load_energy_today,
    discharge: map.battery_discharge_today,
    charge: map.battery_charge_today,
    grid: map.grid_consumption_energy_today,
  };
}

async function fetchEnergyHistoryPoints(hass, plant, plantState, rangeStart, rangeEnd) {
  const map = resolveEntityMap(hass, plant, plantState);
  const ent = resolveEnergyHistoryEntities(map);
  const ids = [ent.pv, ent.feedIn, ent.load, ent.discharge, ent.charge, ent.grid].filter(Boolean);
  if (!ids.length) return { ent, points: null, error: "Daily energy sensors not found. Reload FoxESS Plant." };
  const rangeMs = rangeEnd.getTime() - rangeStart.getTime();
  const significantChangesOnly = rangeMs > 2 * 86400000;
  const hist = await fetchHistoryDuring(hass, ids, rangeStart, rangeEnd, { significantChangesOnly });
  const points = {
    pv: historyToPoints(historyRowsForEntity(hist, ent.pv)),
    feedIn: historyToPoints(historyRowsForEntity(hist, ent.feedIn)),
    load: historyToPoints(historyRowsForEntity(hist, ent.load)),
    discharge: historyToPoints(historyRowsForEntity(hist, ent.discharge)),
    charge: historyToPoints(historyRowsForEntity(hist, ent.charge)),
    grid: historyToPoints(historyRowsForEntity(hist, ent.grid)),
  };
  return { ent, points };
}

function formatFoxPower(w) {
  const abs = Math.abs(w);
  if (abs < 1000) return `${Math.round(abs)} W`;
  const kw = abs / 1000;
  return kw < 10 ? `${kw.toFixed(2)} kW` : `${kw.toFixed(1)} kW`;
}

function formatW(w) {
  const kw = Math.abs(w) / 1000;
  return kw < 10 ? `${kw.toFixed(2)} kW` : `${kw.toFixed(1)} kW`;
}

function timeForInput(value) {
  if (!value) return "00:00";
  const p = String(value).split(":");
  return `${p[0].padStart(2, "0")}:${(p[1] || "00").padStart(2, "0")}`;
}

function modeClass(mode) {
  const m = String(mode || "").toLowerCase();
  if (m.includes("storm")) return "mode-storm";
  if (m.includes("outage")) return "mode-outage";
  if (m.includes("override") || m.includes("tariff") || m.includes("forecast")) return "mode-override";
  if (m === "manual") return "mode-manual";
  return "mode-baseline";
}

function readEnergyFlows(hass, plant, plantState) {
  const map = resolveEntityMap(hass, plant, plantState);
  const pvW = statePowerWatts(hass, map.pv_power);
  const loadW = Math.abs(statePowerWatts(hass, map.load_power));
  const gridImportW = statePowerWatts(hass, map.grid_import);
  const gridExportW = statePowerWatts(hass, map.grid_export);
  const batteryW = statePowerWatts(hass, map.battery_power);
  let batteryStatus = "Idle";
  const statusEntity = map.battery_status;
  if (statusEntity && hass.states[statusEntity]) {
    batteryStatus = hass.states[statusEntity].state;
  } else if (batteryW > 50) batteryStatus = "Discharging";
  else if (batteryW < -50) batteryStatus = "Charging";
  return {
    pvW: Math.max(0, pvW),
    loadW,
    gridImportW: Math.max(0, gridImportW),
    gridExportW: Math.max(0, gridExportW),
    batteryW,
    batterySoc: stateNumber(hass, map.battery_soc),
    batteryStatus,
  };
}

function sunPrevNext(hass, key) {
  const raw = hass?.states?.["sun.sun"]?.attributes?.[`next_${key}`];
  if (!raw) return null;
  const nxt = new Date(raw);
  if (Number.isNaN(nxt.getTime())) return null;
  return { prev: new Date(nxt.getTime() - 86_400_000), nxt };
}

function sunLastEvent(hass, key, now) {
  const pair = sunPrevNext(hass, key);
  if (!pair) return null;
  return now >= pair.nxt ? pair.nxt : pair.prev;
}

function sunNextEvent(hass, key, now) {
  const pair = sunPrevNext(hass, key);
  if (!pair) return null;
  return now >= pair.nxt ? new Date(pair.nxt.getTime() + 86_400_000) : pair.nxt;
}

function resolveFlowScenePeriodFromSun(hass) {
  const sun = hass?.states?.["sun.sun"];
  if (!sun?.state || sun.state === "unknown" || sun.state === "unavailable") return null;
  return sun.state === "above_horizon" ? "day" : "night";
}

/** Parse CSS color to relative luminance (0–1); higher = lighter background. */
function cssColorLuminance(color) {
  const raw = String(color || "").trim();
  if (!raw) return null;
  let r = 0;
  let g = 0;
  let b = 0;
  const hex = raw.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const h = hex[1].length === 3
      ? hex[1].split("").map((c) => c + c).join("")
      : hex[1];
    r = parseInt(h.slice(0, 2), 16);
    g = parseInt(h.slice(2, 4), 16);
    b = parseInt(h.slice(4, 6), 16);
  } else {
    const rgb = raw.match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i);
    if (!rgb) return null;
    r = Number(rgb[1]);
    g = Number(rgb[2]);
    b = Number(rgb[3]);
  }
  const lin = (c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** True when Home Assistant UI is in dark mode (Fox _dark art + black stage). */
function resolveHaUiDark(hass) {
  if (typeof hass?.themes?.darkMode === "boolean") {
    return hass.themes.darkMode;
  }
  try {
    const root = document.documentElement;
    const bg = getComputedStyle(root).getPropertyValue("--primary-background-color").trim();
    const lum = cssColorLuminance(bg);
    if (lum != null) return lum < 0.45;
  } catch (_) {
    /* panel may run before theme vars are ready */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function normalizeFlowSceneTheme(theme) {
  if (!theme || typeof theme !== "string") return null;
  if (FLOW_SCENE_BG_THEMES.has(theme)) return theme;
  if (theme.startsWith("day_")) return "day_dark";
  if (theme.startsWith("night_")) return "night_dark";
  return null;
}

function resolveFlowSceneBgTheme(hass, plantState) {
  const period = resolveFlowScenePeriodFromSun(hass)
    || (() => {
      const t = normalizeFlowSceneTheme(plantState?.flow_scene_theme);
      if (!t) return null;
      return t.startsWith("day_") ? "day" : "night";
    })()
    || "day";
  const suffix = resolveHaUiDark(hass) ? "dark" : "light";
  return `${period}_${suffix}`;
}

/** Backdrop and overlays share the same Fox UI-theme + sun variant. */
function flowSceneOverlayTheme(bgTheme) {
  return bgTheme;
}

/** Baked sky+house at 1024×1017 — PV/AIO scene layers unchanged (tuned paths). */
function flowSceneLayerUrl(layer, bgTheme, overlayTheme = flowSceneOverlayTheme(bgTheme)) {
  if (layer === "backdrop") {
    return `/foxess_plant_panel/flow_home_bg_scene_${bgTheme}.png?v=${FLOW_SCENE_ASSET_VER}`;
  }
  const theme = overlayTheme;
  return `/foxess_plant_panel/flow_${layer}_scene_${theme}.png?v=${FLOW_SCENE_ASSET_VER}`;
}

function inferBatteryFlowDirection(flows, threshold = FLOW_SCENE_PV_THRESHOLD_W) {
  const st = String(flows.batteryStatus || "").toLowerCase();
  if (st.includes("discharg")) {
    return { discharging: true, charging: false };
  }
  if (st.includes("charg")) {
    return { discharging: false, charging: true };
  }
  const w = flows.batteryW;
  return {
    discharging: w > threshold,
    charging: w < -threshold,
  };
}

function computeFlowLines(flows, threshold = FLOW_SCENE_PV_THRESHOLD_W) {
  const lines = [];
  const hasPv = flows.pvW > threshold;
  const hasGridIn = flows.gridImportW > threshold;
  const hasGridOut = flows.gridExportW > threshold;
  const { discharging, charging } = inferBatteryFlowDirection(flows, threshold);
  const hasLoad = flows.loadW > threshold;

  const aioToHub = hasPv || discharging || hasGridOut;
  if (hasPv) {
    lines.push({ id: "solar-aio" });
  }
  if (hasGridIn) lines.push({ id: "grid-hub" });
  if (hasGridOut) lines.push({ id: "hub-grid" });
  if (aioToHub) lines.push({ id: "aio-hub" });
  else if (charging) lines.push({ id: "hub-aio", reverse: true });
  if (hasLoad && (hasGridOut || hasGridIn || aioToHub || charging || hasPv)) {
    lines.push({ id: "hub-home" });
  }
  return lines;
}

async function fetchPlantState(hass, plantId) {
  return hass.connection.sendMessagePromise({
    type: "foxess_plant/plant_state",
    plant_id: plantId,
  });
}

async function fetchTriggerCandidates(hass) {
  return hass.connection.sendMessagePromise({
    type: "foxess_plant/trigger_candidates",
  });
}

const DEFAULT_BRAND_DOMAIN = "foxess_plant";
const DEFAULT_MODBUS_BRAND_DOMAIN = "foxess_modbus";
const DEFAULT_BRAND_ICON_STATIC = "/foxess_plant_panel/icon.png";
const DEVICE_EVO_IMAGE_STATIC = "/foxess_plant_panel/evo10.png?v=15";
const STORM_HERO_IMAGE_STATIC = "/foxess_plant_panel/bg_storm_safe_charging.png?v=5";
const SMART_CHARGE_HERO_IMAGE_STATIC = "/foxess_plant_panel/bg_smart_charge.png?v=3";
const SMART_CHARGE_MODE_ICON_VER = 3;
const SMART_CHARGE_MODE_ICONS = {
  max_safety: `/foxess_plant_panel/smart-charge-max-safety.png?v=${SMART_CHARGE_MODE_ICON_VER}`,
  max_profit: `/foxess_plant_panel/smart-charge-max-profit.png?v=${SMART_CHARGE_MODE_ICON_VER}`,
  max_green: `/foxess_plant_panel/smart-charge-max-green.png?v=${SMART_CHARGE_MODE_ICON_VER}`,
};
const OCTOPUS_GREENER_CARD_TITLE = "Octopus Green Nights 24h Forecast";
const OCTOPUS_UPCOMING_WEEK_CARD_TITLE = "Octopus Greener Nights Week Ahead";
const OCTOPUS_GREENER_DAILY_INTRO =
  "Cut your carbon footprint by using electricity off-peak, and when it's windy and sunny. The graph below forecasts the carbon intensity of the grid, the greener the grid, the greener the graph and the cleaner the energy at that time. The National Green Line indicates when we deem the Low Carbon Score officially green.";
const OCTOPUS_GREENER_DAILY_HELP =
  "Your Low Carbon Score is based on National Energy System Operator\u2019s (NESO) annual forecast for carbon density. The lower the carbon density, the greener the grid and the higher the Low Carbon Score. The National Green Line, refers to carbon intensity (and corresponding Low Carbon Score) when NESO deems the grid green. As of 2025, they deem the anything below 99gCO\u2082/kWh as low, and therefore greener.";
const BANNER_HERO_WIDE_WIDTH = 1024;
const BANNER_HERO_WIDE_HEIGHT = 512;
const STORM_HERO_WIDTH = BANNER_HERO_WIDE_WIDTH;
const STORM_HERO_HEIGHT = BANNER_HERO_WIDE_HEIGHT;
const SMART_CHARGE_HERO_WIDTH = BANNER_HERO_WIDE_WIDTH;
const SMART_CHARGE_HERO_HEIGHT = BANNER_HERO_WIDE_HEIGHT;
const STORM_WEATHER_ICON_VER = 1;

function formatStormMatchedCategories(categories) {
  if (!categories?.length) return "";
  return categories.map((c) => c.label).join(", ");
}

function formatStormGoogleConditionToken(condition) {
  if (condition == null || condition === "") return "—";
  return String(condition);
}

function formatStormForecastActiveLine(nextStorm) {
  if (!nextStorm) return "";
  const hours = esc(String(nextStorm.hours_until));
  const token = esc(formatStormGoogleConditionToken(nextStorm.condition));
  const labels = formatStormMatchedCategories(nextStorm.matched_categories);
  if (labels) {
    return `Forecast: <strong>${esc(labels)}</strong> in ~${hours}h (Google hourly: <code>${token}</code>) — <strong style="color:var(--fp-amber)">pre-charge active</strong>. Uncheck that category below to stop.`;
  }
  return `Forecast: storm in ~${hours}h (<code>${token}</code>) — <strong style="color:var(--fp-amber)">pre-charge active</strong>.`;
}

function formatStormNowLine(cond) {
  if (!cond) return "";
  const token = esc(formatStormGoogleConditionToken(cond.type ?? cond.text));
  const labels = formatStormMatchedCategories(cond.matched_categories);
  const stormNow = cond.is_storm
    ? '<strong style="color:var(--fp-amber)">storm now</strong>'
    : "clear now";
  if (labels && cond.is_storm) {
    return `Now: <strong>${esc(labels)}</strong> (Google: <code>${token}</code>) — ${stormNow}.`;
  }
  return `Now: <strong>${esc(cond.label || cond.text)}</strong> (<code>${token}</code>) — ${stormNow}.`;
}

const DEFAULT_STORM_SOLCAST_MARGIN = 1.35;
const DEFAULT_STORM_SOLCAST_MIN_SOC = 90;

function stormSolcastActionClass(action) {
  if (action === "pv_only") return "storm-solcast-precheck--ok";
  if (action === "full_grid") return "storm-solcast-precheck--warn";
  return "storm-solcast-precheck--neutral";
}

function formatStormSolcastMetrics(precheck) {
  if (!precheck) return "";
  const parts = [];
  if (precheck.soc_pct != null) parts.push(`Battery ${precheck.soc_pct}%`);
  if (precheck.deficit_kwh != null) parts.push(`Gap ${precheck.deficit_kwh} kWh → ${precheck.target_soc_pct ?? 100}%`);
  if (precheck.hours_until_storm != null) parts.push(`Storm ~${precheck.hours_until_storm}h`);
  if (precheck.pv_before_storm_kwh != null) {
    parts.push(`Solcast PV ${precheck.pv_before_storm_kwh} kWh`);
  }
  if (precheck.effective_pv_kwh != null && precheck.safety_margin != null) {
    parts.push(`Effective ${precheck.effective_pv_kwh} kWh (÷ ${precheck.safety_margin} margin)`);
  }
  return parts.length ? parts.map((p) => esc(p)).join(" · ") : "";
}

const STORM_WEATHER_CATEGORY_FALLBACK = [
  { id: "extreme_heat", label: "Extreme heat", icon: "storm_weather_extreme_heat.png" },
  { id: "extreme_cold", label: "Extreme cold", icon: "storm_weather_extreme_cold.png" },
  { id: "heavy_rain", label: "Heavy rain", icon: "storm_weather_heavy_rain.png" },
  { id: "typhoons", label: "Typhoons", icon: "storm_weather_typhoons.png" },
  { id: "dust_storm", label: "Dust storm", icon: "storm_weather_dust_storm.png" },
  { id: "thunderstorms", label: "Thunderstorms", icon: "storm_weather_thunderstorms.png" },
  { id: "wildfires", label: "Wildfires", icon: "storm_weather_wildfires.png" },
  { id: "hailstorms", label: "Hailstorms", icon: "storm_weather_hailstorms.png" },
  { id: "ice_storms", label: "Ice storms", icon: "storm_weather_ice_storms.png" },
];

function stormWeatherIconUrl(iconFile) {
  return `/foxess_plant_panel/${iconFile}?v=${STORM_WEATHER_ICON_VER}`;
}
const IMPACT_ICON_ASSET_VER = 1;
const IMPACT_ICON_PATHS = {
  co2: "/foxess_plant_panel/impact_environment_co2.png",
  tree: "/foxess_plant_panel/impact_environment_planted.png",
  oil: "/foxess_plant_panel/impact_environment_oil.png",
};

function impactIconUrl(icon) {
  const path = IMPACT_ICON_PATHS[icon];
  return path ? `${path}?v=${IMPACT_ICON_ASSET_VER}` : "";
}
let _brandsAccessToken;

async function ensureBrandsAccessToken(hass) {
  if (_brandsAccessToken || !hass?.connection) return _brandsAccessToken;
  try {
    const res = await hass.connection.sendMessagePromise({ type: "brands/access_token" });
    _brandsAccessToken = res?.token;
  } catch {
    /* brands API optional on older HA */
  }
  return _brandsAccessToken;
}

function buildBrandIconUrl(domain) {
  const base = `/api/brands/integration/${domain}/icon.png`;
  const url = new URL(base, location.origin);
  if (_brandsAccessToken) url.searchParams.set("token", _brandsAccessToken);
  return url.toString();
}

async function callService(hass, domain, service, data) {
  await hass.callService(domain, service, data, undefined, { blocking: true });
}

async function callServiceWithResponse(hass, domain, service, serviceData, target) {
  const targetPayload = target ? { ...target } : {};
  if (targetPayload.entity_id && !Array.isArray(targetPayload.entity_id)) {
    targetPayload.entity_id = [targetPayload.entity_id];
  }
  if (typeof hass.callWS === "function") {
    const result = await hass.callWS({
      type: "call_service",
      domain,
      service,
      service_data: serviceData || {},
      target: targetPayload,
      return_response: true,
    });
    return result?.response ?? result;
  }
  return hass.callService(domain, service, serviceData, targetPayload, true, true);
}

const SOC_MIN_PCT = 10;

const SOC_THUMBS = [
  { key: "min_soc", label: "Off-grid min", short: "Off-grid", color: "#e53935" },
  { key: "min_soc_on_grid", label: "System min", short: "On-grid", color: "#f9a825" },
  { key: "max_soc", label: "System max", short: "Max", color: "#2e7d32" },
];

/** Enforce 10–100%, min ≤ system min ≤ max (inverter rejects below 10%). */
function clampSocDraft(d) {
  let min = Math.round(Number(d.min_soc) || SOC_MIN_PCT);
  let mid = Math.round(Number(d.min_soc_on_grid) || SOC_MIN_PCT);
  let max = Math.round(Number(d.max_soc) || 100);
  min = Math.max(SOC_MIN_PCT, Math.min(100, min));
  mid = Math.max(SOC_MIN_PCT, Math.min(100, mid));
  max = Math.max(SOC_MIN_PCT, Math.min(100, max));
  if (mid < min) mid = min;
  if (max < mid) max = mid;
  d.min_soc = min;
  d.min_soc_on_grid = mid;
  d.max_soc = max;
  return d;
}

function tripleSocBatteryFillMarkup(liveSoc) {
  const live = Math.max(0, Math.min(100, Math.round(liveSoc ?? 0)));
  if (live >= 99) {
    return `<div class="triple-soc-battery-fill is-full"></div>`;
  }
  const h = Math.max(4, live);
  return `<div class="triple-soc-battery-fill" style="height:max(4px,calc((100% - 8px) * ${h} / 100))"></div>`;
}

function validateSocLimits(draft, liveSoc) {
  const errors = [];
  const warnings = [];
  if (!draft) return { errors: ["SOC limits unavailable."], warnings: [] };
  const min = Math.round(Number(draft.min_soc));
  const mid = Math.round(Number(draft.min_soc_on_grid));
  const max = Math.round(Number(draft.max_soc));
  if (![min, mid, max].every((v) => Number.isFinite(v))) {
    return { errors: ["Enter a whole-number percentage for each SOC limit."], warnings: [] };
  }
  if (min < SOC_MIN_PCT || mid < SOC_MIN_PCT || max < SOC_MIN_PCT) {
    errors.push(`All SOC limits must be at least ${SOC_MIN_PCT}%.`);
  }
  if (min > 100 || mid > 100 || max > 100) {
    errors.push("SOC limits cannot exceed 100%.");
  }
  if (min > mid) {
    errors.push(`Off-grid min (${min}%) must be ≤ system min (${mid}%).`);
  }
  if (mid > max) {
    errors.push(`System min (${mid}%) must be ≤ system max (${max}%).`);
  }
  const live = Math.ceil(Number(liveSoc));
  if (Number.isFinite(live) && live > 0 && max < live) {
    warnings.push(
      `System max (${max}%) is below the current battery level (${live}%). The inverter may reject this — Save will show the error if it does.`
    );
  }
  return { errors, warnings };
}

function renderSocResultHtml(results) {
  if (!results?.length) return "";
  const items = results
    .map((row) => {
      const ok = row.success;
      const icon = ok ? "✓" : "✕";
      const cls = ok ? "ok" : "err";
      const detail = row.skipped && ok ? "Already set" : row.message || (ok ? "Operation successful" : "Failed");
      return `<li class="soc-result-item ${cls}">
<span class="soc-result-icon" aria-hidden="true">${icon}</span>
<span class="soc-result-text"><strong>${esc(row.label || row.key)}</strong> ${esc(detail)}</span>
</li>`;
    })
    .join("");
  return `<div class="soc-result-panel" role="dialog" aria-label="SOC save result">
<div class="soc-result-head">
<strong>Result</strong>
<button type="button" class="soc-result-close" data-action="soc-result-close" aria-label="Close result">×</button>
</div>
<ul class="soc-result-list">${items}</ul>
</div>`;
}

function renderSocFeedbackHtml(validation, saveError, saveResults) {
  const parts = [];
  if (validation?.errors?.length) {
    parts.push(
      `<div class="soc-validation" role="alert">${validation.errors.map((msg) => `<p>${esc(msg)}</p>`).join("")}</div>`
    );
  }
  if (validation?.warnings?.length) {
    parts.push(
      `<div class="soc-validation warn" role="status">${validation.warnings.map((msg) => `<p>${esc(msg)}</p>`).join("")}</div>`
    );
  }
  if (saveResults?.length) {
    parts.push(renderSocResultHtml(saveResults));
  }
  if (saveError) {
    parts.push(`<div class="soc-validation" role="alert"><p>${esc(saveError)}</p></div>`);
  }
  return parts.join("");
}

/** Map pointer X on the track to an SOC % (track left/right = 0/100 visually). */
function socPctFromTrackPointer(clientX, trackRect, grabOffset = 0) {
  if (!trackRect?.width) return SOC_MIN_PCT;
  const pointerPct = ((clientX - trackRect.left) / trackRect.width) * 100;
  return Math.round(Math.max(SOC_MIN_PCT, Math.min(100, pointerPct + grabOffset)));
}

/** Apply drag to the active thumb first, then push siblings (Fox-app style). */
function applySocDrag(d, thumb, pct) {
  const p = Math.max(SOC_MIN_PCT, Math.min(100, Math.round(pct)));
  if (thumb === "min_soc") {
    d.min_soc = p;
    if (d.min_soc_on_grid < p) d.min_soc_on_grid = p;
    if (d.max_soc < d.min_soc_on_grid) d.max_soc = d.min_soc_on_grid;
  } else if (thumb === "min_soc_on_grid") {
    d.min_soc_on_grid = p;
    if (d.min_soc > p) d.min_soc = p;
    if (d.max_soc < p) d.max_soc = p;
  } else if (thumb === "max_soc") {
    d.max_soc = p;
    if (d.min_soc_on_grid > p) d.min_soc_on_grid = p;
    if (d.min_soc > d.min_soc_on_grid) d.min_soc = d.min_soc_on_grid;
  }
  return clampSocDraft(d);
}

const STYLES = `
:host {
  display: block;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-y: contain;
  font-family: var(--ha-font-family, Roboto, sans-serif);
  background: var(--primary-background-color);
  color: var(--primary-text-color);
  --fp-radius: 14px;
  --fp-accent: var(--primary-color, #03a9f4);
  --fp-green: #2e7d32;
  --fp-amber: #f9a825;
  --fp-red: #e53935;
}
.shell {
  position: relative;
  display: block;
  height: auto;
  min-height: 100%;
  overflow: visible;
  background: var(--primary-background-color);
}
.page-header {
  flex-shrink: 0;
  position: sticky; top: 0; z-index: 10;
  border-bottom: 1px solid var(--divider-color);
  background: var(--app-header-background-color, var(--primary-background-color));
}
.shell.has-subnav .main-inner { padding-top: 28px; }
.panel-header-top {
  display: flex;
  align-items: flex-start;
  gap: 0;
}
.panel-ha-menu-btn {
  display: none;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin: 8px 0 0 4px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--primary-text-color);
  cursor: pointer;
}
.panel-ha-menu-btn:hover {
  background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
}
.panel-ha-menu-btn:focus-visible {
  outline: 2px solid var(--primary-color, #894bfc);
  outline-offset: 2px;
}
:host(.narrow) .panel-ha-menu-btn,
.shell.narrow .panel-ha-menu-btn {
  display: inline-flex;
}
@media (max-width: 870px) {
  .panel-ha-menu-btn { display: inline-flex; }
  .panel-brand-row { padding: 12px 12px 4px 0; }
}
.panel-brand-row {
  display: flex; align-items: center; gap: 12px;
  flex: 1; min-width: 0;
  padding: 12px 16px 4px;
}
:host(.narrow) .panel-brand-row,
.shell.narrow .panel-brand-row {
  padding: 12px 12px 4px 0;
}
.panel-brand-icon {
  width: 40px; height: 40px; flex-shrink: 0;
  object-fit: contain; border-radius: 8px;
}
.panel-brand-title {
  font-size: 18px; font-weight: 600; line-height: 1.2;
  color: var(--primary-text-color);
}
.panel-brand-sub {
  font-size: 12px; color: var(--secondary-text-color); margin-top: 2px;
}
.plant-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 8px 0;
}
.plant-row label {
  font-size: 12px; color: var(--secondary-text-color);
  font-weight: 500;
  white-space: nowrap;
}
.plant-row select {
  font-family: inherit;
  font-size: 13px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--divider-color);
  background: var(--card-background-color);
  color: var(--primary-text-color);
  width: 180px;
}
.tab-bar {
  display: flex; align-items: stretch; gap: 0;
  padding: 0 8px; overflow-x: auto; -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.tab-bar::-webkit-scrollbar { display: none; }
.tab {
  flex-shrink: 0;
  padding: 14px 20px 12px;
  border: none; border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--secondary-text-color);
  font-size: 14px; font-weight: 500; font-family: inherit;
  cursor: pointer; white-space: nowrap;
  position: relative; z-index: 1;
}
.tab:hover { color: var(--primary-text-color); }
.tab.active {
  color: var(--primary-text-color);
  font-weight: 600;
  border-bottom-color: var(--primary-text-color);
}
.tab-bar.sub { padding: 0 16px; border-top: 1px solid var(--divider-color); background: var(--secondary-background-color, transparent); }
.tab-bar.sub .tab { padding: 10px 16px 8px; font-size: 13px; }
.main {
  display: block;
  width: 100%;
  overflow: visible;
}
.main-inner {
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  padding: 20px 24px 40px;
  box-sizing: border-box;
  container-type: inline-size;
  container-name: fp-main;
}
.shell.view-device-new .main-inner {
  max-width: calc(1100px + ${DEVICE_NEW_MAIN_WIDTH_EXTRA_PX}px);
}
.shell.narrow .main-inner { padding: 16px; }
.shell.narrow .tab { padding: 12px 14px 10px; font-size: 13px; }
.header { margin-bottom: 20px; }
.header h1 { margin: 0; font-size: 26px; font-weight: 600; letter-spacing: -0.02em; }
.header p { margin: 6px 0 0; color: var(--secondary-text-color); font-size: 14px; }
.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}
.overview-header { margin-bottom: 16px; }
.overview-model { margin: 4px 0 0; font-size: 15px; font-weight: 500; color: var(--secondary-text-color); letter-spacing: 0.01em; }
.panel-build-footer {
  position: absolute; right: 12px; bottom: 8px; z-index: 1;
  margin: 0; padding: 0;
  font-size: 9px; line-height: 1.3;
  color: var(--secondary-text-color); opacity: 0.42;
  letter-spacing: 0.02em; white-space: nowrap;
  pointer-events: none;
}
.panel-stale-banner { margin-bottom: 14px; }
.overview-status-block { margin-top: 12px; }
.overview-status-row {
  display: flex; align-items: center; flex-wrap: wrap; gap: 6px 8px; line-height: 1.35;
}
.overview-status-row .fox-device-new-check-pill { flex-shrink: 0; }
.fox-inverter-state-pill-link {
  display: inline-flex; align-items: center; padding: 0; margin: 0; border: none;
  background: transparent; font: inherit; color: inherit; cursor: pointer;
  border-radius: 999px;
}
.fox-inverter-state-pill-link:hover { filter: brightness(1.08); }
.fox-inverter-state-pill-link:focus-visible {
  outline: 2px solid var(--primary-color, #894bfc); outline-offset: 2px;
}
.overview-control-hint { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
.overview-weather {
  display: flex; align-items: center; gap: 6px; margin-top: 8px;
  font-size: 14px; font-weight: 600; color: var(--primary-text-color); line-height: 1.2;
}
.overview-weather-icon { width: 18px; height: 18px; flex-shrink: 0; display: block; object-fit: contain; }
.overview-weather-temp { letter-spacing: -0.01em; }
.overview-weather-label { font-size: 13px; font-weight: 500; color: var(--secondary-text-color); }
.hourly-weather-card { margin-top: 14px; padding-bottom: 12px; }
.hourly-weather-card-inner { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.hourly-weather-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.hourly-weather-title {
  display: inline-flex; align-items: center; gap: 8px; margin: 0;
  font-size: 15px; font-weight: 600; letter-spacing: 0; text-transform: none;
  color: var(--primary-text-color);
}
.hourly-weather-title-icon { width: 18px; height: 18px; flex-shrink: 0; opacity: 0.85; }
.hourly-weather-nav { display: inline-flex; gap: 6px; flex-shrink: 0; }
.hourly-weather-nav-btn {
  width: 32px; height: 32px; border-radius: 999px; border: none;
  background: var(--secondary-background-color, rgba(127,127,127,0.12));
  color: var(--primary-text-color); font-size: 18px; line-height: 1;
  cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
}
.hourly-weather-nav-btn:hover { background: color-mix(in srgb, var(--primary-text-color) 8%, var(--secondary-background-color)); }
.hourly-weather-scroll-wrap {
  margin: 0 -4px; overflow: hidden;
}
.hourly-weather-scroll {
  display: flex; gap: 0; overflow-x: auto; overflow-y: hidden;
  padding: 2px 4px 8px; scrollbar-width: none;
  -webkit-overflow-scrolling: touch; overscroll-behavior-x: contain;
  touch-action: pan-x;
}
.hourly-weather-scroll::-webkit-scrollbar { display: none; }
.hourly-weather-col {
  flex: 0 0 72px; display: flex; flex-direction: column; align-items: center;
  gap: 8px; text-align: center;
}
.hourly-weather-temp {
  font-size: 18px; font-weight: 600; line-height: 1.1; color: var(--primary-text-color);
  font-variant-numeric: tabular-nums;
}
.hourly-weather-icon-wrap { display: flex; align-items: center; justify-content: center; min-height: 28px; }
.hourly-weather-icon { width: 28px; height: 28px; display: block; object-fit: contain; }
.hourly-weather-precip {
  font-size: 12px; line-height: 1.2; color: var(--secondary-text-color);
  font-variant-numeric: tabular-nums; min-height: 14px;
}
.hourly-weather-time {
  font-size: 12px; line-height: 1.2; color: var(--secondary-text-color);
  font-variant-numeric: tabular-nums;
}
.hourly-weather-time--now { color: var(--primary-text-color); font-weight: 600; }
.hourly-weather-empty { margin: 0; padding: 8px 0 4px; }
.mode-banner-row {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 14px;
}
.mode-banner-hint { font-size: 13px; color: var(--secondary-text-color); }
.back-btn { background: none; border: none; color: var(--fp-accent); cursor: pointer; font-size: 14px; padding: 0 0 14px; font-family: inherit; }
.card {
  background: var(--card-background-color); border-radius: var(--fp-radius);
  padding: 18px 20px; margin-bottom: 14px;
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.08));
  border: 1px solid var(--divider-color, transparent);
}
.card-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--secondary-text-color); margin: 0 0 14px; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); gap: 12px; }
.overview-hero-row {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 14px;
  margin-bottom: 14px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
.overview-hero-scene {
  width: 100%; max-width: none; margin: 0; min-width: 0; align-self: stretch;
  display: flex; flex-direction: column; gap: 12px; min-height: 0;
}
.overview-hero-scene-slot { flex: 1 1 auto; min-height: 0; }
.overview-hero-scene .scene-card--fox-flow { margin-bottom: 0; width: 100%; height: 100%; }
.overview-system-status-slot {
  flex: 0 0 auto;
  width: 100%;
  display: flex;
  align-items: stretch;
}
.overview-automation-status-slot {
  flex: 0 0 auto;
  width: 100%;
  display: flex;
  align-items: stretch;
}
.overview-automation-status-card {
  flex: 1 1 auto;
  width: 100%;
  min-height: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: row;
  align-items: stretch;
  background: var(--card-background-color);
  border-radius: var(--fp-radius);
  border: 1px solid var(--divider-color, transparent);
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06));
  overflow: hidden;
}
.overview-automation-half {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  padding: 10px 12px;
  margin: 0;
  border: none;
  background: transparent;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  min-height: 0;
}
.overview-automation-half:hover { background: var(--secondary-background-color); }
.overview-automation-half:focus-visible {
  outline: 2px solid var(--primary-color, #894bfc);
  outline-offset: -2px;
  z-index: 1;
}
.overview-automation-half + .overview-automation-half {
  border-top: none;
  border-left: 1px solid var(--divider-color, rgba(127,127,127,0.25));
}
.overview-automation-half-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 6px;
  min-height: 20px;
}
.overview-automation-half-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--secondary-text-color);
  letter-spacing: 0.01em;
  min-width: 0;
}
.overview-automation-status-pill {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  line-height: 1.3;
}
.overview-automation-status-pill--off {
  background: var(--secondary-background-color);
  color: var(--secondary-text-color);
}
.overview-automation-status-pill--idle {
  background: color-mix(in srgb, var(--fp-accent) 14%, transparent);
  color: var(--fp-accent);
}
.overview-automation-status-pill--watch {
  background: color-mix(in srgb, var(--fp-amber) 18%, transparent);
  color: var(--fp-amber);
}
.overview-automation-status-pill--armed {
  background: color-mix(in srgb, #52c41a 18%, transparent);
  color: #52c41a;
}
.overview-automation-half-detail {
  font-size: 12px;
  line-height: 1.35;
  color: var(--secondary-text-color);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.overview-energy-band {
  display: flex; flex-direction: column; gap: 14px;
  width: 100%; margin-bottom: 14px; min-width: 0;
}
.overview-energy-breakdown.breakdown-card { margin-top: 0; margin-bottom: 0; }
.overview-energy-stats-row { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.overview-energy-balance-card { margin-top: 0; margin-bottom: 0; }
.overview-balance-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  align-items: stretch;
}
.overview-balance-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 12px;
  align-items: center;
  padding: 4px 14px 6px 0;
  min-width: 0;
}
.overview-balance-row + .overview-balance-row {
  border-left: 1px solid var(--divider-color, rgba(127,127,127,0.25));
  padding-left: 14px;
  padding-right: 0;
}
.overview-balance-copy { min-width: 0; }
.overview-balance-heading {
  font-size: 14px; color: var(--secondary-text-color); margin: 0 0 4px; font-weight: 500;
}
.overview-balance-total {
  font-size: 24px; font-weight: 700; margin: 0; line-height: 1.05; letter-spacing: -0.02em;
}
.overview-balance-total span {
  font-size: 14px; font-weight: 500; color: var(--secondary-text-color); margin-left: 4px;
}
.overview-balance-spark {
  width: 132px; max-width: 42vw; flex-shrink: 0; display: flex; align-items: center; justify-content: flex-end;
}
.overview-hero-daily-slot {
  display: flex; flex-direction: column; gap: 12px;
  width: 100%; max-width: none; min-width: 0;
  box-sizing: border-box; align-self: stretch; min-height: 0; height: 100%;
}
.overview-hero-daily-charts {
  display: grid; grid-template-rows: 1fr 1fr; gap: 12px;
  flex: 1 1 auto; min-height: 0; width: 100%; height: 100%;
}
.overview-hero-daily-charts .overview-daily-card { min-height: 0; height: 100%; }
.overview-system-status-card {
  flex: 1 1 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--card-background-color); border-radius: var(--fp-radius);
  border: 1px solid var(--divider-color, transparent);
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06));
  padding: 12px 14px; width: 100%; box-sizing: border-box;
}
.overview-system-status-head {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  margin-bottom: 6px; min-height: 24px;
}
.overview-system-status-title {
  font-size: 12px; font-weight: 600; color: var(--secondary-text-color); letter-spacing: 0.01em;
}
.overview-system-status-details {
  flex-shrink: 0; padding: 4px 12px; border-radius: 999px;
  border: 1px solid var(--divider-color, rgba(127,127,127,0.35));
  background: transparent; color: var(--secondary-text-color);
  font-size: 12px; font-weight: 500; line-height: 1.2; cursor: pointer; font-family: inherit;
}
.overview-system-status-details:hover { background: var(--secondary-background-color); }
.overview-system-status-details:focus-visible {
  outline: 2px solid var(--primary-color, #894bfc); outline-offset: 2px;
}
.overview-system-status-body {
  display: flex; align-items: center; gap: 8px; min-height: 20px;
  flex: 1 1 auto;
  font-size: 13px; line-height: 1.35; color: var(--secondary-text-color);
}
.overview-system-status-body--loading { color: var(--secondary-text-color); opacity: 0.85; }
.overview-system-status-glyph { width: 16px; height: 16px; flex-shrink: 0; display: block; }
.overview-system-status-text--fault { color: var(--primary-text-color); font-weight: 500; }
.overview-daily-card {
  background: var(--card-background-color); border-radius: var(--fp-radius);
  border: 1px solid var(--divider-color, transparent);
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06));
  padding: 14px 14px 10px; min-width: 0; width: 100%; max-width: none;
  min-height: 0;
  box-sizing: border-box; text-align: left;
  cursor: pointer; font-family: inherit; color: inherit;
  display: flex; flex-direction: column;
}
.overview-daily-card:hover { background: var(--secondary-background-color); }
.overview-daily-card:has(.overview-daily-chart-wrap:hover) { background: var(--card-background-color); }
.overview-daily-hover-col { pointer-events: none; }
.overview-daily-head {
  display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px;
}
.overview-daily-title {
  font-size: 12px; font-weight: 600; color: var(--secondary-text-color); letter-spacing: 0.01em;
}
.overview-daily-chev { font-size: 16px; line-height: 1; color: var(--secondary-text-color); opacity: 0.55; }
.overview-daily-value {
  font-size: 22px; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 8px; line-height: 1.15;
  flex: 0 0 auto;
}
.overview-daily-chart-wrap {
  position: relative; width: 100%; flex: 1 1 auto; min-height: 0;
  display: flex; align-items: flex-end;
}
.overview-daily-chart { width: 100%; height: auto; max-height: 100%; display: block; }
.overview-daily-bar-hit { cursor: default; pointer-events: all; }
.overview-daily-tooltip {
  position: absolute; z-index: 2; pointer-events: none;
  transform: translate(-50%, calc(-100% - 4px));
  padding: 5px 9px; border-radius: 8px; font-size: 11px; font-weight: 600; line-height: 1.2;
  white-space: nowrap; color: var(--primary-text-color);
  background: var(--card-background-color);
  border: 1px solid var(--divider-color, rgba(127,127,127,0.35));
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
}
.overview-daily-tooltip[hidden] { display: none !important; }
.overview-daily-today-mark {
  font-weight: 600; fill: var(--secondary-text-color);
}
.overview-daily-today-line { stroke: rgba(127,127,127,0.35); stroke-width: 0.75; }
.overview-daily-day { fill: var(--secondary-text-color); opacity: 0.85; }
.overview-daily-loading {
  font-size: 13px; color: var(--secondary-text-color); padding: 24px 14px; text-align: center;
}
.overview-daily-empty {
  font-size: 12px; color: var(--secondary-text-color); line-height: 1.45; padding: 8px 0 0;
}
.breakdown-card { margin-top: 14px; padding-bottom: 8px; }
.statistics-card { padding-bottom: 16px; }
.statistics-card .card-title { margin-bottom: 12px; }
.forecast-accuracy-card { padding-bottom: 10px; }
.forecast-accuracy-card--compact .card-title { margin-bottom: 2px; }
.forecast-accuracy-sub {
  margin: 0 0 8px; font-size: 12px; line-height: 1.4; color: var(--secondary-text-color);
}
.forecast-accuracy-stats {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px 12px; margin-bottom: 6px;
}
.forecast-accuracy-stat label {
  display: block; font-size: 11px; color: var(--secondary-text-color); margin-bottom: 4px;
}
.forecast-accuracy-stat strong { font-size: 16px; font-weight: 700; letter-spacing: -0.02em; }
.forecast-accuracy-stat--high strong { color: #19D4DE; }
.forecast-accuracy-stat--low strong { color: #FF9F43; }
.forecast-accuracy-hint {
  margin: 0 0 6px; font-size: 11px; color: var(--secondary-text-color); line-height: 1.35;
}
.forecast-accuracy-empty {
  margin: 0; padding: 10px 8px; text-align: center; font-size: 12px; line-height: 1.4;
  color: var(--secondary-text-color); border-radius: var(--fp-radius);
  border: 1px dashed var(--divider-color); background: var(--card-background-color);
}
.forecast-accuracy-loading {
  border-style: solid;
  border-color: color-mix(in srgb, var(--primary-color) 28%, var(--divider-color));
  animation: forecast-accuracy-pulse 1.4s ease-in-out infinite;
}
@keyframes forecast-accuracy-pulse {
  0%, 100% { opacity: 0.72; }
  50% { opacity: 1; }
}
.forecast-accuracy-card--compact .forecast-accuracy-empty { padding: 8px 6px; }
.forecast-accuracy-chart-wrap--cloud { margin-top: 6px; }
.forecast-accuracy-chart-wrap--cloud .forecast-accuracy-plot-head { margin-bottom: 6px; }
.forecast-accuracy-plot-head--stacked {
  flex-direction: column; align-items: flex-start; gap: 4px; margin-bottom: 4px;
}
.forecast-accuracy-plot-head--stacked .forecast-accuracy-legend { width: 100%; }
.forecast-accuracy-card--compact .forecast-accuracy-plot-head--stacked { margin-bottom: 6px; gap: 5px; }
.forecast-accuracy-plot--cloud .forecast-accuracy-chart-svg { margin-top: 2px; }
.forecast-accuracy-chart-plot { position: relative; width: 100%; margin: 0; line-height: 0; }
.forecast-accuracy-hit { cursor: crosshair; }
.forecast-accuracy-cloud-fill { pointer-events: none; }
.forecast-accuracy-cloud-line { pointer-events: none; }
.forecast-accuracy-axis-y--cloud,
.forecast-accuracy-y-label--cloud {
  fill: rgba(168, 178, 198, 0.95); font-size: 11px;
}
.forecast-accuracy-y-label--cloud { font-weight: 600; letter-spacing: 0.04em; }
.forecast-accuracy-chart-wrap { width: 100%; margin: 0; margin-top: 2px; }
.forecast-accuracy-plot { width: 100%; }
.forecast-accuracy-plot-head {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 4px 10px;
  margin-bottom: 2px;
}
.forecast-accuracy-plot-label {
  font-size: 11px; font-weight: 600; color: var(--secondary-text-color); letter-spacing: 0.04em;
}
.forecast-accuracy-legend--inline { margin-bottom: 0; }
.forecast-accuracy-legend {
  display: flex; flex-wrap: wrap; gap: 4px 10px; margin-bottom: 0; font-size: 10px;
  color: var(--secondary-text-color);
}
.forecast-accuracy-legend-item { display: inline-flex; align-items: center; gap: 5px; }
.forecast-accuracy-legend-item i {
  width: 12px; height: 2px; border-radius: 1px; display: inline-block;
}
.forecast-accuracy-chart-svg {
  width: 100%; height: auto; display: block; min-height: 168px;
  aspect-ratio: 1000 / 210;
}
.forecast-accuracy-card:not(.forecast-accuracy-card--compact) .forecast-accuracy-chart-svg {
  min-height: 190px;
  aspect-ratio: 1000 / 240;
}
.forecast-accuracy-revisions-wrap { margin-top: 14px; overflow-x: auto; }
.forecast-accuracy-revisions {
  width: 100%; border-collapse: collapse; font-size: 12px;
}
.forecast-accuracy-revisions th,
.forecast-accuracy-revisions td {
  padding: 8px 10px; text-align: left; border-bottom: 1px solid rgba(127, 127, 127, 0.18);
}
.forecast-accuracy-revisions th {
  font-size: 11px; font-weight: 600; color: var(--secondary-text-color);
}
.forecast-accuracy-delta--up { color: #19D4DE; }
.forecast-accuracy-delta--down { color: #FF9F43; }
.fox-analysis-forecast-accuracy-row { margin-top: 14px; }
.fox-analysis-forecast-accuracy-row .forecast-accuracy-card { margin-top: 0; }
.octopus-greener-card {
  /* Uses standard .card background — layout only */
}
.octopus-greener-card--compact .card-title { margin-bottom: 12px; }
.octopus-greener-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  margin-bottom: 12px;
}
.octopus-greener-head .card-title,
.octopus-greener-head .fox-analysis-summary-title {
  margin: 0;
  flex: 1 1 auto;
}
.octopus-greener-headline {
  font-weight: 700; font-size: 15px; line-height: 1.3; margin: 0 0 10px;
  color: var(--octopus-green-bar, #22c55e);
}
.octopus-greener-view-toggle {
  display: inline-flex; padding: 3px; border-radius: 999px;
  background: var(--secondary-background-color, rgba(127, 127, 127, 0.12));
  border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
}
.octopus-greener-view-btn {
  border: 0; background: transparent; color: var(--secondary-text-color); font-size: 12px; padding: 6px 12px;
  border-radius: 999px; cursor: pointer;
}
.octopus-greener-view-btn.active {
  background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff);
}
.octopus-greener-intro, .octopus-greener-hint, .octopus-greener-empty {
  font-size: 12px; line-height: 1.45; color: var(--secondary-text-color); margin: 8px 0 0;
}
.octopus-greener-intro--daily { margin-top: 0; line-height: 1.5; }
.octopus-greener-help-wrap {
  position: relative;
  display: inline-flex;
  vertical-align: middle;
  margin-left: 2px;
}
.octopus-greener-help-btn {
  width: 18px;
  height: 18px;
}
.octopus-greener-help-bubble {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 8px);
  transform: translateX(-50%);
  width: min(340px, 78vw);
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--card-background-color, #1c1c1c);
  border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.22));
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.28);
  font-size: 12px;
  line-height: 1.45;
  color: var(--primary-text-color);
  text-align: left;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  z-index: 8;
}
.octopus-greener-help-bubble::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: -6px;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--divider-color, rgba(127, 127, 127, 0.22));
}
.octopus-greener-help-wrap:hover .octopus-greener-help-bubble,
.octopus-greener-help-wrap:focus-within .octopus-greener-help-bubble {
  opacity: 1;
  visibility: visible;
}
.octopus-greener-error { color: var(--error-color, #f44336); font-size: 12px; margin: 8px 0 0; }
.octopus-greener-chart-wrap { margin-top: 12px; }
.octopus-greener-chart-plot { position: relative; }
.octopus-greener-chart-svg { width: 100%; height: auto; display: block; }
.octopus-greener-hit {
  position: absolute; top: 0; right: 0; bottom: 0; z-index: 1;
  left: var(--octopus-hit-left, calc(54 / 680 * 100%)); cursor: crosshair;
}
.octopus-greener-tooltip {
  position: absolute; z-index: 5; pointer-events: none; min-width: 148px; max-width: 220px;
  padding: 10px 14px; border-radius: 10px; transform: translate(-50%, -100%);
  background: var(--card-background-color, #1c1c1c);
  border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.22));
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.28);
  font-size: 13px; color: var(--primary-text-color);
}
.octopus-greener-tooltip::after {
  content: ""; position: absolute; left: 50%; bottom: -6px; transform: translateX(-50%);
  border: 6px solid transparent; border-top-color: var(--divider-color, rgba(127, 127, 127, 0.22));
}
.octopus-greener-tooltip-time { font-weight: 700; font-size: 15px; line-height: 1.2; margin-bottom: 6px; }
.octopus-greener-tooltip-score { font-size: 13px; line-height: 1.35; margin-bottom: 4px; }
.octopus-greener-tooltip-score strong { font-weight: 700; }
.octopus-greener-tooltip-gco2 { font-size: 12px; color: var(--secondary-text-color); line-height: 1.35; }
.octopus-greener-bar--hover { opacity: 0.82; stroke: var(--primary-text-color); stroke-width: 1; }
.octopus-greener-y-label {
  fill: var(--secondary-text-color); font-size: 9px; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
}
.octopus-greener-y-arrow { stroke: var(--secondary-text-color); stroke-width: 1.5; opacity: 0.65; }
.octopus-greener-y-arrow-head { fill: var(--secondary-text-color); opacity: 0.65; }
.octopus-greener-axis { fill: var(--secondary-text-color); font-size: 10px; }
.octopus-greener-green-line { stroke: var(--secondary-text-color); stroke-width: 1; opacity: 0.55; }
.octopus-greener-legend {
  display: flex; flex-wrap: wrap; gap: 10px 16px; padding: 8px 10px;
  font-size: 11px; color: var(--secondary-text-color);
  border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.22));
  border-radius: 10px;
}
.octopus-greener-legend--top {
  margin: 0 0 10px;
}
.octopus-greener-chart-wrap .octopus-greener-legend:not(.octopus-greener-legend--top) {
  margin-top: 8px;
}
.octopus-greener-swatch {
  display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px;
}
.octopus-greener-swatch--green { background: #22c55e; }
.octopus-greener-swatch--purple { background: #8b5cf6; }
.octopus-greener-swatch-line {
  display: inline-block;
  width: 20px;
  height: 0;
  margin-right: 6px;
  vertical-align: middle;
  border-top: 2px dashed var(--secondary-text-color);
  opacity: 0.75;
}
.octopus-greener-table-wrap {
  margin-top: 12px; overflow-x: auto; border-radius: var(--fp-radius, 12px);
  border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
}
.octopus-greener-table {
  width: 100%; border-collapse: collapse; font-size: 12px;
}
.octopus-greener-table th, .octopus-greener-table td {
  padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--divider-color, rgba(127, 127, 127, 0.15));
}
.octopus-greener-table tbody tr:nth-child(even) { background: var(--secondary-background-color, rgba(127, 127, 127, 0.06)); }
.octopus-greener-table th { font-size: 11px; color: var(--secondary-text-color); font-weight: 600; }
.octopus-greener-timeline {
  position: relative;
  list-style: none;
  margin: 16px 0 0;
  padding: 4px 0 4px 42px;
}
.octopus-greener-timeline::before {
  content: "";
  position: absolute;
  left: 14px;
  top: 8px;
  bottom: 8px;
  width: 4px;
  border-radius: 4px;
  background: rgba(139, 92, 246, 0.32);
}
.octopus-greener-timeline-item {
  position: relative;
  padding: 0 0 16px 0;
  margin: 0;
}
.octopus-greener-timeline-item:last-child { padding-bottom: 0; }
.octopus-greener-timeline-icon {
  position: absolute;
  left: -42px;
  top: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}
.octopus-greener-timeline-icon-svg {
  display: block;
  flex-shrink: 0;
}
.octopus-greener-timeline-icon-svg--leaf {
  width: 22px;
  height: auto;
}
.octopus-greener-timeline-icon-svg--unplugged {
  width: 18px;
  height: auto;
}
.octopus-greener-timeline-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  color: var(--secondary-text-color);
}
.octopus-greener-timeline-title {
  display: block;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
  color: inherit;
}
.octopus-greener-timeline-detail {
  display: block;
  font-size: 12px;
  line-height: 1.45;
  color: inherit;
  opacity: 0.88;
}
.octopus-rewards-split {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 8px;
}
.octopus-rewards-pane {
  padding: 12px 14px; border-radius: var(--fp-radius, 12px);
  background: var(--secondary-background-color, rgba(127, 127, 127, 0.06));
  border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.15));
}
.octopus-rewards-pane label {
  display: block; font-size: 11px; color: var(--secondary-text-color); margin-bottom: 4px;
}
.octopus-rewards-pane strong { display: block; font-size: 18px; line-height: 1.2; }
.octopus-rewards-sub { display: block; margin-top: 4px; font-size: 11px; color: var(--secondary-text-color); }
.fox-analysis-octopus-greener-row { margin-top: 14px; }
.fox-analysis-octopus-greener-row .octopus-greener-card { margin-top: 0; }
.fox-analysis-octopus-upcoming-row { margin-top: 14px; }
.octopus-analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
}
.octopus-analysis-card {
  margin-top: 14px;
}
.octopus-analysis-card .fox-analysis-chart-title {
  margin-bottom: 10px;
}
.octopus-analysis-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 10px 0 4px;
}
.octopus-analysis-metric label {
  display: block;
  font-size: 11px;
  color: var(--secondary-text-color);
  margin-bottom: 4px;
}
.octopus-analysis-metric strong {
  display: block;
  font-size: 18px;
  line-height: 1.2;
}
.octopus-analysis-list {
  margin: 8px 0 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--secondary-text-color);
}
.octopus-analysis-dual-wrap { margin-top: 4px; }
.octopus-analysis-dual-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  font-size: 11px;
  color: var(--secondary-text-color);
  margin-bottom: 8px;
}
.octopus-analysis-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-right: 6px;
  vertical-align: -1px;
}
.octopus-analysis-swatch--green { background: #22c55e; }
.octopus-analysis-swatch--purple { background: #8b5cf6; }
.octopus-analysis-swatch-line {
  display: inline-block;
  width: 20px;
  height: 0;
  margin-right: 6px;
  vertical-align: middle;
  border-top: 2px solid #03a9f4;
}
.octopus-analysis-swatch-line--import { border-top-color: #03a9f4; }
.octopus-analysis-swatch-line--export { border-top-color: #f59e0b; }
.octopus-analysis-chart-hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--secondary-text-color);
  line-height: 1.35;
}
.octopus-analysis-chart-hint .octopus-analysis-swatch {
  margin-right: 6px;
  vertical-align: -1px;
}
@media (max-width: 720px) {
  .octopus-analysis-grid { grid-template-columns: 1fr; }
  .octopus-analysis-metrics { grid-template-columns: 1fr; }
}
.fox-analysis-octopus-upcoming-row .octopus-upcoming-week-card { margin-top: 0; }
.octopus-upcoming-week-card > .fox-analysis-summary-title {
  margin: 0 0 12px;
}
.octopus-upcoming-week-card .octopus-greener-headline { margin: 0 0 8px; }
.octopus-upcoming-week-note {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--secondary-text-color);
}
.octopus-upcoming-week-note { margin-bottom: 14px; }
.octopus-upcoming-week-error {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--error-color, #f44336);
}
.octopus-upcoming-week-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
}
.octopus-upcoming-week-day {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
  min-height: 168px;
  padding: 10px 6px 8px;
  border-radius: 14px;
  border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.25));
  background: var(--secondary-background-color, rgba(127, 127, 127, 0.06));
  text-align: center;
}
.octopus-upcoming-week-day--featured {
  background: rgba(24, 240, 184, 0.18);
  border-color: #18f0b8;
  box-shadow: inset 0 0 0 1px rgba(24, 240, 184, 0.28);
}
.octopus-upcoming-week-day--today:not(.octopus-upcoming-week-day--featured) {
  border-color: var(--primary-color, rgba(3, 169, 244, 0.45));
}
.octopus-upcoming-week-day--past { opacity: 0.72; }
.octopus-upcoming-week-badge {
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  padding: 2px 9px;
  border-radius: 999px;
  background: #18f0b8;
  color: #0b1220;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.3;
  white-space: nowrap;
}
.octopus-upcoming-week-day--featured .octopus-upcoming-week-dayname { margin-top: 18px; }
.octopus-upcoming-week-dayname {
  margin-top: 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--primary-text-color);
}
.octopus-upcoming-week-date {
  font-size: 12px;
  color: var(--secondary-text-color);
}
.octopus-upcoming-week-plant-wrap {
  margin-top: auto;
  width: 100%;
  height: 112px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  flex-shrink: 0;
}
.octopus-upcoming-week-plant {
  display: block;
  flex-shrink: 0;
  object-fit: contain;
  object-position: bottom center;
  max-width: 100%;
}
.octopus-upcoming-week-plant--green {
  width: 112px;
  height: 112px;
}
.octopus-upcoming-week-plant--low {
  width: 96px;
  height: 96px;
}
@media (max-width: 720px) {
  .octopus-upcoming-week-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
@media (max-width: 480px) {
  .octopus-upcoming-week-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .octopus-rewards-split { grid-template-columns: 1fr; }
}
.soc-chart-card { padding-bottom: 16px; }
.soc-chart-card .card-title { margin-bottom: 8px; }
.soc-chart-wrap {
  position: relative; width: 100%; font-family: "Segoe UI", Arial, sans-serif;
}
.soc-chart-head {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  margin-bottom: 10px; flex-wrap: wrap;
}
.soc-chart-value {
  font-size: 22px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
}
.soc-chart-legend {
  display: flex; flex-wrap: wrap; gap: 10px 14px; align-items: center;
  font-size: 11px; color: var(--secondary-text-color); margin-top: 6px;
}
.soc-chart-legend-item {
  display: inline-flex; align-items: center; gap: 6px;
}
.soc-chart-legend-item i {
  width: 14px; height: 3px; border-radius: 1px; display: inline-block;
}
.soc-chart-plot { position: relative; width: 100%; }
.soc-chart-svg { width: 100%; height: 300px; display: block; }
.soc-chart-grid { stroke: rgba(127,127,127,0.12); stroke-width: 1; }
.soc-chart-axis-x, .soc-chart-axis-y {
  fill: var(--secondary-text-color); font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.soc-chart-now-line { stroke: rgba(127,127,127,0.28); stroke-width: 1; stroke-dasharray: 3 3; }
.soc-chart-hit { position: absolute; inset: 0; cursor: crosshair; }
.soc-chart-crosshair {
  position: absolute; top: 0; bottom: 40px; width: 1px; pointer-events: none;
  transform: translateX(-0.5px);
}
.soc-chart-spike {
  width: 1px; height: 100%; background: rgba(127,127,127,0.35);
}
.soc-chart-tooltip {
  position: absolute; z-index: 4; min-width: 160px; padding: 8px 10px; border-radius: 8px;
  pointer-events: none; background: var(--card-background-color, #1c1c1c);
  border: 1px solid rgba(127,127,127,0.35);
  box-shadow: 0 4px 16px rgba(0,0,0,0.28);
  font-size: 12px; color: var(--primary-text-color);
}
.soc-chart-tooltip-time {
  font-size: 11px; color: var(--secondary-text-color); margin-bottom: 6px;
}
.soc-chart-tooltip-row {
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
}
.soc-chart-tooltip-label {
  display: inline-flex; align-items: center; gap: 6px;
}
.soc-chart-tooltip-swatch {
  width: 10px; height: 10px; border-radius: 2px; display: inline-block;
}
.fox-energy-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  align-items: stretch;
}
.fox-energy-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 18px;
  align-items: center;
  padding: 4px 14px 6px 0;
  min-width: 0;
}
.fox-energy-row + .fox-energy-row {
  border-left: 1px solid var(--divider-color, rgba(127,127,127,0.25));
  padding-left: 14px;
  padding-right: 0;
}
.fox-energy-copy { min-width: 0; }
.fox-energy-heading { font-size: 14px; color: var(--secondary-text-color); margin: 0 0 4px; font-weight: 500; }
.fox-energy-total { font-size: 24px; font-weight: 700; margin: 0 0 12px; line-height: 1.05; letter-spacing: -0.02em; }
.fox-energy-total span { font-size: 14px; font-weight: 500; color: var(--secondary-text-color); margin-left: 4px; }
.fox-energy-metric { margin-bottom: 10px; }
.fox-energy-metric:last-child { margin-bottom: 0; }
.fox-energy-metric-label { font-size: 12px; color: var(--secondary-text-color); margin-bottom: 2px; line-height: 1.25; }
.fox-energy-metric-value { font-size: 20px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em; }
.fox-energy-metric-unit { font-size: 13px; font-weight: 500; color: var(--secondary-text-color); margin-left: 2px; }
.fox-energy-chart {
  position: relative; flex-shrink: 0; width: 116px; height: 116px;
  margin-left: auto; align-self: center;
}
.fox-energy-chart svg {
  width: 116px; height: 116px; max-width: 100%; max-height: 100%;
  display: block; aspect-ratio: 1;
}
.fox-energy-chart-center {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  width: 72px; display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; pointer-events: none; gap: 5px;
}
.fox-energy-chart-pct { font-size: 22px; font-weight: 700; line-height: 1.1; letter-spacing: -0.03em; }
.fox-energy-chart-label {
  font-size: 10px; font-weight: 500; color: var(--secondary-text-color);
  line-height: 1.3; margin: 0; max-width: 72px;
}
.energy-period-tabs {
  display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: nowrap;
  padding: 4px; border-radius: 12px;
  background: var(--secondary-background-color, rgba(127,127,127,0.12));
  border: 1px solid var(--divider-color, transparent);
}
.energy-period-tabs button {
  flex: 1; min-width: 0; padding: 10px 8px; border-radius: 10px; border: none;
  background: transparent; color: var(--secondary-text-color); font-family: inherit;
  font-size: 13px; font-weight: 600; cursor: pointer;
}
.energy-period-tabs button.active {
  color: var(--primary-text-color);
  background: var(--card-background-color);
  box-shadow: 0 1px 3px rgba(0,0,0,0.18);
}
.energy-date-nav {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  margin: 0 0 14px; min-height: 40px;
}
.energy-date-nav button {
  width: 36px; height: 36px; border-radius: 10px; border: 1px solid var(--divider-color);
  background: var(--card-background-color); color: var(--primary-text-color);
  font-size: 20px; line-height: 1; cursor: pointer; font-family: inherit;
}
.energy-date-nav button:disabled { opacity: 0.35; cursor: default; }
.energy-date-label { font-size: 15px; font-weight: 600; text-align: center; min-width: 180px; }
.energy-analysis-card { margin-top: 14px; padding: 14px 16px 10px; }
.breakdown-card { margin-top: 14px; }
.energy-chart-card { margin-top: 14px; }
.fox-energy-chart-wrap { width: 100%; }
.fox-energy-mirror-plot { position: relative; width: 100%; }
.fox-energy-mirror-chart { width: 100%; height: 300px; display: block; cursor: crosshair; }
.fox-energy-mirror-legend { margin-bottom: 10px; }
.fox-energy-mirror-legend-item {
  cursor: default; pointer-events: none; gap: 4px 6px;
}
.fox-energy-mirror-legend-value {
  color: var(--secondary-text-color); font-size: 10px; font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.fox-energy-legend { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.fox-energy-legend-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; font-size: 11px; }
.fox-energy-legend-heading { font-weight: 700; font-size: 10px; letter-spacing: 0.04em; color: var(--secondary-text-color); margin-right: 4px; }
.fox-energy-legend-item { display: inline-flex; align-items: center; gap: 5px; color: var(--primary-text-color); }
.fox-energy-legend-item i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.fox-energy-grid { stroke: rgba(127,127,127,0.12); stroke-width: 1; stroke-dasharray: 3 4; }
.fox-energy-zero { stroke: rgba(127,127,127,0.28); stroke-width: 1; }
.fox-energy-axis { fill: var(--secondary-text-color); font-size: 11px; }
.fox-energy-y-label { fill: var(--secondary-text-color); font-size: 12px; font-weight: 600; text-anchor: middle; }
.energy-chart-card .card-title { margin-bottom: 10px; }
.chart-wrap { position: relative; width: 100%; }
.energy-bar-chart { width: 100%; height: 220px; display: block; }
.statistics-chart-wrap {
  position: relative; width: 100%; font-family: "Segoe UI", Arial, sans-serif;
}
.statistics-chart-wrap--side {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px 16px;
  align-items: stretch;
}
.statistics-chart-main { min-width: 0; }
.statistics-chart-legend-side {
  display: flex; flex-direction: column; gap: 14px;
  min-width: 148px; max-width: 168px;
  padding: 8px 4px 8px 0;
}
.statistics-chart-wrap--soc .statistics-chart-legend-side {
  padding-top: 0;
}
.statistics-legend-section { display: flex; flex-direction: column; gap: 8px; }
.statistics-legend-heading {
  font-size: 10px; font-weight: 700; letter-spacing: 0.06em;
  color: var(--secondary-text-color); text-transform: uppercase;
}
.statistics-legend-item--side {
  width: 100%; justify-content: flex-start; text-align: left;
  font-size: 12px; line-height: 1.25;
}
.statistics-legend-item--side i { width: 8px; height: 8px; border-radius: 999px; }
.statistics-chart-legend {
  display: flex; flex-wrap: wrap; gap: 8px 12px; margin-bottom: 10px;
}
.statistics-legend-item {
  display: inline-flex; align-items: center; gap: 6px; padding: 0; border: none;
  background: transparent; color: var(--primary-text-color); font: inherit;
  font-size: 11px; cursor: pointer; opacity: 1;
}
.statistics-legend-item.off { opacity: 0.35; }
.statistics-legend-item i {
  width: 10px; height: 10px; border-radius: 2px; display: inline-block; flex-shrink: 0;
}
.statistics-chart-plot { position: relative; width: 100%; margin: 0; }
.statistics-chart-svg {
  width: 100%; height: 440px; display: block; overflow: visible;
}
.statistics-y-label {
  fill: var(--secondary-text-color); font-size: 12px; font-weight: 600; text-anchor: start;
}
.statistics-y-label--left { text-anchor: start; }
.statistics-y-label--right { text-anchor: end; }
.statistics-y-axis { stroke: rgba(127,127,127,0.35); stroke-width: 1; }
.statistics-y-axis--right { stroke: rgba(127,127,127,0.35); stroke-width: 1; }
.statistics-axis-y--soc { fill: var(--secondary-text-color); }
.statistics-line-soc { pointer-events: none; }
.statistics-axis-x, .statistics-axis-y {
  fill: var(--secondary-text-color); font-size: 12px;
  font-variant-numeric: tabular-nums; text-rendering: geometricPrecision;
}
.statistics-grid { stroke: rgba(127,127,127,0.12); stroke-width: 1; }
.statistics-zero-line { stroke: rgba(127,127,127,0.20); stroke-width: 1; }
.statistics-hit { cursor: crosshair; }
.statistics-crosshair {
  position: absolute; top: 0; bottom: 40px; width: 1px; pointer-events: none;
  transform: translateX(-0.5px);
}
.statistics-spike {
  width: 1px; height: 100%; background: rgba(127,127,127,0.35);
}
.statistics-tooltip {
  position: absolute; z-index: 4; min-width: 180px; max-width: 260px;
  padding: 10px 12px; border-radius: 8px; pointer-events: none;
  background: var(--card-background-color, #1c1c1c);
  border: 1px solid rgba(127,127,127,0.35);
  box-shadow: 0 4px 16px rgba(0,0,0,0.28);
  font-size: 13px; color: var(--primary-text-color);
}
.statistics-tooltip-time {
  font-size: 12px; color: var(--secondary-text-color); margin-bottom: 8px;
}
.statistics-tooltip-row {
  display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 6px;
}
.statistics-tooltip-row:last-child { margin-bottom: 0; }
.statistics-tooltip-label {
  display: inline-flex; align-items: center; gap: 8px; min-width: 0; flex: 1;
}
.statistics-tooltip-swatch {
  width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; display: inline-block;
}
.statistics-tooltip-row strong { font-weight: 600; white-space: nowrap; flex-shrink: 0; }
.chart-grid { stroke: rgba(127,127,127,0.15); stroke-width: 1; }
.chart-axis { fill: var(--secondary-text-color); font-size: 9px; font-family: inherit; }
.chart-legend {
  display: flex; flex-wrap: wrap; gap: 10px 14px; margin-top: 10px; font-size: 12px; color: var(--secondary-text-color);
}
.chart-legend-item { display: inline-flex; align-items: center; gap: 6px; }
.chart-legend-item i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.chart-empty { margin: 24px 0; text-align: center; }
.chart-loading { margin: 24px 0; text-align: center; color: var(--secondary-text-color); font-size: 13px; }
.fox-analysis-top {
  display: grid; grid-template-columns: minmax(120px, 0.9fr) minmax(0, 1.2fr) minmax(0, 1.2fr);
  gap: 12px; margin-bottom: 14px;
}
.fox-analysis-top-card {
  padding: 14px 16px; border-radius: 14px;
  background: var(--card-background-color);
  border: 1px solid var(--divider-color, rgba(127,127,127,0.22));
  min-width: 0;
}
.fox-analysis-top-card--balance {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; gap: 8px;
}
.fox-analysis-top-heading-row {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.fox-analysis-help-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; padding: 0; border: none; background: transparent;
  color: var(--secondary-text-color); cursor: pointer; flex-shrink: 0;
}
.fox-analysis-help-btn svg { width: 16px; height: 16px; display: block; }
.fox-analysis-help-btn:hover { color: var(--primary-text-color); }
.fox-analysis-help-btn:focus-visible {
  outline: 2px solid var(--fp-accent); outline-offset: 2px; border-radius: 999px;
}
.fox-help-modal-backdrop {
  position: fixed; inset: 0; z-index: 1000;
  display: flex; align-items: center; justify-content: center;
  padding: 24px 16px;
  background: rgba(0, 0, 0, 0.45);
}
.fox-help-modal {
  position: relative; width: min(100%, 520px);
  padding: 24px 24px 20px;
  border-radius: 8px;
  background: var(--card-background-color, #fff);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.22);
  color: var(--primary-text-color);
}
.fox-help-modal-close {
  position: absolute; top: 16px; right: 16px;
  width: 28px; height: 28px; padding: 0; border: none; border-radius: 6px;
  background: transparent; color: var(--secondary-text-color);
  font-size: 22px; line-height: 1; cursor: pointer;
}
.fox-help-modal-close:hover { color: var(--primary-text-color); background: color-mix(in srgb, var(--secondary-text-color) 12%, transparent); }
.fox-help-modal-title {
  margin: 0 36px 16px 0; font-size: 18px; font-weight: 700; line-height: 1.3;
  color: var(--primary-text-color);
}
.fox-help-modal-body {
  font-size: 14px; line-height: 1.6; color: var(--primary-text-color);
}
.fox-help-modal-body p { margin: 0 0 14px; }
.fox-help-modal-body p:last-child { margin-bottom: 0; }
.fox-help-modal-footer {
  display: flex; justify-content: flex-end; margin-top: 24px;
}
.fox-help-modal-ok {
  min-width: 72px; padding: 8px 20px; border: none; border-radius: 6px;
  background: #894BFC; color: #fff; font: inherit; font-size: 14px; font-weight: 500;
  cursor: pointer;
}
.fox-help-modal-ok:hover { filter: brightness(1.05); }
.fox-help-modal-ok:focus-visible { outline: 2px solid #894BFC; outline-offset: 2px; }
.fox-analysis-balance-icon svg { width: 52px; height: 52px; display: block; }
.fox-analysis-top-heading {
  font-size: 13px; font-weight: 600; color: var(--secondary-text-color); margin-bottom: 4px;
}
.fox-analysis-top-heading-row .fox-analysis-top-heading { margin-bottom: 0; }
.fox-analysis-top-value {
  font-size: 28px; font-weight: 700; line-height: 1.05; letter-spacing: -0.03em;
  color: var(--primary-text-color); margin-bottom: 10px;
}
.fox-analysis-top-value span {
  font-size: 14px; font-weight: 500; color: var(--secondary-text-color); margin-left: 4px;
}
.fox-analysis-enerbf { padding: 20px; }
.fox-analysis-prc {
  display: flex; flex-direction: column; margin-bottom: 15px;
}
.fox-analysis-num {
  font-weight: 600; font-size: 24px; line-height: 32px;
  color: var(--primary-text-color); letter-spacing: -0.02em;
}
.fox-analysis-unit {
  font-weight: 400; font-size: 14px; margin-left: 4px;
  color: var(--primary-text-color);
}
.fox-analysis-name {
  font-size: 14px; color: var(--secondary-text-color); line-height: 22px; min-height: 32px;
}
.fox-analysis-propor {
  display: flex; width: 100%; height: 32px; overflow: hidden;
}
.fox-analysis-propor--empty {
  background: color-mix(in srgb, var(--secondary-text-color) 12%, transparent);
  border-radius: 2px; opacity: 0.35;
}
.fox-analysis-propor-seg {
  line-height: 32px; text-align: center; min-width: 0; overflow: hidden;
}
.fox-analysis-propor-seg:first-child { border-radius: 2px 0 0 2px; }
.fox-analysis-propor-seg:last-child { border-radius: 0 2px 2px 0; }
.fox-analysis-propor-seg:only-child { border-radius: 2px; }
.fox-analysis-propor-seg span {
  font-size: 14px; font-weight: 500; color: #ffffff; white-space: nowrap;
}
.fox-analysis-info {
  display: flex; justify-content: space-between; gap: 12px; margin-top: 15px;
}
.fox-analysis-info-row {
  width: 50%; min-width: 0; display: flex; flex-direction: column;
}
.fox-analysis-info-na {
  font-size: 14px; color: var(--secondary-text-color); line-height: 22px;
}
.fox-analysis-info-nu {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 8px; line-height: 26px;
}
.fox-analysis-info-l {
  font-weight: 600; font-size: 16px; color: var(--primary-text-color); min-width: 0;
}
.fox-analysis-info-l span { font-weight: 400; font-size: 12px; margin-left: 2px; }
.fox-analysis-info-r { font-weight: 600; font-size: 13px; flex-shrink: 0; }
.fox-analysis-info-pr { width: 100%; height: 4px; margin-top: 5px; border-radius: 1px; }
.fox-analysis-toolbar {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 10px 16px; margin-bottom: 14px; padding: 12px 16px;
}
.fox-analysis-toolbar .energy-period-tabs { margin-bottom: 0; flex: 1 1 280px; }
.fox-report-summary-row {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.15fr) minmax(0, 1.15fr);
  gap: 12px;
  margin-bottom: 14px;
  align-items: stretch;
}
.fox-report-summary-row > .card {
  margin-bottom: 0;
  padding: 14px 16px;
  min-width: 0;
  min-height: 0;
  height: auto;
  align-self: stretch;
  box-sizing: border-box;
  overflow: hidden;
}
.fox-sc-analysis-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.fox-sc-analysis-card {
  background: var(--card-background-color, #1c1c1c);
  border-radius: 12px;
  padding: 14px 16px;
  border: 1px solid var(--divider-color, rgba(255,255,255,0.08));
}
.fox-sc-analysis-card-label { font-size: 12px; opacity: 0.75; margin-bottom: 6px; }
.fox-sc-analysis-card-value { font-size: 22px; font-weight: 600; line-height: 1.2; }
.fox-sc-analysis-card-sub { font-size: 12px; opacity: 0.7; margin-top: 6px; }
.fox-sc-analysis-chart { width: 100%; height: auto; display: block; }
.fox-sc-analysis-chart-legend {
  display: flex; flex-wrap: wrap; gap: 10px 14px; font-size: 12px; margin-bottom: 8px; opacity: 0.85;
}
.fox-sc-analysis-chart-legend span { display: inline-flex; align-items: center; gap: 6px; }
.fox-sc-analysis-chart-legend i {
  display: inline-block; width: 10px; height: 10px; border-radius: 2px;
}
.fox-sc-analysis-table { font-size: 13px; }
@media (max-width: 900px) {
  .fox-sc-analysis-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .fox-sc-analysis-summary { grid-template-columns: 1fr; }
}
.fox-report-balance-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 6px;
}
.fox-report-balance-card .fox-analysis-top-value {
  margin-bottom: 0;
  font-size: 26px;
}
.fox-report-balance-card .fox-analysis-balance-icon svg {
  width: 46px;
  height: 46px;
}
.fox-report-donut-card {
  padding: 14px 16px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}
.fox-report-donut-card .fox-energy-panel--single {
  display: block;
  flex: 1 1 auto;
  min-height: 0;
}
.fox-report-donut-card .fox-energy-panel--single .fox-energy-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 116px;
  gap: 8px 14px;
  align-items: center;
  padding: 0;
  border: none;
  min-height: 0;
}
.fox-report-donut-card .fox-energy-panel--single .fox-energy-row + .fox-energy-row {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}
.fox-report-donut-card .fox-energy-heading {
  font-size: 13px;
  margin-bottom: 2px;
}
.fox-report-donut-card .fox-energy-total {
  font-size: 22px;
  margin-bottom: 8px;
}
.fox-report-donut-card .fox-energy-metric {
  margin-bottom: 6px;
}
.fox-report-donut-card .fox-energy-metric-value {
  font-size: 17px;
}
.fox-report-donut-card .fox-energy-chart {
  width: 116px;
  height: 116px;
  margin-left: 0;
}
.fox-report-details {
  margin-top: 14px;
  padding: 14px 16px 16px;
}
.fox-report-details-title {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 700;
  color: var(--primary-text-color);
}
.fox-report-details-table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.fox-report-details-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  font-size: 13px;
}
.fox-report-details-table th,
.fox-report-details-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--divider-color, rgba(127,127,127,0.22));
  text-align: right;
  white-space: nowrap;
}
.fox-report-details-table th:first-child,
.fox-report-details-table td:first-child {
  text-align: left;
  white-space: normal;
}
.fox-report-details-table thead th {
  background: color-mix(in srgb, var(--secondary-text-color) 8%, transparent);
  font-weight: 600;
  color: var(--secondary-text-color);
}
.fox-report-details-table .fox-report-th-group {
  text-align: center;
  color: var(--primary-text-color);
}
.fox-report-details-table tbody tr:hover td {
  background: color-mix(in srgb, var(--secondary-text-color) 6%, transparent);
}
.fox-report-chart-card {
  margin-top: 14px;
  padding: 14px 16px 8px;
}
@media (max-width: 960px) {
  .fox-report-summary-row {
    grid-template-columns: 1fr;
  }
  .fox-report-summary-row > .card {
    min-height: 0;
  }
}
.fox-analysis-toolbar .energy-date-nav { margin: 0; flex: 0 0 auto; }
.fox-analysis-panels-row {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px; margin-bottom: 14px; align-items: stretch;
}
.fox-analysis-chart-row { min-width: 0; }
.fox-analysis-panel-card,
.fox-analysis-chart-card {
  padding: 14px; border-radius: 14px;
  background: var(--card-background-color);
  border: 1px solid var(--divider-color, rgba(127,127,127,0.22));
  min-width: 0;
}
.fox-analysis-chart-title { margin: 0 0 12px; }
.fox-analysis-panel-card { display: flex; flex-direction: column; justify-content: flex-start; }
.fox-analysis-summary-card-inner { display: flex; flex-direction: column; gap: 12px; min-width: 0; height: 100%; }
.fox-analysis-summary-head {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
}
.fox-analysis-summary-title {
  margin: 0; font-size: 16px; font-weight: 700; letter-spacing: -0.02em; color: var(--primary-text-color);
}
.fox-analysis-summary-details {
  padding: 6px 12px; border-radius: 999px; border: 1px solid var(--divider-color, rgba(127,127,127,0.35));
  background: transparent; color: var(--secondary-text-color); font-size: 12px; font-weight: 600;
  font-family: inherit; cursor: pointer; line-height: 1.2; white-space: nowrap;
}
.fox-analysis-summary-details:hover {
  color: var(--primary-text-color);
  background: var(--secondary-background-color, rgba(127,127,127,0.12));
}
.fox-analysis-summary-rows { display: flex; flex-direction: column; gap: 0; flex: 1; }
.fox-analysis-summary-row {
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(96px, 42%);
  gap: 10px; align-items: center; padding: 12px 0;
  border-top: 1px solid var(--divider-color, rgba(127,127,127,0.18));
}
.fox-analysis-summary-row:first-child { border-top: none; padding-top: 0; }
.fox-analysis-summary-row-main { min-width: 0; }
.fox-analysis-summary-label {
  display: block; font-size: 12px; color: var(--secondary-text-color); margin-bottom: 4px;
}
.fox-analysis-summary-value {
  display: block; font-size: 22px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
  color: var(--primary-text-color);
}
.fox-analysis-summary-value span {
  font-size: 14px; font-weight: 500; color: var(--secondary-text-color); margin-left: 3px;
}
.fox-analysis-summary-row--muted .fox-analysis-summary-value { color: var(--secondary-text-color); }
.fox-analysis-summary-spark {
  display: flex; align-items: center; justify-content: flex-end; min-width: 0; height: 40px;
}
.fox-analysis-sparkline { width: 100%; height: 40px; display: block; overflow: visible; }
.fox-analysis-sparkline-loading,
.fox-analysis-sparkline--empty {
  width: 100%; height: 40px; display: block;
  background: color-mix(in srgb, var(--secondary-text-color) 8%, transparent);
  border-radius: 8px;
}
.fox-analysis-stat-r {
  position: relative;
  padding: 0;
  background: transparent;
  --fox-flow-green: #03bd9a;
  --fox-flow-track: color-mix(in srgb, var(--secondary-text-color) 14%, transparent);
  --fox-stat-border-top: color-mix(in srgb, var(--secondary-text-color) 14%, transparent);
}
.fox-analysis-stat-na {
  display: block;
  font-weight: 500;
  font-size: 14px;
  color: var(--primary-text-color);
  margin: 0 0 10px;
}
.fox-analysis-stat-usage-wrap {
  position: relative;
}
.fox-analysis-stat-na--overlay {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
  margin: 0;
  padding: 0 8px 0 0;
  transform: translateY(calc(-100% - 10px));
  background: var(--card-background-color);
}
.fox-analysis-stat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 114px;
  padding: 20px;
  margin-bottom: 0;
  border-radius: 6px;
  border: 3px solid;
  border-image: linear-gradient(
    180deg,
    var(--fox-stat-border-top),
    var(--fox-stat-border-top) 25%,
    var(--fox-flow-green)
  ) 2 2;
}
.fox-analysis-stat-col {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  text-align: center;
}
.fox-analysis-stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}
.fox-analysis-stat-icon svg {
  width: 32px;
  height: 32px;
  display: block;
}
.fox-analysis-stat-icon--muted { color: #788bab; }
.fox-analysis-stat-col-nu {
  font-weight: 600;
  font-size: 16px;
  line-height: 1.2;
  color: var(--primary-text-color);
  padding-top: 10px;
}
.fox-analysis-stat-col-nu span {
  font-weight: 400;
  font-size: 14px;
  margin-left: 2px;
}
.fox-analysis-stat-col-na {
  font-size: 14px;
  line-height: 22px;
  color: var(--secondary-text-color);
  padding: 0 4px;
}
.fox-analysis-stat-bridge {
  position: relative;
  height: 87px;
  margin: 0;
  contain: layout style;
  isolation: isolate;
}
.fox-analysis-stat-flow {
  width: 87px;
  height: 2px;
  background: var(--fox-flow-track);
  position: absolute;
  top: 50%;
  left: 25%;
  transform: translate(-50%, -50%) rotate(90deg);
  overflow: hidden;
}
.fox-analysis-stat-flow.flow-r {
  left: auto;
  right: 25%;
  transform: translate(50%, -50%) rotate(90deg);
}
.fox-analysis-stat-flow-glow {
  position: absolute;
  inset: 0;
  background: linear-gradient(to right, var(--fox-flow-track) 40%, var(--fox-flow-green));
  transform: translateX(-100%);
  animation: fox-stat-flow-glow 2s linear infinite;
  will-change: transform;
}
@keyframes fox-stat-flow-glow {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.impact-card .card-title { margin-bottom: 12px; }
.impact-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px;
}
.impact-metric {
  text-align: center; padding: 14px 8px 10px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--fp-accent, #19d4de) 6%, var(--card-background-color));
  border: 1px solid var(--divider-color, rgba(127,127,127,0.2));
}
.impact-icon {
  display: block; height: 36px; width: auto; max-width: 56px;
  margin: 0 auto 10px; object-fit: contain;
}
.impact-value {
  font-size: 22px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
  color: var(--primary-text-color);
}
.impact-unit {
  font-size: 13px; font-weight: 500; color: var(--secondary-text-color); margin-left: 3px;
}
.impact-label {
  margin-top: 6px; font-size: 11px; line-height: 1.3; color: var(--secondary-text-color);
}
.impact-basis {
  margin: 12px 0 0; font-size: 11px; color: var(--secondary-text-color); text-align: center;
}
.impact-placeholder { font-size: 13px; line-height: 1.45; margin: 0; }
.impact-placeholder code { font-size: 12px; }
@media (max-width: 560px) {
  .impact-grid { grid-template-columns: 1fr; }
  .fox-energy-panel { grid-template-columns: 1fr; }
  .fox-energy-row {
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 14px 0 6px;
  }
  .fox-energy-chart { width: 128px; height: 128px; }
  .fox-energy-chart svg { width: 128px; height: 128px; }
  .fox-energy-chart-center { width: 78px; }
  .fox-energy-chart-pct { font-size: 24px; }
  .fox-energy-chart-label { font-size: 11px; max-width: 78px; }
  .fox-energy-row + .fox-energy-row {
    border-left: none;
    border-top: 1px solid var(--divider-color, rgba(127,127,127,0.25));
    padding-left: 0;
    padding-top: 16px;
    margin-top: 4px;
  }
  .fox-analysis-top { grid-template-columns: 1fr; }
  .fox-analysis-panels-row { grid-template-columns: 1fr; }
  .fox-analysis-summary-row { grid-template-columns: 1fr; }
  .fox-analysis-summary-spark { justify-content: flex-start; }
  .fox-analysis-stat-flow { width: 64px; }
  .fox-analysis-stat-row {
    flex-direction: row;
    align-items: flex-start;
    min-height: 0;
    gap: 4px;
    padding: 12px 6px;
  }
  .fox-analysis-stat-col-nu { font-size: 13px; padding-top: 6px; }
  .fox-analysis-stat-col-nu span { font-size: 11px; }
  .fox-analysis-stat-col-na { font-size: 11px; line-height: 1.25; padding: 0 2px; }
  .fox-analysis-stat-icon { width: 26px; height: 26px; }
  .fox-analysis-stat-icon svg { width: 26px; height: 26px; }
  .fox-analysis-stat-bridge { height: 64px; }
  .statistics-chart-wrap--side { grid-template-columns: 1fr; }
  .statistics-chart-legend-side {
    max-width: none; padding: 12px 0 0;
  }
  .statistics-chart-wrap--soc .statistics-chart-legend-side {
    padding-top: 12px;
  }
}
.stat { background: var(--card-background-color); border-radius: var(--fp-radius); padding: 16px; border: 1px solid var(--divider-color, transparent); box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06)); }
.stat label { font-size: 12px; color: var(--secondary-text-color); display: block; }
.stat strong { font-size: 22px; display: block; margin-top: 6px; font-weight: 600; }
.mode-pill {
  display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px;
  border-radius: 999px; font-size: 12px; font-weight: 600; text-transform: capitalize;
  background: color-mix(in srgb, var(--fp-green) 20%, transparent); color: var(--fp-green);
}
.mode-pill.mode-storm { background: color-mix(in srgb, var(--fp-amber) 22%, transparent); color: var(--fp-amber); }
.mode-pill.mode-override { background: color-mix(in srgb, #7e57c2 22%, transparent); color: #7e57c2; }
.mode-pill.mode-manual { background: var(--secondary-background-color); color: var(--secondary-text-color); }
.mode-pill.mode-outage { background: color-mix(in srgb, var(--fp-red) 18%, transparent); color: var(--fp-red); }
.banner { display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px; border-radius: var(--fp-radius); margin-bottom: 14px; font-size: 13px; line-height: 1.45; }
.banner.warn { background: color-mix(in srgb, var(--fp-amber) 14%, var(--card-background-color)); border: 1px solid color-mix(in srgb, var(--fp-amber) 40%, transparent); }
.banner.info { background: color-mix(in srgb, var(--fp-accent) 12%, var(--card-background-color)); border: 1px solid color-mix(in srgb, var(--fp-accent) 35%, transparent); }
.banner strong { display: block; margin-bottom: 2px; }
.btn-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
.btn {
  padding: 10px 18px; border-radius: 10px; border: none; font-size: 14px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--fp-accent); color: var(--text-primary-color, #fff); }
.btn-secondary { background: var(--secondary-background-color); color: var(--primary-text-color); }
.btn-danger { background: color-mix(in srgb, var(--fp-red) 85%, #000); color: #fff; }
.list-btn {
  display: flex; justify-content: space-between; align-items: center; width: 100%;
  padding: 16px 18px; border-radius: var(--fp-radius);
  background: var(--card-background-color); color: inherit;
  cursor: pointer; text-align: left; font-family: inherit; margin-bottom: 10px;
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.06));
  border: 1px solid var(--divider-color, transparent); gap: 12px;
  position: relative; z-index: 0; touch-action: manipulation;
  transition: border-color 0.15s ease;
}
.list-btn::before {
  content: ""; position: absolute; inset: 0; border-radius: inherit; z-index: -1;
  background: var(--secondary-background-color); opacity: 0;
  transition: opacity 0.15s ease; pointer-events: none;
}
@media (hover: hover) {
  .list-btn:hover::before { opacity: 1; }
  .list-btn:hover { border-color: var(--divider-color, rgba(127,127,127,0.35)); }
}
.list-btn:focus-visible { outline: 2px solid var(--fp-accent); outline-offset: 2px; }
.list-btn-body { display: flex; flex-direction: column; align-items: flex-start; gap: 5px; flex: 1; min-width: 0; }
.list-btn-title { display: block; font-size: 15px; font-weight: 600; line-height: 1.3; color: var(--primary-text-color); }
.list-btn-sub { display: block; font-size: 13px; font-weight: 400; line-height: 1.35; color: var(--secondary-text-color); }
.list-btn .chev { opacity: 0.45; font-size: 20px; flex-shrink: 0; line-height: 1; }
.list-btn .sub { font-size: 13px; color: var(--secondary-text-color); }
.placeholder { padding: 28px; text-align: center; color: var(--secondary-text-color); background: var(--card-background-color); border-radius: var(--fp-radius); border: 1px dashed var(--divider-color); }
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  padding: 12px 20px; border-radius: 10px; font-size: 14px; font-weight: 500;
  z-index: 100; box-shadow: 0 4px 16px rgba(0,0,0,0.25); max-width: 90%;
}
.toast.ok { background: var(--fp-green); color: #fff; }
.toast.err { background: var(--fp-red); color: #fff; }
.scene-card { background: var(--card-background-color); border-radius: var(--fp-radius); padding: 16px 12px 12px; border: 1px solid var(--divider-color, transparent); margin-bottom: 14px; }
.scene-title { font-size: 12px; font-weight: 700; color: var(--secondary-text-color); margin: 0 0 8px 4px; text-transform: uppercase; letter-spacing: 0.04em; }
.scene-card--fox-flow {
  padding: 0; border: none; border-radius: 0; background: transparent;
  width: 100%; margin: 0 0 14px; overflow: hidden;
}
.fox-flow-scene {
  display: block; width: 100%;
}
.fox-flow-scene--ha-dark {
  background: ${FLOW_SCENE_CANVAS_BG_DARK};
}
.fox-flow-scene--ha-light {
  background: ${FLOW_SCENE_CANVAS_BG_LIGHT};
}
.fox-flow-stage {
  position: relative; width: 100%;
}
.fox-flow-scene--ha-dark .fox-flow-stage {
  background: ${FLOW_SCENE_CANVAS_BG_DARK};
}
.fox-flow-scene--ha-light .fox-flow-stage {
  background: ${FLOW_SCENE_CANVAS_BG_LIGHT};
}
.fox-flow-stage::before {
  content: ""; display: block; width: 100%; padding-top: 99.31640625%;
}
.overview-hero-row .overview-hero-scene .fox-flow-scene,
.overview-hero-row .overview-hero-scene .fox-flow-stage {
  width: 100%; max-width: none; margin: 0; box-sizing: border-box;
}
.fox-flow-layer {
  position: absolute; pointer-events: none; user-select: none;
}
.fox-flow-layer-backdrop,
.fox-flow-layer-pv,
.fox-flow-layer-aio {
  inset: 0; width: 100%; height: 100%;
  object-fit: contain; object-position: center bottom;
  image-rendering: auto;
}
.fox-flow-layer-backdrop { z-index: 0; }
.fox-flow-layer-pv,
.fox-flow-layer-aio { z-index: 2; }
.fox-flow-svg {
  position: absolute; inset: 0; width: 100%; height: 100%;
  z-index: 3; pointer-events: none;
}
.fox-flow-badge {
  position: absolute; z-index: 4;
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 0; background: transparent; backdrop-filter: none;
  pointer-events: none; text-align: center;
}
.fox-flow-badge-label {
  font-size: 10px; font-weight: 600; color: rgba(255, 255, 255, 0.62);
  text-transform: uppercase; letter-spacing: 0.06em; line-height: 1.2;
}
.fox-flow-badge-value {
  font-size: 12px; font-weight: 600; color: #fff; line-height: 1.25;
  letter-spacing: -0.01em;
}
.fox-flow-badge-solar { left: 50%; top: 1%; transform: translateX(-50%); }
/* Day sky is light — solar label sits on the backdrop, not the dark house stage */
.fox-flow-scene--day .fox-flow-badge-solar .fox-flow-badge-label {
  color: rgba(30, 30, 30, 0.72);
}
.fox-flow-scene--day .fox-flow-badge-solar .fox-flow-badge-value {
  color: #1a1a1a;
}
.fox-flow-scene--night .fox-flow-badge-solar .fox-flow-badge-label {
  color: rgba(255, 255, 255, 0.62);
}
.fox-flow-scene--night .fox-flow-badge-solar .fox-flow-badge-value {
  color: #fff;
}
.fox-flow-badge-grid { left: 4%; bottom: 6%; align-items: flex-start; }
.fox-flow-badge-battery { left: 50%; bottom: 6%; transform: translateX(-50%); }
.fox-flow-badge-home { right: 4%; bottom: 6%; align-items: flex-end; }
/* HA light theme — bottom badges sit on white canvas letterboxing */
.fox-flow-scene--ha-light .fox-flow-badge-grid .fox-flow-badge-label,
.fox-flow-scene--ha-light .fox-flow-badge-battery .fox-flow-badge-label,
.fox-flow-scene--ha-light .fox-flow-badge-home .fox-flow-badge-label {
  color: var(--secondary-text-color, rgba(30, 30, 30, 0.72));
}
.fox-flow-scene--ha-light .fox-flow-badge-grid .fox-flow-badge-value,
.fox-flow-scene--ha-light .fox-flow-badge-battery .fox-flow-badge-value,
.fox-flow-scene--ha-light .fox-flow-badge-home .fox-flow-badge-value {
  color: var(--primary-text-color, #1a1a1a);
}
.flow-path { fill: none; stroke-linecap: round; stroke-linejoin: round; }
.flow-path-idle { opacity: 1; }
.flow-path-idle-outline { opacity: 1; pointer-events: none; }
.flow-comet { fill: none; stroke-linejoin: round; pointer-events: none; }
.flow-comet-glow { opacity: 0.48; }
.flow-comet-pulse { opacity: 1; }
.flow-comet-pulse.flow-solar { filter: drop-shadow(0 0 5px rgba(255, 196, 0, 0.95)); }
.flow-comet-pulse.flow-grid { filter: drop-shadow(0 0 5px rgba(61, 154, 255, 0.95)); }
.flow-comet-pulse.flow-export { filter: drop-shadow(0 0 5px rgba(192, 106, 255, 0.95)); }
.flow-comet-pulse.flow-battery { filter: drop-shadow(0 0 6px rgba(0, 255, 102, 0.95)); }
.flow-comet-pulse { animation: flow-comet-pulse-fwd 1.75s linear infinite; }
.flow-comet-glow { animation: flow-comet-pulse-fwd 1.75s linear infinite; }
.flow-comet-pulse.flow-solar,
.flow-comet-glow.flow-solar { animation-duration: 1.55s; }
.flow-comet-pulse.reverse,
.flow-comet-glow.reverse { animation-name: flow-comet-pulse-rev; }
.flow-hub-dot.active { filter: drop-shadow(0 0 10px rgba(0, 255, 102, 0.95)); }
@keyframes flow-comet-pulse-fwd {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: -100; }
}
@keyframes flow-comet-pulse-rev {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: 100; }
}
.device-header { margin-bottom: 8px; }
.device-header h1 { margin-bottom: 4px; }
.device-model { margin: 4px 0 0; font-size: 14px; color: var(--secondary-text-color); }
.device-hero {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  margin: 4px 0 18px; padding: 0 16px; width: 100%; box-sizing: border-box;
}
.device-hero-img {
  max-width: min(200px, 62vw); max-height: 220px; width: auto; height: auto;
  display: block; object-fit: contain;
}
.device-serial-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 8px 12px; border: none; background: transparent;
  color: var(--secondary-text-color); font: inherit; font-size: 13px;
  cursor: pointer; border-radius: 8px; width: 100%; max-width: 360px;
  position: relative; z-index: 0; touch-action: manipulation;
}
.device-serial-btn::before {
  content: ""; position: absolute; inset: 0; border-radius: inherit; z-index: -1;
  background: var(--secondary-background-color, rgba(127,127,127,0.12)); opacity: 0;
  transition: opacity 0.15s ease; pointer-events: none;
}
@media (hover: hover) {
  .device-serial-btn:hover::before { opacity: 1; }
  .device-serial-btn:hover { color: var(--primary-text-color); }
}
.device-serial { font-family: ui-monospace, monospace; letter-spacing: 0.03em; }
.device-serial-muted { margin: 0; font-size: 13px; color: var(--secondary-text-color); text-align: center; }
.device-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;
  margin-bottom: 16px; align-items: stretch;
}
.device-card {
  background: var(--card-background-color); border-radius: 14px; padding: 18px 16px 20px;
  border: 1px solid var(--divider-color, rgba(127,127,127,0.28));
  min-height: 0; display: flex; flex-direction: column; box-sizing: border-box;
}
.device-card--pv { align-items: stretch; justify-content: center; min-height: 100%; }
.device-card--battery { align-items: stretch; justify-content: flex-start; }
.device-pv-gauges {
  width: 100%; display: flex; flex-wrap: nowrap; align-items: flex-start;
  box-sizing: border-box;
}
.device-pv-gauges--single { justify-content: center; }
.device-pv-gauges--single .device-pv-wrap { flex: 0 1 auto; width: 100%; max-width: 160px; }
.device-pv-gauges--dual {
  justify-content: center; gap: 4px 8px; padding: 0 2px;
}
.device-pv-gauges--dual .device-pv-wrap {
  flex: 1 1 0; min-width: 0; max-width: 50%;
}
.device-pv-gauges--dual .device-pv-gauge { max-width: 108px; }
.device-pv-gauges--dual .device-pv-value { font-size: 15px; }
.device-pv-gauges--dual .device-pv-label { font-size: 11px; margin-top: 2px; }
.device-pv-wrap { width: 100%; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.device-pv-gauge {
  position: relative; width: 100%; max-width: 140px; aspect-ratio: 100 / 104; flex-shrink: 0;
}
.device-pv-gauge svg { width: 100%; height: 100%; display: block; }
.device-pv-readout {
  position: absolute; left: 0; right: 0; top: 40%; transform: translateY(-50%);
  text-align: center; min-width: 0; padding: 0 10px; box-sizing: border-box; pointer-events: none;
}
.device-pv-value { font-size: 17px; font-weight: 700; line-height: 1.2; letter-spacing: -0.02em; margin: 0; }
.device-pv-label { font-size: 12px; color: var(--secondary-text-color); font-weight: 500; line-height: 1.3; margin: 3px 0 0; }
.device-pv-cap {
  font-size: 10px; color: var(--secondary-text-color); line-height: 1.25; margin: 0;
  text-align: center; width: 100%; opacity: 0.9;
}
.device-battery-card { width: 100%; box-sizing: border-box; display: flex; flex-direction: column; gap: 0; }
.device-battery-top {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center;
  column-gap: 12px; width: 100%; padding-bottom: 14px;
}
.device-battery-status-row { display: flex; align-items: center; gap: 10px; min-width: 0; }
.device-battery-svg { width: 44px; height: 22px; flex-shrink: 0; }
.device-battery-shell { fill: none; stroke: var(--secondary-text-color); stroke-width: 1.5; }
.device-battery-cap { fill: var(--secondary-text-color); }
.device-battery-fill { fill: #4caf50; }
.device-battery-card.is-discharging .device-battery-fill { fill: var(--fp-accent); }
.device-battery-card.is-charging .device-battery-fill { fill: #4caf50; }
.device-battery-status { font-size: 14px; font-weight: 600; line-height: 1.35; }
.device-battery-pct { font-size: 28px; font-weight: 700; line-height: 1.1; letter-spacing: -0.03em; text-align: right; }
.device-battery-metrics {
  display: flex; flex-direction: row; justify-content: space-between; align-items: flex-start;
  width: 100%; padding-top: 14px; border-top: 1px solid var(--divider-color, rgba(127,127,127,0.35));
}
.device-battery-metric { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 0 1 auto; }
.device-battery-metric--power { align-items: flex-start; text-align: left; }
.device-battery-metric--temp { align-items: flex-end; text-align: right; margin-left: auto; }
.device-battery-metric-label { font-size: 13px; color: var(--secondary-text-color); font-weight: 500; line-height: 1.3; margin: 0; }
.device-battery-metric-value { font-size: 17px; font-weight: 700; line-height: 1.25; letter-spacing: -0.02em; margin: 0; white-space: nowrap; }
.entity-list { border-radius: var(--fp-radius); overflow: hidden; border: 1px solid var(--divider-color, transparent); }
.entity-row { display: flex; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid var(--divider-color); font-size: 14px; }
.entity-row:last-child { border-bottom: none; }
.entity-name { color: var(--secondary-text-color); }
.entity-value { font-weight: 500; }
.device-param-sections { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.device-param-section {
  border-radius: var(--fp-radius);
  border: 1px solid var(--divider-color, transparent);
  background: var(--card-background-color, rgba(127,127,127,0.06));
  overflow: hidden;
}
.device-param-summary {
  width: 100%; border: none; background: transparent; cursor: pointer;
  padding: 14px 18px; font-weight: 600; font-size: 15px; text-align: left;
  display: flex; justify-content: space-between; align-items: center;
  color: inherit; font-family: inherit;
}
.device-param-section.is-open > .device-param-summary { border-bottom: 1px solid var(--divider-color); }
.device-param-summary::after { content: "›"; transform: rotate(90deg); opacity: 0.45; font-size: 18px; transition: transform 0.15s; }
.device-param-section.is-open > .device-param-summary::after { transform: rotate(-90deg); }
.device-param-section .entity-list { border: none; border-radius: 0; }
.device-param-table-wrap { overflow-x: auto; }
.device-param-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.device-param-table th, .device-param-table td { padding: 10px 14px; text-align: right; border-bottom: 1px solid var(--divider-color); white-space: nowrap; }
.device-param-table th:first-child, .device-param-table td:first-child { text-align: left; }
.device-param-table tr:last-child td { border-bottom: none; }
.device-param-table th { color: var(--secondary-text-color); font-weight: 500; font-size: 12px; }
.device-param-empty { padding: 14px 18px; font-size: 13px; color: var(--secondary-text-color); margin: 0; }
.device-param-updated { text-align: center; font-size: 12px; color: var(--secondary-text-color); margin-top: 16px; }
.fox-device-new-layout {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  column-gap: 16px; align-items: start;
  width: 100%; min-width: 0; box-sizing: border-box;
}
.fox-device-new-sidebar-col {
  grid-column: 1; align-self: start;
  min-width: 0; margin: 0; padding: 0;
  position: sticky; top: 0; z-index: 1;
}
.fox-device-new-sidebar-hero {
  display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: 6px; margin: 0 0 10px; padding: 0; width: 100%; box-sizing: border-box;
}
.fox-device-new-content,
.fox-device-new-analysis-stack {
  grid-column: 2; align-self: start;
  min-width: 0; margin: 0; padding: 0;
}
.fox-device-new-analysis-stack {
  display: flex; flex-direction: column; align-items: stretch;
  min-width: 0; width: 100%;
}
.fox-device-new-analysis-stack > .fox-device-new-summary-row {
  flex: 0 0 auto; width: 100%; min-width: 0;
  margin: 0 0 18px; padding: 0;
}
.fox-device-new-analysis-stack > .fox-device-new-toolbar-row {
  flex: 0 0 auto; width: 100%; min-width: 0;
  margin: 0 0 16px; padding: 0;
}
.fox-device-new-analysis-stack > .fox-device-new-charts-col {
  flex: 0 0 auto; width: 100%; min-width: 0;
  margin: 0; padding: 0;
}
.fox-device-new-summary-row { min-width: 0; width: 100%; }
.fox-device-new-toolbar-row { min-width: 0; width: 100%; }
.fox-device-new-content > .fox-device-new-summary { margin: 0 0 12px; }
.fox-device-new-summary {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; align-items: stretch;
  width: 100%; box-sizing: border-box;
}
.fox-device-new-summary > .fox-device-new-summary { display: contents; }
.fox-device-new-charts-col {
  display: flex; flex-direction: column; gap: 14px;
  min-width: 0; width: 100%;
}
.fox-device-new-toolbar-row .fox-analysis-toolbar { margin: 0; }
.fox-device-new-toolbar-row > .card { margin: 0; }
.fox-device-new-analysis-stack .fox-device-new-toolbar-row .fox-analysis-toolbar {
  margin: 0; box-sizing: border-box;
}
.fox-device-new-charts-col > .card { margin: 0; }
.fox-device-new-sidebar {
  margin: 0; width: 100%; box-sizing: border-box;
  border: 1px solid var(--divider-color); border-radius: 12px;
  background: var(--card-background-color); padding: 10px 12px 12px;
}
.fox-device-new-sidebar-hero .device-serial-btn { width: auto; max-width: 100%; }
.fox-device-new-sidebar-serial-row {
  display: flex; align-items: center; justify-content: center; gap: 4px;
  width: 100%; max-width: 100%; min-width: 0;
}
.fox-device-new-sidebar-serial-row .fox-device-new-sidebar-serial-btn {
  flex: 1 1 auto; min-width: 0; justify-content: center;
  font-size: 12px; color: var(--primary-text-color);
}
.fox-device-new-sidebar-serial-prefix {
  color: var(--secondary-text-color); font-weight: 500; flex-shrink: 0; font-size: 12px;
}
.fox-device-new-sidebar-copy-btn {
  flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; padding: 0; border: none; background: transparent;
  color: var(--secondary-text-color); cursor: pointer; border-radius: 6px;
  touch-action: manipulation;
}
.fox-device-new-sidebar-copy-icon { display: block; }
@media (hover: hover) {
  .fox-device-new-sidebar-copy-btn:hover { color: var(--primary-text-color); background: var(--secondary-background-color, rgba(127,127,127,0.12)); }
}
.fox-device-new-sidebar-divider {
  height: 1px; background: var(--divider-color); margin: 0 0 12px;
}
.fox-device-new-sidebar-img { width: 64px; height: auto; max-height: 72px; object-fit: contain; object-position: top center; flex-shrink: 0; display: block; }
.fox-device-new-sidebar-serial-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  padding: 4px 6px; margin: 0; border: none; background: transparent;
  color: var(--secondary-text-color); cursor: pointer; border-radius: 6px;
  font: inherit; max-width: 100%; width: auto;
}
.fox-device-new-sidebar-serial {
  font-family: ui-monospace, monospace; font-size: 12px; font-weight: 600;
  letter-spacing: 0.03em; line-height: 1.35; word-break: break-all;
  color: var(--primary-text-color);
}
.fox-device-new-sidebar-serial-muted { margin: 0; font-size: 11px; }
.fox-device-new-sidebar-serial-btn .chev { font-size: 12px; flex-shrink: 0; }
@media (hover: hover) {
  .fox-device-new-sidebar-serial-btn:hover { color: var(--primary-text-color); }
}
.fox-device-new-sidebar-section-title {
  margin: 0 0 10px; font-size: 14px; font-weight: 700; color: var(--primary-text-color);
}
.fox-device-new-sidebar-list { margin: 0; }
.fox-device-new-sidebar-row {
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px 12px;
  padding: 9px 0; border-bottom: 1px solid var(--divider-color);
  font-size: 12px; align-items: center;
}
.fox-device-new-sidebar-row:last-child { border-bottom: none; }
.fox-device-new-sidebar-row dt { margin: 0; color: var(--secondary-text-color); font-weight: 500; }
.fox-device-new-sidebar-row dd {
  margin: 0; text-align: right; font-weight: 600; color: var(--primary-text-color);
  word-break: break-word; display: flex; justify-content: flex-end; align-items: center;
}
.fox-device-new-sidebar-plant {
  display: inline-flex; align-items: center; justify-content: flex-end; gap: 4px; max-width: 100%;
}
.fox-device-new-sidebar-chevron { color: var(--secondary-text-color); font-size: 14px; line-height: 1; flex-shrink: 0; }
.fox-device-new-check-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 2px 10px 2px 6px; border-radius: 999px;
  font-size: 12px; font-weight: 600; line-height: 1.3; border: 1px solid transparent;
}
.fox-device-new-check-pill--ok {
  color: #52c41a; border-color: rgba(82, 196, 26, 0.5);
  background: rgba(82, 196, 26, 0.1);
}
.fox-device-new-check-pill--off {
  color: var(--secondary-text-color); border-color: var(--divider-color);
  background: var(--secondary-background-color);
}
.fox-device-new-check-pill--fault {
  color: #ff7875; border-color: rgba(255, 120, 117, 0.45);
  background: rgba(255, 120, 117, 0.1);
}
.fox-overview-pill--checking {
  color: #8c8c8c; border-color: rgba(140, 140, 140, 0.45);
  background: rgba(140, 140, 140, 0.1);
}
.fox-overview-pill--offgrid {
  color: #faad14; border-color: rgba(250, 173, 20, 0.5);
  background: rgba(250, 173, 20, 0.1);
}
.fox-overview-pill--work-self-use,
.fox-overview-pill--work-default {
  color: #d4b429; border-color: rgba(244, 208, 93, 0.55);
  background: rgba(244, 208, 93, 0.12);
}
.fox-overview-pill--work-feed-in {
  color: #5a9fd4; border-color: rgba(126, 184, 255, 0.5);
  background: rgba(126, 184, 255, 0.1);
}
.fox-overview-pill--work-back-up {
  color: #90a4ae; border-color: rgba(144, 164, 174, 0.5);
  background: rgba(144, 164, 174, 0.12);
}
.fox-overview-pill--work-force-charge {
  color: #b39ddb; border-color: rgba(126, 87, 194, 0.5);
  background: rgba(126, 87, 194, 0.12);
}
.fox-overview-pill--work-force-discharge {
  color: #ff8a65; border-color: rgba(239, 108, 87, 0.5);
  background: rgba(239, 108, 87, 0.12);
}
.fox-overview-pill--plant-baseline {
  color: var(--fp-green, #52c41a); border-color: rgba(82, 196, 26, 0.35);
  background: rgba(82, 196, 26, 0.08);
}
.fox-overview-pill--plant-storm {
  color: var(--fp-amber, #faad14); border-color: rgba(250, 173, 20, 0.45);
  background: rgba(250, 173, 20, 0.1);
}
.fox-overview-pill--plant-override {
  color: #b39ddb; border-color: rgba(126, 87, 194, 0.45);
  background: rgba(126, 87, 194, 0.1);
}
.fox-overview-pill--plant-manual {
  color: var(--secondary-text-color); border-color: var(--divider-color);
  background: var(--secondary-background-color);
}
.fox-overview-pill--plant-outage {
  color: var(--fp-red, #ff7875); border-color: rgba(255, 120, 117, 0.45);
  background: rgba(255, 120, 117, 0.1);
}
.fox-device-new-check-pill-icon { width: 14px; height: 14px; flex-shrink: 0; }
.fox-device-new-check-pill-text { white-space: nowrap; }
.fox-device-new-content { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.fox-alarm-page { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.fox-alarm-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.fox-alarm-title { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
.fox-alarm-updated { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
.fox-alarm-summary-grid {
  display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 14px; align-items: stretch;
}
.fox-alarm-mini-card { margin: 0; padding: 12px 14px 14px; min-height: 220px; display: flex; flex-direction: column; }
.fox-alarm-mini-card--wide { min-height: 220px; }
.fox-alarm-mini-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.fox-alarm-mini-title { margin: 0; font-size: 15px; font-weight: 700; }
.fox-alarm-mini-body { flex: 1; display: flex; flex-direction: column; justify-content: center; min-height: 0; }
.fox-alarm-donut-wrap { width: 120px; margin: 0 auto; }
.fox-alarm-donut-wrap svg { width: 100%; height: auto; display: block; }
.fox-alarm-legend { list-style: none; margin: 10px 0 0; padding: 0; display: flex; flex-direction: column; gap: 6px; font-size: 12px; }
.fox-alarm-legend li { display: flex; align-items: center; gap: 8px; }
.fox-alarm-legend li strong { margin-left: auto; font-weight: 700; }
.fox-alarm-legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.fox-alarm-no-data {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  min-height: 140px; color: var(--secondary-text-color); font-size: 13px;
}
.fox-alarm-list-card { margin: 0; padding: 0; overflow: hidden; }
.fox-alarm-tabs {
  display: flex; gap: 0; border-bottom: 1px solid var(--divider-color); padding: 0 16px;
}
.fox-alarm-tab {
  appearance: none; border: none; background: transparent; cursor: pointer;
  padding: 12px 16px 10px; font-size: 14px; color: var(--secondary-text-color);
  border-bottom: 2px solid transparent; margin-bottom: -1px;
}
.fox-alarm-tab.active { color: #7c3aed; font-weight: 600; border-bottom-color: #7c3aed; }
.fox-alarm-table-wrap { overflow-x: auto; padding: 8px 12px 16px; }
.fox-alarm-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.fox-alarm-table th, .fox-alarm-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--divider-color); }
.fox-alarm-table th { font-weight: 600; color: var(--secondary-text-color); font-size: 12px; }
.fox-alarm-severity {
  display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; text-transform: capitalize;
}
.fox-alarm-severity--critical { color: #cf1322; background: rgba(255, 77, 79, 0.12); }
.fox-alarm-severity--warning { color: #d48806; background: rgba(250, 173, 20, 0.14); }
.fox-alarm-severity--info { color: #096dd9; background: rgba(24, 144, 255, 0.12); }
.fox-alarm-status { font-weight: 600; font-size: 12px; }
.fox-alarm-status--warn { color: #d48806; }
.fox-alarm-status--ok { color: #389e0d; }
.fox-alarm-empty-list {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; padding: 48px 20px; color: var(--secondary-text-color);
}
.fox-alarm-cog-wrap {
  width: 120px; height: 120px; display: flex; align-items: center; justify-content: center;
}
.fox-alarm-cog-wrap .fox-alarm-cog-svg { width: 100%; height: 100%; display: block; overflow: visible; }
/* CSS spin on gear groups — gray clockwise, green counter-clockwise */
.fox-alarm-cog-gear--gray {
  transform-origin: 512px 512px;
  transform-box: view-box;
  animation: fox-alarm-cog-spin 8s linear infinite;
}
.fox-alarm-cog-gear--green {
  transform-origin: 1106px 1106px;
  transform-box: view-box;
  animation: fox-alarm-cog-spin 6s linear infinite reverse;
}
@media (prefers-reduced-motion: reduce) {
  .fox-alarm-cog-gear--gray, .fox-alarm-cog-gear--green { animation: none; }
}
@keyframes fox-alarm-cog-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.fox-alarm-empty-icon { width: 96px; height: auto; opacity: 0.9; }
.fox-alarm-empty-list p { margin: 0; font-size: 15px; font-weight: 500; }
.fox-alarm-no-data-svg { width: 64px; height: auto; display: block; }
.fox-alarm-no-data-svg svg { width: 100%; height: auto; display: block; }
.fox-alarm-no-data-svg .fox-alarm-icon-empty ellipse {
  fill: color-mix(in srgb, var(--secondary-text-color) 16%, transparent);
}
.fox-alarm-no-data-svg .fox-alarm-icon-empty path[fill="#fafafa"] {
  fill: color-mix(in srgb, var(--card-background-color, var(--ha-card-background, #fff)) 88%, var(--primary-text-color) 12%);
}
.fox-alarm-no-data-svg .fox-alarm-icon-empty g[stroke="#d9d9d9"] path,
.fox-alarm-no-data-svg .fox-alarm-icon-empty path[stroke="#d9d9d9"] {
  stroke: color-mix(in srgb, var(--secondary-text-color) 38%, transparent);
}
.fox-alarm-table-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; padding: 56px 20px 64px; color: var(--secondary-text-color); font-size: 13px;
}
.fox-alarm-hist-toolbar {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px;
  padding: 12px 16px; border-bottom: 1px solid var(--divider-color);
}
.fox-alarm-hist-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.fox-alarm-hist-select-wrap { margin: 0; }
.fox-alarm-hist-select {
  min-width: 108px; padding: 6px 28px 6px 10px; font-size: 13px; border-radius: 6px;
  border: 1px solid var(--divider-color); background: var(--card-background-color, var(--ha-card-background));
  color: var(--primary-text-color);
}
.fox-alarm-hist-clear {
  appearance: none; border: none; background: transparent; cursor: pointer;
  font-size: 13px; color: var(--secondary-text-color); padding: 6px 8px;
}
.fox-alarm-hist-clear:hover { color: #7c3aed; }
.fox-alarm-hist-range { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-left: auto; }
.fox-alarm-hist-dates { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fox-alarm-hist-dates--hidden { display: none; }
.fox-alarm-hist-date {
  padding: 6px 10px; font-size: 13px; border-radius: 6px; border: 1px solid var(--divider-color);
  background: var(--card-background-color, var(--ha-card-background)); color: var(--primary-text-color);
  min-width: 0; max-width: 180px;
}
.fox-alarm-hist-date-sep { color: var(--secondary-text-color); font-size: 12px; }
.fox-alarm-hist-range-btn {
  appearance: none; cursor: pointer; padding: 6px 14px; font-size: 13px; border-radius: 6px;
  border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color);
}
.fox-alarm-hist-range-btn.active {
  border-color: #7c3aed; color: #7c3aed; font-weight: 600;
}
.fox-alarm-table--historical { font-size: 12px; }
.fox-alarm-table--historical th, .fox-alarm-table--historical td { white-space: nowrap; }
.fox-alarm-table--historical .fox-alarm-name-cell { white-space: normal; min-width: 140px; }
.fox-alarm-row--clickable { cursor: pointer; }
.fox-alarm-row--clickable:hover td { background: color-mix(in srgb, #7c3aed 6%, transparent); }
.fox-alarm-name-cell { font-weight: 600; }
.fox-alarm-row-chev { margin-left: 6px; color: var(--secondary-text-color); font-size: 12px; }
.fox-alarm-detail-modal { max-width: 560px; }
.fox-alarm-detail-body { font-size: 14px; line-height: 1.5; }
.fox-alarm-detail-manual { margin: 0 0 10px; color: var(--secondary-text-color); font-size: 13px; }
.fox-alarm-detail-label { font-weight: 600; color: var(--primary-text-color); margin-right: 6px; }
.fox-alarm-detail-desc { margin: 0 0 14px; }
.fox-alarm-detail-subtitle { margin: 0 0 8px; font-size: 15px; font-weight: 700; }
.fox-alarm-detail-solutions { margin: 0 0 16px; padding-left: 18px; }
.fox-alarm-detail-solutions li { margin-bottom: 6px; }
.fox-alarm-detail-section { margin-top: 8px; padding-top: 12px; border-top: 1px solid var(--divider-color); }
.fox-alarm-detail-meta { display: grid; gap: 8px; margin: 0 0 12px; }
.fox-alarm-detail-meta div { display: flex; gap: 8px; font-size: 13px; }
.fox-alarm-detail-meta dt { margin: 0; color: var(--secondary-text-color); min-width: 110px; }
.fox-alarm-detail-meta dd { margin: 0; font-weight: 600; }
.fox-alarm-detail-bits-title { margin: 0 0 8px; font-size: 13px; font-weight: 600; }
.fox-alarm-detail-table-wrap { overflow-x: auto; margin-bottom: 8px; }
.fox-alarm-detail-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.fox-alarm-detail-table th, .fox-alarm-detail-table td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--divider-color); }
.fox-alarm-detail-note, .fox-alarm-detail-source { margin: 8px 0 0; font-size: 12px; color: var(--secondary-text-color); }
.fox-device-new-layout--alarms .fox-device-new-content { gap: 0; }
.fox-device-new-layout--alarms .fox-device-new-content > [data-device-new-alarms] { min-width: 0; width: 100%; }
@media (max-width: 900px) {
  .fox-alarm-summary-grid { grid-template-columns: 1fr; }
  .fox-alarm-mini-card--wide { min-height: 200px; }
}
.fox-device-new-summary-card {
  border-radius: 12px; padding: 10px 12px 12px;
  display: flex; flex-direction: column; gap: 0; min-height: 0; height: auto; align-self: stretch;
  border: 1px solid color-mix(in srgb, var(--fox-summary-accent, var(--divider-color)) 22%, var(--divider-color));
  background: var(--fox-summary-bg, var(--card-background-color));
  overflow: hidden;
}
.fox-device-new-summary-head {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 10px;
  flex: 0 0 auto; margin-bottom: 4px;
}
.fox-device-new-summary-body {
  flex: 1 1 auto; display: flex; flex-direction: column; justify-content: flex-end;
  min-width: 0;
}
.fox-device-new-summary-card--temps .fox-device-new-summary-body {
  justify-content: flex-start;
}
.fox-device-new-summary-label {
  font-size: 13px; color: var(--secondary-text-color); font-weight: 500;
  line-height: 1.35; flex: 1; min-width: 0;
}
.fox-device-new-summary-icon {
  width: 42px; height: 42px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; pointer-events: none;
}
.fox-device-new-summary-icon svg { width: 100%; height: 100%; display: block; }
.fox-device-new-summary-value {
  display: inline-flex; align-items: baseline; gap: 0.2em;
  font-size: 20px; font-weight: 700; line-height: 1.15; color: var(--primary-text-color);
}
.fox-summary-metric-num { font-size: 1em; font-weight: inherit; line-height: inherit; }
.fox-summary-metric-unit {
  font-size: 0.58em; font-weight: 600; line-height: 1; letter-spacing: 0.02em;
  color: color-mix(in srgb, var(--primary-text-color) 88%, var(--secondary-text-color));
}
.fox-device-new-summary-temp-labels,
.fox-device-new-summary-temp-values {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; min-width: 0;
}
.fox-device-new-summary-temp-values { margin-top: auto; padding-top: 4px; }
.fox-device-new-summary-temp-label {
  font-size: 12px; color: var(--secondary-text-color); font-weight: 500; line-height: 1.3;
}
.fox-device-new-summary-temp-value { font-size: 20px; }
.fox-device-new-metric-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  border: 1px solid var(--divider-color); border-radius: 10px; overflow: hidden;
  background: var(--card-background-color);
  --fox-metric-label-bg: color-mix(in srgb, var(--divider-color) 22%, var(--card-background-color));
}
.fox-device-new-metric-item {
  padding: 0; min-height: 40px;
  border-right: 1px solid var(--divider-color); border-bottom: 1px solid var(--divider-color);
  display: flex; align-items: stretch; overflow: hidden;
  background: var(--card-background-color);
}
.fox-device-new-metric-item:nth-child(3n) { border-right: none; }
.fox-device-new-metric-label-wrap {
  flex: 1 1 52%; min-width: 0; padding: 10px 12px;
  display: flex; align-items: center; gap: 0;
  background: var(--fox-metric-label-bg);
  border-right: 1px solid var(--divider-color);
  font-size: 13px; line-height: 1.4;
}
.fox-device-new-metric-label { color: var(--secondary-text-color); font-weight: 500; word-break: break-word; }
.fox-device-new-metric-colon { color: var(--secondary-text-color); flex-shrink: 0; }
.fox-device-new-metric-value {
  flex: 1 1 48%; min-width: 0; padding: 10px 12px;
  display: flex; align-items: center;
  font-size: 13px; font-weight: 600; line-height: 1.4;
  color: var(--primary-text-color); word-break: break-word;
}
.fox-device-new-metric-value .fox-device-new-check-pill,
.fox-device-new-metric-value .fox-device-new-grid-status { vertical-align: middle; }
.fox-device-new-realtime .device-param-table-wrap { margin: 0; --fox-metric-label-bg: color-mix(in srgb, var(--divider-color) 22%, var(--card-background-color)); }
.fox-device-new-realtime .device-param-table { width: 100%; border-collapse: collapse; }
.fox-device-new-realtime .device-param-table th {
  background: var(--fox-metric-label-bg, color-mix(in srgb, var(--divider-color) 22%, var(--card-background-color)));
}
.fox-device-new-realtime .device-param-table td { background: var(--card-background-color); }
.fox-device-new-realtime .device-param-table tbody td:first-child {
  background: var(--fox-metric-label-bg, color-mix(in srgb, var(--divider-color) 22%, var(--card-background-color)));
  color: var(--secondary-text-color); font-weight: 500;
}
.fox-device-new-chart-toolbar { margin: 0; }
.fox-device-new-card {
  border: 1px solid var(--divider-color); border-radius: 14px;
  background: var(--card-background-color); padding: 16px;
  box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,0.08));
  min-width: 0;
}
.fox-device-new-charts-col .fox-device-new-card.card { margin: 0; }
.fox-device-new-card + .fox-device-new-card { margin-top: 0; }
.fox-device-new-card-head {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 10px 16px; margin-bottom: 12px;
}
.fox-device-new-card-head--energy { align-items: flex-start; }
.fox-device-new-card-toolbar {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end;
  gap: 10px 14px; margin-left: auto; max-width: 100%;
}
.fox-device-new-card-toolbar .energy-period-tabs { margin: 0; flex: 1 1 auto; justify-content: flex-end; }
.fox-device-new-card-toolbar .energy-date-nav { margin: 0; flex: 0 0 auto; }
.fox-device-new-date-nav .energy-date-label { min-width: 108px; font-size: 14px; }
.fox-device-new-date-nav button { width: 32px; height: 32px; font-size: 18px; }
.fox-device-new-card-title { margin: 0; font-size: 16px; font-weight: 700; }
.fox-device-new-section { margin-bottom: 18px; }
.fox-device-new-section:last-child { margin-bottom: 0; }
.fox-device-new-section-title {
  margin: 0 0 10px; padding-left: 10px; border-left: 3px solid var(--primary-color, #8a4dff);
  font-size: 15px; font-weight: 700;
}
.fox-device-new-subsection { margin-bottom: 14px; }
.fox-device-new-subsection:last-child { margin-bottom: 0; }
.fox-device-new-subsection-title {
  margin: 0 0 8px; font-size: 13px; font-weight: 700; color: var(--primary-text-color);
}
.fox-device-new-grid-status {
  display: inline-flex; align-items: center; gap: 6px; font-weight: 600;
}
.fox-device-new-grid-status-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #52c41a; flex-shrink: 0;
}
.fox-device-new-grid-status--import .fox-device-new-grid-status-dot { background: #faad14; }
.fox-device-new-grid-status--idle .fox-device-new-grid-status-dot { background: #8c8c8c; }
.fox-device-new-online-badge {
  display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;
  border: 1px solid var(--divider-color); color: var(--secondary-text-color);
}
.fox-device-new-online-badge--on {
  border-color: #52c41a; color: #52c41a; background: rgba(82, 196, 26, 0.08);
}
@media (max-width: 980px) {
  .fox-device-new-layout { grid-template-columns: 1fr; row-gap: 14px; }
  .fox-device-new-sidebar-col,
  .fox-device-new-content,
  .fox-device-new-analysis-stack { grid-column: 1; }
  .fox-device-new-sidebar-col { position: static; }
  .fox-device-new-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .fox-device-new-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .fox-device-new-metric-item:nth-child(3n) { border-right: 1px solid var(--divider-color); }
  .fox-device-new-metric-item:nth-child(2n) { border-right: none; }
}
@container fp-main (max-width: 700px) {
  .fox-device-new-layout { grid-template-columns: 1fr; row-gap: 14px; }
  .fox-device-new-sidebar-col,
  .fox-device-new-content,
  .fox-device-new-analysis-stack { grid-column: 1; }
  .fox-device-new-sidebar-col { position: static; }
}
.shell.narrow .fox-device-new-layout { grid-template-columns: 1fr; row-gap: 14px; }
.shell.narrow .fox-device-new-sidebar-col,
.shell.narrow .fox-device-new-content,
.shell.narrow .fox-device-new-analysis-stack { grid-column: 1; }
.shell.narrow .fox-device-new-sidebar-col { position: static; }
@media (max-width: 520px) {
  .fox-device-new-summary { grid-template-columns: 1fr; }
  .fox-device-new-metric-grid { grid-template-columns: 1fr; }
  .fox-device-new-metric-item { border-right: none; }
}
.period-card { border: 1px solid var(--divider-color); border-radius: var(--fp-radius); padding: 16px; margin-bottom: 12px; background: var(--secondary-background-color, rgba(127,127,127,0.06)); }
.period-card h4 { margin: 0 0 12px; font-size: 15px; }
.field { margin-bottom: 12px; }
.field label { display: block; font-size: 12px; color: var(--secondary-text-color); margin-bottom: 6px; }
.field input[type="time"] {
  width: 9rem; max-width: 100%; box-sizing: border-box;
  padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; font-family: inherit;
}
.field select {
  width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; font-family: inherit;
}
.period-times { display: flex; flex-wrap: wrap; gap: 20px 24px; margin-bottom: 4px; }
.period-times .field { margin-bottom: 0; }
.toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; font-size: 14px; }
.toggle-row input { width: 18px; height: 18px; accent-color: var(--fp-accent); }
.field-hint { font-size: 12px; color: var(--secondary-text-color); margin: 0 0 8px; line-height: 1.45; }
.tariff-entity-picker-host { display: block; min-height: 56px; }
.tariff-entity-picker-host ha-entity-picker { display: block; width: 100%; }
.tariff-entity-picker-loading { margin: 0; font-size: 13px; color: var(--secondary-text-color); }
.tariff-entity-picker-error { margin: 0; font-size: 13px; color: var(--error-color, #db4437); }
.tariff-schedule-card { margin-top: 8px; }
.tariff-band-picker { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 12px; }
.tariff-band-chip { display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 999px; border: 2px solid transparent; background: var(--card-background-color, #fff); font-size: 13px; cursor: pointer; }
.tariff-band-chip.is-active { border-color: var(--primary-color, #03a9f4); box-shadow: 0 0 0 1px var(--primary-color, #03a9f4); }
.tariff-band-swatch { width: 14px; height: 14px; border-radius: 3px; flex-shrink: 0; }
.tariff-hour-grid { display: grid; grid-template-columns: repeat(24, minmax(0, 1fr)); gap: 3px; margin: 0 0 6px; }
.tariff-hour-block { aspect-ratio: 1; min-height: 18px; border: none; border-radius: 3px; padding: 0; cursor: pointer; opacity: 0.92; }
.tariff-hour-block:hover { opacity: 1; transform: scaleY(1.08); }
.tariff-hour-labels { display: grid; grid-template-columns: repeat(24, minmax(0, 1fr)); gap: 3px; font-size: 9px; color: var(--secondary-text-color); text-align: center; margin-bottom: 12px; }
.tariff-band-rates { display: grid; gap: 10px; }
.tariff-band-rate-row { display: grid; grid-template-columns: auto 1fr 1fr; gap: 10px; align-items: end; }
.tariff-schedule-card.tariff-schedule-locked .tariff-band-picker,
.tariff-schedule-card.tariff-schedule-locked .tariff-hour-grid { opacity: 0.72; pointer-events: none; }
.tariff-schedule-card.tariff-schedule-locked .tariff-hour-block { cursor: default; transform: none; }
.tariff-schedule-card.tariff-schedule-locked .tariff-band-chip[data-action="tariff-pick-band"] { cursor: default; }
.tariff-schedule-card.tariff-schedule-locked .tariff-band-rate-row input { opacity: 0.55; cursor: not-allowed; }
.tariff-rate-block.tariff-standing-locked input[data-field="tariff:standing:p"] { opacity: 0.55; cursor: not-allowed; }
@media (max-width: 720px) {
  .tariff-band-rate-row { grid-template-columns: 1fr; }
  .tariff-hour-grid, .tariff-hour-labels { grid-template-columns: repeat(12, minmax(0, 1fr)); }
}
.field-link { color: var(--fp-accent); text-decoration: none; }
.field-link:hover { text-decoration: underline; }
.pv-range-row { display: flex; align-items: center; gap: 12px; }
.pv-range-row input[type="range"] { flex: 1; min-width: 0; accent-color: var(--fp-accent); }
.pv-range-value { min-width: 56px; font-size: 14px; font-variant-numeric: tabular-nums; text-align: right; color: var(--primary-text-color); }
.pv-string-card.pv-string-disabled .pv-config-fields { opacity: 0.55; pointer-events: none; }
.pv-geometry-block { margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(127,127,127,0.2); }
.pv-geometry-block:first-of-type { margin-top: 0; padding-top: 0; border-top: none; }
.pv-geometry-label { margin: 0 0 8px; font-size: 13px; color: var(--secondary-text-color); }
.field input[type="number"].pv-eff-input { width: 100%; max-width: 120px; box-sizing: border-box; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); background: var(--card-background-color, #1c1c1e); color: var(--primary-text-color); }
.triple-soc { padding: 8px 4px 4px; user-select: none; touch-action: none; }
.triple-soc-head { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.triple-soc-battery {
  width: 52px; height: 88px; flex-shrink: 0; border-radius: 10px;
  border: 2px solid var(--divider-color); position: relative; overflow: hidden;
  background: var(--secondary-background-color);
}
.triple-soc-battery-fill {
  position: absolute; left: 4px; right: 4px; bottom: 4px; border-radius: 0 0 6px 6px;
  background: linear-gradient(180deg, #66bb6a 0%, #2e7d32 100%);
  transition: height 0.35s ease, top 0.35s ease, border-radius 0.2s ease;
  min-height: 4px;
}
.triple-soc-battery-fill.is-full {
  top: 4px;
  height: auto;
  border-radius: 6px;
}
.triple-soc-battery-cap {
  position: absolute; top: -8px; left: 50%; transform: translateX(-50%);
  width: 22px; height: 8px; border-radius: 4px 4px 0 0;
  background: var(--divider-color);
}
.triple-soc-battery-pct {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 700; z-index: 1; text-shadow: 0 1px 2px rgba(0,0,0,0.35);
}
.triple-soc-summary { flex: 1; font-size: 13px; color: var(--secondary-text-color); line-height: 1.5; }
.triple-soc-summary strong { color: var(--primary-text-color); font-weight: 600; }
.triple-soc-track-wrap { position: relative; padding: 16px 8px 8px; margin: 0 -4px; }
.triple-soc-track {
  position: relative; height: 14px; border-radius: 999px;
  background: var(--divider-color); overflow: visible;
}
.triple-soc-zones { position: absolute; inset: 0; border-radius: 999px; overflow: hidden; display: flex; }
.triple-soc-zone { height: 100%; }
.triple-soc-zone.critical { background: color-mix(in srgb, #e53935 55%, var(--divider-color)); }
.triple-soc-zone.reserve { background: color-mix(in srgb, #f9a825 50%, var(--divider-color)); }
.triple-soc-zone.usable { background: color-mix(in srgb, #2e7d32 55%, var(--divider-color)); }
.triple-soc-zone.headroom { background: color-mix(in srgb, var(--fp-accent) 35%, var(--divider-color)); }
.triple-soc-live {
  position: absolute; top: -6px; bottom: -6px; width: 3px; margin-left: -1px;
  background: var(--primary-text-color); border-radius: 2px; z-index: 2;
  box-shadow: 0 0 0 2px var(--card-background-color);
  pointer-events: none;
}
.triple-soc-live::after {
  content: "Now"; position: absolute; top: -20px; left: 50%; transform: translateX(-50%);
  font-size: 10px; font-weight: 600; white-space: nowrap; color: var(--primary-text-color);
}
.triple-soc-thumb {
  position: absolute; top: 50%; width: 26px; height: 26px; margin: -13px 0 0 -13px;
  border-radius: 50%; border: 3px solid #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.35);
  cursor: grab; padding: 0; transition: transform 0.1s;
}
.triple-soc-thumb[data-soc-thumb="min_soc"] { z-index: 3; }
.triple-soc-thumb[data-soc-thumb="min_soc_on_grid"] { z-index: 4; }
.triple-soc-thumb[data-soc-thumb="max_soc"] { z-index: 5; }
.triple-soc-thumb.is-dragging { z-index: 10; transform: scale(1.1); transition: transform 0.1s; }
.triple-soc-thumb:active { cursor: grabbing; }
.triple-soc-scale { display: flex; justify-content: space-between; font-size: 11px; color: var(--secondary-text-color); margin-top: 10px; padding: 0 4px; }
.soc-legend { display: flex; flex-wrap: wrap; gap: 12px 16px; margin-top: 16px; font-size: 12px; color: var(--secondary-text-color); }
.soc-legend span { display: inline-flex; align-items: center; gap: 6px; }
.soc-legend i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.soc-numeric { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 18px; }
.soc-numeric label { font-size: 11px; color: var(--secondary-text-color); display: block; margin-bottom: 4px; }
.soc-numeric input {
  width: 100%; box-sizing: border-box; padding: 8px 10px; border-radius: 8px;
  border: 1px solid var(--divider-color); background: var(--card-background-color);
  color: var(--primary-text-color); font-size: 15px; font-weight: 600; text-align: center; font-family: inherit;
}
.soc-limit-note {
  margin-top: 14px; padding: 10px 12px; font-size: 12px; line-height: 1.45;
  color: var(--secondary-text-color);
  background: color-mix(in srgb, var(--fp-amber) 14%, var(--card-background-color));
  border-radius: 10px; border-left: 3px solid var(--fp-amber);
}
.soc-limit-note strong { color: var(--primary-text-color); font-weight: 600; }
.soc-validation {
  margin-top: 14px; padding: 10px 12px; border-radius: 8px;
  background: color-mix(in srgb, #e53935 18%, var(--card-background-color));
  border: 1px solid color-mix(in srgb, #e53935 45%, transparent);
  color: var(--primary-text-color); font-size: 13px; line-height: 1.45;
}
.soc-validation p { margin: 0; }
.soc-validation p + p { margin-top: 6px; }
.soc-validation.warn {
  background: color-mix(in srgb, var(--fp-amber) 18%, var(--card-background-color));
  border-color: color-mix(in srgb, var(--fp-amber) 45%, transparent);
}
.soc-result-panel {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--divider-color);
  background: var(--card-background-color);
}
.soc-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.soc-result-head strong {
  font-size: 15px;
  font-weight: 600;
}
.soc-result-close {
  border: 0;
  background: transparent;
  color: var(--secondary-text-color);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
}
.soc-result-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.soc-result-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  line-height: 1.35;
}
.soc-result-icon {
  flex: 0 0 22px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  margin-top: 1px;
}
.soc-result-item.ok .soc-result-icon {
  background: #2e7d32;
  color: #fff;
}
.soc-result-item.err .soc-result-icon {
  background: #c62828;
  color: #fff;
}
.soc-result-text strong {
  display: block;
  margin-bottom: 2px;
}
.mode-grid { display: grid; gap: 8px; }
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
.mode-option-icon--smart-charge { border: none; background: transparent; }
.mode-option-icon--smart-charge img {
  display: block; width: 100%; height: 100%; object-fit: cover; border: none;
}
.mode-option-body { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; flex: 1; min-width: 0; }
.mode-option .name { display: block; font-weight: 600; font-size: 15px; line-height: 1.3; }
.mode-option .hint { display: block; font-size: 12px; line-height: 1.4; color: var(--secondary-text-color); }
.hero { border-radius: var(--fp-radius); overflow: hidden; background: var(--card-background-color); margin-bottom: 14px; border: 1px solid var(--divider-color); }
.hero-caption { padding: 12px 16px; font-size: 13px; color: var(--secondary-text-color); line-height: 1.45; border-top: 1px solid var(--divider-color); }
.fp-banner-hero {
  display: block; box-sizing: border-box;
  width: calc(100% + 48px); max-width: none;
  margin: -20px -24px 20px; padding: 0; border: none;
  background: #0a1018; overflow: visible; line-height: 0;
}
.shell.narrow .fp-banner-hero { width: calc(100% + 32px); margin: -16px -16px 16px; }
.fp-banner-hero > img {
  display: block; width: 100%; height: auto;
  max-height: none; min-height: 0; margin: 0; padding: 0; border: 0;
}
.fp-banner-hero--wide > img {
  width: 100%; max-width: 100%; height: auto;
  aspect-ratio: ${BANNER_HERO_WIDE_WIDTH} / ${BANNER_HERO_WIDE_HEIGHT};
  object-fit: contain; object-position: center top;
}
.smart-charge-settings-header { margin-top: 0; margin-bottom: 16px; }
.sc-status-card {
  border-radius: 14px; padding: 16px; margin-bottom: 14px;
  border: 1px solid var(--divider-color);
  background: linear-gradient(145deg, color-mix(in srgb, var(--fp-accent) 8%, var(--card-background-color)), var(--card-background-color));
}
.sc-status-card--exporting {
  background: linear-gradient(145deg, color-mix(in srgb, var(--fp-amber,#f9a825) 14%, var(--card-background-color)), var(--card-background-color));
}
.sc-status-card--armed {
  background: linear-gradient(145deg, color-mix(in srgb, var(--fp-green,#4caf50) 12%, var(--card-background-color)), var(--card-background-color));
}
.sc-status-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.sc-status-title { margin: 0; font-size: 15px; font-weight: 600; }
.sc-status-reason { margin: 4px 0 0; font-size: 13px; line-height: 1.45; color: var(--secondary-text-color); }
.sc-status-pill {
  flex-shrink: 0; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;
  background: color-mix(in srgb, var(--secondary-text-color) 12%, transparent);
}
.sc-status-pill--armed { background: color-mix(in srgb, var(--fp-green,#4caf50) 22%, transparent); color: var(--fp-green,#4caf50); }
.sc-status-pill--export { background: color-mix(in srgb, var(--fp-amber,#f9a825) 22%, transparent); color: var(--fp-amber,#f9a825); }
.sc-status-pill--idle { background: color-mix(in srgb, var(--fp-accent) 18%, transparent); color: var(--fp-accent); }
.sc-stat-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
.sc-stat-tile {
  padding: 10px 12px; border-radius: 10px; background: color-mix(in srgb, var(--primary-text-color) 4%, var(--card-background-color));
  border: 1px solid color-mix(in srgb, var(--divider-color) 80%, transparent);
}
.sc-stat-label { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--secondary-text-color); margin-bottom: 4px; }
.sc-stat-value { font-size: 18px; font-weight: 700; line-height: 1.2; }
.sc-gauge-track { margin-top: 8px; height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--divider-color) 70%, transparent); overflow: hidden; }
.sc-gauge-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--fp-accent), var(--fp-green,#4caf50)); }
.sc-timeline-wrap { margin-top: 4px; }
.sc-timeline { display: flex; gap: 2px; height: 28px; align-items: stretch; }
.sc-timeline-seg { flex: 1 1 0; min-width: 2px; border-radius: 3px; opacity: 0.85; }
.sc-timeline-seg--charge { background: var(--fp-green,#4caf50); }
.sc-timeline-seg--export { background: var(--fp-amber,#f9a825); }
.sc-timeline-seg--candidate { background: color-mix(in srgb, var(--fp-accent) 70%, var(--fp-green,#4caf50)); }
.sc-timeline-seg--idle { background: color-mix(in srgb, var(--secondary-text-color) 35%, transparent); }
.sc-timeline-seg--now { box-shadow: 0 0 0 2px var(--primary-text-color); opacity: 1; }
.sc-timeline-legend { display: flex; flex-wrap: wrap; gap: 10px 14px; margin-top: 8px; font-size: 11px; color: var(--secondary-text-color); }
.sc-legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }
.sc-legend-dot--charge { background: var(--fp-green,#4caf50); }
.sc-legend-dot--export { background: var(--fp-amber,#f9a825); }
.sc-legend-dot--candidate { background: var(--fp-accent); }
.sc-legend-dot--idle { background: color-mix(in srgb, var(--secondary-text-color) 45%, transparent); }
.sc-empty-hint { margin: 0; font-size: 12px; color: var(--secondary-text-color); line-height: 1.45; }
.sc-mode-panel {
  margin-top: 14px; padding: 14px 14px 4px; border-radius: 12px;
  border: 1px solid var(--divider-color);
  background: color-mix(in srgb, var(--sc-mode-accent, var(--fp-accent)) 6%, var(--card-background-color));
  border-left: 4px solid var(--sc-mode-accent, var(--fp-accent));
}
.sc-mode-panel-title { margin: 0 0 12px; font-size: 13px; font-weight: 600; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.04em; display: flex; align-items: center; gap: 8px; }
.sc-mode-panel-icon { flex: 0 0 28px; width: 28px; height: 28px; border-radius: 6px; overflow: hidden; }
.sc-mode-panel-icon img { display: block; width: 100%; height: 100%; object-fit: cover; border: none; }
.sc-spread-pairs { display: flex; flex-direction: column; gap: 6px; margin: 10px 0 0; }
.sc-spread-pair {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 8px 10px; border-radius: 8px; font-size: 12px;
  background: color-mix(in srgb, var(--primary-text-color) 4%, var(--card-background-color));
  border: 1px solid color-mix(in srgb, var(--divider-color) 70%, transparent);
}
.sc-spread-pair strong { color: var(--fp-green,#4caf50); font-weight: 600; }
.sc-section-details { margin-top: 12px; }
.sc-section-details summary { cursor: pointer; font-weight: 600; font-size: 13px; padding: 6px 0; color: var(--secondary-text-color); }
.sc-section-details[open] summary { margin-bottom: 10px; color: inherit; }
.storm-settings-header { margin-top: 0; margin-bottom: 16px; }
.trigger-chip { display: inline-block; padding: 4px 10px; border-radius: 8px; font-size: 12px; background: var(--secondary-background-color); margin: 4px 4px 0 0; }
.trigger-chips-wrap { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 10px; min-height: 28px; }
.trigger-chip-selected { display: inline-flex; align-items: center; gap: 4px; padding-right: 8px; background: color-mix(in srgb, var(--fp-accent) 18%, var(--secondary-background-color)); }
.trigger-chip-selected button {
  border: none; background: transparent; color: var(--secondary-text-color);
  cursor: pointer; font-size: 16px; line-height: 1; padding: 0 4px; font-family: inherit;
}
.trigger-chip-selected button:hover { color: var(--fp-red); }
.trigger-filter { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: inherit; font-family: inherit; font-size: 14px; margin-bottom: 8px; }
.trigger-filter-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.trigger-filter-actions .btn { padding: 8px 12px; font-size: 13px; }
.trigger-list { max-height: 280px; overflow-y: auto; border: 1px solid var(--divider-color); border-radius: 10px; padding: 0 12px; background: var(--card-background-color); }
.trigger-row { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--divider-color); font-size: 13px; }
.trigger-row:last-child { border-bottom: none; }
.trigger-row.suggested { background: color-mix(in srgb, var(--fp-amber) 8%, transparent); margin: 0 -12px; padding-left: 12px; padding-right: 12px; }
.trigger-row label { flex: 1; cursor: pointer; line-height: 1.35; user-select: none; }
.trigger-row input[type="checkbox"] { margin-top: 3px; flex-shrink: 0; width: 18px; height: 18px; accent-color: var(--fp-accent); cursor: pointer; }
.trigger-row .entity-id { display: block; font-size: 11px; color: var(--secondary-text-color); margin-top: 2px; }
.trigger-row .entity-state { font-size: 11px; color: var(--fp-accent); margin-left: auto; white-space: nowrap; }
.trigger-section-title { font-size: 12px; font-weight: 600; color: var(--secondary-text-color); margin: 10px 0 6px; text-transform: uppercase; letter-spacing: 0.04em; }
.storm-hint { margin: 0 0 12px; font-size: 13px; line-height: 1.45; color: var(--secondary-text-color); }
.gw-card { border-left: 3px solid var(--fp-accent); }
.gw-card.gw-ready { border-left-color: var(--fp-green, #4caf50); }
.gw-card.gw-warn { border-left-color: var(--fp-amber); }
.storm-solcast-card { border-left: 3px solid var(--fp-amber, #f9a825); }
.gw-status { font-size: 13px; line-height: 1.45; margin: 0 0 10px; color: var(--secondary-text-color); }
.gw-status strong { color: inherit; }
.gw-select { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: inherit; font-family: inherit; font-size: 14px; margin-bottom: 10px; }
.gw-linked { font-size: 12px; color: var(--secondary-text-color); margin: 8px 0 0; line-height: 1.45; }
.gw-linked code { font-size: 11px; }
.storm-advanced summary { cursor: pointer; font-weight: 600; font-size: 13px; padding: 4px 0; color: var(--secondary-text-color); }
.storm-advanced[open] summary { margin-bottom: 10px; color: inherit; }
.storm-advanced { margin-top: 4px; }
.storm-weather-category-list { display: flex; flex-direction: column; }
.storm-weather-category-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 2px;
  border-bottom: 1px solid color-mix(in srgb, var(--divider-color, #888) 35%, transparent);
}
.storm-weather-category-row:last-child { border-bottom: none; }
.storm-weather-category-icon { width: 40px; height: 40px; flex-shrink: 0; object-fit: contain; }
.storm-weather-category-label { flex: 1; font-size: 15px; font-weight: 500; }
.storm-weather-category-row input[type="checkbox"] { width: 20px; height: 20px; accent-color: var(--fp-accent); flex-shrink: 0; }
.storm-weather-category-row--disabled { opacity: 0.45; }
.storm-weather-category-row--disabled .storm-weather-category-icon { filter: grayscale(1); }
.storm-weather-category-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.storm-weather-category-note { font-size: 11px; line-height: 1.35; color: var(--secondary-text-color); }
.storm-solcast-precheck {
  margin-top: 12px; padding: 12px 14px; border-radius: 10px; font-size: 13px; line-height: 1.5;
  border: 1px solid color-mix(in srgb, var(--divider-color) 70%, transparent);
  background: color-mix(in srgb, var(--card-background-color) 92%, var(--primary-text-color) 8%);
}
.storm-solcast-precheck--ok {
  border-color: color-mix(in srgb, var(--fp-green, #4caf50) 45%, transparent);
  background: color-mix(in srgb, var(--fp-green, #4caf50) 10%, var(--card-background-color));
}
.storm-solcast-precheck--warn {
  border-color: color-mix(in srgb, var(--fp-amber) 50%, transparent);
  background: color-mix(in srgb, var(--fp-amber) 10%, var(--card-background-color));
}
.storm-solcast-precheck--neutral {
  border-color: color-mix(in srgb, var(--divider-color) 70%, transparent);
}
.storm-solcast-precheck-title { font-weight: 600; margin: 0 0 6px; font-size: 13px; }
.storm-solcast-precheck-metrics { font-size: 12px; color: var(--secondary-text-color); margin: 8px 0 0; line-height: 1.45; }
.storm-solcast-precheck-detail { font-size: 12px; color: var(--secondary-text-color); margin: 8px 0 0; line-height: 1.45; }
.storm-weather-category-via { font-size: 11px; color: var(--secondary-text-color); opacity: 0.85; }
.storm-weather-category-forecast {
  font-size: 11px; line-height: 1.35; color: var(--secondary-text-color);
}
.storm-weather-category-forecast code {
  font-size: 10px; padding: 1px 4px; border-radius: 4px;
  background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
}
.storm-weather-category-row--active {
  background: color-mix(in srgb, var(--fp-amber) 12%, var(--card-background-color));
  border-radius: 8px;
  margin: 0 -6px;
  padding-left: 6px;
  padding-right: 6px;
}
.storm-weather-category-active-badge {
  display: inline-block;
  margin-top: 2px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fp-amber);
}
.trigger-row.google-weather { background: color-mix(in srgb, var(--fp-accent) 10%, transparent); }
.trigger-role { display: inline-block; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; padding: 2px 6px; border-radius: 6px; margin-left: 6px; background: var(--secondary-background-color); color: var(--fp-accent); }
@container fp-main (min-width: 560px) {
  .overview-hero-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto;
    align-items: stretch;
    gap: 14px;
  }
  .overview-hero-scene,
  .overview-hero-daily-slot {
    display: grid;
    grid-template-rows: subgrid;
    grid-row: span 2;
    gap: 12px;
    min-height: 0;
    height: auto;
    width: 100%;
    max-width: none;
    margin: 0;
  }
  .overview-hero-scene-slot,
  .overview-hero-daily-charts {
    min-height: 0;
  }
  .overview-system-status-slot,
  .overview-automation-status-slot {
    min-width: 0;
  }
  .overview-system-status-card,
  .overview-automation-status-card {
    min-height: 100%;
  }
}
.shell.narrow .overview-hero-row {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.shell.narrow .overview-hero-daily-slot,
.shell.narrow .overview-daily-card {
  width: 100%;
  max-width: none;
}
@media (max-width: 720px) {
  .overview-hero-row {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
  }
  .overview-hero-daily-slot,
  .overview-daily-card {
    width: 100%;
    max-width: none;
  }
  .device-grid { grid-template-columns: 1fr; gap: 12px; }
  .overview-energy-stats-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .overview-balance-panel { grid-template-columns: 1fr; }
  .overview-balance-row + .overview-balance-row {
    border-left: none; border-top: 1px solid var(--divider-color, rgba(127,127,127,0.25));
    padding-left: 0; padding-top: 14px; margin-top: 4px;
  }
  .overview-balance-spark { width: 100%; max-width: none; justify-content: flex-start; }
  .device-card--pv, .device-card--battery { padding: 20px 20px 22px; }
  .device-pv-gauges--dual .device-pv-gauge { max-width: 120px; }
  .device-pv-gauges--dual .device-pv-value { font-size: 14px; }
  .device-pv-gauges--dual .device-pv-readout { padding: 0 6px; }
  .device-pv-gauge { max-width: 160px; }
  .device-pv-value { font-size: 18px; }
  .device-battery-pct { font-size: 32px; }
}
@media (max-width: 600px) {
  .fox-flow-badge-value { font-size: 13px; }
}
`;

function ensureMainInner(mainEl) {
  if (!mainEl) return null;
  let inner = mainEl.querySelector(":scope > .main-inner");
  if (!inner) {
    inner = document.createElement("div");
    inner.className = "main-inner";
    while (mainEl.firstChild) {
      inner.appendChild(mainEl.firstChild);
    }
    mainEl.appendChild(inner);
  }
  return inner;
}

function renderPanelPlaceholderHtml(message) {
  return `<div class="shell"><main class="main"><div class="main-inner"><p class="placeholder">${message}</p></div></main></div>`;
}

class FoxessPlantPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._narrow = false;
    this._panel = undefined;
    this._route = undefined;
    this._view = "overview";
    this._settingsView = "main";
    this._deviceSub = "main";
    this._deviceNewSub = "analysis";
    this._deviceNewScreen = "main";
    this._deviceNewCurveDayOffset = 0;
    this._deviceNewEnergyPeriod = "week";
    this._deviceNewEnergyPeriodOffset = 0;
    this._deviceNewChartsGen = 0;
    this._deviceNewCurveInflight = undefined;
    this._deviceNewEnergyInflight = undefined;
    this._deviceNewStatisticsChart = null;
    this._deviceNewStatisticsChartLoading = false;
    this._deviceNewStatisticsChartPlantId = undefined;
    this._deviceNewEnergyChart = null;
    this._deviceNewEnergyChartLoading = false;
    this._deviceNewEnergyChartPlantId = undefined;
    this._deviceNewAlarmTab = "active";
    this._deviceNewAlarmHistoryRange = "24h";
    this._deviceNewAlarmHistoryStart = "";
    this._deviceNewAlarmHistoryEnd = "";
    this._deviceNewAlarmFilterCategory = "";
    this._deviceNewAlarmFilterSeverity = "";
    this._deviceNewAlarmFilterDevice = "";
    this._deviceNewAlarmFieldFocused = false;
    this._deviceNewAlarmData = null;
    this._deviceNewAlarmLoading = false;
    this._deviceNewAlarmInflight = undefined;
    this._deviceNewAlarmPlantId = undefined;
    this._foxAlarmDetailName = null;
    this._deviceParamOpen = new Set();
    this._smartChargeSectionOpen = null;
    this._plantState = undefined;
    this._selectedPlantId = undefined;
    this._timer = undefined;
    this._busy = false;
    this._toastTimer = undefined;
    this._chargeDraft = null;
    this._socDraft = null;
    this._socSaveError = null;
    this._socSaveResults = null;
    this._workModeDraft = null;
    this._stormDraft = null;
    this._triggerMeta = null;
    this._triggerCandidates = null;
    this._triggerFilter = "";
    this._triggerShowAll = false;
    this._triggerGoogleOnly = false;
    this._stormShowAdvanced = false;
    this._triggerFilterTimer = undefined;
    this._brandIconSrc = DEFAULT_BRAND_ICON_STATIC;
    this._brandIconFallback = DEFAULT_BRAND_ICON_STATIC;
    this._brandIconStatic = DEFAULT_BRAND_ICON_STATIC;
    this._socDrag = null;
    this._rangeDrag = false;
    this._settingsFieldFocused = false;
    this._renderPending = false;
    this._energyPeriod = "day";
    this._energyPeriodOffset = 0;
    this._reportsPeriod = "week";
    this._reportsPeriodOffset = 0;
    this._reportsView = "energy_report";
    this._octopusAnalysisLoading = false;
    this._octopusAnalysisPlantId = undefined;
    this._smartChargeAnalysis = null;
    this._smartChargeAnalysisLoading = false;
    this._smartChargeAnalysisPlantId = undefined;
    this._energyReport = null;
    this._energyReportLoading = false;
    this._energyReportPlantId = undefined;
    this._energyBreakdown = null;
    this._energyChart = null;
    this._energyChartLoading = false;
    this._energyChartPlantId = undefined;
    this._statisticsChart = null;
    this._statisticsChartLoading = false;
    this._statisticsChartPlantId = undefined;
    this._batterySocChart = null;
    this._batterySocChartLoading = false;
    this._batterySocChartPlantId = undefined;
    this._hourlyWeather = null;
    this._hourlyWeatherLoading = false;
    this._hourlyWeatherPlantId = undefined;
    this._overviewDaily = null;
    this._overviewDailyLoading = false;
    this._overviewDailyPlantId = undefined;
    this._overviewDailySlotCache = undefined;
    this._overviewSystemStatus = null;
    this._overviewSystemStatusLoading = false;
    this._overviewSystemStatusPlantId = undefined;
    this._overviewSystemStatusSlotCache = undefined;
    this._overviewAutomationStatusSlotCache = undefined;
    this._overviewSystemStatusInflight = undefined;
    this._overviewHourlyWeatherSlotCache = undefined;
    this._overviewBreakdownSlotCache = undefined;
    this._overviewSummarySlotCache = undefined;
    this._overviewEnergyBandCache = undefined;
    this._analysisTariffDaily = null;
    this._analysisPeriodTariff = null;
    this._analysisTariffSlotCache = undefined;
    this._analysisSummarySpark = null;
    this._analysisSummarySparkLoading = false;
    this._analysisSummarySparkKey = undefined;
    this._forecastAccuracyOverview = null;
    this._forecastAccuracyOverviewLoading = false;
    this._forecastAccuracyOverviewKey = undefined;
    this._forecastAccuracyAnalysis = null;
    this._forecastAccuracyAnalysisLoading = false;
    this._forecastAccuracyAnalysisKey = undefined;
    this._forecastAccuracyAnalysisSlotCache = undefined;
    this._forecastAccuracyAnalysisCache = new Map();
    this._forecastAccuracyLoadGen = 0;
    this._forecastAccuracyAnalysisInflightKey = undefined;
    this._octopusGreenerView = "standard";
    this._octopusGreenerAnalysisSlotCache = undefined;
    this._octopusUpcomingWeekAnalysisSlotCache = undefined;
    this._energyAnalysisSummaryCache = undefined;
    this._energyAnalysisChartSlotCache = undefined;
    this._statisticsForecastSlotTrack = undefined;
    this._energyAnalysisToolbarCache = undefined;
    this._energyBalanceHelpOpen = false;
    this._panelSyncBusy = false;
    this._panelRecoverBusy = false;
    this._panelStale = false;
    this._flowSceneKey = undefined;
    this._flowScenePlantId = undefined;
    this._flowSceneKeyPending = undefined;
    this._flowSceneKeyPendingN = 0;
    this._pvDraft = null;
    this._solcastDraft = null;
    this._tariffDraft = null;
    this._octopusDraft = null;
    this._octopusPickerMountGen = 0;
    this._smartChargeDraft = null;
    this._tariffPickerMountGen = 0;
    this._headerHasSubTabs = undefined;
    this._headerSubNavView = undefined;
    this._renderRaf = 0;
    this._onSocMove = this._onSocMove.bind(this);
    this._onSocEnd = this._onSocEnd.bind(this);
    const root = document.createElement("div");
    root.className = "root";
    this.shadowRoot.append(
      Object.assign(document.createElement("style"), { textContent: STYLES }),
      root
    );
    this._root = root;
    this._onClick = this._handleClick.bind(this);
    this._onInput = this._handleInput.bind(this);
    this._onChange = this._handleChange.bind(this);
    this._onPointerDown = this._onPointerDown.bind(this);
    this._onPointerUp = this._onPointerUp.bind(this);
    this._onFocusIn = this._onFocusIn.bind(this);
    this._onFocusOut = this._onFocusOut.bind(this);
    this._onPaste = this._onPaste.bind(this);
    this._onOctopusGreenerHoverMove = this._handleOctopusGreenerHoverMove.bind(this);
    this._onOctopusGreenerHoverEnd = this._handleOctopusGreenerHoverEnd.bind(this);
    this._octopusGreenerHoverPlot = null;
  }

  connectedCallback() {
    this._root.addEventListener("click", this._onClick);
    this._root.addEventListener("input", this._onInput);
    this._root.addEventListener("change", this._onChange);
    this._root.addEventListener("pointerdown", this._onPointerDown);
    this._root.addEventListener("pointerup", this._onPointerUp);
    this._root.addEventListener("pointercancel", this._onPointerUp);
    this._root.addEventListener("focusin", this._onFocusIn, true);
    this._root.addEventListener("focusout", this._onFocusOut, true);
    this._root.addEventListener("paste", this._onPaste, true);
    this._root.addEventListener("mousemove", this._onOctopusGreenerHoverMove);
    this._root.addEventListener("mouseleave", this._onOctopusGreenerHoverEnd);
    void this._initBrandIcons();
    void this._refreshPlantState();
    this._timer = window.setInterval(() => void this._refreshPlantState(), 30000);
    this._render();
  }

  disconnectedCallback() {
    this._root.removeEventListener("click", this._onClick);
    this._root.removeEventListener("input", this._onInput);
    this._root.removeEventListener("change", this._onChange);
    this._root.removeEventListener("pointerdown", this._onPointerDown);
    this._root.removeEventListener("pointerup", this._onPointerUp);
    this._root.removeEventListener("pointercancel", this._onPointerUp);
    this._root.removeEventListener("focusin", this._onFocusIn, true);
    this._root.removeEventListener("focusout", this._onFocusOut, true);
    this._root.removeEventListener("paste", this._onPaste, true);
    this._root.removeEventListener("mousemove", this._onOctopusGreenerHoverMove);
    this._root.removeEventListener("mouseleave", this._onOctopusGreenerHoverEnd);
    if (this._triggerFilterTimer) window.clearTimeout(this._triggerFilterTimer);
    this._endSocDrag();
    if (this._timer) window.clearInterval(this._timer);
    if (this._toastTimer) window.clearTimeout(this._toastTimer);
  }

  set hass(v) {
    this._hass = v;
    if (v) void this._initBrandIcons();
    if (!this._socDrag) this._scheduleRender();
  }
  get hass() {
    return this._hass;
  }
  set narrow(v) {
    this._narrow = Boolean(v);
    this.classList.toggle("narrow", this._narrow);
    this._syncShellLayoutClasses(this._root.querySelector(".shell"));
  }
  get narrow() {
    return this._narrow;
  }
  set panel(v) {
    this._panel = v;
    const plants = v?.config?.plants ?? [];
    if (!this._selectedPlantId && plants.length) this._selectedPlantId = plants[0].entry_id;
    void this._refreshPlantState();
    this._scheduleRender();
  }
  get panel() {
    return this._panel;
  }
  set route(v) {
    this._route = v;
  }
  get route() {
    return this._route;
  }

  _getPlant() {
    const plants = this._panel?.config?.plants ?? [];
    return plants.find((p) => p.entry_id === this._selectedPlantId) ?? plants[0];
  }

  _clearOctopusGreenerHover() {
    if (this._octopusGreenerHoverPlot) {
      hideOctopusGreenerChartHover(this._octopusGreenerHoverPlot);
      this._octopusGreenerHoverPlot = null;
    }
    this._root?.querySelectorAll("[data-octopus-greener-plot]").forEach((plot) => {
      hideOctopusGreenerChartHover(plot);
    });
  }

  _octopusGreenerPlotFromEvent(ev) {
    const plot = ev.target?.closest?.("[data-octopus-greener-plot]");
    return plot && this._root.contains(plot) ? plot : null;
  }

  _handleOctopusGreenerHoverMove(ev) {
    const plot = this._octopusGreenerPlotFromEvent(ev);
    if (!plot) {
      this._clearOctopusGreenerHover();
      return;
    }
    if (this._octopusGreenerHoverPlot !== plot) {
      if (this._octopusGreenerHoverPlot) {
        hideOctopusGreenerChartHover(this._octopusGreenerHoverPlot);
      }
      this._octopusGreenerHoverPlot = plot;
    }
    updateOctopusGreenerChartHover(plot, ev.clientX);
  }

  _handleOctopusGreenerHoverEnd() {
    this._clearOctopusGreenerHover();
  }

  _panelBuild() {
    const jsVer = panelVersionFromModuleUrl() || PANEL_VERSION;
    const regBuild = this._panel?.config?.panel_js_build || "—";
    const regVer = String(regBuild).split("-")[0] || "—";
    const diskVer = this._plantState?.panel_runtime?.manifest_version || "—";
    return `js ${jsVer} · registered ${regVer} · disk ${diskVer}`;
  }

  _syncPanelBuildFooter(shell) {
    if (!shell) return;
    let el = shell.querySelector(".panel-build-footer");
    if (this._view !== "settings") {
      if (el) el.remove();
      return;
    }
    if (!el) {
      el = document.createElement("p");
      el.className = "panel-build-footer";
      el.setAttribute("aria-hidden", "true");
      shell.appendChild(el);
    }
    el.textContent = `Panel build ${this._panelBuild()}`;
  }

  _panelIsStale() {
    const runtime = this._plantState?.panel_runtime;
    if (!runtime?.js_build) return false;
    const jsVer = panelVersionFromModuleUrl() || PANEL_VERSION;
    const regBuild = this._panel?.config?.panel_js_build;
    const diskVer = runtime.manifest_version;
    const staleReg = Boolean(regBuild && runtime.js_build && regBuild !== runtime.js_build);
    const staleJs = Boolean(diskVer && jsVer && diskVer !== jsVer);
    return staleReg || staleJs;
  }

  _renderPanelStaleBanner() {
    if (!this._panelStale) return "";
    const runtime = this._plantState?.panel_runtime ?? {};
    const jsVer = panelVersionFromModuleUrl() || PANEL_VERSION;
    const regVer = String(this._panel?.config?.panel_js_build || "—").split("-")[0];
    return `<div class="banner warn panel-stale-banner" role="status">
<strong>Panel update pending</strong>
Browser ${esc(jsVer)} · HA registered ${esc(regVer)} · files on disk ${esc(runtime.manifest_version || "—")}.
Reloading panel registration…
</div>`;
  }

  async _recoverEmptyPanelConfig() {
    if (this._panelRecoverBusy || !this._hass) return;
    const configured = this._panel?.config?.plants ?? [];
    if (configured.length) return;
    this._panelRecoverBusy = true;
    try {
      const plants = await fetchPlantList(this._hass);
      if (!plants.length) return;
      this._root.innerHTML = `<div class="main"><p class="placeholder">FoxESS Plant found — reloading panel registration…</p></div>`;
      await this._hass.callService("foxess_plant", "reload_panel", {}, undefined, true, true);
      window.setTimeout(() => window.location.reload(), 400);
    } catch (err) {
      console.warn("FoxESS Plant: panel recovery failed", err);
    } finally {
      this._panelRecoverBusy = false;
    }
  }

  async _syncPanelIfStale() {
    if (this._panelSyncBusy || !this._hass) return;
    const runtime = this._plantState?.panel_runtime;
    if (!runtime?.js_build) return;
    this._panelStale = this._panelIsStale();
    if (!this._panelStale) return;
    const attempted = sessionStorage.getItem(PANEL_SYNC_STORAGE_KEY);
    if (attempted === runtime.js_build) return;
    this._panelSyncBusy = true;
    sessionStorage.setItem(PANEL_SYNC_STORAGE_KEY, runtime.js_build);
    this._scheduleRender();
    try {
      await this._hass.callService("foxess_plant", "reload_panel", {}, undefined, true, true);
    } catch (err) {
      console.warn("FoxESS Plant: reload_panel failed (restart HA if panel stays stale)", err);
    }
    window.setTimeout(() => window.location.reload(), 400);
  }

  async _initBrandIcons() {
    const cfg = this._panel?.config ?? {};
    this._brandIconStatic = cfg.brand_icon_static || DEFAULT_BRAND_ICON_STATIC;
    const plantDomain = cfg.brand_domain || DEFAULT_BRAND_DOMAIN;
    const modbusDomain = cfg.modbus_brand_domain || DEFAULT_MODBUS_BRAND_DOMAIN;
    if (!this._hass) {
      this._brandIconSrc = this._brandIconStatic;
      this._brandIconFallback = this._brandIconStatic;
      return;
    }
    await ensureBrandsAccessToken(this._hass);
    this._brandIconSrc = buildBrandIconUrl(plantDomain);
    this._brandIconFallback = buildBrandIconUrl(modbusDomain);
    if (this.isConnected) this._scheduleRender();
  }

  _renderPanelBrand() {
    const menuLabel =
      this._hass?.localize?.("ui.sidebar.sidebar_toggle") || "Open menu";
    return `<div class="panel-header-top">
<button type="button" class="panel-ha-menu-btn" data-action="ha-menu-toggle" aria-label="${esc(menuLabel)}">${HA_MENU_ICON_SVG}</button>
<div class="panel-brand-row">
<img class="panel-brand-icon" src="${esc(this._brandIconSrc)}" data-fallback="${esc(this._brandIconFallback)}" data-static="${esc(this._brandIconStatic)}" width="40" height="40" alt="FoxESS">
<div>
<div class="panel-brand-title">Fox Plant</div>
<div class="panel-brand-sub">FoxESS inverter control</div>
</div>
</div>
</div>`;
  }

  _toggleHaSidebar() {
    this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
  }

  _bindPanelBrandIcon(headerEl) {
    const img = headerEl?.querySelector(".panel-brand-icon");
    if (!img || img.dataset.bound) return;
    img.dataset.bound = "1";
    img.addEventListener("error", () => {
      const fallback = img.dataset.fallback;
      const staticSrc = img.dataset.static;
      if (fallback && img.src !== fallback) {
        img.src = fallback;
      } else if (staticSrc) {
        img.src = staticSrc;
      }
    });
  }

  _showToast(msg, type = "ok") {
    const old = this.shadowRoot.querySelector(".toast");
    if (old) old.remove();
    if (this._toastTimer) window.clearTimeout(this._toastTimer);
    const el = document.createElement("div");
    el.className = `toast ${type === "err" ? "err" : "ok"}`;
    el.textContent = msg;
    this.shadowRoot.appendChild(el);
    this._toastTimer = window.setTimeout(() => el.remove(), 3500);
  }

  async _refreshPlantState() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    try {
      this._plantState = await fetchPlantState(this._hass, plant.entry_id);
      if (this._settingsView !== "schedules") this._chargeDraft = null;
      if (this._settingsView !== "quick") this._socDraft = null;
      if (this._settingsView !== "workmode") this._workModeDraft = null;
      if (this._settingsView !== "storm") this._stormDraft = null;
      if (this._settingsView !== "tariff") this._tariffDraft = null;
      if (this._settingsView !== "smart") this._smartChargeDraft = null;
      if (this._settingsView !== "glow") this._glowDraft = null;
      if (
        this._settingsView === "solcast" &&
        this._solcastDraft &&
        !this._settingsFieldFocused &&
        !this._rangeDrag
      ) {
        const sc = this._plantState?.solcast ?? {};
        this._solcastDraft.enabled = solcastEnabledFromLive(sc);
        this._solcastDraft.fetch_pv_forecast = sc.fetch_pv_forecast !== false;
        this._solcastDraft.api_key_set = Boolean(sc.api_key_set);
      }
      if (
        this._settingsView === "tariff" &&
        this._octopusDraft &&
        !this._settingsFieldFocused &&
        !this._rangeDrag
      ) {
        const dyn = this._plantState?.tariff?.dynamic ?? {};
        const prevKey = this._octopusDraft.api_key || "";
        this._octopusDraft.api_key_set = Boolean(dyn.api_key_set);
        if (prevKey) this._octopusDraft.api_key = prevKey;
      }
      this._panelStale = this._panelIsStale();
      const forecastPart = this._forecastStatisticsSlotPart?.();
      if (forecastPart !== this._statisticsForecastSlotTrack) {
        this._statisticsForecastSlotTrack = forecastPart;
        this._energyAnalysisChartSlotCache = undefined;
        void this._refreshStatisticsServerForecast();
        this._forecastAccuracyOverviewKey = undefined;
        this._forecastAccuracyAnalysisKey = undefined;
        if (this._view === "overview") void this._loadForecastAccuracyOverview();
        if (this._view === "energy_analysis" && this._energyPeriod === "day") {
          this._beginForecastAccuracyAnalysisLoad();
        }
      }
      if (!this._socDrag) this._scheduleRender();
      void this._syncPanelIfStale();
    } catch {
      /* ws optional */
    }
  }

  _deviceNewAlarmBlocksRender() {
    if (this._view !== "device_new" || this._deviceNewSub !== "alarms") return false;
    if (this._deviceNewAlarmFieldFocused) return true;
    const el = this.shadowRoot?.activeElement || document.activeElement;
    if (!el || !this._root.contains(el)) return false;
    return el.matches?.(".fox-alarm-hist-date, .fox-alarm-hist-select");
  }

  _deviceNewAlarmUiContext() {
    const def = defaultAlarmCustomRangeValues();
    return {
      tab: this._deviceNewAlarmTab || "active",
      filters: {
        category: this._deviceNewAlarmFilterCategory || "",
        severity: this._deviceNewAlarmFilterSeverity || "",
        device: this._deviceNewAlarmFilterDevice || "",
      },
      timeRange: {
        mode: this._deviceNewAlarmHistoryRange || "24h",
        start: this._deviceNewAlarmHistoryStart || def.start,
        end: this._deviceNewAlarmHistoryEnd || def.end,
      },
    };
  }

  _patchDeviceNewAlarmHistBody() {
    const body = this._root?.querySelector?.("[data-fox-alarm-hist-body]");
    if (!body || !this._deviceNewAlarmData || this._deviceNewAlarmData.error) return false;
    const ctx = this._deviceNewAlarmUiContext();
    if (ctx.tab !== "historical") return false;
    body.innerHTML = renderFoxAlarmHistoricalTableRows(
      filterHistoricalAlarmRecords(this._deviceNewAlarmData.historicalRecords || [], ctx.filters, ctx.timeRange)
    );
    return true;
  }

  _patchDeviceNewAlarmListDynamic() {
    const slot = this._root?.querySelector?.("[data-fox-alarm-list-dynamic]");
    if (!slot || !this._deviceNewAlarmData || this._deviceNewAlarmData.error) return false;
    slot.innerHTML = renderFoxAlarmHistListContent(this._deviceNewAlarmData, this._deviceNewAlarmUiContext());
    return true;
  }

  _patchDeviceNewAlarmTabUi() {
    const card = this._root?.querySelector?.("[data-fox-alarm-list-card]");
    if (!card) return false;
    const tab = this._deviceNewAlarmTab || "active";
    card.querySelectorAll(".fox-alarm-tab").forEach((btn) => {
      const on = btn.dataset.tab === tab;
      btn.classList.toggle("active", on);
    });
    return this._patchDeviceNewAlarmListDynamic();
  }

  _patchDeviceNewAlarmsLiveIfNeeded() {
    if (this._view !== "device_new" || this._deviceNewSub !== "alarms") return false;
    if (this._deviceNewAlarmLoading) return false;
    const root = this._root?.querySelector?.("[data-device-new-main]");
    const plant = this._getPlant();
    if (root && plant && this._hass) {
      const summary = repairDeviceNewSummaryElement(root.querySelector("[data-device-new-summary]"));
      if (summary) {
        summary.innerHTML = renderDeviceNewSummaryCardItems(this._hass, plant, this._plantState);
      }
    }
    return true;
  }

  _settingsFieldBlocksRender() {
    if (this._view !== "settings") return false;
    if (this._settingsFieldFocused) return true;
    const el = this.shadowRoot?.activeElement || document.activeElement;
    if (!el || !this._root.contains(el)) return false;
    if (el.tagName === "HA-ENTITY-PICKER" || el.closest?.("ha-entity-picker")) return true;
    const tag = el.tagName;
    if (tag === "SELECT" || tag === "TEXTAREA") return true;
    if (tag !== "INPUT") return false;
    const type = (el.type || "text").toLowerCase();
    return ["range", "date", "number", "text", "password"].includes(type);
  }

  _onFocusIn(e) {
    if (!this._root.contains(e.target)) return;
    if (this._view === "settings") {
      if (
        e.target.matches?.("input, select, textarea, ha-entity-picker") ||
        e.target.closest?.("ha-entity-picker")
      ) {
        this._settingsFieldFocused = true;
      }
      return;
    }
    if (this._view === "device_new" && this._deviceNewSub === "alarms") {
      if (e.target.matches?.(".fox-alarm-hist-date, .fox-alarm-hist-select")) {
        this._deviceNewAlarmFieldFocused = true;
      }
    }
  }

  _onFocusOut() {
    if (this._view === "device_new" && this._deviceNewSub === "alarms") {
      window.requestAnimationFrame(() => {
        const active = this.shadowRoot?.activeElement || document.activeElement;
        if (active && this._root.contains(active) && active.matches?.(".fox-alarm-hist-date, .fox-alarm-hist-select")) {
          return;
        }
        this._deviceNewAlarmFieldFocused = false;
        if (this._renderPending) {
          this._renderPending = false;
          this._scheduleRender();
        }
      });
      return;
    }
    if (this._view !== "settings") {
      if (this._settingsFieldFocused) {
        this._settingsFieldFocused = false;
        if (this._renderPending) {
          this._renderPending = false;
          this._scheduleRender();
        }
      }
      return;
    }
    window.requestAnimationFrame(() => {
      const active = this.shadowRoot?.activeElement || document.activeElement;
      if (
        active &&
        this._root.contains(active) &&
        (active.matches?.("input, select, textarea, ha-entity-picker") || active.closest?.("ha-entity-picker"))
      ) {
        return;
      }
      this._settingsFieldFocused = false;
      if (this._renderPending) {
        this._renderPending = false;
        this._scheduleRender();
      }
    });
  }

  _onPaste(e) {
    const el = e.target;
    if (!el?.dataset?.field || this._busy) return;
    const parts = el.dataset.field.split(":");
    const text = e.clipboardData?.getData("text/plain") ?? "";
    if (!text) return;
    if (parts[0] === "solcast" && parts[1] === "api_key" && this._solcastDraft) {
      this._solcastDraft.api_key = text;
      return;
    }
    if (parts[0] === "octopus" && parts[1] === "api_key" && this._octopusDraft) {
      this._octopusDraft.api_key = text;
    }
  }

  _onPointerDown(e) {
    const t = e.target;
    if (t?.matches?.('input[type="range"][data-field^="pv:"]')) this._rangeDrag = true;
  }

  _onPointerUp() {
    this._rangeDrag = false;
  }

  _updatePvRangeLabel(el) {
    const row = el?.closest?.(".pv-range-row");
    if (!row) return;
    const label = row.querySelector(".pv-range-value");
    if (!label) return;
    const field = el.dataset?.field || "";
    if (field.endsWith(":tilt")) label.textContent = `${el.value}°`;
    else if (field.endsWith(":azimuth")) label.textContent = `${el.value}°`;
    else if (field.endsWith(":panel_count")) label.textContent = String(el.value);
    else if (field.endsWith(":watts_per_panel")) label.textContent = `${el.value} W`;
  }

  _statisticsChartVisible() {
    return (
      this._view === "overview" ||
      ((this._view === "energy_analysis") && this._energyPeriod === "day")
    );
  }

  _pickStatisticsForecastState() {
    const live = this._plantState;
    const cached = this._statisticsChart?.forecastState;
    const detailed = resolveBestSolcastDetailedRows(live, cached, this._hass);
    const liveIntraday = live?.solcast?.forecast_intraday_points;
    const cachedIntraday = cached?.solcast?.forecast_intraday_points;
    const intraday =
      Array.isArray(liveIntraday) && liveIntraday.length >= 2
        ? liveIntraday
        : Array.isArray(cachedIntraday) && cachedIntraday.length >= 2
          ? cachedIntraday
          : null;
    const base = live ?? cached;
    if (!base?.solcast) return base;
    if (!intraday && detailed.length < 2) {
      const liveRows = resolveSolcastDetailedForecast(live, this._hass);
      if (liveRows.length >= 2) return live;
      const cachedRows = resolveSolcastDetailedForecast(cached, this._hass);
      if (cachedRows.length >= 2) return cached;
      return base;
    }
    return {
      ...base,
      solcast: {
        ...(cached?.solcast || {}),
        ...(live?.solcast || {}),
        ...(detailed.length >= 2 ? { detailed_forecast: detailed } : {}),
        ...(intraday ? { forecast_intraday_points: intraday } : {}),
      },
    };
  }

  _forecastFallbackPointsForStatistics(range) {
    if (!range || (this._statisticsChart?.dayOffset ?? 0) > 0) return null;
    const reports = [this._forecastAccuracyOverview, this._forecastAccuracyAnalysis];
    for (const report of reports) {
      if (!report || report.error) continue;
      const pts = report.intraday?.predicted_power_kw;
      if (!Array.isArray(pts) || pts.length < 2) continue;
      const inRange = pts
        .filter(
          (p) =>
            Number.isFinite(p?.t) &&
            Number.isFinite(p?.v) &&
            p.t >= range.tMin &&
            p.t <= range.tMax
        )
        .sort((a, b) => a.t - b.t);
      if (inRange.length >= 2) return inRange;
    }
    return null;
  }

  _forecastStatisticsSlotPart() {
    const state = this._pickStatisticsForecastState();
    const intraday = state?.solcast?.forecast_intraday_points?.length ?? 0;
    const detailed = resolveSolcastDetailedForecast(state, this._hass)?.length ?? 0;
    const accOverview = this._forecastAccuracyOverview?.intraday?.predicted_power_kw?.length ?? 0;
    const accAnalysis = this._forecastAccuracyAnalysis?.intraday?.predicted_power_kw?.length ?? 0;
    return `${intraday}:${detailed}:${accOverview}:${accAnalysis}`;
  }

  async _refreshStatisticsServerForecast() {
    const plant = this._getPlant();
    if (!plant || !this._hass || !this._statisticsChart || (this._statisticsChart.dayOffset ?? 0) > 0) return;
    try {
      const points = await fetchSolcastStatisticsForecastPoints(this._hass, plant);
      if (points.length >= 2 && this._statisticsChart) {
        this._statisticsChart.serverForecastPoints = points;
        this._energyAnalysisChartSlotCache = undefined;
        this._scheduleRender();
      }
    } catch {
      /* server overlay optional */
    }
  }

  _statisticsSeriesForDisplay() {
    const chart = this._statisticsChart;
    if (!chart?.series || !chart?.range) return null;
    const state = this._pickStatisticsForecastState();
    const dayOffset = chart?.dayOffset ?? 0;
    const range = statisticsRangeForDisplay(chart?.range, dayOffset);
    if (!range) return null;
    return mergeStatisticsForecastSeries(
      chart.series,
      range,
      state,
      this._hass,
      {
        dayOffset,
        fallbackPoints: this._forecastFallbackPointsForStatistics(range),
        forecastState: chart.forecastState,
        serverForecastPoints: chart.serverForecastPoints,
      }
    );
  }

  _statisticsChartNeedsReload(plant) {
    if (this._view !== "energy_analysis" || this._energyPeriod !== "day" || !plant) return false;
    const cacheKey = this._energyChartCacheKey(plant);
    if (this._statisticsChartPlantId !== cacheKey) return true;
    if ((this._statisticsChart?.dayOffset ?? 0) !== this._energyPeriodOffset) return true;
    return !this._statisticsChart?.range;
  }

  _ensureStatisticsChartLoaded() {
    if (!this._statisticsChartVisible()) return;
    const plant = this._getPlant();
    if (!plant || this._statisticsChartLoading) return;
    if (this._view === "overview") {
      const cacheKey = `${plant.entry_id}:overview`;
      if (this._statisticsChartPlantId !== cacheKey || !this._statisticsChart?.range) {
        void this._loadOverviewStatisticsChart();
      }
      return;
    }
    if (this._statisticsChartNeedsReload(plant)) {
      void this._loadStatisticsChart();
    }
  }

  _reloadStatisticsChartWhenVisible() {
    if (!this._statisticsChartVisible()) return;
    this._statisticsChart = null;
    this._statisticsChartPlantId = undefined;
    if (this._view === "overview") void this._loadOverviewStatisticsChart();
    else void this._loadStatisticsChart();
  }

  _syncShellLayoutClasses(shell) {
    if (!shell) return;
    const hasSubnav = this._view === "settings" || this._view === "device_new";
    shell.classList.toggle("narrow", this._narrow);
    shell.classList.toggle("view-device-new", this._view === "device_new");
    shell.classList.toggle("has-subnav", hasSubnav);
  }

  _scheduleRender(force = false) {
    if (
      !force &&
      !this._socDrag &&
      !this._rangeDrag &&
      !this._settingsFieldBlocksRender() &&
      !this._deviceNewAlarmBlocksRender() &&
      (this._patchDeviceMainLiveIfNeeded() ||
        this._patchDeviceNewLiveIfNeeded() ||
        this._patchDeviceNewAlarmsLiveIfNeeded() ||
        this._patchSettingsMainLiveIfNeeded() ||
        this._patchGlowSettingsLiveIfNeeded() ||
        this._patchSettingsSmartChargeLiveIfNeeded() ||
        this._patchEnergyAnalysisMainIfNeeded())
    ) {
      this._renderPending = false;
      return;
    }
    if (!force && (this._socDrag || this._rangeDrag || this._settingsFieldBlocksRender() || this._deviceNewAlarmBlocksRender())) {
      this._renderPending = true;
      return;
    }
    this._renderPending = false;
    if (this._renderRaf) return;
    this._renderRaf = requestAnimationFrame(() => {
      this._renderRaf = 0;
      this._render();
    });
  }

  _syncTabActive(headerEl) {
    headerEl.querySelectorAll('[data-action="nav"]').forEach((btn) => {
      const on = btn.dataset.view === this._view;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
    headerEl.querySelectorAll('[data-action="settings-tab"]').forEach((btn) => {
      const on = btn.dataset.sub === this._settingsView;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
    headerEl.querySelectorAll('[data-action="device-new-tab"]').forEach((btn) => {
      const on = btn.dataset.sub === this._deviceNewSub;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
    headerEl.querySelectorAll('[data-action="reports-tab"]').forEach((btn) => {
      const on = btn.dataset.sub === this._reportsView;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
  }

  _renderPlantSelect() {
    const plants = this._panel?.config?.plants ?? [];
    if (plants.length <= 1) return "";
    const selectedId = this._selectedPlantId ?? plants[0]?.entry_id;
    return `<div class="plant-row"><label>Plant</label><select data-action="pick-plant" aria-label="Plant selector">${plants
      .map(
        (p) =>
          `<option value="${esc(p.entry_id)}" ${p.entry_id === selectedId ? "selected" : ""}>${esc(
            p.title
          )}</option>`
      )
      .join("")}</select></div>`;
  }

  _ensureReportsViewValid() {
    if (this._reportsView === "smart_charge" && !smartChargeEnabled(this._plantState)) {
      this._reportsView = "energy_report";
    }
    const nav = reportsNavForState(this._plantState);
    if (!nav.some((item) => item.id === this._reportsView)) {
      this._reportsView = "energy_report";
    }
  }

  _loadActiveReport() {
    this._ensureReportsViewValid();
    if (this._reportsView === "octopus") void this._loadOctopusAnalysis();
    else if (this._reportsView === "smart_charge") void this._loadSmartChargeAnalysis();
    else this._loadEnergyReport();
  }

  _rebuildPageHeader(headerEl) {
    this._ensureReportsViewValid();
    const showSubTabs = this._view === "settings" || this._view === "device_new" || this._view === "reports";
    const subNav =
      this._view === "settings"
        ? SETTINGS_NAV
        : this._view === "device_new"
          ? DEVICE_NEW_NAV
          : reportsNavForState(this._plantState);
    const subActive =
      this._view === "settings"
        ? this._settingsView
        : this._view === "device_new"
          ? this._deviceNewSub
          : this._reportsView;
    const subAction =
      this._view === "settings"
        ? "settings-tab"
        : this._view === "device_new"
          ? "device-new-tab"
          : "reports-tab";
    headerEl.innerHTML =
      this._renderPanelBrand() +
      this._renderPlantSelect() +
      this._renderTabBar(NAV, this._view, "nav", "view") +
      (showSubTabs
        ? this._renderTabBar(subNav, subActive, subAction, "sub", true)
        : "");
    this._bindPanelBrandIcon(headerEl);
    this._headerHasSubTabs = showSubTabs;
  }

  _initChargeDraft() {
    const src =
      this._plantState?.baseline_periods ??
      this._plantState?.desired_periods ??
      DEFAULT_PERIODS;
    this._chargeDraft = JSON.parse(JSON.stringify(src)).slice(0, 2);
    while (this._chargeDraft.length < 2) {
      this._chargeDraft.push({ ...DEFAULT_PERIODS[0] });
    }
  }

  _initSocDraft() {
    const s = this._plantState?.settings ?? {};
    this._socDraft = clampSocDraft({
      min_soc: s.min_soc ?? 10,
      min_soc_on_grid: s.min_soc_on_grid ?? 20,
      max_soc: s.max_soc ?? 100,
    });
  }

  _initWorkModeDraft() {
    this._workModeDraft =
      this._plantState?.settings?.work_mode ??
      stateString(this._hass, this._getPlant()?.entity_map?.work_mode);
  }

  _initSmartChargeDraft() {
    const sc = this._plantState?.smart_charge ?? {};
    const periods = JSON.parse(JSON.stringify(sc.charge_periods ?? DEFAULT_PERIODS)).slice(0, 2);
    while (periods.length < 2) periods.push({ ...DEFAULT_PERIODS[0] });
    this._smartChargeDraft = {
      enabled: Boolean(sc.enabled),
      target_soc: sc.target_soc ?? 100,
      target_max_soc: sc.target_max_soc ?? null,
      max_target_soc: sc.max_target_soc ?? sc.target_soc ?? 100,
      min_deficit_kwh: sc.min_deficit_kwh ?? 0.5,
      solar_safety_margin: sc.solar_safety_margin ?? 1.15,
      round_trip_efficiency: sc.round_trip_efficiency ?? 0.9,
      min_arbitrage_p_per_kwh: sc.min_arbitrage_p_per_kwh ?? 0.5,
      operating_mode: sc.operating_mode ?? "max_safety",
      agile_poll_interval_minutes: sc.agile_poll_interval_minutes ?? 15,
      negative_import_interrupt: sc.negative_import_interrupt !== false,
      price_drop_interrupt_p_per_kwh: sc.price_drop_interrupt_p_per_kwh ?? 2,
      daily_plan_time: sc.daily_plan_time ?? "16:00",
      daily_plan_horizon_hours: sc.daily_plan_horizon_hours ?? 24,
      house_load_kw_fallback: sc.house_load_kw_fallback ?? 1,
      dark_hours_estimate: sc.dark_hours_estimate ?? 8,
      outage_reserve_load_kw: sc.outage_reserve_load_kw ?? null,
      outage_reserve_hours: sc.outage_reserve_hours ?? 3,
      outage_reserve_margin: sc.outage_reserve_margin ?? 1.2,
      safety_reserve_multiplier: sc.safety_reserve_multiplier ?? 1.5,
      green_carbon_weight: sc.green_carbon_weight ?? 0.5,
      export_enabled: sc.export_enabled !== false,
      export_enabled_safety: sc.export_enabled_safety !== false,
      export_enabled_green: Boolean(sc.export_enabled_green),
      min_export_kwh: sc.min_export_kwh ?? 0.5,
      min_export_p_profit: sc.min_export_p_profit ?? 12,
      min_export_p_safety: sc.min_export_p_safety ?? 20,
      min_export_p_green: sc.min_export_p_green ?? 25,
      exportable_fraction_profit: sc.exportable_fraction_profit ?? 1,
      exportable_fraction_safety: sc.exportable_fraction_safety ?? 0.35,
      exportable_fraction_green: sc.exportable_fraction_green ?? 0.15,
      spread_optimizer_enabled: sc.spread_optimizer_enabled !== false,
      min_spread_profit_p_per_kwh: sc.min_spread_profit_p_per_kwh ?? 3,
      peak_import_avoid_start: sc.peak_import_avoid_start ?? "16:00",
      peak_import_avoid_end: sc.peak_import_avoid_end ?? "19:00",
      winter_fill_enabled: sc.winter_fill_enabled !== false,
      green_export_spread_multiplier: sc.green_export_spread_multiplier ?? 2,
      cheap_import_p_per_kwh: sc.cheap_import_p_per_kwh ?? 8,
      peak_import_penalty_p_per_kwh: sc.peak_import_penalty_p_per_kwh ?? 5,
      charge_periods: periods,
    };
  }

  _enterSmartChargeSettings() {
    this._initSmartChargeDraft();
  }

  async _saveSmartChargeSettings() {
    const plant = this._getPlant();
    if (!plant || !this._smartChargeDraft) return;
    this._busy = true;
    this._render();
    try {
      const d = this._smartChargeDraft;
      const target = d.target_max_soc;
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_smart_charge",
        plant_id: plant.entry_id,
        enabled: Boolean(d.enabled),
        target_soc: Number(d.target_soc) || 100,
        target_max_soc: target == null || target === "" ? null : Number(target),
        max_target_soc: Number(d.max_target_soc) || 100,
        min_deficit_kwh: Number(d.min_deficit_kwh) || 0.5,
        solar_safety_margin: Number(d.solar_safety_margin) || 1.15,
        round_trip_efficiency: Number(d.round_trip_efficiency) || 0.9,
        min_arbitrage_p_per_kwh: Number(d.min_arbitrage_p_per_kwh) || 0.5,
        operating_mode: d.operating_mode || "max_safety",
        agile_poll_interval_minutes: Number(d.agile_poll_interval_minutes) || 15,
        negative_import_interrupt: Boolean(d.negative_import_interrupt),
        price_drop_interrupt_p_per_kwh: Number(d.price_drop_interrupt_p_per_kwh) || 2,
        daily_plan_time: String(d.daily_plan_time || "16:00"),
        daily_plan_horizon_hours: Number(d.daily_plan_horizon_hours) || 24,
        house_load_kw_fallback: Number(d.house_load_kw_fallback) || 1,
        dark_hours_estimate: Number(d.dark_hours_estimate) || 8,
        outage_reserve_load_kw:
          d.outage_reserve_load_kw == null || d.outage_reserve_load_kw === ""
            ? null
            : Number(d.outage_reserve_load_kw),
        outage_reserve_hours: Number(d.outage_reserve_hours) || 3,
        outage_reserve_margin: Number(d.outage_reserve_margin) || 1.2,
        safety_reserve_multiplier: Number(d.safety_reserve_multiplier) || 1.5,
        green_carbon_weight: Number(d.green_carbon_weight) || 0.5,
        export_enabled: Boolean(d.export_enabled),
        export_enabled_safety: Boolean(d.export_enabled_safety),
        export_enabled_green: Boolean(d.export_enabled_green),
        min_export_kwh: Number(d.min_export_kwh) || 0.5,
        min_export_p_profit: Number(d.min_export_p_profit) || 12,
        min_export_p_safety: Number(d.min_export_p_safety) || 20,
        min_export_p_green: Number(d.min_export_p_green) || 25,
        exportable_fraction_profit: Number(d.exportable_fraction_profit) || 1,
        exportable_fraction_safety: Number(d.exportable_fraction_safety) || 0.35,
        exportable_fraction_green: Number(d.exportable_fraction_green) || 0.15,
        spread_optimizer_enabled: Boolean(d.spread_optimizer_enabled),
        min_spread_profit_p_per_kwh: Number(d.min_spread_profit_p_per_kwh) || 3,
        peak_import_avoid_start: String(d.peak_import_avoid_start || "16:00"),
        peak_import_avoid_end: String(d.peak_import_avoid_end || "19:00"),
        winter_fill_enabled: Boolean(d.winter_fill_enabled),
        green_export_spread_multiplier: Number(d.green_export_spread_multiplier) || 2,
        cheap_import_p_per_kwh: Number(d.cheap_import_p_per_kwh) || 8,
        peak_import_penalty_p_per_kwh: Number(d.peak_import_penalty_p_per_kwh) || 5,
        charge_periods: d.charge_periods,
      });
      if (state) this._plantState = state;
      this._initSmartChargeDraft();
      this._showToast("SmartCharge settings saved");
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _initStormDraft() {
    const storm = this._plantState?.storm_prep ?? {};
    const periods = JSON.parse(JSON.stringify(storm.charge_periods ?? DEFAULT_PERIODS)).slice(0, 2);
    while (periods.length < 2) periods.push({ ...DEFAULT_PERIODS[0] });
    const catalog = this._getStormWeatherCategoryCatalog();
    const supportedIds = catalog.filter((row) => row.supported !== false).map((row) => row.id);
    const fallbackIds = STORM_WEATHER_CATEGORY_FALLBACK.map((r) => r.id);
    let stormCategories = storm.storm_weather_categories;
    if (stormCategories == null) {
      stormCategories = supportedIds.length ? supportedIds : fallbackIds;
    } else {
      stormCategories = stormCategories.filter((id) => supportedIds.includes(id));
    }
    this._stormDraft = {
      enabled: Boolean(storm.enabled),
      alert_provider: storm.alert_provider || "google_weather",
      google_weather_entry_id: storm.google_weather_entry_id ?? null,
      use_weather_condition: storm.use_weather_condition !== false,
      use_forecast_lead: storm.use_forecast_lead !== false,
      forecast_lead_hours: storm.forecast_lead_hours ?? 4,
      condition_entity_id: storm.condition_entity_id ?? null,
      weather_entity_id: storm.weather_entity_id ?? null,
      storm_weather_categories: [...stormCategories],
      trigger_entities: [...(storm.trigger_entities ?? [])],
      charge_periods: periods,
      target_max_soc: storm.target_max_soc ?? null,
      use_solcast_grid_limit: Boolean(storm.use_solcast_grid_limit),
      solcast_safety_margin: storm.solcast_safety_margin ?? DEFAULT_STORM_SOLCAST_MARGIN,
      solcast_min_soc_floor: storm.solcast_min_soc_floor ?? DEFAULT_STORM_SOLCAST_MIN_SOC,
    };
  }

  _getStormWeatherCategoryCatalog() {
    const entry = this._getSelectedGoogleWeatherEntry();
    if (entry?.storm_weather_categories?.length) {
      return entry.storm_weather_categories;
    }
    return (
      this._plantState?.storm_prep?.storm_weather_category_catalog ??
      this._triggerMeta?.google_weather?.storm_weather_categories ??
      STORM_WEATHER_CATEGORY_FALLBACK.map((row) => ({ ...row, supported: true, unsupported_reason: null, support_via: [] }))
    );
  }

  _pruneUnsupportedStormCategories() {
    if (!this._stormDraft) return;
    const supported = new Set(
      this._getStormWeatherCategoryCatalog()
        .filter((row) => row.supported !== false)
        .map((row) => row.id)
    );
    this._stormDraft.storm_weather_categories = (
      this._stormDraft.storm_weather_categories ?? []
    ).filter((id) => supported.has(id));
  }

  _applyStormEnableDefaults() {
    if (!this._stormDraft) return;
    this._stormDraft.use_forecast_lead = true;
    if (!this._stormDraft.forecast_lead_hours) this._stormDraft.forecast_lead_hours = 4;
    const entries = this._getGoogleWeatherEntries();
    const selected = this._getSelectedGoogleWeatherEntry();
    const entry =
      selected || (entries.length === 1 ? entries[0] : null);
    if (entry) this._applyGoogleWeatherEntry(entry.entry_id);
  }

  _getGoogleWeatherEntries() {
    return this._triggerMeta?.google_weather?.entries ?? [];
  }

  _getSelectedGoogleWeatherEntry() {
    const id =
      this._stormDraft?.google_weather_entry_id ??
      this._plantState?.storm_prep?.google_weather_entry_id;
    if (!id) return null;
    return this._getGoogleWeatherEntries().find((e) => e.entry_id === id) ?? null;
  }

  _applyGoogleWeatherEntry(entryId) {
    if (!this._stormDraft) return;
    this._stormDraft.google_weather_entry_id = entryId || null;
    this._stormDraft.alert_provider = "google_weather";
    const entry = this._getGoogleWeatherEntries().find((e) => e.entry_id === entryId);
    if (!entryId || !entry) {
      this._stormDraft.trigger_entities = [];
      this._stormDraft.condition_entity_id = null;
      this._stormDraft.weather_entity_id = null;
      this._stormDraft.use_weather_condition = false;
      return;
    }
    this._stormDraft.condition_entity_id = entry.condition_entity_id ?? null;
    this._stormDraft.weather_entity_id = entry.weather_entity ?? null;
    this._stormDraft.use_weather_condition = Boolean(
      entry.condition_entity_id || entry.weather_entity
    );
    if (entry.alert_trigger_ids?.length) {
      this._stormDraft.trigger_entities = [...entry.alert_trigger_ids];
    } else {
      this._stormDraft.trigger_entities = [];
    }
    this._pruneUnsupportedStormCategories();
  }

  _inferGoogleWeatherEntryId() {
    const entries = this._getGoogleWeatherEntries();
    const draft = this._stormDraft;
    if (!entries.length || !draft) return null;
    if (draft.condition_entity_id) {
      const match = entries.find((e) => e.condition_entity_id === draft.condition_entity_id);
      if (match) return match.entry_id;
    }
    if (draft.weather_entity_id) {
      const match = entries.find((e) => e.weather_entity === draft.weather_entity_id);
      if (match) return match.entry_id;
    }
    const triggers = draft.trigger_entities ?? [];
    if (triggers.length) {
      for (const entry of entries) {
        const ids = new Set(entry.alert_trigger_ids || []);
        if (triggers.every((t) => ids.has(t)) && ids.size) {
          return entry.entry_id;
        }
      }
    }
    if (entries.length === 1) return entries[0].entry_id;
    return draft.google_weather_entry_id ?? null;
  }

  _enterStormSettings() {
    this._initStormDraft();
    this._triggerFilter = "";
    this._triggerShowAll = false;
    this._triggerGoogleOnly = false;
    this._stormShowAdvanced = false;
    void this._loadTriggerCandidates();
  }

  _initPvDraft() {
    this._pvDraft = normalizePvConfig(this._plantState?.pv_config);
    syncPvDraftEfficiencyFromInstall(this._pvDraft, this._plantState, this._solcastDraft);
  }

  _enterPvSettings() {
    this._initPvDraft();
  }

  _initTariffDraft() {
    const raw = this._plantState?.tariff ?? {};
    this._tariffDraft = {
      ...normalizeTariffDraft(raw),
      import_entity: raw.import_entity || "",
      export_entity: raw.export_entity || "",
      standing_entity: raw.standing_entity || "",
    };
    if (this._tariffActiveBand == null) this._tariffActiveBand = 0;
    this._initOctopusDraft();
  }

  _initOctopusDraft() {
    const prevKey = this._octopusDraft?.api_key || "";
    const raw = this._tariffDraft?.dynamic ?? this._plantState?.tariff?.dynamic ?? {};
    this._octopusDraft = normalizeOctopusDraft(raw, this._plantState?.tariff?.octopus ?? {});
    if (prevKey && !this._octopusDraft.api_key) {
      this._octopusDraft.api_key = prevKey;
    }
  }

  _enterTariffSettings() {
    this._initTariffDraft();
    this._tariffPickerMountGen += 1;
    this._octopusPickerMountGen += 1;
  }

  _syncTariffDraftFromPickers() {
    if (!this._tariffDraft) return;
    for (const kind of ["import", "export", "standing"]) {
      const picker = this._root.querySelector(`[data-tariff-picker="${kind}"] ha-entity-picker`);
      if (picker) this._tariffDraft[`${kind}_entity`] = picker.value || "";
    }
  }

  _syncTariffScheduleFromDom() {
    if (!this._tariffDraft?.schedule) return;
    const currency = normalizeTariffCurrency(this._tariffDraft.currency);
    for (const el of this._root.querySelectorAll('[data-field^="tariff:schedule:band:"]')) {
      const parts = String(el.dataset.field || "").split(":");
      if (parts.length < 5) continue;
      const bandIdx = parseInt(parts[3], 10);
      const field = parts[4];
      if (Number.isNaN(bandIdx) || bandIdx < 0 || bandIdx > 3) continue;
      if (field !== "import" && field !== "export") continue;
      this._tariffDraft.schedule.bands[bandIdx][`${field}_p_per_kwh`] = majorToMinor(
        parseTariffRate(el.value),
        currency
      );
    }
    const standingEl = this._root.querySelector('[data-field="tariff:standing:p"]');
    if (
      standingEl &&
      normalizeTariffStandingSource(this._tariffDraft.standing_source) === "plugin" &&
      !tariffApiLocksStandingCharge(this._plantState?.tariff, this._octopusDraft)
    ) {
      this._tariffDraft.standing_charge_p_per_day = majorToMinor(parseTariffRate(standingEl.value), currency);
    }
  }

  async _syncTariffEntityPickers() {
    if (this._settingsView !== "tariff" || !this._tariffDraft || !this._hass) return;
    const gen = ++this._tariffPickerMountGen;
    for (const kind of ["import", "export", "standing"]) {
      const host = this._root.querySelector(`[data-tariff-picker="${kind}"]`);
      if (!host) continue;
      if (this._tariffDraft[`${kind}_source`] !== "entity") {
        host.replaceChildren();
        continue;
      }
      if (!host.querySelector("ha-entity-picker")) {
        host.innerHTML = `<p class="field-hint tariff-entity-picker-loading">Loading entity picker…</p>`;
      }
    }
    try {
      await ensureHaEntityPickerLoaded();
    } catch (err) {
      if (gen !== this._tariffPickerMountGen) return;
      for (const kind of ["import", "export", "standing"]) {
        const host = this._root.querySelector(`[data-tariff-picker="${kind}"]`);
        if (!host || this._tariffDraft[`${kind}_source`] !== "entity") continue;
        host.innerHTML = `<p class="tariff-entity-picker-error">${esc(err?.message || "Entity picker unavailable")}</p>`;
      }
      return;
    }
    if (gen !== this._tariffPickerMountGen) return;
    for (const kind of ["import", "export", "standing"]) {
      if (this._tariffDraft[`${kind}_source`] !== "entity") continue;
      const host = this._root.querySelector(`[data-tariff-picker="${kind}"]`);
      if (!host) continue;
      let picker = host.querySelector("ha-entity-picker");
      if (!picker) {
        host.replaceChildren();
        picker = document.createElement("ha-entity-picker");
        picker.setAttribute("allow-custom-entity", "");
        if (this._hass.userData?.showEntityIdPicker) picker.setAttribute("show-entity-id", "");
        picker.includeDomains = ["sensor"];
        picker.entityFilter = tariffSensorEntityFilter;
        picker.addEventListener("value-changed", (ev) => {
          if (this._busy || !this._tariffDraft) return;
          this._tariffDraft[`${kind}_entity`] = ev.detail?.value || "";
        });
        host.appendChild(picker);
      }
      picker.hass = this._hass;
      picker.disabled = this._busy;
      const value = this._tariffDraft[`${kind}_entity`] || "";
      if (picker.value !== value) picker.value = value || undefined;
    }
  }

  async _saveTariffSettings() {
    const plant = this._getPlant();
    if (!plant || !this._tariffDraft) return;
    this._syncOctopusIntoTariffDraft();
    this._syncTariffDraftFromPickers();
    this._syncTariffScheduleFromDom();
    const draft = buildTariffSavePayload(this._tariffDraft);
    const missing = [];
    if (draft.import_source === "entity" && !draft.import_entity) missing.push("Import sensor");
    if (draft.export_source === "entity" && !draft.export_entity) missing.push("Export sensor");
    if (draft.standing_source === "entity" && !draft.standing_entity) missing.push("Standing charge sensor");
    if (missing.length) {
      this._showToast(`${missing.join(", ")} required when using sensor source`, "err");
      return;
    }
    this._busy = true;
    this._render();
    try {
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_tariff",
        plant_id: plant.entry_id,
        tariff: draft,
      });
      if (state) this._plantState = state;
      this._initTariffDraft();
      this._showToast("Tariff settings saved");
    } catch (err) {
      this._showToast(tariffSaveErrorMessage(err), "err");
      console.error("FoxESS Plant: tariff save failed", err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _syncOctopusDraftFromPickers() {
    if (!this._octopusDraft) return;
    for (const kind of ["import", "export"]) {
      const picker = this._root.querySelector(`[data-octopus-picker="${kind}"] ha-entity-picker`);
      if (picker) this._octopusDraft[`${kind}_entity`] = picker.value || "";
    }
  }

  _syncOctopusDraftFromDom() {
    if (!this._octopusDraft) return;
    const root = this._root;
    const enabledEl = root.querySelector('[data-field="octopus:enabled"]');
    if (enabledEl) this._octopusDraft.enabled = enabledEl.checked;
    const sourceEl = root.querySelector('[data-field="octopus:source"]');
    if (sourceEl) this._octopusDraft.source = sourceEl.value === "entity" ? "entity" : "native";
    const keyEl = root.querySelector('[data-field="octopus:api_key"]');
    if (keyEl?.value) this._octopusDraft.api_key = keyEl.value;
    const accountEl = root.querySelector('[data-field="octopus:account_number"]');
    if (accountEl) this._octopusDraft.account_number = accountEl.value || "";
    const importMpanEl = root.querySelector('[data-field="octopus:import_mpan"]');
    if (importMpanEl) this._octopusDraft.import_mpan = importMpanEl.value || "";
    const exportMpanEl = root.querySelector('[data-field="octopus:export_mpan"]');
    if (exportMpanEl) this._octopusDraft.export_mpan = exportMpanEl.value || "";
  }

  _syncOctopusIntoTariffDraft() {
    if (!this._tariffDraft || !this._octopusDraft) return;
    this._syncOctopusDraftFromDom();
    const d = this._octopusDraft;
    this._tariffDraft.dynamic = {
      ...this._tariffDraft.dynamic,
      enabled: d.enabled,
      provider: d.provider,
      source: d.source,
      api_key_set: d.api_key_set,
      account_number: d.account_number,
      import_mpan: d.import_mpan,
      export_mpan: d.export_mpan,
      import_entity: d.import_entity,
      export_entity: d.export_entity,
    };
  }

  _buildOctopusSavePayload() {
    if (!this._octopusDraft) return null;
    const d = this._octopusDraft;
    return {
      enabled: Boolean(d.enabled),
      provider: d.enabled ? "octopus" : d.provider || "",
      source: d.source === "entity" ? "entity" : "native",
      account_number: d.account_number || null,
      import_mpan: d.import_mpan || null,
      export_mpan: d.export_mpan || null,
      import_entity: d.import_entity || null,
      export_entity: d.export_entity || null,
      ...(d.api_key ? { api_key: d.api_key } : {}),
    };
  }

  async _saveOctopusSettings(applySchedule = false) {
    const plant = this._getPlant();
    if (!plant || !this._octopusDraft) return;
    this._syncOctopusDraftFromDom();
    this._syncOctopusDraftFromPickers();
    const payload = this._buildOctopusSavePayload();
    if (!payload) return;
    if (payload.enabled && payload.source === "native") {
      if (!payload.api_key && !this._octopusDraft.api_key_set) {
        this._showToast("Octopus API key is required", "err");
        return;
      }
      if (!payload.account_number) {
        this._showToast("Octopus account number is required (e.g. A-12345678)", "err");
        return;
      }
    }
    if (payload.enabled && payload.source === "entity" && !payload.import_entity && !payload.export_entity) {
      this._showToast("Choose at least one import or export sensor for external mode", "err");
      return;
    }
    this._busy = true;
    this._render();
    try {
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_octopus",
        plant_id: plant.entry_id,
        octopus: { ...payload, fetch_now: true, apply_schedule: applySchedule },
      });
      if (state) this._plantState = state;
      this._initTariffDraft();
      this._showToast("Octopus settings saved — schedule synced from API");
    } catch (err) {
      this._showToast(tariffSaveErrorMessage(err), "err");
      console.error("FoxESS Plant: octopus save failed", err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _testOctopusConnection() {
    const plant = this._getPlant();
    if (!plant || !this._octopusDraft) return;
    this._syncOctopusDraftFromDom();
    const key = this._octopusDraft.api_key || undefined;
    if (!key && !this._octopusDraft.api_key_set) {
      this._showToast("Enter an Octopus API key to test", "err");
      return;
    }
    if (!this._octopusDraft.account_number) {
      this._showToast("Enter your Octopus account number to test", "err");
      return;
    }
    this._busy = true;
    this._render();
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/test_octopus",
        plant_id: plant.entry_id,
        api_key: key,
        account_number: this._octopusDraft.account_number,
      });
      if (result?.plant_state) this._plantState = result.plant_state;
      const imp = result?.octopus?.import_meters?.length ?? 0;
      const exp = result?.octopus?.export_meters?.length ?? 0;
      this._showToast(`Connected — ${imp} import meter(s), ${exp} export meter(s)`);
      this._initOctopusDraft();
      this._octopusPickerMountGen += 1;
      this._scheduleRender();
    } catch (err) {
      this._showToast(tariffSaveErrorMessage(err), "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _fetchOctopusRates() {
    const plant = this._getPlant();
    if (!plant) return;
    this._busy = true;
    this._render();
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/fetch_octopus",
        plant_id: plant.entry_id,
      });
      if (result?.plant_state) this._plantState = result.plant_state;
      this._initOctopusDraft();
      this._initTariffDraft();
      const octopus = this._plantState?.tariff?.octopus ?? {};
      const tariffType = octopus.tariff_type ? String(octopus.tariff_type) : "";
      const agile = tariffType === "agile" || tariffType === "tracker";
      this._showToast(
        agile ? "Octopus rates refreshed" : "Octopus rates refreshed — daily schedule updated"
      );
    } catch (err) {
      this._showToast(tariffSaveErrorMessage(err), "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _applyOctopusSchedule() {
    const plant = this._getPlant();
    if (!plant) return;
    this._busy = true;
    this._render();
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/apply_octopus_schedule",
        plant_id: plant.entry_id,
      });
      if (result?.plant_state) this._plantState = result.plant_state;
      this._initTariffDraft();
      this._showToast("Daily schedule filled from Octopus rates");
    } catch (err) {
      this._showToast(tariffSaveErrorMessage(err), "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _syncOctopusEntityPickers() {
    if (this._settingsView !== "tariff" || !this._octopusDraft || this._octopusDraft.source !== "entity" || !this._hass) {
      return;
    }
    const gen = ++this._octopusPickerMountGen;
    for (const kind of ["import", "export"]) {
      const host = this._root.querySelector(`[data-octopus-picker="${kind}"]`);
      if (!host) continue;
      if (!host.querySelector("ha-entity-picker")) {
        host.innerHTML = `<p class="field-hint tariff-entity-picker-loading">Loading entity picker…</p>`;
      }
    }
    try {
      await ensureHaEntityPickerLoaded();
    } catch (err) {
      if (gen !== this._octopusPickerMountGen) return;
      for (const kind of ["import", "export"]) {
        const host = this._root.querySelector(`[data-octopus-picker="${kind}"]`);
        if (!host) continue;
        host.innerHTML = `<p class="tariff-entity-picker-error">${esc(err?.message || "Entity picker unavailable")}</p>`;
      }
      return;
    }
    if (gen !== this._octopusPickerMountGen) return;
    for (const kind of ["import", "export"]) {
      const host = this._root.querySelector(`[data-octopus-picker="${kind}"]`);
      if (!host) continue;
      let picker = host.querySelector("ha-entity-picker");
      if (!picker) {
        host.replaceChildren();
        picker = document.createElement("ha-entity-picker");
        picker.setAttribute("allow-custom-entity", "");
        if (this._hass.userData?.showEntityIdPicker) picker.setAttribute("show-entity-id", "");
        picker.includeDomains = ["sensor"];
        picker.entityFilter = tariffSensorEntityFilter;
        picker.addEventListener("value-changed", (ev) => {
          if (this._busy || !this._octopusDraft) return;
          this._octopusDraft[`${kind}_entity`] = ev.detail?.value || "";
        });
        host.appendChild(picker);
      }
      picker.hass = this._hass;
      picker.disabled = this._busy;
      const value = this._octopusDraft[`${kind}_entity`] || "";
      if (picker.value !== value) picker.value = value || undefined;
    }
  }

  _initSolcastDraft() {
    const sc = this._plantState?.solcast ?? {};
    this._solcastDraft = {
      enabled: solcastEnabledFromLive(sc),
      api_key: "",
      api_key_set: Boolean(sc.api_key_set),
      api_limit: sc.api_limit ?? 10,
      auto_update: sc.auto_update === "all_day" ? "all_day" : "daylight",
      fetch_pv_forecast: sc.fetch_pv_forecast !== false,
      latitude: sc.latitude ?? sc.coordinates?.latitude ?? "",
      longitude: sc.longitude ?? sc.coordinates?.longitude ?? "",
      installation_date: sc.installation_date ?? "",
      period: sc.period ?? "PT30M",
    };
  }

  _enterSolcastSettings() {
    this._solcastDraft = null;
    this._initSolcastDraft();
    this._initPvDraft();
  }

  _initGlowDraft() {
    const g = this._plantState?.glow ?? {};
    this._glowDraft = {
      enabled: Boolean(g.enabled),
      mqtt_enabled: g.mqtt_enabled !== false,
      api_enabled: g.api_enabled !== false,
      username: g.username || "",
      username_set: Boolean(g.username_set),
      password: "",
      password_set: Boolean(g.password_set),
      topic_prefix: g.topic_prefix || "glow",
      device_id: g.device_id || "+",
      import_resource_id: g.import_resource_id || "",
      export_resource_id: g.export_resource_id || "",
    };
  }

  _enterGlowSettings() {
    this._glowDraft = null;
    this._glowFormDirty = false;
    this._initGlowDraft();
  }

  _applyGlowDraftFromSaved(g) {
    if (!this._glowDraft) this._initGlowDraft();
    const d = this._glowDraft;
    d.enabled = Boolean(g.enabled);
    d.mqtt_enabled = g.mqtt_enabled !== false;
    d.api_enabled = g.api_enabled !== false;
    if (g.username) d.username = g.username;
    d.username_set = Boolean(g.username_set || g.username);
    d.password_set = Boolean(g.password_set);
    d.password = "";
    if (g.topic_prefix) d.topic_prefix = g.topic_prefix;
    if (g.device_id) d.device_id = g.device_id;
    if (g.import_resource_id) d.import_resource_id = g.import_resource_id;
    if (g.export_resource_id) d.export_resource_id = g.export_resource_id;
    this._glowFormDirty = false;
  }

  _buildGlowSavePayload() {
    if (!this._glowDraft) return null;
    this._syncGlowDraftFromDom();
    const d = this._glowDraft;
    const payload = {
      enabled: Boolean(d.enabled),
      mqtt_enabled: Boolean(d.mqtt_enabled),
      api_enabled: Boolean(d.api_enabled),
      topic_prefix: String(d.topic_prefix || "glow").trim() || "glow",
      device_id: String(d.device_id || "+").trim() || "+",
    };
    const user = String(d.username || "").trim();
    if (user) payload.username = user;
    const pw = String(d.password || "").trim();
    if (pw) payload.password = pw;
    const importId = String(d.import_resource_id || "").trim();
    if (importId) payload.import_resource_id = importId;
    const exportId = String(d.export_resource_id || "").trim();
    if (exportId) payload.export_resource_id = exportId;
    return payload;
  }

  _syncGlowDraftFromDom() {
    if (!this._glowDraft) return;
    const root = this._root;
    for (const [field, key] of [
      ["glow:enabled", "enabled"],
      ["glow:mqtt_enabled", "mqtt_enabled"],
      ["glow:api_enabled", "api_enabled"],
    ]) {
      const el = root.querySelector(`[data-field="${field}"]`);
      if (el) this._glowDraft[key] = el.checked;
    }
    const textFields = [
      ["glow:username", "username"],
      ["glow:topic_prefix", "topic_prefix"],
      ["glow:device_id", "device_id"],
      ["glow:import_resource_id", "import_resource_id"],
      ["glow:export_resource_id", "export_resource_id"],
    ];
    for (const [field, key] of textFields) {
      const el = root.querySelector(`[data-field="${field}"]`);
      if (el) this._glowDraft[key] = el.value ?? "";
    }
    const pwEl = root.querySelector('[data-field="glow:password"]');
    if (pwEl?.value) this._glowDraft.password = pwEl.value;
  }

  _glowSettingsSubtitle() {
    const g = this._plantState?.glow;
    if (!g?.enabled) return "Off — optional Hildebrand Glow IHD smart meter";
    const live = g.live || {};
    if (live.import_kw != null) return `Live ${Number(live.import_kw).toFixed(2)} kW import · smart meter`;
    if (g.mqtt_connected) return "MQTT connected — awaiting first reading";
    if (g.last_error) return String(g.last_error).slice(0, 60);
    return "Enabled — configure MQTT or Bright API";
  }

  async _saveGlowSettings() {
    const plant = this._getPlant();
    if (!plant || !this._glowDraft) return;
    const payload = this._buildGlowSavePayload();
    if (!payload) return;
    this._busy = true;
    this._render();
    try {
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_glow",
        plant_id: plant.entry_id,
        glow: payload,
      });
      if (state) this._plantState = state;
      this._applyGlowDraftFromSaved(this._plantState?.glow ?? {});
      this._showToast("Glow settings saved");
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _testGlowConnection() {
    const plant = this._getPlant();
    if (!plant || !this._glowDraft) return;
    this._syncGlowDraftFromDom();
    this._busy = true;
    this._render();
    try {
      const draft = this._glowDraft;
      const msg = {
        type: "foxess_plant/test_glow",
        plant_id: plant.entry_id,
      };
      const user = String(draft.username || "").trim();
      const pw = String(draft.password || "").trim();
      if (user) msg.username = user;
      if (pw) msg.password = pw;
      const res = await this._hass.connection.sendMessagePromise(msg);
      if (res?.plant_state) this._plantState = res.plant_state;
      this._applyGlowDraftFromSaved(this._plantState?.glow ?? res?.glow ?? {});
      const g = res?.glow ?? {};
      const lines = [
        g.valid ? "Bright login OK" : "Login failed",
        g.resource_count != null ? `${g.resource_count} resource(s)` : null,
        g.import_resource_id ? `Import: ${g.import_resource_id}` : null,
        g.export_resource_id ? `Export: ${g.export_resource_id}` : null,
      ].filter(Boolean);
      this._showToast(lines.join(" · ") || "Glow test complete");
    } catch (err) {
      this._showToast(err?.message || "Glow test failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _syncSolcastDraftFromDom() {
    if (!this._solcastDraft) return;
    const root = this._root;
    const enabledEl = root.querySelector('[data-field="solcast:enabled"]');
    if (enabledEl) this._solcastDraft.enabled = enabledEl.checked;
    const fetchEl = root.querySelector('[data-field="solcast:fetch_pv_forecast"]');
    if (fetchEl) this._solcastDraft.fetch_pv_forecast = fetchEl.checked;
  }

  _solcastSettingsSubtitle() {
    const sc = this._plantState?.solcast;
    if (!solcastEnabledFromLive(sc)) return "Off — enable for native PV forecast on charts";
    if (!sc.api_key_set) return "API key required";
    if (!sc.coordinates_configured) return "Solcast site latitude/longitude required";
    if (!sc.hobbyist_sites_resolved) return "Linking to Solcast Home PV site(s)… save settings";
    const rem = sc.api_remaining ?? "—";
    return `PV forecast · ${sc.api_used_today ?? 0}/${sc.api_limit ?? 10} API calls today · ${rem} left`;
  }

  async _saveSolcastSettings() {
    const plant = this._getPlant();
    if (!plant || !this._solcastDraft) return;
    this._syncSolcastDraftFromDom();
    this._busy = true;
    this._render();
    try {
      const draft = this._solcastDraft;
      const validationErr = validateSolcastDraft(draft);
      if (validationErr) {
        this._showToast(validationErr, "err");
        return;
      }
      const lat = normalizeSolcastCoordinateInput(draft.latitude);
      const lon = normalizeSolcastCoordinateInput(draft.longitude);
      const payload = {
        enabled: Boolean(draft.enabled),
        api_limit: Math.max(1, Math.min(50, parseInt(draft.api_limit, 10) || 10)),
        auto_update: draft.auto_update === "all_day" ? "all_day" : "daylight",
        fetch_pv_forecast: Boolean(draft.fetch_pv_forecast),
        period: draft.period || "PT30M",
        latitude: lat,
        longitude: lon,
        installation_date: normalizeSolcastInstallationDateInput(draft.installation_date),
      };
      const key = String(draft.api_key || "").trim();
      if (key) payload.api_key = key;
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_solcast",
        plant_id: plant.entry_id,
        solcast: payload,
      });
      if (state) this._plantState = state;
      if (this._pvDraft && draft.fetch_pv_forecast) {
        syncPvDraftEfficiencyFromInstall(this._pvDraft, this._plantState, this._solcastDraft);
        const pvState = await this._hass.connection.sendMessagePromise({
          type: "foxess_plant/update_pv_config",
          plant_id: plant.entry_id,
          pv_config: normalizePvConfig(this._pvDraft),
        });
        if (pvState) this._plantState = pvState;
        this._initPvDraft();
      }
      this._initSolcastDraft();
      this._showToast("Solcast settings saved");
      this._reloadStatisticsChartWhenVisible();
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _testSolcastConnection() {
    const plant = this._getPlant();
    if (!plant || !this._solcastDraft) return;
    this._syncSolcastDraftFromDom();
    this._busy = true;
    this._render();
    try {
      const draft = this._solcastDraft;
      const key = String(draft.api_key || "").trim();
      if (key || !draft.api_key_set) {
        const payload = {
          enabled: Boolean(draft.enabled),
          api_limit: Math.max(1, Math.min(50, parseInt(draft.api_limit, 10) || 10)),
          auto_update: draft.auto_update === "all_day" ? "all_day" : "daylight",
          fetch_pv_forecast: Boolean(draft.fetch_pv_forecast),
          period: draft.period || "PT30M",
          latitude: draft.latitude === "" ? null : parseFloat(draft.latitude),
          longitude: draft.longitude === "" ? null : parseFloat(draft.longitude),
          fetch_now: false,
        };
        if (key) payload.api_key = key;
        const state = await this._hass.connection.sendMessagePromise({
          type: "foxess_plant/update_solcast",
          plant_id: plant.entry_id,
          solcast: payload,
        });
        if (state) this._plantState = state;
      }
      const res = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/test_solcast",
        plant_id: plant.entry_id,
      });
      if (res?.plant_state) this._plantState = res.plant_state;
      this._initSolcastDraft();
      this._reloadStatisticsChartWhenVisible();
      const sc = res?.solcast ?? {};
      const summary = sc.live_summary;
      const match = sc.test_match_note || summary?.match_note;
      const msg = match
        ? `Solcast hobbyist OK — ${match}`
        : summary?.condition_label
          ? `Solcast hobbyist OK — ${summary.condition_label}`
          : "Solcast hobbyist API OK (listed Home PV sites)";
      this._showToast(msg);
    } catch (err) {
      this._showToast(err?.message || "Solcast test failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _savePvConfig() {
    const plant = this._getPlant();
    if (!plant || !this._pvDraft) return;
    syncPvDraftEfficiencyFromInstall(this._pvDraft, this._plantState, this._solcastDraft);
    this._busy = true;
    this._render();
    try {
      const state = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/update_pv_config",
        plant_id: plant.entry_id,
        pv_config: normalizePvConfig(this._pvDraft),
      });
      if (state) this._plantState = state;
      this._initPvDraft();
      this._showToast("PV configuration saved");
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _loadTriggerCandidates() {
    if (!this._hass) return;
    try {
      this._triggerMeta = await fetchTriggerCandidates(this._hass);
      this._triggerCandidates = this._triggerMeta?.entities ?? [];
      if (this._settingsView === "storm" && this._stormDraft) {
        const inferred = this._inferGoogleWeatherEntryId();
        if (inferred && !this._stormDraft.google_weather_entry_id) {
          this._applyGoogleWeatherEntry(inferred);
        } else if (this._stormDraft.google_weather_entry_id) {
          this._applyGoogleWeatherEntry(this._stormDraft.google_weather_entry_id);
        }
        this._scheduleRender();
      }
    } catch {
      this._triggerMeta = null;
      this._triggerCandidates = [];
    }
  }

  async _saveStormPrep() {
    const plant = this._getPlant();
    if (!plant || !this._stormDraft) return;
    this._busy = true;
    this._render();
    try {
      const target = this._stormDraft.target_max_soc;
      const payload = {
        type: "foxess_plant/update_storm_prep",
        plant_id: plant.entry_id,
        enabled: this._stormDraft.enabled,
        trigger_entities: this._stormDraft.trigger_entities,
        charge_periods: this._stormDraft.charge_periods,
        target_max_soc: target == null || target === "" ? null : Number(target),
      };
      if (this._stormDraft.alert_provider) {
        payload.alert_provider = this._stormDraft.alert_provider;
      }
      if (this._stormDraft.google_weather_entry_id) {
        payload.google_weather_entry_id = this._stormDraft.google_weather_entry_id;
      }
      payload.use_forecast_lead = Boolean(this._stormDraft.use_forecast_lead);
      payload.forecast_lead_hours = Number(this._stormDraft.forecast_lead_hours) || 4;
      payload.storm_weather_categories = [...(this._stormDraft.storm_weather_categories ?? [])];
      payload.use_solcast_grid_limit = Boolean(this._stormDraft.use_solcast_grid_limit);
      payload.solcast_safety_margin = Number(this._stormDraft.solcast_safety_margin) || DEFAULT_STORM_SOLCAST_MARGIN;
      payload.solcast_min_soc_floor = Number(this._stormDraft.solcast_min_soc_floor) || DEFAULT_STORM_SOLCAST_MIN_SOC;
      const state = await this._hass.connection.sendMessagePromise(payload);
      if (state) this._plantState = state;
      this._initStormDraft();
      this._showToast("StormSafe settings saved");
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _handleClick(e) {
    const btn = e.target.closest("[data-action]");
    if (!btn || this._busy) return;
    const action = btn.dataset.action;

    if (action === "ha-menu-toggle") {
      this._toggleHaSidebar();
      return;
    }
    if (action === "energy-balance-help-dialog") return;
    if (action === "octopus-greener-view") {
      const nextView = btn.dataset.view === "detailed" ? "detailed" : "standard";
      if (nextView === this._octopusGreenerView) return;
      this._octopusGreenerView = nextView;
      this._octopusGreenerAnalysisSlotCache = undefined;
      this._scheduleRender(true);
      return;
    }
    if (action === "device-alarm-detail-dialog") return;
    if (action === "device-alarm-detail-open") {
      const alarm = btn.dataset.alarm;
      if (!alarm) return;
      this._foxAlarmDetailName = alarm;
      this._syncFoxAlarmDetailModal(this._root.querySelector(".shell"));
      return;
    }
    if (action === "device-alarm-detail-close") {
      this._foxAlarmDetailName = null;
      this._syncFoxAlarmDetailModal(this._root.querySelector(".shell"));
      return;
    }
    if (action === "device-alarm-detail-backdrop") {
      if (e.target === btn) {
        this._foxAlarmDetailName = null;
        this._syncFoxAlarmDetailModal(this._root.querySelector(".shell"));
      }
      return;
    }
    if (action === "energy-balance-help-open") {
      this._energyBalanceHelpOpen = true;
      this._syncEnergyBalanceHelpModal(this._root.querySelector(".shell"));
      return;
    }
    if (action === "energy-balance-help-close") {
      this._energyBalanceHelpOpen = false;
      this._syncEnergyBalanceHelpModal(this._root.querySelector(".shell"));
      return;
    }
    if (action === "energy-balance-help-backdrop") {
      if (e.target === btn) {
        this._energyBalanceHelpOpen = false;
        this._syncEnergyBalanceHelpModal(this._root.querySelector(".shell"));
      }
      return;
    }
    if (action === "nav") {
      const nextView = btn.dataset.view;
      if (
        this._view === "energy_analysis" &&
        nextView !== "energy_analysis"
      ) {
        this._energyPeriodOffset = 0;
        this._energyBreakdown = null;
        this._statisticsChart = null;
        this._statisticsChartPlantId = undefined;
        this._forecastAccuracyAnalysis = null;
        this._forecastAccuracyAnalysisKey = undefined;
        this._forecastAccuracyAnalysisSlotCache = undefined;
        this._energyAnalysisSummaryCache = undefined;
        this._energyAnalysisChartSlotCache = undefined;
        this._energyAnalysisToolbarCache = undefined;
        this._analysisSummarySpark = null;
        this._analysisSummarySparkKey = undefined;
        this._energyBalanceHelpOpen = false;
      }
      if (this._view === "reports" && nextView !== "reports") {
        this._reportsPeriodOffset = 0;
        this._reportsView = "energy_report";
        this._energyReport = null;
        this._energyReportPlantId = undefined;
        this._smartChargeAnalysis = null;
        this._smartChargeAnalysisPlantId = undefined;
        this._octopusAnalysisPlantId = undefined;
        this._energyBalanceHelpOpen = false;
      }
      this._view = normalizePanelView(nextView);
      this._settingsView = "main";
      this._settingsFieldFocused = false;
      this._solcastDraft = null;
      this._deviceSub = "main";
      if (nextView !== "device_new") {
        this._deviceNewSub = "analysis";
        this._deviceNewScreen = "main";
        this._foxAlarmDetailName = null;
        this._deviceNewStatisticsChart = null;
        this._deviceNewStatisticsChartPlantId = undefined;
        this._deviceNewEnergyChart = null;
        this._deviceNewEnergyChartPlantId = undefined;
      } else if (btn.dataset.deviceSub) {
        this._deviceNewSub = btn.dataset.deviceSub;
        this._deviceNewScreen = "main";
        this._foxAlarmDetailName = null;
      }
      if (this._view === "energy_analysis") this._loadEnergyCharts();
      if (this._view === "reports") {
        this._normalizeReportsPeriodState();
        this._loadActiveReport();
      }
      if (this._view === "overview") this._loadOverviewStatisticsChart();
      if (this._view === "device_new") {
        this._loadDeviceNewCharts();
        if (this._deviceNewSub === "alarms") void this._loadDeviceNewAlarms({ force: true });
      }
      this._render();
      return;
    }
    if (action === "device-new-tab") {
      const sub = btn.dataset.sub;
      if (!sub || sub === this._deviceNewSub) return;
      this._deviceNewSub = sub;
      this._deviceNewScreen = "main";
      this._foxAlarmDetailName = null;
      if (sub === "analysis") this._loadDeviceNewCharts();
      if (sub === "alarms") void this._loadDeviceNewAlarms({ force: true });
      if (sub === "pv-config") this._enterPvSettings();
      this._scheduleRender(true);
      return;
    }
    if (action === "device-alarm-tab") {
      const tab = btn.dataset.tab;
      if (!tab || tab === this._deviceNewAlarmTab) return;
      this._deviceNewAlarmTab = tab;
      this._patchDeviceNewAlarmTabUi();
      return;
    }
    if (action === "device-alarm-range") {
      const range = btn.dataset.range;
      if (!range || range === this._deviceNewAlarmHistoryRange) return;
      this._deviceNewAlarmHistoryRange = range;
      if (range === "custom") {
        const def = defaultAlarmCustomRangeValues();
        if (!this._deviceNewAlarmHistoryStart) this._deviceNewAlarmHistoryStart = def.start;
        if (!this._deviceNewAlarmHistoryEnd) this._deviceNewAlarmHistoryEnd = def.end;
      }
      this._patchDeviceNewAlarmListDynamic();
      return;
    }
    if (action === "device-alarm-filter-clear") {
      this._deviceNewAlarmFilterCategory = "";
      this._deviceNewAlarmFilterSeverity = "";
      this._deviceNewAlarmFilterDevice = "";
      this._patchDeviceNewAlarmListDynamic();
      return;
    }
    if (action === "copy-device-serial") {
      e.preventDefault();
      e.stopPropagation();
      const serial = btn.dataset.serial;
      if (!serial) return;
      const ok = await copyTextToClipboard(serial);
      this._showToast(ok ? "Serial number copied" : "Copy failed", ok ? "ok" : "err");
      return;
    }
    if (action === "device-new-sub") {
      const sub = btn.dataset.sub;
      if (!sub) return;
      this._deviceNewScreen = sub;
      this._scheduleRender(true);
      return;
    }
    if (action === "device-new-back") {
      this._deviceNewScreen = "main";
      this._scheduleRender(true);
      return;
    }
    if (action === "device-new-energy-period") {
      const period = btn.dataset.period;
      if (!period || period === this._deviceNewEnergyPeriod) return;
      this._deviceNewEnergyPeriod = period;
      this._deviceNewEnergyPeriodOffset = 0;
      this._invalidateDeviceNewCharts();
      void this._loadDeviceNewCharts();
      this._scheduleRender(true);
      return;
    }
    if (action === "device-new-curve-nav") {
      const dir = btn.dataset.dir;
      const offset = Math.max(0, this._deviceNewCurveDayOffset || 0);
      if (dir === "prev") {
        this._deviceNewCurveDayOffset = offset + 1;
      } else if (dir === "next" && offset > 0) {
        this._deviceNewCurveDayOffset = offset - 1;
      } else {
        return;
      }
      this._invalidateDeviceNewCharts();
      void this._loadDeviceNewCharts();
      this._scheduleRender(true);
      return;
    }
    if (action === "device-new-energy-nav") {
      const dir = btn.dataset.dir;
      const bounds = energyPeriodBounds(this._deviceNewEnergyPeriod, this._deviceNewEnergyPeriodOffset);
      if (dir === "prev") {
        this._deviceNewEnergyPeriodOffset += 1;
      } else if (dir === "next" && bounds.canNext) {
        this._deviceNewEnergyPeriodOffset = Math.max(0, this._deviceNewEnergyPeriodOffset - 1);
      } else {
        return;
      }
      this._invalidateDeviceNewCharts();
      void this._loadDeviceNewCharts();
      this._scheduleRender(true);
      return;
    }
    if (action === "energy-period") {
      const period = btn.dataset.period;
      if (!period || period === this._energyPeriod) return;
      this._energyPeriod = period;
      this._energyPeriodOffset = 0;
      this._energyBreakdown = null;
      this._energyChart = null;
      this._energyChartPlantId = undefined;
      this._statisticsChart = null;
      this._statisticsChartPlantId = undefined;
      this._analysisSummarySpark = null;
      this._analysisSummarySparkKey = undefined;
      this._forecastAccuracyAnalysis = null;
      this._forecastAccuracyAnalysisKey = undefined;
      this._forecastAccuracyAnalysisSlotCache = undefined;
      this._energyAnalysisSummaryCache = undefined;
      this._beginForecastAccuracyAnalysisLoad();
      this._loadEnergyCharts();
      this._scheduleRender(true);
      return;
    }
    if (action === "reports-period") {
      const period = normalizeReportsPeriod(btn.dataset.period);
      if (!period || period === this._reportsPeriod) return;
      this._reportsPeriod = period;
      this._reportsPeriodOffset = 0;
      this._energyReport = null;
      this._energyReportPlantId = undefined;
      this._smartChargeAnalysis = null;
      this._smartChargeAnalysisPlantId = undefined;
      this._loadActiveReport();
      this._scheduleRender(true);
      return;
    }
    if (action === "reports-nav") {
      const dir = btn.dataset.dir;
      const bounds = energyPeriodBounds(this._reportsPeriod, this._reportsPeriodOffset);
      if (dir === "prev") {
        this._reportsPeriodOffset += 1;
      } else if (dir === "next" && bounds.canNext) {
        this._reportsPeriodOffset = Math.max(0, this._reportsPeriodOffset - 1);
      } else {
        return;
      }
      this._energyReport = null;
      this._energyReportPlantId = undefined;
      this._smartChargeAnalysis = null;
      this._smartChargeAnalysisPlantId = undefined;
      this._loadActiveReport();
      this._scheduleRender(true);
      return;
    }
    if (action === "energy-nav") {
      const dir = btn.dataset.dir;
      const bounds = energyPeriodBounds(this._energyPeriod, this._energyPeriodOffset);
      if (dir === "prev") {
        this._energyPeriodOffset += 1;
      } else if (dir === "next" && bounds.canNext) {
        this._energyPeriodOffset = Math.max(0, this._energyPeriodOffset - 1);
      } else {
        return;
      }
      this._energyBreakdown = null;
      this._energyChart = null;
      this._energyChartPlantId = undefined;
      this._statisticsChart = null;
      this._statisticsChartPlantId = undefined;
      this._analysisSummarySpark = null;
      this._analysisSummarySparkKey = undefined;
      this._forecastAccuracyAnalysis = null;
      this._forecastAccuracyAnalysisKey = undefined;
      this._forecastAccuracyAnalysisSlotCache = undefined;
      this._energyAnalysisSummaryCache = undefined;
      this._energyAnalysisChartSlotCache = undefined;
      this._energyAnalysisToolbarCache = undefined;
      this._beginForecastAccuracyAnalysisLoad();
      this._loadEnergyCharts();
      this._scheduleRender(true);
      return;
    }
    if (action === "device-sub") {
      this._deviceSub = btn.dataset.sub;
      if (btn.dataset.sub === "parameters") this._deviceParamOpen = new Set();
      if (btn.dataset.sub === "pv-config") this._enterPvSettings();
      this._render();
      return;
    }
    if (action === "device-param-toggle") {
      const sectionId = btn.dataset.section;
      if (!sectionId) return;
      if (this._deviceParamOpen.has(sectionId)) this._deviceParamOpen.delete(sectionId);
      else this._deviceParamOpen.add(sectionId);
      this._scheduleRender();
      return;
    }
    if (action === "device-back") {
      this._deviceSub = "main";
      this._deviceParamOpen = new Set();
      this._render();
      return;
    }
    if (action === "settings-sub") {
      this._view = "settings";
      if (btn.dataset.sub !== "solcast") this._solcastDraft = null;
      if (btn.dataset.sub !== "tariff") {
        this._tariffDraft = null;
        this._tariffPickerMountGen += 1;
      }
      if (btn.dataset.sub !== "smart") this._smartChargeDraft = null;
      if (btn.dataset.sub !== "glow") this._glowDraft = null;
      this._settingsView = btn.dataset.sub;
      if (btn.dataset.sub === "schedules") this._initChargeDraft();
      if (btn.dataset.sub === "quick") this._initSocDraft();
      if (btn.dataset.sub === "workmode") this._initWorkModeDraft();
      if (btn.dataset.sub === "storm") this._enterStormSettings();
      if (btn.dataset.sub === "pv") this._enterPvSettings();
      if (btn.dataset.sub === "solcast") this._enterSolcastSettings();
      if (btn.dataset.sub === "glow") this._enterGlowSettings();
      if (btn.dataset.sub === "tariff") this._enterTariffSettings();
      if (btn.dataset.sub === "smart") this._enterSmartChargeSettings();
      this._render();
      return;
    }
    if (action === "reports-tab") {
      const sub = btn.dataset.sub;
      if (!sub || sub === this._reportsView) return;
      this._reportsView = sub;
      if (sub === "octopus") void this._loadOctopusAnalysis();
      else if (sub === "smart_charge") void this._loadSmartChargeAnalysis();
      else this._loadEnergyReport();
      this._scheduleRender(true);
      return;
    }
    if (action === "settings-tab") {
      this._view = "settings";
      if (btn.dataset.sub !== "solcast") this._solcastDraft = null;
      if (btn.dataset.sub !== "tariff") {
        this._tariffDraft = null;
        this._tariffPickerMountGen += 1;
      }
      if (btn.dataset.sub !== "smart") this._smartChargeDraft = null;
      if (btn.dataset.sub !== "glow") this._glowDraft = null;
      this._settingsView = btn.dataset.sub;
      if (btn.dataset.sub === "schedules") this._initChargeDraft();
      if (btn.dataset.sub === "quick") this._initSocDraft();
      if (btn.dataset.sub === "workmode") this._initWorkModeDraft();
      if (btn.dataset.sub === "storm") this._enterStormSettings();
      if (btn.dataset.sub === "pv") this._enterPvSettings();
      if (btn.dataset.sub === "solcast") this._enterSolcastSettings();
      if (btn.dataset.sub === "glow") this._enterGlowSettings();
      if (btn.dataset.sub === "tariff") this._enterTariffSettings();
      if (btn.dataset.sub === "smart") this._enterSmartChargeSettings();
      this._render();
      return;
    }
    if (action === "save-pv-config") {
      await this._savePvConfig();
      return;
    }
    if (action === "save-tariff-settings") {
      await this._saveTariffSettings();
      return;
    }
    if (action === "save-octopus-settings") {
      await this._saveOctopusSettings(false);
      return;
    }
    if (action === "save-octopus-apply") {
      await this._saveOctopusSettings(true);
      return;
    }
    if (action === "test-octopus") {
      await this._testOctopusConnection();
      return;
    }
    if (action === "fetch-octopus") {
      await this._fetchOctopusRates();
      return;
    }
    if (action === "apply-octopus-schedule") {
      await this._applyOctopusSchedule();
      return;
    }
    if (action === "tariff-pick-band") {
      if (!this._tariffDraft) return;
      const band = parseInt(btn.dataset.band, 10);
      if (Number.isFinite(band) && band >= 0 && band <= 3) {
        this._tariffActiveBand = band;
        this._render();
      }
      return;
    }
    if (action === "tariff-hour") {
      if (!this._tariffDraft?.schedule || this._busy) return;
      const hour = parseInt(btn.dataset.hour, 10);
      const band = this._tariffActiveBand ?? 0;
      if (Number.isFinite(hour) && hour >= 0 && hour <= 23) {
        this._tariffDraft.schedule.hours[hour] = band;
        this._render();
      }
      return;
    }
    if (action === "save-solcast-settings") {
      await this._saveSolcastSettings();
      return;
    }
    if (action === "save-glow-settings") {
      await this._saveGlowSettings();
      return;
    }
    if (action === "test-glow") {
      await this._testGlowConnection();
      return;
    }
    if (action === "test-solcast") {
      await this._testSolcastConnection();
      return;
    }
    if (action === "pick-work-mode") {
      this._workModeDraft = btn.dataset.mode;
      this._render();
      return;
    }
    if (action === "pick-smart-charge-mode") {
      if (!this._smartChargeDraft) this._initSmartChargeDraft();
      this._smartChargeDraft.operating_mode = btn.dataset.mode || "max_safety";
      this._render();
      return;
    }
    if (action === "copy-period") {
      if (!this._chargeDraft) return;
      const from = parseInt(btn.dataset.from, 10);
      const to = parseInt(btn.dataset.to, 10);
      if (Number.isNaN(from) || Number.isNaN(to)) return;
      this._chargeDraft[to] = { ...this._chargeDraft[from] };
      this._render();
      return;
    }
    if (action === "swap-periods") {
      if (!this._chargeDraft) return;
      const tmp = this._chargeDraft[0];
      this._chargeDraft[0] = this._chargeDraft[1];
      this._chargeDraft[1] = tmp;
      this._render();
      return;
    }
    if (action === "save-schedules") {
      await this._saveSchedules();
      return;
    }
    if (action === "save-soc") {
      await this._saveSoc();
      return;
    }
    if (action === "soc-result-close") {
      this._socSaveResults = null;
      this._render();
      return;
    }
    if (action === "save-work-mode") {
      await this._saveWorkMode();
      return;
    }
    if (action === "apply-baseline") {
      await this._runPlantService("apply_baseline");
      return;
    }
    if (action === "sync-schedule") {
      await this._syncScheduleFromInverter();
      return;
    }
    if (action === "reapply-schedule") {
      await this._runPlantService("reapply_schedule", {}, "Schedule re-applied to inverter");
      return;
    }
    if (action === "take-control") {
      await this._runPlantService("take_control");
      return;
    }
    if (action === "release-control") {
      await this._runPlantService("release_control");
      return;
    }
    if (action === "arm-storm") {
      await this._runPlantService("arm_storm_prep", { reason: "panel_manual" });
      return;
    }
    if (action === "disarm-storm") {
      await this._runPlantService("disarm_storm_prep");
      return;
    }
    if (action === "save-smart-charge") {
      await this._saveSmartChargeSettings();
      return;
    }
    if (action === "save-storm-prep") {
      await this._saveStormPrep();
      return;
    }
    if (action === "remove-storm-trigger") {
      if (!this._stormDraft) return;
      const entityId = btn.dataset.entity;
      if (!entityId) return;
      this._stormDraft.trigger_entities = this._stormDraft.trigger_entities.filter((id) => id !== entityId);
      this._syncStormTriggerPicker();
      return;
    }
    if (action === "toggle-storm-advanced") {
      this._stormShowAdvanced = !this._stormShowAdvanced;
      this._scheduleRender();
      return;
    }
    if (action === "storm-show-google-only") {
      this._triggerGoogleOnly = true;
      this._triggerShowAll = false;
      this._triggerFilter = "";
      this._syncStormTriggerPicker();
      return;
    }
    if (action === "storm-show-suggested") {
      this._triggerGoogleOnly = false;
      this._triggerShowAll = false;
      this._syncStormTriggerPicker();
      return;
    }
    if (action === "storm-show-all") {
      this._triggerGoogleOnly = false;
      this._triggerShowAll = true;
      this._syncStormTriggerPicker();
    }
  }

  _handleChange(e) {
    const el = e.target;
    if (this._busy) return;
    if (el?.dataset?.field?.startsWith("device-alarm:")) {
      const sub = el.dataset.field.split(":")[1];
      if (sub === "category") {
        this._deviceNewAlarmFilterCategory = el.value || "";
        this._patchDeviceNewAlarmHistBody();
        return;
      }
      if (sub === "severity") {
        this._deviceNewAlarmFilterSeverity = el.value || "";
        this._patchDeviceNewAlarmHistBody();
        return;
      }
      if (sub === "device") {
        this._deviceNewAlarmFilterDevice = el.value || "";
        this._patchDeviceNewAlarmHistBody();
        return;
      }
      if (sub === "range-start") {
        this._deviceNewAlarmHistoryStart = el.value || "";
        this._deviceNewAlarmHistoryRange = "custom";
        this._patchDeviceNewAlarmHistBody();
        return;
      }
      if (sub === "range-end") {
        this._deviceNewAlarmHistoryEnd = el.value || "";
        this._deviceNewAlarmHistoryRange = "custom";
        this._patchDeviceNewAlarmHistBody();
        return;
      }
    }
    if (el?.dataset?.field) {
      const parts = el.dataset.field.split(":");
      if (parts[0] === "solcast" && this._solcastDraft) {
        if (parts[1] === "enabled") {
          this._solcastDraft.enabled = el.checked;
          this._scheduleRender();
          return;
        }
        if (parts[1] === "fetch_pv_forecast") {
          this._solcastDraft.fetch_pv_forecast = el.checked;
          this._scheduleRender();
          return;
        }
      }
      if (parts[0] === "smart-charge" && this._smartChargeDraft) {
        if (parts[1] === "enabled") {
          this._smartChargeDraft.enabled = el.checked;
          this._scheduleRender();
          return;
        }
      }
      if (parts[0] === "octopus" && this._octopusDraft) {
        if (parts[1] === "enabled") {
          this._octopusDraft.enabled = el.checked;
          if (this._octopusDraft.enabled && !this._octopusDraft.provider) {
            this._octopusDraft.provider = "octopus";
          }
          this._scheduleRender();
          return;
        }
        if (parts[1] === "source") {
          this._octopusDraft.source = el.value === "entity" ? "entity" : "native";
          this._octopusPickerMountGen += 1;
          this._scheduleRender();
          void this._syncOctopusEntityPickers();
          return;
        }
        if (parts[1] === "import_mpan") {
          this._octopusDraft.import_mpan = el.value || "";
          return;
        }
        if (parts[1] === "export_mpan") {
          this._octopusDraft.export_mpan = el.value || "";
          return;
        }
      }
      if (parts[0] === "glow" && this._glowDraft) {
        const field = parts[1];
        if (field === "enabled" || field === "mqtt_enabled" || field === "api_enabled") {
          this._glowDraft[field] = el.checked;
          this._glowFormDirty = true;
          return;
        }
      }
      if (parts[0] === "tariff" && this._tariffDraft) {
        const kind = parts[1];
        const sub = parts[2];
        if (kind === "currency") {
          this._tariffDraft.currency = normalizeTariffCurrency(el.value);
          this._scheduleRender();
          return;
        }
        if (kind === "import" || kind === "export" || kind === "standing") {
          if (sub === "source") {
            if (kind === "standing") {
              this._tariffDraft.standing_source = el.value === "entity" ? "entity" : "plugin";
            } else {
              this._tariffDraft[`${kind}_source`] = el.value === "entity" ? "entity" : "schedule";
            }
            this._scheduleRender();
            void this._syncTariffEntityPickers();
            return;
          }
        }
        if (kind === "schedule" && sub === "band") {
          const bandIdx = parseInt(parts[3], 10);
          const field = parts[4];
          if (!this._tariffDraft?.schedule || Number.isNaN(bandIdx) || bandIdx < 0 || bandIdx > 3) return;
          if (field === "import" || field === "export") {
            const currency = normalizeTariffCurrency(this._tariffDraft.currency);
            this._tariffDraft.schedule.bands[bandIdx][`${field}_p_per_kwh`] = majorToMinor(
              parseTariffRate(el.value),
              currency
            );
          }
          return;
        }
      }
      if (parts[0] === "pv" && ["tilt", "azimuth", "panel_count", "watts_per_panel"].includes(parts[2])) {
        this._rangeDrag = false;
        this._scheduleRender(true);
        return;
      }
    }
    if (!el?.dataset?.action) return;
    if (el.dataset.action === "toggle-storm-trigger") {
      if (!this._stormDraft) return;
      const entityId = el.dataset.entity;
      if (!entityId) return;
      const list = this._stormDraft.trigger_entities;
      if (el.checked) {
        if (!list.includes(entityId)) list.push(entityId);
      } else {
        this._stormDraft.trigger_entities = list.filter((id) => id !== entityId);
      }
      this._syncStormTriggerPicker();
      return;
    }
    if (el.dataset.action === "toggle-storm-enabled") {
      if (!this._stormDraft) this._initStormDraft();
      this._stormDraft.enabled = el.checked;
      if (el.checked) this._applyStormEnableDefaults();
      this._scheduleRender();
      return;
    }
    if (el.dataset.action === "toggle-storm-category") {
      if (!this._stormDraft) this._initStormDraft();
      const categoryId = el.dataset.category;
      if (!categoryId) return;
      const row = this._getStormWeatherCategoryCatalog().find((c) => c.id === categoryId);
      if (row && row.supported === false) return;
      const catalogIds = this._getStormWeatherCategoryCatalog()
        .filter((c) => c.supported !== false)
        .map((row) => row.id);
      let list = this._stormDraft.storm_weather_categories ?? [...catalogIds];
      if (el.checked) {
        if (!list.includes(categoryId)) list.push(categoryId);
      } else {
        list = list.filter((id) => id !== categoryId);
      }
      this._stormDraft.storm_weather_categories = list;
    }
  }

  _handleInput(e) {
    const el = e.target;
    if (el?.dataset?.action === "pick-google-weather-entry") {
      if (!this._stormDraft) return;
      this._applyGoogleWeatherEntry(el.value || null);
      this._scheduleRender();
      return;
    }
    if (el?.dataset?.action === "pick-plant") {
      const id = el.value;
      if (!id || id === this._selectedPlantId) return;
      this._selectedPlantId = id;
      this._plantState = undefined;
      this._energyChart = null;
      this._energyChartPlantId = undefined;
      this._statisticsChart = null;
      this._statisticsChartPlantId = undefined;
      this._energyPeriodOffset = 0;
      this._energyBreakdown = null;
      this._analysisSummarySpark = null;
      this._analysisSummarySparkKey = undefined;
      this._batterySocChart = null;
      this._batterySocChartPlantId = undefined;
      this._hourlyWeather = null;
      this._hourlyWeatherPlantId = undefined;
      this._settingsView = "main";
      this._deviceSub = "main";
      this._view = "overview";
      void this._refreshPlantState();
      this._render();
      return;
    }
    if (el?.dataset?.action === "storm-trigger-filter") {
      this._triggerFilter = el.value;
      if (this._triggerFilterTimer) window.clearTimeout(this._triggerFilterTimer);
      this._triggerFilterTimer = window.setTimeout(() => {
        this._triggerFilterTimer = undefined;
        this._syncStormTriggerPicker();
      }, 120);
      return;
    }
    if (!el?.dataset?.field) return;
    const parts = el.dataset.field.split(":");
    const kind = parts[0];
    if (kind === "smart-period" && this._smartChargeDraft) {
      const i = parseInt(parts[1], 10);
      const field = parts[2];
      if (el.type === "checkbox") {
        this._smartChargeDraft.charge_periods[i][field] = el.checked;
      } else {
        this._smartChargeDraft.charge_periods[i][field] = el.value;
      }
      return;
    }
    if (kind === "storm-period" && this._stormDraft) {
      const i = parseInt(parts[1], 10);
      const field = parts[2];
      if (el.type === "checkbox") {
        this._stormDraft.charge_periods[i][field] = el.checked;
      } else {
        this._stormDraft.charge_periods[i][field] = el.value;
      }
      return;
    }
    if (kind === "storm-max-soc" && this._stormDraft) {
      const raw = String(el.value).trim();
      this._stormDraft.target_max_soc = raw === "" ? null : Math.max(10, Math.min(100, parseFloat(raw) || 100));
      return;
    }
    if (kind === "storm-lead-hours" && this._stormDraft) {
      const n = parseInt(String(el.value).trim(), 10);
      this._stormDraft.forecast_lead_hours = Math.max(1, Math.min(48, Number.isFinite(n) ? n : 4));
      return;
    }
    if (kind === "toggle-storm-forecast" && this._stormDraft) {
      this._stormDraft.use_forecast_lead = el.checked;
      this._scheduleRender();
      return;
    }
    if (kind === "toggle-storm-solcast" && this._stormDraft) {
      this._stormDraft.use_solcast_grid_limit = el.checked;
      this._scheduleRender();
      return;
    }
    if (kind === "storm-solcast-margin" && this._stormDraft) {
      const n = parseFloat(String(el.value).trim());
      this._stormDraft.solcast_safety_margin = Math.max(1, Math.min(3, Number.isFinite(n) ? n : DEFAULT_STORM_SOLCAST_MARGIN));
      return;
    }
    if (kind === "storm-solcast-min-soc" && this._stormDraft) {
      const n = parseFloat(String(el.value).trim());
      this._stormDraft.solcast_min_soc_floor = Math.max(10, Math.min(100, Number.isFinite(n) ? n : DEFAULT_STORM_SOLCAST_MIN_SOC));
      return;
    }
    if (kind === "smart-charge" && this._smartChargeDraft) {
      const field = parts[1];
      if (field === "enabled") {
        this._smartChargeDraft.enabled = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "target_soc") {
        this._smartChargeDraft.target_soc = Math.max(10, Math.min(100, parseFloat(el.value) || 100));
        return;
      }
      if (field === "target_max_soc") {
        const raw = String(el.value).trim();
        this._smartChargeDraft.target_max_soc = raw === "" ? null : Math.max(10, Math.min(100, parseFloat(raw) || 100));
        return;
      }
      if (field === "min_deficit_kwh") {
        this._smartChargeDraft.min_deficit_kwh = Math.max(0, parseFloat(el.value) || 0.5);
        return;
      }
      if (field === "solar_safety_margin") {
        this._smartChargeDraft.solar_safety_margin = Math.max(1, Math.min(3, parseFloat(el.value) || 1.15));
        return;
      }
      if (field === "round_trip_efficiency") {
        this._smartChargeDraft.round_trip_efficiency = Math.max(0.5, Math.min(1, parseFloat(el.value) || 0.9));
        return;
      }
      if (field === "min_arbitrage_p_per_kwh") {
        this._smartChargeDraft.min_arbitrage_p_per_kwh = Math.max(0, parseFloat(el.value) || 0.5);
        return;
      }
      if (field === "operating_mode") {
        this._smartChargeDraft.operating_mode = el.value || "max_safety";
        this._scheduleRender();
        return;
      }
      if (field === "max_target_soc") {
        this._smartChargeDraft.max_target_soc = Math.max(10, Math.min(100, parseFloat(el.value) || 100));
        return;
      }
      if (field === "agile_poll_interval_minutes") {
        this._smartChargeDraft.agile_poll_interval_minutes = Math.max(5, Math.min(60, parseInt(el.value, 10) || 15));
        return;
      }
      if (field === "negative_import_interrupt") {
        this._smartChargeDraft.negative_import_interrupt = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "price_drop_interrupt_p_per_kwh") {
        this._smartChargeDraft.price_drop_interrupt_p_per_kwh = Math.max(0, parseFloat(el.value) || 2);
        return;
      }
      if (field === "daily_plan_time") {
        this._smartChargeDraft.daily_plan_time = el.value || "16:00";
        return;
      }
      if (field === "daily_plan_horizon_hours") {
        this._smartChargeDraft.daily_plan_horizon_hours = Math.max(1, Math.min(48, parseInt(el.value, 10) || 24));
        return;
      }
      if (field === "house_load_kw_fallback") {
        this._smartChargeDraft.house_load_kw_fallback = Math.max(0.1, parseFloat(el.value) || 1);
        return;
      }
      if (field === "dark_hours_estimate") {
        this._smartChargeDraft.dark_hours_estimate = Math.max(0, Math.min(24, parseFloat(el.value) || 8));
        return;
      }
      if (field === "outage_reserve_load_kw") {
        const raw = String(el.value).trim();
        this._smartChargeDraft.outage_reserve_load_kw = raw === "" ? null : Math.max(0, parseFloat(raw) || 0);
        return;
      }
      if (field === "outage_reserve_hours") {
        this._smartChargeDraft.outage_reserve_hours = Math.max(0, Math.min(24, parseFloat(el.value) || 3));
        return;
      }
      if (field === "outage_reserve_margin") {
        this._smartChargeDraft.outage_reserve_margin = Math.max(1, Math.min(5, parseFloat(el.value) || 1.2));
        return;
      }
      if (field === "safety_reserve_multiplier") {
        this._smartChargeDraft.safety_reserve_multiplier = Math.max(1, Math.min(5, parseFloat(el.value) || 1.5));
        return;
      }
      if (field === "green_carbon_weight") {
        this._smartChargeDraft.green_carbon_weight = Math.max(0, Math.min(1, parseFloat(el.value) || 0.5));
        return;
      }
      if (field === "export_enabled") {
        this._smartChargeDraft.export_enabled = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "export_enabled_safety") {
        this._smartChargeDraft.export_enabled_safety = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "export_enabled_green") {
        this._smartChargeDraft.export_enabled_green = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "min_export_kwh") {
        this._smartChargeDraft.min_export_kwh = Math.max(0.1, parseFloat(el.value) || 0.5);
        return;
      }
      if (field === "min_export_p_profit") {
        this._smartChargeDraft.min_export_p_profit = Math.max(0, parseFloat(el.value) || 12);
        return;
      }
      if (field === "min_export_p_safety") {
        this._smartChargeDraft.min_export_p_safety = Math.max(0, parseFloat(el.value) || 20);
        return;
      }
      if (field === "min_export_p_green") {
        this._smartChargeDraft.min_export_p_green = Math.max(0, parseFloat(el.value) || 25);
        return;
      }
      if (field === "exportable_fraction_profit") {
        this._smartChargeDraft.exportable_fraction_profit = Math.max(0.05, Math.min(1, parseFloat(el.value) || 1));
        return;
      }
      if (field === "exportable_fraction_safety") {
        this._smartChargeDraft.exportable_fraction_safety = Math.max(0.05, Math.min(1, parseFloat(el.value) || 0.35));
        return;
      }
      if (field === "exportable_fraction_green") {
        this._smartChargeDraft.exportable_fraction_green = Math.max(0.05, Math.min(1, parseFloat(el.value) || 0.15));
        return;
      }
      if (field === "spread_optimizer_enabled") {
        this._smartChargeDraft.spread_optimizer_enabled = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "min_spread_profit_p_per_kwh") {
        this._smartChargeDraft.min_spread_profit_p_per_kwh = Math.max(0, parseFloat(el.value) || 3);
        return;
      }
      if (field === "peak_import_avoid_start") {
        this._smartChargeDraft.peak_import_avoid_start = el.value || "16:00";
        return;
      }
      if (field === "peak_import_avoid_end") {
        this._smartChargeDraft.peak_import_avoid_end = el.value || "19:00";
        return;
      }
      if (field === "winter_fill_enabled") {
        this._smartChargeDraft.winter_fill_enabled = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "green_export_spread_multiplier") {
        this._smartChargeDraft.green_export_spread_multiplier = Math.max(1, parseFloat(el.value) || 2);
        return;
      }
      if (field === "cheap_import_p_per_kwh") {
        this._smartChargeDraft.cheap_import_p_per_kwh = Math.max(0, parseFloat(el.value) || 8);
        return;
      }
      if (field === "peak_import_penalty_p_per_kwh") {
        this._smartChargeDraft.peak_import_penalty_p_per_kwh = Math.max(0, parseFloat(el.value) || 5);
        return;
      }
    }
    if (kind === "octopus" && this._octopusDraft) {
      const field = parts[1];
      if (field === "api_key") {
        this._octopusDraft.api_key = el.value;
        return;
      }
      if (field === "account_number") {
        this._octopusDraft.account_number = el.value;
        return;
      }
    }
    if (kind === "solcast" && this._solcastDraft) {
      const field = parts[1];
      if (!field) return;
      if (field === "enabled") {
        this._solcastDraft.enabled = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "fetch_pv_forecast") {
        this._solcastDraft.fetch_pv_forecast = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "auto_update") {
        this._solcastDraft.auto_update = el.value === "all_day" ? "all_day" : "daylight";
        return;
      }
      if (field === "api_limit") {
        const n = parseInt(String(el.value).trim(), 10);
        this._solcastDraft.api_limit = Math.max(1, Math.min(50, Number.isFinite(n) ? n : 10));
        return;
      }
      if (field === "api_key") {
        this._solcastDraft.api_key = el.value;
        return;
      }
      if (field === "latitude" || field === "longitude") {
        this._solcastDraft[field] = el.value;
        return;
      }
      if (field === "installation_date") {
        this._solcastDraft.installation_date = el.value;
        if (this._pvDraft) {
          syncPvDraftEfficiencyFromInstall(this._pvDraft, this._plantState, this._solcastDraft);
        }
        this._scheduleRender();
        return;
      }
      return;
    }
    if (kind === "glow" && this._glowDraft) {
      const field = parts[1];
      if (!field) return;
      if (field === "username") {
        this._glowDraft.username = el.value ?? "";
        this._glowFormDirty = true;
        return;
      }
      if (field === "password") {
        this._glowDraft.password = el.value ?? "";
        this._glowFormDirty = true;
        return;
      }
      if (field === "topic_prefix") {
        this._glowDraft.topic_prefix = el.value ?? "";
        this._glowFormDirty = true;
        return;
      }
      if (field === "device_id") {
        this._glowDraft.device_id = el.value ?? "";
        this._glowFormDirty = true;
        return;
      }
      if (field === "import_resource_id") {
        this._glowDraft.import_resource_id = el.value ?? "";
        this._glowFormDirty = true;
        return;
      }
      if (field === "export_resource_id") {
        this._glowDraft.export_resource_id = el.value ?? "";
        this._glowFormDirty = true;
        return;
      }
      return;
    }
    if (kind === "tariff" && this._tariffDraft) {
      const rateKind = parts[1];
      const sub = parts[2];
      const currency = normalizeTariffCurrency(this._tariffDraft.currency);
      if (rateKind === "schedule" && sub === "band") {
        const bandIdx = parseInt(parts[3], 10);
        const field = parts[4];
        if (!this._tariffDraft.schedule || Number.isNaN(bandIdx) || bandIdx < 0 || bandIdx > 3) return;
        if (field === "import" || field === "export") {
          this._tariffDraft.schedule.bands[bandIdx][`${field}_p_per_kwh`] = majorToMinor(
            parseTariffRate(el.value),
            currency
          );
        }
        return;
      }
      if ((rateKind === "import" || rateKind === "export") && sub === "p") {
        this._tariffDraft[`${rateKind}_p_per_kwh`] = majorToMinor(parseTariffRate(el.value), currency);
        return;
      }
      if (rateKind === "standing" && sub === "p") {
        if (tariffApiLocksStandingCharge(this._plantState?.tariff, this._octopusDraft)) return;
        this._tariffDraft.standing_charge_p_per_day = majorToMinor(parseTariffRate(el.value), currency);
        return;
      }
      if (rateKind === "currency") {
        this._tariffDraft.currency = normalizeTariffCurrency(el.value);
        return;
      }
    }
    if (kind === "pv-meta" && this._pvDraft) {
      const field = parts[1];
      if (field === "annual_degradation_pct") {
        const raw = String(el.value).trim();
        if (raw === "") return;
        const v = parseFloat(raw);
        if (!Number.isFinite(v)) return;
        this._pvDraft.annual_degradation_pct = Math.max(0, Math.min(10, v));
        syncPvDraftEfficiencyFromInstall(this._pvDraft, this._plantState, this._solcastDraft);
        if (e.type === "change") this._scheduleRender();
      }
      return;
    }
    if (kind === "pv" && this._pvDraft) {
      const which = parts[1];
      const field = parts[2];
      const cfg = this._pvDraft[which];
      if (!cfg || !field) return;
      if (el.type === "checkbox") {
        cfg.enabled = el.checked;
        this._scheduleRender();
        return;
      }
      if (field === "panel_count") {
        cfg.panel_count = Math.max(1, Math.min(12, parseInt(el.value, 10) || 1));
      } else if (field === "watts_per_panel") {
        cfg.watts_per_panel = Math.max(100, Math.min(1000, parseInt(el.value, 10) || 450));
      } else if (field === "efficiency_factor") {
        if (pvInstallationDate(this._plantState, this._solcastDraft)) return;
        const raw = String(el.value).trim();
        if (raw === "") return;
        const v = parseFloat(raw);
        if (!Number.isFinite(v)) return;
        cfg.efficiency_factor = Math.max(1, Math.min(100, v));
        if (e.type === "change") this._scheduleRender();
        return;
      } else if (field === "tilt") {
        cfg.tilt = Math.max(0, Math.min(90, parseInt(el.value, 10) || 25));
      } else if (field === "azimuth") {
        cfg.azimuth = Math.max(0, Math.min(359, parseInt(el.value, 10) || 180));
      } else if (field === "installation_cost") {
        const currency = pvConfigCurrency(this._plantState, this._tariffDraft);
        const raw = String(el.value).trim();
        if (raw === "") {
          cfg.installation_cost_minor = 0;
        } else {
          cfg.installation_cost_minor = majorToMinor(parseTariffRate(el.value), currency);
        }
        if (e.type === "change") this._scheduleRender();
        return;
      } else {
        return;
      }
      this._updatePvRangeLabel(el);
      return;
    }
    if (kind === "period" && this._chargeDraft) {
      const i = parseInt(parts[1], 10);
      const field = parts[2];
      if (el.type === "checkbox") {
        this._chargeDraft[i][field] = el.checked;
      } else {
        this._chargeDraft[i][field] = el.value;
      }
      return;
    }
    if (kind === "soc-num" && this._socDraft) {
      const field = parts[1];
      const raw = String(el.value).trim();
      if (raw === "") return;
      const v = parseFloat(raw);
      if (Number.isNaN(v)) return;
      if (e.type === "change" || (v >= SOC_MIN_PCT && v <= 100)) {
        this._socSaveError = null;
        this._socSaveResults = null;
        applySocDrag(this._socDraft, field, v);
        this._updateTripleSocDom();
      }
    }
  }

  _endSocDrag() {
    if (!this._socDrag) return;
    window.removeEventListener("pointermove", this._onSocMove);
    window.removeEventListener("pointerup", this._onSocEnd);
    window.removeEventListener("pointercancel", this._onSocEnd);
    this._socDrag = null;
  }

  _onSocMove(e) {
    if (!this._socDrag || !this._socDraft) return;
    this._socSaveError = null;
    this._socSaveResults = null;
    const rect = this._socDrag.track.getBoundingClientRect();
    const pct = socPctFromTrackPointer(e.clientX, rect, this._socDrag.grabOffset ?? 0);
    applySocDrag(this._socDraft, this._socDrag.thumb, pct);
    this._updateTripleSocDom();
  }

  _onSocEnd() {
    const thumb = this._socDrag?.thumbEl;
    if (thumb) thumb.classList.remove("is-dragging");
    this._endSocDrag();
  }

  _liveBatterySoc(plant) {
    if (!plant || !this._hass) return null;
    const v = stateNumber(this._hass, plant.entity_map?.battery_soc);
    return Number.isFinite(v) ? v : null;
  }

  _socValidationIssues() {
    return validateSocLimits(this._socDraft, this._liveBatterySoc(this._getPlant()));
  }

  _syncSocValidationUi() {
    const validation = this._socValidationIssues();
    const wrap = this._root.querySelector(".triple-soc");
    if (!wrap) return;
    const html = renderSocFeedbackHtml(validation, this._socSaveError, this._socSaveResults);
    wrap.querySelectorAll(".soc-validation, .soc-result-panel").forEach((el) => el.remove());
    if (html) wrap.querySelector(".soc-numeric")?.insertAdjacentHTML("afterend", html);
    const saveBtn = this._root.querySelector('[data-action="save-soc"]');
    if (saveBtn) saveBtn.disabled = Boolean(this._busy || validation.errors.length);
  }

  _bindTripleSoc() {
    const track = this._root.querySelector(".triple-soc-track");
    if (!track) return;
    track.querySelectorAll("[data-soc-thumb]").forEach((thumb) => {
      thumb.addEventListener("pointerdown", (e) => {
        if (this._busy) return;
        e.preventDefault();
        this._socSaveError = null;
        this._socSaveResults = null;
        track.querySelectorAll(".triple-soc-thumb").forEach((t) => t.classList.remove("is-dragging"));
        thumb.classList.add("is-dragging");
        thumb.setPointerCapture(e.pointerId);
        const rect = track.getBoundingClientRect();
        const thumbKey = thumb.dataset.socThumb;
        const currentVal = clampSocDraft(this._socDraft)[thumbKey];
        const pointerPct = rect.width ? ((e.clientX - rect.left) / rect.width) * 100 : currentVal;
        this._socDrag = {
          thumb: thumbKey,
          thumbEl: thumb,
          track,
          grabOffset: currentVal - pointerPct,
        };
        window.addEventListener("pointermove", this._onSocMove);
        window.addEventListener("pointerup", this._onSocEnd);
        window.addEventListener("pointercancel", this._onSocEnd);
      });
    });
  }

  _updateTripleSocDom() {
    const wrap = this._root.querySelector(".triple-soc");
    if (!wrap || !this._socDraft) return;
    const d = clampSocDraft(this._socDraft);
    const min = d.min_soc;
    const mid = d.min_soc_on_grid;
    const max = d.max_soc;
    const zones = wrap.querySelector(".triple-soc-zones");
    if (zones) {
      zones.innerHTML = `
<div class="triple-soc-zone critical" style="width:${min}%"></div>
<div class="triple-soc-zone reserve" style="width:${mid - min}%"></div>
<div class="triple-soc-zone usable" style="width:${max - mid}%"></div>
<div class="triple-soc-zone headroom" style="width:${100 - max}%"></div>`;
    }
    SOC_THUMBS.forEach((t) => {
      const thumb = wrap.querySelector(`[data-soc-thumb="${t.key}"]`);
      const val = d[t.key];
      if (thumb) {
        thumb.style.left = `${val}%`;
        thumb.style.background = t.color;
        thumb.title = `${t.label}: ${val}%`;
      }
      const num = wrap.querySelector(`[data-field="soc-num:${t.key}"]`);
      if (num && document.activeElement !== num) num.value = String(val);
    });
    const summary = wrap.querySelector(".triple-soc-summary");
    if (summary) {
      const live = wrap.querySelector(".triple-soc-battery-pct")?.textContent?.replace("%", "") ?? "0";
      summary.innerHTML =
        min === mid
          ? `<strong>Reserve from</strong> ${min}%<br><strong>Usable to</strong> ${max}% · <strong>Now</strong> ${live}%`
          : `<strong>Reserve band</strong> ${min}% – ${mid}%<br><strong>Usable to</strong> ${max}% · <strong>Now</strong> ${live}%`;
    }
    this._syncSocValidationUi();
  }

  _renderTripleSoc(plant, d, liveSoc) {
    const clamped = clampSocDraft({ ...d });
    const min = clamped.min_soc;
    const mid = clamped.min_soc_on_grid;
    const max = clamped.max_soc;
    const live = Math.max(0, Math.min(100, Math.round(liveSoc ?? 0)));
    const fillMarkup = tripleSocBatteryFillMarkup(live);

    const thumbsHtml = SOC_THUMBS.map(
      (t) =>
        `<button type="button" class="triple-soc-thumb" data-soc-thumb="${t.key}" style="left:${clamped[t.key]}%;background:${t.color}" title="${esc(t.label)}: ${clamped[t.key]}%" aria-label="${esc(t.label)} ${clamped[t.key]}%"></button>`
    ).join("");

    const numericHtml = SOC_THUMBS.map(
      (t) =>
        `<div><label>${esc(t.label)}</label><input type="number" min="${SOC_MIN_PCT}" max="100" step="1" data-field="soc-num:${t.key}" value="${clamped[t.key]}"></div>`
    ).join("");

    return `<div class="triple-soc">
<div class="triple-soc-head">
<div class="triple-soc-battery" aria-hidden="true">
<div class="triple-soc-battery-cap"></div>
${fillMarkup}
<div class="triple-soc-battery-pct">${live}%</div>
</div>
<div class="triple-soc-summary">
${
      min === mid
        ? `<strong>Reserve from</strong> ${min}%<br><strong>Usable to</strong> ${max}% · <strong>Now</strong> ${live}%`
        : `<strong>Reserve band</strong> ${min}% – ${mid}%<br><strong>Usable to</strong> ${max}% · <strong>Now</strong> ${live}%`
    }
</div>
</div>
<div class="triple-soc-track-wrap">
<div class="triple-soc-track">
<div class="triple-soc-zones">
<div class="triple-soc-zone critical" style="width:${min}%"></div>
<div class="triple-soc-zone reserve" style="width:${mid - min}%"></div>
<div class="triple-soc-zone usable" style="width:${max - mid}%"></div>
<div class="triple-soc-zone headroom" style="width:${100 - max}%"></div>
</div>
<div class="triple-soc-live" style="left:${live}%"></div>
${thumbsHtml}
</div>
<div class="triple-soc-scale"><span>${SOC_MIN_PCT}%</span><span>100%</span></div>
</div>
<div class="soc-legend">
<span><i style="background:#e53935"></i> Below off-grid min</span>
<span><i style="background:#f9a825"></i> Off-grid reserve</span>
<span><i style="background:#2e7d32"></i> Normal use</span>
<span><i style="background:var(--fp-accent)"></i> Charge headroom</span>
</div>
<div class="soc-numeric">${numericHtml}</div>
${renderSocFeedbackHtml(validateSocLimits(clamped, live), this._socSaveError, this._socSaveResults)}
<p class="soc-limit-note">Minimum for all three limits is <strong>10%</strong>. Keep <strong>off-grid min ≤ system min ≤ system max</strong>. The inverter may reject limits that conflict with the current battery level — Save will show the error if it does.</p>
</div>`;
  }

  async _runPlantService(service, extra = {}, toastMsg = "Updated") {
    const plant = this._getPlant();
    if (!plant) return;
    this._busy = true;
    this._render();
    try {
      await callService(this._hass, "foxess_plant", service, {
        plant_id: plant.entry_id,
        ...extra,
      });
      await this._refreshPlantState();
      this._showToast(toastMsg);
    } catch (err) {
      this._showToast(err?.message || "Action failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _syncScheduleFromInverter() {
    const plant = this._getPlant();
    if (!plant) return;
    this._busy = true;
    this._render();
    try {
      await callService(this._hass, "foxess_plant", "sync_schedule_from_inverter", {
        plant_id: plant.entry_id,
      });
      await this._refreshPlantState();
      this._initChargeDraft();
      this._showToast("Synced schedule from inverter");
    } catch (err) {
      this._showToast(err?.message || "Sync failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _saveSchedules() {
    const plant = this._getPlant();
    if (!plant || !this._chargeDraft) return;
    this._busy = true;
    this._render();
    try {
      await callService(this._hass, "foxess_plant", "set_charge_periods", {
        plant_id: plant.entry_id,
        charge_periods: this._chargeDraft,
        as_override: false,
      });
      await callService(this._hass, "foxess_plant", "apply_desired", {
        plant_id: plant.entry_id,
      });
      await this._refreshPlantState();
      this._showToast("Charge schedule saved & applied");
    } catch (err) {
      this._showToast(err?.message || "Save failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _saveSoc() {
    const plant = this._getPlant();
    if (!plant || !this._socDraft) return;
    const clamped = clampSocDraft({ ...this._socDraft });
    const validation = validateSocLimits(clamped, this._liveBatterySoc(plant));
    if (validation.errors.length) {
      this._showToast(validation.errors[0], "err");
      return;
    }
    const { min_soc, min_soc_on_grid, max_soc } = clamped;
    this._socDraft = clamped;
    this._socSaveError = null;
    this._socSaveResults = null;
    this._busy = true;
    this._render();
    try {
      const response = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/set_soc_limits",
        plant_id: plant.entry_id,
        min_soc,
        min_soc_on_grid,
        max_soc,
      });
      if (response) {
        const { soc_write_results: socResults, ...plantState } = response;
        this._plantState = plantState;
        this._socSaveResults = Array.isArray(socResults) ? socResults : null;
      }
      await this._refreshPlantState();
      const allOk = !this._socSaveResults?.length || this._socSaveResults.every((row) => row.success);
      if (allOk) {
        this._socSaveError = null;
        this._showToast("SOC limits saved");
      } else {
        const failed = this._socSaveResults.filter((row) => !row.success).map((row) => row.label);
        this._socSaveError = `Save incomplete: ${failed.join(", ")}`;
        this._showToast(this._socSaveError, "err");
      }
    } catch (err) {
      this._socSaveResults = null;
      this._socSaveError = err?.message || "SOC save failed";
      this._render();
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _saveWorkMode() {
    const plant = this._getPlant();
    const entity_id = plant?.entity_map?.work_mode;
    if (!entity_id || !this._workModeDraft) return;
    this._busy = true;
    this._render();
    try {
      await callService(this._hass, "select", "select_option", {
        entity_id,
        option: this._workModeDraft,
      });
      await this._refreshPlantState();
      this._showToast("Work mode updated");
    } catch (err) {
      this._showToast(err?.message || "Work mode failed", "err");
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _renderTabBar(items, activeId, actionName, dataAttr = "view", sub = false) {
    const barClass = sub ? "tab-bar sub" : "tab-bar";
    return `<nav class="${barClass}" role="tablist">${items
      .map(
        (item) =>
          `<button type="button" class="tab ${activeId === item.id ? "active" : ""}" role="tab" aria-selected="${activeId === item.id}" data-action="${actionName}" data-${dataAttr}="${item.id}">${esc(item.label)}</button>`
      )
      .join("")}</nav>`;
  }

  _scheduleSyncButtons() {
    const dis = this._busy ? "disabled" : "";
    return `<div class="btn-row schedule-sync-row">
<button type="button" class="btn btn-secondary" data-action="sync-schedule" ${dis}>Sync from inverter</button>
<button type="button" class="btn btn-primary" data-action="reapply-schedule" ${dis}>Re-apply to inverter</button>
</div>`;
  }

  _modeBannerExtra() {
    const st = this._plantState;
    if (!st) return "";
    if (st.drift) {
      return `<div class="banner warn"><strong>Schedule drift</strong>Inverter charge windows differ from what Fox Plant expects. Sync copies the inverter into your app settings; re-apply pushes your app schedule to the inverter and enables plant control.${this._scheduleSyncButtons()}</div>`;
    }
    if (!st.control_active) {
      return `<div class="banner info"><strong>Manual control</strong>Fox Plant is not managing charge periods. Modbus or the Fox app may change settings freely.</div>`;
    }
    return "";
  }

  _modeBanner() {
    const st = this._plantState;
    if (!st) return "";
    const mode = st.mode ?? "baseline";
    return `<div class="mode-banner-row"><span class="mode-pill ${modeClass(mode)}">${esc(mode)}</span><span class="mode-banner-hint">${st.control_active ? "Plant control active" : "Plant control off"}</span></div>${this._modeBannerExtra()}`;
  }

  _renderOverviewWeather() {
    const wx = this._plantState?.overview_weather;
    if (!wx || (!wx.temperature_display && !wx.condition_label)) return "";
    const icon = googleWeatherIconHtml(this._hass, {
      conditionType: wx.condition_type,
      haCondition: wx.ha_condition,
      iconKey: wx.icon_key,
      isDaytime: wx.is_daytime,
    });
    const temp = wx.temperature_display
      ? `<span class="overview-weather-temp">${esc(wx.temperature_display)}</span>`
      : "";
    const label = wx.condition_label
      ? `<span class="overview-weather-label">${esc(wx.condition_label)}</span>`
      : "";
    const aria = [wx.temperature_display, wx.condition_label].filter(Boolean).join(", ");
    return `<div class="overview-weather" role="img" aria-label="${esc(aria || "Weather")}">${icon}${temp}${label}</div>`;
  }

  _resolveOverviewWeatherEntity() {
    const wx = this._plantState?.overview_weather;
    if (wx?.weather_entity_id) return wx.weather_entity_id;
    const storm = this._plantState?.storm_prep;
    if (storm?.weather_entity_id) return storm.weather_entity_id;
    return null;
  }

  _overviewHourlyWeatherEnabled() {
    return Boolean(this._resolveOverviewWeatherEntity());
  }

  _renderHourlyWeatherCard() {
    if (!this._overviewHourlyWeatherEnabled()) return "";
    if (this._hourlyWeatherLoading) {
      return `<div class="card hourly-weather-card"><p class="chart-loading">Loading hourly forecast…</p></div>`;
    }
    const body = renderHourlyWeatherOverviewHtml(this._hass, this._hourlyWeather);
    return `<div class="card hourly-weather-card">${body}</div>`;
  }

  async _loadHourlyWeather() {
    const plant = this._getPlant();
    const weatherEntityId = this._resolveOverviewWeatherEntity();
    if (!plant || !this._hass || !weatherEntityId) return;
    const plantId = plant.entry_id;
    this._hourlyWeatherLoading = true;
    this._hourlyWeather = null;
    this._hourlyWeatherPlantId = plantId;
    this._scheduleRender();
    try {
      this._hourlyWeather = await fetchHourlyWeatherOverview(
        this._hass,
        weatherEntityId,
        this._plantState?.overview_weather
      );
    } catch (err) {
      this._hourlyWeather = {
        error: err?.message || "Could not load hourly forecast.",
      };
    } finally {
      this._hourlyWeatherLoading = false;
      if (this._getPlant()?.entry_id === plantId) this._scheduleRender();
    }
  }

  _renderOverviewStatusBlock(plant) {
    const st = this._plantState;
    if (!st) return "";
    const systemStatus = foxInverterStateLabel(this._hass, plant, this._plantState);
    const workMode = foxWorkModeLabel(this._hass, plant, this._plantState);
    const plantMode = st.mode ?? "baseline";
    const statusPart =
      systemStatus !== "—"
        ? wrapFoxInverterStatePillLink(
            systemStatus,
            formatFoxOverviewStatusPill(systemStatus),
            { fromOverview: true }
          )
        : "";
    const workPart = workMode !== "—" ? formatFoxOverviewWorkModePill(workMode) : "";
    return `<div class="overview-status-block">
<div class="overview-status-row">
${statusPart}
${workPart}
${formatFoxOverviewPlantModePill(plantMode)}
<span class="overview-control-hint">${st.control_active ? "Plant control active" : "Plant control off"}</span>
</div>
${this._renderOverviewWeather()}
${this._modeBannerExtra()}
</div>`;
  }

  _renderFlowBackdropMarkup(ctx) {
    return `<img class="fox-flow-layer fox-flow-layer-backdrop" src="${esc(flowSceneLayerUrl("backdrop", ctx.bgTheme, ctx.overlayTheme))}" alt="" loading="eager" decoding="async" fetchpriority="high" />`;
  }

  _renderEnergyScene(plant) {
    const ctx = this._flowSceneContext(plant);
    const pathsHtml = renderFlowScenePaths({
      lines: ctx.lines,
      activeIds: ctx.activeIds,
      gridExporting: ctx.gridExporting,
      isNight: ctx.isNight,
    });
    const haClass = ctx.haUiDark ? "fox-flow-scene--ha-dark" : "fox-flow-scene--ha-light";
    const skyClass = ctx.bgTheme === "day_light" ? " fox-flow-scene--light-sky" : "";
    return `<div class="scene-card scene-card--fox-flow">
<div class="fox-flow-scene ${ctx.isNight ? "fox-flow-scene--night" : "fox-flow-scene--day"} ${haClass}${skyClass}" role="img" aria-label="Live energy flow" data-panel-build="${esc(this._panelBuild())}">
<div class="fox-flow-stage">
${this._renderFlowBackdropMarkup(ctx)}
<img class="fox-flow-layer fox-flow-layer-pv" src="${esc(flowSceneLayerUrl("pv", ctx.bgTheme, ctx.overlayTheme))}" alt="" loading="lazy" decoding="async" />
<img class="fox-flow-layer fox-flow-layer-aio" src="${esc(flowSceneLayerUrl("aio", ctx.bgTheme, ctx.overlayTheme))}" alt="" loading="lazy" decoding="async" />
<svg class="fox-flow-svg" viewBox="0 0 1024 1017" preserveAspectRatio="xMidYMid meet" aria-hidden="true" data-flow-paths-ver="${esc(this._panel?.config?.flow_paths_ver || FLOW_PATHS_VER)}" data-flow-pipe-day="${FLOW_PIPE_STROKE.day}" data-flow-stroke-base="${FLOW_STROKE.base}" data-flow-stroke-active="${FLOW_STROKE.hubActive}" data-hub-r="${FLOW_STROKE.hubR}" data-hub-home="${esc(FOX_FLOW_PATHS["hub-home"])}" data-aio-hub="${esc(FOX_FLOW_PATHS["aio-hub"])}">
${pathsHtml}
<circle class="flow-hub-dot ${ctx.hubActive ? "active" : ""}" cx="${FOX_FLOW_HUB.x}" cy="${FOX_FLOW_HUB.y}" r="${FLOW_STROKE.hubR}" fill="${ctx.hubActive ? FLOW_ACTIVE_STROKE.battery : flowPipeStroke(ctx.isNight)}"/>
</svg>
<div class="fox-flow-badge fox-flow-badge-solar">
<span class="fox-flow-badge-label">Solar</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(ctx.flows.pvW))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-grid">
<span class="fox-flow-badge-label">${esc(ctx.gridLabel)}</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(ctx.gridPower))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-battery">
<span class="fox-flow-badge-label">${esc(ctx.batteryStatus)}</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(ctx.batteryPower))} | ${esc(formatPercent(ctx.soc))}</span>
</div>
<div class="fox-flow-badge fox-flow-badge-home">
<span class="fox-flow-badge-label">Home</span>
<span class="fox-flow-badge-value">${esc(formatFoxPower(ctx.flows.loadW))}</span>
</div>
</div>
</div>
</div>`;
  }

  _flowSceneContext(plant) {
    const flows = readEnergyFlows(this._hass, plant, this._plantState);
    const lines = computeFlowLines(flows);
    const activeIds = new Set(lines.map((l) => l.id));
    const bgTheme = resolveFlowSceneBgTheme(this._hass, this._plantState);
    const overlayTheme = flowSceneOverlayTheme(bgTheme);
    const haUiDark = resolveHaUiDark(this._hass);
    const isNight = !bgTheme.startsWith("day_");
    const soc = Math.min(100, Math.max(0, flows.batterySoc));
    const gridExporting =
      flows.gridExportW > flows.gridImportW && flows.gridExportW > FLOW_SCENE_PV_THRESHOLD_W;
    return {
      flows,
      lines,
      activeIds,
      bgTheme,
      overlayTheme,
      haUiDark,
      isNight,
      soc,
      gridExporting,
      gridLabel: gridExporting ? "To Grid" : "On Grid",
      gridPower: gridExporting ? flows.gridExportW : flows.gridImportW,
      batteryStatus: String(flows.batteryStatus || "Idle").toUpperCase(),
      batteryPower: Math.abs(flows.batteryW),
      hubActive: lines.some((l) => l.id.includes("hub")),
      key: flowSceneStructureKey(lines, gridExporting, isNight, bgTheme, haUiDark),
    };
  }

  /** Require two matching updates before rebuilding flow pipes (avoids threshold flicker). */
  _stableFlowSceneKey(nextKey) {
    if (this._flowSceneKey == null) {
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      return nextKey;
    }
    if (nextKey === this._flowSceneKey) {
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      return this._flowSceneKey;
    }
    if (nextKey === this._flowSceneKeyPending) {
      this._flowSceneKeyPendingN += 1;
    } else {
      this._flowSceneKeyPending = nextKey;
      this._flowSceneKeyPendingN = 1;
    }
    if (this._flowSceneKeyPendingN >= 2) {
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      return nextKey;
    }
    return this._flowSceneKey;
  }

  _patchFlowBadges(stage, ctx) {
    const set = (sel, text) => {
      const el = stage.querySelector(sel);
      if (el) el.textContent = text;
    };
    set(".fox-flow-badge-solar .fox-flow-badge-value", formatFoxPower(ctx.flows.pvW));
    set(".fox-flow-badge-grid .fox-flow-badge-label", ctx.gridLabel);
    set(".fox-flow-badge-grid .fox-flow-badge-value", formatFoxPower(ctx.gridPower));
    set(".fox-flow-badge-battery .fox-flow-badge-label", ctx.batteryStatus);
    set(
      ".fox-flow-badge-battery .fox-flow-badge-value",
      `${formatFoxPower(ctx.batteryPower)} | ${formatPercent(ctx.soc)}`
    );
    set(".fox-flow-badge-home .fox-flow-badge-value", formatFoxPower(ctx.flows.loadW));
  }

  _renderOverviewHeader(plant) {
    const modelLine = plantModelSubtitle(this._hass, plant, this._plantState);
    return `<header class="header overview-header"><h1>${esc(plant.title)}</h1>${modelLine !== "—" ? `<p class="overview-model">${esc(modelLine)}</p>` : ""}${this._renderOverviewStatusBlock(plant)}</header>`;
  }

  _renderOverviewAfterHero(plant) {
    const forecastSlot = this._forecastAccuracyForOverview();
    const forecastCard =
      statisticsSolcastForecastEnabled(this._plantState, this._hass)
        ? renderForecastAccuracyCard(forecastSlot.report, {
            compact: true,
            loading: forecastSlot.loading,
          })
        : "";
    const greenerPayload = octopusGreenerPayload(this._plantState);
    const octopusGreenerCard = octopusTariffEnabled(this._plantState)
      ? renderOctopusGreenerNightsCard(greenerPayload, {
          compact: true,
          view: this._octopusGreenerView,
        })
      : "";
    const octopusRewardsCard = octopusTariffEnabled(this._plantState)
      ? renderOctopusRewardsCard(greenerPayload, { compact: true })
      : "";
    return `${forecastCard}<div class="card statistics-card" style="margin-top:14px">
<p class="card-title">Statistics</p>
${this._renderStatisticsChartBody()}
</div>
<div class="card soc-chart-card" style="margin-top:14px">
<p class="card-title">Battery SOC</p>
${this._renderBatterySocChartBody(plant)}
</div>
${octopusGreenerCard}${octopusRewardsCard}
${this._renderImpactPanel()}`;
  }

  _overviewHourlyWeatherSlotKey() {
    if (!this._overviewHourlyWeatherEnabled()) return "";
    if (this._hourlyWeatherLoading) return "loading";
    if (!this._hourlyWeather) return "pending";
    const data = this._hourlyWeather;
    if (data.error) return `err:${data.error}`;
    if (data.empty) return `empty:${data.empty}`;
    const slots = data.slots || [];
    return `ok:${slots.map((s) => s.t).join(",")}`;
  }

  _ensureOverviewHeroLayout(mainEl) {
    const heroRow = mainEl?.querySelector?.(".overview-hero-row");
    if (!heroRow || heroRow.dataset.overviewHeroLayout === "4") return;
    const sceneSlot = heroRow.querySelector(".overview-hero-scene-slot");
    let sceneHtml = sceneSlot?.innerHTML || "";
    if (!sceneHtml) {
      const sceneEl = heroRow.querySelector(".overview-hero-scene");
      if (sceneEl) {
        const scratch = document.createElement("div");
        scratch.innerHTML = sceneEl.innerHTML;
        scratch.querySelector(
          ".overview-status-row, .overview-system-status-slot, .overview-automation-status-slot, .overview-system-status-card, .overview-automation-status-card"
        )?.remove();
        sceneHtml = scratch.innerHTML.trim();
      }
    }
    const chartsEl =
      heroRow.querySelector(".overview-hero-daily .overview-hero-daily-charts") ||
      heroRow.querySelector(".overview-hero-daily-charts");
    const chartsHtml = chartsEl?.innerHTML || "";
    const automationEl = heroRow.querySelector(".overview-automation-status-slot");
    const automationHtml = automationEl?.innerHTML || "";
    heroRow.innerHTML = `<div class="overview-hero-scene">
<div class="overview-hero-scene-slot">${sceneHtml}</div>
<div class="overview-system-status-slot"></div>
</div>
<div class="overview-hero-daily-slot">
<div class="overview-hero-daily-charts">${chartsHtml}</div>
<div class="overview-automation-status-slot">${automationHtml}</div>
</div>`;
    heroRow.dataset.overviewHeroLayout = "4";
    this._overviewDailySlotCache = undefined;
    this._overviewSystemStatusSlotCache = undefined;
    this._overviewAutomationStatusSlotCache = undefined;
  }

  _patchOverviewHourlyWeatherSlot(mainEl) {
    const slot = mainEl.querySelector(".overview-hourly-weather-slot");
    if (!slot) return;
    const key = this._overviewHourlyWeatherSlotKey();
    if (key === this._overviewHourlyWeatherSlotCache) return;
    const prevCard = slot.querySelector("[data-hourly-weather]");
    const scrollLeft = prevCard?.dataset?.scrollLeft
      ? Number(prevCard.dataset.scrollLeft)
      : slot.querySelector(".hourly-weather-scroll")?.scrollLeft ?? 0;
    slot.innerHTML = this._renderHourlyWeatherCard();
    this._overviewHourlyWeatherSlotCache = key;
    const scroller = slot.querySelector(".hourly-weather-scroll");
    if (scroller && scrollLeft > 0) scroller.scrollLeft = scrollLeft;
    bindHourlyWeatherOverview(mainEl);
  }

  /** Refresh overview without disconnecting the flow scene (CSS animations keep running). */
  _renderOverviewMain(mainEl, plant) {
    const ctx = this._flowSceneContext(plant);
    if (this._flowScenePlantId !== plant.entry_id) {
      this._flowSceneKey = undefined;
      this._flowScenePlantId = plant.entry_id;
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      this._overviewDailySlotCache = undefined;
      this._overviewSystemStatusSlotCache = undefined;
      this._overviewAutomationStatusSlotCache = undefined;
      this._overviewHourlyWeatherSlotCache = undefined;
      this._overviewBreakdownSlotCache = undefined;
      this._overviewSummarySlotCache = undefined;
      this._overviewEnergyBandCache = undefined;
    }
    const stableKey = this._stableFlowSceneKey(ctx.key);
    const rebuildFlow = stableKey !== this._flowSceneKey;

    if (!mainEl.querySelector(".overview-root")) {
      mainEl.innerHTML = `<div class="overview-root">
<div class="overview-chrome"></div>
<div class="overview-hero-row" data-overview-hero-layout="4">
<div class="overview-hero-scene">
<div class="overview-hero-scene-slot"></div>
<div class="overview-system-status-slot"></div>
</div>
<div class="overview-hero-daily-slot">
<div class="overview-hero-daily-charts"></div>
<div class="overview-automation-status-slot"></div>
</div>
</div>
<div class="overview-energy-band-slot"></div>
<div class="overview-hourly-weather-slot"></div>
<div class="overview-after-hero"></div>
</div>`;
    }
    this._ensureOverviewHeroLayout(mainEl);

    mainEl.querySelector(".overview-chrome").innerHTML =
      this._renderOverviewHeader(plant) + this._renderPanelStaleBanner();
    const dailyKey = this._overviewDailySlotKey();
    const statusKey = this._overviewSystemStatusSlotKey();
    if (statusKey !== this._overviewSystemStatusSlotCache) {
      const statusSlot = mainEl.querySelector(".overview-system-status-slot");
      if (statusSlot) {
        statusSlot.innerHTML = this._renderOverviewSystemStatusCard();
        this._overviewSystemStatusSlotCache = statusKey;
      }
    }
    const automationKey = this._overviewAutomationStatusSlotKey();
    if (automationKey !== this._overviewAutomationStatusSlotCache) {
      const automationSlot = mainEl.querySelector(".overview-automation-status-slot");
      if (automationSlot) {
        automationSlot.innerHTML = this._renderOverviewAutomationStatusCard();
        this._overviewAutomationStatusSlotCache = automationKey;
      }
    }
    const chartsSlot = mainEl.querySelector(".overview-hero-daily-charts");
    if (chartsSlot && dailyKey !== this._overviewDailySlotCache) {
      chartsSlot.innerHTML = this._renderOverviewDailyCharts();
      this._overviewDailySlotCache = dailyKey;
      bindOverviewDailyCharts(mainEl.querySelector(".overview-hero-daily-slot"));
    }
    const breakdownKey = this._overviewEnergyBandKey(plant);
    const energyBandSlot = mainEl.querySelector(".overview-energy-band-slot");
    if (energyBandSlot && breakdownKey !== this._overviewEnergyBandCache) {
      energyBandSlot.innerHTML = this._renderOverviewEnergyBand(plant);
      this._overviewEnergyBandCache = breakdownKey;
      this._overviewBreakdownSlotCache = breakdownKey;
      this._overviewSummarySlotCache = breakdownKey;
    }
    this._patchOverviewHourlyWeatherSlot(mainEl);
    mainEl.querySelector(".overview-after-hero").innerHTML = this._renderOverviewAfterHero(plant);

    const sceneSlot = mainEl.querySelector(".overview-hero-scene-slot");
    if (rebuildFlow || !sceneSlot?.querySelector(".fox-flow-stage")) {
      if (sceneSlot) sceneSlot.innerHTML = this._renderEnergyScene(plant);
      this._flowSceneKey = stableKey;
    } else {
      const stage = sceneSlot.querySelector(".fox-flow-stage");
      if (stage) this._patchFlowBadges(stage, ctx);
    }
  }

  _renderStormHero(armed) {
    return `<div class="fp-banner-hero fp-banner-hero--wide">
<img src="${esc(STORM_HERO_IMAGE_STATIC)}" width="${STORM_HERO_WIDTH}" height="${STORM_HERO_HEIGHT}" alt="StormSafe: home battery backup during a storm" loading="eager" decoding="async" />
</div>`;
  }

  _renderSmartChargeHero() {
    return `<div class="fp-banner-hero fp-banner-hero--wide">
<img src="${esc(SMART_CHARGE_HERO_IMAGE_STATIC)}" width="${SMART_CHARGE_HERO_WIDTH}" height="${SMART_CHARGE_HERO_HEIGHT}" alt="SmartCharge: Fox home battery charging from solar and off-peak grid" loading="eager" decoding="async" />
</div>`;
  }

  _stat(label, value, suffix = "") {
    const has = value != null && value !== "—" && !(typeof value === "number" && !Number.isFinite(value));
    const show = has ? esc(String(value)) + esc(suffix) : "—";
    return `<div class="stat"><label>${esc(label)}</label><strong>${show}</strong></div>`;
  }

  _renderImpactPanel() {
    const imp = this._plantState?.impact ?? {};
    if (imp.co2_kg == null && imp.trees_planted == null && imp.oil_litres == null) {
      return `<div class="card impact-card" style="margin-top:14px">
<p class="card-title">Impact</p>
<p class="placeholder impact-placeholder">Lifetime yield not available yet. Reload FoxESS Plant after foxess_modbus exposes <code>total_yield_total</code> (Yield Total).</p>
</div>`;
    }
    const items = [
      {
        label: "CO₂ reduction",
        value: imp.co2_kg,
        unit: "kg",
        icon: "co2",
      },
      {
        label: "Trees planted",
        value: imp.trees_planted,
        unit: "",
        icon: "tree",
      },
      {
        label: "Oil saved",
        value: imp.oil_litres,
        unit: "L",
        icon: "oil",
      },
    ];
    const grid = items
      .map((item) => {
        const has = item.value != null;
        const display = has
          ? `${Number(item.value).toFixed(1)}${item.unit ? `<span class="impact-unit">${esc(item.unit)}</span>` : ""}`
          : "—";
        return `<div class="impact-metric">
<img class="impact-icon" src="${esc(impactIconUrl(item.icon))}" alt="" loading="lazy" decoding="async" />
<div class="impact-value">${display}</div>
<div class="impact-label">${esc(item.label)}</div>
</div>`;
      })
      .join("");
    const basisKwh = imp.impact_basis_kwh ?? imp.solar_kwh_total;
    const basis =
      basisKwh != null
        ? `<p class="impact-basis">Based on ${Number(basisKwh).toFixed(1)} kWh lifetime yield</p>`
        : "";
    return `<div class="card impact-card" style="margin-top:14px">
<p class="card-title">Impact</p>
<div class="impact-grid">${grid}</div>
${basis}
</div>`;
  }

  _renderOverviewDailyCard(title, values, labels, accentColor, analyticsFallback) {
    const todayVal = values?.[values.length - 1];
    const display =
      todayVal != null && Number.isFinite(todayVal) && todayVal > 0
        ? todayVal
        : analyticsFallback != null && Number.isFinite(Number(analyticsFallback))
          ? Number(analyticsFallback)
          : todayVal;
    const chart =
      values?.length && labels?.length
        ? renderOverviewDailySparklineSvg(values, labels, accentColor)
        : "";
    return `<button type="button" class="overview-daily-card" data-action="nav" data-view="energy_analysis" aria-label="${esc(title)}">
<div class="overview-daily-head"><span class="overview-daily-title">${esc(title)}</span><span class="overview-daily-chev" aria-hidden="true">›</span></div>
<div class="overview-daily-value">${esc(formatDailyKwh(display))}</div>
${chart}
</button>`;
  }

  _overviewDailySlotKey() {
    if (this._overviewDailyLoading) return "loading";
    const data = this._overviewDaily;
    if (data?.error) return `err:${data.error}`;
    if (!data?.labels?.length) return "empty";
    const a = this._plantState?.analytics ?? {};
    const dates = data.labels.map((d) => d.getTime()).join(",");
    const prod = (data.production || []).join(",");
    const cons = (data.consumption || []).join(",");
    return `${dates}|${prod}|${cons}|${a.pv_production_kwh_today ?? ""}|${a.load_consumption_kwh_today ?? ""}`;
  }

  _overviewSystemStatusSlotKey() {
    if (this._overviewSystemStatusLoading) return "loading";
    const data = this._overviewSystemStatus;
    if (!data) return "pending";
    if (data.error) return `err:${data.error}`;
    return `ok:${data.faultCount ?? 0}`;
  }

  _overviewAutomationStatusSlotKey() {
    const st = this._plantState;
    if (!st) return "pending";
    const storm = st.storm_prep ?? {};
    const sc = st.smart_charge ?? {};
    return [
      storm.enabled,
      storm.condition_active,
      storm.forecast_active,
      (st.active_storm_triggers ?? []).join(","),
      st.mode,
      st.override_active,
      st.forecast_armed,
      storm.solcast_precheck?.action,
      sc.enabled,
      sc.armed,
      sc.decision?.reason,
    ].join("|");
  }

  _renderOverviewAutomationStatusCard() {
    return renderOverviewAutomationStatusCard(this._plantState ?? {});
  }

  _renderOverviewSystemStatusCard() {
    if (this._overviewSystemStatusLoading) {
      return renderOverviewSystemStatusCard({ loading: true });
    }
    const data = this._overviewSystemStatus;
    if (!data) {
      return renderOverviewSystemStatusCard({ loading: true });
    }
    if (data.error) {
      return renderOverviewSystemStatusCard({ error: data.error, faultCount: null });
    }
    return renderOverviewSystemStatusCard({ faultCount: data.faultCount ?? 0 });
  }

  _renderOverviewDailyCharts() {
    if (this._overviewDailyLoading) {
      return `<div class="overview-daily-loading">Loading daily energy…</div>`;
    }
    const data = this._overviewDaily;
    if (data?.error) {
      return `<div class="overview-daily-card"><p class="overview-daily-empty">${esc(data.error)}</p></div>`;
    }
    if (!data?.labels?.length) {
      return "";
    }
    const a = this._plantState?.analytics ?? {};
    return `${this._renderOverviewDailyCard(
      "Daily Production",
      data.production,
      data.labels,
      OVERVIEW_DAILY_COLORS.production,
      a.pv_production_kwh_today
    )}${this._renderOverviewDailyCard(
      "Daily Consumption",
      data.consumption,
      data.labels,
      OVERVIEW_DAILY_COLORS.consumption,
      a.load_consumption_kwh_today
    )}`;
  }

  _renderOverviewHeroDailyColumn() {
    return `<div class="overview-hero-daily-slot">
<div class="overview-hero-daily-charts">${this._renderOverviewDailyCharts()}</div>
<div class="overview-automation-status-slot">${this._renderOverviewAutomationStatusCard()}</div>
</div>`;
  }

  async _loadOverviewSystemStatus({ force = false } = {}) {
    const plant = this._getPlant();
    if (!plant || !this._hass || this._view !== "overview") return;
    const plantId = plant.entry_id;
    if (!force && this._overviewSystemStatusPlantId === plantId && this._overviewSystemStatus) return;
    if (this._overviewSystemStatusInflight === plantId) return;
    this._overviewSystemStatusInflight = plantId;
    this._overviewSystemStatusLoading = true;
    this._overviewSystemStatusSlotCache = undefined;
    this._overviewAutomationStatusSlotCache = undefined;
    this._scheduleRender();
    try {
      if (!this._plantState) await this._refreshPlantState();
      const data = await fetchDeviceAlarmDashboard(this._hass, plant, this._plantState);
      if (this._view !== "overview" || this._getPlant()?.entry_id !== plantId) return;
      const faultCount = countOverviewFaultsLast24h(data);
      if (faultCount == null) {
        this._overviewSystemStatus = { error: data.error || "System status unavailable.", faultCount: null };
      } else {
        this._overviewSystemStatus = { faultCount, fetchedAt: Date.now() };
      }
      this._overviewSystemStatusPlantId = plantId;
    } catch (err) {
      if (this._view !== "overview" || this._getPlant()?.entry_id !== plantId) return;
      this._overviewSystemStatus = {
        error: err?.message || "Could not load system status.",
        faultCount: null,
      };
      this._overviewSystemStatusPlantId = plantId;
    } finally {
      if (this._overviewSystemStatusInflight === plantId) this._overviewSystemStatusInflight = undefined;
      this._overviewSystemStatusLoading = false;
      if (this._view === "overview" && this._getPlant()?.entry_id === plantId) {
        this._overviewSystemStatusSlotCache = undefined;
    this._overviewAutomationStatusSlotCache = undefined;
        this._scheduleRender();
      }
    }
  }

  async _loadOverviewDailyCards() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const plantId = plant.entry_id;
    this._overviewDailyLoading = true;
    this._overviewDaily = null;
    this._analysisTariffDaily = null;
    this._overviewDailyPlantId = plantId;
    this._scheduleRender();
    try {
      if (!this._plantState) await this._refreshPlantState();
      const overview = await fetchOverviewDailyEnergy(this._hass, plant, this._plantState);
      this._overviewDaily = overview;
      this._analysisTariffDaily = await fetchAnalysisTariffIntraday(
        this._hass,
        plant,
        this._plantState,
        overview
      );
    } catch (err) {
      this._overviewDaily = {
        error:
          err?.message ||
          "Could not load daily energy history. Enable the Home Assistant recorder for your daily kWh sensors.",
      };
      this._analysisTariffDaily = { configured: false, error: err?.message };
    } finally {
      this._overviewDailyLoading = false;
      if (
        this._getPlant()?.entry_id === plantId &&
        (this._view === "overview" || this._view === "energy_analysis")
      ) {
        this._scheduleRender();
      }
    }
  }

  _renderOverview(plant) {
    return `${this._renderOverviewHeader(plant)}
${this._renderPanelStaleBanner()}
<div class="overview-hero-row" data-overview-hero-layout="4">
<div class="overview-hero-scene">
<div class="overview-hero-scene-slot">${this._renderEnergyScene(plant)}</div>
<div class="overview-system-status-slot">${this._renderOverviewSystemStatusCard()}</div>
</div>
${this._renderOverviewHeroDailyColumn()}
</div>
${this._renderOverviewEnergyBand(plant)}
${this._renderOverviewAfterHero(plant)}`;
  }

  _identityRows(plant) {
    const id = this._plantState?.identity ?? {};
    const rows = [
      ["pcs_model_name", "PCS model"],
      ["pcs_serial_number", "PCS serial"],
      ["grid_status", "Grid status"],
      ["inverter_state", "System status"],
      ["modbus_protocol_version", "Modbus protocol"],
      ["master_version", "Master firmware"],
      ["slave_version", "Slave firmware"],
      ["manager_version", "Manager firmware"],
      ["bms_online", "BMS online"],
      ["bms_pack_serial_modbus", "BMS pack serial (Modbus)"],
      ["bms_pack_count", "BMS pack count"],
    ];
    return rows
      .map(([key, label]) => {
        let value = id[key];
        if (value == null || value === "" || value === "unavailable" || value === "unknown") return null;
        if (key === "inverter_state") {
          value = foxInverterStateLabel(this._hass, plant, this._plantState);
        }
        return { label, value };
      })
      .filter(Boolean);
  }

  _identityValueList(rows) {
    if (!rows.length) {
      return `<p class="placeholder">No identity entities discovered yet. Update foxess_modbus, reload Home Assistant, then reload this panel.</p>`;
    }
    return `<div class="entity-list">${rows
      .map(
        (r) =>
          `<div class="entity-row"><span class="entity-name">${esc(r.label)}</span><span class="entity-value">${esc(r.value)}</span></div>`
      )
      .join("")}</div>`;
  }

  _renderDeviceStatusRow(plant) {
    const systemStatus = foxInverterStateLabel(this._hass, plant, this._plantState);
    if (systemStatus === "—") return "";
    return `<div class="overview-status-block">
<div class="overview-status-row">
${wrapFoxInverterStatePillLink(systemStatus, formatFoxOverviewStatusPill(systemStatus), { fromOverview: true })}
</div>
</div>`;
  }

  /** @deprecated Devices Legacy — use _renderDeviceNew. */
  _renderDeviceLegacy(plant) {
    if (this._deviceSub === "system") {
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>System info</h1><p>From Modbus (matches Fox app where confirmed)</p></header>${this._identityValueList(this._identityRows(plant))}`;
    }
    if (this._deviceSub === "parameters") {
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>Parameters</h1><p>Live Modbus values (Fox app layout)</p></header>${this._renderDeviceParameters(plant)}`;
    }
    if (this._deviceSub === "battery") {
      const map = resolveEntityMap(this._hass, plant, this._plantState);
      const section = DEVICE_PARAMETER_SECTIONS.find((s) => s.id === "battery");
      const rows = section ? entityMapRows(this._hass, plant, this._plantState, section.rows) : [];
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button><header class="header"><h1>Battery</h1></header>${this._entityList(rows)}`;
    }
    if (this._deviceSub === "pv-config") {
      return `<button type="button" class="back-btn" data-action="device-back">← Device</button>${this._renderPvConfiguration({
        title: "System PV Configuration",
        subtitle: "General solar panel settings for PV1 and PV2",
      })}`;
    }
    const serial = plantDeviceSerial(this._hass, plant, this._plantState);
    const modelLine = plantModelSubtitle(this._hass, plant, this._plantState);
    const serialRow =
      serial !== "—"
        ? `<button type="button" class="device-serial-btn" data-action="device-sub" data-sub="system"><span class="device-serial">${esc(serial)}</span><span class="chev">›</span></button>`
        : `<p class="device-serial device-serial-muted">Serial unavailable</p>`;
    return `<div data-device-main="1"><header class="header device-header"><h1>${esc(plant.title)}</h1>${modelLine !== "—" ? `<p class="device-model">${esc(modelLine)}</p>` : ""}<div data-device-status-wrap>${this._renderDeviceStatusRow(plant)}</div></header>
<div class="device-hero"><img class="device-hero-img" src="${esc(DEVICE_EVO_IMAGE_STATIC)}" alt="${esc(modelLine !== "—" ? modelLine : "Inverter")}" loading="lazy" />${serialRow}</div>
<div data-device-live>${this._renderDeviceLiveHtml(plant)}</div>
<div data-device-nav>
${renderListButton({ action: "device-sub", sub: "parameters" }, "Detailed parameters", "PV, AC, battery, grid — like Fox app")}
${renderListButton({ action: "device-sub", sub: "system" }, "System info", "Firmware, BMS, grid status")}
${renderListButton({ action: "device-sub", sub: "pv-config" }, "System PV Configuration", pvConfigSummary(this._plantState?.pv_config))}
</div></div>`;
  }

  _isDeviceMainView() {
    return this._view === PANEL_VIEW_DEVICE_LEGACY && this._deviceSub === "main";
  }

  _renderDeviceLiveHtml(plant) {
    const flows = readEnergyFlows(this._hass, plant, this._plantState);
    const pvCard = renderDevicePvCard(this._hass, plant, this._plantState);
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    const tempParts = batteryTempMetricParts(this._hass, map.bms_temp_low);
    const tempDisplay = tempParts.unit
      ? `${tempParts.num}${tempParts.unit}`
      : tempParts.num;
    return `<div class="device-grid">${pvCard}<div class="device-card device-card--battery">${renderDeviceBatteryCard(flows, tempDisplay)}</div></div>`;
  }

  _patchDeviceMainLiveIfNeeded() {
    if (!this._isDeviceMainView() || !this._hass) return false;
    const root = this._root.querySelector("[data-device-main]");
    const live = this._root.querySelector("[data-device-live]");
    if (!root || !live) return false;
    const plant = this._getPlant();
    if (!plant) return false;
    const statusWrap = root.querySelector("[data-device-status-wrap]");
    if (statusWrap) statusWrap.innerHTML = this._renderDeviceStatusRow(plant);
    live.innerHTML = this._renderDeviceLiveHtml(plant);
    const pvSub = root.querySelector('[data-action="device-sub"][data-sub="pv-config"] .list-btn-sub');
    if (pvSub) pvSub.textContent = pvConfigSummary(this._plantState?.pv_config);
    return true;
  }

  _entityList(rows) {
    if (!rows.length) return `<p class="placeholder">No entities mapped.</p>`;
    return `<div class="entity-list">${rows
      .map(
        (r) =>
          `<div class="entity-row"><span class="entity-name">${esc(r.name)}</span><span class="entity-value">${esc(stateString(this._hass, r.entity_id))}${esc(entityUnit(this._hass, r.entity_id))}</span></div>`
      )
      .join("")}</div>`;
  }

  _entityMapRows(pairs) {
    return entityMapRows(this._hass, this._getPlant(), this._plantState, pairs);
  }

  _renderDevicePvTable(map) {
    const rows = DEVICE_PV_STRINGS.map((n) => {
      const v = map[`pv${n}_voltage`];
      const c = map[`pv${n}_current`];
      const p = map[`pv${n}_power`];
      if (!v && !c && !p) return null;
      return `<tr><td>PV${n}</td><td>${esc(entityDisplayValue(this._hass, v))}</td><td>${esc(entityDisplayValue(this._hass, c))}</td><td>${esc(entityDisplayValue(this._hass, p))}</td></tr>`;
    }).filter(Boolean);
    if (!rows.length) return `<p class="device-param-empty">No PV string sensors discovered.</p>`;
    const total =
      map.pv_power && this._hass?.states?.[map.pv_power]
        ? `<tr><td>PV</td><td>—</td><td>—</td><td>${esc(entityDisplayValue(this._hass, map.pv_power))}</td></tr>`
        : "";
    return `<div class="device-param-table-wrap"><table class="device-param-table"><thead><tr><th>PV</th><th>Voltage (V)</th><th>Current (A)</th><th>Power (kW)</th></tr></thead><tbody>${total}${rows.join("")}</tbody></table></div>`;
  }

  _renderDeviceMetricTable(map, keys, headers) {
    const values = keys.map((key) => entityDisplayValue(this._hass, map[key]));
    if (values.every((v) => v === "—")) {
      return `<p class="device-param-empty">No sensors discovered for this section.</p>`;
    }
    return `<div class="device-param-table-wrap"><table class="device-param-table"><thead><tr>${headers
      .map((h) => `<th>${esc(h)}</th>`)
      .join("")}</tr></thead><tbody><tr>${values.map((v) => `<td>${esc(v)}</td>`).join("")}</tr></tbody></table></div>`;
  }

  _renderDeviceDataloggerRows(plant, map, { layout = "list" } = {}) {
    const id = this._plantState?.identity ?? {};
    const rows = [];
    const bmsId = map.bms_online;
    if (bmsId && this._hass?.states?.[bmsId]) {
      const on = this._hass.states[bmsId].state === "on";
      rows.push({ name: "Status", value: on ? "Online" : "Offline" });
    } else if (id.bms_online != null && id.bms_online !== "") {
      rows.push({ name: "Status", value: id.bms_online === true || id.bms_online === "on" ? "Online" : "Offline" });
    }
    const firmware = formatFoxDataloggerSoftwareVersion(this._hass, this._plantState, map);
    if (firmware && firmware !== "—") rows.push({ name: "Software version", value: firmware });
    const proto = id.modbus_protocol_version || entityDisplayValue(this._hass, map.modbus_protocol_version);
    if (proto && proto !== "—") rows.push({ name: "Modbus protocol", value: proto });
    const master = id.master_version || entityDisplayValue(this._hass, map.master_version);
    if (master && master !== "—") rows.push({ name: "Master firmware", value: master });
    const slave = id.slave_version || entityDisplayValue(this._hass, map.slave_version);
    if (slave && slave !== "—") rows.push({ name: "Slave firmware", value: slave });
    if (!rows.length) {
      return `<p class="device-param-empty">No datalogger sensors discovered yet.</p>`;
    }
    if (layout === "grid") {
      return renderDeviceNewMetricGrid(this._hass, rows);
    }
    return `<div class="entity-list">${rows
      .map(
        (r) =>
          `<div class="entity-row"><span class="entity-name">${esc(r.name)}</span><span class="entity-value">${esc(r.value)}</span></div>`
      )
      .join("")}</div>`;
  }

  _deviceParamSectionHasContent(section, map) {
    if (section.kind === "pv-table") {
      return DEVICE_PV_STRINGS.some((n) => map[`pv${n}_voltage`] || map[`pv${n}_current`] || map[`pv${n}_power`]) || map.pv_power;
    }
    if (section.kind === "metric-table") {
      return section.keys.some((key) => map[key]);
    }
    if (section.kind === "datalogger") {
      return Boolean(
        map.bms_online ||
          map.manager_version ||
          map.master_version ||
          map.modbus_protocol_version ||
          this._plantState?.identity?.modbus_protocol_version
      );
    }
    if (section.kind === "rows") {
      return section.rows.some(([key]) => map[key]);
    }
    return false;
  }

  _renderDeviceParamSectionBody(section, plant, map) {
    if (section.kind === "pv-table") return this._renderDevicePvTable(map);
    if (section.kind === "metric-table") {
      return this._renderDeviceMetricTable(map, section.keys, section.headers);
    }
    if (section.kind === "datalogger") return this._renderDeviceDataloggerRows(plant, map);
    const rows = entityMapRows(this._hass, plant, this._plantState, section.rows);
    return this._entityList(rows);
  }

  _renderDeviceParameters(plant) {
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    const sections = DEVICE_PARAMETER_SECTIONS.filter((section) => this._deviceParamSectionHasContent(section, map));
    if (!sections.length) {
      return `<p class="placeholder">No Modbus sensors discovered. Reload foxess_modbus and this panel, or reconfigure the plant device link.</p>`;
    }
    const entityIds = deviceParamEntityIds(map, sections);
    const updated = deviceParamLastUpdated(this._hass, entityIds);
    const body = sections
      .map((section) => {
        const isOpen = this._deviceParamOpen.has(section.id);
        const sectionBody = isOpen ? this._renderDeviceParamSectionBody(section, plant, map) : "";
        return `<div class="device-param-section${isOpen ? " is-open" : ""}"><button type="button" class="device-param-summary" data-action="device-param-toggle" data-section="${esc(section.id)}" aria-expanded="${isOpen}">${esc(section.title)}</button>${isOpen ? `<div class="device-param-body">${sectionBody}</div>` : ""}</div>`;
      })
      .join("");
    const stamp = updated ? `<p class="device-param-updated">${esc(updated)}</p>` : "";
    return `<div class="device-param-sections">${body}</div>${stamp}`;
  }

  _deviceNewChartsCacheKey(plant) {
    return `${plant.entry_id}:device-new:curve:${this._deviceNewCurveDayOffset}:energy:${this._deviceNewEnergyPeriod}:${this._deviceNewEnergyPeriodOffset}`;
  }

  _deviceNewCurveChartCacheKey(plant) {
    const dayOffset = Math.max(0, this._deviceNewCurveDayOffset || 0);
    return `${this._deviceNewChartsCacheKey(plant)}:curve:${dayOffset}`;
  }

  _deviceNewEnergyChartCacheKey(plant) {
    const period = this._deviceNewEnergyPeriod || "week";
    const offset = Math.max(0, this._deviceNewEnergyPeriodOffset || 0);
    return `${plant.entry_id}:device-new:energy:${period}:${offset}`;
  }

  _invalidateDeviceNewCharts() {
    this._deviceNewChartsGen += 1;
    this._deviceNewStatisticsChart = null;
    this._deviceNewStatisticsChartPlantId = undefined;
    this._deviceNewEnergyChart = null;
    this._deviceNewEnergyChartPlantId = undefined;
    this._deviceNewCurveInflight = undefined;
    this._deviceNewEnergyInflight = undefined;
    this._deviceNewStatisticsChartLoading = false;
    this._deviceNewEnergyChartLoading = false;
    this._deviceNewAlarmData = null;
    this._deviceNewAlarmPlantId = undefined;
    this._deviceNewAlarmInflight = undefined;
    this._deviceNewAlarmLoading = false;
  }

  _deviceNewAlarmCacheKey(plant) {
    const tab = this._deviceNewAlarmTab || "active";
    return `${plant.entry_id}:device-new:alarms:${tab}`;
  }

  _renderDeviceNewAlarmsBody() {
    const def = defaultAlarmCustomRangeValues();
    return renderFoxAlarmPage(this._deviceNewAlarmData, {
      tab: this._deviceNewAlarmTab || "active",
      loading: this._deviceNewAlarmLoading,
      filters: {
        category: this._deviceNewAlarmFilterCategory || "",
        severity: this._deviceNewAlarmFilterSeverity || "",
        device: this._deviceNewAlarmFilterDevice || "",
      },
      timeRange: {
        mode: this._deviceNewAlarmHistoryRange || "24h",
        start: this._deviceNewAlarmHistoryStart || def.start,
        end: this._deviceNewAlarmHistoryEnd || def.end,
      },
    });
  }

  _patchDeviceNewAlarmsList() {
    const slot = this._root?.querySelector?.("[data-device-new-alarms]");
    if (slot) slot.innerHTML = this._renderDeviceNewAlarmsBody();
  }

  async _loadDeviceNewAlarms({ force = false } = {}) {
    const plant = this._getPlant();
    if (!plant || !this._hass || this._view !== "device_new" || this._deviceNewSub !== "alarms") return;
    const cacheKey = this._deviceNewAlarmCacheKey(plant);
    if (!force && this._deviceNewAlarmPlantId === cacheKey && this._deviceNewAlarmData) return;
    if (this._deviceNewAlarmInflight === cacheKey) return;
    this._deviceNewAlarmInflight = cacheKey;
    this._deviceNewAlarmLoading = true;
    this._scheduleRender();
    try {
      const data = await fetchDeviceAlarmDashboard(this._hass, plant, this._plantState);
      if (this._view !== "device_new" || this._deviceNewSub !== "alarms") return;
      if (this._deviceNewAlarmCacheKey(this._getPlant()) !== cacheKey) return;
      this._deviceNewAlarmData = data;
      this._deviceNewAlarmPlantId = cacheKey;
    } catch (err) {
      if (this._view !== "device_new" || this._deviceNewSub !== "alarms") return;
      if (this._deviceNewAlarmCacheKey(this._getPlant()) !== cacheKey) return;
      this._deviceNewAlarmData = {
        error: err?.message || "Could not load alarm history. Enable the Home Assistant recorder for alarm sensors.",
      };
      this._deviceNewAlarmPlantId = cacheKey;
    } finally {
      if (this._deviceNewAlarmInflight === cacheKey) this._deviceNewAlarmInflight = undefined;
      this._deviceNewAlarmLoading = false;
      if (this._view === "device_new" && this._deviceNewSub === "alarms") {
        if (!this._patchDeviceNewAlarmsIfNeeded()) {
          if (this._deviceNewAlarmBlocksRender()) {
            this._patchDeviceNewAlarmHistBody();
          } else {
            this._patchDeviceNewAlarmsList();
          }
        }
        this._scheduleRender();
      }
    }
  }

  _patchDeviceNewAlarmsIfNeeded() {
    if (this._view !== "device_new" || this._deviceNewSub !== "alarms") return false;
    const slot = this._root?.querySelector?.("[data-device-new-alarms]");
    if (!slot) return false;
    const plant = this._getPlant();
    if (!plant) return false;
    const cacheKey = this._deviceNewAlarmCacheKey(plant);
    if (this._deviceNewAlarmLoading || this._deviceNewAlarmPlantId !== cacheKey || !this._deviceNewAlarmData) return false;
    if (!slot.querySelector(".chart-loading")) return false;
    slot.innerHTML = this._renderDeviceNewAlarmsBody();
    return true;
  }

  _loadDeviceNewCharts() {
    if (this._view !== "device_new" || this._deviceNewSub !== "analysis") return;
    void this._loadDeviceNewCurveChart();
    void this._loadDeviceNewEnergyChart();
  }

  _deviceNewAnalysisLayoutStale() {
    if (this._view !== "device_new" || this._deviceNewSub !== "analysis") return false;
    const root = this._root?.querySelector?.("[data-device-new-main]");
    if (!root) return true;
    if (root.dataset.deviceNewLayoutVer !== DEVICE_NEW_ANALYSIS_LAYOUT_VER) return true;
    return !root.querySelector(".fox-device-new-analysis-stack");
  }

  _deviceNewAnalysisChartsStale() {
    if (this._view !== "device_new" || this._deviceNewSub !== "analysis") return false;
    if (this._deviceNewAnalysisLayoutStale()) return false;
    const plant = this._getPlant();
    if (!plant) return false;
    const curveKey = this._deviceNewCurveChartCacheKey(plant);
    const energyKey = this._deviceNewEnergyChartCacheKey(plant);
    const curveSlot = this._root?.querySelector?.("[data-device-new-curve]");
    const energySlot = this._root?.querySelector?.("[data-device-new-energy-chart]");
    const curveDomLoading = Boolean(curveSlot?.querySelector?.(".chart-loading"));
    const energyDomLoading = Boolean(energySlot?.querySelector?.(".chart-loading"));
    const curveReady =
      !this._deviceNewStatisticsChartLoading &&
      this._deviceNewStatisticsChartPlantId === curveKey &&
      Boolean(this._deviceNewStatisticsChart);
    const energyReady =
      !this._deviceNewEnergyChartLoading &&
      this._deviceNewEnergyChartPlantId === energyKey &&
      Boolean(this._deviceNewEnergyChart);
    return (curveDomLoading && curveReady) || (energyDomLoading && energyReady);
  }

  _patchDeviceNewAnalysisChartsIfNeeded() {
    if (this._view !== "device_new" || this._deviceNewSub !== "analysis") return false;
    if (this._deviceNewAnalysisLayoutStale()) return false;
    const plant = this._getPlant();
    if (!plant) return false;
    const curveKey = this._deviceNewCurveChartCacheKey(plant);
    const energyKey = this._deviceNewEnergyChartCacheKey(plant);
    let patched = false;
    const curveSlot = this._root.querySelector("[data-device-new-curve]");
    if (
      curveSlot &&
      !this._deviceNewStatisticsChartLoading &&
      this._deviceNewStatisticsChartPlantId === curveKey &&
      this._deviceNewStatisticsChart &&
      curveSlot.querySelector(".chart-loading")
    ) {
      curveSlot.innerHTML = this._renderDeviceNewCurveBody();
      patched = true;
      if (this._deviceNewStatisticsChart?.series?.length && this._deviceNewStatisticsChart?.range) {
        this._bindDeviceNewCharts();
      }
    }
    const energySlot = this._root.querySelector("[data-device-new-energy-chart]");
    if (
      energySlot &&
      !this._deviceNewEnergyChartLoading &&
      this._deviceNewEnergyChartPlantId === energyKey &&
      this._deviceNewEnergyChart &&
      energySlot.querySelector(".chart-loading")
    ) {
      energySlot.innerHTML = this._renderDeviceNewEnergyBody();
      patched = true;
      bindMirroredEnergyChart(energySlot);
    }
    return patched;
  }

  async _loadDeviceNewCurveChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass || this._view !== "device_new") return;
    const cacheKey = this._deviceNewCurveChartCacheKey(plant);
    if (this._deviceNewStatisticsChartPlantId === cacheKey && this._deviceNewStatisticsChart) return;
    if (this._deviceNewCurveInflight === cacheKey) return;
    this._deviceNewCurveInflight = cacheKey;
    const gen = this._deviceNewChartsGen;
    this._deviceNewStatisticsChartLoading = true;
    this._scheduleRender();
    try {
      const dayOffset = Math.max(0, this._deviceNewCurveDayOffset || 0);
      const curve = await fetchDeviceRealtimeChartSeries(this._hass, plant, this._plantState, { dayOffset });
      if (gen !== this._deviceNewChartsGen || this._view !== "device_new") return;
      if (this._deviceNewCurveChartCacheKey(this._getPlant()) !== cacheKey) return;
      this._deviceNewStatisticsChart = curve;
      this._deviceNewStatisticsChartPlantId = cacheKey;
    } catch (err) {
      if (gen !== this._deviceNewChartsGen || this._view !== "device_new") return;
      if (this._deviceNewCurveChartCacheKey(this._getPlant()) !== cacheKey) return;
      this._deviceNewStatisticsChart = {
        error:
          err?.message ||
          "Could not load device curve. Enable the Home Assistant recorder for inverter power sensors.",
      };
      this._deviceNewStatisticsChartPlantId = cacheKey;
    } finally {
      if (this._deviceNewCurveInflight === cacheKey) this._deviceNewCurveInflight = undefined;
      if (gen === this._deviceNewChartsGen) {
        this._deviceNewStatisticsChartLoading = false;
        if (this._view === "device_new" && this._getPlant()?.entry_id === plant.entry_id) {
          this._patchDeviceNewAnalysisChartsIfNeeded();
          this._scheduleRender(true);
        }
      }
    }
  }

  async _loadDeviceNewEnergyChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass || this._view !== "device_new") return;
    const cacheKey = this._deviceNewEnergyChartCacheKey(plant);
    if (this._deviceNewEnergyChartPlantId === cacheKey && this._deviceNewEnergyChart) return;
    if (this._deviceNewEnergyInflight === cacheKey) return;
    this._deviceNewEnergyInflight = cacheKey;
    const gen = this._deviceNewChartsGen;
    this._deviceNewEnergyChartLoading = true;
    this._scheduleRender();
    try {
      const period = this._deviceNewEnergyPeriod || "week";
      const offset = Math.max(0, this._deviceNewEnergyPeriodOffset || 0);
      const bar = await fetchFoxMirroredBarChart(
        this._hass,
        plant,
        this._plantState,
        period,
        offset
      );
      if (gen !== this._deviceNewChartsGen || this._view !== "device_new") return;
      if (this._deviceNewEnergyChartCacheKey(this._getPlant()) !== cacheKey) return;
      this._deviceNewEnergyChart = { kind: "mirror", svg: bar.svg, title: bar.title };
      this._deviceNewEnergyChartPlantId = cacheKey;
    } catch (err) {
      if (gen !== this._deviceNewChartsGen || this._view !== "device_new") return;
      if (this._deviceNewEnergyChartCacheKey(this._getPlant()) !== cacheKey) return;
      this._deviceNewEnergyChart = {
        error:
          err?.message ||
          "Could not load energy analysis. Enable the Home Assistant recorder and keep history for energy sensors.",
      };
      this._deviceNewEnergyChartPlantId = cacheKey;
    } finally {
      if (this._deviceNewEnergyInflight === cacheKey) this._deviceNewEnergyInflight = undefined;
      if (gen === this._deviceNewChartsGen) {
        this._deviceNewEnergyChartLoading = false;
        if (this._view === "device_new" && this._getPlant()?.entry_id === plant.entry_id) {
          this._patchDeviceNewAnalysisChartsIfNeeded();
          this._scheduleRender(true);
        }
      }
    }
  }

  _renderDeviceNewCurveDateNav() {
    const offset = Math.max(0, this._deviceNewCurveDayOffset || 0);
    const { start } = energyPeriodBounds("day", offset);
    const label = formatDeviceCurveDateLabel(start);
    const canNext = offset > 0;
    return `<div class="energy-date-nav fox-device-new-date-nav">
<button type="button" data-action="device-new-curve-nav" data-dir="prev" aria-label="Previous day">‹</button>
<span class="energy-date-label">${esc(label)}</span>
<button type="button" data-action="device-new-curve-nav" data-dir="next" aria-label="Next day"${canNext ? "" : " disabled"}>›</button>
</div>`;
  }

  _renderDeviceNewEnergyPeriodTabs() {
    const tabs = DEVICE_NEW_ENERGY_PERIOD_TABS.map(
      (p) =>
        `<button type="button" data-action="device-new-energy-period" data-period="${p.id}" class="${p.id === this._deviceNewEnergyPeriod ? "active" : ""}">${p.label}</button>`
    ).join("");
    return `<div class="energy-period-tabs">${tabs}</div>`;
  }

  _renderDeviceNewEnergyDateNav() {
    if (this._deviceNewEnergyPeriod === "total") return "";
    const bounds = energyPeriodBounds(this._deviceNewEnergyPeriod, this._deviceNewEnergyPeriodOffset);
    const label = deviceNewEnergyPeriodNavLabel(
      this._deviceNewEnergyPeriod,
      this._deviceNewEnergyPeriodOffset
    );
    return `<div class="energy-date-nav fox-device-new-date-nav">
<button type="button" data-action="device-new-energy-nav" data-dir="prev" aria-label="Previous period">‹</button>
<span class="energy-date-label">${esc(label)}</span>
<button type="button" data-action="device-new-energy-nav" data-dir="next" aria-label="Next period"${bounds.canNext ? "" : " disabled"}>›</button>
</div>`;
  }

  _renderDeviceNewEnergyCardToolbar() {
    return `<div class="fox-device-new-card-toolbar">${this._renderDeviceNewEnergyPeriodTabs()}${this._renderDeviceNewEnergyDateNav()}</div>`;
  }

  _renderDeviceNewCurveBody() {
    if (this._deviceNewStatisticsChartLoading) {
      return `<p class="chart-loading">Loading real-time curve…</p>`;
    }
    const chart = this._deviceNewStatisticsChart;
    if (chart?.error) {
      return `<p class="placeholder chart-empty">${esc(chart.error)}</p>`;
    }
    if (chart?.empty) {
      return `<p class="placeholder chart-empty">${esc(chart.empty)}</p>`;
    }
    if (!chart) {
      return `<p class="placeholder chart-empty">Real-time curve not loaded yet.</p>`;
    }
    const dayOffset = chart.dayOffset ?? 0;
    const range = statisticsRangeForDisplay(chart.range, dayOffset);
    if (!range) {
      return `<p class="placeholder chart-empty">Real-time curve not loaded yet.</p>`;
    }
    const series = (chart?.series || []).filter((s) => s.points?.length);
    const socSeries = chart?.socSeries;
    if (!series.length && !socSeries?.points?.length) {
      return `<p class="placeholder chart-empty">No power history for this day yet.</p>`;
    }
    return renderStatisticsChartHtml(series, range, {
      sideLegend: false,
      includeSoc: true,
      socSeries,
      legendFromSeries: true,
      forecastFullDaySolid: dayOffset > 0,
    });
  }

  _renderDeviceNewEnergyBody() {
    if (this._deviceNewEnergyChartLoading) {
      return `<p class="chart-loading">Loading energy analysis…</p>`;
    }
    if (this._deviceNewEnergyChart?.error) {
      return `<p class="placeholder chart-empty">${esc(this._deviceNewEnergyChart.error)}</p>`;
    }
    if (this._deviceNewEnergyChart?.svg) {
      return this._deviceNewEnergyChart.svg;
    }
    return `<p class="placeholder chart-empty">Energy analysis not loaded yet.</p>`;
  }

  _renderDeviceNewAnalysisCharts() {
    return `<div class="card fox-device-new-card">
<div class="fox-device-new-card-head">
<h3 class="fox-device-new-card-title">Realtime Curve</h3>
${this._renderDeviceNewCurveDateNav()}
</div>
<div data-device-new-curve="1">${this._renderDeviceNewCurveBody()}</div>
</div>
<div class="card fox-device-new-card">
<div class="fox-device-new-card-head fox-device-new-card-head--energy">
<h3 class="fox-device-new-card-title">Energy Analysis</h3>
${this._renderDeviceNewEnergyCardToolbar()}
</div>
<div data-device-new-energy-chart="1">${this._renderDeviceNewEnergyBody()}</div>
</div>`;
  }

  _deviceNewSectionHasContent(section, map) {
    // Fox Cloud always renders these sections; missing Modbus values show as —.
    return true;
  }

  _renderDeviceNewSectionBody(section, plant, map) {
    if (section.kind === "pv-table") return renderDeviceNewPvTable(this._hass, map);
    if (section.kind === "metric-table") {
      return renderDeviceNewMetricTable(this._hass, map, section.keys, section.headers);
    }
    if (section.kind === "fox-datalogger") {
      return renderDeviceNewFoxDatalogger(this._hass, plant, this._plantState, map);
    }
    if (section.kind === "subsections") {
      return renderDeviceNewSubsections(this._hass, plant, this._plantState, section);
    }
    if (section.kind === "rows") {
      return renderDeviceNewMetricRows(this._hass, plant, this._plantState, section.rows);
    }
    return `<p class="device-param-empty">Unsupported section.</p>`;
  }

  _renderDeviceNewRealtimeSections(plant) {
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    const sections = DEVICE_NEW_REALTIME_SECTIONS.filter((section) =>
      this._deviceNewSectionHasContent(section, map)
    );
    if (!sections.length) {
      return `<p class="placeholder">No Modbus sensors discovered yet. Reload foxess_modbus and this panel.</p>`;
    }
    return `<div class="fox-device-new-realtime">${sections
      .map(
        (section) =>
          `<section class="fox-device-new-section"><h3 class="fox-device-new-section-title">${esc(section.title)}</h3>${this._renderDeviceNewSectionBody(section, plant, map)}</section>`
      )
      .join("")}</div>`;
  }

  _renderDeviceNew(plant) {
    if (this._deviceNewScreen === "system") {
      return `<div data-device-new-main="1" data-plant-id="${esc(plant.entry_id)}">
<button type="button" class="back-btn" data-action="device-new-back">← Device</button>
<header class="header"><h1>System info</h1><p>From Modbus (matches Fox app where confirmed)</p></header>
${this._identityValueList(this._identityRows(plant))}
</div>`;
    }
    if (this._deviceNewSub === "pv-config") {
      return `<div data-device-new-main="1" data-plant-id="${esc(plant.entry_id)}">
${this._renderPvConfiguration({
  title: "System PV Configuration",
  subtitle: "General solar panel settings for PV1 and PV2",
})}
</div>`;
    }
    const summary = renderDeviceNewSummaryCards(this._hass, plant, this._plantState);
    const sidebar = renderDeviceNewSidebar(this._hass, plant, this._plantState);
    if (this._deviceNewSub === "analysis") {
      return `<div data-device-new-main="1" data-device-new-layout-ver="${DEVICE_NEW_ANALYSIS_LAYOUT_VER}" data-plant-id="${esc(plant.entry_id)}">
<div class="fox-device-new-layout fox-device-new-layout--analysis">
${sidebar}
<div class="fox-device-new-analysis-stack">
<div class="fox-device-new-summary-row">${summary}</div>
<div class="fox-device-new-charts-col">${this._renderDeviceNewAnalysisCharts()}</div>
</div>
</div>
</div>`;
    }
    if (this._deviceNewSub === "alarms") {
      return `<div data-device-new-main="1" data-plant-id="${esc(plant.entry_id)}">
<div class="fox-device-new-layout fox-device-new-layout--alarms">
${sidebar}
<div class="fox-device-new-content">
${summary}
<div data-device-new-alarms="1">${this._renderDeviceNewAlarmsBody()}</div>
</div>
</div>
</div>`;
    }
    const body = this._renderDeviceNewRealtimeSections(plant);
    return `<div data-device-new-main="1" data-plant-id="${esc(plant.entry_id)}">
<div class="fox-device-new-layout">
${sidebar}
<div class="fox-device-new-content">
${summary}
${body}
</div>
</div>
</div>`;
  }

  _patchDeviceNewLiveIfNeeded() {
    if (this._view !== "device_new" || !this._hass) return false;
    if (this._deviceNewSub === "analysis" || this._deviceNewSub === "pv-config" || this._deviceNewSub === "alarms") return false;
    if (this._deviceNewScreen !== "main") return false;
    if (this._deviceNewAnalysisChartsStale()) return false;
    const root = this._root.querySelector("[data-device-new-main]");
    if (!root) return false;
    const plant = this._getPlant();
    if (!plant || root.dataset.plantId !== plant.entry_id) return false;
    const summary = repairDeviceNewSummaryElement(root.querySelector("[data-device-new-summary]"));
    if (!summary) return false;
    summary.innerHTML = renderDeviceNewSummaryCardItems(this._hass, plant, this._plantState);
    return true;
  }

  _bindDeviceNewCharts() {
    const curveRoot = this._root.querySelector("[data-device-new-curve]");
    const chart = this._deviceNewStatisticsChart;
    if (curveRoot && chart?.series?.length) {
      const dayOffset = chart.dayOffset ?? 0;
      const range = statisticsRangeForDisplay(chart.range, dayOffset);
      if (range) {
        const series = chart.series.filter((s) => s.points?.length);
        const soc = chart.socSeries;
        const meta = soc?.points?.length ? [...series, soc] : series;
        const inner = curveRoot.querySelector("[data-statistics-chart]");
        if (inner) {
          delete inner.dataset.bound;
          bindStatisticsChart(curveRoot, meta);
        }
      }
    }
    const energyRoot = this._root.querySelector("[data-device-new-energy-chart]");
    if (energyRoot) bindMirroredEnergyChart(energyRoot);
  }

  _energyHistoryEntities(plant) {
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    return resolveEnergyHistoryEntities(map);
  }

  _energyChartCacheKey(plant) {
    return `${plant.entry_id}:${this._energyPeriod}:${this._energyPeriodOffset}`;
  }

  async _loadEnergyCharts() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const cacheKey = this._energyChartCacheKey(plant);
    if (this._energyPeriod === "day") {
      if (
        this._statisticsChartPlantId === cacheKey &&
        this._statisticsChart &&
        (this._statisticsChart.dayOffset ?? 0) === this._energyPeriodOffset
      ) {
        return;
      }
      return this._loadStatisticsChart();
    }
    if (this._energyChartPlantId === cacheKey && this._energyChart) return;
    if (!this._plantState) await this._refreshPlantState();
    this._energyChartLoading = true;
    this._energyChart = null;
    this._energyChartPlantId = cacheKey;
    this._scheduleRender();
    try {
      const bar = await fetchFoxMirroredBarChart(
        this._hass,
        plant,
        this._plantState,
        this._energyPeriod,
        this._energyPeriodOffset
      );
      this._energyChart = { kind: "mirror", svg: bar.svg, title: bar.title };
      if (bar.breakdown) this._energyBreakdown = bar.breakdown;
    } catch (err) {
      this._energyChart = {
        error:
          err?.message ||
          "Could not load history. Enable the Home Assistant recorder and keep history for power sensors.",
      };
    } finally {
      this._energyChartLoading = false;
      if (this._energyChartCacheKey(this._getPlant()) === cacheKey && this._view === "energy_analysis") {
        this._scheduleRender();
      }
    }
  }

  async _loadOverviewStatisticsChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const cacheKey = `${plant.entry_id}:overview`;
    if (this._statisticsChartPlantId === cacheKey && this._statisticsChart) return;
    this._statisticsChartLoading = true;
    this._statisticsChart = null;
    this._statisticsChartPlantId = cacheKey;
    this._scheduleRender();
    try {
      if (resolveSolcastDetailedForecast(this._plantState, this._hass).length < 2) {
        await this._refreshPlantState();
      }
      this._statisticsChart = await fetchStatisticsChartSeries(this._hass, plant, this._plantState, {
        dayOffset: 0,
      });
    } catch (err) {
      this._statisticsChart = {
        error:
          err?.message ||
          "Could not load history. Enable the Home Assistant recorder and keep history for power sensors.",
      };
    } finally {
      this._statisticsChartLoading = false;
      if (this._getPlant()?.entry_id === plant.entry_id && this._view === "overview") {
        void this._refreshStatisticsServerForecast();
        this._scheduleRender();
      }
    }
  }

  async _loadStatisticsChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const cacheKey = this._energyChartCacheKey(plant);
    if (
      this._statisticsChartPlantId === cacheKey &&
      this._statisticsChart &&
      (this._statisticsChart.dayOffset ?? 0) === this._energyPeriodOffset
    ) {
      return;
    }
    this._statisticsChartLoading = true;
    this._statisticsChart = null;
    this._statisticsChartPlantId = cacheKey;
    this._scheduleRender();
    try {
      if (
        this._energyPeriodOffset === 0 &&
        resolveSolcastDetailedForecast(this._plantState, this._hass).length < 2
      ) {
        await this._refreshPlantState();
      }
      const chart = await this._fetchStatisticsChartData(plant);
      this._statisticsChart = chart;
      if (this._energyPeriod === "day" && this._energyPeriodOffset > 0) {
        const bounds = energyPeriodBounds("day", this._energyPeriodOffset);
        const { points } = await fetchEnergyHistoryPoints(
          this._hass,
          plant,
          this._plantState,
          bounds.start,
          bounds.end
        );
        if (points) {
          this._energyBreakdown = computeEnergyBreakdown(points, buildDaysInRange(bounds.start, bounds.end));
        }
      } else if (this._energyPeriod === "day" && this._energyPeriodOffset === 0) {
        this._energyBreakdown = null;
      }
    } catch (err) {
      this._statisticsChart = {
        error:
          err?.message ||
          "Could not load history. Enable the Home Assistant recorder and keep history for power sensors.",
      };
    } finally {
      this._statisticsChartLoading = false;
      if (this._energyChartCacheKey(this._getPlant()) === cacheKey) {
        if (this._energyPeriodOffset === 0) void this._refreshStatisticsServerForecast();
        if (this._view === "energy_analysis") this._energyAnalysisChartSlotCache = undefined;
        this._scheduleRender();
      }
    }
  }

  async _fetchStatisticsChartData(plant) {
    return fetchStatisticsChartSeries(this._hass, plant, this._plantState, {
      dayOffset: this._energyPeriodOffset,
    });
  }

  _renderStatisticsChartBody(options = {}) {
    try {
      return this._renderStatisticsChartBodyInner(options);
    } catch (err) {
      console.error("FoxESS Plant statistics chart render failed", err);
      if (this._statisticsChartVisible()) this._ensureStatisticsChartLoaded();
      return `<p class="placeholder chart-empty">Statistics chart unavailable. Reload the panel or refresh the page.</p>`;
    }
  }

  _renderStatisticsChartBodyInner(options = {}) {
    if (this._statisticsChartLoading) {
      return `<p class="chart-loading">Loading statistics…</p>`;
    }
    const chart = this._statisticsChart;
    if (chart?.error) {
      return `<p class="placeholder chart-empty">${esc(chart.error)}</p>`;
    }
    if (chart?.empty) {
      return `<p class="placeholder chart-empty">${esc(chart.empty)}</p>`;
    }
    const dayOffset = chart?.dayOffset ?? 0;
    const range = statisticsRangeForDisplay(chart?.range, dayOffset);
    if (!range) {
      if (this._statisticsChartVisible()) {
        this._ensureStatisticsChartLoaded();
        return `<p class="chart-loading">Loading statistics…</p>`;
      }
      return `<p class="placeholder chart-empty">Open Analysis or wait for history to load.</p>`;
    }
    const series = this._statisticsSeriesForDisplay();
    const includeSoc = options.includeSoc === true;
    const socSeries = includeSoc ? chart?.socSeries : null;
    if (series?.length || socSeries?.points?.length) {
      return renderStatisticsChartHtml(series || [], range, {
        ...options,
        socSeries,
        forecastFullDaySolid: dayOffset > 0,
      });
    }
    return `<p class="placeholder chart-empty">Open Analysis or wait for history to load.</p>`;
  }

  _bindForecastAccuracyCharts() {
    const cards = this._root.querySelectorAll('[data-forecast-accuracy="1"]');
    cards.forEach((card) => {
      const report = card.closest("[data-energy-analysis-forecast]")
        ? this._forecastAccuracyAnalysis
        : this._forecastAccuracyOverview;
      if (report?.intraday && !report.error) {
        bindForecastAccuracyChart(
          card,
          buildForecastAccuracySeriesMeta(report.intraday, {
            compact: card.classList.contains("forecast-accuracy-card--compact"),
          })
        );
      }
    });
  }

  _bindOctopusGreenerCharts() {
    bindOctopusGreenerCharts(this._root);
  }

  _bindStatisticsChart() {
    const series = this._statisticsSeriesForDisplay() || [];
    const includeSoc = this._view === "energy_analysis" && this._energyPeriod === "day";
    const soc = includeSoc ? this._statisticsChart?.socSeries : null;
    const meta = soc?.points?.length ? [...series, soc] : series;
    if (!meta.length) return;
    bindStatisticsChart(this._root, meta);
    this._bindForecastAccuracyCharts();
    this._bindOctopusGreenerCharts();
  }

  async _loadBatterySocChart() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const plantId = plant.entry_id;
    this._batterySocChartLoading = true;
    this._batterySocChart = null;
    this._batterySocChartPlantId = plantId;
    this._scheduleRender();
    try {
      await this._refreshPlantState();
      this._batterySocChart = await fetchBatterySocChartSeries(this._hass, plant, this._plantState);
    } catch (err) {
      this._batterySocChart = {
        error:
          err?.message ||
          "Could not load battery SOC history. Enable the Home Assistant recorder for battery_soc.",
      };
    } finally {
      this._batterySocChartLoading = false;
      if (this._getPlant()?.entry_id === plantId) this._scheduleRender();
    }
  }

  _renderBatterySocChartBody(plant) {
    if (this._batterySocChartLoading) {
      return `<p class="chart-loading">Loading battery SOC…</p>`;
    }
    if (this._batterySocChart?.error) {
      return `<p class="placeholder chart-empty">${esc(this._batterySocChart.error)}</p>`;
    }
    if (this._batterySocChart?.empty) {
      return `<p class="placeholder chart-empty">${esc(this._batterySocChart.empty)}</p>`;
    }
    if (this._batterySocChart?.socPts?.length) {
      const displaySoc = resolveBatterySocDisplay(
        this._hass,
        plant,
        this._plantState,
        this._batterySocChart
      );
      return renderBatterySocChartHtml(this._batterySocChart, displaySoc);
    }
    return `<p class="placeholder chart-empty">Waiting for battery SOC history…</p>`;
  }

  _bindBatterySocChart() {
    if (!this._batterySocChart?.socPts?.length) return;
    bindBatterySocChart(this._root, this._batterySocChart);
  }

  _renderEnergyPeriodTabs() {
    const tabs = ENERGY_PERIOD_TABS.map(
      (p) =>
        `<button type="button" data-action="energy-period" data-period="${p.id}" class="${p.id === this._energyPeriod ? "active" : ""}">${p.label}</button>`
    ).join("");
    return `<div class="energy-period-tabs">${tabs}</div>`;
  }

  _renderReportsDateNav() {
    const bounds = energyPeriodBounds(this._reportsPeriod, this._reportsPeriodOffset);
    const label = energyPeriodNavLabel(this._reportsPeriod, this._reportsPeriodOffset);
    return `<div class="energy-date-nav">
<button type="button" data-action="reports-nav" data-dir="prev" aria-label="Previous period">‹</button>
<span class="energy-date-label">${esc(label)}</span>
<button type="button" data-action="reports-nav" data-dir="next" aria-label="Next period"${bounds.canNext ? "" : " disabled"}>›</button>
</div>`;
  }

  _renderReportsPeriodTabs() {
    const period = normalizeReportsPeriod(this._reportsPeriod);
    const tabs = REPORTS_PERIOD_TABS.map(
      (p) =>
        `<button type="button" data-action="reports-period" data-period="${p.id}" class="${p.id === period ? "active" : ""}">${p.label}</button>`
    ).join("");
    return `<div class="energy-period-tabs">${tabs}</div>`;
  }

  _normalizeReportsPeriodState() {
    const next = normalizeReportsPeriod(this._reportsPeriod);
    if (next !== this._reportsPeriod) {
      this._reportsPeriod = next;
      this._reportsPeriodOffset = 0;
      this._energyReport = null;
      this._energyReportPlantId = undefined;
    }
  }

  _energyReportCacheKey(plant) {
    return `${plant.entry_id}:reports:${this._reportsPeriod}:${this._reportsPeriodOffset}`;
  }

  async _loadEnergyReport() {
    const plant = this._getPlant();
    if (!plant || !this._hass || this._view !== "reports") return;
    this._normalizeReportsPeriodState();
    const cacheKey = this._energyReportCacheKey(plant);
    if (this._energyReportPlantId === cacheKey && this._energyReport) return;
    this._energyReportLoading = true;
    this._energyReport = null;
    this._energyReportPlantId = cacheKey;
    this._scheduleRender();
    try {
      if (!this._plantState) await this._refreshPlantState();
      this._energyReport = await fetchEnergyReportData(
        this._hass,
        plant,
        this._plantState,
        this._reportsPeriod,
        this._reportsPeriodOffset
      );
    } catch (err) {
      this._energyReport = {
        title: energyPeriodNavLabel(this._reportsPeriod, this._reportsPeriodOffset),
        error:
          err?.message ||
          "Could not load energy report. Enable the Home Assistant recorder and keep history for energy sensors.",
        analytics: null,
        chartSvg: "",
        detailRows: [],
      };
    } finally {
      this._energyReportLoading = false;
      if (this._energyReportCacheKey(this._getPlant()) === cacheKey && this._view === "reports") {
        this._scheduleRender();
      }
    }
  }

  _renderEnergyReportChartBody() {
    if (this._energyReportLoading) {
      return `<p class="chart-loading">Loading chart…</p>`;
    }
    if (this._energyReport?.error) {
      return `<p class="placeholder chart-empty">${esc(this._energyReport.error)}</p>`;
    }
    if (this._energyReport?.chartSvg) {
      return this._energyReport.chartSvg;
    }
    return `<p class="chart-loading">Loading chart…</p>`;
  }

  _renderEnergyReport(plant) {
    const title = energyBreakdownTitle(this._reportsPeriod, this._reportsPeriodOffset);
    const report = this._energyReport;
    const analytics =
      report?.analytics ||
      (report?.breakdown ? analyticsFromBreakdown(report.breakdown) : readLiveAnalytics(this._hass, plant, this._plantState, this._overviewDaily));
    const summaryHtml = analytics
      ? `<div class="fox-report-summary-row">
${renderEnergyReportBalanceCard(analytics)}
${renderEnergyReportPvDonutCard(analytics)}
${renderEnergyReportLoadDonutCard(analytics)}
</div>`
      : `<p class="placeholder chart-empty">${esc(report?.error || "Loading energy report…")}</p>`;
    const detailsHtml = report?.error
      ? ""
      : `<div class="card fox-report-details">
<h3 class="fox-report-details-title">Details</h3>
${this._energyReportLoading ? `<p class="chart-loading">Loading details…</p>` : renderEnergyReportDetailsTable(report?.detailRows || [])}
</div>`;
    return `<div data-energy-report-main="1" data-plant-id="${esc(plant.entry_id)}">
<header class="header"><h1>Energy Report</h1><p>${esc(title)}</p></header>
<div class="card fox-analysis-toolbar" data-energy-report-toolbar="1">
${this._renderReportsPeriodTabs()}
${this._renderReportsDateNav()}
</div>
${summaryHtml}
<div class="card fox-report-chart-card fox-analysis-chart-card" data-energy-report-chart="1">
<h3 class="fox-analysis-summary-title fox-analysis-chart-title">Energy Analysis</h3>
${this._renderEnergyReportChartBody()}
</div>
${detailsHtml}
</div>`;
  }

  _renderReports(plant) {
    if (this._reportsView === "octopus") {
      return this._renderOctopusEnergyAnalysis(plant);
    }
    if (this._reportsView === "smart_charge") {
      return this._renderSmartChargeAnalysisReport(plant);
    }
    return this._renderEnergyReport(plant);
  }

  _smartChargeAnalysisCacheKey(plant) {
    return `${plant.entry_id}:smart_charge_analysis:${this._reportsPeriod}:${this._reportsPeriodOffset}`;
  }

  async _loadSmartChargeAnalysis() {
    const plant = this._getPlant();
    if (!plant || !this._hass || this._view !== "reports" || this._reportsView !== "smart_charge") return;
    if (!smartChargeEnabled(this._plantState)) return;
    this._normalizeReportsPeriodState();
    const cacheKey = this._smartChargeAnalysisCacheKey(plant);
    if (this._smartChargeAnalysisPlantId === cacheKey && this._smartChargeAnalysis) return;
    this._smartChargeAnalysisLoading = true;
    this._smartChargeAnalysis = null;
    this._smartChargeAnalysisPlantId = cacheKey;
    this._scheduleRender();
    try {
      if (!this._plantState) await this._refreshPlantState();
      const result = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/fetch_smart_charge_analysis",
        plant_id: plant.entry_id,
        period: this._reportsPeriod,
        offset: this._reportsPeriodOffset,
      });
      if (result?.plant_state) this._plantState = result.plant_state;
      if (this._smartChargeAnalysisCacheKey(this._getPlant()) === cacheKey) {
        this._smartChargeAnalysis = result?.smart_charge_analysis || null;
      }
    } catch (err) {
      if (this._smartChargeAnalysisCacheKey(this._getPlant()) === cacheKey) {
        this._smartChargeAnalysis = {
          error:
            err?.message ||
            "Could not load SmartCharge analysis. Enable the recorder for smart charge and power sensors.",
        };
      }
    } finally {
      this._smartChargeAnalysisLoading = false;
      if (this._view === "reports" && this._reportsView === "smart_charge") {
        this._scheduleRender();
      }
    }
  }

  _renderSmartChargeAnalysisReport(plant) {
    if (!smartChargeEnabled(this._plantState)) {
      return renderSmartChargeAnalysisPage({ enabled: false });
    }
    const toolbar = `<div class="card fox-analysis-toolbar" data-smart-charge-report-toolbar="1">
${this._renderReportsPeriodTabs()}
${this._renderReportsDateNav()}
</div>`;
    const body = renderSmartChargeAnalysisPage(this._smartChargeAnalysis, {
      loading: this._smartChargeAnalysisLoading && !this._smartChargeAnalysis,
    });
    if (body.includes("data-smart-charge-analysis-main")) {
      return body.replace(
        "<header class=\"header\">",
        `${toolbar}<header class="header">`
      );
    }
    return `${toolbar}${body}`;
  }

  _octopusAnalysisCacheKey(plant) {
    const payload = octopusAnalysisPayload(this._plantState);
    return `${plant.entry_id}:octopus_analysis:${payload?.fetched_at || "none"}`;
  }

  async _loadOctopusAnalysis({ force = false } = {}) {
    const plant = this._getPlant();
    if (!plant || !this._hass || this._view !== "reports" || this._reportsView !== "octopus") return;
    if (!octopusTariffEnabled(this._plantState)) return;
    if (!force && octopusAnalysisPayload(this._plantState)) {
      return;
    }
    this._octopusAnalysisLoading = true;
    this._scheduleRender();
    try {
      if (!this._plantState) await this._refreshPlantState();
      const result = await this._hass.connection.sendMessagePromise({
        type: "foxess_plant/fetch_octopus_analysis",
        plant_id: plant.entry_id,
        force,
      });
      if (result?.plant_state) this._plantState = result.plant_state;
    } catch (err) {
      this._showToast(err?.message || "Could not refresh Octopus Energy Analysis", "err");
    } finally {
      this._octopusAnalysisLoading = false;
      if (this._view === "reports" && this._reportsView === "octopus") {
        this._scheduleRender();
      }
    }
  }

  _renderOctopusEnergyAnalysis(plant) {
    if (!octopusTariffEnabled(this._plantState)) {
      return renderOctopusEnergyAnalysisPage(null);
    }
    const payload = octopusAnalysisPayload(this._plantState);
    return renderOctopusEnergyAnalysisPage(payload, {
      loading: this._octopusAnalysisLoading && !payload,
      greenerView: this._octopusGreenerView,
    });
  }

  _bindReportsCharts() {
    const energyRoot = this._root.querySelector("[data-energy-report-chart]");
    if (energyRoot) bindMirroredEnergyChart(energyRoot);
    bindOctopusGreenerCharts(this._root);
  }

  _renderEnergyDateNav() {
    if (this._energyPeriod === "total") return "";
    const bounds = energyPeriodBounds(this._energyPeriod, this._energyPeriodOffset);
    const label = energyPeriodNavLabel(this._energyPeriod, this._energyPeriodOffset);
    return `<div class="energy-date-nav">
<button type="button" data-action="energy-nav" data-dir="prev" aria-label="Previous period">‹</button>
<span class="energy-date-label">${esc(label)}</span>
<button type="button" data-action="energy-nav" data-dir="next" aria-label="Next period"${bounds.canNext ? "" : " disabled"}>›</button>
</div>`;
  }

  _energyAnalyticsForView(plant) {
    if (this._energyBreakdown) return analyticsFromBreakdown(this._energyBreakdown);
    const live = readLiveAnalytics(this._hass, plant, this._plantState, this._overviewDaily);
    return live;
  }

  _renderEnergyQuickStatsRow(a) {
    return `<div class="stats-row overview-energy-stats-row">
${this._stat("Load", a.load_consumption_kwh_today, " kWh")}
${this._stat("From grid", a.load_from_grid_kwh_today, " kWh")}
${this._stat("PV today", a.pv_production_kwh_today, " kWh")}
${this._stat("PV → grid", a.pv_to_grid_kwh_today, " kWh")}
</div>`;
  }

  _renderEnergyBalanceCard(a, { inBand = false } = {}) {
    const bandClass = inBand ? " overview-energy-balance-card" : "";
    const bandStyle = inBand ? "" : ' style="margin-top:14px"';
    const daily = this._overviewDaily;
    const loading = this._overviewDailyLoading;
    const chargeVal = Number(a.battery_charge_kwh_today ?? 0) || 0;
    const dischargeVal = Number(a.battery_discharge_kwh_today ?? 0) || 0;
    const chargeSpark = renderOverviewBalanceSpark(
      daily?.batteryChargeSpark,
      OVERVIEW_BALANCE_SPARK_COLORS.charge,
      chargeVal,
      loading
    );
    const dischargeSpark = renderOverviewBalanceSpark(
      daily?.batteryDischargeSpark,
      OVERVIEW_BALANCE_SPARK_COLORS.discharge,
      dischargeVal,
      loading
    );
    return `<div class="card${bandClass}"${bandStyle}><p class="card-title">Balance</p>
<div class="overview-balance-panel">
${renderOverviewBalanceMetric("Battery charge", a.battery_charge_kwh_today, chargeSpark)}
${renderOverviewBalanceMetric("Battery discharge", a.battery_discharge_kwh_today, dischargeSpark)}
</div></div>`;
  }

  _renderEnergyBreakdownRows(a, title, { extraClass = "" } = {}) {
    return `<div class="card breakdown-card${extraClass ? ` ${extraClass}` : ""}">
<p class="card-title">${esc(title)}</p>
<div class="fox-energy-panel">${buildEnergyBreakdownPvRow(a)}${buildEnergyBreakdownLoadRow(a)}</div>
</div>`;
  }

  _overviewBreakdownSlotKey(plant) {
    if (this._overviewDailyLoading && !this._plantState?.analytics) return "loading";
    const a = readLiveAnalytics(this._hass, plant, this._plantState, this._overviewDaily);
    return [
      a.pv_production_kwh_today,
      a.pv_to_load_battery_kwh_today,
      a.pv_to_grid_kwh_today,
      a.load_consumption_kwh_today,
      a.load_from_pv_battery_kwh_today,
      a.load_from_grid_kwh_today,
      a.self_consumption_percent_today,
      a.self_sufficiency_percent_today,
    ].join("|");
  }

  _overviewSummarySlotKey(plant) {
    if (this._overviewDailyLoading && !this._plantState?.analytics) return "loading";
    const a = readLiveAnalytics(this._hass, plant, this._plantState, this._overviewDaily);
    const d = this._overviewDaily;
    return [
      a.load_consumption_kwh_today,
      a.load_from_grid_kwh_today,
      a.pv_production_kwh_today,
      a.pv_to_grid_kwh_today,
      a.battery_charge_kwh_today,
      a.battery_discharge_kwh_today,
      (d?.batteryChargeSpark || []).join(","),
      (d?.batteryDischargeSpark || []).join(","),
    ].join("|");
  }

  _overviewEnergyBandKey(plant) {
    return `${this._overviewBreakdownSlotKey(plant)}|${this._overviewSummarySlotKey(plant)}`;
  }

  _renderOverviewEnergyBreakdown(plant) {
    if (this._overviewDailyLoading && !this._plantState?.analytics) {
      return `<div class="card breakdown-card overview-energy-breakdown"><p class="chart-loading">Loading breakdown…</p></div>`;
    }
    const a = readLiveAnalytics(this._hass, plant, this._plantState, this._overviewDaily);
    return this._renderEnergyBreakdownRows(a, "Today energy breakdown", {
      extraClass: "overview-energy-breakdown",
    });
  }

  _renderOverviewEnergyBand(plant) {
    if (this._overviewDailyLoading && !this._plantState?.analytics) {
      return `<div class="overview-energy-band"><p class="chart-loading">Loading energy data…</p></div>`;
    }
    const a = readLiveAnalytics(this._hass, plant, this._plantState, this._overviewDaily);
    return `<div class="overview-energy-band">
${this._renderOverviewEnergyBreakdown(plant)}
${this._renderEnergyQuickStatsRow(a)}
${this._renderEnergyBalanceCard(a, { inBand: true })}
</div>`;
  }

  _analysisTariffForCard() {
    if (this._view === "energy_analysis" && this._energyPeriod === "day" && this._analysisPeriodTariff?.configured) {
      return this._analysisPeriodTariff;
    }
    return this._analysisTariffDaily;
  }

  _energyAnalysisSummaryKey(a) {
    if (this._analysisSummarySparkLoading) return "spark:loading";
    const spark = this._analysisSummarySpark;
    const t = this._analysisTariffForCard();
    if (spark?.error) return `spark:err:${spark.error}`;
    const prod = (spark?.production || []).join(",");
    const cons = (spark?.consumption || []).join(",");
    const tariffPart = t?.configured
      ? [
          t.totals?.importCost,
          t.totals?.exportRevenue,
          t.totals?.totalCost,
          (t.series?.importCost || []).join(","),
          (t.series?.exportRevenue || []).join(","),
          (t.series?.totalCost || []).join(","),
        ].join("|")
      : String(t?.configured);
    return `${this._energyPeriod}|${this._energyPeriodOffset}|${prod}|${cons}|${tariffPart}|${a.pv_production_kwh_today}|${a.load_consumption_kwh_today}|${a.load_from_grid_kwh_today}|${a.pv_to_grid_kwh_today}`;
  }

  _analysisSummarySparkCacheKey(plant) {
    const base = `${plant.entry_id}:${this._energyPeriod}:${this._energyPeriodOffset}:spark`;
    if (this._energyPeriod === "day") {
      const bucket = Math.floor(Date.now() / (5 * 60 * 1000));
      return `${base}:${bucket}`;
    }
    return base;
  }

  async _loadAnalysisSummarySpark() {
    const plant = this._getPlant();
    if (!plant || !this._hass) return;
    const cacheKey = this._analysisSummarySparkCacheKey(plant);
    if (this._analysisSummarySparkKey === cacheKey && this._analysisSummarySpark && !this._analysisSummarySpark.error) {
      return;
    }
    this._analysisSummarySparkLoading = true;
    this._analysisSummarySparkKey = cacheKey;
    this._energyAnalysisSummaryCache = undefined;
    this._scheduleRender();
    try {
      if (!this._plantState) await this._refreshPlantState();
      this._analysisSummarySpark = await fetchAnalysisSummarySparkData(
        this._hass,
        plant,
        this._plantState,
        this._energyPeriod,
        this._energyPeriodOffset
      );
      this._analysisPeriodTariff = null;
      if (this._plantState?.tariff?.configured && this._energyPeriod === "day") {
        const now = new Date();
        const bounds = energyPeriodBounds("day", this._energyPeriodOffset, now);
        const fetchEnd = bounds.end > now ? now : bounds.end;
        this._analysisPeriodTariff = await fetchAnalysisTariffIntraday(
          this._hass,
          plant,
          this._plantState,
          this._overviewDaily,
          { start: bounds.start, end: fetchEnd }
        );
      }
    } catch (err) {
      this._analysisSummarySpark = {
        error:
          err?.message ||
          "Could not load energy history for sparklines. Enable the Home Assistant recorder for daily kWh sensors.",
        production: [],
        consumption: [],
      };
    } finally {
      this._analysisSummarySparkLoading = false;
      if (this._analysisSummarySparkCacheKey(this._getPlant()) === cacheKey) {
        this._energyAnalysisSummaryCache = undefined;
        this._scheduleRender();
      }
    }
  }

  _forecastAccuracyReportCacheKey(plant, dayOffset = 0) {
    const base = `${plant.entry_id}:${dayOffset}:forecast-accuracy`;
    if (dayOffset === 0) {
      const bucket = Math.floor(Date.now() / (5 * 60 * 1000));
      const sc = this._plantState?.solcast;
      const solcastRev =
        sc?.pv_forecast_fetched_at || sc?.updated_at || sc?.forecast_intraday_points?.length || 0;
      return `${base}:${bucket}:${solcastRev}`;
    }
    return base;
  }

  _forecastAccuracyOverviewCacheKey(plant) {
    return this._forecastAccuracyReportCacheKey(plant, 0);
  }

  _syncForecastAccuracyToday(plant, result, dayOffset) {
    if (!plant || dayOffset !== 0 || !result || result.error) return;
    const todayKey = this._forecastAccuracyOverviewCacheKey(plant);
    this._forecastAccuracyOverview = result;
    this._forecastAccuracyOverviewKey = todayKey;
    if (this._energyPeriod === "day" && this._energyPeriodOffset === 0) {
      this._forecastAccuracyAnalysis = result;
      this._forecastAccuracyAnalysisKey = this._forecastAccuracyAnalysisCacheKey(plant);
    }
    this._energyAnalysisChartSlotCache = undefined;
  }

  _forecastAccuracyForOverview() {
    const overview = this._forecastAccuracyOverview;
    if (this._forecastAccuracyOverviewLoading) {
      return { report: overview, loading: true };
    }
    if (overview && !overview.error) {
      return { report: overview, loading: false };
    }
    const analysis = this._forecastAccuracyAnalysis;
    if (analysis && !analysis.error && analysis.is_today) {
      return { report: analysis, loading: this._forecastAccuracyAnalysisLoading };
    }
    return { report: overview, loading: false };
  }

  _forecastAccuracyAnalysisCacheKey(plant) {
    return this._forecastAccuracyReportCacheKey(plant, this._energyPeriodOffset);
  }

  _forecastAccuracyHasChartData(report) {
    const intraday = report?.intraday;
    return (
      (intraday?.actual_power_kw?.length ?? 0) >= 2 ||
      (intraday?.predicted_power_kw?.length ?? 0) >= 2
    );
  }

  _storeForecastAccuracyAnalysisCache(cacheKey, result) {
    if (!cacheKey || !result || result.error || !this._forecastAccuracyHasChartData(result)) return;
    if (!this._forecastAccuracyAnalysisCache) this._forecastAccuracyAnalysisCache = new Map();
    this._forecastAccuracyAnalysisCache.set(cacheKey, result);
    if (this._forecastAccuracyAnalysisCache.size > 16) {
      const oldest = this._forecastAccuracyAnalysisCache.keys().next().value;
      this._forecastAccuracyAnalysisCache.delete(oldest);
    }
  }

  _beginForecastAccuracyAnalysisLoad() {
    if (this._energyPeriod !== "day") return;
    const plant = this._getPlant();
    if (!plant || !this._hass || !statisticsSolcastForecastEnabled(this._plantState, this._hass)) return;
    const cacheKey = this._forecastAccuracyAnalysisCacheKey(plant);
    const cached = this._forecastAccuracyAnalysisCache?.get(cacheKey);
    this._forecastAccuracyAnalysisSlotCache = undefined;
    this._forecastAccuracyAnalysisInflight = null;
    this._forecastAccuracyAnalysisInflightKey = undefined;
    if (cached && this._forecastAccuracyHasChartData(cached)) {
      this._forecastAccuracyAnalysis = cached;
      this._forecastAccuracyAnalysisKey = cacheKey;
      this._forecastAccuracyAnalysisLoading = false;
      return;
    }
    this._forecastAccuracyAnalysis = null;
    this._forecastAccuracyAnalysisKey = undefined;
    this._forecastAccuracyAnalysisLoading = true;
    this._forecastAccuracyLoadGen += 1;
    void this._loadForecastAccuracyAnalysis(this._forecastAccuracyLoadGen);
  }

  _octopusGreenerSlotKey() {
    if (!octopusTariffEnabled(this._plantState)) return "disabled";
    const payload = octopusGreenerPayload(this._plantState);
    return [
      this._energyPeriod,
      this._energyPeriodOffset,
      this._octopusGreenerView,
      payload?.fetched_at ?? "",
      payload?.carbon_periods?.length ?? 0,
      payload?.greener_nights?.length ?? 0,
      payload?.title ?? "",
    ].join(":");
  }

  _octopusUpcomingWeekSlotKey() {
    if (!octopusTariffEnabled(this._plantState)) return "disabled";
    const payload = octopusGreenerPayload(this._plantState);
    const rows = octopusUpcomingWeekRows(payload?.greener_nights ?? []);
    return [
      payload?.fetched_at ?? "",
      rows.map((r) => `${r.date}:${r.is_greener_night ? 1 : 0}:${r.greenness_score ?? ""}`).join("|"),
    ].join(":");
  }

  _forecastAccuracyAnalysisSlotKey() {
    if (this._energyPeriod !== "day") return "hidden";
    if (!statisticsSolcastForecastEnabled(this._plantState, this._hass)) return "disabled";
    if (this._forecastAccuracyAnalysisLoading) {
      return `loading:${this._energyPeriodOffset}:${this._forecastAccuracyAnalysisKey ?? ""}`;
    }
    const report = this._forecastAccuracyAnalysis;
    if (report?.error) return `err:${this._energyPeriodOffset}:${report.error}`;
    return [
      this._energyPeriodOffset,
      this._forecastAccuracyAnalysisKey ?? "",
      report?.day ?? "",
      report?.actual_kwh ?? "",
      report?.predicted_kwh ?? "",
      report?.error_kwh ?? "",
      report?.revision_count ?? 0,
      report?.intraday?.actual_power_kw?.length ?? 0,
      report?.intraday?.predicted_power_kw?.length ?? 0,
      report?.intraday?.cloud_coverage_pct?.length ?? 0,
      (report?.revisions || []).map((r) => `${r.fetched_at_ms}:${r.forecast_today_kwh}`).join("|"),
    ].join(":");
  }

  async _loadForecastAccuracyOverview() {
    const plant = this._getPlant();
    if (!plant || !this._hass || !statisticsSolcastForecastEnabled(this._plantState, this._hass)) return;
    const cacheKey = this._forecastAccuracyOverviewCacheKey(plant);
    if (this._forecastAccuracyOverviewKey === cacheKey) return;
    if (this._forecastAccuracyOverviewInflight) return this._forecastAccuracyOverviewInflight;
    this._forecastAccuracyOverviewLoading = true;
    this._scheduleRender();
    this._forecastAccuracyOverviewInflight = (async () => {
      try {
        if (!this._plantState) await this._refreshPlantState();
        const result = await fetchForecastAccuracyReport(this._hass, plant, 0);
        if (this._forecastAccuracyOverviewCacheKey(this._getPlant()) !== cacheKey) return;
        this._forecastAccuracyOverview = result;
        this._forecastAccuracyOverviewKey = cacheKey;
        if (result && !result.error) {
          this._syncForecastAccuracyToday(plant, result, 0);
        } else {
          this._energyAnalysisChartSlotCache = undefined;
        }
      } catch (err) {
        if (this._forecastAccuracyOverviewCacheKey(this._getPlant()) !== cacheKey) return;
        this._forecastAccuracyOverview = {
          error: err?.message || "Failed to load forecast accuracy",
          solcast_enabled: true,
        };
        this._forecastAccuracyOverviewKey = cacheKey;
      } finally {
        this._forecastAccuracyOverviewLoading = false;
        this._forecastAccuracyOverviewInflight = null;
        if (this._forecastAccuracyOverviewCacheKey(this._getPlant()) === cacheKey) {
          this._scheduleRender();
        }
      }
    })();
    return this._forecastAccuracyOverviewInflight;
  }

  async _loadForecastAccuracyAnalysis(loadGen = this._forecastAccuracyLoadGen) {
    const plant = this._getPlant();
    if (
      !plant ||
      !this._hass ||
      this._energyPeriod !== "day" ||
      !statisticsSolcastForecastEnabled(this._plantState, this._hass)
    ) {
      return;
    }
    const cacheKey = this._forecastAccuracyAnalysisCacheKey(plant);
    if (
      this._forecastAccuracyAnalysisKey === cacheKey &&
      this._forecastAccuracyHasChartData(this._forecastAccuracyAnalysis)
    ) {
      this._forecastAccuracyAnalysisLoading = false;
      return;
    }
    if (
      this._forecastAccuracyAnalysisInflight &&
      this._forecastAccuracyAnalysisInflightKey === cacheKey
    ) {
      return this._forecastAccuracyAnalysisInflight;
    }
    this._forecastAccuracyAnalysisInflightKey = cacheKey;
    this._forecastAccuracyAnalysisLoading = true;
    this._forecastAccuracyAnalysisSlotCache = undefined;
    this._scheduleRender();
    this._forecastAccuracyAnalysisInflight = (async () => {
      try {
        if (!this._plantState) await this._refreshPlantState();
        const result = await fetchForecastAccuracyReport(
          this._hass,
          plant,
          this._energyPeriodOffset
        );
        if (loadGen !== this._forecastAccuracyLoadGen) return;
        if (this._forecastAccuracyAnalysisCacheKey(this._getPlant()) !== cacheKey) return;
        this._forecastAccuracyAnalysis = result;
        this._forecastAccuracyAnalysisKey = cacheKey;
        if (result && !result.error) {
          this._storeForecastAccuracyAnalysisCache(cacheKey, result);
          this._syncForecastAccuracyToday(plant, result, this._energyPeriodOffset);
        } else {
          this._energyAnalysisChartSlotCache = undefined;
        }
      } catch (err) {
        if (loadGen !== this._forecastAccuracyLoadGen) return;
        if (this._forecastAccuracyAnalysisCacheKey(this._getPlant()) !== cacheKey) return;
        this._forecastAccuracyAnalysis = {
          error: err?.message || "Failed to load forecast accuracy",
          solcast_enabled: true,
        };
        this._forecastAccuracyAnalysisKey = cacheKey;
      } finally {
        if (this._forecastAccuracyAnalysisInflightKey === cacheKey) {
          this._forecastAccuracyAnalysisInflight = null;
          this._forecastAccuracyAnalysisInflightKey = undefined;
        }
        if (loadGen !== this._forecastAccuracyLoadGen) return;
        this._forecastAccuracyAnalysisLoading = false;
        this._forecastAccuracyAnalysisSlotCache = undefined;
        if (this._forecastAccuracyAnalysisCacheKey(this._getPlant()) === cacheKey) {
          this._scheduleRender(true);
        }
      }
    })();
    return this._forecastAccuracyAnalysisInflight;
  }

  _energyAnalysisChartSlotKey() {
    if (this._energyPeriod === "day") {
      const offsetPart = `offset:${this._energyPeriodOffset}|`;
      if (this._statisticsChartLoading) return `${offsetPart}stat:loading`;
      const chart = this._statisticsChart;
      if (chart?.error) return `${offsetPart}stat:err:${chart.error}`;
      if (chart?.empty) return `${offsetPart}stat:empty:${chart.empty}`;
      if (!chart?.series?.length && !chart?.socSeries?.points?.length) return `${offsetPart}stat:none`;
      const socLen = chart?.socSeries?.points?.length ?? 0;
      const forecastPart = this._forecastStatisticsSlotPart();
      return `${offsetPart}stat:${this._statisticsChartPlantId ?? ""}|soc:${socLen}|${forecastPart}`;
    }
    if (this._energyChartLoading) return "energy:loading";
    return `energy:${this._energyChartPlantId ?? ""}|${this._energyChart?.svg ? 1 : 0}|${this._energyChart?.error ?? ""}`;
  }

  _energyAnalysisToolbarKey() {
    return `${this._energyPeriod}|${this._energyPeriodOffset}`;
  }

  _patchFoxAnalysisSummaryValues(root, a, period = this._energyPeriod) {
    const periodLabel = energyPeriodSummaryLabel(period);
    const pvVal = Number(a.pv_production_kwh_today ?? 0) || 0;
    const loadVal = Number(a.load_consumption_kwh_today ?? 0) || 0;
    const prodLabel = root.querySelector('[data-summary-label="production"]');
    const consLabel = root.querySelector('[data-summary-label="consumption"]');
    if (prodLabel) prodLabel.textContent = `${periodLabel} Production`;
    if (consLabel) consLabel.textContent = `${periodLabel} Consumption`;
    const prodEl = root.querySelector('[data-summary-value="production"]');
    const consEl = root.querySelector('[data-summary-value="consumption"]');
    if (prodEl) prodEl.innerHTML = `${pvVal.toFixed(2)}<span>kWh</span>`;
    if (consEl) consEl.innerHTML = `${loadVal.toFixed(2)}<span>kWh</span>`;
    const tariffState = this._plantState?.tariff;
    if (!tariffState?.configured && !this._analysisTariffForCard()?.configured) return;
    const rates = tariffEffectiveRates(tariffState || {});
    const importKwh = Number(a.load_from_grid_kwh_today ?? 0) || 0;
    const exportKwh = Number(a.pv_to_grid_kwh_today ?? 0) || 0;
    const currency = tariffCurrencyFromTariff(tariffState || {});
    const importCost = importKwh * minorToMajor(rates.import_p_per_kwh, currency);
    const exportRevenue = exportKwh * minorToMajor(rates.export_p_per_kwh, currency);
    const standing = minorToMajor(rates.standing_charge_p_per_day, currency);
    const totalCost = standing + importCost - exportRevenue;
    const exportEl = root.querySelector('[data-summary-value="export_revenue"]');
    const importEl = root.querySelector('[data-summary-value="import_cost"]');
    const totalEl = root.querySelector('[data-summary-value="total_cost"]');
    const exportMoney = formatTariffMoneyDisplay(exportRevenue, currency);
    const importMoney = formatTariffMoneyDisplay(importCost, currency);
    const totalMoney = formatTariffMoneyDisplay(totalCost, currency);
    if (exportEl) {
      exportEl.innerHTML = `${exportMoney.value}${exportMoney.unit ? `<span>${esc(exportMoney.unit.trim())}</span>` : ""}`;
    }
    if (importEl) {
      importEl.innerHTML = `${importMoney.value}${importMoney.unit ? `<span>${esc(importMoney.unit.trim())}</span>` : ""}`;
    }
    if (totalEl) {
      totalEl.innerHTML = `${totalMoney.value}${totalMoney.unit ? `<span>${esc(totalMoney.unit.trim())}</span>` : ""}`;
    }
  }

  _patchFoxAnalysisStatValues(root, a) {
    const values = [
      a.load_from_grid_kwh_today,
      a.pv_production_kwh_today,
      a.battery_discharge_kwh_today,
      a.pv_to_grid_kwh_today,
      a.load_consumption_kwh_today,
      a.battery_charge_kwh_today,
    ];
    root.querySelectorAll(".fox-analysis-stat-col-nu").forEach((el, i) => {
      const v = Number(values[i] ?? 0) || 0;
      el.innerHTML = `${v.toFixed(2)}<span>kWh</span>`;
    });
  }

  _patchEnergyAnalysisMainIfNeeded() {
    if (this._view !== "energy_analysis" || !this._hass) return false;
    const root = this._root.querySelector("[data-energy-analysis-main]");
    if (!root) return false;
    const plant = this._getPlant();
    if (!plant || root.dataset.plantId !== plant.entry_id) return false;

    const a = this._energyAnalyticsForView(plant);
    const title = energyBreakdownTitle(this._energyPeriod, this._energyPeriodOffset);
    const sub = root.querySelector(".header p");
    if (sub) sub.textContent = title;

    const toolbarKey = this._energyAnalysisToolbarKey();
    if (toolbarKey !== this._energyAnalysisToolbarCache) {
      const toolbar = root.querySelector("[data-energy-analysis-toolbar]");
      if (toolbar) {
        toolbar.innerHTML = `${this._renderEnergyPeriodTabs()}${this._renderEnergyDateNav()}`;
      }
      this._energyAnalysisToolbarCache = toolbarKey;
      if (this._energyPeriod === "day") {
        this._energyAnalysisChartSlotCache = undefined;
        if (!this._statisticsChartLoading && this._statisticsChartNeedsReload(plant)) {
          this._statisticsChart = null;
          this._statisticsChartPlantId = undefined;
          void this._loadStatisticsChart();
        }
      }
    }

    const top = root.querySelector("[data-energy-analysis-top]");
    if (top) {
      if (top.querySelector("[data-energy-split-card]")) {
        patchFoxAnalysisTopCardsEl(top, a);
      } else {
        top.innerHTML = renderFoxAnalysisTopCards(a);
      }
    }

    this._patchFoxAnalysisStatValues(root, a);

    const summaryKey = this._energyAnalysisSummaryKey(a);
    const summary = root.querySelector("[data-energy-analysis-summary]");
    if (summaryKey !== this._energyAnalysisSummaryCache) {
      if (summary) {
        summary.innerHTML = renderFoxAnalysisSummaryCard(a, this._analysisSummarySpark, this._analysisTariffForCard(), {
          loading: this._analysisSummarySparkLoading,
          period: this._energyPeriod,
        });
      }
      this._energyAnalysisSummaryCache = summaryKey;
    } else {
      this._patchFoxAnalysisSummaryValues(root, a);
    }

    const greenerKey = this._octopusGreenerSlotKey();
    if (greenerKey !== this._octopusGreenerAnalysisSlotCache) {
      let greenerRow = root.querySelector("[data-energy-analysis-greener]");
      const showGreener =
        octopusTariffEnabled(this._plantState) &&
        (this._energyPeriod === "day" || this._energyPeriod === "week");
      if (showGreener) {
        const html = renderOctopusGreenerNightsCard(octopusGreenerPayload(this._plantState), {
          compact: false,
          view: this._octopusGreenerView,
          energyPeriod: this._energyPeriod,
          energyPeriodOffset: this._energyPeriodOffset,
        });
        if (html) {
          if (greenerRow) {
            greenerRow.innerHTML = html;
          } else {
            const forecastRow = root.querySelector("[data-energy-analysis-forecast]");
            const panels = root.querySelector(".fox-analysis-panels-row");
            const wrap = document.createElement("div");
            wrap.className = "fox-analysis-octopus-greener-row";
            wrap.dataset.energyAnalysisGreener = "1";
            wrap.innerHTML = html;
            if (forecastRow) forecastRow.before(wrap);
            else if (panels) panels.after(wrap);
          }
        } else if (greenerRow) {
          greenerRow.remove();
        }
      } else if (greenerRow) {
        greenerRow.remove();
      }
      this._octopusGreenerAnalysisSlotCache = greenerKey;
      bindOctopusGreenerCharts(root);
    }

    const upcomingKey = this._octopusUpcomingWeekSlotKey();
    if (upcomingKey !== this._octopusUpcomingWeekAnalysisSlotCache) {
      let upcomingRow = root.querySelector("[data-energy-analysis-upcoming-week]");
      const showUpcoming =
        octopusTariffEnabled(this._plantState) &&
        (this._energyPeriod === "day" || this._energyPeriod === "week");
      if (showUpcoming) {
        const html = renderOctopusUpcomingWeekCard(octopusGreenerPayload(this._plantState));
        if (html) {
          if (upcomingRow) {
            upcomingRow.innerHTML = html;
          } else {
            const forecastRow = root.querySelector("[data-energy-analysis-forecast]");
            const greenerRow = root.querySelector("[data-energy-analysis-greener]");
            const panels = root.querySelector(".fox-analysis-panels-row");
            const wrap = document.createElement("div");
            wrap.className = "fox-analysis-octopus-upcoming-row";
            wrap.dataset.energyAnalysisUpcomingWeek = "1";
            wrap.innerHTML = html;
            if (forecastRow) forecastRow.before(wrap);
            else if (greenerRow) greenerRow.after(wrap);
            else if (panels) panels.after(wrap);
          }
        } else if (upcomingRow) {
          upcomingRow.remove();
        }
      } else if (upcomingRow) {
        upcomingRow.remove();
      }
      this._octopusUpcomingWeekAnalysisSlotCache = upcomingKey;
    }

    const forecastKey = this._forecastAccuracyAnalysisSlotKey();
    if (forecastKey !== this._forecastAccuracyAnalysisSlotCache) {
      let forecastRow = root.querySelector("[data-energy-analysis-forecast]");
      if (this._energyPeriod === "day" && statisticsSolcastForecastEnabled(this._plantState, this._hass)) {
        const html = renderForecastAccuracyCard(this._forecastAccuracyAnalysis, {
          compact: false,
          loading: this._forecastAccuracyAnalysisLoading,
          period: this._energyPeriod,
        });
        if (html) {
          if (forecastRow) {
            forecastRow.innerHTML = html;
          } else {
            const panels = root.querySelector(".fox-analysis-panels-row");
            const chartRow = root.querySelector("[data-energy-analysis-chart]");
            const wrap = document.createElement("div");
            wrap.className = "fox-analysis-forecast-accuracy-row";
            wrap.dataset.energyAnalysisForecast = "1";
            wrap.innerHTML = html;
            if (chartRow) chartRow.before(wrap);
            else if (panels) panels.after(wrap);
          }
        } else if (forecastRow) {
          forecastRow.remove();
        }
      } else if (forecastRow) {
        forecastRow.remove();
      }
      this._forecastAccuracyAnalysisSlotCache = forecastKey;
    }

    let chartUpdated = false;
    const chartKey = this._energyAnalysisChartSlotKey();
    if (chartKey !== this._energyAnalysisChartSlotCache) {
      const chart = root.querySelector("[data-energy-analysis-chart]");
      if (chart) chart.innerHTML = this._renderEnergyAnalysisCharts();
      this._energyAnalysisChartSlotCache = chartKey;
      chartUpdated = true;
    }

    if (
      chartUpdated &&
      this._energyPeriod === "day" &&
      this._statisticsChart?.series
    ) {
      this._bindStatisticsChart();
    }

    return true;
  }

  _renderEnergyAnalysisCharts() {
    let body;
    if (this._energyPeriod === "day") {
      body = this._renderStatisticsChartBody({ sideLegend: true, includeSoc: true });
    } else if (this._energyChartLoading) {
      body = `<p class="chart-loading">Loading chart…</p>`;
    } else if (this._energyChart?.error) {
      body = `<p class="placeholder chart-empty">${esc(this._energyChart.error)}</p>`;
    } else if (this._energyChart?.svg) {
      body = this._energyChart.svg;
    } else {
      body = `<p class="chart-loading">Loading chart…</p>`;
    }
    return `<div class="fox-analysis-chart-card">
<h3 class="fox-analysis-summary-title fox-analysis-chart-title">Statistics</h3>
${body}
</div>`;
  }

  _syncEnergyBalanceHelpModal(shell) {
    if (!shell) return;
    shell.querySelector("[data-energy-balance-help-modal]")?.remove();
    if (!this._energyBalanceHelpOpen) return;
    const wrap = document.createElement("div");
    wrap.innerHTML = renderEnergyBalanceHelpModal();
    const modal = wrap.firstElementChild;
    if (modal) shell.appendChild(modal);
  }

  _syncFoxAlarmDetailModal(shell) {
    if (!shell) return;
    shell.querySelector("[data-fox-alarm-detail-modal]")?.remove();
    if (!this._foxAlarmDetailName || !this._hass) return;
    const plant = this._getPlant();
    if (!plant) return;
    const map = resolveEntityMap(this._hass, plant, this._plantState);
    const wrap = document.createElement("div");
    wrap.innerHTML = renderFoxAlarmDetailModal(this._foxAlarmDetailName, {
      hass: this._hass,
      map,
      esc,
    });
    const modal = wrap.firstElementChild;
    if (modal) shell.appendChild(modal);
  }

  _renderEnergyAnalysis(plant) {
    const a = this._energyAnalyticsForView(plant);
    const title = energyBreakdownTitle(this._energyPeriod, this._energyPeriodOffset);
    const summaryCard = renderFoxAnalysisSummaryCard(a, this._analysisSummarySpark, this._analysisTariffForCard(), {
      loading: this._analysisSummarySparkLoading,
      period: this._energyPeriod,
    });
    this._energyAnalysisSummaryCache = this._energyAnalysisSummaryKey(a);
    this._energyAnalysisChartSlotCache = this._energyAnalysisChartSlotKey();
    this._energyAnalysisToolbarCache = this._energyAnalysisToolbarKey();
    this._forecastAccuracyAnalysisSlotCache = this._forecastAccuracyAnalysisSlotKey();
    const greenerPayload = octopusGreenerPayload(this._plantState);
    const octopusGreenerCard =
      octopusTariffEnabled(this._plantState) &&
      (this._energyPeriod === "day" || this._energyPeriod === "week")
        ? `<div class="fox-analysis-octopus-greener-row" data-energy-analysis-greener="1">${renderOctopusGreenerNightsCard(
            greenerPayload,
            {
              compact: false,
              view: this._octopusGreenerView,
              energyPeriod: this._energyPeriod,
              energyPeriodOffset: this._energyPeriodOffset,
            }
          )}</div>`
        : "";
    const octopusUpcomingWeekCard =
      octopusTariffEnabled(this._plantState) &&
      (this._energyPeriod === "day" || this._energyPeriod === "week")
        ? `<div class="fox-analysis-octopus-upcoming-row" data-energy-analysis-upcoming-week="1">${renderOctopusUpcomingWeekCard(
            greenerPayload
          )}</div>`
        : "";
    const forecastCard =
      this._energyPeriod === "day" && statisticsSolcastForecastEnabled(this._plantState, this._hass)
        ? `<div class="fox-analysis-forecast-accuracy-row" data-energy-analysis-forecast="1">${renderForecastAccuracyCard(this._forecastAccuracyAnalysis, {
            compact: false,
            loading: this._forecastAccuracyAnalysisLoading,
            period: this._energyPeriod,
          })}</div>`
        : "";
    return `<div data-energy-analysis-main="1" data-plant-id="${esc(plant.entry_id)}">
<header class="header"><h1>Energy Analysis</h1><p>${esc(title)}</p></header>
<div class="card fox-analysis-toolbar" data-energy-analysis-toolbar="1">
${this._renderEnergyPeriodTabs()}
${this._renderEnergyDateNav()}
</div>
<div data-energy-analysis-top="1">${renderFoxAnalysisTopCards(a)}</div>
<div class="fox-analysis-panels-row">
<div class="fox-analysis-panel-card" data-energy-analysis-supply="1">${renderFoxSupplyUsagePanel(a)}</div>
<div class="fox-analysis-panel-card" data-energy-analysis-summary="1">${summaryCard}</div>
</div>
${octopusGreenerCard}
${octopusUpcomingWeekCard}
${forecastCard}
<div class="fox-analysis-chart-row" data-energy-analysis-chart="1">
${this._renderEnergyAnalysisCharts()}
</div>
</div>`;
  }

  _renderPeriodCard(idx, period, fieldPrefix = "period", titlePrefix = "Period") {
    const p = period || DEFAULT_PERIODS[0];
    const actual = fieldPrefix === "period" ? this._plantState?.actual_periods?.[idx] : null;
    const drift =
      actual &&
      (Boolean(p.enable_force_charge) !== Boolean(actual.enable_force_charge) ||
        Boolean(p.enable_charge_from_grid) !== Boolean(actual.enable_charge_from_grid));
    return `<div class="period-card">
<h4>${titlePrefix} ${idx + 1} ${drift ? '<span style="color:var(--fp-amber);font-size:12px">≠ inverter</span>' : ""}</h4>
<div class="toggle-row"><span>Force charge</span><input type="checkbox" data-field="${fieldPrefix}:${idx}:enable_force_charge" ${p.enable_force_charge ? "checked" : ""}></div>
<div class="toggle-row"><span>Charge from grid</span><input type="checkbox" data-field="${fieldPrefix}:${idx}:enable_charge_from_grid" ${p.enable_charge_from_grid ? "checked" : ""}></div>
<div class="period-times">
<div class="field"><label>Start</label><input type="time" data-field="${fieldPrefix}:${idx}:start" value="${esc(timeForInput(p.start))}"></div>
<div class="field"><label>End</label><input type="time" data-field="${fieldPrefix}:${idx}:end" value="${esc(timeForInput(p.end))}"></div>
</div>
</div>`;
  }

  _triggerRowId(entityId) {
    return `tr-${String(entityId).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  }

  _getFilteredTriggerRows() {
    const all = this._triggerCandidates ?? [];
    const filter = (this._triggerFilter || "").trim().toLowerCase();
    let rows = all;
    if (filter) {
      rows = all.filter((row) => {
        const blob = `${row.entity_id} ${row.name}`.toLowerCase();
        return blob.includes(filter);
      });
    } else if (this._triggerGoogleOnly) {
      const gw = all.filter((row) => row.provider === "google_weather");
      rows = gw.length ? gw : all.filter((row) => row.suggested);
    } else if (!this._triggerShowAll) {
      const suggested = all.filter((row) => row.suggested);
      rows = suggested.length ? suggested : all;
    }
    return rows;
  }

  _googleRoleLabel(role) {
    if (role === "urgent") return "Urgent";
    if (role === "severe") return "Severe";
    if (role === "any") return "Alert";
    return "";
  }

  _renderStormEnableCard() {
    const draft = this._stormDraft;
    if (!draft) {
      return `<div class="card"><p class="card-title">StormSafe</p><p class="gw-status">Loading…</p></div>`;
    }
    return `<div class="card">
<div class="toggle-row"><span><strong>Enable StormSafe</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Arms when Google Weather reports a storm-type condition (or alert binaries turn on)</span></span>
<input type="checkbox" data-action="toggle-storm-enabled" ${draft.enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
</div>`;
  }

  _renderGoogleWeatherSource() {
    const gw = this._triggerMeta?.google_weather;
    const draft = this._stormDraft;
    if (!gw || !draft) {
      return `<div class="card gw-card gw-warn"><p class="card-title">Weather source</p><p class="gw-status">Loading…</p></div>`;
    }
    const repo = gw.hacs_repo || "https://github.com/safepay/ha_google_weather";
    const entries = gw.entries ?? [];
    const selectedId = draft.google_weather_entry_id || "";
    const selected = this._getSelectedGoogleWeatherEntry();

    if (!gw.installed) {
      return `<div class="card gw-card gw-warn"><p class="card-title">Install Google Weather (2 minutes)</p>
<ol class="storm-hint" style="margin:0;padding-left:18px;line-height:1.6">
<li>HACS → Custom repositories → <a href="${esc(repo)}" target="_blank" rel="noopener">ha_google_weather</a></li>
<li>Install <strong>Google Weather</strong>, restart Home Assistant</li>
<li>Settings → Integrations → Add → Google Weather (API key + your home location)</li>
<li>Return here, enable <strong>StormSafe</strong>, pick your Google Weather location, and press <strong>Save StormSafe settings</strong></li>
</ol></div>`;
    }

    if (!entries.length) {
      return `<div class="card gw-card gw-warn"><p class="card-title">Google Weather</p>
<p class="gw-status">No Google Weather config entries found. Add the integration under Settings → Devices &amp; services.</p></div>`;
    }

    const options = entries
      .map(
        (e) =>
          `<option value="${esc(e.entry_id)}" ${e.entry_id === selectedId ? "selected" : ""}>${esc(e.title)}</option>`
      )
      .join("");
    let cls = "gw-card";
    let detail = "";

    const savedStorm = this._plantState?.storm_prep ?? {};
    const cond = savedStorm.current_condition ?? selected?.current_condition;
    const forecast = savedStorm.forecast_detail ?? {};
    const forecastActive = Boolean(savedStorm.forecast_active);

    if (selected?.alerts_supported) {
      cls += " gw-ready";
      const names = selected.alert_entities.map((a) => esc(a.name)).join(", ");
      detail = `<p class="gw-linked"><strong>Alert triggers:</strong> ${names} (when <em>on</em>).</p>`;
    }

    if (selected?.condition_supported || selected?.weather_entity) {
      cls += selected?.alerts_supported ? "" : " gw-ready";
      detail += `<p class="gw-linked"><strong>Native Google Weather</strong> — current conditions + hourly forecast. Pre-charges when a storm is due within your lead time (below).</p>`;
      if (cond) {
        detail += `<p class="gw-linked">${formatStormNowLine(cond)}</p>`;
      } else if (selected.condition_entity_id) {
        detail += `<p class="gw-linked">Enable the <strong>Weather condition</strong> sensor in HA if hidden (eye icon).</p>`;
      }
      if (forecastActive && forecast.next_storm) {
        detail += `<p class="gw-linked">${formatStormForecastActiveLine(forecast.next_storm)}</p>`;
      } else if (draft.use_forecast_lead && selected.weather_entity) {
        detail += `<p class="gw-linked">Forecast: no storm in the next <strong>${esc(String(draft.forecast_lead_hours || 4))}</strong> hours.</p>`;
      }
    } else if (selected) {
      cls += " gw-warn";
      detail = `<p class="gw-linked">No weather condition sensor found for this integration entry. Update Google Weather or pick another source under Advanced.</p>`;
    } else {
      detail = `<p class="gw-linked">Choose your Google Weather location. StormSafe uses official alert binaries (if available) and/or the weather condition sensor.</p>`;
    }

    if (selected?.weather_entity) {
      detail += `<p class="gw-linked">Also watches: <code>${esc(selected.weather_entity)}</code></p>`;
    }

    const enableHint =
      draft.enabled && !selected
        ? `<p class="storm-hint" style="margin:12px 0 0;color:var(--fp-amber)">Select a location below, then press <strong>Save StormSafe settings</strong>.</p>`
        : "";

    return `<div class="card ${cls}"><p class="card-title">Google Weather</p>
<p class="storm-hint">Weather data source for StormSafe — live conditions, hourly forecast lead time, and optional severe-weather alert sensors from the Google Weather integration in Home Assistant.</p>
<label class="field" style="margin-top:12px"><span style="font-size:12px;color:var(--secondary-text-color)">Google Weather location</span>
<p class="field-hint" style="margin:4px 0 8px">Each Home Assistant config entry is one place Google tracks (usually your home). StormSafe reads current weather and forecast from the entry you choose.</p>
<select class="gw-select" data-action="pick-google-weather-entry" ${this._busy || !draft.enabled ? "disabled" : ""}>
<option value="">— Select location —</option>
${options}
</select></label>
${enableHint}${detail}</div>`;
  }

  _renderStormSolcastSection() {
    const draft = this._stormDraft;
    const precheck = this._plantState?.storm_prep?.solcast_precheck ?? {};
    const solcast = this._plantState?.solcast ?? {};
    const solcastConfigured = Boolean(solcast.enabled && solcast.api_key_configured);
    const margin = draft?.solcast_safety_margin ?? DEFAULT_STORM_SOLCAST_MARGIN;
    const minSoc = draft?.solcast_min_soc_floor ?? DEFAULT_STORM_SOLCAST_MIN_SOC;
    const enabled = Boolean(draft?.use_solcast_grid_limit);
    const action = precheck.action ?? "disabled";
    const precheckClass = stormSolcastActionClass(action);
    const metrics = formatStormSolcastMetrics(precheck);
    const summary = precheck.summary
      ? esc(precheck.summary)
      : "Enable the option below to evaluate whether solar can cover the battery gap before grid import.";
    const detail = precheck.detail ? `<p class="storm-solcast-precheck-detail">${esc(precheck.detail)}</p>` : "";
    const metricsBlock = metrics
      ? `<p class="storm-solcast-precheck-metrics">${metrics}</p>`
      : "";
    const solcastHint = !solcastConfigured
      ? `<p class="storm-hint" style="margin:12px 0 0">Solcast is not set up yet — configure it under <strong>Settings → Solcast</strong> (API key and PV strings) before turning this on.</p>`
      : "";
    const precheckTitle =
      action === "pv_only"
        ? "PV likely sufficient — grid import can be skipped"
        : action === "full_grid" && enabled && precheck.forecast_active
          ? "Grid pre-charge recommended"
          : "Pre-charge check";
    return `<div class="card storm-solcast-card">
<p class="card-title">Solcast PV pre-check</p>
<p class="storm-hint">Optional. When a storm is only in the <strong>forecast</strong> (not active yet), Fox Plant can compare your battery gap to Solcast solar expected <em>before</em> the storm hour. If PV covers the gap (with a safety margin), StormSafe arms without grid import — saving import cost while still monitoring the weather.</p>
<p class="storm-hint" style="margin-top:8px"><strong>Important:</strong> When storm conditions are <em>active now</em>, or battery SOC is below your safety floor, full grid pre-charge always applies regardless of this setting. Turning this option off always uses grid pre-charge when StormSafe arms.</p>
<div class="toggle-row"><span><strong>Limit grid pre-charge using Solcast</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Off by default — enable only if you accept relying on forecast solar before severe weather</span></span>
<input type="checkbox" data-field="toggle-storm-solcast" ${enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="field" style="margin-top:10px"><label>Safety margin (×)</label>
<p class="field-hint">Conservative factor on Solcast PV (default 1.35 — higher = less trust in forecast). SmartCharge uses 1.15; StormSafe uses a larger margin because backup matters more than cost.</p>
<input type="number" min="1" max="3" step="0.05" data-field="storm-solcast-margin" value="${esc(String(margin))}" ${!enabled || this._busy ? "disabled" : ""}></div>
<div class="field"><label>Minimum SOC floor (%)</label>
<p class="field-hint">If battery is below this level when a forecast storm is due, grid pre-charge is used even when Solcast looks sufficient (default 90%).</p>
<input type="number" min="10" max="100" step="1" data-field="storm-solcast-min-soc" value="${esc(String(minSoc))}" ${!enabled || this._busy ? "disabled" : ""}></div>
${solcastHint}
<div class="storm-solcast-precheck ${precheckClass}">
<p class="storm-solcast-precheck-title">${esc(precheckTitle)}</p>
<p style="margin:0;font-size:13px;line-height:1.5">${summary}</p>
${metricsBlock}${detail}
<p class="storm-solcast-precheck-detail" style="margin-top:8px">Press <strong>Save StormSafe settings</strong> to apply option changes and refresh this calculation.</p>
</div>
</div>`;
  }

  _renderStormWeatherCategories() {
    const draft = this._stormDraft;
    const catalog = this._getStormWeatherCategoryCatalog();
    const gwEntry = this._getSelectedGoogleWeatherEntry();
    const savedStorm = this._plantState?.storm_prep ?? {};
    const forecast = savedStorm.forecast_detail ?? {};
    const forecastActive = Boolean(savedStorm.forecast_active);
    const activeForecastCatIds = new Set(
      (forecast.next_storm?.matched_categories ?? []).map((c) => c.id)
    );
    const activeNowCatIds = new Set(
      (savedStorm.current_condition?.matched_categories ?? []).map((c) => c.id)
    );
    if (!catalog.length) {
      return `<div class="card"><p class="card-title">Weather warnings</p>
<p class="storm-hint">Choose which Google Weather conditions trigger StormSafe pre-charge.</p>
<p class="placeholder" style="margin:8px 0 0">Loading categories…</p></div>`;
    }
    if (!gwEntry) {
      return `<div class="card"><p class="card-title">Weather warnings</p>
<p class="storm-hint">Select a Google Weather location above to see which Fox-style warning categories Google publishes for your area.</p></div>`;
    }
    const supportedIds = catalog.filter((row) => row.supported !== false).map((row) => row.id);
    const selected = new Set(
      (draft?.storm_weather_categories ?? supportedIds).filter((id) => supportedIds.includes(id))
    );
    const gatedCount = catalog.filter((row) => row.supported === false).length;
    const rows = catalog
      .map((cat) => {
        const supported = cat.supported !== false;
        const on = supported && selected.has(cat.id);
        const disabled = !supported || this._busy;
        const note = cat.unsupported_reason
          ? `<span class="storm-weather-category-note">${esc(cat.unsupported_reason)}</span>`
          : "";
        const via =
          supported && cat.support_via?.length
            ? `<span class="storm-weather-category-via">via ${esc(cat.support_via.join(" + "))}</span>`
            : "";
        const forecastTokens = cat.forecast_conditions?.length
          ? cat.forecast_conditions
          : cat.forecast_conditions_label
            ? cat.forecast_conditions_label.split(",").map((s) => s.trim()).filter(Boolean)
            : [];
        const forecastHint = forecastTokens.length
          ? `<span class="storm-weather-category-forecast">Hourly forecast matches: ${forecastTokens
              .map((token) => `<code>${esc(token)}</code>`)
              .join(", ")}</span>`
          : "";
        const isForecastActive = forecastActive && activeForecastCatIds.has(cat.id);
        const isNowActive = activeNowCatIds.has(cat.id);
        const activeBadge = isForecastActive
          ? `<span class="storm-weather-category-active-badge">Pre-charging — forecast</span>`
          : isNowActive
            ? `<span class="storm-weather-category-active-badge">Active now</span>`
            : "";
        const activeClass =
          isForecastActive || isNowActive ? " storm-weather-category-row--active" : "";
        return `<div class="storm-weather-category-row${supported ? "" : " storm-weather-category-row--disabled"}${activeClass}">
<img class="storm-weather-category-icon" src="${esc(stormWeatherIconUrl(cat.icon))}" alt="" width="40" height="40" loading="lazy" ${supported ? "" : 'style="opacity:0.7"'}>
<div class="storm-weather-category-body">
<span class="storm-weather-category-label">${esc(cat.label)}</span>
${note}${via}${forecastHint}${activeBadge}
</div>
<input type="checkbox" data-action="toggle-storm-category" data-category="${esc(cat.id)}" ${on ? "checked" : ""} ${disabled ? "disabled" : ""} aria-label="${esc(cat.label)}">
</div>`;
      })
      .join("");
    const gatedHint = gatedCount
      ? `<p class="storm-hint" style="margin:12px 0 0">${gatedCount} categor${gatedCount === 1 ? "y is" : "ies are"} unavailable for <strong>${esc(gwEntry.title)}</strong> — Google does not publish those alerts or forecast types there.</p>`
      : "";
    return `<div class="card"><p class="card-title">Weather warnings</p>
<p class="storm-hint">Toggle the severe weather types that should trigger StormSafe for <strong>${esc(gwEntry.title)}</strong>. Each row shows which Google hourly forecast tokens map to that category (e.g. <code>rainy</code> → Heavy rain). Uncheck a category to ignore that forecast. Grey rows are not offered by Google Weather in this region.</p>
<div class="storm-weather-category-list">${rows}</div>${gatedHint}</div>`;
  }

  _renderStormAdvancedTriggers() {
    const draft = this._stormDraft;
    if (!this._stormShowAdvanced) {
      return `<details class="storm-advanced"><summary data-action="toggle-storm-advanced">Advanced: pick individual trigger entities</summary></details>`;
    }
    return `<details class="storm-advanced" open>
<summary data-action="toggle-storm-advanced">Advanced: pick individual trigger entities</summary>
<p class="storm-hint">Only needed if you are not using Google Weather alerts, or you want extra sensors (MeteoAlarm, NWS, templates).</p>
<div data-storm-trigger-chips>${this._renderTriggerChips()}</div>
<input type="search" class="trigger-filter" data-action="storm-trigger-filter" placeholder="Search entities…" value="${esc(this._triggerFilter)}" aria-label="Filter trigger entities">
<div class="trigger-filter-actions">
<button type="button" class="btn btn-secondary" data-action="storm-show-suggested" ${!this._triggerShowAll && !this._triggerFilter ? "disabled" : ""}>Weather matches</button>
<button type="button" class="btn btn-secondary" data-action="storm-show-all" ${this._triggerShowAll ? "disabled" : ""}>All binary sensors</button>
</div>
<div data-storm-trigger-list>${this._renderTriggerPickerListHtml()}</div>
<p style="margin:10px 0 0;font-size:12px;color:var(--secondary-text-color)" data-storm-trigger-count>${draft.trigger_entities.length} selected</p>
</details>`;
  }

  _renderTriggerChips() {
    const selected = this._stormDraft?.trigger_entities ?? [];
    if (!selected.length) {
      return '<p class="storm-hint" style="margin:0">Selected triggers appear here. Tick entities below, or use the search box.</p>';
    }
    return `<div class="trigger-chips-wrap">${selected
      .map((entityId) => {
        const row = (this._triggerCandidates ?? []).find((r) => r.entity_id === entityId);
        const name = row?.name ?? entityId;
        return `<span class="trigger-chip trigger-chip-selected"><button type="button" data-action="remove-storm-trigger" data-entity="${esc(entityId)}" aria-label="Remove ${esc(name)}">×</button>${esc(name)}</span>`;
      })
      .join("")}</div>`;
  }

  _renderTriggerPickerListHtml() {
    const selected = new Set(this._stormDraft?.trigger_entities ?? []);
    const rows = this._getFilteredTriggerRows();
    const all = this._triggerCandidates ?? [];
    const suggestedCount = all.filter((r) => r.suggested).length;

    if (!all.length) {
      return `<p class="placeholder" style="margin:8px 0 0">Loading entities… If this stays empty, reload FoxESS Plant and ensure weather warning binary sensors exist in Home Assistant.</p>`;
    }
    if (!rows.length) {
      const hint = this._triggerGoogleOnly
        ? "No Google Weather alerts match. Install Google Weather with alerts enabled, or show all sensors."
        : `No matches for “${esc(this._triggerFilter)}”. Try “alert”, “warning”, or show all sensors.`;
      return `<p class="placeholder" style="margin:8px 0 0">${hint}</p>`;
    }

    const showGroupedHeader =
      !this._triggerFilter && !this._triggerGoogleOnly && this._triggerShowAll && suggestedCount > 0;
    const googleRows = showGroupedHeader ? rows.filter((r) => r.provider === "google_weather") : [];
    const suggestedRows = showGroupedHeader
      ? rows.filter((r) => r.suggested && r.provider !== "google_weather")
      : [];
    const otherRows = showGroupedHeader
      ? rows.filter((r) => !r.suggested && r.provider !== "google_weather")
      : rows;

    const renderRows = (list) =>
      list
        .map((row) => {
          const on = selected.has(row.entity_id);
          const cls = [
            "trigger-row",
            row.provider === "google_weather" ? "google-weather" : "",
            row.suggested ? "suggested" : "",
          ]
            .filter(Boolean)
            .join(" ");
          const id = this._triggerRowId(row.entity_id);
          const role = row.provider === "google_weather" ? this._googleRoleLabel(row.role) : "";
          const roleHtml = role ? `<span class="trigger-role">${esc(role)}</span>` : "";
          return `<div class="${cls}">
<input type="checkbox" id="${id}" data-action="toggle-storm-trigger" data-entity="${esc(row.entity_id)}" ${on ? "checked" : ""}>
<label for="${id}">${esc(row.name)}${roleHtml}<span class="entity-id">${esc(row.entity_id)}</span></label>
<span class="entity-state">${esc(row.state)}</span>
</div>`;
        })
        .join("");

    let body = "";
    if (showGroupedHeader && googleRows.length) {
      body += `<p class="trigger-section-title">Google Weather (${googleRows.length})</p>${renderRows(googleRows)}`;
      if (suggestedRows.length) {
        body += `<p class="trigger-section-title">Other weather &amp; warnings (${suggestedRows.length})</p>${renderRows(suggestedRows)}`;
      }
      if (otherRows.length) {
        body += `<p class="trigger-section-title">Other binary sensors (${otherRows.length})</p>${renderRows(otherRows)}`;
      }
    } else if (this._triggerGoogleOnly && rows.length) {
      body += `<p class="trigger-section-title">Google Weather alerts (${rows.length})</p>${renderRows(rows)}`;
    } else {
      body = renderRows(rows);
    }

    return `<div class="trigger-list">${body}</div>`;
  }

  _syncStormTriggerPicker() {
    if (this._settingsView !== "storm" || !this._stormDraft) return;
    const main = this._root.querySelector(".main");
    if (!main) return;

    const listHost = main.querySelector("[data-storm-trigger-list]");
    const chipsHost = main.querySelector("[data-storm-trigger-chips]");
    const countEl = main.querySelector("[data-storm-trigger-count]");
    const filterEl = main.querySelector('[data-action="storm-trigger-filter"]');
    if (!listHost) return;

    const scrollEl = listHost.querySelector(".trigger-list");
    const scrollTop = scrollEl?.scrollTop ?? 0;
    const filterHadFocus = document.activeElement === filterEl;
    const selStart = filterEl?.selectionStart ?? 0;
    const selEnd = filterEl?.selectionEnd ?? 0;

    if (chipsHost) chipsHost.innerHTML = this._renderTriggerChips();
    listHost.innerHTML = this._renderTriggerPickerListHtml();
    if (countEl) {
      countEl.textContent = `${this._stormDraft.trigger_entities.length} selected`;
    }

    const newScroll = listHost.querySelector(".trigger-list");
    if (newScroll) newScroll.scrollTop = scrollTop;

    if (filterHadFocus && filterEl) {
      filterEl.focus();
      try {
        filterEl.setSelectionRange(selStart, selEnd);
      } catch {
        /* some browsers reject on type=search */
      }
    }
  }

  _isSettingsMainView() {
    return this._view === "settings" && this._settingsView === "main";
  }

  _settingsStormSubtitle() {
    const storm = this._plantState?.storm_prep ?? {};
    const triggersArmed = Boolean(this._plantState?.active_storm_triggers?.length);
    const overrideArmed =
      Boolean(this._plantState?.override_active) && String(this._plantState?.mode ?? "") === "storm";
    const armed = triggersArmed || overrideArmed;
    const gwEntry = (this._getGoogleWeatherEntries() || []).find(
      (e) => e.entry_id === storm.google_weather_entry_id
    );
    if (!storm.enabled) return "Off";
    if (gwEntry) return `${gwEntry.title}${armed ? " · active" : ""}`;
    return `${(storm.trigger_entities ?? []).length} trigger(s)`;
  }

  _smartChargeSettingsSubtitle() {
    const sc = this._plantState?.smart_charge ?? {};
    if (!sc.enabled) return "Off";
    const decision = sc.decision?.reason;
    if (sc.discharge_armed) return decision ? `Exporting — ${decision}` : "Exporting";
    if (sc.armed) return decision ? `Armed — ${decision}` : "Armed";
    return decision || "Enabled";
  }

  _settingsMainSubtitles() {
    const s = this._plantState?.settings ?? {};
    return {
      quick: `Max ${s.max_soc ?? "—"}% · Min ${s.min_soc ?? "—"}% · Off-grid ${s.min_soc_on_grid ?? "—"}%`,
      workmode: String(s.work_mode ?? "—"),
      pv: pvConfigSummary(this._plantState?.pv_config),
      solcast: this._solcastSettingsSubtitle(),
      glow: this._glowSettingsSubtitle(),
      tariff: tariffSettingsSummary(this._plantState?.tariff),
      smart: this._smartChargeSettingsSubtitle(),
      storm: this._settingsStormSubtitle(),
      control: this._plantState?.control_active ? "Fox Plant manages periods" : "Released to manual",
    };
  }

  _renderSettingsMainLiveHtml() {
    return this._modeBanner();
  }

  _patchSettingsMainLiveIfNeeded() {
    if (!this._isSettingsMainView() || !this._hass) return false;
    const root = this._root.querySelector("[data-settings-main]");
    const live = this._root.querySelector("[data-settings-live]");
    if (!root || !live) return false;
    live.innerHTML = this._renderSettingsMainLiveHtml();
    const subs = this._settingsMainSubtitles();
    for (const [sub, text] of Object.entries(subs)) {
      const el = root.querySelector(`[data-action="settings-sub"][data-sub="${sub}"] .list-btn-sub`);
      if (el) el.textContent = text;
    }
    return true;
  }

  _renderGlowStatusInnerHtml() {
    const live = this._plantState?.glow ?? {};
    const liveData = live.live || {};
    const lastMqtt = live.last_mqtt_at ? esc(formatSolcastTimestamp(live.last_mqtt_at)) : "—";
    const lastApi = live.last_api_at ? esc(formatSolcastTimestamp(live.last_api_at)) : "—";
    const lastErr = live.last_error ? esc(String(live.last_error)) : "None";
    const importKw =
      liveData.import_kw != null ? `${Number(liveData.import_kw).toFixed(3)} kW` : "—";
    const importToday =
      liveData.import_kwh_today != null ? `${Number(liveData.import_kwh_today).toFixed(2)} kWh` : "—";
    return `<div class="entity-list">
<div class="entity-row"><span class="entity-name">MQTT</span><span class="entity-value">${live.mqtt_connected ? "Connected" : "Not connected"}</span></div>
<div class="entity-row"><span class="entity-name">Live import power</span><span class="entity-value">${esc(importKw)}</span></div>
<div class="entity-row"><span class="entity-name">Import today (meter)</span><span class="entity-value">${esc(importToday)}</span></div>
<div class="entity-row"><span class="entity-name">Last MQTT</span><span class="entity-value">${lastMqtt}</span></div>
<div class="entity-row"><span class="entity-name">Last API</span><span class="entity-value">${lastApi}</span></div>
<div class="entity-row"><span class="entity-name">Device MAC</span><span class="entity-value">${esc(String(live.device_mac || "—"))}</span></div>
<div class="entity-row"><span class="entity-name">MPAN</span><span class="entity-value">${esc(String(liveData.mpan || "—"))}</span></div>
<div class="entity-row"><span class="entity-name">Last error</span><span class="entity-value">${lastErr}</span></div>
</div>
<p class="field-hint" style="margin-top:8px">When enabled, analytics <strong>From grid</strong> uses the smart meter. Solar production and battery flows stay on FoxESS plant sensors.</p>`;
  }

  _patchGlowSettingsLiveIfNeeded() {
    if (this._view !== "settings" || this._settingsView !== "glow" || !this._hass) return false;
    const liveEl = this._root.querySelector("[data-glow-live]");
    if (!liveEl) return false;
    liveEl.innerHTML = this._renderGlowStatusInnerHtml();
    return true;
  }

  _renderSettingsMain(plant) {
    const subs = this._settingsMainSubtitles();
    return `<div data-settings-main="1"><header class="header"><h1>Settings</h1><p>Quick controls for your plant</p></header>
<div data-settings-live>${this._renderSettingsMainLiveHtml()}</div>
<div data-settings-nav>
${renderListButton({ action: "settings-sub", sub: "quick" }, "Quick Settings", subs.quick)}
${renderListButton({ action: "settings-sub", sub: "schedules" }, "Charge schedule", "Two charge windows (baseline)")}
${renderListButton({ action: "settings-sub", sub: "workmode" }, "Work mode", subs.workmode)}
${renderListButton({ action: "settings-sub", sub: "pv" }, "PV Configuration", subs.pv)}
${renderListButton({ action: "settings-sub", sub: "solcast" }, "Solcast", subs.solcast)}
${renderListButton({ action: "settings-sub", sub: "glow" }, "Glow smart meter", subs.glow)}
${renderListButton({ action: "settings-sub", sub: "tariff" }, "Tariff", subs.tariff)}
${renderListButton({ action: "settings-sub", sub: "smart" }, "SmartCharge", subs.smart)}
${renderListButton({ action: "settings-sub", sub: "storm" }, "StormSafe", subs.storm)}
${renderListButton({ action: "settings-sub", sub: "control" }, "Plant control", subs.control)}
</div></div>`;
  }

  _renderSettingsQuick() {
    if (!this._socDraft) this._initSocDraft();
    const plant = this._getPlant();
    const liveSoc = this._liveBatterySoc(plant) ?? 0;
    const validation = validateSocLimits(this._socDraft, liveSoc);
    return `<header class="header"><h1>Quick Settings</h1><p>Drag the three handles — off-grid min, system min, system max</p></header>
<div class="card">
<p class="card-title">SOC limits</p>
${this._renderTripleSoc(plant, this._socDraft, liveSoc)}
<div class="btn-row"><button type="button" class="btn btn-primary" data-action="save-soc" ${this._busy || validation.errors.length ? "disabled" : ""}>Save to inverter</button></div>
</div>`;
  }

  _renderSettingsSchedules() {
    if (!this._chargeDraft) this._initChargeDraft();
    const driftHint = this._plantState?.drift
      ? `<div class="banner warn" style="margin-bottom:12px"><strong>Schedule drift</strong> Inverter and app schedules differ.${this._scheduleSyncButtons()}</div>`
      : "";
    return `<header class="header"><h1>Charge schedule</h1><p>Baseline periods — Fox Plant keeps the inverter in sync</p></header>
${driftHint}
${this._renderPeriodCard(0, this._chargeDraft[0])}
${this._renderPeriodCard(1, this._chargeDraft[1])}
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="save-schedules" ${this._busy ? "disabled" : ""}>Save & apply</button>
<button type="button" class="btn btn-secondary" data-action="sync-schedule" ${this._busy ? "disabled" : ""}>Sync from inverter</button>
<button type="button" class="btn btn-secondary" data-action="reapply-schedule" ${this._busy ? "disabled" : ""}>Re-apply to inverter</button>
<button type="button" class="btn btn-secondary" data-action="copy-period" data-from="0" data-to="1" ${this._busy ? "disabled" : ""}>Copy period 1 → 2</button>
<button type="button" class="btn btn-secondary" data-action="swap-periods" ${this._busy ? "disabled" : ""}>Swap 1 ↔ 2</button>
</div>`;
  }

  _renderSettingsWorkMode() {
    if (!this._workModeDraft) this._initWorkModeDraft();
    const options = this._plantState?.settings?.work_mode_options ?? [];
    if (!options.length) {
      return `<header class="header"><h1>Work mode</h1></header><p class="placeholder">Work mode entity not found. Reload the integration.</p>`;
    }
    return `<header class="header"><h1>Work mode</h1><p>Matches the FoxESS inverter modes</p></header>
<div class="mode-grid">${options
      .map((opt) => {
        const sel = opt === this._workModeDraft ? "selected" : "";
        const meta = workModeMeta(opt);
        return `<button type="button" class="mode-option ${sel}" data-action="pick-work-mode" data-mode="${esc(opt)}">
${renderWorkModeIconHtml(opt)}<span class="mode-option-body"><span class="name">${esc(meta.title)}</span>${meta.hint ? `<span class="hint">${esc(meta.hint)}</span>` : ""}</span></button>`;
      })
      .join("")}</div>
<div class="btn-row" style="margin-top:16px"><button type="button" class="btn btn-primary" data-action="save-work-mode" ${this._busy ? "disabled" : ""}>Apply work mode</button></div>`;
  }

  _renderSmartChargeModePicker(draft) {
    const busy = this._busy ? "disabled" : "";
    const modes = ["max_safety", "max_profit", "max_green"];
    const cards = modes
      .map((mode) => {
        const meta = SMART_CHARGE_MODE_META[mode];
        const sel = draft.operating_mode === mode ? "selected" : "";
        return `<button type="button" class="mode-option ${sel}" data-action="pick-smart-charge-mode" data-mode="${esc(mode)}" ${busy}>
<span class="mode-option-icon mode-option-icon--smart-charge" aria-hidden="true">${smartChargeModeIconHtml(mode)}</span>
<span class="mode-option-body"><span class="name">${esc(meta.title)}</span><span class="hint">${esc(meta.hint)}</span></span>
</button>`;
      })
      .join("");
    return `<p class="card-title" style="margin-top:14px">Operating mode</p>
<div class="mode-grid">${cards}</div>`;
  }

  _renderSmartChargeModePanel(draft) {
    const mode = draft.operating_mode || "max_safety";
    const meta = SMART_CHARGE_MODE_META[mode] || SMART_CHARGE_MODE_META.max_safety;
    const busy = this._busy ? "disabled" : "";
    let body = "";
    if (mode === "max_profit") {
      body = `<div class="toggle-row"><span><strong>Enable grid export</strong></span>
<input type="checkbox" data-field="smart-charge:export_enabled" ${draft.export_enabled ? "checked" : ""} ${busy}></div>
<div class="field"><label>Min export rate (p/kWh)</label>
<input type="number" min="0" max="100" step="0.5" data-field="smart-charge:min_export_p_profit" value="${esc(String(draft.min_export_p_profit ?? 12))}" ${busy}></div>
<div class="field"><label>Max exportable fraction</label>
<input type="number" min="0.05" max="1" step="0.05" data-field="smart-charge:exportable_fraction_profit" value="${esc(String(draft.exportable_fraction_profit ?? 1))}" ${busy}></div>
<div class="field"><label>Min arbitrage profit (p/kWh)</label>
<input type="number" min="0" max="50" step="0.1" data-field="smart-charge:min_arbitrage_p_per_kwh" value="${esc(String(draft.min_arbitrage_p_per_kwh ?? 0.5))}" ${busy}>
<p class="field-hint">Negative import — charge when later export beats this after losses.</p></div>`;
    } else if (mode === "max_green") {
      body = `<div class="toggle-row"><span><strong>Enable grid export</strong></span>
<input type="checkbox" data-field="smart-charge:export_enabled" ${draft.export_enabled ? "checked" : ""} ${busy}></div>
<div class="toggle-row"><span><strong>Allow export in green mode</strong></span>
<input type="checkbox" data-field="smart-charge:export_enabled_green" ${draft.export_enabled_green ? "checked" : ""} ${busy}></div>
<div class="field"><label>Min export rate (p/kWh)</label>
<input type="number" min="0" max="100" step="0.5" data-field="smart-charge:min_export_p_green" value="${esc(String(draft.min_export_p_green ?? 25))}" ${busy}></div>
<div class="field"><label>Max exportable fraction</label>
<input type="number" min="0.05" max="1" step="0.05" data-field="smart-charge:exportable_fraction_green" value="${esc(String(draft.exportable_fraction_green ?? 0.15))}" ${busy}></div>
<div class="field"><label>Carbon weight (0–1)</label>
<input type="number" min="0" max="1" step="0.05" data-field="smart-charge:green_carbon_weight" value="${esc(String(draft.green_carbon_weight ?? 0.5))}" ${busy}>
<p class="field-hint">Prefer low-carbon slots when choosing charge windows.</p></div>
<div class="field"><label>Green spread multiplier</label>
<input type="number" min="1" max="10" step="0.1" data-field="smart-charge:green_export_spread_multiplier" value="${esc(String(draft.green_export_spread_multiplier ?? 2))}" ${busy}></div>`;
    } else {
      body = `<div class="toggle-row"><span><strong>Enable grid export</strong></span>
<input type="checkbox" data-field="smart-charge:export_enabled" ${draft.export_enabled ? "checked" : ""} ${busy}></div>
<div class="toggle-row"><span><strong>Allow export in safety mode</strong></span>
<input type="checkbox" data-field="smart-charge:export_enabled_safety" ${draft.export_enabled_safety ? "checked" : ""} ${busy}></div>
<div class="field"><label>Min export rate (p/kWh)</label>
<input type="number" min="0" max="100" step="0.5" data-field="smart-charge:min_export_p_safety" value="${esc(String(draft.min_export_p_safety ?? 20))}" ${busy}></div>
<div class="field"><label>Max exportable fraction</label>
<input type="number" min="0.05" max="1" step="0.05" data-field="smart-charge:exportable_fraction_safety" value="${esc(String(draft.exportable_fraction_safety ?? 0.35))}" ${busy}></div>
<div class="field"><label>Safety reserve multiplier</label>
<input type="number" min="1" max="5" step="0.05" data-field="smart-charge:safety_reserve_multiplier" value="${esc(String(draft.safety_reserve_multiplier ?? 1.5))}" ${busy}></div>`;
    }
    body += `<div class="field"><label>Minimum export energy (kWh)</label>
<input type="number" min="0.1" max="50" step="0.1" data-field="smart-charge:min_export_kwh" value="${esc(String(draft.min_export_kwh ?? 0.5))}" ${busy}></div>`;
    return `<div class="sc-mode-panel" style="--sc-mode-accent: ${meta.accent}">
<p class="sc-mode-panel-title"><span class="sc-mode-panel-icon" aria-hidden="true">${smartChargeModeIconHtml(mode)}</span>${esc(meta.title)} settings</p>
${body}
</div>`;
  }

  _smartChargeSectionDefaults(draft) {
    const mode = draft?.operating_mode || "max_safety";
    return {
      energy: true,
      reserve: false,
      agile: false,
      spread: mode === "max_profit",
      charge: false,
    };
  }

  _smartChargeSectionIsOpen(sectionId, draft) {
    if (this._smartChargeSectionOpen && sectionId in this._smartChargeSectionOpen) {
      return Boolean(this._smartChargeSectionOpen[sectionId]);
    }
    return Boolean(this._smartChargeSectionDefaults(draft)[sectionId]);
  }

  _smartChargeSectionOpenAttr(sectionId, draft) {
    return this._smartChargeSectionIsOpen(sectionId, draft) ? " open" : "";
  }

  _captureSmartChargeDetailsOpen() {
    if (!this._smartChargeSectionOpen) this._smartChargeSectionOpen = {};
    const sections = this._root?.querySelectorAll?.("details.sc-section-details[data-sc-section]");
    if (!sections?.length) return;
    sections.forEach((el) => {
      this._smartChargeSectionOpen[el.dataset.scSection] = el.open;
    });
  }

  _bindSmartChargeDetailsOpen() {
    const sections = this._root?.querySelectorAll?.("details.sc-section-details[data-sc-section]");
    if (!sections?.length) return;
    sections.forEach((el) => {
      el.addEventListener(
        "toggle",
        () => {
          if (!this._smartChargeSectionOpen) this._smartChargeSectionOpen = {};
          this._smartChargeSectionOpen[el.dataset.scSection] = el.open;
        },
        { passive: true }
      );
    });
  }

  _smartChargeLivePlanContext() {
    const live = this._plantState?.smart_charge ?? {};
    const decision = live.decision ?? {};
    const dailyPlan = live.daily_plan ?? decision.daily_plan ?? [];
    const planSlots = dailyPlan.filter((s) => s.start && s.end && s.reason !== "no_slots");
    const spreadPairs =
      (decision.spread_pairs?.length ? decision.spread_pairs : null) ??
      (dailyPlan[0]?.spread_pairs?.length ? dailyPlan[0].spread_pairs : []);
    const planHorizon = dailyPlan[0]?.plan_horizon === "24h" ? "24h plan" : "rest-of-today plan";
    const exportCount = planSlots.filter((s) => s.action === "export" || s.action === "spread_export").length;
    const chargeCount = planSlots.filter(
      (s) =>
        s.action === "charge" ||
        s.action === "charge_candidate" ||
        s.action === "spread_charge" ||
        s.action === "winter_fill"
    ).length;
    const spreadLabel = spreadPairs.length ? ` · ${spreadPairs.length} spread pair${spreadPairs.length === 1 ? "" : "s"}` : "";
    const planSummary =
      planSlots.length > 0
        ? `${planHorizon}: ${exportCount} export · ${chargeCount} charge · ${planSlots.length} slots${spreadLabel}`
        : "No daily plan yet (built at daily plan time after Octopus refresh)";
    return { live, decision, planSlots, spreadPairs, planSummary };
  }

  _patchSettingsSmartChargeLiveIfNeeded() {
    if (this._view !== "settings" || this._settingsView !== "smart" || !this._hass) return false;
    const liveEl = this._root.querySelector("[data-smart-charge-live]");
    if (!liveEl || !this._smartChargeDraft?.enabled) return false;
    const { live, decision, planSlots, spreadPairs, planSummary } = this._smartChargeLivePlanContext();
    liveEl.innerHTML = this._renderSmartChargeStatusCard(live, decision, planSlots, spreadPairs, planSummary);
    return true;
  }

  _renderSmartChargeSpreadPanel(draft) {
    const mode = draft.operating_mode || "max_safety";
    if (mode === "max_safety") return "";
    const busy = this._busy ? "disabled" : "";
    const greenOnly = mode === "max_green";
    return `<details class="sc-section-details" data-sc-section="spread"${this._smartChargeSectionOpenAttr("spread", draft)}>
<summary>Spread optimizer</summary>
<div class="toggle-row"><span><strong>Enable spread pairing</strong></span>
<input type="checkbox" data-field="smart-charge:spread_optimizer_enabled" ${draft.spread_optimizer_enabled ? "checked" : ""} ${busy}></div>
<div class="toggle-row"><span><strong>Winter cheap-fill</strong></span>
<input type="checkbox" data-field="smart-charge:winter_fill_enabled" ${draft.winter_fill_enabled ? "checked" : ""} ${busy}></div>
${greenOnly ? "" : `<div class="field"><label>Min spread profit (p/kWh)</label>
<input type="number" min="0" max="50" step="0.5" data-field="smart-charge:min_spread_profit_p_per_kwh" value="${esc(String(draft.min_spread_profit_p_per_kwh ?? 3))}" ${busy}></div>`}
<div class="field"><label>Cheap import ceiling (p/kWh)</label>
<input type="number" min="0" max="50" step="0.5" data-field="smart-charge:cheap_import_p_per_kwh" value="${esc(String(draft.cheap_import_p_per_kwh ?? 8))}" ${busy}></div>
<div class="field"><label>Peak import avoid — start</label>
<input type="time" data-field="smart-charge:peak_import_avoid_start" value="${esc(String(draft.peak_import_avoid_start ?? "16:00"))}" ${busy}></div>
<div class="field"><label>Peak import avoid — end</label>
<input type="time" data-field="smart-charge:peak_import_avoid_end" value="${esc(String(draft.peak_import_avoid_end ?? "19:00"))}" ${busy}></div>
<div class="field"><label>Peak import penalty (p/kWh)</label>
<input type="number" min="0" max="50" step="0.5" data-field="smart-charge:peak_import_penalty_p_per_kwh" value="${esc(String(draft.peak_import_penalty_p_per_kwh ?? 5))}" ${busy}></div>
</details>`;
  }

  _renderSmartChargeStatusCard(live, decision, dailyPlan, spreadPairs, planSummary) {
    const armed = Boolean(live.armed);
    const dischargeArmed = Boolean(live.discharge_armed);
    const statusLine = decision.reason
      ? `${dischargeArmed ? "Exporting" : armed ? "Charging" : "Idle"} — ${decision.reason}`
      : dischargeArmed
        ? "Exporting to grid"
        : armed
          ? "Grid charge armed"
          : "Waiting for first evaluation";
    const pillClass = dischargeArmed
      ? "sc-status-pill sc-status-pill--export"
      : armed
        ? "sc-status-pill sc-status-pill--armed"
        : "sc-status-pill sc-status-pill--idle";
    const pillLabel = dischargeArmed ? "Exporting" : armed ? "Charging" : "Ready";
    const cardClass = dischargeArmed
      ? "sc-status-card sc-status-card--exporting"
      : armed
        ? "sc-status-card sc-status-card--armed"
        : "sc-status-card";
    const spreadHtml = spreadPairs.length
      ? `<div class="sc-spread-pairs">${spreadPairs
          .slice(0, 4)
          .map(
            (p) =>
              `<div class="sc-spread-pair"><span>${esc(p.charge_start)} → ${esc(p.export_start)}</span><strong>+${Number(p.spread_p_per_kwh).toFixed(1)}p</strong></div>`
          )
          .join("")}</div>`
      : "";
    return `<div class="${cardClass}">
<div class="sc-status-head">
<div><p class="sc-status-title">Live status</p><p class="sc-status-reason">${esc(statusLine)}</p></div>
<span class="${pillClass}">${esc(pillLabel)}</span>
</div>
${renderSmartChargeStatTiles(decision)}
${renderSmartChargePlanTimeline(dailyPlan, decision.current_plan_slot)}
<p class="field-hint" style="margin:10px 0 0">${esc(planSummary)}</p>
${spreadHtml}
</div>`;
  }

  _renderSettingsSmartCharge() {
    if (!this._smartChargeDraft) this._initSmartChargeDraft();
    const draft = this._smartChargeDraft;
    const { live, decision, planSlots, spreadPairs, planSummary } = this._smartChargeLivePlanContext();
    const busy = this._busy ? "disabled" : "";
    const statusCard = draft.enabled
      ? this._renderSmartChargeStatusCard(live, decision, planSlots, spreadPairs, planSummary)
      : "";
    return `<div data-smart-charge-settings="1">${this._renderSmartChargeHero()}
<header class="header smart-charge-settings-header"><h1>SmartCharge</h1><p>Combines Solcast PV forecast with Octopus Agile rates. Targets house-load sufficiency (not 100% SOC), with an outage reserve floor. StormSafe always overrides.</p></header>
${draft.enabled ? `<div data-smart-charge-live>${statusCard}</div>` : statusCard}
<div class="card">
<p class="card-title">Automation</p>
<div class="toggle-row"><span><strong>Enable SmartCharge</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Requires Fox Plant control, Solcast PV forecast, and tariff rates</span></span>
<input type="checkbox" data-field="smart-charge:enabled" ${draft.enabled ? "checked" : ""} ${busy}></div>
${draft.enabled ? this._renderSmartChargeModePicker(draft) : ""}
${draft.enabled ? this._renderSmartChargeModePanel(draft) : ""}
${draft.enabled ? `<details class="sc-section-details" data-sc-section="energy"${this._smartChargeSectionOpenAttr("energy", draft)}>
<summary>Energy budget</summary>
<div class="field"><label>Max target SOC ceiling (%)</label>
<input type="number" min="10" max="100" step="1" data-field="smart-charge:max_target_soc" value="${esc(String(draft.max_target_soc ?? 100))}" ${busy}>
<p class="field-hint">House-load budget sets the effective target — this is the upper limit only.</p></div>
<div class="field"><label>Max SOC when charging (optional)</label>
<input type="number" min="10" max="100" step="1" data-field="smart-charge:target_max_soc" value="${draft.target_max_soc != null ? esc(String(draft.target_max_soc)) : ""}" placeholder="Same as ceiling" ${busy}></div>
<div class="field"><label>Solar safety margin</label>
<input type="number" min="1" max="3" step="0.05" data-field="smart-charge:solar_safety_margin" value="${esc(String(draft.solar_safety_margin ?? 1.15))}" ${busy}></div>
<div class="field"><label>Minimum deficit (kWh)</label>
<input type="number" min="0" max="50" step="0.1" data-field="smart-charge:min_deficit_kwh" value="${esc(String(draft.min_deficit_kwh ?? 0.5))}" ${busy}></div>
<div class="field"><label>Round-trip efficiency</label>
<input type="number" min="0.5" max="1" step="0.01" data-field="smart-charge:round_trip_efficiency" value="${esc(String(draft.round_trip_efficiency ?? 0.9))}" ${busy}></div>
</details>
<details class="sc-section-details" data-sc-section="reserve"${this._smartChargeSectionOpenAttr("reserve", draft)}>
<summary>Outage reserve &amp; house load</summary>
<div class="field"><label>House load fallback (kW)</label>
<input type="number" min="0.1" max="50" step="0.1" data-field="smart-charge:house_load_kw_fallback" value="${esc(String(draft.house_load_kw_fallback ?? 1))}" ${busy}></div>
<div class="field"><label>Reserve load override (kW, optional)</label>
<input type="number" min="0" max="50" step="0.1" data-field="smart-charge:outage_reserve_load_kw" value="${draft.outage_reserve_load_kw != null ? esc(String(draft.outage_reserve_load_kw)) : ""}" placeholder="Use live/fallback load" ${busy}></div>
<div class="field"><label>Vulnerable hours (reserve)</label>
<input type="number" min="0" max="24" step="0.5" data-field="smart-charge:outage_reserve_hours" value="${esc(String(draft.outage_reserve_hours ?? 3))}" ${busy}></div>
<div class="field"><label>Reserve safety margin</label>
<input type="number" min="1" max="5" step="0.05" data-field="smart-charge:outage_reserve_margin" value="${esc(String(draft.outage_reserve_margin ?? 1.2))}" ${busy}></div>
<div class="field"><label>Dark hours estimate (no meaningful PV)</label>
<input type="number" min="0" max="24" step="0.5" data-field="smart-charge:dark_hours_estimate" value="${esc(String(draft.dark_hours_estimate ?? 8))}" ${busy}></div>
</details>
<details class="sc-section-details" data-sc-section="agile"${this._smartChargeSectionOpenAttr("agile", draft)}>
<summary>Agile polling &amp; daily plan</summary>
<div class="field"><label>Agile poll interval (minutes)</label>
<input type="number" min="5" max="60" step="1" data-field="smart-charge:agile_poll_interval_minutes" value="${esc(String(draft.agile_poll_interval_minutes ?? 15))}" ${busy}></div>
<div class="toggle-row"><span><strong>Negative import interrupt</strong></span>
<input type="checkbox" data-field="smart-charge:negative_import_interrupt" ${draft.negative_import_interrupt ? "checked" : ""} ${busy}></div>
<div class="field"><label>Daily plan time (UK local)</label>
<input type="time" data-field="smart-charge:daily_plan_time" value="${esc(String(draft.daily_plan_time ?? "16:00"))}" ${busy}></div>
<div class="field"><label>Daily plan horizon (hours)</label>
<input type="number" min="1" max="48" step="1" data-field="smart-charge:daily_plan_horizon_hours" value="${esc(String(draft.daily_plan_horizon_hours ?? 24))}" ${busy}></div>
<div class="field"><label>Price-drop replan threshold (p/kWh)</label>
<input type="number" min="0" max="50" step="0.5" data-field="smart-charge:price_drop_interrupt_p_per_kwh" value="${esc(String(draft.price_drop_interrupt_p_per_kwh ?? 2))}" ${busy}></div>
</details>
${this._renderSmartChargeSpreadPanel(draft)}
<details class="sc-section-details" data-sc-section="charge"${this._smartChargeSectionOpenAttr("charge", draft)}>
<summary>Charge period template</summary>
<p class="field-hint">Start/end times are chosen automatically — these flags apply to the programmed window.</p>
${this._renderPeriodCard(0, draft.charge_periods[0], "smart-period", "Charge template")}
${this._renderPeriodCard(1, draft.charge_periods[1], "smart-period", "Reserve period")}
</details>` : ""}
<div class="btn-row"><button type="button" class="btn btn-primary" data-action="save-smart-charge" ${busy}>Save SmartCharge</button></div>
</div></div>`;
  }

  _renderSettingsStorm() {
    if (!this._stormDraft) this._initStormDraft();
    const draft = this._stormDraft;
    const triggersArmed = Boolean(this._plantState?.active_storm_triggers?.length);
    const overrideArmed =
      Boolean(this._plantState?.override_active) && String(this._plantState?.mode ?? "") === "storm";
    const armed = triggersArmed || overrideArmed;
    const activeTriggers = this._plantState?.active_storm_triggers ?? [];
    const maxSocVal = draft.target_max_soc == null ? "" : String(draft.target_max_soc);
    const precheck = this._plantState?.storm_prep?.solcast_precheck ?? {};
    const armedMsg =
      armed && precheck.action === "pv_only"
        ? "Storm prep is <strong>active</strong> — PV top-up only (no grid import per Solcast pre-check)."
        : armed
          ? "Storm prep is <strong>active</strong> — storm charge schedule applied."
          : "No storm triggers active right now.";
    return `${this._renderStormHero(armed)}
<header class="header storm-settings-header"><h1>StormSafe</h1><p>Pre-charge before severe weather — <strong>Google Weather</strong> detects storms; optional <strong>Solcast</strong> can reduce grid import when forecast solar covers the gap</p></header>
<div class="card">
<p class="card-title">Status</p>
<p style="margin:0 0 10px;font-size:14px">${armedMsg}</p>
${activeTriggers.length ? `<div>${activeTriggers.map((t) => `<span class="trigger-chip">${esc(t)}</span>`).join("")}</div>` : ""}
<div class="btn-row" style="margin-top:12px">
<button type="button" class="btn btn-primary" data-action="arm-storm" ${this._busy ? "disabled" : ""}>Test arm</button>
<button type="button" class="btn btn-secondary" data-action="disarm-storm" ${this._busy ? "disabled" : ""}>Disarm override</button>
</div>
</div>
${this._renderStormEnableCard()}
${this._renderGoogleWeatherSource()}
${this._renderStormSolcastSection()}
${this._renderStormWeatherCategories()}
<div class="card">
<p class="card-title">Pre-charge timing</p>
<div class="toggle-row"><span><strong>Forecast pre-charge</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Start storm schedule when Google hourly forecast shows severe weather within the lead time</span></span>
<input type="checkbox" data-field="toggle-storm-forecast" ${draft.use_forecast_lead ? "checked" : ""} ${!draft.enabled || this._busy ? "disabled" : ""}></div>
<div class="field" style="margin-top:10px"><label>Lead time (hours before forecast storm)</label>
<input type="number" min="1" max="48" step="1" data-field="storm-lead-hours" value="${esc(String(draft.forecast_lead_hours ?? 4))}" ${!draft.enabled || !draft.use_forecast_lead || this._busy ? "disabled" : ""}></div>
</div>
${this._renderStormAdvancedTriggers()}
<div class="card">
<p class="card-title">Storm charge schedule</p>
<p class="storm-hint">Applied while a trigger is active (separate from your baseline schedule).</p>
${this._renderPeriodCard(0, draft.charge_periods[0], "storm-period", "Storm period")}
${this._renderPeriodCard(1, draft.charge_periods[1], "storm-period", "Storm period")}
</div>
<div class="card">
<p class="card-title">Optional max SoC during storm</p>
<div class="field"><label>Target max % (leave empty to keep current max)</label>
<input type="number" min="10" max="100" step="1" data-field="storm-max-soc" value="${esc(maxSocVal)}" placeholder="e.g. 100"></div>
</div>
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="save-storm-prep" ${this._busy ? "disabled" : ""}>Save StormSafe settings</button>
</div>`;
  }

  _renderPvTiltAzimuthFields(which, { allowWhenDisabled = false } = {}) {
    if (!this._pvDraft) this._initPvDraft();
    const cfg = this._pvDraft[which];
    const stringLabel = which === "pv2" ? "PV2" : "PV1";
    const disabled = this._busy || (!allowWhenDisabled && !cfg.enabled);
    const offHint = !cfg.enabled && !allowWhenDisabled ? " (string off — enable under PV Configuration)" : "";
    return `<div class="pv-geometry-block" data-pv-string="${esc(which)}">
<p class="pv-geometry-label"><strong>${esc(stringLabel)}</strong>${esc(offHint)}</p>
<div class="field">
<label>Tilt (°)</label>
<p class="field-hint">Panel angle from horizontal (default 25° if unset)</p>
<div class="pv-range-row">
<input type="range" min="0" max="90" step="1" data-field="pv:${which}:tilt" value="${esc(String(cfg.tilt))}" ${disabled ? "disabled" : ""}>
<span class="pv-range-value">${esc(String(cfg.tilt))}°</span>
</div>
</div>
<div class="field">
<label>Azimuth (°)</label>
<p class="field-hint">0° = north, 90° = east, 180° = south (default 180° if unset)</p>
<div class="pv-range-row">
<input type="range" min="0" max="359" step="1" data-field="pv:${which}:azimuth" value="${esc(String(cfg.azimuth))}" ${disabled ? "disabled" : ""}>
<span class="pv-range-value">${esc(String(cfg.azimuth))}°</span>
</div>
</div>
</div>`;
  }

  _renderPvStringBlock(which) {
    if (!this._pvDraft) this._initPvDraft();
    const cfg = this._pvDraft[which];
    const sectionTitle = which === "pv2" ? "PV2 configuration" : "PV1 configuration";
    const enabledLabel = which === "pv2" ? "PV2 Enabled" : "PV1 Enabled";
    const arrayHintTarget = which === "pv2" ? "PV2" : "PV1";
    const disabled = this._busy || !cfg.enabled;
    const disabledClass = cfg.enabled ? "" : " pv-string-disabled";
    const installDate = pvInstallationDate(this._plantState, this._solcastDraft);
    const autoEff = Boolean(installDate);
    if (autoEff) {
      syncPvDraftEfficiencyFromInstall(this._pvDraft, this._plantState, this._solcastDraft);
    }
    const annualRate = this._pvDraft.annual_degradation_pct ?? DEFAULT_PV_CONFIG.annual_degradation_pct;
    const autoHint = autoEff ? formatPvEfficiencyAgeHint(installDate, annualRate) : "";
    const effHint = autoEff
      ? `<p class="field-hint">${esc(autoHint)} <a class="field-link" href="${esc(PV_EFFICIENCY_FACTOR_URL)}" target="_blank" rel="noopener noreferrer">What is the efficiency factor?</a></p>`
      : `<p class="field-hint"><a class="field-link" href="${esc(PV_EFFICIENCY_FACTOR_URL)}" target="_blank" rel="noopener noreferrer">What is the efficiency factor?</a></p>`;
    const effDisabled = disabled || autoEff;
    const nameplateKw = ((cfg.panel_count * cfg.watts_per_panel) / 1000).toFixed(2);
    const effectiveKw = (
      (cfg.panel_count * cfg.watts_per_panel * cfg.efficiency_factor) /
      100000
    ).toFixed(2);
    const currency = pvConfigCurrency(this._plantState, this._tariffDraft);
    const costStep = tariffRateInputStep(currency);
    const costDisplay =
      cfg.installation_cost_minor > 0 ? minorToMajor(cfg.installation_cost_minor, currency) : "";
    return `<div class="card pv-string-card${disabledClass}">
<p class="card-title">${esc(sectionTitle)}</p>
<div class="toggle-row"><span><strong>${esc(enabledLabel)}</strong></span>
<input type="checkbox" data-field="pv:${which}:enabled" ${cfg.enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="pv-config-fields">
<div class="field">
<label>PV Array size</label>
<p class="field-hint">Total number of panels on ${esc(arrayHintTarget)}</p>
<div class="pv-range-row">
<input type="range" min="1" max="12" step="1" data-field="pv:${which}:panel_count" value="${esc(String(cfg.panel_count))}" ${disabled ? "disabled" : ""}>
<span class="pv-range-value">${esc(String(cfg.panel_count))}</span>
</div>
</div>
<div class="field">
<label>Wattage per panel</label>
<div class="pv-range-row">
<input type="range" min="100" max="1000" step="10" data-field="pv:${which}:watts_per_panel" value="${esc(String(cfg.watts_per_panel))}" ${disabled ? "disabled" : ""}>
<span class="pv-range-value">${esc(String(cfg.watts_per_panel))} W</span>
</div>
</div>
<div class="field">
<label>Efficiency Factor</label>
${effHint}
<input type="number" class="pv-eff-input" min="1" max="100" step="1" data-field="pv:${which}:efficiency_factor" value="${esc(String(cfg.efficiency_factor))}" ${effDisabled ? "disabled" : ""} aria-label="Efficiency factor percent"> <span style="font-size:14px">%</span>
</div>
<div class="field">
<label>Installation cost</label>
<p class="field-hint">Optional total cost for this PV string in ${esc(currency)} — for future payback analysis (uses your tariff currency)</p>
<input type="number" class="pv-eff-input" min="0" step="${esc(costStep)}" inputmode="decimal" data-field="pv:${which}:installation_cost" value="${costDisplay !== "" ? esc(String(costDisplay)) : ""}" placeholder="0" ${disabled ? "disabled" : ""} aria-label="Installation cost">
</div>
${this._renderPvTiltAzimuthFields(which)}
<p class="field-hint" style="margin-top:4px">Nameplate ${esc(nameplateKw)} kW DC · Effective ${esc(effectiveKw)} kW (after efficiency)</p>
</div>
</div>`;
  }

  _renderPvConfiguration({ title, subtitle }) {
    if (!this._pvDraft) this._initPvDraft();
    const installDate = pvInstallationDate(this._plantState, this._solcastDraft);
    const annualRate = this._pvDraft.annual_degradation_pct ?? DEFAULT_PV_CONFIG.annual_degradation_pct;
    const installHint = installDate
      ? `<p class="field-hint" style="margin:8px 0 0">Installation date <strong>${esc(installDate)}</strong> (from Solcast settings) — efficiency is calculated automatically and saved daily on each install-date anniversary (00:15 local).</p>`
      : `<p class="field-hint" style="margin:8px 0 0">Set an installation date under <strong>Settings → Solcast</strong> to auto-calculate efficiency from system age.</p>`;
    return `<header class="header"><h1>${esc(title)}</h1>${subtitle ? `<p>${esc(subtitle)}</p>` : ""}</header>
<section class="card" style="margin-bottom:12px"><p class="card-title">PV Configuration</p>
<p class="field-hint" style="margin:0">Panel count, wattage, efficiency, tilt, and azimuth drive the native Solcast rooftop PV forecast on Overview and Energy charts.</p>
${installHint}
<div class="field" style="margin-top:12px"><label>Annual degradation (%)</label>
<p class="field-hint">Solcast-style performance loss per year (default 2% — pro-rated by month since installation).</p>
<input type="number" min="0" max="10" step="0.1" data-field="pv-meta:annual_degradation_pct" value="${esc(String(annualRate))}" ${this._busy || !installDate ? "disabled" : ""} aria-label="Annual degradation percent"></div>
</section>
${this._renderPvStringBlock("pv1")}
${this._renderPvStringBlock("pv2")}
<div class="btn-row"><button type="button" class="btn btn-primary" data-action="save-pv-config" ${this._busy ? "disabled" : ""}>Save PV configuration</button></div>`;
  }

  _renderSettingsPv() {
    return this._renderPvConfiguration({
      title: "PV Configuration",
      subtitle: "Configure PV1 and PV2 arrays for analysis",
    });
  }

  _renderTariffRateBlock(kind, { label, unitLabel, placeholder, liveMeta, pluginEntityId }) {
    if (!this._tariffDraft) this._initTariffDraft();
    const draft = this._tariffDraft;
    const currency = normalizeTariffCurrency(draft.currency);
    const sourceKey = `${kind}_source`;
    const entityKey = `${kind}_entity`;
    const isStanding = kind === "standing";
    const source = isStanding
      ? normalizeTariffStandingSource(draft[sourceKey])
      : draft[sourceKey] === "entity"
        ? "entity"
        : "schedule";
    const manualKey = isStanding ? "standing_charge_p_per_day" : `${kind}_p_per_kwh`;
    const manualMinor = draft[manualKey];
    const manualDisplay = manualMinor > 0 ? minorToMajor(manualMinor, currency) : "";
    const entityId = draft[entityKey] || "";
    const inputStep = tariffRateInputStep(currency);
    const suggestedHint = source === "entity" ? tariffSuggestedEntitiesHint(this._hass, kind) : "";
    const scheduleOption = isStanding ? "plugin" : "schedule";
    const scheduleLabel = isStanding
      ? "Plugin sensor (configured below)"
      : "Time-of-use schedule (plugin sensor)";
    let liveHint = "";
    if (source === "entity") {
      if (liveMeta?.available === false) {
        liveHint = entityId
          ? `Sensor ${entityId} is unavailable`
          : "Choose a sensor that reports this rate";
      } else if (liveMeta?.resolved_p != null) {
        liveHint = `Live: ${formatTariffMoney(liveMeta.resolved_p, currency)}${unitLabel}${liveMeta.entity_id ? ` from ${liveMeta.entity_id}` : ""}`;
      } else if (entityId && liveMeta?.state != null) {
        liveHint = `Live state: ${liveMeta.state}${liveMeta.unit ? ` ${liveMeta.unit}` : ""} — could not convert to ${currency} automatically`;
      } else if (entityId) {
        liveHint = "Waiting for a numeric reading from the selected sensor";
      } else {
        liveHint = suggestedHint;
      }
    } else if (pluginEntityId) {
      liveHint = `Plugin sensor: ${pluginEntityId} — updated on schedule boundaries for recorder history`;
    } else if (!isStanding) {
      liveHint = "Save to create plugin sensors that update each hour (or when the band changes)";
    }
    const entityHint = source === "entity" ? liveHint || suggestedHint : liveHint;
    const standingApiLocked =
      isStanding &&
      source === "plugin" &&
      tariffApiLocksStandingCharge(this._plantState?.tariff, this._octopusDraft);
    const standingInputDisabled = this._busy || standingApiLocked;
    const standingManualBlock =
      isStanding && source === "plugin"
        ? `<div class="field" data-tariff-manual="${esc(kind)}">
<p class="field-hint">${
            standingApiLocked
              ? `Synced from Octopus automatically whenever rates are fetched — published to the plugin sensor in ${esc(currency)}/day`
              : `Daily standing charge in ${esc(currency)} — published to the plugin sensor on save`
          }</p>
<input type="number" min="0" max="9999" step="${esc(inputStep)}" inputmode="decimal" data-field="tariff:${esc(kind)}:p" value="${esc(String(manualDisplay || ""))}" placeholder="${esc(placeholder)}" ${standingInputDisabled ? "disabled readonly" : ""}>
</div>`
        : "";
    return `<div class="tariff-rate-block${standingApiLocked ? " tariff-standing-locked" : ""}" data-tariff-kind="${esc(kind)}">
<div class="field">
<label>${esc(label)}</label>
<select data-field="tariff:${esc(kind)}:source" ${this._busy ? "disabled" : ""}>
<option value="${esc(scheduleOption)}" ${source === scheduleOption ? "selected" : ""}>${esc(scheduleLabel)}</option>
<option value="entity" ${source === "entity" ? "selected" : ""}>Home Assistant sensor</option>
</select>
</div>
${standingManualBlock}
<div class="field" ${source === "entity" ? "" : 'style="display:none"'} data-tariff-entity="${esc(kind)}">
<p class="field-hint">${esc(entityHint || "Use the Home Assistant sensor picker — search by friendly name or entity id.")}</p>
<div class="tariff-entity-picker-host" data-tariff-picker="${esc(kind)}"></div>
</div>
</div>`;
  }

  _renderTariffScheduleEditor() {
    if (!this._tariffDraft) this._initTariffDraft();
    const draft = this._tariffDraft;
    const showImport = normalizeTariffImportSource(draft.import_source) === "schedule";
    const showExport = normalizeTariffExportSource(draft.export_source) === "schedule";
    if (!showImport && !showExport) return "";
    const octopusLocked = octopusNativeManagesSchedule(this._plantState?.tariff, this._octopusDraft);
    const scheduleDisabled = this._busy || octopusLocked;
    const currency = normalizeTariffCurrency(draft.currency);
    const schedule = normalizeTariffSchedule(draft.schedule);
    const activeBand = this._tariffActiveBand ?? 0;
    const bandChips = TARIFF_BAND_LABELS.map(
      (label, idx) =>
        `<button type="button" class="tariff-band-chip${idx === activeBand ? " is-active" : ""}" data-action="tariff-pick-band" data-band="${idx}" ${scheduleDisabled ? "disabled" : ""}><span class="tariff-band-swatch" style="background:${TARIFF_BAND_COLORS[idx]}"></span>${esc(label)}</button>`
    ).join("");
    const hourBlocks = schedule.hours
      .map((bandIdx, hour) => {
        const color = TARIFF_BAND_COLORS[bandIdx] ?? TARIFF_BAND_COLORS[0];
        return `<button type="button" class="tariff-hour-block" style="background:${color}" title="${String(hour).padStart(2, "0")}:00–${String((hour + 1) % 24).padStart(2, "0")}:00 · ${esc(TARIFF_BAND_LABELS[bandIdx] || "Band A")}" data-action="tariff-hour" data-hour="${hour}" ${scheduleDisabled ? "disabled" : ""} aria-label="Hour ${hour}"></button>`;
      })
      .join("");
    const hourLabels = schedule.hours
      .map((_, hour) => `<span>${hour % 6 === 0 ? String(hour).padStart(2, "0") : ""}</span>`)
      .join("");
    const inputStep = tariffRateInputStep(currency);
    const bandRows = schedule.bands
      .map((band, idx) => {
        const importDisplay =
          showImport && band.import_p_per_kwh > 0 ? minorToMajor(band.import_p_per_kwh, currency) : "";
        const exportDisplay =
          showExport && band.export_p_per_kwh > 0 ? minorToMajor(band.export_p_per_kwh, currency) : "";
        return `<div class="tariff-band-rate-row">
<span class="tariff-band-chip" style="cursor:default;border:none;padding:4px 0"><span class="tariff-band-swatch" style="background:${TARIFF_BAND_COLORS[idx]}"></span>${esc(TARIFF_BAND_LABELS[idx])}</span>
${showImport ? `<div class="field" style="margin:0"><label>Import ${esc(currency)}/kWh</label><input type="number" min="0" max="9999" step="${esc(inputStep)}" inputmode="decimal" data-field="tariff:schedule:band:${idx}:import" value="${esc(String(importDisplay || ""))}" placeholder="${currency === "GBP" ? "e.g. 0.245" : "e.g. 0.25"}" ${scheduleDisabled ? "disabled" : ""}></div>` : `<div></div>`}
${showExport ? `<div class="field" style="margin:0"><label>Export ${esc(currency)}/kWh</label><input type="number" min="0" max="9999" step="${esc(inputStep)}" inputmode="decimal" data-field="tariff:schedule:band:${idx}:export" value="${esc(String(exportDisplay || ""))}" placeholder="${currency === "GBP" ? "e.g. 0.150" : "e.g. 0.15"}" ${scheduleDisabled ? "disabled" : ""}></div>` : `<div></div>`}
</div>`;
      })
      .join("");
    const pluginIds = this._plantState?.tariff?.plugin_sensors ?? {};
    const pluginHint = pluginIds.import || pluginIds.export
      ? `<p class="field-hint" style="margin:0 0 12px">Plugin sensors: ${[pluginIds.import, pluginIds.export].filter(Boolean).map((id) => esc(id)).join(" · ") || "—"} — rates update at each hour boundary so the recorder captures when costs change.</p>`
      : `<p class="field-hint" style="margin:0 0 12px">Plugin sensors are created when you save. They update at each hour boundary so the recorder captures when costs change (same path planned for Agile API tariffs).</p>`;
    const scheduleIntro = octopusLocked
      ? "Rates and hour bands are synced from Octopus automatically whenever rates are fetched (including the 30-minute poll). Edit Octopus settings above to change tariff source."
      : "24 hourly blocks from 00:00 to 24:00, same every day. Pick a band colour, then tap hours to assign it. Use one band for a flat tariff, or two to four for peak/off-peak.";
    return `<div class="card tariff-schedule-card${octopusLocked ? " tariff-schedule-locked" : ""}">
<p class="card-title">Daily time-of-use schedule</p>
<p class="field-hint" style="margin:0 0 12px">${esc(scheduleIntro)}</p>
${pluginHint}
<div class="tariff-band-picker">${bandChips}</div>
<div class="tariff-hour-grid">${hourBlocks}</div>
<div class="tariff-hour-labels">${hourLabels}</div>
<div class="tariff-band-rates">${bandRows}</div>
</div>`;
  }

  _renderSettingsTariff() {
    if (!this._tariffDraft) this._initTariffDraft();
    const draft = this._tariffDraft;
    const currency = normalizeTariffCurrency(draft.currency);
    const live = this._plantState?.tariff ?? {};
    const liveCurrency = tariffCurrencyFromTariff(live);
    const entities = live.entities ?? {};
    const historyCount = live.rate_history_count ?? 0;
    const lastUpdated = live.last_updated_at ? esc(formatSolcastTimestamp(live.last_updated_at)) : "Never";
    const effective = tariffEffectiveRates(live);
    const effectiveBits = [];
    if (effective.import_p_per_kwh) effectiveBits.push(`Import ${formatTariffMoney(effective.import_p_per_kwh, liveCurrency)}/kWh`);
    if (effective.export_p_per_kwh) effectiveBits.push(`Export ${formatTariffMoney(effective.export_p_per_kwh, liveCurrency)}/kWh`);
    if (effective.standing_charge_p_per_day) {
      effectiveBits.push(`Standing ${formatTariffMoney(effective.standing_charge_p_per_day, liveCurrency)}/day`);
    }
    const currencyOptions = Object.entries(TARIFF_CURRENCIES)
      .sort((a, b) => a[1].name.localeCompare(b[1].name))
      .map(
        ([code, meta]) =>
          `<option value="${esc(code)}" ${code === currency ? "selected" : ""}>${esc(code)} — ${esc(meta.name)}</option>`
      )
      .join("");
    const pluginSensors = live.plugin_sensors ?? {};
    const scheduleStatus = live.schedule_status ?? {};
    const bandLabel =
      scheduleStatus.band_index != null ? TARIFF_BAND_LABELS[scheduleStatus.band_index] || "" : "";
    return `<header class="header"><h1>Tariff</h1><p>Electricity rates for cost and revenue analysis. Use the daily schedule with plugin sensors (recorder-friendly), bind external Home Assistant sensors, or combine both.</p></header>
<div class="card">
<p class="card-title">Electricity tariff</p>
<div class="field">
<label>Currency</label>
<select data-field="tariff:currency" ${this._busy ? "disabled" : ""}>${currencyOptions}</select>
<p class="field-hint">Rates are stored in the selected currency. Changing currency does not convert existing values — re-enter rates after switching.</p>
</div>
${this._renderTariffRateBlock("import", {
      label: "Import cost",
      unitLabel: `${currency}/kWh`,
      placeholder: currency === "GBP" ? "e.g. 0.245" : "e.g. 0.25",
      liveMeta: entities.import,
      pluginEntityId: pluginSensors.import,
    })}
${this._renderTariffRateBlock("export", {
      label: "Export revenue",
      unitLabel: `${currency}/kWh`,
      placeholder: currency === "GBP" ? "e.g. 0.150" : "e.g. 0.15",
      liveMeta: entities.export,
      pluginEntityId: pluginSensors.export,
    })}
${this._renderTariffScheduleEditor()}
${this._renderTariffRateBlock("standing", {
      label: "Daily standing charge",
      unitLabel: `${currency}/day`,
      placeholder: currency === "GBP" ? "e.g. 0.53" : "e.g. 1.00",
      liveMeta: entities.standing,
      pluginEntityId: pluginSensors.standing,
    })}
<div class="btn-row"><button type="button" class="btn btn-primary" data-action="save-tariff-settings" ${this._busy ? "disabled" : ""}>Save tariff</button></div>
</div>
<div class="card">
<p class="card-title">Status</p>
<p style="margin:0 0 8px;font-size:14px">${live.configured ? "Tariff configured — ready for cost analysis." : "Not configured yet — save at least one rate above."}</p>
${effectiveBits.length ? `<p class="field-hint" style="margin:0 0 8px">Effective rates now: ${esc(effectiveBits.join(" · "))}${bandLabel ? ` · ${esc(bandLabel)} (hour ${scheduleStatus.hour ?? "—"})` : ""}</p>` : ""}
<p class="field-hint" style="margin:0">Last saved: ${lastUpdated}${historyCount ? ` · ${esc(String(historyCount))} rate snapshot(s) recorded` : ""}</p>
</div>
${this._renderOctopusSettings()}`;
  }

  _renderOctopusSettings() {
    if (!this._octopusDraft) this._initOctopusDraft();
    const draft = this._octopusDraft;
    const live = this._plantState?.tariff?.octopus ?? {};
    const currency = tariffCurrencyFromTariff(this._plantState?.tariff ?? {});
    const keyPlaceholder = draft.api_key_set ? "••••••••  (leave blank to keep)" : "Paste Octopus API key";
    const native = draft.source !== "entity";
    const connected = Boolean(live.connected);
    const tariffType = live.tariff_type ? String(live.tariff_type) : "";
    const agile = tariffType === "agile" || tariffType === "tracker";
    const lastFetch = live.last_fetch_at ? esc(formatSolcastTimestamp(live.last_fetch_at)) : "Never";
    const lastErr = live.last_error ? esc(String(live.last_error)) : "";
    const importMeters = live.import_meters ?? [];
    const exportMeters = live.export_meters ?? [];
    const importOptions = importMeters
      .map(
        (m) =>
          `<option value="${esc(m.mpan)}" ${draft.import_mpan === m.mpan ? "selected" : ""}>${esc(m.display_name || m.mpan)}</option>`
      )
      .join("");
    const exportOptions = exportMeters
      .map(
        (m) =>
          `<option value="${esc(m.mpan)}" ${draft.export_mpan === m.mpan ? "selected" : ""}>${esc(m.display_name || m.mpan)}</option>`
      )
      .join("");
    const rateBits = [];
    if (live.current_import_p_per_kwh != null) {
      rateBits.push(`Import ${formatTariffMoney(live.current_import_p_per_kwh, currency)}/kWh`);
    }
    if (live.current_export_p_per_kwh != null) {
      rateBits.push(`Export ${formatTariffMoney(live.current_export_p_per_kwh, currency)}/kWh`);
    }
    const statusLines = [];
    if (connected && live.import_tariff_code) {
      statusLines.push(`Import tariff: ${esc(live.import_tariff_code)}`);
    }
    if (live.export_tariff_code) {
      statusLines.push(`Export tariff: ${esc(live.export_tariff_code)}`);
    }
    if (tariffType) {
      statusLines.push(`Type: ${esc(tariffType)}${agile ? " — live half-hourly plugin sensors" : " — daily schedule"}`);
    }
    if (rateBits.length) statusLines.push(`Current: ${esc(rateBits.join(" · "))}`);
    statusLines.push(`Last fetch: ${lastFetch}`);
    if (lastErr) statusLines.push(`Error: ${lastErr}`);
    const entityBlock =
      draft.source === "entity"
        ? `<div class="field"><label>External import rate sensor</label>
<div class="tariff-entity-picker-host" data-octopus-picker="import"></div>
</div>
<div class="field"><label>External export rate sensor</label>
<div class="tariff-entity-picker-host" data-octopus-picker="export"></div>
<p class="field-hint">Use this if you already run the official <code>octopus_energy</code> integration — Fox Plant reads those entities instead of polling Octopus directly.</p>
</div>`
        : `<div class="field"><label>API key</label>
<input type="password" autocomplete="off" data-field="octopus:api_key" value="${esc(String(draft.api_key || ""))}" placeholder="${esc(keyPlaceholder)}" ${this._busy ? "disabled" : ""}>
<p class="field-hint">Create a key in your <a class="field-link" href="${esc(OCTOPUS_API_DOCS_URL)}" target="_blank" rel="noopener noreferrer">Octopus dashboard</a> (Developer settings → API access).</p>
</div>
<div class="field"><label>Account number</label>
<input type="text" data-field="octopus:account_number" value="${esc(String(draft.account_number || ""))}" placeholder="A-12345678" ${this._busy ? "disabled" : ""}>
</div>
${importMeters.length > 1 ? `<div class="field"><label>Import MPAN</label><select data-field="octopus:import_mpan" ${this._busy ? "disabled" : ""}><option value="">Select meter…</option>${importOptions}</select></div>` : ""}
${exportMeters.length > 1 ? `<div class="field"><label>Export MPAN (SEG)</label><select data-field="octopus:export_mpan" ${this._busy ? "disabled" : ""}><option value="">None / auto</option>${exportOptions}</select></div>` : ""}`;
    const scheduleAutoHint =
      native && draft.enabled && connected && !agile
        ? "Fixed tariffs update the daily schedule automatically when rates are fetched."
        : "";
    return `<div class="card">
<p class="card-title">Octopus Energy</p>
<p class="field-hint" style="margin:0 0 12px">Native Octopus polling for Go, Economy 7, flat SVT, and Agile. ${scheduleAutoHint || "Fixed tariffs sync the 24-hour schedule on fetch; Agile updates plugin import/export sensors every 30 minutes (including negative rates)."}</p>
<div class="toggle-row"><span><strong>Enable Octopus tariff link</strong></span>
<input type="checkbox" data-field="octopus:enabled" ${draft.enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>Rate source</label>
<select data-field="octopus:source" ${this._busy ? "disabled" : ""}>
<option value="native" ${native ? "selected" : ""}>Native API (recommended)</option>
<option value="entity" ${!native ? "selected" : ""}>External Home Assistant sensors</option>
</select>
</div>
${entityBlock}
<div class="btn-row">
<button type="button" class="btn btn-secondary" data-action="test-octopus" ${this._busy || !native ? "disabled" : ""}>Test connection</button>
<button type="button" class="btn btn-secondary" data-action="fetch-octopus" ${this._busy || !draft.enabled || !native ? "disabled" : ""}>Fetch rates now</button>
<button type="button" class="btn btn-primary" data-action="save-octopus-settings" ${this._busy ? "disabled" : ""}>Save Octopus</button>
</div>
${statusLines.length ? `<p class="field-hint" style="margin:12px 0 0">${statusLines.map((l) => esc(l)).join("<br>")}</p>` : ""}
</div>`;
  }

  _renderSettingsSolcast() {
    if (!this._solcastDraft) this._initSolcastDraft();
    const draft = this._solcastDraft;
    const live = this._plantState?.solcast ?? {};
    const keyPlaceholder = draft.api_key_set ? "••••••••  (leave blank to keep)" : "Paste Solcast API key";
    const coordConfigured = Boolean(live.coordinates_configured);
    const coordDisplay =
      live.coordinates?.latitude != null && live.coordinates?.longitude != null
        ? `${Number(live.coordinates.latitude).toFixed(SOLCAST_COORD_DECIMALS)}, ${Number(live.coordinates.longitude).toFixed(SOLCAST_COORD_DECIMALS)}`
        : "Not set";
    const installDisplay = live.installation_date
      ? esc(String(live.installation_date))
      : "Not set";
    const installMax = solcastInstallationDateMax();
    const lastFetch = esc(formatSolcastTimestamp(live.cache_updated_at || live.last_fetch_at));
    const nextFetch = esc(formatSolcastNextFetch(live));
    const lastErr = live.last_error ? esc(String(live.last_error)) : "None";
    const pvReqs = live.pv_requests ?? [];
    const pvReqLines = pvReqs.length
      ? pvReqs
          .map(
            (r) =>
              `${esc(r.label)}: ${esc(String(r.capacity_kw))} kW · ${esc(String(r.tilt))}° tilt · ${esc(String(r.azimuth))}° az · loss ${esc(String(r.loss_factor))}`
          )
          .join("<br>")
      : "Enable PV strings in PV Configuration to request rooftop forecasts.";
    const solcastLiveOn = solcastEnabledFromLive(live) && live.fetch_pv_forecast !== false;
    const pvStatus = live.pv_forecast_available
      ? `${live.pv_forecast_periods ?? 0} forecast periods · ${live.pv_power_now_kw != null ? `${Number(live.pv_power_now_kw).toFixed(2)} kW now` : "power pending"}${live.forecast_persisted ? " · cached" : ""}`
      : live.forecast_persisted
        ? `${live.pv_forecast_periods ?? 0} cached periods — awaiting chart reload`
        : solcastLiveOn
          ? "Awaiting PV forecast fetch"
          : "PV forecast off";
    const sched = live.poll_schedule;
    let scheduleHint = "";
    if (sched && draft.auto_update === "daylight") {
      const interval = sched.interval_minutes ?? "—";
      const hours = sched.window_hours ?? "—";
      const until = sched.poll_until ? new Date(sched.poll_until).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";
      const inWin = sched.in_window ? "active now" : "outside window (before sunrise or within 1h of sunset)";
      scheduleHint = `<p class="field-hint">Daylight schedule: <strong>${esc(String(hours))}</strong> h between sunrise and 1 h before sunset · about <strong>${esc(String(interval))}</strong> min between refreshes (spread across your ${esc(String(draft.api_limit))}/day API limit) · polls until <strong>${esc(until)}</strong> · ${esc(inWin)}</p>`;
    } else if (sched && draft.auto_update === "all_day") {
      scheduleHint = `<p class="field-hint">24 h mode: about <strong>${esc(String(sched.interval_minutes ?? "—"))}</strong> min between refreshes.</p>`;
    }
    return `<header class="header"><h1>Solcast</h1><p><a class="field-link" href="${esc(SOLCAST_API_DOCS_URL)}" target="_blank" rel="noopener noreferrer">Solcast hobbyist API</a> for <strong>rooftop PV forecast</strong> only — overview weather and StormSafe stay on Google Weather.</p></header>
<div class="card">
<p class="card-title">Account</p>
<p class="field-hint">Register a free <a class="field-link" href="${esc(SOLCAST_HOBBYIST_URL)}" target="_blank" rel="noopener noreferrer">Home PV System</a> account (10 API requests/day). All quota goes to PV forecasts — no weather calls.</p>
<div class="toggle-row"><span><strong>Enable Solcast PV forecast</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Replaces a third-party Solcast integration for chart PV lines</span></span>
<input type="checkbox" data-field="solcast:enabled" ${draft.enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>API key</label>
<input type="password" autocomplete="off" data-field="solcast:api_key" value="${esc(String(draft.api_key || ""))}" placeholder="${esc(keyPlaceholder)}" ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>API limit (requests per day)</label>
<p class="field-hint">Hobbyist plans are typically 10/day — used to spread automatic polling.</p>
<input type="number" min="1" max="50" step="1" data-field="solcast:api_limit" value="${esc(String(draft.api_limit))}" ${this._busy ? "disabled" : ""}></div>
</div>
<div class="card">
<p class="card-title">Auto update</p>
<div class="field"><label>Schedule</label>
<select data-field="solcast:auto_update" ${this._busy ? "disabled" : ""}>
<option value="daylight" ${draft.auto_update === "daylight" ? "selected" : ""}>Automatic update of forecasts from sunrise to sunset</option>
<option value="all_day" ${draft.auto_update === "all_day" ? "selected" : ""}>Automatic update over 24 hours</option>
</select></div>
${scheduleHint}
<p class="field-hint">Each refresh uses <strong>1 request per unique tilt/azimuth group</strong>. In daylight mode, your ${esc(String(draft.api_limit))} daily calls are spread from <strong>sunrise</strong> until <strong>1 hour before sunset</strong> (from Home Assistant <code>sun.sun</code>).</p>
<div class="toggle-row" style="margin-top:12px"><span><strong>Fetch PV forecast</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Uses hobbyist <code>rooftop_sites/{resource_id}/forecasts</code> (matched to your toolkit Home PV sites)</span></span>
<input type="checkbox" data-field="solcast:fetch_pv_forecast" ${draft.fetch_pv_forecast ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
</div>
<div class="card">
<p class="card-title">Rooftop tilt &amp; azimuth</p>
<p class="field-hint" style="margin:0">Used for each enabled PV string on the Solcast API. Panel count, wattage, and efficiency are under <strong>Settings → PV Configuration</strong>. Saved together when you press <strong>Save</strong> below.</p>
${this._renderPvTiltAzimuthFields("pv1", { allowWhenDisabled: true })}
${this._renderPvTiltAzimuthFields("pv2", { allowWhenDisabled: true })}
</div>
<div class="card">
<p class="card-title">Solcast site location</p>
<p class="field-hint">Hobbyist accounts may register <strong>two</strong> rooftop sites on <a class="field-link" href="${esc(SOLCAST_ACCOUNT_LOCATIONS_URL)}" target="_blank" rel="noopener noreferrer">Solcast → Locations</a>. Enter the <strong>latitude and longitude exactly as shown there</strong> for the site you use. Do <strong>not</strong> copy Home Assistant home coordinates — extra decimal places will not match Solcast and API calls can fail or return the wrong site.</p>
<div class="field"><label>Latitude <span class="field-required">*</span></label>
<input type="number" step="0.0001" inputmode="decimal" data-field="solcast:latitude" value="${esc(String(draft.latitude))}" placeholder="e.g. -33.8568" ${this._busy ? "disabled" : ""} required></div>
<div class="field"><label>Longitude <span class="field-required">*</span></label>
<input type="number" step="0.0001" inputmode="decimal" data-field="solcast:longitude" value="${esc(String(draft.longitude))}" placeholder="e.g. 151.2153" ${this._busy ? "disabled" : ""} required></div>
<p class="field-hint">Saved as ${SOLCAST_COORD_DECIMALS} decimal places to match typical Solcast listings. Saved site: <strong>${esc(coordDisplay)}</strong>${coordConfigured ? "" : " — required when Solcast is enabled"}</p>
<div class="field"><label>Installation date</label>
<p class="field-hint">Same field as Solcast <strong>Add Home PV System</strong> (used for age derating on their site). Optional here — not sent to the rooftop API yet. Use your best estimate if unsure.</p>
<input type="date" data-field="solcast:installation_date" value="${esc(String(draft.installation_date || ""))}" max="${esc(installMax)}" ${this._busy ? "disabled" : ""}></div>
<p class="field-hint">Saved: <strong>${installDisplay}</strong></p>
<div class="field"><label>Data period</label>
<p class="field-hint">PT30M = 30-minute resolution (recommended for hobbyist quota).</p>
<input type="text" data-field="solcast:period" value="${esc(String(draft.period))}" readonly></div>
</div>
<div class="card">
<p class="card-title">Status</p>
<div class="entity-list">
<div class="entity-row"><span class="entity-name">API used today</span><span class="entity-value">${esc(String(live.api_used_today ?? 0))} / ${esc(String(live.api_limit ?? draft.api_limit))}</span></div>
<div class="entity-row"><span class="entity-name">Remaining today</span><span class="entity-value">${esc(String(live.api_remaining ?? "—"))}</span></div>
<div class="entity-row"><span class="entity-name">Last fetch</span><span class="entity-value">${lastFetch}</span></div>
<div class="entity-row"><span class="entity-name">Next fetch</span><span class="entity-value">${nextFetch}</span></div>
<div class="entity-row"><span class="entity-name">Last error</span><span class="entity-value">${lastErr}</span></div>
<div class="entity-row"><span class="entity-name">PV forecast</span><span class="entity-value">${esc(pvStatus)}</span></div>
<div class="entity-row"><span class="entity-name">Installation date</span><span class="entity-value">${installDisplay}</span></div>
<div class="entity-row"><span class="entity-name">Toolkit sites</span><span class="entity-value">${esc(
      live.hobbyist_sites_resolved
        ? (live.rooftop_sites_meta ?? [])
            .map((s) => `${s.label}: ${s.name || s.resource_id}`)
            .join(" · ") || "Linked"
        : "Not linked — press Save"
    )}</span></div>
</div>
<p class="field-hint" style="margin-top:8px"><strong>API groups</strong> (from PV config):<br>${pvReqLines}</p>
<p class="field-hint">Diagnostic sensors expose <code>detailed_forecast</code> for automations — charts use plant state directly.</p>
</div>
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="save-solcast-settings" ${this._busy ? "disabled" : ""}>Save</button>
<button type="button" class="btn btn-secondary" data-action="test-solcast" ${this._busy ? "disabled" : ""}>Test connection</button>
<p class="field-hint" style="margin-top:10px">Test lists your <strong>Home PV systems</strong> from the Solcast toolkit (does not use your daily forecast quota).</p>
</div>`;
  }

  _renderSettingsGlow() {
    if (!this._glowDraft) this._initGlowDraft();
    const draft = this._glowDraft;
    const pwPlaceholder = draft.password_set ? "••••••••" : "Bright app password";
    return `<header class="header"><h1>Glow smart meter</h1><p>Optional Hildebrand Glow IHD for <strong>live grid import</strong> from your SMETS2 meter. PV production always comes from the Fox plant — Glow replaces only grid-side readings.</p></header>
<div class="card">
<p class="card-title">Enable</p>
<p class="field-hint">Requires a Glow IHD/CAD on your network with MQTT enabled by Hildebrand, or Bright API credentials. See the <a class="field-link" href="${esc(GLOW_DOCS_URL)}" target="_blank" rel="noopener noreferrer">Glowmarkt Bright API docs</a> and <a class="field-link" href="${esc(GLOW_MQTT_INTEGRATION_URL)}" target="_blank" rel="noopener noreferrer">MQTT topic reference</a>.</p>
<div class="toggle-row"><span><strong>Enable Glow smart meter</strong><br><span style="font-size:12px;color:var(--secondary-text-color)">Uses utility-meter data for grid import (more accurate than inverter CTs)</span></span>
<input type="checkbox" data-field="glow:enabled" ${draft.enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
</div>
<div class="card">
<p class="card-title">Live MQTT (recommended)</p>
<p class="field-hint">Subscribe to local <code>glow/{MAC}/SENSOR/electricitymeter</code> broadcasts — updates every few seconds with live kW and cumulative kWh.</p>
<div class="toggle-row"><span><strong>MQTT listener</strong></span>
<input type="checkbox" data-field="glow:mqtt_enabled" ${draft.mqtt_enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>Topic prefix</label>
<input type="text" data-field="glow:topic_prefix" value="${esc(String(draft.topic_prefix || "glow"))}" placeholder="glow" ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>Device ID</label>
<p class="field-hint">Glow MAC without colons, or <code>+</code> for all devices on the broker.</p>
<input type="text" data-field="glow:device_id" value="${esc(String(draft.device_id || "+"))}" placeholder="+" ${this._busy ? "disabled" : ""}></div>
</div>
<div class="card">
<p class="card-title">Bright API (optional)</p>
<p class="field-hint">Cloud fallback for resource discovery and historical readings. Same credentials as the Bright mobile app.</p>
<div class="toggle-row"><span><strong>API access</strong></span>
<input type="checkbox" data-field="glow:api_enabled" ${draft.api_enabled ? "checked" : ""} ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>Bright username</label>
<input type="text" autocomplete="username" data-field="glow:username" value="${esc(String(draft.username || ""))}" ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>Bright password</label>
<input type="password" autocomplete="current-password" data-field="glow:password" value="${esc(String(draft.password || ""))}" placeholder="${esc(pwPlaceholder)}" ${this._busy ? "disabled" : ""}></div>
<div class="field"><label>Import resource ID</label>
<input type="text" data-field="glow:import_resource_id" value="${esc(String(draft.import_resource_id || ""))}" placeholder="Auto-discovered on test" ${this._busy ? "disabled" : ""}></div>
</div>
<div class="card">
<p class="card-title">Status</p>
<div data-glow-live>${this._renderGlowStatusInnerHtml()}</div>
</div>
<div class="btn-row">
<button type="button" class="btn btn-primary" data-action="save-glow-settings" ${this._busy ? "disabled" : ""}>Save</button>
<button type="button" class="btn btn-secondary" data-action="test-glow" ${this._busy ? "disabled" : ""}>Test Bright API</button>
</div>`;
  }

  _renderSettingsControl() {
    const active = this._plantState?.control_active;
    return `<header class="header"><h1>Plant control</h1></header>
<div class="card">
<p style="margin:0 0 12px;line-height:1.5;font-size:14px">When <strong>active</strong>, Fox Plant is the only writer for charge periods (via <code>foxess_modbus</code>). Release control if you need to edit schedules in the Fox app temporarily.</p>
<div class="btn-row">
${active
      ? `<button type="button" class="btn btn-danger" data-action="release-control" ${this._busy ? "disabled" : ""}>Release control</button>`
      : `<button type="button" class="btn btn-primary" data-action="take-control" ${this._busy ? "disabled" : ""}>Take control</button>`}
<button type="button" class="btn btn-secondary" data-action="apply-baseline" ${this._busy ? "disabled" : ""}>Apply baseline now</button>
</div></div>`;
  }

  _renderSettings(plant) {
    switch (this._settingsView) {
      case "quick":
        return this._renderSettingsQuick();
      case "schedules":
        return this._renderSettingsSchedules();
      case "workmode":
        return this._renderSettingsWorkMode();
      case "pv":
        return this._renderSettingsPv();
      case "tariff":
        return this._renderSettingsTariff();
      case "smart":
        return this._renderSettingsSmartCharge();
      case "solcast":
        return this._renderSettingsSolcast();
      case "glow":
        return this._renderSettingsGlow();
      case "storm":
        return this._renderSettingsStorm();
      case "control":
        return this._renderSettingsControl();
      default:
        return this._renderSettingsMain(plant);
    }
  }

  _renderView(plant) {
    switch (this._view) {
      case "overview":
        return this._renderOverview(plant);
      case PANEL_VIEW_DEVICE_LEGACY:
        return this._renderDeviceLegacy(plant);
      case "device_new":
        return this._renderDeviceNew(plant);
      case "energy_analysis":
        return this._renderEnergyAnalysis(plant);
      case "reports":
        return this._renderReports(plant);
      case "settings":
        return this._renderSettings(plant);
      default:
        return "";
    }
  }

  _render() {
    try {
      this._renderPanel();
    } catch (err) {
      console.error("FoxESS Plant panel render failed", err);
      const ver = panelVersionFromModuleUrl() || PANEL_VERSION;
      this._root.innerHTML = `<div class="shell"><main class="main"><div class="main-inner"><p class="placeholder">Fox Plant panel error: ${esc(err?.message || String(err))}</p><p class="placeholder" style="margin-top:8px;font-size:12px;opacity:0.75">Panel JS ${esc(ver)} — update FoxESS Plant in HACS, restart Home Assistant, then call <code>foxess_plant.reload_panel</code> or hard-refresh the browser.</p></div></main></div>`;
    }
  }

  _renderPanel() {
    this._clearOctopusGreenerHover();
    if (!this._hass) {
      this._headerHasSubTabs = undefined;
    this._headerSubNavView = undefined;
      this._root.innerHTML = renderPanelPlaceholderHtml("Loading Fox Plant…");
      return;
    }
    const plant = this._getPlant();
    if (!plant) {
      this._headerHasSubTabs = undefined;
    this._headerSubNavView = undefined;
      void this._recoverEmptyPanelConfig();
      this._root.innerHTML = renderPanelPlaceholderHtml(
        "Add FoxESS Plant and select your inverter device."
      );
      return;
    }

    this._view = normalizePanelView(this._view);

    const showSubTabs = this._view === "settings" || this._view === "device_new" || this._view === "reports";
    const subNavView = showSubTabs ? this._view : "";
    let shell = this._root.querySelector(".shell");
    if (!shell) {
      shell = document.createElement("div");
      shell.className = "shell";
      shell.append(
        Object.assign(document.createElement("header"), { className: "page-header" }),
        Object.assign(document.createElement("main"), { className: "main" })
      );
      this._root.replaceChildren(shell);
      this._headerHasSubTabs = undefined;
      this._headerSubNavView = undefined;
    }
    this._syncShellLayoutClasses(shell);
    this._syncPanelBuildFooter(shell);

    const headerEl = shell.querySelector(".page-header");
    const reportsNavKey =
      this._view === "reports"
        ? reportsNavForState(this._plantState)
            .map((item) => item.id)
            .join(",")
        : "";
    if (
      this._headerHasSubTabs !== showSubTabs ||
      this._headerSubNavView !== subNavView ||
      this._headerReportsNavKey !== reportsNavKey
    ) {
      this._rebuildPageHeader(headerEl);
      this._headerSubNavView = subNavView;
      this._headerReportsNavKey = reportsNavKey;
    } else {
      this._syncTabActive(headerEl);
    }

    const mainEl = shell.querySelector(".main");
    const contentEl = ensureMainInner(mainEl);
    if (this._view === "settings" && this._settingsView === "smart") {
      this._captureSmartChargeDetailsOpen();
    }
    if (this._view === "overview") {
      this._renderOverviewMain(contentEl, plant);
    } else {
      this._flowSceneKey = undefined;
      this._flowScenePlantId = undefined;
      this._flowSceneKeyPending = undefined;
      this._flowSceneKeyPendingN = 0;
      contentEl.innerHTML = this._renderView(plant);
    }
    this._syncEnergyBalanceHelpModal(shell);
    this._syncFoxAlarmDetailModal(shell);

    if (this._view === "settings" && this._settingsView === "quick") {
      this._bindTripleSoc();
    }
    if (this._view === "settings" && this._settingsView === "storm" && this._stormDraft) {
      this._syncStormTriggerPicker();
    }
    if (this._view === "settings" && this._settingsView === "tariff" && this._tariffDraft) {
      void this._syncTariffEntityPickers();
      void this._syncOctopusEntityPickers();
    }
    if (this._view === "settings" && this._settingsView === "smart") {
      this._bindSmartChargeDetailsOpen();
    }
    if (
      (this._view === "overview" ||
        ((this._view === "energy_analysis") && this._energyPeriod === "day")) &&
      this._statisticsChart?.series &&
      this._statisticsChart?.range
    ) {
      this._bindStatisticsChart();
    } else if (
      this._view === "energy_analysis" &&
      this._root.querySelector("[data-octopus-greener-plot]")
    ) {
      this._bindOctopusGreenerCharts();
    }
    if (this._view === "overview") {
      bindOverviewDailyCharts(this._root);
      this._bindOctopusGreenerCharts();
      if (!mainEl?.querySelector?.(".overview-hourly-weather-slot [data-hourly-weather][data-bound]")) {
        bindHourlyWeatherOverview(this._root);
      }
      if (this._batterySocChart?.socPts?.length) {
        this._bindBatterySocChart();
      }
    }
    if (this._view === "energy_analysis") {
      const plant = this._getPlant();
      if (!plant) return;
      const cacheKey = this._energyChartCacheKey(plant);
      if (this._energyPeriod === "day") {
        if (
          !this._statisticsChartLoading &&
          this._statisticsChartNeedsReload(plant)
        ) {
          this._loadStatisticsChart();
        }
      } else if (!this._energyChartLoading && (this._energyChartPlantId !== cacheKey || !this._energyChart)) {
        this._loadEnergyCharts();
      }
      const sparkKey = this._analysisSummarySparkCacheKey(plant);
      if (
        !this._analysisSummarySparkLoading &&
        (this._analysisSummarySparkKey !== sparkKey || !this._analysisSummarySpark)
      ) {
        void this._loadAnalysisSummarySpark();
      }
      if (
        plant &&
        statisticsSolcastForecastEnabled(this._plantState, this._hass) &&
        !this._forecastAccuracyAnalysisLoading &&
        !this._forecastAccuracyAnalysisInflight &&
        this._forecastAccuracyAnalysisKey !== this._forecastAccuracyAnalysisCacheKey(plant)
      ) {
        void this._loadForecastAccuracyAnalysis();
      }
      if (
        this._view === "energy_analysis" &&
        !this._overviewDailyLoading &&
        (this._overviewDailyPlantId !== plant.entry_id || !this._overviewDaily)
      ) {
        this._loadOverviewDailyCards();
      }
    }
    if (this._view === "overview") {
      const plant = this._getPlant();
      if (
        plant &&
        statisticsSolcastForecastEnabled(this._plantState, this._hass) &&
        !this._forecastAccuracyOverviewLoading &&
        !this._forecastAccuracyOverviewInflight &&
        this._forecastAccuracyOverviewKey !== this._forecastAccuracyOverviewCacheKey(plant)
      ) {
        void this._loadForecastAccuracyOverview();
      }
      if (
        plant &&
        !this._statisticsChartLoading &&
        (this._statisticsChartPlantId !== `${plant.entry_id}:overview` || !this._statisticsChart)
      ) {
        this._loadOverviewStatisticsChart();
      }
      if (
        plant &&
        !this._batterySocChartLoading &&
        (this._batterySocChartPlantId !== plant.entry_id || !this._batterySocChart)
      ) {
        this._loadBatterySocChart();
      }
      if (
        plant &&
        !this._overviewDailyLoading &&
        (this._overviewDailyPlantId !== plant.entry_id || !this._overviewDaily)
      ) {
        this._loadOverviewDailyCards();
      }
      if (
        plant &&
        !this._overviewSystemStatusLoading &&
        (this._overviewSystemStatusPlantId !== plant.entry_id || !this._overviewSystemStatus)
      ) {
        void this._loadOverviewSystemStatus();
      }
      const map = plant ? resolveEntityMap(this._hass, plant, this._plantState) : {};
      const alarmWatch = [map.inverter_alarms, map.inverter_alarm_last, map.inverter_fault_code].filter(Boolean);
      if (plant && alarmWatch.length && !this._overviewSystemStatusLoading && this._overviewSystemStatus?.fetchedAt) {
        const stale = alarmWatch.some((id) => {
          const st = this._hass?.states?.[id];
          if (!st?.last_changed) return false;
          return new Date(st.last_changed).getTime() > this._overviewSystemStatus.fetchedAt;
        });
        if (stale) void this._loadOverviewSystemStatus({ force: true });
      }
      if (
        plant &&
        this._overviewHourlyWeatherEnabled() &&
        !this._hourlyWeatherLoading &&
        (this._hourlyWeatherPlantId !== plant.entry_id || !this._hourlyWeather)
      ) {
        this._loadHourlyWeather();
      }
    }
    if (this._view === "device_new") {
      const plant = this._getPlant();
      if (plant && this._deviceNewSub === "analysis") {
        const curveKey = this._deviceNewCurveChartCacheKey(plant);
        const energyKey = this._deviceNewEnergyChartCacheKey(plant);
        const curveReady =
          this._deviceNewStatisticsChartPlantId === curveKey && this._deviceNewStatisticsChart;
        const energyReady = this._deviceNewEnergyChartPlantId === energyKey && this._deviceNewEnergyChart;
        if (!this._deviceNewStatisticsChartLoading && !curveReady) {
          void this._loadDeviceNewCurveChart();
        }
        if (!this._deviceNewEnergyChartLoading && !energyReady) {
          void this._loadDeviceNewEnergyChart();
        }
        this._bindDeviceNewCharts();
      }
      if (plant && this._deviceNewSub === "alarms") {
        const alarmKey = this._deviceNewAlarmCacheKey(plant);
        const alarmReady = this._deviceNewAlarmPlantId === alarmKey && this._deviceNewAlarmData;
        if (!this._deviceNewAlarmLoading && !alarmReady) {
          void this._loadDeviceNewAlarms();
        } else if (!this._deviceNewAlarmLoading && this._deviceNewAlarmData?.fetchedAt) {
          const map = resolveEntityMap(this._hass, plant, this._plantState);
          const watchIds = [map.inverter_alarms, map.inverter_alarm_last, map.inverter_fault_code].filter(Boolean);
          const stale = watchIds.some((id) => {
            const st = this._hass?.states?.[id];
            if (!st?.last_changed) return false;
            return new Date(st.last_changed).getTime() > this._deviceNewAlarmData.fetchedAt;
          });
          if (stale) void this._loadDeviceNewAlarms({ force: true });
        }
        this._patchDeviceNewAlarmsIfNeeded();
      }
    }
    if (this._view === "reports") {
      const plant = this._getPlant();
      this._ensureReportsViewValid();
      if (this._reportsView === "octopus") {
        if (plant && !this._octopusAnalysisLoading && !octopusAnalysisPayload(this._plantState)) {
          void this._loadOctopusAnalysis();
        }
      } else if (this._reportsView === "smart_charge") {
        if (
          plant &&
          smartChargeEnabled(this._plantState) &&
          !this._smartChargeAnalysisLoading &&
          (this._smartChargeAnalysisPlantId !== this._smartChargeAnalysisCacheKey(plant) ||
            !this._smartChargeAnalysis)
        ) {
          void this._loadSmartChargeAnalysis();
        }
      } else if (
        plant &&
        !this._energyReportLoading &&
        (this._energyReportPlantId !== this._energyReportCacheKey(plant) || !this._energyReport)
      ) {
        void this._loadEnergyReport();
      }
      this._bindReportsCharts();
    }
  }
}

registerFoxessPlantPanel();
