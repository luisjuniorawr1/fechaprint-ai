from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(settings.data_dir); DATA.mkdir(parents=True, exist_ok=True)
pipeline = Pipeline()
app = FastAPI(title="FechaPrint AI Open Source Pipeline", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health(): return {"ok": True, "service": "FechaPrint AI", "version": "3.0.0"}

@app.get("/api/capabilities")
def capabilities(): return {"engines": pipeline.capabilities()}

@app.post("/api/process")
async def process(file: UploadFile = File(...), width: float = Form(...), height: float = Form(...), unit: str = Form("cm"), material: str = Form("canvas"), mode: str = Form("auto")):
    if unit not in {"mm", "cm", "m"}: raise HTTPException(400, "Unidade inválida")
    suffix = Path(file.filename or "upload.png").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}: raise HTTPException(400, "Use JPG, PNG ou WEBP")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = Path(tmp.name); size = 0
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                temp_path.unlink(missing_ok=True); raise HTTPException(413, f"Arquivo maior que {settings.max_upload_mb} MB")
            tmp.write(chunk)
    try:
        return pipeline.process(temp_path, width=width, height=height, unit=unit, material=material, mode=mode)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)

@app.get("/api/files/{job_id}/{filename}")
def files(job_id: str, filename: str):
    if not job_id.isalnum() or filename not in {"final.jpg", "final.pdf"}: raise HTTPException(404)
    path = DATA / job_id / filename
    if not path.exists(): raise HTTPException(404)
    media = "application/pdf" if filename.endswith(".pdf") else "image/jpeg"
    return FileResponse(path, media_type=media, filename=f"fechaprint-{job_id}.{filename.rsplit('.',1)[1]}")

app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="frontend")
