import { useState, useEffect } from 'react';
import { Panel, Group, Separator } from 'react-resizable-panels';
import EntryList from './EntryList';
import EntryViewer from './EntryViewer';
import EntryEditorModal from './EntryEditorModal';
import ExportModal from './ExportModal';
import ImportModal from './ImportModal';
import './JournalTab.css';

interface JournalTabProps {
  /** Set by App when Cmd+N fires — open a fresh entry editor, then
   *  call onNewEntryHandled so a later remount doesn't re-trigger. */
  pendingNewEntry?: boolean;
  onNewEntryHandled?: () => void;
  /** "Find in Journal" card filter (set from the Library card viewer) */
  cardFilter?: string | null;
  onClearCardFilter?: () => void;
  onFindCardInJournal?: (cardName: string) => void;
}

export default function JournalTab({
  pendingNewEntry,
  onNewEntryHandled,
  cardFilter,
  onClearCardFilter,
  onFindCardInJournal,
}: JournalTabProps) {
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [editingEntryId, setEditingEntryId] = useState<number | null>(null);
  const [templateEntryId, setTemplateEntryId] = useState<number | null>(null);
  const [showExport, setShowExport] = useState(false);
  const [showImport, setShowImport] = useState(false);

  const handleNewEntry = () => {
    setEditingEntryId(null);
    setTemplateEntryId(null);
    setShowEditor(true);
  };

  // "New like this": fresh entry copying an existing one's structure
  const handleNewFromEntry = (entryId: number) => {
    setEditingEntryId(null);
    setTemplateEntryId(entryId);
    setShowEditor(true);
  };

  useEffect(() => {
    if (pendingNewEntry) {
      handleNewEntry();
      onNewEntryHandled?.();
    }
  }, [pendingNewEntry, onNewEntryHandled]);

  const handleEdit = (entryId: number) => {
    setEditingEntryId(entryId);
    setTemplateEntryId(null);
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
            cardFilter={cardFilter}
            onClearCardFilter={onClearCardFilter}
          />
        </Panel>
        <Separator className="resize-handle" />
        <Panel minSize="20%">
          <div className="journal-tab__content">
            {selectedEntryId ? (
              <EntryViewer
                entryId={selectedEntryId}
                onEdit={handleEdit}
                onNewFromEntry={handleNewFromEntry}
                onFindCardInJournal={onFindCardInJournal}
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
        templateEntryId={templateEntryId}
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
