/**
 * Settings → Archetype Notes.
 *
 * Archetype-first authoring page. Pick a cartomancy type, pick an
 * archetype from the sidebar, then edit per-archetype content for
 * every source that covers that type. Each source's fields become
 * a stack of labeled rich-text editors. Saves are debounced.
 *
 * Source CRUD (create / rename / delete / cartomancy types / field
 * sets) is owned by the Reference Sources page — this page is
 * read-only over sources and fields.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getReferenceSources,
  getSourceFields,
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
  SourceField,
  CartomancyType,
} from '../../../types';
import '../SettingsTab.css';
import './ArchetypeNotesSection.css';

const SUPPORTED_TYPES = [
  'Tarot', 'Lenormand', 'Playing Cards', 'Kipper', 'I Ching',
  'Playing Cards (Spanish)', 'Oracle Belline', 'Vera Sibilla Italiana / Sibilla della Zingara',
];

interface Props {
  /** Deep link from the Reference viewer's "Edit in Settings →".
   *  We open the archetype's cartomancy type and select it in the
   *  sidebar so the user lands ready to edit. */
  initialArchetypeId?: number;
  onInitialApplied?: () => void;
}

export default function ArchetypeNotesSection({
  initialArchetypeId,
  onInitialApplied,
}: Props) {
  const { data: types = [] } = useQuery<CartomancyType[]>({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });
  const supportedTypes = useMemo(
    () => types.filter(t => SUPPORTED_TYPES.includes(t.name)),
    [types],
  );

  const [cartomancyType, setCartomancyType] = useState('Tarot');

  // Apply the deep-link by resolving which type owns the archetype,
  // then switching to that type. The archetype itself is honoured
  // separately via `initialArchetypeId` passed down to the editor.
  const { data: archetypeForDeepLink } = useQuery({
    queryKey: ['archetype-for-deep-link', initialArchetypeId],
    queryFn: async () => {
      if (!initialArchetypeId) return null;
      const all = await Promise.all(
        SUPPORTED_TYPES.map(t =>
          getArchetypes(t).then(rows => ({ type: t, rows })),
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

  return (
    <div className="settings-tab__scroll archetype-notes-edit">
      <h2 className="settings-tab__title">Archetype Notes</h2>
      <p className="settings-tab__hint">
        Pick an archetype on the left to edit per-card content for every
        source that covers this cartomancy type. To add a new source, set
        which types it covers, or define new fields (e.g. "Upright Meaning"
        + "Reversed"), head to <strong>Reference Sources</strong>.
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

        <ArchetypeAuthoring
          cartomancyType={cartomancyType}
          initialArchetypeId={initialArchetypeId}
        />
      </section>
    </div>
  );
}

// =================================================================
// ArchetypeAuthoring — sidebar of archetypes + per-source editors
// =================================================================

function ArchetypeAuthoring({
  cartomancyType,
  initialArchetypeId,
}: {
  cartomancyType: string;
  initialArchetypeId?: number;
}) {
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

  // Sources that cover this type. The page is read-only over this
  // list; updates happen on the Reference Sources page.
  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources', cartomancyType],
    queryFn: () => getReferenceSources(cartomancyType),
  });

  // Set of archetype ids that have ANY content authored across any
  // source for this type — drives the sidebar dot indicator. Built
  // from the source-entries queries fanned out below.
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

  // Authored-content set: union of archetype_ids touched by any source
  // for this type. Used purely to render the sidebar dot indicator.
  const allEntries = useAllEntriesForType(sources, cartomancyType);
  const archetypeHasContent = useMemo(() => {
    const s = new Set<number>();
    for (const e of allEntries) s.add(e.archetype_id);
    return s;
  }, [allEntries]);

  if (sortedArchetypes.length === 0) {
    return (
      <p className="archetype-notes-edit__empty">
        No archetypes seeded for {cartomancyType}.
      </p>
    );
  }

  return (
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
              {archetypeHasContent.has(a.id) && (
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

      <div className="archetype-notes-edit__editor-stack">
        {activeArchetype && (
          <ArchetypeEditor
            archetype={activeArchetype}
            cartomancyType={cartomancyType}
            sources={sources}
          />
        )}
      </div>
    </div>
  );
}

// =================================================================
// ArchetypeEditor — for one (archetype), one editor stack per source
// =================================================================

function ArchetypeEditor({
  archetype,
  cartomancyType,
  sources,
}: {
  archetype: Archetype;
  cartomancyType: string;
  sources: ReferenceSource[];
}) {
  return (
    <div>
      <h4 className="archetype-notes-edit__editor-title">{archetype.name}</h4>
      {sources.length === 0 ? (
        <p className="settings-tab__hint">
          No sources cover {cartomancyType} yet. Add one over in
          {' '}<strong>Reference Sources</strong>.
        </p>
      ) : (
        sources.map(source => (
          <SourceFieldStack
            key={source.id}
            archetype={archetype}
            cartomancyType={cartomancyType}
            source={source}
          />
        ))
      )}
    </div>
  );
}

// =================================================================
// SourceFieldStack — every field this source defines for the type
// =================================================================

function SourceFieldStack({
  archetype,
  cartomancyType,
  source,
}: {
  archetype: Archetype;
  cartomancyType: string;
  source: ReferenceSource;
}) {
  const { data: fields = [] } = useQuery<SourceField[]>({
    queryKey: ['source-fields', source.id, cartomancyType],
    queryFn: () => getSourceFields(source.id, cartomancyType),
  });

  // All entries this source has for this type, used to seed the
  // editor for the active archetype's row.
  const { data: entries = [] } = useQuery<SourceAuthoringEntry[]>({
    queryKey: ['source-entries', source.id, cartomancyType],
    queryFn: () => getSourceEntries(source.id, cartomancyType),
  });
  const entryForField = useCallback(
    (fieldId: number) =>
      entries.find(
        e => e.archetype_id === archetype.id && e.field_id === fieldId,
      )?.content ?? '',
    [entries, archetype.id],
  );

  // Whether THIS archetype has any non-empty content for THIS
  // source — drives the dot indicator on the heading.
  const hasContent = useMemo(
    () =>
      entries.some(
        e =>
          e.archetype_id === archetype.id &&
          e.content &&
          e.content.replace(/<[^>]*>/g, '').trim().length > 0,
      ),
    [entries, archetype.id],
  );

  // Collapsed by default; resets to collapsed whenever the active
  // archetype changes so expansion choices on one card don't carry
  // over to the next. Same UX as the Reference viewer's Notes tab.
  const [open, setOpen] = useState(false);
  useEffect(() => {
    setOpen(false);
  }, [archetype.id]);

  return (
    <section className="archetype-notes-edit__source-detail">
      <button
        type="button"
        className="archetype-notes-edit__source-toggle"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
      >
        <span
          className={`archetype-notes-edit__chevron ${open ? 'archetype-notes-edit__chevron--open' : ''}`}
          aria-hidden="true"
        >
          ▸
        </span>
        <span className="archetype-notes-edit__source-name">
          {source.name}
        </span>
        {source.authors.length > 0 && (
          <span className="archetype-notes-edit__source-authors">
            {source.authors.join('; ')}
          </span>
        )}
        {hasContent && (
          <span
            className="archetype-notes-edit__source-dot"
            aria-label="Has content"
          >
            •
          </span>
        )}
      </button>
      {open && (
        <div className="archetype-notes-edit__source-body">
          {fields.length === 0 ? (
            <p className="settings-tab__hint">
              This source has no fields for {cartomancyType} yet. Add one
              over in <strong>Reference Sources</strong>.
            </p>
          ) : (
            fields.map(f => (
              <ArchetypeFieldEditor
                key={`${archetype.id}-${f.id}`}
                archetype={archetype}
                sourceId={source.id}
                field={f}
                initialContent={entryForField(f.id)}
              />
            ))
          )}
        </div>
      )}
    </section>
  );
}

// =================================================================
// ArchetypeFieldEditor — debounced autosave for one (archetype, field)
// cell
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
  // Re-hydrate when the active archetype or seed content changes —
  // otherwise switching cards would keep showing the prior content.
  const seededRef = useRef<{ archetypeId: number; fieldId: number }>({
    archetypeId: archetype.id,
    fieldId: field.id,
  });
  useEffect(() => {
    const last = seededRef.current;
    if (last.archetypeId !== archetype.id || last.fieldId !== field.id) {
      seededRef.current = { archetypeId: archetype.id, fieldId: field.id };
      setContent(initialContent);
      firstRunRef.current = true;
    }
  }, [archetype.id, field.id, initialContent]);

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

  // Collapsible fields render with a chevron disclosure (collapsed
  // by default). The editor stays mounted under display:none rather
  // than unmounted so the 600ms-debounced save isn't cancelled when
  // the user collapses immediately after typing.
  const isCollapsible = !!field.collapsible;
  const [open, setOpen] = useState(!isCollapsible);
  // Default-collapse again whenever the archetype changes or the
  // field flips into a collapsible flag.
  useEffect(() => {
    setOpen(!isCollapsible);
  }, [archetype.id, isCollapsible]);

  const hasContent = useMemo(
    () => content.replace(/<[^>]*>/g, '').trim().length > 0,
    [content],
  );

  if (!isCollapsible) {
    return (
      <div className="archetype-notes-edit__field-editor">
        <h6 className="archetype-notes-edit__field-editor-name">{field.name}</h6>
        <RichTextEditor content={content} onChange={setContent} />
      </div>
    );
  }
  return (
    <div className="archetype-notes-edit__field-editor archetype-notes-edit__field-editor--collapsible">
      <button
        type="button"
        className="archetype-notes-edit__field-toggle"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
      >
        <span
          className={`archetype-notes-edit__chevron ${open ? 'archetype-notes-edit__chevron--open' : ''}`}
          aria-hidden="true"
        >
          ▸
        </span>
        <span className="archetype-notes-edit__field-toggle-name">
          {field.name}
        </span>
        {hasContent && (
          <span
            className="archetype-notes-edit__source-dot"
            aria-label="Has content"
          >
            •
          </span>
        )}
      </button>
      <div
        className="archetype-notes-edit__field-editor-body"
        style={open ? undefined : { display: 'none' }}
      >
        <RichTextEditor content={content} onChange={setContent} />
      </div>
    </div>
  );
}

// =================================================================
// useAllEntriesForType — light fan-out over per-source entries to
// drive the sidebar dot indicator.
//
// Uses RQ's useQueries so each (source, type) pair is cached
// independently; this also avoids the infinite-render-loop the
// previous useEffect+fetchQuery+setState version produced (the
// `sources` array destructured with `= []` allocates a fresh
// empty array on every render, which kept invalidating effect
// deps and re-firing setState).
// =================================================================

function useAllEntriesForType(
  sources: ReferenceSource[],
  cartomancyType: string,
): SourceAuthoringEntry[] {
  const queries = useQueries({
    queries: sources.map(s => ({
      queryKey: ['source-entries', s.id, cartomancyType],
      queryFn: () => getSourceEntries(s.id, cartomancyType),
    })),
  });
  const out: SourceAuthoringEntry[] = [];
  for (const q of queries) {
    if (q.data) out.push(...q.data);
  }
  return out;
}
