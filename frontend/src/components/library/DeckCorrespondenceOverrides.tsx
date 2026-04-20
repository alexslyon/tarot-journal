import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getDeckCorrespondenceOverrides,
  setDeckCorrespondenceOverride,
  deleteDeckCorrespondenceGroup,
  getArchetypes,
  getFieldOptions,
  type DeckCorrespondenceOverride,
  type Archetype,
  type FieldOption,
} from '../../api/correspondences';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../types';
import MultiValueSelect from '../common/MultiValueSelect';
import FreeTextValue from '../common/FreeTextValue';
import { getBulkGroups, getBulkCategories, filterArchetypesByGroup } from '../../utils/bulkGroups';
import './DeckCorrespondenceOverrides.css';

interface DeckCorrespondenceOverridesProps {
  deckId: number;
  cartomancyType?: string;
}

/** One visible row: all values any card received for this (group, field). */
type GroupedOverride = {
  source_group: string;
  field_name: string;
  values: string[];
  card_count: number;
};

export default function DeckCorrespondenceOverrides({
  deckId,
  cartomancyType = 'Tarot',
}: DeckCorrespondenceOverridesProps) {
  const queryClient = useQueryClient();

  const [showBulkAdd, setShowBulkAdd] = useState(false);
  const [bulkGroup, setBulkGroup] = useState('');
  const [bulkField, setBulkField] = useState<string>(CORRESPONDENCE_FIELDS[0]);
  const [bulkValues, setBulkValues] = useState<string[]>([]);
  const [bulkApplying, setBulkApplying] = useState(false);

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

  const BULK_GROUPS = getBulkGroups(cartomancyType);
  const BULK_CATEGORIES = getBulkCategories(BULK_GROUPS);

  // Roll up override rows by (source_group, field). All rows share the same
  // set of values across archetypes (bulk apply writes them identically), so
  // we just collect distinct values and count the archetypes affected.
  const grouped = new Map<string, GroupedOverride>();
  for (const o of overrides) {
    if (!o.source_group) continue; // legacy per-archetype rows are hidden
    const key = `${o.source_group}:${o.field_name}`;
    if (!grouped.has(key)) {
      grouped.set(key, {
        source_group: o.source_group,
        field_name: o.field_name,
        values: [],
        card_count: 0,
      });
    }
    const g = grouped.get(key)!;
    if (!g.values.includes(o.field_value)) g.values.push(o.field_value);
  }
  // Count distinct archetypes per group+field
  const cardCounts = new Map<string, Set<number>>();
  for (const o of overrides) {
    if (!o.source_group) continue;
    const key = `${o.source_group}:${o.field_name}`;
    if (!cardCounts.has(key)) cardCounts.set(key, new Set());
    cardCounts.get(key)!.add(o.archetype_id);
  }
  for (const [key, g] of grouped) {
    g.card_count = cardCounts.get(key)?.size ?? 0;
  }

  const groupedList = [...grouped.values()].sort((a, b) => {
    if (a.source_group !== b.source_group) {
      return a.source_group.localeCompare(b.source_group);
    }
    return a.field_name.localeCompare(b.field_name);
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['deck-correspondence-overrides', deckId] });
    queryClient.invalidateQueries({ queryKey: ['card-correspondences'] });
  };

  const handleUpdateGroup = async (
    groupLabel: string,
    fieldName: string,
    values: string[],
  ) => {
    const targets = filterArchetypesByGroup(archetypes, BULK_GROUPS, groupLabel);
    if (targets.length === 0) return;
    if (values.length === 0) {
      await deleteDeckCorrespondenceGroup(deckId, groupLabel, fieldName);
    } else {
      for (const a of targets) {
        await setDeckCorrespondenceOverride(deckId, a.id, fieldName, values, groupLabel);
      }
    }
    invalidate();
  };

  const handleRemoveGroup = async (groupLabel: string, fieldName: string) => {
    await deleteDeckCorrespondenceGroup(deckId, groupLabel, fieldName);
    invalidate();
  };

  const handleBulkAdd = async () => {
    if (!bulkGroup || !bulkField || bulkValues.length === 0) return;
    const targets = filterArchetypesByGroup(archetypes, BULK_GROUPS, bulkGroup);
    if (targets.length === 0) return;
    setBulkApplying(true);
    try {
      for (const a of targets) {
        await setDeckCorrespondenceOverride(deckId, a.id, bulkField, bulkValues, bulkGroup);
      }
      invalidate();
      setShowBulkAdd(false);
      setBulkGroup('');
      setBulkField(CORRESPONDENCE_FIELDS[0]);
      setBulkValues([]);
    } finally {
      setBulkApplying(false);
    }
  };

  return (
    <div className="deck-corr-overrides">
      <p className="deck-corr-overrides__hint">
        Deck-level overrides apply to a whole group of cards (all Wands, all
        Pages, etc.) and take precedence over the correspondence system.
        Individual cards can still override them.
      </p>

      {groupedList.length === 0 && !showBulkAdd && (
        <p className="deck-corr-overrides__empty">No group overrides for this deck.</p>
      )}

      {groupedList.length > 0 && (
        <div className="deck-corr-overrides__list">
          {groupedList.map(g => (
            <div key={`${g.source_group}:${g.field_name}`} className="deck-corr-overrides__row">
              <span className="deck-corr-overrides__archetype">
                {g.source_group}
                <span className="deck-corr-overrides__count"> · {g.card_count} cards</span>
              </span>
              <span className="deck-corr-overrides__field">
                {CORRESPONDENCE_FIELD_LABELS[g.field_name] || g.field_name}
              </span>
              <div className="deck-corr-overrides__values">
                {g.field_name === 'numerology' ? (
                  <FreeTextValue
                    values={g.values}
                    onCommit={vals => handleUpdateGroup(g.source_group, g.field_name, vals)}
                    compact
                  />
                ) : (
                  <MultiValueSelect
                    values={g.values}
                    options={optionsByField.get(g.field_name) || []}
                    onCommit={vals => handleUpdateGroup(g.source_group, g.field_name, vals)}
                    compact
                  />
                )}
              </div>
              <button
                type="button"
                className="deck-corr-overrides__remove-btn"
                onClick={() => handleRemoveGroup(g.source_group, g.field_name)}
                title="Remove this group override"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {showBulkAdd ? (
        <div className="deck-corr-overrides__add-form">
          <div className="deck-corr-overrides__add-row">
            <select value={bulkGroup} onChange={e => setBulkGroup(e.target.value)}>
              <option value="">Choose group...</option>
              {BULK_CATEGORIES.map(cat => (
                <optgroup key={cat} label={cat}>
                  {BULK_GROUPS.filter(g => g.category === cat).map(g => (
                    <option key={g.label} value={g.label}>{g.label}</option>
                  ))}
                </optgroup>
              ))}
            </select>
            <select value={bulkField} onChange={e => setBulkField(e.target.value)}>
              {CORRESPONDENCE_FIELDS.map(f => (
                <option key={f} value={f}>{CORRESPONDENCE_FIELD_LABELS[f]}</option>
              ))}
            </select>
            <div className="deck-corr-overrides__add-values">
              {bulkField === 'numerology' ? (
                <FreeTextValue
                  values={bulkValues}
                  onCommit={setBulkValues}
                  compact
                  placeholder="Values..."
                />
              ) : (
                <MultiValueSelect
                  values={bulkValues}
                  options={optionsByField.get(bulkField) || []}
                  onCommit={setBulkValues}
                  compact
                  placeholder="Values..."
                />
              )}
            </div>
          </div>
          <div className="deck-corr-overrides__add-actions">
            <button
              type="button"
              onClick={() => { setShowBulkAdd(false); setBulkGroup(''); setBulkValues([]); }}
              disabled={bulkApplying}
            >
              Cancel
            </button>
            <button
              type="button"
              className="deck-corr-overrides__save-btn"
              onClick={handleBulkAdd}
              disabled={!bulkGroup || bulkValues.length === 0 || bulkApplying}
            >
              {bulkApplying ? 'Applying...' : 'Apply to Group'}
            </button>
          </div>
        </div>
      ) : BULK_GROUPS.length > 0 ? (
        <button type="button" className="deck-corr-overrides__add-btn" onClick={() => setShowBulkAdd(true)}>
          + Add Group Override
        </button>
      ) : null}
    </div>
  );
}
