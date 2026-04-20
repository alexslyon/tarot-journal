/**
 * Golden Dawn decan attributions for Tarot pip cards (Two through Ten of each suit).
 * Aces get numerology = 1 but no decan — they represent the pure elemental root.
 *
 * Source: Standard Golden Dawn / RWS-era attributions. Mirrors the RWS seed data
 * in database/correspondence_seed.py.
 */

export const TAROT_PIP_DECANS: Record<string, string> = {
  // Wands (Fire) — Aries, Leo, Sagittarius
  'Two of Wands':   'Mars in Aries',
  'Three of Wands': 'Sun in Aries',
  'Four of Wands':  'Venus in Aries',
  'Five of Wands':  'Saturn in Leo',
  'Six of Wands':   'Jupiter in Leo',
  'Seven of Wands': 'Mars in Leo',
  'Eight of Wands': 'Mercury in Sagittarius',
  'Nine of Wands':  'Moon in Sagittarius',
  'Ten of Wands':   'Saturn in Sagittarius',
  // Cups (Water) — Cancer, Scorpio, Pisces
  'Two of Cups':    'Venus in Cancer',
  'Three of Cups':  'Mercury in Cancer',
  'Four of Cups':   'Moon in Cancer',
  'Five of Cups':   'Mars in Scorpio',
  'Six of Cups':    'Sun in Scorpio',
  'Seven of Cups':  'Venus in Scorpio',
  'Eight of Cups':  'Saturn in Pisces',
  'Nine of Cups':   'Jupiter in Pisces',
  'Ten of Cups':    'Mars in Pisces',
  // Swords (Air) — Libra, Aquarius, Gemini
  'Two of Swords':   'Moon in Libra',
  'Three of Swords': 'Saturn in Libra',
  'Four of Swords':  'Jupiter in Libra',
  'Five of Swords':  'Venus in Aquarius',
  'Six of Swords':   'Mercury in Aquarius',
  'Seven of Swords': 'Moon in Aquarius',
  'Eight of Swords': 'Jupiter in Gemini',
  'Nine of Swords':  'Mars in Gemini',
  'Ten of Swords':   'Sun in Gemini',
  // Pentacles (Earth) — Capricorn, Taurus, Virgo
  'Two of Pentacles':   'Jupiter in Capricorn',
  'Three of Pentacles': 'Mars in Capricorn',
  'Four of Pentacles':  'Sun in Capricorn',
  'Five of Pentacles':  'Mercury in Taurus',
  'Six of Pentacles':   'Moon in Taurus',
  'Seven of Pentacles': 'Saturn in Taurus',
  'Eight of Pentacles': 'Sun in Virgo',
  'Nine of Pentacles':  'Venus in Virgo',
  'Ten of Pentacles':   'Mercury in Virgo',
};

/** Rank-name prefix → numerology value. Only pip ranks (Ace-Ten); court cards omitted. */
const PIP_RANK_NAME_TO_NUMBER: Record<string, string> = {
  'Ace': '1', 'Two': '2', 'Three': '3', 'Four': '4', 'Five': '5',
  'Six': '6', 'Seven': '7', 'Eight': '8', 'Nine': '9', 'Ten': '10',
};

/**
 * If the archetype is a Tarot pip card (Ace-Ten of any suit), return its
 * numerology value. Returns null for majors and courts.
 */
export function tarotPipNumerology(archetypeName: string): string | null {
  const rankName = archetypeName.split(' of ')[0];
  return PIP_RANK_NAME_TO_NUMBER[rankName] ?? null;
}

/**
 * If the archetype is a pip 2-10, return its Golden Dawn decan string.
 * Aces and everything else return null.
 */
export function tarotPipDecan(archetypeName: string): string | null {
  return TAROT_PIP_DECANS[archetypeName] ?? null;
}
