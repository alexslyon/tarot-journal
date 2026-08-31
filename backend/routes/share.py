"""
Share export/import for spreads and profiles — JSON files in the same
spirit as the journal-entry export, so users can trade layouts and
people between installs.

Deliberate exclusions: spread default_deck_id (deck ids don't survive
the trip between databases) and profile astrology caches (regenerated
on demand). Imports skip same-name rows rather than duplicating or
overwriting — the report says what was skipped.
"""

import json
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

from backend.utils import row_to_dict, require_json

share_bp = Blueprint('share', __name__)


def _parse_json_column(raw, default=None):
    if raw is None or raw == '':
        return default
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def _parse_ids_arg():
    raw = request.args.get('ids', '')
    if not raw:
        return None, None
    try:
        return [int(x) for x in raw.split(',') if x.strip()], None
    except ValueError:
        return None, (jsonify(
            {'error': 'Invalid ids format - must be comma-separated integers'}), 400)


# === Spreads ===

@share_bp.route('/api/spreads/export')
def export_spreads():
    """Export spreads as shareable JSON. Optional ?ids=1,2 for a subset."""
    db = current_app.config['DB']
    ids, err = _parse_ids_arg()
    if err:
        return err

    cursor = db.conn.cursor()
    if ids:
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'SELECT * FROM spreads WHERE id IN ({placeholders})', ids)
    else:
        cursor.execute('SELECT * FROM spreads')
    rows = [row_to_dict(r) for r in cursor.fetchall()]
    tags_by_spread = db.get_tags_for_spreads()
    source_names = {s['id']: s['name'] for s in db.get_reference_sources()}

    spreads = []
    for r in rows:
        spreads.append({
            'name': r['name'],
            'description': r.get('description'),
            'positions': _parse_json_column(r.get('positions'), []),
            'cartomancy_type': r.get('cartomancy_type'),
            'allowed_deck_types': _parse_json_column(r.get('allowed_deck_types')),
            'deck_slots': _parse_json_column(r.get('deck_slots')),
            'archived': bool(r.get('archived')),
            'source': source_names.get(r.get('source_id')),
            'tags': [{'name': t['name'], 'color': t['color']}
                     for t in tags_by_spread.get(r['id'], [])],
        })

    return jsonify({
        'version': '1.0',
        'kind': 'spreads',
        'exported_at': datetime.now().isoformat(),
        'spreads': spreads,
    })


@share_bp.route('/api/spreads/import', methods=['POST'])
@require_json
def import_spreads(data):
    """Import spreads from a share file. Same-name spreads (case-
    insensitive) are skipped; tags are matched by name and created
    (with the exported color) when missing."""
    db = current_app.config['DB']
    payload = data.get('data', data)
    spreads = payload.get('spreads')
    if not isinstance(spreads, list):
        return jsonify({'error': 'Not a spreads export file (no "spreads" list).'}), 400

    existing_names = {
        row_to_dict(s)['name'].lower() for s in db.get_spreads()}
    tag_ids_by_name = {
        row_to_dict(t)['name'].lower(): row_to_dict(t)['id']
        for t in db.get_spread_tags()}
    source_ids_by_name = {
        s['name'].lower(): s['id'] for s in db.get_reference_sources()}

    imported = 0
    skipped = []
    tags_created = 0
    sources_created = 0
    for s in spreads:
        name = (s.get('name') or '').strip()
        positions = s.get('positions')
        if not name or not isinstance(positions, list):
            skipped.append(name or '(unnamed)')
            continue
        if name.lower() in existing_names:
            skipped.append(name)
            continue
        # Source attribution travels by name: match an existing
        # reference source (case-insensitive), create it when missing
        # (typed by the spread's deck types, Tarot as a last resort).
        source_id = None
        source_name = (s.get('source') or '').strip()
        if source_name:
            source_id = source_ids_by_name.get(source_name.lower())
            if source_id is None:
                types = s.get('allowed_deck_types') or (
                    [s['cartomancy_type']] if s.get('cartomancy_type') else ['Tarot'])
                source_id = db.create_reference_source(
                    source_name, cartomancy_types=types)
                source_ids_by_name[source_name.lower()] = source_id
                sources_created += 1

        spread_id = db.add_spread(
            name=name,
            positions=positions,
            description=s.get('description'),
            cartomancy_type=s.get('cartomancy_type'),
            allowed_deck_types=s.get('allowed_deck_types'),
            deck_slots=s.get('deck_slots'),
            source_id=source_id,
        )
        if s.get('archived'):
            db.update_spread(spread_id, archived=True)
        tag_ids = []
        for t in (s.get('tags') or []):
            tname = (t.get('name') or '').strip()
            if not tname:
                continue
            tid = tag_ids_by_name.get(tname.lower())
            if tid is None:
                tid = db.add_spread_tag(tname, t.get('color') or '#6B5B95')
                tag_ids_by_name[tname.lower()] = tid
                tags_created += 1
            tag_ids.append(tid)
        if tag_ids:
            db.set_spread_tags(spread_id, tag_ids)
        existing_names.add(name.lower())
        imported += 1

    return jsonify({
        'imported': imported,
        'skipped': skipped,
        'tags_created': tags_created,
        'sources_created': sources_created,
    })


