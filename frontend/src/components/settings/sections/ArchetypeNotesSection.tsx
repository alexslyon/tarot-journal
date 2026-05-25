import { useState, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getArchetypeNoteFields,
  createArchetypeNoteField,
  updateArchetypeNoteField,
  deleteArchetypeNoteField,
  reorderArchetypeNoteFields,
  getArchetypeNoteFieldEntryCount,
  getArchetypeNoteEntries,
  createArchetypeNoteEntry,
  updateArchetypeNoteEntry,
  deleteArchetypeNoteEntry,
  reorderArchetypeNoteEntries,
} from '../../../api/archetypeNotes';
import { getReferenceSources } from '../../../api/referenceSources';
import { getArchetypes, type Archetype } from '../../../api/correspondences';
import { getCartomancyTypes } from '../../../api/decks';
import RichTextEditor from '../../common/RichTextEditor';
import RichTextViewer from '../../common/RichTextViewer';
import { useToast } from '../../../context/ToastContext';
import type {
  ArchetypeNoteField,
  ArchetypeNoteEntry,
  CartomancyType,
  ReferenceSource,
} from '../../../types';
import '../SettingsTab.css';
import './ArchetypeNotesSection.css';

const SUPPORTED_TYPES = ['Tarot', 'Lenormand', 'Playing Cards', 'Kipper', 'I Ching'];

interface Props {
  /** Pre-select this archetype on first render (deep-link from Reference). */
  initialArchetypeId?: number;
  onInitialApplied?: () => void;
}

