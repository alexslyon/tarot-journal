import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDecks, getCartomancyTypes } from '../../../../api/decks';
import { getCards } from '../../../../api/cards';
import { cardPreviewUrl } from '../../../../api/images';
import { getCardCorrespondences } from '../../../../api/correspondences';
import { getArchetypeNotes } from '../../../../api/archetypeNotes';
import RichTextViewer from '../../../common/RichTextViewer';
import {
  CORRESPONDENCE_FIELDS,
  CORRESPONDENCE_FIELD_LABELS,
} from '../../../../types';
import type {
  Deck,
  Card,
  CartomancyType,
  ResolvedCorrespondence,
  ArchetypeNoteEntry,
} from '../../../../types';
import type { Archetype } from '../../../../api/correspondences';
import './ArchetypeCompareTab.css';

interface Props {
  archetype: Archetype;
  cartomancyType: string;
}

const STORAGE = (which: 'left' | 'right', archetypeId: number) =>
  `archetypes-viewer.compare.${which}.${archetypeId}`;

export default function ArchetypeCompareTab({ archetype, cartomancyType }: Props) {
  const { data: types = [] } = useQuery<CartomancyType[]>({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });
  const typeId = useMemo(
    () => types.find(t => t.name === cartomancyType)?.id,
    [types, cartomancyType],
  );

  const { data: decks = [] } = useQuery<Deck[]>({
    queryKey: ['decks', typeId],
    queryFn: () => getDecks(typeId),
    enabled: typeId != null,
  });

  // Notes are per-archetype (deck-independent), so they're shared across
  // both columns — fetch once and pass to both.
  const { data: notes = [] } = useQuery<ArchetypeNoteEntry[]>({
    queryKey: ['archetype-notes', archetype.id],
    queryFn: () => getArchetypeNotes(archetype.id),
  });

  if (decks.length < 2) {
    return (
      <div className="archetype-compare archetype-compare--empty">
        Need at least two {cartomancyType} decks in your library to compare.
      </div>
    );
  }

  return (
    <div className="archetype-compare">
      <CompareColumn
        side="left"
        archetype={archetype}
        decks={decks}
        notes={notes}
      />
      <CompareColumn
        side="right"
        archetype={archetype}
        decks={decks}
        notes={notes}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// One column of the comparison
// ---------------------------------------------------------------------------

function CompareColumn({
  side,
  archetype,
  decks,
  notes,
}: {
  side: 'left' | 'right';
  archetype: Archetype;
  decks: Deck[];
  notes: ArchetypeNoteEntry[];
}) {
  const [deckId, setDeckId] = useState<number | null>(null);
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE(side, archetype.id));
    const savedNum = saved ? Number(saved) : null;
    if (savedNum && decks.some(d => d.id === savedNum)) {
      setDeckId(savedNum);
    } else if (decks.length > 0) {
      // Default the right column to the second deck so the user gets a
      // useful default comparison out of the box.
      setDeckId(decks[side === 'left' ? 0 : Math.min(1, decks.length - 1)].id);
    } else {
      setDeckId(null);
    }
  }, [archetype.id, decks, side]);
  useEffect(() => {
    if (deckId != null) {
      localStorage.setItem(STORAGE(side, archetype.id), String(deckId));
    }
  }, [archetype.id, deckId, side]);

  const { data: deckCards = [] } = useQuery<Card[]>({
    queryKey: ['cards', deckId],
    queryFn: () => (deckId != null ? getCards(deckId) : Promise.resolve([])),
    enabled: deckId != null,
  });
  const matchingCard = useMemo(
    () => deckCards.find(c => c.archetype === archetype.name) || null,
    [deckCards, archetype.name],
  );

  const { data: corrs = [] } = useQuery<ResolvedCorrespondence[]>({
    queryKey: ['card-correspondences', matchingCard?.id],
    queryFn: () => getCardCorrespondences(matchingCard!.id),
    enabled: matchingCard?.id != null,
  });
  const corrMap = useMemo(() => {
    const m = new Map<string, ResolvedCorrespondence>();
    for (const c of corrs) m.set(c.field_name, c);
    return m;
  }, [corrs]);

  // Group notes by field for display, same shape as the Notes sub-tab.
  const noteFields = useMemo(() => {
    const m = new Map<number, { fieldName: string; fieldOrder: number; entries: ArchetypeNoteEntry[] }>();
    for (const e of notes) {
      const fid = e.field_def_id;
      if (!m.has(fid)) {
        m.set(fid, {
          fieldName: e.field_name || '',
          fieldOrder: e.field_order ?? 0,
          entries: [],
        });
      }
      if (e.id != null) m.get(fid)!.entries.push(e);
    }
    return [...m.entries()]
      .filter(([, v]) => v.entries.length > 0)
      .sort((a, b) =>
        a[1].fieldOrder !== b[1].fieldOrder
          ? a[1].fieldOrder - b[1].fieldOrder
          : a[0] - b[0],
      );
  }, [notes]);

  return (
    <div className="archetype-compare__col">
      <div className="archetype-compare__deck-row">
        <select
          value={deckId ?? ''}
          onChange={e => setDeckId(e.target.value ? Number(e.target.value) : null)}
        >
          {decks.map(d => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>

      <div className="archetype-compare__image-wrap">
        {matchingCard ? (
          <img
            className="archetype-compare__image"
            src={cardPreviewUrl(matchingCard.id)}
            alt={archetype.name}
          />
        ) : (
          <div className="archetype-compare__no-image">
            This deck doesn't have "{archetype.name}".
          </div>
        )}
      </div>

      {matchingCard && (
        <dl className="archetype-compare__corr">
          {CORRESPONDENCE_FIELDS.map(f => {
            const c = corrMap.get(f);
            const values = c?.values || [];
            if (values.length === 0) return null;
            return (
              <div key={f} className="archetype-compare__corr-row">
                <dt>{CORRESPONDENCE_FIELD_LABELS[f] || f}</dt>
                <dd>{values.join(', ')}</dd>
              </div>
            );
          })}
        </dl>
      )}

      {noteFields.length > 0 && (
        <div className="archetype-compare__notes">
          {noteFields.map(([fid, info]) => (
            <section key={fid} className="archetype-compare__note-field">
              <h5>{info.fieldName}</h5>
              <ul>
                {info.entries.map(e => (
                  <li key={e.id}>
                    <RichTextViewer content={e.content} />
                    {e.source_name && (
                      <span className="archetype-compare__note-source">
                        — {e.source_name}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
