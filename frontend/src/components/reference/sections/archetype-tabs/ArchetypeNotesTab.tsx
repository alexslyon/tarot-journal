import { useMemo, useState } from 'react';
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getArchetypeSourceEntries,
  getReferenceSources,
  getSourceFields,
  setArchetypeSourceEntry,
} from '../../../../api/referenceSources';
import RichTextViewer from '../../../common/RichTextViewer';
import RichTextEditor from '../../../common/RichTextEditor';
import { ensureHtml } from '../../../../utils/formatting';
import { useToast } from '../../../../context/ToastContext';
import ArchetypeCardImage from './ArchetypeCardImage';
import type { Archetype } from '../../../../api/correspondences';
import type { ArchetypeSourceEntry, ReferenceSource, SourceField } from '../../../../types';
import './ArchetypeNotesTab.css';

interface Props {
  archetype: Archetype;
  cartomancyType: string;
  onNavigateToSettings?: (
    section: string,
    payload?: { archetypeId?: number; sourceId?: number; fieldId?: number },
  ) => void;
}

/**
 * One section per source that has any populated field for this card.
 * Inside each section, one row per non-empty field. Both layers obey
 * the "absent or empty → hidden" rule — until Edit mode, which shows
 * EVERY source covering this type and every field (empty included),
 * so authoring happens right here instead of in Settings.
 */
