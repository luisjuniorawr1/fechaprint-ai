import {
  MATERIALS, getTargetPpi, printGeometry, effectivePpi, qualityStatus,
  orientation, formatRatio, estimateRasterMemory, autoUpscaleFactor,
} from './print-engine.js';
import { loadImageFile, renderComposition, compositionToJpegBlob } from './image-engine.js';
import { buildProductionPdf } from './pdf-engine.js';
import { aiProvider } from './ai-provider.js';
import { colorManagement } from './color-management.js';

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const els = {
  dropzone: $('#dropzone'), fileInput: $('#fileInput'), fileCard: $('#fileCard'), filePreview: $('#filePreview'),
  fileName: $('#fileName'), fileMeta: $('#fileMeta'), width: $('#width'), height: $('#height'), unit: $('#unit'),
  material: $('#material'), ppi: $('#ppi'), customPpi: $('#customPpi'), customPpiWrap: $('#customPpiWrap'),
  bleed: $('#bleed'), customBleed: $('#customBleed'), customBleedWrap: $('#customBleedWrap'),
  fitButtons: $$('.fit-option'), fitBg: $('#fitBg'), bgMode: $('#bgMode'), bgColor: $('#bgColor'),
  zoom: $('#zoom'), zoomValue: $('#zoomValue'), resetPosition: $('#resetPosition'),
  canvas: $('#previewCanvas'), emptyPreview: $('#emptyPreview'), orientation: $('#orientation'), ratio: $('#ratio'),
  originalPx: $('#originalPx'), requiredPx: $('#requiredPx'), effectivePpi: $('#effectivePpi'), targetPpi: $('#targetPpi'),
  qualityCard: $('#qualityCard'), qualityLabel: $('#qualityLabel'), qualityDescription: $('#qualityDescription'),
  alerts: $('#alerts'), finalSize: $('#finalSize'), bleedSize: $('#bleedSize'), materialOut: $('#materialOut'),
  modeOut: $('#modeOut'), bleedOut: $('#bleedOut'), colorOut: $('#colorOut'), memoryOut: $('#memoryOut'),
  advancedToggle: $('#advancedToggle'), advanced: $('#advanced'), aiStatus: $('#aiStatus'), cmykStatus: $('#cmykStatus'),
  generate: $('#generate'), progress: $('#progress'), result: $('#result'), resultMeta: $('#resultMeta'), download: $('#download'),
};

const state = {
  image: null,
  imageUrl: null,
  file: null,
  transparency: false,
  fitMode: 'fill',
  panX: 0,
  panY: 0,
  drag: null,
  pdfUrl: null,
};

for (const [key, info] of Object.entries(MATERIALS)) {
  const option = document.createElement('option');
  option.value = key;
  option.textContent = info.label;
  if (key === 'canvas') option.selected = true;
  els.material.append(option);
}

