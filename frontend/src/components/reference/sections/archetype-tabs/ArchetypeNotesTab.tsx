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
    payload?: { archetypeId?: number; fieldId?: number; sourceId?: number },
  ) => void;
}

/**
 * One section per reference source that has authored content for this
 * archetype. Empty sources don't render at all — the "fields are empty
 * → no row" rule the user asked for.
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
          {entries.length === 0 ? (
            <p className="archetype-notes__empty">
              No source notes for {archetype.name} yet.
              {onNavigateToSettings && ' Click "Edit in Settings" to add some.'}
            </p>
          ) : (
            entries.map(e => (
              <section key={e.entry_id} className="archetype-notes__field">
                <h4 className="archetype-notes__field-name">{e.source_name}</h4>
                <div className="archetype-notes__source-block">
                  <RichTextViewer content={e.content} />
                </div>
              </section>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
