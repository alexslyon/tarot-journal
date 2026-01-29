import { useState } from 'react';
import { Panel, Group, Separator } from 'react-resizable-panels';
import EntryList from './EntryList';
import EntryViewer from './EntryViewer';
import EntryEditorModal from './EntryEditorModal';
import ExportModal from './ExportModal';
import ImportModal from './ImportModal';
import './JournalTab.css';

export default function JournalTab() {
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [editingEntryId, setEditingEntryId] = useState<number | null>(null);
  const [showExport, setShowExport] = useState(false);
  const [showImport, setShowImport] = useState(false);

  const handleNewEntry = () => {
    setEditingEntryId(null);
    setShowEditor(true);
  };

  const handleEdit = (entryId: number) => {
    setEditingEntryId(entryId);
    setShowEditor(true);
  };

  const handleDeleted = () => {
    setSelectedEntryId(null);
  };

  return (
    <div className="journal-tab">
      <Group orientation="horizontal" style={{ width: '100%', height: '100%' }}>
        <Panel defaultSize="30%" minSize="20%">
          <EntryList
            selectedEntryId={selectedEntryId}
            onSelectEntry={setSelectedEntryId}
            onNewEntry={handleNewEntry}
            onExport={() => setShowExport(true)}
            onImport={() => setShowImport(true)}
          />
        </Panel>
        <Separator className="resize-handle" />
        <Panel minSize="20%">
          <div className="journal-tab__content">
            {selectedEntryId ? (
              <EntryViewer
                entryId={selectedEntryId}
                onEdit={handleEdit}
                onDeleted={handleDeleted}
              />
            ) : (
              <div className="journal-tab__placeholder">
                Select an entry to view details
              </div>
            )}
          </div>
        </Panel>
      </Group>

      <EntryEditorModal
        entryId={editingEntryId}
        open={showEditor}
        onClose={() => setShowEditor(false)}
        onSaved={(id) => setSelectedEntryId(id)}
      />

      {showExport && (
        <ExportModal
          onClose={() => setShowExport(false)}
          selectedEntryIds={selectedEntryId ? [selectedEntryId] : undefined}
        />
      )}

      {showImport && (
        <ImportModal onClose={() => setShowImport(false)} />
      )}
    </div>
  );
}
