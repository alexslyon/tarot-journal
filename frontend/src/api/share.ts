import api from './client';

// === Spreads & profiles share export/import ===

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function stamp(): string {
  return new Date().toISOString().slice(0, 10);
}

export async function downloadSpreadsExport(ids?: number[]): Promise<void> {
  const qs = ids?.length ? `?ids=${ids.join(',')}` : '';
  const res = await api.get(`/api/spreads/export${qs}`);
  downloadJson(`spreads_${stamp()}.json`, res.data);
}

export interface SpreadImportResult {
  imported: number;
  skipped: string[];
  tags_created: number;
}

export async function importSpreads(data: unknown): Promise<SpreadImportResult> {
  const res = await api.post('/api/spreads/import', { data });
  return res.data;
}

export async function downloadProfilesExport(ids?: number[]): Promise<void> {
  const qs = ids?.length ? `?ids=${ids.join(',')}` : '';
  const res = await api.get(`/api/profiles/export${qs}`);
  downloadJson(`profiles_${stamp()}.json`, res.data);
}

export interface ProfileImportResult {
  imported: number;
  skipped: string[];
}

export async function importProfiles(data: unknown): Promise<ProfileImportResult> {
  const res = await api.post('/api/profiles/import', { data });
  return res.data;
}
