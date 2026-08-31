/**
 * Numerology & Ranks — a reference-text section. The dropdown picks
 * between Numerology (the open-ended number list: however many
 * entries exist, they render in list order, with a system picker only
 * once entries carry more than one system tag) and each suited deck
 * type's ranks. Every entry is a heading plus its source texts — no
 * card grids.
 */
import { useMemo, useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getNumerologyReference, getRanksReference } from '../../../api/reference';
import SearchCombobox from '../../common/SearchCombobox';
import EntityNotes from './EntityNotes';
import EntityScribeModal from '../../scribe/EntityScribeModal';
import '../ReferenceTab.css';

export default function NumerologySection() {
  const [scribeOpen, setScribeOpen] = useState(false);
  const [numerologySystem, setNumerologySystem] = useState<string | null>(null);
  // null = the Numerology view; a string = that deck type's ranks.
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
      <div className="ref-section-head">
        <h2 className="reference-section__title">Numerology &amp; Ranks</h2>
        <button type="button" className="ref-scribe-btn" onClick={() => setScribeOpen(true)}>
          Import from source (Scribe)
        </button>
      </div>

      {data && (
        <div className="ref-type-picker">
          <span className="ref-type-picker__label">Show</span>
          <SearchCombobox
            options={[
              { id: 0, label: 'Numerology' },
              ...data.suit_types.map((t, i) => ({ id: i + 1, label: t })),
            ]}
            value={rankType === null ? 0 : data.suit_types.indexOf(rankType) + 1}
            onSelect={(option) => {
              if (!option) return;
              setRankType(option.id === 0 ? null : data.suit_types[option.id - 1]);
            }}
            placeholder="Numerology or a deck type…"
          />
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
              <EntityNotes
                kind="rank"
                entityKey={`${rankType}::${rank.rank}`}
                label={`the ${rank.rank} rank in ${rankType}`}
              />
            </div>
          ))}
        </>
      )}
      {scribeOpen && (
        <EntityScribeModal
          open
          onClose={() => setScribeOpen(false)}
          initialKind={rankType ? 'rank' : 'number'}
          initialType={rankType}
        />
      )}
    </div>
  );
}
