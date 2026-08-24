import api from './client';
import type { MajorCardRef } from './birthCards';

// === Name cards (Greer, Archetypal Tarot Ch. 17) ===

export type YMode = 'heuristic' | 'always_vowel' | 'always_consonant';
export type NameRole = 'first' | 'middle' | 'last';

export interface YOverride {
  /** Index into the parts array. */
  part: number;
  /** Letter index within the NORMALIZED part. */
  index: number;
  as: 'vowel' | 'consonant';
}

/** The user's saved adjustments, stored per profile. */
export interface NameCardsConfig {
  parts?: string[];
  roles?: NameRole[] | null;
  y_mode?: YMode;
  y_overrides?: YOverride[];
  drop_suffixes?: boolean;
}

export interface NameLetter {
  letter: string;
  key: number;
  is_vowel: boolean;
  note: string;
}

export interface NamePartResult {
  original: string;
  normalized: string;
  input_index: number;
  role: NameRole;
  letters: NameLetter[];
  vowel_sum: number;
  consonant_sum: number;
  sum: number;
}

export interface NameCardsResult {
  parts: NamePartResult[];
  normalized: boolean;
  dropped_suffixes: string[];
  y_mode: YMode;
  y_positions: {
    part: number;
    index: number;
    classified_as: 'vowel' | 'consonant';
    overridden: boolean;
  }[];

  first_name_card: number | null;
  middle_name_card: number | null;
  last_name_card: number | null;
  theme_chord: (number | null)[];

  all_vowels: number;
  all_consonants: number;
  all_letters: number;
  desires_inner_motivation: number | null;
  outer_persona: number | null;
  theme_note: number;
  rhythm: number;
  melody: number;
  shared_root: number;
  hidden_factor_name: number[];

  constellation_count: Record<string, number>;
  most_represented: number[];
  absent: number[];

  mandala: (NameLetter & { part: number })[];
  max_letter_frequency: number;
  leading_letter: { letter: string; key: number; is_vowel: boolean };
  first_vowel: { letter: string; key: number } | null;
  rhythm_pattern: string[];

  life_potential: number | null;
  eight_eleven: string;
  cards: {
    first_name: MajorCardRef | null;
    middle_name: MajorCardRef | null;
    last_name: MajorCardRef | null;
    desires_inner_motivation: MajorCardRef | null;
    outer_persona: MajorCardRef | null;
    theme_note: MajorCardRef;
    rhythm: MajorCardRef;
    melody: MajorCardRef;
    hidden_factor_name: MajorCardRef[];
    life_potential: MajorCardRef | null;
  };
  majors_by_number: Record<string, MajorCardRef>;
}

export async function calculateNameCards(input: {
  parts: string[];
  roles?: NameRole[] | null;
  y_mode?: YMode;
  y_overrides?: YOverride[];
  drop_suffixes?: boolean;
  profile_id?: number;
}): Promise<NameCardsResult> {
  const res = await api.post('/api/name-cards/calculate', input);
  return res.data;
}

// === Alternate names (chosen names, nicknames) ===

export type NameKind = 'birth' | 'chosen' | 'nickname' | 'other';

export interface ProfileName {
  id: number;
  profile_id: number;
  name_kind: NameKind;
  display_name: string;
  parts: string[] | null;
  roles: NameRole[] | null;
  y_mode: YMode;
  y_overrides: YOverride[];
  drop_suffixes: boolean;
}

export async function getProfileNames(profileId: number): Promise<ProfileName[]> {
  const res = await api.get(`/api/profiles/${profileId}/names`);
  return res.data;
}

export async function addProfileName(
  profileId: number,
  input: { display_name: string; name_kind: NameKind },
): Promise<{ id: number }> {
  const res = await api.post(`/api/profiles/${profileId}/names`, input);
  return res.data;
}

export async function updateProfileName(
  nameId: number,
  changes: Partial<{
    display_name: string;
    name_kind: NameKind;
    parts: string[];
    roles: NameRole[] | null;
    y_mode: YMode;
    y_overrides: YOverride[];
    drop_suffixes: boolean;
  }>,
): Promise<void> {
  await api.put(`/api/profile-names/${nameId}`, changes);
}

export async function deleteProfileName(nameId: number): Promise<void> {
  await api.delete(`/api/profile-names/${nameId}`);
}

export async function getNameCardsConfig(profileId: number): Promise<{
  full_name: string | null;
  config: NameCardsConfig | null;
}> {
  const res = await api.get(`/api/profiles/${profileId}/name-cards-config`);
  return res.data;
}

export async function setNameCardsConfig(
  profileId: number,
  config: NameCardsConfig | null,
): Promise<void> {
  await api.put(`/api/profiles/${profileId}/name-cards-config`, { config });
}
