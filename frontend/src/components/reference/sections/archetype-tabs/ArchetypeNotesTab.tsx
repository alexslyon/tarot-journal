import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getArchetypeNotes } from '../../../../api/archetypeNotes';
import RichTextViewer from '../../../common/RichTextViewer';
import ArchetypeCardImage from './ArchetypeCardImage';
import type { Archetype } from '../../../../api/correspondences';
import type { ArchetypeNoteEntry } from '../../../../types';
import './ArchetypeNotesTab.css';

interface Props {
  archetype: Archetype;
  cartomancyType: string;
  onNavigateToSettings?: (
    section: string,
    payload?: { archetypeId?: number; fieldId?: number },
  ) => void;
}

interface FieldGroup {
  fieldId: number;
  fieldName: string;
  fieldOrder: number;
  bySource: Map<string, ArchetypeNoteEntry[]>;
  sourceOrder: string[];
}

const UNSOURCED_KEY = '__other__';

export default function ArchetypeNotesTab({ archetype, cartomancyType, onNavigateToSettings }: Props) {
  const { data: rawEntries = [] } = useQuery<ArchetypeNoteEntry[]>({
    queryKey: ['archetype-notes', archetype.id],
    queryFn: () => getArchetypeNotes(archetype.id),
  });

  // Group by field, then by source within each field. Unsourced entries land
  // in the "Other" group, which always sorts last.
  const groups = useMemo<FieldGroup[]>(() => {
    const byField = new Map<number, FieldGroup>();
    for (const e of rawEntries) {
      // Field-only rows from the LEFT JOIN have no entry id; include them so
      // empty fields still render their headers.
      const fieldId = e.field_def_id;
      const fieldOrder = e.field_order ?? 0;
      const fieldName = e.field_name || '';
      if (!byField.has(fieldId)) {
        byField.set(fieldId, {
          fieldId,
          fieldName,
          fieldOrder,
          bySource: new Map(),
          sourceOrder: [],
        });
      }
      if (e.id == null) continue; // header-only row from LEFT JOIN
      const fg = byField.get(fieldId)!;
      const key = e.source_name || UNSOURCED_KEY;
      if (!fg.bySource.has(key)) {
        fg.bySource.set(key, []);
        fg.sourceOrder.push(key);
      }
      fg.bySource.get(key)!.push(e);
    }
    // Sort source headings: alphabetical sources first, "Other" last.
    for (const fg of byField.values()) {
      fg.sourceOrder.sort((a, b) => {
        if (a === UNSOURCED_KEY) return 1;
        if (b === UNSOURCED_KEY) return -1;
        return a.localeCompare(b);
      });
    }
    return [...byField.values()].sort((a, b) =>
      a.fieldOrder !== b.fieldOrder
        ? a.fieldOrder - b.fieldOrder
        : a.fieldId - b.fieldId,
    );
  }, [rawEntries]);

  const populatedGroups = groups.filter(g => g.bySource.size > 0);

  return (
    <div className="archetype-notes">
      <div className="archetype-notes__header">
        <h3 className="archetype-notes__title">{archetype.name} — Notes</h3>
        {onNavigateToSettings && (
          <button
            className="archetype-notes__edit-link"
            onClick={() =>
              onNavigateToSettings('archetype-notes', { archetypeId: archetype.id })
            }
          >
            Edit in Settings →
          </button>
        )}
      </div>

      <div className="archetype-notes__body">
        <ArchetypeCardImage
          archetype={archetype}
          cartomancyType={cartomancyType}
        />
        <div className="archetype-notes__main">
          {populatedGroups.length === 0 ? (
            <p className="archetype-notes__empty">
              No notes for {archetype.name} yet.
              {onNavigateToSettings && ' Click "Edit in Settings" to add some.'}
            </p>
          ) : (
            populatedGroups.map(fg => (
              <section key={fg.fieldId} className="archetype-notes__field">
                <h4 className="archetype-notes__field-name">{fg.fieldName}</h4>
                {fg.sourceOrder.map(sourceKey => (
                  <div key={sourceKey} className="archetype-notes__source-block">
                    <h5 className="archetype-notes__source-label">
                      {sourceKey === UNSOURCED_KEY ? 'Other' : sourceKey}
                    </h5>
                    <ul className="archetype-notes__entries">
                      {fg.bySource.get(sourceKey)!.map(e => (
                        <li key={e.id} className="archetype-notes__entry">
                          <RichTextViewer content={e.content} />
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </section>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
