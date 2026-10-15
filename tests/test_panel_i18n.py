"""The panel's labels all come from www/i18n/en.json (plain Python, no HA needed).

Covers the sidebar panel, the alarm guide and the Fox Flow Scene card. Checks: every label
the code asks for exists, nothing in the file is unused, plurals have both forms, and no
English is left written straight into the code (so a translation is just another JSON file).
"""

import json
import re
from pathlib import Path

WWW = Path(__file__).resolve().parent.parent / "custom_components" / "foxess_plant" / "www"
FILES = ("foxess-plant-panel.js", "fox-alarm-guide.js", "fox-flow-scene-card.js", "fox-i18n.js")
EN = json.loads((WWW / "i18n" / "en.json").read_text(encoding="utf-8"))
KEY = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")

# Text that isn't a label: product names, units, ids, examples, code the panel hands to other sites.
ALLOWED_TEXT = {
    "Octopus", "Fuse", "Solcast", "Open-Meteo", "StormSafe", "SmartCharge", "Glow", "FoxESS", "MQTT",
    "Ecowitt", "E.ON Next", "Fox Cloud", "Google Weather", "Home Assistant", "Fox Plant", "FoxESS Plant",
    "Self Use",  # work-mode value written to the inverter (its display titles are labels)
    "Fox Flow Scene",  # card name in HA's card picker
    "kWh", "PV", "SOC",  # units / abbreviations
    "sensor.my_wind_speed", "sensor.…_import_unit_rate", "you@example.com", "glow",  # example values
}


def strip_css(js: str) -> str:
    """Drop the panel stylesheet (const STYLES = `…`;)."""
    start = js.find("const STYLES = `")
    if start < 0:
        return js
    end = js.index("\n`;", start)
    return js[:start] + js[end + 3 :]


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return re.sub(r"(?m)\s//\s.*$", "", text)


def without_snippet(js: str) -> str:
    """The E.ON console snippet runs on eonnext.com, in the user's browser console — not a label."""
    return re.sub(r"const EON_NEXT_TOKEN_SNIPPET =.*?\n\n", "\n", js, flags=re.S)


def without_alarm_names(js: str) -> str:
    """Alarm names stay English inside: they're matched against foxess_modbus states and the backend's
    alert log (alert_log.py). alarmDisplayName() / bmsBitDisplayName() translate them where shown."""
    js = re.sub(r"const FOX_ALARM_CODE_MAP = \(\(\) => \{.*?\n\}\)\(\);", "", js, flags=re.S)
    js = re.sub(r'const INVERTER_NOT_RESPONDING = "[^"]*";', "", js)
    return re.sub(r"export const FOX_BMS_FAULT_BITS = \[.*?\r?\n\];", "", js, flags=re.S)


CODE = "\n".join(
    strip_comments(without_alarm_names(without_snippet(strip_css((WWW / name).read_text(encoding="utf-8")))))
    for name in FILES
)


