import { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import './MultiValueSelect.css';

interface MultiValueSelectProps {
  values: string[];
  options: string[];
  onCommit: (values: string[]) => void;
  placeholder?: string;
  compact?: boolean;
  /** Optional className for the root trigger button */
  className?: string;
}

/**
 * A compact multi-select that shows the currently-selected values as text,
 * and opens a popover with checkboxes when clicked. Changes are committed
 * when the popover closes (click outside, Escape, or Done button).
 *
 * The popover is rendered in a portal with fixed positioning so it isn't
 * clipped by scroll containers. When there isn't enough space below the
 * trigger, it flips and opens upward.
 *
 * Custom values that aren't in the options list are preserved in the
 * selection and shown at the top of the list with a "(custom)" marker.
 */
export default function MultiValueSelect({
  values,
  options,
  onCommit,
  placeholder = '—',
  compact = false,
  className = '',
}: MultiValueSelectProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[]>(values);
  const [filter, setFilter] = useState('');
  const [popoverStyle, setPopoverStyle] = useState<React.CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setDraft(values);
  }, [values]);

  // Commit on close
  const commitIfChanged = () => {
    const sortedDraft = [...draft].sort();
    const sortedValues = [...values].sort();
    if (JSON.stringify(sortedDraft) !== JSON.stringify(sortedValues)) {
      onCommit(draft);
    }
  };

  // Position the popover relative to the trigger; flip up if needed
  useLayoutEffect(() => {
    if (!open || !triggerRef.current) return;

    const positionPopover = () => {
      const trigger = triggerRef.current;
      const popover = popoverRef.current;
      if (!trigger) return;
      const triggerRect = trigger.getBoundingClientRect();
      const popoverHeight = popover?.offsetHeight ?? 320;
      const popoverWidth = popover?.offsetWidth ?? 240;
      const viewportHeight = window.innerHeight;
      const viewportWidth = window.innerWidth;
      const margin = 8;

      // Vertical: prefer below, flip above if not enough room
      const spaceBelow = viewportHeight - triggerRect.bottom;
      const spaceAbove = triggerRect.top;
      const openUpward = spaceBelow < popoverHeight + margin && spaceAbove > spaceBelow;

      let top: number;
      if (openUpward) {
        top = Math.max(margin, triggerRect.top - popoverHeight - 4);
      } else {
        top = triggerRect.bottom + 2;
      }

      // Horizontal: keep within viewport
      let left = triggerRect.left;
      if (left + popoverWidth + margin > viewportWidth) {
        left = Math.max(margin, viewportWidth - popoverWidth - margin);
      }

      // Cap max height so long option lists stay scrollable on screen
      const maxHeight = openUpward
        ? triggerRect.top - margin - 4
        : viewportHeight - triggerRect.bottom - margin - 4;

      setPopoverStyle({
        position: 'fixed',
        top,
        left,
        maxHeight: Math.max(160, maxHeight),
      });
    };

    positionPopover();
    // Re-position after the popover renders (so we have measured height)
    const raf = requestAnimationFrame(positionPopover);
    window.addEventListener('resize', positionPopover);
    window.addEventListener('scroll', positionPopover, true);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', positionPopover);
      window.removeEventListener('scroll', positionPopover, true);
    };
  }, [open, filter]);

  // Click-outside and escape to close
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target)) return;
      if (popoverRef.current?.contains(target)) return;
      commitIfChanged();
      setOpen(false);
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        commitIfChanged();
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, draft, values]);

  const toggle = (v: string) => {
    setDraft(prev =>
      prev.includes(v) ? prev.filter(x => x !== v) : [...prev, v]
    );
  };

  // Preserve custom values (not in options) at the top
  const customValues = draft.filter(v => !options.includes(v));
  const allEntries = [...customValues.map(v => ({ value: v, custom: true })),
                      ...options.map(v => ({ value: v, custom: false }))];

  const filtered = filter
    ? allEntries.filter(e => e.value.toLowerCase().includes(filter.toLowerCase()))
    : allEntries;

  const display = values.length > 0 ? values.join(', ') : placeholder;

  const popover = open ? (
    <div
      ref={popoverRef}
      className="multi-select__popover"
      style={popoverStyle}
    >
      {options.length > 6 && (
        <input
          type="text"
          className="multi-select__filter"
          placeholder="Filter..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          autoFocus
        />
      )}
      <div className="multi-select__list">
        {filtered.length === 0 && (
          <div className="multi-select__empty">No matches</div>
        )}
        {filtered.map(({ value, custom }) => (
          <label key={value} className="multi-select__option">
            <input
              type="checkbox"
              checked={draft.includes(value)}
              onChange={() => toggle(value)}
            />
            <span className="multi-select__option-label">
              {value}
              {custom && <span className="multi-select__custom-mark"> (custom)</span>}
            </span>
          </label>
        ))}
      </div>
      <div className="multi-select__footer">
        <button
          type="button"
          className="multi-select__clear-btn"
          onClick={() => setDraft([])}
          disabled={draft.length === 0}
        >
          Clear
        </button>
        <button
          type="button"
          className="multi-select__done-btn"
          onClick={() => {
            commitIfChanged();
            setOpen(false);
          }}
        >
          Done
        </button>
      </div>
    </div>
  ) : null;

  return (
    <div className={`multi-select ${compact ? 'multi-select--compact' : ''} ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        className={`multi-select__trigger ${values.length === 0 ? 'multi-select__trigger--empty' : ''}`}
        onClick={() => {
          if (open) {
            commitIfChanged();
            setOpen(false);
          } else {
            setOpen(true);
            setFilter('');
          }
        }}
      >
        <span className="multi-select__display">{display}</span>
        <span className="multi-select__caret">▾</span>
      </button>

      {popover && createPortal(popover, document.body)}
    </div>
  );
}
