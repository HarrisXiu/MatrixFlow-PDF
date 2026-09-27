import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject, ArrayObject, FloatObject
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pypdfium2 as pdfium

from blank_pages import remove_blank_pages


class BlankPageTests(unittest.TestCase):
    def test_visual_detection_preserves_sparse_and_annotated_content(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'mixed.pdf'
            output = Path(folder) / 'clean.pdf'
            c = canvas.Canvas(str(source), pagesize=(300, 400))
            c.showPage()  # 1: truly blank
            c.drawString(20, 200, 'Content'); c.showPage()  # 2: text
            c.setFillColorRGB(1, 1, 1); c.rect(0, 0, 300, 400, fill=1, stroke=0); c.showPage()  # 3: white drawing
            c.setLineWidth(.2); c.line(20, 200, 80, 200); c.showPage()  # 4: thin line
            c.rect(100, 100, 1, 1, fill=1, stroke=0); c.showPage()  # 5: tiny mark
            c.drawImage(ImageReader(Image.new('RGB', (300, 400), 'white')), 0, 0, 300, 400); c.showPage()  # 6: white scan
            c.setFillColorRGB(.98, .98, .98); c.drawString(20, 200, 'Faint text'); c.showPage()  # 7
            c.setFillColorRGB(1, 1, 0); c.rect(20, 20, 5, 5, fill=1, stroke=0); c.showPage()  # 8: yellow mark
            c.drawImage(ImageReader(Image.new('RGB', (300, 400), (245, 245, 245))), 0, 0, 300, 400); c.showPage()  # 9: uncertain scan
            c.showPage(); c.save()  # 10: annotation added below
            writer = PdfWriter(clone_from=source)
            writer.add_annotation(9, DictionaryObject({
                NameObject('/Type'): NameObject('/Annot'), NameObject('/Subtype'): NameObject('/Text'),
                NameObject('/Contents'): TextStringObject('Keep this note'),
                NameObject('/Rect'): ArrayObject([FloatObject(n) for n in (20, 20, 40, 40)]),
            }))
            with source.open('wb') as stream: writer.write(stream)
            original = source.read_bytes()
            result, removed = remove_blank_pages(str(source), str(output))
            self.assertEqual(removed, [1, 3, 6])
            self.assertEqual(result, str(output))
            self.assertEqual(len(PdfReader(output).pages), 7)
            self.assertEqual(source.read_bytes(), original)

    def test_all_blank_render_failure_and_cancellation(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'blank.pdf', Path(folder)/'out.pdf'
            writer = PdfWriter(); writer.add_blank_page(width=300, height=400)
            with source.open('wb') as stream: writer.write(stream)
            self.assertEqual(remove_blank_pages(str(source), str(output)), (None, [1]))
            self.assertFalse(output.exists())
            warnings = []
            with patch.object(pdfium.PdfPage, 'render', side_effect=RuntimeError('render failed')):
                self.assertEqual(remove_blank_pages(str(source), str(output), on_warning=warnings.append), (str(source), []))
            self.assertTrue(warnings)
            cancelled = threading.Event(); cancelled.set()
            with self.assertRaises(InterruptedError):
                remove_blank_pages(str(source), str(output), cancelled)
