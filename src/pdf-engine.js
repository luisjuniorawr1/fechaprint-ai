const encoder = new TextEncoder();

function ascii(str) {
  return encoder.encode(str);
}

function concat(chunks) {
  const total = chunks.reduce((sum, c) => sum + c.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.length;
  }
  return out;
}

function fmt(n) {
  return Number(n).toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
}

export function buildProductionPdf({ jpegBytes, imageWidth, imageHeight, mediaBox, trimBox, bleedBox, title = 'Arquivo para impressão' }) {
  if (!(jpegBytes instanceof Uint8Array)) jpegBytes = new Uint8Array(jpegBytes);
  const [mx0, my0, mx1, my1] = mediaBox;
  const pageW = mx1 - mx0;
  const pageH = my1 - my0;

  const objects = [];
  objects[1] = ascii('<< /Type /Catalog /Pages 2 0 R >>');
  objects[2] = ascii('<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
  objects[3] = ascii(`<< /Type /Page /Parent 2 0 R /MediaBox [${mediaBox.map(fmt).join(' ')}] /TrimBox [${trimBox.map(fmt).join(' ')}] /BleedBox [${bleedBox.map(fmt).join(' ')}] /Resources << /XObject << /Im0 4 0 R >> >> /ProcSet [/PDF /ImageC] >> /Contents 5 0 R >>`);
  const imageHead = ascii(`<< /Type /XObject /Subtype /Image /Width ${imageWidth} /Height ${imageHeight} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.length} >>\nstream\n`);
  objects[4] = concat([imageHead, jpegBytes, ascii('\nendstream')]);
  const stream = `q\n${fmt(pageW)} 0 0 ${fmt(pageH)} 0 0 cm\n/Im0 Do\nQ\n`;
  objects[5] = ascii(`<< /Length ${ascii(stream).length} >>\nstream\n${stream}endstream`);
  const safeTitle = String(title).replace(/[()\\]/g, '');
  objects[6] = ascii(`<< /Title (${safeTitle}) /Producer (FechaPrint AI - PDF de producao) /Creator (FechaPrint AI) >>`);

  const header = new Uint8Array([0x25,0x50,0x44,0x46,0x2d,0x31,0x2e,0x37,0x0a,0x25,0xe2,0xe3,0xcf,0xd3,0x0a]);
  const chunks = [header];
  const offsets = [0];
  let cursor = header.length;

  for (let i = 1; i <= 6; i++) {
    offsets[i] = cursor;
    const pre = ascii(`${i} 0 obj\n`);
    const post = ascii('\nendobj\n');
    chunks.push(pre, objects[i], post);
    cursor += pre.length + objects[i].length + post.length;
  }

  const xrefOffset = cursor;
  let xref = 'xref\n0 7\n0000000000 65535 f \n';
  for (let i = 1; i <= 6; i++) xref += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  const trailer = `${xref}trailer\n<< /Size 7 /Root 1 0 R /Info 6 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  chunks.push(ascii(trailer));
  return concat(chunks);
}
