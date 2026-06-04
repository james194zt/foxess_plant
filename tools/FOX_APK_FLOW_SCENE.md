# Fox app flow scene (APK 2.0.2.12)

Decoded with WSL: `/tmp/foxapkvenv/bin/python3 tools/decode_fox_apk.py` and `tools/resolve_fox_ids.py`.

## Layout: `fragment_plant_hybrid_flow.xml`

Fragment: `com.fox.foxcloud.ui.view.fragment.PlantFragmentHybridFlow`

### Layer stack (residential / hybrid block `cl_022F`)

| Z-order | View | Resource (XML default) | Runtime |
|--------|------|------------------------|---------|
| 0 | `ConstraintLayout` `cl_01EB` **background** | `flow_home_bg_day_dark` | `flow_home_bg_{day\|night}_{light\|dark}` |
| 1 | `ImageView` `iv_0736` full-bleed | `flow_home_day_dark` | `flow_home_{theme}` via data-binding |
| 2 | `ImageView` `binding_2` | *(none)* | `flow_pv_{overlay}` — 18.3% width, bias (0.2, 0.43), ratio 72:50 |
| 3 | `ConstraintLayout` + `binding_3` | bubble placeholder | `flow_aio_812_*` (model-specific) |

Aspect ratios: outer `393:465`, inner scene `393:391` (matches panel `1024×1017`).

### Resource ID map (resolved from `resources.arsc`)

| Hex | Name |
|-----|------|
| `0x7F0F009D` | `mipmap/flow_home_bg_day_dark` |
| `0x7F0F00A1` | `mipmap/flow_home_day_dark` |
| `0x7F0F00B1` | `mipmap/flow_industry_day_dark` (alternate industry block) |

Assets on disk: `res/mipmap-nodpi-v4/flow_home_day_light.webp` (+ `_bg_`, `_pv_`, `_aio_812_`, four themes).

### Fox `_light` vs `_dark` suffix

In the Fox Android app, **`light` / `dark` is the app UI theme**, not time of day.

**HA panel (v0.8.155+):**
- Detect HA UI mode via `hass.themes.darkMode` (fallback: `--primary-background-color` luminance).
- Sun `above_horizon` + HA **dark** UI → `day_dark` on `#000` stage.
- Sun below horizon + HA **dark** UI → `night_dark` on `#000` stage.
- Sun up + HA **light** UI → `day_light` on `#fff` stage.
- Sun down + HA **light** UI → `night_light` on `#fff` stage.

Backdrop/overlays use the same variant; flow SVG paths stay on 1024×1017.
