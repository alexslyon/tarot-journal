/**
 * Suits reference, one tab per deck type that has suits. Tarot shows
 * the curated four (elements, alternate names, playing-card
 * counterparts); other types derive their suits and cards from their
 * archetypes, with images from that type's default deck. Pips and
 * courts render separately; each suit takes source texts.
 */
import { useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getSuitsReference } from '../../../api/reference';
import SearchCombobox from '../../common/SearchCombobox';
import { RefTile, useCardPeek } from './referenceShared';
import EntityNotes from './EntityNotes';
import type { SuitCardRef } from '../../../api/reference';
import '../ReferenceTab.css';

/** Caption a tile with its rank when the card's own name doesn't
 *  already carry it (Lenormand's Rider is a Nine; "Nine of Hearts"
 *  needs no caption). */
function rankCaption(card: SuitCardRef): string | undefined {
  const rank = card.rank == null ? '' : String(card.rank);
  if (!rank || card.name.toLowerCase().includes(rank.toLowerCase())) {
    return undefined;
  }
  return rank;
}

export default function SuitsSection() {
  const [type, setType] = useState<string | null>(null);
  const [suitName, setSuitName] = useState<string | null>(null);
  const { openCard, cardModal } = useCardPeek();

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
                {suit.glyph && <span className="ref-detail__glyph">{suit.glyph}</span>}
                <h3 className="ref-detail__title">{suit.name}</h3>
                {suit.element && <span className="ref-detail__dates">{suit.element}</span>}
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

              <div className="ref-detail__kicker">Pips</div>
              <div className="ref-detail__row">
                {suit.pips.map(card => (
                  <RefTile key={card.name} card={card} caption={rankCaption(card)} onOpen={openCard} />
                ))}
              </div>

              {suit.courts.length > 0 && (
                <>
                  <div className="ref-detail__kicker">Courts</div>
                  <div className="ref-detail__row">
                    {suit.courts.map(card => (
                      <RefTile key={card.name} card={card} caption={rankCaption(card)} onOpen={openCard} />
                    ))}
                  </div>
                </>
              )}

              <EntityNotes kind="suit" entityKey={suit.name} label={suit.name} />
            </div>
          )}
        </>
      )}

      {cardModal}
    </div>
  );
}
