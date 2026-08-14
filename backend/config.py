from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    data_dir: str = os.getenv("FECHAPRINT_DATA_DIR", "/tmp/fechaprint")
    public_base_url: str = os.getenv("FECHAPRINT_PUBLIC_BASE_URL", "")
    max_upload_mb: int = int(os.getenv("FECHAPRINT_MAX_UPLOAD_MB", "80"))
    ocr_similarity_threshold: float = float(os.getenv("FECHAPRINT_OCR_SIMILARITY", "0.90"))
    quality_edge_ratio: float = float(os.getenv("FECHAPRINT_MIN_EDGE_RATIO", "0.82"))
    quality_max_difference: float = float(os.getenv("FECHAPRINT_MAX_VISUAL_DIFF", "0.24"))
    realesrgan_tile: int = int(os.getenv("FECHAPRINT_REALESRGAN_TILE", "256"))
    max_crop_fraction: float = float(os.getenv("FECHAPRINT_MAX_CROP_FRACTION", "0.22"))
    worker_count: int = int(os.getenv("FECHAPRINT_WORKERS", "1"))
    enable_ocr: bool = os.getenv("FECHAPRINT_ENABLE_OCR", "1") == "1"

settings = Settings()
