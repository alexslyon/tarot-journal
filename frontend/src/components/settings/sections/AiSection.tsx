import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getLlmConfig,
  updateLlmConfig,
  testLlmConnection,
  type LlmProvider,
  type LlmFeature,
} from '../../../api/llm';
import '../SettingsTab.css';

const PROVIDER_LABELS: { id: LlmProvider; label: string }[] = [
  { id: 'anthropic', label: 'Anthropic (Claude)' },
  { id: 'openai', label: 'OpenAI (ChatGPT)' },
  { id: 'deepseek', label: 'DeepSeek' },
  { id: 'openai-compatible', label: 'Local / other (OpenAI-compatible)' },
];

const MODEL_PLACEHOLDERS: Record<LlmProvider, string> = {
  anthropic: 'claude-opus-5',
  openai: 'gpt-4o',
  deepseek: 'deepseek-chat',
  'openai-compatible': 'e.g. llama3, qwen2.5, mistral…',
};

const KEY_PROVIDERS: { id: LlmProvider; label: string; optional?: boolean }[] = [
  { id: 'anthropic', label: 'Anthropic' },
  { id: 'openai', label: 'OpenAI' },
  { id: 'deepseek', label: 'DeepSeek' },
  { id: 'openai-compatible', label: 'Local / other', optional: true },
];

const FEATURE_LABELS: { id: LlmFeature; label: string; hint: string }[] = [
  { id: 'scribe', label: 'Scribe (book imports)', hint: 'transcription-heavy — a capable model pays off; photo imports need Claude or ChatGPT (DeepSeek is text-only)' },
  { id: 'mirror', label: 'Mirror (reflections)', hint: 'short questions — a fast, cheap model is plenty' },
  { id: 'analyst', label: 'Analyst (journal patterns)', hint: 'reads many entries per question' },
];

const EMPTY_FEATURE_MODELS: Record<LlmFeature, string> = {
  scribe: '', mirror: '', analyst: '',
};
const EMPTY_FEATURE_PROVIDERS: Record<LlmFeature, LlmProvider | ''> = {
  scribe: '', mirror: '', analyst: '',
};
const EMPTY_KEY_INPUTS: Record<LlmProvider, string> = {
  anthropic: '', openai: '', deepseek: '', 'openai-compatible': '',
};

