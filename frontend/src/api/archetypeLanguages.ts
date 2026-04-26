import api from './client';
import type { ArchetypeLanguage, ArchetypeLanguageName } from '../types';

// === Languages ===

export async function getArchetypeLanguages(): Promise<ArchetypeLanguage[]> {
  const res = await api.get('/api/archetype-languages');
  return res.data;
}

export async function createArchetypeLanguage(name: string): Promise<{ id: number }> {
  const res = await api.post('/api/archetype-languages', { name });
  return res.data;
}

export async function updateArchetypeLanguage(languageId: number, name: string) {
  await api.put(`/api/archetype-languages/${languageId}`, { name });
}

export async function deleteArchetypeLanguage(languageId: number) {
  await api.delete(`/api/archetype-languages/${languageId}`);
}

export async function getArchetypeLanguageDependencyCount(
  languageId: number,
): Promise<{ count: number }> {
  const res = await api.get(`/api/archetype-languages/${languageId}/dependency-count`);
  return res.data;
}

export async function reorderArchetypeLanguages(orderedIds: number[]) {
  await api.post('/api/archetype-languages/reorder', { ordered_ids: orderedIds });
}

// === Names ===

export async function getArchetypeNames(
  archetypeId: number,
): Promise<ArchetypeLanguageName[]> {
  const res = await api.get('/api/archetype-language-names', {
    params: { archetype_id: archetypeId },
  });
  return res.data;
}

export async function getArchetypeNamesForType(
  cartomancyType: string,
): Promise<ArchetypeLanguageName[]> {
  const res = await api.get('/api/archetype-language-names', {
    params: { cartomancy_type: cartomancyType },
  });
  return res.data;
}

export async function createArchetypeName(
  archetypeId: number,
  languageId: number,
  name: string,
  romanization?: string | null,
  ipa?: string | null,
): Promise<{ id: number }> {
  const res = await api.post('/api/archetype-language-names', {
    archetype_id: archetypeId,
    language_id: languageId,
    name,
    romanization: romanization ?? null,
    ipa: ipa ?? null,
  });
  return res.data;
}

export async function updateArchetypeName(
  nameId: number,
  patch: { name?: string; romanization?: string | null; ipa?: string | null },
) {
  await api.put(`/api/archetype-language-names/${nameId}`, patch);
}

export async function deleteArchetypeName(nameId: number) {
  await api.delete(`/api/archetype-language-names/${nameId}`);
}

export async function reorderArchetypeNames(
  archetypeId: number,
  languageId: number,
  orderedIds: number[],
) {
  await api.post('/api/archetype-language-names/reorder', {
    archetype_id: archetypeId,
    language_id: languageId,
    ordered_ids: orderedIds,
  });
}
