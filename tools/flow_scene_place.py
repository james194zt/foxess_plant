"""Fox flow scene layer placement (1024×1017). Shared by bake_flow_overlays + preview_flow_scene."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

CANVAS = (1024, 1017)

BOXES = {
    "pv": {"left": 0.388, "top": 0.342, "width": 0.448, "height": 0.242},
    "aio": {"left": 0.312, "top": 0.622, "width": 0.136, "height": 0.222},
}

# Defaults used when baking to www/ (override via preview CLI without writing).
DEFAULT_PV = {
    "scale_inset": 1.06,
    "at_box_origin": True,
    "dx": -2,
    "dy": 8,
}

# Flow-path tap on the AIO right face toward hub (sync FOX_FLOW_PATHS aio-hub / hub-aio).
AIO_FACE_X = 405
# White wall → grey apron on flow_home_bg_scene (column ~380); not the placement-box floor.
AIO_FOOT_Y = 778
# ~2/3 up the right edge of opaque AIO art (from foot toward top).
AIO_HUB_TAP_UP_FRAC = 2 / 3
AIO_CONNECT = (405, 724)
# Opaque bbox fractions on flow_aio_812 sprite (232×255, after matte strip).
AIO_OPAQUE_FRAC = (66 / 232, 14 / 255, 172 / 232, 175 / 255)  # y1 = cabinet base (excl. shadow)


def _aio_scale(sprite: Image.Image, scale_inset: float) -> tuple[float, int, int]:
    _, top, bw, bh = box_pixels(BOXES["aio"])
    sw, sh = sprite.size
    scale = min(bw / sw, bh / sh) * scale_inset
    nw = max(1, int(sw * scale))
    nh = max(1, int(sh * scale))
    return scale, nw, nh


def aio_paste_xy(sprite: Image.Image, placement: AioPlacement) -> tuple[int, int, float, int, int]:
    """Bottom of opaque art on the placement-box floor (wall ground in scene)."""
    left, top, bw, bh = box_pixels(BOXES["aio"])
    ox0, oy0, ox1, oy1 = AIO_OPAQUE_FRAC
    sw, sh = sprite.size
    x0, y0, x1, y1 = int(sw * ox0), int(sh * oy0), int(sw * ox1), int(sh * oy1)
    scale, nw, nh = _aio_scale(sprite, placement.scale_inset)
    opaque_cx = (x0 + x1) / 2
    px = round(left + bw / 2 - opaque_cx * scale) + placement.dx
    py = round(AIO_FOOT_Y - y1 * scale) + placement.dy
    return px, py, scale, nw, nh


def aio_hub_connect(sprite: Image.Image, placement: AioPlacement) -> tuple[int, int]:
    """Right-edge tap for aio-hub / hub-aio (default ~2/3 up from AIO foot)."""
    px, py, scale, _, _ = aio_paste_xy(sprite, placement)
    ox0, oy0, ox1, oy1 = AIO_OPAQUE_FRAC
    sw, sh = sprite.size
    x0, y0, x1, y1 = int(sw * ox0), int(sh * oy0), int(sw * ox1), int(sh * oy1)
    tap_y = y1 - (y1 - y0) * AIO_HUB_TAP_UP_FRAC
    return round(px + x1 * scale), round(py + tap_y * scale)


DEFAULT_AIO = {
    "scale_inset": 1.0,
    "dx": 0,
    "dy": 10,
}


@dataclass
class PvPlacement:
    scale_inset: float = DEFAULT_PV["scale_inset"]
    at_box_origin: bool = DEFAULT_PV["at_box_origin"]
    dx: int = 0
    dy: int = 0


@dataclass
class AioPlacement:
    scale_inset: float = DEFAULT_AIO["scale_inset"]
    dx: int = DEFAULT_AIO["dx"]
    dy: int = DEFAULT_AIO["dy"]


def box_pixels(box: dict, canvas: tuple[int, int] = CANVAS) -> tuple[int, int, int, int]:
    w, h = canvas
    return (
        int(box["left"] * w),
        int(box["top"] * h),
        int(box["width"] * w),
        int(box["height"] * h),
    )


def render_pv_layer(sprite: Image.Image, placement: PvPlacement | None = None) -> Image.Image:
    """Transparent 1024×1017 canvas with PV sprite placed like the HA panel overlay."""
    placement = placement or PvPlacement(**DEFAULT_PV)
    left, top, bw, bh = box_pixels(BOXES["pv"])
    sw, sh = sprite.size
    scale = min(bw / sw, bh / sh) * placement.scale_inset
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    scaled = sprite.resize((nw, nh), Image.Resampling.LANCZOS)
    if placement.at_box_origin:
        px, py = left, top
    else:
        px = left + (bw - nw) // 2
        py = top + (bh - nh) // 2
    px += placement.dx
    py += placement.dy
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.paste(scaled, (px, py), scaled)
    return canvas


def render_aio_layer(sprite: Image.Image, placement: AioPlacement | None = None) -> Image.Image:
    """Uniform scale; opaque bottom on placement-box floor (ground level on wall)."""
    placement = placement or AioPlacement(**DEFAULT_AIO)
    px, py, _, nw, nh = aio_paste_xy(sprite, placement)
    sw, sh = sprite.size
    scaled = sprite.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.paste(scaled, (px, py), scaled)
    return canvas


def composite_scene(
    bg: Image.Image,
    pv: Image.Image,
    aio: Image.Image,
) -> Image.Image:
    """Same stack order as foxess-plant-panel.js: bg → pv → aio."""
    out = bg.convert("RGBA")
    out.alpha_composite(pv.convert("RGBA"))
    out.alpha_composite(aio.convert("RGBA"))
    return out


def pv_placement_summary(placement: PvPlacement, sprite: Image.Image) -> str:
    left, top, bw, bh = box_pixels(BOXES["pv"])
    sw, sh = sprite.size
    scale = min(bw / sw, bh / sh) * placement.scale_inset
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    if placement.at_box_origin:
        px, py = left, top
    else:
        px = left + (bw - nw) // 2
        py = top + (bh - nh) // 2
    px += placement.dx
    py += placement.dy
    return (
        f"pv {nw}x{nh} @ ({px},{py}) "
        f"scale_inset={placement.scale_inset} "
        f"origin={'box-tl' if placement.at_box_origin else 'centered'} "
        f"offset=({placement.dx},{placement.dy})"
    )


def aio_placement_summary(placement: AioPlacement, sprite: Image.Image) -> str:
    px, py, _, nw, nh = aio_paste_xy(sprite, placement)
    hub = aio_hub_connect(sprite, placement)
    return (
        f"aio {nw}x{nh} @ ({px},{py}) "
        f"scale_inset={placement.scale_inset} hub@{hub} "
        f"offset=({placement.dx},{placement.dy})"
    )
