#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

for color in ["#894BFC", "#894bfc", "#EB6D48", "#03BD9A", "#03bd9a", "#788bab"]:
    print(color, app.count(color))

# icons with purple fill
for m in re.finditer(r'id:"(icon-[^"]+)"[^}}]*content:\'([^\']{0,2500})\'', app):
    icon_id, content = m.group(1), m.group(2)
    if "#894BFC" in content or "#894bfc" in content:
        if "viewBox" in content:
            print("PURPLE", icon_id, "len", len(content))

# search produced string near svg usage in lazy chunks within app - maybe inline require
idx = app.find("produced")
while idx != -1:
    chunk = app[idx:idx+400]
    if "icon" in chunk.lower():
        print("produced ctx:", chunk[:350])
    idx = app.find("produced", idx + 1)
    if idx > 0 and app.count("produced") > 20:
        break

# icon with sun rays - search content for sun-like paths
for m in re.finditer(r'id:"(icon-[^"]+)"[^}}]*content:\'([^\']+)\'', app):
    icon_id, content = m.group(1), m.group(2)
    if "894BFC" in content and "36 36" in content:
        print("36 purple", icon_id)

for m in re.finditer(r'id:"(icon-[^"]+)"[^}}]*viewBox:"0 0 36 36"', app):
    print("36vb", m.group(1))
