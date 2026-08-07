"""
Text extraction from source files for the Scribe.

Turns an uploaded book file into plain text the LLM can read:

  .epub          → unzip, read the spine's HTML files in order
  .pdf           → text-layer extraction via pypdf (a scanned PDF with
                   no text layer gets a warning instead of silence)
  .mobi / .azw*  → unpack with the mobi library, then treat the result
                   as EPUB or HTML
  .txt / .md     → decoded as-is
  .html / .htm   → tags stripped

Images never come through here — the frontend reads those directly and
sends them to vision models as image parts.
"""

from __future__ import annotations

import html as html_mod
import io
import os
import re
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET


class ExtractionError(Exception):
    """Extraction failed; .args[0] is a user-readable message."""


EBOOK_EXTENSIONS = ('.epub', '.pdf', '.mobi', '.azw', '.azw3',
                    '.txt', '.md', '.html', '.htm')


def extract_text(filename: str, data: bytes) -> dict:
    """Returns {'text': str, 'warning': str | None}."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.epub':
        return _extract_epub(data)
    if ext == '.pdf':
        return _extract_pdf(data)
    if ext in ('.mobi', '.azw', '.azw3'):
        return _extract_mobi(data, ext)
    if ext in ('.txt', '.md'):
        return {'text': data.decode('utf-8', errors='replace').strip(),
                'warning': None}
    if ext in ('.html', '.htm'):
        return {'text': _strip_html(data.decode('utf-8', errors='replace')),
                'warning': None}
    raise ExtractionError(
        f"Unsupported file type '{ext}'. Supported: EPUB, PDF, MOBI/AZW, "
        "plain text, and HTML — or use photos for image-based sources."
    )


# ── HTML flattening ──────────────────────────────────────────────────

def _strip_html(raw: str) -> str:
    s = raw
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', s, flags=re.I | re.S)
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</p>\s*<p[^>]*>', '\n\n', s, flags=re.I)
    s = re.sub(r'<li[^>]*>', '\n- ', s, flags=re.I)
    s = re.sub(r'</(p|div|ul|ol|li|h[1-6]|blockquote|tr|table|section|article)>',
               '\n', s, flags=re.I)
    s = re.sub(r'<h([1-6])[^>]*>', '\n\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = html_mod.unescape(s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


# ── EPUB ─────────────────────────────────────────────────────────────

def _extract_epub(data: bytes) -> dict:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ExtractionError("This EPUB file appears to be corrupted (not a valid zip).")
    with zf:
        docs = _epub_spine_documents(zf)
        if docs is None:
            # Malformed metadata — fall back to every HTML file in
            # archive order rather than failing outright.
            docs = [n for n in zf.namelist()
                    if n.lower().endswith(('.xhtml', '.html', '.htm'))]
            warning = ("The book's chapter order metadata couldn't be read; "
                       "chapters may appear out of order.")
        else:
            warning = None
        chunks = []
        for name in docs:
            try:
                raw = zf.read(name).decode('utf-8', errors='replace')
            except KeyError:
                continue
            text = _strip_html(raw)
            if text:
                chunks.append(text)
    if not chunks:
        raise ExtractionError("No readable text found inside this EPUB.")
    return {'text': '\n\n'.join(chunks), 'warning': warning}


def _epub_spine_documents(zf: zipfile.ZipFile):
    """Reading-order document paths from the OPF, or None if unparseable."""
    try:
        container = ET.fromstring(zf.read('META-INF/container.xml'))
        ns = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container'}
        opf_path = container.find('.//c:rootfile', ns).get('full-path')
        opf_dir = os.path.dirname(opf_path)
        opf = ET.fromstring(zf.read(opf_path))
        ns = {'o': 'http://www.idpf.org/2007/opf'}
        manifest = {
            item.get('id'): item.get('href')
            for item in opf.findall('.//o:manifest/o:item', ns)
        }
        docs = []
        for itemref in opf.findall('.//o:spine/o:itemref', ns):
            href = manifest.get(itemref.get('idref'))
            if href:
                path = f"{opf_dir}/{href}" if opf_dir else href
                docs.append(path.replace('%20', ' '))
        return docs or None
    except Exception:
        return None


# ── PDF ──────────────────────────────────────────────────────────────

def _extract_pdf(data: bytes) -> dict:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or '' for page in reader.pages]
    except Exception:
        raise ExtractionError("This PDF couldn't be read — it may be corrupted or encrypted.")
    text = '\n\n'.join(p.strip() for p in pages if p.strip())
    if len(text) < 200:
        # Nearly-empty text layer → almost certainly a scan. Render
        # the pages to images so the vision model can read them —
        # exactly what we used to ask the user to do by hand.
        images = _rasterize_pdf(data, len(reader.pages))
        page_word = 'page' if len(images) == 1 else 'pages'
        warning = (
            f"No text layer (scanned PDF) — converted {len(images)} "
            f"{page_word} to images for the vision model to read."
        )
        if len(reader.pages) > MAX_SCAN_PAGES:
            warning += (
                f" Only the first {MAX_SCAN_PAGES} of {len(reader.pages)} "
                "pages were converted — split the PDF for the rest."
            )
        return {'text': '', 'images': images, 'warning': warning}
    warning = None
    if len(text) < 100 * len(pages):
        warning = ("This PDF's text layer looks sparse — some pages may be "
                   "scanned images the extraction can't read.")
    return {'text': text, 'warning': warning}


# Cap on scanned pages rendered per PDF: keeps a pathological upload
# from ballooning into gigabytes of page images in one response.
MAX_SCAN_PAGES = 500

# The Flask process inherits Electron's minimal PATH, which usually
# lacks Homebrew's bin — check the usual install spots directly.
_PDFTOPPM_CANDIDATES = (
    'pdftoppm',
    '/opt/homebrew/bin/pdftoppm',
    '/usr/local/bin/pdftoppm',
)


def _find_pdftoppm() -> str | None:
    import shutil
    for candidate in _PDFTOPPM_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def _rasterize_pdf(data: bytes, page_count: int) -> list:
    """Render a scanned PDF's pages to JPEGs via poppler's pdftoppm.
    Returns [{'data': <b64>, 'media_type': 'image/jpeg'}, ...] in page
    order. Raises ExtractionError (with the manual-workaround advice)
    when pdftoppm isn't installed or fails."""
    import base64
    import glob
    import subprocess
    import tempfile

    manual_advice = (
        "This PDF has no text layer (it's likely scanned images). "
        "Try photographing or screenshotting the pages and adding "
        "them as images instead — vision models can read those."
    )
    pdftoppm = _find_pdftoppm()
    if not pdftoppm:
        raise ExtractionError(manual_advice)

    last_page = min(page_count, MAX_SCAN_PAGES)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'in.pdf')
            with open(src, 'wb') as f:
                f.write(data)
            # 150 dpi puts a letter page at ~1275×1650 px — plenty for
            # reading text, well under the Scribe's image size cap.
            subprocess.run(
                [pdftoppm, '-jpeg', '-r', '150', '-jpegopt', 'quality=80',
                 '-f', '1', '-l', str(last_page), src,
                 os.path.join(tmp, 'page')],
                check=True, capture_output=True, timeout=600,
            )
            images = []
            for path in sorted(glob.glob(os.path.join(tmp, 'page-*.jpg'))):
                with open(path, 'rb') as f:
                    images.append({
                        'data': base64.b64encode(f.read()).decode('ascii'),
                        'media_type': 'image/jpeg',
                    })
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError(manual_advice)
    if not images:
        raise ExtractionError(manual_advice)
    return images


# ── MOBI / AZW ───────────────────────────────────────────────────────

def _extract_mobi(data: bytes, ext: str) -> dict:
    import mobi

    tmpdir = None
    src = None
    try:
        fd, src = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        try:
            tmpdir, out_path = mobi.extract(src)
        except Exception:
            raise ExtractionError(
                "This MOBI/AZW file couldn't be unpacked. Converting it to "
                "EPUB (Calibre does this well) and importing that usually works."
            )
        with open(out_path, 'rb') as f:
            out_data = f.read()
        lower = out_path.lower()
        if lower.endswith('.epub'):
            return _extract_epub(out_data)
        if lower.endswith(('.html', '.htm', '.xhtml')):
            text = _strip_html(out_data.decode('utf-8', errors='replace'))
            if not text:
                raise ExtractionError("No readable text found inside this MOBI file.")
            return {'text': text, 'warning': None}
        if lower.endswith('.pdf'):
            return _extract_pdf(out_data)
        raise ExtractionError(
            "This MOBI file unpacked to an unexpected format. Converting it "
            "to EPUB with Calibre and importing that should work."
        )
    finally:
        if src and os.path.exists(src):
            os.unlink(src)
        if tmpdir and os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)
