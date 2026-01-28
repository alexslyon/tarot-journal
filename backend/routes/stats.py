"""
Statistics endpoint.
"""

from flask import Blueprint, jsonify, current_app

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/api/stats')
def get_stats():
    db = current_app.config['DB']
    data = db.get_stats()
    return jsonify(data)