# === Profiles ===

_PROFILE_FIELDS = (
    'name', 'full_name', 'gender', 'birth_date', 'birth_time',
    'birth_place_name', 'birth_place_lat', 'birth_place_lon',
)


@share_bp.route('/api/profiles/export')
def export_profiles():
    """Export profiles as shareable JSON. Optional ?ids=1,2 subset.
    Astrology chart caches are excluded (regenerated on demand)."""
    db = current_app.config['DB']
    ids, err = _parse_ids_arg()
    if err:
        return err

    rows = [row_to_dict(p) for p in db.get_profiles()]
    if ids:
        wanted = set(ids)
        rows = [r for r in rows if r['id'] in wanted]

    profiles = []
    for r in rows:
        p = {k: r.get(k) for k in _PROFILE_FIELDS}
        p['querent_only'] = bool(r.get('querent_only'))
        p['hidden'] = bool(r.get('hidden'))
        p['name_cards_config'] = _parse_json_column(r.get('name_cards_config'))
        p['alternate_names'] = [{
            'name_kind': row_to_dict(n)['name_kind'],
            'display_name': row_to_dict(n)['display_name'],
            'parts': _parse_json_column(row_to_dict(n).get('parts')),
            'roles': _parse_json_column(row_to_dict(n).get('roles')),
            'y_mode': row_to_dict(n).get('y_mode') or 'heuristic',
            'y_overrides': _parse_json_column(row_to_dict(n).get('y_overrides')),
            'drop_suffixes': bool(row_to_dict(n).get('drop_suffixes', 1)),
        } for n in db.get_profile_names(r['id'])]
        profiles.append(p)

    return jsonify({
        'version': '1.0',
        'kind': 'profiles',
        'exported_at': datetime.now().isoformat(),
        'profiles': profiles,
    })


@share_bp.route('/api/profiles/import', methods=['POST'])
@require_json
def import_profiles(data):
    """Import profiles from a share file; same-name profiles (case-
    insensitive) are skipped."""
    db = current_app.config['DB']
    payload = data.get('data', data)
    profiles = payload.get('profiles')
    if not isinstance(profiles, list):
        return jsonify({'error': 'Not a profiles export file (no "profiles" list).'}), 400

    existing_names = {
        row_to_dict(p)['name'].lower() for p in db.get_profiles()}

    imported = 0
    skipped = []
    for p in profiles:
        name = (p.get('name') or '').strip()
        if not name or name.lower() in existing_names:
            skipped.append(name or '(unnamed)')
            continue
        profile_id = db.add_profile(
            name=name,
            gender=p.get('gender'),
            birth_date=p.get('birth_date'),
            birth_time=p.get('birth_time'),
            birth_place_name=p.get('birth_place_name'),
            birth_place_lat=p.get('birth_place_lat'),
            birth_place_lon=p.get('birth_place_lon'),
            querent_only=bool(p.get('querent_only')),
            hidden=bool(p.get('hidden')),
            full_name=p.get('full_name'),
        )
        config = p.get('name_cards_config')
        if isinstance(config, dict):
            db.update_profile(profile_id,
                              name_cards_config=json.dumps(config))
        for alt in (p.get('alternate_names') or []):
            display = (alt.get('display_name') or '').strip()
            if not display:
                continue
            db.add_profile_name(
                profile_id, display,
                name_kind=alt.get('name_kind') or 'other',
                parts=json.dumps(alt['parts'])
                    if alt.get('parts') is not None else None,
                roles=json.dumps(alt['roles'])
                    if alt.get('roles') is not None else None,
                y_mode=alt.get('y_mode') or 'heuristic',
                y_overrides=json.dumps(alt['y_overrides'])
                    if alt.get('y_overrides') is not None else None,
                drop_suffixes=bool(alt.get('drop_suffixes', True)))
        existing_names.add(name.lower())
        imported += 1

    return jsonify({'imported': imported, 'skipped': skipped})
