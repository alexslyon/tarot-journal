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
  { id: 'openai-compatible', label: 'Local / other (OpenAI-compatible)' },
];

const MODEL_PLACEHOLDERS: Record<LlmProvider, string> = {
  anthropic: 'claude-opus-5',
  openai: 'gpt-4o',
  'openai-compatible': 'e.g. llama3, qwen2.5, mistral…',
};

const FEATURE_LABELS: { id: LlmFeature; label: string; hint: string }[] = [
  { id: 'scribe', label: 'Scribe (book imports)', hint: 'transcription-heavy — a capable model pays off' },
  { id: 'mirror', label: 'Mirror (reflections)', hint: 'short questions — a fast, cheap model is plenty' },
  { id: 'analyst', label: 'Analyst (journal patterns)', hint: 'reads many entries per question' },
];

const EMPTY_FEATURE_MODELS: Record<LlmFeature, string> = {
  scribe: '', mirror: '', analyst: '',
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
  const [apiKey, setApiKey] = useState('');
  const [featureModels, setFeatureModels] = useState<Record<LlmFeature, string>>(EMPTY_FEATURE_MODELS);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Load stored config into the form (the key itself never arrives —
  // the field stays blank and only updates the key when typed into).
  useEffect(() => {
    if (!config || dirty) return;
    setProvider(config.provider);
    setModel(config.model);
    setBaseUrl(config.base_url);
    setFeatureModels({ ...EMPTY_FEATURE_MODELS, ...(config.feature_models || {}) });
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
      await updateLlmConfig({
        provider,
        model,
        base_url: baseUrl,
        feature_models: featureModels,
        ...(apiKey ? { api_key: apiKey } : {}),
      });
      setApiKey('');
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ['llm-config'] });
      showMsg('AI settings saved.', 'success');
    } catch {
      showMsg('Failed to save AI settings.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleClearKey = async () => {
    try {
      await updateLlmConfig({ api_key: '' });
      queryClient.invalidateQueries({ queryKey: ['llm-config'] });
      showMsg('API key removed.', 'success');
    } catch {
      showMsg('Failed to remove the API key.', 'error');
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setMessage(null);
    const result = await testLlmConnection();
    setTesting(false);
    if (result.ok) {
      showMsg(`Connected — ${result.model} replied: "${result.reply}"`, 'success');
    } else {
      showMsg(result.error || 'Connection test failed.', 'error');
    }
  };

  const needsBaseUrl = provider === 'openai-compatible';
  const needsKey = provider !== 'openai-compatible';

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
          <label className="settings-tab__label">Provider</label>
          <select
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value as LlmProvider)}
          >
            {PROVIDER_LABELS.map(p => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </div>

        {needsBaseUrl && (
          <div className="settings-tab__field">
            <label className="settings-tab__label">Server URL</label>
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
          <label className="settings-tab__label">Model</label>
          <input
            type="text"
            value={model}
            placeholder={MODEL_PLACEHOLDERS[provider]}
            onChange={(e) => { setModel(e.target.value); markDirty(); }}
          />
        </div>

        <div className="settings-tab__field">
          <label className="settings-tab__label">Per-feature models (optional)</label>
          <p className="settings-tab__hint">
            Leave blank to use the model above. Set one to give a feature
            its own model — e.g. a cheaper, faster model for the Mirror.
          </p>
          {FEATURE_LABELS.map(f => (
            <div key={f.id} className="settings-tab__feature-model">
              <span className="settings-tab__feature-model-label">{f.label}</span>
              <input
                type="text"
                value={featureModels[f.id]}
                placeholder={model || MODEL_PLACEHOLDERS[provider]}
                title={f.hint}
                onChange={e => {
                  setFeatureModels(prev => ({ ...prev, [f.id]: e.target.value }));
                  markDirty();
                }}
              />
            </div>
          ))}
        </div>

        <div className="settings-tab__field">
          <label className="settings-tab__label">
            API key
            {config?.has_api_key && !apiKey && (
              <span className="settings-tab__hint"> (saved: {config.api_key_hint})</span>
            )}
          </label>
          <input
            type="password"
            value={apiKey}
            placeholder={config?.has_api_key ? 'Leave blank to keep the saved key' : needsKey ? 'Paste your API key' : 'Usually not needed for local servers'}
            onChange={(e) => { setApiKey(e.target.value); markDirty(); }}
            autoComplete="off"
          />
          <p className="settings-tab__hint">
            Stored locally on this computer, only ever sent to the provider above.
            {config?.has_api_key && (
              <> {' '}<button className="settings-tab__link-btn" onClick={handleClearKey}>Remove saved key</button></>
            )}
          </p>
        </div>

        <div className="settings-tab__ai-actions">
          <button className="primary" onClick={handleSave} disabled={saving || !dirty}>
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button onClick={handleTest} disabled={testing || dirty}>
            {testing ? 'Testing…' : 'Test connection'}
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
