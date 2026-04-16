import api from './client';
import type { CorrespondenceSystem, CorrespondenceAssignment, ResolvedCorrespondence } from '../types';

// === Correspondence Systems ===

export async function getCorrespondenceSystems(): Promise<CorrespondenceSystem[]> {
  const res = await api.get('/api/correspondence-systems');
  return res.data;
}

export async function getCorrespondenceSystem(systemId: number): Promise<CorrespondenceSystem & { assignments: CorrespondenceAssignment[] }> {
  const res = await api.get(`/api/correspondence-systems/${systemId}`);
  return res.data;
}

export async function createCorrespondenceSystem(data: { name: string; description?: string }): Promise<{ id: number }> {
  const res = await api.post('/api/correspondence-systems', data);
  return res.data;
}

export async function updateCorrespondenceSystem(systemId: number, data: { name?: string; description?: string }) {
  await api.put(`/api/correspondence-systems/${systemId}`, data);
}

export async function deleteCorrespondenceSystem(systemId: number) {
  await api.delete(`/api/correspondence-systems/${systemId}`);
}

export async function cloneCorrespondenceSystem(systemId: number, name: string): Promise<{ id: number }> {
  const res = await api.post(`/api/correspondence-systems/${systemId}/clone`, { name });
  return res.data;
}

// === System Assignments ===

export async function getSystemAssignments(
  systemId: number,
  archetypeId?: number,
): Promise<CorrespondenceAssignment[]> {
  const params = archetypeId ? { archetype_id: archetypeId } : {};
  const res = await api.get(`/api/correspondence-systems/${systemId}/assignments`, { params });
  return res.data;
}

export async function bulkSetAssignments(
  systemId: number,
  assignments: { archetype_id: number; field_name: string; field_value: string }[],
) {
  await api.put(`/api/correspondence-systems/${systemId}/assignments`, { assignments });
}

export async function setAssignment(
  systemId: number,
  archetypeId: number,
  fieldName: string,
  value: string,
) {
  await api.put(`/api/correspondence-systems/${systemId}/assignments/${archetypeId}/${fieldName}`, { value });
}

export async function deleteAssignment(systemId: number, archetypeId: number, fieldName: string) {
  await api.delete(`/api/correspondence-systems/${systemId}/assignments/${archetypeId}/${fieldName}`);
}

// === Card-Level Overrides ===

export async function getCardCorrespondences(cardId: number): Promise<ResolvedCorrespondence[]> {
  const res = await api.get(`/api/cards/${cardId}/correspondences`);
  return res.data;
}

export async function setCardOverrides(
  cardId: number,
  overrides: { field_name: string; field_value: string | null }[],
) {
  await api.put(`/api/cards/${cardId}/correspondences`, { overrides });
}

export async function deleteCardOverride(cardId: number, fieldName: string) {
  await api.delete(`/api/cards/${cardId}/correspondences/${fieldName}`);
}

// === Cross-System Queries ===

export async function getCorrespondencesByArchetype(archetypeId: number): Promise<CorrespondenceAssignment[]> {
  const res = await api.get(`/api/correspondences/by-archetype/${archetypeId}`);
  return res.data;
}

export async function compareCorrespondenceSystems(systemIds: number[]): Promise<CorrespondenceAssignment[]> {
  const res = await api.get('/api/correspondences/compare', {
    params: { systems: systemIds.join(',') },
  });
  return res.data;
}

// === Card Names (for Reference tab) ===

export interface CardNameEntry {
  field_name: string;
  field_value: string;
  archetype: string | null;
  card_name: string;
  deck_name: string;
}

export async function getCardNames(): Promise<CardNameEntry[]> {
  const res = await api.get('/api/card-names');
  return res.data;
}
