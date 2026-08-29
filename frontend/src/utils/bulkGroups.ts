import type { Archetype } from '../api/correspondences';
import { LENORMAND_PLAYING_CARD } from './lenormand';

export type BulkGroup = {
  label: string;
  category: string;
  filter: (a: Archetype) => boolean;
};

const TAROT_BULK_GROUPS: BulkGroup[] = [
  { label: 'Major Arcana', category: 'Card Type', filter: a => a.card_type === 'major' },
  { label: 'Minor Arcana', category: 'Card Type', filter: a => a.card_type === 'minor' },
  { label: 'Wands', category: 'Suits', filter: a => a.suit === 'Wands' },
  { label: 'Cups', category: 'Suits', filter: a => a.suit === 'Cups' },
  { label: 'Swords', category: 'Suits', filter: a => a.suit === 'Swords' },
  { label: 'Pentacles', category: 'Suits', filter: a => a.suit === 'Pentacles' },
  { label: 'Pages', category: 'Court Ranks', filter: a => a.name.startsWith('Page of') },
  { label: 'Knights', category: 'Court Ranks', filter: a => a.name.startsWith('Knight of') },
  { label: 'Queens', category: 'Court Ranks', filter: a => a.name.startsWith('Queen of') },
  { label: 'Kings', category: 'Court Ranks', filter: a => a.name.startsWith('King of') },
  { label: 'Court Cards', category: 'Court Ranks', filter: a => {
    if (a.card_type !== 'minor') return false;
    const rankNum = parseInt(a.rank?.slice(-2) || '0');
    return rankNum >= 11 && rankNum <= 14;
  }},
  { label: 'Aces', category: 'Pip Numbers', filter: a => a.name.startsWith('Ace of') },
  { label: 'Twos', category: 'Pip Numbers', filter: a => a.name.startsWith('Two of') },
  { label: 'Threes', category: 'Pip Numbers', filter: a => a.name.startsWith('Three of') },
  { label: 'Fours', category: 'Pip Numbers', filter: a => a.name.startsWith('Four of') },
  { label: 'Fives', category: 'Pip Numbers', filter: a => a.name.startsWith('Five of') },
  { label: 'Sixes', category: 'Pip Numbers', filter: a => a.name.startsWith('Six of') },
  { label: 'Sevens', category: 'Pip Numbers', filter: a => a.name.startsWith('Seven of') },
  { label: 'Eights', category: 'Pip Numbers', filter: a => a.name.startsWith('Eight of') },
  { label: 'Nines', category: 'Pip Numbers', filter: a => a.name.startsWith('Nine of') },
  { label: 'Tens', category: 'Pip Numbers', filter: a => a.name.startsWith('Ten of') },
  { label: 'Pips (Ace-10)', category: 'Pip Numbers', filter: a => {
    if (a.card_type !== 'minor') return false;
    const rankNum = parseInt(a.rank?.slice(-2) || '0');
    return rankNum >= 1 && rankNum <= 10;
  }},
];

const PLAYING_CARDS_BULK_GROUPS: BulkGroup[] = [
  { label: 'Hearts', category: 'Suits', filter: a => a.suit === 'Hearts' },
  { label: 'Diamonds', category: 'Suits', filter: a => a.suit === 'Diamonds' },
  { label: 'Clubs', category: 'Suits', filter: a => a.suit === 'Clubs' },
  { label: 'Spades', category: 'Suits', filter: a => a.suit === 'Spades' },
  { label: 'Aces', category: 'Ranks', filter: a => a.rank === 'Ace' },
  { label: 'Twos', category: 'Ranks', filter: a => a.rank === 'Two' },
  { label: 'Threes', category: 'Ranks', filter: a => a.rank === 'Three' },
  { label: 'Fours', category: 'Ranks', filter: a => a.rank === 'Four' },
  { label: 'Fives', category: 'Ranks', filter: a => a.rank === 'Five' },
  { label: 'Sixes', category: 'Ranks', filter: a => a.rank === 'Six' },
  { label: 'Sevens', category: 'Ranks', filter: a => a.rank === 'Seven' },
  { label: 'Eights', category: 'Ranks', filter: a => a.rank === 'Eight' },
  { label: 'Nines', category: 'Ranks', filter: a => a.rank === 'Nine' },
  { label: 'Tens', category: 'Ranks', filter: a => a.rank === 'Ten' },
  { label: 'Jacks', category: 'Ranks', filter: a => a.rank === 'Jack' },
  { label: 'Queens', category: 'Ranks', filter: a => a.rank === 'Queen' },
  { label: 'Kings', category: 'Ranks', filter: a => a.rank === 'King' },
  { label: 'Jokers', category: 'Ranks', filter: a => a.rank === 'Joker' },
];

