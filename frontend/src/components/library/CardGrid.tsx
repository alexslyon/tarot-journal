import { useQuery } from '@tanstack/react-query';
import { getCards } from '../../api/cards';
import { cardThumbnailUrl } from '../../api/images';
import type { Card } from '../../types';
import './CardGrid.css';

interface CardGridProps {
  deckId: number | null;
  deckName: string;
  onCardClick?: (card: Card) => void;
  /** When provided, renders these cards instead of fetching by deckId (search mode). */
  searchResults?: Card[] | null;
  searchLoading?: boolean;
  /** Multi-select state managed by parent */
  selectedIds?: Set<number>;
  onSelectionChange?: (ids: Set<number>) => void;
  onBatchEdit?: () => void;
}

export default function CardGrid({ deckId, deckName, onCardClick, searchResults, searchLoading, selectedIds, onSelectionChange, onBatchEdit }: CardGridProps) {
  const { data: deckCards = [], isLoading: deckLoading } = useQuery({
    queryKey: ['cards', deckId],
    queryFn: () => getCards(deckId!),
    enabled: deckId !== null && searchResults === undefined,
  });

  const isSearchMode = searchResults !== undefined && searchResults !== null;
  const cards = isSearchMode ? searchResults : deckCards;
  const isLoading = isSearchMode ? !!searchLoading : deckLoading;

  if (!isSearchMode && !deckId) {
    return (
      <div className="card-grid__empty">
        <p>Select a deck to view its cards</p>
      </div>
    );
  }

  const title = isSearchMode ? 'Search Results' : deckName;
  const selectable = !!onSelectionChange;
  const selCount = selectedIds?.size ?? 0;

  const toggleSelect = (cardId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!selectedIds || !onSelectionChange) return;
    const next = new Set(selectedIds);
    if (next.has(cardId)) next.delete(cardId);
    else next.add(cardId);
    onSelectionChange(next);
  };

  const selectAll = () => {
    if (!onSelectionChange) return;
    onSelectionChange(new Set(cards.map(c => c.id)));
  };

  const deselectAll = () => {
    if (!onSelectionChange) return;
    onSelectionChange(new Set());
  };

  return (
    <div className="card-grid">
      <div className="card-grid__header">
        <h2 className="card-grid__title">{title}</h2>
        <span className="card-grid__count">{cards.length} cards</span>
        {selectable && cards.length > 0 && (
          <div className="card-grid__sel-controls">
            <button className="card-grid__sel-btn" onClick={selCount === cards.length ? deselectAll : selectAll}>
              {selCount === cards.length ? 'Deselect All' : 'Select All'}
            </button>
            {selCount > 0 && (
              <>
                <span className="card-grid__sel-count">{selCount} selected</span>
                <button className="card-grid__sel-btn card-grid__sel-btn--edit" onClick={onBatchEdit}>
                  Batch Edit
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="card-grid__loading">Loading cards...</div>
      ) : cards.length === 0 ? (
        <div className="card-grid__empty">
          <p>{isSearchMode ? 'No cards match your search' : 'No cards in this deck'}</p>
        </div>
      ) : (
        <div className="card-grid__items">
          {cards.map((card) => (
            <div
              key={card.id}
              className={`card-grid__card ${selectedIds?.has(card.id) ? 'card-grid__card--selected' : ''}`}
              onClick={() => onCardClick?.(card)}
              title={card.name}
            >
              {selectable && (
                <div className="card-grid__checkbox" onClick={(e) => toggleSelect(card.id, e)}>
                  <input
                    type="checkbox"
                    checked={selectedIds?.has(card.id) ?? false}
                    readOnly
                  />
                </div>
              )}
              {card.image_path ? (
                <img
                  className="card-grid__image"
                  src={cardThumbnailUrl(card.id)}
                  alt={card.name}
                  loading="lazy"
                />
              ) : (
                <div className="card-grid__placeholder">
                  <span>{card.name}</span>
                </div>
              )}
              <div className="card-grid__label">{card.name}</div>
              {isSearchMode && card.deck_name && (
                <div className="card-grid__deck-label">{card.deck_name}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
