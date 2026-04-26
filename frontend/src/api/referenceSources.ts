import api from './client';
import type { ReferenceSource } from '../types';

export async function getReferenceSources(): Promise<ReferenceSource[]> {
  const res = await api.get('/api/reference/sources');
  return res.data;
}

export async function createReferenceSource(name: string): Promise<{ id: number }> {
  const res = await api.post('/api/reference/sources', { name });
  return res.data;
}

export async function updateReferenceSource(sourceId: number, name: string) {
  await api.put(`/api/reference/sources/${sourceId}`, { name });
}

export async function deleteReferenceSource(
  sourceId: number,
  reassignTo?: number,
) {
  const params = new URLSearchParams();
  if (reassignTo != null) params.set('reassign_to', String(reassignTo));
  const qs = params.toString() ? `?${params}` : '';
  await api.delete(`/api/reference/sources/${sourceId}${qs}`);
}

export async function getReferenceSourceDependencies(
  sourceId: number,
): Promise<{ lenormand_meanings: number; archetype_notes_entries: number }> {
  const res = await api.get(`/api/reference/sources/${sourceId}/dependencies`);
  return res.data;
}
