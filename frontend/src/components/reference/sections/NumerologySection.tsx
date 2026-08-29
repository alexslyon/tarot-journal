/**
 * Numerology & Ranks. First tab: the open-ended number list — however
 * many entries exist (master numbers or a second system later), they
 * render in list order, with a system picker only once entries carry
 * more than one system tag. The other tabs, one per deck type that
 * has suits, group that type's cards by rank.
 */
import { useMemo, useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getNumerologyReference, getRanksReference } from '../../../api/reference';
import { RefTile, useCardPeek } from './referenceShared';
import EntityNotes from './EntityNotes';
import '../ReferenceTab.css';

export default function NumerologySection() {
  const { openCard, cardModal } = useCardPeek();
  const [numerologySystem, setNumerologySystem] = useState<string | null>(null);
  // null = the Numerology tab; a string = that deck type's rank tab.
  const [rankType, setRankType] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-numerology'],
    queryFn: getNumerologyReference,
  });

  const { data: rankData, isError: ranksError, refetch: refetchRanks } = useQuery({
    queryKey: ['reference-ranks', rankType],
    queryFn: () => getRanksReference(rankType),
    enabled: rankType !== null,
    placeholderData: keepPreviousData,
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
      <h2 className="reference-section__title">Numerology &amp; Ranks</h2>

      {data && (
        <div className="ref-subtabs">
          <button
            type="button"
            className={`ref-subtabs__tab ${rankType === null ? 'ref-subtabs__tab--active' : ''}`}
            onClick={() => setRankType(null)}
          >
            Numerology
          </button>
          {data.suit_types.map(t => (
            <button
              key={t}
              type="button"
              className={`ref-subtabs__tab ${rankType === t ? 'ref-subtabs__tab--active' : ''}`}
              onClick={() => setRankType(t)}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="numerology reference" onRetry={() => refetch()} />}

      {rankType === null && data && (
        <>
          <p className="reference-section__hint">
            The app uses two reductions: birth and year cards reduce to
            22 at most (every trump stays reachable), while classic
            numerology reduces to a single digit (the digital root).
          </p>
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

              <EntityNotes kind="number" entityKey={entry.number} label={`number ${entry.number}`} />
            </div>
          ))}
        </>
      )}

      {rankType !== null && (
        <>
          {ranksError && <QueryError what="ranks" onRetry={() => refetchRanks()} />}
          {rankData?.ranks.map(rank => (
            <div key={rank.rank} className="ref-detail" style={{ marginBottom: 16 }}>
              <div className="ref-detail__header">
                <h3 className="ref-detail__title">{rank.rank}</h3>
              </div>
              <div className="ref-detail__row">
                {rank.cards.map(card => (
                  <RefTile key={card.name} card={card} caption={card.suit} onOpen={openCard} />
                ))}
              </div>
              <EntityNotes kind="rank" entityKey={rank.rank} label={`the rank ${rank.rank}`} />
            </div>
          ))}
        </>
      )}

      {cardModal}
    </div>
  );
}