export default function ArchetypeNotesSection({
  initialArchetypeId,
  onInitialApplied,
}: Props) {
  const { showToast } = useToast();

  // Cartomancy type + archetype pickers — same shape as the Reference viewer.
  const { data: types = [] } = useQuery<CartomancyType[]>({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });
  const supportedTypes = useMemo(
    () => types.filter(t => SUPPORTED_TYPES.includes(t.name)),
    [types],
  );

  const [cartomancyType, setCartomancyType] = useState('Tarot');

  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', cartomancyType],
    queryFn: () => getArchetypes(cartomancyType),
  });
  const sortedArchetypes = useMemo(
    () =>
      [...archetypes].sort(
        (a, b) => parseInt(a.rank || '0', 10) - parseInt(b.rank || '0', 10),
      ),
    [archetypes],
  );

  const [archetypeId, setArchetypeId] = useState<number | null>(null);
  useEffect(() => {
    if (sortedArchetypes.length === 0) return;
    if (!archetypeId || !sortedArchetypes.some(a => a.id === archetypeId)) {
      setArchetypeId(sortedArchetypes[0].id);
    }
  }, [sortedArchetypes, archetypeId]);
  // Apply deep-link selection once.
  useEffect(() => {
    if (initialArchetypeId) {
      setArchetypeId(initialArchetypeId);
      onInitialApplied?.();
    }
  }, [initialArchetypeId, onInitialApplied]);

  return (
    <div className="settings-tab__scroll archetype-notes-edit">
      <h2 className="settings-tab__title">Archetype Notes</h2>
      <p className="settings-tab__hint">
        Per-card freeform fields and entries. Each entry can optionally cite a
        shared reference source.
      </p>

      <section className="settings-tab__section">
        <div className="archetype-notes-edit__pickers">
          <div className="archetype-notes-edit__picker">
            <label className="settings-tab__label">Type</label>
            <select
              value={cartomancyType}
              onChange={e => setCartomancyType(e.target.value)}
            >
              {supportedTypes.map(t => (
                <option key={t.id} value={t.name}>{t.name}</option>
              ))}
            </select>
          </div>
          <div className="archetype-notes-edit__picker">
            <label className="settings-tab__label">Card</label>
            <select
              value={archetypeId ?? ''}
              onChange={e => setArchetypeId(e.target.value ? Number(e.target.value) : null)}
            >
              {sortedArchetypes.map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
        </div>

        {archetypeId != null && (
          <FieldList archetypeId={archetypeId} showToast={showToast} />
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Fields list for the selected archetype
// ---------------------------------------------------------------------------

function FieldList({
  archetypeId,
  showToast,
}: {
  archetypeId: number;
  showToast: (msg: string) => void;
}) {
  const queryClient = useQueryClient();
  const fieldsKey = ['archetype-note-fields', archetypeId];
  const { data: fields = [] } = useQuery<ArchetypeNoteField[]>({
    queryKey: fieldsKey,
    queryFn: () => getArchetypeNoteFields(archetypeId),
  });
  const invalidateFields = () => queryClient.invalidateQueries({ queryKey: fieldsKey });
  const invalidateNotes = () =>
    queryClient.invalidateQueries({ queryKey: ['archetype-notes', archetypeId] });

  const [adding, setAdding] = useState(false);
  const [newFieldName, setNewFieldName] = useState('');

  const handleAdd = async () => {
    if (!newFieldName.trim()) return;
    try {
      await createArchetypeNoteField(archetypeId, newFieldName.trim());
      setNewFieldName('');
      setAdding(false);
      invalidateFields();
    } catch {
      showToast('Could not add field.');
    }
  };

  // Drag-to-reorder for fields.
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);
  const handleFieldDrop = async (targetId: number) => {
    if (draggedId == null || draggedId === targetId) {
      setDraggedId(null); setDragOverId(null); return;
    }
    const ids = fields.map(f => f.id);
    const fromIdx = ids.indexOf(draggedId);
    const toIdx = ids.indexOf(targetId);
    if (fromIdx === -1 || toIdx === -1) {
      setDraggedId(null); setDragOverId(null); return;
    }
    ids.splice(fromIdx, 1);
    ids.splice(toIdx, 0, draggedId);
    try {
      await reorderArchetypeNoteFields(archetypeId, ids);
      invalidateFields();
      invalidateNotes();
    } catch {
      showToast('Could not reorder fields.');
    }
    setDraggedId(null); setDragOverId(null);
  };

  return (
    <>
      {fields.length === 0 && !adding && (
        <p className="archetype-notes-edit__empty">No fields yet.</p>
      )}

      <ul className="archetype-notes-edit__field-list">
        {fields.map(f => (
          <FieldRow
            key={f.id}
            field={f}
            archetypeId={archetypeId}
            showToast={showToast}
            onChanged={() => { invalidateFields(); invalidateNotes(); }}
            draggedId={draggedId}
            dragOverId={dragOverId}
            onDragStart={setDraggedId}
            onDragOver={setDragOverId}
            onDrop={handleFieldDrop}
            onDragEnd={() => { setDraggedId(null); setDragOverId(null); }}
          />
        ))}
      </ul>

      {adding ? (
        <div className="archetype-notes-edit__add-form">
          <input
            autoFocus
            placeholder="Field name (e.g. 'Divinatory Meaning', 'Symbolism')"
            value={newFieldName}
            onChange={e => setNewFieldName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            className="archetype-notes-edit__field-input"
          />
          <button onClick={handleAdd} disabled={!newFieldName.trim()}>Add</button>
          <button onClick={() => { setAdding(false); setNewFieldName(''); }}>Cancel</button>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="archetype-notes-edit__add-btn"
        >
          + Add Field
        </button>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Single field with its entries
// ---------------------------------------------------------------------------

function FieldRow({
  field,
  archetypeId,
  showToast,
  onChanged,
  draggedId,
  dragOverId,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: {
  field: ArchetypeNoteField;
  archetypeId: number;
  showToast: (msg: string) => void;
  onChanged: () => void;
  draggedId: number | null;
  dragOverId: number | null;
  onDragStart: (id: number) => void;
  onDragOver: (id: number) => void;
  onDrop: (id: number) => void;
  onDragEnd: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draftName, setDraftName] = useState(field.field_name);

  useEffect(() => {
    if (!editing) setDraftName(field.field_name);
  }, [field.field_name, editing]);

  const handleSaveName = async () => {
    if (!draftName.trim() || draftName.trim() === field.field_name) {
      setEditing(false);
      return;
    }
    try {
      await updateArchetypeNoteField(field.id, draftName.trim());
      setEditing(false);
      onChanged();
    } catch {
      showToast('Could not rename field.');
    }
  };

  const handleDeleteField = async () => {
    try {
      const { count } = await getArchetypeNoteFieldEntryCount(field.id);
      const msg = count > 0
        ? `Delete the field "${field.field_name}" and its ${count} entr${count === 1 ? 'y' : 'ies'}?`
        : `Delete the field "${field.field_name}"?`;
      if (!window.confirm(msg)) return;
      await deleteArchetypeNoteField(field.id);
      onChanged();
    } catch {
      showToast('Could not delete field.');
    }
  };

  const rowClass = [
    'archetype-notes-edit__field',
    draggedId === field.id ? 'archetype-notes-edit__field--dragging' : '',
    dragOverId === field.id ? 'archetype-notes-edit__field--drag-over' : '',
  ].filter(Boolean).join(' ');

  return (
    <li
      className={rowClass}
      draggable={!editing}
      onDragStart={() => onDragStart(field.id)}
      onDragOver={e => {
        if (draggedId == null || draggedId === field.id) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (dragOverId !== field.id) onDragOver(field.id);
      }}
      onDrop={e => { e.preventDefault(); onDrop(field.id); }}
      onDragEnd={onDragEnd}
    >
      <div className="archetype-notes-edit__field-header">
        <span className="archetype-notes-edit__drag" title="Drag to reorder">⋮⋮</span>
        {editing ? (
          <>
            <input
              autoFocus
              value={draftName}
              onChange={e => setDraftName(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') handleSaveName();
                if (e.key === 'Escape') { setDraftName(field.field_name); setEditing(false); }
              }}
              onBlur={handleSaveName}
              className="archetype-notes-edit__field-input"
            />
          </>
        ) : (
          <>
            <h4 className="archetype-notes-edit__field-name">{field.field_name}</h4>
            <button
              className="archetype-notes-edit__field-edit"
              onClick={() => setEditing(true)}
            >
              Rename
            </button>
            <button
              className="danger"
              onClick={handleDeleteField}
            >
              Delete
            </button>
          </>
        )}
      </div>

      <EntriesList
        fieldId={field.id}
        archetypeId={archetypeId}
        showToast={showToast}
      />
    </li>
  );
}

// ---------------------------------------------------------------------------
// Entries within a single field
// ---------------------------------------------------------------------------

function EntriesList({
  fieldId,
  archetypeId,
  showToast,
}: {
  fieldId: number;
  archetypeId: number;
  showToast: (msg: string) => void;
}) {
  const queryClient = useQueryClient();
  const entriesKey = ['archetype-note-entries', fieldId];
  const { data: entries = [] } = useQuery<ArchetypeNoteEntry[]>({
    queryKey: entriesKey,
    queryFn: () => getArchetypeNoteEntries(fieldId),
  });
  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: getReferenceSources,
  });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: entriesKey });
    queryClient.invalidateQueries({ queryKey: ['archetype-notes', archetypeId] });
  };

  const [adding, setAdding] = useState(false);
  const [draftContent, setDraftContent] = useState('');
  const [draftSourceId, setDraftSourceId] = useState<number | ''>('');

  // Drag-to-reorder for entries within this field.
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);
  const handleDrop = async (targetId: number) => {
    if (draggedId == null || draggedId === targetId) {
      setDraggedId(null); setDragOverId(null); return;
    }
    const ids = entries.map(e => e.id);
    const fromIdx = ids.indexOf(draggedId);
    const toIdx = ids.indexOf(targetId);
    if (fromIdx === -1 || toIdx === -1) {
      setDraggedId(null); setDragOverId(null); return;
    }
    ids.splice(fromIdx, 1);
    ids.splice(toIdx, 0, draggedId);
    try {
      await reorderArchetypeNoteEntries(fieldId, ids);
      invalidate();
    } catch {
      showToast('Could not reorder entries.');
    }
    setDraggedId(null); setDragOverId(null);
  };

  const handleAdd = async () => {
    if (!plainTextHasContent(draftContent)) return;
    try {
      await createArchetypeNoteEntry(
        fieldId,
        draftContent,
        draftSourceId === '' ? null : draftSourceId,
      );
      setDraftContent('');
      setDraftSourceId('');
      setAdding(false);
      invalidate();
    } catch {
      showToast('Could not add entry.');
    }
  };

  return (
    <div className="archetype-notes-edit__entries">
      <ul className="archetype-notes-edit__entry-list">
        {entries.map(e => (
          <EntryRow
            key={e.id}
            entry={e}
            sources={sources}
            invalidate={invalidate}
            showToast={showToast}
            draggedId={draggedId}
            dragOverId={dragOverId}
            onDragStart={setDraggedId}
            onDragOver={setDragOverId}
            onDrop={handleDrop}
            onDragEnd={() => { setDraggedId(null); setDragOverId(null); }}
          />
        ))}
      </ul>

      {adding ? (
        <div className="archetype-notes-edit__entry-edit">
          <RichTextEditor
            content={draftContent}
            onChange={setDraftContent}
            placeholder="Entry content..."
            minHeight={100}
          />
          <select
            value={draftSourceId}
            onChange={e => setDraftSourceId(e.target.value ? Number(e.target.value) : '')}
            className="archetype-notes-edit__source-select"
          >
            <option value="">— No source —</option>
            {sources.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <div className="archetype-notes-edit__entry-actions">
            <button onClick={() => { setAdding(false); setDraftContent(''); setDraftSourceId(''); }}>
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!plainTextHasContent(draftContent)}
              className="archetype-notes-edit__save-btn"
            >
              Add Entry
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="archetype-notes-edit__add-entry-btn"
        >
          + Add Entry
        </button>
      )}
    </div>
  );
}

function EntryRow({
  entry,
  sources,
  invalidate,
  showToast,
  draggedId,
  dragOverId,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: {
  entry: ArchetypeNoteEntry;
  sources: ReferenceSource[];
  invalidate: () => void;
  showToast: (msg: string) => void;
  draggedId: number | null;
  dragOverId: number | null;
  onDragStart: (id: number) => void;
  onDragOver: (id: number) => void;
  onDrop: (id: number) => void;
  onDragEnd: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draftContent, setDraftContent] = useState(entry.content);
  const [draftSourceId, setDraftSourceId] = useState<number | ''>(entry.source_id ?? '');

  useEffect(() => {
    if (!editing) {
      setDraftContent(entry.content);
      setDraftSourceId(entry.source_id ?? '');
    }
  }, [entry.content, entry.source_id, editing]);

  const handleSave = async () => {
    try {
      await updateArchetypeNoteEntry(entry.id, {
        content: draftContent,
        source_id: draftSourceId === '' ? null : draftSourceId,
      });
      setEditing(false);
      invalidate();
    } catch {
      showToast('Could not update entry.');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this entry?')) return;
    try {
      await deleteArchetypeNoteEntry(entry.id);
      invalidate();
    } catch {
      showToast('Could not delete entry.');
    }
  };

  const rowClass = [
    'archetype-notes-edit__entry',
    draggedId === entry.id ? 'archetype-notes-edit__entry--dragging' : '',
    dragOverId === entry.id ? 'archetype-notes-edit__entry--drag-over' : '',
  ].filter(Boolean).join(' ');

  return (
    <li
      className={rowClass}
      draggable={!editing}
      onDragStart={() => onDragStart(entry.id)}
      onDragOver={e => {
        if (draggedId == null || draggedId === entry.id) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (dragOverId !== entry.id) onDragOver(entry.id);
      }}
      onDrop={e => { e.preventDefault(); onDrop(entry.id); }}
      onDragEnd={onDragEnd}
    >
      <span className="archetype-notes-edit__drag" title="Drag to reorder">⋮⋮</span>
      {editing ? (
        <div className="archetype-notes-edit__entry-edit">
          <RichTextEditor
            content={draftContent}
            onChange={setDraftContent}
            minHeight={100}
          />
          <select
            value={draftSourceId}
            onChange={e => setDraftSourceId(e.target.value ? Number(e.target.value) : '')}
            className="archetype-notes-edit__source-select"
          >
            <option value="">— No source —</option>
            {sources.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <div className="archetype-notes-edit__entry-actions">
            <button onClick={() => { setEditing(false); setDraftContent(entry.content); setDraftSourceId(entry.source_id ?? ''); }}>
              Cancel
            </button>
            <button onClick={handleSave} className="archetype-notes-edit__save-btn">Save</button>
          </div>
        </div>
      ) : (
        <div className="archetype-notes-edit__entry-view">
          <RichTextViewer content={entry.content} />
          <div className="archetype-notes-edit__entry-meta">
            <span className="archetype-notes-edit__entry-source">
              {entry.source_name || 'Unsourced'}
            </span>
            <button onClick={() => setEditing(true)}>Edit</button>
            <button onClick={handleDelete} className="danger">Delete</button>
          </div>
        </div>
      )}
    </li>
  );
}

function plainTextHasContent(html: string): boolean {
  return html.replace(/<[^>]*>/g, '').trim().length > 0;
}
