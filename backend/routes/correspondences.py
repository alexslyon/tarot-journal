"""
Correspondence system endpoints -- CRUD for systems, assignments, and card overrides.
"""

from flask import Blueprint, jsonify, request, current_app
from backend.utils import row_to_dict, require_json

correspondences_bp = Blueprint('correspondences', __name__)


# === Correspondence Systems ===

@correspondences_bp.route('/api/correspondence-systems')
def list_systems():
    db = current_app.config['DB']
    systems = db.get_correspondence_systems()
    return jsonify([row_to_dict(s) for s in systems])


@correspondences_bp.route('/api/correspondence-systems', methods=['POST'])
@require_json
def create_system(data):
    db = current_app.config['DB']
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    description = data.get('description', '').strip() or None
    try:
        system_id = db.create_correspondence_system(name, description)
    except Exception:
        return jsonify({'error': 'A system with that name already exists'}), 409
    return jsonify({'id': system_id}), 201


@correspondences_bp.route('/api/correspondence-systems/<int:system_id>')
def get_system(system_id):
    db = current_app.config['DB']
    system = db.get_correspondence_system(system_id)
    if not system:
        return jsonify({'error': 'System not found'}), 404
    result = row_to_dict(system)
    result['assignments'] = [
        row_to_dict(a) for a in db.get_system_assignments(system_id)
    ]
    return jsonify(result)


@correspondences_bp.route('/api/correspondence-systems/<int:system_id>', methods=['PUT'])
@require_json
def update_system(system_id, data):
    db = current_app.config['DB']
    system = db.get_correspondence_system(system_id)
    if not system:
        return jsonify({'error': 'System not found'}), 404
    try:
        db.update_correspondence_system(
            system_id,
            name=data.get('name'),
            description=data.get('description'),
        )
    except Exception:
        return jsonify({'error': 'A system with that name already exists'}), 409
    return jsonify({'ok': True})


@correspondences_bp.route('/api/correspondence-systems/<int:system_id>', methods=['DELETE'])
def delete_system(system_id):
    db = current_app.config['DB']
    system = db.get_correspondence_system(system_id)
    if not system:
        return jsonify({'error': 'System not found'}), 404
    db.delete_correspondence_system(system_id)
    return jsonify({'ok': True})


@correspondences_bp.route('/api/correspondence-systems/<int:system_id>/clone', methods=['POST'])
@require_json
def clone_system(system_id, data):
    db = current_app.config['DB']
    new_name = data.get('name', '').strip()
    if not new_name:
        return jsonify({'error': 'Name is required'}), 400
    new_id = db.clone_correspondence_system(system_id, new_name)
    if new_id is None:
        return jsonify({'error': 'Source system not found'}), 404
    return jsonify({'id': new_id}), 201


# === System Assignments ===

@correspondences_bp.route('/api/correspondence-systems/<int:system_id>/assignments')
def get_assignments(system_id):
    db = current_app.config['DB']
    archetype_id = request.args.get('archetype_id', type=int)
    assignments = db.get_system_assignments(system_id, archetype_id=archetype_id)
    return jsonify([row_to_dict(a) for a in assignments])


@correspondences_bp.route('/api/correspondence-systems/<int:system_id>/assignments', methods=['PUT'])
@require_json
def bulk_set_assignments(system_id, data):
    db = current_app.config['DB']
    assignments = data.get('assignments', [])
    if not assignments:
        return jsonify({'error': 'No assignments provided'}), 400
    try:
        db.bulk_set_system_assignments(system_id, assignments)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True})


@correspondences_bp.route(
    '/api/correspondence-systems/<int:system_id>/assignments/<int:archetype_id>/<field_name>',
    methods=['PUT']
)
@require_json
def set_assignment(system_id, archetype_id, field_name, data):
    db = current_app.config['DB']
    field_value = data.get('value', '').strip()
    if not field_value:
        return jsonify({'error': 'Value is required'}), 400
    try:
        db.set_system_assignment(system_id, archetype_id, field_name, field_value)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True})


@correspondences_bp.route(
    '/api/correspondence-systems/<int:system_id>/assignments/<int:archetype_id>/<field_name>',
    methods=['DELETE']
)
def delete_assignment(system_id, archetype_id, field_name):
    db = current_app.config['DB']
    db.delete_system_assignment(system_id, archetype_id, field_name)
    return jsonify({'ok': True})


# === Card-Level Overrides ===

@correspondences_bp.route('/api/cards/<int:card_id>/correspondences')
def get_card_correspondences(card_id):
    db = current_app.config['DB']
    correspondences = db.get_card_correspondences(card_id)
    return jsonify(correspondences)


@correspondences_bp.route('/api/cards/<int:card_id>/correspondences', methods=['PUT'])
@require_json
def set_card_overrides(card_id, data):
    """Set one or more card-level overrides. Body: {overrides: [{field_name, field_value}]}"""
    db = current_app.config['DB']
    overrides = data.get('overrides', [])
    for override in overrides:
        field_name = override.get('field_name')
        field_value = override.get('field_value')
        if field_value is None or field_value == '':
            db.delete_card_correspondence_override(card_id, field_name)
        else:
            try:
                db.set_card_correspondence_override(card_id, field_name, field_value)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True})


@correspondences_bp.route('/api/cards/<int:card_id>/correspondences/<field_name>', methods=['DELETE'])
def delete_card_override(card_id, field_name):
    db = current_app.config['DB']
    db.delete_card_correspondence_override(card_id, field_name)
    return jsonify({'ok': True})


# === Cross-System Queries (for Reference tab) ===

@correspondences_bp.route('/api/correspondences/by-archetype/<int:archetype_id>')
def correspondences_by_archetype(archetype_id):
    db = current_app.config['DB']
    assignments = db.get_correspondences_by_archetype(archetype_id)
    return jsonify([row_to_dict(a) for a in assignments])


@correspondences_bp.route('/api/correspondences/compare')
def compare_systems():
    db = current_app.config['DB']
    system_ids_str = request.args.get('systems', '')
    try:
        system_ids = [int(x) for x in system_ids_str.split(',') if x.strip()]
    except ValueError:
        return jsonify({'error': 'Invalid system IDs'}), 400
    if not system_ids:
        return jsonify({'error': 'At least one system ID required'}), 400
    assignments = db.compare_correspondence_systems(system_ids)
    return jsonify([row_to_dict(a) for a in assignments])


@correspondences_bp.route('/api/card-names')
def card_names():
    """Get card names in other languages, aggregated by archetype."""
    db = current_app.config['DB']
    cursor = db.conn.cursor()
    # Find all custom fields with "Name" in the field name
    cursor.execute('''
        SELECT ccf.field_name, ccf.field_value, c.archetype, c.name AS card_name,
               d.name AS deck_name
        FROM card_custom_fields ccf
        JOIN cards c ON c.id = ccf.card_id
        JOIN decks d ON d.id = c.deck_id
        WHERE ccf.field_name LIKE '%Name%'
          AND ccf.field_value IS NOT NULL
          AND ccf.field_value != ''
        ORDER BY c.archetype, ccf.field_name
    ''')
    rows = cursor.fetchall()
    return jsonify([row_to_dict(r) for r in rows])
