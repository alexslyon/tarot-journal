import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEntries, searchEntries } from '../../api/entries';
import { getEntryTags as getAllEntryTags } from '../../api/tags';
import type { JournalEntry, Tag } from '../../types';
import './EntryList.css';

interface EntryListProps {
  selectedEntryId: number | null;
  onSelectEntry: (entryId: number) => void;
  onNewEntry: () => void;
  onExport: () => void;
  onImport: () => void;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

export default function EntryList({
  selectedEntryId,
  onSelectEntry,
  onNewEntry,
  onExport,
  onImport,
}: EntryListProps) {
  const [query, setQuery] = useState('');
  const [filterTagId, setFilterTagId] = useState<number | undefined>(undefined);
  const [isSearching, setIsSearching] = useState(false);

  const { data: tags = [] } = useQuery<Tag[]>({
    queryKey: ['entry-tags'],
    queryFn: getAllEntryTags,
  });

  const { data: allEntries = [], isLoading: entriesLoading } = useQuery<JournalEntry[]>({
    queryKey: ['entries'],
    queryFn: () => getEntries(200, 0),
    enabled: !isSearching,
  });

  const searchParams = isSearching
    ? {
        query: query.trim() || undefined,
        tag_ids: filterTagId ? [filterTagId] : undefined,
      }
    : null;

  const { data: searchResults = [], isLoading: searchLoading } = useQuery<JournalEntry[]>({
    queryKey: ['entry-search', searchParams],
    queryFn: () => searchEntries(searchParams!),
    enabled: isSearching && searchParams !== null,
  });

  const entries = isSearching ? searchResults : allEntries;
  const loading = isSearching ? searchLoading : entriesLoading;

  const doSearch = useCallback(() => {
    if (!query.trim() && !filterTagId) return;
    setIsSearching(true);
  }, [query, filterTagId]);

  const clearSearch = useCallback(() => {
    setQuery('');
    setFilterTagId(undefined);
    setIsSearching(false);
  }, []);

  const handleTagFilter = (tagId: number | undefined) => {
    setFilterTagId(tagId);
    if (tagId || query.trim()) {
      setIsSearching(true);
    } else {
      setIsSearching(false);
    }
  };

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
          onKeyDown={(e) => e.key === 'Enter' && doSearch()}
        />
        <button className="entry-list__btn entry-list__btn--sm" onClick={doSearch}>
          Search
        </button>
        {isSearching && (
          <button
            className="entry-list__btn entry-list__btn--sm entry-list__btn--clear"
            onClick={clearSearch}
          >
            Clear
          </button>
        )}
      </div>

      {tags.length > 0 && (
        <div className="entry-list__filters">
          <select
            className="entry-list__tag-filter"
            value={filterTagId ?? ''}
            onChange={(e) => handleTagFilter(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">All Tags</option>
            {tags.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
      )}

      <div className="entry-list__rows">
        {loading && <div className="entry-list__loading">Loading...</div>}
        {!loading && entries.length === 0 && (
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
