from __future__ import annotations

import re
import shutil
import uuid
from dataclasses import asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps

from .config import settings
from .pdf_engine import build_pdf
from .providers.paddleocr import PaddleOCRProvider
from .providers.realesrgan import RealESRGANProvider
from .providers.command_models import LaMaProvider, PowerPaintProvider, SeedVR2Provider, QwenImageEditProvider, GFPGANProvider

MATERIALS = {
    "paper": {"label": "Papel / flyer", "ppi": 300, "bleed": 3},
    "sticker": {"label": "Adesivo", "ppi": 200, "bleed": 3},
    "banner": {"label": "Banner", "ppi": 120, "bleed": 5},
    "canvas": {"label": "Lona", "ppi": 100, "bleed": 5},
    "panel": {"label": "Painel", "ppi": 100, "bleed": 5},
    "outdoor": {"label": "Outdoor", "ppi": 72, "bleed": 0},
}


def to_cm(value: float, unit: str) -> float:
    if unit == "m": return value * 100
    if unit == "mm": return value / 10
    return value


def target_ppi(material: str, width_cm: float, height_cm: float) -> int:
    base = MATERIALS.get(material, MATERIALS["canvas"])["ppi"]
    longest = max(width_cm, height_cm)
    if material in {"canvas", "banner"}:
        if longest >= 500: return min(base, 60)
        if longest >= 300: return min(base, 72)
    if material == "outdoor" and longest >= 500: return 36
    return base


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\wÀ-ÿ0-9 ]", " ", text.lower())).strip()


def ocr_similarity(a: str, b: str) -> float:
    a, b = normalize_text(a), normalize_text(b)
    if not a or not b: return 1.0
    return SequenceMatcher(None, a, b).ratio()


