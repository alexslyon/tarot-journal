"""
Multi-provider LLM access layer.

Each assistant feature (Scribe / Mirror / Analyst) can talk to its own
provider, or fall back to the default assistant chosen in Settings → AI.
Four provider styles are supported:

  - "anthropic"          → Claude, via the official anthropic SDK
  - "openai"             → ChatGPT, via api.openai.com
  - "deepseek"           → DeepSeek, via api.deepseek.com (OpenAI wire
                           format; text-only — no image understanding)
  - "openai-compatible"  → anything speaking the OpenAI chat format at a
                           custom URL (Ollama, LM Studio, llama.cpp, etc.)

Everything above this module speaks one neutral message shape, so the
Scribe / chat features don't care which provider is active:

  messages = [{"role": "user"|"assistant", "content": <str or parts>}]
  part     = {"type": "text", "text": "..."}
           | {"type": "image", "media_type": "image/png", "data": "<b64>"}

Configuration lives in the settings table: llm_provider + llm_model for
the default assistant, llm_provider_<feature> / llm_model_<feature> for
per-feature overrides, and one API key per provider
(llm_api_key_<provider>; the pre-multi-provider llm_api_key is still
read as the default provider's key). Keys are stored in the local
database — fine for a personal desktop app, but worth knowing.
"""

from __future__ import annotations

import requests

from logger_config import get_logger

logger = get_logger(__name__)

# Timeouts are generous: a Scribe extraction over a whole book chapter
# can legitimately take minutes.
REQUEST_TIMEOUT = 600  # seconds
DEFAULT_MAX_TOKENS = 8192

DEFAULT_MODELS = {
    'anthropic': 'claude-opus-5',
    'openai': 'gpt-4o',
    'deepseek': 'deepseek-chat',
    'openai-compatible': '',
}

PROVIDERS = ('anthropic', 'openai', 'deepseek', 'openai-compatible')

DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'

# Features that may override the default provider/model (Settings → AI).
FEATURES = ('scribe', 'mirror', 'analyst')


class LLMError(Exception):
    """A provider call failed; .args[0] is a user-readable message."""


# ── Configuration ────────────────────────────────────────────────────

def get_api_key(db, provider: str) -> str:
    """The stored key for a provider. The pre-multi-provider single key
    (llm_api_key) still counts, but only for the default provider — it
    was entered for that one, and must never leak to another service."""
    key = db.get_setting(f'llm_api_key_{provider}') or ''
    if not key:
        default_provider = db.get_setting('llm_provider') or 'anthropic'
        if provider == default_provider:
            key = db.get_setting('llm_api_key') or ''
    return key


def get_config(db, feature: str | None = None) -> dict:
    """The LLM configuration resolved for `feature` (or the default
    assistant when feature is None / has no overrides).

    Resolution: a feature with its own provider uses that provider and
    its own model (or the provider's default model — the global model
    name belongs to the default provider). A feature with only a model
    override keeps the default provider. The API key always follows the
    resolved provider."""
    default_provider = db.get_setting('llm_provider') or 'anthropic'
    if default_provider not in PROVIDERS:
        default_provider = 'anthropic'
    default_model = db.get_setting('llm_model') or DEFAULT_MODELS.get(default_provider, '')

    feature_models = {
        f: db.get_setting(f'llm_model_{f}') or '' for f in FEATURES
    }
    feature_providers = {}
    for f in FEATURES:
        p = db.get_setting(f'llm_provider_{f}') or ''
        feature_providers[f] = p if p in PROVIDERS else ''

    provider = default_provider
    model = default_model
    if feature in FEATURES:
        if feature_providers[feature]:
            provider = feature_providers[feature]
            if provider == default_provider:
                model = feature_models[feature] or default_model
            else:
                model = feature_models[feature] or DEFAULT_MODELS.get(provider, '')
        elif feature_models[feature]:
            model = feature_models[feature]

    return {
        'provider': provider,
        'api_key': get_api_key(db, provider),
        'base_url': db.get_setting('llm_base_url') or '',
        'model': model,
        'feature_models': feature_models,
        'feature_providers': feature_providers,
    }


def save_config(db, data: dict) -> None:
    if 'provider' in data:
        provider = data['provider']
        if provider not in PROVIDERS:
            raise LLMError(f"Unknown provider: {provider}")
        db.set_setting('llm_provider', provider)
    if 'api_key' in data:
        # Legacy single-key write: store it as the (possibly just
        # updated) default provider's key.
        provider = db.get_setting('llm_provider') or 'anthropic'
        db.set_setting(f'llm_api_key_{provider}', data['api_key'] or '')
        db.set_setting('llm_api_key', '')
    if 'api_keys' in data:
        for provider, key in (data['api_keys'] or {}).items():
            if provider not in PROVIDERS:
                raise LLMError(f"Unknown provider: {provider}")
            db.set_setting(f'llm_api_key_{provider}', key or '')
            # A per-provider write supersedes the legacy single key for
            # that provider; clear it so an emptied key stays empty.
            if provider == (db.get_setting('llm_provider') or 'anthropic'):
                db.set_setting('llm_api_key', '')
    if 'base_url' in data:
        db.set_setting('llm_base_url', (data['base_url'] or '').rstrip('/'))
    if 'model' in data:
        db.set_setting('llm_model', data['model'] or '')
    if 'feature_models' in data:
        overrides = data['feature_models'] or {}
        for f in FEATURES:
            if f in overrides:
                db.set_setting(f'llm_model_{f}', (overrides[f] or '').strip())
    if 'feature_providers' in data:
        overrides = data['feature_providers'] or {}
        for f in FEATURES:
            if f in overrides:
                p = (overrides[f] or '').strip()
                if p and p not in PROVIDERS:
                    raise LLMError(f"Unknown provider: {p}")
                db.set_setting(f'llm_provider_{f}', p)


