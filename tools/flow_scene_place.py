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
    "dx": 0,
    "dy": -14,
}


@dataclass
class PvPlacement:
    scale_inset: float = DEFAULT_PV["scale_inset"]
    at_box_origin: bool = DEFAULT_PV["at_box_origin"]
    dx: int = 0
    dy: int = 0


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
    placement = placement or PvPlacement()
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


def render_aio_layer(sprite: Image.Image) -> Image.Image:
    left, top, bw, bh = box_pixels(BOXES["aio"])
    fitted = sprite.resize((bw, bh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.paste(fitted, (left, top), fitted)
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
