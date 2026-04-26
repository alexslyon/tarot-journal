import { useState, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getArchetypeLanguages,
  createArchetypeLanguage,
  updateArchetypeLanguage,
  deleteArchetypeLanguage,
  reorderArchetypeLanguages,
  getArchetypeLanguageDependencyCount,
  getArchetypeNames,
  createArchetypeName,
  updateArchetypeName,
  deleteArchetypeName,
  reorderArchetypeNames,
} from '../../../api/archetypeLanguages';
import { getArchetypes, type Archetype } from '../../../api/correspondences';
import { getCartomancyTypes } from '../../../api/decks';
import { useToast } from '../../../context/ToastContext';
import type {
  ArchetypeLanguage,
  ArchetypeLanguageName,
  CartomancyType,
} from '../../../types';
import '../SettingsTab.css';
import './ArchetypeLanguagesSection.css';

const SUPPORTED_TYPES = ['Tarot'];

interface Props {
  initialArchetypeId?: number;
  onInitialApplied?: () => void;
}

export default function ArchetypeLanguagesSection({
  initialArchetypeId,
  onInitialApplied,
}: Props) {
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  // === Cartomancy + archetype pickers ===
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
  useEffect(() => {
    if (initialArchetypeId) {
      setArchetypeId(initialArchetypeId);
      onInitialApplied?.();
    }
  }, [initialArchetypeId, onInitialApplied]);

  // === Languages list ===
  const { data: languages = [] } = useQuery<ArchetypeLanguage[]>({
    queryKey: ['archetype-languages'],
    queryFn: getArchetypeLanguages,
  });
  const invalidateLanguages = () => {
    queryClient.invalidateQueries({ queryKey: ['archetype-languages'] });
    queryClient.invalidateQueries({ queryKey: ['archetype-language-names'] });
    queryClient.invalidateQueries({ queryKey: ['archetype-language-names-by-type'] });
  };

  return (
    <div className="settings-tab__scroll archetype-langs-edit">
      <h2 className="settings-tab__title">Archetype Languages</h2>
      <p className="settings-tab__hint">
        Manage your language list and per-card translations. Drag languages to
        change their column order in Reference table mode.
      </p>

      <LanguageList
        languages={languages}
        invalidate={invalidateLanguages}
        showToast={showToast}
      />

      <section className="settings-tab__section">
        <h3 className="settings-tab__section-title">Names</h3>

        <div className="archetype-langs-edit__pickers">
          <div className="archetype-langs-edit__picker">
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
          <div className="archetype-langs-edit__picker">
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

        {archetypeId != null && languages.length > 0 && (
          <NamesEditor
            archetypeId={archetypeId}
            languages={languages}
            showToast={showToast}
          />
        )}
        {languages.length === 0 && (
          <p className="archetype-langs-edit__empty">
            Add a language above to start entering card names.
          </p>
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Languages list (top of the page)
// ---------------------------------------------------------------------------

function LanguageList({
  languages,
  invalidate,
  showToast,
}: {
  languages: ArchetypeLanguage[];
  invalidate: () => void;
  showToast: (msg: string) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);

  const handleAdd = async () => {
    if (!newName.trim()) return;
    try {
      await createArchetypeLanguage(newName.trim());
      setNewName('');
      setAdding(false);
      invalidate();
    } catch {
      showToast('Could not add language (name may already exist).');
    }
  };

  const handleSaveEdit = async () => {
    if (editingId == null || !editingName.trim()) return;
    try {
      await updateArchetypeLanguage(editingId, editingName.trim());
      setEditingId(null);
      setEditingName('');
      invalidate();
    } catch {
      showToast('Could not rename language.');
    }
  };

  const handleDelete = async (lang: ArchetypeLanguage) => {
    try {
      const { count } = await getArchetypeLanguageDependencyCount(lang.id);
      const msg = count > 0
        ? `Delete "${lang.name}" and ${count} associated name${count === 1 ? '' : 's'}?`
        : `Delete "${lang.name}"?`;
      if (!window.confirm(msg)) return;
      await deleteArchetypeLanguage(lang.id);
      invalidate();
    } catch {
      showToast('Could not delete language.');
    }
  };

  const handleDrop = async (targetId: number) => {
    if (draggedId == null || draggedId === targetId) {
      setDraggedId(null); setDragOverId(null); return;
    }
    const ids = languages.map(l => l.id);
    const fromIdx = ids.indexOf(draggedId);
    const toIdx = ids.indexOf(targetId);
    if (fromIdx === -1 || toIdx === -1) {
      setDraggedId(null); setDragOverId(null); return;
    }
    ids.splice(fromIdx, 1);
    ids.splice(toIdx, 0, draggedId);
    try {
      await reorderArchetypeLanguages(ids);
      invalidate();
    } catch {
      showToast('Could not reorder languages.');
    }
    setDraggedId(null); setDragOverId(null);
  };

  return (
    <section className="settings-tab__section">
      <h3 className="settings-tab__section-title">Languages</h3>

      {languages.length === 0 && !adding && (
        <p className="archetype-langs-edit__empty">No languages yet.</p>
      )}

      <ul className="archetype-langs-edit__lang-list">
        {languages.map(l => {
          const rowClass = [
            'archetype-langs-edit__lang-row',
            draggedId === l.id ? 'archetype-langs-edit__lang-row--dragging' : '',
            dragOverId === l.id ? 'archetype-langs-edit__lang-row--drag-over' : '',
          ].filter(Boolean).join(' ');
          return (
            <li
              key={l.id}
              className={rowClass}
              draggable={editingId !== l.id}
              onDragStart={() => setDraggedId(l.id)}
              onDragOver={e => {
                if (draggedId == null || draggedId === l.id) return;
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                if (dragOverId !== l.id) setDragOverId(l.id);
              }}
              onDrop={e => { e.preventDefault(); handleDrop(l.id); }}
              onDragEnd={() => { setDraggedId(null); setDragOverId(null); }}
            >
              <span className="archetype-langs-edit__drag" title="Drag to reorder">⋮⋮</span>
              {editingId === l.id ? (
                <>
                  <input
                    autoFocus
                    value={editingName}
                    onChange={e => setEditingName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSaveEdit()}
                    className="archetype-langs-edit__lang-input"
                  />
                  <button onClick={handleSaveEdit}>Save</button>
                  <button onClick={() => { setEditingId(null); setEditingName(''); }}>Cancel</button>
                </>
              ) : (
                <>
                  <span className="archetype-langs-edit__lang-name">{l.name}</span>
                  <button onClick={() => { setEditingId(l.id); setEditingName(l.name); }}>
                    Rename
                  </button>
                  <button className="danger" onClick={() => handleDelete(l)}>Delete</button>
                </>
              )}
            </li>
          );
        })}
      </ul>

      {adding ? (
        <div className="archetype-langs-edit__add-form">
          <input
            autoFocus
            placeholder="Language name (e.g. 'French', 'Japanese')"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            className="archetype-langs-edit__lang-input"
          />
          <button onClick={handleAdd} disabled={!newName.trim()}>Add</button>
          <button onClick={() => { setAdding(false); setNewName(''); }}>Cancel</button>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} className="archetype-langs-edit__add-btn">
          + Add Language
        </button>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Names editor — for the selected card, grouped by language
// ---------------------------------------------------------------------------

function NamesEditor({
  archetypeId,
  languages,
  showToast,
}: {
  archetypeId: number;
  languages: ArchetypeLanguage[];
  showToast: (msg: string) => void;
}) {
  const queryClient = useQueryClient();
  const namesKey = ['archetype-language-names', archetypeId];
  const { data: names = [] } = useQuery<ArchetypeLanguageName[]>({
    queryKey: namesKey,
    queryFn: () => getArchetypeNames(archetypeId),
  });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: namesKey });
    queryClient.invalidateQueries({ queryKey: ['archetype-language-names-by-type'] });
  };

  // Group names by language id
  const byLang = useMemo(() => {
    const m = new Map<number, ArchetypeLanguageName[]>();
    for (const n of names) {
      if (!m.has(n.language_id)) m.set(n.language_id, []);
      m.get(n.language_id)!.push(n);
    }
    return m;
  }, [names]);

  return (
    <div className="archetype-langs-edit__names">
      {languages.map(lang => (
        <LangGroupEditor
          key={lang.id}
          archetypeId={archetypeId}
          language={lang}
          names={byLang.get(lang.id) || []}
          invalidate={invalidate}
          showToast={showToast}
        />
      ))}
    </div>
  );
}

function LangGroupEditor({
  archetypeId,
  language,
  names,
  invalidate,
  showToast,
}: {
  archetypeId: number;
  language: ArchetypeLanguage;
  names: ArchetypeLanguageName[];
  invalidate: () => void;
  showToast: (msg: string) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [draftName, setDraftName] = useState('');
  const [draftRomanization, setDraftRomanization] = useState('');
  const [draftIpa, setDraftIpa] = useState('');

  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);
  const handleDrop = async (targetId: number) => {
    if (draggedId == null || draggedId === targetId) {
      setDraggedId(null); setDragOverId(null); return;
    }
    const ids = names.map(n => n.id);
    const fromIdx = ids.indexOf(draggedId);
    const toIdx = ids.indexOf(targetId);
    if (fromIdx === -1 || toIdx === -1) {
      setDraggedId(null); setDragOverId(null); return;
    }
    ids.splice(fromIdx, 1);
    ids.splice(toIdx, 0, draggedId);
    try {
      await reorderArchetypeNames(archetypeId, language.id, ids);
      invalidate();
    } catch {
      showToast('Could not reorder names.');
    }
    setDraggedId(null); setDragOverId(null);
  };

  const handleAdd = async () => {
    if (!draftName.trim()) return;
    try {
      await createArchetypeName(
        archetypeId,
        language.id,
        draftName.trim(),
        draftRomanization.trim() || null,
        draftIpa.trim() || null,
      );
      setDraftName('');
      setDraftRomanization('');
      setDraftIpa('');
      setAdding(false);
      invalidate();
    } catch {
      showToast('Could not add name.');
    }
  };

  return (
    <section className="archetype-langs-edit__lang-group">
      <h4 className="archetype-langs-edit__lang-group-name">{language.name}</h4>

      {names.length === 0 && !adding && (
        <p className="archetype-langs-edit__empty">No entries yet for this language.</p>
      )}

      <ul className="archetype-langs-edit__name-list">
        {names.map(n => (
          <NameRow
            key={n.id}
            entry={n}
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
        <div className="archetype-langs-edit__name-add">
          <input
            autoFocus
            placeholder="Name in this language"
            value={draftName}
            onChange={e => setDraftName(e.target.value)}
          />
          <input
            placeholder="Romanization (optional)"
            value={draftRomanization}
            onChange={e => setDraftRomanization(e.target.value)}
          />
          <input
            placeholder="IPA (optional)"
            value={draftIpa}
            onChange={e => setDraftIpa(e.target.value)}
          />
          <div className="archetype-langs-edit__name-add-actions">
            <button onClick={() => { setAdding(false); setDraftName(''); setDraftRomanization(''); setDraftIpa(''); }}>
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!draftName.trim()}
              className="archetype-langs-edit__save-btn"
            >
              Add
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="archetype-langs-edit__add-name-btn"
        >
          + Add Name
        </button>
      )}
    </section>
  );
}

function NameRow({
  entry,
  invalidate,
  showToast,
  draggedId,
  dragOverId,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: {
  entry: ArchetypeLanguageName;
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
  const [draftName, setDraftName] = useState(entry.name);
  const [draftRomanization, setDraftRomanization] = useState(entry.romanization || '');
  const [draftIpa, setDraftIpa] = useState(entry.ipa || '');

  useEffect(() => {
    if (!editing) {
      setDraftName(entry.name);
      setDraftRomanization(entry.romanization || '');
      setDraftIpa(entry.ipa || '');
    }
  }, [entry.name, entry.romanization, entry.ipa, editing]);

  const handleSave = async () => {
    try {
      await updateArchetypeName(entry.id, {
        name: draftName.trim(),
        romanization: draftRomanization.trim() || null,
        ipa: draftIpa.trim() || null,
      });
      setEditing(false);
      invalidate();
    } catch {
      showToast('Could not update name.');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this name?')) return;
    try {
      await deleteArchetypeName(entry.id);
      invalidate();
    } catch {
      showToast('Could not delete name.');
    }
  };

  const rowClass = [
    'archetype-langs-edit__name-row',
    draggedId === entry.id ? 'archetype-langs-edit__name-row--dragging' : '',
    dragOverId === entry.id ? 'archetype-langs-edit__name-row--drag-over' : '',
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
      <span className="archetype-langs-edit__drag" title="Drag to reorder">⋮⋮</span>
      {editing ? (
        <div className="archetype-langs-edit__name-edit">
          <input
            value={draftName}
            onChange={e => setDraftName(e.target.value)}
            placeholder="Name"
          />
          <input
            value={draftRomanization}
            onChange={e => setDraftRomanization(e.target.value)}
            placeholder="Romanization (optional)"
          />
          <input
            value={draftIpa}
            onChange={e => setDraftIpa(e.target.value)}
            placeholder="IPA (optional)"
          />
          <div className="archetype-langs-edit__name-add-actions">
            <button onClick={() => setEditing(false)}>Cancel</button>
            <button onClick={handleSave} className="archetype-langs-edit__save-btn">Save</button>
          </div>
        </div>
      ) : (
        <div className="archetype-langs-edit__name-view">
          <span className="archetype-langs-edit__name-text">{entry.name}</span>
          {(entry.romanization || entry.ipa) && (
            <span className="archetype-langs-edit__name-meta">
              {entry.romanization && <em>{entry.romanization}</em>}
              {entry.ipa && <span className="archetype-langs-edit__name-ipa">/{entry.ipa}/</span>}
            </span>
          )}
          <div className="archetype-langs-edit__name-actions">
            <button onClick={() => setEditing(true)}>Edit</button>
            <button className="danger" onClick={handleDelete}>Delete</button>
          </div>
        </div>
      )}
    </li>
  );
}
