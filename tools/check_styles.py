import re
from pathlib import Path

s = Path("custom_components/foxess_plant/www/foxess-plant-panel.js").read_text(encoding="utf-8")
m = re.search(r"const STYLES = `\n([\s\S]*?)\n`;", s)
if not m:
    raise SystemExit("STYLES not found")
css = m.group(1)
d = 0
for i, ch in enumerate(css):
    if ch == "{":
        d += 1
    elif ch == "}":
        d -= 1
    if d < 0:
        print("negative balance at char", i)
        break
print("brace balance:", d)
paren = 0
for i, ch in enumerate(css):
    if ch == "(":
        paren += 1
    elif ch == ")":
        paren -= 1
    if paren < 0:
        print("negative paren balance at char", i)
        break
print("paren balance:", paren)
lines = css.splitlines()
for i, line in enumerate(lines):
    if line.strip() == ".fox-device-new-sidebar {" and i + 1 < len(lines):
        nxt = lines[i + 1].strip()
        if nxt.startswith("."):
            print(f"BAD: line {i+1} sidebar not closed before {nxt[:50]}")
if paren != 0:
    raise SystemExit(1)
if d != 0:
    raise SystemExit(1)
