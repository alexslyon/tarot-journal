import api from './client';

/** Phase 1: only `readings` is honored on the server. Later phases
 *  will populate the rest of these fields per PLANNING_PDF_EXPORT.md.
 *  Kept on the type so the modal can build them up incrementally. */
export interface PdfExportOptions {
  readings?: number[];
  include_correspondences?: boolean;
  correspondence_types?: string[];
  include_custom_fields?: boolean;
  custom_fields?: string[];
  include_archetype_fields?: boolean;
  archetype_fields?: string[];
  include_chart?: boolean;
}

/**
 * Trigger a PDF download for the given entry. The browser handles
 * the actual save via a temporary `<a download>` link; the server
 * sends a Content-Disposition with the suggested filename, but
 * since axios+blob downloads strip headers we surface the filename
 * inline from the JSON response if the request fails, or extract
 * it from Content-Disposition when the response is binary.
 */
export async function exportEntryPdf(
  entryId: number,
  options: PdfExportOptions = {},
): Promise<void> {
  const res = await api.post(`/api/entries/${entryId}/export-pdf`, options, {
    responseType: 'blob',
  });

  // Extract filename from Content-Disposition if present.
  let filename = `journal_entry_${entryId}.pdf`;
  const cd =
    res.headers['content-disposition'] ||
    (res.headers as Record<string, string>)['Content-Disposition'];
  if (cd) {
    const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd);
    if (match && match[1]) filename = decodeURIComponent(match[1]);
  }

  // Trigger a download.
  const blob = new Blob([res.data], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
