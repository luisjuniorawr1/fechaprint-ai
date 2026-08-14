import test from 'node:test';
import assert from 'node:assert/strict';
import { printGeometry, effectivePpi, qualityStatus, cmToPdfPoints } from '../src/print-engine.js';
import { placementFor } from '../src/image-engine.js';

test('Teste 1: 6000x4000 em 30x20 cm a 300 PPI é adequado', () => {
  const eff = effectivePpi(6000, 4000, 30, 20, 'fill');
  const status = qualityStatus(eff, 300);
  assert.ok(eff > 300);
  assert.equal(status.label, 'Excelente');
});

test('Teste 2: 1000x1000 em 100x100 cm a 150 PPI é insuficiente', () => {
  const eff = effectivePpi(1000, 1000, 100, 100, 'fill');
  const status = qualityStatus(eff, 150);
  assert.ok(eff < 30);
  assert.equal(status.label, 'Insuficiente');
});

test('Teste 3: quadrada em 200x50 nunca é esticada horizontalmente', () => {
  const fill = placementFor({ srcW: 1000, srcH: 1000, dstW: 2000, dstH: 500, mode: 'fill' });
  const fit = placementFor({ srcW: 1000, srcH: 1000, dstW: 2000, dstH: 500, mode: 'fit' });
  assert.equal(fill.w / fill.h, 1);
  assert.equal(fit.w / fit.h, 1);
  assert.ok(fill.h > 500, 'Preencher deve recortar verticalmente');
  assert.ok(fit.w < 2000, 'Encaixar deve deixar áreas laterais');
  assert.ok(effectivePpi(1000, 1000, 200, 50, 'fit') > effectivePpi(1000, 1000, 200, 50, 'fill'));
});

test('Teste 4: 100x50 cm converte exatamente para pontos PDF', () => {
  const g = printGeometry({ width: 100, height: 50, unit: 'cm', bleedMm: 0, ppi: 150 });
  assert.ok(Math.abs(g.mediaBox[2] - cmToPdfPoints(100)) < 1e-9);
  assert.ok(Math.abs(g.mediaBox[3] - cmToPdfPoints(50)) < 1e-9);
  assert.ok(Math.abs(g.mediaBox[2] - 2834.645669291339) < 1e-6);
});

test('Teste 5: sangria 5 mm gera total 101x51 e boxes coerentes', () => {
  const g = printGeometry({ width: 100, height: 50, unit: 'cm', bleedMm: 5, ppi: 150 });
  assert.equal(g.totalWidthCm, 101);
  assert.equal(g.totalHeightCm, 51);
  assert.ok(Math.abs((g.trimBox[2] - g.trimBox[0]) - cmToPdfPoints(100)) < 1e-9);
  assert.ok(Math.abs((g.trimBox[3] - g.trimBox[1]) - cmToPdfPoints(50)) < 1e-9);
  assert.ok(Math.abs((g.bleedBox[2] - g.bleedBox[0]) - cmToPdfPoints(101)) < 1e-9);
  assert.ok(Math.abs((g.bleedBox[3] - g.bleedBox[1]) - cmToPdfPoints(51)) < 1e-9);
});
