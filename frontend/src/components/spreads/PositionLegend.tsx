import { useState } from 'react';
import type { SpreadPosition } from '../../types';
import './PositionLegend.css';

interface PositionLegendProps {
  positions: SpreadPosition[];
  selectedIndex: number | null;
  onSelectIndex: (index: number | null) => void;
  /** When provided, positions can be reordered: drag a row to a new
   *  spot, or use the up/down buttons (keyboard-friendly). */
  onReorder?: (fromIndex: number, toIndex: number) => void;
  /** When provided, the key and label become click-to-edit inline —
   *  no need to select the position on the canvas first. */
  onUpdatePosition?: (index: number, updates: Partial<SpreadPosition>) => void;
}

export default function PositionLegend({
  positions,
  selectedIndex,
  onSelectIndex,
  onReorder,
  onUpdatePosition,
}: PositionLegendProps) {
  // Inline editing: which cell is being edited and its draft value.
  const [editing, setEditing] = useState<{ idx: number; field: 'key' | 'label' } | null>(null);
  const [draft, setDraft] = useState('');

  const startEdit = (idx: number, field: 'key' | 'label', current: string) => {
    if (!onUpdatePosition) return;
    setEditing({ idx, field });
    setDraft(current);
  };

  const commitEdit = () => {
    if (!editing || !onUpdatePosition) return;
    onUpdatePosition(editing.idx, { [editing.field]: draft.trim() });
    setEditing(null);
  };
  // Drag-and-drop reordering (same HTML5 DnD pattern as the Reference
  // Sources field list). Index-based since legend rows have no ids.
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);

  const handleDrop = (targetIdx: number) => {
    const from = draggedIdx;
    setDraggedIdx(null);
    setDragOverIdx(null);
    if (!onReorder || from === null || from === targetIdx) return;
    onReorder(from, targetIdx);
  };
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
            className={`pos-legend__item ${idx === selectedIndex ? 'pos-legend__item--selected' : ''}${draggedIdx === idx ? ' pos-legend__item--dragging' : ''}${dragOverIdx === idx && draggedIdx !== idx ? ' pos-legend__item--drag-over' : ''}`}
            onClick={() => onSelectIndex(idx === selectedIndex ? null : idx)}
            draggable={!!onReorder}
            onDragStart={(e) => {
              e.dataTransfer.effectAllowed = 'move';
              setDraggedIdx(idx);
            }}
            onDragOver={(e) => {
              if (draggedIdx === null) return;
              e.preventDefault();
              e.dataTransfer.dropEffect = 'move';
              if (draggedIdx !== idx) setDragOverIdx(idx);
            }}
            onDrop={(e) => {
              e.preventDefault();
              handleDrop(idx);
            }}
            onDragEnd={() => {
              setDraggedIdx(null);
              setDragOverIdx(null);
            }}
          >
            {onReorder && (
              <span className="pos-legend__drag-handle" aria-hidden="true" title="Drag to reorder">
                ⋮⋮
              </span>
            )}
            {editing?.idx === idx && editing.field === 'key' ? (
              <input
                className="pos-legend__edit pos-legend__edit--key"
                value={draft}
                autoFocus
                onChange={(e) => setDraft(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                onBlur={commitEdit}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitEdit();
                  if (e.key === 'Escape') setEditing(null);
                }}
              />
            ) : (
              <span
                className={`pos-legend__key ${onUpdatePosition ? 'pos-legend__cell--editable' : ''}`}
                title={onUpdatePosition ? 'Click to edit the key' : undefined}
                onClick={(e) => {
                  if (!onUpdatePosition) return;
                  e.stopPropagation();
                  startEdit(idx, 'key', String(pos.key ?? idx + 1));
                }}
              >
                {pos.key || idx + 1}
              </span>
            )}
            {editing?.idx === idx && editing.field === 'label' ? (
              <input
                className="pos-legend__edit"
                value={draft}
                autoFocus
                onChange={(e) => setDraft(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                onBlur={commitEdit}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitEdit();
                  if (e.key === 'Escape') setEditing(null);
                }}
              />
            ) : (
              <span
                className={`pos-legend__label ${onUpdatePosition ? 'pos-legend__cell--editable' : ''}`}
                title={onUpdatePosition ? 'Click to edit the name' : undefined}
                onClick={(e) => {
                  if (!onUpdatePosition) return;
                  e.stopPropagation();
                  startEdit(idx, 'label', pos.label || '');
                }}
              >
                {pos.label}
              </span>
            )}
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
