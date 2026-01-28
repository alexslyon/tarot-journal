import { useState } from 'react';
import { exportEntriesUrl } from '../../api/entries';
import Modal from '../common/Modal';
import './ExportModal.css';

interface ExportModalProps {
  onClose: () => void;
  selectedEntryIds?: number[];
}

export default function ExportModal({ onClose, selectedEntryIds }: ExportModalProps) {
  const [scope, setScope] = useState<'all' | 'selected'>(
    selectedEntryIds?.length ? 'selected' : 'all'
  );

  const handleExport = () => {
    const ids = scope === 'selected' ? selectedEntryIds : undefined;
    const url = exportEntriesUrl(ids);
    // Open in new tab to trigger download
    window.open(url, '_blank');
    onClose();
  };

  return (
    <Modal open={true} onClose={onClose} title="Export Journal Entries" width={440}>
      <div className="export-modal">
        <div className="export-modal__options">
          <label className="export-modal__radio">
            <input
              type="radio"
              name="exportScope"
              checked={scope === 'all'}
              onChange={() => setScope('all')}
            />
            <span>Export all entries</span>
          </label>
          {selectedEntryIds && selectedEntryIds.length > 0 && (
            <label className="export-modal__radio">
              <input
                type="radio"
                name="exportScope"
                checked={scope === 'selected'}
                onChange={() => setScope('selected')}
              />
              <span>Export selected ({selectedEntryIds.length} entries)</span>
            </label>
          )}
        </div>

        <p className="export-modal__info">
          Entries will be exported as a JSON file that can be imported back later.
        </p>

        <div className="export-modal__footer">
          <button onClick={onClose}>Cancel</button>
          <button className="primary" onClick={handleExport}>Export</button>
        </div>
      </div>
    </Modal>
  );
}
