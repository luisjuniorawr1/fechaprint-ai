# FechaPrint v2 — Quality First

FechaPrint v2 recebe uma arte raster, analisa a resolução para o tamanho físico solicitado e só libera a produção quando consegue preservar qualidade.

## Regra principal

**Sem Real-ESRGAN real, não existe falso upscale.** Se faltarem pixels, o job é bloqueado em vez de devolver um arquivo interpolado pior.

## Pipeline

1. análise de pixels, tamanho, PPI e proporção;
2. Real-ESRGAN 2×/4× com tiles quando necessário;
3. PaddleOCR opcional antes/depois para proteger texto;
4. Quality Gate de nitidez, fidelidade e OCR;
5. raster exato + sangria por extensão de borda;
6. PDF físico com MediaBox/TrimBox/BleedBox.

Veja `V2-ARCHITECTURE.md` para detalhes.

## API

```text
GET  /api/health
GET  /api/capabilities
POST /api/analyze
POST /api/jobs
GET  /api/jobs/{job_id}
GET  /api/files/{job_id}/final.jpg
GET  /api/files/{job_id}/final.pdf
```

`POST /api/process` permanece como endpoint síncrono para testes/integrações.

## Rodar a API base

```bash
python -m pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8080
```

O servidor base funciona sem GPU, mas bloqueia jobs que exigem ampliação até um provider Real-ESRGAN real ser configurado.

## Real-ESRGAN

A integração aceita uma destas opções:

- `realesrgan-ncnn-vulkan` disponível no `PATH`;
- `FECHAPRINT_REALESRGAN_SCRIPT=/caminho/Real-ESRGAN/inference_realesrgan.py`;
- wrapper customizado em `FECHAPRINT_REALESRGAN_CMD`.

O tile padrão é 256 e pode ser alterado por `FECHAPRINT_REALESRGAN_TILE`.

## OCR

PaddleOCR é opcional no primeiro boot. Se instalado, a v2 compara o texto detectado antes/depois da super-resolução e pode rejeitar uma saída que altere demais a arte.

## Testes

```bash
PYTHONPATH=. pytest -q tests/test_v2_analysis.py
```
