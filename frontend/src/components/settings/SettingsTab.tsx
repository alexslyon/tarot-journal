import { useState, useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTheme } from '../../context/ThemeContext';
import {
  getThemePresets,
  applyThemePreset,
  updateTheme,
  getDefaults,
  updateDefaults,
  createBackup,
  restoreBackup,
  getCacheStats,
  clearCache,
} from '../../api/settings';
import {
  getImportPresetsDetails,
  saveImportPreset,
  deleteImportPreset,
  resetImportPreset,
  type ImportPresetDetail,
} from '../../api/importExport';
import { getProfiles } from '../../api/profiles';
import { getCartomancyTypes, getDecks } from '../../api/decks';
import type { ThemeColors, Profile, Deck, CartomancyType } from '../../types';
import MappingsEditor from './MappingsEditor';
import './SettingsTab.css';

// Base font sizes used to compute scale factor
const BASE_SIZES = { size_title: 22, size_heading: 14, size_body: 12, size_small: 10 };

const COLOR_LABELS: Record<string, string> = {
  bg_primary: 'Background',
  bg_secondary: 'Panels',
  bg_tertiary: 'Hover',
  bg_input: 'Inputs',
  accent: 'Accent',
  accent_hover: 'Accent Hover',
  accent_dim: 'Accent Dim',
  text_primary: 'Text',
  text_secondary: 'Text Secondary',
  text_dim: 'Text Dim',
  border: 'Borders',
  success: 'Success',
  warning: 'Warning',
  danger: 'Danger',
  card_slot: 'Card Slot',
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function SettingsTab() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();
  const [showCustomize, setShowCustomize] = useState(false);
  const [saving, setSaving] = useState(false);
  const [backingUp, setBackingUp] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [includeImages, setIncludeImages] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Local color editing state
  const [editColors, setEditColors] = useState<ThemeColors>({ ...theme.colors });

  useEffect(() => {
    setEditColors({ ...theme.colors });
  }, [theme.colors]);

  const { data: presets } = useQuery({
    queryKey: ['theme-presets'],
    queryFn: getThemePresets,
  });

  const { data: defaults } = useQuery({
    queryKey: ['settings-defaults'],
    queryFn: getDefaults,
  });

  const { data: profiles = [] } = useQuery<Profile[]>({
    queryKey: ['profiles'],
    queryFn: getProfiles,
  });

  const { data: cartomancyTypes = [] } = useQuery<CartomancyType[]>({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });

  const { data: decks = [] } = useQuery<Deck[]>({
    queryKey: ['decks'],
    queryFn: () => getDecks(),
  });

  const { data: cacheStats } = useQuery({
    queryKey: ['cache-stats'],
    queryFn: getCacheStats,
  });

  const { data: importPresets = [] } = useQuery<ImportPresetDetail[]>({
    queryKey: ['import-presets-details'],
    queryFn: getImportPresetsDetails,
  });

  // Import preset editing state
  const [editingPreset, setEditingPreset] = useState<ImportPresetDetail | null>(null);
  const [presetForm, setPresetForm] = useState({
    name: '',
    type: 'Tarot',
    description: '',
    suit_names: {} as Record<string, string>,
    mappings_grouped: {} as Record<string, string[]>,
  });
  const [showMappings, setShowMappings] = useState(false);
  const [presetSaving, setPresetSaving] = useState(false);

  const startEditPreset = (preset: ImportPresetDetail) => {
    setEditingPreset(preset);
    setPresetForm({
      name: preset.name.replace('Custom: ', ''),
      type: preset.type,
      description: preset.description,
      suit_names: { ...preset.suit_names },
      mappings_grouped: { ...preset.mappings_grouped },
    });
    setShowMappings(false);
  };

  const startNewPreset = () => {
    setEditingPreset({ name: '', type: 'Tarot', description: '', suit_names: {}, card_count: 0, is_builtin: false, is_customized: false, mappings_grouped: {} });
    setPresetForm({
      name: '',
      type: 'Tarot',
      description: '',
      suit_names: {},
      mappings_grouped: {},
    });
    setShowMappings(false);
  };

  const cancelEditPreset = () => {
    setEditingPreset(null);
    setShowMappings(false);
  };

  const handleSavePreset = async () => {
    if (!presetForm.name.trim()) {
      showMsg('Preset name is required', 'error');
      return;
    }
    setPresetSaving(true);
    try {
      // Convert grouped mappings back to flat { pattern: cardName } format
      const flatMappings: Record<string, string> = {};
      for (const [cardName, patterns] of Object.entries(presetForm.mappings_grouped)) {
        for (const pattern of patterns) {
          flatMappings[pattern] = cardName;
        }
      }

      await saveImportPreset({
        name: presetForm.name.trim(),
        type: presetForm.type,
        description: presetForm.description,
        suit_names: presetForm.suit_names,
        mappings: flatMappings,
      });
      queryClient.invalidateQueries({ queryKey: ['import-presets-details'] });
      queryClient.invalidateQueries({ queryKey: ['import-presets'] });
      setEditingPreset(null);
      showMsg('Import preset saved', 'success');
    } catch {
      showMsg('Failed to save import preset', 'error');
    } finally {
      setPresetSaving(false);
    }
  };

  const handleDeletePreset = async (preset: ImportPresetDetail) => {
    const action = preset.is_customized ? 'reset to default' : 'delete';
    if (!window.confirm(`Are you sure you want to ${action} "${preset.name}"?`)) return;
    try {
      if (preset.is_customized) {
        await resetImportPreset(preset.name);
      } else {
        await deleteImportPreset(preset.name);
      }
      queryClient.invalidateQueries({ queryKey: ['import-presets-details'] });
      queryClient.invalidateQueries({ queryKey: ['import-presets'] });
      showMsg(`Import preset ${action === 'delete' ? 'deleted' : 'reset'}`, 'success');
    } catch {
      showMsg(`Failed to ${action} preset`, 'error');
    }
  };

  const SUIT_KEYS_BY_TYPE: Record<string, string[]> = {
    Tarot: ['wands', 'cups', 'swords', 'pentacles'],
    'Playing Cards': ['hearts', 'diamonds', 'clubs', 'spades'],
    Lenormand: ['hearts', 'diamonds', 'clubs', 'spades'],
  };

  const showMsg = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const handlePreset = async (name: string) => {
    try {
      const result = await applyThemePreset(name);
      setTheme(result);
      showMsg(`Applied "${name}" theme`, 'success');
    } catch {
      showMsg('Failed to apply preset', 'error');
    }
  };

  const handleSaveCustomColors = async () => {
    setSaving(true);
    try {
      const result = await updateTheme({ colors: editColors });
      setTheme(result);
      setShowCustomize(false);
      showMsg('Custom colors saved', 'success');
    } catch {
      showMsg('Failed to save colors', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleColorChange = (key: string, value: string) => {
    setEditColors((prev) => ({ ...prev, [key]: value }));
    // Live preview
    setTheme({ ...theme, colors: { ...theme.colors, [key]: value } });
  };

  // Text size: derive current scale from body size vs default (12px)
  const textScale = Math.round((theme.fonts.size_body / BASE_SIZES.size_body) * 100);

  const applyTextScale = (percent: number) => {
    const factor = percent / 100;
    const fonts = {
      ...theme.fonts,
      size_title: Math.round(BASE_SIZES.size_title * factor),
      size_heading: Math.round(BASE_SIZES.size_heading * factor),
      size_body: Math.round(BASE_SIZES.size_body * factor),
      size_small: Math.round(BASE_SIZES.size_small * factor),
    };
    setTheme({ ...theme, fonts });
  };

  const handleTextScaleSave = async (percent: number) => {
    const factor = percent / 100;
    const fonts = {
      ...theme.fonts,
      size_title: Math.round(BASE_SIZES.size_title * factor),
      size_heading: Math.round(BASE_SIZES.size_heading * factor),
      size_body: Math.round(BASE_SIZES.size_body * factor),
      size_small: Math.round(BASE_SIZES.size_small * factor),
    };
    try {
      await updateTheme({ fonts });
    } catch {
      showMsg('Failed to save text size', 'error');
    }
  };

  const handleDefaultChange = async (field: string, value: number | null | boolean) => {
    try {
      await updateDefaults({ [field]: value });
      queryClient.invalidateQueries({ queryKey: ['settings-defaults'] });
    } catch {
      showMsg('Failed to save default', 'error');
    }
  };

  const handleDefaultDeckChange = async (typeName: string, deckId: number | null) => {
    try {
      const updatedDecks = {
        ...(defaults?.default_decks || {}),
        [typeName]: deckId,
      };
      await updateDefaults({ default_decks: updatedDecks });
      queryClient.invalidateQueries({ queryKey: ['settings-defaults'] });
    } catch {
      showMsg('Failed to save default deck', 'error');
    }
  };

  // Helper to get decks that match a given cartomancy type
  const getDecksForType = (typeName: string): Deck[] => {
    return decks.filter(deck => {
      // Check multi-type array first
      if (deck.cartomancy_types && deck.cartomancy_types.length > 0) {
        return deck.cartomancy_types.some(t => t.name === typeName);
      }
      // Fall back to legacy single-type field
      return deck.cartomancy_type === typeName;
    });
  };

  const handleBackup = async () => {
    setBackingUp(true);
    try {
      const blob = await createBackup(includeImages);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tarot_backup_${new Date().toISOString().slice(0, 10)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      queryClient.invalidateQueries({ queryKey: ['settings-defaults'] });
      showMsg('Backup created successfully', 'success');
    } catch {
      showMsg('Backup failed', 'error');
    } finally {
      setBackingUp(false);
    }
  };

  const handleRestore = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!window.confirm('Restore from backup? This will replace all current data. A safety backup will be created first.')) {
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    setRestoring(true);
    try {
      await restoreBackup(file);
      queryClient.invalidateQueries();
      showMsg('Backup restored successfully. Reload the page to see changes.', 'success');
    } catch {
      showMsg('Restore failed', 'error');
    } finally {
      setRestoring(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleClearCache = async () => {
    if (!window.confirm('Clear the thumbnail cache? Thumbnails will be regenerated as needed.')) return;
    try {
      await clearCache();
      queryClient.invalidateQueries({ queryKey: ['cache-stats'] });
      showMsg('Cache cleared', 'success');
    } catch {
      showMsg('Failed to clear cache', 'error');
    }
  };

  return (
    <div className="settings-tab">
      <div className="settings-tab__scroll">
        <h2 className="settings-tab__title">Settings</h2>

        {message && (
          <div className={`settings-tab__message settings-tab__message--${message.type}`}>
            {message.text}
          </div>
        )}

        {/* Theme Section */}
        <section className="settings-tab__section">
          <h3 className="settings-tab__section-title">Theme</h3>

          <div className="settings-tab__presets">
            {presets && Object.keys(presets).map((name) => (
              <button
                key={name}
                className="settings-tab__preset-btn"
                onClick={() => handlePreset(name)}
              >
                <span
                  className="settings-tab__preset-swatch"
                  style={{ background: presets[name].colors.accent }}
                />
                {name}
              </button>
            ))}
          </div>

          <div className="settings-tab__text-size">
            <label className="settings-tab__text-size-label">Text Size</label>
            <div className="settings-tab__text-size-row">
              <span className="settings-tab__text-size-hint">A</span>
              <input
                type="range"
                min={75}
                max={200}
                step={5}
                value={textScale}
                onChange={(e) => applyTextScale(Number(e.target.value))}
                onMouseUp={(e) => handleTextScaleSave(Number((e.target as HTMLInputElement).value))}
                className="settings-tab__text-size-slider"
              />
              <span className="settings-tab__text-size-hint settings-tab__text-size-hint--large">A</span>
              <span className="settings-tab__text-size-value">{textScale}%</span>
            </div>
          </div>

          <button
            className="settings-tab__customize-btn"
            onClick={() => setShowCustomize(!showCustomize)}
          >
            {showCustomize ? 'Hide Custom Colors' : 'Customize Colors...'}
          </button>

          {showCustomize && (
            <div className="settings-tab__color-editor">
              <div className="settings-tab__color-grid">
                {Object.entries(COLOR_LABELS).map(([key, label]) => (
                  <div key={key} className="settings-tab__color-field">
                    <label className="settings-tab__color-label">{label}</label>
                    <div className="settings-tab__color-input-row">
                      <input
                        type="color"
                        value={editColors[key as keyof ThemeColors] || '#000000'}
                        onChange={(e) => handleColorChange(key, e.target.value)}
                      />
                      <span className="settings-tab__color-hex">
                        {editColors[key as keyof ThemeColors]}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="settings-tab__color-actions">
                <button onClick={() => { setEditColors({ ...theme.colors }); setShowCustomize(false); }}>
                  Cancel
                </button>
                <button
                  className="settings-tab__save-btn"
                  onClick={handleSaveCustomColors}
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save Colors'}
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Defaults Section */}
        <section className="settings-tab__section">
          <h3 className="settings-tab__section-title">Defaults</h3>

          <div className="settings-tab__defaults-grid">
            <div className="settings-tab__field">
              <label className="settings-tab__label">Default Reader</label>
              <select
                value={defaults?.default_reader ?? ''}
                onChange={(e) => handleDefaultChange('default_reader', e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">None</option>
                {profiles
                  .filter((p) => !p.querent_only && (!p.hidden || p.id === defaults?.default_reader))
                  .map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
              </select>
            </div>

            <div className="settings-tab__field">
              <label className="settings-tab__label">Default Querent</label>
              <select
                value={defaults?.default_querent ?? ''}
                onChange={(e) => handleDefaultChange('default_querent', e.target.value ? Number(e.target.value) : null)}
                disabled={defaults?.default_querent_same_as_reader}
              >
                <option value="">None</option>
                {profiles
                  .filter((p) => !p.hidden || p.id === defaults?.default_querent)
                  .map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
              </select>
            </div>

            <div className="settings-tab__field settings-tab__field--checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={defaults?.default_querent_same_as_reader ?? false}
                  onChange={(e) => handleDefaultChange('default_querent_same_as_reader', e.target.checked)}
                />
                Querent same as reader
              </label>
            </div>
          </div>

          <h4 className="settings-tab__subsection-title">Default Decks</h4>
          <p className="settings-tab__hint">
            Select a default deck for each type. These will be auto-selected when creating journal entries.
          </p>
          <div className="settings-tab__defaults-grid">
            {cartomancyTypes.map((type) => {
              const typeDecks = getDecksForType(type.name);
              return (
                <div key={type.id} className="settings-tab__field">
                  <label className="settings-tab__label">{type.name}</label>
                  <select
                    value={defaults?.default_decks?.[type.name] ?? ''}
                    onChange={(e) => handleDefaultDeckChange(type.name, e.target.value ? Number(e.target.value) : null)}
                  >
                    <option value="">None</option>
                    {typeDecks.map((deck) => (
                      <option key={deck.id} value={deck.id}>{deck.name}</option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>
        </section>

        {/* Import Presets Section */}
        <section className="settings-tab__section">
          <h3 className="settings-tab__section-title">Import Presets</h3>
          <p className="settings-tab__hint">
            These presets control how card images are named and organized when importing a deck from a folder.
          </p>

          <div className="settings-tab__preset-list">
            {importPresets.map((preset) => (
              <div key={preset.name} className="settings-tab__import-preset-row">
                <div className="settings-tab__import-preset-info">
                  <span className="settings-tab__import-preset-name">
                    {preset.name}
                    {preset.is_customized && (
                      <span className="settings-tab__import-preset-badge">modified</span>
                    )}
                    {!preset.is_builtin && (
                      <span className="settings-tab__import-preset-badge settings-tab__import-preset-badge--custom">custom</span>
                    )}
                  </span>
                  <span className="settings-tab__import-preset-desc">
                    {preset.description || `${preset.type} · ${preset.card_count} cards`}
                  </span>
                </div>
                <div className="settings-tab__import-preset-actions">
                  <button
                    className="settings-tab__import-preset-btn"
                    onClick={() => startEditPreset(preset)}
                    title="Edit"
                  >
                    Edit
                  </button>
                  {(preset.is_customized || !preset.is_builtin) && (
                    <button
                      className="settings-tab__import-preset-btn settings-tab__import-preset-btn--danger"
                      onClick={() => handleDeletePreset(preset)}
                      title={preset.is_customized ? 'Reset to default' : 'Delete'}
                    >
                      {preset.is_customized ? 'Reset' : 'Delete'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <button className="settings-tab__add-preset-btn" onClick={startNewPreset}>
            + Add New Preset
          </button>

          {editingPreset && (
            <div className="settings-tab__preset-editor">
              <h4 className="settings-tab__subsection-title">
                {editingPreset.name ? `Edit: ${editingPreset.name}` : 'New Preset'}
              </h4>

              <div className="settings-tab__preset-form">
                <div className="settings-tab__field">
                  <label className="settings-tab__label">Name</label>
                  <input
                    type="text"
                    value={presetForm.name}
                    onChange={(e) => setPresetForm({ ...presetForm, name: e.target.value })}
                    placeholder="My Custom Preset"
                    disabled={editingPreset.is_builtin}
                  />
                </div>

                <div className="settings-tab__field">
                  <label className="settings-tab__label">Deck Type</label>
                  <select
                    value={presetForm.type}
                    onChange={(e) => {
                      const newType = e.target.value;
                      const defaultSuits = SUIT_KEYS_BY_TYPE[newType];
                      setPresetForm({
                        ...presetForm,
                        type: newType,
                        suit_names: defaultSuits
                          ? Object.fromEntries(defaultSuits.map((k) => [k, k.charAt(0).toUpperCase() + k.slice(1)]))
                          : {},
                      });
                    }}
                    disabled={editingPreset.is_builtin}
                  >
                    {cartomancyTypes.map((t) => (
                      <option key={t.id} value={t.name}>{t.name}</option>
                    ))}
                  </select>
                </div>

                <div className="settings-tab__field">
                  <label className="settings-tab__label">Description</label>
                  <input
                    type="text"
                    value={presetForm.description}
                    onChange={(e) => setPresetForm({ ...presetForm, description: e.target.value })}
                    placeholder="Brief description of this preset"
                  />
                </div>

                {SUIT_KEYS_BY_TYPE[presetForm.type] && (
                  <>
                    <label className="settings-tab__label">Suit Names</label>
                    <div className="settings-tab__suit-grid">
                      {SUIT_KEYS_BY_TYPE[presetForm.type].map((key) => (
                        <div key={key} className="settings-tab__field">
                          <label className="settings-tab__label settings-tab__label--small">
                            {key.charAt(0).toUpperCase() + key.slice(1)}
                          </label>
                          <input
                            type="text"
                            value={presetForm.suit_names[key] || ''}
                            onChange={(e) =>
                              setPresetForm({
                                ...presetForm,
                                suit_names: { ...presetForm.suit_names, [key]: e.target.value },
                              })
                            }
                          />
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>

              <div className="settings-tab__mappings-toggle">
                <button
                  className="settings-tab__customize-btn"
                  onClick={() => setShowMappings(!showMappings)}
                >
                  {showMappings ? 'Hide Card Mappings' : `Show Card Mappings (${Object.keys(presetForm.mappings_grouped).length} cards)`}
                </button>
              </div>

              {showMappings && (
                <MappingsEditor
                  mappings={presetForm.mappings_grouped}
                  onChange={(updated) =>
                    setPresetForm({ ...presetForm, mappings_grouped: updated })
                  }
                />
              )}

              <div className="settings-tab__preset-form-actions">
                <button onClick={cancelEditPreset}>Cancel</button>
                <button
                  className="settings-tab__save-btn"
                  onClick={handleSavePreset}
                  disabled={presetSaving}
                >
                  {presetSaving ? 'Saving...' : 'Save Preset'}
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Backup & Restore Section */}
        <section className="settings-tab__section">
          <h3 className="settings-tab__section-title">Backup & Restore</h3>

          {defaults?.last_backup_time && (
            <p className="settings-tab__last-backup">
              Last backup: {new Date(defaults.last_backup_time).toLocaleString()}
            </p>
          )}

          <div className="settings-tab__backup-row">
            <label className="settings-tab__checkbox-label">
              <input
                type="checkbox"
                checked={includeImages}
                onChange={(e) => setIncludeImages(e.target.checked)}
              />
              Include card images
            </label>
            <button
              className="settings-tab__backup-btn"
              onClick={handleBackup}
              disabled={backingUp}
            >
              {backingUp ? 'Creating...' : 'Create Backup'}
            </button>
          </div>

          <div className="settings-tab__restore-row">
            <button
              className="settings-tab__restore-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={restoring}
            >
              {restoring ? 'Restoring...' : 'Restore from Backup'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              onChange={handleRestore}
              style={{ display: 'none' }}
            />
          </div>
        </section>

        {/* Cache Section */}
        <section className="settings-tab__section">
          <h3 className="settings-tab__section-title">Thumbnail Cache</h3>
          {cacheStats && (
            <p className="settings-tab__cache-info">
              {cacheStats.count} thumbnails ({formatBytes(cacheStats.size_bytes)})
            </p>
          )}
          <button className="settings-tab__clear-cache-btn" onClick={handleClearCache}>
            Clear Cache
          </button>
        </section>
      </div>
    </div>
  );
}
