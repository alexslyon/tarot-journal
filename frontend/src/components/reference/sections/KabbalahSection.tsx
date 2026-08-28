/**
 * Kabbalah reference: the interactive Tree of Life IS the section —
 * click sephiroth and paths for their details. (The flat Sephiroth /
 * Paths list tabs were removed 2026-08; recover from git history if
 * they're ever wanted back.)
 */
import { useQuery } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getKabbalahReference } from '../../../api/reference';
import {
  ReferenceSystemPicker,
  useCardPeek,
  useReferenceSystem,
} from './referenceShared';
import TreeOfLife from './TreeOfLife';
import '../ReferenceTab.css';
import './KabbalahSection.css';

interface KabbalahSectionProps {
  onOpenArchetype?: (id: number, cartomancyType: string) => void;
}

export default function KabbalahSection({ onOpenArchetype }: KabbalahSectionProps) {
  const { systems, systemId, setSystemId } = useReferenceSystem();
  const { openCard, cardModal } = useCardPeek();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-kabbalah', systemId],
    queryFn: () => getKabbalahReference(systemId),
  });

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Kabbalah</h2>
      <p className="reference-section__hint">
        The Tree of Life: ten sephiroth joined by twenty-two paths, one
        Hebrew letter and one trump per path.
      </p>
      <ReferenceSystemPicker systems={systems} systemId={systemId} onChange={setSystemId} />

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="Kabbalah reference" onRetry={() => refetch()} />}

      {data && (
        <TreeOfLife data={data} openCard={openCard} onOpenArchetype={onOpenArchetype} />
      )}

      {cardModal}
    </div>
  );
}
