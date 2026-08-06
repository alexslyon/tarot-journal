import api from './client';

// ── The Scribe: import book content into reference data ──────

export interface ExtractedText {
  filename: string;
  text: string;
  char_count: number;
  warning: string | null;
}

/** Extract plain text from an ebook / text file (EPUB, PDF, MOBI…).
 *  Images don't go through this — they're read in the browser. */
export async function extractSourceText(file: File): Promise<ExtractedText> {
  const form = new FormData();
  form.append('file', file);
  const res = await api.post('/api/scribe/extract-text', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  });
  return res.data;
}

/** Decode an image the browser can't (HEIC from iPhones, mainly) —
 *  the backend converts it to a downscaled base64 JPEG. */
export async function convertSourceImage(file: File): Promise<{
  data: string;
  media_type: string;
  filename: string;
}> {
  const form = new FormData();
  form.append('file', file);
  const res = await api.post('/api/scribe/convert-image', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  });
  return res.data;
}

export type ScribeWrite =
  | { target: 'archetype'; archetype_id: number; field_id: number; content: string }
  | { target: 'card'; card_id: number; field_name: string; content: string };

export async function applyScribeWrites(writes: ScribeWrite[]): Promise<{
  applied: number;
  errors: { index: number; error: string }[];
}> {
  const res = await api.post('/api/scribe/apply', { writes });
  return res.data;
}
