/**
 * Suits reference: the four Tarot suits — element, alternate names,
 * the suit's pips and courts as clickable tiles, cards the chosen
 * correspondence system assigns to the suit's element, and source
 * texts per suit.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getSuitsReference } from '../../../api/reference';
import {
  AssignedCards,
  ReferenceSystemPicker,
  RefTile,
  useCardPeek,
  useReferenceSystem,
} from './referenceShared';
import EntityNotes from './EntityNotes';
import '../ReferenceTab.css';

interface SuitsSectionProps {
  onOpenArchetype?: (id: number, cartomancyType: string) => void;
}

export default function SuitsSection({ onOpenArchetype }: SuitsSectionProps) {
  const [suitName, setSuitName] = useState('Wands');
  const { systems, systemId, setSystemId } = useReferenceSystem();
  const { openCard, cardModal } = useCardPeek();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-suits', systemId],
    queryFn: () => getSuitsReference(systemId),
  });

  const suit = data?.suits.find(s => s.name === suitName);

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Suits</h2>
      <p className="reference-section__hint">
        The four Tarot suits with their Golden Dawn elements and
        playing-card counterparts.
      </p>
      <ReferenceSystemPicker systems={systems} systemId={systemId} onChange={setSystemId} />

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="suits reference" onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="ref-selector">
            {data.suits.map(s => (
              <button
                key={s.name}
                type="button"
                className={`ref-selector__item ${s.name === suitName ? 'ref-selector__item--active' : ''}`}
                onClick={() => setSuitName(s.name)}
              >
                <span className="ref-selector__glyph">{s.glyph}</span>
                <span className="ref-selector__name">{s.name}</span>
              </button>
            ))}
          </div>

          {suit && (
            <div className="ref-detail">
              <div className="ref-detail__header">
                <span className="ref-detail__glyph">{suit.glyph}</span>
                <h3 className="ref-detail__title">{suit.name}</h3>
                <span className="ref-detail__dates">{suit.element}</span>
              </div>
              <div className="ref-detail__meta">
                <span>Also called <strong>{suit.alt_names.join(', ')}</strong></span>
                <span>Playing cards: <strong>{suit.playing_card}</strong></span>
              </div>

              <div className="ref-detail__kicker">Pips</div>
              <div className="ref-detail__row">
                {suit.pips.map(card => (
                  <RefTile key={card.name} card={card} onOpen={openCard} />
                ))}
              </div>

              <div className="ref-detail__kicker">Courts</div>
              <div className="ref-detail__row">
                {suit.courts.map(card => (
                  <RefTile key={card.name} card={card} onOpen={openCard} />
                ))}
              </div>

              <AssignedCards refs={suit.assigned} onOpenArchetype={onOpenArchetype} />
              <EntityNotes kind="suit" entityKey={suit.name} label={suit.name} />
            </div>
          )}
        </>
      )}

      {cardModal}
    </div>
  );
}
