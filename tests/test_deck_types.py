"""Deck Types manager: custom cartomancy types + archetype CRUD.

Built-in types are re-seeded on every startup, so rename/delete must
refuse them; custom types cascade cleanly through the string-keyed
tables and the archetype FK graph.
"""


def _type_by_name(client, name):
    return next((t for t in client.get('/api/types').get_json()
                 if t['name'] == name), None)


def test_builtin_flag_and_custom_add(client):
    types = client.get('/api/types').get_json()
    assert all(t['builtin'] for t in types)
    r = client.post('/api/types', json={'name': 'Runes'})
    assert r.status_code == 201
    t = _type_by_name(client, 'Runes')
    assert t and t['builtin'] is False
    # Duplicate rejected cleanly
    assert client.post('/api/types', json={'name': 'Runes'}).status_code == 400


def test_builtin_rename_and_delete_refused(client):
    tarot = _type_by_name(client, 'Tarot')
    assert client.put(f"/api/types/{tarot['id']}",
                      json={'name': 'Tarocchi'}).status_code == 400
    assert client.delete(f"/api/types/{tarot['id']}").status_code == 400


def test_custom_type_rename_cascades(client, db):
    client.post('/api/types', json={'name': 'Runes'})
    t = _type_by_name(client, 'Runes')
    a1 = client.post('/api/archetypes', json={
        'cartomancy_type': 'Runes', 'name': 'Fehu'}).get_json()['id']
    a2 = client.post('/api/archetypes', json={
        'cartomancy_type': 'Runes', 'name': 'Uruz'}).get_json()['id']
    client.post('/api/scribe/apply', json={'writes': [
        {'target': 'combination', 'cartomancy_type': 'Runes',
         'archetype_ids': [a1, a2], 'content': 'Wealth in motion.'}]})

    r = client.put(f"/api/types/{t['id']}", json={'name': 'Elder Futhark'})
    assert r.status_code == 200
    assert _type_by_name(client, 'Runes') is None
    assert _type_by_name(client, 'Elder Futhark') is not None
    # Archetypes and combinations follow the rename
    archs = client.get('/api/archetypes?cartomancy_type=Elder Futhark').get_json()
    assert {a['name'] for a in archs} == {'Fehu', 'Uruz'}
    meanings = client.get(
        '/api/combinations/meanings?cartomancy_type=Elder Futhark'
        f'&card_1={a1}&card_2={a2}').get_json()
    assert len(meanings) == 1


def test_custom_type_delete_guard_and_cascade(client, db):
    client.post('/api/types', json={'name': 'Runes'})
    t = _type_by_name(client, 'Runes')
    deck = client.post('/api/decks', json={
        'name': 'Rune Set', 'type_ids': [t['id']]}).get_json()
    assert client.delete(f"/api/types/{t['id']}").status_code == 400
    client.delete(f"/api/decks/{deck['id']}")

    client.post('/api/archetypes', json={
        'cartomancy_type': 'Runes', 'name': 'Fehu'})
    assert client.delete(f"/api/types/{t['id']}").status_code == 200
    assert _type_by_name(client, 'Runes') is None
    assert client.get('/api/archetypes?cartomancy_type=Runes').get_json() == []


def test_archetype_crud(client, db):
    client.post('/api/types', json={'name': 'Runes'})
    r = client.post('/api/archetypes', json={
        'cartomancy_type': 'Runes', 'name': 'Fehu', 'rank': '1'})
    assert r.status_code == 201
    aid = r.get_json()['id']
    # Duplicate name for the type is a clean 400
    assert client.post('/api/archetypes', json={
        'cartomancy_type': 'Runes', 'name': 'Fehu'}).status_code == 400

    # Rename updates cards tagged with the old archetype name
    t = _type_by_name(client, 'Runes')
    deck = client.post('/api/decks', json={
        'name': 'Rune Set', 'type_ids': [t['id']]}).get_json()
    card = client.post('/api/cards', json={
        'deck_id': deck['id'], 'name': 'fehu scan'}).get_json()
    client.put(f"/api/cards/{card['id']}/metadata", json={'archetype': 'Fehu'})
    client.put(f'/api/archetypes/{aid}', json={'name': 'Fehu (Cattle)'})
    got = client.get(f"/api/cards/{card['id']}").get_json()
    assert got['archetype'] == 'Fehu (Cattle)'

    client.delete(f'/api/archetypes/{aid}')
    assert client.get('/api/archetypes?cartomancy_type=Runes').get_json() == []


def test_archetype_bulk_and_seed_from_deck(client, db):
    client.post('/api/types', json={'name': 'Runes'})
    r = client.post('/api/archetypes/bulk', json={
        'cartomancy_type': 'Runes',
        'rows': [{'name': 'Fehu', 'rank': '1'}, {'name': 'Uruz'},
                 {'name': 'Fehu'}, {'name': '  '}]})
    data = r.get_json()
    assert data['created'] == 2 and data['skipped'] == 1

    t = _type_by_name(client, 'Runes')
    deck = client.post('/api/decks', json={
        'name': 'Rune Set', 'type_ids': [t['id']]}).get_json()
    for name in ('Fehu', 'Thurisaz', 'Ansuz'):
        client.post('/api/cards', json={'deck_id': deck['id'], 'name': name})
    r = client.post('/api/archetypes/seed-from-deck', json={
        'deck_id': deck['id'], 'cartomancy_type': 'Runes'})
    assert r.get_json()['created'] == 2   # Fehu already existed
    archs = client.get('/api/archetypes?cartomancy_type=Runes').get_json()
    assert {a['name'] for a in archs} == {'Fehu', 'Uruz', 'Thurisaz', 'Ansuz'}
    # Untagged cards got their archetype tag set
    cards = client.get(f"/api/cards?deck_id={deck['id']}").get_json()
    assert cards and all(c['archetype'] for c in cards)


def test_seed_from_deck_carries_rank_and_suit(client, db):
    """Seeding transfers each card's rank/suit onto its archetype, and
    re-running backfills archetypes created before the fix."""
    client.post('/api/types', json={'name': 'Runes'})
    t = _type_by_name(client, 'Runes')
    deck = client.post('/api/decks', json={
        'name': 'Rune Set', 'type_ids': [t['id']]}).get_json()
    card = client.post('/api/cards', json={
        'deck_id': deck['id'], 'name': 'Fehu'}).get_json()
    client.put(f"/api/cards/{card['id']}/metadata",
               json={'rank': '1', 'suit': "Freyr's Aett"})
    card2 = client.post('/api/cards', json={
        'deck_id': deck['id'], 'name': 'Hagalaz'}).get_json()
    client.put(f"/api/cards/{card2['id']}/metadata",
               json={'rank': '9', 'suit': "Heimdall's Aett"})

    # Simulate a pre-fix pass: Fehu already exists with no rank/suit
    client.post('/api/archetypes', json={
        'cartomancy_type': 'Runes', 'name': 'Fehu'})

    r = client.post('/api/archetypes/seed-from-deck', json={
        'deck_id': deck['id'], 'cartomancy_type': 'Runes'})
    assert r.get_json()['created'] == 1   # Hagalaz; Fehu existed

    archs = {a['name']: a for a in
             client.get('/api/archetypes?cartomancy_type=Runes').get_json()}
    assert archs['Hagalaz']['rank'] == '9'
    assert archs['Hagalaz']['suit'] == "Heimdall's Aett"
    # The pre-existing bare archetype got backfilled
    assert archs['Fehu']['rank'] == '1'
    assert archs['Fehu']['suit'] == "Freyr's Aett"
