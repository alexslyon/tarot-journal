"""
Anki export endpoint -- generates a zip file with tab-separated card data
and images that can be imported directly into Anki.
"""

import io
import os
import zipfile

from flask import Blueprint, current_app, request, send_file, jsonify
from backend.utils import require_json

anki_export_bp = Blueprint('anki_export', __name__)

# Display labels for correspondence fields (matches frontend labels)
FIELD_LABELS = {
    'element': 'Element',
    'planet': 'Planet',
    'zodiac_sign': 'Zodiac Sign',
    'decan': 'Decan',
    'hebrew_letter': 'Kabbalah',
    'numerology': 'Numerology',
    'rune': 'Rune',
    'i_ching_hexagram': 'I Ching Hexagram',
    'chakra': 'Chakra',
}


@anki_export_bp.route('/api/decks/<int:deck_id>/anki-export', methods=['POST'])
@require_json
def anki_export(deck_id, data):
    """Export a deck as an Anki-importable zip.

    Request body:
        fields: list of field keys in export order
            Available keys: 'image', 'name', 'element', 'planet', 'zodiac_sign',
            'decan', 'hebrew_letter', 'numerology', 'rune', 'i_ching_hexagram',
            'chakra', 'notes', plus any custom field names.

    Response: zip file containing:
        - cards.txt: tab-separated file with Anki directives
        - card images (flat, referenced by filename in the txt)
    """
    db = current_app.config['DB']

    deck = db.get_deck(deck_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404

    fields = data.get('fields', [])
    if not fields:
        return jsonify({'error': 'No fields selected'}), 400

    # Get all cards in the deck
    cards = db.get_cards(deck_id)
    if not cards:
        return jsonify({'error': 'Deck has no cards'}), 400

    # Get correspondences for all cards
    card_correspondences = {}
    for card in cards:
        card_correspondences[card['id']] = {
            c['field_name']: c['value']
            for c in db.get_card_correspondences(card['id'])
            if c['value']
        }

    # Get custom fields for all cards
    card_custom_fields = {}
    for card in cards:
        cursor = db.conn.cursor()
        cursor.execute(
            'SELECT field_name, field_value FROM card_custom_fields WHERE card_id = ?',
            (card['id'],)
        )
        card_custom_fields[card['id']] = {
            r['field_name']: r['field_value'] for r in cursor.fetchall()
        }

    # Correspondence field names (for detecting which fields are correspondences)
    from database.correspondences import CORRESPONDENCE_FIELDS

    # Build the zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Build tab-separated text file
        lines = []
        lines.append('#separator:tab')
        lines.append('#html:true')

        # Header comment with field names
        header_labels = []
        for f in fields:
            if f == 'image':
                header_labels.append('Card Image')
            elif f == 'name':
                header_labels.append('Card Name')
            elif f == 'notes':
                header_labels.append('Notes')
            elif f in CORRESPONDENCE_FIELDS:
                header_labels.append(FIELD_LABELS.get(f, f.replace('_', ' ').title()))
            else:
                header_labels.append(f)
        lines.append('#' + '\t'.join(header_labels))

        image_files = {}  # filename -> absolute path on disk

        for card in cards:
            corr = card_correspondences.get(card['id'], {})
            custom = card_custom_fields.get(card['id'], {})
            row = []

            for f in fields:
                if f == 'image':
                    if card.get('image_path') and os.path.isfile(card['image_path']):
                        # Use a safe filename
                        ext = os.path.splitext(card['image_path'])[1] or '.jpg'
                        safe_name = f"card_{card['id']}{ext}"
                        image_files[safe_name] = card['image_path']
                        row.append(f'<img src="{safe_name}">')
                    else:
                        row.append('')
                elif f == 'name':
                    row.append(card.get('name', ''))
                elif f == 'notes':
                    row.append(card.get('notes', '') or '')
                elif f in CORRESPONDENCE_FIELDS:
                    row.append(corr.get(f, ''))
                else:
                    # Custom field
                    row.append(custom.get(f, ''))

            lines.append('\t'.join(row))

        # Write the text file
        zf.writestr('cards.txt', '\n'.join(lines))

        # Write image files
        for filename, filepath in image_files.items():
            zf.write(filepath, filename)

    buf.seek(0)

    safe_deck_name = ''.join(c for c in deck['name'] if c.isalnum() or c in ' -_').strip()
    download_name = f"{safe_deck_name}_anki.zip"

    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name,
    )


@anki_export_bp.route('/api/decks/<int:deck_id>/anki-fields')
def anki_fields(deck_id):
    """Get available fields for Anki export for a given deck.

    Returns fields in recommended order with metadata about which are populated.
    """
    db = current_app.config['DB']

    deck = db.get_deck(deck_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404

    from database.correspondences import CORRESPONDENCE_FIELDS

    # Always-available fields
    fields = [
        {'key': 'image', 'label': 'Card Image', 'always': True},
        {'key': 'name', 'label': 'Card Name', 'always': True},
    ]

    # Check which correspondence fields have any values in this deck
    cards = db.get_cards(deck_id)
    corr_populated = set()
    for card in cards[:10]:  # Sample first 10 cards for speed
        for c in db.get_card_correspondences(card['id']):
            if c['value']:
                corr_populated.add(c['field_name'])

    for f in CORRESPONDENCE_FIELDS:
        label = FIELD_LABELS.get(f, f.replace('_', ' ').title())
        fields.append({
            'key': f,
            'label': label,
            'always': False,
            'populated': f in corr_populated,
        })

    # Notes
    fields.append({'key': 'notes', 'label': 'Notes', 'always': False})

    # Custom fields defined for this deck
    cursor = db.conn.cursor()
    cursor.execute(
        'SELECT field_name FROM deck_custom_fields WHERE deck_id = ? ORDER BY field_order',
        (deck_id,)
    )
    for row in cursor.fetchall():
        fields.append({
            'key': row['field_name'],
            'label': row['field_name'],
            'always': False,
        })

    return jsonify(fields)
