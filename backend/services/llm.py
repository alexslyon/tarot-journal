"""
Multi-provider LLM access layer.

The app talks to exactly one configured "assistant" at a time, chosen in
Settings → AI. Three provider styles are supported:

  - "anthropic"          → Claude, via the official anthropic SDK
  - "openai"             → ChatGPT, via api.openai.com
  - "openai-compatible"  → anything speaking the OpenAI chat format at a
                           custom URL (Ollama, LM Studio, llama.cpp, etc.)

Everything above this module speaks one neutral message shape, so the
Scribe / chat features don't care which provider is active:

  messages = [{"role": "user"|"assistant", "content": <str or parts>}]
  part     = {"type": "text", "text": "..."}
           | {"type": "image", "media_type": "image/png", "data": "<b64>"}

Configuration lives in the settings table (llm_provider, llm_api_key,
llm_base_url, llm_model). The API key is stored in the local database —
fine for a personal desktop app, but worth knowing.
"""

from __future__ import annotations

import requests

# Timeouts are generous: a Scribe extraction over a whole book chapter
# can legitimately take minutes.
REQUEST_TIMEOUT = 600  # seconds
DEFAULT_MAX_TOKENS = 8192

DEFAULT_MODELS = {
    'anthropic': 'claude-opus-5',
    'openai': 'gpt-4o',
    'openai-compatible': '',
}

PROVIDERS = ('anthropic', 'openai', 'openai-compatible')


class LLMError(Exception):
    """A provider call failed; .args[0] is a user-readable message."""


# ── Configuration ────────────────────────────────────────────────────

def get_config(db) -> dict:
    provider = db.get_setting('llm_provider') or 'anthropic'
    if provider not in PROVIDERS:
        provider = 'anthropic'
    return {
        'provider': provider,
        'api_key': db.get_setting('llm_api_key') or '',
        'base_url': db.get_setting('llm_base_url') or '',
        'model': db.get_setting('llm_model') or DEFAULT_MODELS.get(provider, ''),
    }


def save_config(db, data: dict) -> None:
    if 'provider' in data:
        provider = data['provider']
        if provider not in PROVIDERS:
            raise LLMError(f"Unknown provider: {provider}")
        db.set_setting('llm_provider', provider)
    if 'api_key' in data:
        db.set_setting('llm_api_key', data['api_key'] or '')
    if 'base_url' in data:
        db.set_setting('llm_base_url', (data['base_url'] or '').rstrip('/'))
    if 'model' in data:
        db.set_setting('llm_model', data['model'] or '')


# ── The one call everything uses ─────────────────────────────────────

def chat(config: dict, messages: list, system: str | None = None,
         max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Send a conversation, return the assistant's text reply."""
    provider = config.get('provider') or 'anthropic'
    model = config.get('model') or DEFAULT_MODELS.get(provider)
    if not model:
        raise LLMError("No model configured. Set one in Settings → AI.")
    if provider == 'anthropic':
        return _chat_anthropic(config, model, messages, system, max_tokens)
    return _chat_openai_style(config, model, messages, system, max_tokens)


def test_connection(config: dict) -> str:
    """Tiny round-trip to verify provider/key/model. Returns the reply."""
    return chat(
        config,
        [{'role': 'user', 'content': "Reply with the single word: OK"}],
        max_tokens=1024,
    )


# ── Anthropic (official SDK) ─────────────────────────────────────────

def _chat_anthropic(config, model, messages, system, max_tokens) -> str:
    import anthropic

    if not config.get('api_key'):
        raise LLMError("No API key set. Add your Anthropic key in Settings → AI.")
    client = anthropic.Anthropic(api_key=config['api_key'],
                                 timeout=float(REQUEST_TIMEOUT))
    kwargs = {}
    if system:
        # The system prompt is stable for a whole Scribe session — cache
        # it so refinement turns don't re-bill it at full price.
        kwargs['system'] = [{
            'type': 'text',
            'text': system,
            'cache_control': {'type': 'ephemeral'},
        }]
    converted = [_to_anthropic_message(m) for m in messages]
    # Prompt caching: mark the end of the conversation so the next turn
    # re-reads everything before it (book text included) at ~10% of the
    # normal input price instead of full price. Prefixes shorter than
    # the model's minimum just silently don't cache — no harm done.
    if converted:
        _mark_cache_breakpoint(converted[-1])
    try:
        # Streaming keeps long extractions from hitting HTTP timeouts;
        # get_final_message() collects the whole reply for us.
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=converted,
            **kwargs,
        ) as stream:
            response = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise LLMError("Anthropic rejected the API key. Check it in Settings → AI.")
    except anthropic.NotFoundError:
        raise LLMError(f"Model '{model}' not found. Check the model name in Settings → AI.")
    except anthropic.RateLimitError:
        raise LLMError("Anthropic rate limit hit. Wait a minute and try again.")
    except anthropic.APIStatusError as e:
        raise LLMError(f"Anthropic API error ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        raise LLMError("Could not reach the Anthropic API. Check your internet connection.")

    if response.stop_reason == 'refusal':
        raise LLMError("The model declined this request (safety refusal).")
    text = ''.join(b.text for b in response.content if b.type == 'text')
    if not text:
        raise LLMError("The model returned an empty response.")
    return text


def _mark_cache_breakpoint(msg: dict) -> None:
    """Put a cache_control marker on the message's last content block
    (converting plain-string content to block form if needed)."""
    content = msg['content']
    if isinstance(content, str):
        content = [{'type': 'text', 'text': content}]
        msg['content'] = content
    if content:
        content[-1]['cache_control'] = {'type': 'ephemeral'}


def _to_anthropic_message(msg: dict) -> dict:
    content = msg['content']
    if isinstance(content, str):
        return {'role': msg['role'], 'content': content}
    parts = []
    for p in content:
        if p['type'] == 'text':
            parts.append({'type': 'text', 'text': p['text']})
        elif p['type'] == 'image':
            parts.append({
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': p['media_type'],
                    'data': p['data'],
                },
            })
    return {'role': msg['role'], 'content': parts}


