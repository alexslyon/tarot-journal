import { useState, useRef, useEffect } from 'react';
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
  const rootRef = useRef<HTMLDivElement>(null);

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

  // Click-outside and escape to close
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        commitIfChanged();
        setOpen(false);
      }
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

  return (
    <div className={`multi-select ${compact ? 'multi-select--compact' : ''} ${className}`} ref={rootRef}>
      <button
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

      {open && (
        <div className="multi-select__popover">
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
      )}
    </div>
  );
}
