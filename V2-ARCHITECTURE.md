# FechaPrint v2 — Quality First

## Promise

FechaPrint v2 never claims that interpolation is super-resolution. If the requested physical size requires more pixels, production only continues when a real Real-ESRGAN provider is available and the enhanced image passes the quality gate.

## Production pipeline

1. Analyze source pixels, requested physical size, material PPI and aspect ratio.
2. Block excessive aspect-ratio crop instead of stretching or inventing layout.
3. If more pixels are required, run Real-ESRGAN 2× or 4× with tiling.
4. If PaddleOCR is available, read text before and after enhancement.
5. Quality Gate downsamples the enhanced result back to the source scale and checks edge retention, visual drift and OCR similarity.
6. Reject the enhanced result if it is worse or text changed too much.
7. Render the exact trim raster. This final step may downsample but cannot enlarge more than 5%.
8. Extend edge pixels into bleed; do not stretch the trim art into bleed.
9. Generate PDF with physical MediaBox/TrimBox/BleedBox.

## API

- `GET /api/health`
- `GET /api/capabilities`
- `POST /api/analyze`
- `POST /api/jobs` → asynchronous job
- `GET /api/jobs/{job_id}` → progress / completed / blocked / failed
- `GET /api/files/{job_id}/final.jpg`
- `GET /api/files/{job_id}/final.pdf`
- `POST /api/process` kept for synchronous integrations/tests

## Real-ESRGAN

The provider accepts, in order:

1. `FECHAPRINT_REALESRGAN_CMD` custom command template.
2. `realesrgan-ncnn-vulkan` executable on PATH.
3. `FECHAPRINT_REALESRGAN_SCRIPT=/path/to/Real-ESRGAN/inference_realesrgan.py`.

Default tile size: `256`, configurable by `FECHAPRINT_REALESRGAN_TILE`.

## Safety defaults

- No browser upscale in production.
- One Real-ESRGAN pass maximum (2× or 4×).
- Source needing more than 4× is blocked.
- Centered cover crop greater than 22% is blocked.
- OCR similarity threshold: 90% when OCR is available.
- Failed quality gate means no final production file.
