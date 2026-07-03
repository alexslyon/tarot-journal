import { useState, useCallback, useMemo } from 'react';
import { useQuery, useInfiniteQuery, keepPreviousData } from '@tanstack/react-query';
import { getEntries, searchEntries, getProfiles } from '../../api/entries';
import { getEntryTags as getAllEntryTags } from '../../api/tags';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import type { JournalEntry, Tag, Profile } from '../../types';
import QueryError from '../common/QueryError';
import './EntryList.css';

interface EntryListProps {
  selectedEntryId: number | null;
  onSelectEntry: (entryId: number) => void;
  onNewEntry: () => void;
  onExport: () => void;
  onImport: () => void;
}

import { formatDate } from '../../utils/formatting';

export default function EntryList({
  selectedEntryId,
  onSelectEntry,
  onNewEntry,
  onExport,
  onImport,
}: EntryListProps) {
  const [query, setQuery] = useState('');
  const [filterTagId, setFilterTagId] = useState<number | undefined>(undefined);
  const [filterQuerentId, setFilterQuerentId] = useState<number | undefined>(undefined);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  // Search is live: results filter as you type (debounced so we don't
  // query on every keystroke). Any text or filter = searching.
  const debouncedQuery = useDebouncedValue(query, 300);
  const isSearching =
    debouncedQuery.trim().length > 0 ||
    filterTagId !== undefined ||
    filterQuerentId !== undefined ||
    dateFrom !== '' ||
    dateTo !== '';

  const { data: tags = [] } = useQuery<Tag[]>({
    queryKey: ['entry-tags'],
    queryFn: getAllEntryTags,
  });

  const { data: profiles = [] } = useQuery<Profile[]>({
    queryKey: ['profiles'],
    queryFn: getProfiles,
  });

  // Entries load in pages so the journal never silently truncates —
  // a daily practitioner passes any fixed cap within months. A full
  // page means there may be older entries; a short page is the end.
  const PAGE_SIZE = 100;
  const {
    data: entryPages,
    isLoading: entriesLoading,
    isError: entriesError,
    refetch: refetchEntries,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['entries'],
    queryFn: ({ pageParam }) => getEntries(PAGE_SIZE, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage: JournalEntry[], allPages: JournalEntry[][]) =>
      lastPage.length === PAGE_SIZE ? allPages.length * PAGE_SIZE : undefined,
    enabled: !isSearching,
  });
  const allEntries = useMemo(
    () => (entryPages?.pages ?? []).flat(),
    [entryPages],
  );

  const searchParams = isSearching
    ? {
        query: debouncedQuery.trim() || undefined,
        tag_ids: filterTagId ? [filterTagId] : undefined,
        querent_id: filterQuerentId,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }
    : null;

  const {
    data: searchResults = [],
    isLoading: searchLoading,
    isError: searchError,
    refetch: refetchSearch,
  } = useQuery<JournalEntry[]>({
    queryKey: ['entry-search', searchParams],
    queryFn: () => searchEntries(searchParams!),
    enabled: isSearching && searchParams !== null,
    // Show the previous results while the next keystroke's search runs
    // so the list doesn't flash empty between characters.
    placeholderData: keepPreviousData,
  });

  const entries = isSearching ? searchResults : allEntries;
  const loading = isSearching ? searchLoading : entriesLoading;
  const loadError = isSearching ? searchError : entriesError;
  const retry = isSearching ? refetchSearch : refetchEntries;

  const clearSearch = useCallback(() => {
    setQuery('');
    setFilterTagId(undefined);
    setFilterQuerentId(undefined);
    setDateFrom('');
    setDateTo('');
  }, []);
  const hasAnyFilter =
    query !== '' || filterTagId !== undefined || filterQuerentId !== undefined ||
    dateFrom !== '' || dateTo !== '';

  return (
    <div className="entry-list">
      <div className="entry-list__header">
        <h2 className="entry-list__title">Journal</h2>
        <button className="entry-list__btn" onClick={onNewEntry}>+ New</button>
      </div>

      <div className="entry-list__search">
        <input
          className="entry-list__search-input"
          type="text"
          placeholder="Search entries..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {hasAnyFilter && (
          <button
            className="entry-list__btn entry-list__btn--sm entry-list__btn--clear"
            onClick={clearSearch}
          >
            Clear
          </button>
        )}
      </div>

      <div className="entry-list__filters">
        {tags.length > 0 && (
          <select
            className="entry-list__tag-filter"
            value={filterTagId ?? ''}
            onChange={(e) => setFilterTagId(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">All Tags</option>
            {tags.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        )}
        {profiles.length > 0 && (
          <select
            className="entry-list__tag-filter"
            value={filterQuerentId ?? ''}
            onChange={(e) => setFilterQuerentId(e.target.value ? Number(e.target.value) : undefined)}
            title="Filter by querent"
          >
            <option value="">Any Querent</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        )}
      </div>
      <div className="entry-list__filters entry-list__filters--dates">
        <input
          type="date"
          className="entry-list__date-filter"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          title="Readings from this date"
        />
        <span className="entry-list__date-sep">to</span>
        <input
          type="date"
          className="entry-list__date-filter"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          title="Readings up to this date (inclusive)"
        />
      </div>

      <div className="entry-list__rows">
        {loading && <div className="entry-list__loading">Loading...</div>}
        {!loading && loadError && (
          <QueryError what="journal entries" onRetry={() => retry()} />
        )}
        {!loading && !loadError && entries.length === 0 && (
          <div className="entry-list__empty">
            {isSearching ? 'No entries found.' : 'No journal entries yet.'}
          </div>
        )}
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={`entry-list__row ${entry.id === selectedEntryId ? 'entry-list__row--selected' : ''}`}
            onClick={() => onSelectEntry(entry.id)}
          >
            <div className="entry-list__row-date">
              {formatDate(entry.reading_datetime || entry.created_at)}
            </div>
            <div className="entry-list__row-title">
              {entry.title || 'Untitled Entry'}
            </div>
            {entry.location_name && (
              <div className="entry-list__row-location">{entry.location_name}</div>
            )}
          </div>
        ))}
        {!isSearching && hasNextPage && (
          <button
            className="entry-list__load-older"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? 'Loading…' : 'Load older entries'}
          </button>
        )}
      </div>

      <div className="entry-list__footer">
        <button className="entry-list__btn entry-list__btn--sm" onClick={onExport}>
          Export
        </button>
        <button className="entry-list__btn entry-list__btn--sm" onClick={onImport}>
          Import
        </button>
      </div>
    </div>
  );
}
