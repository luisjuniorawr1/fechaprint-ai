from __future__ import annotations
import shutil, uuid
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .job_manager import JobManager
from .pipeline import Pipeline, ProductionBlocked

ROOT=Path(__file__).resolve().parents[1]; DATA=Path(settings.data_dir); DATA.mkdir(parents=True,exist_ok=True); pipeline=Pipeline(); jobs=JobManager(pipeline); app=FastAPI(title="FechaPrint v2",version="2.0.0"); app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
def _validate(unit:str,suffix:str):
    if unit not in {"mm","cm","m"}: raise HTTPException(400,"Unidade inválida")
    if suffix not in {".jpg",".jpeg",".png",".webp"}: raise HTTPException(400,"Use JPG, PNG ou WEBP")
async def _save_upload(file:UploadFile,job_id:str)->Path:
    suffix=Path(file.filename or "upload.png").suffix.lower(); _validate("cm",suffix); job_dir=DATA/job_id; job_dir.mkdir(parents=True,exist_ok=True); target=job_dir/f"upload{suffix}"; size=0
    with target.open("wb") as out:
        while chunk:=await file.read(1024*1024):
            size+=len(chunk)
            if size>settings.max_upload_mb*1024*1024: target.unlink(missing_ok=True); raise HTTPException(413,f"Arquivo maior que {settings.max_upload_mb} MB")
            out.write(chunk)
    return target
@app.get("/api/health")
def health(): return {"ok":True,"service":"FechaPrint v2","version":"2.0.0"}
@app.get("/api/capabilities")
def capabilities(): return {"version":"2.0.0","quality_first":True,"fake_browser_upscale":False,"engines":pipeline.capabilities()}
@app.post("/api/analyze")
async def analyze(file:UploadFile=File(...),width:float=Form(...),height:float=Form(...),unit:str=Form("cm"),material:str=Form("canvas")):
    suffix=Path(file.filename or "upload.png").suffix.lower(); _validate(unit,suffix); job_id=uuid.uuid4().hex[:12]; source=await _save_upload(file,job_id)
    try: return pipeline.analyze(source,width=width,height=height,unit=unit,material=material)
    finally: shutil.rmtree(DATA/job_id,ignore_errors=True)
@app.post("/api/jobs")
async def create_job(file:UploadFile=File(...),width:float=Form(...),height:float=Form(...),unit:str=Form("cm"),material:str=Form("canvas")):
    suffix=Path(file.filename or "upload.png").suffix.lower(); _validate(unit,suffix); job_id=uuid.uuid4().hex[:12]; source=await _save_upload(file,job_id); return jobs.create(job_id,source,width=width,height=height,unit=unit,material=material).to_dict()
@app.get("/api/jobs/{job_id}")
def get_job(job_id:str):
    if not job_id.isalnum(): raise HTTPException(404)
    state=jobs.get(job_id)
    if not state: raise HTTPException(404,"Job não encontrado")
    return state.to_dict()
@app.post("/api/process")
async def process(file:UploadFile=File(...),width:float=Form(...),height:float=Form(...),unit:str=Form("cm"),material:str=Form("canvas")):
    suffix=Path(file.filename or "upload.png").suffix.lower(); _validate(unit,suffix); job_id=uuid.uuid4().hex[:12]; source=await _save_upload(file,job_id)
    try: return pipeline.process(source,width=width,height=height,unit=unit,material=material,job_id=job_id)
    except ProductionBlocked as exc: raise HTTPException(422,detail=exc.payload()) from exc
@app.get("/api/files/{job_id}/{filename}")
def files(job_id:str,filename:str):
    if not job_id.isalnum() or filename not in {"final.jpg","final.pdf"}: raise HTTPException(404)
    path=DATA/job_id/filename
    if not path.exists(): raise HTTPException(404)
    media="application/pdf" if filename.endswith(".pdf") else "image/jpeg"; return FileResponse(path,media_type=media,filename=f"fechaprint-{job_id}.{filename.rsplit('.',1)[1]}")
app.mount("/",StaticFiles(directory=str(ROOT),html=True),name="frontend")
