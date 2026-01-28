import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCartomancyTypes } from '../../api/decks';
import { getImportPresets, scanFolder, importFromFolder } from '../../api/importExport';
import Modal from '../common/Modal';
import './ImportDeckModal.css';

interface ImportDeckModalProps {
  onClose: () => void;
  onImported: (deckId: number) => void;
}

type Step = 'configure' | 'preview' | 'importing' | 'done';

export default function ImportDeckModal({ onClose, onImported }: ImportDeckModalProps) {
  const queryClient = useQueryClient();

  const { data: types = [] } = useQuery({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });

  const { data: presets = [] } = useQuery({
    queryKey: ['import-presets'],
    queryFn: getImportPresets,
  });

  // Configure step
  const [folder, setFolder] = useState('');
  const [deckName, setDeckName] = useState('');
  const [typeId, setTypeId] = useState<number>(0);
  const [preset, setPreset] = useState('');
  const [error, setError] = useState('');

  // Preview step
  const [step, setStep] = useState<Step>('configure');
  const [previewCards, setPreviewCards] = useState<Array<{ filename: string; name: string; sort_order: number }>>([]);
  const [scanning, setScanning] = useState(false);

  // Done step
  const [result, setResult] = useState<{ deck_id: number; cards_imported: number } | null>(null);

  // Default type to first available
  if (typeId === 0 && types.length > 0) {
    setTypeId(types[0].id);
  }

  const handleScan = async () => {
    if (!folder.trim()) {
      setError('Please enter a folder path');
      return;
    }
    setError('');
    setScanning(true);
    try {
      const res = await scanFolder(folder, preset);
      setPreviewCards(res.cards);
      if (!deckName) {
        // Default deck name to folder name
        const parts = folder.replace(/\/$/, '').split('/');
        setDeckName(parts[parts.length - 1]);
      }
      setStep('preview');
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Failed to scan folder');
    } finally {
      setScanning(false);
    }
  };

  const handleImport = async () => {
    if (!deckName.trim()) {
      setError('Deck name is required');
      return;
    }
    setError('');
    setStep('importing');
    try {
      const res = await importFromFolder({
        folder,
        deck_name: deckName,
        cartomancy_type_id: typeId,
        preset_name: preset,
      });
      setResult(res);
      setStep('done');
      queryClient.invalidateQueries({ queryKey: ['decks'] });
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Import failed');
      setStep('preview');
    }
  };

  return (
    <Modal open={true} onClose={onClose} width={600}>
      <div className="import-deck">
        <h2 className="import-deck__title">Import Deck from Folder</h2>

        {error && <div className="import-deck__error">{error}</div>}

        {step === 'configure' && (
          <>
            <div className="import-deck__form">
              <div className="import-deck__field">
                <label className="import-deck__label">Image Folder Path</label>
                <input
                  type="text"
                  value={folder}
                  onChange={e => setFolder(e.target.value)}
                  placeholder="/path/to/card/images"
                />
              </div>

              <div className="import-deck__field">
                <label className="import-deck__label">Deck Name</label>
                <input
                  type="text"
                  value={deckName}
                  onChange={e => setDeckName(e.target.value)}
                  placeholder="Will default to folder name"
                />
              </div>

              <div className="import-deck__row">
                <div className="import-deck__field" style={{ flex: 1 }}>
                  <label className="import-deck__label">Cartomancy Type</label>
                  <select value={typeId} onChange={e => setTypeId(parseInt(e.target.value))}>
                    {types.map(t => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>

                <div className="import-deck__field" style={{ flex: 1 }}>
                  <label className="import-deck__label">Import Preset</label>
                  <select value={preset} onChange={e => setPreset(e.target.value)}>
                    <option value="">None (use filenames)</option>
                    {presets.map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="import-deck__footer">
              <button onClick={onClose}>Cancel</button>
              <button
                className="import-deck__primary-btn"
                onClick={handleScan}
                disabled={scanning || !folder.trim()}
              >
                {scanning ? 'Scanning...' : 'Scan Folder'}
              </button>
            </div>
          </>
        )}

        {step === 'preview' && (
          <>
            <div className="import-deck__preview">
              <p className="import-deck__preview-count">
                Found {previewCards.length} cards in folder
              </p>
              <div className="import-deck__preview-list">
                <div className="import-deck__preview-header">
                  <span>#</span>
                  <span>Filename</span>
                  <span>Card Name</span>
                </div>
                {previewCards.map((c, i) => (
                  <div key={i} className="import-deck__preview-row">
                    <span>{c.sort_order}</span>
                    <span className="import-deck__preview-filename">{c.filename}</span>
                    <span>{c.name}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="import-deck__footer">
              <button onClick={() => setStep('configure')}>Back</button>
              <button
                className="import-deck__primary-btn"
                onClick={handleImport}
                disabled={!deckName.trim()}
              >
                Import {previewCards.length} Cards
              </button>
            </div>
          </>
        )}

        {step === 'importing' && (
          <div className="import-deck__status">
            Importing cards...
          </div>
        )}

        {step === 'done' && result && (
          <>
            <div className="import-deck__status import-deck__status--success">
              Successfully imported {result.cards_imported} cards!
            </div>
            <div className="import-deck__footer">
              <button
                className="import-deck__primary-btn"
                onClick={() => {
                  onImported(result.deck_id);
                  onClose();
                }}
              >
                View Deck
              </button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
