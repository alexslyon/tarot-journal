"""
LLM assistant routes — configuration, connection test, and chat.

The API key is write-only from the frontend's perspective: GET returns
whether a key exists (plus a hint of its last characters) but never the
key itself.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from backend.services import llm

llm_bp = Blueprint('llm', __name__)


@llm_bp.route('/api/llm/config')
def get_llm_config():
    db = current_app.config['DB']
    config = llm.get_config(db)
    key = config['api_key']
    api_keys = {}
    for provider in llm.PROVIDERS:
        pkey = llm.get_api_key(db, provider)
        api_keys[provider] = {
            'has_key': bool(pkey),
            'hint': f"…{pkey[-4:]}" if len(pkey) >= 8 else '',
        }
    return jsonify({
        'provider': config['provider'],
        'model': config['model'],
        'base_url': config['base_url'],
        'has_api_key': bool(key),
        'api_key_hint': f"…{key[-4:]}" if len(key) >= 8 else '',
        'feature_models': config['feature_models'],
        'feature_providers': config['feature_providers'],
        'api_keys': api_keys,
    })


@llm_bp.route('/api/llm/config', methods=['PUT'])
def update_llm_config():
    db = current_app.config['DB']
    data = request.get_json() or {}
    try:
        llm.save_config(db, data)
    except llm.LLMError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True})


@llm_bp.route('/api/llm/test', methods=['POST'])
def test_llm():
    """Round-trip a trivial prompt to verify the configuration works.
    Body may carry {"feature": "scribe"|"mirror"|"analyst"} to test
    that feature's resolved provider/model instead of the default."""
    db = current_app.config['DB']
    data = request.get_json(silent=True) or {}
    config = llm.get_config(db, feature=data.get('feature'))
    try:
        reply = llm.test_connection(config)
    except llm.LLMError as e:
        return jsonify({'ok': False, 'error': str(e)}), 502
    return jsonify({
        'ok': True,
        'provider': config['provider'],
        'model': config['model'],
        'reply': reply.strip()[:200],
    })


@llm_bp.route('/api/llm/chat', methods=['POST'])
def llm_chat():
    """Generic chat completion for in-app assistant features.

    Body: {"messages": [...], "system": "...", "max_tokens": 8192}
    Reply: {"text": "..."}
    """
    db = current_app.config['DB']
    data = request.get_json() or {}
    # A feature name ("scribe" / "mirror" / "analyst") selects that
    # feature's model override, when one is configured.
    config = llm.get_config(db, feature=data.get('feature'))
    messages = data.get('messages') or []
    if not messages:
        return jsonify({'error': 'messages is required'}), 400
    max_tokens = min(int(data.get('max_tokens') or llm.DEFAULT_MAX_TOKENS), 64000)
    try:
        result = llm.chat(config, messages, system=data.get('system'),
                          max_tokens=max_tokens,
                          cache_conversation=bool(data.get('cache', True)),
                          thinking=bool(data.get('thinking', False)))
    except llm.LLMError as e:
        return jsonify({'error': str(e)}), 502
    return jsonify(result)
