import { useState, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { importEntries } from '../../api/entries';
import Modal from '../common/Modal';
import './ImportModal.css';

interface ImportModalProps {
  onClose: () => void;
}

type Step = 'upload' | 'importing' | 'done';

export default function ImportModal({ onClose }: ImportModalProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>('upload');
  const [fileName, setFileName] = useState('');
  const [fileData, setFileData] = useState<unknown>(null);
  const [mergeTags, setMergeTags] = useState(true);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{
    imported: number;
    skipped: number;
    tags_created: number;
  } | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setError('');

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target?.result as string);
        setFileData(data);
      } catch {
        setError('Invalid JSON file. Please select a valid export file.');
        setFileData(null);
      }
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    if (!fileData) return;
    setStep('importing');
    setError('');

    try {
      const res = await importEntries(fileData, mergeTags);
      setResult(res);
      setStep('done');
      queryClient.invalidateQueries({ queryKey: ['entries'] });
      queryClient.invalidateQueries({ queryKey: ['entry-tags'] });
    } catch (err) {
      setError('Import failed. Please check the file format and try again.');
      setStep('upload');
      console.error('Import error:', err);
    }
  };

  return (
    <Modal open={true} onClose={onClose} title="Import Journal Entries" width={480}>
      <div className="import-modal">
        {step === 'upload' && (
          <>
            <div className="import-modal__file-area">
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleFileSelect}
                className="import-modal__file-input"
              />
              <button
                className="import-modal__file-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                Choose JSON File
              </button>
              {fileName && (
                <span className="import-modal__file-name">{fileName}</span>
              )}
            </div>

            <label className="import-modal__check">
              <input
                type="checkbox"
                checked={mergeTags}
                onChange={(e) => setMergeTags(e.target.checked)}
              />
              <span>Merge tags with existing tags (match by name)</span>
            </label>

            {error && <div className="import-modal__error">{error}</div>}

            <div className="import-modal__footer">
              <button onClick={onClose}>Cancel</button>
              <button
                className="primary"
                onClick={handleImport}
                disabled={!fileData}
              >
                Import
              </button>
            </div>
          </>
        )}

        {step === 'importing' && (
          <div className="import-modal__status">
            Importing entries...
          </div>
        )}

        {step === 'done' && result && (
          <>
            <div className="import-modal__result">
              <div className="import-modal__result-row">
                <span className="import-modal__result-label">Entries imported:</span>
                <span className="import-modal__result-value">{result.imported}</span>
              </div>
              <div className="import-modal__result-row">
                <span className="import-modal__result-label">Entries skipped:</span>
                <span className="import-modal__result-value">{result.skipped}</span>
              </div>
              <div className="import-modal__result-row">
                <span className="import-modal__result-label">Tags created:</span>
                <span className="import-modal__result-value">{result.tags_created}</span>
              </div>
            </div>
            <div className="import-modal__footer">
              <button className="primary" onClick={onClose}>Done</button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