class Pipeline:
    def __init__(self):
        self.ocr = PaddleOCRProvider(); self.upscale = RealESRGANProvider(); self.lama = LaMaProvider(); self.powerpaint = PowerPaintProvider(); self.seedvr2 = SeedVR2Provider(); self.qwen = QwenImageEditProvider(); self.gfpgan = GFPGANProvider()

    def capabilities(self) -> list[dict[str, Any]]:
        rows = []
        for p in [self.ocr, self.upscale, self.lama, self.powerpaint, self.seedvr2, self.qwen, self.gfpgan]:
            row = asdict(p.status())
            if p.key == "gfpgan" and not settings.enable_gfpgan:
                row["available"] = False; row["reason"] = "desativado por padrão por cautela de licenças de componentes terceiros"
            if p.key == "qwen_image_edit" and not settings.enable_qwen: row["available"] = False
            if p.key == "seedvr2" and not settings.enable_seedvr2: row["available"] = False
            if p.key == "powerpaint" and not settings.enable_powerpaint: row["available"] = False
            if p.key == "lama" and not settings.enable_lama: row["available"] = False
            rows.append(row)
        return rows

    def process(self, source: Path, *, width: float, height: float, unit: str, material: str, mode: str = "auto") -> dict[str, Any]:
        job = uuid.uuid4().hex[:12]; job_dir = Path(settings.data_dir) / job; job_dir.mkdir(parents=True, exist_ok=True)
        original = job_dir / f"original{source.suffix.lower() or '.png'}"; shutil.copy2(source, original); steps: list[dict[str, Any]] = []
        width_cm, height_cm = to_cm(width, unit), to_cm(height, unit)
        if width_cm <= 0 or height_cm <= 0: raise ValueError("Tamanho final inválido")
        mat = MATERIALS.get(material, MATERIALS["canvas"]); ppi = target_ppi(material, width_cm, height_cm); bleed_mm = mat["bleed"]; target_ratio = width_cm / height_cm
        with Image.open(original) as img: src_w, src_h = img.size
        src_ratio = src_w / src_h; ratio_delta = abs(src_ratio / target_ratio - 1)
        scale_needed = max((width_cm / 2.54 * ppi) / src_w, (height_cm / 2.54 * ppi) / src_h)
        text_before = self.ocr.extract_text(original) if self.ocr.available() else ""
        if text_before: steps.append({"engine": "PaddleOCR", "status": "ok", "detail": "texto original registrado para validação"})
        current = original; generative_candidate: Path | None = None

        if ratio_delta > 0.16 and mode in {"auto", "relayout"} and settings.enable_qwen and self.qwen.available():
            prompt = f"Reformat this existing graphic design to aspect ratio {target_ratio:.5f}. Preserve every word, name, date, logo, face, religious symbol and factual element exactly. Do not invent or rewrite text. Redistribute the existing composition naturally across the new canvas, moving decorative elements toward the edges and using the full width/height."
            try:
                generative_candidate = self.qwen.transform(current, job_dir / "qwen", ratio=target_ratio, prompt=prompt)
                steps.append({"engine": "Qwen-Image-Edit", "status": "ok", "detail": "reformulação de layout aplicada"})
            except Exception as exc: steps.append({"engine": "Qwen-Image-Edit", "status": "skip", "detail": str(exc)[:200]})

        if generative_candidate is None and ratio_delta > 0.08 and mode != "safe":
            for provider, label, enabled in [(self.powerpaint, "PowerPaint", settings.enable_powerpaint), (self.lama, "LaMa", settings.enable_lama)]:
                if not enabled or not provider.available(): continue
                try:
                    generative_candidate = provider.transform(current, job_dir / provider.key, ratio=target_ratio, prompt="extend background only; preserve original content exactly")
                    steps.append({"engine": label, "status": "ok", "detail": "áreas novas completadas sem esticar a arte"}); break
                except Exception as exc: steps.append({"engine": label, "status": "skip", "detail": str(exc)[:200]})

        if generative_candidate is not None:
            if text_before and self.ocr.available():
                similarity = ocr_similarity(text_before, self.ocr.extract_text(generative_candidate))
                if similarity < settings.ocr_similarity_threshold:
                    steps.append({"engine": "PaddleOCR", "status": "rejected", "detail": f"edição rejeitada: similaridade textual {similarity:.0%}"}); generative_candidate = None
                else: steps.append({"engine": "PaddleOCR", "status": "ok", "detail": f"texto validado: {similarity:.0%} de similaridade"})
            if generative_candidate is not None: current = generative_candidate

        if scale_needed > 4.0 and settings.enable_seedvr2 and self.seedvr2.available():
            try:
                current = self.seedvr2.transform(current, job_dir / "seedvr2", width=int(src_w * min(scale_needed, 4)), height=int(src_h * min(scale_needed, 4)))
                steps.append({"engine": "SeedVR2", "status": "ok", "detail": "restauração pesada aplicada"})
            except Exception as exc: steps.append({"engine": "SeedVR2", "status": "skip", "detail": str(exc)[:200]})

        if self.upscale.available() and scale_needed > 1.15:
            try:
                factor = 4 if scale_needed > 2.1 else 2; current = self.upscale.enhance(current, job_dir / "realesrgan", factor)
                steps.append({"engine": "Real-ESRGAN", "status": "ok", "detail": f"super-resolução {factor}×"})
            except Exception as exc: steps.append({"engine": "Real-ESRGAN", "status": "skip", "detail": str(exc)[:200]})

        if settings.enable_gfpgan and self.gfpgan.available():
            try:
                current = self.gfpgan.transform(current, job_dir / "gfpgan"); steps.append({"engine": "GFPGAN", "status": "ok", "detail": "restauração facial aplicada"})
            except Exception as exc: steps.append({"engine": "GFPGAN", "status": "skip", "detail": str(exc)[:200]})

        final_jpg = job_dir / "final.jpg"; self._final_raster(current, final_jpg, target_ratio, width_cm, height_cm, ppi, preserve=(generative_candidate is None)); steps.append({"engine": "FechaPrint Raster", "status": "ok", "detail": f"raster final a {ppi} PPI"})
        pdf = job_dir / "final.pdf"; build_pdf(final_jpg, pdf, width_cm, height_cm, bleed_mm); steps.append({"engine": "FechaPrint PDF", "status": "ok", "detail": "MediaBox/TrimBox/BleedBox gerados"})
        return {"job_id": job, "width_cm": width_cm, "height_cm": height_cm, "material": mat["label"], "target_ppi": ppi, "bleed_mm": bleed_mm, "steps": steps, "image_url": f"/api/files/{job}/final.jpg", "pdf_url": f"/api/files/{job}/final.pdf", "ocr_text_detected": bool(text_before)}

    def _final_raster(self, source: Path, output: Path, ratio: float, width_cm: float, height_cm: float, ppi: int, preserve: bool) -> None:
        target_w = max(1, round(width_cm / 2.54 * ppi)); target_h = max(1, round(height_cm / 2.54 * ppi)); max_side = 14000
        scale = min(1.0, max_side / max(target_w, target_h)); target_w, target_h = max(1, round(target_w * scale)), max(1, round(target_h * scale))
        with Image.open(source) as raw:
            img = ImageOps.exif_transpose(raw).convert("RGB")
            if abs((img.width / img.height) / ratio - 1) < 0.035:
                canvas = ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS, centering=(0.5,0.5))
            elif preserve:
                bg = ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=max(8, min(target_w, target_h)//80)))
                fg = ImageOps.contain(img, (target_w, target_h), method=Image.Resampling.LANCZOS); x, y = (target_w - fg.width)//2, (target_h - fg.height)//2; canvas = bg; canvas.paste(fg, (x,y))
            else:
                canvas = ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
            canvas.save(output, "JPEG", quality=94, subsampling=0, optimize=True)
