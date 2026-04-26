"""
Archetype Languages endpoints — managed language list and per-archetype names.
"""

from flask import Blueprint, jsonify, request, current_app
from backend.utils import row_to_dict, require_json

archetype_languages_bp = Blueprint('archetype_languages', __name__)


# === Languages ===

@archetype_languages_bp.route('/api/archetype-languages')
def list_languages():
    db = current_app.config['DB']
    rows = db.get_archetype_languages()
    return jsonify([row_to_dict(r) for r in rows])


@archetype_languages_bp.route('/api/archetype-languages', methods=['POST'])
@require_json
def create_language(data):
    db = current_app.config['DB']
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    try:
        new_id = db.create_archetype_language(name)
    except Exception as e:
        return jsonify({'error': f'Could not create language: {e}'}), 400
    return jsonify({'id': new_id})


@archetype_languages_bp.route('/api/archetype-languages/<int:language_id>', methods=['PUT'])
@require_json
def update_language(language_id, data):
    db = current_app.config['DB']
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    db.update_archetype_language(language_id, name)
    return jsonify({'ok': True})


@archetype_languages_bp.route('/api/archetype-languages/<int:language_id>', methods=['DELETE'])
def delete_language(language_id):
    db = current_app.config['DB']
    db.delete_archetype_language(language_id)
    return jsonify({'ok': True})


@archetype_languages_bp.route('/api/archetype-languages/<int:language_id>/dependency-count')
def dependency_count(language_id):
    db = current_app.config['DB']
    return jsonify({'count': db.count_archetype_language_names(language_id)})


@archetype_languages_bp.route('/api/archetype-languages/reorder', methods=['POST'])
@require_json
def reorder_languages(data):
    db = current_app.config['DB']
    ordered_ids = data.get('ordered_ids') or []
    if not isinstance(ordered_ids, list):
        return jsonify({'error': 'ordered_ids list required'}), 400
    db.reorder_archetype_languages([int(i) for i in ordered_ids])
    return jsonify({'ok': True})


# === Names ===

@archetype_languages_bp.route('/api/archetype-language-names')
def list_names():
    """Either ?archetype_id=N for one card, or ?cartomancy_type=Tarot for all."""
    db = current_app.config['DB']
    archetype_id = request.args.get('archetype_id')
    cartomancy_type = request.args.get('cartomancy_type')
    if archetype_id:
        rows = db.get_archetype_names(int(archetype_id))
    elif cartomancy_type:
        rows = db.get_archetype_names_for_type(cartomancy_type)
    else:
        return jsonify({'error': 'archetype_id or cartomancy_type required'}), 400
    return jsonify([row_to_dict(r) for r in rows])


@archetype_languages_bp.route('/api/archetype-language-names', methods=['POST'])
@require_json
def create_name(data):
    db = current_app.config['DB']
    archetype_id = data.get('archetype_id')
    language_id = data.get('language_id')
    name = (data.get('name') or '').strip()
    romanization = data.get('romanization')
    ipa = data.get('ipa')
    if archetype_id is None or language_id is None or not name:
        return jsonify({'error': 'archetype_id, language_id, and name are required'}), 400
    try:
        new_id = db.add_archetype_name(
            int(archetype_id), int(language_id), name,
            romanization=romanization, ipa=ipa,
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'id': new_id})


@archetype_languages_bp.route('/api/archetype-language-names/<int:name_id>', methods=['PUT'])
@require_json
def update_name(name_id, data):
    db = current_app.config['DB']
    name = data.get('name')
    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'error': 'name cannot be empty'}), 400

    romanization = data.get('romanization', '__missing__')
    clear_romanization = romanization is None
    if romanization == '__missing__':
        romanization = None

    ipa = data.get('ipa', '__missing__')
    clear_ipa = ipa is None
    if ipa == '__missing__':
        ipa = None

    db.update_archetype_name(
        name_id,
        name=name,
        romanization=romanization if not clear_romanization else None,
        ipa=ipa if not clear_ipa else None,
        clear_romanization=clear_romanization,
        clear_ipa=clear_ipa,
    )
    return jsonify({'ok': True})


@archetype_languages_bp.route('/api/archetype-language-names/<int:name_id>', methods=['DELETE'])
def delete_name(name_id):
    db = current_app.config['DB']
    db.delete_archetype_name(name_id)
    return jsonify({'ok': True})


@archetype_languages_bp.route('/api/archetype-language-names/reorder', methods=['POST'])
@require_json
def reorder_names(data):
    """Reorder names within a single (archetype, language) group."""
    db = current_app.config['DB']
    archetype_id = data.get('archetype_id')
    language_id = data.get('language_id')
    ordered_ids = data.get('ordered_ids') or []
    if archetype_id is None or language_id is None or not isinstance(ordered_ids, list):
        return jsonify({'error': 'archetype_id, language_id, and ordered_ids are required'}), 400
    db.reorder_archetype_names(
        int(archetype_id), int(language_id), [int(i) for i in ordered_ids],
    )
    return jsonify({'ok': True})
