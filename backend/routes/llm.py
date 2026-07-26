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
    return jsonify({
        'provider': config['provider'],
        'model': config['model'],
        'base_url': config['base_url'],
        'has_api_key': bool(key),
        'api_key_hint': f"…{key[-4:]}" if len(key) >= 8 else '',
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
    """Round-trip a trivial prompt to verify the configuration works."""
    db = current_app.config['DB']
    config = llm.get_config(db)
    try:
        reply = llm.test_connection(config)
    except llm.LLMError as e:
        return jsonify({'ok': False, 'error': str(e)}), 502
    return jsonify({'ok': True, 'model': config['model'], 'reply': reply.strip()[:200]})


@llm_bp.route('/api/llm/chat', methods=['POST'])
def llm_chat():
    """Generic chat completion for in-app assistant features.

    Body: {"messages": [...], "system": "...", "max_tokens": 8192}
    Reply: {"text": "..."}
    """
    db = current_app.config['DB']
    config = llm.get_config(db)
    data = request.get_json() or {}
    messages = data.get('messages') or []
    if not messages:
        return jsonify({'error': 'messages is required'}), 400
    max_tokens = min(int(data.get('max_tokens') or llm.DEFAULT_MAX_TOKENS), 32000)
    try:
        text = llm.chat(config, messages, system=data.get('system'),
                        max_tokens=max_tokens)
    except llm.LLMError as e:
        return jsonify({'error': str(e)}), 502
    return jsonify({'text': text})
