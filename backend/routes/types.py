"""
Cartomancy type endpoints (Tarot, Lenormand, Oracle, etc.)
"""

from flask import Blueprint, jsonify, request, current_app

types_bp = Blueprint('types', __name__)


def _row_to_dict(row):
    return dict(row) if row else None


@types_bp.route('/api/types')
def get_types():
    db = current_app.config['DB']
    rows = db.get_cartomancy_types()
    return jsonify([_row_to_dict(r) for r in rows])


@types_bp.route('/api/types', methods=['POST'])
def add_type():
    db = current_app.config['DB']
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    type_id = db.add_cartomancy_type(name)
    return jsonify({'id': type_id, 'name': name}), 201
