"""
Lenormand combination endpoints -- CRUD for sources, combinations, and meanings.
"""

from flask import Blueprint, jsonify, request, current_app
from backend.utils import row_to_dict, require_json

lenormand_bp = Blueprint('lenormand_combinations', __name__)


# === Sources ===

@lenormand_bp.route('/api/lenormand/sources')
def list_sources():
    db = current_app.config['DB']
    rows = db.get_lenormand_sources()
    return jsonify([row_to_dict(r) for r in rows])


@lenormand_bp.route('/api/lenormand/sources', methods=['POST'])
@require_json
def create_source(data):
    db = current_app.config['DB']
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    try:
        new_id = db.create_lenormand_source(name)
    except Exception as e:
        # UNIQUE constraint violation falls through here as a generic error.
        return jsonify({'error': f'Could not create source: {e}'}), 400
    return jsonify({'id': new_id})


@lenormand_bp.route('/api/lenormand/sources/<int:source_id>', methods=['PUT'])
@require_json
def update_source(source_id, data):
    db = current_app.config['DB']
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    db.update_lenormand_source(source_id, name)
    return jsonify({'ok': True})


@lenormand_bp.route('/api/lenormand/sources/<int:source_id>', methods=['DELETE'])
def delete_source(source_id):
    """Delete a source. Optional ?reassign_to=<id> reassigns dependent meanings;
    omitting it sets them to unsourced.
    """
    db = current_app.config['DB']
    reassign_to = request.args.get('reassign_to')
    reassign_id = int(reassign_to) if reassign_to else None
    db.delete_lenormand_source(source_id, reassign_to=reassign_id)
    return jsonify({'ok': True})


# === Meanings (combination-keyed) ===

@lenormand_bp.route('/api/lenormand/meanings')
def list_meanings():
    """Get all meanings for a card pair. Query params: card_1, card_2."""
    db = current_app.config['DB']
    try:
        card_1 = int(request.args.get('card_1', ''))
        card_2 = int(request.args.get('card_2', ''))
    except (TypeError, ValueError):
        return jsonify({'error': 'card_1 and card_2 are required integers'}), 400
    rows = db.get_lenormand_meanings(card_1, card_2)
    return jsonify([row_to_dict(r) for r in rows])


@lenormand_bp.route('/api/lenormand/meanings', methods=['POST'])
@require_json
def create_meaning(data):
    """Add a meaning to a combination, creating the combination row if needed.
    Body: {card_1, card_2, meaning, source_id?}
    """
    db = current_app.config['DB']
    try:
        card_1 = int(data.get('card_1'))
        card_2 = int(data.get('card_2'))
    except (TypeError, ValueError):
        return jsonify({'error': 'card_1 and card_2 are required integers'}), 400
    meaning = (data.get('meaning') or '').strip()
    source_id = data.get('source_id')
    if source_id == '' or source_id is None:
        source_id = None
    else:
        try:
            source_id = int(source_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'source_id must be an integer'}), 400
    try:
        new_id = db.add_lenormand_meaning(card_1, card_2, meaning, source_id)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'id': new_id})


@lenormand_bp.route('/api/lenormand/meanings/<int:meaning_id>', methods=['PUT'])
@require_json
def update_meaning(meaning_id, data):
    """Update a meaning's text and/or source.
    Body keys: meaning?, source_id? (null clears the source).
    """
    db = current_app.config['DB']
    meaning = data.get('meaning')
    if meaning is not None:
        meaning = meaning.strip()
        if not meaning:
            return jsonify({'error': 'meaning cannot be empty'}), 400

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

    db.update_lenormand_meaning(
        meaning_id,
        meaning=meaning,
        source_id=source_id,
        clear_source=clear_source,
    )
    return jsonify({'ok': True})


@lenormand_bp.route('/api/lenormand/meanings/<int:meaning_id>', methods=['DELETE'])
def delete_meaning(meaning_id):
    db = current_app.config['DB']
    db.delete_lenormand_meaning(meaning_id)
    return jsonify({'ok': True})


@lenormand_bp.route('/api/lenormand/meanings/reorder', methods=['POST'])
@require_json
def reorder_meanings(data):
    """Reorder meanings within a combination.
    Body: {combination_id, ordered_ids: [int, ...]}
    """
    db = current_app.config['DB']
    combination_id = data.get('combination_id')
    ordered_ids = data.get('ordered_ids') or []
    if combination_id is None or not isinstance(ordered_ids, list):
        return jsonify({'error': 'combination_id and ordered_ids are required'}), 400
    db.reorder_lenormand_meanings(int(combination_id), [int(i) for i in ordered_ids])
    return jsonify({'ok': True})
