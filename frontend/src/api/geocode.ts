import api from './client';

export interface GeocodeMatch {
  name: string;
  admin1: string | null;
  country: string;
  latitude: number;
  longitude: number;
  population: number;
  timezone: string | null;
  display_name: string;
}

/** Look up places matching the query against the local GeoNames index.
 *  The first call may be slow (~5-30s) because the backend has to
 *  download the data files on demand. */
export async function geocode(q: string, limit = 10): Promise<GeocodeMatch[]> {
  if (q.trim().length < 2) return [];
  const res = await api.get('/api/geocode', { params: { q, limit } });
  return res.data?.results || [];
}
