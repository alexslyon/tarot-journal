"""
Reference-source endpoints + per-archetype source-entry CRUD.

In the new model a reference source belongs to a cartomancy type and
implicitly grants every archetype of that type a "field" under the
source. The /api/archetype-source-entries routes handle the per-cell
content; /api/reference/sources still handles the source list itself
plus its authors.

Lenormand combinations keep using sources the legacy way (per-pair
meanings with a source attribution); those endpoints aren't touched.
"""

from flask import Blueprint, jsonify, request, current_app
from backend.utils import require_json

reference_sources_bp = Blueprint('reference_sources', __name__)


# === Sources =================================================

@reference_sources_bp.route('/api/reference/sources')
def list_sources():
    """List reference sources. ?cartomancy_type=Tarot scopes the result."""
    db = current_app.config['DB']
    ctype = request.args.get('cartomancy_type')
    return jsonify(db.get_reference_sources(cartomancy_type=ctype))


@reference_sources_bp.route('/api/reference/sources/<int:source_id>')
def get_source(source_id):
    db = current_app.config['DB']
    source = db.get_reference_source(source_id)
    if not source:
        return jsonify({'error': 'Source not found'}), 404
    return jsonify(source)


@reference_sources_bp.route('/api/reference/sources', methods=['POST'])
@require_json
def create_source(data):
    db = current_app.config['DB']
    name = (data.get('name') or '').strip()
    cartomancy_type = (data.get('cartomancy_type') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if not cartomancy_type:
        return jsonify({'error': 'cartomancy_type is required'}), 400
    authors = data.get('authors') or []
    try:
        new_id = db.create_reference_source(
            name, cartomancy_type=cartomancy_type, authors=authors,
        )
    except Exception as e:
        return jsonify({'error': f'Could not create source: {e}'}), 400
    return jsonify({'id': new_id})


@reference_sources_bp.route('/api/reference/sources/<int:source_id>', methods=['PUT'])
@require_json
def update_source(source_id, data):
    """Update any subset of name / cartomancy_type / authors. Empty
    body keys are ignored so partial updates don't need to round-trip
    the full row."""
    db = current_app.config['DB']
    name = data.get('name')
    if name is not None and not str(name).strip():
        return jsonify({'error': 'Name cannot be blank'}), 400
    ctype = data.get('cartomancy_type')
    if ctype is not None and not str(ctype).strip():
        return jsonify({'error': 'cartomancy_type cannot be blank'}), 400
    authors = data.get('authors')
    db.update_reference_source(
        source_id,
        name=name.strip() if isinstance(name, str) else None,
        cartomancy_type=ctype.strip() if isinstance(ctype, str) else None,
        authors=authors if isinstance(authors, list) else None,
    )
    return jsonify({'ok': True})


@reference_sources_bp.route('/api/reference/sources/<int:source_id>', methods=['DELETE'])
def delete_source(source_id):
    """Delete a source. ?reassign_to=<id> reassigns Lenormand-meaning
    rows; archetype source entries are dropped with the source."""
    db = current_app.config['DB']
    reassign_to = request.args.get('reassign_to')
    reassign_id = int(reassign_to) if reassign_to else None
    db.delete_reference_source(source_id, reassign_to=reassign_id)
    return jsonify({'ok': True})


@reference_sources_bp.route('/api/reference/sources/<int:source_id>/dependencies')
def source_dependencies(source_id):
    db = current_app.config['DB']
    return jsonify(db.count_reference_source_dependencies(source_id))


# === Per-archetype source entries ============================

@reference_sources_bp.route('/api/archetypes/<int:archetype_id>/source-entries')
def list_entries_for_archetype(archetype_id):
    """All non-empty entries for an archetype, optionally scoped by
    cartomancy type. The Archetypes viewer calls this with the active
    type so it only sees the relevant sources."""
    db = current_app.config['DB']
    ctype = request.args.get('cartomancy_type')
    return jsonify(db.get_source_entries_for_archetype(archetype_id, cartomancy_type=ctype))


@reference_sources_bp.route('/api/reference/sources/<int:source_id>/entries')
def list_entries_for_source(source_id):
    """Every entry under a source. Used by the Settings authoring page."""
    db = current_app.config['DB']
    return jsonify(db.get_source_entries_for_source(source_id))


@reference_sources_bp.route(
    '/api/archetypes/<int:archetype_id>/source-entries/<int:source_id>',
    methods=['PUT'],
)
@require_json
def set_entry(archetype_id, source_id, data):
    """Upsert content for an (archetype, source) pair. Blank content
    deletes the row (the viewer treats absence and emptiness the same)."""
    db = current_app.config['DB']
    content = data.get('content', '')
    db.set_source_entry(archetype_id, source_id, content)
    return jsonify({'ok': True})


@reference_sources_bp.route(
    '/api/archetypes/<int:archetype_id>/source-entries/<int:source_id>',
    methods=['DELETE'],
)
def delete_entry(archetype_id, source_id):
    db = current_app.config['DB']
    db.delete_source_entry(archetype_id, source_id)
    return jsonify({'ok': True})
