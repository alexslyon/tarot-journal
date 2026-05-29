import { useState, useRef, useEffect } from 'react';
import { geocode, type GeocodeMatch } from '../../api/geocode';
import './PlaceLookupButton.css';

interface Props {
  /** Current place name (used as the lookup query). */
  query: string;
  /** Disable the button (e.g. when query is too short). */
  disabled?: boolean;
  /** Called when the user picks a match — the caller is responsible
   *  for stuffing latitude/longitude back into form state and
   *  (optionally) updating the place name to the canonical form. */
  onSelect: (m: GeocodeMatch) => void;
}

/** "Look up" button that opens an inline popover with geocoded matches.
 *  Used wherever a free-text place field needs to fill in lat/lon —
 *  profile birth place, journal entry location. */
export default function PlaceLookupButton({ query, disabled, onSelect }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<GeocodeMatch[]>([]);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    function onMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [open]);

  const handleClick = async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setOpen(true);
    setLoading(true);
    setError(null);
    try {
      const matches = await geocode(q, 12);
      setResults(matches);
    } catch (err) {
      setError('Geocoder request failed.');
      // eslint-disable-next-line no-console
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePick = (m: GeocodeMatch) => {
    onSelect(m);
    setOpen(false);
  };

  return (
    <div className="place-lookup" ref={containerRef}>
      <button
        type="button"
        className="place-lookup__btn"
        onClick={handleClick}
        disabled={disabled || query.trim().length < 2}
        title="Search GeoNames for this place"
      >
        Look up
      </button>
      {open && (
        <div className="place-lookup__popover" role="listbox">
          {loading ? (
            <div className="place-lookup__loading">
              Searching… (first lookup downloads the index, ~7 MB, one time)
            </div>
          ) : error ? (
            <div className="place-lookup__error">{error}</div>
          ) : results.length === 0 ? (
            <div className="place-lookup__empty">
              No matches — try a different spelling or a larger nearby city.
            </div>
          ) : (
            <ul className="place-lookup__list">
              {results.map((m, i) => (
                <li key={`${m.name}-${m.latitude}-${i}`}>
                  <button
                    type="button"
                    className="place-lookup__item"
                    onClick={() => handlePick(m)}
                  >
                    <span className="place-lookup__item-name">{m.display_name}</span>
                    <span className="place-lookup__item-coords">
                      {m.latitude.toFixed(3)}, {m.longitude.toFixed(3)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
