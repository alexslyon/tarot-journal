import api from './client';
import type { CourtSystem, EightEleven, MajorCardRef, MinorCardRef } from './birthCards';

// === Reference-section content (astrology / kabbalah / numerology / chakras) ===

/** An archetype the chosen correspondence system assigns to an entity. */
export interface AssignedRef {
  archetype_id: number;
  name: string;
  cartomancy_type: string;
}

/** Any card hydrated by name (courts, arbitrary lookups). */
export interface NamedCardRef {
  name: string;
  archetype_id: number | null;
  card_id: number | null;
}

export interface DecanRef {
  index: 1 | 2 | 3;
  dates: string;
  planet: string;
  minor: MinorCardRef;
  planet_trump: MajorCardRef;
}

export interface CourtArcRef extends NamedCardRef {
  rank: string;
  suit: string;
  court_sign: string;
  span: string;
}

export interface SignRef {
  name: string;
  glyph: string;
  element: string;
  modality: string;
  ruler: string;
  modern_ruler?: string;
  themes: string;
  dates: string;
  trump: MajorCardRef;
  decans: DecanRef[];
  courts: Record<CourtSystem, CourtArcRef[]>;
  assigned: AssignedRef[];
}

export interface PlanetRef {
  name: string;
  glyph: string;
  classical: boolean;
  rules: string[];
  themes: string;
  trump: MajorCardRef | null;
  modern_attribution: boolean;
  decans_ruled: { sign: string; minor: MinorCardRef }[];
  assigned: AssignedRef[];
}

export interface AstrologyData {
  eight_eleven: EightEleven;
  court_system: CourtSystem;
  signs: SignRef[];
  planets: PlanetRef[];
  /** Which decan today's date falls in (the wheel's marker). */
  today_decan: { sign: string; index: 1 | 2 | 3 };
}

export interface SephiraRef {
  number: number;
  name: string;
  hebrew: string;
  translation: string;
  pillar: 'middle' | 'mercy' | 'severity';
  planet: string;
  x: number;
  y: number;
  meaning: string;
  minors: MinorCardRef[];
  /** Tetragrammaton courts, present only on sephiroth 2 / 3 / 6 / 10;
   *  rank names follow the saved Courts preference. */
  court_rank?: string;
  courts?: (NamedCardRef & { rank: string; suit: string })[];
  /** The tree's own system's cards for this sephira, when it assigns
   *  them — these replace the rank-derived minors and courts. */
  cards?: NamedCardRef[];
}

export interface TreePathRef {
  path: number;
  from: number;
  to: number;
  letter: string;
  glyph: string;
  value: number;
  /** Canonical GD trump — the fallback when the tree's system doesn't
   *  assign this letter. */
  trump: MajorCardRef;
  /** The tree's correspondence system's cards for this letter
   *  (hebrew_letter assignments), images from the tree's deck. */
  letter_cards: NamedCardRef[];
}

export interface KabbalahData {
  sephiroth: SephiraRef[];
  paths: TreePathRef[];
  court_system: CourtSystem;
}

/** A configured Tree of Life tab: correspondence system + image deck. */
export interface KabbalahTreeConfig {
  label: string;
  system_id: number;
  deck_id: number;
}

export async function getKabbalahTrees(): Promise<{ trees: KabbalahTreeConfig[] }> {
  const res = await api.get('/api/reference/kabbalah/trees');
  return res.data;
}

export async function setKabbalahTrees(
  trees: KabbalahTreeConfig[],
): Promise<{ trees: KabbalahTreeConfig[] }> {
  const res = await api.put('/api/reference/kabbalah/trees', { trees });
  return res.data;
}

export interface NumberEntry {
  number: string;
  system: string | null;
  title: string;
  meaning: string;
  tarot_connection: string;
  majors?: MajorCardRef[];
  minors?: MinorCardRef[];
  assigned: AssignedRef[];
}

export interface ChakraRef {
  name: string;
  sanskrit: string;
  color: string;
  location: string;
  themes: string;
  assigned: AssignedRef[];
}

function qs(systemId?: number | null): string {
  return systemId ? `?system_id=${systemId}` : '';
}

export async function getAstrologyReference(systemId?: number | null): Promise<AstrologyData> {
  const res = await api.get(`/api/reference/astrology${qs(systemId)}`);
  return res.data;
}

export async function getKabbalahReference(
  systemId?: number | null,
  deckId?: number | null,
): Promise<KabbalahData> {
  const params = new URLSearchParams();
  if (systemId) params.set('system_id', String(systemId));
  if (deckId) params.set('deck_id', String(deckId));
  const q = params.toString();
  const res = await api.get(`/api/reference/kabbalah${q ? `?${q}` : ''}`);
  return res.data;
}

export async function getNumerologyReference(
  systemId?: number | null,
): Promise<{ entries: NumberEntry[] }> {
  const res = await api.get(`/api/reference/numerology${qs(systemId)}`);
  return res.data;
}

export async function getChakrasReference(
  systemId?: number | null,
): Promise<{ chakras: ChakraRef[] }> {
  const res = await api.get(`/api/reference/chakras${qs(systemId)}`);
  return res.data;
}
