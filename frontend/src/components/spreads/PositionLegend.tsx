import type { SpreadPosition } from '../../types';
import './PositionLegend.css';

interface PositionLegendProps {
  positions: SpreadPosition[];
  selectedIndex: number | null;
  onSelectIndex: (index: number | null) => void;
}

export default function PositionLegend({
  positions,
  selectedIndex,
  onSelectIndex,
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
          </div>
        ))}
      </div>
    </div>
  );
}
