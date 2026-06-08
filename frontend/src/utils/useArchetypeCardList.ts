import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDefaults } from '../api/settings';
import { getCards } from '../api/cards';
import { getArchetypes, type Archetype } from '../api/correspondences';
import type { Card } from '../types';

export interface ArchetypeCardEntry {
  /** `card_archetypes.id` — the stable identifier the combinations
   *  table references. */
  archetypeId: number;
  /** Display name: the archetype name (e.g. "The Fool", "Rider"). */
  name: string;
  /** Optional rank/order string for display. */
  rank: string | null;
  /** Card row id in the active default deck, if a card maps to this
   *  archetype (used for the thumbnail in the picker). */
  cardId?: number;
}

/**
 * The canonical archetype list for a given cartomancy type, paired
 * with thumbnail card ids from the user's default deck of that type.
 *
 * Returns `cardList` keyed by `card_archetypes.id` so callers can
 * pass the same identifier through to the combinations API. The
 * default-deck join is best-effort: if no deck is set or a card
 * doesn't map cleanly, the entry still appears with no thumbnail.
 */
export function useArchetypeCardList(cartomancyType: string | null): {
  cardList: ArchetypeCardEntry[];
  defaultDeckId: number | null;
} {
  const { data: defaults } = useQuery({
    queryKey: ['settings-defaults'],
    queryFn: getDefaults,
  });
  const defaultDeckId =
    (cartomancyType &&
      defaults?.default_decks &&
      defaults.default_decks[cartomancyType]) ||
    null;

  const { data: deckCards = [] } = useQuery<Card[]>({
    queryKey: ['cards', defaultDeckId],
    queryFn: () =>
      defaultDeckId != null ? getCards(defaultDeckId) : Promise.resolve([]),
    enabled: defaultDeckId != null,
  });

  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', cartomancyType],
    queryFn: () => (cartomancyType ? getArchetypes(cartomancyType) : Promise.resolve([])),
    enabled: !!cartomancyType,
  });

  const cardList = useMemo<ArchetypeCardEntry[]>(() => {
    // First default-deck card per archetype name (some decks have
    // multiple variants of one archetype; the picker just needs one
    // thumbnail).
    const cardByArchetypeName = new Map<string, Card>();
    for (const c of deckCards) {
      if (!c.archetype) continue;
      if (!cardByArchetypeName.has(c.archetype)) {
        cardByArchetypeName.set(c.archetype, c);
      }
    }
    return archetypes.map(a => {
      const card = cardByArchetypeName.get(a.name);
      return {
        archetypeId: a.id,
        name: a.name,
        rank: a.rank ?? null,
        cardId: card?.id,
      };
    });
  }, [archetypes, deckCards]);

  return { cardList, defaultDeckId };
}
