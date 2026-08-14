from __future__ import annotations

from pathlib import Path
from .base import CommandProvider


class ImageCommandProvider(CommandProvider):
    def transform(self, input_path: Path, output_dir: Path, **params) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        self.run(input=input_path, output_dir=output_dir, **params)
        return self.newest_image(output_dir)


class LaMaProvider(ImageCommandProvider):
    key = "lama"; label = "LaMa"; license = "Apache-2.0"; role = "inpainting/outpainting conservador de fundos"; env_command = "FECHAPRINT_LAMA_CMD"

class PowerPaintProvider(ImageCommandProvider):
    key = "powerpaint"; label = "PowerPaint"; license = "MIT"; role = "outpainting e preenchimento guiado"; env_command = "FECHAPRINT_POWERPAINT_CMD"

class SeedVR2Provider(ImageCommandProvider):
    key = "seedvr2"; label = "SeedVR2"; license = "Apache-2.0"; role = "restauração pesada"; env_command = "FECHAPRINT_SEEDVR2_CMD"

class QwenImageEditProvider(ImageCommandProvider):
    key = "qwen_image_edit"; label = "Qwen-Image-Edit-2511"; license = "Apache-2.0"; role = "reformulação visual avançada"; env_command = "FECHAPRINT_QWEN_CMD"

class GFPGANProvider(ImageCommandProvider):
    key = "gfpgan"; label = "GFPGAN"; license = "Apache-2.0 + componentes de terceiros"; role = "restauração facial opcional"; env_command = "FECHAPRINT_GFPGAN_CMD"
