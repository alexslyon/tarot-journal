import { useState, useRef, useCallback, useMemo } from 'react';
import type { SpreadPosition, DeckSlot } from '../../types';
import './SpreadDesigner.css';

// Minimum canvas dimensions (used when empty or for small spreads)
const MIN_CANVAS_W = 620;
const MIN_CANVAS_H = 460;
const GRID_SIZE = 20;
const DEFAULT_W = 80;
const DEFAULT_H = 120;
const HANDLE_SIZE = 10;
const CANVAS_PADDING = 20; // Padding around content

interface SpreadDesignerProps {
  positions: SpreadPosition[];
  onChange: (positions: SpreadPosition[]) => void;
  selectedIndex: number | null;
  onSelectIndex: (index: number | null) => void;
  deckSlots: DeckSlot[];
}

export default function SpreadDesigner({
  positions,
  onChange,
  selectedIndex,
  onSelectIndex,
  deckSlots,
}: SpreadDesignerProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [gridEnabled, setGridEnabled] = useState(true);
  const [dragging, setDragging] = useState<{
    index: number;
    startMouseX: number;
    startMouseY: number;
    startPosX: number;
    startPosY: number;
  } | null>(null);
  const [resizing, setResizing] = useState<{
    index: number;
    startMouseX: number;
    startMouseY: number;
    startW: number;
    startH: number;
  } | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    index: number;
  } | null>(null);
  const [showSlotMenu, setShowSlotMenu] = useState(false);

  // Calculate dynamic canvas dimensions based on position bounding box
  const canvasDimensions = useMemo(() => {
    if (positions.length === 0) {
      return { width: MIN_CANVAS_W, height: MIN_CANVAS_H };
    }
    // Find the bounding box of all positions
    const maxX = Math.max(...positions.map(p => (p.x || 0) + (p.width || DEFAULT_W)));
    const maxY = Math.max(...positions.map(p => (p.y || 0) + (p.height || DEFAULT_H)));
    // Use the larger of content bounds + padding or minimum dimensions
    return {
      width: Math.max(MIN_CANVAS_W, maxX + CANVAS_PADDING),
      height: Math.max(MIN_CANVAS_H, maxY + CANVAS_PADDING),
    };
  }, [positions]);

  const snap = useCallback(
    (val: number) => (gridEnabled ? Math.round(val / GRID_SIZE) * GRID_SIZE : Math.round(val)),
    [gridEnabled],
  );

  // Convert screen coordinates to viewBox (logical) coordinates
  const getSVGPoint = useCallback(
    (e: React.MouseEvent) => {
      const svg = svgRef.current;
      if (!svg) return { x: 0, y: 0 };
      const rect = svg.getBoundingClientRect();
      // Calculate scale factor from rendered size to viewBox size
      const scaleX = canvasDimensions.width / rect.width;
      const scaleY = canvasDimensions.height / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      };
    },
    [canvasDimensions],
  );

  const handleAddPosition = () => {
    const label = window.prompt('Position label:', `Position ${positions.length + 1}`);
    if (!label) return;
    const cx = snap(canvasDimensions.width / 2 - DEFAULT_W / 2);
    const cy = snap(canvasDimensions.height / 2 - DEFAULT_H / 2);
    onChange([
      ...positions,
      { x: cx, y: cy, width: DEFAULT_W, height: DEFAULT_H, label, key: String(positions.length + 1) },
    ]);
    onSelectIndex(positions.length);
  };

  const handleClearAll = () => {
    if (positions.length === 0) return;
    if (!window.confirm('Clear all positions?')) return;
    onChange([]);
    onSelectIndex(null);
  };

  // ── Mouse handlers ──

  const handlePositionMouseDown = (e: React.MouseEvent, index: number) => {
    if (e.button !== 0) return; // left click only
    e.stopPropagation();
    const pt = getSVGPoint(e);
    const pos = positions[index];
    setDragging({
      index,
      startMouseX: pt.x,
      startMouseY: pt.y,
      startPosX: pos.x,
      startPosY: pos.y,
    });
    onSelectIndex(index);
    setContextMenu(null);
  };

  const handleResizeMouseDown = (e: React.MouseEvent, index: number) => {
    e.stopPropagation();
    e.preventDefault();
    const pt = getSVGPoint(e);
    const pos = positions[index];
    setResizing({
      index,
      startMouseX: pt.x,
      startMouseY: pt.y,
      startW: pos.width,
      startH: pos.height,
    });
  };

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const pt = getSVGPoint(e);

      if (dragging) {
        const dx = pt.x - dragging.startMouseX;
        const dy = pt.y - dragging.startMouseY;
        let newX = snap(dragging.startPosX + dx);
        let newY = snap(dragging.startPosY + dy);
        // Only prevent negative coordinates; canvas will grow to fit
        newX = Math.max(0, newX);
        newY = Math.max(0, newY);
        const updated = [...positions];
        updated[dragging.index] = { ...updated[dragging.index], x: newX, y: newY };
        onChange(updated);
      }

      if (resizing) {
        const dx = pt.x - resizing.startMouseX;
        const dy = pt.y - resizing.startMouseY;
        const newW = snap(Math.max(40, resizing.startW + dx));
        const newH = snap(Math.max(40, resizing.startH + dy));
        // No upper limit on size; canvas will grow to fit
        const updated = [...positions];
        updated[resizing.index] = { ...updated[resizing.index], width: newW, height: newH };
        onChange(updated);
      }
    },
    [dragging, resizing, positions, onChange, getSVGPoint, snap],
  );

  const handleMouseUp = useCallback(() => {
    setDragging(null);
    setResizing(null);
  }, []);

  const handleCanvasClick = () => {
    onSelectIndex(null);
    setContextMenu(null);
  };

  // ── Context menu ──

  const handleContextMenu = (e: React.MouseEvent, index: number) => {
    e.preventDefault();
    e.stopPropagation();
    onSelectIndex(index);
    setContextMenu({ x: e.clientX, y: e.clientY, index });
  };

  const handleEditPosition = () => {
    if (contextMenu === null) return;
    const pos = positions[contextMenu.index];
    const label = window.prompt('Position label:', pos.label);
    if (label === null) return;
    const key = window.prompt('Legend key (number or letter):', pos.key || String(contextMenu.index + 1));
    const updated = [...positions];
    updated[contextMenu.index] = { ...updated[contextMenu.index], label, key: key || undefined };
    onChange(updated);
    setContextMenu(null);
  };

  const handleRotatePosition = () => {
    if (contextMenu === null) return;
    const pos = positions[contextMenu.index];
    const updated = [...positions];
    updated[contextMenu.index] = {
      ...updated[contextMenu.index],
      width: pos.height,
      height: pos.width,
      rotated: !pos.rotated,
    };
    onChange(updated);
    setContextMenu(null);
  };

  const handleDeletePosition = () => {
    if (contextMenu === null) return;
    const updated = positions.filter((_, i) => i !== contextMenu.index);
    onChange(updated);
    onSelectIndex(null);
    setContextMenu(null);
  };

  const handleSetDeckSlot = (slotKey: string | null) => {
    if (contextMenu === null) return;
    const updated = [...positions];
    updated[contextMenu.index] = {
      ...updated[contextMenu.index],
      deck_slot: slotKey || undefined,
    };
    onChange(updated);
    setShowSlotMenu(false);
    setContextMenu(null);
  };

  // ── Grid lines ──

  const gridLines = [];
  if (gridEnabled) {
    for (let x = GRID_SIZE; x < canvasDimensions.width; x += GRID_SIZE) {
      gridLines.push(
        <line key={`gx-${x}`} x1={x} y1={0} x2={x} y2={canvasDimensions.height} className="designer__grid-line" />,
      );
    }
    for (let y = GRID_SIZE; y < canvasDimensions.height; y += GRID_SIZE) {
      gridLines.push(
        <line key={`gy-${y}`} x1={0} y1={y} x2={canvasDimensions.width} y2={y} className="designer__grid-line" />,
      );
    }
  }

  return (
    <div className="designer">
      <div className="designer__toolbar">
        <button onClick={handleAddPosition}>+ Add Position</button>
        <button onClick={handleClearAll} disabled={positions.length === 0}>Clear All</button>
        <label className="designer__grid-toggle">
          <input
            type="checkbox"
            checked={gridEnabled}
            onChange={(e) => setGridEnabled(e.target.checked)}
          />
          <span>Snap to Grid</span>
        </label>
      </div>

      <div className="designer__canvas-wrapper">
        <svg
          ref={svgRef}
          className="designer__canvas"
          viewBox={`0 0 ${canvasDimensions.width} ${canvasDimensions.height}`}
          style={{ aspectRatio: `${canvasDimensions.width} / ${canvasDimensions.height}` }}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onClick={handleCanvasClick}
        >
          {/* Background */}
          <rect width={canvasDimensions.width} height={canvasDimensions.height} className="designer__bg" />

          {/* Grid */}
          {gridLines}

          {/* Positions */}
          {positions.map((pos, idx) => {
            const isSelected = idx === selectedIndex;
            return (
              <g key={idx}>
                {/* Card rectangle */}
                <rect
                  x={pos.x}
                  y={pos.y}
                  width={pos.width}
                  height={pos.height}
                  className={`designer__position ${isSelected ? 'designer__position--selected' : ''}`}
                  onMouseDown={(e) => handlePositionMouseDown(e, idx)}
                  onContextMenu={(e) => handleContextMenu(e, idx)}
                  style={{ cursor: dragging ? 'grabbing' : 'grab' }}
                />

                {/* Key badge (top-left corner) */}
                <circle
                  cx={pos.x + 12}
                  cy={pos.y + 12}
                  r={9}
                  className="designer__key-bg"
                  onMouseDown={(e) => handlePositionMouseDown(e, idx)}
                />
                <text
                  x={pos.x + 12}
                  y={pos.y + 16}
                  className="designer__key-text"
                  onMouseDown={(e) => handlePositionMouseDown(e, idx)}
                >
                  {pos.key || idx + 1}
                </text>

                {/* Label (center) */}
                <text
                  x={pos.x + pos.width / 2}
                  y={pos.y + pos.height / 2 + 4}
                  className="designer__label-text"
                  onMouseDown={(e) => handlePositionMouseDown(e, idx)}
                >
                  {pos.label}
                </text>

                {/* Rotated indicator */}
                {pos.rotated && (
                  <text
                    x={pos.x + pos.width - 14}
                    y={pos.y + 15}
                    className="designer__rotated-icon"
                    onMouseDown={(e) => handlePositionMouseDown(e, idx)}
                  >
                    ↺
                  </text>
                )}

                {/* Deck slot indicator (bottom) - only show if multiple slots */}
                {deckSlots.length > 1 && (
                  <text
                    x={pos.x + pos.width / 2}
                    y={pos.y + pos.height - 6}
                    className="designer__slot-text"
                    onMouseDown={(e) => handlePositionMouseDown(e, idx)}
                  >
                    {pos.deck_slot || deckSlots[0]?.key || 'A'}
                  </text>
                )}

                {/* Resize handle (bottom-right, shown when selected) */}
                {isSelected && (
                  <rect
                    x={pos.x + pos.width - HANDLE_SIZE}
                    y={pos.y + pos.height - HANDLE_SIZE}
                    width={HANDLE_SIZE}
                    height={HANDLE_SIZE}
                    className="designer__resize-handle"
                    onMouseDown={(e) => handleResizeMouseDown(e, idx)}
                    style={{ cursor: 'nwse-resize' }}
                  />
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Context menu */}
      {contextMenu && (
        <>
          <div className="designer__menu-overlay" onClick={() => { setContextMenu(null); setShowSlotMenu(false); }} />
          <div
            className="designer__context-menu"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <button onClick={handleEditPosition}>Edit Label / Key</button>
            <button onClick={handleRotatePosition}>
              {positions[contextMenu.index]?.rotated ? 'Unrotate' : 'Rotate 90°'}
            </button>
            {/* Only show deck slot option if there are multiple slots */}
            {deckSlots.length > 1 && (
              <>
                <button onClick={() => setShowSlotMenu(!showSlotMenu)}>
                  Deck Slot: {positions[contextMenu.index]?.deck_slot || deckSlots[0]?.key || 'A'} ▸
                </button>
                {showSlotMenu && (
                  <div className="designer__submenu">
                    {deckSlots.map((slot) => (
                      <button key={slot.key} onClick={() => handleSetDeckSlot(slot.key)}>
                        {slot.key}: {slot.label || slot.cartomancy_type}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
            <button onClick={handleDeletePosition} className="designer__menu-danger">Delete</button>
          </div>
        </>
      )}
    </div>
  );
}
