import api from './client';
import type { LenormandMeaning } from '../types';

// Sources are managed via the shared `referenceSources` API — see
// frontend/src/api/referenceSources.ts.

// === Meanings ===

export async function getLenormandMeanings(
  card1: number,
  card2: number,
): Promise<LenormandMeaning[]> {
  const res = await api.get('/api/lenormand/meanings', {
    params: { card_1: card1, card_2: card2 },
  });
  return res.data;
}

export async function createLenormandMeaning(
  card1: number,
  card2: number,
  meaning: string,
  sourceId: number | null = null,
): Promise<{ id: number }> {
  const res = await api.post('/api/lenormand/meanings', {
    card_1: card1,
    card_2: card2,
    meaning,
    source_id: sourceId,
  });
  return res.data;
}

export async function updateLenormandMeaning(
  meaningId: number,
  patch: { meaning?: string; source_id?: number | null },
) {
  await api.put(`/api/lenormand/meanings/${meaningId}`, patch);
}

export async function deleteLenormandMeaning(meaningId: number) {
  await api.delete(`/api/lenormand/meanings/${meaningId}`);
}

export async function reorderLenormandMeanings(
  combinationId: number,
  orderedIds: number[],
) {
  await api.post('/api/lenormand/meanings/reorder', {
    combination_id: combinationId,
    ordered_ids: orderedIds,
  });
}
