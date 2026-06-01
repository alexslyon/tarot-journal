import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getLenormandMeanings } from '../../../api/lenormandCombinations';
import { getReferenceSources } from '../../../api/referenceSources';
import { cardPreviewUrl } from '../../../api/images';
import RichTextViewer from '../../common/RichTextViewer';
import { useLenormandCardList, type LenormandCardEntry } from '../../../utils/useLenormandCardList';
import type { ReferenceSource, LenormandMeaning } from '../../../types';
import './LenormandCombinationsViewer.css';

interface ViewerProps {
  /** Called when the user clicks "Edit this combination" — passes (card_1, card_2). */
  onEditCombination?: (card_1: number, card_2: number) => void;
}

export default function LenormandCombinationsViewer({ onEditCombination }: ViewerProps) {
  const { cardList, defaultDeckId: lenormandDeckId } = useLenormandCardList();

  const [card1, setCard1] = useState<number | null>(null);
  const [card2, setCard2] = useState<number | null>(null);

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: () => getReferenceSources(),
  });

  const { data: meanings = [] } = useQuery<LenormandMeaning[]>({
    queryKey: ['lenormand-meanings', card1, card2],
    queryFn: () => getLenormandMeanings(card1!, card2!),
    enabled: card1 != null && card2 != null && card1 !== card2,
  });

  // Group meanings by source for display
  const grouped = useMemo(() => {
    const bySource = new Map<string, LenormandMeaning[]>();
    for (const m of meanings) {
      const key = m.source_name || '__unsourced__';
      if (!bySource.has(key)) bySource.set(key, []);
      bySource.get(key)!.push(m);
    }
    // Stable order: sources alphabetical, unsourced last
    const orderedSources = sources
      .map(s => s.name)
      .filter(name => bySource.has(name))
      .sort((a, b) => a.localeCompare(b));
    const result: { label: string; items: LenormandMeaning[] }[] = [];
    for (const name of orderedSources) {
      result.push({ label: name, items: bySource.get(name)! });
    }
    if (bySource.has('__unsourced__')) {
      result.push({ label: 'Other', items: bySource.get('__unsourced__')! });
    }
    return result;
  }, [meanings, sources]);

  const bothSelected = card1 != null && card2 != null && card1 !== card2;

  return (
    <div className="reference-section lenormand-comb-view">
      <h2 className="reference-section__title">Lenormand Combinations</h2>
      <p className="reference-section__hint">
        Look up meanings for any ordered pair of Lenormand cards. The order
        matters — Dog + Ring is different from Ring + Dog.
      </p>

      {lenormandDeckId == null && (
        <p className="lenormand-comb-view__warn">
          No default Lenormand deck is set. Card names and images come from the
          default deck — set one in Settings → General.
        </p>
      )}

      <div className="lenormand-comb-view__pickers">
        <CardPicker
          label="First card"
          value={card1}
          onChange={setCard1}
          cardList={cardList}
          excludeNum={card2}
        />
        <CardPicker
          label="Second card"
          value={card2}
          onChange={setCard2}
          cardList={cardList}
          excludeNum={card1}
        />
      </div>

      {bothSelected && meanings.length === 0 && (
        <div className="lenormand-comb-view__empty">
          <p>No meanings have been entered for this combination yet.</p>
          {onEditCombination && (
            <button
              type="button"
              className="lenormand-comb-view__edit-link"
              onClick={() => onEditCombination(card1!, card2!)}
            >
              Add meanings in Settings →
            </button>
          )}
        </div>
      )}

      {bothSelected && meanings.length > 0 && (
        <div className="lenormand-comb-view__results">
          {grouped.map(group => (
            <section key={group.label} className="lenormand-comb-view__group">
              <h3 className="lenormand-comb-view__group-label">{group.label}</h3>
              <ul className="lenormand-comb-view__items">
                {group.items.map(m => (
                  <li key={m.id} className="lenormand-comb-view__item">
                    <RichTextViewer content={m.meaning} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
          {onEditCombination && (
            <button
              type="button"
              className="lenormand-comb-view__edit-link"
              onClick={() => onEditCombination(card1!, card2!)}
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
  excludeNum,
}: {
  label: string;
  value: number | null;
  onChange: (n: number | null) => void;
  cardList: LenormandCardEntry[];
  excludeNum: number | null;
}) {
  const selected = value != null ? cardList.find(c => c.num === value) : null;
  return (
    <div className="lenormand-comb-view__picker">
      <label className="lenormand-comb-view__picker-label">{label}</label>
      <select
        value={value ?? ''}
        onChange={e => onChange(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Choose card...</option>
        {cardList.map(c => (
          <option key={c.num} value={c.num} disabled={c.num === excludeNum}>
            {c.num} · {c.name}
          </option>
        ))}
      </select>
      <div className="lenormand-comb-view__picker-image">
        {selected?.cardId ? (
          <img src={cardPreviewUrl(selected.cardId)} alt={selected.name} />
        ) : selected ? (
          <div className="lenormand-comb-view__placeholder">{selected.name}</div>
        ) : (
          <div className="lenormand-comb-view__placeholder">No selection</div>
        )}
      </div>
    </div>
  );
}
