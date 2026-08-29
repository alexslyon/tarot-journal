/**
 * Numerology reference, rendered from the server's open-ended entry
 * list — however many numbers exist (master numbers or a second
 * system later), they render in list order. A system picker appears
 * only when entries actually carry more than one system tag.
 */
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getNumerologyReference } from '../../../api/reference';
import {
  AssignedCards,
  ReferenceSystemPicker,
  RefTile,
  useCardPeek,
  useReferenceSystem,
} from './referenceShared';
import EntityNotes from './EntityNotes';
import '../ReferenceTab.css';

interface NumerologySectionProps {
  onOpenArchetype?: (id: number, cartomancyType: string) => void;
}

export default function NumerologySection({ onOpenArchetype }: NumerologySectionProps) {
  const { systems, systemId, setSystemId } = useReferenceSystem();
  const { openCard, cardModal } = useCardPeek();
  const [numerologySystem, setNumerologySystem] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-numerology', systemId],
    queryFn: () => getNumerologyReference(systemId),
  });

  // Distinct numerological systems present in the data. The picker
  // stays invisible until a second one exists.
  const numerologySystems = useMemo(() => {
    const tags = new Set((data?.entries ?? []).map(e => e.system ?? ''));
    return [...tags];
  }, [data?.entries]);
  const entries = (data?.entries ?? []).filter(
    e => numerologySystems.length < 2 || (e.system ?? '') === (numerologySystem ?? numerologySystems[0]),
  );

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Numerology</h2>
      <p className="reference-section__hint">
        Number meanings as they thread through the Majors, the pips, and
        numerological practice. The app uses two reductions: birth and
        year cards reduce to 22 at most (every trump stays reachable),
        while classic numerology reduces to a single digit (the digital
        root).
      </p>
      <ReferenceSystemPicker systems={systems} systemId={systemId} onChange={setSystemId} />
      {numerologySystems.length >= 2 && (
        <label className="ref-system-picker">
          <span>Numerology system</span>
          <select
            value={numerologySystem ?? numerologySystems[0]}
            onChange={(e) => setNumerologySystem(e.target.value)}
          >
            {numerologySystems.map(tag => (
              <option key={tag} value={tag}>{tag || 'Default'}</option>
            ))}
          </select>
        </label>
      )}

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="numerology reference" onRetry={() => refetch()} />}

      {entries.map(entry => (
        <div key={`${entry.system ?? ''}-${entry.number}`} className="ref-detail" style={{ marginBottom: 16 }}>
          <div className="ref-detail__header">
            <span className="ref-detail__glyph">{entry.number}</span>
          </div>

          {(entry.majors?.length || entry.minors?.length) ? (
            <div className="ref-detail__row" style={{ marginTop: 12 }}>
              {(entry.majors ?? []).map(m => (
                <RefTile key={`M${m.number}`} card={m} onOpen={openCard} />
              ))}
              {(entry.minors ?? []).map(m => (
                <RefTile key={m.name} card={m} onOpen={openCard} />
              ))}
            </div>
          ) : null}

          <AssignedCards refs={entry.assigned} onOpenArchetype={onOpenArchetype} />
          <EntityNotes kind="number" entityKey={entry.number} label={`number ${entry.number}`} />
        </div>
      ))}

      {cardModal}
    </div>
  );
}
