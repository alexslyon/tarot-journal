/**
 * Entity rosters shared by both Scribe surfaces: the kinds of
 * reference entries the app knows, their entity lists (static for
 * most kinds, fetched for numbers/suits/ranks), alias spellings, and
 * name resolution. Used by the entity-only Scribe and by the card
 * Scribe's merged imports.
 */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  getNumerologyReference,
  getRanksReference,
  getSuitsReference,
  type EntityKind,
} from '../../api/reference';

export const ENTITY_KIND_LABELS: Record<EntityKind, string> = {
  sign: 'Astrology — signs',
  planet: 'Astrology — planets',
  sephira: 'Kabbalah — sephiroth',
  path: 'Kabbalah — paths (by Hebrew letter)',
  chakra: 'Chakras',
  number: 'Numerology numbers',
  suit: 'Suits',
  rank: 'Ranks',
};

/** Kinds whose entities (and notes) are scoped to a deck type. */
export const TYPED_ENTITY_KINDS: EntityKind[] = ['suit', 'rank'];

export const ALL_ENTITY_KINDS = Object.keys(ENTITY_KIND_LABELS) as EntityKind[];

// Static entity rosters (the dynamic kinds — numbers, suits, ranks —
// load from the reference endpoints instead).
export const STATIC_ENTITIES: Partial<Record<EntityKind, string[]>> = {
  sign: ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra',
    'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'],
  planet: ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn',
    'Uranus', 'Neptune', 'Pluto'],
  sephira: ['Kether', 'Chokmah', 'Binah', 'Chesed', 'Geburah', 'Tiphareth',
    'Netzach', 'Hod', 'Yesod', 'Malkuth'],
  path: ['Aleph', 'Beth', 'Gimel', 'Daleth', 'Heh', 'Vav', 'Zayin', 'Cheth',
    'Teth', 'Yod', 'Kaph', 'Lamed', 'Mem', 'Nun', 'Samekh', 'Ayin', 'Peh',
    'Tzaddi', 'Qoph', 'Resh', 'Shin', 'Tav'],
  chakra: ['Root', 'Sacral', 'Solar Plexus', 'Heart', 'Throat', 'Third Eye',
    'Crown'],
};

// Alternate spellings folded into matching (mirrors the backend's
// alias tables).
export const ENTITY_ALIASES: Record<string, string> = {
  alef: 'Aleph', bet: 'Beth', beit: 'Beth', gimmel: 'Gimel', dalet: 'Daleth',
  he: 'Heh', hey: 'Heh', vau: 'Vav', waw: 'Vav', zain: 'Zayin',
  chet: 'Cheth', het: 'Cheth', heth: 'Cheth', tet: 'Teth', yud: 'Yod',
  caph: 'Kaph', kaf: 'Kaph', lamedh: 'Lamed', samech: 'Samekh',
  pe: 'Peh', fe: 'Peh', tsade: 'Tzaddi', tzadi: 'Tzaddi', tsadi: 'Tzaddi',
  qof: 'Qoph', kof: 'Qoph', tau: 'Tav', taw: 'Tav',
  keter: 'Kether', chochmah: 'Chokmah', hokmah: 'Chokmah', chokma: 'Chokmah',
  hesed: 'Chesed', gevurah: 'Geburah', tiphereth: 'Tiphareth',
  tiferet: 'Tiphareth', tifereth: 'Tiphareth', netsach: 'Netzach',
  malchut: 'Malkuth', malkut: 'Malkuth',
  muladhara: 'Root', svadhisthana: 'Sacral', manipura: 'Solar Plexus',
  anahata: 'Heart', vishuddha: 'Throat', visuddha: 'Throat',
  ajna: 'Third Eye', sahasrara: 'Crown',
};

export const normEntity = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toLowerCase();

/** Resolve a model-emitted entry name against a kind's roster. */
export function resolveEntityName(raw: string, roster: string[]): string {
  const n = normEntity(raw);
  const direct = roster.find(e => normEntity(e) === n);
  if (direct) return direct;
  const alias = ENTITY_ALIASES[n];
  if (alias && roster.includes(alias)) return alias;
  // 'Nine of Hearts'-style or 'the Kings' → try the leading word
  const first = normEntity(raw.split(/ of |,/)[0]).replace(/^the /, '').replace(/s$/, '');
  return roster.find(e => normEntity(e) === first || normEntity(e) === `${first}s`) ?? '';
}

/** Plain text from the model → simple HTML for the rich-text viewer. */
export function entityTextToHtml(text: string): string {
  const esc = (s: string) => s
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  return text
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => `<p>${esc(p).replaceAll('\n', '<br>')}</p>`)
    .join('');
}

/**
 * Rosters for a set of kinds, fetching the dynamic ones. deckType
 * scopes the suit/rank rosters (null = the type's default resolution
 * server-side). Also exposes the suited-type list for pickers.
 */
export function useEntityRosters(
  kinds: EntityKind[],
  deckType: string | null,
  enabled: boolean,
): {
  rosters: Map<EntityKind, string[]>;
  suitTypes: string[];
  resolvedDeckType: string | null;
} {
  const { data: suitData } = useQuery({
    queryKey: ['reference-suits', deckType],
    queryFn: () => getSuitsReference(deckType),
    enabled: enabled && (kinds.includes('suit') || kinds.includes('rank')),
  });
  const { data: rankData } = useQuery({
    queryKey: ['reference-ranks', deckType],
    queryFn: () => getRanksReference(deckType),
    enabled: enabled && kinds.includes('rank'),
  });
  const { data: numberData } = useQuery({
    queryKey: ['reference-numerology'],
    queryFn: getNumerologyReference,
    enabled: enabled && kinds.includes('number'),
  });

  const rosters = useMemo(() => {
    const map = new Map<EntityKind, string[]>();
    for (const kind of kinds) {
      if (kind === 'suit') map.set(kind, (suitData?.suits ?? []).map(s => s.name));
      else if (kind === 'rank') map.set(kind, (rankData?.ranks ?? []).map(r => r.rank));
      else if (kind === 'number') map.set(kind, (numberData?.entries ?? []).map(e => e.number));
      else map.set(kind, STATIC_ENTITIES[kind] ?? []);
    }
    return map;
  }, [kinds, suitData, rankData, numberData]);

  return {
    rosters,
    suitTypes: suitData?.types ?? rankData?.types ?? [],
    resolvedDeckType: suitData?.type ?? rankData?.type ?? deckType,
  };
}
