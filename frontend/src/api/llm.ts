import api from './client';

// ── AI assistant (multi-provider LLM) ────────────────────────

export type LlmProvider = 'anthropic' | 'openai' | 'openai-compatible';

export type LlmFeature = 'scribe' | 'mirror' | 'analyst';

export interface LlmConfig {
  provider: LlmProvider;
  model: string;
  base_url: string;
  has_api_key: boolean;
  api_key_hint: string;
  /** Per-feature model overrides; '' means "use the default model". */
  feature_models: Record<LlmFeature, string>;
}

/** One message in the neutral chat shape the backend accepts. */
export interface LlmMessagePart {
  type: 'text' | 'image';
  text?: string;
  media_type?: string;
  data?: string; // base64
}
export interface LlmMessage {
  role: 'user' | 'assistant';
  content: string | LlmMessagePart[];
}

export async function getLlmConfig(): Promise<LlmConfig> {
  const res = await api.get('/api/llm/config');
  return res.data;
}

export async function updateLlmConfig(data: {
  provider?: LlmProvider;
  model?: string;
  base_url?: string;
  api_key?: string;
  feature_models?: Partial<Record<LlmFeature, string>>;
}): Promise<void> {
  await api.put('/api/llm/config', data);
}

export async function testLlmConnection(): Promise<{ ok: boolean; model?: string; reply?: string; error?: string }> {
  try {
    const res = await api.post('/api/llm/test');
    return res.data;
  } catch (err: unknown) {
    const e = err as { response?: { data?: { error?: string } } };
    return { ok: false, error: e.response?.data?.error || 'Connection test failed.' };
  }
}

/** Generic chat completion. Long timeout — extractions can take minutes.
 *  `truncated` means the model hit its reply-length limit mid-answer. */
export async function llmChat(data: {
  messages: LlmMessage[];
  system?: string;
  max_tokens?: number;
  /** Selects that feature's model override, when one is configured. */
  feature?: LlmFeature;
  /** false = one-shot request whose content will never be re-sent;
   *  skips the prompt-cache write surcharge on the conversation. */
  cache?: boolean;
}): Promise<{ text: string; truncated: boolean }> {
  // A maxed-out (64k-token) reply can take over 15 minutes to
  // generate; the wait ceiling must sit above the worst case, or the
  // app abandons (but still pays for) an almost-finished reply.
  const res = await api.post('/api/llm/chat', data, { timeout: 1_260_000 });
  return res.data;
}
