import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDecks, getCartomancyTypes, updateDeck } from '../../api/decks';
import type { Deck } from '../../types';
import QueryError from '../common/QueryError';
import './DeckList.css';

interface DeckListProps {
  selectedDeckId: number | null;
  onSelectDeck: (deck: Deck) => void;
  onEditDeck?: (deckId: number) => void;
  onImport?: () => void;
  onExport?: (deckId: number) => void;
}

export default function DeckList({ selectedDeckId, onSelectDeck, onEditDeck, onImport }: DeckListProps) {
  const queryClient = useQueryClient();
  const [filterTypeId, setFilterTypeId] = useState<number | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'type' | 'cards'>('name');
  const [sortAsc, setSortAsc] = useState(true);
  const [showTags, setShowTags] = useState(false);
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  const { data: types = [] } = useQuery({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });

  const { data: decks = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['decks', filterTypeId],
    queryFn: () => getDecks(filterTypeId),
  });

  const toggleFavorite = async (deck: Deck) => {
    await updateDeck(deck.id, { favorite: !deck.favorite });
    queryClient.invalidateQueries({ queryKey: ['decks'] });
  };

  const searched = searchQuery.trim()
    ? decks.filter((d) => d.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : decks;
  const filteredDecks = favoritesOnly ? searched.filter(d => !!d.favorite) : searched;

  // Strip a leading "The " when sorting names so "The Fool" sorts as "Fool".
  const nameSortKey = (name: string) => name.replace(/^the\s+/i, '');

  const sortedDecks = [...filteredDecks].sort((a, b) => {
    let cmp = 0;
    if (sortBy === 'name') {
      cmp = nameSortKey(a.name).localeCompare(nameSortKey(b.name));
    } else if (sortBy === 'type') {
      cmp = (a.cartomancy_type || '').localeCompare(b.cartomancy_type || '');
    } else if (sortBy === 'cards') {
      cmp = (a.card_count || 0) - (b.card_count || 0);
    }
    return sortAsc ? cmp : -cmp;
  });

  const handleHeaderClick = (col: 'name' | 'type' | 'cards') => {
    if (sortBy === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortBy(col);
      setSortAsc(true);
    }
  };

  return (
    <div className="deck-list">
      <div className="deck-list__header">
        <h2 className="deck-list__title">Decks</h2>
        {onImport && (
          <button className="deck-list__import-btn" onClick={onImport}>Import</button>
        )}
        <label className="deck-list__tag-toggle">
          <input
            type="checkbox"
            checked={showTags}
            onChange={(e) => setShowTags(e.target.checked)}
          />
          <span>Tags</span>
        </label>
        <label className="deck-list__toggle" title="Only decks starred for the phone companion">
          <input
            type="checkbox"
            checked={favoritesOnly}
            onChange={(e) => setFavoritesOnly(e.target.checked)}
          />
          <span>★ Favorites</span>
        </label>
      </div>
      <div className="deck-list__filters">
        <input
          type="text"
          className="deck-list__search"
          placeholder="Search decks..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <select
          className="deck-list__filter"
          value={filterTypeId ?? ''}
          onChange={(e) => setFilterTypeId(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">All Types</option>
          {types.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
      </div>

      <div className="deck-list__sort-bar">
        <span className="deck-list__sort-label">Sort:</span>
        {(['name', 'type', 'cards'] as const).map((col) => (
          <button
            key={col}
            className={`deck-list__sort-btn ${sortBy === col ? 'deck-list__sort-btn--active' : ''}`}
            onClick={() => handleHeaderClick(col)}
          >
            {col === 'cards' ? '#' : col.charAt(0).toUpperCase() + col.slice(1)}
            {sortBy === col && (sortAsc ? ' \u25B2' : ' \u25BC')}
          </button>
        ))}
      </div>

      <div className="deck-list__rows">
        {isLoading && <div className="deck-list__loading">Loading...</div>}
        {!isLoading && isError && (
          <QueryError what="decks" onRetry={() => refetch()} />
        )}
        {sortedDecks.map((deck) => (
          <div
            key={deck.id}
            className={`deck-list__row ${deck.id === selectedDeckId ? 'deck-list__row--selected' : ''}`}
            onClick={() => onSelectDeck(deck)}
            onDoubleClick={() => onEditDeck?.(deck.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSelectDeck(deck);
              }
            }}
          >
            <div className="deck-list__row-content">
              <span className="deck-list__name">
                {deck.name}
                {showTags && deck.tags && deck.tags.length > 0 && (
                  <span className="deck-list__tags">
                    {deck.tags.map(t => (
                      <span
                        key={t.id}
                        className="deck-list__tag-dot"
                        style={{ backgroundColor: t.color }}
                        title={t.name}
                      />
                    ))}
                  </span>
                )}
              </span>
              <span className="deck-list__subtitle">
                {deck.cartomancy_type || 'Untyped'}
                {deck.card_count != null && ` \u00B7 ${deck.card_count} cards`}
              </span>
            </div>
            <button
              type="button"
              className={`deck-list__fav ${deck.favorite ? 'deck-list__fav--on' : ''}`}
              title={deck.favorite
                ? 'Favorite — synced to the phone companion. Click to unfavorite.'
                : 'Mark as favorite (synced to the phone companion)'}
              aria-label={deck.favorite ? `Unfavorite ${deck.name}` : `Favorite ${deck.name}`}
              onClick={(e) => { e.stopPropagation(); toggleFavorite(deck); }}
            >
              ★
            </button>
            {onEditDeck && (
              <button
                className="deck-list__edit-btn"
                onClick={(e) => { e.stopPropagation(); onEditDeck(deck.id); }}
                title="Edit deck"
              >
                &#9998;
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
