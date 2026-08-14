import test from 'node:test';
import assert from 'node:assert/strict';
import { buildProductionPdf } from '../src/pdf-engine.js';
import { printGeometry } from '../src/print-engine.js';

test('PDF inclui MediaBox, TrimBox e BleedBox numéricos', () => {
  const g = printGeometry({ width: 100, height: 50, unit: 'cm', bleedMm: 5, ppi: 150 });
  const pdf = buildProductionPdf({
    jpegBytes: new Uint8Array([0xff,0xd8,0xff,0xd9]), imageWidth: 1, imageHeight: 1,
    mediaBox: g.mediaBox, trimBox: g.trimBox, bleedBox: g.bleedBox,
  });
  const text = new TextDecoder('latin1').decode(pdf);
  assert.match(text, /%PDF-1\.7/);
  assert.match(text, /\/MediaBox \[0 0 2862\.9921 1445\.6693\]/);
  assert.match(text, /\/TrimBox \[14\.1732 14\.1732 2848\.8189 1431\.4961\]/);
  assert.match(text, /\/BleedBox \[0 0 2862\.9921 1445\.6693\]/);
});
