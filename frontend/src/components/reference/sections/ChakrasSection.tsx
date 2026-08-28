/**
 * Chakras reference: the seven centers root to crown, each with its
 * color as a small accent and the cards the chosen correspondence
 * system's chakra field assigns.
 */
import { useQuery } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getChakrasReference } from '../../../api/reference';
import {
  AssignedCards,
  ReferenceSystemPicker,
  useReferenceSystem,
} from './referenceShared';
import '../ReferenceTab.css';

interface ChakrasSectionProps {
  onOpenArchetype?: (id: number, cartomancyType: string) => void;
}

export default function ChakrasSection({ onOpenArchetype }: ChakrasSectionProps) {
  const { systems, systemId, setSystemId } = useReferenceSystem();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-chakras', systemId],
    queryFn: () => getChakrasReference(systemId),
  });

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Chakras</h2>
      <p className="reference-section__hint">
        The seven energy centers, root to crown. Cards appear where your
        chosen correspondence system's chakra field assigns them.
      </p>
      <ReferenceSystemPicker systems={systems} systemId={systemId} onChange={setSystemId} />

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="chakras reference" onRetry={() => refetch()} />}

      {data?.chakras.map(chakra => (
        <div key={chakra.name} className="ref-detail" style={{ marginBottom: 16 }}>
          <div className="ref-detail__header">
            <span
              className="ref-chakra-swatch"
              style={{ background: chakra.color }}
              aria-hidden="true"
            />
            <h3 className="ref-detail__title">{chakra.name}</h3>
            <span className="ref-detail__dates">{chakra.sanskrit}</span>
          </div>
          <div className="ref-detail__meta">
            <span>{chakra.location}</span>
          </div>
          <p className="ref-detail__themes">{chakra.themes}</p>
          <AssignedCards refs={chakra.assigned} onOpenArchetype={onOpenArchetype} />
        </div>
      ))}
    </div>
  );
}
