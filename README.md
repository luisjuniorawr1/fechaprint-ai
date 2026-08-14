# FechaPrint AI — pipeline open-source para impressão

O FechaPrint recebe JPG/PNG/WEBP, tamanho físico e material, executa automaticamente o melhor pipeline gratuito disponível e gera JPG final + PDF com tamanho físico correto.

## Fluxo

**upload → tamanho/material → processamento automático → PDF**

## Motores integrados

- **PaddleOCR** — registra e valida texto antes/depois (Apache-2.0).
- **Real-ESRGAN** — upscale/restauração padrão (BSD-3-Clause).
- **LaMa** — inpainting/outpainting conservador (Apache-2.0).
- **PowerPaint** — outpainting avançado (MIT).
- **SeedVR2** — restauração pesada (Apache-2.0).
- **Qwen-Image-Edit-2511** — reformulação visual avançada (Apache-2.0).
- **GFPGAN** — restauração facial opcional; fica desativado por padrão porque o projeto lista componentes de terceiros com licenças adicionais.

Os pesos/modelos não são redistribuídos aqui. Instale os projetos oficiais no servidor GPU e configure os comandos em `.env`.

## Trava de texto

PaddleOCR lê o original e a proposta gerativa. Se a similaridade cair abaixo de `FECHAPRINT_OCR_SIMILARITY` (0,84 por padrão), a edição é rejeitada e o pipeline volta para uma composição conservadora sem deformar a arte.

## API

- `GET /api/health`
- `GET /api/capabilities`
- `POST /api/process` (`file`, `width`, `height`, `unit`, `material`, `mode`)
- `GET /api/files/{job_id}/final.jpg`
- `GET /api/files/{job_id}/final.pdf`

## Rodar

```bash
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8080
```

Abra `http://localhost:8080`.

## Docker

```bash
docker build -t fechaprint .
docker run --rm -p 8080:8080 -v fechaprint-data:/data fechaprint
```

O container base serve frontend + orquestrador. Os modelos GPU devem ser instalados/montados no servidor e configurados pelas variáveis de `.env.example`.

## Real-ESRGAN

Se `realesrgan-ncnn-vulkan` estiver no `PATH`, o backend detecta automaticamente. Também é possível apontar o script oficial:

```env
FECHAPRINT_REALESRGAN_CMD=python /models/Real-ESRGAN/inference_realesrgan.py -n RealESRGAN_x4plus -i {input} -o {output_dir} --outscale {scale} --tile 512
```

## Testes locais

```bash
python -m unittest discover -s tests -v
```
