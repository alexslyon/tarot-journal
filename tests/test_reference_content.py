"""Reference-content datasets and endpoints: astrology, Kabbalah,
numerology, chakras.

Dataset integrity is asserted structurally (counts, uniqueness, the 22
paths carrying each trump exactly once) so a future edit that breaks
the tables fails loudly; endpoint tests check hydration shape and the
correspondence cross-references.
"""

import reference_content as rc
import birth_cards as bc


# === Dataset integrity ===

def test_signs_dataset():
    assert len(rc.SIGNS) == 12
    names = [s['name'] for s in rc.SIGNS]
    assert names == bc._SIGN_ORDER          # same order as the decan calendar
    for s in rc.SIGNS:
        assert s['element'] in ('Fire', 'Earth', 'Air', 'Water')
        assert s['modality'] in ('Cardinal', 'Fixed', 'Mutable')
        assert s['name'] in bc.SIGN_MAJORS  # every sign has a trump


def test_planets_dataset():
    assert len(rc.PLANETS) == 10
    classical = [p['name'] for p in rc.PLANETS if p['classical']]
    assert set(classical) == set(bc.PLANET_MAJORS)
    modern = [p['name'] for p in rc.PLANETS if not p['classical']]
    assert set(modern) == set(rc.MODERN_PLANET_MAJORS)
    # Every sign's ruler is a real planet
    planet_names = {p['name'] for p in rc.PLANETS}
    for s in rc.SIGNS:
        assert s['ruler'] in planet_names
        if 'modern_ruler' in s:
            assert s['modern_ruler'] in planet_names


def test_sephiroth_dataset():
    assert len(rc.SEPHIROTH) == 10
    assert [s['number'] for s in rc.SEPHIROTH] == list(range(1, 11))
    for s in rc.SEPHIROTH:
        assert s['pillar'] in ('middle', 'mercy', 'severity')
        assert 0 <= s['x'] <= 100 and 0 <= s['y'] <= 100
    # Three pillars with the standard membership
    middle = [s['number'] for s in rc.SEPHIROTH if s['pillar'] == 'middle']
    assert middle == [1, 6, 9, 10]


def test_tree_paths_dataset():
    assert len(rc.TREE_PATHS) == 22
    assert [p['path'] for p in rc.TREE_PATHS] == list(range(11, 33))
    # Each trump 1-22 appears exactly once; letters unique; endpoints valid
    assert sorted(p['trump'] for p in rc.TREE_PATHS) == list(range(1, 23))
    assert len({p['letter'] for p in rc.TREE_PATHS}) == 22
    assert len({p['glyph'] for p in rc.TREE_PATHS}) == 22
    # Hebrew letter gematria values sum to 1495
    assert sum(p['value'] for p in rc.TREE_PATHS) == 1495
    sephira_numbers = {s['number'] for s in rc.SEPHIROTH}
    for p in rc.TREE_PATHS:
        assert p['from'] in sephira_numbers and p['to'] in sephira_numbers
        assert p['from'] < p['to']
    # Every sephira is touched by at least one path
    touched = {n for p in rc.TREE_PATHS for n in (p['from'], p['to'])}
    assert touched == sephira_numbers


def test_chakras_and_numbers_datasets():
    assert len(rc.CHAKRAS) == 7
    assert [c['name'] for c in rc.CHAKRAS][0] == 'Root'
    assert [c['name'] for c in rc.CHAKRAS][-1] == 'Crown'
    # NUMBERS is a flat, open-ended list: unique labels, required keys
    labels = [n['number'] for n in rc.NUMBERS]
    assert len(labels) == len(set(labels))
    for n in rc.NUMBERS:
        assert n['title'] and n['meaning']
        assert 'system' in n


# === Endpoints ===

