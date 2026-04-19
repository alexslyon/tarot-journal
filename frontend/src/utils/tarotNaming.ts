/**
 * Tarot naming/ordering transformations for correspondence systems.
 * Applies only when cartomancy_type is 'Tarot'.
 *
 * The underlying archetype_id is unchanged — only the display label
 * (and, for Marseille, the displayed rank number) is transformed.
 */

export type TarotNamingStyle = 'RWS' | 'Thoth' | 'Marseille';

// Thoth renames applied on top of the canonical RWS names
const THOTH_NAME_OVERRIDES: Record<string, string> = {
  // Major Arcana renames
  'The Magician': 'The Magus',
  'The High Priestess': 'The Priestess',
  'Strength': 'Lust',
  'Justice': 'Adjustment',
  'Temperance': 'Art',
  'Judgement': 'The Aeon',
  'The World': 'The Universe',
};

// Suit name overrides for Thoth. Pentacles is called Disks in Thoth decks.
const THOTH_SUIT_OVERRIDES: Record<string, string> = {
  'Pentacles': 'Disks',
};

/** Translate a suit name (e.g. "Pentacles") under the given style. */
export function displaySuitName(
  suit: string,
  namingStyle: string | null | undefined,
): string {
  if (namingStyle === 'Thoth' && THOTH_SUIT_OVERRIDES[suit]) {
    return THOTH_SUIT_OVERRIDES[suit];
  }
  return suit;
}

function applyThothSuitRename(name: string): string {
  for (const [from, to] of Object.entries(THOTH_SUIT_OVERRIDES)) {
    // Replace "of Pentacles" → "of Disks" (with word boundary to avoid
    // accidentally replacing inside other tokens)
    name = name.replace(new RegExp(`\\bof ${from}\\b`), `of ${to}`);
  }
  return name;
}

function thothCourtRename(name: string): string {
  if (name.startsWith('Page of ')) return 'Princess of ' + name.slice('Page of '.length);
  if (name.startsWith('Knight of ')) return 'Prince of ' + name.slice('Knight of '.length);
  if (name.startsWith('King of ')) return 'Knight of ' + name.slice('King of '.length);
  return name;
}

export function displayArchetypeName(
  name: string,
  namingStyle: string | null | undefined,
): string {
  if (!namingStyle || namingStyle === 'RWS') return name;
  if (namingStyle === 'Thoth') {
    const majorOverride = THOTH_NAME_OVERRIDES[name];
    if (majorOverride) return majorOverride;
    return applyThothSuitRename(thothCourtRename(name));
  }
  // Marseille uses canonical RWS names — the ordering swap is handled at
  // sort time, not via name remapping
  return name;
}

/** Translate a group/suit label for display under the given style. */
export function displayGroupLabel(
  label: string,
  namingStyle: string | null | undefined,
): string {
  if (namingStyle === 'Thoth' && THOTH_SUIT_OVERRIDES[label]) {
    return THOTH_SUIT_OVERRIDES[label];
  }
  return label;
}

/**
 * Under Marseille / Pre-Golden Dawn ordering, Justice is #8 and Strength is
 * #11 (the reverse of RWS). Return the numeric rank that should be displayed
 * for a given archetype under the selected naming style.
 */
export function displayArchetypeRank(
  name: string,
  rank: string | null,
  namingStyle: string | null | undefined,
): string {
  if (!rank) return '';
  if (namingStyle === 'Marseille') {
    if (name === 'Strength') return '11';
    if (name === 'Justice') return '8';
  }
  return rank;
}

/**
 * Compute the sort key for an archetype under the selected naming style.
 * For Marseille we swap Strength (8 → 11) and Justice (11 → 8). Minor
 * arcana ranks are unchanged across all styles.
 */
export function archetypeSortKey(
  name: string,
  rank: string | null,
  namingStyle: string | null | undefined,
): number {
  const n = parseInt(rank || '0', 10);
  if (namingStyle === 'Marseille') {
    if (name === 'Strength') return 11;
    if (name === 'Justice') return 8;
  }
  return n;
}
