/**
 * Export / Import button pair for shareable JSON collections (spreads,
 * profiles). Export downloads immediately — everything, or just the
 * selected item when the caller passes one. Import opens a small modal:
 * pick a .json share file, see what happened.
 */
import { useRef, useState } from 'react';
import Modal, { ModalCancelButton } from './Modal';
import { useToast } from '../../context/ToastContext';
import './ShareControls.css';

interface ShareControlsProps {
  /** Noun for labels, e.g. "spreads". */
  noun: string;
  /** Download everything (no args) or a selection (ids). */
  onExport: (ids?: number[]) => Promise<void>;
  /** The currently selected item, offered as an export choice. */
  selected?: { id: number; name: string } | null;
  /** Parse-and-import; resolves to a human summary line. */
  onImport: (data: unknown) => Promise<string>;
}

export default function ShareControls({
  noun,
  onExport,
  selected,
  onImport,
}: ShareControlsProps) {
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const runExport = async (ids?: number[]) => {
    setBusy(true);
    try {
      await onExport(ids);
      setExportOpen(false);
    } catch {
      showToast(`Could not export ${noun}.`);
    } finally {
      setBusy(false);
    }
  };

  const handleExportClick = () => {
    // With nothing selected there's only one choice — skip the modal.
    if (selected) setExportOpen(true);
    else runExport();
  };

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      let data: unknown;
      try {
        data = JSON.parse(ev.target?.result as string);
      } catch {
        showToast('That file is not valid JSON.');
        return;
      }
      setBusy(true);
      try {
        const summary = await onImport(data);
        showToast(summary, 'success');
      } catch (err) {
        const detail = (err as { response?: { data?: { error?: string } } })
          ?.response?.data?.error;
        showToast(detail || `Could not import ${noun}.`);
      } finally {
        setBusy(false);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="share-controls">
      <button onClick={handleExportClick} disabled={busy}>Export</button>
      <button onClick={() => fileInputRef.current?.click()} disabled={busy}>
        Import
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json,application/json"
        hidden
        onChange={e => { handleFile(e.target.files?.[0]); e.target.value = ''; }}
      />

      <Modal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        title={`Export ${noun}`}
        width={420}
      >
        <div className="share-controls__export">
          <button className="primary" onClick={() => runExport()} disabled={busy}>
            Export all {noun}
          </button>
          {selected && (
            <button onClick={() => runExport([selected.id])} disabled={busy}>
              Export only “{selected.name}”
            </button>
          )}
          <div className="share-controls__footer">
            <ModalCancelButton>Cancel</ModalCancelButton>
          </div>
        </div>
      </Modal>
    </div>
  );
}
