"""
Onboarding routes: first-run flags and the consented starter spreads.

The Getting Started checklist itself is computed client-side from
real data (profiles/decks/spreads/entries counts); the backend only
remembers the two dismissal flags and performs the starter-spread
seeding when the user asks for it — nothing is ever seeded silently.
"""

from flask import Blueprint, current_app, jsonify

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


# Classic layouts in the spread designer's coordinate space
# (cards ~80x120, the same conventions user-made spreads follow).
STARTER_SPREADS = [
    {
        'name': 'Single Card',
        'description': 'One card: a daily draw, a focus, an answer.',
        'positions': [
            {'x': 220, 'y': 60, 'width': 120, 'height': 180,
             'label': 'The Card'},
        ],
    },
    {
        'name': 'Three Card Line',
        'description': 'The classic line — read as past / present / '
                       'future, situation / action / outcome, or any '
                       'triad you prefer.',
        'positions': [
            {'x': 140, 'y': 80, 'width': 80, 'height': 120, 'label': 'Past'},
            {'x': 240, 'y': 80, 'width': 80, 'height': 120, 'label': 'Present'},
            {'x': 340, 'y': 80, 'width': 80, 'height': 120, 'label': 'Future'},
        ],
    },
    {
        'name': 'Celtic Cross',
        'description': 'The ten-card classic: cross on the left, '
                       'staff on the right.',
        'positions': [
            {'x': 180, 'y': 160, 'width': 80, 'height': 120, 'label': 'Present'},
            {'x': 165, 'y': 180, 'width': 80, 'height': 120, 'label': 'Challenge',
             'rotated': True, 'z_index': 1},
            {'x': 180, 'y': 20, 'width': 80, 'height': 120, 'label': 'Crown'},
            {'x': 180, 'y': 300, 'width': 80, 'height': 120, 'label': 'Foundation'},
            {'x': 60, 'y': 160, 'width': 80, 'height': 120, 'label': 'Past'},
            {'x': 300, 'y': 160, 'width': 80, 'height': 120, 'label': 'Future'},
            {'x': 440, 'y': 310, 'width': 80, 'height': 120, 'label': 'Self'},
            {'x': 440, 'y': 205, 'width': 80, 'height': 120, 'label': 'Environment'},
            {'x': 440, 'y': 100, 'width': 80, 'height': 120, 'label': 'Hopes / Fears'},
            {'x': 440, 'y': -5, 'width': 80, 'height': 120, 'label': 'Outcome'},
        ],
    },
    {
        'name': 'Horseshoe',
        'description': 'Seven cards in an arc, from what led here to '
                       'where it leads.',
        'positions': [
            {'x': 20, 'y': 200, 'width': 80, 'height': 120, 'label': 'Past'},
            {'x': 105, 'y': 130, 'width': 80, 'height': 120, 'label': 'Present'},
            {'x': 190, 'y': 80, 'width': 80, 'height': 120,
             'label': 'Hidden Influences'},
            {'x': 275, 'y': 60, 'width': 80, 'height': 120, 'label': 'Obstacles'},
            {'x': 360, 'y': 80, 'width': 80, 'height': 120,
             'label': 'External Influences'},
            {'x': 445, 'y': 130, 'width': 80, 'height': 120, 'label': 'Advice'},
            {'x': 530, 'y': 200, 'width': 80, 'height': 120, 'label': 'Outcome'},
        ],
    },
    {
        'name': 'Relationship Cross',
        'description': 'Five cards on two people and what runs '
                       'between them.',
        'positions': [
            {'x': 80, 'y': 140, 'width': 80, 'height': 120, 'label': 'You'},
            {'x': 400, 'y': 140, 'width': 80, 'height': 120, 'label': 'Them'},
            {'x': 240, 'y': 30, 'width': 80, 'height': 120, 'label': 'The Bond'},
            {'x': 240, 'y': 140, 'width': 80, 'height': 120,
             'label': 'Where It Stands'},
            {'x': 240, 'y': 250, 'width': 80, 'height': 120,
             'label': 'The Challenge'},
        ],
    },
]


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
            description=spec['description'],
        )
        added.append(spec['name'])
    return jsonify({'added': added, 'skipped': skipped})