function formatNumber(n, digits = 0) {
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: digits }).format(n || 0);
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let n = bytes, i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0).replace('.', ',')} ${units[i]}`;
}

function getBleedMm() {
  return els.bleed.value === 'custom' ? Math.max(0, Number(els.customBleed.value || 0)) : Number(els.bleed.value || 0);
}

function getSettings() {
  const ppiValue = getTargetPpi(els.material.value, els.ppi.value, els.customPpi.value);
  const geometry = printGeometry({
    width: els.width.value,
    height: els.height.value,
    unit: els.unit.value,
    bleedMm: getBleedMm(),
    ppi: ppiValue,
  });
  return { ppiValue, geometry };
}

async function detectTransparency(img, file) {
  if (!['image/png', 'image/webp'].includes(file.type)) return false;
  const c = document.createElement('canvas');
  const max = 256;
  const scale = Math.min(max / img.naturalWidth, max / img.naturalHeight, 1);
  c.width = Math.max(1, Math.round(img.naturalWidth * scale));
  c.height = Math.max(1, Math.round(img.naturalHeight * scale));
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.clearRect(0, 0, c.width, c.height);
  ctx.drawImage(img, 0, 0, c.width, c.height);
  const data = ctx.getImageData(0, 0, c.width, c.height).data;
  for (let i = 3; i < data.length; i += 4) if (data[i] < 255) return true;
  return false;
}

async function handleFile(file) {
  const allowed = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowed.includes(file.type)) return showGlobalError('Use JPG, JPEG, PNG ou WEBP.');
  try {
    const loaded = await loadImageFile(file);
    if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
    state.file = file;
    state.image = loaded.img;
    state.imageUrl = loaded.url;
    state.panX = 0; state.panY = 0;
    state.transparency = await detectTransparency(loaded.img, file);
    els.filePreview.src = loaded.url;
    els.fileName.textContent = file.name;
    els.fileMeta.textContent = `${formatNumber(loaded.width)} × ${formatNumber(loaded.height)} px · ${formatBytes(file.size)} · ${formatRatio(loaded.width, loaded.height, 3)}`;
    els.fileCard.hidden = false;
    els.emptyPreview.hidden = true;
    update();
  } catch (err) {
    showGlobalError(err.message);
  }
}

function showGlobalError(message) {
  els.alerts.innerHTML = `<div class="alert bad"><strong>Não foi possível continuar.</strong><span>${escapeHtml(message)}</span></div>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function alertsFor(settings, effective) {
  const { geometry, ppiValue } = settings;
  const list = [];
  if (!state.image) return list;
  const srcRatio = state.image.naturalWidth / state.image.naturalHeight;
  const dstRatio = geometry.trimWidthCm / geometry.trimHeightCm;
  if (Math.abs(srcRatio / dstRatio - 1) > 0.02) {
    list.push({ level: 'warn', title: 'Proporções diferentes', text: 'A imagem não será esticada. Use Preencher (corte) ou Encaixar (preserva 100%).' });
  }
  if (effective < ppiValue * 0.67) {
    const factor = autoUpscaleFactor(state.image.naturalWidth, state.image.naturalHeight, geometry.trimWidthPx, geometry.trimHeightPx);
    list.push({ level: 'bad', title: 'Resolução insuficiente', text: `A fonte tem cerca de ${formatNumber(effective)} PPI efetivos. Um upscale aproximado de ${factor}× seria necessário para chegar perto da meta, mas ampliar pixels não recria detalhes.` });
  }
  if (state.transparency) {
    list.push({ level: 'warn', title: 'Transparência detectada', text: 'A saída PDF será achatada em RGB sobre o fundo selecionado antes da incorporação.' });
  }
  const memory = estimateRasterMemory(geometry.totalWidthPx, geometry.totalHeightPx);
  if (geometry.totalWidthPx > 16000 || geometry.totalHeightPx > 16000 || memory.mb > 340) {
    list.push({ level: 'bad', title: 'Raster muito grande para o navegador', text: `Esta configuração exigiria aproximadamente ${formatNumber(geometry.totalWidthPx)} × ${formatNumber(geometry.totalHeightPx)} px (~${formatNumber(memory.mb)} MB só em memória raster). Reduza o PPI ou use processamento servidor.` });
  } else if (memory.mb > 220) {
    list.push({ level: 'warn', title: 'Arquivo pesado', text: `O processamento pode usar cerca de ${formatNumber(memory.mb)} MB de memória raster. Em grande formato, 100–150 PPI costuma ser mais prático conforme a distância de visualização.` });
  }
  return list;
}

function renderAlerts(list) {
  if (!state.image) {
    els.alerts.innerHTML = '<div class="alert neutral"><strong>Aguardando imagem</strong><span>Envie um arquivo para iniciar o diagnóstico.</span></div>';
    return;
  }
  if (!list.length) {
    els.alerts.innerHTML = '<div class="alert good"><strong>Configuração consistente</strong><span>Nenhum alerta crítico detectado para esta combinação.</span></div>';
    return;
  }
  els.alerts.innerHTML = list.map(a => `<div class="alert ${a.level}"><strong>${escapeHtml(a.title)}</strong><span>${escapeHtml(a.text)}</span></div>`).join('');
}

