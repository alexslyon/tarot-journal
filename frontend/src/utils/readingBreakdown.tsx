/**
 * Reading Breakdown — pure helpers, value-render lookup, and the hook
 * that assembles per-reading + aggregate breakdowns from a journal entry.
 *
 * Initial implementation renders all values as text. The renderBreakdownValue
 * function is the single touch-point for swapping in glyphs later (per the
 * planning doc's three-tier glyph plan).
 */
import { useQueries } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { getCardCorrespondences } from '../api/correspondences';
import {
  CORRESPONDENCE_FIELDS,
  CORRESPONDENCE_FIELD_LABELS,
} from '../types';
import type {
  CardUsed,
  EntryReadingParsed,
  JournalEntryFull,
  ResolvedCorrespondence,
} from '../types';

// ───────────────────────────────────────────────────────────────────────
// Types
// ───────────────────────────────────────────────────────────────────────

export interface BreakdownColumn {
  /** The raw value (used for lookup keys, sort tiebreaks). */
  value: string;
  /** Number of cards in the tab whose categorized value equals `value`. */
  count: number;
}

export interface BreakdownRow {
  /** Stable key — 'suit', 'rank', or a correspondence field_name. */
  key: string;
  /** Human-readable row label. */
  label: string;
  /** Columns sorted by count descending, then alphabetically as tiebreak. */
  columns: BreakdownColumn[];
}

export interface BreakdownTab {
  /** 'all' for the aggregate, or a reading id. */
  id: 'all' | number;
  /** Display label — the spread name for per-reading tabs, "All Readings" for aggregate. */
  label: string;
  /** Cards counted into this tab (deduped by occurrence, not by card_id —
   *  a card appearing twice across two readings counts twice). */
  cardCount: number;
  /** Rows in the table. Suit + Rank first, then correspondence rows. */
  rows: BreakdownRow[];
}

export interface BreakdownData {
  isLoading: boolean;
  /** One per reading + an "all" aggregate. Always at least one tab when
   *  the entry has readings. */
  tabs: BreakdownTab[];
  /** Correspondence field_names that have at least one value somewhere in
   *  the entry — used to populate the filter popover. Order follows
   *  CORRESPONDENCE_FIELDS. */
  presentCorrespondenceFields: string[];
}

// ───────────────────────────────────────────────────────────────────────
// Pure helpers — rank/suit categorization per cartomancy type
// ───────────────────────────────────────────────────────────────────────

const TAROT_MINOR_OF_RE = /^(.+?) of (.+)$/;

/**
 * Derive the rank/suit values to count this card under in the breakdown.
 * Returns null for fields that don't apply (e.g. major arcana cards have
 * no meaningful rank).
 *
 * Rules:
 *   - Tarot: parse from canonical archetype name ("Knight of Wands"
 *     → rank=Knight, suit=Wands). Major arcana → suit="Major Arcana",
 *     rank=null. Falls back to card.rank/suit if archetype isn't set.
 *   - Lenormand / Playing Cards: use card.rank/card.suit directly.
 *     Lenormand cards are seeded with their playing-card associations,
 *     so this surfaces the playing-card rank+suit per the design.
 *   - Other types (Oracle, I Ching, Kipper…): use whatever the card
 *     has, which may be null for both fields.
 */
export function getCardCategories(card: CardUsed): {
  rank: string | null;
  suit: string | null;
} {
  const type = card.cartomancy_type;

  if (type === 'Tarot') {
    if (card.archetype) {
      const m = card.archetype.match(TAROT_MINOR_OF_RE);
      if (m) return { rank: m[1], suit: m[2] };
      return { rank: null, suit: 'Major Arcana' };
    }
    return { rank: card.rank ?? null, suit: card.suit ?? null };
  }

  return { rank: card.rank ?? null, suit: card.suit ?? null };
}

// ───────────────────────────────────────────────────────────────────────
// Build a tab from a list of (cards, correspondences)
// ───────────────────────────────────────────────────────────────────────

interface CardWithCorrespondences {
  card: CardUsed;
  correspondences: ResolvedCorrespondence[];
}

function tallyToColumns(tally: Map<string, number>): BreakdownColumn[] {
  return [...tally.entries()]
    .map(([value, count]) => ({ value, count }))
    .sort(
      (a, b) =>
        b.count - a.count || a.value.localeCompare(b.value),
    );
}

