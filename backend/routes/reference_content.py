"""
Reference-section endpoints: astrology, Kabbalah, numerology, chakras.

Static curated content comes from the root reference_content module;
everything derivable comes live from birth_cards.py (decan calendar,
rulers, trumps, court systems). Card references are hydrated exactly
like the birth-card endpoints (archetype ids + default-Tarot-deck card
ids for images).

Every endpoint accepts an optional ?system_id= naming a correspondence
system; when present, each sign/planet/letter/number/chakra also lists
the archetypes that system assigns to it (zodiac_sign / planet / decan /
hebrew_letter / numerology / chakra fields). Cross-references are
computed, never stored here.
"""

from collections import defaultdict
from datetime import date

from flask import Blueprint, jsonify, request, current_app

import birth_cards as bc
import reference_content as rc
from database.correspondences import parse_decan
from backend.routes.birth_cards import make_card_hydrators, _prefs

reference_content_bp = Blueprint('reference_content', __name__)

_MONTHS = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Alternate romanizations seen in the wild, so a user's hebrew_letter
# field options match regardless of spelling convention.
_LETTER_ALIASES = {
    'Aleph': ['alef'], 'Beth': ['bet', 'beit'], 'Gimel': ['gimmel'],
    'Daleth': ['dalet'], 'Heh': ['he', 'hey'], 'Vav': ['vau', 'waw'],
    'Zayin': ['zain'], 'Cheth': ['chet', 'het', 'heth'],
    'Teth': ['tet'], 'Yod': ['yud'], 'Kaph': ['caph', 'kaf'],
    'Lamed': ['lamedh'], 'Mem': [], 'Nun': [], 'Samekh': ['samech'],
    'Ayin': [], 'Peh': ['pe', 'fe'], 'Tzaddi': ['tsade', 'tzadi', 'tsadi'],
    'Qoph': ['qof', 'kof'], 'Resh': [], 'Shin': [], 'Tav': ['tau', 'taw'],
}


def _span_text(start, end):
    """'(3, 21), (4, 20)' -> 'Mar 21 – Apr 20'."""
    return (f'{_MONTHS[start[0]]} {start[1]} – '
            f'{_MONTHS[end[0]]} {end[1]}')


def _assignments_index(db):
    """Group the chosen system's assignments by (field, value.lower())
    -> [archetype refs]. Returns None when no system was requested."""
    raw = request.args.get('system_id')
    if not raw:
        return None
    try:
        system_id = int(raw)
    except ValueError:
        return None
    index = defaultdict(list)
    seen = defaultdict(set)
    for row in db.get_system_assignments(system_id):
        r = row if isinstance(row, dict) else dict(row)
        value = (r.get('field_value') or '').strip()
        if not value:
            continue
        key = (r['field_name'], value.lower())
        if r['archetype_id'] in seen[key]:
            continue
        seen[key].add(r['archetype_id'])
        index[key].append({
            'archetype_id': r['archetype_id'],
            'name': r['archetype_name'],
            'cartomancy_type': r['cartomancy_type'],
        })
        # Decan values ('Jupiter in Libra') also count toward their
        # sign and planet.
        if r['field_name'] == 'decan':
            parsed = parse_decan(value)
            if parsed:
                planet, sign = parsed
                for field, name in (('planet', planet), ('zodiac_sign', sign)):
                    dkey = (field, name.lower())
                    if r['archetype_id'] not in seen[dkey]:
                        seen[dkey].add(r['archetype_id'])
                        index[dkey].append(index[key][-1])
    return index


def _assigned(index, field, *values):
    """Assigned archetypes for any of the given values (deduped)."""
    if index is None:
        return []
    out, have = [], set()
    for v in values:
        for ref in index.get((field, v.lower()), []):
            if ref['archetype_id'] not in have:
                have.add(ref['archetype_id'])
                out.append(ref)
    return out