// Lenormand cards each have a traditional playing-card inset. Group by that
// inset's suit and rank so "Aces" in Lenormand = Ring/Man/Woman/Sun, etc.
const LENORMAND_BULK_GROUPS: BulkGroup[] = [
  { label: 'Hearts', category: 'Suits',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.suit === 'Hearts' },
  { label: 'Diamonds', category: 'Suits',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.suit === 'Diamonds' },
  { label: 'Clubs', category: 'Suits',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.suit === 'Clubs' },
  { label: 'Spades', category: 'Suits',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.suit === 'Spades' },
  { label: 'Aces', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Ace' },
  { label: 'Sixes', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Six' },
  { label: 'Sevens', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Seven' },
  { label: 'Eights', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Eight' },
  { label: 'Nines', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Nine' },
  { label: 'Tens', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Ten' },
  { label: 'Jacks', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Jack' },
  { label: 'Queens', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Queen' },
  { label: 'Kings', category: 'Ranks',
    filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'King' },
];

const GROUPS_BY_TYPE: Record<string, BulkGroup[]> = {
  'Tarot': TAROT_BULK_GROUPS,
  'Playing Cards': PLAYING_CARDS_BULK_GROUPS,
  'Petit Lenormand': LENORMAND_BULK_GROUPS,
};

export function getBulkGroups(
  cartomancyType: string,
  archetypes: Archetype[] = [],
): BulkGroup[] {
  const preset = GROUPS_BY_TYPE[cartomancyType];
  if (preset) return preset;
  return deriveGroupsFromArchetypes(archetypes);
}

/** Types without a curated list get groups straight from their own
 *  archetype data: every distinct suit and every distinct rank that
 *  covers at least two cards becomes a group. This is what makes the
 *  Sibillas (playing-card rank/suit on every archetype), Spanish
 *  Playing Cards, and any future custom type work without touching
 *  this file. Single-member "groups" are skipped as noise — that also
 *  keeps unique-numbered types (Kipper, I Ching) from listing every
 *  card as its own group. */
function deriveGroupsFromArchetypes(archetypes: Archetype[]): BulkGroup[] {
  const suitCounts = new Map<string, number>();
  const rankCounts = new Map<string, number>();
  for (const a of archetypes) {
    if (a.suit) suitCounts.set(a.suit, (suitCounts.get(a.suit) ?? 0) + 1);
    if (a.rank) rankCounts.set(a.rank, (rankCounts.get(a.rank) ?? 0) + 1);
  }
  const groups: BulkGroup[] = [];
  for (const [suit, count] of suitCounts) {
    if (count < 2) continue;
    groups.push({ label: suit, category: 'Suits', filter: a => a.suit === suit });
  }
  for (const [rank, count] of rankCounts) {
    if (count < 2) continue;
    groups.push({ label: rank, category: 'Ranks', filter: a => a.rank === rank });
  }
  return groups;
}

/** Ordered list of unique category names (preserves BULK_GROUPS order). */
export function getBulkCategories(groups: BulkGroup[]): string[] {
  const out: string[] = [];
  for (const g of groups) {
    if (!out.includes(g.category)) out.push(g.category);
  }
  return out;
}

export function filterArchetypesByGroup(
  archetypes: Archetype[],
  groups: BulkGroup[],
  groupLabel: string,
): Archetype[] {
  const group = groups.find(g => g.label === groupLabel);
  if (!group) return [];
  return archetypes.filter(group.filter);
}
