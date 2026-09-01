/**
 * The role registry and color resolution for "Indicate Birth & Name
 * Cards": every kind of birth and name card has its own configurable
 * color (Settings → General), defaulting to gold for the birth system
 * and violet for the name system.
 */
import { useQuery } from '@tanstack/react-query';
import { getIndicationColors } from '../api/settings';

export const BIRTH_DEFAULT = '#d9a54a';
export const NAME_DEFAULT = '#9b7fd4';

export interface IndicationRole {
  key: string;
  label: string;
  system: 'birth' | 'name';
}

/** Every role a card can be flagged with, in display order. */
export const INDICATION_ROLES: IndicationRole[] = [
  { key: 'personality', label: 'Personality', system: 'birth' },
  { key: 'soul', label: 'Soul', system: 'birth' },
  { key: 'teacher', label: 'Teacher', system: 'birth' },
  { key: 'hidden_factor', label: 'Hidden Factor (Shadow / Teacher)', system: 'birth' },
  { key: 'lesson', label: 'Lessons & Opportunities', system: 'birth' },
  { key: 'zodiacal_lesson', label: 'Zodiacal Lesson', system: 'birth' },
  { key: 'zodiacal_ruler', label: 'Zodiacal Ruler', system: 'birth' },
  { key: 'planetary_ruler', label: 'Planetary Ruler', system: 'birth' },
  { key: 'court_ruler', label: 'Court Ruler', system: 'birth' },
  { key: 'year_card', label: 'Year Card', system: 'birth' },
  { key: 'first_name', label: 'First Name', system: 'name' },
  { key: 'middle_name', label: 'Middle Name', system: 'name' },
  { key: 'last_name', label: 'Last Name', system: 'name' },
  { key: 'desires_inner', label: 'Desires & Inner Motivation', system: 'name' },
  { key: 'outer_persona', label: 'Outer Persona', system: 'name' },
  { key: 'theme_note', label: 'Theme Note', system: 'name' },
  { key: 'rhythm', label: 'Rhythm', system: 'name' },
  { key: 'melody', label: 'Melody', system: 'name' },
  { key: 'hidden_factor_name', label: 'Hidden Factor (Name)', system: 'name' },
  { key: 'life_potential', label: 'Life Potential', system: 'name' },
];

export function defaultColorFor(roleKey: string): string {
  const role = INDICATION_ROLES.find(r => r.key === roleKey);
  return role?.system === 'name' ? NAME_DEFAULT : BIRTH_DEFAULT;
}

/** The saved palette merged over the defaults; colorFor never fails. */
export function useIndicationColors(enabled = true): {
  colorFor: (roleKey: string) => string;
  overrides: Record<string, string>;
  ready: boolean;
} {
  const { data, isSuccess, isError } = useQuery({
    queryKey: ['indication-colors'],
    queryFn: getIndicationColors,
    enabled,
    staleTime: 30_000,
  });
  const overrides = data?.colors ?? {};
  return {
    colorFor: (roleKey: string) => overrides[roleKey] ?? defaultColorFor(roleKey),
    overrides,
    ready: isSuccess || isError,
  };
}
