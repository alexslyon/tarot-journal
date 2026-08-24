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
