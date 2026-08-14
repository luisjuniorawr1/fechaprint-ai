from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageOps

CM_PER_INCH = 2.54

MATERIALS = {
    "paper": {"label": "Papel / flyer", "ppi": 300, "bleed_mm": 3.0},
    "sticker": {"label": "Adesivo", "ppi": 200, "bleed_mm": 3.0},
    "banner": {"label": "Banner", "ppi": 120, "bleed_mm": 5.0},
    "canvas": {"label": "Lona", "ppi": 100, "bleed_mm": 5.0},
    "panel": {"label": "Painel", "ppi": 100, "bleed_mm": 5.0},
    "outdoor": {"label": "Outdoor", "ppi": 72, "bleed_mm": 0.0},
}


def to_cm(value: float, unit: str) -> float:
    if unit == "m": return value * 100.0
    if unit == "mm": return value / 10.0
    return value


def recommended_ppi(material: str, width_cm: float, height_cm: float) -> int:
    base = MATERIALS.get(material, MATERIALS["canvas"])["ppi"]
    longest = max(width_cm, height_cm)
    if material in {"canvas", "banner"}:
        if longest >= 500: return min(base, 60)
        if longest >= 300: return min(base, 72)
    if material == "outdoor":
        if longest >= 500: return 36
        if longest >= 300: return 48
    if material == "panel" and longest >= 300: return min(base, 72)
    return int(base)


@dataclass(frozen=True)
class PrintPlan:
    source_width_px: int
    source_height_px: int
    width_cm: float
    height_cm: float
    material_key: str
    material_label: str
    target_ppi: int
    bleed_mm: float
    target_width_px: int
    target_height_px: int
    source_effective_ppi: float
    scale_needed: float
    upscale_factor: int
    target_ratio: float
    source_ratio: float
    ratio_delta: float
    crop_fraction: float
    max_width_cm_at_4x: float
    max_height_cm_at_4x: float
    can_reach_target_with_4x: bool

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_print_job(source: Path, *, width: float, height: float, unit: str, material: str) -> PrintPlan:
    width_cm = to_cm(float(width), unit); height_cm = to_cm(float(height), unit)
    if width_cm <= 0 or height_cm <= 0: raise ValueError("Tamanho final inválido")
    mat = MATERIALS.get(material, MATERIALS["canvas"])
    ppi = recommended_ppi(material, width_cm, height_cm)
    target_w = max(1, round(width_cm / CM_PER_INCH * ppi)); target_h = max(1, round(height_cm / CM_PER_INCH * ppi))
    with Image.open(source) as raw:
        img = ImageOps.exif_transpose(raw); src_w, src_h = img.size
    target_ratio = width_cm / height_cm; source_ratio = src_w / src_h; ratio_delta = abs(source_ratio / target_ratio - 1.0)
    scale_needed = max(target_w / src_w, target_h / src_h)
    source_effective_ppi = ppi / max(scale_needed, 1e-9)
    if scale_needed <= 1.05: factor = 1
    elif scale_needed <= 2.0: factor = 2
    elif scale_needed <= 4.0: factor = 4
    else: factor = 0
    if source_ratio > target_ratio:
        crop_fraction = max(0.0, 1.0 - (src_h * target_ratio) / src_w)
    else:
        crop_fraction = max(0.0, 1.0 - (src_w / target_ratio) / src_h)
    return PrintPlan(src_w, src_h, width_cm, height_cm, material if material in MATERIALS else "canvas", mat["label"], ppi, float(mat["bleed_mm"]), target_w, target_h, source_effective_ppi, scale_needed, factor, target_ratio, source_ratio, ratio_delta, crop_fraction, src_w * 4 / ppi * CM_PER_INCH, src_h * 4 / ppi * CM_PER_INCH, scale_needed <= 4.0)
