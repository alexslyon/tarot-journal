import api from './client';
import { API_BASE } from './client';

export async function getImportPresets(): Promise<string[]> {
  const res = await api.get('/api/import/presets');
  return res.data;
}

export async function scanFolder(folder: string, presetName: string): Promise<{
  cards: Array<{ filename: string; name: string; sort_order: number }>;
  card_back: string | null;
  count: number;
}> {
  const res = await api.post('/api/import/scan-folder', { folder, preset_name: presetName });
  return res.data;
}

export async function importFromFolder(data: {
  folder: string;
  deck_name: string;
  cartomancy_type_id: number;
  preset_name: string;
}): Promise<{ deck_id: number; cards_imported: number }> {
  const res = await api.post('/api/import/from-folder', data);
  return res.data;
}

export function exportDeckUrl(deckId: number): string {
  return `${API_BASE}/api/export/deck/${deckId}`;
}

export async function importDeckJson(data: unknown): Promise<{
  deck_id: number;
  deck_name: string;
  cards_imported: number;
}> {
  const res = await api.post('/api/import/deck-json', data);
  return res.data;
}
