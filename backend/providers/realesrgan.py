from __future__ import annotations

import subprocess
from pathlib import Path

from .base import CommandProvider


class RealESRGANProvider(CommandProvider):
    key = "realesrgan"
    label = "Real-ESRGAN"
    license = "BSD-3-Clause"
    role = "super-resolução e remoção de artefatos"
    env_command = "FECHAPRINT_REALESRGAN_CMD"
    binary_names = ("realesrgan-ncnn-vulkan",)

    def enhance(self, input_path: Path, output_dir: Path, scale: int = 4) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.command_template():
            self.run(input=input_path, output_dir=output_dir, scale=scale)
            return self.newest_image(output_dir)
        binary = self.detected_binary()
        if binary:
            out = output_dir / f"{input_path.stem}_realesrgan.png"
            subprocess.run([binary, "-i", str(input_path), "-o", str(out), "-s", str(scale)], check=True, timeout=1800)
            return out
        raise RuntimeError("Real-ESRGAN não instalado")
