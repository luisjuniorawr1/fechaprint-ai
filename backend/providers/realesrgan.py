from __future__ import annotations
import os, subprocess, sys
from pathlib import Path
from .base import CommandProvider, ProviderStatus

class RealESRGANProvider(CommandProvider):
    key = "realesrgan"; label = "Real-ESRGAN"; license = "BSD-3-Clause"; role = "super-resolução real 2×/4× e remoção de artefatos"; env_command = "FECHAPRINT_REALESRGAN_CMD"; binary_names = ("realesrgan-ncnn-vulkan", "realesrgan-ncnn-vulkan.exe")
    def python_script(self) -> str | None:
        configured = os.getenv("FECHAPRINT_REALESRGAN_SCRIPT", "").strip(); return configured if configured and Path(configured).exists() else None
    def available(self) -> bool: return bool(self.command_template() or self.detected_binary() or self.python_script())
    def status(self) -> ProviderStatus:
        if self.command_template(): reason = f"configurado por {self.env_command}"
        elif self.detected_binary(): reason = f"NCNN/Vulkan detectado: {self.detected_binary()}"
        elif self.python_script(): reason = f"script Python detectado: {self.python_script()}"
        else: reason = "Real-ESRGAN real não instalado; saída de produção será bloqueada se precisar ampliar"
        return ProviderStatus(self.key, self.label, self.available(), reason, self.license, self.role)
    def enhance(self, input_path: Path, output_dir: Path, scale: int = 4, tile: int = 256) -> Path:
        if scale not in {2,4}: raise ValueError("FechaPrint v2 usa Real-ESRGAN em 2× ou 4×")
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.command_template(): self.run(input=input_path, output_dir=output_dir, scale=scale, tile=tile); return self.newest_image(output_dir)
        binary = self.detected_binary()
        if binary:
            out = output_dir / f"{input_path.stem}_realesrgan_x{scale}.png"; subprocess.run([binary,"-i",str(input_path),"-o",str(out),"-n","realesrgan-x4plus","-s",str(scale),"-t",str(tile),"-f","png"], check=True, timeout=1800); return out
        script = self.python_script()
        if script:
            subprocess.run([sys.executable,script,"-n","RealESRGAN_x4plus","-i",str(input_path),"-o",str(output_dir),"--outscale",str(scale),"--tile",str(tile),"--ext","png"], check=True, timeout=1800); return self.newest_image(output_dir)
        raise RuntimeError("Real-ESRGAN real não está instalado")
