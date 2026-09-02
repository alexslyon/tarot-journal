import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import type { SpreadPosition, DeckSlot } from '../../types';
import './SpreadDesigner.css';
import { confirmDialog } from '../common/ConfirmDialog';
import { slotTypeLabel } from '../../utils/formatting';

// Minimum canvas dimensions (used when empty or for small spreads);
// the toolbar lets the user raise them per session.
const MIN_CANVAS_W = 620;
const MIN_CANVAS_H = 460;
const GRID_SIZE = 20;
const DEFAULT_W = 80;
const DEFAULT_H = 120;
const HANDLE_SIZE = 16;
// Working margin shown around the spread on ALL four sides, so there
// is always room to drag a card outward in any direction.
const WORK_MARGIN = 60;

interface SpreadDesignerProps {
  positions: SpreadPosition[];
  onChange: (positions: SpreadPosition[]) => void;
  selectedIndex: number | null;
  onSelectIndex: (index: number | null) => void;
  deckSlots: DeckSlot[];
  readOnly?: boolean;
  showLabels?: boolean;
}

export default function SpreadDesigner({
  positions,
  onChange,
  selectedIndex,
  onSelectIndex,
  deckSlots,
  readOnly = false,
  showLabels,
}: SpreadDesignerProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [gridEnabled, setGridEnabled] = useState(true);
  const [showLabelsOnPositions, setShowLabelsOnPositions] = useState(false);
  const [dragging, setDragging] = useState<{
    index: number;
    startMouseX: number;
    startMouseY: number;
    startPosX: number;
    startPosY: number;
  } | null>(null);
  const [resizing, setResizing] = useState<{
    index: number;
    startClientX: number;  // Screen coordinates (stable during resize)
    startClientY: number;
    startW: number;
    startH: number;
    scaleX: number;  // Locked scale factor at start of resize
    scaleY: number;
  } | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    index: number;
  } | null>(null);
  const [showSlotMenu, setShowSlotMenu] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editLabel, setEditLabel] = useState('');
  const [editKey, setEditKey] = useState('');

  // Build a render-order list: positions sorted by z_index (lower draws first = behind)
  // while preserving original array indices for data operations
  const renderOrder = useMemo(() => {
    return positions
      .map((pos, idx) => ({ pos, idx }))
      .sort((a, b) => (a.pos.z_index ?? a.idx) - (b.pos.z_index ?? b.idx));
  }, [positions]);

  // User-adjustable minimum canvas size (session-level working area).
  const [minCanvas, setMinCanvas] = useState({ w: MIN_CANVAS_W, h: MIN_CANVAS_H });

  // The spread's bounding box plus the working margin — what the
  // viewport must at least contain.
  const contentBox = useMemo(() => {
    if (positions.length === 0) return null;
    const minX = Math.min(...positions.map(p => p.x || 0));
    const minY = Math.min(...positions.map(p => p.y || 0));
    const maxX = Math.max(...positions.map(p => (p.x || 0) + (p.width || DEFAULT_W)));
    const maxY = Math.max(...positions.map(p => (p.y || 0) + (p.height || DEFAULT_H)));
    return {
      x: minX - WORK_MARGIN,
      y: minY - WORK_MARGIN,
      w: maxX - minX + 2 * WORK_MARGIN,
      h: maxY - minY + 2 * WORK_MARGIN,
    };
  }, [positions]);

  // A box that hugs the content (centered inside the minimum size).
  const fitBox = useCallback((min: { w: number; h: number }) => {
    if (!contentBox) return { x: 0, y: 0, width: min.w, height: min.h };
    const width = Math.max(contentBox.w, min.w);
    const height = Math.max(contentBox.h, min.h);
    return {
      x: contentBox.x - (width - contentBox.w) / 2,
      y: contentBox.y - (height - contentBox.h) / 2,
      width,
      height,
    };
  }, [contentBox]);

  // Canvas viewport. Crucially it is GROW-ONLY during a session:
  // re-fitting it after every gesture made the whole view lurch by
  // the drag distance on release (the origin tracks the leftmost
  // card when the spread is smaller than the minimum canvas), which
  // read as "I moved a card and everything snapped back". The box
  // only expands when content needs more room; the Fit button
  // re-hugs on demand.
  const [canvasBox, setCanvasBox] = useState(() => fitBox(minCanvas));
  useEffect(() => {
    setCanvasBox(prev => {
      let x = prev.x;
      let y = prev.y;
      let right = prev.x + prev.width;
      let bottom = prev.y + prev.height;
      if (contentBox) {
        x = Math.min(x, contentBox.x);
        y = Math.min(y, contentBox.y);
        right = Math.max(right, contentBox.x + contentBox.w);
        bottom = Math.max(bottom, contentBox.y + contentBox.h);
      }
      if (right - x < minCanvas.w) {
        const extra = (minCanvas.w - (right - x)) / 2;
        x -= extra; right += extra;
      }
      if (bottom - y < minCanvas.h) {
        const extra = (minCanvas.h - (bottom - y)) / 2;
        y -= extra; bottom += extra;
      }
      const next = { x, y, width: right - x, height: bottom - y };
      return (next.x === prev.x && next.y === prev.y
        && next.width === prev.width && next.height === prev.height)
        ? prev : next;
    });
  }, [contentBox, minCanvas]);

  const snap = useCallback(
    (val: number) => (gridEnabled ? Math.round(val / GRID_SIZE) * GRID_SIZE : Math.round(val)),
    [gridEnabled],
  );

  // Convert screen coordinates to viewBox (logical) coordinates.
  // The canvas box is gesture-stable (grow-only), so the mapping
  // can't drift mid-drag.
  const getSVGPoint = useCallback(
    (e: { clientX: number; clientY: number }) => {
      const svg = svgRef.current;
      if (!svg) return { x: 0, y: 0 };
      const rect = svg.getBoundingClientRect();
      const scaleX = canvasBox.width / rect.width;
      const scaleY = canvasBox.height / rect.height;
      return {
        x: canvasBox.x + (e.clientX - rect.left) * scaleX,
        y: canvasBox.y + (e.clientY - rect.top) * scaleY,
      };
    },
    [canvasBox],
  );

  const handleAddPosition = () => {
    // New positions match the size (and rotation) of the selected
    // position — or the last one — so additions to an existing layout
    // fit without hand-resizing. 80×120 only for the first card.
    const template =
      (selectedIndex !== null ? positions[selectedIndex] : undefined) ??
      positions[positions.length - 1];
    const w = template?.width || DEFAULT_W;
    const h = template?.height || DEFAULT_H;
    const cx = snap(canvasBox.x + canvasBox.width / 2 - w / 2);
    const cy = snap(canvasBox.y + canvasBox.height / 2 - h / 2);
    const newIndex = positions.length;
    const defaultLabel = `Position ${newIndex + 1}`;
    const defaultKey = String(newIndex + 1);
    // Place new position on top of the stack
    const maxZ = positions.reduce((max, p, i) => Math.max(max, p.z_index ?? i), -1);
    onChange([
      ...positions,
      {
        x: cx, y: cy, width: w, height: h,
        rotated: template?.rotated || undefined,
        label: defaultLabel, key: defaultKey, z_index: maxZ + 1,
      },
    ]);
    onSelectIndex(newIndex);
    // Open context menu for the new position so user can edit
    // Use a small delay to ensure the position is rendered
    setTimeout(() => {
      const svg = svgRef.current;
      if (svg) {
        const rect = svg.getBoundingClientRect();
        setContextMenu({
          x: rect.left + rect.width / 2,
          y: rect.top + rect.height / 2,
          index: newIndex,
        });
        setEditMode(true);
        setEditLabel(defaultLabel);
        setEditKey(defaultKey);
      }
    }, 0);
  };

  const handleClearAll = async () => {
    if (positions.length === 0) return;
    if (!(await confirmDialog('Clear all positions?'))) return;
    onChange([]);
    onSelectIndex(null);
  };

  // Duplicate a position: same size/rotation, offset one grid step,
  // placed on top. Key clears so the copy shows its own number.
  const duplicatePosition = useCallback((index: number) => {
    const pos = positions[index];
    if (!pos) return;
    const maxZ = positions.reduce((max, p, i) => Math.max(max, p.z_index ?? i), -1);
    onChange([
      ...positions,
      {
        ...pos,
        x: pos.x + GRID_SIZE,
        y: pos.y + GRID_SIZE,
        key: undefined,
        label: pos.label ? `${pos.label} copy` : `Position ${positions.length + 1}`,
        z_index: maxZ + 1,
      },
    ]);
    onSelectIndex(positions.length);
  }, [positions, onChange, onSelectIndex]);

  // Numeric inspector: set one dimension of the selected position
  const setSelectedField = (field: 'x' | 'y' | 'width' | 'height', raw: string) => {
    if (selectedIndex === null) return;
    const n = Number(raw);
    if (!Number.isFinite(n)) return;
    const min = field === 'x' || field === 'y' ? 0 : 40;
    const updated = [...positions];
    updated[selectedIndex] = { ...updated[selectedIndex], [field]: Math.max(min, Math.round(n)) };
    onChange(updated);
  };

  // Apply the selected position's size to every position (respecting
  // each one's own rotation by swapping the dimensions where needed).
  const applySizeToAll = () => {
    if (selectedIndex === null) return;
    const src = positions[selectedIndex];
    if (!src) return;
    onChange(positions.map(p => {
      const sameOrientation = !!p.rotated === !!src.rotated;
      return {
        ...p,
        width: sameOrientation ? src.width : src.height,
        height: sameOrientation ? src.height : src.width,
      };
    }));
  };

  // Keyboard: arrows nudge the selected position by one grid step
  // (Shift = 1px for fine placement); Cmd/Ctrl+D duplicates.
  useEffect(() => {
    if (readOnly || selectedIndex === null) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      )) return;
      if (e.key.toLowerCase() === 'd' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        duplicatePosition(selectedIndex);
        return;
      }
      const step = e.shiftKey ? 1 : GRID_SIZE;
      let dx = 0, dy = 0;
      if (e.key === 'ArrowLeft') dx = -step;
      else if (e.key === 'ArrowRight') dx = step;
      else if (e.key === 'ArrowUp') dy = -step;
      else if (e.key === 'ArrowDown') dy = step;
      else return;
      e.preventDefault();
      const pos = positions[selectedIndex];
      if (!pos) return;
      const updated = [...positions];
      updated[selectedIndex] = { ...pos, x: pos.x + dx, y: pos.y + dy };
      onChange(updated);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [readOnly, selectedIndex, positions, onChange, duplicatePosition]);

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
    if (e.button !== 0) return; // left click only
    e.stopPropagation();
    e.preventDefault();
    const pos = positions[index];
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    // Lock scale factors at gesture start.
    setResizing({
      index,
      startClientX: e.clientX,
      startClientY: e.clientY,
      startW: pos.width,
      startH: pos.height,
      scaleX: canvasBox.width / rect.width,
      scaleY: canvasBox.height / rect.height,
    });
  };

  const handleMouseMove = useCallback(
    (e: { clientX: number; clientY: number }) => {
      if (dragging) {
        const pt = getSVGPoint(e);
        const dx = pt.x - dragging.startMouseX;
        const dy = pt.y - dragging.startMouseY;
        // The card follows the mouse smoothly during the drag; grid
        // snapping is applied once on release, so it doesn't jump
        // between grid cells under the cursor. Negative coordinates
        // are allowed mid-gesture (the canvas has margin on all four
        // sides); mouse-up normalizes them away.
        const newX = Math.round(dragging.startPosX + dx);
        const newY = Math.round(dragging.startPosY + dy);
        const updated = [...positions];
        updated[dragging.index] = { ...updated[dragging.index], x: newX, y: newY };
        onChange(updated);
      }

      if (resizing) {
        // Use locked scale factors from start of resize to avoid jumpy behavior
        // when canvas dimensions change during drag
        const dx = (e.clientX - resizing.startClientX) * resizing.scaleX;
        const dy = (e.clientY - resizing.startClientY) * resizing.scaleY;
        // Smooth while resizing; snapped on release (see handleMouseUp)
        const newW = Math.round(Math.max(40, resizing.startW + dx));
        const newH = Math.round(Math.max(40, resizing.startH + dy));
        // No upper limit on size; canvas will grow to fit
        const updated = [...positions];
        updated[resizing.index] = { ...updated[resizing.index], width: newW, height: newH };
        onChange(updated);
      }
    },
    [dragging, resizing, positions, onChange, getSVGPoint, snap],
  );

  const handleMouseUp = useCallback(() => {
    const gestureIndex = dragging?.index ?? resizing?.index ?? null;
    if (gestureIndex !== null && positions[gestureIndex]) {
      // Apply the grid snap once, at the end of the gesture.
      let next = [...positions];
      const p = next[gestureIndex];
      if (dragging) {
        next[gestureIndex] = { ...p, x: snap(p.x), y: snap(p.y) };
      } else if (resizing) {
        next[gestureIndex] = {
          ...p,
          width: Math.max(40, snap(p.width)),
          height: Math.max(40, snap(p.height)),
        };
      }
      onChange(next);
    }
    setDragging(null);
    setResizing(null);
  }, [dragging, resizing, positions, onChange, snap]);

  // Gestures listen on the window so a fast drag that momentarily
  // leaves the canvas doesn't drop the card mid-flight.
  useEffect(() => {
    if (!dragging && !resizing) return;
    const move = (e: MouseEvent) => handleMouseMove(e);
    const up = () => handleMouseUp();
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    return () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
  }, [dragging, resizing, handleMouseMove, handleMouseUp]);

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
    setEditLabel(pos.label || '');
    setEditKey(pos.key || String(contextMenu.index + 1));
    setEditMode(true);
  };

  const handleSaveEdit = () => {
    if (contextMenu === null) return;
    const updated = [...positions];
    updated[contextMenu.index] = {
      ...updated[contextMenu.index],
      label: editLabel,
      key: editKey || undefined,
    };
    onChange(updated);
    setEditMode(false);
    setContextMenu(null);
  };

  const handleCancelEdit = () => {
    setEditMode(false);
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

  // ── Layer ordering ──

  const handleBringToFront = () => {
    if (contextMenu === null) return;
    const maxZ = positions.reduce((max, p, i) => Math.max(max, p.z_index ?? i), 0);
    const current = positions[contextMenu.index].z_index ?? contextMenu.index;
    if (current >= maxZ) { setContextMenu(null); return; }
    const updated = [...positions];
    updated[contextMenu.index] = { ...updated[contextMenu.index], z_index: maxZ + 1 };
    onChange(updated);
    setContextMenu(null);
  };

  const handleSendToBack = () => {
    if (contextMenu === null) return;
    const minZ = positions.reduce((min, p, i) => Math.min(min, p.z_index ?? i), Infinity);
    const current = positions[contextMenu.index].z_index ?? contextMenu.index;
    if (current <= minZ) { setContextMenu(null); return; }
    const updated = [...positions];
    updated[contextMenu.index] = { ...updated[contextMenu.index], z_index: minZ - 1 };
    onChange(updated);
    setContextMenu(null);
  };

  const handleBringForward = () => {
    if (contextMenu === null) return;
    const currentZ = positions[contextMenu.index].z_index ?? contextMenu.index;
    // Find the position with the next higher z_index
    let nextZ = Infinity;
    let nextIdx = -1;
    positions.forEach((p, i) => {
      const z = p.z_index ?? i;
      if (z > currentZ && z < nextZ) {
        nextZ = z;
        nextIdx = i;
      }
    });
    if (nextIdx === -1) { setContextMenu(null); return; }
    const updated = [...positions];
    updated[contextMenu.index] = { ...updated[contextMenu.index], z_index: nextZ };
    updated[nextIdx] = { ...updated[nextIdx], z_index: currentZ };
    onChange(updated);
    setContextMenu(null);
  };

  const handleSendBackward = () => {
    if (contextMenu === null) return;
    const currentZ = positions[contextMenu.index].z_index ?? contextMenu.index;
    // Find the position with the next lower z_index
    let prevZ = -Infinity;
    let prevIdx = -1;
    positions.forEach((p, i) => {
      const z = p.z_index ?? i;
      if (z < currentZ && z > prevZ) {
        prevZ = z;
        prevIdx = i;
      }
    });
    if (prevIdx === -1) { setContextMenu(null); return; }
    const updated = [...positions];
    updated[contextMenu.index] = { ...updated[contextMenu.index], z_index: prevZ };
    updated[prevIdx] = { ...updated[prevIdx], z_index: currentZ };
    onChange(updated);
    setContextMenu(null);
  };

  // ── Grid lines ──

  const gridLines = [];
  if (gridEnabled) {
    const gx0 = Math.ceil(canvasBox.x / GRID_SIZE) * GRID_SIZE;
    const gy0 = Math.ceil(canvasBox.y / GRID_SIZE) * GRID_SIZE;
    for (let x = gx0; x < canvasBox.x + canvasBox.width; x += GRID_SIZE) {
      gridLines.push(
        <line key={`gx-${x}`} x1={x} y1={canvasBox.y} x2={x} y2={canvasBox.y + canvasBox.height} className="designer__grid-line" />,
      );
    }
    for (let y = gy0; y < canvasBox.y + canvasBox.height; y += GRID_SIZE) {
      gridLines.push(
        <line key={`gy-${y}`} x1={canvasBox.x} y1={y} x2={canvasBox.x + canvasBox.width} y2={y} className="designer__grid-line" />,
      );
    }
  }

  return (
    <div className={`designer ${readOnly ? 'designer--readonly' : ''}`}>
      {!readOnly && (
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
          <label className="designer__grid-toggle">
            <input
              type="checkbox"
              checked={showLabelsOnPositions}
              onChange={(e) => setShowLabelsOnPositions(e.target.checked)}
            />
            <span>Show Labels</span>
          </label>
          <span className="designer__canvas-size" title="Minimum working area — the canvas still grows if the spread needs more room">
            <span>Canvas ≥</span>
            <input
              type="number"
              min={200}
              step={GRID_SIZE}
              value={minCanvas.w}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (Number.isFinite(n)) setMinCanvas(mc => ({ ...mc, w: Math.max(200, n) }));
              }}
            />
            <span>×</span>
            <input
              type="number"
              min={200}
              step={GRID_SIZE}
              value={minCanvas.h}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (Number.isFinite(n)) setMinCanvas(mc => ({ ...mc, h: Math.max(200, n) }));
              }}
            />
            <button
              onClick={() => {
                setMinCanvas({ w: MIN_CANVAS_W, h: MIN_CANVAS_H });
                setCanvasBox(fitBox({ w: MIN_CANVAS_W, h: MIN_CANVAS_H }));
              }}
              title="Re-hug the canvas around the spread (plus margin)"
            >
              Fit
            </button>
          </span>
        </div>
      )}

      {/* Numeric inspector for the selected position — exact placement
          and sizing without fighting the drag handles. Values track
          live while dragging. */}
      {!readOnly && selectedIndex !== null && positions[selectedIndex] && (
        <div className="designer__inspector">
          <span className="designer__inspector-name">
            {positions[selectedIndex].key || selectedIndex + 1}
            {positions[selectedIndex].label ? ` · ${positions[selectedIndex].label}` : ''}
          </span>
          {(['x', 'y', 'width', 'height'] as const).map(f => (
            <label key={f} className="designer__inspector-field">
              <span>{f === 'width' ? 'W' : f === 'height' ? 'H' : f.toUpperCase()}</span>
              <input
                type="number"
                value={Math.round(positions[selectedIndex][f] ?? 0)}
                min={f === 'x' || f === 'y' ? 0 : 40}
                step={1}
                onChange={(e) => setSelectedField(f, e.target.value)}
              />
            </label>
          ))}
          <button
            onClick={applySizeToAll}
            disabled={positions.length < 2}
            title="Resize every position to match this one"
          >
            Match Size to All
          </button>
          <button onClick={() => duplicatePosition(selectedIndex)} title="Duplicate (Cmd+D)">
            Duplicate
          </button>
        </div>
      )}

      <div className="designer__canvas-wrapper">
        <svg
          ref={svgRef}
          className="designer__canvas"
          viewBox={`${canvasBox.x} ${canvasBox.y} ${canvasBox.width} ${canvasBox.height}`}
          style={{ aspectRatio: `${canvasBox.width} / ${canvasBox.height}` }}
          onClick={readOnly ? undefined : handleCanvasClick}
        >
          {/* Background */}
          <rect x={canvasBox.x} y={canvasBox.y} width={canvasBox.width} height={canvasBox.height} className="designer__bg" />

          {/* Grid (hidden in read-only mode) */}
          {!readOnly && gridLines}

          {/* Positions – rendered in z_index order (lowest first = behind) */}
          {renderOrder.map(({ pos, idx }) => {
            const isSelected = !readOnly && idx === selectedIndex;
            return (
              <g key={idx}>
                {/* Card rectangle */}
                <rect
                  x={pos.x}
                  y={pos.y}
                  width={pos.width}
                  height={pos.height}
                  className={`designer__position ${isSelected ? 'designer__position--selected' : ''}`}
                  onMouseDown={readOnly ? undefined : (e) => handlePositionMouseDown(e, idx)}
                  onContextMenu={readOnly ? undefined : (e) => handleContextMenu(e, idx)}
                  style={{ cursor: readOnly ? 'default' : dragging ? 'grabbing' : 'grab' }}
                />

                {/* Key badge (top-left corner) */}
                <circle
                  cx={pos.x + 12}
                  cy={pos.y + 12}
                  r={9}
                  className="designer__key-bg"
                />
                <text
                  x={pos.x + 12}
                  y={pos.y + 16}
                  className="designer__key-text"
                >
                  {pos.key || idx + 1}
                </text>

                {/* Label (center) - respect showLabels prop if provided, otherwise use internal toggle */}
                {(showLabels !== undefined ? showLabels : (readOnly || showLabelsOnPositions)) && (
                  <text
                    x={pos.x + pos.width / 2}
                    y={pos.y + pos.height / 2 + 4}
                    className="designer__label-text"
                  >
                    {pos.label}
                  </text>
                )}

                {/* Rotated indicator */}
                {pos.rotated && (
                  <text
                    x={pos.x + pos.width - 14}
                    y={pos.y + 15}
                    className="designer__rotated-icon"
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
                  >
                    {pos.deck_slot || deckSlots[0]?.key || 'A'}
                  </text>
                )}

                {/* Resize handle (hidden in read-only mode) */}
                {!readOnly && (
                  <rect
                    x={pos.x + pos.width - HANDLE_SIZE}
                    y={pos.y + pos.height - HANDLE_SIZE}
                    width={HANDLE_SIZE}
                    height={HANDLE_SIZE}
                    className={`designer__resize-handle ${isSelected ? 'designer__resize-handle--visible' : ''}`}
                    onMouseDown={(e) => handleResizeMouseDown(e, idx)}
                  />
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Context menu (hidden in read-only mode) */}
      {!readOnly && contextMenu && (
        <>
          <div className="designer__menu-overlay" onClick={() => { setContextMenu(null); setShowSlotMenu(false); setEditMode(false); }} />
          <div
            className="designer__context-menu"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            {editMode ? (
              <div className="designer__edit-form">
                <div className="designer__edit-field">
                  <label>Label:</label>
                  <input
                    type="text"
                    value={editLabel}
                    onChange={(e) => setEditLabel(e.target.value)}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveEdit();
                      if (e.key === 'Escape') handleCancelEdit();
                    }}
                  />
                </div>
                <div className="designer__edit-field">
                  <label>Key:</label>
                  <input
                    type="text"
                    value={editKey}
                    onChange={(e) => setEditKey(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveEdit();
                      if (e.key === 'Escape') handleCancelEdit();
                    }}
                  />
                </div>
                <div className="designer__edit-buttons">
                  <button onClick={handleSaveEdit}>Save</button>
                  <button onClick={handleCancelEdit}>Cancel</button>
                </div>
              </div>
            ) : (
              <>
                <button onClick={handleEditPosition}>Edit Label / Key</button>
                <button onClick={() => { duplicatePosition(contextMenu.index); setContextMenu(null); }}>
                  Duplicate
                </button>
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
                            {slot.key}: {slot.label || slotTypeLabel(slot)}
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
                <div className="designer__menu-separator" />
                <button onClick={handleBringToFront}>Bring to Front</button>
                <button onClick={handleBringForward}>Bring Forward</button>
                <button onClick={handleSendBackward}>Send Backward</button>
                <button onClick={handleSendToBack}>Send to Back</button>
                <div className="designer__menu-separator" />
                <button onClick={handleDeletePosition} className="designer__menu-danger">Delete</button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
