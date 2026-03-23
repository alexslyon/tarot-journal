"""
Tag endpoints -- CRUD for entry tags, deck tags, and card tags.
"""

from flask import Blueprint, jsonify, current_app
from backend.utils import row_to_dict, require_json, validate_length

tags_bp = Blueprint('tags', __name__)


def _tag_crud(tag_type, get_all, get_one, add, update, delete):
    """Register CRUD routes for a tag type (entry-tags, deck-tags, card-tags)."""

    @tags_bp.route(f'/api/{tag_type}', endpoint=f'get_{tag_type}')
    def get_tags():
        db = current_app.config['DB']
        rows = get_all(db)
        return jsonify([row_to_dict(r) for r in rows])

    @tags_bp.route(f'/api/{tag_type}', methods=['POST'], endpoint=f'add_{tag_type}')
    @require_json
    def add_tag(data):
        db = current_app.config['DB']
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'name is required'}), 400
        err = validate_length(name, field_name='name')
        if err:
            return jsonify({'error': err}), 400
        tag_id = add(db, name=name, color=data.get('color', '#6B5B95'))
        return jsonify({'id': tag_id}), 201

    @tags_bp.route(f'/api/{tag_type}/<int:tag_id>', methods=['PUT'], endpoint=f'update_{tag_type}')
    @require_json
    def update_tag(tag_id, data):
        db = current_app.config['DB']
        if not get_one(db, tag_id):
            return jsonify({'error': 'Tag not found'}), 404
        name = data.get('name')
        if name:
            err = validate_length(name, field_name='name')
            if err:
                return jsonify({'error': err}), 400
        update(db, tag_id, name=name, color=data.get('color'))
        return jsonify({'ok': True})

    @tags_bp.route(f'/api/{tag_type}/<int:tag_id>', methods=['DELETE'], endpoint=f'delete_{tag_type}')
    def delete_tag(tag_id):
        db = current_app.config['DB']
        if not get_one(db, tag_id):
            return jsonify({'error': 'Tag not found'}), 404
        delete(db, tag_id)
        return jsonify({'ok': True})


# Register all three tag types
_tag_crud(
    'entry-tags',
    get_all=lambda db: db.get_tags(),
    get_one=lambda db, tid: db.get_tag(tid),
    add=lambda db, **kw: db.add_tag(**kw),
    update=lambda db, tid, **kw: db.update_tag(tid, **kw),
    delete=lambda db, tid: db.delete_tag(tid),
)

_tag_crud(
    'deck-tags',
    get_all=lambda db: db.get_deck_tags(),
    get_one=lambda db, tid: db.get_deck_tag(tid),
    add=lambda db, **kw: db.add_deck_tag(**kw),
    update=lambda db, tid, **kw: db.update_deck_tag(tid, **kw),
    delete=lambda db, tid: db.delete_deck_tag(tid),
)

_tag_crud(
    'card-tags',
    get_all=lambda db: db.get_card_tags(),
    get_one=lambda db, tid: db.get_card_tag(tid),
    add=lambda db, **kw: db.add_card_tag(**kw),
    update=lambda db, tid, **kw: db.update_card_tag(tid, **kw),
    delete=lambda db, tid: db.delete_card_tag(tid),
)
