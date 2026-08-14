export const CM_PER_INCH = 2.54;
export const PDF_POINTS_PER_INCH = 72;

export const MATERIALS = {
  stationery: { label: 'Cartão / Papelaria', ppi: 300 },
  flyer: { label: 'Flyer / Folder', ppi: 300 },
  photo: { label: 'Fotografia', ppi: 300 },
  sticker: { label: 'Adesivo', ppi: 200 },
  banner: { label: 'Banner', ppi: 150 },
  canvas: { label: 'Lona', ppi: 150 },
  panel: { label: 'Painel', ppi: 100 },
  outdoor: { label: 'Outdoor', ppi: 72 },
  other: { label: 'Outro', ppi: 150 },
};

export function toCm(value, unit = 'cm') {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  if (unit === 'mm') return n / 10;
  if (unit === 'm') return n * 100;
  return n;
}

export function mmToCm(mm) {
  return Number(mm || 0) / 10;
}

export function cmToInches(cm) {
  return Number(cm || 0) / CM_PER_INCH;
}

export function cmToPdfPoints(cm) {
  return cmToInches(cm) * PDF_POINTS_PER_INCH;
}

export function ratio(width, height) {
  return height > 0 ? width / height : 0;
}

export function orientation(width, height) {
  const r = ratio(width, height);
  if (!r) return '—';
  if (Math.abs(r - 1) < 0.02) return 'Quadrado';
  if (r >= 2.4) return 'Formato panorâmico';
  return r > 1 ? 'Paisagem' : 'Retrato';
}

export function getTargetPpi(materialKey, ppiMode, customPpi) {
  if (ppiMode === 'auto') return MATERIALS[materialKey]?.ppi ?? 150;
  if (ppiMode === 'custom') return Math.max(1, Number(customPpi || 150));
  return Math.max(1, Number(ppiMode || 150));
}

export function printGeometry({ width, height, unit = 'cm', bleedMm = 0, ppi = 150 }) {
  const trimWidthCm = toCm(width, unit);
  const trimHeightCm = toCm(height, unit);
  const bleedCm = mmToCm(bleedMm);
  const totalWidthCm = trimWidthCm + bleedCm * 2;
  const totalHeightCm = trimHeightCm + bleedCm * 2;
  const totalWidthPx = Math.round(cmToInches(totalWidthCm) * ppi);
  const totalHeightPx = Math.round(cmToInches(totalHeightCm) * ppi);
  const trimWidthPx = Math.round(cmToInches(trimWidthCm) * ppi);
  const trimHeightPx = Math.round(cmToInches(trimHeightCm) * ppi);

  return {
    trimWidthCm,
    trimHeightCm,
    totalWidthCm,
    totalHeightCm,
    bleedCm,
    totalWidthPx,
    totalHeightPx,
    trimWidthPx,
    trimHeightPx,
    mediaBox: [0, 0, cmToPdfPoints(totalWidthCm), cmToPdfPoints(totalHeightCm)],
    trimBox: [
      cmToPdfPoints(bleedCm),
      cmToPdfPoints(bleedCm),
      cmToPdfPoints(bleedCm + trimWidthCm),
      cmToPdfPoints(bleedCm + trimHeightCm),
    ],
    bleedBox: [0, 0, cmToPdfPoints(totalWidthCm), cmToPdfPoints(totalHeightCm)],
  };
}

export function effectivePpi(imageWidthPx, imageHeightPx, trimWidthCm, trimHeightCm, fitMode = 'fill') {
  if (!imageWidthPx || !imageHeightPx || !trimWidthCm || !trimHeightCm) return 0;
  const ppiX = imageWidthPx / cmToInches(trimWidthCm);
  const ppiY = imageHeightPx / cmToInches(trimHeightCm);
  const srcRatio = imageWidthPx / imageHeightPx;
  const dstRatio = trimWidthCm / trimHeightCm;

  // "fit" encosta a dimensão limitante e deixa margem na outra.
  if (fitMode === 'fit') return srcRatio > dstRatio ? ppiX : ppiY;
  // "fill" encosta a dimensão oposta e recorta o excesso.
  return srcRatio > dstRatio ? ppiY : ppiX;
}

export function qualityStatus(effective, target) {
  if (!target) return { level: 'neutral', label: 'Aguardando', description: 'Defina a configuração de impressão.' };
  const ratioValue = effective / target;
  if (ratioValue >= 1) return { level: 'good', label: 'Excelente', description: 'Imagem suficientemente grande para a resolução alvo.' };
  if (ratioValue >= 0.67) return { level: 'warn', label: 'Aceitável', description: 'Pode funcionar, mas existe perda de definição.' };
  return { level: 'bad', label: 'Insuficiente', description: 'Recomendamos aprimoramento ou redução do PPI/tamanho.' };
}

export function autoUpscaleFactor(imageWidthPx, imageHeightPx, requiredWidthPx, requiredHeightPx) {
  if (!imageWidthPx || !imageHeightPx) return 1;
  const factor = Math.max(requiredWidthPx / imageWidthPx, requiredHeightPx / imageHeightPx, 1);
  if (factor <= 1.2) return 1;
  if (factor <= 2.4) return 2;
  if (factor <= 4.5) return 4;
  return Math.ceil(factor * 10) / 10;
}

export function formatRatio(width, height, digits = 3) {
  const r = ratio(width, height);
  return r ? `${r.toFixed(digits).replace('.', ',')} : 1` : '—';
}

export function estimateRasterMemory(widthPx, heightPx) {
  const bytes = Math.max(0, widthPx) * Math.max(0, heightPx) * 4;
  return { bytes, mb: bytes / 1024 / 1024 };
}
