import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getDeckCorrespondenceOverrides,
  setDeckCorrespondenceOverride,
  deleteDeckCorrespondenceOverride,
  getArchetypes,
  getFieldOptions,
  type DeckCorrespondenceOverride,
  type Archetype,
  type FieldOption,
} from '../../api/correspondences';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../types';
import MultiValueSelect from '../common/MultiValueSelect';
import FreeTextValue from '../common/FreeTextValue';
import './DeckCorrespondenceOverrides.css';

interface DeckCorrespondenceOverridesProps {
  deckId: number;
  cartomancyType?: string;
}

/** Group existing overrides by (archetype, field) key for display. */
type GroupedOverride = {
  archetype_id: number;
  archetype_name: string;
  field_name: string;
  values: string[];
};

export default function DeckCorrespondenceOverrides({
  deckId,
  cartomancyType = 'Tarot',
}: DeckCorrespondenceOverridesProps) {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [newArchetypeId, setNewArchetypeId] = useState<number | ''>('');
  const [newField, setNewField] = useState<string>(CORRESPONDENCE_FIELDS[0]);
  const [newValues, setNewValues] = useState<string[]>([]);

  const { data: overrides = [] } = useQuery<DeckCorrespondenceOverride[]>({
    queryKey: ['deck-correspondence-overrides', deckId],
    queryFn: () => getDeckCorrespondenceOverrides(deckId),
  });

  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', cartomancyType],
    queryFn: () => getArchetypes(cartomancyType),
  });

  const { data: allFieldOptions = [] } = useQuery<FieldOption[]>({
    queryKey: ['field-options', 'all'],
    queryFn: () => getFieldOptions(),
  });

  const optionsByField = new Map<string, string[]>();
  for (const opt of allFieldOptions) {
    if (!optionsByField.has(opt.field_name)) optionsByField.set(opt.field_name, []);
    optionsByField.get(opt.field_name)!.push(opt.option_value);
  }

  // Group override rows by (archetype, field)
  const grouped = new Map<string, GroupedOverride>();
  for (const o of overrides) {
    const key = `${o.archetype_id}:${o.field_name}`;
    if (!grouped.has(key)) {
      grouped.set(key, {
        archetype_id: o.archetype_id,
        archetype_name: o.archetype_name,
        field_name: o.field_name,
        values: [],
      });
    }
    grouped.get(key)!.values.push(o.field_value);
  }

  const sortedArchetypes = [...archetypes].sort((a, b) => {
    const aRank = parseInt(a.rank || '0', 10);
    const bRank = parseInt(b.rank || '0', 10);
    return aRank - bRank;
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['deck-correspondence-overrides', deckId] });
    queryClient.invalidateQueries({ queryKey: ['card-correspondences'] });
  };

  const handleAdd = async () => {
    if (!newArchetypeId || !newField || newValues.length === 0) return;
    await setDeckCorrespondenceOverride(deckId, newArchetypeId, newField, newValues);
    invalidate();
    setShowAdd(false);
    setNewArchetypeId('');
    setNewField(CORRESPONDENCE_FIELDS[0]);
    setNewValues([]);
  };

  const handleUpdate = async (archetypeId: number, fieldName: string, values: string[]) => {
    if (values.length === 0) {
      await deleteDeckCorrespondenceOverride(deckId, archetypeId, fieldName);
    } else {
      await setDeckCorrespondenceOverride(deckId, archetypeId, fieldName, values);
    }
    invalidate();
  };

  const handleRemove = async (archetypeId: number, fieldName: string) => {
    await deleteDeckCorrespondenceOverride(deckId, archetypeId, fieldName);
    invalidate();
  };

  const groupedList = [...grouped.values()].sort((a, b) => {
    if (a.archetype_name !== b.archetype_name) {
      return a.archetype_name.localeCompare(b.archetype_name);
    }
    return a.field_name.localeCompare(b.field_name);
  });

  return (
    <div className="deck-corr-overrides">
      <p className="deck-corr-overrides__hint">
        Deck-level overrides apply to all cards in this deck with the given
        archetype. They take precedence over the correspondence system but can
        still be overridden on individual cards.
      </p>

      {groupedList.length === 0 && !showAdd && (
        <p className="deck-corr-overrides__empty">No overrides for this deck.</p>
      )}

      {groupedList.length > 0 && (
        <div className="deck-corr-overrides__list">
          {groupedList.map(g => (
            <div key={`${g.archetype_id}:${g.field_name}`} className="deck-corr-overrides__row">
              <span className="deck-corr-overrides__archetype">{g.archetype_name}</span>
              <span className="deck-corr-overrides__field">
                {CORRESPONDENCE_FIELD_LABELS[g.field_name] || g.field_name}
              </span>
              <div className="deck-corr-overrides__values">
                {g.field_name === 'numerology' ? (
                  <FreeTextValue
                    values={g.values}
                    onCommit={vals => handleUpdate(g.archetype_id, g.field_name, vals)}
                    compact
                  />
                ) : (
                  <MultiValueSelect
                    values={g.values}
                    options={optionsByField.get(g.field_name) || []}
                    onCommit={vals => handleUpdate(g.archetype_id, g.field_name, vals)}
                    compact
                  />
                )}
              </div>
              <button
                type="button"
                className="deck-corr-overrides__remove-btn"
                onClick={() => handleRemove(g.archetype_id, g.field_name)}
                title="Remove this override"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {showAdd ? (
        <div className="deck-corr-overrides__add-form">
          <div className="deck-corr-overrides__add-row">
            <select
              value={newArchetypeId}
              onChange={e => setNewArchetypeId(e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">Choose card...</option>
              {sortedArchetypes.map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
            <select value={newField} onChange={e => setNewField(e.target.value)}>
              {CORRESPONDENCE_FIELDS.map(f => (
                <option key={f} value={f}>{CORRESPONDENCE_FIELD_LABELS[f]}</option>
              ))}
            </select>
            <div className="deck-corr-overrides__add-values">
              {newField === 'numerology' ? (
                <FreeTextValue
                  values={newValues}
                  onCommit={setNewValues}
                  compact
                  placeholder="Values..."
                />
              ) : (
                <MultiValueSelect
                  values={newValues}
                  options={optionsByField.get(newField) || []}
                  onCommit={setNewValues}
                  compact
                  placeholder="Values..."
                />
              )}
            </div>
          </div>
          <div className="deck-corr-overrides__add-actions">
            <button type="button" onClick={() => { setShowAdd(false); setNewArchetypeId(''); setNewValues([]); }}>
              Cancel
            </button>
            <button
              type="button"
              className="deck-corr-overrides__save-btn"
              onClick={handleAdd}
              disabled={!newArchetypeId || newValues.length === 0}
            >
              Add
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="deck-corr-overrides__add-btn" onClick={() => setShowAdd(true)}>
          + Add Override
        </button>
      )}
    </div>
  );
}
