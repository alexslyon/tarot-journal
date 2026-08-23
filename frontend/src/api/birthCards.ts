import api from './client';

// === Birth cards (Greer "Lifetime Cards") ===

export type BirthCardMethod = 'greer' | 'amberstone';
export type EightEleven = 'golden_dawn' | 'marseille';

/** A Major Arcana reference, hydrated by the backend. */
export interface MajorCardRef {
  /** 1–22; The Fool is 22 internally (displayed as 0 by convention). */
  number: number;
  name: string;
  archetype_id: number | null;
  /** Matching card in the default Tarot deck, for the image. */
  card_id: number | null;
}

/** A Minor Arcana reference (decan / lessons cards). */
export interface MinorCardRef {
  rank: number;
  suit: string;
  name: string;
  archetype_id: number | null;
  card_id: number | null;
}

export interface BirthCardProfile {
  method: BirthCardMethod;
  base_number: number;
  personality: number;
  soul: number;
  teacher: number | null;
  hidden_factor: number[];
  pattern: string;
  nighttime: boolean;
  fool_center: boolean;
  constellation: { root: number; majors: number[] };
  dynamic: 1 | 2 | 3 | null;
  /** Golden Dawn decan attributions for the zodiacal card. */
  zodiacal_rulers: {
    sign: string;
    planet: string;
    sign_major: number;
    planet_major: number;
  };
  karmic_year: number;
  year_card: number;
  generic_year: number;
  personal_month: number;
  birth_date: string;
  age: number;
  eight_eleven: EightEleven;
  reference_year: number;
  reference_month: number;
  cards: {
    personality: MajorCardRef;
    soul: MajorCardRef;
    teacher: MajorCardRef | null;
    hidden_factor: MajorCardRef[];
    constellation_majors: MajorCardRef[];
    lessons_and_opportunities: MinorCardRef[];
    zodiacal: MinorCardRef;
    zodiacal_sign_ruler: MajorCardRef;
    zodiacal_planet_ruler: MajorCardRef;
    year_card: MajorCardRef;
    generic_year: MajorCardRef;
    personal_month: MajorCardRef;
  };
}

export interface BirthCardPrefs {
  method: BirthCardMethod;
  eight_eleven: EightEleven;
}

export async function getProfileBirthCards(
  profileId: number,
  opts?: { method?: BirthCardMethod; eightEleven?: EightEleven },
): Promise<BirthCardProfile> {
  const params = new URLSearchParams();
  if (opts?.method) params.set('method', opts.method);
  if (opts?.eightEleven) params.set('eight_eleven', opts.eightEleven);
  const qs = params.toString();
  const res = await api.get(`/api/profiles/${profileId}/birth-cards${qs ? `?${qs}` : ''}`);
  return res.data;
}

export async function getBirthCardsForDate(
  date: string,
  opts?: { method?: BirthCardMethod; eightEleven?: EightEleven },
): Promise<BirthCardProfile> {
  const params = new URLSearchParams({ date });
  if (opts?.method) params.set('method', opts.method);
  if (opts?.eightEleven) params.set('eight_eleven', opts.eightEleven);
  const res = await api.get(`/api/birth-cards?${params.toString()}`);
  return res.data;
}

export async function getBirthCardPrefs(): Promise<BirthCardPrefs> {
  const res = await api.get('/api/birth-cards/prefs');
  return res.data;
}

export async function setBirthCardPrefs(
  prefs: Partial<BirthCardPrefs>,
): Promise<BirthCardPrefs> {
  const res = await api.put('/api/birth-cards/prefs', prefs);
  return res.data;
}
