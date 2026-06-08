import api from './client';
import type { CombinationMeaning, PopulatedCombination } from '../types';

// Sources are managed via the shared `referenceSources` API — see
// frontend/src/api/referenceSources.ts.

// === Meanings ===

export async function getCombinationMeanings(
  cartomancyType: string,
  card1: number,
  card2: number,
): Promise<CombinationMeaning[]> {
  const res = await api.get('/api/combinations/meanings', {
    params: { cartomancy_type: cartomancyType, card_1: card1, card_2: card2 },
  });
  return res.data;
}

/** Combinations of a type that have at least one meaning authored. */
export async function getPopulatedCombinations(
  cartomancyType: string,
): Promise<PopulatedCombination[]> {
  const res = await api.get('/api/combinations/populated', {
    params: { cartomancy_type: cartomancyType },
  });
  return res.data;
}

export async function createCombinationMeaning(
  cartomancyType: string,
  card1: number,
  card2: number,
  meaning: string,
  sourceId: number | null = null,
): Promise<{ id: number }> {
  const res = await api.post('/api/combinations/meanings', {
    cartomancy_type: cartomancyType,
    card_1: card1,
    card_2: card2,
    meaning,
    source_id: sourceId,
  });
  return res.data;
}

export async function updateCombinationMeaning(
  meaningId: number,
  patch: { meaning?: string; source_id?: number | null },
) {
  await api.put(`/api/combinations/meanings/${meaningId}`, patch);
}

export async function deleteCombinationMeaning(meaningId: number) {
  await api.delete(`/api/combinations/meanings/${meaningId}`);
}

export async function reorderCombinationMeanings(
  combinationId: number,
  orderedIds: number[],
) {
  await api.post('/api/combinations/meanings/reorder', {
    combination_id: combinationId,
    ordered_ids: orderedIds,
  });
}