export function buildBreakdownTab(
  id: 'all' | number,
  label: string,
  cards: CardWithCorrespondences[],
): BreakdownTab {
  const suitTally = new Map<string, number>();
  const rankTally = new Map<string, number>();
  // field_name -> value -> count
  const corrTallies = new Map<string, Map<string, number>>();

  for (const { card, correspondences } of cards) {
    const { rank, suit } = getCardCategories(card);
    if (suit) suitTally.set(suit, (suitTally.get(suit) || 0) + 1);
    if (rank) rankTally.set(rank, (rankTally.get(rank) || 0) + 1);

    for (const c of correspondences) {
      if (!c.values || c.values.length === 0) continue;
      let inner = corrTallies.get(c.field_name);
      if (!inner) {
        inner = new Map();
        corrTallies.set(c.field_name, inner);
      }
      // Multi-valued correspondences (e.g. a card may have two elements)
      // each contribute one to the count.
      for (const v of c.values) {
        inner.set(v, (inner.get(v) || 0) + 1);
      }
    }
  }

  const rows: BreakdownRow[] = [];
  if (suitTally.size > 0) {
    rows.push({ key: 'suit', label: 'Suit', columns: tallyToColumns(suitTally) });
  }
  if (rankTally.size > 0) {
    rows.push({ key: 'rank', label: 'Rank', columns: tallyToColumns(rankTally) });
  }
  // Correspondence rows in canonical CORRESPONDENCE_FIELDS order so the
  // table layout doesn't reshuffle as cards change.
  for (const field of CORRESPONDENCE_FIELDS) {
    const tally = corrTallies.get(field);
    if (!tally || tally.size === 0) continue;
    rows.push({
      key: field,
      label: CORRESPONDENCE_FIELD_LABELS[field] || field,
      columns: tallyToColumns(tally),
    });
  }

  return { id, label, cardCount: cards.length, rows };
}

// ───────────────────────────────────────────────────────────────────────
// Render lookup — single touch-point for future glyph swap
// ───────────────────────────────────────────────────────────────────────

/**
 * Render a correspondence/rank/suit value for display. Initial implementation
 * is text-only; per the planning doc, swapping in glyphs (Unicode for
 * Tier 1, SVG for Tier 2/3) is meant to be a one-line change here per
 * correspondence type. Add `if (field === 'hebrew_letter') return <HebrewGlyph value={value} />`
 * style branches as the glyph library lands.
 */
export function renderBreakdownValue(
  _field: string,
  value: string,
): ReactNode {
  return value;
}

// ───────────────────────────────────────────────────────────────────────
// Hook — fetches each unique card's correspondences and assembles tabs
// ───────────────────────────────────────────────────────────────────────

export function useEntryBreakdown(entry: JournalEntryFull | undefined): BreakdownData {
  // Collect every unique card_id across all readings — react-query dedupes
  // per id so a card appearing in multiple readings only fetches once.
  const uniqueCardIds = (() => {
    if (!entry) return [] as number[];
    const seen = new Set<number>();
    for (const r of entry.readings) {
      for (const c of r.cards_used || []) {
        if (c.card_id) seen.add(c.card_id);
      }
    }
    return [...seen];
  })();

  const queries = useQueries({
    queries: uniqueCardIds.map(id => ({
      queryKey: ['card-correspondences', id],
      queryFn: () => getCardCorrespondences(id),
    })),
  });

  const isLoading = queries.some(q => q.isLoading);
  const corrByCardId = new Map<number, ResolvedCorrespondence[]>();
  uniqueCardIds.forEach((id, i) => {
    corrByCardId.set(id, queries[i].data || []);
  });

  if (!entry || entry.readings.length === 0) {
    return { isLoading: false, tabs: [], presentCorrespondenceFields: [] };
  }

  // Build per-reading tabs.
  const perReading: BreakdownTab[] = entry.readings.map(reading =>
    buildBreakdownTab(
      reading.id,
      reading.spread_name || 'Reading',
      readingCards(reading, corrByCardId),
    ),
  );

  // Aggregate tab — concat all reading cards. A card appearing twice
  // across readings counts twice (per the design doc).
  const allCards: CardWithCorrespondences[] = [];
  for (const r of entry.readings) {
    for (const cwc of readingCards(r, corrByCardId)) allCards.push(cwc);
  }
  const aggregate = buildBreakdownTab('all', 'All Readings', allCards);

  // Tabs: per-reading first, aggregate last. If only one reading, the
  // aggregate is identical — UI hides tabs in that case.
  const tabs = perReading.length === 1 ? [perReading[0]] : [...perReading, aggregate];

  // Which correspondence fields appeared anywhere in the entry — drives
  // the filter popover. Use the aggregate's row keys (it sees all cards).
  const presentCorrespondenceFields = aggregate.rows
    .filter(r => r.key !== 'suit' && r.key !== 'rank')
    .map(r => r.key);

  return { isLoading, tabs, presentCorrespondenceFields };
}

function readingCards(
  reading: EntryReadingParsed,
  corrByCardId: Map<number, ResolvedCorrespondence[]>,
): CardWithCorrespondences[] {
  const out: CardWithCorrespondences[] = [];
  for (const card of reading.cards_used || []) {
    // Skip cards whose card_id never resolved — per the design they're
    // silently excluded, no "unassigned" column.
    if (!card.card_id) continue;
    out.push({
      card,
      correspondences: corrByCardId.get(card.card_id) || [],
    });
  }
  return out;
}
