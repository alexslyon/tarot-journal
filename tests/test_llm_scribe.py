"""LLM provider config routes + Scribe extraction/apply."""
import io
import zipfile
from unittest.mock import patch

def test_llm_config_roundtrip(client):
    r = client.get('/api/llm/config')
    assert r.status_code == 200
    data = r.get_json()
    assert data['provider'] == 'anthropic'
    assert data['model'] == 'claude-opus-5'
    assert data['has_api_key'] is False

    r = client.put('/api/llm/config', json={
        'provider': 'openai-compatible',
        'base_url': 'http://localhost:11434/v1/',
        'model': 'llama3',
        'api_key': 'secret-key-12345',
    })
    assert r.status_code == 200

    r = client.get('/api/llm/config')
    data = r.get_json()
    assert data['provider'] == 'openai-compatible'
    assert data['base_url'] == 'http://localhost:11434/v1'  # trailing slash stripped
    assert data['model'] == 'llama3'
    assert data['has_api_key'] is True
    assert 'secret-key-12345' not in r.get_data(as_text=True)
    assert data['api_key_hint'] == '…2345'

    r = client.put('/api/llm/config', json={'provider': 'bogus'})
    assert r.status_code == 400

def test_llm_chat_requires_messages(client):
    r = client.post('/api/llm/chat', json={})
    assert r.status_code == 400

def test_openai_style_wire_format(client):
    client.put('/api/llm/config', json={
        'provider': 'openai-compatible',
        'base_url': 'http://fake-server/v1',
        'model': 'test-model',
    })
    captured = {}
    class FakeResp:
        status_code = 200
        def json(self):
            return {'choices': [{'message': {'content': 'hello back'}}]}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured['url'] = url; captured['body'] = json
        return FakeResp()
    with patch('backend.services.llm.requests.post', side_effect=fake_post):
        r = client.post('/api/llm/chat', json={
            'messages': [{'role': 'user', 'content': [
                {'type': 'text', 'text': 'hi'},
                {'type': 'image', 'media_type': 'image/png', 'data': 'AAAA'},
            ]}],
            'system': 'be brief',
        })
    assert r.status_code == 200
    assert r.get_json()['text'] == 'hello back'
    assert captured['url'] == 'http://fake-server/v1/chat/completions'
    msgs = captured['body']['messages']
    assert msgs[0] == {'role': 'system', 'content': 'be brief'}
    parts = msgs[1]['content']
    assert parts[1]['image_url']['url'].startswith('data:image/png;base64,')

def test_anthropic_requires_key(client):
    client.put('/api/llm/config', json={'provider': 'anthropic', 'api_key': ''})
    r = client.post('/api/llm/chat', json={'messages': [{'role': 'user', 'content': 'hi'}]})
    assert r.status_code == 502
    assert 'API key' in r.get_json()['error']




def make_epub():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('mimetype', 'application/epub+zip')
        z.writestr('META-INF/container.xml', '''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
 <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>''')
        z.writestr('OEBPS/content.opf', '''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
 <manifest>
  <item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
  <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
 </manifest>
 <spine><itemref idref="ch1"/><itemref idref="ch2"/></spine>
</package>''')
        z.writestr('OEBPS/ch1.xhtml', '<html><body><h1>The Fool</h1><p>New beginnings &amp; leaps of faith.</p></body></html>')
        z.writestr('OEBPS/ch2.xhtml', '<html><body><h1>The Magician</h1><p>Will and skill.</p></body></html>')
    return buf.getvalue()

def test_epub_extraction(client):
    r = client.post('/api/scribe/extract-text',
                    data={'file': (io.BytesIO(make_epub()), 'book.epub')},
                    content_type='multipart/form-data')
    assert r.status_code == 200, r.get_json()
    data = r.get_json()
    # Spine order respected: Fool chapter before Magician
    assert data['text'].index('The Fool') < data['text'].index('The Magician')
    assert 'New beginnings & leaps' in data['text']
    assert data['warning'] is None

