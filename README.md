# FechaPrint AI — MVP funcional

Aplicação web estática que prepara JPG/JPEG/PNG/WEBP para impressão e gera um PDF de produção diretamente no navegador.

## Implementado

- Upload/drag-and-drop com leitura real de dimensões.
- Conversões mm/cm/m e cálculo matemático de PPI/pixels necessários.
- Presets de material com PPI sugerido e PPI manual.
- Diagnóstico de resolução efetiva, qualidade e memória raster estimada.
- Enquadramento sem distorção: Preencher (crop) e Encaixar (branco, preto, cor, fundo desfocado).
- Pan/zoom no preview.
- Sangria externa e linhas de corte.
- PDF real com página no tamanho físico solicitado e `MediaBox`, `TrimBox`, `BleedBox`.
- Saída RGB honesta; sem falso CMYK ou falso PDF/X.
- Arquitetura desacoplada para `AIImageProvider` e gerenciamento de cor futuro.
- Processamento local no browser, sem upload de arquivo ao servidor.

## Limites intencionais

- Outpainting/upscale por IA só é habilitado quando um provider real for configurado.
- Conversão CMYK/ICC certificada e PDF/X-4 exigem pipeline externo/servidor apropriado.
- Rasterização no navegador é bloqueada acima de limites conservadores de dimensão/memória para evitar crash.

## Testes

```bash
npm test
```

## Rodar localmente

```bash
npm run serve
```

Abra `http://localhost:4173`.
