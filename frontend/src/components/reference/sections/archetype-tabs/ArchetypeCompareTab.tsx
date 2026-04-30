import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDecks, getCartomancyTypes } from '../../../../api/decks';
import { getCards, getCard } from '../../../../api/cards';
import { getDefaults } from '../../../../api/settings';
import { cardPreviewUrl } from '../../../../api/images';
import { getCardCorrespondences } from '../../../../api/correspondences';
import { getArchetypes } from '../../../../api/correspondences';
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

// The card detail endpoint returns these joined extras alongside the Card row.
interface CardDetail extends Card {
  card_custom_fields?: Array<{
    field_name: string;
    field_value: string | null;
    field_type: string;
  }>;
}

function plainTextHasContent(value: string | null | undefined): boolean {
  if (!value) return false;
  return value.replace(/<[^>]*>/g, '').trim().length > 0;
}

interface Props {
  archetype: Archetype;
  cartomancyType: string;
}

// Per-side deck choice is remembered by cartomancy type so it persists as
// the user flips between archetypes within the same type. Card choice is
// not persisted — each column re-derives its default card from the parent
// archetype every time the deck or archetype changes.
const STORAGE = (which: 'left' | 'right', cartomancyType: string) =>
  `archetypes-viewer.compare.${which}.${cartomancyType}`;

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

  const { data: defaults } = useQuery({
    queryKey: ['settings-defaults'],
    queryFn: getDefaults,
  });
  const defaultDeckId =
    (defaults?.default_decks && defaults.default_decks[cartomancyType]) || null;

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
        cartomancyType={cartomancyType}
        decks={decks}
        defaultDeckId={defaultDeckId}
      />
      <CompareColumn
        side="right"
        archetype={archetype}
        cartomancyType={cartomancyType}
        decks={decks}
        defaultDeckId={defaultDeckId}
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
  cartomancyType,
  decks,
  defaultDeckId,
}: {
  side: 'left' | 'right';
  archetype: Archetype;
  cartomancyType: string;
  decks: Deck[];
  defaultDeckId: number | null;
}) {
  const [deckId, setDeckId] = useState<number | null>(null);
  useEffect(() => {
    // Re-evaluate only on cartomancy/decks/default changes — the deck choice
    // sticks across archetype switches.
    const saved = localStorage.getItem(STORAGE(side, cartomancyType));
    const savedNum = saved ? Number(saved) : null;
    if (savedNum && decks.some(d => d.id === savedNum)) {
      setDeckId(savedNum);
      return;
    }
    if (decks.length === 0) {
      setDeckId(null);
      return;
    }
    // Left column prefers the cartomancy type's default deck; right column
    // prefers any deck other than the default so the user sees two distinct
    // cards by default rather than the same one twice.
    if (side === 'left') {
      const left = defaultDeckId && decks.some(d => d.id === defaultDeckId)
        ? defaultDeckId
        : decks[0].id;
      setDeckId(left);
    } else {
      const otherThanDefault = decks.find(d => d.id !== defaultDeckId);
      setDeckId((otherThanDefault ?? decks[Math.min(1, decks.length - 1)]).id);
    }
  }, [cartomancyType, decks, side, defaultDeckId]);
  useEffect(() => {
    if (deckId != null) {
      localStorage.setItem(STORAGE(side, cartomancyType), String(deckId));
    }
  }, [cartomancyType, deckId, side]);

  const { data: deckCards = [] } = useQuery<Card[]>({
    queryKey: ['cards', deckId],
    queryFn: () => (deckId != null ? getCards(deckId) : Promise.resolve([])),
    enabled: deckId != null,
  });

  // Card pick: defaults to the card whose archetype matches the parent
  // selection, falls back to the first card. Reset whenever the deck or the
  // parent archetype changes — manual picks are intentionally session-local
  // so the user can compare arbitrary pairs without persisted state getting
  // in the way of the simpler "follow the archetype" flow.
  const [cardId, setCardId] = useState<number | null>(null);
  useEffect(() => {
    if (deckCards.length === 0) {
      setCardId(null);
      return;
    }
    const match = deckCards.find(c => c.archetype === archetype.name);
    setCardId((match ?? deckCards[0]).id);
  }, [deckCards, archetype.name]);

  const selectedCard = useMemo(
    () => deckCards.find(c => c.id === cardId) || null,
    [deckCards, cardId],
  );

  const { data: corrs = [] } = useQuery<ResolvedCorrespondence[]>({
    queryKey: ['card-correspondences', selectedCard?.id],
    queryFn: () => getCardCorrespondences(selectedCard!.id),
    enabled: selectedCard?.id != null,
  });
  const corrMap = useMemo(() => {
    const m = new Map<string, ResolvedCorrespondence>();
    for (const c of corrs) m.set(c.field_name, c);
    return m;
  }, [corrs]);

  // Full card detail for custom fields. The basic deck listing doesn't carry
  // them; we have to fetch each card individually.
  const { data: cardDetail } = useQuery<CardDetail>({
    queryKey: ['card-detail', selectedCard?.id],
    queryFn: () => getCard(selectedCard!.id),
    enabled: selectedCard?.id != null,
  });
  const customFields = useMemo(() => {
    if (!cardDetail) return [] as { field_name: string; field_value: string }[];
    // Legacy JSON blob in card.custom_fields
    let legacy: Record<string, string> = {};
    if (cardDetail.custom_fields) {
      try { legacy = JSON.parse(cardDetail.custom_fields); }
      catch { /* ignore parse errors on legacy data */ }
    }
    const legacyEntries = Object.entries(legacy)
      .filter(([_, v]) => plainTextHasContent(v))
      .map(([field_name, field_value]) => ({ field_name, field_value }));
    const tableEntries = (cardDetail.card_custom_fields || [])
      .filter(f => plainTextHasContent(f.field_value))
      .map(f => ({ field_name: f.field_name, field_value: f.field_value || '' }));
    return [...legacyEntries, ...tableEntries];
  }, [cardDetail]);

  // Notes are tied to whichever archetype this column's card belongs to —
  // when the columns hold cards with different archetypes (the whole point
  // of arbitrary card comparison), each column shows its own card's notes.
  // Resolve archetype id by looking up the card's archetype name in the
  // cached archetypes list for this cartomancy type.
  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', cartomancyType],
    queryFn: () => getArchetypes(cartomancyType),
  });
  const cardArchetypeId = useMemo(() => {
    if (!selectedCard?.archetype) return null;
    const match = archetypes.find(a => a.name === selectedCard.archetype);
    return match?.id ?? null;
  }, [archetypes, selectedCard?.archetype]);

  const { data: notes = [] } = useQuery<ArchetypeNoteEntry[]>({
    queryKey: ['archetype-notes', cardArchetypeId],
    queryFn: () => getArchetypeNotes(cardArchetypeId!),
    enabled: cardArchetypeId != null,
  });

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
      <div className="archetype-compare__selectors">
        <select
          className="archetype-compare__deck-select"
          value={deckId ?? ''}
          onChange={e => setDeckId(e.target.value ? Number(e.target.value) : null)}
        >
          {decks.map(d => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
        <select
          className="archetype-compare__card-select"
          value={cardId ?? ''}
          onChange={e => setCardId(e.target.value ? Number(e.target.value) : null)}
          disabled={deckCards.length === 0}
        >
          {deckCards.length === 0 && <option value="">No cards</option>}
          {deckCards.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      <div className="archetype-compare__image-wrap">
        {selectedCard ? (
          <img
            className="archetype-compare__image"
            src={cardPreviewUrl(selectedCard.id)}
            alt={selectedCard.name}
          />
        ) : (
          <div className="archetype-compare__no-image">
            This deck has no cards.
          </div>
        )}
      </div>

      {selectedCard && (
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

      {customFields.length > 0 && (
        <div className="archetype-compare__custom">
          {customFields.map((f, i) => (
            <div key={`${f.field_name}-${i}`} className="archetype-compare__custom-field">
              <h5>{f.field_name}</h5>
              <RichTextViewer content={f.field_value} />
            </div>
          ))}
        </div>
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