export default function AiSection() {
  const queryClient = useQueryClient();
  const { data: config } = useQuery({
    queryKey: ['llm-config'],
    queryFn: getLlmConfig,
  });

  const [provider, setProvider] = useState<LlmProvider>('anthropic');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [keyInputs, setKeyInputs] = useState<Record<LlmProvider, string>>(EMPTY_KEY_INPUTS);
  const [featureModels, setFeatureModels] = useState<Record<LlmFeature, string>>(EMPTY_FEATURE_MODELS);
  const [featureProviders, setFeatureProviders] = useState<Record<LlmFeature, LlmProvider | ''>>(EMPTY_FEATURE_PROVIDERS);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<'default' | LlmFeature | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Load stored config into the form (keys themselves never arrive —
  // the fields stay blank and only update a key when typed into).
  useEffect(() => {
    if (!config || dirty) return;
    setProvider(config.provider);
    setModel(config.model);
    setBaseUrl(config.base_url);
    setFeatureModels({ ...EMPTY_FEATURE_MODELS, ...(config.feature_models || {}) });
    setFeatureProviders({ ...EMPTY_FEATURE_PROVIDERS, ...(config.feature_providers || {}) });
  }, [config, dirty]);

  const showMsg = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
  };

  const markDirty = () => { setDirty(true); setMessage(null); };

  const handleProviderChange = (p: LlmProvider) => {
    setProvider(p);
    // Switching providers usually means a different model name too;
    // clear it so the placeholder suggests a sensible default.
    setModel('');
    markDirty();
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const typedKeys = Object.fromEntries(
        Object.entries(keyInputs).filter(([, v]) => v.trim() !== ''),
      );
      await updateLlmConfig({
        provider,
        model,
        base_url: baseUrl,
        feature_models: featureModels,
        feature_providers: featureProviders,
        ...(Object.keys(typedKeys).length ? { api_keys: typedKeys } : {}),
      });
      setKeyInputs(EMPTY_KEY_INPUTS);
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ['llm-config'] });
      showMsg('AI settings saved.', 'success');
    } catch {
      showMsg('Failed to save AI settings.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleClearKey = async (p: LlmProvider) => {
    try {
      await updateLlmConfig({ api_keys: { [p]: '' } });
      queryClient.invalidateQueries({ queryKey: ['llm-config'] });
      showMsg('API key removed.', 'success');
    } catch {
      showMsg('Failed to remove the API key.', 'error');
    }
  };

  const handleTest = async (target: 'default' | LlmFeature) => {
    setTesting(target);
    setMessage(null);
    const result = await testLlmConnection(target === 'default' ? undefined : target);
    setTesting(null);
    if (result.ok) {
      const where = target === 'default' ? '' : ` for the ${target}`;
      showMsg(`Connected${where} — ${result.model} replied: "${result.reply}"`, 'success');
    } else {
      showMsg(result.error || 'Connection test failed.', 'error');
    }
  };

  const needsBaseUrl = provider === 'openai-compatible'
    || Object.values(featureProviders).includes('openai-compatible');

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">AI Assistant</h2>

      <p className="settings-tab__hint">
        Connect an AI model for assistant features like importing book
        content into your reference notes. The app never interprets
        readings — the AI only helps with organizing and importing.
      </p>

      {message && (
        <div className={`settings-tab__message settings-tab__message--${message.type}`}>
          {message.text}
        </div>
      )}

      <section className="settings-tab__section">
        <div className="settings-tab__ai-form">
        <div className="settings-tab__field">
          <label className="settings-tab__label">Default assistant</label>
          <div className="settings-tab__ai-role-row">
            <select
              value={provider}
              onChange={(e) => handleProviderChange(e.target.value as LlmProvider)}
            >
              {PROVIDER_LABELS.map(p => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
            <input
              type="text"
              value={model}
              placeholder={MODEL_PLACEHOLDERS[provider]}
              onChange={(e) => { setModel(e.target.value); markDirty(); }}
            />
            <button onClick={() => handleTest('default')} disabled={testing !== null || dirty}>
              {testing === 'default' ? 'Testing…' : 'Test'}
            </button>
          </div>
        </div>

        {needsBaseUrl && (
          <div className="settings-tab__field">
            <label className="settings-tab__label">Server URL (local / other)</label>
            <input
              type="text"
              value={baseUrl}
              placeholder="http://localhost:11434/v1"
              onChange={(e) => { setBaseUrl(e.target.value); markDirty(); }}
            />
            <p className="settings-tab__hint">
              The address of your local model server. For Ollama this is
              http://localhost:11434/v1; for LM Studio, http://localhost:1234/v1.
            </p>
          </div>
        )}

        <div className="settings-tab__field">
          <label className="settings-tab__label">Per-role assistants (optional)</label>
          <p className="settings-tab__hint">
            Each role can use its own provider and model — e.g. DeepSeek
            for the Mirror, Claude for the Scribe. Leave on "Default
            assistant" to use the one above; leave the model blank for
            that provider's standard model.
          </p>
          {FEATURE_LABELS.map(f => {
            const fp = featureProviders[f.id];
            const effectiveProvider = fp || provider;
            return (
              <div key={f.id} className="settings-tab__feature-model">
                <span className="settings-tab__feature-model-label" title={f.hint}>{f.label}</span>
                <select
                  value={fp}
                  onChange={e => {
                    const v = e.target.value as LlmProvider | '';
                    setFeatureProviders(prev => ({ ...prev, [f.id]: v }));
                    // Provider switch invalidates the old model name.
                    setFeatureModels(prev => ({ ...prev, [f.id]: '' }));
                    markDirty();
                  }}
                >
                  <option value="">Default assistant</option>
                  {PROVIDER_LABELS.map(p => (
                    <option key={p.id} value={p.id}>{p.label}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={featureModels[f.id]}
                  placeholder={fp
                    ? MODEL_PLACEHOLDERS[fp] || 'model name'
                    : model || MODEL_PLACEHOLDERS[effectiveProvider]}
                  title={f.hint}
                  onChange={e => {
                    setFeatureModels(prev => ({ ...prev, [f.id]: e.target.value }));
                    markDirty();
                  }}
                />
                <button onClick={() => handleTest(f.id)} disabled={testing !== null || dirty}>
                  {testing === f.id ? 'Testing…' : 'Test'}
                </button>
              </div>
            );
          })}
        </div>

        <div className="settings-tab__field">
          <label className="settings-tab__label">API keys</label>
          <p className="settings-tab__hint">
            One key per provider — only the providers you use need one.
            Keys are stored locally on this computer and only ever sent
            to their own provider.
          </p>
          {KEY_PROVIDERS.map(kp => {
            const status = config?.api_keys?.[kp.id];
            return (
              <div key={kp.id} className="settings-tab__feature-model">
                <span className="settings-tab__feature-model-label">
                  {kp.label}
                  {status?.has_key && !keyInputs[kp.id] && (
                    <span className="settings-tab__hint"> (saved: {status.hint})</span>
                  )}
                </span>
                <input
                  type="password"
                  value={keyInputs[kp.id]}
                  placeholder={status?.has_key
                    ? 'Leave blank to keep the saved key'
                    : kp.optional ? 'Usually not needed for local servers' : 'Paste your API key'}
                  onChange={(e) => {
                    setKeyInputs(prev => ({ ...prev, [kp.id]: e.target.value }));
                    markDirty();
                  }}
                  autoComplete="off"
                />
                {status?.has_key ? (
                  <button onClick={() => handleClearKey(kp.id)} title={`Remove the saved ${kp.label} key`}>
                    Remove
                  </button>
                ) : <span className="settings-tab__key-spacer" />}
              </div>
            );
          })}
        </div>

        <div className="settings-tab__ai-actions">
          <button className="primary" onClick={handleSave} disabled={saving || !dirty}>
            {saving ? 'Saving…' : 'Save'}
          </button>
          {dirty && (
            <span className="settings-tab__hint">Save before testing.</span>
          )}
        </div>
        </div>
      </section>
    </div>
  );
}
