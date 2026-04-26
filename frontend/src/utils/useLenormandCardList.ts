import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDefaults } from '../api/settings';
import { getCards } from '../api/cards';
import { getArchetypes, type Archetype } from '../api/correspondences';
import type { Card } from '../types';

export interface LenormandCardEntry {
  /** Canonical Lenormand position, 1-36. */
  num: number;
  /** Display name — from the default deck if available, otherwise the
   *  canonical archetype name. */
  name: string;
  /** Card row id in the default deck if present (used for image preview). */
  cardId?: number;
}

/**
 * Build the canonical 1-36 Lenormand card list, with names and image ids
 * pulled from the user's default Lenormand deck.
 *
 * Card position comes from the `card_archetypes` table (where ranks are 1-36)
 * joined via each deck card's `archetype` field — NOT from the deck card's
 * own `rank` field, which often stores the playing-card inset (e.g. "King",
 * "Ace", "6") and therefore doesn't map to the 1-36 numbering.
 */
export function useLenormandCardList(): {
  cardList: LenormandCardEntry[];
  defaultDeckId: number | null;
} {
  const { data: defaults } = useQuery({
    queryKey: ['settings-defaults'],
    queryFn: getDefaults,
  });
  const defaultDeckId =
    (defaults?.default_decks && defaults.default_decks['Lenormand']) || null;

  const { data: deckCards = [] } = useQuery<Card[]>({
    queryKey: ['cards', defaultDeckId],
    queryFn: () => (defaultDeckId != null ? getCards(defaultDeckId) : Promise.resolve([])),
    enabled: defaultDeckId != null,
  });

  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', 'Lenormand'],
    queryFn: () => getArchetypes('Lenormand'),
  });

  const cardList = useMemo<LenormandCardEntry[]>(() => {
    // archetype name -> canonical rank
    const archetypeToRank = new Map<string, number>();
    for (const a of archetypes) {
      const n = parseInt(a.rank || '0', 10);
      if (n >= 1 && n <= 36) archetypeToRank.set(a.name, n);
    }
    // canonical archetype name lookup keyed by rank (for fallback name)
    const archetypeNameByRank = new Map<number, string>();
    for (const [name, rank] of archetypeToRank) {
      if (!archetypeNameByRank.has(rank)) archetypeNameByRank.set(rank, name);
    }

    // Default deck cards keyed by canonical rank, via archetype name.
    const byRank = new Map<number, Card>();
    for (const c of deckCards) {
      if (!c.archetype) continue;
      const rank = archetypeToRank.get(c.archetype);
      if (rank && !byRank.has(rank)) byRank.set(rank, c);
    }

    return Array.from({ length: 36 }, (_, i) => {
      const num = i + 1;
      const card = byRank.get(num);
      const fallbackName = archetypeNameByRank.get(num) || `Card ${num}`;
      return {
        num,
        name: card?.name || fallbackName,
        cardId: card?.id,
      };
    });
  }, [deckCards, archetypes]);

  return { cardList, defaultDeckId };
}