# ── OpenAI & OpenAI-compatible (raw HTTP; shared wire format) ────────

def _chat_openai_style(config, model, messages, system, max_tokens) -> str:
    provider = config.get('provider')
    if provider == 'openai':
        base_url = 'https://api.openai.com/v1'
        if not config.get('api_key'):
            raise LLMError("No API key set. Add your OpenAI key in Settings → AI.")
    else:
        base_url = (config.get('base_url') or '').rstrip('/')
        if not base_url:
            raise LLMError(
                "No server URL set. Enter your local server's URL in "
                "Settings → AI (e.g. http://localhost:11434/v1 for Ollama)."
            )

    headers = {'Content-Type': 'application/json'}
    if config.get('api_key'):
        headers['Authorization'] = f"Bearer {config['api_key']}"

    wire_messages = []
    if system:
        wire_messages.append({'role': 'system', 'content': system})
    wire_messages.extend(_to_openai_message(m) for m in messages)

    body = {'model': model, 'messages': wire_messages, 'max_tokens': max_tokens}
    data = _post_openai(base_url, headers, body)
    # Newer OpenAI models reject max_tokens in favor of
    # max_completion_tokens; retry once with the newer name.
    if data is None:
        body.pop('max_tokens')
        body['max_completion_tokens'] = max_tokens
        data = _post_openai(base_url, headers, body, retry_token_param=False)

    try:
        text = data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise LLMError("The server returned an unexpected response format.")
    if not text:
        raise LLMError("The model returned an empty response.")
    return text


def _post_openai(base_url, headers, body, retry_token_param=True):
    """POST to /chat/completions. Returns parsed JSON, or None when the
    server rejected the max_tokens parameter name (caller retries)."""
    try:
        resp = requests.post(f"{base_url}/chat/completions", headers=headers,
                             json=body, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.ConnectionError:
        raise LLMError(f"Could not connect to {base_url}. Is the server running?")
    except requests.exceptions.Timeout:
        raise LLMError("The request timed out. The model may be too slow for this task.")

    if resp.status_code == 401:
        raise LLMError("The server rejected the API key. Check it in Settings → AI.")
    if resp.status_code == 404:
        raise LLMError(
            f"Not found at {base_url}/chat/completions — check the server "
            "URL (it usually ends in /v1) and the model name."
        )
    if resp.status_code >= 400:
        detail = ''
        try:
            detail = resp.json().get('error', {}).get('message', '')
        except Exception:
            detail = resp.text[:200]
        if retry_token_param and 'max_tokens' in detail and 'max_completion_tokens' in detail:
            return None
        raise LLMError(f"Server error ({resp.status_code}): {detail or 'unknown error'}")
    try:
        return resp.json()
    except ValueError:
        raise LLMError("The server returned a non-JSON response.")


def _to_openai_message(msg: dict) -> dict:
    content = msg['content']
    if isinstance(content, str):
        return {'role': msg['role'], 'content': content}
    if all(p['type'] == 'text' for p in content):
        # Plain string is the most widely supported shape for local servers
        return {'role': msg['role'],
                'content': '\n\n'.join(p['text'] for p in content)}
    parts = []
    for p in content:
        if p['type'] == 'text':
            parts.append({'type': 'text', 'text': p['text']})
        elif p['type'] == 'image':
            parts.append({
                'type': 'image_url',
                'image_url': {'url': f"data:{p['media_type']};base64,{p['data']}"},
            })
    return {'role': msg['role'], 'content': parts}
