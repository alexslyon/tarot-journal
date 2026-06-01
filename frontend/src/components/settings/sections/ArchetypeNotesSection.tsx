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
} from '../../../api/referenceSources';
import { getArchetypes, type Archetype } from '../../../api/correspondences';
import { getCartomancyTypes } from '../../../api/decks';
import RichTextEditor from '../../common/RichTextEditor';
import { useToast } from '../../../context/ToastContext';
import type {
  ReferenceSource,
  SourceAuthoringEntry,
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

  const { data: entries = [] } = useQuery<SourceAuthoringEntry[]>({
    queryKey: ['source-entries', source.id],
    queryFn: () => getSourceEntries(source.id),
  });
  const entryByArchetype = useMemo(() => {
    const m = new Map<number, string>();
    for (const e of entries) m.set(e.archetype_id, e.content);
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
  const draftSeed = activeArchetype ? entryByArchetype.get(activeArchetype.id) ?? '' : '';

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

      <h3 className="archetype-notes-edit__heading">Per-card content</h3>
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
                {entryByArchetype.has(a.id) && (
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
          <ArchetypeContentEditor
            key={`${source.id}-${activeArchetype.id}`}
            archetype={activeArchetype}
            sourceId={source.id}
            initialContent={draftSeed}
          />
        )}
      </div>
    </section>
  );
}

// =================================================================
// ArchetypeContentEditor — debounced autosave for one cell
// =================================================================

function ArchetypeContentEditor({
  archetype,
  sourceId,
  initialContent,
}: {
  archetype: Archetype;
  sourceId: number;
  initialContent: string;
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [content, setContent] = useState(initialContent);
  // Skip the autosave that the hydration triggers.
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
        await setArchetypeSourceEntry(archetype.id, sourceId, content);
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
  }, [content, archetype.id, sourceId, queryClient, showToast]);

  return (
    <div className="archetype-notes-edit__editor">
      <h4 className="archetype-notes-edit__editor-title">{archetype.name}</h4>
      <RichTextEditor content={content} onChange={setContent} />
      <p className="settings-tab__hint">
        Leave blank to remove this card from the source's column.
      </p>
    </div>
  );
}
