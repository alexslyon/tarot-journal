"""
Archetype Notes endpoints — per-card freeform fields and entries.
"""

from flask import Blueprint, jsonify, request, current_app
from backend.utils import row_to_dict, require_json

archetype_notes_bp = Blueprint('archetype_notes', __name__)


# === Field definitions ===

@archetype_notes_bp.route('/api/archetype-notes/fields')
def list_fields():
    """List all field definitions for a single archetype.
    Query: ?archetype_id=N
    """
    db = current_app.config['DB']
    archetype_id = request.args.get('archetype_id')
    if not archetype_id:
        return jsonify({'error': 'archetype_id required'}), 400
    rows = db.get_archetype_note_fields(int(archetype_id))
    return jsonify([row_to_dict(r) for r in rows])


@archetype_notes_bp.route('/api/archetype-notes/fields', methods=['POST'])
@require_json
def create_field(data):
    db = current_app.config['DB']
    archetype_id = data.get('archetype_id')
    field_name = (data.get('field_name') or '').strip()
    if archetype_id is None or not field_name:
        return jsonify({'error': 'archetype_id and field_name are required'}), 400
    try:
        new_id = db.create_archetype_note_field(int(archetype_id), field_name)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'id': new_id})


@archetype_notes_bp.route('/api/archetype-notes/fields/<int:field_id>', methods=['PUT'])
@require_json
def update_field(field_id, data):
    db = current_app.config['DB']
    field_name = (data.get('field_name') or '').strip()
    if not field_name:
        return jsonify({'error': 'field_name cannot be empty'}), 400
    db.update_archetype_note_field(field_id, field_name)
    return jsonify({'ok': True})


@archetype_notes_bp.route('/api/archetype-notes/fields/<int:field_id>', methods=['DELETE'])
def delete_field(field_id):
    db = current_app.config['DB']
    db.delete_archetype_note_field(field_id)
    return jsonify({'ok': True})


@archetype_notes_bp.route('/api/archetype-notes/fields/<int:field_id>/entry-count')
def field_entry_count(field_id):
    db = current_app.config['DB']
    return jsonify({'count': db.count_archetype_note_field_entries(field_id)})


@archetype_notes_bp.route('/api/archetype-notes/fields/reorder', methods=['POST'])
@require_json
def reorder_fields(data):
    db = current_app.config['DB']
    archetype_id = data.get('archetype_id')
    ordered_ids = data.get('ordered_ids') or []
    if archetype_id is None or not isinstance(ordered_ids, list):
        return jsonify({'error': 'archetype_id and ordered_ids required'}), 400
    db.reorder_archetype_note_fields(int(archetype_id), [int(i) for i in ordered_ids])
    return jsonify({'ok': True})


# === Entries ===

@archetype_notes_bp.route('/api/archetype-notes/entries')
def list_entries():
    """Either ?field_id=N for one field, or ?archetype_id=N for all entries
    on an archetype joined with field metadata.
    """
    db = current_app.config['DB']
    field_id = request.args.get('field_id')
    archetype_id = request.args.get('archetype_id')
    if field_id:
        rows = db.get_archetype_note_entries(int(field_id))
    elif archetype_id:
        rows = db.get_archetype_notes(int(archetype_id))
    else:
        return jsonify({'error': 'field_id or archetype_id required'}), 400
    return jsonify([row_to_dict(r) for r in rows])


@archetype_notes_bp.route('/api/archetype-notes/entries', methods=['POST'])
@require_json
def create_entry(data):
    db = current_app.config['DB']
    field_id = data.get('field_id')
    content = data.get('content', '')
    source_id = data.get('source_id')
    if source_id == '' or source_id is None:
        source_id = None
    else:
        try:
            source_id = int(source_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'source_id must be an integer'}), 400
    if field_id is None:
        return jsonify({'error': 'field_id required'}), 400
    try:
        new_id = db.add_archetype_note_entry(int(field_id), content, source_id)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'id': new_id})


@archetype_notes_bp.route('/api/archetype-notes/entries/<int:entry_id>', methods=['PUT'])
@require_json
def update_entry(entry_id, data):
    db = current_app.config['DB']
    content = data.get('content')
    clear_source = False
    source_id = data.get('source_id', '__missing__')
    if source_id is None:
        clear_source = True
        source_id = None
    elif source_id == '__missing__':
        source_id = None
    else:
        try:
            source_id = int(source_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'source_id must be an integer or null'}), 400
    db.update_archetype_note_entry(
        entry_id,
        content=content,
        source_id=source_id,
        clear_source=clear_source,
    )
    return jsonify({'ok': True})


@archetype_notes_bp.route('/api/archetype-notes/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    db = current_app.config['DB']
    db.delete_archetype_note_entry(entry_id)
    return jsonify({'ok': True})


@archetype_notes_bp.route('/api/archetype-notes/entries/reorder', methods=['POST'])
@require_json
def reorder_entries(data):
    db = current_app.config['DB']
    field_id = data.get('field_id')
    ordered_ids = data.get('ordered_ids') or []
    if field_id is None or not isinstance(ordered_ids, list):
        return jsonify({'error': 'field_id and ordered_ids required'}), 400
    db.reorder_archetype_note_entries(int(field_id), [int(i) for i in ordered_ids])
    return jsonify({'ok': True})
