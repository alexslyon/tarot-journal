import { useQuery } from '@tanstack/react-query';
import { getSpreads } from '../../api/spreads';
import type { Spread } from '../../types';
import './SpreadList.css';

interface SpreadListProps {
  selectedSpreadId: number | null;
  onSelect: (spread: Spread) => void;
  onNew: () => void;
  onClone: () => void;
  onDelete: () => void;
}

export default function SpreadList({
  selectedSpreadId,
  onSelect,
  onNew,
  onClone,
  onDelete,
}: SpreadListProps) {
  const { data: spreads = [], isLoading } = useQuery<Spread[]>({
    queryKey: ['spreads'],
    queryFn: getSpreads,
  });

  return (
    <div className="spread-list">
      <div className="spread-list__header">
        <h2 className="spread-list__title">Spreads</h2>
        <div className="spread-list__actions">
          <button onClick={onNew} title="New spread">New</button>
          <button onClick={onClone} disabled={!selectedSpreadId} title="Clone selected">Clone</button>
          <button onClick={onDelete} disabled={!selectedSpreadId} title="Delete selected">Delete</button>
        </div>
      </div>

      <div className="spread-list__rows">
        {isLoading && <div className="spread-list__loading">Loading...</div>}
        {spreads.map((spread) => {
          const positions = Array.isArray(spread.positions) ? spread.positions : [];
          return (
            <div
              key={spread.id}
              className={`spread-list__row ${spread.id === selectedSpreadId ? 'spread-list__row--selected' : ''}`}
              onClick={() => onSelect(spread)}
            >
              <span className="spread-list__name">{spread.name}</span>
              <span className="spread-list__count">{positions.length} pos</span>
            </div>
          );
        })}
        {!isLoading && spreads.length === 0 && (
          <div className="spread-list__empty">No spreads yet</div>
        )}
      </div>
    </div>
  );
}
