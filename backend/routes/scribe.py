"""
Scribe routes — importing external sources into reference data.

Two halves:
  - POST /api/scribe/extract-text  — turn an uploaded ebook/text file
    into plain text (images are handled entirely in the frontend)
  - POST /api/scribe/apply         — write reviewed proposals in one
    batch: archetype source entries and/or card custom fields
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from backend.services import source_text

scribe_bp = Blueprint('scribe', __name__)

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # a whole book is a few MB; 100 MB is generous


@scribe_bp.route('/api/scribe/extract-text', methods=['POST'])
def extract_text():
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'error': 'No file uploaded'}), 400
    data = file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return jsonify({'error': 'File is too large (over 100 MB).'}), 413
    try:
        result = source_text.extract_text(file.filename, data)
    except source_text.ExtractionError as e:
        return jsonify({'error': str(e)}), 422
    return jsonify({
        'filename': file.filename,
        'text': result['text'],
        'char_count': len(result['text']),
        'warning': result['warning'],
    })


@scribe_bp.route('/api/scribe/apply', methods=['POST'])
def apply_proposals():
    """Write a reviewed batch of proposals.

    Body: {"writes": [
        {"target": "archetype", "archetype_id": 1, "field_id": 2, "content": "..."},
        {"target": "card", "card_id": 5, "field_name": "Keywords", "content": "..."}
    ]}

    Card writes upsert by field name: update the card's existing custom
    field if one has that name, otherwise create it (type "text").
    """
    db = current_app.config['DB']
    data = request.get_json() or {}
    writes = data.get('writes') or []
    if not writes:
        return jsonify({'error': 'writes is required'}), 400

    applied = 0
    errors = []
    for i, w in enumerate(writes):
        try:
            target = w.get('target')
            content = (w.get('content') or '').strip()
            if target == 'archetype':
                db.set_source_entry(int(w['archetype_id']), int(w['field_id']), content)
            elif target == 'card':
                _upsert_card_field(db, int(w['card_id']), w['field_name'], content)
            else:
                raise ValueError(f"unknown target {target!r}")
            applied += 1
        except Exception as e:  # keep going; report per-row failures
            errors.append({'index': i, 'error': str(e)})

    return jsonify({'applied': applied, 'errors': errors})


def _upsert_card_field(db, card_id: int, field_name: str, content: str):
    if not field_name or not field_name.strip():
        raise ValueError('field_name is required')
    field_name = field_name.strip()
    _ensure_deck_field_definition(db, card_id, field_name)
    existing = db.get_card_custom_fields(card_id)
    match = next(
        (dict(f) for f in existing
         if (f['field_name'] or '').strip().lower() == field_name.lower()),
        None,
    )
    if match:
        db.update_card_custom_field(match['id'], field_value=content)
    else:
        db.add_card_custom_field(card_id, field_name=field_name,
                                 field_type='text', field_value=content)


def _ensure_deck_field_definition(db, card_id: int, field_name: str):
    """A brand-new imported field name gets a deck-level definition, so
    it shows up in the deck editor's Custom Fields list and on every
    card — not just the ones the import happened to write."""
    card = db.get_card(card_id)
    card = dict(card) if card else None
    if not card or not card.get('deck_id'):
        return
    deck_id = card['deck_id']
    defs = db.get_deck_custom_fields(deck_id)
    if any((d['field_name'] or '').strip().lower() == field_name.lower()
           for d in defs):
        return
    db.add_deck_custom_field(deck_id, field_name=field_name,
                             field_type='text', field_order=len(defs))
