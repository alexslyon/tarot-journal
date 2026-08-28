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
  /** Entry to show (or clear), set by the palette and by back/forward
   *  history; the token makes each application take effect. */
  entryLink?: { id: number | null; token: number } | null;
  /** Report user entry selections so history can restore them. */
  onEntrySelected?: (id: number | null) => void;
}

export default function JournalTab({
  pendingNewEntry,
  onNewEntryHandled,
  cardFilter,
  onClearCardFilter,
  onFindCardInJournal,
  entryLink,
  onEntrySelected,
}: JournalTabProps) {
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  /** User-driven selection: update state and tell the history. */
  const selectEntry = (id: number | null) => {
    setSelectedEntryId(id);
    onEntrySelected?.(id);
  };
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

  // Deep link (palette or history): show — or clear — an entry (the
  // viewer fetches by id, so it needn't be in the visible list page).
  // Applied directly, not via selectEntry: history applications must
  // not re-record themselves.
  useEffect(() => {
    if (!entryLink) return;
    setSelectedEntryId(entryLink.id);
  }, [entryLink]);

  const handleEdit = (entryId: number) => {
    setEditingEntryId(entryId);
    setTemplateEntryId(null);
    setShowEditor(true);
  };

  const handleDeleted = () => {
    selectEntry(null);
  };

  return (
    <div className="journal-tab">
      <Group orientation="horizontal" style={{ width: '100%', height: '100%' }}>
        <Panel defaultSize="30%" minSize="20%">
          <EntryList
            selectedEntryId={selectedEntryId}
            onSelectEntry={selectEntry}
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
                onNavigateEntry={selectEntry}
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
        onSaved={(id) => selectEntry(id)}
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