def strip_interpolations(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\$\{[^{}`]*\}", "", text)
    return text


def literal_keys() -> set[str]:
    return set(re.findall(r"\btln?\(\s*\"([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)\"", CODE)) | set(
        re.findall(r"\"([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)\"", CODE)
    )


def test_language_file_is_flat_strings():
    assert EN, "en.json is empty"
    for key, value in EN.items():
        assert KEY.match(key), f"odd key {key!r}"
        assert isinstance(value, str), f"{key} is not a string"


def test_every_label_used_exists():
    missing = []
    for key in set(re.findall(r"\btl\(\s*\"([^\"]+)\"", CODE)):
        if key not in EN:
            missing.append(key)
    for base in set(re.findall(r"\btln\(\s*\"([^\"]+)\"", CODE)):
        if f"{base}.one" not in EN or f"{base}.other" not in EN:
            missing.append(base)
    assert not missing, f"used but not in en.json: {sorted(missing)}"


def test_labels_are_called_with_literal_keys():
    """Keys are always written out in full, so the checks here (and translators) can find them."""
    callers = "\n".join(strip_comments((WWW / name).read_text(encoding="utf-8")) for name in FILES if name != "fox-i18n.js")
    dynamic = re.findall(r"\btln?\(\s*([^\"\s][^,)]*)", callers)
    assert not dynamic, f"tl()/tln() with a computed key: {dynamic}"


def scan(text: str, start: int, stop_at_comma: bool = False) -> int:
    """Index just past the bracketed expression at text[start] (or of the next top-level comma),
    skipping strings and template literals (with their ${…} parts)."""
    stack: list[str] = []
    i = start
    pairs = {")": "(", "]": "[", "}": "{"}
    while i < len(text):
        ch = text[i]
        top = stack[-1] if stack else ""
        if top == "`":
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                stack.pop()
            elif text.startswith("${", i):
                stack.append("{")
                i += 1
        elif ch in "\"'":
            j = i + 1
            while j < len(text) and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            i = j
        elif ch == "`":
            stack.append("`")
        elif ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack:
                return i
            stack.pop()
            if not stack and not stop_at_comma:
                return i + 1
        elif ch == "," and not stack and stop_at_comma:
            return i
        i += 1
    return i


def top_level_names(obj: str) -> set[str]:
    """Property names of an object literal's source ("{ a, b: f({c}), d }" → a, b, d)."""
    names, inner, i = set(), obj[1:-1], 0
    while i < len(inner):
        end = scan(inner, i, stop_at_comma=True)
        name = re.match(r"\s*([A-Za-z_$][\w$]*)", inner[i:end])
        if name:
            names.add(name[1])
        i = end + 1
    return names


def balanced(text: str, start: int) -> str:
    return text[start : scan(text, start)]


def test_placeholders_are_filled():
    """Every {name} in a label is given by the call that uses it."""
    problems = []
    for m in re.finditer(r"\b(tln?)\(\s*\"([^\"]+)\"\s*(,\s*)?", CODE):
        fn, key = m[1], m[2]
        rest = CODE[m.end() :]
        if fn == "tln":  # tln("key", count, { … })
            rest = rest[len(balanced(rest, 0)) :] if rest[:1] in "([{" else re.sub(r"^[^,)]*", "", rest)
            rest = re.sub(r"^\s*,\s*", "", rest)
        given = top_level_names(balanced(rest, 0)) if rest.startswith("{") else set()
        texts = [EN.get(key, "")] if fn == "tl" else [EN.get(f"{key}.one", ""), EN.get(f"{key}.other", "")]
        needed = {n for t in texts for n in re.findall(r"\{(\w+)\}", t)} - ({"count"} if fn == "tln" else set())
        if needed - given:
            problems.append(f"{key}: needs {sorted(needed - given)}")
    assert not problems, problems


def test_no_unused_labels():
    used = literal_keys()
    plural_bases = set(re.findall(r"\btln\(\s*\"([^\"]+)\"", CODE))
    unused = [
        key
        for key in EN
        if key not in used and not any(key in (f"{b}.one", f"{b}.other") for b in plural_bases)
    ]
    assert not unused, f"in en.json but never used: {sorted(unused)}"


def data_removed(code: str) -> str:
    """The code without places where English is data, not text: embedded icon SVGs, object keys,
    comparisons and lookups against inverter/HA values (e.g. "Self Use", "Grid Lost Fault")."""
    code = "\n".join(line for line in code.split("\n") if len(line) < 3000)  # icon blobs
    q = r"(?:\"[^\"\n]*\"|'[^'\n]*')"
    code = re.sub(rf"(^|[{{,])\s*{q}\s*:", r"\1", code, flags=re.M)  # object keys
    code = re.sub(rf"[!=]==?\s*{q}|{q}\s*[!=]==?", "", code)  # comparisons
    code = re.sub(rf"\bcase\s+{q}\s*:", "", code)
    code = re.sub(
        rf"\b(startsWith|endsWith|includes|indexOf|replace|has|get|add|delete|setAttribute|querySelector(All)?|console\.\w+)\(\s*{q}",
        "(",
        code,
    )
    return code


def leftovers() -> list[str]:
    found = []
    code = data_removed(CODE)
    # Text between tags in the HTML templates (a real tag on each side, not "a > b && c < d").
    for raw in re.findall(r"(?<=[\w\"'/])>([^<>\n]+)</?[A-Za-z]", code):
        text = strip_interpolations(raw).strip()
        if re.search(r"[;{}=`]|=>", text):  # JavaScript ("a => b", "x < y"), not markup
            continue
        if re.search(r"[A-Za-z]{2,}", text):
            found.append(text)
    for attr in re.findall(r"(?:title|aria-label|placeholder|alt)=\"([^\"$]*[A-Za-z]{2,}[^\"$]*)\"", code):
        found.append(attr)
    # Quoted phrases: two or more words starting with a capital (e.g. "Schedule saved")
    for phrase in re.findall(r"[\"`']([A-Z][a-z']+ [a-z][^\"`'\n$]*)[\"`']", code):
        found.append(phrase)
    return [f for f in found if f not in ALLOWED_TEXT]


def test_no_english_left_in_the_code():
    assert not leftovers(), f"English still in the panel code: {leftovers()}"
