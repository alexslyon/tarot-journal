/**
 * Suits reference, one page per deck type that has suits (picked via
 * searchable dropdown). A reading-focused section: each suit shows
 * its alternate names and playing-card counterpart (where curated)
 * and, chiefly, its source texts — no card grids, no elemental
 * attributions.
 */
import { useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getSuitsReference } from '../../../api/reference';
import SearchCombobox from '../../common/SearchCombobox';
import EntityNotes from './EntityNotes';
import '../ReferenceTab.css';

export default function SuitsSection() {
  const [type, setType] = useState<string | null>(null);
  const [suitName, setSuitName] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-suits', type],
    queryFn: () => getSuitsReference(type),
    placeholderData: keepPreviousData,
  });

  const suits = data?.suits ?? [];
  const suit = suits.find(s => s.name === suitName) ?? suits[0];

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Suits</h2>

      {data && (
        <div className="ref-type-picker">
          <span className="ref-type-picker__label">Deck type</span>
          <SearchCombobox
            options={data.types.map((t, i) => ({ id: i, label: t }))}
            value={data.types.indexOf(data.type)}
            onSelect={(option) => {
              if (!option) return;
              setType(option.label);
              setSuitName(null);
            }}
            placeholder="Choose a deck type…"
          />
        </div>
      )}

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="suits reference" onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="ref-selector">
            {suits.map(s => (
              <button
                key={s.name}
                type="button"
                className={`ref-selector__item ${s.name === suit?.name ? 'ref-selector__item--active' : ''}`}
                onClick={() => setSuitName(s.name)}
              >
                <span className="ref-selector__name">{s.name}</span>
              </button>
            ))}
          </div>

          {suit && (
            <div className="ref-detail">
              <div className="ref-detail__header">
                <h3 className="ref-detail__title">{suit.name}</h3>
              </div>
              {(suit.alt_names || suit.playing_card) && (
                <div className="ref-detail__meta">
                  {suit.alt_names && (
                    <span>Also called <strong>{suit.alt_names.join(', ')}</strong></span>
                  )}
                  {suit.playing_card && (
                    <span>Playing cards: <strong>{suit.playing_card}</strong></span>
                  )}
                </div>
              )}

              <EntityNotes
                kind="suit"
                entityKey={`${data.type}::${suit.name}`}
                label={`${suit.name} in ${data.type}`}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
