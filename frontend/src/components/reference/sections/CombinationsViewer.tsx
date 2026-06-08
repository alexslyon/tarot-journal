import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCombinationMeanings } from '../../../api/combinations';
import { getReferenceSources } from '../../../api/referenceSources';
import { cardPreviewUrl } from '../../../api/images';
import RichTextViewer from '../../common/RichTextViewer';
import {
  useArchetypeCardList,
  type ArchetypeCardEntry,
} from '../../../utils/useArchetypeCardList';
import {
  SUPPORTED_COMBINATION_TYPES,
  type CombinationCartomancyType,
} from '../../settings/sections/CombinationsSection';
import type { ReferenceSource, CombinationMeaning } from '../../../types';
import './CombinationsViewer.css';

interface ViewerProps {
  /** Called when the user clicks "Edit this combination" — passes the
   *  type and both archetype ids. */
  onEditCombination?: (
    cartomancyType: string,
    archetype_1_id: number,
    archetype_2_id: number,
  ) => void;
}

export default function CombinationsViewer({ onEditCombination }: ViewerProps) {
  const [cartomancyType, setCartomancyType] =
    useState<CombinationCartomancyType>('Lenormand');
  const [card1Id, setCard1Id] = useState<number | null>(null);
  const [card2Id, setCard2Id] = useState<number | null>(null);

  useEffect(() => {
    setCard1Id(null);
    setCard2Id(null);
  }, [cartomancyType]);

  const { cardList, defaultDeckId } = useArchetypeCardList(cartomancyType);

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: () => getReferenceSources(),
  });

  const { data: meanings = [] } = useQuery<CombinationMeaning[]>({
    queryKey: ['combination-meanings', cartomancyType, card1Id, card2Id],
    queryFn: () => getCombinationMeanings(cartomancyType, card1Id!, card2Id!),
    enabled: card1Id != null && card2Id != null && card1Id !== card2Id,
  });

  const grouped = useMemo(() => {
    const bySource = new Map<string, CombinationMeaning[]>();
    for (const m of meanings) {
      const key = m.source_name || '__unsourced__';
      if (!bySource.has(key)) bySource.set(key, []);
      bySource.get(key)!.push(m);
    }
    const orderedSources = sources
      .map(s => s.name)
      .filter(name => bySource.has(name))
      .sort((a, b) => a.localeCompare(b));
    const result: { label: string; items: CombinationMeaning[] }[] = [];
    for (const name of orderedSources) {
      result.push({ label: name, items: bySource.get(name)! });
    }
    if (bySource.has('__unsourced__')) {
      result.push({ label: 'Other', items: bySource.get('__unsourced__')! });
    }
    return result;
  }, [meanings, sources]);

  const bothSelected = card1Id != null && card2Id != null && card1Id !== card2Id;

  return (
    <div className="reference-section combinations-view">
      <h2 className="reference-section__title">Combinations</h2>
      <p className="reference-section__hint">
        Look up meanings for any ordered pair of cards. The order matters — in
        Lenormand, for instance, Dog + Ring reads differently from Ring + Dog.
      </p>

      <div className="combinations-view__type-row">
        <label className="combinations-view__type-label">Cartomancy type</label>
        <select
          value={cartomancyType}
          onChange={e => setCartomancyType(e.target.value as CombinationCartomancyType)}
        >
          {SUPPORTED_COMBINATION_TYPES.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {defaultDeckId == null && (
        <p className="combinations-view__warn">
          No default {cartomancyType} deck is set. Card thumbnails come from
          the default deck — set one in Settings → General.
        </p>
      )}

      <div className="combinations-view__pickers">
        <CardPicker
          label="First card"
          value={card1Id}
          onChange={setCard1Id}
          cardList={cardList}
          excludeId={card2Id}
        />
        <CardPicker
          label="Second card"
          value={card2Id}
          onChange={setCard2Id}
          cardList={cardList}
          excludeId={card1Id}
        />
      </div>

      {bothSelected && meanings.length === 0 && (
        <div className="combinations-view__empty">
          <p>No meanings have been entered for this combination yet.</p>
          {onEditCombination && (
            <button
              type="button"
              className="combinations-view__edit-link"
              onClick={() => onEditCombination(cartomancyType, card1Id!, card2Id!)}
            >
              Add meanings in Settings →
            </button>
          )}
        </div>
      )}

      {bothSelected && meanings.length > 0 && (
        <div className="combinations-view__results">
          {grouped.map(group => (
            <section key={group.label} className="combinations-view__group">
              <h3 className="combinations-view__group-label">{group.label}</h3>
              <ul className="combinations-view__items">
                {group.items.map(m => (
                  <li key={m.id} className="combinations-view__item">
                    <RichTextViewer content={m.meaning} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
          {onEditCombination && (
            <button
              type="button"
              className="combinations-view__edit-link"
              onClick={() => onEditCombination(cartomancyType, card1Id!, card2Id!)}
            >
              Edit this combination →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function CardPicker({
  label,
  value,
  onChange,
  cardList,
  excludeId,
}: {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
  cardList: ArchetypeCardEntry[];
  excludeId: number | null;
}) {
  const selected = value != null ? cardList.find(c => c.archetypeId === value) : null;
  return (
    <div className="combinations-view__picker">
      <label className="combinations-view__picker-label">{label}</label>
      <select
        value={value ?? ''}
        onChange={e => onChange(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Choose card...</option>
        {cardList.map(c => (
          <option
            key={c.archetypeId}
            value={c.archetypeId}
            disabled={c.archetypeId === excludeId}
          >
            {c.rank ? `${c.rank} · ${c.name}` : c.name}
          </option>
        ))}
      </select>
      <div className="combinations-view__picker-image">
        {selected?.cardId ? (
          <img src={cardPreviewUrl(selected.cardId)} alt={selected.name} />
        ) : selected ? (
          <div className="combinations-view__placeholder">{selected.name}</div>
        ) : (
          <div className="combinations-view__placeholder">No selection</div>
        )}
      </div>
    </div>
  );
}
