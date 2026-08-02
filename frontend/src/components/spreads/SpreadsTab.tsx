import { useState, useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useDirtyGuard } from '../../utils/dirtyGuard';
import { Panel, Group, Separator } from 'react-resizable-panels';
import { createSpread, updateSpread, deleteSpread, cloneSpread } from '../../api/spreads';
import { useToast } from '../../context/ToastContext';
import SpreadList from './SpreadList';
import SpreadDesigner from './SpreadDesigner';
import SpreadProperties from './SpreadProperties';
import PositionLegend from './PositionLegend';
import RichTextViewer from '../common/RichTextViewer';
import type { Spread, SpreadPosition, DeckSlot } from '../../types';

/** Check if a description string has meaningful content (handles both plain text and HTML). */
function hasDescriptionContent(desc: string | null | undefined): boolean {
  if (!desc) return false;
  // Strip HTML tags and check for non-whitespace
  return desc.replace(/<[^>]*>/g, '').trim().length > 0;
}

import { ensureHtml } from '../../utils/formatting';
import './SpreadsTab.css';
import { confirmDialog } from '../common/ConfirmDialog';

export default function SpreadsTab() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [selectedSpread, setSelectedSpread] = useState<Spread | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState('');

  // Local editing state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [positions, setPositions] = useState<SpreadPosition[]>([]);
  const [allowedDeckTypes, setAllowedDeckTypes] = useState<string[]>([]);
  const [defaultDeckId, setDefaultDeckId] = useState<number | null>(null);
  const [deckSlots, setDeckSlots] = useState<DeckSlot[]>([]);
  const [descOpen, setDescOpen] = useState(false);
  const [viewerShowLabels, setViewerShowLabels] = useState(false);

  // Unsaved-changes detection: the form state diverging from the
  // selected spread (or any content on a brand-new spread). Feeds the
  // shared dirty guard so quitting the app or switching tabs asks for
  // confirmation instead of silently discarding a half-designed spread.
  const isDirty = useMemo(() => {
    if (isNew) {
      return name.trim() !== '' || positions.length > 0;
    }
    if (!selectedSpread || !editing) return false;
    if (name !== selectedSpread.name) return true;
    if ((description || '') !== (selectedSpread.description || '')) return true;
    const basePositions = Array.isArray(selectedSpread.positions) ? selectedSpread.positions : [];
    if (JSON.stringify(positions) !== JSON.stringify(basePositions)) return true;
    const baseAllowed = Array.isArray(selectedSpread.allowed_deck_types)
      ? selectedSpread.allowed_deck_types : [];
    if (JSON.stringify(allowedDeckTypes) !== JSON.stringify(baseAllowed)) return true;
    if ((defaultDeckId ?? null) !== (selectedSpread.default_deck_id ?? null)) return true;
    let baseSlots: DeckSlot[] = [];
    const rawSlots = selectedSpread.deck_slots;
    if (Array.isArray(rawSlots)) baseSlots = rawSlots;
    else if (typeof rawSlots === 'string') {
      try { baseSlots = JSON.parse(rawSlots); } catch { baseSlots = []; }
    }
    if (JSON.stringify(deckSlots) !== JSON.stringify(baseSlots)) return true;
    return false;
  }, [isNew, editing, selectedSpread, name, description, positions, allowedDeckTypes, defaultDeckId, deckSlots]);
  useDirtyGuard(isDirty);

  // Populate form when a spread is selected
  useEffect(() => {
    if (selectedSpread && !isNew) {
      setName(selectedSpread.name);
      setDescription(selectedSpread.description || '');
      setPositions(
        Array.isArray(selectedSpread.positions) ? selectedSpread.positions : [],
      );
      setAllowedDeckTypes(
        Array.isArray(selectedSpread.allowed_deck_types)
          ? selectedSpread.allowed_deck_types
          : [],
      );
      setDefaultDeckId(selectedSpread.default_deck_id);
      // Parse deck_slots from spread
      const slots = selectedSpread.deck_slots;
      if (Array.isArray(slots)) {
        setDeckSlots(slots);
      } else if (typeof slots === 'string') {
        try {
          setDeckSlots(JSON.parse(slots));
        } catch {
          setDeckSlots([]);
        }
      } else {
        setDeckSlots([]);
      }
      setSelectedIndex(null);
    }
  }, [selectedSpread, isNew]);

  const handleSelect = (spread: Spread) => {
    setSelectedSpread(spread);
    setIsNew(false);
    setEditing(false);
  };

  const handleNew = () => {
    setSelectedSpread(null);
    setIsNew(true);
    setEditing(true);
    setName('');
    setDescription('');
    setPositions([]);
    setAllowedDeckTypes([]);
    setDefaultDeckId(null);
    // Default to one deck slot with Tarot type
    setDeckSlots([{ key: 'A', cartomancy_type: 'Tarot', label: 'Main Deck' }]);
    setSelectedIndex(null);
  };

  const handleClone = async () => {
    if (!selectedSpread) return;
    setError('');
    try {
      const result = await cloneSpread(selectedSpread.id);
      queryClient.invalidateQueries({ queryKey: ['spreads'] });
      // Select the cloned spread after list refreshes
      setSelectedSpread({
        ...selectedSpread,
        id: result.id,
        name: `Copy of ${selectedSpread.name}`,
      });
      setName(`Copy of ${selectedSpread.name}`);
      setIsNew(false);
      setEditing(false);
    } catch (err) {
      console.error('Failed to clone spread:', err);
      showToast('Failed to clone spread.');
    }
  };

  const handleDelete = async () => {
    if (!selectedSpread) return;
    if (!(await confirmDialog({ message: `Delete "${selectedSpread.name}"? This cannot be undone.`, title: 'Delete Spread', confirmLabel: 'Delete' }))) return;
    setError('');
    try {
      await deleteSpread(selectedSpread.id);
      queryClient.invalidateQueries({ queryKey: ['spreads'] });
      setSelectedSpread(null);
      setIsNew(false);
      setEditing(false);
    } catch (err) {
      console.error('Failed to delete spread:', err);
      showToast('Failed to delete spread.');
    }
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError('');
    try {
      if (isNew) {
        const result = await createSpread({
          name: name.trim(),
          positions,
          description: description || undefined,
          allowed_deck_types: allowedDeckTypes.length > 0 ? allowedDeckTypes : undefined,
          default_deck_id: defaultDeckId,
          deck_slots: deckSlots.length > 0 ? deckSlots : undefined,
        });
        setIsNew(false);
        // Re-select the newly created spread
        const newSpread: Spread = {
          id: result.id,
          name: name.trim(),
          description,
          positions,
          cartomancy_type: null,
          allowed_deck_types: allowedDeckTypes,
          default_deck_id: defaultDeckId,
          deck_slots: deckSlots,
          created_at: new Date().toISOString(),
        };
        setSelectedSpread(newSpread);
      } else if (selectedSpread) {
        await updateSpread(selectedSpread.id, {
          name: name.trim(),
          positions,
          description: description || undefined,
          allowed_deck_types: allowedDeckTypes.length > 0 ? allowedDeckTypes : null,
          default_deck_id: defaultDeckId,
          clear_default_deck: defaultDeckId === null && selectedSpread.default_deck_id !== null,
          deck_slots: deckSlots.length > 0 ? deckSlots : null,
        });
        setSelectedSpread({
          ...selectedSpread,
          name: name.trim(),
          description,
          positions,
          allowed_deck_types: allowedDeckTypes,
          default_deck_id: defaultDeckId,
          deck_slots: deckSlots,
        });
      }
      queryClient.invalidateQueries({ queryKey: ['spreads'] });
      setEditing(false);
    } catch (err) {
      console.error('Failed to save spread:', err);
      showToast('Failed to save spread.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    if (isNew) {
      // Cancel creating a new spread entirely
      setIsNew(false);
      setEditing(false);
      return;
    }
    // Revert to saved data
    if (selectedSpread) {
      setName(selectedSpread.name);
      setDescription(selectedSpread.description || '');
      setPositions(
        Array.isArray(selectedSpread.positions) ? selectedSpread.positions : [],
      );
    }
    setEditing(false);
  };

  const hasSelection = selectedSpread !== null || isNew;

  // View-mode content for selected spread
  const renderViewer = () => {
    if (!selectedSpread) return null;
    return (
      <div className="spreads-tab__viewer">
        {error && <div className="spreads-tab__error">{error}</div>}
        <div className="spreads-tab__viewer-scroll">
          <h2 className="spreads-tab__viewer-name">{selectedSpread.name}</h2>
          {selectedSpread.archived ? (
            <p className="spreads-tab__archived-note">
              Archived — hidden from pickers; existing entries still use it.
            </p>
          ) : null}
          {hasDescriptionContent(selectedSpread.description) ? (
            <div className="spreads-tab__desc">
              <button
                type="button"
                className="spreads-tab__desc-toggle"
                aria-expanded={descOpen}
                onClick={() => setDescOpen(o => !o)}
              >
                <span className={`spreads-tab__desc-chevron ${descOpen ? 'spreads-tab__desc-chevron--open' : ''}`} aria-hidden="true">▸</span>
                Description &amp; instructions
              </button>
              {descOpen && (
                <RichTextViewer content={ensureHtml(selectedSpread.description!)} className="spreads-tab__viewer-description" />
              )}
            </div>
          ) : (
            <p className="spreads-tab__viewer-description spreads-tab__viewer-description--empty">No description</p>
          )}

          <div className="spreads-tab__viewer-canvas">
            <label className="spreads-tab__viewer-label-toggle">
              <input
                type="checkbox"
                checked={viewerShowLabels}
                onChange={(e) => setViewerShowLabels(e.target.checked)}
              />
              <span>Show Labels</span>
            </label>
            <SpreadDesigner
              positions={positions}
              onChange={setPositions}
              selectedIndex={null}
              onSelectIndex={() => {}}
              deckSlots={deckSlots}
              readOnly
              showLabels={viewerShowLabels}
            />
          </div>

          <div className="spreads-tab__viewer-legend">
            <PositionLegend
              positions={positions}
              selectedIndex={null}
              onSelectIndex={() => {}}
            />
          </div>
        </div>

        <div className="spreads-tab__footer">
          <button
            className="spreads-tab__edit-btn"
            onClick={() => setEditing(true)}
          >
            Edit Spread
          </button>
        </div>
      </div>
    );
  };

  // Edit-mode content
  const renderEditor = () => (
    <div className="spreads-tab__editor">
      {error && <div className="spreads-tab__error">{error}</div>}
      <div className="spreads-tab__editor-scroll">
        <div className="spreads-tab__props-section">
          <SpreadProperties
            name={name}
            description={description}
            deckSlots={deckSlots}
            onNameChange={setName}
            onDescriptionChange={setDescription}
            onDeckSlotsChange={setDeckSlots}
          />
        </div>

        <div className="spreads-tab__designer-section">
          <h3 className="spreads-tab__section-title">Designer</h3>
          <SpreadDesigner
            positions={positions}
            onChange={setPositions}
            selectedIndex={selectedIndex}
            onSelectIndex={setSelectedIndex}
            deckSlots={deckSlots}
          />
        </div>

        <div className="spreads-tab__legend-section">
          <PositionLegend
            positions={positions}
            selectedIndex={selectedIndex}
            onSelectIndex={setSelectedIndex}
            onUpdatePosition={(idx, updates) =>
              setPositions(prev => prev.map((p, i) => (i === idx ? { ...p, ...updates } : p)))}
            onReorder={(from, to) => {
              setPositions(prev => {
                const next = [...prev];
                const [moved] = next.splice(from, 1);
                next.splice(to, 0, moved);
                return next;
              });
              // Keep selection following the moved item
              if (selectedIndex === from) {
                setSelectedIndex(to);
              } else if (selectedIndex !== null) {
                // Adjust selection if it was between from and to
                if (from < to && selectedIndex > from && selectedIndex <= to) {
                  setSelectedIndex(selectedIndex - 1);
                } else if (from > to && selectedIndex >= to && selectedIndex < from) {
                  setSelectedIndex(selectedIndex + 1);
                }
              }
            }}
          />
        </div>
      </div>

      <div className="spreads-tab__footer">
        {!isNew && (
          <button
            className="spreads-tab__cancel-btn"
            onClick={handleCancelEdit}
          >
            Cancel
          </button>
        )}
        <button
          className="spreads-tab__save-btn"
          onClick={handleSave}
          disabled={saving || !name.trim()}
        >
          {saving ? 'Saving...' : isNew ? 'Create Spread' : 'Save Spread'}
        </button>
      </div>
    </div>
  );

  return (
    <div className="spreads-tab">
      <Group orientation="horizontal" style={{ width: '100%', height: '100%' }}>
        <Panel defaultSize="30%" minSize="20%">
          <SpreadList
            selectedSpreadId={selectedSpread?.id ?? null}
            onSelect={handleSelect}
            onNew={handleNew}
            onClone={handleClone}
            onDelete={handleDelete}
          />
        </Panel>
        <Separator className="resize-handle" />
        <Panel minSize="30%">
          {hasSelection ? (
            editing ? renderEditor() : renderViewer()
          ) : (
            <div className="spreads-tab__empty">
              Select a spread from the list, or click "New" to create one.
            </div>
          )}
        </Panel>
      </Group>
    </div>
  );
}
