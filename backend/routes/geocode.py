"""
Place-name geocoder endpoint.

Backs the "Look up" button on profile and entry editors. Uses the local
GeoNames cities500 index (~30 MB on disk, downloaded on first use).
Designed so a Nominatim fallback can be slotted in later without
changing the route contract.
"""

from flask import Blueprint, jsonify, request

geocode_bp = Blueprint('geocode', __name__)


@geocode_bp.route('/api/geocode')
def geocode():
    """Search for places matching the query string.

    Query params:
      q:     the place-name query (required, min 2 chars)
      limit: max results (default 10, capped at 25)

    Response: { results: [{name, admin1, country, latitude, longitude,
                           population, timezone, display_name}, ...] }

    The first request triggers a one-time ~7 MB download of the GeoNames
    cities500 zip + an ~80 KB admin1 names file, so it may take a few
    seconds. Subsequent requests are served from the local SQLite index.
    """
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify({'results': []})

    try:
        limit = max(1, min(int(request.args.get('limit') or 10), 25))
    except ValueError:
        limit = 10

    try:
        import geocoder
        results = geocoder.lookup(q, limit=limit)
    except Exception as e:
        return jsonify({'error': f'Geocoder failed: {e}'}), 500

    return jsonify({'results': results})
