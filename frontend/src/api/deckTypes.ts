import api from './client';

// === Deck Types manager (custom cartomancy types + archetypes) ===

export async function addCartomancyType(name: string): Promise<{ id: number }> {
  const res = await api.post('/api/types', { name });
  return res.data;
}

export async function renameCartomancyType(typeId: number, name: string): Promise<void> {
  await api.put(`/api/types/${typeId}`, { name });
}

export async function deleteCartomancyType(typeId: number): Promise<void> {
  await api.delete(`/api/types/${typeId}`);
}

export async function addArchetype(input: {
  cartomancy_type: string;
  name: string;
  rank?: string;
  suit?: string;
}): Promise<{ id: number }> {
  const res = await api.post('/api/archetypes', input);
  return res.data;
}

export async function bulkAddArchetypes(
  cartomancyType: string,
  rows: { name: string; rank?: string; suit?: string }[],
): Promise<{ created: number; skipped: number }> {
  const res = await api.post('/api/archetypes/bulk', {
    cartomancy_type: cartomancyType,
    rows,
  });
  return res.data;
}

export async function seedArchetypesFromDeck(
  deckId: number,
  cartomancyType: string,
): Promise<{ created: number }> {
  const res = await api.post('/api/archetypes/seed-from-deck', {
    deck_id: deckId,
    cartomancy_type: cartomancyType,
  });
  return res.data;
}

export async function updateArchetype(
  archetypeId: number,
  changes: { name?: string; rank?: string; suit?: string },
): Promise<void> {
  await api.put(`/api/archetypes/${archetypeId}`, changes);
}

export async function deleteArchetype(archetypeId: number): Promise<void> {
  await api.delete(`/api/archetypes/${archetypeId}`);
}
