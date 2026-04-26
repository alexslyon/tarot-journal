import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getReferenceSources,
  createReferenceSource,
  updateReferenceSource,
  deleteReferenceSource,
  getReferenceSourceDependencies,
} from '../../../api/referenceSources';
import { useToast } from '../../../context/ToastContext';
import type { ReferenceSource } from '../../../types';
import '../SettingsTab.css';
import './ReferenceSourcesSection.css';

export default function ReferenceSourcesSection() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: getReferenceSources,
  });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['reference-sources'] });
    queryClient.invalidateQueries({ queryKey: ['lenormand-meanings'] });
    queryClient.invalidateQueries({ queryKey: ['archetype-notes'] });
    queryClient.invalidateQueries({ queryKey: ['archetype-note-entries'] });
  };

  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<ReferenceSource | null>(null);

  const handleAdd = async () => {
    if (!newName.trim()) return;
    try {
      await createReferenceSource(newName.trim());
      setNewName('');
      setAdding(false);
      invalidate();
    } catch {
      showToast('Could not add source (name may already exist).');
    }
  };

  const handleSaveEdit = async () => {
    if (editingId == null || !editingName.trim()) return;
    try {
      await updateReferenceSource(editingId, editingName.trim());
      setEditingId(null);
      setEditingName('');
      invalidate();
    } catch {
      showToast('Could not rename source.');
    }
  };

  return (
    <div className="settings-tab__scroll reference-sources">
      <h2 className="settings-tab__title">Reference Sources</h2>
      <p className="settings-tab__hint">
        Shared sources used across Lenormand combinations and Archetype notes.
        A source can be a book, website, your own notes — anything you want to
        cite when entering reference material.
      </p>

      <section className="settings-tab__section">
        {sources.length === 0 && !adding && (
          <p className="reference-sources__empty">No sources yet.</p>
        )}

        <ul className="reference-sources__list">
          {sources.map(s => (
            <li key={s.id} className="reference-sources__row">
              {editingId === s.id ? (
                <>
                  <input
                    autoFocus
                    value={editingName}
                    onChange={e => setEditingName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSaveEdit()}
                    className="reference-sources__input"
                  />
                  <button onClick={handleSaveEdit}>Save</button>
                  <button onClick={() => { setEditingId(null); setEditingName(''); }}>Cancel</button>
                </>
              ) : (
                <>
                  <span className="reference-sources__name">{s.name}</span>
                  <button onClick={() => { setEditingId(s.id); setEditingName(s.name); }}>
                    Rename
                  </button>
                  <button className="danger" onClick={() => setDeleteTarget(s)}>
                    Delete
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>

        {adding ? (
          <div className="reference-sources__add">
            <input
              autoFocus
              placeholder="Source name"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAdd()}
              className="reference-sources__input"
            />
            <button onClick={handleAdd} disabled={!newName.trim()}>Add</button>
            <button onClick={() => { setAdding(false); setNewName(''); }}>Cancel</button>
          </div>
        ) : (
          <button onClick={() => setAdding(true)} className="reference-sources__add-btn">
            + Add Source
          </button>
        )}
      </section>

      {deleteTarget && (
        <DeleteDialog
          source={deleteTarget}
          otherSources={sources.filter(s => s.id !== deleteTarget.id)}
          onClose={() => setDeleteTarget(null)}
          onDeleted={() => {
            setDeleteTarget(null);
            invalidate();
          }}
          showToast={showToast}
        />
      )}
    </div>
  );
}

function DeleteDialog({
  source,
  otherSources,
  onClose,
  onDeleted,
  showToast,
}: {
  source: ReferenceSource;
  otherSources: ReferenceSource[];
  onClose: () => void;
  onDeleted: () => void;
  showToast: (msg: string) => void;
}) {
  const { data: deps = { lenormand_meanings: 0, archetype_notes_entries: 0 } } =
    useQuery({
      queryKey: ['reference-source-deps', source.id],
      queryFn: () => getReferenceSourceDependencies(source.id),
    });
  const total = deps.lenormand_meanings + deps.archetype_notes_entries;

  const [reassignTo, setReassignTo] = useState<'unsource' | number>('unsource');

  const handleDelete = async () => {
    try {
      await deleteReferenceSource(
        source.id,
        reassignTo === 'unsource' ? undefined : reassignTo,
      );
      onDeleted();
    } catch {
      showToast('Could not delete source.');
    }
  };

  return (
    <div className="reference-sources__dialog-backdrop" onClick={onClose}>
      <div
        className="reference-sources__dialog"
        onClick={e => e.stopPropagation()}
      >
        <h4>Delete source "{source.name}"?</h4>
        {total === 0 ? (
          <p>No entries reference this source. Deletion is safe.</p>
        ) : (
          <>
            <p>
              {total} entr{total === 1 ? 'y references' : 'ies reference'} this source
              {deps.lenormand_meanings > 0 && (
                <> ({deps.lenormand_meanings} Lenormand meaning{deps.lenormand_meanings === 1 ? '' : 's'}</>
              )}
              {deps.lenormand_meanings > 0 && deps.archetype_notes_entries > 0 && ', '}
              {deps.archetype_notes_entries > 0 && (
                <>{deps.archetype_notes_entries} archetype note{deps.archetype_notes_entries === 1 ? '' : 's'}</>
              )}
              {(deps.lenormand_meanings > 0 || deps.archetype_notes_entries > 0) && ')'}.
              The entries themselves will not be deleted — pick what should
              happen to their source label:
            </p>
            <label className="reference-sources__dialog-option">
              <input
                type="radio"
                name="reassign"
                checked={reassignTo === 'unsource'}
                onChange={() => setReassignTo('unsource')}
              />
              Make those entries unsourced
            </label>
            {otherSources.map(s => (
              <label key={s.id} className="reference-sources__dialog-option">
                <input
                  type="radio"
                  name="reassign"
                  checked={reassignTo === s.id}
                  onChange={() => setReassignTo(s.id)}
                />
                Reassign to "{s.name}"
              </label>
            ))}
          </>
        )}
        <div className="reference-sources__dialog-actions">
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleDelete} className="danger">Delete</button>
        </div>
      </div>
    </div>
  );
}
