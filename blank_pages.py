"""Conservative blank-page detection without changing source documents."""
import threading
from contextlib import closing

from PIL import ImageChops
from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium


_RENDER_LOCK = threading.Lock()


def remove_blank_pages(source, destination, cancel=None, on_warning=None):
    """Return (usable PDF path or None, removed 1-based page numbers).

    Text, annotations and forms always keep a page. Other pages must render
    entirely white/near-white in every color channel. Ambiguous/render-failed
    pages are retained; this intentionally does not erase noisy scan pages.
    """
    reader = PdfReader(source)
    removed = []
    with _RENDER_LOCK, pdfium.PdfDocument(source) as document:
        if len(document) != len(reader.pages):
            raise ValueError('PDF page counts disagree; blank-page removal stopped')
        for index, original in enumerate(reader.pages):
            if cancel is not None and cancel.is_set():
                raise InterruptedError('Blank-page detection cancelled')
            try:
                if original.get('/Annots') or (original.extract_text() or '').strip():
                    continue
                with closing(document[index]) as page:
                    width, height = page.get_size()
                    # Keep unusually large pages rather than downsample away small marks.
                    if width <= 0 or height <= 0 or width * height * 2.25 > 8_000_000:
                        continue
                    bitmap = page.render(scale=1.5, draw_annots=True)
                    try:
                        image = bitmap.to_pil().convert('RGB')
                        red, green, blue = image.split()
                        darkest = ImageChops.darker(ImageChops.darker(red, green), blue)
                        if darkest.getextrema()[0] >= 252:
                            removed.append(index + 1)
                    finally:
                        bitmap.close()
            except Exception as exc:
                if on_warning:
                    on_warning(f'空白页识别：第 {index + 1} 页无法确认，已保留（{exc}）')
    if cancel is not None and cancel.is_set():
        raise InterruptedError('Blank-page detection cancelled')
    if not removed:
        return source, removed
    if len(removed) == len(reader.pages):
        return None, removed
    writer = PdfWriter()
    excluded = set(removed)
    for number, page in enumerate(reader.pages, 1):
        if number not in excluded:
            writer.add_page(page)
    with open(destination, 'wb') as stream:
        writer.write(stream)
    return destination, removed
