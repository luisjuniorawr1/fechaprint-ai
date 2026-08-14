from __future__ import annotations

from pathlib import Path

CM_PER_INCH = 2.54
PT_PER_INCH = 72


def cm_to_pt(cm: float) -> float:
    return cm / CM_PER_INCH * PT_PER_INCH


def _fmt(n: float) -> str:
    text = f"{n:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def build_pdf(jpeg_path: Path, output_path: Path, width_cm: float, height_cm: float, bleed_mm: float = 0.0) -> None:
    jpeg = jpeg_path.read_bytes()
    from PIL import Image
    with Image.open(jpeg_path) as img:
        iw, ih = img.size
    bleed_cm = bleed_mm / 10.0
    total_w_cm = width_cm + 2 * bleed_cm
    total_h_cm = height_cm + 2 * bleed_cm
    media = [0, 0, cm_to_pt(total_w_cm), cm_to_pt(total_h_cm)]
    trim = [cm_to_pt(bleed_cm), cm_to_pt(bleed_cm), cm_to_pt(bleed_cm + width_cm), cm_to_pt(bleed_cm + height_cm)]
    page_w, page_h = media[2], media[3]
    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    box = lambda b: " ".join(_fmt(x) for x in b)
    objects[3] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [{box(media)}] /TrimBox [{box(trim)}] /BleedBox [{box(media)}] /Resources << /XObject << /Im0 4 0 R >> >> /ProcSet [/PDF /ImageC] >> /Contents 5 0 R >>").encode()
    head = f"<< /Type /XObject /Subtype /Image /Width {iw} /Height {ih} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpeg)} >>\nstream\n".encode()
    objects[4] = head + jpeg + b"\nendstream"
    stream = f"q\n{_fmt(page_w)} 0 0 {_fmt(page_h)} 0 0 cm\n/Im0 Do\nQ\n".encode()
    objects[5] = f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"endstream"
    objects[6] = b"<< /Title (FechaPrint AI) /Producer (FechaPrint AI Open Source Pipeline) >>"
    header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    chunks = [header]; offsets = [0] * 7; cursor = len(header)
    for i in range(1, 7):
        offsets[i] = cursor
        chunk = f"{i} 0 obj\n".encode() + objects[i] + b"\nendobj\n"
        chunks.append(chunk); cursor += len(chunk)
    xref_offset = cursor
    xref = b"xref\n0 7\n0000000000 65535 f \n" + b"".join(f"{offsets[i]:010d} 00000 n \n".encode() for i in range(1,7))
    trailer = xref + f"trailer\n<< /Size 7 /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    output_path.write_bytes(b"".join(chunks) + trailer)
