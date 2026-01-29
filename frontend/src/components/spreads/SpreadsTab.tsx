import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Panel, Group, Separator } from 'react-resizable-panels';
import { createSpread, updateSpread, deleteSpread, cloneSpread } from '../../api/spreads';
import SpreadList from './SpreadList';
import SpreadDesigner from './SpreadDesigner';
import SpreadProperties from './SpreadProperties';
import PositionLegend from './PositionLegend';
import type { Spread, SpreadPosition } from '../../types';
import './SpreadsTab.css';

export default function SpreadsTab() {
  const queryClient = useQueryClient();
  const [selectedSpread, setSelectedSpread] = useState<Spread | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);

  // Local editing state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [positions, setPositions] = useState<SpreadPosition[]>([]);
  const [allowedDeckTypes, setAllowedDeckTypes] = useState<string[]>([]);
  const [defaultDeckId, setDefaultDeckId] = useState<number | null>(null);

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
      setSelectedIndex(null);
    }
  }, [selectedSpread, isNew]);

  const handleSelect = (spread: Spread) => {
    setSelectedSpread(spread);
    setIsNew(false);
  };

  const handleNew = () => {
    setSelectedSpread(null);
    setIsNew(true);
    setName('');
    setDescription('');
    setPositions([]);
    setAllowedDeckTypes([]);
    setDefaultDeckId(null);
    setSelectedIndex(null);
  };

  const handleClone = async () => {
    if (!selectedSpread) return;
    try {
      const result = await cloneSpread(selectedSpread.id);
      queryClient.invalidateQueries({ queryKey: ['spreads'] });
      // Select the cloned spread after list refreshes
      // We'll set isNew=false and wait for the list to include it
      setSelectedSpread({
        ...selectedSpread,
        id: result.id,
        name: `Copy of ${selectedSpread.name}`,
      });
      setName(`Copy of ${selectedSpread.name}`);
      setIsNew(false);
    } catch (err) {
      console.error('Failed to clone spread:', err);
    }
  };

  const handleDelete = async () => {
    if (!selectedSpread) return;
    if (!window.confirm(`Delete "${selectedSpread.name}"? This cannot be undone.`)) return;
    try {
      await deleteSpread(selectedSpread.id);
      queryClient.invalidateQueries({ queryKey: ['spreads'] });
      setSelectedSpread(null);
      setIsNew(false);
    } catch (err) {
      console.error('Failed to delete spread:', err);
    }
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (isNew) {
        const result = await createSpread({
          name: name.trim(),
          positions,
          description: description || undefined,
          allowed_deck_types: allowedDeckTypes.length > 0 ? allowedDeckTypes : undefined,
          default_deck_id: defaultDeckId,
        });
        setIsNew(false);
        // Re-select the newly created spread
        setSelectedSpread({
          id: result.id,
          name: name.trim(),
          description,
          positions,
          cartomancy_type: null,
          allowed_deck_types: allowedDeckTypes,
          default_deck_id: defaultDeckId,
          created_at: new Date().toISOString(),
        });
      } else if (selectedSpread) {
        await updateSpread(selectedSpread.id, {
          name: name.trim(),
          positions,
          description: description || undefined,
          allowed_deck_types: allowedDeckTypes.length > 0 ? allowedDeckTypes : null,
          default_deck_id: defaultDeckId,
          clear_default_deck: defaultDeckId === null && selectedSpread.default_deck_id !== null,
        });
        setSelectedSpread({
          ...selectedSpread,
          name: name.trim(),
          description,
          positions,
          allowed_deck_types: allowedDeckTypes,
          default_deck_id: defaultDeckId,
        });
      }
      queryClient.invalidateQueries({ queryKey: ['spreads'] });
    } catch (err) {
      console.error('Failed to save spread:', err);
    } finally {
      setSaving(false);
    }
  };

  const hasSelection = selectedSpread !== null || isNew;

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
            <div className="spreads-tab__editor">
              <div className="spreads-tab__editor-scroll">
                <div className="spreads-tab__props-section">
                  <SpreadProperties
                    name={name}
                    description={description}
                    allowedDeckTypes={allowedDeckTypes}
                    defaultDeckId={defaultDeckId}
                    onNameChange={setName}
                    onDescriptionChange={setDescription}
                    onAllowedTypesChange={setAllowedDeckTypes}
                    onDefaultDeckChange={setDefaultDeckId}
                  />
                </div>

                <div className="spreads-tab__designer-section">
                  <h3 className="spreads-tab__section-title">Designer</h3>
                  <SpreadDesigner
                    positions={positions}
                    onChange={setPositions}
                    selectedIndex={selectedIndex}
                    onSelectIndex={setSelectedIndex}
                  />
                </div>

                <div className="spreads-tab__legend-section">
                  <PositionLegend
                    positions={positions}
                    selectedIndex={selectedIndex}
                    onSelectIndex={setSelectedIndex}
                  />
                </div>
              </div>

              <div className="spreads-tab__footer">
                <button
                  className="spreads-tab__save-btn"
                  onClick={handleSave}
                  disabled={saving || !name.trim()}
                >
                  {saving ? 'Saving...' : isNew ? 'Create Spread' : 'Save Spread'}
                </button>
              </div>
            </div>
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
