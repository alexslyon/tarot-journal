"""
Name-card endpoints (Greer, Archetypal Tarot Ch. 17). Computation lives
in the root name_cards module; the profile stores only the full birth
name (profiles.full_name, edited in the profile form) and the user's
saved adjustments (profiles.name_cards_config, JSON: parts, roles,
y_mode, y_overrides, drop_suffixes).

The calculate endpoint takes an ordered parts array — whitespace
splitting of full_name is the UI's suggestion for the user to confirm,
never something this layer does.
"""

import json
from datetime import date

from flask import Blueprint, jsonify, current_app

import birth_cards as bc
import name_cards as nc
from backend.utils import require_json
from backend.routes.birth_cards import (
    EIGHT_ELEVEN_KEY, tarot_archetype_ids, default_tarot_card_ids)

name_cards_bp = Blueprint('name_cards', __name__)


def _major_hydrator(db):
    """A function hydrating a Major number (1-22) with display name,
    archetype id, and default-Tarot-deck card id. Name cards are
    number-derived, so the 8/11 relabel preference applies, same as
    the numerological birth cards."""
    eight_eleven = db.get_setting(EIGHT_ELEVEN_KEY) or 'golden_dawn'
    if eight_eleven not in ('golden_dawn', 'marseille'):
        eight_eleven = 'golden_dawn'
    by_rank, _ = tarot_archetype_ids(db)
    card_ids = default_tarot_card_ids(db)

    def major(n):
        if n is None:
            return None
        candidates = [bc.major_name(n, eight_eleven), bc.MAJOR_NAMES[n]]
        if n == 8:
            candidates.append('Justice')
        if n == 11:
            candidates.append('Strength')
        candidates.extend(bc.MAJOR_ALIASES.get(n, []))
        card_id = next(
            (card_ids[c.lower()] for c in candidates if c.lower() in card_ids),
            None)
        return {
            'number': n,
            'name': bc.major_name(n, eight_eleven),
            'archetype_id': by_rank.get(bc.major_archetype_rank(n)),
            'card_id': card_id,
        }

    return major, eight_eleven


@name_cards_bp.route('/api/name-cards/calculate', methods=['POST'])
@require_json
def calculate(data):
    db = current_app.config['DB']
    parts = data.get('parts')
    if not isinstance(parts, list) or not parts:
        return jsonify({'error': 'parts must be a non-empty list'}), 400
    try:
        profile = nc.calculate_name_cards(
            parts,
            roles=data.get('roles'),
            y_mode=data.get('y_mode', 'heuristic'),
            y_overrides=data.get('y_overrides'),
            drop_suffixes=data.get('drop_suffixes', True),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    # Life Potential needs the birth date's unreduced Greer base.
    life = None
    birth_date_str = None
    profile_id = data.get('profile_id')
    if profile_id:
        row = db.get_profile(profile_id)
        if row:
            prow = row if isinstance(row, dict) else dict(row)
            birth_date_str = prow.get('birth_date')
    if birth_date_str:
        try:
            birth = date.fromisoformat(birth_date_str)
            life = nc.life_potential(
                bc.method_base(birth, bc.GREER), profile['all_letters'])
        except ValueError:
            life = None

    major, eight_eleven = _major_hydrator(db)
    profile['life_potential'] = life
    profile['eight_eleven'] = eight_eleven
    profile['cards'] = {
        'first_name': major(profile['first_name_card']),
        'middle_name': major(profile['middle_name_card']),
        'last_name': major(profile['last_name_card']),
        'desires_inner_motivation': major(profile['desires_inner_motivation']),
        'outer_persona': major(profile['outer_persona']),
        'theme_note': major(profile['theme_note']),
        'rhythm': major(profile['rhythm']),
        'melody': major(profile['melody']),
        'hidden_factor_name': [major(n) for n in profile['hidden_factor_name']],
        'life_potential': major(life),
    }
    # One entry per Major so the UI can render the mandala and the
    # constellation strip without a hydration call per letter.
    profile['majors_by_number'] = {n: major(n) for n in range(1, 23)}
    return jsonify(profile)


# === Alternate names (chosen names, nicknames — spec §9) ===

def _loads(raw, default=None):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def _name_row_json(row) -> dict:
    r = row if isinstance(row, dict) else dict(row)
    return {
        'id': r['id'],
        'profile_id': r['profile_id'],
        'name_kind': r['name_kind'],
        'display_name': r['display_name'],
        'parts': _loads(r.get('parts')),
        'roles': _loads(r.get('roles')),
        'y_mode': r.get('y_mode') or 'heuristic',
        'y_overrides': _loads(r.get('y_overrides'), []),
        'drop_suffixes': bool(r.get('drop_suffixes', 1)),
    }


@name_cards_bp.route('/api/profiles/<int:profile_id>/names')
def get_profile_names(profile_id):
    db = current_app.config['DB']
    if not db.get_profile(profile_id):
        return jsonify({'error': 'Profile not found'}), 404
    return jsonify([_name_row_json(r) for r in db.get_profile_names(profile_id)])


@name_cards_bp.route('/api/profiles/<int:profile_id>/names', methods=['POST'])
@require_json
def add_profile_name(profile_id, data):
    db = current_app.config['DB']
    if not db.get_profile(profile_id):
        return jsonify({'error': 'Profile not found'}), 404
    display_name = (data.get('display_name') or '').strip()
    if not display_name:
        return jsonify({'error': 'display_name is required'}), 400
    parts = data.get('parts')
    try:
        new_id = db.add_profile_name(
            profile_id, display_name,
            name_kind=data.get('name_kind') or 'other',
            parts=json.dumps(parts) if parts is not None else None,
            roles=json.dumps(data['roles']) if data.get('roles') is not None else None,
            y_mode=data.get('y_mode') or 'heuristic',
            y_overrides=json.dumps(data['y_overrides'])
                if data.get('y_overrides') is not None else None,
            drop_suffixes=data.get('drop_suffixes', True))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'id': new_id}), 201


