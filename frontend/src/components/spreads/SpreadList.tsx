import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getSpreads, updateSpread } from '../../api/spreads';
import { useToast } from '../../context/ToastContext';
import type { Spread } from '../../types';
import QueryError from '../common/QueryError';
import './SpreadList.css';

interface SpreadListProps {
  selectedSpreadId: number | null;
  onSelect: (spread: Spread) => void;
  onNew: () => void;
  onClone: () => void;
  onDelete: () => void;
}

type SortKey = 'name' | 'positions';

function positionCount(spread: Spread): number {
  return Array.isArray(spread.positions) ? spread.positions.length : 0;
}

export default function SpreadList({
  selectedSpreadId,
  onSelect,
  onNew,
  onClone,
  onDelete,
}: SpreadListProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { data: spreads = [], isLoading, isError, refetch } = useQuery<Spread[]>({
    queryKey: ['spreads'],
    queryFn: getSpreads,
  });

  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [showArchived, setShowArchived] = useState(false);

  const selected = spreads.find(s => s.id === selectedSpreadId) ?? null;

  const { active, archived } = useMemo(() => {
    const q = search.trim().toLowerCase();
    const matches = (s: Spread) => !q || s.name.toLowerCase().includes(q);
    const sorted = [...spreads].sort((a, b) =>
      sortKey === 'positions'
        ? positionCount(a) - positionCount(b) || a.name.localeCompare(b.name)
        : a.name.localeCompare(b.name));
    return {
      active: sorted.filter(s => !s.archived && matches(s)),
      archived: sorted.filter(s => !!s.archived && matches(s)),
    };
  }, [spreads, search, sortKey]);

  const handleArchiveToggle = async () => {
    if (!selected) return;
    const archiving = !selected.archived;
    try {
      await updateSpread(selected.id, { archived: archiving });
      queryClient.invalidateQueries({ queryKey: ['spreads'] });
      showToast(
        archiving
          ? `Archived "${selected.name}" — existing journal entries keep it.`
          : `Restored "${selected.name}".`,
        'success',
      );
      if (archiving && !showArchived) setShowArchived(true);
    } catch {
      showToast('Failed to update the spread.');
    }
  };

  const renderRow = (spread: Spread) => (
    <div
      key={spread.id}
      className={`spread-list__row ${spread.id === selectedSpreadId ? 'spread-list__row--selected' : ''}`}
      onClick={() => onSelect(spread)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(spread);
        }
      }}
    >
      <span className="spread-list__name">{spread.name}</span>
      <span className="spread-list__count">{positionCount(spread)} pos</span>
    </div>
  );

  return (
    <div className="spread-list">
      <div className="spread-list__header">
        <h2 className="spread-list__title">Spreads</h2>
        <div className="spread-list__actions">
          <button onClick={onNew} title="New spread">New</button>
          <button onClick={onClone} disabled={!selectedSpreadId} title="Clone selected">Clone</button>
          <button
            onClick={handleArchiveToggle}
            disabled={!selected}
            title={selected?.archived
              ? 'Restore this spread to the active list'
              : 'Hide from the list and pickers without deleting — older entries keep it'}
          >
            {selected?.archived ? 'Restore' : 'Archive'}
          </button>
          <button onClick={onDelete} disabled={!selectedSpreadId} title="Delete selected">Delete</button>
        </div>
      </div>

      <div className="spread-list__filters">
        <input
          type="search"
          className="spread-list__search"
          placeholder="Search spreads..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="spread-list__sort-bar">
          <span className="spread-list__sort-label">Sort:</span>
          <button
            className={`spread-list__sort-btn ${sortKey === 'name' ? 'spread-list__sort-btn--active' : ''}`}
            onClick={() => setSortKey('name')}
          >
            Name
          </button>
          <button
            className={`spread-list__sort-btn ${sortKey === 'positions' ? 'spread-list__sort-btn--active' : ''}`}
            onClick={() => setSortKey('positions')}
          >
            # Positions
          </button>
        </div>
      </div>

      <div className="spread-list__rows">
        {isLoading && <div className="spread-list__loading">Loading...</div>}
        {!isLoading && isError && (
          <QueryError what="spreads" onRetry={() => refetch()} />
        )}
        {active.map(renderRow)}
        {!isLoading && !isError && active.length === 0 && (
          <div className="spread-list__empty">
            {search ? 'No spreads match.' : 'No spreads yet'}
          </div>
        )}

        {archived.length > 0 && (
          <div className="spread-list__archived">
            <button
              className="spread-list__archived-toggle"
              aria-expanded={showArchived}
              onClick={() => setShowArchived(o => !o)}
            >
              <span className={`spread-list__chevron ${showArchived ? 'spread-list__chevron--open' : ''}`} aria-hidden="true">▸</span>
              Archived ({archived.length})
            </button>
            {showArchived && archived.map(renderRow)}
          </div>
        )}
      </div>
    </div>
  );
}
