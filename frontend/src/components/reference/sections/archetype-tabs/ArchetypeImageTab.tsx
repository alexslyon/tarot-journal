import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDecks, getCartomancyTypes } from '../../../../api/decks';
import { getCards } from '../../../../api/cards';
import { cardPreviewUrl } from '../../../../api/images';
import type { Archetype } from '../../../../api/correspondences';
import type { Deck, Card, CartomancyType } from '../../../../types';
import './ArchetypeImageTab.css';

interface Props {
  archetype: Archetype;
  cartomancyType: string;
}

/**
 * Saved last-deck-per-archetype, so picking a deck for "The Fool" remembers it
 * across sessions and across navigation between archetypes.
 */
const STORAGE_KEY = (archetypeId: number) =>
  `archetypes-viewer.image.deck.${archetypeId}`;

export default function ArchetypeImageTab({ archetype, cartomancyType }: Props) {
  // Look up the cartomancy type id so we can filter decks server-side.
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

  // Saved selection per archetype, with a fallback to the first available deck.
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

  // Find the matching card in the selected deck via the archetype name.
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
      <div className="archetype-image">
        <p className="archetype-image__empty">
          No {cartomancyType} decks in your library yet. Add a deck to view its
          cards here.
        </p>
      </div>
    );
  }

  return (
    <div className="archetype-image">
      <div className="archetype-image__deck-row">
        <label className="archetype-image__label">Deck</label>
        <select
          value={deckId ?? ''}
          onChange={e => setDeckId(e.target.value ? Number(e.target.value) : null)}
        >
          {decks.map(d => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>
      <div className="archetype-image__viewer">
        {matchingCard ? (
          <img
            className="archetype-image__img"
            src={cardPreviewUrl(matchingCard.id)}
            alt={`${archetype.name} from ${decks.find(d => d.id === deckId)?.name ?? ''}`}
          />
        ) : (
          <div className="archetype-image__placeholder">
            This deck doesn't have a card matching "{archetype.name}".
          </div>
        )}
      </div>
    </div>
  );
}
