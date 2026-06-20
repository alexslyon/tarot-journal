import { useEffect, useMemo, useState } from 'react';
import { exportEntryPdf } from '../../api/pdfExport';
import { useToast } from '../../context/ToastContext';
import { useEntryBreakdown } from '../../utils/readingBreakdown';
import { CORRESPONDENCE_FIELD_LABELS } from '../../types';
import type { JournalEntryFull, BreakdownSettings } from '../../types';
import './PdfExportModal.css';

interface Props {
  entry: JournalEntryFull;
  open: boolean;
  onClose: () => void;
}

/**
 * Resolve the default sub-toggle state for the Correspondence
 * Breakdown section. Per the planning doc: prefer the visibility
 * the user already saved for this entry's in-app Reading Breakdown
 * (so opening the export modal feels like "what I was just
 * looking at"), otherwise default to every present field enabled.
 */
function defaultEnabledFields(
  presentFilterFields: string[],
  savedSettings: BreakdownSettings | null,
): Set<string> {
  if (!savedSettings) {
    return new Set(presentFilterFields);
  }
  // Reading Breakdown convention: missing key = visible.
  const visible = savedSettings.visible || {};
  return new Set(
    presentFilterFields.filter(f => visible[f] !== false),
  );
}

function parseBreakdownSettings(raw: string | null): BreakdownSettings | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return {
      open: typeof parsed.open === 'boolean' ? parsed.open : false,
      last_tab:
        parsed.last_tab === 'all' || typeof parsed.last_tab === 'number'
          ? parsed.last_tab
          : 'all',
      visible:
        parsed.visible && typeof parsed.visible === 'object'
          ? parsed.visible
          : {},
    };
  } catch {
    return null;
  }
}

function labelForField(field: string): string {
  if (field === 'suit') return 'Suit';
  if (field === 'rank') return 'Rank';
  return CORRESPONDENCE_FIELD_LABELS[field] || field;
}

/**
 * Phase 2 of the journal PDF export modal. Reading selection
 * plus a master "include correspondence breakdown" toggle with
 * a sub-checklist of every field the in-app Reading Breakdown
 * surfaces for this entry. The remaining optional sections
 * (custom fields, archetype fields, chart) stay stubbed as
 * "coming soon" placeholders for later phases.
 */
