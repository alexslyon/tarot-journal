import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCartomancyTypes } from '../../api/decks';
import './CardSearchBar.css';

export interface SearchFilters {
  query: string;
  deck_type?: string;
  card_category?: string;
  archetype?: string;
  suit?: string;
  rank?: string;
  has_notes?: boolean;
  has_image?: boolean;
  sort_by: string;
  sort_asc: boolean;
}

const EMPTY_FILTERS: SearchFilters = {
  query: '',
  sort_by: 'name',
  sort_asc: true,
};

interface CardSearchBarProps {
  deckId: number | null;
  onSearch: (filters: SearchFilters | null) => void;
}

export default function CardSearchBar({ deckId, onSearch }: CardSearchBarProps) {
  const [query, setQuery] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>(EMPTY_FILTERS);
  const [isSearching, setIsSearching] = useState(false);

  const { data: types = [] } = useQuery({
    queryKey: ['cartomancy-types'],
    queryFn: getCartomancyTypes,
  });

  const doSearch = useCallback(() => {
    const merged = { ...filters, query };
    // Only search if there's a query or at least one filter is set
    const hasFilter = query.trim() ||
      merged.deck_type ||
      merged.card_category ||
      merged.archetype ||
      merged.suit ||
      merged.rank ||
      merged.has_notes !== undefined ||
      merged.has_image !== undefined;

    if (!hasFilter) return;

    setIsSearching(true);
    onSearch(merged);
  }, [query, filters, onSearch]);

  const clearSearch = useCallback(() => {
    setQuery('');
    setFilters(EMPTY_FILTERS);
    setIsSearching(false);
    setShowAdvanced(false);
    onSearch(null);
  }, [onSearch]);

  const updateFilter = <K extends keyof SearchFilters>(key: K, value: SearchFilters[K]) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="card-search">
      <div className="card-search__bar">
        <input
          className="card-search__input"
          type="text"
          placeholder={deckId ? 'Search this deck...' : 'Search all cards...'}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
        />
        <button className="card-search__btn" onClick={doSearch}>Search</button>
        {isSearching && (
          <button className="card-search__btn card-search__btn--clear" onClick={clearSearch}>
            Clear
          </button>
        )}
        <button
          className={`card-search__btn card-search__btn--toggle ${showAdvanced ? 'active' : ''}`}
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          Filters {showAdvanced ? '▴' : '▾'}
        </button>
      </div>

      {showAdvanced && (
        <div className="card-search__filters">
          <div className="card-search__filter-row">
            <label className="card-search__filter-label">
              Deck Type
              <select
                value={filters.deck_type || ''}
                onChange={e => updateFilter('deck_type', e.target.value || undefined)}
              >
                <option value="">All Types</option>
                {types.map(t => (
                  <option key={t.id} value={t.name}>{t.name}</option>
                ))}
              </select>
            </label>

            <label className="card-search__filter-label">
              Category
              <select
                value={filters.card_category || ''}
                onChange={e => updateFilter('card_category', e.target.value || undefined)}
              >
                <option value="">All Categories</option>
                <option value="Major Arcana">Major Arcana</option>
                <option value="Minor Arcana">Minor Arcana</option>
                <option value="Court Cards">Court Cards</option>
              </select>
            </label>

            <label className="card-search__filter-label">
              Archetype
              <input
                type="text"
                placeholder="e.g. The Fool"
                value={filters.archetype || ''}
                onChange={e => updateFilter('archetype', e.target.value || undefined)}
              />
            </label>
          </div>

          <div className="card-search__filter-row">
            <label className="card-search__filter-label">
              Suit
              <input
                type="text"
                placeholder="e.g. Cups"
                value={filters.suit || ''}
                onChange={e => updateFilter('suit', e.target.value || undefined)}
              />
            </label>

            <label className="card-search__filter-label">
              Rank
              <input
                type="text"
                placeholder="e.g. Queen"
                value={filters.rank || ''}
                onChange={e => updateFilter('rank', e.target.value || undefined)}
              />
            </label>

            <label className="card-search__filter-label">
              Sort By
              <select
                value={filters.sort_by}
                onChange={e => updateFilter('sort_by', e.target.value)}
              >
                <option value="name">Name</option>
                <option value="deck">Deck</option>
                <option value="card_order">Card Order</option>
              </select>
            </label>
          </div>

          <div className="card-search__filter-row">
            <label className="card-search__filter-check">
              <input
                type="checkbox"
                checked={filters.has_notes === true}
                onChange={e => updateFilter('has_notes', e.target.checked ? true : undefined)}
              />
              Has Notes
            </label>

            <label className="card-search__filter-check">
              <input
                type="checkbox"
                checked={filters.has_image === true}
                onChange={e => updateFilter('has_image', e.target.checked ? true : undefined)}
              />
              Has Image
            </label>

            <label className="card-search__filter-check">
              <input
                type="checkbox"
                checked={!filters.sort_asc}
                onChange={e => updateFilter('sort_asc', !e.target.checked)}
              />
              Descending
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
