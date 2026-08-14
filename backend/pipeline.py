from __future__ import annotations
import shutil, uuid
from pathlib import Path
from typing import Any, Callable
from .analysis import PrintPlan, analyze_print_job
from .config import settings
from .pdf_engine import build_pdf
from .providers.paddleocr import PaddleOCRProvider
from .providers.realesrgan import RealESRGANProvider
from .quality_gate import evaluate_quality
from .raster_engine import render_print_raster

class ProductionBlocked(RuntimeError):
    def __init__(self, message: str, *, code: str, plan: PrintPlan | None = None, details: dict | None = None): super().__init__(message); self.code=code; self.plan=plan; self.details=details or {}
    def payload(self) -> dict[str,Any]:
        data={"code":self.code,"message":str(self),**self.details}
        if self.plan: data["plan"]=self.plan.to_dict()
        return data

class Pipeline:
    def __init__(self, *, upscale: RealESRGANProvider | None = None, ocr: PaddleOCRProvider | None = None): self.upscale=upscale or RealESRGANProvider(); self.ocr=ocr or PaddleOCRProvider()
    def capabilities(self) -> list[dict[str,Any]]: return [self.upscale.status().__dict__, self.ocr.status().__dict__]
    def analyze(self, source: Path, *, width: float, height: float, unit: str, material: str) -> dict[str,Any]:
        plan=analyze_print_job(source,width=width,height=height,unit=unit,material=material); data=plan.to_dict(); data["upscaler_available"]=self.upscale.available(); data["ocr_available"]=settings.enable_ocr and self.ocr.available(); data["production_ready"]=plan.can_reach_target_with_4x and plan.crop_fraction<=settings.max_crop_fraction and (plan.upscale_factor==1 or self.upscale.available())
        if plan.scale_needed>4: data["block_reason"]="A fonte é pequena demais para atingir o raster solicitado com uma única super-resolução 4× segura."
        elif plan.crop_fraction>settings.max_crop_fraction: data["block_reason"]="A proporção exigiria corte excessivo; a v2 não deforma nem inventa layout nesta etapa."
        elif plan.upscale_factor>1 and not self.upscale.available(): data["block_reason"]="Real-ESRGAN real não está conectado."
        return data
    def process(self, source: Path, *, width: float, height: float, unit: str, material: str, job_id: str | None = None, progress: Callable[[int,str],None] | None = None) -> dict[str,Any]:
        job=job_id or uuid.uuid4().hex[:12]; job_dir=Path(settings.data_dir)/job; job_dir.mkdir(parents=True,exist_ok=True); original=job_dir/f"original{source.suffix.lower() or '.png'}"
        if source.resolve()!=original.resolve(): shutil.copy2(source,original)
        def report(percent:int,message:str):
            if progress: progress(percent,message)
        report(5,"Analisando resolução e tamanho de impressão"); plan=analyze_print_job(original,width=width,height=height,unit=unit,material=material); steps=[]
        if plan.crop_fraction>settings.max_crop_fraction: raise ProductionBlocked("A proporção solicitada cortaria conteúdo demais. Ajuste o tamanho/proporção antes da produção.",code="ratio_mismatch",plan=plan,details={"crop_fraction":plan.crop_fraction})
        if not plan.can_reach_target_with_4x: raise ProductionBlocked("A imagem é pequena demais para o tamanho solicitado mesmo com uma passagem 4× segura.",code="source_too_small",plan=plan,details={"max_width_cm_at_4x":plan.max_width_cm_at_4x,"max_height_cm_at_4x":plan.max_height_cm_at_4x})
        ocr_before=""
        if settings.enable_ocr and self.ocr.available():
            report(12,"Registrando textos para proteção"); ocr_before=self.ocr.extract_text(original)
            if ocr_before: steps.append({"engine":"PaddleOCR","status":"ok","detail":"texto original registrado"})
        current=original; quality_report=None
        if plan.upscale_factor>1:
            if not self.upscale.available(): raise ProductionBlocked("Esta arte precisa de super-resolução real. O Real-ESRGAN não está instalado no servidor.",code="upscaler_unavailable",plan=plan)
            report(20,f"Executando Real-ESRGAN {plan.upscale_factor}×"); enhanced=self.upscale.enhance(original,job_dir/"realesrgan",plan.upscale_factor,tile=settings.realesrgan_tile); steps.append({"engine":"Real-ESRGAN","status":"ok","detail":f"super-resolução real {plan.upscale_factor}×"})
            report(68,"Validando qualidade da super-resolução"); ocr_after=self.ocr.extract_text(enhanced) if ocr_before and settings.enable_ocr and self.ocr.available() else ""; quality_report=evaluate_quality(original,enhanced,ocr_before=ocr_before,ocr_after=ocr_after,min_edge_ratio=settings.quality_edge_ratio,max_normalized_difference=settings.quality_max_difference,min_ocr_similarity=settings.ocr_similarity_threshold)
            if not quality_report.passed: raise ProductionBlocked("A super-resolução foi rejeitada porque não preservou a qualidade da arte original.",code="quality_gate_failed",plan=plan,details={"quality":quality_report.to_dict()})
            steps.append({"engine":"Quality Gate","status":"ok","detail":"nitidez/fidelidade aprovadas"})
            if quality_report.ocr_similarity is not None: steps.append({"engine":"PaddleOCR","status":"ok","detail":f"texto preservado: {quality_report.ocr_similarity:.0%}"})
            current=enhanced
        else: steps.append({"engine":"Quality Gate","status":"ok","detail":"a fonte já possui pixels suficientes; nenhuma ampliação artificial foi aplicada"})
        report(78,"Montando raster final e sangria"); final_jpg=job_dir/"final.jpg"; raster_size=render_print_raster(current,final_jpg,plan); steps.append({"engine":"FechaPrint Raster","status":"ok","detail":f"raster final {raster_size[0]}×{raster_size[1]} px"})
        report(90,"Gerando PDF físico"); pdf=job_dir/"final.pdf"; build_pdf(final_jpg,pdf,plan.width_cm,plan.height_cm,plan.bleed_mm); steps.append({"engine":"FechaPrint PDF","status":"ok","detail":"MediaBox/TrimBox/BleedBox gerados"}); report(100,"Arquivo pronto")
        return {"job_id":job,"status":"completed","plan":plan.to_dict(),"quality":quality_report.to_dict() if quality_report else None,"steps":steps,"image_url":f"/api/files/{job}/final.jpg","pdf_url":f"/api/files/{job}/final.pdf"}
