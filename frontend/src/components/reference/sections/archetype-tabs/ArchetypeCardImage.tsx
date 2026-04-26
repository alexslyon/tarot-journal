import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDecks, getCartomancyTypes } from '../../../../api/decks';
import { getCards } from '../../../../api/cards';
import { cardPreviewUrl } from '../../../../api/images';
import type { Archetype } from '../../../../api/correspondences';
import type { Deck, Card, CartomancyType } from '../../../../types';
import './ArchetypeCardImage.css';

interface Props {
  archetype: Archetype;
  cartomancyType: string;
  /** Optional className passed through to the outer container so consumers
   *  can compose layouts (e.g. side-by-side with the tab content). */
  className?: string;
}

/**
 * Shows the selected card from a deck of choice. Used as the top banner of
 * the Languages, Correspondences, and Notes sub-tabs. Deck selection is
 * remembered per archetype across sessions, shared across all consumers.
 */
const STORAGE_KEY = (archetypeId: number) =>
  `archetypes-viewer.image.deck.${archetypeId}`;

export default function ArchetypeCardImage({ archetype, cartomancyType, className }: Props) {
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

  const [deckId, setDeckId] = useState<number | null>(null);
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY(archetype.id));
    const savedNum = saved ? Number(saved) : null;
    if (savedNum && decks.some(d => d.id === savedNum)) {
      setDeckId(savedNum);
    } else if (decks.length > 0) {
      setDeckId(decks[0].id);
    } else {
      setDeckId(null);
    }
  }, [archetype.id, decks]);
  useEffect(() => {
    if (deckId != null) {
      localStorage.setItem(STORAGE_KEY(archetype.id), String(deckId));
    }
  }, [archetype.id, deckId]);

  const { data: deckCards = [] } = useQuery<Card[]>({
    queryKey: ['cards', deckId],
    queryFn: () => (deckId != null ? getCards(deckId) : Promise.resolve([])),
    enabled: deckId != null,
  });
  const matchingCard = useMemo(
    () => deckCards.find(c => c.archetype === archetype.name) || null,
    [deckCards, archetype.name],
  );

  if (decks.length === 0) {
    return (
      <aside className={`archetype-card-image ${className || ''}`}>
        <p className="archetype-card-image__empty">
          No {cartomancyType} decks in your library yet.
        </p>
      </aside>
    );
  }

  return (
    <aside className={`archetype-card-image ${className || ''}`}>
      <div className="archetype-card-image__viewer">
        {matchingCard ? (
          <img
            className="archetype-card-image__img"
            src={cardPreviewUrl(matchingCard.id)}
            alt={archetype.name}
          />
        ) : (
          <div className="archetype-card-image__placeholder">
            No matching card in this deck.
          </div>
        )}
      </div>
      <select
        className="archetype-card-image__deck"
        value={deckId ?? ''}
        onChange={e => setDeckId(e.target.value ? Number(e.target.value) : null)}
      >
        {decks.map(d => (
          <option key={d.id} value={d.id}>{d.name}</option>
        ))}
      </select>
    </aside>
  );
}
