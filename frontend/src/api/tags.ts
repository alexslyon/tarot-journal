import api from './client';
import type { Tag } from '../types';

// ── Entry Tags ──────────────────────────────────────────────

export async function getEntryTags(): Promise<Tag[]> {
  const res = await api.get('/api/entry-tags');
  return res.data;
}

export async function addEntryTag(data: { name: string; color?: string }): Promise<{ id: number }> {
  const res = await api.post('/api/entry-tags', data);
  return res.data;
}

export async function updateEntryTag(tagId: number, data: { name?: string; color?: string }): Promise<void> {
  await api.put(`/api/entry-tags/${tagId}`, data);
}

export async function deleteEntryTag(tagId: number): Promise<void> {
  await api.delete(`/api/entry-tags/${tagId}`);
}

// ── Deck Tags ───────────────────────────────────────────────

export async function getDeckTags(): Promise<Tag[]> {
  const res = await api.get('/api/deck-tags');
  return res.data;
}

export async function addDeckTag(data: { name: string; color?: string }): Promise<{ id: number }> {
  const res = await api.post('/api/deck-tags', data);
  return res.data;
}

export async function updateDeckTag(tagId: number, data: { name?: string; color?: string }): Promise<void> {
  await api.put(`/api/deck-tags/${tagId}`, data);
}

export async function deleteDeckTag(tagId: number): Promise<void> {
  await api.delete(`/api/deck-tags/${tagId}`);
}

// ── Card Tags ───────────────────────────────────────────────

export async function getCardTags(): Promise<Tag[]> {
  const res = await api.get('/api/card-tags');
  return res.data;
}

export async function addCardTag(data: { name: string; color?: string }): Promise<{ id: number }> {
  const res = await api.post('/api/card-tags', data);
  return res.data;
}

export async function updateCardTag(tagId: number, data: { name?: string; color?: string }): Promise<void> {
  await api.put(`/api/card-tags/${tagId}`, data);
}

export async function deleteCardTag(tagId: number): Promise<void> {
  await api.delete(`/api/card-tags/${tagId}`);
}
