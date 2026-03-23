import type { SpreadPosition } from '../../types';
import './PositionLegend.css';

interface PositionLegendProps {
  positions: SpreadPosition[];
  selectedIndex: number | null;
  onSelectIndex: (index: number | null) => void;
  /** When provided, shows up/down reorder buttons on each position. */
  onReorder?: (fromIndex: number, toIndex: number) => void;
}

export default function PositionLegend({
  positions,
  selectedIndex,
  onSelectIndex,
  onReorder,
}: PositionLegendProps) {
  if (positions.length === 0) {
    return (
      <div className="pos-legend">
        <h3 className="pos-legend__title">Position Legend</h3>
        <div className="pos-legend__empty">
          No positions defined. Click "Add Position" to start designing.
        </div>
      </div>
    );
  }

  const handleMove = (idx: number, direction: -1 | 1) => {
    if (!onReorder) return;
    const target = idx + direction;
    if (target < 0 || target >= positions.length) return;
    onReorder(idx, target);
  };

  return (
    <div className="pos-legend">
      <h3 className="pos-legend__title">Position Legend</h3>
      <div className="pos-legend__list">
        {positions.map((pos, idx) => (
          <div
            key={idx}
            className={`pos-legend__item ${idx === selectedIndex ? 'pos-legend__item--selected' : ''}`}
            onClick={() => onSelectIndex(idx === selectedIndex ? null : idx)}
          >
            <span className="pos-legend__key">{pos.key || idx + 1}</span>
            <span className="pos-legend__label">{pos.label}</span>
            {pos.rotated && <span className="pos-legend__rotated" title="Rotated">↺</span>}
            {onReorder && (
              <span className="pos-legend__reorder">
                <button
                  className="pos-legend__move-btn"
                  disabled={idx === 0}
                  onClick={(e) => { e.stopPropagation(); handleMove(idx, -1); }}
                  title="Move up"
                  aria-label={`Move ${pos.label} up`}
                >
                  ▲
                </button>
                <button
                  className="pos-legend__move-btn"
                  disabled={idx === positions.length - 1}
                  onClick={(e) => { e.stopPropagation(); handleMove(idx, 1); }}
                  title="Move down"
                  aria-label={`Move ${pos.label} down`}
                >
                  ▼
                </button>
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
