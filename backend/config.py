from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    data_dir: str = os.getenv("FECHAPRINT_DATA_DIR", "/tmp/fechaprint")
    public_base_url: str = os.getenv("FECHAPRINT_PUBLIC_BASE_URL", "")
    max_upload_mb: int = int(os.getenv("FECHAPRINT_MAX_UPLOAD_MB", "80"))
    ocr_similarity_threshold: float = float(os.getenv("FECHAPRINT_OCR_SIMILARITY", "0.84"))
    enable_gfpgan: bool = os.getenv("FECHAPRINT_ENABLE_GFPGAN", "0") == "1"
    enable_qwen: bool = os.getenv("FECHAPRINT_ENABLE_QWEN", "1") == "1"
    enable_seedvr2: bool = os.getenv("FECHAPRINT_ENABLE_SEEDVR2", "1") == "1"
    enable_powerpaint: bool = os.getenv("FECHAPRINT_ENABLE_POWERPAINT", "1") == "1"
    enable_lama: bool = os.getenv("FECHAPRINT_ENABLE_LAMA", "1") == "1"


settings = Settings()
