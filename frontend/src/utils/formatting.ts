import type { Deck } from '../types';

/** Format a date string as a short date (e.g. "Mar 22, 2026"). */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

/** Format just the time portion (e.g. "3:15 PM"). */
export function formatTimeOnly(dateStr: string | null): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleTimeString(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

/** Bucket a date for the journal list's group headers: "Today",
 *  "Yesterday", "This Week" (past 7 days), "This Month", then
 *  month-year labels like "June 2026" for anything older. */
export function entryDateBucket(dateStr: string | null): string {
  if (!dateStr) return 'Undated';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return 'Undated';

  const now = new Date();
  const startOfDay = (x: Date) =>
    new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const dayMs = 24 * 60 * 60 * 1000;
  const diffDays = Math.round((startOfDay(now) - startOfDay(d)) / dayMs);

  if (diffDays <= 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return 'This Week';
  if (d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()) {
    return 'This Month';
  }
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'long' });
}

/** Format a date string as date + time (e.g. "March 22, 2026, 03:15 PM"). */
export function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Convert plain text (with newlines) to HTML paragraphs if it doesn't already
 * contain HTML tags. Used to prepare content for TipTap rich text editors.
 */
export function ensureHtml(text: string): string {
  if (!text) return '';
  if (/<[a-z][\s\S]*>/i.test(text)) return text;
  return text
    .split('\n')
    .map((line) => `<p>${line || '<br>'}</p>`)
    .join('');
}

/**
 * Check if a deck matches a required cartomancy type.
 * Supports both multi-type decks (cartomancy_types array)
 * and legacy single-type (cartomancy_type string).
 */
export function deckMatchesType(deck: Deck, requiredType: string): boolean {
  if (requiredType === 'Any') return true;
  if (deck.cartomancy_types && deck.cartomancy_types.length > 0) {
    return deck.cartomancy_types.some(t => t.name === requiredType);
  }
  return deck.cartomancy_type === requiredType;
}
