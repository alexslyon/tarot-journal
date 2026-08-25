import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCombinationMeanings, getCombinationPartners, getReversedCombinationTypes } from '../../../api/combinations';
import { MeaningsEditor } from '../../combinations/MeaningsEditor';
import { useToast } from '../../../context/ToastContext';
import { getReferenceSources } from '../../../api/referenceSources';
import { cardPreviewUrl } from '../../../api/images';
import RichTextViewer from '../../common/RichTextViewer';
import SearchCombobox from '../../common/SearchCombobox';
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

export default function CombinationsViewer() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [cartomancyType, setCartomancyType] =
    useState<CombinationCartomancyType>('Lenormand');
  const [card1Id, setCard1Id] = useState<number | null>(null);
  const [card2Id, setCard2Id] = useState<number | null>(null);
  const [card1Rev, setCard1Rev] = useState(false);
  const [card2Rev, setCard2Rev] = useState(false);
  // Two-card by default; triad mode adds a third slot.
  const [triad, setTriad] = useState(false);
  const [card3Id, setCard3Id] = useState<number | null>(null);
  const [card3Rev, setCard3Rev] = useState(false);
  const effCard3 = triad ? card3Id : null;

  useEffect(() => {
    setCard1Id(null);
    setCard2Id(null);
    setCard1Rev(false);
    setCard2Rev(false);
    setCard3Id(null);
    setCard3Rev(false);
  }, [cartomancyType]);

  const { data: reversedTypes = [] } = useQuery<string[]>({
    queryKey: ['combination-reversed-types'],
    queryFn: getReversedCombinationTypes,
  });
  const reversalsEnabled = reversedTypes.includes(cartomancyType);

  const { cardList, defaultDeckId } = useArchetypeCardList(cartomancyType);

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: () => getReferenceSources(),
  });

  // "has meanings" hints for the second/third card dropdowns
  const { data: partners2 = {} } = useQuery({
    queryKey: ['combination-partners', cartomancyType, card1Id, card1Rev, triad],
    queryFn: () => getCombinationPartners({
      cartomancyType, card1: card1Id!, card1Reversed: card1Rev, triad,
    }),
    enabled: card1Id != null,
  });
  const { data: partners3 = {} } = useQuery({
    queryKey: ['combination-partners3', cartomancyType, card1Id, card1Rev, card2Id, card2Rev],
    queryFn: () => getCombinationPartners({
      cartomancyType, card1: card1Id!, card1Reversed: card1Rev,
      triad: true, card2: card2Id, card2Reversed: card2Rev,
    }),
    enabled: triad && card1Id != null && card2Id != null,
  });

  const meaningsKey = ['combination-meanings', cartomancyType, card1Id, card1Rev, card2Id, card2Rev, effCard3, card3Rev];
  const { data: meanings = [] } = useQuery<CombinationMeaning[]>({
    queryKey: meaningsKey,
    queryFn: () => getCombinationMeanings(cartomancyType, card1Id!, card2Id!, card1Rev, card2Rev, effCard3, card3Rev),
    enabled: card1Id != null && card2Id != null && card1Id !== card2Id
      && (!triad || (card3Id != null && card3Id !== card1Id && card3Id !== card2Id)),
  });
  const invalidateMeanings = () =>
    queryClient.invalidateQueries({ queryKey: meaningsKey });

  // Inline editing — the meat of authoring happens right here, no
  // Settings round-trip. Editing state resets when the pair changes.
  const [editing, setEditing] = useState(false);
  // Whether edit mode should open with the add form already showing
  // (true when entered from an empty combination's "+ Add meanings").
  const [editStartsAdding, setEditStartsAdding] = useState(false);
  useEffect(() => {
    setEditing(false);
  }, [cartomancyType, card1Id, card2Id, card1Rev, card2Rev, effCard3, card3Rev]);
  // Attribution only offers sources covering this deck type.
  const typeSources = useMemo(
    () => sources.filter(s => s.cartomancy_types.includes(cartomancyType)),
    [sources, cartomancyType],
  );

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

  const bothSelected = card1Id != null && card2Id != null && card1Id !== card2Id
    && (!triad || (card3Id != null && card3Id !== card1Id && card3Id !== card2Id));

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
        <div className="combinations-view__count-toggle" role="group" aria-label="Combination size">
          <button
            type="button"
            className={!triad ? 'combinations-view__count-btn--active' : ''}
            onClick={() => setTriad(false)}
          >
            Two cards
          </button>
          <button
            type="button"
            className={triad ? 'combinations-view__count-btn--active' : ''}
            onClick={() => setTriad(true)}
          >
            Three cards
          </button>
        </div>
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
          excludeIds={[card2Id, effCard3]}
          reversed={card1Rev}
          onReversedChange={reversalsEnabled ? setCard1Rev : undefined}
        />
        <CardPicker
          label="Second card"
          value={card2Id}
          onChange={setCard2Id}
          cardList={cardList}
          populated={partners2}
          excludeIds={[card1Id, effCard3]}
          reversed={card2Rev}
          onReversedChange={reversalsEnabled ? setCard2Rev : undefined}
        />
        {triad && (
          <CardPicker
            label="Third card"
            value={card3Id}
            onChange={setCard3Id}
            cardList={cardList}
            populated={partners3}
            excludeIds={[card1Id, card2Id]}
            reversed={card3Rev}
            onReversedChange={reversalsEnabled ? setCard3Rev : undefined}
          />
        )}
      </div>

      {bothSelected && editing && (
        <div className="combinations-view__results">
          <div className="combinations-view__edit-bar">
            <button type="button" onClick={() => setEditing(false)}>
              Done editing
            </button>
          </div>
          <MeaningsEditor
            cartomancyType={cartomancyType}
            card1Id={card1Id!}
            card2Id={card2Id!}
            card1Rev={card1Rev}
            card2Rev={card2Rev}
            card3Id={effCard3}
            card3Rev={card3Rev}
            startAdding={editStartsAdding}
            meanings={meanings}
            sources={typeSources}
            onChanged={invalidateMeanings}
            showToast={showToast}
          />
        </div>
      )}

      {bothSelected && !editing && meanings.length === 0 && (
        <div className="combinations-view__empty">
          <p>No meanings have been entered for this combination yet.</p>
          <button
            type="button"
            className="combinations-view__edit-link"
            onClick={() => { setEditStartsAdding(true); setEditing(true); }}
          >
            + Add meanings
          </button>
        </div>
      )}

      {bothSelected && !editing && meanings.length > 0 && (
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
          <button
            type="button"
            className="combinations-view__edit-link"
            onClick={() => { setEditStartsAdding(false); setEditing(true); }}
          >
            Edit
          </button>
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
  excludeIds,
  reversed = false,
  onReversedChange,
  populated,
}: {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
  cardList: ArchetypeCardEntry[];
  excludeIds: (number | null)[];
  reversed?: boolean;
  /** archetype id -> authored meaning count, for dropdown hints. */
  populated?: Record<string, number>;
  onReversedChange?: (reversed: boolean) => void;
}) {
  const selected = value != null ? cardList.find(c => c.archetypeId === value) : null;
  return (
    <div className="combinations-view__picker">
      <label className="combinations-view__picker-label">{label}</label>
      <SearchCombobox
        options={cardList
          .filter(c => !excludeIds.includes(c.archetypeId))
          .map(c => {
            const count = populated?.[String(c.archetypeId)];
            return {
              id: c.archetypeId,
              label: c.rank ? `${c.rank} · ${c.name}` : c.name,
              keywords: [c.name],
              hint: count ? `${count} meaning${count === 1 ? '' : 's'}` : undefined,
            };
          })}
        value={value ?? undefined}
        onSelect={opt => onChange(opt ? opt.id : null)}
        placeholder="Type to search cards…"
      />
      {onReversedChange && (
        <label className="combinations-view__reversed-check">
          <input
            type="checkbox"
            checked={reversed}
            onChange={e => onReversedChange(e.target.checked)}
          />
          <span>Reversed</span>
        </label>
      )}
      <div className={`combinations-view__picker-image ${reversed ? 'combinations-view__picker-image--reversed' : ''}`}>
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