def test_astrology_endpoint(client):
    data = client.get('/api/reference/astrology').get_json()
    assert len(data['signs']) == 12
    assert len(data['planets']) == 10
    assert data['court_system'] in bc.COURT_SYSTEMS

    aries = data['signs'][0]
    assert aries['name'] == 'Aries'
    assert aries['dates'] == 'Mar 21 – Apr 20'
    assert aries['trump']['name'] == 'The Emperor'
    assert len(aries['decans']) == 3
    assert aries['decans'][0]['minor']['name'] == 'Two of Wands'
    assert aries['decans'][0]['planet'] == 'Mars'
    # Both court arcs, under all three systems, all distinct tables
    assert set(aries['courts']) == set(bc.COURT_SYSTEMS)
    for system, arcs in aries['courts'].items():
        assert len(arcs) == 2
    assert aries['courts']['golden_dawn'][0]['name'] == 'Queen of Wands'
    assert aries['courts']['bota'][0]['name'] == 'King of Wands'

    # Leo's trump is always canonical Strength (card identity)
    leo = next(s for s in data['signs'] if s['name'] == 'Leo')
    assert leo['trump']['name'] == 'Strength'

    mars = next(p for p in data['planets'] if p['name'] == 'Mars')
    assert mars['trump']['name'] == 'The Tower'
    assert mars['modern_attribution'] is False
    # Mars rules 6 decans (the Chaldean doubling at the Pisces seam)
    assert len(mars['decans_ruled']) == 6
    uranus = next(p for p in data['planets'] if p['name'] == 'Uranus')
    assert uranus['trump']['name'] == 'The Fool'
    assert uranus['modern_attribution'] is True


def test_astrology_today_decan_and_positions(client):
    """The wheel's markers: today's decan is always a real position,
    and decan_position round-trips the decan table."""
    assert bc.decan_position({'rank': 2, 'suit': 'Wands'}) == {
        'sign': 'Aries', 'index': 1}
    # The year-boundary wrap decan sits in Capricorn II
    assert bc.decan_position({'rank': 3, 'suit': 'Pentacles'}) == {
        'sign': 'Capricorn', 'index': 2}

    data = client.get('/api/reference/astrology').get_json()
    today = data['today_decan']
    assert today['sign'] in [s['name'] for s in rc.SIGNS]
    assert today['index'] in (1, 2, 3)


def test_kabbalah_endpoint(client):
    data = client.get('/api/reference/kabbalah').get_json()
    assert len(data['sephiroth']) == 10
    assert len(data['paths']) == 22
    kether = data['sephiroth'][0]
    assert [m['name'] for m in kether['minors']] == [
        'Ace of Wands', 'Ace of Cups', 'Ace of Swords', 'Ace of Pentacles']
    malkuth = data['sephiroth'][-1]
    assert malkuth['minors'][0]['name'] == 'Ten of Wands'
    path11 = data['paths'][0]
    assert path11['letter'] == 'Aleph'
    assert path11['trump']['name'] == 'The Fool'


def test_tree_courts_follow_court_preference(client):
    """Tetragrammaton courts on 2/3/6/10, rank names per the saved
    Courts preference (user ruling: B.O.T.A. reads as Book T titles)."""
    # Dataset: all three systems present, keys fixed
    assert set(rc.TREE_COURT_RANKS) == set(bc.COURT_SYSTEMS)
    for table in rc.TREE_COURT_RANKS.values():
        assert set(table) == {2, 3, 6, 10}
        assert table[3] == 'Queen' and table[10] == 'Page'

    data = client.get('/api/reference/kabbalah').get_json()
    by_number = {s['number']: s for s in data['sephiroth']}
    assert data['court_system'] == 'golden_dawn'
    assert by_number[2]['court_rank'] == 'King'
    assert [c['name'] for c in by_number[6]['courts']] == [
        'Knight of Wands', 'Knight of Cups', 'Knight of Swords',
        'Knight of Pentacles']
    # No courts off the Tetragrammaton four
    assert 'courts' not in by_number[1] and 'courts' not in by_number[9]

    # Waite figures flip the 2/6 ranks
    client.put('/api/birth-cards/prefs', json={'court_system': 'golden_dawn_waite'})
    data = client.get('/api/reference/kabbalah').get_json()
    by_number = {s['number']: s for s in data['sephiroth']}
    assert by_number[2]['court_rank'] == 'Knight'
    assert by_number[6]['court_rank'] == 'King'

    # B.O.T.A. reads as Book T titles on the tree
    client.put('/api/birth-cards/prefs', json={'court_system': 'bota'})
    data = client.get('/api/reference/kabbalah').get_json()
    by_number = {s['number']: s for s in data['sephiroth']}
    assert by_number[2]['court_rank'] == 'King'
    assert by_number[6]['court_rank'] == 'Knight'


