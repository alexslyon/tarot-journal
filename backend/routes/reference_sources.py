"""
Shared reference-source endpoints. The same source list is used across
Lenormand combinations and Archetype notes.
"""

from flask import Blueprint, jsonify, request, current_app
from backend.utils import row_to_dict, require_json

reference_sources_bp = Blueprint('reference_sources', __name__)


@reference_sources_bp.route('/api/reference/sources')
def list_sources():
    db = current_app.config['DB']
    rows = db.get_reference_sources()
    return jsonify([row_to_dict(r) for r in rows])


@reference_sources_bp.route('/api/reference/sources', methods=['POST'])
@require_json
def create_source(data):
    db = current_app.config['DB']
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    try:
        new_id = db.create_reference_source(name)
    except Exception as e:
        return jsonify({'error': f'Could not create source: {e}'}), 400
    return jsonify({'id': new_id})


@reference_sources_bp.route('/api/reference/sources/<int:source_id>', methods=['PUT'])
@require_json
def update_source(source_id, data):
    db = current_app.config['DB']
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    db.update_reference_source(source_id, name)
    return jsonify({'ok': True})


@reference_sources_bp.route('/api/reference/sources/<int:source_id>', methods=['DELETE'])
def delete_source(source_id):
    """Delete a source. ?reassign_to=<id> reassigns dependent rows; otherwise
    they're set to unsourced. Dependent rows are never deleted with the source.
    """
    db = current_app.config['DB']
    reassign_to = request.args.get('reassign_to')
    reassign_id = int(reassign_to) if reassign_to else None
    db.delete_reference_source(source_id, reassign_to=reassign_id)
    return jsonify({'ok': True})


@reference_sources_bp.route('/api/reference/sources/<int:source_id>/dependencies')
def source_dependencies(source_id):
    """Return how many entries in each dependent table reference this source."""
    db = current_app.config['DB']
    return jsonify(db.count_reference_source_dependencies(source_id))
