import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import './SearchCombobox.css';

export interface ComboOption {
  id: number;
  label: string;
  /** Alternate names the option also matches on (e.g. a card's
   *  archetype: searching "Ace of Wands" finds "As de Bâtons"). */
  keywords?: string[];
  /** Dimmed text shown after the label in the list — makes keyword
   *  matches self-explanatory (typically the archetype name). */
  hint?: string;
}

interface SearchComboboxProps {
  options: ComboOption[];
  /** Currently selected option id (undefined = nothing selected) */
  value: number | undefined;
  /** Called with the chosen option, or null when cleared */
  onSelect: (option: ComboOption | null) => void;
  /** Fired after a deliberate selection (Enter/click) — used by the
   *  reading editor to auto-advance focus to the next position. */
  onCommitted?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export interface SearchComboboxHandle {
  focus: () => void;
}

/** Searchable picker: type to filter ("tow" → The Tower), arrow keys
 *  to navigate, Enter or click to select. Used for cards, spreads, and
 *  decks in the reading editor in place of long <select> dropdowns. */
const SearchCombobox = forwardRef<SearchComboboxHandle, SearchComboboxProps>(
  function SearchCombobox(
    { options, value, onSelect, onCommitted, disabled, placeholder },
    ref,
  ) {
    const inputRef = useRef<HTMLInputElement>(null);
    const listRef = useRef<HTMLUListElement>(null);
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [highlight, setHighlight] = useState(0);

    useImperativeHandle(ref, () => ({
      focus: () => {
        inputRef.current?.focus();
        inputRef.current?.select();
      },
    }));

    const selectedLabel = useMemo(
      () => options.find((o) => o.id === value)?.label ?? '',
      [options, value],
    );

    // Prefix matches rank above substring matches, so "tow" puts
    // "Tower" before "Two of Cups"... and vice versa for "two".
    // Label matches always rank above keyword (alternate-name) matches.
    const filtered = useMemo(() => {
      const q = query.trim().toLowerCase();
      if (!q) return options;
      const starts: ComboOption[] = [];
      const wordStarts: ComboOption[] = [];
      const contains: ComboOption[] = [];
      const keywordStarts: ComboOption[] = [];
      const keywordContains: ComboOption[] = [];
      for (const o of options) {
        const label = o.label.toLowerCase();
        if (label.startsWith(q)) { starts.push(o); continue; }
        if (label.split(/\s+/).some((w) => w.startsWith(q))) { wordStarts.push(o); continue; }
        if (label.includes(q)) { contains.push(o); continue; }
        const kws = o.keywords?.map((k) => k.toLowerCase()) ?? [];
        if (kws.some((k) => k.startsWith(q) || k.split(/\s+/).some((w) => w.startsWith(q)))) {
          keywordStarts.push(o);
        } else if (kws.some((k) => k.includes(q))) {
          keywordContains.push(o);
        }
      }
      return [...starts, ...wordStarts, ...contains, ...keywordStarts, ...keywordContains];
    }, [options, query]);

    useEffect(() => setHighlight(0), [query]);

    // Keep the highlighted option scrolled into view
    useEffect(() => {
      if (!open || !listRef.current) return;
      const el = listRef.current.children[highlight] as HTMLElement | undefined;
      el?.scrollIntoView({ block: 'nearest' });
    }, [highlight, open]);

    const commit = (option: ComboOption) => {
      onSelect(option);
      setOpen(false);
      setQuery('');
      onCommitted?.();
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        if (open) {
          // Swallow the Escape so it closes only the dropdown, not the
          // whole entry modal (Modal listens for Escape on window).
          e.stopPropagation();
          setOpen(false);
          setQuery('');
        }
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (!open) setOpen(true);
        else setHighlight((h) => Math.min(h + 1, filtered.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlight((h) => Math.max(h - 1, 0));
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        if (open && filtered[highlight]) commit(filtered[highlight]);
        return;
      }
      if (e.key === 'Tab') {
        // Tab confirms an unambiguous filtered choice, then moves on
        // naturally — lets a fast typist do "tow<Tab>ace<Tab>..."
        if (open && query.trim() && filtered[highlight]) {
          commit(filtered[highlight]);
        } else {
          setOpen(false);
        }
      }
    };

    return (
      <div className={`search-combobox ${disabled ? 'search-combobox--disabled' : ''}`}>
        <input
          ref={inputRef}
          className="search-combobox__input"
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          disabled={disabled}
          placeholder={placeholder ?? 'Type to search cards…'}
          value={open ? query : selectedLabel}
          onFocus={(e) => e.target.select()}
          onClick={() => {
            if (!open) {
              setOpen(true);
              setQuery('');
            }
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!open) setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            setOpen(false);
            setQuery('');
          }}
        />
        {value !== undefined && !disabled && !open && (
          <button
            type="button"
            className="search-combobox__clear"
            title="Clear card"
            // mousedown fires before the input's blur, keeping focus flow sane
            onMouseDown={(e) => {
              e.preventDefault();
              onSelect(null);
            }}
          >
            &times;
          </button>
        )}
        {open && (
          <ul className="search-combobox__list" ref={listRef} role="listbox">
            {filtered.length === 0 && (
              <li className="search-combobox__empty">No matching cards</li>
            )}
            {filtered.map((o, i) => (
              <li
                key={o.id}
                role="option"
                aria-selected={o.id === value}
                className={`search-combobox__option ${i === highlight ? 'search-combobox__option--active' : ''} ${o.id === value ? 'search-combobox__option--selected' : ''}`}
                // mousedown (not click) so it fires before the input blurs
                onMouseDown={(e) => {
                  e.preventDefault();
                  commit(o);
                }}
                onMouseEnter={() => setHighlight(i)}
              >
                {o.label}
                {o.hint && (
                  <span className="search-combobox__option-hint"> — {o.hint}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  },
);

export default SearchCombobox;