@reference_content_bp.route('/api/reference/astrology')
def astrology():
    db = current_app.config['DB']
    _, eight_eleven, court_system = _prefs(db)
    major, minor, by_card_name = make_card_hydrators(db, eight_eleven)
    index = _assignments_index(db)

    def court_arc(ref, system):
        court = bc.decan_court(ref, system)
        return {**court, **by_card_name(court['name'])}

    signs = []
    for i, sign in enumerate(rc.SIGNS):
        decan_rows = bc.DECANS[i * 3:i * 3 + 3]
        decans = []
        for j, (start, end, rank, suit) in enumerate(decan_rows):
            ref = {'rank': rank, 'suit': suit}
            rulers = bc.zodiacal_rulers(ref)
            decans.append({
                'index': j + 1,
                'dates': _span_text(start, end),
                'planet': rulers['planet'],
                'minor': minor(ref),
                'planet_trump': major(rulers['planet_major'], canonical=True),
            })
        # The sign's span: first decan's start through third's end.
        dates = _span_text(decan_rows[0][0], decan_rows[2][1])
        # Two court arcs touch each sign: its own court (0°–20°) via
        # decan I, and the next sign's court (20°–30°) via decan III.
        first, third = decan_rows[0], decan_rows[2]
        courts = {
            system: [
                court_arc({'rank': first[2], 'suit': first[3]}, system),
                court_arc({'rank': third[2], 'suit': third[3]}, system),
            ]
            for system in bc.COURT_SYSTEMS
        }
        signs.append({
            **sign,
            'dates': dates,
            'trump': major(bc.SIGN_MAJORS[sign['name']], canonical=True),
            'decans': decans,
            'courts': courts,
            'assigned': _assigned(index, 'zodiac_sign', sign['name']),
        })

    planets = []
    for planet in rc.PLANETS:
        trump_number = bc.PLANET_MAJORS.get(planet['name'])
        modern = False
        if trump_number is None:
            trump_number = rc.MODERN_PLANET_MAJORS.get(planet['name'])
            modern = trump_number is not None
        decans_ruled = [
            {'sign': rulers['sign'],
             'minor': minor({'rank': rank, 'suit': suit})}
            for (start, end, rank, suit) in bc.DECANS
            for rulers in [bc.zodiacal_rulers({'rank': rank, 'suit': suit})]
            if rulers['planet'] == planet['name']
        ]
        planets.append({
            **planet,
            'trump': major(trump_number, canonical=True) if trump_number else None,
            'modern_attribution': modern,
            'decans_ruled': decans_ruled,
            'assigned': _assigned(index, 'planet', planet['name']),
        })

    # Today's decan, for the wheel's "you are here" marker.
    today_ref = bc.zodiacal_card(date.today())
    return jsonify({
        'eight_eleven': eight_eleven,
        'court_system': court_system,
        'signs': signs,
        'planets': planets,
        'today_decan': bc.decan_position(today_ref),
    })


@reference_content_bp.route('/api/reference/kabbalah')
def kabbalah():
    db = current_app.config['DB']
    _, eight_eleven, court_system = _prefs(db)
    major, minor, by_card_name = make_card_hydrators(db, eight_eleven)
    index = _assignments_index(db)

    court_ranks = rc.TREE_COURT_RANKS[court_system]
    sephiroth = []
    for s in rc.SEPHIROTH:
        entry = {
            **s,
            # The four Minors of the sephira's number: Aces for Kether
            # down to Tens for Malkuth.
            'minors': [minor({'rank': s['number'], 'suit': suit})
                       for suit in bc.SUITS],
        }
        # Tetragrammaton courts on 2 / 3 / 6 / 10.
        rank = court_ranks.get(s['number'])
        if rank:
            entry['court_rank'] = rank
            entry['courts'] = [
                {'rank': rank, 'suit': suit,
                 **by_card_name(f'{rank} of {suit}')}
                for suit in bc.SUITS
            ]
        sephiroth.append(entry)
    paths = [
        {**p,
         'trump': major(p['trump'], canonical=True),
         'assigned': _assigned(index, 'hebrew_letter',
                               p['letter'], p['glyph'],
                               *_LETTER_ALIASES.get(p['letter'], []))}
        for p in rc.TREE_PATHS
    ]
    return jsonify({'sephiroth': sephiroth, 'paths': paths,
                    'court_system': court_system})


@reference_content_bp.route('/api/reference/numerology')
def numerology():
    db = current_app.config['DB']
    _, eight_eleven, _court = _prefs(db)
    major, minor, _ = make_card_hydrators(db, eight_eleven)
    index = _assignments_index(db)

    entries = []
    for entry in rc.NUMBERS:
        out = dict(entry)
        # Derived blocks attach only where they apply, so future
        # entries outside these ranges ('11', '22', a second system's
        # numbers) still render their text cleanly with nothing broken.
        try:
            n = int(entry['number'])
        except (TypeError, ValueError):
            n = None
        if n == 0:
            out['majors'] = [major(22)]
        elif n is not None and n in bc.CONSTELLATIONS:
            out['majors'] = [major(m) for m in bc.CONSTELLATIONS[n]]
        if n is not None and 1 <= n <= 10:
            out['minors'] = [minor({'rank': n, 'suit': s}) for s in bc.SUITS]
        out['assigned'] = _assigned(index, 'numerology', entry['number'])
        entries.append(out)
    return jsonify({'entries': entries})


@reference_content_bp.route('/api/reference/chakras')
def chakras():
    db = current_app.config['DB']
    index = _assignments_index(db)
    return jsonify({'chakras': [
        {**c,
         'assigned': _assigned(index, 'chakra', c['name'],
                               c['sanskrit'], f"{c['name']} Chakra")}
        for c in rc.CHAKRAS
    ]})
