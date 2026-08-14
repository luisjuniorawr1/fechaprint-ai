from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\wÀ-ÿ0-9 ]", " ", (text or "").lower())).strip()


def text_similarity(a: str, b: str) -> float:
    a, b = _normalize_text(a), _normalize_text(b)
    if not a or not b: return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _comparison_gray(path: Path, max_side: int = 1600) -> Image.Image:
    with Image.open(path) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")
        if max(img.size) > max_side:
            ratio = max_side / max(img.size)
            img = img.resize((max(1, round(img.width * ratio)), max(1, round(img.height * ratio))), Image.Resampling.LANCZOS)
        return img.convert("L")


def _edge_energy(img: Image.Image) -> float:
    return float(ImageStat.Stat(img.filter(ImageFilter.FIND_EDGES)).var[0])


def _mean_abs_diff(a: Image.Image, b: Image.Image) -> float:
    if a.size != b.size: b = b.resize(a.size, Image.Resampling.LANCZOS)
    return float(ImageStat.Stat(ImageChops.difference(a, b)).mean[0]) / 255.0


@dataclass(frozen=True)
class QualityReport:
    passed: bool
    edge_ratio: float
    normalized_difference: float
    ocr_similarity: float | None
    reasons: tuple[str, ...]
    def to_dict(self) -> dict:
        data = asdict(self); data["reasons"] = list(self.reasons); return data


def evaluate_quality(source: Path, candidate: Path, *, ocr_before: str = "", ocr_after: str = "", min_edge_ratio: float = 0.82, max_normalized_difference: float = 0.24, min_ocr_similarity: float = 0.90) -> QualityReport:
    src = _comparison_gray(source); cand = _comparison_gray(candidate); cand_same = cand.resize(src.size, Image.Resampling.LANCZOS)
    edge_ratio = _edge_energy(cand_same) / max(_edge_energy(src), 1e-6)
    difference = _mean_abs_diff(src, cand_same)
    similarity = text_similarity(ocr_before, ocr_after) if ocr_before and ocr_after else None
    reasons: list[str] = []
    if edge_ratio < min_edge_ratio: reasons.append(f"nitidez caiu demais ({edge_ratio:.0%} da referência)")
    if difference > max_normalized_difference: reasons.append(f"mudança visual excessiva ({difference:.0%})")
    if similarity is not None and similarity < min_ocr_similarity: reasons.append(f"texto divergiu ({similarity:.0%} de similaridade)")
    return QualityReport(not reasons, edge_ratio, difference, similarity, tuple(reasons))