function update() {
  const settings = getSettings();
  const { ppiValue, geometry } = settings;
  const validSize = geometry.trimWidthCm > 0 && geometry.trimHeightCm > 0;
  const sourceWidthCm = state.fitMode === 'fill' ? geometry.totalWidthCm : geometry.trimWidthCm;
  const sourceHeightCm = state.fitMode === 'fill' ? geometry.totalHeightCm : geometry.trimHeightCm;
  const zoomFactor = Number(els.zoom.value) / 100;
  const eff = state.image && validSize ? effectivePpi(state.image.naturalWidth, state.image.naturalHeight, sourceWidthCm, sourceHeightCm, state.fitMode) / zoomFactor : 0;
  const quality = qualityStatus(eff, ppiValue);

  els.customPpiWrap.hidden = els.ppi.value !== 'custom';
  els.customBleedWrap.hidden = els.bleed.value !== 'custom';
  els.fitBg.hidden = state.fitMode !== 'fit';
  els.bgColor.hidden = els.bgMode.value !== 'color';
  els.zoomValue.textContent = `${els.zoom.value}%`;

  els.ratio.textContent = validSize ? formatRatio(geometry.trimWidthCm, geometry.trimHeightCm, 3) : '—';
  els.orientation.textContent = validSize ? orientation(geometry.trimWidthCm, geometry.trimHeightCm) : '—';
  els.originalPx.textContent = state.image ? `${formatNumber(state.image.naturalWidth)} × ${formatNumber(state.image.naturalHeight)} px` : '—';
  els.requiredPx.textContent = validSize ? `${formatNumber(geometry.totalWidthPx)} × ${formatNumber(geometry.totalHeightPx)} px` : '—';
  els.effectivePpi.textContent = state.image && validSize ? `${formatNumber(eff)} PPI` : '—';
  els.targetPpi.textContent = `${formatNumber(ppiValue)} PPI`;
  els.qualityCard.dataset.level = quality.level;
  els.qualityLabel.textContent = quality.label;
  els.qualityDescription.textContent = quality.description;

  els.finalSize.textContent = validSize ? `${formatNumber(geometry.trimWidthCm, 2)} × ${formatNumber(geometry.trimHeightCm, 2)} cm` : '—';
  els.bleedSize.textContent = validSize ? `${formatNumber(geometry.totalWidthCm, 2)} × ${formatNumber(geometry.totalHeightCm, 2)} cm` : '—';
  els.materialOut.textContent = MATERIALS[els.material.value]?.label ?? '—';
  els.modeOut.textContent = state.fitMode === 'fill' ? 'Preencher / recortar' : state.fitMode === 'fit' ? 'Encaixar' : 'Expandir com IA';
  els.bleedOut.textContent = `${formatNumber(getBleedMm(), 1)} mm`;
  els.colorOut.textContent = 'RGB / DeviceRGB';
  els.memoryOut.textContent = validSize ? `~${formatNumber(estimateRasterMemory(geometry.totalWidthPx, geometry.totalHeightPx).mb)} MB raster` : '—';
  els.aiStatus.textContent = aiProvider.available ? aiProvider.name : 'Não configurado — sem processamento simulado';
  els.cmykStatus.textContent = colorManagement.description;

  const list = alertsFor(settings, eff);
  renderAlerts(list);
  els.generate.disabled = !(state.image && validSize) || state.fitMode === 'outpaint';
  drawPreview(settings);
}