export default function PdfExportModal({ entry, open, onClose }: Props) {
  const { showToast } = useToast();
  const [selectedReadings, setSelectedReadings] = useState<Set<number>>(
    new Set(),
  );
  const [generating, setGenerating] = useState(false);
  const [includeCorrespondences, setIncludeCorrespondences] = useState(false);
  const [enabledFields, setEnabledFields] = useState<Set<string>>(new Set());

  const breakdown = useEntryBreakdown(open ? entry : undefined);
  const presentFilterFields = breakdown.presentFilterFields;
  const savedSettings = useMemo(
    () => parseBreakdownSettings(entry.breakdown_settings),
    [entry.breakdown_settings],
  );

  // Reset selection whenever the modal opens or the entry changes,
  // defaulting to "all readings" and (per the planning doc) the
  // user's saved breakdown visibility for the sub-toggles.
  useEffect(() => {
    if (open) {
      setSelectedReadings(new Set(entry.readings.map(r => r.id)));
      setIncludeCorrespondences(false);
    }
  }, [open, entry.id, entry.readings]);

  // Re-seed sub-toggle defaults once the breakdown data resolves
  // (queries fan out per card so it can take a render or two).
  useEffect(() => {
    if (!open) return;
    if (presentFilterFields.length === 0) return;
    setEnabledFields(defaultEnabledFields(presentFilterFields, savedSettings));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, entry.id, presentFilterFields.join('|')]);

  const hasMultipleReadings = entry.readings.length > 1;
  const noneSelected = selectedReadings.size === 0;
  const hasFilterableBreakdown = presentFilterFields.length > 0;

  const orderedReadings = useMemo(
    () => [...entry.readings].sort((a, b) => a.id - b.id),
    [entry.readings],
  );

  const toggleReading = (id: number) => {
    setSelectedReadings(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleField = (field: string) => {
    setEnabledFields(prev => {
      const next = new Set(prev);
      if (next.has(field)) next.delete(field);
      else next.add(field);
      return next;
    });
  };

  const handleGenerate = async () => {
    if (noneSelected) return;
    setGenerating(true);
    try {
      await exportEntryPdf(entry.id, {
        readings: [...selectedReadings],
        include_correspondences: includeCorrespondences && hasFilterableBreakdown,
        correspondence_types:
          includeCorrespondences && hasFilterableBreakdown
            ? [...enabledFields]
            : undefined,
      });
      showToast('PDF downloaded');
      onClose();
    } catch (e) {
      console.error('PDF export failed:', e);
      showToast('PDF export failed — see console for details');
    } finally {
      setGenerating(false);
    }
  };

  if (!open) return null;

  return (
    <div className="pdf-export-modal__backdrop" onClick={onClose}>
      <div
        className="pdf-export-modal"
        role="dialog"
        aria-modal="true"
        onClick={e => e.stopPropagation()}
      >
        <div className="pdf-export-modal__header">
          <h2>Export to PDF</h2>
          <button
            type="button"
            className="pdf-export-modal__close"
            aria-label="Close"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="pdf-export-modal__body">
          {hasMultipleReadings && (
            <section className="pdf-export-modal__section">
              <h3>Readings to include</h3>
              <ul className="pdf-export-modal__list">
                {orderedReadings.map(r => (
                  <li key={r.id}>
                    <label>
                      <input
                        type="checkbox"
                        checked={selectedReadings.has(r.id)}
                        onChange={() => toggleReading(r.id)}
                      />
                      <span>
                        {r.spread_name || `Reading ${r.id}`}
                        {r.deck_name ? ` — ${r.deck_name}` : ''}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
              {noneSelected && (
                <p className="pdf-export-modal__error">
                  Select at least one reading to include.
                </p>
              )}
            </section>
          )}

          <section className="pdf-export-modal__section">
            <h3>Always included</h3>
            <ul className="pdf-export-modal__static-list">
              <li>Header (title, date, location, querents/reader, tags)</li>
              <li>Spread layout with card images and position labels</li>
              <li>Position key (position → card name)</li>
              <li>Journal entry notes</li>
              <li>Follow-up notes</li>
            </ul>
          </section>

          <section className="pdf-export-modal__section">
            <h3>Correspondence breakdown</h3>
            <label className="pdf-export-modal__master">
              <input
                type="checkbox"
                checked={includeCorrespondences}
                onChange={e => setIncludeCorrespondences(e.target.checked)}
                disabled={!hasFilterableBreakdown}
              />
              <span>Include correspondence breakdown</span>
            </label>
            {!hasFilterableBreakdown && (
              <p className="pdf-export-modal__hint">
                {breakdown.isLoading
                  ? 'Loading card correspondences…'
                  : 'No correspondences resolved for this entry — nothing to break down.'}
              </p>
            )}
            {includeCorrespondences && hasFilterableBreakdown && (
              <ul className="pdf-export-modal__list pdf-export-modal__list--nested">
                {presentFilterFields.map(field => (
                  <li key={field}>
                    <label>
                      <input
                        type="checkbox"
                        checked={enabledFields.has(field)}
                        onChange={() => toggleField(field)}
                      />
                      <span>{labelForField(field)}</span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Remaining optional sections — phases 3 & 4. */}
          <section className="pdf-export-modal__section pdf-export-modal__section--disabled">
            <h3>Optional sections (coming soon)</h3>
            <ul className="pdf-export-modal__list">
              <li>
                <label>
                  <input type="checkbox" disabled />
                  <span>Card custom fields</span>
                </label>
              </li>
              <li>
                <label>
                  <input type="checkbox" disabled />
                  <span>Archetype reference info</span>
                </label>
              </li>
              <li>
                <label>
                  <input type="checkbox" disabled />
                  <span>Astrological event chart</span>
                </label>
              </li>
            </ul>
          </section>
        </div>

        <div className="pdf-export-modal__footer">
          <button
            type="button"
            className="pdf-export-modal__cancel"
            onClick={onClose}
            disabled={generating}
          >
            Cancel
          </button>
          <button
            type="button"
            className="pdf-export-modal__generate"
            onClick={handleGenerate}
            disabled={noneSelected || generating}
          >
            {generating ? 'Generating…' : 'Generate PDF'}
          </button>
        </div>
      </div>
    </div>
  );
}
