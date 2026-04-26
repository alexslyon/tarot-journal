import api from './client';
import type { ArchetypeNoteField, ArchetypeNoteEntry } from '../types';

// === Field definitions ===

export async function getArchetypeNoteFields(
  archetypeId: number,
): Promise<ArchetypeNoteField[]> {
  const res = await api.get('/api/archetype-notes/fields', {
    params: { archetype_id: archetypeId },
  });
  return res.data;
}

export async function createArchetypeNoteField(
  archetypeId: number,
  fieldName: string,
): Promise<{ id: number }> {
  const res = await api.post('/api/archetype-notes/fields', {
    archetype_id: archetypeId,
    field_name: fieldName,
  });
  return res.data;
}

export async function updateArchetypeNoteField(
  fieldId: number,
  fieldName: string,
) {
  await api.put(`/api/archetype-notes/fields/${fieldId}`, { field_name: fieldName });
}

export async function deleteArchetypeNoteField(fieldId: number) {
  await api.delete(`/api/archetype-notes/fields/${fieldId}`);
}

export async function getArchetypeNoteFieldEntryCount(
  fieldId: number,
): Promise<{ count: number }> {
  const res = await api.get(`/api/archetype-notes/fields/${fieldId}/entry-count`);
  return res.data;
}

export async function reorderArchetypeNoteFields(
  archetypeId: number,
  orderedIds: number[],
) {
  await api.post('/api/archetype-notes/fields/reorder', {
    archetype_id: archetypeId,
    ordered_ids: orderedIds,
  });
}

// === Entries ===

export async function getArchetypeNoteEntries(
  fieldId: number,
): Promise<ArchetypeNoteEntry[]> {
  const res = await api.get('/api/archetype-notes/entries', {
    params: { field_id: fieldId },
  });
  return res.data;
}

export async function getArchetypeNotes(
  archetypeId: number,
): Promise<ArchetypeNoteEntry[]> {
  const res = await api.get('/api/archetype-notes/entries', {
    params: { archetype_id: archetypeId },
  });
  return res.data;
}

export async function createArchetypeNoteEntry(
  fieldId: number,
  content: string,
  sourceId: number | null = null,
): Promise<{ id: number }> {
  const res = await api.post('/api/archetype-notes/entries', {
    field_id: fieldId,
    content,
    source_id: sourceId,
  });
  return res.data;
}

export async function updateArchetypeNoteEntry(
  entryId: number,
  patch: { content?: string; source_id?: number | null },
) {
  await api.put(`/api/archetype-notes/entries/${entryId}`, patch);
}

export async function deleteArchetypeNoteEntry(entryId: number) {
  await api.delete(`/api/archetype-notes/entries/${entryId}`);
}

export async function reorderArchetypeNoteEntries(
  fieldId: number,
  orderedIds: number[],
) {
  await api.post('/api/archetype-notes/entries/reorder', {
    field_id: fieldId,
    ordered_ids: orderedIds,
  });
}
