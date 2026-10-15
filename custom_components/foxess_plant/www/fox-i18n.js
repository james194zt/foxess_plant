/**
 * Fox Plant labels — every word the panel, the alarm guide and the Fox Flow Scene card show.
 * @module fox-i18n
 *
 * Labels live in www/i18n/<lang>.json (flat keys like "smart_charge.save_smartcharge") and are
 * loaded before anything renders. They follow Home Assistant's language: English is loaded
 * first, then the file for HA's language on top (e.g. de.json), so a missing file — or a label
 * a translation hasn't got yet — shows in English. Adding a language is just adding a file.
 * {name} placeholders are filled from the values given; labels may contain HTML, and callers
 * escape anything that comes from the user or HA. tests/test_panel_i18n.py checks keys and
 * leftovers.
 */

async function loadLabels(lang) {
  try {
    // Revalidate every load (cheap 304): the files' URLs don't change between releases.
    const res = await fetch(new URL(`i18n/${lang}.json`, import.meta.url), { cache: "no-cache" });
    if (res.ok) return await res.json();
    if (lang === "en") console.error(`Fox Plant: couldn't load labels (HTTP ${res.status})`);
  } catch (err) {
    if (lang === "en") console.error("Fox Plant: couldn't load labels", err);
  }
  return null;
}

/** HA's language: it sets <html lang>; else the language picked in HA, else the browser's. */
function haLanguage() {
  let picked = "";
  try {
    picked = JSON.parse(localStorage.getItem("selectedLanguage") || "null") || "";
  } catch {
    // Not set, or not JSON.
  }
  return String(document.documentElement.lang || picked || navigator.language || "en").toLowerCase();
}

export const LANG = haLanguage();

const STRINGS = await (async () => {
  const labels = { ...((await loadLabels("en")) || {}) };
  // "de-de" → de-de.json, else de.json. English (any en-…) is already the base.
  for (const lang of [...new Set([LANG, LANG.split("-")[0]])]) {
    if (lang === "en" || lang.startsWith("en-")) break;
    const local = await loadLabels(lang);
    if (local) return { ...labels, ...local };
  }
  return labels;
})();

/** A label, with {placeholders} filled in. A missing key shows as the key itself. */
export function tl(key, vars) {
  let text = STRINGS[key];
  if (text == null) {
    console.warn(`Fox Plant: no label for "${key}"`);
    return key;
  }
  if (vars) text = text.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m));
  return text;
}

/**
 * A status word shown in a pill or badge. The code keeps these English inside (pill colours and
 * battery-flow direction are worked out from them, and some come straight from HA states), so
 * they are only translated here, where they are shown. Anything else is returned unchanged.
 */
export function stateWord(value) {
  const text = String(value ?? "");
  const labels = {
    Normal: "state.normal",
    Checking: "state.checking",
    "Off Grid": "state.off_grid",
    Fault: "state.fault",
    Online: "state.online",
    Offline: "state.offline",
    On: "state.on",
    Off: "state.off",
    Idle: "state.idle",
    Charging: "state.charging",
    Discharging: "state.discharging",
  };
  return labels[text] ? tl(labels[text]) : text;
}

/** Singular/plural label: "<key>.one" or "<key>.other", with {count}. */
export function tln(key, count, vars = {}) {
  return tl(`${key}.${Number(count) === 1 ? "one" : "other"}`, { count, ...vars });
}
