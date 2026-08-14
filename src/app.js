const $ = (s) => document.querySelector(s);
const els = {
  dropzone: $('#dropzone'), fileInput: $('#fileInput'), fileCard: $('#fileCard'), filePreview: $('#filePreview'), fileName: $('#fileName'), fileMeta: $('#fileMeta'),
  width: $('#width'), height: $('#height'), unit: $('#unit'), material: $('#material'), mode: $('#mode'), process: $('#process'), progress: $('#progress'),
  largePreview: $('#largePreview'), emptyPreview: $('#emptyPreview'), backendState: $('#backendState'), engines: $('#engines'), resultPanel: $('#resultPanel'),
  resultSummary: $('#resultSummary'), steps: $('#steps'), downloadPdf: $('#downloadPdf'), downloadImage: $('#downloadImage'), errorPanel: $('#errorPanel'),
};

const state = { file: null, objectUrl: null, backendOnline: false };
const API = window.FECHAPRINT_API_URL || '';

boot();

async function boot() {
  bind();
  await checkBackend();
}

function bind() {
  els.dropzone.addEventListener('click', () => els.fileInput.click());
  els.dropzone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); els.fileInput.click(); } });
  els.fileInput.addEventListener('change', (e) => handleFile(e.target.files?.[0]));
  els.dropzone.addEventListener('dragover', (e) => { e.preventDefault(); els.dropzone.classList.add('drag'); });
  els.dropzone.addEventListener('dragleave', () => els.dropzone.classList.remove('drag'));
  els.dropzone.addEventListener('drop', (e) => { e.preventDefault(); els.dropzone.classList.remove('drag'); handleFile(e.dataTransfer.files?.[0]); });
  els.process.addEventListener('click', processJob);
}

async function checkBackend() {
  try {
    const response = await fetch(`${API}/api/capabilities`, { cache: 'no-store' });
    if (!response.ok) throw new Error('backend offline');
    const data = await response.json();
    state.backendOnline = true;
    els.backendState.dataset.state = 'online';
    els.backendState.textContent = 'Backend open-source online';
    renderEngines(data.engines || []);
  } catch {
    state.backendOnline = false;
    els.backendState.dataset.state = 'offline';
    els.backendState.textContent = 'Backend de IA não conectado';
    els.engines.innerHTML = `<div class="engine unavailable"><span class="engine-dot"></span><div><strong>Servidor de processamento ausente</strong><span>O frontend está online, mas os modelos open-source precisam rodar no backend GPU.</span></div></div>`;
  }
  updateButton();
}

function renderEngines(engines) {
  els.engines.innerHTML = engines.map((engine) => `
    <div class="engine ${engine.available ? 'available' : 'unavailable'}">
      <span class="engine-dot"></span>
      <div><strong>${escapeHtml(engine.label)}</strong><span>${escapeHtml(engine.role)} · ${escapeHtml(engine.reason)}</span></div>
      <code>${escapeHtml(engine.license)}</code>
    </div>`).join('') || '<div class="engine">Nenhum motor reportado.</div>';
}

function handleFile(file) {
  if (!file) return;
  if (!['image/jpeg','image/png','image/webp'].includes(file.type)) return showError('Use JPG, PNG ou WEBP.');
  state.file = file;
  if (state.objectUrl) URL.revokeObjectURL(state.objectUrl);
  state.objectUrl = URL.createObjectURL(file);
  els.filePreview.src = state.objectUrl;
  els.largePreview.src = state.objectUrl;
  els.largePreview.hidden = false;
  els.emptyPreview.hidden = true;
  els.fileName.textContent = file.name;
  els.fileMeta.textContent = `${formatBytes(file.size)} · ${file.type.replace('image/','').toUpperCase()}`;
  els.fileCard.hidden = false;
  els.resultPanel.hidden = true;
  hideError();
  updateButton();
}

function updateButton() {
  els.process.disabled = !(state.file && state.backendOnline);
}

async function processJob() {
  if (!state.file || !state.backendOnline) return;
  hideError(); els.resultPanel.hidden = true; setLoading(true);
  const form = new FormData();
  form.append('file', state.file);
  form.append('width', els.width.value);
  form.append('height', els.height.value);
  form.append('unit', els.unit.value);
  form.append('material', els.material.value);
  form.append('mode', els.mode.value);
  try {
    const response = await fetch(`${API}/api/process`, { method: 'POST', body: form });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Falha no processamento (${response.status})`);
    renderResult(data);
  } catch (error) {
    showError(error.message || 'Não foi possível processar a arte.');
  } finally { setLoading(false); }
}

function renderResult(data) {
  els.resultSummary.textContent = `${number(data.width_cm)} × ${number(data.height_cm)} cm · ${data.material} · ${data.target_ppi} PPI · sangria ${number(data.bleed_mm)} mm`;
  els.steps.innerHTML = (data.steps || []).map((s) => `<div class="step ${escapeHtml(s.status)}"><strong>${escapeHtml(s.engine)}:</strong> ${escapeHtml(s.detail)}</div>`).join('');
  els.downloadPdf.href = `${API}${data.pdf_url}`;
  els.downloadImage.href = `${API}${data.image_url}`;
  els.resultPanel.hidden = false;
  els.largePreview.src = `${API}${data.image_url}?t=${Date.now()}`;
  els.largePreview.hidden = false;
  els.emptyPreview.hidden = true;
}

function setLoading(value) { els.process.disabled = value || !(state.file && state.backendOnline); els.progress.hidden = !value; }
function showError(message) { els.errorPanel.textContent = message; els.errorPanel.hidden = false; }
function hideError() { els.errorPanel.hidden = true; els.errorPanel.textContent = ''; }
function formatBytes(bytes) { return bytes < 1024*1024 ? `${(bytes/1024).toFixed(1)} KB` : `${(bytes/1024/1024).toFixed(2)} MB`; }
function number(v) { return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(Number(v||0)); }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
window.addEventListener('beforeunload', () => { if (state.objectUrl) URL.revokeObjectURL(state.objectUrl); });
