from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageOps
from .analysis import PrintPlan


def render_print_raster(source: Path, output: Path, plan: PrintPlan) -> tuple[int, int]:
    trim_w, trim_h = plan.target_width_px, plan.target_height_px
    bleed_px = max(0, round(plan.bleed_mm / 25.4 * plan.target_ppi))
    with Image.open(source) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")
        required_scale = max(trim_w / img.width, trim_h / img.height)
        if required_scale > 1.05: raise RuntimeError(f"quality gate: ainda seria necessário ampliar {required_scale:.2f}× após a super-resolução")
        trim = ImageOps.fit(img, (trim_w, trim_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    if bleed_px:
        canvas = Image.new("RGB", (trim_w + 2 * bleed_px, trim_h + 2 * bleed_px)); canvas.paste(trim, (bleed_px, bleed_px))
        canvas.paste(trim.crop((0, 0, trim_w, 1)).resize((trim_w, bleed_px)), (bleed_px, 0))
        canvas.paste(trim.crop((0, trim_h - 1, trim_w, trim_h)).resize((trim_w, bleed_px)), (bleed_px, bleed_px + trim_h))
        canvas.paste(trim.crop((0, 0, 1, trim_h)).resize((bleed_px, trim_h)), (0, bleed_px))
        canvas.paste(trim.crop((trim_w - 1, 0, trim_w, trim_h)).resize((bleed_px, trim_h)), (bleed_px + trim_w, bleed_px))
        canvas.paste(trim.getpixel((0, 0)), (0, 0, bleed_px, bleed_px)); canvas.paste(trim.getpixel((trim_w - 1, 0)), (bleed_px + trim_w, 0, 2 * bleed_px + trim_w, bleed_px))
        canvas.paste(trim.getpixel((0, trim_h - 1)), (0, bleed_px + trim_h, bleed_px, 2 * bleed_px + trim_h)); canvas.paste(trim.getpixel((trim_w - 1, trim_h - 1)), (bleed_px + trim_w, bleed_px + trim_h, 2 * bleed_px + trim_w, 2 * bleed_px + trim_h))
    else: canvas = trim
    output.parent.mkdir(parents=True, exist_ok=True); canvas.save(output, "JPEG", quality=97, subsampling=0, optimize=True); return canvas.size
