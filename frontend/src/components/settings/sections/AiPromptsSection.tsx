/**
 * Settings → AI Prompts: view, edit, and switch the system prompts
 * behind the three assistants. The shipped prompt is always present
 * as a read-only "Built-in default"; user-authored presets are named
 * versions — duplicate, tweak, activate, and swap back freely.
 */
import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getPromptConfig,
  addPromptPreset,
  updatePromptPreset,
  deletePromptPreset,
  setActivePromptPreset,
  type PromptPreset,
} from '../../../api/prompts';
import { DEFAULT_PROMPTS, PROMPT_EDITOR_NOTES } from '../../../utils/assistantPrompts';
import type { LlmFeature } from '../../../api/llm';
import { useToast } from '../../../context/ToastContext';
import { confirmDialog } from '../../common/ConfirmDialog';
import '../SettingsTab.css';
import './AiPromptsSection.css';

const FEATURES: { id: LlmFeature; label: string }[] = [
  { id: 'mirror', label: 'Mirror' },
  { id: 'analyst', label: 'Analyst' },
  { id: 'scribe', label: 'Scribe' },
];

export default function AiPromptsSection() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [feature, setFeature] = useState<LlmFeature>('mirror');
  // null = the built-in default is selected in the editor
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const [nameDraft, setNameDraft] = useState('');
  const [dirty, setDirty] = useState(false);

  const { data: config } = useQuery({
    queryKey: ['prompt-config', feature],
    queryFn: () => getPromptConfig(feature),
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['prompt-config', feature] });

  const selected: PromptPreset | null =
    selectedId != null
      ? config?.presets.find(p => p.id === selectedId) ?? null
      : null;
  const isDefault = selectedId == null;
  const activeId = config?.active_id ?? null;

  // Load the selected prompt into the editor (not while mid-edit).
  useEffect(() => {
    if (dirty) return;
    setDraft(isDefault ? DEFAULT_PROMPTS[feature] : selected?.content ?? '');
    setNameDraft(selected?.name ?? '');
  }, [feature, selectedId, config, dirty, isDefault, selected]);

  const switchFeature = (f: LlmFeature) => {
    if (dirty && !window.confirm('Discard unsaved prompt changes?')) return;
    setFeature(f);
    setSelectedId(null);
    setDirty(false);
  };

  const switchPreset = (id: number | null) => {
    if (dirty && !window.confirm('Discard unsaved prompt changes?')) return;
    setSelectedId(id);
    setDirty(false);
  };

  const handleDuplicate = async () => {
    const baseName = isDefault ? 'My version' : `${selected?.name} (copy)`;
    try {
      const { id } = await addPromptPreset(feature, {
        name: baseName,
        content: draft,
      });
      await invalidate();
      setSelectedId(id);
      setDirty(false);
      showToast(`Created "${baseName}" — it's editable now.`, 'success');
    } catch {
      showToast('Could not create the preset.');
    }
  };

  const handleSave = async () => {
    if (isDefault || !selected) return;
    try {
      await updatePromptPreset(selected.id, {
        content: draft,
        ...(nameDraft.trim() && nameDraft.trim() !== selected.name
          ? { name: nameDraft.trim() }
          : {}),
      });
      setDirty(false);
      invalidate();
      showToast('Preset saved.', 'success');
    } catch {
      showToast('Could not save the preset.');
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    if (!(await confirmDialog({
      message: `Delete the preset "${selected.name}"?`,
      title: 'Delete Preset',
      confirmLabel: 'Delete',
    }))) return;
    try {
      await deletePromptPreset(selected.id);
      await invalidate();
      setSelectedId(null);
      setDirty(false);
      showToast('Preset deleted.', 'success');
    } catch {
      showToast('Could not delete the preset.');
    }
  };

  const handleActivate = async (id: number | null) => {
    try {
      await setActivePromptPreset(feature, id);
      invalidate();
      showToast(
        id == null
          ? 'Built-in default is now active.'
          : 'Preset activated — it takes effect on the next conversation.',
        'success',
      );
    } catch {
      showToast('Could not switch the active prompt.');
    }
  };

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">AI Prompts</h2>
      <p className="settings-tab__hint">
        The exact instructions each assistant works from. The built-in
        default is always kept; duplicate it to make an editable
        version, then activate whichever version you want to try.
        Switching is instant and takes effect on the next conversation.
      </p>

      <div className="ai-prompts__features">
        {FEATURES.map(f => (
          <button
            key={f.id}
            className={`ai-prompts__feature ${feature === f.id ? 'ai-prompts__feature--active' : ''}`}
            onClick={() => switchFeature(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <section className="settings-tab__section ai-prompts__layout">
        <div className="ai-prompts__list">
          <button
            className={`ai-prompts__preset ${isDefault ? 'ai-prompts__preset--selected' : ''}`}
            onClick={() => switchPreset(null)}
          >
            <span className="ai-prompts__preset-name">Built-in default</span>
            {activeId == null && <span className="ai-prompts__badge">active</span>}
          </button>
          {(config?.presets ?? []).map(p => (
            <button
              key={p.id}
              className={`ai-prompts__preset ${selectedId === p.id ? 'ai-prompts__preset--selected' : ''}`}
              onClick={() => switchPreset(p.id)}
            >
              <span className="ai-prompts__preset-name">{p.name}</span>
              {activeId === p.id && <span className="ai-prompts__badge">active</span>}
            </button>
          ))}
        </div>

        <div className="ai-prompts__editor">
          <p className="settings-tab__hint">{PROMPT_EDITOR_NOTES[feature]}</p>
          {!isDefault && (
            <input
              type="text"
              className="ai-prompts__name"
              value={nameDraft}
              onChange={e => { setNameDraft(e.target.value); setDirty(true); }}
              placeholder="Preset name"
            />
          )}
          <textarea
            className="ai-prompts__textarea"
            value={draft}
            readOnly={isDefault}
            onChange={e => { setDraft(e.target.value); setDirty(true); }}
            spellCheck={false}
          />
          <div className="ai-prompts__actions">
            {isDefault ? (
              <>
                <button className="primary" onClick={handleDuplicate}>
                  Duplicate to edit
                </button>
                {activeId != null && (
                  <button onClick={() => handleActivate(null)}>
                    Use built-in default
                  </button>
                )}
              </>
            ) : (
              <>
                <button className="primary" onClick={handleSave} disabled={!dirty}>
                  Save
                </button>
                {activeId !== selectedId && (
                  <button onClick={() => handleActivate(selectedId)} disabled={dirty}>
                    Use this version
                  </button>
                )}
                <button onClick={handleDuplicate}>Duplicate</button>
                <button onClick={handleDelete}>Delete</button>
              </>
            )}
            {dirty && <span className="settings-tab__hint">Unsaved changes.</span>}
          </div>
        </div>
      </section>
    </div>
  );
}
