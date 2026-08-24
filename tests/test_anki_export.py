"""Anki export: the Classification fields (archetype / rank / suit,
with the card modal's I Ching aliases) are selectable and exported."""

import io
import zipfile


def _make_deck(client, type_name):
    types = client.get('/api/types').get_json()
    t = next(x for x in types if x['name'] == type_name)
    return client.post('/api/decks', json={
        'name': f'{type_name} Anki Deck', 'type_ids': [t['id']]}).get_json()


def _field_map(client, deck_id):
    rows = client.get(f'/api/decks/{deck_id}/anki-fields').get_json()
    return {f['key']: f for f in rows}


def test_classification_fields_listed_and_labeled(client, db):
    deck = _make_deck(client, 'Tarot')
    card = client.post('/api/cards', json={
        'deck_id': deck['id'], 'name': 'The Fool'}).get_json()
    client.put(f"/api/cards/{card['id']}/metadata", json={
        'archetype': 'The Fool', 'rank': '0', 'suit': 'Major Arcana'})

    fields = _field_map(client, deck['id'])
    assert fields['archetype']['label'] == 'Archetype'
    assert fields['rank']['label'] == 'Rank'
    assert fields['suit']['label'] == 'Suit'
    assert fields['archetype']['populated'] is True
    assert 'traditional_chinese' not in fields   # I Ching only


def test_iching_aliases(client, db):
    deck = _make_deck(client, 'I Ching')
    client.post('/api/cards', json={'deck_id': deck['id'], 'name': 'Qian'})
    fields = _field_map(client, deck['id'])
    assert fields['rank']['label'] == 'Hexagram Number'
    assert fields['suit']['label'] == 'Pinyin'
    assert fields['traditional_chinese']['label'] == 'Traditional Chinese'
    assert fields['simplified_chinese']['label'] == 'Simplified Chinese'
    assert fields['rank']['populated'] is False


def test_export_includes_classification_values(client, db):
    deck = _make_deck(client, 'Tarot')
    card = client.post('/api/cards', json={
        'deck_id': deck['id'], 'name': 'The Fool'}).get_json()
    client.put(f"/api/cards/{card['id']}/metadata", json={
        'archetype': 'The Fool', 'rank': '0', 'suit': 'Major Arcana'})

    res = client.post(f"/api/decks/{deck['id']}/anki-export", json={
        'fields': ['name', 'archetype', 'rank', 'suit']})
    assert res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(res.data)) as zf:
        text = zf.read('cards.txt').decode('utf-8')
    lines = text.splitlines()
    assert '#Card Name\tArchetype\tRank\tSuit' in lines
    assert 'The Fool\tThe Fool\t0\tMajor Arcana' in lines
