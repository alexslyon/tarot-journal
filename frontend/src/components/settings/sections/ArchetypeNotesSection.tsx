/**
 * Settings → Archetype Notes (still called "Notes" by request).
 *
 * In the source-as-typed-field model:
 *   - Each reference source is scoped to a cartomancy type.
 *   - Every archetype of that type implicitly has a cell under the source.
 *   - Authoring is: pick the type, pick (or create) a source, fill in the
 *     per-archetype content cells.
 *
 * Layout:
 *   - Type picker
 *   - "Sources" list with [+ Add] and per-row Edit/Delete
 *   - "Editing: <source>" panel: form for name/type/authors + a
 *     vertical list of every archetype of the type with a rich-text
 *     content editor
 */
import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getReferenceSources,
  createReferenceSource,
  updateReferenceSource,
  deleteReferenceSource,
  getReferenceSourceDependencies,
  getSourceEntries,
  setArchetypeSourceEntry,
  getSourceFields,
  createSourceField,
  updateSourceField,
  deleteSourceField,
} from '../../../api/referenceSources';
import { getArchetypes, type Archetype } from '../../../api/correspondences';
import { getCartomancyTypes } from '../../../api/decks';
import RichTextEditor from '../../common/RichTextEditor';
import { useToast } from '../../../context/ToastContext';
import type {
  ReferenceSource,
  SourceAuthoringEntry,
  SourceField,
  CartomancyType,
} from '../../../types';
import '../SettingsTab.css';
import './ArchetypeNotesSection.css';

const SUPPORTED_TYPES = ['Tarot', 'Lenormand', 'Playing Cards', 'Kipper', 'I Ching'];

interface Props {
  /** Optional deep-link entry point. Kept for compatibility but the new
   *  page is source-centric, so we route an archetype-only deep link to
   *  the type that matches the archetype. */
  initialArchetypeId?: number;
  onInitialApplied?: () => void;
}

