import api from './client';
import type { CombinationMeaning, PopulatedCombination } from '../types';

// Sources are managed via the shared `referenceSources` API — see
// frontend/src/api/referenceSources.ts.

// === Meanings ===

export async function getCombinationMeanings(
  cartomancyType: string,
  card1: number,
  card2: number,
  card1Reversed = false,
  card2Reversed = false,
  card3: number | null = null,
  card3Reversed = false,
): Promise<CombinationMeaning[]> {
  const res = await api.get('/api/combinations/meanings', {
    params: {
      cartomancy_type: cartomancyType,
      card_1: card1,
      card_2: card2,
      ...(card1Reversed ? { card_1_reversed: '1' } : {}),
      ...(card2Reversed ? { card_2_reversed: '1' } : {}),
      ...(card3 ? { card_3: card3 } : {}),
      ...(card3 && card3Reversed ? { card_3_reversed: '1' } : {}),
    },
  });
  return res.data;
}

/** Cartomancy types whose combinations may involve reversed cards. */
export async function getReversedCombinationTypes(): Promise<string[]> {
  const res = await api.get('/api/combinations/reversed-types');
  return res.data.types;
}

export async function setReversedCombinationTypes(types: string[]): Promise<void> {
  await api.put('/api/combinations/reversed-types', { types });
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
  card1Reversed = false,
  card2Reversed = false,
  card3: number | null = null,
  card3Reversed = false,
): Promise<{ id: number }> {
  const res = await api.post('/api/combinations/meanings', {
    cartomancy_type: cartomancyType,
    card_1: card1,
    card_2: card2,
    meaning,
    source_id: sourceId,
    card_1_reversed: card1Reversed,
    card_2_reversed: card2Reversed,
    card_3: card3,
    card_3_reversed: card3Reversed,
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