export default function ArchetypeNotesTab({
  archetype,
  cartomancyType,
}: Props) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: entries = [] } = useQuery<ArchetypeSourceEntry[]>({
    queryKey: ['archetype-source-entries', archetype.id, cartomancyType],
    queryFn: () => getArchetypeSourceEntries(archetype.id, cartomancyType),
  });
  const invalidateEntries = () =>
    queryClient.invalidateQueries({
      queryKey: ['archetype-source-entries', archetype.id, cartomancyType],
    });

  // Edit mode persists across card switches — authoring a source card
  // by card is the natural flow; per-field editors are keyed by
  // (archetype, field) so drafts never leak between cards.
  const [editing, setEditing] = useState(false);

  // Every source covering this type (edit mode shows them all, even
  // ones with nothing authored for this card yet)…
  const { data: allSources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources', cartomancyType],
    queryFn: () => getReferenceSources(cartomancyType),
    enabled: editing,
  });
  // …with each source's field list for this type.
  const fieldQueries = useQueries({
    queries: allSources.map(src => ({
      queryKey: ['source-fields', src.id, cartomancyType],
      queryFn: () => getSourceFields(src.id, cartomancyType),
      enabled: editing,
    })),
  });
  const fieldsBySource = useMemo(() => {
    const map = new Map<number, SourceField[]>();
    allSources.forEach((src, i) => {
      map.set(src.id, (fieldQueries[i]?.data as SourceField[] | undefined) ?? []);
    });
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allSources, ...fieldQueries.map(q => q.data)]);

  const entryByField = useMemo(() => {
    const map = new Map<number, ArchetypeSourceEntry>();
    for (const e of entries) map.set(e.field_id, e);
    return map;
  }, [entries]);

  // Group by source preserving the server's sort (source name asc,
  // field sort_order asc). Each source keeps its own field array.
  const grouped = useMemo(() => {
    const bySource = new Map<
      number,
      { sourceName: string; sourceId: number; fields: ArchetypeSourceEntry[] }
    >();
    for (const e of entries) {
      let bucket = bySource.get(e.source_id);
      if (!bucket) {
        bucket = { sourceName: e.source_name, sourceId: e.source_id, fields: [] };
        bySource.set(e.source_id, bucket);
      }
      bucket.fields.push(e);
    }
    return [...bySource.values()];
  }, [entries]);

  // Which sources are expanded. Default is "all collapsed" — clicking
  // a header toggles. Expansion is keyed by source, so it deliberately
  // PERSISTS across card switches: reading one source across many
  // cards shouldn't require re-expanding it on every card.
  const [openSources, setOpenSources] = useState<Set<number>>(new Set());

  const toggleSource = (sourceId: number) => {
    setOpenSources(prev => {
      const next = new Set(prev);
      if (next.has(sourceId)) next.delete(sourceId);
      else next.add(sourceId);
      return next;
    });
  };

  // Fields marked collapsible get their own disclosure, collapsed by
  // default. Keyed by field_id so — like source expansion — it
  // persists while flipping through cards.
  const [openFields, setOpenFields] = useState<Set<number>>(new Set());

  const toggleField = (fieldId: number) => {
    setOpenFields(prev => {
      const next = new Set(prev);
      if (next.has(fieldId)) next.delete(fieldId);
      else next.add(fieldId);
      return next;
    });
  };

  return (
    <div className="archetype-notes">
      <div className="archetype-notes__header">
        <h3 className="archetype-notes__title">{archetype.name} — Notes</h3>
        <button
          className="archetype-notes__edit-link"
          onClick={() => setEditing(e => !e)}
        >
          {editing ? 'Done editing' : 'Edit'}
        </button>
      </div>

      <div className="archetype-notes__body">
        <ArchetypeCardImage
          archetype={archetype}
          cartomancyType={cartomancyType}
        />
        <div className="archetype-notes__main">
          {editing ? (
            allSources.length === 0 ? (
              <p className="archetype-notes__empty">
                No reference sources cover {cartomancyType} yet — create
                one in Settings → Reference Sources first.
              </p>
            ) : (
              allSources.map(src => {
                const open = openSources.has(src.id);
                const fields = fieldsBySource.get(src.id) ?? [];
                return (
                  <section key={src.id} className="archetype-notes__source">
                    <button
                      type="button"
                      className="archetype-notes__source-toggle"
                      aria-expanded={open}
                      onClick={() => toggleSource(src.id)}
                    >
                      <span
                        className={`archetype-notes__chevron ${open ? 'archetype-notes__chevron--open' : ''}`}
                        aria-hidden="true"
                      >
                        ▸
                      </span>
                      <span className="archetype-notes__source-name">{src.name}</span>
                    </button>
                    {open && (
                      <div className="archetype-notes__source-body">
                        {fields.length === 0 ? (
                          <p className="archetype-notes__empty">
                            This source has no {cartomancyType} fields —
                            define them in Settings → Reference Sources.
                          </p>
                        ) : (
                          fields.map(f => (
                            <EditableField
                              key={`${archetype.id}-${f.id}`}
                              archetypeId={archetype.id}
                              field={f}
                              initial={entryByField.get(f.id)?.content ?? ''}
                              onSaved={invalidateEntries}
                              showToast={showToast}
                            />
                          ))
                        )}
                      </div>
                    )}
                  </section>
                );
              })
            )
          ) : grouped.length === 0 ? (
            <p className="archetype-notes__empty">
              No source notes for {archetype.name} yet. Click "Edit" to
              add some.
            </p>
          ) : (
            grouped.map(group => {
              const open = openSources.has(group.sourceId);
              return (
                <section
                  key={group.sourceId}
                  className="archetype-notes__source"
                >
                  <button
                    type="button"
                    className="archetype-notes__source-toggle"
                    aria-expanded={open}
                    onClick={() => toggleSource(group.sourceId)}
                  >
                    <span
                      className={`archetype-notes__chevron ${
                        open ? 'archetype-notes__chevron--open' : ''
                      }`}
                      aria-hidden="true"
                    >
                      ▸
                    </span>
                    <span className="archetype-notes__source-name">
                      {group.sourceName}
                    </span>
                  </button>
                  {open && (
                    <div className="archetype-notes__source-body">
                      {group.fields.map(e => {
                        if (!e.field_collapsible) {
                          return (
                            <div key={e.entry_id} className="archetype-notes__field">
                              <h5 className="archetype-notes__field-name">{e.field_name}</h5>
                              <div className="archetype-notes__field-content">
                                <RichTextViewer content={e.content} />
                              </div>
                            </div>
                          );
                        }
                        const fieldOpen = openFields.has(e.field_id);
                        return (
                          <div key={e.entry_id} className="archetype-notes__field">
                            <button
                              type="button"
                              className="archetype-notes__field-toggle"
                              aria-expanded={fieldOpen}
                              onClick={() => toggleField(e.field_id)}
                            >
                              <span
                                className={`archetype-notes__chevron ${
                                  fieldOpen ? 'archetype-notes__chevron--open' : ''
                                }`}
                                aria-hidden="true"
                              >
                                ▸
                              </span>
                              <span className="archetype-notes__field-name archetype-notes__field-name--toggle">
                                {e.field_name}
                              </span>
                            </button>
                            {fieldOpen && (
                              <div className="archetype-notes__field-content archetype-notes__field-content--collapsible">
                                <RichTextViewer content={e.content} />
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

/** One field in edit mode: a rich-text editor prefilled with the
 *  current content (blank when nothing is authored), with a Save
 *  button that lights up on change. */
function EditableField({
  archetypeId,
  field,
  initial,
  onSaved,
  showToast,
}: {
  archetypeId: number;
  field: SourceField;
  initial: string;
  onSaved: () => void;
  showToast: (msg: string) => void;
}) {
  const [draft, setDraft] = useState(() => ensureHtml(initial));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await setArchetypeSourceEntry(archetypeId, field.id, draft);
      setDirty(false);
      onSaved();
    } catch {
      showToast('Could not save the note.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="archetype-notes__field archetype-notes__field--editing">
      <div className="archetype-notes__field-edit-head">
        <h5 className="archetype-notes__field-name">{field.name}</h5>
        <button
          className="archetype-notes__field-save"
          onClick={handleSave}
          disabled={!dirty || saving}
        >
          {saving ? 'Saving…' : dirty ? 'Save' : 'Saved'}
        </button>
      </div>
      <RichTextEditor
        content={draft}
        onChange={(html) => { setDraft(html); setDirty(true); }}
        placeholder="Nothing authored for this field yet…"
        minHeight={80}
      />
    </div>
  );
}