# ── The one call everything uses ─────────────────────────────────────

def chat(config: dict, messages: list, system: str | None = None,
         max_tokens: int = DEFAULT_MAX_TOKENS,
         cache_conversation: bool = True,
         thinking: bool = False) -> dict:
    """Send a conversation. Returns {'text': str, 'truncated': bool} —
    truncated means the reply hit max_tokens and is cut off mid-thought,
    which callers should surface rather than silently accept.

    cache_conversation=False marks only the (reused) system prompt for
    prompt caching, not the conversation: one-shot requests whose
    content will never be re-sent — like Scribe part extractions —
    would otherwise pay the cache-write surcharge for nothing."""
    provider = config.get('provider') or 'anthropic'
    model = config.get('model') or DEFAULT_MODELS.get(provider)
    if not model:
        raise LLMError("No model configured. Set one in Settings → AI.")
    if provider == 'anthropic':
        return _chat_anthropic(config, model, messages, system, max_tokens,
                               cache_conversation, thinking)
    # Non-Anthropic providers: the thinking request is quietly ignored.
    return _chat_openai_style(config, model, messages, system, max_tokens)


def test_connection(config: dict) -> str:
    """Tiny round-trip to verify provider/key/model. Returns the reply."""
    return chat(
        config,
        [{'role': 'user', 'content': "Reply with the single word: OK"}],
        max_tokens=1024,
    )['text']


# ── Anthropic (official SDK) ─────────────────────────────────────────

def _chat_anthropic(config, model, messages, system, max_tokens,
                    cache_conversation=True, thinking=False) -> dict:
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
    # One-shot requests skip this (cache writes cost +25%).
    if converted and cache_conversation:
        _mark_cache_breakpoint(converted[-1])
    def _run(with_thinking: bool):
        call_kwargs = dict(kwargs)
        if with_thinking:
            # Adaptive extended thinking — used for the Scribe's audit
            # and refinement turns, where cross-referencing the whole
            # book pays off. Claude 4.6+ models accept it; older ones
            # fall back below.
            call_kwargs['thinking'] = {'type': 'adaptive'}
        # Streaming keeps long extractions from hitting HTTP timeouts;
        # get_final_message() collects the whole reply for us.
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=converted,
            **call_kwargs,
        ) as stream:
            return stream.get_final_message()

    try:
        try:
            response = _run(thinking)
        except anthropic.BadRequestError as e:
            # A model that predates adaptive thinking rejects the
            # parameter — retry once without rather than failing.
            if thinking and 'thinking' in str(e).lower():
                logger.info('model %s rejected thinking; retrying without', model)
                response = _run(False)
            else:
                raise
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

    usage = getattr(response, 'usage', None)
    if usage:
        # cache_write > 0 on a session's first turn, cache_read > 0 on
        # later turns = prompt caching is working end to end.
        logger.info(
            "Anthropic call (%s): input=%s output=%s cache_write=%s cache_read=%s",
            model,
            getattr(usage, 'input_tokens', '?'),
            getattr(usage, 'output_tokens', '?'),
            getattr(usage, 'cache_creation_input_tokens', '?'),
            getattr(usage, 'cache_read_input_tokens', '?'),
        )
    if response.stop_reason == 'refusal':
        raise LLMError("The model declined this request (safety refusal).")
    text = ''.join(b.text for b in response.content if b.type == 'text')
    if not text:
        raise LLMError("The model returned an empty response.")
    return {'text': text, 'truncated': response.stop_reason == 'max_tokens'}


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
    elif provider == 'deepseek':
        base_url = DEEPSEEK_BASE_URL
        if not config.get('api_key'):
            raise LLMError("No API key set. Add your DeepSeek key in Settings → AI.")
        if any(p.get('type') == 'image'
               for m in messages if isinstance(m.get('content'), list)
               for p in m['content']):
            raise LLMError(
                "DeepSeek models can't read images. Use Claude or ChatGPT "
                "for photo imports, or configure one of those for the Scribe."
            )
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
        choice = data['choices'][0]
        text = choice['message']['content']
    except (KeyError, IndexError, TypeError):
        raise LLMError("The server returned an unexpected response format.")
    if not text:
        raise LLMError("The model returned an empty response.")
    return {'text': text, 'truncated': choice.get('finish_reason') == 'length'}


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
