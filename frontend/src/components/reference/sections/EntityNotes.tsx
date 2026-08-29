/**
 * Source texts on a reference entity (a sign, planet, sephira, path,
 * chakra, or number) — the entity-level counterpart of the Archetype
 * Notes page. One rich-text note per reference source; sources are
 * managed in Settings → Reference Sources.
 */
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import RichTextViewer from '../../common/RichTextViewer';
import RichTextEditor from '../../common/RichTextEditor';
import { confirmDialog } from '../../common/ConfirmDialog';
import {
  getEntityNotes,
  setEntityNote,
  type EntityKind,
  type EntityNote,
} from '../../../api/reference';
import { getReferenceSources } from '../../../api/referenceSources';
import type { ReferenceSource } from '../../../types';
import './EntityNotes.css';

interface EntityNotesProps {
  kind: EntityKind;
  entityKey: string;
  /** What to call the entity in empty-state copy, e.g. "Leo". */
  label?: string;
}

interface DraftState {
  sourceId: number | '';
  content: string;
  /** Which note is being edited; undefined = adding a new one. */
  noteId?: number;
}

export default function EntityNotes({ kind, entityKey, label }: EntityNotesProps) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ['entity-notes', kind, entityKey],
    queryFn: () => getEntityNotes(kind, entityKey),
  });
  const notes = data?.notes ?? [];

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: () => getReferenceSources(),
    enabled: draft !== null,
  });
  // One note per source per entity: offer only sources without one
  // (except the one already being edited).
  const usedSourceIds = new Set(notes.map(n => n.source_id));
  const selectableSources = sources.filter(
    s => !usedSourceIds.has(s.id) ||
      (draft?.noteId !== undefined &&
        notes.find(n => n.id === draft.noteId)?.source_id === s.id),
  );

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ['entity-notes', kind, entityKey] });

  const save = async () => {
    if (!draft || draft.sourceId === '' || !draft.content.trim()) {
      setSaveError('Pick a source and write something first.');
      return;
    }
    try {
      await setEntityNote(kind, entityKey, draft.sourceId, draft.content);
      setDraft(null);
      setSaveError(null);
      refresh();
    } catch {
      setSaveError('Saving failed.');
    }
  };

  const remove = async (note: EntityNote) => {
    const ok = await confirmDialog({
      title: 'Remove Note',
      message: `Remove the ${note.source_name} note here? The source itself is untouched.`,
      confirmLabel: 'Remove',
    });
    if (!ok) return;
    await setEntityNote(kind, entityKey, note.source_id, '');
    refresh();
  };

  return (
    <div className="entity-notes">
      <div className="ref-detail__kicker">Source texts</div>

      {notes.length === 0 && !draft && (
        <p className="ref-detail__note">
          No source texts{label ? ` for ${label}` : ''} yet.
        </p>
      )}

      {notes.map(note => (
        draft?.noteId === note.id ? null : (
          <div key={note.id} className="entity-notes__note">
            <div className="entity-notes__note-head">
              <span className="entity-notes__source">{note.source_name}</span>
              <span className="entity-notes__actions">
                <button
                  type="button"
                  className="entity-notes__action"
                  onClick={() => {
                    setSaveError(null);
                    setDraft({
                      sourceId: note.source_id,
                      content: note.content,
                      noteId: note.id,
                    });
                  }}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="entity-notes__action"
                  onClick={() => remove(note)}
                >
                  Remove
                </button>
              </span>
            </div>
            <RichTextViewer content={note.content} />
          </div>
        )
      ))}

      {draft ? (
        <div className="entity-notes__editor">
          <label className="entity-notes__source-pick">
            <span>Source</span>
            <select
              value={draft.sourceId === '' ? '' : String(draft.sourceId)}
              disabled={draft.noteId !== undefined}
              onChange={(e) => setDraft({
                ...draft,
                sourceId: e.target.value === '' ? '' : Number(e.target.value),
              })}
            >
              <option value="">Choose a source…</option>
              {selectableSources.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </label>
          {selectableSources.length === 0 && draft.noteId === undefined && (
            <p className="ref-detail__note">
              Every source already has a note here — add more sources in
              Settings → Reference Sources.
            </p>
          )}
          <RichTextEditor
            content={draft.content}
            onChange={(html) => setDraft(d => (d ? { ...d, content: html } : d))}
            placeholder="The source's text for this entry…"
            minHeight={120}
          />
          {saveError && <p className="entity-notes__error">{saveError}</p>}
          <div className="entity-notes__editor-actions">
            <button type="button" onClick={() => { setDraft(null); setSaveError(null); }}>
              Cancel
            </button>
            <button type="button" className="primary" onClick={save}>
              Save
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className="entity-notes__add"
          onClick={() => {
            setSaveError(null);
            setDraft({ sourceId: '', content: '' });
          }}
        >
          + Add source text
        </button>
      )}
    </div>
  );
}
