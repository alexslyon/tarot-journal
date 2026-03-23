"""
Cartomancy type endpoints (Tarot, Lenormand, Oracle, etc.)
"""

from flask import Blueprint, jsonify, current_app
from backend.utils import row_to_dict, sort_types, require_json, validate_length

types_bp = Blueprint('types', __name__)


@types_bp.route('/api/types')
def get_types():
    db = current_app.config['DB']
    rows = db.get_cartomancy_types()
    types = [row_to_dict(r) for r in rows]
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
    type_id = db.add_cartomancy_type(name)
    return jsonify({'id': type_id, 'name': name}), 201
