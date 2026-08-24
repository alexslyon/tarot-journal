"""
Cartomancy type endpoints (Tarot, Lenormand, Oracle, etc.)
"""

from flask import Blueprint, jsonify, current_app
from backend.utils import row_to_dict, sort_types, require_json, validate_length
from database.core import DEFAULT_TYPE_NAMES

types_bp = Blueprint('types', __name__)


@types_bp.route('/api/types')
def get_types():
    db = current_app.config['DB']
    rows = db.get_cartomancy_types()
    types = [row_to_dict(r) for r in rows]
    for t in types:
        # Built-ins are re-seeded on startup, so the manager UI keeps
        # rename/delete off them.
        t['builtin'] = t['name'] in DEFAULT_TYPE_NAMES
    return jsonify(sort_types(types))


@types_bp.route('/api/types', methods=['POST'])
@require_json
def add_type(data):
    db = current_app.config['DB']
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    err = validate_length(name, field_name='name')
    if err:
        return jsonify({'error': err}), 400
    try:
        type_id = db.add_cartomancy_type(name)
    except Exception:
        return jsonify({'error': f'A type named "{name}" already exists.'}), 400
    return jsonify({'id': type_id, 'name': name}), 201


def _find_type(db, type_id):
    return next(
        (row_to_dict(t) for t in db.get_cartomancy_types()
         if row_to_dict(t)['id'] == type_id), None)


@types_bp.route('/api/types/<int:type_id>', methods=['PUT'])
@require_json
def rename_type(type_id, data):
    db = current_app.config['DB']
    t = _find_type(db, type_id)
    if not t:
        return jsonify({'error': 'Type not found'}), 404
    if t['name'] in DEFAULT_TYPE_NAMES:
        return jsonify({'error': 'Built-in types cannot be renamed — the app '
                                 're-creates them on startup.'}), 400
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    err = validate_length(name, field_name='name')
    if err:
        return jsonify({'error': err}), 400
    if any(row_to_dict(x)['name'] == name for x in db.get_cartomancy_types()):
        return jsonify({'error': f'A type named "{name}" already exists.'}), 400
    db.rename_cartomancy_type(type_id, name)
    return jsonify({'ok': True, 'name': name})


@types_bp.route('/api/types/<int:type_id>', methods=['DELETE'])
def delete_type(type_id):
    db = current_app.config['DB']
    t = _find_type(db, type_id)
    if not t:
        return jsonify({'error': 'Type not found'}), 404
    if t['name'] in DEFAULT_TYPE_NAMES:
        return jsonify({'error': 'Built-in types cannot be deleted — the app '
                                 're-creates them on startup.'}), 400
    deck_count = db.count_decks_for_type(type_id)
    if deck_count:
        return jsonify({'error': f'{deck_count} deck{"s" if deck_count != 1 else ""} '
                                 'still use this type. Reassign or delete them first.'}), 400
    db.delete_cartomancy_type(type_id)
    return jsonify({'ok': True})
