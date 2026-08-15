/**
 * The combination meanings editor — add / edit / delete / reorder
 * meanings with per-meaning source attribution. Shared by the
 * Settings editor page and the Reference tab's inline edit mode, so
 * the two can never drift apart.
 */
import { useState, useEffect } from 'react';
import {
  createCombinationMeaning,
  updateCombinationMeaning,
  deleteCombinationMeaning,
  reorderCombinationMeanings,
} from '../../api/combinations';
import RichTextEditor from '../common/RichTextEditor';
import RichTextViewer from '../common/RichTextViewer';
import { confirmDialog } from '../common/ConfirmDialog';
import type { ReferenceSource, CombinationMeaning } from '../../types';
import '../settings/sections/CombinationsSection.css';

// ---------------------------------------------------------------------------
// Meanings editor
// ---------------------------------------------------------------------------

export function MeaningsEditor({
  cartomancyType,
  card1Id,
  card2Id,
  card1Rev,
  card2Rev,
  meanings,
  sources,
  onChanged,
  showToast,
}: {
  cartomancyType: string;
  card1Id: number;
  card2Id: number;
  card1Rev: boolean;
  card2Rev: boolean;
  meanings: CombinationMeaning[];
  sources: ReferenceSource[];
  onChanged: () => void;
  showToast: (msg: string) => void;
}) {
  const [draftMeaning, setDraftMeaning] = useState('');
  const [draftSourceId, setDraftSourceId] = useState<number | ''>('');
  const [adding, setAdding] = useState(false);

  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);

  const handleAdd = async () => {
    if (!draftMeaning.trim()) return;
    try {
      await createCombinationMeaning(
        cartomancyType,
        card1Id,
        card2Id,
        draftMeaning,
        draftSourceId === '' ? null : draftSourceId,
        card1Rev,
        card2Rev,
      );
      setDraftMeaning('');
      setDraftSourceId('');
      setAdding(false);
      onChanged();
    } catch {
      showToast('Could not add meaning.');
    }
  };

  const handleDrop = async (targetId: number) => {
    if (draggedId == null || draggedId === targetId) {
      setDraggedId(null);
      setDragOverId(null);
      return;
    }
    const ids = meanings.map(m => m.id);
    const fromIdx = ids.indexOf(draggedId);
    const toIdx = ids.indexOf(targetId);
    if (fromIdx === -1 || toIdx === -1) {
      setDraggedId(null);
      setDragOverId(null);
      return;
    }
    ids.splice(fromIdx, 1);
    ids.splice(toIdx, 0, draggedId);
    const combinationId = meanings[0]?.combination_id;
    if (combinationId == null) return;
    try {
      await reorderCombinationMeanings(combinationId, ids);
      onChanged();
    } catch {
      showToast('Could not reorder meanings.');
    }
    setDraggedId(null);
    setDragOverId(null);
  };

  return (
    <div className="combinations__editor">
      {meanings.length === 0 && !adding && (
        <p className="combinations__empty">
          No meanings yet for this combination.
        </p>
      )}

      <ul className="combinations__meanings">
        {meanings.map(m => (
          <MeaningRow
            key={m.id}
            meaning={m}
            sources={sources}
            onChanged={onChanged}
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
        <div className="combinations__meaning-add">
          <RichTextEditor
            content={draftMeaning}
            onChange={setDraftMeaning}
            placeholder="Meaning..."
            minHeight={80}
          />
          <select
            value={draftSourceId}
            onChange={e => setDraftSourceId(e.target.value ? Number(e.target.value) : '')}
            className="combinations__source-select"
          >
            <option value="">— No source —</option>
            {sources.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <div className="combinations__meaning-add-actions">
            <button onClick={() => { setAdding(false); setDraftMeaning(''); setDraftSourceId(''); }}>
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!plainTextHasContent(draftMeaning)}
              className="combinations__save-btn"
            >
              Add Meaning
            </button>
          </div>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} className="combinations__add-meaning-btn">
          + Add Meaning
        </button>
      )}
    </div>
  );
}

function MeaningRow({
  meaning,
  sources,
  onChanged,
  showToast,
  draggedId,
  dragOverId,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: {
  meaning: CombinationMeaning;
  sources: ReferenceSource[];
  onChanged: () => void;
  showToast: (msg: string) => void;
  draggedId: number | null;
  dragOverId: number | null;
  onDragStart: (id: number) => void;
  onDragOver: (id: number) => void;
  onDrop: (id: number) => void;
  onDragEnd: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(meaning.meaning);
  const [draftSourceId, setDraftSourceId] = useState<number | ''>(
    meaning.source_id ?? '',
  );
  // The list is filtered to this deck type; if the meaning is already
  // attributed to a source outside it, keep that source selectable so
  // editing the text can't silently drop the attribution.
  const rowSources = meaning.source_id != null
    && !sources.some(src => src.id === meaning.source_id)
    ? [{ id: meaning.source_id, name: meaning.source_name || 'Unknown source' } as ReferenceSource, ...sources]
    : sources;

  useEffect(() => {
    if (!editing) {
      setDraft(meaning.meaning);
      setDraftSourceId(meaning.source_id ?? '');
    }
  }, [meaning.meaning, meaning.source_id, editing]);

  const handleSave = async () => {
    try {
      await updateCombinationMeaning(meaning.id, {
        meaning: draft,
        source_id: draftSourceId === '' ? null : draftSourceId,
      });
      setEditing(false);
      onChanged();
    } catch {
      showToast('Could not update meaning.');
    }
  };

  const handleDelete = async () => {
    if (!(await confirmDialog('Delete this meaning?'))) return;
    try {
      await deleteCombinationMeaning(meaning.id);
      onChanged();
    } catch {
      showToast('Could not delete meaning.');
    }
  };

  const rowClass = [
    'combinations__meaning-row',
    draggedId === meaning.id ? 'combinations__meaning-row--dragging' : '',
    dragOverId === meaning.id ? 'combinations__meaning-row--drag-over' : '',
  ].filter(Boolean).join(' ');

  return (
    <li
      className={rowClass}
      draggable={!editing}
      onDragStart={() => onDragStart(meaning.id)}
      onDragOver={e => {
        if (draggedId == null || draggedId === meaning.id) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (dragOverId !== meaning.id) onDragOver(meaning.id);
      }}
      onDrop={e => { e.preventDefault(); onDrop(meaning.id); }}
      onDragEnd={onDragEnd}
    >
      <span className="combinations__drag-handle" title="Drag to reorder">⋮⋮</span>
      {editing ? (
        <div className="combinations__meaning-edit">
          <RichTextEditor
            content={draft}
            onChange={setDraft}
            minHeight={80}
          />
          <select
            value={draftSourceId}
            onChange={e => setDraftSourceId(e.target.value ? Number(e.target.value) : '')}
            className="combinations__source-select"
          >
            <option value="">— No source —</option>
            {rowSources.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <div className="combinations__meaning-edit-actions">
            <button onClick={() => { setEditing(false); setDraft(meaning.meaning); setDraftSourceId(meaning.source_id ?? ''); }}>
              Cancel
            </button>
            <button onClick={handleSave} className="combinations__save-btn">
              Save
            </button>
          </div>
        </div>
      ) : (
        <div className="combinations__meaning-content">
          <RichTextViewer content={meaning.meaning} />
          <div className="combinations__meaning-meta">
            <span className="combinations__meaning-source">
              {meaning.source_name || 'Unsourced'}
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
