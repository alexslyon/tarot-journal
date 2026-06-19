"""
Journal entry PDF export. Phase 1: header, spread image (HTML/CSS
positioned), position key, journal notes, follow-up notes.

The pipeline:
  1. Hydrate the entry the same way GET /api/entries/<id> does.
  2. Build a render-context dict for Jinja2 — flattens DB rows and
     pre-resolves card image absolute paths so WeasyPrint can pull
     them off disk.
  3. Render the print template + CSS.
  4. WeasyPrint converts the HTML to a PDF and we stream it back.

WeasyPrint's HTML/CSS support handles the rich-text content
(TipTap stores HTML already) and the absolute-positioned spread
layout without us reconstructing anything in low-level drawing
primitives.
"""

# PEP 604 union syntax (str | None) for type annotations on this
# Python 3.9 venv.
from __future__ import annotations

import json
import logging
import re
from io import BytesIO
from pathlib import Path

from flask import Blueprint, current_app, request, send_file, abort, jsonify

from backend.utils import row_to_dict


logger = logging.getLogger(__name__)

pdf_export_bp = Blueprint('pdf_export', __name__)

# Resolved at import time so the Jinja2 + CSS files travel with the
# backend package.
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / 'pdf_templates'


def _file_uri(path: str, cache=None) -> str | None:
    """Convert a card's stored image_path (possibly relative to the
    project root) into a file:// URI WeasyPrint can embed.

    When a thumbnail cache is provided, prefer the cached PREVIEW
    rendition (~500x750) over the original. Card scans are often
    several MB each; for an A4 print the preview is plenty crisp
    and keeps the resulting PDF small enough to share.
    """
    if not path:
        return None
    if cache is not None:
        try:
            preview_path = cache.get_thumbnail_path(path, size=cache.PREVIEW_SIZE)
        except Exception:
            preview_path = None
        if preview_path:
            p = Path(preview_path)
            if p.exists():
                return p.as_uri()
    # Fallback: stream the original.
    p = Path(path)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parent.parent.parent / p).resolve()
    if not p.exists():
        return None
    return p.as_uri()


def _safe_filename(stem: str) -> str:
    """Sanitize an entry title for use in the download filename.
    Drops anything other than alphanumerics, dash, and underscore."""
    cleaned = re.sub(r'[^A-Za-z0-9_-]+', '_', stem).strip('_')
    return cleaned or 'journal_entry'


def _parse_cards_used(raw):
    """Mirror of routes/entries.py's _parse_cards_used so we get the
    same shape (list of dicts with name + reversed + position_index +
    card_id) from the JSON the DB stores."""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except (TypeError, ValueError):
        pass
    return []


def _hydrate_entry_for_pdf(db, entry_id: int, cache=None) -> dict | None:
    """Return the entry as a dict ready for the Jinja2 template, or
    None if it doesn't exist. Card images are resolved to absolute
    file:// URIs so WeasyPrint can load them directly (preferring
    the cached preview rendition). Spreads are fetched once each,
    keyed by id, and attached to their reading."""
    row = db.get_entry(entry_id)
    if not row:
        return None
    entry = row_to_dict(row)
    entry['content_html'] = entry.get('content') or ''

    readings_rows = db.get_entry_readings(entry_id)
    spread_cache: dict[int, dict] = {}
    readings: list[dict] = []
    for r in readings_rows:
        rd = row_to_dict(r)
        # Hydrate each card with image URI + card_id-driven lookups.
        cards = _parse_cards_used(rd.get('cards_used'))
        hydrated_cards = []
        for c in cards:
            card_id = c.get('card_id')
            card_row = db.get_card(card_id) if card_id else None
            card = dict(card_row) if card_row else {}
            hydrated_cards.append({
                'name': c.get('name') or (card.get('name') if card else ''),
                'reversed': bool(c.get('reversed')),
                'position_index': c.get('position_index'),
                'card_id': card_id,
                'image_uri': _file_uri(card.get('image_path'), cache) if card else None,
            })
        rd['cards_used'] = hydrated_cards

        # Spread definition for the visual layout.
        spread = None
        if rd.get('spread_id'):
            sid = rd['spread_id']
            if sid not in spread_cache:
                sp_row = db.get_spread(sid)
                if sp_row:
                    sp = row_to_dict(sp_row)
                    positions = sp.get('positions')
                    if isinstance(positions, str):
                        try:
                            positions = json.loads(positions)
                        except (TypeError, ValueError):
                            positions = []
                    sp['positions'] = positions or []
                    spread_cache[sid] = sp
            spread = spread_cache.get(sid)
        rd['spread'] = spread
        readings.append(rd)
    entry['readings'] = readings

    tags = db.get_entry_tags(entry_id)
    entry['tags'] = [row_to_dict(t) for t in tags]

    follow_ups = db.get_follow_up_notes(entry_id)
    entry['follow_up_notes'] = [row_to_dict(n) for n in follow_ups]

    querents = db.get_entry_querents(entry_id)
    entry['querents'] = [row_to_dict(q) for q in querents]
    if entry.get('querent_id'):
        q = db.get_profile(entry['querent_id'])
        entry['querent_name'] = q['name'] if q else None
    if entry.get('reader_id'):
        rp = db.get_profile(entry['reader_id'])
        entry['reader_name'] = rp['name'] if rp else None

    return entry


def _select_readings(entry: dict, ids: list[int] | None) -> dict:
    """If the request specified a readings subset, filter the entry's
    readings list to just those ids. Mutates and returns the entry."""
    if not ids:
        return entry
    keep = set(int(i) for i in ids)
    entry['readings'] = [r for r in entry['readings'] if int(r['id']) in keep]
    return entry


@pdf_export_bp.route('/api/entries/<int:entry_id>/export-pdf', methods=['POST'])
def export_pdf(entry_id):
    """Generate a PDF for a journal entry. Phase 1 honors only the
    readings selection from the request body — the other toggles
    listed in PLANNING_PDF_EXPORT.md are placeholders for later
    phases. Returns the PDF as an attachment download."""
    # Local imports so a missing weasyprint install fails on POST
    # (with a clear 500), not on app startup.
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from weasyprint import HTML, CSS

    db = current_app.config['DB']
    cache = current_app.config.get('THUMB_CACHE')
    body = request.get_json(silent=True) or {}

    entry = _hydrate_entry_for_pdf(db, entry_id, cache=cache)
    if entry is None:
        return jsonify({'error': 'Entry not found'}), 404

    _select_readings(entry, body.get('readings'))
    if not entry['readings']:
        # The doc says the modal requires at least one reading; this
        # is a backstop for the API path.
        return jsonify({'error': 'At least one reading must be selected'}), 400

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(['html']),
    )
    template = env.get_template('entry_export.html')
    html_str = template.render(entry=entry)

    css_path = _TEMPLATE_DIR / 'entry_export.css'
    try:
        pdf_bytes = HTML(string=html_str, base_url=str(_TEMPLATE_DIR)).write_pdf(
            stylesheets=[CSS(filename=str(css_path))],
        )
    except Exception as e:
        logger.exception('PDF export failed for entry %s: %s', entry_id, e)
        return jsonify({'error': f'PDF generation failed: {e}'}), 500

    title_stem = entry.get('title') or f'entry_{entry_id}'
    date_part = (entry.get('reading_datetime') or entry.get('created_at') or '')[:10]
    filename = f'{_safe_filename(title_stem)}_{date_part}.pdf' if date_part \
        else f'{_safe_filename(title_stem)}.pdf'

    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )
