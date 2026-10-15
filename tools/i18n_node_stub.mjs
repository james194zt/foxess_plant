// Label functions for the Node tool tests. The browser loader (www/fox-i18n.js) fetches its JSON with
// top-level await; here the same tl / tln / stateWord source runs with www/i18n/en.json embedded.
import { readFileSync } from "node:fs";

const www = new URL("../custom_components/foxess_plant/www/", import.meta.url);
const EN = readFileSync(new URL("i18n/en.json", www), "utf8");
const loader = readFileSync(new URL("fox-i18n.js", www), "utf8");

// Everything from tl() to the end of the loader (tl, stateWord, tln), without the export keywords.
const start = loader.indexOf("export function tl(");
if (start < 0) throw new Error("fox-i18n.js: tl() not found");
const FUNCTIONS = loader.slice(start).replace(/^export function /gm, "function ");

/** Classic-script source defining STRINGS, tl, tln and stateWord. */
export function i18nStubSource() {
  return `const STRINGS = ${EN};\n${FUNCTIONS}\n`;
}

/** The same as an ES module (for a temporary fox-i18n.js next to a copied module). */
export function i18nStubModule() {
  return `${i18nStubSource()}export const LANG = "en";\nexport { tl, tln, stateWord };\n`;
}