export default function ArchetypeNotesSection({
  initialArchetypeId,
  onInitialApplied,
}: Props) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // === Type + source pickers =================================
  const { data: types = [] } = useQuery<CartomancyType[]>({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });
  const supportedTypes = useMemo(
    () => types.filter(t => SUPPORTED_TYPES.includes(t.name)),
    [types],
  );

  const [cartomancyType, setCartomancyType] = useState('Tarot');

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources', cartomancyType],
    queryFn: () => getReferenceSources(cartomancyType),
  });

  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  // Auto-select first source on type change; clear when no sources exist.
  useEffect(() => {
    if (sources.length === 0) {
      setSelectedSourceId(null);
      return;
    }
    if (!selectedSourceId || !sources.some(s => s.id === selectedSourceId)) {
      setSelectedSourceId(sources[0].id);
    }
  }, [sources, selectedSourceId]);

  const selectedSource = sources.find(s => s.id === selectedSourceId) || null;

  // Apply deep-link: open the type that owns the archetype (we don't
  // open a specific source — the user lands and picks the source).
  const { data: archetypeForDeepLink } = useQuery({
    queryKey: ['archetype-for-deep-link', initialArchetypeId],
    queryFn: async () => {
      if (!initialArchetypeId) return null;
      const all = await Promise.all(
        SUPPORTED_TYPES.map(t =>
          getArchetypes(t).then(rows => ({ type: t, rows }))
        ),
      );
      for (const { type, rows } of all) {
        if (rows.some(a => a.id === initialArchetypeId)) return type;
      }
      return null;
    },
    enabled: initialArchetypeId != null,
  });
  useEffect(() => {
    if (archetypeForDeepLink) {
      setCartomancyType(archetypeForDeepLink);
      onInitialApplied?.();
    }
  }, [archetypeForDeepLink, onInitialApplied]);

  // === Source CRUD ===========================================

  const [newName, setNewName] = useState('');
  const handleCreate = useCallback(async () => {
    const name = newName.trim();
    if (!name) return;
    try {
      const { id } = await createReferenceSource({
        name,
        cartomancy_type: cartomancyType,
        authors: [],
      });
      setNewName('');
      await queryClient.invalidateQueries({
        queryKey: ['reference-sources', cartomancyType],
      });
      setSelectedSourceId(id);
    } catch (err) {
      console.error('Failed to create source:', err);
      showToast('Failed to create source — name may already be in use.');
    }
  }, [newName, cartomancyType, queryClient, showToast]);

  const handleDelete = useCallback(async (source: ReferenceSource) => {
    const deps = await getReferenceSourceDependencies(source.id);
    const warningParts: string[] = [];
    if (deps.archetype_source_entries > 0) {
      warningParts.push(
        `${deps.archetype_source_entries} per-card entr${deps.archetype_source_entries === 1 ? 'y' : 'ies'} will be deleted along with it`,
      );
    }
    if (deps.lenormand_meanings > 0) {
      warningParts.push(
        `${deps.lenormand_meanings} Lenormand combination meaning${deps.lenormand_meanings === 1 ? '' : 's'} will lose attribution`,
      );
    }
    const warning = warningParts.length
      ? `${warningParts.join(', ')}.\n\n`
      : '';
    if (!window.confirm(`Delete "${source.name}"?\n\n${warning}This cannot be undone.`)) {
      return;
    }
    try {
      await deleteReferenceSource(source.id);
      await queryClient.invalidateQueries({
        queryKey: ['reference-sources', cartomancyType],
      });
      setSelectedSourceId(null);
    } catch (err) {
      console.error('Failed to delete source:', err);
      showToast('Failed to delete source.');
    }
  }, [cartomancyType, queryClient, showToast]);

  return (
    <div className="settings-tab__scroll archetype-notes-edit">
      <h2 className="settings-tab__title">Archetype Notes</h2>
      <p className="settings-tab__hint">
        Each reference source is scoped to a cartomancy type and lets you
        author per-card content (book commentary, your own readings, etc).
        Cards without content for a source don't appear in that source's
        column on the Reference viewer.
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
        </div>

        <h3 className="archetype-notes-edit__heading">Sources</h3>
        <div className="archetype-notes-edit__source-list">
          {sources.length === 0 ? (
            <p className="archetype-notes-edit__empty">
              No sources yet for {cartomancyType}.
            </p>
          ) : (
            <ul className="archetype-notes-edit__sources">
              {sources.map(s => (
                <li
                  key={s.id}
                  className={`archetype-notes-edit__source ${
                    s.id === selectedSourceId
                      ? 'archetype-notes-edit__source--active'
                      : ''
                  }`}
                >
                  <button
                    type="button"
                    className="archetype-notes-edit__source-pick"
                    onClick={() => setSelectedSourceId(s.id)}
                  >
                    <span className="archetype-notes-edit__source-name">
                      {s.name}
                    </span>
                    {s.authors.length > 0 && (
                      <span className="archetype-notes-edit__source-authors">
                        {s.authors.join('; ')}
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    className="archetype-notes-edit__source-delete"
                    onClick={() => handleDelete(s)}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="archetype-notes-edit__new-source">
            <input
              type="text"
              value={newName}
              placeholder={`New ${cartomancyType} source name…`}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleCreate(); }}
            />
            <button type="button" onClick={handleCreate} disabled={!newName.trim()}>
              + Add
            </button>
          </div>
        </div>
      </section>

      {selectedSource && (
        <SourceEditor
          source={selectedSource}
          cartomancyType={cartomancyType}
          initialArchetypeId={initialArchetypeId}
        />
      )}
    </div>
  );
}

// =================================================================
// SourceEditor — name/type/authors form + per-archetype content list
// =================================================================

function SourceEditor({
  source,
  cartomancyType,
  initialArchetypeId,
}: {
  source: ReferenceSource;
  cartomancyType: string;
  initialArchetypeId?: number;
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // Hydrate form state from the source row each time the selected
  // source changes; debounced autosave on change.
  const [name, setName] = useState(source.name);
  const [authorsText, setAuthorsText] = useState(source.authors.join(', '));
  const sourceIdRef = useRef(source.id);
  useEffect(() => {
    sourceIdRef.current = source.id;
    setName(source.name);
    setAuthorsText(source.authors.join(', '));
    firstSaveSkipRef.current = true;
  }, [source.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Skip the autosave fire that the hydration above triggers.
  const firstSaveSkipRef = useRef(true);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (firstSaveSkipRef.current) {
      firstSaveSkipRef.current = false;
      return;
    }
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(async () => {
      const trimmedName = name.trim();
      if (!trimmedName) return;
      const authors = authorsText
        .split(/[,;\n]/)
        .map(s => s.trim())
        .filter(Boolean);
      try {
        await updateReferenceSource(sourceIdRef.current, {
          name: trimmedName,
          authors,
        });
        queryClient.invalidateQueries({
          queryKey: ['reference-sources', cartomancyType],
        });
      } catch (err) {
        console.error('Failed to save source metadata:', err);
        showToast('Failed to save source.');
      }
    }, 500);
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [name, authorsText, cartomancyType, queryClient, showToast]);

  // === Per-archetype entries ================================
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

  // Fields the source defines (e.g. Upright, Reversed, Symbolism)
  const { data: fields = [] } = useQuery<SourceField[]>({
    queryKey: ['source-fields', source.id],
    queryFn: () => getSourceFields(source.id),
  });

  // Existing entries across all (archetype, field) cells under this
  // source. Used both to flag archetypes that have any content (the
  // sidebar dot) and to seed the per-field editors.
  const { data: entries = [] } = useQuery<SourceAuthoringEntry[]>({
    queryKey: ['source-entries', source.id],
    queryFn: () => getSourceEntries(source.id),
  });
  const entriesByArchetype = useMemo(() => {
    // archetype_id -> field_id -> content
    const m = new Map<number, Map<number, string>>();
    for (const e of entries) {
      let inner = m.get(e.archetype_id);
      if (!inner) {
        inner = new Map();
        m.set(e.archetype_id, inner);
      }
      inner.set(e.field_id, e.content);
    }
    return m;
  }, [entries]);

  const [activeArchetypeId, setActiveArchetypeId] = useState<number | null>(null);
  useEffect(() => {
    if (sortedArchetypes.length === 0) {
      setActiveArchetypeId(null);
      return;
    }
    if (
      initialArchetypeId &&
      sortedArchetypes.some(a => a.id === initialArchetypeId)
    ) {
      setActiveArchetypeId(initialArchetypeId);
      return;
    }
    if (
      !activeArchetypeId ||
      !sortedArchetypes.some(a => a.id === activeArchetypeId)
    ) {
      setActiveArchetypeId(sortedArchetypes[0].id);
    }
  }, [sortedArchetypes, initialArchetypeId, activeArchetypeId]);

  const activeArchetype = sortedArchetypes.find(a => a.id === activeArchetypeId);
  const activeArchetypeEntries = activeArchetype
    ? entriesByArchetype.get(activeArchetype.id) ?? new Map<number, string>()
    : new Map<number, string>();

  return (
    <section className="settings-tab__section archetype-notes-edit__source-detail">
      <h3 className="archetype-notes-edit__heading">
        Editing: {source.name}
      </h3>

      <div className="archetype-notes-edit__source-meta">
        <div className="archetype-notes-edit__field">
          <label className="settings-tab__label">Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
          />
        </div>
        <div className="archetype-notes-edit__field">
          <label className="settings-tab__label">Authors</label>
          <input
            type="text"
            value={authorsText}
            placeholder="e.g. Rachel Pollack, Mary K. Greer"
            onChange={e => setAuthorsText(e.target.value)}
          />
          <p className="settings-tab__hint">
            Comma- or semicolon-separated. Order is preserved.
          </p>
        </div>
        <div className="archetype-notes-edit__field">
          <label className="settings-tab__label">Cartomancy Type</label>
          <input type="text" value={source.cartomancy_type} disabled />
          <p className="settings-tab__hint">
            Locked after creation — delete + recreate to move a source between
            types.
          </p>
        </div>
      </div>

      <FieldsManager source={source} fields={fields} />

      <h3 className="archetype-notes-edit__heading">Per-card content</h3>
      {fields.length === 0 ? (
        <p className="settings-tab__hint">
          Add at least one field above to start authoring per-card content.
        </p>
      ) : (
        <div className="archetype-notes-edit__archetype-grid">
          <ul className="archetype-notes-edit__archetype-list">
            {sortedArchetypes.map(a => (
              <li key={a.id}>
                <button
                  type="button"
                  className={`archetype-notes-edit__archetype-pick ${
                    a.id === activeArchetypeId
                      ? 'archetype-notes-edit__archetype-pick--active'
                      : ''
                  }`}
                  onClick={() => setActiveArchetypeId(a.id)}
                >
                  <span>{a.name}</span>
                  {entriesByArchetype.has(a.id) && (
                    <span
                      className="archetype-notes-edit__archetype-dot"
                      aria-label="Has content"
                    >
                      •
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>

          {activeArchetype && (
            <div className="archetype-notes-edit__editor-stack">
              <h4 className="archetype-notes-edit__editor-title">
                {activeArchetype.name}
              </h4>
              {fields.map(f => (
                <ArchetypeFieldEditor
                  key={`${activeArchetype.id}-${f.id}`}
                  archetype={activeArchetype}
                  sourceId={source.id}
                  field={f}
                  initialContent={activeArchetypeEntries.get(f.id) ?? ''}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// =================================================================
// FieldsManager — add / rename / delete fields on a source
// =================================================================

function FieldsManager({
  source,
  fields,
}: {
  source: ReferenceSource;
  fields: SourceField[];
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [newName, setNewName] = useState('');

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['source-fields', source.id] });
    queryClient.invalidateQueries({ queryKey: ['source-entries', source.id] });
    // Archetype-side viewer queries also need refresh in case a field
    // rename or delete changes what shows up there.
    queryClient.invalidateQueries({ queryKey: ['archetype-source-entries'] });
  }, [queryClient, source.id]);

  const handleAdd = useCallback(async () => {
    const name = newName.trim();
    if (!name) return;
    try {
      await createSourceField(source.id, name);
      setNewName('');
      invalidate();
    } catch (err) {
      console.error('Failed to create field:', err);
      showToast('Could not add field (name may already be used on this source).');
    }
  }, [newName, source.id, invalidate, showToast]);

  const handleDelete = useCallback(
    async (field: SourceField) => {
      if (
        !window.confirm(
          `Delete the "${field.name}" field?\n\n` +
            `All content authored under this field across every card will be removed. This cannot be undone.`,
        )
      ) {
        return;
      }
      try {
        await deleteSourceField(field.id);
        invalidate();
      } catch (err) {
        console.error('Failed to delete field:', err);
        showToast('Failed to delete field.');
      }
    },
    [invalidate, showToast],
  );

  return (
    <div className="archetype-notes-edit__fields-manager">
      <h3 className="archetype-notes-edit__heading">Fields</h3>
      <p className="settings-tab__hint">
        Define which slots each card under this source should have
        (e.g. "Upright Meaning", "Reversed", "Symbolism"). Cards with
        empty content for a field don't appear in that field's column
        on the Reference viewer.
      </p>

      {fields.length === 0 ? (
        <p className="archetype-notes-edit__empty">No fields yet.</p>
      ) : (
        <ul className="archetype-notes-edit__fields-list">
          {fields.map(f => (
            <FieldRow key={f.id} field={f} onChanged={invalidate} onDelete={handleDelete} />
          ))}
        </ul>
      )}

      <div className="archetype-notes-edit__new-source">
        <input
          type="text"
          value={newName}
          placeholder="New field name (e.g. Upright Meaning)…"
          onChange={e => setNewName(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleAdd(); }}
        />
        <button type="button" onClick={handleAdd} disabled={!newName.trim()}>
          + Add Field
        </button>
      </div>
    </div>
  );
}

function FieldRow({
  field,
  onChanged,
  onDelete,
}: {
  field: SourceField;
  onChanged: () => void;
  onDelete: (f: SourceField) => void;
}) {
  const { showToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(field.name);
  useEffect(() => { setDraft(field.name); }, [field.name]);

  const save = useCallback(async () => {
    const name = draft.trim();
    if (!name || name === field.name) {
      setEditing(false);
      setDraft(field.name);
      return;
    }
    try {
      await updateSourceField(field.id, { name });
      setEditing(false);
      onChanged();
    } catch (err) {
      console.error('Failed to rename field:', err);
      showToast('Could not rename field.');
    }
  }, [draft, field.id, field.name, onChanged, showToast]);

  return (
    <li className="archetype-notes-edit__field-row">
      {editing ? (
        <>
          <input
            type="text"
            autoFocus
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') save();
              if (e.key === 'Escape') { setDraft(field.name); setEditing(false); }
            }}
          />
          <button type="button" onClick={save}>Save</button>
          <button
            type="button"
            onClick={() => { setDraft(field.name); setEditing(false); }}
          >
            Cancel
          </button>
        </>
      ) : (
        <>
          <span className="archetype-notes-edit__field-row-name">{field.name}</span>
          <button type="button" onClick={() => setEditing(true)}>Rename</button>
          <button
            type="button"
            className="archetype-notes-edit__source-delete"
            onClick={() => onDelete(field)}
          >
            Delete
          </button>
        </>
      )}
    </li>
  );
}

// =================================================================
// ArchetypeFieldEditor — debounced autosave for one (archetype, field)
// cell. One of these per field is stacked under the active archetype.
// =================================================================

function ArchetypeFieldEditor({
  archetype,
  sourceId,
  field,
  initialContent,
}: {
  archetype: Archetype;
  sourceId: number;
  field: SourceField;
  initialContent: string;
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [content, setContent] = useState(initialContent);
  const firstRunRef = useRef(true);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (firstRunRef.current) {
      firstRunRef.current = false;
      return;
    }
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(async () => {
      try {
        await setArchetypeSourceEntry(archetype.id, field.id, content);
        queryClient.invalidateQueries({
          queryKey: ['source-entries', sourceId],
        });
        queryClient.invalidateQueries({
          queryKey: ['archetype-source-entries', archetype.id],
        });
      } catch (err) {
        console.error('Failed to save entry:', err);
        showToast('Failed to save entry.');
      }
    }, 600);
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [content, archetype.id, field.id, sourceId, queryClient, showToast]);

  return (
    <div className="archetype-notes-edit__field-editor">
      <h5 className="archetype-notes-edit__field-editor-name">{field.name}</h5>
      <RichTextEditor content={content} onChange={setContent} />
    </div>
  );
}
