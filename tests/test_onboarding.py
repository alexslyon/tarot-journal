"""Tests for the onboarding endpoints: first-run flags and the
consented starter-spread seeding."""

import json


def test_flags_roundtrip(client, db):
    flags = client.get('/api/onboarding/flags').get_json()
    assert flags == {'welcome_done': False, 'checklist_dismissed': False}

    client.put('/api/onboarding/flags', json={'welcome_done': True})
    flags = client.get('/api/onboarding/flags').get_json()
    assert flags['welcome_done'] is True
    assert flags['checklist_dismissed'] is False

    client.put('/api/onboarding/flags', json={'checklist_dismissed': True})
    assert client.get('/api/onboarding/flags').get_json() == {
        'welcome_done': True, 'checklist_dismissed': True}


def test_starter_spreads_seed_and_idempotency(client, db):
    res = client.post('/api/onboarding/starter-spreads')
    assert res.status_code == 200
    body = res.get_json()
    assert 'Celtic Cross' in body['added']
    assert len(body['added']) == 5 and body['skipped'] == []

    spreads = {s['name']: s for s in db.get_spreads()}
    assert len(spreads) == 5
    # Positions land in the designer's format
    celtic = spreads['Celtic Cross']
    positions = celtic['positions']
    if isinstance(positions, str):
        positions = json.loads(positions)
    assert len(positions) == 10
    assert {'x', 'y', 'width', 'height', 'label'} <= set(positions[0])
    assert any(p.get('rotated') for p in positions), 'crossing card rotates'

    # Second click: everything skipped, nothing duplicated
    again = client.post('/api/onboarding/starter-spreads').get_json()
    assert again['added'] == [] and len(again['skipped']) == 5
    assert len(db.get_spreads()) == 5


def test_starter_spreads_respect_existing_names(client, db):
    db.add_spread(name='Celtic Cross', positions=[
        {'x': 0, 'y': 0, 'width': 80, 'height': 120, 'label': 'Mine'}])
    body = client.post('/api/onboarding/starter-spreads').get_json()
    assert 'Celtic Cross' in body['skipped']
    # The user's own version is untouched
    mine = next(s for s in db.get_spreads() if s['name'] == 'Celtic Cross')
    positions = mine['positions']
    if isinstance(positions, str):
        positions = json.loads(positions)
    assert positions[0]['label'] == 'Mine'
