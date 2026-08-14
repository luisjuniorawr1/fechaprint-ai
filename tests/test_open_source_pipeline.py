import tempfile
import unittest
from pathlib import Path
from PIL import Image

from backend.pipeline import ocr_similarity, target_ppi, Pipeline
from backend.pdf_engine import build_pdf


class PipelineTests(unittest.TestCase):
    def test_ocr_similarity_accepts_formatting_changes(self):
        self.assertGreater(ocr_similarity('Francisca Maria da Silva 1931', 'FRANCISCA  MARIA DA SILVA - 1931'), 0.9)

    def test_large_canvas_uses_large_format_ppi(self):
        self.assertEqual(target_ppi('canvas', 500, 200), 60)
        self.assertEqual(target_ppi('canvas', 100, 50), 100)

    def test_pdf_has_print_boxes(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); jpg = td / 'image.jpg'; Image.new('RGB', (100, 50), 'white').save(jpg, 'JPEG'); pdf = td / 'print.pdf'
            build_pdf(jpg, pdf, 100, 50, 5); data = pdf.read_bytes()
            self.assertIn(b'/MediaBox', data); self.assertIn(b'/TrimBox', data); self.assertIn(b'/BleedBox', data)

    def test_fallback_pipeline_generates_files_without_models(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); img = td / 'source.jpg'; Image.new('RGB', (600, 900), '#d8c8a8').save(img, 'JPEG')
            result = Pipeline().process(img, width=100, height=40, unit='cm', material='canvas', mode='safe')
            self.assertTrue(result['pdf_url'].endswith('final.pdf')); self.assertTrue(result['image_url'].endswith('final.jpg'))

if __name__ == '__main__': unittest.main()