function drawPreview(settings) {
  const canvas = els.canvas;
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.max(320, Math.round(rect.width * dpr));
  const h = Math.max(360, Math.round(rect.height * dpr));
  if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#eef1f4'; ctx.fillRect(0, 0, w, h);
  if (!state.image || !settings.geometry.trimWidthCm || !settings.geometry.trimHeightCm) return;

  const { geometry } = settings;
  const pad = 44 * dpr;
  const availableW = w - pad * 2;
  const availableH = h - pad * 2;
  const pageRatio = geometry.totalWidthCm / geometry.totalHeightCm;
  let pageW = availableW;
  let pageH = pageW / pageRatio;
  if (pageH > availableH) { pageH = availableH; pageW = pageH * pageRatio; }
  const x = (w - pageW) / 2, y = (h - pageH) / 2;
  const bleedFracX = geometry.totalWidthCm ? geometry.bleedCm / geometry.totalWidthCm : 0;
  const bleedFracY = geometry.totalHeightCm ? geometry.bleedCm / geometry.totalHeightCm : 0;
  const trimRect = { x: pageW * bleedFracX, y: pageH * bleedFracY, w: pageW * geometry.trimWidthCm / geometry.totalWidthCm, h: pageH * geometry.trimHeightCm / geometry.totalHeightCm };

  ctx.save(); ctx.translate(x, y);
  ctx.shadowColor = 'rgba(20,28,38,.18)'; ctx.shadowBlur = 24 * dpr; ctx.shadowOffsetY = 8 * dpr;
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, pageW, pageH); ctx.restore();

  ctx.save(); ctx.translate(x, y);
  ctx.beginPath(); ctx.rect(0, 0, pageW, pageH); ctx.clip();
  renderComposition(ctx, {
    image: state.image, width: pageW, height: pageH, trimRect,
    mode: state.fitMode === 'fit' ? 'fit' : 'fill',
    zoom: Number(els.zoom.value) / 100,
    panX: state.panX, panY: state.panY,
    background: els.bgMode.value,
    backgroundColor: els.bgColor.value,
    clip: true,
  });
  ctx.restore();

  ctx.save(); ctx.translate(x, y);
  if (geometry.bleedCm > 0) {
    ctx.strokeStyle = '#e65a5a'; ctx.lineWidth = 1.5 * dpr; ctx.setLineDash([7 * dpr, 5 * dpr]);
    ctx.strokeRect(0, 0, pageW, pageH);
  }
  ctx.strokeStyle = '#15191f'; ctx.lineWidth = 1.5 * dpr; ctx.setLineDash([]);
  ctx.strokeRect(trimRect.x, trimRect.y, trimRect.w, trimRect.h);
  const mark = 8 * dpr;
  ctx.strokeStyle = '#15191f'; ctx.lineWidth = 1 * dpr;
  const tx = trimRect.x, ty = trimRect.y, tr = trimRect.x + trimRect.w, tb = trimRect.y + trimRect.h;
  [[tx,ty,-mark,0],[tx,ty,0,-mark],[tr,ty,mark,0],[tr,ty,0,-mark],[tx,tb,-mark,0],[tx,tb,0,mark],[tr,tb,mark,0],[tr,tb,0,mark]].forEach(([sx,sy,dx,dy])=>{ctx.beginPath();ctx.moveTo(sx,sy);ctx.lineTo(sx+dx,sy+dy);ctx.stroke();});
  ctx.restore();

  canvas.dataset.pageX = x; canvas.dataset.pageY = y; canvas.dataset.pageW = pageW; canvas.dataset.pageH = pageH;
}

async function generatePdf() {
  const settings = getSettings();
  const { geometry, ppiValue } = settings;
  const memory = estimateRasterMemory(geometry.totalWidthPx, geometry.totalHeightPx);
  if (!state.image) return;
  if (state.fitMode === 'outpaint') return showGlobalError('Expandir com IA requer um provider real de outpainting; nenhum está configurado neste runtime.');
  if (geometry.totalWidthPx > 16000 || geometry.totalHeightPx > 16000 || memory.mb > 340) {
    return showGlobalError('A rasterização ultrapassa o limite seguro deste processamento no navegador. Reduza o PPI ou as dimensões físicas.');
  }
  els.generate.disabled = true;
  els.progress.hidden = false;
  els.progress.textContent = 'Preparando raster final…';
  els.result.hidden = true;
  try {
    const bleedPxX = Math.round(geometry.totalWidthPx * geometry.bleedCm / geometry.totalWidthCm);
    const bleedPxY = Math.round(geometry.totalHeightPx * geometry.bleedCm / geometry.totalHeightCm);
    const trimRect = { x: bleedPxX, y: bleedPxY, w: geometry.trimWidthPx, h: geometry.trimHeightPx };
    const jpeg = await compositionToJpegBlob({
      image: state.image,
      width: geometry.totalWidthPx,
      height: geometry.totalHeightPx,
      trimRect,
      mode: state.fitMode,
      zoom: Number(els.zoom.value) / 100,
      panX: state.panX,
      panY: state.panY,
      background: els.bgMode.value,
      backgroundColor: els.bgColor.value,
      clip: true,
    }, 0.92);
    els.progress.textContent = 'Montando PDF com MediaBox, TrimBox e BleedBox…';
    const jpegBytes = new Uint8Array(await jpeg.arrayBuffer());
    const pdfBytes = buildProductionPdf({
      jpegBytes,
      imageWidth: geometry.totalWidthPx,
      imageHeight: geometry.totalHeightPx,
      mediaBox: geometry.mediaBox,
      trimBox: geometry.trimBox,
      bleedBox: geometry.bleedBox,
      title: `Impressão ${formatNumber(geometry.trimWidthCm,2)} x ${formatNumber(geometry.trimHeightCm,2)} cm`,
    });
    const blob = new Blob([pdfBytes], { type: 'application/pdf' });
    if (state.pdfUrl) URL.revokeObjectURL(state.pdfUrl);
    state.pdfUrl = URL.createObjectURL(blob);
    const name = `impressao_${String(formatNumber(geometry.trimWidthCm,2)).replace(/\./g,'').replace(',','-')}x${String(formatNumber(geometry.trimHeightCm,2)).replace(/\./g,'').replace(',','-')}cm_${ppiValue}ppi.pdf`;
    els.download.href = state.pdfUrl;
    els.download.download = name;
    const sourceWidthCm = state.fitMode === 'fill' ? geometry.totalWidthCm : geometry.trimWidthCm;
    const sourceHeightCm = state.fitMode === 'fill' ? geometry.totalHeightCm : geometry.trimHeightCm;
    const eff = effectivePpi(state.image.naturalWidth, state.image.naturalHeight, sourceWidthCm, sourceHeightCm, state.fitMode) / (Number(els.zoom.value) / 100);
    els.resultMeta.innerHTML = `<strong>${formatNumber(geometry.totalWidthCm,2)} × ${formatNumber(geometry.totalHeightCm,2)} cm</strong> com sangria · ${formatBytes(blob.size)} · raster físico ${formatNumber(ppiValue)} PPI · fonte efetiva ~${formatNumber(eff)} PPI · RGB · PDF de produção`;
    els.result.hidden = false;
  } catch (err) {
    showGlobalError(err?.message || 'Falha inesperada ao gerar o PDF.');
  } finally {
    els.progress.hidden = true;
    els.generate.disabled = false;
  }
}

