import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getArchetypeSourceEntries } from '../../../../api/referenceSources';
import RichTextViewer from '../../../common/RichTextViewer';
import ArchetypeCardImage from './ArchetypeCardImage';
import type { Archetype } from '../../../../api/correspondences';
import type { ArchetypeSourceEntry } from '../../../../types';
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
 * the "absent or empty → hidden" rule.
 */
export default function ArchetypeNotesTab({
  archetype,
  cartomancyType,
  onNavigateToSettings,
}: Props) {
  const { data: entries = [] } = useQuery<ArchetypeSourceEntry[]>({
    queryKey: ['archetype-source-entries', archetype.id, cartomancyType],
    queryFn: () => getArchetypeSourceEntries(archetype.id, cartomancyType),
  });

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
          {grouped.length === 0 ? (
            <p className="archetype-notes__empty">
              No source notes for {archetype.name} yet.
              {onNavigateToSettings && ' Click "Edit in Settings" to add some.'}
            </p>
          ) : (
            grouped.map(group => (
              <section
                key={group.sourceId}
                className="archetype-notes__source"
              >
                <h4 className="archetype-notes__source-name">{group.sourceName}</h4>
                {group.fields.map(e => (
                  <div key={e.entry_id} className="archetype-notes__field">
                    <h5 className="archetype-notes__field-name">{e.field_name}</h5>
                    <div className="archetype-notes__field-content">
                      <RichTextViewer content={e.content} />
                    </div>
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
