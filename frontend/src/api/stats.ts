import api from './client';

export interface AppStats {
  total_entries: number;
  total_decks: number;
  total_cards: number;
  total_spreads: number;
  top_decks: Array<[string, number]>;
  top_spreads: Array<[string, number]>;
}

export async function getStats(): Promise<AppStats> {
  const res = await api.get('/api/stats');
  return res.data;
}
