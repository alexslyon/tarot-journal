import { useEffect, useMemo, useState } from 'react';
import { exportEntryPdf } from '../../api/pdfExport';
import { useToast } from '../../context/ToastContext';
import type { JournalEntryFull } from '../../types';
import './PdfExportModal.css';

interface Props {
  entry: JournalEntryFull;
  open: boolean;
  onClose: () => void;
}

/**
 * Phase 1 of the journal PDF export modal. Surfaces the reading
 * selection only; the optional sections (correspondences, custom
 * fields, archetype fields, chart) are stubbed in as disabled rows
 * with "Coming soon" copy so the layout is in place for later
 * phases. Reading selection requires at least one box checked.
 */
export default function PdfExportModal({ entry, open, onClose }: Props) {
  const { showToast } = useToast();
  const [selectedReadings, setSelectedReadings] = useState<Set<number>>(
    new Set(),
  );
  const [generating, setGenerating] = useState(false);

  // Reset selection whenever the modal opens or the entry changes,
  // defaulting to "all readings" — matches the planning doc.
  useEffect(() => {
    if (open) {
      setSelectedReadings(new Set(entry.readings.map(r => r.id)));
    }
  }, [open, entry.id, entry.readings]);

  const hasMultipleReadings = entry.readings.length > 1;
  const noneSelected = selectedReadings.size === 0;

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

  const handleGenerate = async () => {
    if (noneSelected) return;
    setGenerating(true);
    try {
      await exportEntryPdf(entry.id, {
        readings: [...selectedReadings],
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

          {/* The optional sections from PLANNING_PDF_EXPORT.md land
              in later phases. Surface them as disabled rows now so
              the modal layout is recognisable when those toggles
              come online. */}
          <section className="pdf-export-modal__section pdf-export-modal__section--disabled">
            <h3>Optional sections</h3>
            <ul className="pdf-export-modal__list">
              <li>
                <label>
                  <input type="checkbox" disabled />
                  <span>Correspondence breakdown — coming soon</span>
                </label>
              </li>
              <li>
                <label>
                  <input type="checkbox" disabled />
                  <span>Card custom fields — coming soon</span>
                </label>
              </li>
              <li>
                <label>
                  <input type="checkbox" disabled />
                  <span>Archetype reference info — coming soon</span>
                </label>
              </li>
              <li>
                <label>
                  <input type="checkbox" disabled />
                  <span>Astrological event chart — coming soon</span>
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