def test_numerology_endpoint(client):
    data = client.get('/api/reference/numerology').get_json()
    entries = {e['number']: e for e in data['entries']}
    # 0: just the Fool, no minors
    assert [m['name'] for m in entries['0']['majors']] == ['The Fool']
    assert 'minors' not in entries['0']
    # 5: constellation pair + four Fives
    assert [m['number'] for m in entries['5']['majors']] == [5, 14]
    assert len(entries['5']['minors']) == 4
    # 10: Tens but no constellation block (10 is not a root)
    assert 'majors' not in entries['10']
    assert entries['10']['minors'][0]['name'] == 'Ten of Wands'


def test_chakras_endpoint(client):
    data = client.get('/api/reference/chakras').get_json()
    assert len(data['chakras']) == 7
    assert data['chakras'][3]['name'] == 'Heart'
    assert data['chakras'][3]['assigned'] == []


def test_correspondence_cross_references(client):
    """A chosen system's assignments surface on the matching entities —
    including decan values counting toward their sign and planet, and
    hebrew-letter alias spellings."""
    sid = client.post('/api/correspondence-systems', json={
        'name': 'ZZ Ref Test', 'cartomancy_type': 'Tarot'}).get_json()['id']
    a1 = client.post('/api/archetypes', json={
        'cartomancy_type': 'Tarot', 'name': 'ZZ Test Card A'}).get_json()['id']
    a2 = client.post('/api/archetypes', json={
        'cartomancy_type': 'Tarot', 'name': 'ZZ Test Card B'}).get_json()['id']
    client.put(f'/api/correspondence-systems/{sid}/assignments', json={
        'assignments': [
            {'archetype_id': a1, 'field_name': 'zodiac_sign', 'field_value': 'Leo'},
            {'archetype_id': a1, 'field_name': 'chakra', 'field_value': 'Anahata'},
            {'archetype_id': a1, 'field_name': 'numerology', 'field_value': '7'},
            {'archetype_id': a1, 'field_name': 'hebrew_letter', 'field_value': 'Alef'},
            {'archetype_id': a2, 'field_name': 'decan', 'field_value': 'Jupiter in Leo'},
        ]})

    astro = client.get(f'/api/reference/astrology?system_id={sid}').get_json()
    leo = next(s for s in astro['signs'] if s['name'] == 'Leo')
    assert {a['name'] for a in leo['assigned']} == {'ZZ Test Card A', 'ZZ Test Card B'}
    jupiter = next(p for p in astro['planets'] if p['name'] == 'Jupiter')
    assert {a['name'] for a in jupiter['assigned']} == {'ZZ Test Card B'}
    # Unassigned sign stays empty
    aries = astro['signs'][0]
    assert aries['assigned'] == []

    kab = client.get(f'/api/reference/kabbalah?system_id={sid}').get_json()
    aleph = kab['paths'][0]
    assert [a['name'] for a in aleph['assigned']] == ['ZZ Test Card A']

    num = client.get(f'/api/reference/numerology?system_id={sid}').get_json()
    seven = next(e for e in num['entries'] if e['number'] == '7')
    assert [a['name'] for a in seven['assigned']] == ['ZZ Test Card A']

    chak = client.get(f'/api/reference/chakras?system_id={sid}').get_json()
    heart = next(c for c in chak['chakras'] if c['name'] == 'Heart')
    assert [a['name'] for a in heart['assigned']] == ['ZZ Test Card A']

    # No system_id: cross-refs quietly absent
    astro = client.get('/api/reference/astrology').get_json()
    assert astro['signs'][4]['assigned'] == []
