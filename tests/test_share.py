"""Spreads & profiles share export/import roundtrips."""


def test_spreads_roundtrip(client, db):
    tag_id = db.add_spread_tag('Daily', '#123456')
    sid = db.add_spread(
        'Three Card Line', [{'x': 0, 'y': 0, 'label': 'Past'}],
        description='<p>Left to right.</p>',
        deck_slots=[{'key': 'A', 'cartomancy_types': ['Tarot', 'Oracle'],
                     'cartomancy_type': 'Any'}])
    db.set_spread_tags(sid, [tag_id])

    data = client.get('/api/spreads/export').get_json()
    assert data['kind'] == 'spreads'
    s = next(x for x in data['spreads'] if x['name'] == 'Three Card Line')
    assert s['positions'][0]['label'] == 'Past'
    assert s['deck_slots'][0]['cartomancy_types'] == ['Tarot', 'Oracle']
    assert s['tags'] == [{'name': 'Daily', 'color': '#123456'}]

    # Import into the same DB: same-name skip, nothing duplicated
    res = client.post('/api/spreads/import', json=data).get_json()
    assert res['imported'] == 0
    assert 'Three Card Line' in res['skipped']

    # Rename in the payload -> imports fresh, reusing the existing tag
    s['name'] = 'Imported Line'
    res = client.post('/api/spreads/import', json=data).get_json()
    assert res['imported'] == 1 and res['tags_created'] == 0
    spreads = client.get('/api/spreads').get_json()
    imported = next(x for x in spreads if x['name'] == 'Imported Line')
    assert [t['name'] for t in imported.get('tags', [])] == ['Daily']

    # Unknown tag names get created with their exported color
    s['name'] = 'Third Line'
    s['tags'] = [{'name': 'Brand New', 'color': '#ff0000'}]
    res = client.post('/api/spreads/import', json=data).get_json()
    assert res['imported'] == 1 and res['tags_created'] == 1


def test_spreads_import_rejects_wrong_file(client):
    res = client.post('/api/spreads/import', json={'profiles': []})
    assert res.status_code == 400


def test_profiles_roundtrip(client, db):
    db.add_profile('Lys', full_name='Lysander Example', birth_date='1990-05-05',
                   querent_only=True)
    pid2 = db.add_profile('Config Person', full_name='Con Fig')
    db.update_profile(pid2, name_cards_config='{"y_mode": "always_vowel"}')

    data = client.get('/api/profiles/export').get_json()
    assert data['kind'] == 'profiles'
    lys = next(p for p in data['profiles'] if p['name'] == 'Lys')
    assert lys['full_name'] == 'Lysander Example'
    assert lys['querent_only'] is True
    cfg = next(p for p in data['profiles'] if p['name'] == 'Config Person')
    assert cfg['name_cards_config'] == {'y_mode': 'always_vowel'}

    # Same-name profiles skip
    res = client.post('/api/profiles/import', json=data).get_json()
    assert res['imported'] == 0 and len(res['skipped']) == 2

    # Renamed imports land with config intact
    lys['name'] = 'Lys (imported)'
    cfg['name'] = 'Config Person (imported)'
    res = client.post('/api/profiles/import', json=data).get_json()
    assert res['imported'] == 2
    profs = client.get('/api/profiles').get_json()
    got = next(p for p in profs if p['name'] == 'Config Person (imported)')
    assert '"always_vowel"' in (got['name_cards_config'] or '')
    got2 = next(p for p in profs if p['name'] == 'Lys (imported)')
    assert got2['full_name'] == 'Lysander Example'


def test_profiles_export_subset(client, db):
    a = db.add_profile('Only Me')
    db.add_profile('Not Me')
    data = client.get(f'/api/profiles/export?ids={a}').get_json()
    assert [p['name'] for p in data['profiles']] == ['Only Me']


def test_spread_source_attribution(client):
    """Spreads can be attributed to a reference source: set, hydrated
    with the name, cleared with an explicit null, survives cloning,
    nulled when the source is deleted."""
    sid = client.post('/api/reference/sources', json={
        'name': 'ZZ Spread Book', 'cartomancy_types': ['Tarot'],
    }).get_json()['id']
    spread = client.post('/api/spreads', json={
        'name': 'ZZ Attributed Spread',
        'positions': [{'x': 0, 'y': 0, 'label': '1'}],
        'source_id': sid,
    }).get_json()

    got = client.get(f"/api/spreads/{spread['id']}").get_json()
    assert got['source_id'] == sid
    assert got['source_name'] == 'ZZ Spread Book'

    # Clone carries the attribution
    clone = client.post(f"/api/spreads/{spread['id']}/clone", json={}).get_json()
    assert client.get(f"/api/spreads/{clone['id']}").get_json()['source_id'] == sid

    # Updating without mentioning source_id leaves it alone
    client.put(f"/api/spreads/{spread['id']}", json={'name': 'ZZ Attributed Spread'})
    assert client.get(f"/api/spreads/{spread['id']}").get_json()['source_id'] == sid
    # Explicit null clears it
    client.put(f"/api/spreads/{spread['id']}", json={'source_id': None})
    assert client.get(f"/api/spreads/{spread['id']}").get_json()['source_id'] is None

    # Deleting the source nulls remaining attributions (the clone's)
    client.put(f"/api/spreads/{spread['id']}", json={'source_id': sid})
    client.delete(f'/api/reference/sources/{sid}')
    assert client.get(f"/api/spreads/{spread['id']}").get_json()['source_id'] is None


def test_spread_share_carries_source(client):
    """Share export names the source; import matches an existing source
    or creates one typed by the spread's deck types."""
    sid = client.post('/api/reference/sources', json={
        'name': 'ZZ Travelling Book', 'cartomancy_types': ['Tarot'],
    }).get_json()['id']
    spread = client.post('/api/spreads', json={
        'name': 'ZZ Travelling Spread',
        'positions': [{'x': 0, 'y': 0, 'label': '1'}],
        'allowed_deck_types': ['Tarot'],
        'source_id': sid,
    }).get_json()

    export = client.get(f"/api/spreads/export?ids={spread['id']}").get_json()
    assert export['spreads'][0]['source'] == 'ZZ Travelling Book'

    # Re-import under a new name: source matched by name, not recreated
    export['spreads'][0]['name'] = 'ZZ Travelled Spread'
    r = client.post('/api/spreads/import', json={'data': export}).get_json()
    assert (r['imported'], r['sources_created']) == (1, 0)
    imported = next(s for s in client.get('/api/spreads').get_json()
                    if s['name'] == 'ZZ Travelled Spread')
    assert imported['source_id'] == sid

    # Unknown source name: created on the fly
    export['spreads'][0]['name'] = 'ZZ Twice Travelled'
    export['spreads'][0]['source'] = 'ZZ Brand New Book'
    r = client.post('/api/spreads/import', json={'data': export}).get_json()
    assert (r['imported'], r['sources_created']) == (1, 1)
    names = {s['name'] for s in client.get('/api/reference/sources').get_json()}
    assert 'ZZ Brand New Book' in names
