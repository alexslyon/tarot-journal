import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTheme } from '../../../context/ThemeContext';
import {
  getThemePresets,
  applyThemePreset,
  updateTheme,
  getDefaults,
  updateDefaults,
  HOUSE_SYSTEMS,
} from '../../../api/settings';
import { getProfiles } from '../../../api/profiles';
import { getCartomancyTypes, getDecks } from '../../../api/decks';
import type { ThemeColors, Profile, Deck, CartomancyType } from '../../../types';
import '../SettingsTab.css';

const BASE_SIZES = { size_title: 22, size_heading: 14, size_body: 13, size_small: 11 };

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

export default function GeneralSection() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();
  const [showCustomize, setShowCustomize] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

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
    setTheme({ ...theme, colors: { ...theme.colors, [key]: value } });
  };

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

  const handleDefaultChange = async (field: string, value: number | null | boolean | string) => {
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

  const getDecksForType = (typeName: string): Deck[] => {
    return decks.filter(deck => {
      if (deck.cartomancy_types && deck.cartomancy_types.length > 0) {
        return deck.cartomancy_types.some(t => t.name === typeName);
      }
      return deck.cartomancy_type === typeName;
    });
  };

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">General</h2>

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

      {/* Astrology Section */}
      <section className="settings-tab__section">
        <h3 className="settings-tab__section-title">Astrology Charts</h3>
        <p className="settings-tab__hint">
          Settings for natal and event charts. Changing the house system
          invalidates every cached chart on next view.
        </p>
        <div className="settings-tab__field">
          <label className="settings-tab__label">House System</label>
          <select
            value={defaults?.astrology_house_system ?? 'Whole Sign'}
            onChange={(e) => handleDefaultChange('astrology_house_system', e.target.value)}
          >
            {HOUSE_SYSTEMS.map(h => (
              <option key={h} value={h}>{h}</option>
            ))}
          </select>
        </div>
        <div className="settings-tab__field">
          <label className="settings-tab__checkbox-label">
            <input
              type="checkbox"
              checked={defaults?.astrology_allow_solar_chart ?? false}
              onChange={(e) => handleDefaultChange('astrology_allow_solar_chart', e.target.checked)}
            />
            <span>Generate solar charts when birth time is missing</span>
          </label>
          <p className="settings-tab__hint">
            When on, profiles without a birth time get a chart cast at
            local noon, with a note that house positions and Ascendant
            are approximate. When off, no chart is generated.
          </p>
        </div>
      </section>
    </div>
  );
}
