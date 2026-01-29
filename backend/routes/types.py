"""
Cartomancy type endpoints (Tarot, Lenormand, Oracle, etc.)
"""

from flask import Blueprint, jsonify, request, current_app

types_bp = Blueprint('types', __name__)

# Preferred display order for cartomancy types
TYPE_ORDER = ['Tarot', 'Lenormand', 'Oracle', 'Playing Cards', 'Kipper', 'I Ching']


def _row_to_dict(row):
    return dict(row) if row else None


def _sort_types(types):
    """Sort types by preferred display order, with unknown types at the end."""
    def sort_key(t):
        name = t.get('name', '') if isinstance(t, dict) else t['name']
        try:
            return TYPE_ORDER.index(name)
        except ValueError:
            return len(TYPE_ORDER)  # Unknown types go at the end
    return sorted(types, key=sort_key)


@types_bp.route('/api/types')
def get_types():
    db = current_app.config['DB']
    rows = db.get_cartomancy_types()
    types = [_row_to_dict(r) for r in rows]
    return jsonify(_sort_types(types))


@types_bp.route('/api/types', methods=['POST'])
def add_type():
    db = current_app.config['DB']
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    type_id = db.add_cartomancy_type(name)
    return jsonify({'id': type_id, 'name': name}), 201