def test_txt_and_unsupported(client):
    r = client.post('/api/scribe/extract-text',
                    data={'file': (io.BytesIO('hello world'.encode()), 'notes.txt')},
                    content_type='multipart/form-data')
    assert r.status_code == 200 and r.get_json()['text'] == 'hello world'
    r = client.post('/api/scribe/extract-text',
                    data={'file': (io.BytesIO(b'x'), 'thing.docx')},
                    content_type='multipart/form-data')
    assert r.status_code == 422

def test_apply_writes(client, db):
    # archetype target: need an archetype + source field
    types = client.get('/api/types').get_json()
    tname = types[0]['name']
    src = client.post('/api/reference/sources',
                      json={'name': 'Test Book', 'cartomancy_types': [tname]}).get_json()
    field = client.post(f"/api/reference/sources/{src['id']}/fields",
                        json={'name': 'Meaning', 'cartomancy_type': tname}).get_json()
    archetypes = client.get(f'/api/archetypes?cartomancy_type={tname}').get_json()
    arch_id = archetypes[0]['id']

    # card target: create deck + card
    deck = client.post('/api/decks', json={'name': 'Scribe Deck', 'type_ids': [types[0]['id']]}).get_json()
    card = client.post('/api/cards', json={'deck_id': deck['id'], 'name': 'Test Card'}).get_json()

    r = client.post('/api/scribe/apply', json={'writes': [
        {'target': 'archetype', 'archetype_id': arch_id, 'field_id': field['id'], 'content': 'A meaning.'},
        {'target': 'card', 'card_id': card['id'], 'field_name': 'Keywords', 'content': 'alpha, beta'},
        {'target': 'card', 'card_id': card['id'], 'field_name': 'keywords', 'content': 'gamma'},  # upsert same field
        {'target': 'bogus'},
    ]})
    assert r.status_code == 200
    data = r.get_json()
    assert data['applied'] == 3
    assert len(data['errors']) == 1 and data['errors'][0]['index'] == 3

    fields = client.get(f"/api/cards/{card['id']}/custom-fields").get_json()
    kw = [f for f in fields if f['field_name'].lower() == 'keywords']
    assert len(kw) == 1 and kw[0]['field_value'] == 'gamma'

    entries = client.get(f"/api/archetypes/{arch_id}/source-entries").get_json()
    assert any(e.get('content') == 'A meaning.' for e in entries)


def test_anthropic_prompt_caching_shape(client):
    """The Anthropic call caches the system prompt and marks the end of
    the conversation, so refinement turns re-read the book at ~10% price."""
    client.put('/api/llm/config', json={
        'provider': 'anthropic', 'api_key': 'sk-ant-test', 'model': 'claude-opus-5',
    })

    captured = {}

    class FakeStream:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get_final_message(self):
            class Block:
                type = 'text'
                text = 'extracted!'
            class Msg:
                stop_reason = 'end_turn'
                content = [Block()]
            return Msg()

    class FakeMessages:
        def stream(self, **kwargs):
            captured.update(kwargs)
            return FakeStream()

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    with patch('anthropic.Anthropic', FakeClient):
        r = client.post('/api/llm/chat', json={
            'system': 'You are the Scribe.',
            'messages': [
                {'role': 'user', 'content': [{'type': 'text', 'text': 'book text here'}]},
                {'role': 'assistant', 'content': 'proposals...'},
                {'role': 'user', 'content': 'fix the Queen of Cups'},
            ],
        })

    assert r.status_code == 200 and r.get_json()['text'] == 'extracted!'
    # System prompt carries a cache marker
    assert captured['system'][0]['cache_control'] == {'type': 'ephemeral'}
    msgs = captured['messages']
    # Only the LAST message is marked; earlier ones stay unmarked so the
    # cached prefix bytes are identical across turns
    assert 'cache_control' not in msgs[0]['content'][-1]
    assert isinstance(msgs[1]['content'], str)
    # Final message: string content converted to block form + marked
    assert msgs[2]['content'][-1]['cache_control'] == {'type': 'ephemeral'}
    assert msgs[2]['content'][-1]['text'] == 'fix the Queen of Cups'
