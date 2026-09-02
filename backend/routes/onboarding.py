"""
Onboarding routes: first-run flags and the consented starter spreads.

The Getting Started checklist itself is computed client-side from
real data (profiles/decks/spreads/entries counts); the backend only
remembers the two dismissal flags and performs the starter-spread
seeding when the user asks for it — nothing is ever seeded silently.
"""

from flask import Blueprint, current_app, jsonify

from backend.starter_spreads import STARTER_SPREADS
from backend.utils import require_json

onboarding_bp = Blueprint('onboarding', __name__)

WELCOME_KEY = 'onboarding_welcome_done'
CHECKLIST_KEY = 'onboarding_checklist_dismissed'


@onboarding_bp.route('/api/onboarding/flags')
def get_flags():
    db = current_app.config['DB']
    return jsonify({
        'welcome_done': db.get_setting(WELCOME_KEY) == 'true',
        'checklist_dismissed': db.get_setting(CHECKLIST_KEY) == 'true',
    })


@onboarding_bp.route('/api/onboarding/flags', methods=['PUT'])
@require_json
def set_flags(data):
    db = current_app.config['DB']
    if 'welcome_done' in data:
        db.set_setting(WELCOME_KEY, 'true' if data['welcome_done'] else 'false')
    if 'checklist_dismissed' in data:
        db.set_setting(CHECKLIST_KEY,
                       'true' if data['checklist_dismissed'] else 'false')
    return jsonify({'ok': True})


@onboarding_bp.route('/api/onboarding/starter-spreads', methods=['POST'])
def add_starter_spreads():
    """Seed the classic spreads the user consented to. Idempotent:
    a spread whose name already exists is skipped, so re-clicking
    (or an established database) never gets duplicates."""
    db = current_app.config['DB']
    existing = {s['name'].strip().lower() for s in db.get_spreads()}
    added, skipped = [], []
    for spec in STARTER_SPREADS:
        if spec['name'].lower() in existing:
            skipped.append(spec['name'])
            continue
        db.add_spread(
            name=spec['name'],
            positions=spec['positions'],
            description=spec.get('description'),
            allowed_deck_types=spec.get('allowed_deck_types'),
            deck_slots=spec.get('deck_slots'),
        )
        added.append(spec['name'])
    return jsonify({'added': added, 'skipped': skipped})