@name_cards_bp.route('/api/profile-names/<int:name_id>', methods=['PUT'])
@require_json
def update_profile_name(name_id, data):
    db = current_app.config['DB']
    db.update_profile_name(
        name_id,
        display_name=data.get('display_name'),
        name_kind=data.get('name_kind'),
        parts=json.dumps(data['parts']) if data.get('parts') is not None else None,
        roles=json.dumps(data['roles']) if data.get('roles') is not None else None,
        clear_roles=data.get('roles', 'missing') is None,
        y_mode=data.get('y_mode'),
        y_overrides=json.dumps(data['y_overrides'])
            if data.get('y_overrides') is not None else None,
        drop_suffixes=data.get('drop_suffixes'))
    return jsonify({'ok': True})


@name_cards_bp.route('/api/profile-names/<int:name_id>', methods=['DELETE'])
def delete_profile_name(name_id):
    db = current_app.config['DB']
    db.delete_profile_name(name_id)
    return jsonify({'ok': True})


@name_cards_bp.route('/api/profiles/<int:profile_id>/name-cards-config')
def get_name_cards_config(profile_id):
    db = current_app.config['DB']
    row = db.get_profile(profile_id)
    if not row:
        return jsonify({'error': 'Profile not found'}), 404
    prow = row if isinstance(row, dict) else dict(row)
    config = None
    raw = prow.get('name_cards_config')
    if raw:
        try:
            config = json.loads(raw)
        except ValueError:
            config = None
    return jsonify({'full_name': prow.get('full_name'), 'config': config})


@name_cards_bp.route('/api/profiles/<int:profile_id>/name-cards-config',
                     methods=['PUT'])
@require_json
def set_name_cards_config(profile_id, data):
    db = current_app.config['DB']
    if not db.get_profile(profile_id):
        return jsonify({'error': 'Profile not found'}), 404
    config = data.get('config')
    if config is not None and not isinstance(config, dict):
        return jsonify({'error': 'config must be an object or null'}), 400
    db.update_profile(
        profile_id,
        name_cards_config=json.dumps(config) if config is not None else '')
    return jsonify({'ok': True})
