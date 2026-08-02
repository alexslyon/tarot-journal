/**
 * Card-world synonyms for the "no results" search fallback: when a
 * search comes up empty, we retry with equivalent terms — a deck that
 * calls its suit Coins should still be findable by someone typing
 * Pentacles, and vice versa. Families cover suit names across
 * traditions and languages, court ranks, and the Major Arcana cards
 * that go by different names in Marseille / RWS / Thoth decks.
 */

const FAMILIES: string[][] = [
  // Suits across traditions and languages
  ['pentacles', 'coins', 'disks', 'discs', 'deniers', 'oros'],
  ['wands', 'batons', 'bâtons', 'staves', 'rods', 'bastos'],
  ['cups', 'chalices', 'goblets', 'copas', 'coupes'],
  ['swords', 'blades', 'espadas', 'épées', 'epees'],
  ['hearts', 'cœurs', 'coeurs'],
  ['spades', 'piques'],
  ['diamonds', 'carreaux'],
  ['clubs', 'trèfles', 'trefles', 'tréboles'],
  // Groupings
  ['major arcana', 'majors', 'trumps', 'triumphs'],
  // Court ranks
  ['page', 'knave', 'jack', 'valet', 'princess'],
  ['knight', 'cavalier', 'prince'],
  // Majors that changed names between traditions
  ['strength', 'fortitude', 'lust'],
  ['temperance', 'art'],
  ['justice', 'adjustment'],
  ['the world', 'the universe'],
  ['judgement', 'judgment', 'the aeon'],
  ['the hierophant', 'the pope'],
  ['the high priestess', 'the papess', 'the popess'],
  ['the magician', 'the juggler', 'the magus'],
  ['wheel of fortune', 'the wheel'],
  ['the hanged man', 'the hanged one'],
];

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Alternative queries worth trying when `query` found nothing —
 *  each has one synonym swapped in (word-boundary matches only, so
 *  "art" never fires inside "heart"). Longest original terms are
 *  tried first so "the high priestess" wins over "priestess". */
export function synonymAlternatives(query: string): string[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const out: string[] = [];
  const pairs: { term: string; alts: string[] }[] = [];
  for (const family of FAMILIES) {
    for (const term of family) {
      pairs.push({ term, alts: family.filter(a => a !== term) });
    }
  }
  pairs.sort((a, b) => b.term.length - a.term.length);
  for (const { term, alts } of pairs) {
    const re = new RegExp(`\\b${escapeRegExp(term)}\\b`, 'i');
    if (!re.test(q)) continue;
    for (const alt of alts) {
      const candidate = q.replace(re, alt);
      if (candidate !== q && !out.includes(candidate)) out.push(candidate);
    }
  }
  return out;
}