els.dropzone.addEventListener('click', () => els.fileInput.click());
els.dropzone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') els.fileInput.click(); });
els.fileInput.addEventListener('change', () => els.fileInput.files?.[0] && handleFile(els.fileInput.files[0]));
['dragenter','dragover'].forEach(type => els.dropzone.addEventListener(type, e => { e.preventDefault(); els.dropzone.classList.add('dragging'); }));
['dragleave','drop'].forEach(type => els.dropzone.addEventListener(type, e => { e.preventDefault(); els.dropzone.classList.remove('dragging'); }));
els.dropzone.addEventListener('drop', e => e.dataTransfer.files?.[0] && handleFile(e.dataTransfer.files[0]));

[els.width, els.height, els.unit, els.material, els.ppi, els.customPpi, els.bleed, els.customBleed, els.bgMode, els.bgColor, els.zoom].forEach(el => el.addEventListener('input', update));
els.material.addEventListener('change', update); els.ppi.addEventListener('change', update); els.bleed.addEventListener('change', update); els.bgMode.addEventListener('change', update);
els.fitButtons.forEach(btn => btn.addEventListener('click', () => {
  if (btn.dataset.mode === 'outpaint' && !aiProvider.available) return;
  state.fitMode = btn.dataset.mode;
  els.fitButtons.forEach(b => b.classList.toggle('active', b === btn));
  state.panX = 0; state.panY = 0; update();
}));
els.resetPosition.addEventListener('click', () => { state.panX = 0; state.panY = 0; els.zoom.value = 100; update(); });
els.advancedToggle.addEventListener('click', () => { els.advanced.hidden = !els.advanced.hidden; els.advancedToggle.setAttribute('aria-expanded', String(!els.advanced.hidden)); });
els.generate.addEventListener('click', generatePdf);

els.canvas.addEventListener('pointerdown', e => { if (!state.image) return; state.drag = { x: e.clientX, y: e.clientY, panX: state.panX, panY: state.panY }; els.canvas.setPointerCapture(e.pointerId); });
els.canvas.addEventListener('pointermove', e => {
  if (!state.drag) return;
  const pw = Number(els.canvas.dataset.pageW || 1) / (window.devicePixelRatio || 1);
  const ph = Number(els.canvas.dataset.pageH || 1) / (window.devicePixelRatio || 1);
  state.panX = Math.max(-1, Math.min(1, state.drag.panX + (e.clientX - state.drag.x) / Math.max(40, pw / 2)));
  state.panY = Math.max(-1, Math.min(1, state.drag.panY + (e.clientY - state.drag.y) / Math.max(40, ph / 2)));
  update();
});
['pointerup','pointercancel'].forEach(type => els.canvas.addEventListener(type, () => { state.drag = null; }));
window.addEventListener('resize', () => update());

update();
