from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from .base import CommandProvider, ProviderStatus


class PaddleOCRProvider(CommandProvider):
    key = "paddleocr"
    label = "PaddleOCR"
    license = "Apache-2.0"
    role = "leitura e validação de textos"
    env_command = "FECHAPRINT_PADDLEOCR_CMD"
    binary_names = ("paddleocr",)

    def available(self) -> bool:
        if self.command_template() or self.detected_binary():
            return True
        try:
            import paddleocr  # noqa: F401
            return True
        except Exception:
            return False

    def status(self) -> ProviderStatus:
        if self.available():
            return ProviderStatus(self.key, self.label, True, "pacote/CLI detectado", self.license, self.role)
        return ProviderStatus(self.key, self.label, False, "instale paddleocr ou configure FECHAPRINT_PADDLEOCR_CMD", self.license, self.role)

    def extract_text(self, input_path: Path) -> str:
        if self.command_template():
            result = self.run(input=input_path)
            return self._parse_text(result.stdout)
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(lang=os.getenv("FECHAPRINT_OCR_LANG", "pt"))
            result = ocr.predict(str(input_path)) if hasattr(ocr, "predict") else ocr.ocr(str(input_path), cls=True)
            return self._flatten(result)
        except Exception:
            binary = self.detected_binary()
            if binary:
                result = subprocess.run([binary, "ocr", "-i", str(input_path)], check=True, capture_output=True, text=True, timeout=600)
                return self._parse_text(result.stdout)
            return ""

    def _parse_text(self, raw: str) -> str:
        raw = raw.strip()
        if not raw:
            return ""
        try:
            return self._flatten(json.loads(raw))
        except Exception:
            return re.sub(r"\s+", " ", raw)

    def _flatten(self, value) -> str:
        pieces: list[str] = []
        def walk(obj):
            if obj is None:
                return
            if isinstance(obj, str):
                if len(obj.strip()) > 1: pieces.append(obj.strip())
            elif isinstance(obj, dict):
                for key in ("text", "rec_text", "rec_texts"):
                    if key in obj: walk(obj[key])
                for v in obj.values():
                    if isinstance(v, (dict, list, tuple)): walk(v)
            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], (list, tuple)) and item[1] and isinstance(item[1][0], str):
                        pieces.append(item[1][0].strip())
                    else: walk(item)
            elif hasattr(obj, "__dict__"):
                walk(vars(obj))
        walk(value)
        dedup, seen = [], set()
        for p in pieces:
            p = re.sub(r"\s+", " ", p)
            if p and p not in seen:
                dedup.append(p); seen.add(p)
        return " ".join(dedup)
