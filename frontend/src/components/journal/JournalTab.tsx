import { useState, useEffect } from 'react';
import { Panel, Group, Separator } from 'react-resizable-panels';
import EntryList from './EntryList';
import EntryViewer from './EntryViewer';
import EntryEditorModal from './EntryEditorModal';
import ExportModal from './ExportModal';
import ImportModal from './ImportModal';
import AnalystModal from './AnalystModal';
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
  /** Entry to select on mount (set by the command palette) */
  pendingEntryId?: number | null;
  onPendingEntryHandled?: () => void;
}

export default function JournalTab({
  pendingNewEntry,
  onNewEntryHandled,
  cardFilter,
  onClearCardFilter,
  onFindCardInJournal,
  pendingEntryId,
  onPendingEntryHandled,
}: JournalTabProps) {
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  // Ids of entries currently visible in the list (list order: newest
  // first) — lets the viewer offer Newer/Older navigation.
  const [visibleIds, setVisibleIds] = useState<number[]>([]);
  const [showEditor, setShowEditor] = useState(false);
  const [editingEntryId, setEditingEntryId] = useState<number | null>(null);
  const [templateEntryId, setTemplateEntryId] = useState<number | null>(null);
  const [showExport, setShowExport] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showAnalyst, setShowAnalyst] = useState(false);

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

  // Command-palette deep link: open the requested entry (the viewer
  // fetches it by id, so it needn't be in the visible list page).
  useEffect(() => {
    if (pendingEntryId == null) return;
    setSelectedEntryId(pendingEntryId);
    onPendingEntryHandled?.();
  }, [pendingEntryId, onPendingEntryHandled]);

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
            onAnalyst={() => setShowAnalyst(true)}
            cardFilter={cardFilter}
            onClearCardFilter={onClearCardFilter}
            onVisibleEntries={setVisibleIds}
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
                // List is newest-first: "newer" is the previous index
                newerEntryId={(() => {
                  const idx = visibleIds.indexOf(selectedEntryId);
                  return idx > 0 ? visibleIds[idx - 1] : null;
                })()}
                olderEntryId={(() => {
                  const idx = visibleIds.indexOf(selectedEntryId);
                  return idx >= 0 && idx < visibleIds.length - 1 ? visibleIds[idx + 1] : null;
                })()}
                onNavigateEntry={setSelectedEntryId}
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

      <AnalystModal
        entryIds={visibleIds}
        open={showAnalyst}
        onClose={() => setShowAnalyst(false)}
      />

      {showImport && (
        <ImportModal onClose={() => setShowImport(false)} />
      )}
    </div>
  );
}
