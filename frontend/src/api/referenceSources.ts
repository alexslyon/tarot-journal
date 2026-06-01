import api from './client';
import type { ReferenceSource, ArchetypeSourceEntry, SourceAuthoringEntry } from '../types';

/** List sources, optionally scoped to a cartomancy type. */
export async function getReferenceSources(cartomancyType?: string): Promise<ReferenceSource[]> {
  const params = cartomancyType ? { cartomancy_type: cartomancyType } : {};
  const res = await api.get('/api/reference/sources', { params });
  return res.data;
}

export async function getReferenceSource(sourceId: number): Promise<ReferenceSource> {
  const res = await api.get(`/api/reference/sources/${sourceId}`);
  return res.data;
}

export async function createReferenceSource(data: {
  name: string;
  cartomancy_type: string;
  authors?: string[];
}): Promise<{ id: number }> {
  const res = await api.post('/api/reference/sources', data);
  return res.data;
}

/** Partial update — pass only the keys you want to change. */
export async function updateReferenceSource(
  sourceId: number,
  data: { name?: string; cartomancy_type?: string; authors?: string[] },
): Promise<void> {
  await api.put(`/api/reference/sources/${sourceId}`, data);
}

export async function deleteReferenceSource(
  sourceId: number,
  reassignTo?: number,
): Promise<void> {
  const params = new URLSearchParams();
  if (reassignTo != null) params.set('reassign_to', String(reassignTo));
  const qs = params.toString() ? `?${params}` : '';
  await api.delete(`/api/reference/sources/${sourceId}${qs}`);
}

export async function getReferenceSourceDependencies(
  sourceId: number,
): Promise<{ lenormand_meanings: number; archetype_source_entries: number }> {
  const res = await api.get(`/api/reference/sources/${sourceId}/dependencies`);
  return res.data;
}

// === Per-archetype source entries ===

/** All non-empty source entries for a given archetype, optionally
 *  scoped to a cartomancy type. */
export async function getArchetypeSourceEntries(
  archetypeId: number,
  cartomancyType?: string,
): Promise<ArchetypeSourceEntry[]> {
  const params = cartomancyType ? { cartomancy_type: cartomancyType } : {};
  const res = await api.get(`/api/archetypes/${archetypeId}/source-entries`, { params });
  return res.data;
}

/** Every entry under a source. Used by the Settings authoring page
 *  where one source is being filled in across all its archetypes. */
export async function getSourceEntries(sourceId: number): Promise<SourceAuthoringEntry[]> {
  const res = await api.get(`/api/reference/sources/${sourceId}/entries`);
  return res.data;
}

/** Upsert content for an (archetype, source) pair. Blank/whitespace
 *  content deletes the row server-side. */
export async function setArchetypeSourceEntry(
  archetypeId: number,
  sourceId: number,
  content: string,
): Promise<void> {
  await api.put(
    `/api/archetypes/${archetypeId}/source-entries/${sourceId}`,
    { content },
  );
}

export async function deleteArchetypeSourceEntry(
  archetypeId: number,
  sourceId: number,
): Promise<void> {
  await api.delete(`/api/archetypes/${archetypeId}/source-entries/${sourceId}`);
}
