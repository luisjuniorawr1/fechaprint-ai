from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ProviderStatus:
    key: str
    label: str
    available: bool
    reason: str
    license: str
    role: str


class CommandProvider:
    key = "provider"
    label = "Provider"
    license = ""
    role = ""
    env_command = ""
    binary_names: tuple[str, ...] = ()

    def command_template(self) -> Optional[str]:
        return os.getenv(self.env_command) if self.env_command else None

    def detected_binary(self) -> Optional[str]:
        for name in self.binary_names:
            path = shutil.which(name)
            if path:
                return path
        return None

    def available(self) -> bool:
        return bool(self.command_template() or self.detected_binary())

    def status(self) -> ProviderStatus:
        if self.command_template():
            reason = f"configurado por {self.env_command}"
        elif self.detected_binary():
            reason = f"binário detectado: {self.detected_binary()}"
        else:
            reason = f"configure {self.env_command}" if self.env_command else "não instalado"
        return ProviderStatus(self.key, self.label, self.available(), reason, self.license, self.role)

    def render_command(self, **kwargs) -> list[str]:
        template = self.command_template()
        if not template:
            raise RuntimeError(f"{self.label} não está configurado")
        rendered = template.format(**{k: str(v) for k, v in kwargs.items()})
        return shlex.split(rendered)

    def run(self, *, timeout: int = 1800, **kwargs) -> subprocess.CompletedProcess:
        cmd = self.render_command(**kwargs)
        return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)

    @staticmethod
    def newest_image(folder: Path) -> Path:
        files = [p for p in folder.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        if not files:
            raise RuntimeError("O provider não gerou uma imagem de saída")
        return max(files, key=lambda p: p.stat().st_mtime)
